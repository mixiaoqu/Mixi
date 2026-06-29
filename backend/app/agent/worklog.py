from __future__ import annotations

from app.agent.base import CapabilityRuntime, IntakeContext
from app.agent.graph.models import (
    AgentRequest,
    Artifact,
    CapabilityAvailability,
    CapabilityRuleMatch,
    ClarificationQuestion,
    ConversationPatch,
    IntentResult,
    PlanResult,
    PlanStep,
    RetryPolicy,
    SemanticIntent,
)
from app.agent.subgraphs.base import SubgraphContext
from app.agent.subgraphs.worklog import WorklogSubgraph
from app.schemas.worklog import WorklogGenerateRequest
from app.services.worklog_intake import WorklogIntakeExtractor

EXPLICIT_KEYWORDS = ("worklog", "工作日志", "工作日记", "日报", "周报")
ACTION_KEYWORDS = ("总结", "整理", "汇总", "生成", "写一份", "回顾")
OBJECT_KEYWORDS = ("工作", "进展", "提交", "代码变更", "开发内容", "项目进度", "日志")
EXCLUDED_LOG_KEYWORDS = ("错误日志", "系统日志", "访问日志", "运行日志", "审计日志", "api 日志", "api日志")


class WorklogCapability:
    id = "worklog.generate"
    name = "工作日志生成"
    description = "根据 Git 活动和用户补充事项生成日报、周报或指定时间范围的工作日志。"
    active_intent = "worklog"

    def catalog_entry(self) -> CapabilityAvailability:
        return CapabilityAvailability(
            capability=self.id,
            name=self.name,
            description=self.description,
        )

    def match(self, request: AgentRequest) -> CapabilityRuleMatch | None:
        prompt = request.prompt.strip()
        normalized = prompt.lower()
        if any(keyword in normalized for keyword in EXCLUDED_LOG_KEYWORDS):
            return None

        context_follow_up = (
            request.conversation.active_intent == self.active_intent
            and bool(request.conversation.missing_fields)
        )
        explicit = any(keyword in normalized for keyword in EXPLICIT_KEYWORDS)
        action_object = (
            any(keyword in normalized for keyword in ACTION_KEYWORDS)
            and any(keyword in normalized for keyword in OBJECT_KEYWORDS)
        )
        if not context_follow_up and not explicit and not action_object:
            return None

        slots = _extract_slots(prompt)
        missing = list(request.conversation.missing_fields)
        if "time_range" not in slots and "time_range" not in missing:
            missing.append("time_range")
        action = "compare" if _contains_compare_signal(prompt) else "generate"
        return CapabilityRuleMatch(
            rule_id="worklog.context_follow_up" if context_follow_up else "worklog.explicit",
            goal=prompt,
            intents=[SemanticIntent(action=action, objects=["worklog"], filters=slots)],
            extracted_slots=slots,
            missing_slots=missing,
            confidence=0.98 if explicit else 0.94,
            terminal=True,
        )

    def check_availability(self, runtime: CapabilityRuntime) -> CapabilityAvailability:
        data_sources = runtime.repositories.git_data_sources.list_by_user(runtime.current_user.id)
        return CapabilityAvailability(
            capability=self.id,
            name=self.name,
            description=self.description,
            available=bool(data_sources),
            missing_requirements=[] if data_sources else ["git_data_source"],
        )

    async def plan(
        self,
        context: IntakeContext,
        intent: IntentResult,
        *,
        attempt: int,
    ) -> PlanResult:
        data_sources = context.repositories.git_data_sources.list_by_user(context.current_user.id)
        intake = await WorklogIntakeExtractor(context.llm_client).extract(
            prompt=context.prompt.strip(),
            history=context.history,
            data_sources=data_sources,
            now=context.now,
        )
        patch = ConversationPatch(
            active_intent=None if intake.auto_run else self.active_intent,
            missing_fields=list(intake.missing_fields),
        )
        if not intake.auto_run:
            return PlanResult(
                status="blocked",
                objective=intent.goal,
                missing_requirements=list(intake.missing_fields),
                clarification_message=_build_follow_up_message(intake, has_data_sources=bool(data_sources)),
                conversation_patch=patch,
                attempt=attempt,
            )

        return PlanResult(
            status="ready",
            objective=intent.goal,
            steps=[
                PlanStep(
                    id="worklog",
                    title=self.name,
                    kind="subgraph",
                    target="worklog",
                    capability=self.id,
                    input_payload={
                        "data_source_id": intake.data_source_id,
                        "branch": intake.branch,
                        "start_at": intake.start_at.isoformat() if intake.start_at else None,
                        "end_at": intake.end_at.isoformat() if intake.end_at else None,
                        "user_prompt": intake.user_prompt,
                        "non_code_notes": intake.non_code_notes,
                        "missing_fields": intake.missing_fields,
                        "auto_run": intake.auto_run,
                    },
                    side_effect="reversible",
                    retry_policy=RetryPolicy(max_attempts=1, idempotent=False),
                )
            ],
            conversation_patch=patch,
            attempt=attempt,
        )

    def build_clarification(
        self,
        *,
        reason_code: str,
        missing_requirements: list[str],
        plan: PlanResult | None,
    ) -> tuple[str, list[ClarificationQuestion], ConversationPatch]:
        missing = list(dict.fromkeys(missing_requirements))
        if reason_code == "confirmation_required":
            message = f"请确认是否继续执行{self.name}任务。"
            questions = [ClarificationQuestion(field="confirmation", prompt=message)]
            patch = ConversationPatch(active_intent=self.active_intent, awaiting_confirmation=True)
            return message, questions, patch
        if plan is not None and plan.clarification_message:
            message = plan.clarification_message
        elif "git_data_source" in missing and "time_range" in missing:
            message = "请先连接 Git 数据源，并告诉我要生成今天、昨天还是本周的工作日志。"
        elif "git_data_source" in missing:
            message = "你还没有连接 Git 数据源。请先连接仓库，然后再生成工作日志。"
        elif "time_range" in missing:
            message = "请告诉我要生成今天、昨天还是本周的工作日志。"
        else:
            message = "请补充生成工作日志所需的信息。"
        questions = [ClarificationQuestion(field=field, prompt=message) for field in missing]
        patch = plan.conversation_patch if plan and plan.conversation_patch else ConversationPatch(
            active_intent=self.active_intent,
            missing_fields=missing,
        )
        return message, questions, patch

    async def execute(
        self,
        step: PlanStep,
        payload: dict[str, object],
        runtime: CapabilityRuntime,
    ) -> Artifact:
        if step.target != "worklog":
            raise ValueError(f"工作日志能力不支持执行目标：{step.target}")
        result = await WorklogSubgraph().run(
            context=SubgraphContext(
                current_user=runtime.current_user,
                repositories=runtime.repositories,
            ),
            request=WorklogGenerateRequest.model_validate(payload),
        )
        return Artifact(kind="worklog", data=result.model_dump(mode="json"))


def _extract_slots(prompt: str) -> dict[str, list[str]]:
    ranges = [
        value
        for token, value in (
            ("本周", "this_week"),
            ("这周", "this_week"),
            ("上周", "last_week"),
            ("这两周", "last_2_weeks"),
            ("近两周", "last_2_weeks"),
            ("最近两周", "last_2_weeks"),
            ("今天", "today"),
            ("今日", "today"),
            ("昨天", "yesterday"),
        )
        if token in prompt
    ]
    return {"time_range": list(dict.fromkeys(ranges))} if ranges else {}


def _contains_compare_signal(prompt: str) -> bool:
    return any(token in prompt.lower() for token in ("比较", "对比", "diff", "compare"))


def _build_follow_up_message(intake, *, has_data_sources: bool) -> str:
    if not has_data_sources:
        return "你还没有连接 Git 数据源。请先连接仓库，然后再生成工作日志。"
    prompts = []
    if "data_source" in intake.missing_fields:
        prompts.append("请告诉我要使用哪个 Git 数据源")
    if "time_range" in intake.missing_fields:
        prompts.append("请告诉我要生成今天、昨天还是本周的工作日志")
    return "，".join(prompts) if prompts else "请继续补充信息。"

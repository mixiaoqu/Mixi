from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.repositories.agent import AgentRepository
from app.db.repositories.git_data_source import GitDataSourceRepository
from app.db.repositories.knowledge import KnowledgeBaseRepository, KnowledgeDocumentRepository
from app.db.repositories.user import UserRepository, UserSessionRepository
from app.db.repositories.workflow import WorkflowRunRepository, WorkflowRunStepRepository
from app.db.repositories.workspace import WorkspaceMembershipRepository, WorkspaceRepository


@dataclass(slots=True)
class Repositories:
    users: UserRepository
    user_sessions: UserSessionRepository
    git_data_sources: GitDataSourceRepository
    workspaces: WorkspaceRepository
    workspace_memberships: WorkspaceMembershipRepository
    agents: AgentRepository
    knowledge_bases: KnowledgeBaseRepository
    knowledge_documents: KnowledgeDocumentRepository
    workflow_runs: WorkflowRunRepository
    workflow_run_steps: WorkflowRunStepRepository

    @classmethod
    def from_session(cls, session: Session) -> "Repositories":
        return cls(
            users=UserRepository(session),
            user_sessions=UserSessionRepository(session),
            git_data_sources=GitDataSourceRepository(session),
            workspaces=WorkspaceRepository(session),
            workspace_memberships=WorkspaceMembershipRepository(session),
            agents=AgentRepository(session),
            knowledge_bases=KnowledgeBaseRepository(session),
            knowledge_documents=KnowledgeDocumentRepository(session),
            workflow_runs=WorkflowRunRepository(session),
            workflow_run_steps=WorkflowRunStepRepository(session),
        )

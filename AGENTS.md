# Codex Project Rules

## Core Principle

Write code with the smallest clean change that solves the real problem. Prefer simple, readable, modern implementations over broad abstractions, extra compatibility layers, or speculative features.

## Execution Rules

- Keep changes minimal and focused on the user's actual request.
- Do not add extra compatibility, fallback paths, polyfills, framework layers, or configuration unless they are clearly required by the current project.
- Avoid over-engineering. Add abstractions only when they remove real duplication or make the code easier to understand and maintain.
- Follow current best practices for the project's stack. Prefer modern, maintained APIs and patterns over old or deprecated approaches.
- If the user's proposed approach is risky, outdated, unnecessarily complex, or misaligned with the project, explain the concern and recommend a better approach before implementing.
- Optimize for learning and long-term skill growth: choose solutions that teach good engineering habits, not quick hacks that hide important tradeoffs.
- Preserve the existing project style, architecture, naming, and component patterns unless there is a clear reason to improve them.
- Do not refactor unrelated code while completing a task.
- Keep feature pages and non-trivial components in dedicated files and directories. Do not place full pages, large visual components, or feature-specific styling inside `App.tsx` or another catch-all file.
- Make UI code clean, accessible, responsive, and consistent, but do not add decorative complexity that does not improve the user experience.
- Verify important changes with the fastest relevant check available, such as typecheck, lint, unit tests, or build.

## Decision Standard

When choosing between options, prefer the one that is:

1. Correct for the current requirement.
2. Simple to read and maintain.
3. Consistent with the existing codebase.
4. Modern and actively recommended.
5. Easy to extend only when extension is actually needed.

If a simpler solution is enough, use it.

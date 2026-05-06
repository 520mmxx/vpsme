# Goal Implementation Runbook

This is the execution guide for Codex goal-style work on OpenDeepSeek.

## Default Workflow

1. Read:

```text
AGENTS.md
docs/PROJECT-REQUIREMENTS-AND-STATUS.md
docs/OPENDEEPSEEK-CN-ROADMAP.md
docs/GOALS/OPENDEEPSEEK-CN.md
docs/GOALS/STATUS.md
```

2. Identify the `Next recommended goal` in `docs/GOALS/STATUS.md`.
3. Implement only that milestone.
4. Keep changes small and reviewable.
5. Run the milestone validation commands.
6. Fix validation failures before expanding scope.
7. Update `docs/GOALS/STATUS.md`.

## Scope Discipline

Do:

- Add docs, scripts, config templates, and tests inside the milestone scope.
- Prefer explicit placeholders for cloud registry/account values.
- Preserve existing international installation behavior.
- Preserve existing smoke tests.
- Keep Chinese user experience readable and practical.

Do not:

- Combine multiple milestones unless the user explicitly asks.
- Modify Bridge routing unless the milestone is M4 or M5.
- Lower Hermes output budgets.
- Expose Hermes/Bridge publicly by default.
- Commit secrets.
- Push, merge, tag, upload OSS/COS assets, or publish registry images without explicit approval.

## Validation Policy

Use `scripts/goal-check.sh` for common checks.

Milestone-specific commands in `OPENDEEPSEEK-CN.md` take priority.

If Docker or the OpenDeepSeek stack is intentionally stopped, record skipped runtime checks in `STATUS.md` instead of pretending they passed.

## Status Update Template

Append a dated entry to `docs/GOALS/STATUS.md`:

```markdown
## YYYY-MM-DD - Mx short title

Status: done | blocked | partial

Changed files:
- path

Validation:
- command: PASS/FAIL/SKIPPED - note

Decisions:
- decision

Risks:
- risk or none

Next recommended goal:
- /goal ...
```

## Recovery

If a validation fails:

1. Stop expanding scope.
2. Fix only the failing area.
3. Re-run the failing validation.
4. Update `STATUS.md` with the failure and fix.

If a task needs credentials or cloud console access:

1. Stop.
2. Document exactly what is needed.
3. Do not invent credentials or fake success.

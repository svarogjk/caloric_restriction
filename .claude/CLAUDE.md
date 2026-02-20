# GEO Survival Analysis

See @../README.md for project overview and @../backend/pyproject.toml for Python dependencies.

## Commands

```bash
# Run servers
cd backend && uv run python -m uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev

# Validate changes
cd frontend && npx tsc --noEmit   # Typecheck
cd frontend && npm run lint        # Lint
cd frontend && npm run build       # Build

# Tests
cd backend && uv run pytest
cd frontend && npm test
```

## Workflow

- After backend changes: run `uv run pytest` and fix failures before committing
- After frontend changes: run `npx tsc --noEmit` then `npm run build` to catch errors
- Prefer running single test files over full suites for speed

## Compaction

When compacting, preserve: list of modified files, test commands run, and any failing test output.

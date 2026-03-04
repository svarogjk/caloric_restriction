# GEO Survival Analysis

See @../README.md for project overview and @../backend/pyproject.toml for Python dependencies.

## Commands

```bash
# Servers
cd backend && uv run python -m uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev

# Backend validate
cd backend && uv run pytest
cd backend && uv run alembic upgrade head

# Frontend validate
cd frontend && npx tsc --noEmit && npm run build
```

## Architecture

- Chat uses **LangChain 1.x `create_agent`** (returns `CompiledStateGraph`, not `AgentExecutor`)
- Input format: `{"messages": [...]}` — `AgentExecutor`, `create_tool_calling_agent`, and `langchain.memory` do not exist in 1.x
- Tools defined in `backend/app/services/chat/agent_tools.py`
- RAG uses **pgvector** (PostgreSQL extension) via `langchain-postgres` `PGVector` store
- Embeddings always use `mistral-embed` (single key; Anthropic has no embedding API)
- Estimation uses LangChain `with_structured_output()` (not pydantic-ai)
- History trimming uses `trim_messages` from `langchain_core.messages` (replaces removed `ConversationSummaryBufferMemory`)

## Workflow

- After backend changes: `uv run pytest` (no tests configured yet — write them as you go)
- After frontend changes: `npx tsc --noEmit` then `npm run build`
- After DB model changes: generate migration with `uv run alembic revision --autogenerate -m "desc"`

## Roadmap

Product roadmap: `/roadmap` (view features + status), `/implement-feature F01` (implement specific feature), `/strategize` (plan new features), `/cleanup` (review + improve code).

## Compaction

When compacting, preserve: list of modified files, migration revision IDs applied, test commands run, and any failing output.

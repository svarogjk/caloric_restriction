# GEO Survival Analysis

See @../README.md for project overview and @../backend/pyproject.toml for Python dependencies.

## Commands

```bash
# Servers
cd backend && uv run python -m uvicorn app.main:app --reload --reload-dir app --port 8000
cd frontend && npm run dev

# Backend validate
cd backend && uv run pytest
cd backend && uv run alembic upgrade head

# Frontend validate
cd frontend && npx tsc --noEmit && npm run build
```

## Architecture

- Chat uses **pydantic-ai** `Agent` with tool calling and `run_stream()` for streaming
- Input: `agent.run(user_content, message_history=history, deps=deps)`
- Tools defined in `backend/app/services/chat/agent_tools.py`, registered via `AGENT_TOOLS` list
- RAG uses **numpy cosine similarity** over Mistral embeddings (no pgvector); index stored in `backend/data/`
- Embeddings always use `mistral-embed` via Mistral SDK (Anthropic has no embedding API)
- Estimation uses pydantic-ai structured output in `estimation_service.py`
- History trimming: char-count based (≤16 000 chars), drops oldest messages, in `PydanticAIService._trim_history()`
- Dynamic system prompt per request via `@agent.system_prompt` decorator reading `ctx.deps.user_settings`
- `set_deps()` invalidates cached agents — call it after all services are ready at startup

## Workflow

- After backend changes: `uv run pytest` (no tests configured yet — write them as you go)
- After frontend changes: `npx tsc --noEmit` then `npm run build`
- After DB model changes: generate migration with `uv run alembic revision --autogenerate -m "desc"`

## Roadmap

Product roadmap: `/roadmap` (view features + status), `/implement-feature F01` (implement specific feature), `/strategize` (plan new features), `/cleanup` (review + improve code).

## Compaction

When compacting, preserve: list of modified files, migration revision IDs applied, test commands run, and any failing output.

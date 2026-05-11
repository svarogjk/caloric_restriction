---
name: pydantic-ai-chat
description: PydanticAI Chat Integration — Agent setup, tool calling, streaming, history trimming, and multi-model support. Use when implementing or modifying the chat agent, tools, streaming, or conversation history.
---

# PydanticAI Chat Integration

> **Installed version: pydantic-ai 1.14+**
> Framework: `pydantic_ai.Agent` with `run_stream()` for streaming responses.

## Agent Setup (primary pattern)

```python
from pydantic_ai import Agent, RunContext
from app.services.chat.agent_tools import AgentDeps, AGENT_TOOLS

agent: Agent[AgentDeps, str] = Agent(
    model,                  # MistralModel or AnthropicModel instance
    deps_type=AgentDeps,
    system_prompt=BASE_SYSTEM_PROMPT,
    tools=AGENT_TOOLS,
)

# Dynamic per-request system prompt block — reads ctx.deps at run time
@agent.system_prompt
async def _settings_prompt(ctx: RunContext[AgentDeps]) -> str:
    return build_settings_block(ctx.deps.user_settings)
```

## Model Initialisation

```python
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.anthropic import AnthropicProvider

mistral = MistralModel("magistral-small-latest", provider=MistralProvider(api_key=key))
claude  = AnthropicModel("claude-haiku-4-5-20251001", provider=AnthropicProvider(api_key=key))
```

## Non-streaming Invocation

```python
result = await agent.run(
    user_content,
    message_history=history,   # list[ModelMessage]
    deps=deps,                  # AgentDeps instance
)
response_text = result.output
```

## Streaming

```python
async with agent.run_stream(
    user_content,
    message_history=history,
    deps=deps,
) as result:
    async for chunk in result.stream_text(delta=True):
        yield chunk

# After exhaustion — extract tool calls from this run
tools_invoked = [
    part.tool_name
    for msg in result.new_messages()
    for part in getattr(msg, "parts", [])
    if hasattr(part, "tool_name")
]
```

## History Format

```python
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

# Convert DB dicts to pydantic-ai message objects
def convert_history(messages: list[dict]) -> list[ModelMessage]:
    result = []
    for msg in messages:
        if msg["role"] == "user":
            result.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
        elif msg["role"] == "assistant":
            result.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
        # system messages handled via system_prompt parameter — skip here
    return result
```

## History Trimming

LangChain's `trim_messages` does not exist. Use char-count trimming instead:

```python
_MAX_HISTORY_CHARS = 16_000  # ≈ 4000 tokens at 4 chars/token

def trim_history(messages: list[ModelMessage]) -> list[ModelMessage]:
    def char_count(msgs):
        return sum(
            len(part.content)
            for m in msgs
            for part in m.parts
            if hasattr(part, "content") and isinstance(part.content, str)
        )

    while messages and char_count(messages) > _MAX_HISTORY_CHARS:
        messages = messages[1:]

    # History must start with a user (ModelRequest) message
    while messages and not isinstance(messages[0], ModelRequest):
        messages = messages[1:]

    return messages
```

## Tool Definition

Tools live in `backend/app/services/chat/agent_tools.py` and are registered at agent creation:

```python
from pydantic_ai import RunContext
from dataclasses import dataclass

@dataclass
class AgentDeps:
    rag_service: DatasetRAGService
    geo_client: GEOClient
    user_settings: dict | None
    user_id: str | None

async def search_known_datasets(ctx: RunContext[AgentDeps], query: str) -> str:
    """Search indexed GEO dataset metadata using semantic similarity."""
    docs = await ctx.deps.rag_service.search(query, k=5)
    return "\n".join(d["content"] for d in docs)

AGENT_TOOLS = [search_known_datasets, estimate_query, search_geo_datasets, get_gene_info, get_user_recent_results]
```

## RAG (numpy, not pgvector)

RAG is implemented in `dataset_rag_service.py` using Mistral embeddings + numpy cosine similarity. No PostgreSQL or pgvector required.

```python
# Index at startup
await rag_service.index_datasets()   # embeds new/changed JSON files in backend/datasets/

# Search
docs = await rag_service.search("bladder cancer survival", k=5)
# returns list[dict] with keys: accession, content, metadata
```

Index files persist in `backend/data/` (`rag_index.json`, `rag_docs.json`, `rag_embeddings.npy`).

## Dependency Injection

```python
# At startup, after all services are initialised:
pydantic_ai_service.set_deps(AgentDeps(
    rag_service=rag_service,
    geo_client=geo_client,
    user_settings=None,   # overridden per-request
    user_id=None,
))
# set_deps() clears self._agents so they are rebuilt with fresh deps
```

## File Locations

| File | Role |
|------|------|
| `backend/app/services/chat/pydantic_ai_service.py` | Core agent service — streaming, history, metrics |
| `backend/app/services/chat/agent_tools.py` | Tool definitions + `AgentDeps` dataclass |
| `backend/app/services/chat/dataset_rag_service.py` | numpy RAG indexing and search |
| `backend/app/services/chat/estimation_service.py` | Query pre-flight validation |
| `backend/app/api/chat_routes.py` | FastAPI endpoints; injects `AgentDeps` per-request |
| `backend/app/main.py` | Startup wiring — calls `set_deps()` after RAG init |

## Common Mistakes

| Wrong | Correct |
|-------|---------|
| `from langchain.agents import create_agent` | `from pydantic_ai import Agent` |
| `from langchain_core.messages import trim_messages` | char-count loop in `_trim_history()` |
| `from langchain_postgres import PGVector` | `DatasetRAGService` (numpy cosine similarity) |
| `from langchain_mistralai import ChatMistralAI` | `MistralModel(..., provider=MistralProvider(...))` |
| `result["messages"][-1].content` | `result.output` |
| `agent.astream_events(...)` | `agent.run_stream(...) → result.stream_text(delta=True)` |

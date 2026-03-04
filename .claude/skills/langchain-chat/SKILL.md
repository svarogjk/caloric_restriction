# LangChain Chat Integration (LangChain 1.x)

> **Installed version: LangChain 1.2.7**
> API is entirely different from 0.3.x.
> AgentExecutor, create_tool_calling_agent, and langchain.memory are all REMOVED.

## Agent (primary pattern)

Use create_agent from langchain.agents — returns a CompiledStateGraph (LangGraph-based).

```python
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

# Create once, reuse
agent = create_agent(
    model=llm,          # ChatMistralAI or ChatAnthropic instance
    tools=tools,        # list of @tool-decorated coroutines
    system_prompt="...",
)

# Invoke — input is a messages list
result = await agent.ainvoke({
    "messages": [*history, HumanMessage(content=user_input)]
})

# Last AI reply in returned state
ai_reply = result["messages"][-1].content
```

## Tool Definition

Tools live in backend/app/services/chat/agent_tools.py.

```python
from langchain_core.tools import tool

@tool
async def search_known_datasets(query: str) -> str:
    """Search indexed GEO dataset metadata using semantic similarity."""
    docs = await rag_service.search(query, k=5)
    return "
".join(doc.page_content for doc in docs)
```

Registered tools: search_known_datasets, estimate_query, search_geo_datasets, run_survival_analysis, get_gene_info.
Tools injected at startup via LangChainService.set_tools(tools) — invalidates cached agents.

## History Management (replaces ConversationSummaryBufferMemory)

langchain.memory is removed in 1.x. Use trim_messages from langchain_core.messages instead.

```python
from langchain_core.messages import trim_messages, BaseMessage

def trim_history(messages: list[BaseMessage]) -> list[BaseMessage]:
    return trim_messages(
        messages,
        strategy="last",
        max_tokens=16_000,
        token_counter=lambda msgs: sum(len(getattr(m, "content", "")) for m in msgs),
        start_on="human",
        end_on=("human", "tool"),
        include_system=False,
    )
```

## Streaming

```python
async for event in agent.astream_events({"messages": agent_messages}, version="v2"):
    if event["event"] == "on_chat_model_stream":
        chunk = event["data"].get("chunk")
        if chunk and chunk.content:
            yield chunk.content
```

For a plain chain (no tools):
```python
async for chunk in chain.astream({"history": history, "input": user_input}):
    if chunk.content:
        yield chunk.content
```

## Structured Output (estimation)

```python
from langchain_mistralai import ChatMistralAI
from pydantic import BaseModel

class AIEstimationResult(BaseModel):
    confidence_score: float
    estimated_datasets: int
    suggestions: list[str]

structured_llm = ChatMistralAI(model="mistral-small-latest").with_structured_output(AIEstimationResult)
result = await structured_llm.ainvoke([HumanMessage(content=prompt)])
# result is an AIEstimationResult instance
```

## pgvector RAG

```python
from langchain_postgres import PGVector
from langchain_mistralai import MistralAIEmbeddings

embeddings = MistralAIEmbeddings(model="mistral-embed", api_key=mistral_key)
store = PGVector(
    embeddings=embeddings,
    collection_name="geo_datasets",
    connection=postgresql_psycopg_url,  # must use postgresql+psycopg:// (psycopg3)
)
docs = await store.asimilarity_search(query, k=5)
```

Always use mistral-embed regardless of chat model — Anthropic has no embedding API.

## Model Initialisation

```python
from langchain_mistralai import ChatMistralAI
from langchain_anthropic import ChatAnthropic

mistral = ChatMistralAI(api_key=key, model="mistral-small-latest", streaming=True)
claude  = ChatAnthropic(api_key=key, model="claude-3-haiku-20240307", streaming=True)
```

## File Locations

| File | Role |
|------|------|
| backend/app/services/chat/langchain_service.py | Core agent/chain service |
| backend/app/services/chat/agent_tools.py | @tool definitions |
| backend/app/services/chat/dataset_rag_service.py | pgvector RAG indexing/search |
| backend/app/services/chat/estimation_service.py | query estimation with structured output |
| backend/app/api/chat_routes.py | FastAPI endpoints; exposes set_tools() |
| backend/app/main.py | Startup wiring — calls set_tools() after RAG init |

## Common Mistakes

| Wrong (0.3.x) | Correct (1.x) |
|---------------|---------------|
| from langchain.agents import create_tool_calling_agent, AgentExecutor | from langchain.agents import create_agent |
| from langchain.memory import ConversationSummaryBufferMemory | from langchain_core.messages import trim_messages |
| AgentExecutor.ainvoke({"input": x}) | agent.ainvoke({"messages": [*history, HumanMessage(content=x)]}) |
| result["output"] | result["messages"][-1].content |

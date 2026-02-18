---
name: langchain-chat
description: LangChain integration patterns for conversational AI. Use when building chat features, conversation chains, streaming responses, or integrating with Mistral/Anthropic models.
---

# LangChain Chat Integration

## Components

| Component | Purpose |
|-----------|---------|
| `ChatMistralAI` | Mistral model integration |
| `ChatAnthropic` | Claude model integration |
| `ChatPromptTemplate` | Structured prompt construction |
| `MessagesPlaceholder` | Insert conversation history |

## Initialize Models

```python
from langchain_mistralai import ChatMistralAI
from langchain_anthropic import ChatAnthropic

def init_models():
    return {
        "mistral": ChatMistralAI(
            api_key=os.getenv("MISTRAL_KEY"), model="mistral-small-latest",
            streaming=True, temperature=0.7,
        ),
        "anthropic": ChatAnthropic(
            api_key=os.getenv("ANTHROPIC_KEY"), model="claude-3-haiku-20240307",
            streaming=True, temperature=0.7,
        ),
    }
```

## Conversation Chain

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

def create_chat_chain(llm, system_prompt: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])
    return prompt | llm

def convert_messages(messages: list[dict]) -> list:
    type_map = {"user": HumanMessage, "assistant": AIMessage, "system": SystemMessage}
    return [type_map[msg["role"]](content=msg["content"]) for msg in messages]
```

## Streaming Response

```python
async def stream_response(chain, history: list, user_input: str) -> AsyncGenerator[str, None]:
    async for chunk in chain.astream({"history": history, "input": user_input}):
        if hasattr(chunk, "content"):
            yield chunk.content
```

## Service Pattern

```python
class LangChainService:
    def __init__(self):
        self.models = init_models()
        self.chains = {}

    def get_chain(self, model: str, system_prompt: str):
        key = f"{model}:{hash(system_prompt)}"
        if key not in self.chains:
            self.chains[key] = create_chat_chain(self.models[model], system_prompt)
        return self.chains[key]

    async def stream_chat(self, messages: list[dict], model: str = "mistral") -> AsyncGenerator[str, None]:
        chain = self.get_chain(model, self._get_system_prompt())
        history = convert_messages(messages[:-1])
        async for chunk in stream_response(chain, history, messages[-1]["content"]):
            yield chunk
```

## pydantic-ai Integration

```python
from pydantic_ai import Agent

class QueryEstimation(BaseModel):
    confidence: float
    suggestions: list[str]
    improved_query: str | None

estimation_agent = Agent(
    model=model_dict["mistral"],
    output_type=QueryEstimation,
    system_prompt="Evaluate survival analysis queries...",
)
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `RateLimitError` | Too many requests | Add delay between messages |
| Empty streaming | Model doesn't support streaming | Check model capabilities |
| Context too long | Too many messages | Use summary memory |
| Inconsistent responses | High temperature | Lower to 0.3-0.5 |

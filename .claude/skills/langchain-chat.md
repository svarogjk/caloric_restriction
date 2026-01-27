# LangChain Chat Skill

Use this skill when implementing conversational AI features with LangChain, including conversation chains, memory management, and streaming responses.

## Domain Knowledge

### Key Concepts

- **Conversation Chain**: Sequence of messages with context preservation
- **Memory**: Stores conversation history for context-aware responses
- **Streaming**: Token-by-token response delivery for better UX
- **Prompt Templates**: Structured prompts with variables and message history

### LangChain Components

| Component | Purpose |
|-----------|---------|
| `ChatMistralAI` | Mistral model integration |
| `ChatAnthropic` | Claude model integration |
| `ChatPromptTemplate` | Structured prompt construction |
| `MessagesPlaceholder` | Insert conversation history |
| `ConversationBufferMemory` | Store full message history |

## Code Patterns

### Initialize Chat Models

```python
from langchain_mistralai import ChatMistralAI
from langchain_anthropic import ChatAnthropic
import os

def init_models():
    return {
        "mistral": ChatMistralAI(
            api_key=os.getenv("MISTRAL_KEY"),
            model="mistral-small-latest",
            streaming=True,
            temperature=0.7,
        ),
        "anthropic": ChatAnthropic(
            api_key=os.getenv("ANTHROPIC_KEY"),
            model="claude-3-haiku-20240307",
            streaming=True,
            temperature=0.7,
        ),
    }
```

### Create Conversation Chain

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
```

### Convert Message History

```python
def convert_messages(messages: list[dict]) -> list:
    """Convert dict messages to LangChain format."""
    converted = []
    for msg in messages:
        if msg["role"] == "user":
            converted.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            converted.append(AIMessage(content=msg["content"]))
        elif msg["role"] == "system":
            converted.append(SystemMessage(content=msg["content"]))
    return converted
```

### Streaming Response

```python
from typing import AsyncGenerator

async def stream_response(
    chain,
    history: list,
    user_input: str,
) -> AsyncGenerator[str, None]:
    """Stream response tokens."""
    async for chunk in chain.astream({
        "history": history,
        "input": user_input,
    }):
        if hasattr(chunk, "content"):
            yield chunk.content
```

### Non-Streaming Response

```python
async def generate_response(
    chain,
    history: list,
    user_input: str,
) -> str:
    """Generate complete response."""
    response = await chain.ainvoke({
        "history": history,
        "input": user_input,
    })
    return response.content
```

### Memory Management

```python
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory

# For short conversations (< 20 messages)
buffer_memory = ConversationBufferMemory(
    return_messages=True,
    memory_key="history",
)

# For long conversations (summarize older messages)
summary_memory = ConversationSummaryMemory(
    llm=llm,
    return_messages=True,
    memory_key="history",
)
```

## Integration with pydantic-ai

The project uses pydantic-ai for structured outputs. Combine with LangChain:

```python
from pydantic_ai import Agent
from pydantic import BaseModel

class QueryEstimation(BaseModel):
    confidence: float
    suggestions: list[str]
    improved_query: str | None

# Use pydantic-ai for structured outputs
estimation_agent = Agent(
    model=model_dict["mistral"],
    output_type=QueryEstimation,
    system_prompt="Evaluate survival analysis queries...",
)

# Use LangChain for conversational flow
chat_chain = create_chat_chain(models["mistral"], system_prompt)
```

## Project Integration

### Service Pattern

```python
# backend/app/services/chat/langchain_service.py

class LangChainService:
    def __init__(self):
        self.models = init_models()
        self.chains = {}

    def get_chain(self, model: str, system_prompt: str):
        key = f"{model}:{hash(system_prompt)}"
        if key not in self.chains:
            self.chains[key] = create_chat_chain(
                self.models[model],
                system_prompt,
            )
        return self.chains[key]

    async def chat(
        self,
        messages: list[dict],
        model: str = "mistral",
    ) -> str:
        chain = self.get_chain(model, self._get_system_prompt())
        history = convert_messages(messages[:-1])
        user_input = messages[-1]["content"]
        return await generate_response(chain, history, user_input)

    async def stream_chat(
        self,
        messages: list[dict],
        model: str = "mistral",
    ) -> AsyncGenerator[str, None]:
        chain = self.get_chain(model, self._get_system_prompt())
        history = convert_messages(messages[:-1])
        user_input = messages[-1]["content"]
        async for chunk in stream_response(chain, history, user_input):
            yield chunk
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `RateLimitError` | Too many requests | Add delay between messages |
| Empty streaming | Model doesn't support streaming | Check model capabilities |
| Context too long | Too many messages | Use summary memory |
| Inconsistent responses | High temperature | Lower to 0.3-0.5 for accuracy |

## Dependencies

```toml
# Add to pyproject.toml
langchain>=0.1.0
langchain-mistralai>=0.1.0
langchain-anthropic>=0.1.0
langchain-core>=0.1.0
```

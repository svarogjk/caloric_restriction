# LangChain Exercises

Exercises based on patterns from `backend/app/services/chat/langchain_service.py` and the project's LLM integration.

## Beginner

### Exercise 1: Create a Chat Prompt Template
**Task**: Build a `ChatPromptTemplate` with a system message (bioinformatics assistant role), a few-shot example, and a human message placeholder. Format it with actual values and verify the output.
**Starter code**:
```python
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

def create_analysis_prompt(query: str, context: str = "") -> list:
    # TODO: Create system message template with bioinformatics assistant role
    #   Include: role description, instructions to be scientific, cite sources
    # TODO: Create human message template with {query} and optional {context} variables
    # TODO: Build ChatPromptTemplate from messages
    # TODO: Format with provided query and context
    # TODO: Return the formatted messages list
    return []
```
**Test criteria**:
- System message contains role instructions
- Human message includes the query and context
- Template formats correctly with different inputs
**Key concepts**: ChatPromptTemplate, message types, template variables, format_messages

### Exercise 2: Initialize a Chat Model
**Task**: Create a function that initializes either `ChatMistralAI` or `ChatAnthropic` based on a model name parameter. Configure temperature, streaming, and API keys from environment variables.
**Starter code**:
```python
import os
from langchain_mistralai import ChatMistralAI
from langchain_anthropic import ChatAnthropic

def get_chat_model(model_name: str = "mistral", temperature: float = 0.7, streaming: bool = True):
    # TODO: Map model names to providers:
    #   "mistral" → ChatMistralAI with MISTRAL_KEY
    #   "claude" → ChatAnthropic with ANTHROPIC_KEY
    # TODO: Configure temperature and streaming
    # TODO: Raise ValueError for unknown model names
    return None
```
**Test criteria**:
- Returns correct model class for each name
- Temperature and streaming configured, raises ValueError for unknown
**Key concepts**: ChatMistralAI, ChatAnthropic, model configuration, env vars

## Intermediate

### Exercise 3: Conversation Chain with Memory
**Task**: Build a conversation chain that maintains message history. Use `ConversationBufferWindowMemory` to keep the last 10 messages. The chain should include a system prompt and support multi-turn conversation.
**Starter code**:
```python
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def create_conversation_chain(model_name: str = "mistral"):
    # TODO: Create chat model using get_chat_model
    # TODO: Create prompt with system message and MessagesPlaceholder for history
    # TODO: Create ConversationBufferWindowMemory with k=10
    # TODO: Build ConversationChain with model, prompt, memory
    # TODO: Return the chain
    return None

async def chat(chain, user_message: str) -> str:
    # TODO: Call chain.apredict(input=user_message)
    # TODO: Return the response
    return ""
```
**Test criteria**:
- Chain maintains conversation history across calls
- Memory keeps only last 10 messages
- System prompt included in every call
**Key concepts**: ConversationChain, memory, MessagesPlaceholder, multi-turn

### Exercise 4: Streaming Response Handler
**Task**: Implement a streaming response handler that yields tokens as they arrive from the LLM. Include a callback handler that collects tokens and supports async iteration.
**Starter code**:
```python
from langchain_core.callbacks import AsyncCallbackHandler
from typing import AsyncIterator

class StreamingHandler(AsyncCallbackHandler):
    # TODO: __init__ with asyncio.Queue for tokens
    # TODO: async on_llm_new_token(token: str) - put token in queue
    # TODO: async on_llm_end(response) - put sentinel None in queue

async def stream_response(model, prompt: str) -> AsyncIterator[str]:
    # TODO: Create StreamingHandler
    # TODO: Call model.agenerate with callbacks=[handler]
    # TODO: Yield tokens from handler's queue until sentinel
    pass
```
**Test criteria**:
- Tokens yielded one at a time as they arrive
- Stream ends when LLM completes (sentinel received)
- Works with both Mistral and Anthropic models
**Key concepts**: AsyncCallbackHandler, streaming, asyncio.Queue, AsyncIterator

## Advanced

### Exercise 5: Structured Output with Pydantic
**Task**: Create a chain that returns structured output parsed into a Pydantic model. The chain should analyze a natural language query about gene expression and return a structured `QueryAnalysis` with extracted entities.
**Starter code**:
```python
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class QueryAnalysis(BaseModel):
    genes: list[str] = Field(description="Gene symbols mentioned")
    organism: str | None = Field(description="Organism (human, mouse, etc.)")
    cancer_type: str | None = Field(description="Cancer type if mentioned")
    has_survival_focus: bool = Field(description="Whether query focuses on survival")
    confidence: float = Field(ge=0, le=1, description="Confidence in extraction")

def create_analysis_chain(model_name: str = "mistral"):
    # TODO: Create PydanticOutputParser for QueryAnalysis
    # TODO: Create prompt that includes format_instructions from parser
    # TODO: Build chain: prompt | model | parser
    # TODO: Return the chain
    return None

async def analyze_query(chain, query: str) -> QueryAnalysis:
    # TODO: Invoke chain with query
    # TODO: Return parsed QueryAnalysis
    return QueryAnalysis(genes=[], organism=None, cancer_type=None, has_survival_focus=False, confidence=0)
```
**Test criteria**:
- Returns valid QueryAnalysis for various query types
- Extracts gene symbols, organism, cancer type correctly
- Confidence reflects extraction quality
**Key concepts**: PydanticOutputParser, structured output, LCEL chain, format instructions

### Exercise 6: Multi-Step Analysis Chain
**Task**: Build a multi-step chain: (1) analyze query to extract entities, (2) search for relevant context based on entities, (3) generate a response using the context. Use `RunnablePassthrough` for context passing between steps.
**Starter code**:
```python
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

def create_multi_step_chain(model_name: str = "mistral"):
    # TODO: Step 1 chain: query → QueryAnalysis (structured extraction)
    # TODO: Step 2 function: QueryAnalysis → search results (context retrieval)
    # TODO: Step 3 chain: (query + context) → final response
    # TODO: Compose: step1 | RunnableLambda(step2) | step3
    # TODO: Return the composed chain
    return None
```
**Test criteria**:
- Chain passes data between steps correctly
- Final response incorporates context from step 2
- Works end-to-end with a real query
**Key concepts**: LCEL composition, RunnablePassthrough, RunnableLambda, multi-step

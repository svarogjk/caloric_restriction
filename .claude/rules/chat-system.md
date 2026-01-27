# Chat System Rules

Rules for developing and maintaining the AI chat system.

## API Rules

| Rule | Enforcement |
|------|-------------|
| Always use streaming for chat responses | Required |
| Validate message content (1-5000 chars) | Required |
| Rate limit: 10 messages/minute per conversation | Required |
| Return conversation ID in all responses | Required |

## Service Layer Rules

1. **Async Everything**
   ```python
   # CORRECT
   async def send_message(self, conversation_id: str, content: str) -> ChatResponse:
       messages = await self.conversation_service.get_messages(conversation_id)

   # WRONG
   def send_message(self, conversation_id: str, content: str) -> ChatResponse:
       messages = self.conversation_service.get_messages(conversation_id)
   ```

2. **Always Save Messages**
   - Save user message BEFORE generating response
   - Save assistant message AFTER complete response
   - Include token count and model used

3. **Error Handling**
   ```python
   # Catch specific LLM errors
   from langchain_core.exceptions import OutputParserException
   from httpx import HTTPStatusError

   try:
       response = await chain.ainvoke(input)
   except HTTPStatusError as e:
       logger.error(f"LLM API error: {e.response.status_code}")
       raise ChatServiceError("AI service temporarily unavailable")
   except OutputParserException as e:
       logger.warning(f"Parse error: {e}")
       # Retry or return raw response
   ```

## Query Estimation Rules

1. **Always Estimate First**
   - Run estimation before expensive analysis
   - Show confidence score to user
   - Provide actionable suggestions

2. **Confidence Thresholds**
   | Score | Action |
   |-------|--------|
   | >= 0.7 | Proceed with analysis |
   | 0.4 - 0.7 | Show suggestions, allow proceed |
   | < 0.4 | Strongly suggest improvements |

3. **Required Suggestions**
   - If no survival keywords: suggest adding "survival", "prognosis"
   - If no cancer type: suggest specifying disease
   - If no organism: suggest "human" or "mouse"

## Frontend Rules

1. **Loading States**
   - Show typing indicator during AI response
   - Disable input while waiting
   - Show progress for long operations

2. **Message Display**
   - User messages: right-aligned, blue background
   - Assistant messages: left-aligned, gray background
   - System messages: centered, yellow background

3. **Error Handling**
   ```typescript
   // Always show user-friendly errors
   catch (error) {
       dispatch(setError(
           error instanceof Error
               ? error.message
               : "Failed to send message. Please try again."
       ))
   }
   ```

## Database Rules

1. **UUID for IDs**
   ```python
   import uuid
   id = str(uuid.uuid4())
   ```

2. **Soft Delete**
   - Don't hard delete conversations
   - Add `deleted_at` timestamp
   - Filter out deleted in queries

3. **Timestamps**
   - Always set `created_at` on insert
   - Always update `updated_at` on changes
   - Use UTC timezone

## Security Rules

1. **Input Validation**
   - Sanitize user input before storing
   - Escape HTML in message display
   - Limit message length

2. **No Sensitive Data in Prompts**
   - Don't include API keys in prompts
   - Don't log full message content
   - Mask any detected credentials

3. **Rate Limiting**
   - Per-conversation limits
   - Per-IP limits for unauthenticated
   - Exponential backoff on failures

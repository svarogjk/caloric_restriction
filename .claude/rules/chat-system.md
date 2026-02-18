---
paths:
  - "backend/app/**/chat*"
  - "backend/app/**/conversation*"
  - "backend/app/**/estimation*"
  - "backend/app/**/langchain*"
  - "frontend/src/**/*chat*"
  - "frontend/src/**/Chat*"
  - "frontend/src/**/Message*"
  - "frontend/src/**/Conversation*"
  - "frontend/src/**/QueryEstimation*"
---

# Chat System Rules

## API Requirements

- Always use streaming for chat responses
- Validate message content (1-5000 chars)
- Rate limit: 10 messages/minute per conversation
- Return conversation ID in all responses

## Message Persistence

- Save user message BEFORE generating response
- Save assistant message AFTER complete response
- Include token count and model used

## Error Handling

- Catch `HTTPStatusError` for LLM API failures → raise `ChatServiceError("AI service temporarily unavailable")`
- Catch `OutputParserException` → log warning, retry or return raw response
- Never expose raw LLM errors to users

## Query Estimation

- Always estimate before expensive analysis
- Confidence >= 0.7: proceed | 0.4-0.7: show suggestions | < 0.4: strongly suggest improvements
- Suggest "survival"/"prognosis" if missing survival keywords
- Suggest disease type if no cancer type specified

## Database

- Soft delete only: use `deleted_at` timestamp, filter in queries
- Always set `created_at`/`updated_at` (UTC)

## Security

- Sanitize user input before storing, escape HTML in display
- Never include API keys in prompts or log full message content
- Per-conversation and per-IP rate limiting

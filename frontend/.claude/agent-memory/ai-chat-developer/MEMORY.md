# AI Chat Developer Memory

## Streaming Implementation (F06, Mar 2026)

- `sendMessageStream` added to `/frontend/src/services/chatApi.ts` — uses `fetch` + `ReadableStream`, not axios
- Token passed explicitly to `sendMessageStream`; auth token retrieved via `getStoredToken()` from `authApi`
- `chatSlice.ts` has `isStreaming`, `streamingContent`, `streamingMessageId` state fields
- Reducers: `startStreaming(tempId)`, `appendStreamToken(token)`, `finalizeStreaming()`
- `sendMessage` thunk: optimistic user message -> `startStreaming` -> `sendMessageStream` -> on complete: `finalizeStreaming` + resolve
- `MessageList.tsx` accepts `isStreaming` + `streamingContent` props; shows streaming bubble with blinking cursor `&#9612;` while streaming, falls back to bouncing dots when `isLoading && !isStreaming`
- `ChatContainer.tsx` passes `isStreaming` and `streamingContent` from Redux to `MessageList`; also disables `ChatInput` when `isStreaming`

## SSE Event Format (backend)

Backend sends SSE with these event types:
- `{ type: 'token', content: '...' }` — partial AI token
- `{ type: 'message_complete', message: { message_id, role, content, created_at, model_used, suggested_actions } }` — final message
- `{ type: 'error', message: '...' }` — error

## Key File Paths

- `/frontend/src/services/chatApi.ts` — axios client + `sendMessageStream` fetch function
- `/frontend/src/store/chatSlice.ts` — all chat Redux state including streaming
- `/frontend/src/components/chat/MessageList.tsx` — renders messages + streaming bubble
- `/frontend/src/components/chat/ChatContainer.tsx` — wires Redux to components

## Preserved State (do not overwrite)

- `analysisProgress` / `runAnalysis` thunk — F05 agent
- `geneFilterInput` / `setGeneFilterInput` — F10 agent
- `conversationsLastFetched` with 30s TTL cache — caching architecture

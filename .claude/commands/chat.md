---
description: Start the AI chat development server and open chat interface
user-invocable: true
---

# /chat Command

Start the AI chat interface for survival analysis query assistance.

## Usage

```
/chat [action]
```

### Actions

| Action | Description |
|--------|-------------|
| `start` | Start both backend and frontend (default) |
| `backend` | Start only the backend chat API |
| `frontend` | Start only the frontend chat UI |
| `test` | Run chat system tests |

## Examples

```bash
# Start full chat system
/chat start

# Start backend only
/chat backend

# Run tests
/chat test
```

## What This Does

### /chat start
1. Ensures database is initialized
2. Starts FastAPI backend on port 8000
3. Starts React frontend on port 5173
4. Opens browser to chat interface

### Commands Executed

**Backend:**
```bash
cd backend && uv run python -m uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend && npm run dev
```

**Database Init:**
```bash
cd backend && uv run python -c "from app.config.database import init_db; init_db()"
```

## Chat Features

The chat interface provides:

1. **Conversation History** - Full message history with persistence
2. **Query Estimation** - Confidence scores before running analysis
3. **Improvement Suggestions** - AI-powered query optimization
4. **Model Selection** - Choose between Mistral and Claude
5. **Streaming Responses** - Real-time token delivery

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/conversations` | GET | List conversations |
| `/api/chat/conversations` | POST | Create conversation |
| `/api/chat/conversations/{id}/messages` | POST | Send message |
| `/api/chat/estimate` | POST | Estimate query |
| `/ws/chat/{id}` | WS | Streaming chat |

## Troubleshooting

**Port already in use:**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

**Database not found:**
```bash
# Initialize database
cd backend && uv run python -c "from app.config.database import init_db; init_db()"
```

**Missing dependencies:**
```bash
cd backend && uv sync
cd frontend && npm install
```

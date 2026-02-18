---
description: Start the FastAPI backend development server on port 8000 with hot reload
user-invocable: true
---

# Run Backend Server

Start the backend server:

```bash
cd backend && uv run python -m uvicorn app.main:app --reload --port 8000
```

- **Port**: 8000
- **Hot Reload**: Enabled
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

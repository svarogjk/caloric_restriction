# Run Backend Server

Start the FastAPI backend development server.

## Usage

Run this command to start the backend server with hot reload enabled.

## Execution

```bash
cd backend && uv run python -m uvicorn app.main:app --reload --port 8000
```

## Details

- **Port:** 8000
- **Hot Reload:** Enabled (auto-restarts on code changes)
- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **Alternative Docs:** http://localhost:8000/redoc (ReDoc)

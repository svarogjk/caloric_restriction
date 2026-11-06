.PHONY: dev backend frontend

# Start backend (port 8000) and frontend (port 5173) together; Ctrl+C stops both.
dev:
	@trap 'kill 0' INT TERM EXIT; \
	(cd backend && uv run python -m uvicorn app.main:app --reload --reload-dir app --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

backend:
	cd backend && uv run python -m uvicorn app.main:app --reload --reload-dir app --port 8000

frontend:
	cd frontend && npm run dev

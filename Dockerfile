# ── Stage 1: Build React frontend ──────────────────────────────────────────────
FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
# Cache npm package downloads; invalidated only when lock file changes
RUN --mount=type=cache,target=/root/.npm \
    npm ci --silent
COPY frontend/ .
RUN npm run build

# ── Stage 2: Install Python dependencies ───────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS python-build
WORKDIR /app
# Bind-mount lock files so they are available during install without becoming
# image layers. Cache mount persists uv's download cache across builds.
# Invalidated only when pyproject.toml or uv.lock changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    uv sync --no-dev --frozen --no-install-project

# ── Stage 3: Production runtime ────────────────────────────────────────────────
FROM python:3.13-slim AS runtime
WORKDIR /app

# Copy installed packages from build stage
COPY --from=python-build /app/.venv /app/.venv

# Copy backend source and migrations
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini .

# Copy compiled frontend assets
COPY --from=frontend-build /frontend/dist ./frontend/dist

# Create dirs that are mounted as Railway volumes at runtime
# data/ also holds the SQLite database file (geo_chat.db) and RAG index
RUN mkdir -p geo_logs platform_mappings data datasets

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Use shell form so Railway's $PORT variable is expanded at runtime
CMD sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"

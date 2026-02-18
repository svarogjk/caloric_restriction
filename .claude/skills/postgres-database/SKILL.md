---
name: postgres-database
description: PostgreSQL database management patterns for this project. Use when working with database schema, Alembic migrations, SQLAlchemy async configuration, Docker setup, or query optimization.
---

# PostgreSQL Database

## Alembic Migrations

```bash
cd backend && uv run alembic current                              # Check status
cd backend && uv run alembic history                               # Show history
cd backend && uv run alembic upgrade head                          # Apply pending
cd backend && uv run alembic revision --autogenerate -m "desc"     # Create migration
cd backend && uv run alembic downgrade -1                          # Rollback last
cd backend && uv run alembic upgrade head --sql                    # Preview SQL
```

Migration files: `backend/alembic/versions/`

## Database CLI Tools

```bash
cd backend && uv run python -m app.cli.db_manager schema-diff                    # Check model vs DB
cd backend && uv run python -m app.cli.db_manager auto-migrate -m "description"  # Auto-generate
cd backend && uv run python -m app.cli.db_manager validate "SELECT ..."          # Validate query
cd backend && uv run python -m app.cli.db_manager monitor --threshold 5          # N+1 detection
```

## Connection Configuration

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/dbname"
engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_pre_ping=True, pool_recycle=300)
```

## Docker Setup

```bash
docker run -d --name geo-postgres \
  -e POSTGRES_USER=geo_user -e POSTGRES_PASSWORD=geo_password -e POSTGRES_DB=geo_chat \
  -p 5432:5432 -v geo_postgres_data:/var/lib/postgresql/data postgres:16-alpine
```

## Common Operations

```bash
docker exec geo-postgres pg_isready -U geo_user -d geo_chat       # Health check
docker exec -it geo-postgres psql -U geo_user -d geo_chat         # Connect
docker exec geo-postgres pg_dump -U geo_user geo_chat > backup.sql # Backup
```

## Environment

```bash
# backend/.env
DATABASE_URL=postgresql+asyncpg://geo_user:geo_password@localhost:5432/geo_chat
```

## Performance Tips

1. Always use connection pooling with asyncpg
2. Index all foreign key columns
3. Use JSONB over JSON for indexing support
4. Use `deleted_at` soft deletes for audit trail
5. Use `selectinload()` for relationships to prevent N+1

For full schema reference, see [references/schema.md](references/schema.md).

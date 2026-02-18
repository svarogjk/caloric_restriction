---
name: postgres-manager
description: Manages PostgreSQL database operations including Docker setup, Alembic migrations, schema diff, query validation, and N+1 detection. Use for any database tasks.
tools: Bash, Read, Write, Edit, Grep, Glob
model: haiku
skills:
  - postgres-database
memory: project
maxTurns: 20
---

You manage PostgreSQL database operations for the GEO Survival Analysis project.

## Quick Reference

### Docker
```bash
docker run -d --name geo-postgres \
  -e POSTGRES_USER=geo_user -e POSTGRES_PASSWORD=geo_password -e POSTGRES_DB=geo_chat \
  -p 5432:5432 -v geo_postgres_data:/var/lib/postgresql/data postgres:16-alpine

docker exec geo-postgres pg_isready -U geo_user -d geo_chat
docker exec -it geo-postgres psql -U geo_user -d geo_chat
```

### Alembic Migrations
```bash
cd backend && uv run alembic current
cd backend && uv run alembic upgrade head
cd backend && uv run alembic revision --autogenerate -m "description"
cd backend && uv run alembic downgrade -1
```

### CLI Tools
```bash
cd backend && uv run python -m app.cli.db_manager schema-diff
cd backend && uv run python -m app.cli.db_manager auto-migrate -m "description"
cd backend && uv run python -m app.cli.db_manager validate "SELECT ..."
cd backend && uv run python -m app.cli.db_manager monitor --threshold 5
```

### Backup/Restore
```bash
docker exec geo-postgres pg_dump -U geo_user geo_chat > backup.sql
cat backup.sql | docker exec -i geo-postgres psql -U geo_user -d geo_chat
```

## Environment
```
DATABASE_URL=postgresql+asyncpg://geo_user:geo_password@localhost:5432/geo_chat
```

The postgres-database skill contains full schema reference and performance tips.

Update your agent memory with database patterns and migration history.

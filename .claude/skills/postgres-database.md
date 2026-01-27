# PostgreSQL Database Skill

Domain knowledge for PostgreSQL database management in this project.

## Project Database Schema

### Tables

```sql
-- Users table (authentication)
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    disabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table
CREATE TABLE conversations (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255),
    context_type VARCHAR(50) DEFAULT 'general',
    analysis_query TEXT,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Messages table
CREATE TABLE messages (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    tokens_used INTEGER,
    model_used VARCHAR(50),
    is_complete BOOLEAN DEFAULT TRUE,
    tool_calls JSONB,
    estimation_id VARCHAR(36) REFERENCES query_estimations(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Query estimations table
CREATE TABLE query_estimations (
    id VARCHAR(36) PRIMARY KEY,
    original_query TEXT NOT NULL,
    confidence_score FLOAT NOT NULL,
    estimated_datasets INTEGER,
    estimated_time_seconds FLOAT,
    can_proceed BOOLEAN,
    suggestions JSONB,
    improved_query TEXT,
    has_survival_keywords BOOLEAN DEFAULT FALSE,
    has_cancer_type BOOLEAN DEFAULT FALSE,
    has_organism BOOLEAN DEFAULT FALSE,
    has_gene_focus BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX ix_users_username ON users(username);
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_conversations_user_id ON conversations(user_id);
CREATE INDEX ix_conversations_created_at ON conversations(created_at);
CREATE INDEX ix_conversations_updated_at ON conversations(updated_at);
CREATE INDEX ix_messages_conversation_id ON messages(conversation_id);
CREATE INDEX ix_messages_created_at ON messages(created_at);
CREATE INDEX ix_query_estimations_created_at ON query_estimations(created_at);
```

## Database Management CLI

Utilities for schema management, query validation, and N+1 detection.

### Schema Diff
```bash
# Check if models match database schema
cd backend && uv run python -m app.cli.db_manager schema-diff
```

### Auto-Generate Migrations
```bash
# Detect changes and create migration
cd backend && uv run python -m app.cli.db_manager auto-migrate -m "description"
```

### Query Validation
```bash
# Validate a query before execution
cd backend && uv run python -m app.cli.db_manager validate "SELECT * FROM users WHERE email = 'test@example.com'"

# Validate queries in a file
cd backend && uv run python -m app.cli.db_manager validate-file queries.sql
```

### N+1 Query Detection
```bash
# Monitor queries for N+1 patterns
cd backend && uv run python -m app.cli.db_manager monitor --threshold 5
```

## Alembic Migrations

Schema changes are managed via Alembic. Never modify tables directly in production.

### Common Commands

```bash
# Check current migration status
cd backend && uv run alembic current

# Show migration history
cd backend && uv run alembic history

# Apply all pending migrations
cd backend && uv run alembic upgrade head

# Create new migration after model changes
cd backend && uv run alembic revision --autogenerate -m "description"

# Rollback last migration
cd backend && uv run alembic downgrade -1

# Show SQL without executing
cd backend && uv run alembic upgrade head --sql
```

### Migration Files Location
```
backend/alembic/versions/
```

## Connection Configuration

### asyncpg with SQLAlchemy

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/dbname"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)
```

### Connection Pool Settings

| Setting | Development | Production |
|---------|-------------|------------|
| pool_size | 5 | 20 |
| max_overflow | 10 | 30 |
| pool_recycle | 300 | 1800 |
| pool_pre_ping | True | True |

## Docker Configuration

### Default Container

```bash
docker run -d \
  --name geo-postgres \
  -e POSTGRES_USER=geo_user \
  -e POSTGRES_PASSWORD=geo_password \
  -e POSTGRES_DB=geo_chat \
  -p 5432:5432 \
  -v geo_postgres_data:/var/lib/postgresql/data \
  postgres:16-alpine
```

### Docker Compose (Alternative)

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    container_name: geo-postgres
    environment:
      POSTGRES_USER: geo_user
      POSTGRES_PASSWORD: geo_password
      POSTGRES_DB: geo_chat
    ports:
      - "5432:5432"
    volumes:
      - geo_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U geo_user -d geo_chat"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  geo_postgres_data:
```

## Common Operations

### Check if PostgreSQL is Running
```bash
docker exec geo-postgres pg_isready -U geo_user -d geo_chat
```

### Connect via psql
```bash
docker exec -it geo-postgres psql -U geo_user -d geo_chat
```

### List Tables
```sql
\dt
```

### Describe Table
```sql
\d+ conversations
```

### Count Records
```sql
SELECT
    (SELECT COUNT(*) FROM users) as users,
    (SELECT COUNT(*) FROM conversations) as conversations,
    (SELECT COUNT(*) FROM messages) as messages,
    (SELECT COUNT(*) FROM query_estimations) as estimations;
```

## Performance Tips

### 1. Use Connection Pooling
Always use connection pooling with asyncpg to avoid connection overhead.

### 2. Index Foreign Keys
All foreign key columns should be indexed for faster JOINs.

### 3. JSONB Over JSON
Use JSONB type for JSON data - it's faster and supports indexing.

### 4. Soft Deletes
Use `deleted_at` timestamp instead of hard deletes for audit trail.

### 5. Partial Indexes
Create partial indexes for common filtered queries:
```sql
CREATE INDEX idx_active_conversations
ON conversations(updated_at)
WHERE deleted_at IS NULL;
```

## Backup & Restore

### Backup
```bash
docker exec geo-postgres pg_dump -U geo_user geo_chat > backup_$(date +%Y%m%d).sql
```

### Restore
```bash
cat backup.sql | docker exec -i geo-postgres psql -U geo_user -d geo_chat
```

### Backup with Compression
```bash
docker exec geo-postgres pg_dump -U geo_user geo_chat | gzip > backup_$(date +%Y%m%d).sql.gz
```

## Troubleshooting

### Connection Refused
1. Check container is running: `docker ps | grep postgres`
2. Check port binding: `docker port geo-postgres`
3. Check PostgreSQL is ready: `docker exec geo-postgres pg_isready`

### Authentication Failed
1. Verify credentials in .env match Docker environment
2. Check pg_hba.conf allows connections
3. Try resetting password: `ALTER USER geo_user PASSWORD 'new_password';`

### Slow Queries
1. Enable query logging: `SET log_statement = 'all';`
2. Check for missing indexes: `EXPLAIN ANALYZE <query>`
3. Monitor with pg_stat_statements extension

### Out of Connections
1. Check max_connections setting
2. Verify pool settings in application
3. Look for connection leaks: `SELECT * FROM pg_stat_activity;`

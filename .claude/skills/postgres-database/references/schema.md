# PostgreSQL Schema Reference

## Tables

```sql
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
```

## Indexes

```sql
CREATE INDEX ix_users_username ON users(username);
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_conversations_user_id ON conversations(user_id);
CREATE INDEX ix_conversations_created_at ON conversations(created_at);
CREATE INDEX ix_conversations_updated_at ON conversations(updated_at);
CREATE INDEX ix_messages_conversation_id ON messages(conversation_id);
CREATE INDEX ix_messages_created_at ON messages(created_at);
CREATE INDEX ix_query_estimations_created_at ON query_estimations(created_at);

-- Partial index for active conversations
CREATE INDEX idx_active_conversations ON conversations(updated_at) WHERE deleted_at IS NULL;
```

## Connection Pool Settings

| Setting | Development | Production |
|---------|-------------|------------|
| pool_size | 5 | 20 |
| max_overflow | 10 | 30 |
| pool_recycle | 300 | 1800 |
| pool_pre_ping | True | True |

## Docker Compose

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

## Troubleshooting

| Issue | Check | Solution |
|-------|-------|----------|
| Connection Refused | `docker ps \| grep postgres` | Start container |
| Auth Failed | Credentials in .env vs Docker | Reset password with ALTER USER |
| Slow Queries | `EXPLAIN ANALYZE <query>` | Add indexes |
| Out of Connections | `SELECT * FROM pg_stat_activity;` | Increase pool_size |

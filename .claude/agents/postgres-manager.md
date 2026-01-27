---
name: postgres-manager
description: Manages PostgreSQL database operations including installation, configuration, migrations, and troubleshooting
tools: Bash, Read, Write, Edit, Grep, Glob
model: haiku
skills: postgres-database
---

# PostgreSQL Manager Agent

Specialized agent for managing PostgreSQL database operations in the GEO Survival Analysis project.

## Capabilities

1. **Installation**
   - Docker-based PostgreSQL setup
   - Native installation guidance
   - Version management

2. **Configuration**
   - Connection string setup
   - Environment variable management
   - Performance tuning

3. **Database Operations**
   - Create/drop databases
   - User management
   - Table creation and migrations
   - **Auto-generate migrations from model changes**
   - **Schema diff analysis**

4. **Troubleshooting**
   - Connection issues
   - Performance problems
   - Data integrity checks
   - **N+1 query detection**

5. **Query Validation**
   - **Pre-execution query validation**
   - SQL syntax checking
   - Performance prediction

## Common Tasks

### Install PostgreSQL via Docker
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

### Check Connection
```bash
docker exec geo-postgres pg_isready -U geo_user -d geo_chat
```

### Initialize Database Tables (Legacy - prefer Alembic)
```bash
cd backend && uv run python -c "
import asyncio
from app.config.database import init_db
asyncio.run(init_db())
"
```

## Alembic Migrations

### Check Current Migration Status
```bash
cd backend && uv run alembic current
```

### Show Migration History
```bash
cd backend && uv run alembic history
```

### Apply All Pending Migrations
```bash
cd backend && uv run alembic upgrade head
```

### Create New Migration (after model changes)
```bash
cd backend && uv run alembic revision --autogenerate -m "description_of_changes"
```

### Rollback Last Migration
```bash
cd backend && uv run alembic downgrade -1
```

### Rollback All Migrations
```bash
cd backend && uv run alembic downgrade base
```

### Show SQL Without Executing
```bash
cd backend && uv run alembic upgrade head --sql
```

### Backup Database
```bash
docker exec geo-postgres pg_dump -U geo_user geo_chat > backup.sql
```

### Restore Database
```bash
cat backup.sql | docker exec -i geo-postgres psql -U geo_user -d geo_chat
```

## Environment Setup

Ensure `backend/.env` contains:
```
DATABASE_URL=postgresql+asyncpg://geo_user:geo_password@localhost:5432/geo_chat
```

## Monitoring Queries

### Check active connections
```sql
SELECT * FROM pg_stat_activity WHERE datname = 'geo_chat';
```

### Check table sizes
```sql
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### Check slow queries
```sql
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## Advanced Capabilities

### 1. Auto-Generate Migrations from Model Changes

**Quick command using CLI tool:**

```bash
# Detect changes and auto-generate migration
cd backend && uv run python -m app.cli.db_manager auto-migrate -m "add_user_preferences"

# Or use the manual workflow:
# Step 1: Check for schema differences
cd backend && uv run python -m app.cli.db_manager schema-diff

# Step 2: Generate migration if changes detected
cd backend && uv run alembic revision --autogenerate -m "add_user_preferences_table"

# Step 3: Review generated migration file
cat backend/alembic/versions/<latest_revision>.py

# Step 4: Apply migration
cd backend && uv run alembic upgrade head
```

**Workflow for model changes:**
1. Modify models in `backend/app/models/database.py`
2. Run model change detection script
3. Generate migration with `alembic revision --autogenerate`
4. **ALWAYS review generated migration** - autogenerate may miss some changes
5. Apply migration with `alembic upgrade head`

### 2. Validate Queries Before Execution

**Quick command using CLI tool:**

```bash
# Validate a single query
cd backend && uv run python -m app.cli.db_manager validate \
  "SELECT u.username, COUNT(c.id) FROM users u LEFT JOIN conversations c ON u.id = c.user_id GROUP BY u.username"

# Validate all queries in a file
cd backend && uv run python -m app.cli.db_manager validate-file queries.sql

# Or use programmatically:
cd backend && uv run python -c "
import asyncio
from app.config.database import get_db
from app.utils.query_validator import validate_query

async def check_query():
    async for session in get_db():
        result = await validate_query(session, '''
            SELECT u.username, COUNT(c.id) as conversation_count
            FROM users u
            LEFT JOIN conversations c ON u.id = c.user_id
            GROUP BY u.username
        ''')

        if result['valid']:
            print('✅ Query is valid')
            print(f\"Cost: {result['analysis']['total_cost']}\")
            if result['analysis']['warnings']:
                print('Warnings:', result['analysis']['warnings'])
        else:
            print(f\"❌ Invalid: {result['error']}\")
        break

asyncio.run(check_query())
"
```

**Query validation checklist:**
- ✓ Syntax is valid
- ✓ Tables and columns exist
- ✓ No sequential scans on large tables
- ✓ Indexes are being used
- ✓ Join conditions are correct
- ✓ No N+1 patterns

### 3. Schema Diff Analysis

**Quick command using CLI tool:**

```bash
# Quick schema diff check
cd backend && uv run python -m app.cli.db_manager schema-diff

# Or use programmatically:
cd backend && uv run python -c "
from app.utils.schema_diff import SchemaDiff

diff = SchemaDiff()
diff.print_report()

# Get structured diff data
full_diff = diff.get_full_diff()
print(f\"Has changes: {full_diff['has_changes']}\")
"
```

**Check what SQL migrations would generate:**

```bash
# Generate current schema SQL (without executing)
cd backend && uv run alembic upgrade head --sql > pending_changes.sql

# View first 50 lines of changes
cd backend && uv run alembic upgrade head --sql | head -50
```

**When to use schema diff:**
- Before generating migrations - see what will change
- After deployment - verify schema matches models
- During troubleshooting - identify schema drift
- Code reviews - understand migration impact

### 4. Debug N+1 Queries

**Quick monitoring using CLI tool:**

```bash
# Start query monitoring (run in background while testing)
cd backend && uv run python -m app.cli.db_manager monitor --threshold 5

# Then run your application/tests and watch for alerts
cd backend && uv run pytest tests/

# Or enable in your application code:
cd backend && uv run python -c "
from app.utils.query_monitor import enable_query_monitoring, get_query_report

# Enable monitoring
enable_query_monitoring()

# Run your code...
# Then get report
report = get_query_report()
print(f\"Total queries: {report['total_queries']}\")
print(f\"N+1 detected: {report['has_potential_n_plus_1']}\")
"
```

**Enable query logging during development:**

```bash
# Add to backend/.env for development
SQLALCHEMY_ECHO=true

# Or enable programmatically:
cd backend && uv run python -c "
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
"
```

**Common N+1 patterns and fixes:**

| ❌ N+1 Pattern | ✅ Fixed with eager loading |
|----------------|----------------------------|
| `for user in users:` <br> `  user.conversations` | `users = await session.execute(` <br> `  select(User).options(selectinload(User.conversations))` <br> `)` |
| `for conv in conversations:` <br> `  conv.messages` | `conversations = await session.execute(` <br> `  select(Conversation).options(selectinload(Conversation.messages))` <br> `)` |

**Check for N+1 in API endpoints:**

```bash
# Monitor queries during API call
cd backend && uv run python -c "
import asyncio
import httpx
from app.utils.query_monitor import QueryMonitor, monitor

async def test_endpoint():
    monitor.reset()

    async with httpx.AsyncClient() as client:
        response = await client.get('http://localhost:8000/api/users')

    print(f'Total queries executed: {len(monitor.queries)}')
    print(f'Unique query patterns: {len(monitor.query_counts)}')

    # If unique patterns << total queries, likely N+1
    if len(monitor.queries) > len(monitor.query_counts) * 3:
        print('⚠️  N+1 PATTERN DETECTED!')

asyncio.run(test_endpoint())
"
```

**Prevention strategies:**
1. Use `selectinload()` for relationships
2. Use `joinedload()` for many-to-one relationships
3. Add `lazy='select'` or `lazy='joined'` to relationships
4. Monitor query counts in tests
5. Use database query logging in development

## When to Use This Agent

- Setting up PostgreSQL for the first time
- Troubleshooting database connection issues
- Running migrations
- **Auto-generating migrations after model changes**
- **Validating queries before executing in production**
- **Detecting schema drift between code and database**
- **Debugging N+1 query problems**
- Performance optimization
- Backup and restore operations
- User and permission management

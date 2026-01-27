---
description: Manage PostgreSQL database - install, start, stop, and configure
user-invocable: true
---

# /postgres Command

Manage PostgreSQL database for the chat system.

## Usage

```
/postgres [action]
```

### Actions

| Action | Description |
|--------|-------------|
| `start` | Start PostgreSQL server (default) |
| `stop` | Stop PostgreSQL server |
| `status` | Check if PostgreSQL is running |
| `install` | Install PostgreSQL via Docker |
| `setup` | Create database and user |
| `migrate` | Run database migrations |
| `shell` | Open psql shell |
| `logs` | View PostgreSQL logs |

## Examples

```bash
# Install and start PostgreSQL
/postgres install
/postgres start

# Check status
/postgres status

# Setup database
/postgres setup

# Open shell
/postgres shell
```

## Docker Installation (Recommended)

The install command uses Docker for easy setup:

```bash
# Pull and run PostgreSQL container
docker run -d \
  --name geo-postgres \
  -e POSTGRES_USER=geo_user \
  -e POSTGRES_PASSWORD=geo_password \
  -e POSTGRES_DB=geo_chat \
  -p 5432:5432 \
  -v geo_postgres_data:/var/lib/postgresql/data \
  postgres:16-alpine
```

## Environment Configuration

Add to `backend/.env`:

```bash
DATABASE_URL=postgresql+asyncpg://geo_user:geo_password@localhost:5432/geo_chat
```

## Commands Executed

### /postgres install
```bash
# Check if Docker is available
docker --version

# Pull PostgreSQL image
docker pull postgres:16-alpine

# Create and start container
docker run -d \
  --name geo-postgres \
  -e POSTGRES_USER=geo_user \
  -e POSTGRES_PASSWORD=geo_password \
  -e POSTGRES_DB=geo_chat \
  -p 5432:5432 \
  -v geo_postgres_data:/var/lib/postgresql/data \
  postgres:16-alpine

# Wait for PostgreSQL to be ready
docker exec geo-postgres pg_isready -U geo_user -d geo_chat
```

### /postgres start
```bash
docker start geo-postgres
```

### /postgres stop
```bash
docker stop geo-postgres
```

### /postgres status
```bash
docker ps --filter name=geo-postgres --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker exec geo-postgres pg_isready -U geo_user -d geo_chat
```

### /postgres setup
```bash
# Create tables (run from backend)
cd backend && uv run python -c "
import asyncio
from app.config.database import init_db
asyncio.run(init_db())
print('Database tables created successfully')
"
```

### /postgres migrate
```bash
cd backend && uv run alembic upgrade head
```

### /postgres shell
```bash
docker exec -it geo-postgres psql -U geo_user -d geo_chat
```

### /postgres logs
```bash
docker logs geo-postgres --tail 100 -f
```

## Troubleshooting

**Container won't start:**
```bash
# Check if port 5432 is in use
lsof -i :5432

# Remove existing container and recreate
docker rm -f geo-postgres
/postgres install
```

**Connection refused:**
```bash
# Verify container is running
docker ps | grep geo-postgres

# Check PostgreSQL is ready
docker exec geo-postgres pg_isready
```

**Permission denied:**
```bash
# Reset volume permissions
docker volume rm geo_postgres_data
/postgres install
```

**Can't connect from app:**
```bash
# Verify DATABASE_URL in .env
cat backend/.env | grep DATABASE_URL

# Test connection
docker exec geo-postgres psql -U geo_user -d geo_chat -c "SELECT 1"
```

## Native Installation (Alternative)

If you prefer native installation over Docker:

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo -u postgres createuser --interactive
sudo -u postgres createdb geo_chat
```

### macOS (Homebrew)
```bash
brew install postgresql@16
brew services start postgresql@16
createdb geo_chat
```

### Windows
Download from https://www.postgresql.org/download/windows/

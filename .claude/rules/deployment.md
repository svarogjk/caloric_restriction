# Deployment

## Infrastructure

| Property | Value |
|----------|-------|
| Host | Hetzner Cloud |
| Instance (Phase 1) | CX32 — 4 vCPU AMD, 8 GB RAM, 80 GB NVMe (~$10/mo) |
| Instance (Phase 2, post-publication) | CX42 — 8 vCPU AMD, 16 GB RAM, 160 GB NVMe (~$22/mo) |
| OS | Ubuntu 24.04 |
| Domain | geosurv.io (register at Cloudflare, point A record to server IP) |
| TLS | Automatic via Caddy + Let's Encrypt |
| Stack | Docker Compose: `app` (FastAPI) + `caddy` (reverse proxy) |

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Defines app + caddy services, named volumes |
| `Caddyfile` | Reverse proxy config; `flush_interval -1` enables SSE streaming |
| `.github/workflows/deploy.yml` | CI/CD: build image → push to GHCR → SSH deploy |
| `Dockerfile` | Multi-stage build (Node 22 → Python 3.13); already production-ready |

## Persistent Volumes

| Volume | Container path | Purpose |
|--------|---------------|---------|
| `app_data` | `/app/data` | SQLite database (`geo_chat.db`) + FAISS RAG index |
| `app_datasets` | `/app/datasets` | Cached GEO expression matrices (parquet) — grows to 50-100 GB |
| `app_platform_mappings` | `/app/platform_mappings` | Probe→gene symbol mappings (parquet) |
| `app_logs` | `/app/geo_logs` | Structured application logs |

**Never delete these volumes** — dataset re-download takes hours.

## Server Setup (one-time)

```bash
# On fresh Hetzner CX32 (Ubuntu 24.04)
apt update && apt install -y docker.io docker-compose-plugin curl
systemctl enable --now docker

mkdir -p /opt/geo-survival
cd /opt/geo-survival

# Copy docker-compose.yml and Caddyfile from repo
# Create .env with secrets (see below)

docker compose up -d
```

## Environment Variables (server `/opt/geo-survival/.env`)

```
MISTRAL_KEY=...
ANTHROPIC_KEY=...
JWT_SECRET_KEY=<random 64 chars: openssl rand -hex 32>
EMAIL=svarogjk1989@gmail.com
```

`DATABASE_URL` is set automatically in `docker-compose.yml` to point at the `app_data` volume.

## GitHub Secrets Required

| Secret | Value |
|--------|-------|
| `HETZNER_HOST` | Server IP address |
| `HETZNER_SSH_KEY` | Private SSH key (matching key added to server) |
| `GITHUB_TOKEN` | Auto-provided by Actions (for GHCR push) |

## Deploy a New Version

Push to `development` branch — GitHub Actions builds the image, pushes to GHCR, and SSHes into the server to pull + restart.

Manual deploy:
```bash
cd /opt/geo-survival
docker compose pull && docker compose up -d
```

## Scaling

- **Resize to CX42**: Hetzner console → resize (takes ~2 min, no data loss)
- **More disk**: Attach a Hetzner Volume (~$5/100 GB/mo), mount at `/app/datasets`
- **PostgreSQL**: Set `DATABASE_URL=postgresql+asyncpg://...` and add a `postgres` service to `docker-compose.yml`

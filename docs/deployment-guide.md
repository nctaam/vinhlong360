# Deployment Guide — vinhlong360
> STATUS (2026-07-10): active — hướng dẫn deploy tham chiếu.


Production deployment to VPS using the tarball flow (proven since 2026-06-18).

## Architecture

```
Internet → Nginx (443/SSL) → Nuxt SSR (:3000)
                            → FastAPI (:8360)  → PostgreSQL
                            → Bot gateway (:8361)
```

- **VPS:** Vultr 1GB Ubuntu 22.04+, `/opt/vinhlong360`
- **Services:** `vl-agent` (FastAPI backend), `vl-nuxt` (Nuxt SSR frontend)
- **Database:** PostgreSQL 16 (Docker container `vl360-postgres`)
- **Reverse proxy:** Nginx with Let's Encrypt SSL

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| VPS with Ubuntu 22.04+ | 1GB RAM minimum; 2GB recommended for build |
| Domain + A record | `vinhlong360.vn` → VPS IP |
| SSH key-based auth | Key: `~/.ssh/vinhlong_vps` |
| Python 3.12+ venv on VPS | `/opt/vinhlong360/venv` |
| Node.js 18+ on VPS | For `npm install` of Nuxt server deps |
| Docker (for PostgreSQL) | `docker compose up -d postgres` |
| Local dev machine | Windows (Git Bash) or Linux for building |

## Initial VPS Setup (One-time)

```bash
# On VPS as root
mkdir -p /opt/vinhlong360/{backups,ssl}
cd /opt/vinhlong360

# Python virtualenv
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# PostgreSQL via Docker
docker compose up -d postgres
# Wait for healthy, then init schema:
docker exec -i vl360-postgres psql -U vl360 vinhlong360 < init.sql

# .env (NEVER edit carelessly — parse error crash-loops vl-agent)
cp .env.example .env
# Set real values: LLM_API_KEY, ADMIN_API_KEY, DATABASE_URL, CORS_ORIGINS, etc.

# systemd services
cat > /etc/systemd/system/vl-agent.service << 'UNIT'
[Unit]
Description=VinhLong360 Backend (FastAPI)
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/vinhlong360
EnvironmentFile=/opt/vinhlong360/.env
ExecStart=/opt/vinhlong360/venv/bin/python agent/server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

cat > /etc/systemd/system/vl-nuxt.service << 'UNIT'
[Unit]
Description=VinhLong360 Frontend (Nuxt SSR)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/vinhlong360/web-nuxt
ExecStart=/usr/bin/node .output/server/index.mjs
Environment=NUXT_API_BASE=http://127.0.0.1:8360
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable vl-agent vl-nuxt
```

## SSL Setup (One-time)

```bash
apt install -y certbot
certbot certonly --standalone -d vinhlong360.vn -d www.vinhlong360.vn \
  --email contact@vinhlong360.vn --agree-tos --non-interactive

# Link certs for Nginx
ln -sf /etc/letsencrypt/live/vinhlong360.vn/fullchain.pem /opt/vinhlong360/ssl/fullchain.pem
ln -sf /etc/letsencrypt/live/vinhlong360.vn/privkey.pem /opt/vinhlong360/ssl/privkey.pem

# Render host loopback upstreams for the systemd topology. Keep the staging file
# beside the live site so mv replaces it atomically on the same filesystem.
python3 scripts/ops/render_nginx_config.py \
  --topology systemd \
  --input nginx-ssl.conf \
  --output /etc/nginx/sites-available/.vinhlong360.systemd.rendered
chmod 0644 /etc/nginx/sites-available/.vinhlong360.systemd.rendered
mv -f /etc/nginx/sites-available/.vinhlong360.systemd.rendered /etc/nginx/sites-available/vinhlong360
ln -sf /etc/nginx/sites-available/vinhlong360 /etc/nginx/sites-enabled/
# Validate the rendered systemd config before reloading Nginx.
nginx -t && systemctl reload nginx

# Auto-renewal hook
cat > /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh << 'HOOK'
#!/bin/bash
systemctl reload nginx
HOOK
chmod +x /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh
```

## Regular Deployment (scripts/deploy.sh)

The deploy script installs one verified closed-release archive. Database migration is a separate prerequisite and is never run implicitly by the closed deploy.

### Migration prerequisite

Only run this workflow after the owner explicitly authorizes the production migration. Create a PostgreSQL backup first; the closed deploy does not create one automatically:

```bash
cd /opt/vinhlong360
python scripts/backup_data.py \
  --target pg \
  --database-url-env DATABASE_URL \
  --out-dir /var/lib/vinhlong360/backups \
  --label before-migration

# Run the owner-authorized migration command separately.
python scripts/apply_migrations.py --migrations agent/migrations

# Optional local gate check: DATABASE_URL is read from the environment only.
python scripts/check_migration_gate.py \
  --migrations agent/migrations \
  --db-check
```

Do not source `.env` in a deploy command or put a DSN in process arguments. `scripts/deploy.sh` admits the verified archive, materializes its checker and canonical migration set from the archive bytes, pins the external environment authority as a 0600 snapshot, and runs the exact read-only DB gate before traffic closes and again immediately before installation. Both checks use the existing release venv at `$REMOTE/venv/bin/python` by default, require `psycopg2`, and bind the resolved interpreter digest across the traffic-close boundary; `VL360_DEPLOY_MIGRATION_GATE_PYTHON` may select another reviewed absolute interpreter path. If production is behind or any pinned authority/evidence does not match, deploy stops before release mutation; it never applies migrations itself.

### Common commands

```bash
# From repo root (Git Bash on Windows):

# Full closed-release deploy (frontend + backend; no data mutation)
scripts/deploy.sh --all

# Frontend only (after CSS/template changes)
scripts/deploy.sh --frontend

# Backend only (after Python code changes)
scripts/deploy.sh --backend

# Skip build (if .output is already fresh)
scripts/deploy.sh --frontend --skip-build
```

### What the script does

1. **Build and audit:** build Nuxt, audit Compose, and create the source-bound combined archive plus SHA-256 sidecar.
2. **Admit and verify:** upload the archive and sidecar; a trusted bootstrap snapshots them from one descriptor, verifies the sidecar, and extracts only archive-bound verifier/installer helpers.
3. **Migration prerequisite gate:** materialize the checker and canonical migrations from the admitted archive, pin the external environment authority, and compare the exact read-only `public.schema_version` tuple before traffic mutation and again after traffic closes.
4. **Close traffic:** enable maintenance and prove the closed public/operator boundary.
5. **Install atomically:** invoke `install_closed_release.sh` with the external environment/runtime/mount authorities.
6. **Restart and verify:** restart systemd services, verify Nuxt-to-agent proxy readiness, then reopen traffic.

### Rollback

Keep a known-good code archive and PostgreSQL backup before a production change. The closed deploy does not create either backup automatically:

```bash
# On VPS:
cd /opt/vinhlong360

# Restore code
tar -xzf backups/pre-deploy-YYYYMMDD-HHMMSS.tar.gz

# Restore database from an owner-selected custom dump. Use libpq environment
# (PGHOST/PGPORT/PGUSER/PGDATABASE/PGPASSWORD or a service file), never a DSN argument.
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname vinhlong360 backups/db-pre-deploy-YYYYMMDD-HHMMSS.dump

# Restart
systemctl restart vl-agent vl-nuxt
```

### Restore drill

Run this after major deploys or at least monthly. It does not touch the live
database: it creates a temporary database, restores the latest `.dump`, runs the
migration gate, checks core row counts, then drops the temporary database.

```bash
cd /opt/vinhlong360
set -a; . ./.env; set +a
./venv/bin/python scripts/restore_drill.py --backup-dir backups
```

Keep the temporary restored database only when investigating an incident:

```bash
./venv/bin/python scripts/restore_drill.py --backup-dir backups --keep-db
```

## Hard-Won Gotchas

These have caused real incidents and are encoded in the deploy script:

1. **Nuxt .output path:** Live path is `web-nuxt/.output`, NOT the stale top-level `.output`
2. **rm -rf before extract:** Must delete `.output` before tar extraction — symlinks cause "File exists" errors
3. **npm install on server:** `.output/server` needs `npm install --omit=dev` for Linux-native dependencies (built on Windows)
4. **data --replace guard:** Requires `ALLOW_DESTRUCTIVE_DB_REPLACE=1` env var + service restart to reload RAM cache
5. **pg_dump path:** Use `/tmp` as intermediate (peer-auth postgres user can't write to root-owned paths)
6. **NEVER edit prod .env carelessly:** A parse error crash-loops `vl-agent` (server.py hard-reads env vars at startup)
7. **PG_USE_POOL=false during replace:** Connection pool hangs during destructive replace at startup
8. **Build OOM:** Nuxt build with maplibre needs `--max-old-space-size=4096`; don't go higher (starves esbuild)

## Health Checks

```bash
# Backend health (should return {"status": "ok", ...})
curl -s http://localhost:8360/health | jq .

# Deep health (checks LLM connectivity)
curl -s http://localhost:8360/health/deep | jq .

# Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/

# Service status
systemctl status vl-agent vl-nuxt

# Recent errors
journalctl -u vl-agent --since "10 min ago" -p err --no-pager
journalctl -u vl-nuxt --since "10 min ago" -p err --no-pager
```

## Environment Variables (Production)

See `.env.example` for the full list. Critical ones:

| Variable | Required | Notes |
|----------|----------|-------|
| `ENVIRONMENT` | Yes | Set to `production` |
| `LLM_API_KEY` | Yes | API key for LLM provider |
| `LLM_BASE_URL` | Yes | OpenAI-compatible endpoint |
| `ADMIN_API_KEY` | Yes | Strong random (`secrets.token_urlsafe(32)`) |
| `DATABASE_URL` | Yes | `postgresql://vl360:PASSWORD@localhost:5432/vinhlong360` |
| `CORS_ORIGINS` | Yes | `https://vinhlong360.vn,https://www.vinhlong360.vn` |
| `VL360_FORCE_SECURE_COOKIES` | Recommended behind VPS proxy | Set `true` when TLS terminates at Nginx so auth cookies are always `Secure` on `vinhlong360.vn` even if the app sees local HTTP. |
| `TELEGRAM_BOT_TOKEN` | Optional | For admin bot + digest |
| `ADMIN_TELEGRAM_IDS` | Optional | Comma-separated chat IDs for bot access |
| `SCHEDULER_ENABLED` | Recommended | `true` for background tasks |
| `SCHEDULER_ENABLE_AUTONOMOUS_TASKS` | Default: false | Must explicitly opt-in |

## Nginx Routing Summary

| Path | Backend | Rate limit |
|------|---------|------------|
| `/chat`, `/events` | FastAPI (SSE) | 10r/m burst 5 |
| `/api/*` | FastAPI | 30r/m burst 20 |
| `/auth/*` | FastAPI | 30r/m burst 5 |
| `/admin-api/*` | FastAPI `/admin` | 30r/m burst 3 |
| `/health`, `/seo`, etc. | FastAPI | 30r/m burst 10 |
| `/sitemap*.xml`, `/robots.txt` | FastAPI (cached 1h) | — |
| `/webhook/*` | Bot gateway (:8361) | — |
| `/*` (everything else) | Nuxt SSR (:3000) | — |

## Backup Strategy

- **Before migration:** Run `python scripts/backup_data.py --target pg --database-url-env DATABASE_URL --out-dir /var/lib/vinhlong360/backups --label before-migration`.
- **Rotation:** The backup command retains the configured backup history; review the resulting manifest before proceeding.
- **Manual local snapshot:** `python scripts/backup_data.py` creates `scratch/backups/<timestamp>/` with data.json + manifest.
- **Database:** Use the owner-approved libpq environment/service configuration; the deploy script does not call `pg_dump`:
  ```bash
  pg_dump -Fc --dbname=vinhlong360 -f /tmp/manual-backup.dump
  ```

# Deploy Guide — vinhlong360

## Prerequisites

- VPS with Ubuntu 22.04+ (Vultr/DigitalOcean/etc.)
- Domain pointing to VPS IP (A record)
- Docker & Docker Compose installed
- SSH access with key-based auth

## 1. Initial Setup

```bash
# Clone and configure
git clone <repo-url> /opt/vinhlong360
cd /opt/vinhlong360
cp .env.example .env
# Edit .env with production values (LLM_API_KEY, ADMIN_API_KEY, etc.)
nano .env
```

## 2. SSL with Let's Encrypt

```bash
# Install certbot
apt update && apt install -y certbot

# Get certificate (standalone mode, before starting nginx)
certbot certonly --standalone -d vinhlong360.vn -d www.vinhlong360.vn \
  --email contact@vinhlong360.vn --agree-tos --non-interactive

# Certificates are at:
#   /etc/letsencrypt/live/vinhlong360.vn/fullchain.pem
#   /etc/letsencrypt/live/vinhlong360.vn/privkey.pem

# Generate DH params (one-time, takes a few minutes)
openssl dhparam -out /etc/letsencrypt/dhparam.pem 2048
```

## 3. Build & Start

```bash
cd /opt/vinhlong360

# Build frontend
cd web-nuxt && npm ci && npm run build && cd ..

# Start with production overlay
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or without Docker:
# Backend
ENVIRONMENT=production python agent/server.py &

# Frontend (Nuxt production)
cd web-nuxt && node .output/server/index.mjs &
```

## 4. Nginx Configuration

Copy `nginx-ssl.conf` and update domain/paths:

```bash
cp nginx-ssl.conf /etc/nginx/sites-available/vinhlong360
ln -s /etc/nginx/sites-available/vinhlong360 /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

Key settings in `nginx-ssl.conf`:
- SSL termination on port 443
- HTTP-to-HTTPS redirect on port 80
- ACME challenge passthrough for certbot renewal
- Modern TLS 1.2/1.3 ciphers
- HSTS, OCSP stapling, CSP headers

## 5. Auto-Renew SSL

```bash
# Certbot auto-renewal (reload nginx after renewal)
cat > /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh << 'EOF'
#!/bin/bash
systemctl reload nginx
EOF
chmod +x /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh

# Test renewal
certbot renew --dry-run
```

Certbot creates a systemd timer that runs twice daily. No cron needed.

## 6. Health Checks

```bash
# Backend health
curl -s http://localhost:8360/health | jq .

# Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/

# SSL grade
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=vinhlong360.vn
```

## 7. Monitoring

See `docs/monitoring-setup.md` for UptimeRobot + Telegram alert setup.

## 8. Updates

```bash
cd /opt/vinhlong360
git pull origin main

# Rebuild frontend if changed
cd web-nuxt && npm ci && npm run build && cd ..

# Restart services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Or without Docker:
systemctl restart vinhlong360-backend
systemctl restart vinhlong360-frontend
```

## 9. Backup

```bash
# Manual backup
python scripts/backup_data.py

# Backups stored in scratch/backups/ with timestamp
```

## Environment Variables (required for production)

| Variable | Description |
|----------|------------|
| `ENVIRONMENT` | `production` |
| `LLM_API_KEY` | API key for LLM provider |
| `LLM_BASE_URL` | LLM API endpoint |
| `ADMIN_API_KEY` | Admin dashboard access key |
| `CORS_ORIGINS` | `https://vinhlong360.vn,https://www.vinhlong360.vn` |

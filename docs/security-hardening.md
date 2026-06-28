# Security Hardening Guide — vinhlong360

> Date: 2026-06-27 | Status: Draft — implements Phase 0 of upgrade-plan.md
> Audience: Solo dev / future contributors

---

## 1. Current Security Posture

The platform already ships several strong security features. These should be preserved and built upon.

### What's already in place

| Feature | Implementation | Status |
|---------|---------------|--------|
| Prompt injection detection | 30+ regex patterns (Vietnamese + English) in guardrails module | Production-ready (dormant, flag `HAS_GUARDRAILS`) |
| PII masking | Strips phone numbers, email, CCCD, bank accounts from LLM context | Production-ready (dormant, flag `HAS_GUARDRAILS`) |
| OTP rate limiting | Multi-layer: per-phone, per-IP, global per-minute cap | Active |
| CSRF tokens | Server-side token validation on auth endpoints | Active |
| Server-side sessions | Session store with max concurrent sessions per user (`MAX_SESSIONS_PER_USER`) | Active |
| Account lockout | Exponential backoff after failed OTP attempts (`LOCKOUT_THRESHOLD`, `LOCKOUT_DURATION`) | Active |
| Destructive ops lock | `DESTRUCTIVE_OPS_LOCKED=1` prevents data-destructive admin operations | Active |
| Secret scanning | TruffleHog in CI pipeline | Active |
| Memory encryption | Fernet encryption for cold memory (user profiles) at rest | Active |
| Showcase-only commerce | No payment processing on-site — eliminates PCI-DSS scope | By design |

---

## 2. Critical Fixes Required (agent/ session scope)

These require code changes in `agent/` and are tracked in Phase 0.1 of upgrade-plan.md.

### 2.1 Session fixation — CRITICAL

**Problem:** If the server accepts a session ID provided by the client without regeneration, an attacker can fixate a victim's session.

**Fix (agent/server.py):**
- Enforce server-side session ID generation (UUID4) on every new session
- Reject any client-provided session ID — always overwrite with a fresh server-generated value
- Regenerate session ID after successful OTP authentication (session upgrade)

**Verification:**
```bash
# Attempt to set own session ID — server must ignore and generate a new one
curl -v -b "session_id=attacker-chosen-id" https://vinhlong360.vn/health
# Response Set-Cookie header must contain a NEW server-generated UUID
```

### 2.2 CORS fail-closed — HIGH

**Problem:** If `CORS_ORIGINS` env var is empty or unset, the fallback behavior must be deny-all, not allow-all.

**Fix (agent/server.py):**
```python
# BAD: if not origins: origins = ["*"]
# GOOD: if not origins: origins = []  # deny all cross-origin requests
```

**Verification:**
```bash
# With CORS_ORIGINS="" — response must NOT have Access-Control-Allow-Origin: *
curl -v -H "Origin: https://evil.com" https://vinhlong360.vn/api/v1/entities
```

### 2.3 HTTPS enforcement — HIGH

**Fix (agent/server.py):**
- Add HSTS middleware: `Strict-Transport-Security: max-age=63072000; includeSubDomains`
- Set `Secure` flag on all session cookies
- Set `SameSite=Lax` on cookies (prevents CSRF on cross-origin GET)

### 2.4 Password login rate limiting — MEDIUM

**Problem:** Current rate limiting is per-IP. Attackers behind shared IPs (VPNs, ISPs) can still brute-force specific phone numbers.

**Fix:**
- Add per-phone exponential backoff in addition to per-IP limiting
- After 5 failed attempts on same phone: 15-minute lockout
- After 10 failed attempts: 1-hour lockout + Telegram alert to admin

---

## 3. Infrastructure Fixes (DevOps scope)

These require changes to nginx, Cloudflare, or VPS config. Tracked in Phase 0.2.

### 3.1 Content Security Policy (CSP) — replace unsafe-inline

**Current:** `style-src 'unsafe-inline'` allows XSS via injected style attributes.

**Fix (nginx.conf):**
```nginx
# Generate nonce per request
set $csp_nonce $request_id;

add_header Content-Security-Policy "
  default-src 'self';
  script-src 'self' 'nonce-$csp_nonce';
  style-src 'self' 'nonce-$csp_nonce';
  img-src 'self' data: https://*.bfcplatform.vn;
  font-src 'self';
  connect-src 'self' https://api.vinhlong360.vn wss://vinhlong360.vn;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
";
```

**Nuxt integration:** Pass the nonce to Nuxt via `x-csp-nonce` header. Nuxt injects it into `<script>` and `<style>` tags via `useHead()`.

### 3.2 Admin endpoint IP whitelist — HIGH

**Fix (nginx.conf):**
```nginx
location /admin-api/ {
    # Allow only trusted IPs
    allow 127.0.0.1;
    allow <your-home-IP>;
    allow <VPN-IP>;
    deny all;

    proxy_pass http://agent:8360;
}
```

Update the IP list when your network changes. Consider a VPN (WireGuard) for stable access.

### 3.3 WAF & DDoS protection (Cloudflare free tier)

| Step | Action | Cost |
|------|--------|------|
| 1 | Sign up at cloudflare.com, add domain | Free |
| 2 | Change nameservers at registrar to Cloudflare | Free |
| 3 | Enable "Proxied" (orange cloud) on DNS A record | Free |
| 4 | SSL/TLS → Full (Strict) + Always Use HTTPS | Free |
| 5 | Security → WAF → Managed Rules → ON | Free |
| 6 | Security → Bots → Bot Fight Mode → ON | Free |
| 7 | Security → Rate Limiting → add rule: >100 req/10s from same IP → Block 10 min | Free (1 rule) |

**Important:** After enabling Cloudflare proxy, nginx sees Cloudflare IPs, not client IPs. Fix:
```nginx
# /etc/nginx/conf.d/cloudflare.conf
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 103.21.244.0/22;
# ... (full list at https://www.cloudflare.com/ips-v4/)
real_ip_header CF-Connecting-IP;
```

### 3.4 SSH hardening

```bash
# /etc/ssh/sshd_config
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
MaxAuthTries 3
AllowUsers deploy

# Install fail2ban
apt install fail2ban
systemctl enable fail2ban
```

Default fail2ban config bans IPs after 5 failed SSH attempts for 10 minutes.

---

## 4. Secret Management

### Current state

| Secret | Location | Rotation |
|--------|----------|----------|
| ADMIN_API_KEY | .env on VPS | Never rotated |
| LLM_API_KEY | .env on VPS | Never rotated |
| POSTGRES_PASSWORD | .env on VPS | Never rotated |
| MEMORY_ENCRYPTION_KEY | Auto-generated, stored on disk | Never rotated |
| CSRF_SECRET | Auto-generated at startup | Per restart |
| ESMS_API_KEY/SECRET | .env on VPS | Never rotated |
| S3 credentials | .env on VPS | Never rotated |

### Target: quarterly rotation

1. Generate new key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Update `.env` on VPS
3. Restart affected service: `sudo systemctl restart vl360-agent`
4. Verify `/health` returns 200
5. Invalidate old key (provider dashboard)

**Rotation schedule:**
- ADMIN_API_KEY: every 90 days
- LLM_API_KEY: every 90 days
- POSTGRES_PASSWORD: every 180 days (coordinate with pg_hba.conf)
- S3 credentials: every 180 days

### Long-term (when budget allows)

- HashiCorp Vault (self-hosted, free) or Doppler (free tier: 3 projects)
- Secrets injected at runtime via environment, not stored in files
- Audit trail for secret access

---

## 5. Audit Logging

### Current state

- `admin_audit.jsonl` records admin actions (entity CRUD, data quality operations)
- File-based, not tamper-evident
- No per-user data export capability

### Target improvements

#### 5.1 Tamper-evident logs (HMAC chain)

Each log entry gets an HMAC signature chained to the previous entry:

```json
{
  "timestamp": "2026-06-27T10:00:00Z",
  "action": "entity.update",
  "actor": "admin",
  "entity_id": 42,
  "changes": {"summary": ["old", "new"]},
  "hmac": "sha256:abc123...",
  "prev_hmac": "sha256:def456..."
}
```

Verification: replay the chain, recompute each HMAC, compare. Any tampered entry breaks the chain.

#### 5.2 GDPR readiness — per-user data export

- Endpoint: `GET /admin-api/users/{user_id}/export` → JSON bundle
- Includes: profile, posts, comments, reviews, session metadata
- Excludes: internal scores, moderation flags
- Response time target: <30 seconds for any user

#### 5.3 Log retention

- Keep audit logs for 2 years (legal compliance)
- Compress logs older than 90 days
- Off-site backup of audit logs (same R2 bucket as DB backups)

---

## 6. Security Checklist

### Phase 0 — Before public launch

- [ ] Session fixation fix (server-side ID generation)
- [ ] CORS fail-closed (deny all when CORS_ORIGINS empty)
- [ ] HSTS middleware + Secure cookie flag
- [ ] Admin endpoint IP whitelist in nginx
- [ ] CSP nonce-based (replace unsafe-inline)
- [ ] Cloudflare proxy enabled (DNS proxied)
- [ ] Cloudflare WAF managed rules ON
- [ ] Cloudflare bot protection ON
- [ ] SSH password auth disabled
- [ ] fail2ban installed and running
- [ ] TruffleHog CI step passing (no secrets in code)

### Phase 1 — First month of operation

- [ ] Enable `HAS_GUARDRAILS=true` (PII masking + injection detection)
- [ ] Per-phone rate limiting on OTP endpoints
- [ ] HMAC-chained audit logging
- [ ] First secret rotation (ADMIN_API_KEY, LLM_API_KEY)
- [ ] Cloudflare rate limiting rule active

### Ongoing — Quarterly

- [ ] Rotate ADMIN_API_KEY
- [ ] Rotate LLM_API_KEY
- [ ] Review nginx access logs for anomalies
- [ ] Review admin_audit.jsonl for unauthorized actions
- [ ] Update Cloudflare IP ranges in nginx config
- [ ] Run `pip audit` / `npm audit` for dependency vulnerabilities
- [ ] Verify backup restore works (monthly test)

---

## References

- Phase 0 of `docs/upgrade-plan.md` — security & stability roadmap
- `docs/incident-runbook.md` — incident response procedures
- `.env.example` — all configurable security parameters
- Cloudflare free tier docs: https://developers.cloudflare.com/fundamentals/

# Deploy Runbook — User System Waves 2–4 + AdminCP polish (2FA shipped DARK)
> STATUS (2026-07-10): done — runbook đợt deploy User-System waves 2–4 + 2FA + dark đã hoàn tất; deploy hiện tại xem docs/HANDOFF.md.


**Status:** prepared for a LATER deploy (owner-run). Not deployed as of 2026-07-04.
**Decision:** ship the code with 2FA **disabled** (`TWO_FACTOR_ENABLED=false`, the default) — no `TOTP_ENC_KEY` needed until you choose to enable 2FA.

This runbook only covers what's NEW for this deploy. The full VPS flow + every past incident/gotcha lives in the `ref-vps-deploy` memory and `scripts/deploy.sh` header. **Read those first.**

---

## What ships in this deploy

- **Wave 2** (activity timeline, profile views, badge progress, friend feed, weekly digest) — migration **063**.
- **Wave 3** (achievements, login streak, XP bar, contribution heatmap, leaderboard filters) — migrations **064, 065**.
- **Wave 4** (TOTP 2FA, recovery codes, trusted devices, suspicious-login) — migrations **066, 067** + new deps **pyotp, qrcode**. **Ships DARK** (kill-switch off).
- **AdminCP polish** (activity-feed labels, stacked completeness bar, inline placeId, history diff, markdown-lite preview, prefs persistence) + deviation tweaks (compare_days, audit rotation OR-size, /admin/backup-status, diacritic dup-check).

New migrations to apply on prod: **063, 064, 065, 066, 067** (all additive; each already has `ALTER TABLE … OWNER TO vl360;` baked in, so the owner-permission gotcha is pre-handled). New tables: `profile_views`, `login_streak`/`last_login_date` cols, `achievements`+`user_achievements`, `user_2fa`+`user_2fa_recovery_codes`+`pending_2fa`, `trusted_devices`.

`PG_REQUIRED_SCHEMA_VERSION` stays **62** (convention — not bumped per-migration).

---

## Preconditions (MUST hold before deploying)

1. **Clean working tree.** `git status --porcelain` should be (near) empty. As of prep time there are ~137 uncommitted files from PARALLEL SESSIONS — do NOT deploy over that. Either those sessions commit/finish first, or deploy from a clean checkout of the intended commit. `deploy.sh` blocks a dirty tree unless `--allow-dirty` — do NOT use `--allow-dirty` to force-ship the current mess.
2. **`database.py` mojibake resolved** (a parallel session's issue). Confirm `agent/database.py` imports/loads cleanly.
3. **Tests:** `python -m pytest -q -p no:randomly` — the Wave test files (`test_wave2/3/4.py`, `test_admin_deviations.py`) all green; the remaining failures are the documented pre-existing baseline, not new.
4. **Deps installed on prod** happen automatically via `deploy.sh --backend` (`pip install -r requirements.txt` picks up `pyotp`/`qrcode`).
5. **`TWO_FACTOR_ENABLED` stays unset** in prod `.env` (defaults to `false`). Do NOT set `TOTP_ENC_KEY` yet — not needed while 2FA is dark.

---

## Deploy (owner runs — §4)

From repo root in Git Bash, with `VL360_DEPLOY_HOST` set (SSH key `~/.ssh/vinhlong_vps`):

```bash
# 1. Build Nuxt in the BACKGROUND first (never build inside a foreground deploy — 120s timeout footgun; see incidents)
cd web-nuxt && rm -rf .output .nuxt && npm run build && cd ..

# 2. Deploy frontend + backend + migrations, WITH auto prod backup. NO --replace (no entity-data change in these waves).
scripts/deploy.sh --frontend --backend --migrate --skip-build
```

- `--migrate` applies the additive migrations (063–067) as the app user.
- Auto-backup runs unless `--no-backup` (keep it — §B1).
- **No `--replace`** — these waves add UGC/auth tables only; they do NOT change entity data. `--replace` would be a destructive no-op + downtime.
- If the parallel sessions' `_prod_seed_post_filter`/entity work is ALSO meant to ship, review that separately — it's not part of these waves.

## Verify (do NOT trust home-page 200 alone — see D02 incident)

```bash
ssh -i ~/.ssh/vinhlong_vps root@66.42.57.202 '
  curl -s -o /dev/null -w "agent_health: %{http_code}\n" http://127.0.0.1:8360/health
  curl -s -o /dev/null -w "home: %{http_code}\n" http://127.0.0.1:3000/
  systemctl is-active vl-agent vl-nuxt
  journalctl -u vl-agent -p err --since "5 min ago" --no-pager | tail
  ./venv/bin/python -c "import sys; sys.path.insert(0,\"agent\"); import database; print(\"schema_ok\")"
'
```

- Confirm `agent_health: 200` (the migrations + new routers loaded).
- Spot-check a new endpoint returns sanely (e.g. `GET /api/community/leaderboard?period=7d`).
- Confirm 2FA is dark: `POST /auth/2fa/setup` (as a logged-in user) should return **403** ("Xác thực 2 bước chưa được kích hoạt").

## Rollback

`deploy.sh` writes `backups/pre-deploy-<TS>.tar.gz` + `db-pre-deploy-<TS>.sql`. The migrations are additive (new tables), so a code rollback + leaving the new tables in place is safe; or restore the DB dump if needed.

---

## LATER: turning 2FA ON (separate, deliberate step — §4)

Only when you're ready to offer 2FA to users:

1. **Set a dedicated `TOTP_ENC_KEY`** in prod `.env` — a stable Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`). This decouples TOTP-secret encryption from `ADMIN_API_KEY`. **Do this BEFORE any user enrolls** — otherwise a future `ADMIN_API_KEY` rotation makes all stored 2FA secrets undecryptable and locks those users out.
2. **Set `TWO_FACTOR_ENABLED=true`** in prod `.env`.
3. `systemctl restart vl-agent`.
4. Verify `POST /auth/2fa/setup` now returns a QR (not 403), enroll a test account end-to-end (setup → verify-setup → recovery codes → log out → log in with a TOTP code → trusted-device remember).

Never rotate `TOTP_ENC_KEY` after users have enrolled without a re-enrollment migration.

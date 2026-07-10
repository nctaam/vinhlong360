# UGC/Auth chạy trên Postgres (quyết định GĐ3.1)
> STATUS (2026-07-10): active — quyết định kiến trúc UGC/Auth-Postgres còn hiệu lực.


## Quyết định
Tính năng **cộng đồng/UGC + xác thực** (users, OTP, posts, comments, likes, follows,
notifications, reports...) **chỉ chạy trên Postgres**, KHÔNG port sang SQLite.

SQLite chỉ phục vụ **tầng tri thức** (entity / relationship / itinerary) cho dev/CI nhanh.

## Vì sao
- **Dev/prod parity** — production dùng Postgres (`docker-compose.yml`, `init.sql`). Test UGC
  trên SQLite rồi deploy PG sẽ dính bug khác biệt phương ngữ (RETURNING, JSONB, `id::text`, FK).
- **UGC vốn quan hệ/transactional** — Postgres là công cụ đúng.
- **Solo dev**: không phải bảo trì 2 phương ngữ SQL mãi mãi.

## Hành vi
- Server chạy **SQLite** (không set `DATABASE_URL`): endpoint `/auth/*` và `/api/*` (social/community)
  trả **HTTP 503** với thông báo rõ ràng (guard `_require_pg` ở `auth.py`/`social.py`/`notifications.py`).
  Knowledge/chat (`/chat`, `/api/entities`, `/api/itineraries`...) **vẫn chạy bình thường**.
- Server chạy **Postgres** (`DATABASE_URL=postgresql://...`): UGC hoạt động đầy đủ.

## Dev cộng đồng tại máy
```powershell
# bật Postgres (compose đã provision sẵn vl360-postgres + init.sql)
docker compose up -d postgres
# trỏ backend vào PG
$env:DATABASE_URL = "postgresql://vl360:<password>@localhost:5432/vinhlong360"
python agent/database.py --import   # seed tri thức vào PG (ALLOW_DESTRUCTIVE_DB_REPLACE=1 nếu --replace)
python agent/server.py
```

## Liên quan
- `CLAUDE.md` §1.3 (quyết định kiến trúc).
- `docs/architecture-decisions.md` #3 (SQLite = dev cache, Postgres = primary).
- Test: `test_ugc_degrades_to_503_on_sqlite` (integration), `test_create_user_unavailable_on_sqlite_by_design` (xfail by design).

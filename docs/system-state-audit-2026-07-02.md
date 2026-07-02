# Audit hiện trạng hệ thống — 2026-07-02

> Audit đa-agent (7 auditor song song + kiến trúc sư trưởng tổng hợp + phản biện độ đầy đủ),
> mọi risk kèm bằng chứng `file:line` hoặc output lệnh. So với baseline audit tháng 6/2026
> (BE 5.4/10, tổng thể 5.5/10). Người phản biện đánh giá độ tin cậy: **cao**.

## Điểm tổng: 6.6/10 (tháng 6: 5.5) — code đã hồi phục, QUY TRÌNH thụt lùi

| Chiều | Điểm | Một dòng |
|---|---|---|
| Bảo mật | **8.0** | Mạnh nhất: PBKDF2-310k, session hash, admin fail-closed, SSRF/upload hardening |
| Kiến trúc frontend | **7.5** | 68 trang/48 component, render per-route chuẩn, CSS thuần token, bundle lành mạnh |
| Kiến trúc backend | **7.0** | 10 router thật, middleware kỷ luật, P0 tháng 6 đã fix kiểm chứng được; còn 4 god-module |
| CSDL | **6.5** | DAL 2 phương ngữ ổn; chuỗi migration đứt 3 chỗ, 2 bảng ngoài migration |
| Tầng dữ liệu | **6.5** | validate exit 0; NHƯNG 3 kho dữ liệu phân kỳ + 0/1730 ảnh |
| Test & sức khoẻ | **6.5** | 5.037 pass / 36 fail (baseline đỏ); FE vitest 51/51 skip = 0 phủ |
| Deploy & hạ tầng | **6.5** | 18 ngày uptime, 0 OOM, log sạch; NHƯNG backup không lịch/không offsite, không monitoring |

**Phán quyết:** codebase là điểm 7; cách vận hành 2 tuần qua là điểm 5. Quy trình suy thoái
(cây WIP ~151 file không commit từ nhiều session song song, deploy `--allow-dirty`, baseline
test đỏ được "bình thường hoá") đã gây **sự cố production thật** — xem Incident bên dưới.

## 🔴 INCIDENT (phát hiện bởi audit, ĐÃ HOTFIX + VERIFY cùng ngày)

**`/api/search` trả HTTP 500 trên prod với MỌI request** (curl xác nhận độc lập 2026-07-02).
Nguyên nhân gốc: session song song viết lại endpoint search + thêm hàm xếp hạng
`_rank_search_entities` gọi `_normalize_text` ở 3 chỗ (`public_api.py:1534,1538,1539`)
nhưng **không bao giờ định nghĩa hàm này** (HEAD cũng không có). Vì lần deploy trước dùng
`--allow-dirty`, bản lỗi này nằm trên prod (diff prod-vs-local sau khi bỏ nhiễu CRLF = 0 dòng).
Không ai phát hiện vì (a) không có uptime monitoring, (b) test bắt được lỗi này nằm lẫn trong
36 failure "drift" của baseline đỏ.

**Hotfix:** thêm `_normalize_text` uỷ quyền cho `_fold_text` sẵn có (+ `đ→d`), test trực tiếp
+ 208/209 test search pass (1 fail còn lại là test brittle cắt-source có sẵn, không phải hành vi),
ship phẫu thuật 1 file, restart `vl-agent` (health 200 sau 4s). Verify: 3 query 200, ranking
tiếng Việt không dấu đúng, journalctl err 5 phút = 0. **Hotfix nằm trong file WIP chưa commit**
— chờ đợt triage cây WIP (hành động #2).

## Bản đồ kiến trúc (như-nó-đang-là)

```
Internet → nginx (Vultr 1GB RAM + 2.4GB swap; gzip proxied JSON; /_nuxt static; TLS→2026-09)
├─ vl-nuxt  :3000  28MB  — Nuxt 4.4.8 SSR, 68 trang, SWR/prerender/spa-admin per-route,
│                          CSS thuần 9 file, apiFetch SSR qua URL public, maplibre lazy
├─ vl-agent :8360 158MB — FastAPI 79 module / 57.645 dòng / ~387 endpoint
│     10 router (admin 130, social 66, public_api 47, auth 23…) + 71 inline server.py
│     middleware: CORS→GZip→CSP-nonce→body-limit→admin-cloak→drain→timeout
│     startup: preload toàn bộ tri thức vào RAM; scheduler 15 task (6 task LLM OFF §B8)
│     ⚠ cụm agentic ~25 module/~20k dòng (orchestrator, reflexion, 3 tầng cache…)
├─ vl-bot   69MB
└─ postgresql local (36MB): TOÀN BỘ UGC + tri thức prod; SQLite chỉ dev
Deploy: tarball ssh root; LẦN CUỐI --allow-dirty → prod = cây dirty, không tái tạo từ git
```

## Bản đồ CSDL (như-nó-đang-là)

- **1 DAL 2 phương ngữ** (`database.py` 1.612 dòng, `_ph`→`%s`/`?`); PG schema_version 58.
- **Tầng tri thức** (2 engine): `entities` (19 cột; 4 cột JSONB: season/attributes/source/images;
  STI-with-registry 18 type + 11 kind trong `entity_schemas.py` — CHỦ ĐÍCH không tách bảng),
  `relationships`, `itineraries`. Index partial public-visibility + GIN unaccent/trigram.
- **Tầng UGC** (Postgres-ONLY, chặn 503 trên SQLite): ~45 bảng (users, sessions, posts,
  comments, reviews, entity_claims, notifications, saved, plans, shared_rate_limits…).
- **Drift schema:** `entity_changes` (DDL chỉ SQLite `database.py:389` nhưng admin GHI mỗi lần
  sửa entity), `site_settings_history` (CREATE runtime). Migration: init.sql WIP **không
  bootstrap được DB trắng** (index trỏ cột `posts.deleted_at` chưa có); migration 029 che 037
  (`entity_claims.reviewer_note` không bao giờ được tạo khi replay); chỉ 005 có ALTER OWNER.
- **3 kho phân kỳ:** SQLite local 1.780e/9.303r (model type CŨ) ≠ data.json 1.730e/12.208r
  (model MỚI, de-facto master — NGƯỢC quyết định DB-as-SoT) ≠ prod PG ~1.779e.

## Top rủi ro (sau dedup, kèm mức)

1. ~~**[critical] /api/search 500 toàn bộ trên prod**~~ → **ĐÃ HOTFIX + VERIFY** (xem Incident)
2. **[critical] Prod chạy code không commit** (`--allow-dirty`; md5 prod = cây dirty) — không tái tạo được từ git
3. **[high] Bootstrap DB trắng đứt 3 chỗ độc lập** (init.sql lỗi index; 029 che 037; bảng ngoài migration)
4. **[high] Backup không lịch + không offsite** — toàn bộ UGC nằm trên đúng 1 đĩa VPS
5. **[high] Lưới an toàn regression sập cả 2 stack** (BE 36 fail đỏ; FE vitest 51/51 skip) — đã bỏ lọt incident thật
6. **[high] 3 kho tri thức phân kỳ**; luồng --replace bỏ qua guard ghi (coords bbox, alias)
7. **[high] /admin/data-quality/apply crash giữa chừng** (import `scripts/normalize_data.py` ĐÃ BỊ XOÁ, sau khi đã ghi data.json) — bẫy vi phạm §B1
8. **[high] 0/1.730 entity có ảnh** — nghẽn cổ chai sản phẩm #1 (không đổi từ tháng 6)
9. **[medium] Không monitoring/alerting**; hardening prod phụ thuộc 1 biến ENVIRONMENT
10. **[medium] 3 placeholder `?` sót trong admin.py** (2 endpoint admin 500 trên PG) + `_build_messages` còn sync httpx weather trên event loop

## Top hành động đề xuất (giá trị/công, tôn trọng §2 + ngân sách)

| # | Hành động | Cỡ | Ghi chú |
|---|---|---|---|
| 1 | ~~Hotfix search~~ **XONG** + thêm `GET /api/search?q=` vào verify của deploy.sh | XS | nửa sau chưa làm |
| 2 | **Đóng băng session song song, triage cây WIP** thành commit nhỏ theo mối quan tâm (data.json backup §B1 trước), redeploy từ commit sạch, cấm `--allow-dirty` | M | **quyết định của chủ** |
| 3 | pg_dump systemd timer hằng ngày + đẩy offsite free-tier (R2/B2) + 1 lần restore drill | S | 0đ, §B8 OK |
| 4 | Sửa chuỗi migration additive: fix init.sql, migration 059 (reviewer_note + entity_changes + site_settings_history), replay-test trên PG docker trắng | S-M | |
| 5 | Xanh hoá baseline 2 stack: 10 test index-refactor, seo 404, config JWT, vitest setup-hook; viết lại ~25 test cắt-source thành test hành vi | M | |
| 6 | UptimeRobot free trên /api/health + /api/search; startup assert ENVIRONMENT+secrets | XS | 0đ |
| 7 | Fix 3 placeholder `?` admin.py:672,894,900 → `db._ph` + rule chặn trong pre_merge_check | XS | |
| 8 | data_quality.py: backup TRƯỚC khi ghi + bỏ import normalize_data.py chết | S | §B4 kèm test |
| 9 | Tái lập DB→data.json export tự động; port guard vào _bulk_load; resync SQLite local | M | |
| 10 | Chạy pipeline ảnh AI theo batch (top-traffic trước, qua flow duyệt admin sẵn có) | L | nghẽn #1 |

## So với audit tháng 6/2026

- **Backend 5.4 → 7.0.** P0 campaigns THẬT: moderation sống ở mọi đường ghi UGC
  (`social.py:395,573,827,2046,2174`), blocking-async fix hot-path (300+ `to_thread`),
  monolith → 10 router, 0 circular import (AST-verify), placeholder PG gần sạch (còn 3).
- **Bảo mật thành chiều mạnh nhất (8/10)** — truy vết trực tiếp từ các đợt remediation.
- **Thụt lùi: kỷ luật quy trình.** ~151 file WIP không commit (§B5 bỏ rơi), baseline đỏ
  (§3.4/§3.5 vi phạm), FE 0 test chạy được, deploy dirty → sự cố search là **cái giá đã trả**.

## Vùng CHƯA phủ (phản biện chỉ ra — audit sau nên bổ sung)

bot_gateway (vl-bot webhook/auth), guardrails.py + pipeline chat/LLM (prompt-injection, cost),
autonomous_budget.py (§B8 cap có được gọi đủ chỗ?), seo.py như một subsystem, notifications.py,
chuỗi storage/R2 ảnh UGC, load/concurrency test (PG pool vs max_connections trên 1GB),
CVE dependency (pip/npm audit), 9 task scheduler không-LLM (§B7), tuân thủ B6/introduce-only,
CWV/a11y đo lại thực tế.

## Đính chính của người phản biện (đã tiếp thu)

Claim "search 500 NGAY LÚC NÀY" của bản tổng hợp ban đầu là suy luận chưa có bằng chứng trực
tiếp trong audit thô → **tôi đã tự curl xác nhận độc lập trước khi hành động** (500 thật, sau
hotfix 200). Claim "prod schema_version=58" là số trong code, chưa query prod thật. Mốc "sự cố
từ 03:43" là suy từ mtime backup, không phải log.

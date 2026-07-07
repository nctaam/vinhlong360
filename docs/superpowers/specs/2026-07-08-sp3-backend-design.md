# SP3 Backend — Design (full-deep)

> **STATUS (2026-07-08): active — chủ đã chốt "full deep gồm core-80% coverage" + deploy 1 lần cuối SP3. Chờ duyệt spec.**
> Thuộc chương trình chuẩn-hoá. Grounding: workflow 5-agent đo THẬT 2026-07-08 (không dựa memory 8 ngày cũ). Backend nền đã 8.8/10 — SP3 = bật gate R20.* pending + trả nợ có kiểm soát + vá bug thật, KHÔNG đại tu.

## Grounding — số đo chốt (2026-07-08)

| Mặt | Đo được | Vào SP3? |
|---|---|---|
| R20.2 async-blocking | **0 vi phạm thật** (weather API đã `asyncio.to_thread` + test chốt); 4 cảnh báo cosmetic | Chỉ KHÓA regression (hook ruff ASYNC) + fix 4 nit |
| R20.1 ruff | **773** (default ruleset, chưa có config). 282 safe-autofix; ~491 style cố ý (`;`-chain/lazy-import); **1 F821 = bug tiềm ẩn** | CÓ — config + safe-fix + F821 + ratchet phần còn lại |
| R20.8 complexity | **250** (=baseline). 84 hàm sát ngưỡng + builder lớn (build_entity_jsonld 134, homepage_curated 80) | CÓ — tách builder tuyến tính → ~170; tránh streaming/dispatch |
| R20.4 coverage | agent/ **51.1%** source-only (FAIL sàn 60%); core: database 78.5% (thiếu 13 stmt), auth 25.6%, social 18.7%, server 21% | CÓ — trọng tâm; core-80% là phần lớn nhất |
| Bug: comment hard-delete | `delete_comment` hard-DELETE + cascade xóa reply con NGƯỜI KHÁC; comments không có `deleted_at` (lệch posts) | CÓ — P0 mất-UGC |
| Bug: error-shape | 36 chỗ `JSONResponse({error})` bypass chuẩn `_error_response({detail,request_id})` (server.py:940) | CÓ — chuẩn hóa |
| response_model | 1/406 endpoint (0.25%) | CÓ — ~15-20 endpoint trọng yếu đợt đầu |
| Dead code / TODO | 0 marker, 0 module orphan | KHÔNG có việc |

## Nguyên tắc thực thi (bất biến)
- **B3 test-trước-refactor vùng mù**: server.py chat-handler, social.py, auth.py, database.py, orchestrator — PHẢI có test bao phủ TRƯỚC khi tách hàm/sửa. Coverage-first chính là thực hiện B3.
- **B2 additive-first · B5 commit nhỏ 1 việc · B1 backup trước data-op · B4 một schema-change = một test.**
- **KHÔNG one-shot `ruff --fix` toàn repo** (đụng 127 file). Chỉ autofix nhóm 100% an toàn theo lô + test đối chiếu.
- Ratchet: nợ soft (complexity/ruff-style) chỉ được GIẢM; gate mới (ruff-safe, coverage) baseline đo lúc bật, ratchet forward.
- Deploy: gom cuối SP3, 1 lần (deploy.sh --backend --migrate cho migration comments.deleted_at + code); verify 200 toàn bộ.

## Workstreams

- **W1 · Ruff config + safe-fix + F821** (M):
  - Thêm `[tool.ruff]` vào `pyproject.toml`: pin ruleset (E/F/W + I import-sort), target-version, `per-file-ignores` cho E402 (lazy-import cố ý ở file có sys.path hack), exclude web-nuxt. Thêm `ruff` vào requirements-dev/tooling (hiện chưa có trong deps).
  - Autofix lô an toàn: F401 unused-import (167) + F541 (63) + E401 (42) — mỗi lô commit riêng, pytest đối chiếu fail-đã-biết trước/sau.
  - **Soi + sửa F821** (undefined-name — bug runtime tiềm ẩn, có test nếu là code path thật).
  - Gate mới **R20.1**: check_ruff hard-ratchet — đếm vi phạm nhóm-đã-bật; baseline = số sau safe-fix (nhóm style E402/E701/E702 để ratchet giảm dần, KHÔNG ép). Thêm vào hook.
- **W2 · Async lock** (S): fix 4 cosmetic (3 ASYNC240 → `_MODULE_DIR` module-const; 1 ASYNC110 noqa có lý do); thêm `ruff --select ASYNC` vào hook (soft). Gate **R20.2** = 0 blocking-async (baseline 0, đã đạt).
- **W3 · Complexity paydown** (M-L): tách ~15-20 hàm builder/tuyến tính (build_entity_jsonld, homepage_curated, _build_messages, _build_user_interest_profile, admin.list_entities/entity_completeness…) theo per-section/per-rule helper. Nhóm 84 hàm dải 13-15 tách 1 guard/loop. Đích **R20.8 250 → ≤170**. KHÔNG đụng chat/chat_stream/event_stream/_call_tool_impl (inherent, backlog). Mỗi hàm: nếu là vùng-mù → test-trước (B3), commit nhỏ.
- **W4 · Coverage nền + gate** (M): thêm `.coveragerc` (`omit = agent/tests/*` — con số thật 51.1% thay 70.4% ảo) + `pytest-cov` vào deps. Viết `scripts/checks/check_coverage.py` → gate **R20.4** (đọc coverage.xml/json; đo agent-total + core-4; ratchet). database.py 78.5%→80% (chỉ +13 stmt — thắng rẻ nhất). agent/ 51%→60% bằng test module 0-25% dễ (crawler 0%, freshness 12%, site_settings 14%, notifications 19%, itinerary_gen 10%, recommender 12%).
- **W5 · Core coverage 80%** (L — phần lớn nhất, nhiều batch): viết test bao phủ auth.py (25.6%→80%, +707), social.py (18.7%→80%, +1351), server.py chat-path (21%→80%, +1406). Theo B3 (test-trước). Chia batch theo module + nhóm chức năng; mỗi batch commit + đo coverage tăng. Đây cũng chính là nền an toàn cho W3/W6 refactor.
- **W6 · API-hygiene bugs** (M): (a) **comment soft-delete** — migration thêm `deleted_at TIMESTAMPTZ` vào comments + index, đổi `delete_comment` sang UPDATE (bỏ cascade hard-xóa reply con), lọc `deleted_at IS NULL` mọi query list-comment (B1 backup + B4 test). (b) **error-shape**: ép 36 chỗ `JSONResponse({error})` (public_api 19 + server 17) dùng chung `_error_response` → `{detail, request_id}`; gate/test chặn tái diễn. (c) **response_model**: ~15-20 endpoint public_api trọng yếu thêm Pydantic response schema (đợt đầu; ratchet coverage không tụt).
- **W7 · Kết đợt + deploy** (M): pytest full (fail-đã-biết không tăng) + scorecard (backend-dim TĂNG, không dim tụt) + plan-result + merge main + **deploy 1 lần** (`deploy.sh --backend --migrate` cho migration + code; verify home/agent/ready/search/public-api = 200; migration comments.deleted_at áp tay theo runbook + `ALTER TABLE ... OWNER TO vl360`).

## DoD (số cứng)

| # | Tiêu chí | Đích |
|---|---|---|
| 1 | R20.1 ruff nhóm-đã-bật | 0 (safe-fix + F821 sạch); style-debt ratchet giảm |
| 2 | R20.2 async | gate bật, 0 blocking-async, hook khóa |
| 3 | R20.8 complexity | **≤170** (từ 250) |
| 4 | R20.4 agent/ coverage | **≥60%** + database ≥80% |
| 5 | R20.4 core (auth/social/server-chat) | **≥80%** mỗi module |
| 6 | comment soft-delete | migration + soft-delete + 0 cascade hard-xóa; B4 test |
| 7 | error-shape | 0 chỗ `JSONResponse({error})` bypass; mọi lỗi `{detail,request_id}` |
| 8 | response_model | ≥15 endpoint trọng yếu có schema |
| 9 | Hệ thống | pytest fail-đã-biết không tăng; scorecard backend-dim tăng; deploy verify 200 |

## Ngoài phạm vi SP3
Cụm streaming/dispatch complexity (chat/chat_stream/event_stream/_call_tool_impl — inherent, cần refactor lớn có test riêng) · response_model cho toàn bộ 406 endpoint (chương trình dài, chia đợt sau) · ruff style-debt E402/E701/E702 ép về 0 (giữ style `;`-chain của repo; chỉ ratchet) · API versioning /v1/ · Gunicorn/PgBouncer/Alembic (P3 infra) · scripts/validate_data.py complexity 359 (giá trị thấp).

## Điều kiện dừng
Coverage một module không lên nổi 80% sau 2 batch (code khó test/cần refactor lớn) → dừng ở mức đạt được + ghi hồ sơ, KHÔNG nhồi test rỗng assertion. Migration prod lỗi → restore pg_dump, báo chủ. Refactor làm test đang-xanh-bỗng-đỏ → DỪNG (B3), không yếu assertion.

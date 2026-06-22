# Audit findings vinhlong360 — 2026-06-22 (3 lượt quét sâu đa-agent)

Tổng verified: 110 (audit-1: 44, audit-2: 66) | crit 3, high 26, med 46, low 35

> Mỗi finding qua scan→verify đối-kháng (model sonnet). GS-02 (88 ward BT/TV → vinh-long) là DƯƠNG-TÍNH-GIẢ (sau sáp nhập đúng). Audit-3 critical .env-leak cũng GIẢ (đã verify: .env gitignore đúng).

---

## CRITICAL

- **CONC-001** [Concurrency/async] (a2) — Synchronous OpenAI SDK calls inside async SSE generator block event loop
  - file: `agent/server.py`
  - Lines 2003, 2043, 2164: inside the `async def event_stream()` generator (which runs directly on the asyncio event loop as an async generator), three separate `client.chat.completions.create(...)` calls are made synchronously — the non-streaming tool-call round (line 2003), the st
  - FIX: Wrap each synchronous LLM call inside event_stream() with `await asyncio.to_thread(client.chat.completions.create, ...)`. Alternatively switch to the async OpenAI client (`AsyncOpenAI`) for the stream

- **F1** [DB layer] (a1) — replace_from_json PG path: DELETEs committed before re-insert — non-atomic, data-loss on crash
  - file: `agent/database.py`
  - Lines 867–875: `with self._conn() as conn:` deletes all rows from relationships, itineraries, entities. For PG, the block then does `pass` (line 877–878), so the connection commits with empty tables. Line 960–961 (outside the `with` block) then calls `self.migrate_from_json(json_
  - FIX: For PG, move the DELETE + INSERT logic inside a single `with self._conn() as conn:` block so both are in one transaction that either fully commits or fully rolls back. Mirror the SQLite executemany pa

- **TC-01** [Test coverage blind-spot] (a2) — ETL scripts (scripts/*.py) — 0% test, ghi thẳng data.json không backup gate
  - file: `scripts/optimize_data.py`
  - scripts/optimize_data.py dòng 14: `data = json.load(DATA.open(...))` rồi ghi lại cuối file — không có unit test nào. Tìm kiếm toàn bộ tests/ và agent/tests/ cho 'optimize_data', 'enrich_data', 'import_crawled', 'crawler', 'auto_learn', 'import_govsite': không có file test nào. Tư
  - FIX: Ưu tiên viết test cho 5 script đã thực thi pass-2: resolve_missing_placeid.py (parser COMMUNE regex + hội tụ ward), fix_placeid_crosswalk.py (Round A/B logic), geocode_approx.py (gate 5km + street_of(

## HIGH

- **ARCH-001** [Architecture/consistency] (a1) — Province entity 'vinh-long' has wrong area='ben-tre' in both DB and data.json
  - file: `web/data.json (entity id='vinh-long') + agent/data/vinhlong360.db (entities table)`
  - DB query: SELECT id, name, area, level FROM entities WHERE level='tinh' → ('vinh-long', 'Tỉnh Vĩnh Long', 'ben-tre', 'tinh'). Same value confirmed in data.json. The single tinh-level entity represents Vĩnh Long province but carries area='ben-tre'. validate_data.py has no check fo
  - FIX: Set area='vinh-long' on the entity id='vinh-long' in both DB (UPDATE entities SET area='vinh-long' WHERE id='vinh-long') and re-export to data.json. Add a validate_data.py check: for type='place' leve

- **F1** [Backend API] (a1) — admission_fee bị mất hoàn toàn trong chat tool responses do key alias mismatch
  - file: `agent/database.py:281 + agent/server.py:428-631`
  - database.py:273-283: _ATTR_ALIASES ánh xạ 'admission_fee' → 'admission' khi ghi vào DB. Kết quả thực tế trong DB: entity 'bao-tang-ben-tre' có attributes.admission = 'Người lớn: 50.000 VNĐ...' nhưng attributes.admission_fee = None. Tuy nhiên server.py đọc attrs.get('admission_fee
  - FIX: Sửa server.py: thay attrs.get('admission_fee') bằng attrs.get('admission_fee') or attrs.get('admission') tại 5 vị trí (line 428, 467, 528, 579, 630). Hoặc bỏ alias 'admission_fee' → 'admission' khỏi _

- **CLP-01** [Chat/LLM pipeline] (a2) — memory_graph._extract_facts_llm() gọi LLM đồng bộ không có timeout, block mỗi chat turn
  - file: `agent/memory_graph.py`
  - Dòng 646: `client.chat.completions.create(model=model, messages=[...], temperature=0, max_tokens=500)` — không có `timeout=` arg. Hàm này được gọi từ `on_chat_complete()` (dòng 798: `facts = self.extract_facts(message, reply)`), và `on_chat_complete` được gọi ĐỒNG BỘ bên trong ch
  - FIX: Thêm `timeout=5` vào `client.chat.completions.create()` trong `_extract_facts_llm` (dòng 646). Cân nhắc chuyển `on_chat_complete` sang `asyncio.to_thread` hoặc đặt hẳn vào background thread để không b

- **CLP-02** [Chat/LLM pipeline] (a2) — Streaming path: json.loads(tc.function.arguments) không có try/except, crash toàn stream nếu LLM trả JSON malformed
  - file: `agent/server.py`
  - Dòng 2015 trong `event_stream()`: `fn_args = json.loads(tc.function.arguments)` không có try/except. Nếu LLM trả về tool call với `arguments` không phải JSON hợp lệ (ví dụ cắt nửa chừng do token limit), dòng này ném `json.JSONDecodeError` — thoát `for tc in msg.tool_calls` loop v
  - FIX: Bọc dòng 2015 trong try/except JSONDecodeError: nếu parse lỗi, append tool result lỗi vào messages rồi continue sang tool_call tiếp theo, tránh crash cả stream. Pattern: `try: fn_args = json.loads(tc.

- **F3** [DB layer] (a1) — round-trip loss: `description` field silently dropped by upsert_entity and replace_from_json
  - file: `agent/database.py`
  - The INSERT column list at lines 305–306 (PG) and 333–334 (SQLite) in upsert_entity does NOT include `description`. The INSERT column list in replace_from_json (lines 908–910) also omits `description`. The DB schema has a `description TEXT DEFAULT ''` column (line 186 SQLite, init
  - FIX: Add `description` to the upsert_entity INSERT column list and to the ON CONFLICT DO UPDATE SET clause (PG) with COALESCE to preserve existing non-empty descriptions: `description = CASE WHEN EXCLUDED.

- **DF-01** [Data fact-check sâu] (a2) — 4 entity trùng cho cùng 1 đền Chùa Vàm Ray
  - file: `web/data.json`
  - 4 entity cùng mô tả Chùa Vàm Ray (Trà Vinh) với nội dung mâu thuẫn nhau: chua-vam-ray-tra-vinh (placeId=xa-nhi-long, coords=[10.026,106.293]—sai vùng), chua-vam-ray (placeId=xa-tra-cu, coords=[9.655,106.274]), chua-vam-ray-wat-samrong (placeId=xa-ham-giang, coords=[9.657,106.265]
  - FIX: Giữ lại 1 entity canonical (chua-vam-ray, placeId=xa-tra-cu, coords=[9.655,106.274] gần Hàm Tân Trà Cú nhất), merge relationship từ 3 entity còn lại vào đó rồi xóa. Cần xác minh lại tuyên bố 'lớn nhất

- **DF-02** [Data fact-check sâu] (a2) — 68 entity có summary sai tỉnh, 37 entity ghi sai tỉnh trong địa chỉ
  - file: `web/data.json`
  - 68 entity có area=ben-tre hoặc area=tra-vinh nhưng summary nhắc tỉnh khác. Nghiêm trọng nhất—37 entity ghi địa chỉ rõ ràng sai tỉnh: (1) ao-ba-om-ao-vuong-tra-vinh (area=tra-vinh) summary: 'thắng cảnh nổi tiếng ở tỉnh Vĩnh Long... thuộc tỉnh Vĩnh Long'; (2) cua-hang-ocop-tinh-ben
  - FIX: Batch-replace toàn bộ 37 địa chỉ sai tỉnh trước khi release. Tìm bằng regex 'tỉnh Vĩnh Long' trong entity có area!=vinh-long và ngược lại. Vì summary được crawl từ nguồn ngoài, cần thêm bước post-proc

- **DF-04** [Data fact-check sâu] (a2) — 9 entity tọa độ sai rõ ràng—transposed digit (8 entity lon=104.0xx, 1 entity lat=8.68)
  - file: `web/data.json`
  - 8 entity có longitude=104.0xxx khi lẽ ra phải ~106.xxx (VL/BT/TV đều ở lon 105.5-107.0): khach-san-phu-gia [10.056,104.024] (address rõ: 'phường Phước Hậu, TP Vĩnh Long'), banh-xeo-oc-gao-phu-da [10.017,104.013] (Ben Tre), di-tich-lich-su-luu-cu [10.043,104.018] (Tra Cu), con-oc-
  - FIX: Cho 8 entity lon=104.0xx: cần re-geocode từ địa chỉ vì 104+2=106 chỉ là ước tính và vẫn có thể sai (ví dụ buoi-da-xanh Giồng Trôm cần lon ~106.45, không phải 106.00). Cho khu-di-tich-lang-ong-con-tau:

- **DF-05** [Data fact-check sâu] (a2) — 2 entity trùng cho cùng 1 thực thể (cu-lao-may-tra-on + cu-lao-may-tra-on-vinh-long)
  - file: `web/data.json`
  - cu-lao-may-tra-on và cu-lao-may-tra-on-vinh-long có EXACT cùng coordinates=[9.9423674, 105.9188123] và cùng placeId=xa-luc-si-thanh. Đây là bằng chứng chắc chắn entity trùng. cu-lao-may-tra-on có 19 relationship, cu-lao-may-tra-on-vinh-long chỉ có 5.
  - FIX: Giữ cu-lao-may-tra-on (nhiều relationship hơn), merge 5 relationship của cu-lao-may-tra-on-vinh-long sang entity gốc, xóa bản trùng. Tương tự cho 4 cặp near-dup khác có cùng placeId: (3) nha-gom-tu-bu

- **D02** [Deps/perf/bundle] (a2) — PostgreSQL không dùng connection pool — mỗi request tạo new psycopg2 connection
  - file: `agent/database.py:94-106`
  - Hàm `_conn()` tại line 97: `conn = psycopg2.connect(self._dsn)` — mỗi lần vào context manager là 1 TCP handshake + auth round-trip với Postgres. Với FastAPI async và nhiều concurrent request (/chat, /api/entities, /api/places, ...), mỗi request mở rồi đóng connection ngay. Postgr
  - FIX: Dùng `psycopg2.pool.ThreadedConnectionPool` hoặc `psycopg2.pool.SimpleConnectionPool` với minconn=2, maxconn=10 (phù hợp VPS 1GB). Khởi tạo pool 1 lần lúc `_conn()` đầu tiên (lazy). Với FastAPI async:

- **ETL-01** [ETL pipeline] (a1) — optimize_data.py ghi thẳng không DRY-RUN, không backup — chạy = ghi đè ngay
  - file: `scripts/optimize_data.py`
  - Line 183-185: `with DATA.open('w', encoding='utf-8') as f: json.dump(data, f, ..., indent=None, separators=(',',':'))` — không có flag `--apply`, không có `--check`, không có backup. Mọi import đều bị mất indent (minified). Thêm vào đó, line 184 dùng `indent=None, separators=(','
  - FIX: Thêm `--apply` flag (default dry-run) và gọi `backup_data.py` trước khi ghi. Sửa `indent=2` cho nhất quán. Đây là script duy nhất trong codebase không có dry-run guard.

- **ETL-02** [ETL pipeline] (a1) — optimize_data.py tạo produced_in cho orphan entity — vi phạm §1.4 (quan hệ bịa, không có bằng chứng)
  - file: `scripts/optimize_data.py`
  - Lines 144-163: logic section 7 lấy mọi entity không có relationship nào rồi tự gán `produced_in` về placeId (hoặc về `area_places[area][0]` — tức phường/xã đầu tiên theo thứ tự dict). Một homestay hay điểm ăn uống không có quan hệ nào không có nghĩa nó 'sản xuất' tại ward đó. Lin
  - FIX: Bỏ section 7 (auto-link orphans). §1.4 cấm bịa quan hệ. Orphan entity nên được xử lý bằng crosswalk có bằng chứng (như migrate_huyen_to_ward.py) chứ không phải auto-link.

- **ETL-03** [ETL pipeline] (a1) — migrate_sap_nhap.py dùng key sai (from_id/to_id) để update relationships trong data.json — bỏ lọt toàn bộ
  - file: `scripts/migrate_sap_nhap.py`
  - Lines 183-188: `if r.get('from_id') == xa_id: r['from_id'] = p_id` và `if r.get('to_id') == xa_id: r['to_id'] = p_id`. Nhưng toàn bộ data.json dùng key `from`/`to` (không phải `from_id`/`to_id`) — xác nhận tại migrate_huyen_to_ward.py line 197 và fix_audit_safe.py line 89. Hệ quả
  - FIX: Sửa lines 183-188 thành `r.get('from')` / `r.get('to')` và cập nhật `r['from']` / `r['to']` tương ứng. Kiểm tra thêm với `from_id` làm fallback nếu cần backward-compat.

- **ETL-04** [ETL pipeline] (a1) — fix_audit_safe.py tạo located_in ward→'vinh-long' cho TẤT CẢ wards (kể cả Bến Tre, Trà Vinh)
  - file: `scripts/fix_audit_safe.py`
  - Lines 78-80: `for w in wards: t = (w, 'vinh-long', 'located_in')` — vòng lặp chạy qua MỌI ward của cả 3 tỉnh và tạo `located_in` về `vinh-long`. Phường p-ben-tre, p-tra-vinh... đều sẽ bị gán `located_in vinh-long`. Đây là bug sai nghĩa hành chính nghiêm trọng: tỉnh Bến Tre/Trà Vi
  - FIX: Thay `'vinh-long'` bằng area lookup: `tgt = {'vinh-long':'vinh-long','ben-tre':'ben-tre','tra-vinh':'tra-vinh'}.get(w_entity.get('area'))` rồi chỉ tạo rel khi tgt tồn tại trong byid. Cần kiểm tra data

- **ETL-05** [ETL pipeline] (a1) — fix_data_issues.py --fix ghi thẳng vào data.json không backup
  - file: `scripts/fix_data_issues.py`
  - Lines 386-400: khi `mode == '--fix'`, script gọi `fix_broken_relationships(data)`, `fix_produced_in_area_conflicts(data)` rồi `save_data(data)` (line 399). `save_data()` (lines 28-31) ghi thẳng vào DATA_PATH. Không có bước backup, không có lệnh gọi backup_data.py, không có shutil
  - FIX: Thêm `shutil.copy2(DATA_PATH, DATA_PATH.with_suffix('.json.bak'))` hoặc gọi subprocess backup_data.py ở đầu block `--fix`. Thêm note vào docstring: 'Run backup_data.py BEFORE --fix'.

- **ETL-06** [ETL pipeline] (a1) — ingest_wikimedia_images.py (legacy/direct-publish mode) ghi data.json không backup — kể cả ghi từng 50 batch
  - file: `scripts/ingest_wikimedia_images.py`
  - Lines 275-277: ghi intermediate mỗi 50 entity: `with open(DATA_FILE, 'w', ...) as f: json.dump(data, ...)`. Lines 280-282: ghi cuối. Không có backup nào. Docstring (line 13) gọi direct-publish là 'legacy' nhưng vẫn là default khi không truyền `--mode=queue`.
  - FIX: Ở đầu run (ngoài dry-run), thêm shutil.copy2 backup trước khi ghi lần đầu. Hoặc loại bỏ direct-publish mode hoàn toàn, chỉ giữ queue mode (khuyến nghị trong docstring nhưng chưa enforce).

- **EH-01** [Error handling/resilience] (a2) — generate_followups gọi LLM không có timeout — treo thread POST /chat
  - file: `agent/server.py`
  - Dòng 319: `client.chat.completions.create(model=MODEL_MINI, messages=[...], temperature=0.7)` — không có tham số `timeout`. Hàm này được gọi đồng bộ qua `call_tool('suggest_followups', ...)` trong `_run_agent` và stream loop, cả hai đều chạy trên thread pool (`asyncio.to_thread`)
  - FIX: Thêm `timeout=LLM_TIMEOUT` vào lời gọi tại dòng 319: `client.chat.completions.create(model=MODEL_MINI, messages=[...], temperature=0.7, timeout=LLM_TIMEOUT)`.

- **EH-02** [Error handling/resilience] (a2) — json.loads(tc.function.arguments) không guard ở _run_agent và stream loop — JSONDecodeError thoát vòng lặp agent
  - file: `agent/server.py`
  - Dòng 1427 (_run_agent): `fn_args = json.loads(tc.function.arguments)` — nằm bên trong `for tc in msg.tool_calls` nhưng NGOÀI try/except. Nếu LLM trả JSON tool-arguments lỗi (cắt bởi max_tokens, stream corrupt), JSONDecodeError ném ra và được bắt bởi outer `except Exception as llm
  - FIX: Bọc cả hai site bằng try/except: `try: fn_args = json.loads(tc.function.arguments)
except (json.JSONDecodeError, ValueError): fn_args = {}` — đồng nhất với cách orchestrator.py:628-630 đã làm.

- **EH-04** [Error handling/resilience] (a2) — DDGS (DuckDuckGo) không có timeout ở tất cả call-site — một DDG chậm treo tool call
  - file: `agent/server.py`
  - Dòng 281: `with DDGS() as ddgs: results = list(ddgs.text(query, region="vn-vi", max_results=max_results))` — không có timeout. Tương tự tại `agent/auto_learn.py:225`, `agent/learn_loop.py:93`, `agent/mcp_server.py:131`. DDGS theo mặc định không có global request timeout nếu không
  - FIX: Truyền timeout qua `DDGS(timeout=10)` (constructor) hoặc gọi với `asyncio.wait_for` / `signal.alarm`. Ví dụ: `with DDGS(timeout=10) as ddgs:` — kiểm tra phiên bản ddgs đang dùng để xác nhận param đúng

- **EH-06** [Error handling/resilience] (a2) — moderation.py _moderate_images: lặp qua image_urls tuần tự không timeout riêng từng request — tích lũy latency
  - file: `agent/moderation.py`
  - Dòng 115: `async with httpx.AsyncClient(timeout=15) as client:` rồi vòng `for url in image_urls[:4]:` — mỗi Google Vision request có 15s timeout nhưng lần lượt. Tệ nhất: 4 ảnh × 15s = 60s. `moderate_content` được gọi khi user đăng bài (endpoint UGC), kéo latency response lên đến
  - FIX: Chạy các request ảnh song song với `asyncio.gather(*[_fetch_image(url) for url in image_urls[:4]], return_exceptions=True)` và đặt total timeout 15s thay vì per-request.

- **SEO-01** [FE quality/SEO] (a1) — Breadcrumb JSON-LD position-2 hard-code /du-lich cho mọi entity type
  - file: `C:\Code\vinhlong360\web-nuxt\pages\dia-diem\[id].vue`
  - Dòng 773: `item: 'https://vinhlong360.vn/du-lich'` — hard-code, bất kể entity.type là product (/san-pham), accommodation (/luu-tru), organization (/danh-ba). typeBreadcrumbUrl đã tính đúng URL (dòng 485) nhưng breadcrumb JSON-LD không dùng nó.
  - FIX: Thay dòng 773 dùng biến: `item: 'https://vinhlong360.vn' + typeBreadcrumbUrl.value`. Đảm bảo TYPE_BREADCRUMB map đủ các type. Mismatch này khiến Google Index breadcrumb sai category cho product/accomm

- **GS-02** [Graph semantic] (a2) — 88/124 ward thuộc ben-tre/tra-vinh có located_in trỏ sai vào node 'vinh-long'
  - file: `web/data.json`
  - 88 ward entity có area='ben-tre' hoặc 'tra-vinh' nhưng tất cả đều có rel located_in -> 'vinh-long'. Ví dụ: xa-quoi-dien (area=ben-tre) -> vinh-long; p-tra-vinh (area=tra-vinh) -> vinh-long; xa-tra-cu (area=tra-vinh) -> vinh-long. Không có node 'ben-tre' hay 'tra-vinh' trong entit
  - FIX: Tạo thêm 2 entity place: id='ben-tre', name='Tỉnh Bến Tre' và id='tra-vinh', name='Tỉnh Trà Vinh'. Cập nhật 88 located_in rels của ward ben-tre/tra-vinh trỏ đúng tỉnh. Backup trước (B1). Thêm vào ROAD

- **SEC-001** [Security] (a1) — OTP plaintext bị trả về trong API response khi không có ESMS_API_KEY
  - file: `C:\Code\vinhlong360\agent\auth.py`
  - Dòng 234: `"dev_code": code if not ESMS_API_KEY else None` — OTP gốc (chưa hash) được trả trong JSON response bất cứ khi nào ESMS_API_KEY rỗng. Điều này không chỉ xảy ra ở DEV: nếu production khởi động mà quên set ESMS_API_KEY (ví dụ: thiếu trong .env prod), mọi caller của POST /
  - FIX: Xoá trường dev_code khỏi response production. Nếu cần DEV mode, chỉ in ra console/log server (không bao giờ trả về HTTP response). Kiểm tra biến ESMS_API_KEY ngay khi khởi động và log cảnh báo rõ ràng

- **SEC-002** [Security] (a1) — X-Forwarded-For trong auth.py bỏ qua TRUSTED_PROXIES — IP có thể bị giả mạo
  - file: `C:\Code\vinhlong360\agent\auth.py`
  - Dòng 207-208: IP rate-limit cho OTP lấy trực tiếp `request.headers.get('x-forwarded-for', '').split(',')[0].strip()` mà KHÔNG kiểm tra xem request có đến từ trusted proxy không. Trong khi đó middleware.py:386-403 đã có hàm get_client_ip() thực hiện đúng việc này (chỉ trust XFF kh
  - FIX: Thay đoạn lấy IP ở dòng 207-208 bằng cách import và gọi `get_client_ip(request)` từ middleware.py — hàm này đã có sẵn và đúng logic. Thêm `from middleware import get_client_ip` vào auth.py và dùng nó

- **TC-02** [Test coverage blind-spot] (a2) — call_tool() dispatcher trong server.py — 15+ nhánh, chỉ 2 nhánh được test
  - file: `agent/server.py`
  - server.py:398 định nghĩa call_tool() với ít nhất 15 nhánh: search, entity_detail, seasonal_now, list_itineraries, itinerary_detail, places_in_area, stats, compare_areas, nearby_entities, suggest_followups, generate_itinerary, directory_lookup, create_itinerary, get_current_time,
  - FIX: Tạo test/test_call_tool.py với fixture mock knowledge.* — test từng nhánh call_tool() bằng cách gọi trực tiếp hàm (không qua HTTP), kiểm tra JSON output hợp lệ và các edge case như entity_id không tồn

- **TC-04** [Test coverage blind-spot] (a2) — replace_from_json trên PostgreSQL — 0% test, non-atomic (vẫn là finding từ audit-1 chưa có test cover)
  - file: `agent/database.py`
  - database.py:960: `if self._use_pg: result = self.migrate_from_json(json_path)` — nhánh PostgreSQL của replace_from_json gọi migrate_from_json() không có transaction bao bọc toàn bộ DELETE+INSERT. test_database.py:184 test_replace_from_json_with_override_roundtrip chỉ test SQLite
  - FIX: Thêm test_replace_from_json_pg_is_atomic với @pg_only: bơm 5 entity, gọi replace_from_json với data gồm 3 entity mới, mock migrate_from_json() ném exception sau khi xóa một nửa → kiểm tra DB vẫn nhất

## MEDIUM

- **ARCH-003** [Architecture/consistency] (a1) — seo.py and freshness.py read web/data.json directly instead of DB, creating a stale-data window when DB is updated without running export_data.py
  - file: `agent/seo.py:4,24 and agent/freshness.py:29,46-49`
  - seo.py line 4: 'The SEO layer reads from web/data.json because that file remains the moderated public source of truth.' freshness.py line 46: 'Load entities from web/data.json.' When an admin edits an entity via the admin panel (which writes to DB via database.py.upsert_entity),
  - FIX: After any DB upsert via admin panel, trigger export_from_db() (export_data.py) automatically, or make seo.py/freshness.py read from DB directly (via the knowledge module that already has DB-backed dat

- **F2** [Backend API] (a1) — /api/entities trả total > len(entities) khi có entity provisional — phân trang bị sai
  - file: `agent/public_api.py:102-118`
  - Tại public_api.py:102-113, total được tính từ db.count_entities_filtered() hoặc len(filtered) TRƯỚC khi áp _is_public() filter. Dòng 116 mới áp quarantine: results = [e for e in results if _is_public(e)]. Nếu dataset có N entity provisional/unverified, total = T nhưng len(entitie
  - FIX: Di chuyển _is_public filter lên trước khi tính total. Với nhánh month: lọc provisional ngay sau dòng 108 (filtered = [e for e in full if _in_month(e) and _is_public(e)]). Với nhánh q: lọc trước khi đế

- **F4** [Backend API] (a1) — Admin GET /admin/entities: total bị bound bởi limit khi dùng q — số thực tế bị che
  - file: `agent/admin.py:219-238`
  - Tại admin.py:220: khi có q, gọi db.search_entities(q=q, ..., limit=limit) — limit mặc định 50, tối đa 500. Dòng 230: total = len(results) — nhưng results đã bị cắt bởi limit từ trước. Kết quả: total luôn ≤ limit, không phản ánh số thực trong DB. Ví dụ nếu có 200 entity khớp q='ch
  - FIX: Thêm db.count_entities_filtered(entity_type=type, area=area, q=q) để lấy total thật khi có q, độc lập với limit. Xóa dòng 231 items = results[:limit] vì redundant.

- **CLP-03** [Chat/LLM pipeline] (a2) — generate_followups() gọi LLM không có timeout, chặn agent loop khi LLM chậm
  - file: `agent/server.py`
  - Dòng 319-327: `client.chat.completions.create(model=MODEL_MINI, messages=[...], temperature=0.7)` — không có `timeout=` arg. Hàm này được gọi từ `call_tool('suggest_followups', ...)` (dòng 647), nằm trong vòng lặp `_run_agent` và `event_stream`. Không có circuit breaker bao quanh
  - FIX: Thêm `timeout=LLM_TIMEOUT` (hoặc nhỏ hơn, ví dụ 10 giây) vào `client.chat.completions.create()` tại dòng 319. Hoặc dùng `safe_llm_call` để được circuit breaker bảo vệ.

- **CLP-04** [Chat/LLM pipeline] (a2) — safe_llm_call trong _run_agent thiếu timeout=LLM_TIMEOUT, dùng default 30s từ signature
  - file: `agent/server.py`
  - Dòng 1398: `safe_llm_call(client, model=MODEL, messages=messages, tools=TOOLS, tool_choice='auto')` — thiếu `timeout=LLM_TIMEOUT`. `safe_llm_call` signature tại circuit_breaker.py dòng 457 có `timeout: float = 30.0` default. Nếu admin đặt `LLM_TIMEOUT=10` để tránh treo, call này
  - FIX: Sửa dòng 1398 thành: `safe_llm_call(client, model=MODEL, messages=messages, tools=TOOLS, tool_choice='auto', timeout=LLM_TIMEOUT)`.

- **CLP-05** [Chat/LLM pipeline] (a2) — Prompt injection detector bỏ sót Vietnamese có dấu — bypass dễ dàng
  - file: `agent/guardrails.py`
  - Dòng 97-113: các pattern Vietnamese injection (`vn_bo_qua`, `vn_quen_di`, `vn_bay_gio_ban_la`, `vn_gia_vo`, `vn_che_do_moi`, `vn_hien_thi_prompt`, `vn_vuot_qua`) đều dùng từ KHÔNG DẤU (vd: `bo qua chi thi`, `quen di`, `bay gio ban la`). Nhưng `detect()` nhận `text` gốc có dấu. Ví
  - FIX: Trước khi apply Vietnamese patterns, normalize text về không dấu (NFD + strip combining chars + replace đ→d), giống như `_normalize()` trong agentic_rag.py dòng 644-647. Cách nhanh nhất: thêm `text_no

- **CLP-06** [Chat/LLM pipeline] (a2) — history dict không validate role/content — KeyError/AttributeError khi history chứa entry lạ
  - file: `agent/server.py`
  - ChatRequest dòng 924: `history: list[dict]` chỉ validate là list of dict, không kiểm tra các key `role` và `content`. `_build_messages` dòng 1250-1252 gọi `messages.extend(history[-20:])` rồi truyền thẳng cho OpenAI API. Nếu client gửi history entry thiếu `role` hoặc `content` (v
  - FIX: Thêm validator trong ChatRequest hoặc tại đầu `_build_messages`: filter `history` chỉ giữ entry có `role in {'user','assistant','system'}` và `content` là string. Ví dụ: `history = [m for m in history

- **CONC-002** [Concurrency/async] (a2) — Non-atomic triple assignment to knowledge module globals creates torn-state window during reload
  - file: `agent/knowledge.py`
  - Line 129 in `reload()`: `_entities, _relationships, _itineraries = new_e, new_r, new_i`. Python tuple-unpacking is NOT atomic under the GIL for attribute/global writes — the interpreter executes three separate STORE_NAME opcodes. A reader thread (or coroutine body resumed between
  - FIX: Replace the three-line assignment with a single atomic replacement of a container object: store all three as `_state = {'entities': new_e, 'relationships': new_r, 'itineraries': new_i}` and use a sing

- **CONC-003** [Concurrency/async] (a2) — _index_build_state dict mutated from background thread without a lock — TOCTOU race on 'running' flag
  - file: `agent/server.py`
  - Lines 742–774: `_index_build_state` is a plain module-level `dict`. The background thread's `_run()` (line 760) calls `_index_build_state.update(...)` and sets individual keys; the main thread checks `_index_build_state['running']` at line 757 without any lock. If two concurrent
  - FIX: Guard `start_search_index_build` with a threading.Lock: acquire the lock, recheck `_index_build_state['running']`, set it to True, then release before spawning the thread. This closes the TOCTOU windo

- **CONC-004** [Concurrency/async] (a2) — analytics.track_query / track_entity_hit called directly in async handlers — sync file I/O inside event loop
  - file: `agent/analytics.py`
  - Lines 65–101 in analytics.py: `track_query()` acquires `_lock` and calls `_load()` (reads ANALYTICS_FILE from disk) then `_save()` (writes the entire file), all under a threading.Lock. This function is called directly (not via `asyncio.to_thread`) from the async /chat handler at
  - FIX: Wrap `analytics.track_query` and `analytics.track_entity_hit` in `asyncio.to_thread()` at the call sites, or make analytics writes fire-and-forget via a background queue (e.g. `asyncio.get_event_loop(

- **F7** [DB layer] (a1) — create_user and update_user use PG-only syntax (RETURNING *, NOW(), id::text) with no SQLite fallback
  - file: `agent/database.py`
  - Lines 1030–1035: `INSERT INTO users ... RETURNING *` and `NOW()` are PG-specific. Lines 1051: `id::text = {ph}` and `RETURNING *` are PG-specific. The class docstring says 'PostgreSQL or SQLite fallback' and the architecture decision (CLAUDE.md §1.3) says UGC/auth is Postgres-onl
  - FIX: Add a guard at the top of get_user_by_phone, create_user, update_user, get_user_by_id: `if not self._use_pg: raise NotImplementedError('User methods require PostgreSQL; call returns 503 in API layer')

- **DF-03** [Data fact-check sâu] (a2) — 169 entity orphan (0 relationship)
  - file: `web/data.json`
  - 169 entity không xuất hiện trong bất kỳ relationship nào. Phân bố: dish=119, place=37, nature=23, product (orphan)=1, và các loại khác. Mẫu entity orphan: meo-u-kitchen---mon-nhat, brownie-coffee-and-tea, catimo-coffee (119 dish entity), itinerary: ben-tre-tong-tai-romantic-2day-
  - FIX: Phân loại: (a) dish/place orphan có thể được do chưa có relationship 'located_in' hoặc 'serves'—cần ETL bổ sung quan hệ; (b) itinerary orphan cần được link đến entity điểm đến; (c) Sau khi tạo relatio

- **DF-06** [Data fact-check sâu] (a2) — 46 sản phẩm nhắc OCOP trong summary nhưng thiếu trường ocop trong attributes
  - file: `web/data.json`
  - 46 entity type=product có từ 'OCOP' trong summary nhưng attributes không có khóa 'ocop', 'ocop_star', 'ocop_stars': cam-sanh-tam-binh ('Cam Sành Tam Bình là đặc sản... Vĩnh Long'), buoi-nam-roi-binh-minh ('mệnh danh là nữ hoàng các loại bưởi... sản phẩm OCOP'), muoi-ba-tri ('sản
  - FIX: Dùng script ETL parse summary để trích xuất số sao OCOP ('OCOP 4 sao', 'OCOP 3 sao') và backfill vào attributes.ocop. Với các entity không rõ sao, set ocop='OCOP' (như đã làm cho một số entity). Đây l

- **DF-07** [Data fact-check sâu] (a2) — 11 tuyên bố superlative chưa kiểm chứng trong summary
  - file: `web/data.json`
  - 11 trường hợp dùng các cụm 'lớn nhất Việt Nam', 'lớn nhất cả nước', 'lớn nhất miền Tây', 'nổi tiếng nhất Việt Nam': (1) chua-vam-ray-chua-phat-nam: 'Ngôi chùa Khmer lớn nhất Việt Nam...tượng Phật nằm ngoài trời lớn nhất cả nước'; (2) chua-vam-ray-wat-samrong: 'tượng Phật ngoài tr
  - FIX: Cần thêm nguồn tham chiếu hoặc làm mềm các tuyên bố: 'một trong những' thay cho 'lớn nhất'. Đặc biệt 4 entity Vàm Ray đưa ra 4 cấp độ khác nhau—mâu thuẫn nội bộ cần hợp nhất. Quy tắc §1.4: không bịa d

- **DF-08** [Data fact-check sâu] (a2) — 214 entity không-place bị kẹt ở tọa độ fallback cấp tỉnh/phường
  - file: `web/data.json`
  - 812 entity dùng tọa độ ward-level fallback (nhóm 5+ entity cùng 1 điểm). Trong đó 214 entity thuộc type attraction/experience/dish/product/history/accommodation đang dùng tọa độ fallback trung tâm TP (không phải ward của chính nó): 56 attraction, 41 experience, 35 dish, 28 produc
  - FIX: Ưu tiên geocode lại 56 attraction và 13 accommodation (user quan tâm nhất). Với 35 dish entity ở trung tâm VL—hầu hết là quán ăn cụ thể với địa chỉ thật trong attributes, có thể dùng Google Places / O

- **DI-001** [Data integrity] (a1) — 58 entities have coordinates outside the ĐBSCL bounding box
  - file: `web/data.json`
  - 58 entities have coordinates[lat,lng] that fall outside lat 9–11 / lon 105–107 (the geographic footprint of Vĩnh Long + Bến Tre + Trà Vinh). Categories: 24 are lat>11 (e.g. khu-di-tich-nguyen-dinh-chieu [11.274,106.508] area=ben-tre; mang-cut-binh-hoa-phuoc [11.423,106.607] area=
  - FIX: Tighten validate_data.py bbox to lat 9.0–11.0, lon 104.8–107.1 and report these as errors. Cross-check each of the 58 entities against OSM; most appear to have longitude digits transposed or are geoco

- **DI-002** [Data integrity] (a1) — 128 of 133 produced_in relationships point to craft_village entities, not xa/phuong places
  - file: `web/data.json`
  - produced_in relationship type count=133. Target breakdown: craft_village/None=128, place/phuong=3, place/xa=2. All 128 bad targets are craft_village entities, e.g. lang-keo-dua-mo-cay (Làng nghề kẹo dừa Mỏ Cày), lang-nghe-com-dep-ba-so, chom-chom-binh-hoa-phuoc, vung-trong-dua-sa
  - FIX: Add a check to validate_data.py: produced_in target must be type=place with level in {xa, phuong}. For the 128 non-conforming links: either (a) change the relationship type to associated_with or relat

- **DI-004** [Data integrity] (a1) — 37 entities typed as place have level=None and no parentId — likely wrong entity type
  - file: `web/data.json`
  - 37 entities have type=place, level=None, parentId=None. They are not administrative units — they are POIs: restaurants (tinh-binh-chay-vinh-long, com-chay-au-lac-vinh-long, ba-nhi-bun-bo-hue-vinh-long), bus stations (ben-xe-vinh-long-trung-tam-vinh-long, ben-xe-ben-tre-trung-tam-
  - FIX: Retype these 37 entities to their correct type: restaurants→dish or attraction, bus stations/ferry terminals→facility, hospitals/clinics→facility, markets/supermarkets→facility or attraction, cooperat

- **D03** [Deps/perf/bundle] (a2) — public_api.py gọi db.list_entities(limit=100000) để filter Python-side — 3 callsite
  - file: `agent/public_api.py:107, 372, 552`
  - Line 107 (GET /api/entities với month filter): `full = db.list_entities(entity_type=type, area=area, limit=100000, offset=0)` rồi `filtered = [e for e in full if _in_month(e)]`. Line 372 (homepage feed): `all_ents = db.list_entities(limit=100000, offset=0)`. Line 552 (GET sự kiện
  - FIX: SQLite: `WHERE json_extract(season, '$.months') LIKE '%"6"%'` hoặc dùng `json_each()`. Postgres: `WHERE (season::jsonb->'months') @> '6'::jsonb`. Nếu không muốn SQL phức tạp, ít nhất thêm index trên c

- **D04** [Deps/perf/bundle] (a2) — places_in_area / ocop_products / accommodation_search: quét toàn _entities + N get_place() calls mỗi chat turn
  - file: `agent/server.py:499-509, 542-586, 600-638`
  - Tool `places_in_area` (line 499-509): vòng lặp `for e in knowledge._entities.values()` (~1800 item) tính content_counts, mỗi entity gọi không tốn nhưng tổng là O(N). Tool `ocop_products` (line 542-586): cùng vòng lặp toàn tập, trong đó với area filter gọi `knowledge.get_place(e["
  - FIX: Xây dựng index phụ lúc startup (hoặc sau reload): `_ocop_index = {eid: e for eid, e in _entities.items() if (e.get('attributes') or {}).get('ocop')}` và tương tự cho accommodation. places_in_area đã c

- **D05** [Deps/perf/bundle] (a2) — search_entities(): gọi get_place(e['id']) bên trong vòng lặp toàn tập khi có area filter hoặc text query
  - file: `agent/knowledge.py:261-335`
  - Hàm `search_entities()` (line 261): khi `area` được truyền vào (line 280-293), mỗi entity đều gọi `p = get_place(e['id'])` (line 281) — tức là lookup `_entities.get(e.get('placeId'))`. Khi có text query (line 303-315), cũng gọi `place_info = get_place(e['id'])` (line 306) cho mỗi
  - FIX: Thêm pre-computed map `_entity_to_area: dict[str, str]` = `{eid: _entities[pid].get('area') for eid, e in _entities.items() if (pid := e.get('placeId')) and pid in _entities}` sau mỗi reload. Filter a

- **D06** [Deps/perf/bundle] (a2) — requirements.txt dùng >= version lỏng cho toàn bộ 20+ dependency — build không tái lập
  - file: `requirements.txt:1-24`
  - Tất cả 20+ dependency đều dùng `>=` (e.g. `fastapi>=0.115`, `openai>=1.82`, `nuxt: ^4.4.8` trong package.json). Không có file `requirements.lock` hay `pip freeze` output. `nuxt: ^4.4.8` (package.json line 17) dùng caret — minor/patch update có thể vào tự động. Hệ quả: `pip instal
  - FIX: Chạy `pip freeze > requirements.lock` sau khi đã cài đủ và test xanh. Dùng `pip install -r requirements.lock` trong deploy script. Với npm: thêm `package-lock.json` vào git (đang bị .gitignore). Tối t

- **EH-03** [Error handling/resilience] (a2) — os.environ["LLM_API_KEY"] / os.environ["LLM_BASE_URL"] tại module-level — KeyError crash khi import
  - file: `agent/server.py`
  - Dòng 270-271: `client = OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=os.environ["LLM_BASE_URL"])` — dùng subscript `[]` thay vì `.get()`. Cùng pattern tại: `agent/crawler.py:31-32`, `agent/auto_learn.py:44-45`, `agent/image_recognition.py:55`, `agent/import_crawled.py:29-30
  - FIX: Đổi sang `os.environ.get("LLM_API_KEY", "")` và `os.environ.get("LLM_BASE_URL", "")`. Nếu muốn fail-fast rõ ràng hơn, kiểm tra sớm trong `lifespan()` và raise với thông báo rõ ràng thay vì để KeyError

- **EH-05** [Error handling/resilience] (a2) — admin.py ai_triage gọi LLM không timeout — admin endpoint bị treo
  - file: `agent/admin.py`
  - Dòng 1095: `resp = client.chat.completions.create(model=MODEL_MINI, temperature=0.3, max_tokens=400, messages=[...])` — không có `timeout`. Đây là endpoint `/admin/ai/triage` mà admin bấm on-demand, nếu LLM chậm có thể treo request nhiều phút.
  - FIX: Thêm `timeout=LLM_TIMEOUT` (hoặc hardcode 30) vào lời gọi: `client.chat.completions.create(model=MODEL_MINI, temperature=0.3, max_tokens=400, timeout=30, messages=[...])`.

- **EH-07** [Error handling/resilience] (a2) — middleware.py StructuredLogger._flush() nuốt exception ghi file — mất log không thông báo
  - file: `agent/middleware.py`
  - Dòng 98: `except Exception: pass` trong `_flush()`. Nếu disk đầy, path lỗi, hoặc encoding issue khi ghi `server.log.jsonl`, lỗi bị nuốt hoàn toàn. Tương tự `_rotate()` tại dòng 110: `except Exception: pass`. Hệ thống không biết log đang bị mất.
  - FIX: Thay `pass` bằng ít nhất `self._py_logger.error(f"Log flush failed: {e}", exc_info=True)` để có stderr output khi file I/O lỗi — không nên nuốt hoàn toàn lỗi của chính logger.

- **EH-08** [Error handling/resilience] (a2) — scheduler Telegram gửi tuần tự trong vòng lặp không có per-recipient timeout guard
  - file: `agent/scheduler.py`
  - Dòng 307-309 và 325-327: `for cid in admin_ids: httpx.post(telegram_url, ..., timeout=15)` — có timeout 15s/recipient nhưng nếu có nhiều admin_ids và đầu tiên treo full 15s, tổng thời gian tích lũy. Nghiêm trọng hơn: nếu một recipient fail, `except Exception` ở dòng 311 bắt cả vò
  - FIX: Bọc từng `httpx.post` trong try/except riêng bên trong vòng lặp để một recipient lỗi không chặn các recipient khác. Thêm log khi từng lần gửi fail.

- **EH-09** [Error handling/resilience] (a2) — autonomous_budget.py try_consume: ghi file thất bại bị nuốt, nhưng count trong RAM vẫn tăng — mismatch RAM vs disk
  - file: `agent/autonomous_budget.py`
  - Dòng 62-63: `except Exception: pass  # ghi log thất bại không nên chặn`. Khi ghi `.tmp` thất bại (disk full, permission), count trong RAM đã tăng nhưng file không được persist. Sau restart server, count bị reset về 0, agent tự động có thể gọi thêm LLM ngoài cap. Comment thừa nhận
  - FIX: Ghi log warning rõ ràng khi persist fail: `import logging; logging.getLogger('autonomous_budget').warning(f'Cap persist failed: {e}')`. Cân nhắc ghi count vào đồng thời DB (bảng settings) để tồn tại q

- **EH-10** [Error handling/resilience] (a2) — learn_loop.py _web_search_light và auto_learn.py web_search: DDGS không có timeout
  - file: `agent/learn_loop.py`
  - Dòng 93 (learn_loop.py): `with DDGS() as ddgs: results = list(ddgs.text(...))` — không timeout. Dòng 225 (auto_learn.py): tương tự. Các hàm này được gọi từ scheduler background tasks. Một DDG hang treo toàn bộ scheduled task slot (scheduler chạy đơn luồng), chặn các task tiếp the
  - FIX: Áp dụng timeout tương tự như EH-04: `DDGS(timeout=10)`. Ngoài ra, scheduler task nên có hard timeout qua `subprocess.run(..., timeout=300)` — đã có ở `task_auto_learn` nhưng cần đảm bảo learn_loop int

- **SEO-03** [FE quality/SEO] (a1) — Canonical /theo-mua bỏ ?month= nhưng JSON-LD entity URL lại chứa query-string — mâu thuẫn
  - file: `C:\Code\vinhlong360\web-nuxt\pages\theo-mua.vue`
  - Dòng 316: canonical = canonicalUrl('/theo-mua') (bỏ query). Dòng 324: JSON-LD url = canonicalUrl('/theo-mua?month=X') (giữ query). Hàm canonicalUrl (useSeoHelpers.ts:3-6) strip query nên dòng 324 cũng trả về /theo-mua, nhưng ý đồ có vẻ muốn canonical theo tháng. Nếu mục tiêu là 1
  - FIX: Quyết định: (a) nếu /theo-mua là 1 trang duy nhất giữ nguyên canonical='/theo-mua' và bỏ url trong JSON-LD hoặc đặt cùng giá trị; (b) nếu muốn 12 URL index được, sửa canonical thành canonicalUrl('/the

- **CWV-01** [FE quality/SEO] (a1) — Phần lớn ảnh entity không đi qua NuxtImg/weserv — mất WebP và srcset tự động
  - file: `C:\Code\vinhlong360\web-nuxt\pages\dia-diem\[id].vue`
  - Dòng 18: ảnh cover hero dùng `<img>` thường (không phải NuxtImg). Dòng 44-59: thumbnail strip dùng `<img>`. Lightbox dòng 74: `<img>`. EntityCard.vue dòng 4-5: chỉ remote image dùng NuxtImg, local image dùng `<img>` thường. Weserv chỉ được dùng qua NuxtImg. nuxt.config.ts dòng 22
  - FIX: Ưu tiên đổi hero cover img sang NuxtImg với sizes='100vw' và format=['webp'] để weserv transcode. Thumbnail strip có thể giữ img nhưng cần chắc chắn URL đã là weserv. Ít nhất LCP image (hero cover) nê

- **CWV-02** [FE quality/SEO] (a1) — Region tile dùng background-image CSS — ảnh không được preload, không có WebP fallback
  - file: `C:\Code\vinhlong360\web-nuxt\pages\index.vue`
  - Dòng 130: `:style="{ backgroundImage: 'url(/img/cat/...' }"` — ảnh set qua CSS inline, browser phát hiện muộn hơn img tag, không có srcset/WebP, không lazy/eager signal rõ ràng. 3 region tile đều dùng cách này.
  - FIX: Thêm <link rel='preload' as='image'> cho 3 ảnh region tile trong useHead, hoặc chuyển sang img element với loading='lazy' width/height được set, cho phép weserv transcode qua NuxtImg. Nếu giữ backgrou

- **SSR-01** [FE quality/SEO] (a1) — xa-phuong/[id].vue dùng `id.value` (snapshot tại setup-time) làm cache key của useAsyncData — client navigation không rehydrate khi id thay đổi
  - file: `C:\Code\vinhlong360\web-nuxt\pages\xa-phuong\[id].vue`
  - Dòng 148: `await useAsyncData('ward-' + id.value, ...)` — key là string cố định tại thời điểm setup (id.value được evaluate một lần). Không có option `watch: [id]` như dia-diem/[id].vue (dòng 380). Nếu user navigate từ /xa-phuong/A sang /xa-phuong/B trong SPA mode, useAsyncData s
  - FIX: Đổi key thành computed: `await useAsyncData(computed(() => 'ward-' + id.value), ..., { watch: [id] })` — giống pattern của dia-diem/[id].vue dòng 377-381.

- **GS-03** [Graph semantic] (a2) — 308 entity (17%) không có located_in — backbone địa lý bị thiếu
  - file: `web/data.json`
  - 308/1775 entity không có bất kỳ rel located_in nào. Phân tích: dish 138, product 47, nature 24, attraction 22, place 38, history 14, craft_village 8, experience 8, accommodation 4, event 3, person 2. Ví dụ orphan dishes: meo-u-kitchen---mon-nhat (Mèo Ú Kitchen), brownie-coffee-an
  - FIX: Batch geocode 308 entity dựa trên trường area + tên địa điểm để gán ward phù hợp. Ưu tiên accommodation (4) và attraction (22) trước vì impact lớn nhất. 119 entity từ foody.vn hoàn toàn không có rel —

- **GS-04** [Graph semantic] (a2) — 169 entity mồ côi — không có bất kỳ relationship nào (in hoặc out)
  - file: `web/data.json`
  - 169 entity không xuất hiện trong bất kỳ rel nào: itinerary 2, dish 119, attraction 5, nature 3, experience 1, product 1, accommodation 1, place 37. Đáng chú ý: 2 itinerary hoàn toàn bị cô lập ('Bến Tre 2N1Đ – Tổng tài đưa nữ chính về miền Tây', 'Backpacker tiết kiệm 3 ngày dưới 5
  - FIX: Phân loại 3 nhóm: (a) 2 itinerary mồ côi cần thêm related_to cho POI/dish trong lộ trình; (b) 119 dish từ foody cần gán located_in ward tối thiểu; (c) 37 place tiện ích nên thêm located_in và near với

- **GS-05** [Graph semantic] (a2) — 311 near rels liên quan đến entity type=person — sai ngữ nghĩa hoàn toàn
  - file: `web/data.json`
  - 150 near đi từ person, 174 near đến person, tổng 311 (7% tổng near). Ví dụ sai rõ ràng: 'Thành Tôn near Bánh phu thê Vĩnh Long' (người near món ăn?), 'Phan Thanh Giản near Nem chua Sáu Xệ' (nhân vật lịch sử near đặc sản?), 'Nguyễn Đình Chiểu near Nguyễn Thị Định' (2 nhân vật lịch
  - FIX: near rels liên quan đến person phải được thay bằng associated_with (nếu có liên hệ lịch sử thực sự) hoặc xóa. Script lọc: xóa near rels mà from hoặc to có type=person, giữ lại associated_with person->

- **GS-06** [Graph semantic] (a2) — 275 near rels cross-province — địa lý mâu thuẫn
  - file: `web/data.json`
  - 275 near rels giữa entity thuộc hai tỉnh khác nhau (area khác nhau). Phân bổ: vinh-long<->tra-vinh 146, vinh-long<->ben-tre 124, ben-tre<->tra-vinh 5. Ví dụ: 'Chèo xuồng ba lá [vinh-long] near Vườn Sầu Riêng Bảy Thảo [ben-tre]', 'Chùa KompongNigrodha [vinh-long] near Bún suông [t
  - FIX: Xem xét lại thuật toán sinh near: có thể giới hạn near chỉ trong cùng area, hoặc thêm distance_km vào near rel. 275 cross-province near nên review thủ công hoặc xóa tự động nếu không có placeId/coords

- **GS-07** [Graph semantic] (a2) — p-long-chau (Phường Long Châu) là hub bất thường với 209 entity — gấp 16x trung bình
  - file: `web/data.json`
  - Ward p-long-chau có 209 entity located_in trong khi avg toàn bộ 124 ward = 13.1 entity/ward. Top wards: p-long-chau=209, xa-nhi-long=102, xa-nhon-phu=95, p-phu-khuong=94, p-phuoc-hau=91. Phân tích 209 entity trong p-long-chau: attraction 41, experience 34, accommodation 33, histo
  - FIX: p-long-chau đang được dùng như catch-all cho trung tâm TP Vĩnh Long. Cần phân tách: xem xét coords thực của từng entity để gán đúng ward (p-thanh-duc, p-phuoc-hau, v.v.). 29 ward khác hiện có 0 entity

- **GS-08** [Graph semantic] (a2) — 592 associated_with dish->craft_village với nhiều cặp phi ngữ nghĩa — có thể là Cartesian artifact còn sót
  - file: `web/data.json`
  - 73 dish entity có tổng 592 associated_with rels đến 71 craft_village, trung bình 8.1 craft_village/dish. Nhiều cặp vô nghĩa: 'Bánh canh Bến Tre' -> 'Công ty Cổ phần XNK Bến Tre (Betrimex)'; 'Chè chuối nướng' -> 'Công ty TNHH Chế biến dừa Lương Quới'; 'Cháo Ếch' -> 'Làng nghề sản
  - FIX: Lọc associated_with dish->craft_village: chỉ giữ cặp có semantic rõ ràng (ví dụ: 'Kẹo dừa Mỏ Cày' -> 'Làng nghề kẹo dừa Mỏ Cày' là đúng). Xóa các cặp crosshatch (bánh canh -> công ty dừa). Cân nhắc đổ

- **GS-09** [Graph semantic] (a2) — Người-hub bất thường: Nguyễn Thiện Thành có 92 associated_with rels đến 84 entity history khác nhau
  - file: `web/data.json`
  - 35 person entity nhưng phân bổ out-degree rất lệch: Nguyễn Thiện Thành=92, Thanh Hương=80, Nguyễn Đình Chiểu=75, Thành Tôn=67, Thành Lộc=64, Đồng Văn Cống=51, Nguyễn Thị Định=50. Đây là 84-92 associated_with person->history từ một người, ví dụ: Nguyễn Thiện Thành associated_with
  - FIX: associated_with person->history nên chỉ giữ lại liên kết có bằng chứng thực (nhân vật được thờ/sinh/mất tại di tích đó). Hiện tại có vẻ là Cartesian trong phạm vi tỉnh. Cần review thủ công hoặc scrub

- **GS-10** [Graph semantic] (a2) — 7 entity là bản sao của cùng 1 thực thể thực (duplicate entities)
  - file: `web/data.json`
  - 3 IDs cho Bảo tàng Văn hóa Khmer Trà Vinh: bao-tang-van-hoa-dan-toc-khmer-tinh-tra-vinh [attraction], bao-tang-van-hoa-dan-toc-khmer [attraction, không có area], bao-tang-van-hoa-dan-toc-khmer-tra-vinh [history]. 2 IDs cho Bảo tàng Vĩnh Long: bao-tang-tinh-vinh-long [history, 19
  - FIX: Merge các entity trùng: chọn ID canonical cho mỗi nhóm, cập nhật tất cả rels trỏ vào ID cũ sang ID canonical, xóa entity cũ. Backup B1 bắt buộc. Ưu tiên Khmer museum (3->1) và Vinh Long museum (2->1).

- **SEC-003** [Security] (a1) — os.environ[...] không có default gây KeyError/crash khi thiếu LLM_API_KEY hoặc LLM_BASE_URL
  - file: `C:\Code\vinhlong360\agent\server.py`
  - Dòng 270-271: `client = OpenAI(api_key=os.environ['LLM_API_KEY'], base_url=os.environ['LLM_BASE_URL'])` dùng index notation (không phải .get()), sẽ ném KeyError ngay khi import module nếu thiếu biến. Dòng 3284 cũng có `os.environ['LLM_BASE_URL']` khi print. Tương tự ở auto_learn.
  - FIX: Thay `os.environ['LLM_API_KEY']` bằng `os.environ.get('LLM_API_KEY', '')` rồi kiểm tra và raise lỗi có thông báo rõ ràng nếu rỗng (ví dụ: `if not api_key: raise RuntimeError('LLM_API_KEY must be set i

- **SEC-004** [Security] (a1) — Itinerary và relationship endpoints không validate input — bất kỳ dict nào được ghi thẳng vào DB
  - file: `C:\Code\vinhlong360\agent\admin.py`
  - Dòng 431: `async def create_itinerary(body: dict)` và dòng 438: `async def update_itinerary(itin_id: str, body: dict)` nhận raw dict, chỉ kiểm tra `body.get('id')` và `body.get('title')`, sau đó gọi `db.upsert_itinerary(body)` với toàn bộ payload. Tương tự, dòng 455-456: `add_rel
  - FIX: Tạo Pydantic model cho ItineraryCreate/ItineraryUpdate và RelationshipCreate tương tự EntityCreate/EntityUpdate đã có. Chỉ cho phép các field đã biết (id, title, area, duration, summary, stops v.v.),

- **TC-03** [Test coverage blind-spot] (a2) — Luồng pass-2 (placeId=None cố ý, coords_approximate) không có test regression
  - file: `agent/database.py`
  - Grep 'coords_approximate|crosswalk|geocode_approx|resolve_missing_placeid' trong cả tests/ và agent/tests/ không trả về kết quả nào. test_database.py có test_upsert_get_entity_roundtrip (dòng 61-70) và test_entities_by_place (dòng 254-267) nhưng không có test nào xác nhận: (a) en
  - FIX: Thêm vào agent/tests/test_database.py: test_entities_by_place_excludes_null_placeid (entity với placeId=None không lọt vào trang hub ward), test_upsert_preserves_coords_approximate_flag (upsert entity

- **TC-05** [Test coverage blind-spot] (a2) — test_integration.py — nhiều test chỉ assert isinstance(data, dict), không kiểm tra nội dung
  - file: `tests/test_integration.py`
  - Grep 'assert isinstance.*dict\)$' trong test_integration.py trả về 7 trường hợp: test_vector_stats_endpoint (dòng 266), test_prompt_cache_stats_endpoint (dòng 276), test_analytics_summary_endpoint (dòng 286), test_circuit_breaker_stats_endpoint (dòng 296), test_welcome_endpoint (
  - FIX: Nâng assertion cho 5 test trên: test_analytics_summary_endpoint kiểm tra {'queries', 'entity_hits', 'unanswered', 'daily_stats'} là subset của data.keys(); test_circuit_breaker_stats_endpoint kiểm tra

- **TC-07** [Test coverage blind-spot] (a2) — tests/test_integration.py dùng scope='module' cho client fixture — side effect giữa tests
  - file: `tests/test_integration.py`
  - test_integration.py:59-74: `@pytest.fixture(scope='module')` cho client fixture. KB singleton (knowledge._entities) và analytics data được chia sẻ giữa tất cả test trong module. test_chat_endpoint (dòng 130) ghi vào analytics; test_analytics_summary_endpoint (dòng 282) đọc analyt
  - FIX: Đổi scope='module' → scope='function' cho client fixture trong test_integration.py, hoặc thêm autouse fixture reset analytics và report_limiter sau mỗi test. Trong test_chat_smoke.py, đảm bảo knowledg

- **TC-08** [Test coverage blind-spot] (a2) — Crosswalk parser NQ1687 (migrate_huyen_to_ward.py) — regex COMMUNE/CITY không có unit test
  - file: `scripts/migrate_huyen_to_ward.py`
  - resolve_missing_placeid.py:21 và fix_placeid_crosswalk.py đều re-import migrate_huyen_to_ward.py để dùng regex COMMUNE/CITY/norm/OLD2NEW/NUMBERED. Đây là logic phân tích địa chỉ tiếng Việt phức tạp (viết tắt 'P.', 'X.', 'TT.', số phường, ...). Không có test nào verify: 'P. Long H
  - FIX: Tạo tests/test_crosswalk_parser.py import migrate_huyen_to_ward bằng importlib.util (như test_normalize_data.py). Test các case: (1) 'P. Long Hồ, tỉnh Vĩnh Long' → 'p-long-ho'; (2) 'X. Sơn Đông, huyện

## LOW

- **ARCH-002** [Architecture/consistency] (a1) — data.json↔DB field drift: 'verifiedAt' and 'createdAt' exist only in data.json, not in DB schema
  - file: `agent/data/vinhlong360.db (entities table) vs web/data.json`
  - DB PRAGMA table_info(entities) has 18 columns; data.json entities have 20 fields. Fields in JSON but NOT in DB: ['createdAt', 'verifiedAt']. These are computed at read time in database.py:1115-1151 (_normalize_entity_timestamps) and injected into the dict returned by DB reads, bu
  - FIX: This is an intentional pattern (computed on read) — document it explicitly in database.py near line 1115 and in export_data.py. Add a unit test that verifies export output contains both verifiedAt and

- **ARCH-004** [Architecture/consistency] (a1) — export_data.py docstring still lists deleted web-astro target and non-existent --astro-only flag
  - file: `agent/export_data.py:7,12`
  - Line 7: '3. web-astro/src/data/data.json — Astro SSG build source'. Line 12: 'python agent/export_data.py --astro-only # Export only to Astro'. The web-astro directory does not exist (confirmed by ls: only web/ and web-nuxt/ present). Line 97 in the same file correctly notes 'web
  - FIX: Remove lines 7 and 12 from the module docstring. The docstring should list only: (1) web/data.js, (2) web/data.json. This is a pure documentation fix with no code impact.

- **ARCH-005** [Architecture/consistency] (a1) — BUILD_SEARCH_INDEXES and SCHEDULER_ENABLED default to True in config.py — unsafe for local dev without explicit env override
  - file: `agent/config.py:59-61`
  - Lines 59-61: BUILD_SEARCH_INDEXES: bool = True, BACKGROUND_INDEX_BUILD: bool = True, SCHEDULER_ENABLED: bool = True. CLAUDE.md §5 instructs developers to run the server with explicit env flags: '$env:BUILD_SEARCH_INDEXES=false; $env:BACKGROUND_INDEX_BUILD=false; $env:SCHEDULER_EN
  - FIX: No change needed for production correctness — autonomous flags are already safe. For ergonomics, consider adding a .env.example with BUILD_SEARCH_INDEXES=false/BACKGROUND_INDEX_BUILD=false/SCHEDULER_E

- **ARCH-006** [Architecture/consistency] (a1) — Nuxt build: no NODE_OPTIONS=--max-old-space-size set for VPS builds; maplibre-gl bundles to 1 MB client chunk
  - file: `scripts/deploy.sh:67 and web-nuxt/nuxt.config.ts:141-145`
  - deploy.sh line 67: '( cd web-nuxt && npm run build )' with no NODE_OPTIONS. package.json 'build' script: 'nuxt build' with no memory flag. The largest client chunk is BSCK7p18.js at 1,053,439 bytes (maplibre-gl, confirmed by .output/public/_nuxt/ listing). nuxt.config.ts vite sec
  - FIX: Add NODE_OPTIONS='--max-old-space-size=512' before npm run build in scripts/deploy.sh and scripts/build-prerender.sh. This caps Node's heap to 512 MB, giving the OS headroom without OOM-killing the bu

- **F3** [Backend API] (a1) — /graph endpoint không có xác thực — toàn bộ graph KB lộ ra ngoài
  - file: `agent/server.py:2899-2904`
  - Endpoint GET /graph tại line 2899-2904 không có dependency require_admin, không có verify_admin_key, không có rate limiting. graph_expand() tại agentic_rag.py:247 có thể trả tối đa 50 node + toàn bộ edges qua nhiều hops. Kẻ tấn công có thể crawl toàn bộ knowledge graph bằng cách
  - FIX: Thêm rate limiting cho /graph (dùng chat_limiter hoặc tạo graph_limiter riêng). Nếu graph chỉ dùng cho frontend Nuxt (trang detail entity), cân nhắc move vào /api/graph để dùng chung rate limit với cá

- **F5** [Backend API] (a1) — Response shape không nhất quán: /api/search trả 'results' nhưng /api/entities trả 'entities'
  - file: `agent/public_api.py:251-261 + agent/public_api.py:86-118`
  - GET /api/search (line 251-261) trả {'q', 'total', 'results': [...]}. GET /api/entities (line 86-118) trả {'total', 'entities': [...]}. Cùng dữ liệu entity, cùng _enrich_place(), cùng total, nhưng key mảng khác nhau. Frontend Nuxt phải xử lý 2 shape riêng. Không crash nhưng gây lỗ
  - FIX: Chuẩn hoá về một key, ưu tiên 'entities' (nhất quán với admin.py). Hoặc ít nhất document rõ sự khác biệt. Thay 'results' → 'entities' trong GET /api/search response (line 261) nếu frontend đã sẵn sàng

- **F6** [Backend API] (a1) — call_tool 'places_in_area' dùng knowledge._entities (in-memory) trong event loop — tiềm ẩn block nếu KB lớn
  - file: `agent/server.py:498-509`
  - places_in_area tool tại line 498-509 vòng qua toàn bộ knowledge._entities.values() (có thể ~2000+ entity sau pass-2) trong event loop handler của call_tool, được gọi từ _run_agent chạy trong asyncio.to_thread (line 1607). Tuy nhiên nếu HAS_ORCHESTRATOR=False hoặc các tool calls t
  - FIX: Thấp ưu tiên với dataset <2k. Nếu muốn fix: pre-compute content_counts một lần khi load/reload KB thay vì vòng lặp mỗi lần gọi tool. Có thể cache trong knowledge module tương tự cách adjacency list đư

- **CLP-07** [Chat/LLM pipeline] (a2) — cross_domain_query trong agentic_rag có thể gây O(n^2) KB lookup, làm chậm build_rag_context
  - file: `agent/agentic_rag.py`
  - Dòng 543-571: `cross_domain_query()` với 2 vòng lặp lồng nhau: `for i in range(len(detected_concepts))` × `for j in range(i+1, len(detected_concepts))` × `for eid_a in c_from['entities'][:3]` × `for eid_b in c_to['entities'][:3]`. Mỗi cặp gọi `find_paths(eid_a, eid_b, max_hops=3)
  - FIX: Giới hạn `cross_domain_query` chỉ chạy khi intent là `multi_hop` hoặc khi phát hiện >=2 entity thực sự từ KB (không chạy cho mọi `moderate`). Thêm limit: `if len(detected_concepts) > 3: detected_conce

- **CLP-08** [Chat/LLM pipeline] (a2) — memory_graph.decay_weights() gọi _save_unlocked() vẫn trong `with self._lock` — không phải lỗi deadlock nhưng là pattern nguy hiểm, và save vô điều kiện dù không có thay đổi
  - file: `agent/memory_graph.py`
  - Dòng 583-599: `decay_weights()` mở `with self._lock`, sau đó nếu `not to_remove` gọi `self._save_unlocked()` (dòng 599). `_save_unlocked()` không acquire lock (đúng theo comment dòng 192: 'caller must hold self._lock'), nên không deadlock. Tuy nhiên nhánh `else` ở dòng 598-599 gọ
  - FIX: Trong nhánh `else` (không có edge nào bị xoá), bỏ `self._save_unlocked()` — không cần save nếu không thay đổi. Hoặc dùng `self._maybe_auto_save()` thay thế để chỉ save theo ngưỡng mutation.

- **CONC-005** [Concurrency/async] (a2) — _ensure() initial load has check-then-act race under concurrent startup requests
  - file: `agent/knowledge.py`
  - Lines 107–110: `_ensure()` checks `if _entities is None` then calls `_load()` and assigns globals. There is no lock. During server startup, if two coroutines (e.g. lifespan at line 788 and an early /health request) both call `_ensure()` simultaneously before the first `_load()` c
  - FIX: Add `_reload_lock` (already exists) to `_ensure()`: acquire it, recheck `if _entities is None`, then load. One line of change: `with _reload_lock: if _entities is None: ...`. Since lifespan already ca

- **F5** [DB layer] (a1) — PG upsert_entity: `season` column stored as TEXT (json.dumps string) but Postgres schema declares it JSONB
  - file: `agent/database.py`
  - init.sql line 24: `season JSONB`. upsert_entity PG path (line 322): passes `json.dumps(season_val, ensure_ascii=False)` — a Python string — to psycopg2 for a JSONB column. psycopg2 will auto-cast a string to JSONB only if the value is valid JSON text, which works. However, line 1
  - FIX: For PG JSONB columns (season, attributes, source, images, coordinates), pass the Python object directly wrapped in `psycopg2.extras.Json(value)` rather than pre-serializing with `json.dumps`. This ens

- **F6** [DB layer] (a1) — replace_from_json SQLite: coords_val bypasses _coords_in_region guard present in upsert_entity
  - file: `agent/database.py`
  - upsert_entity line 297: `if coords_val and not _coords_in_region(coords_val): coords_val = None` — out-of-region coordinates are nulled. replace_from_json line 887: `coords_val = entity.get("coordinates")` with no region guard before line 898: `json.dumps(coords_val) if coords_va
  - FIX: Add the same guard to replace_from_json after line 887: `if coords_val and not _coords_in_region(coords_val): coords_val = None`. Also apply _validate_place_level() which is also missing from the repl

- **DI-005** [Data integrity] (a1) — validate_data.py missing checks for self-loops, itinerary stop dangling refs, produced_in target type, and place level=None
  - file: `scripts/validate_data.py`
  - Gap analysis of validate_data.py against the full data contract. The following checks are absent: (1) self-loop relationships where from==to — audit confirmed 0 currently but no guard against future regressions; (2) itinerary stop.entityId not in entity id_set — audit confirmed 0
  - FIX: Add the following checks to validate_data.py: (a) rel from==to => self_loop error; (b) itinerary stop entityId not in id_set => dangling_itinerary_stop error; (c) produced_in target not place/xa-phuon

- **D01** [Deps/perf/bundle] (a2) — maplibre-gl (~900 KB gzip) trong dependencies, optimizeDeps eager-bundle vào main chunk
  - file: `web-nuxt/package.json:16 + web-nuxt/nuxt.config.ts:141-145`
  - package.json line 16: `"maplibre-gl": "^5.24.0"` nằm trong `dependencies` (không phải devDependencies). nuxt.config.ts lines 141-145 khai báo `vite.optimizeDeps.include: ['maplibre-gl']` — directive này bảo Vite pre-bundle maplibre-gl vào main chunk eager thay vì để nó dynamic-im
  - FIX: Xoá `vite.optimizeDeps.include: ['maplibre-gl']` khỏi nuxt.config.ts — Vite tự pre-bundle dep khi cần, dynamic-import trong ban-do.vue đã đúng rồi. maplibre-gl có thể giữ trong dependencies (cần để bu

- **D07** [Deps/perf/bundle] (a2) — boto3 + redis + opentelemetry-sdk cài unconditionally dù chỉ dùng có điều kiện
  - file: `requirements.txt:11-18`
  - requirements.txt lines 11-12: `opentelemetry-api>=1.25` và `opentelemetry-sdk>=1.25` được cài mặc định, nhưng agent/tracing.py có `try: from opentelemetry import trace ... except ImportError: _HAS_OTEL = False` — tức là OTel là optional. Lines 16-18: `redis>=5.0`, `Pillow>=10.0`,
  - FIX: Tách thành `requirements-optional.txt` (boto3, redis, opentelemetry-sdk) và `requirements.txt` (core only). Hoặc dùng extras: `pip install '.[storage,cache,tracing]'`. Tối thiểu: comment rõ `# optiona

- **D08** [Deps/perf/bundle] (a2) — maplibre-gl version pin lỏng ^5.24.0 — minor update có thể thay đổi tile API hoặc break CSS import
  - file: `web-nuxt/package.json:16`
  - Caret `^5.24.0` cho phép tự động lên 5.x.y bất kỳ. maplibre-gl v5 đang active development; changelog v5.x có breaking changes về style spec và CSS class names. useNDAMap.ts line 19 dùng `await import('maplibre-gl/dist/maplibre-gl.css')` — path này thay đổi giữa các major/minor re
  - FIX: Pin exact: `"maplibre-gl": "5.24.0"` hoặc `~5.24.0` (patch-only). Thêm comment trong package.json giải thích lý do pin.

- **D09** [Deps/perf/bundle] (a2) — `import re as _re` bên trong vòng lặp hot-path ocop_products (mỗi entity iteration)
  - file: `agent/server.py:557`
  - Trong tool `ocop_products` (line 534-586), vòng lặp `for e in knowledge._entities.values()` ở line 542, bên trong có `import re as _re` tại line 557 — nằm trong vòng lặp, chạy mỗi entity. Python cache module sau lần import đầu nên không re-execute module code, nhưng vẫn thực hiện
  - FIX: Xoá `import re as _re` tại line 557. Dùng trực tiếp `re.search(r'(\d)', ocop_val)` — `re` đã available từ top-level import. Tương tự tại server.py line 1062 (`import re as _re` trong `_resolve_context

- **D10** [Deps/perf/bundle] (a2) — Startup cost: build_search_indexes() chạy BM25 + embedding trên toàn entity mỗi lần khởi động
  - file: `agent/server.py:705-739, 785-803`
  - Hàm `build_search_indexes()` (line 705-739) gọi `contextual.build_all_contextual(entities, adapted_rels)` — build contextual text cho ~1800 entity + ~9500 relationship, rồi `bm25.build_index(texts)`. Hàm `embedding_store.build_index(entities)` tạo embedding cho toàn tập nếu HAS_V
  - FIX: Persist BM25 index ra file (pickle) và load lại nếu entities checksum chưa đổi (so sánh `knowledge.stats()['total_content']` với value trong file index). Chỉ rebuild khi data thực sự thay đổi (sau /re

- **ETL-08** [ETL pipeline] (a1) — normalize_data.py backup vào thư mục khác (kb_snapshots) — không nhất quán với B1, dễ bỏ qua
  - file: `scripts/normalize_data.py`
  - Line 20: `DEFAULT_BACKUP_DIR = ROOT / 'agent' / 'data' / 'kb_snapshots'`. Tất cả script ETL khác dùng `scratch/backups/` (backup_data.py line 32: `BACKUP_ROOT = ROOT / 'scratch' / 'backups'`). Thêm vào đó, normalize_data.py chỉ backup data.json, không backup vinhlong360.db (khác
  - FIX: Đổi DEFAULT_BACKUP_DIR về `ROOT / 'scratch' / 'backups'` cho nhất quán. Xem xét bỏ `--no-backup` hoặc thêm cảnh báo nổi bật khi dùng flag đó. Thêm backup DB vào normalize_data.py.

- **EH-11** [Error handling/resilience] (a2) — admin.py _sync_kb() nuốt exception reload KB — write-through thất bại âm thầm
  - file: `agent/admin.py`
  - Dòng 46-49: `def _sync_kb(): try: knowledge.reload() except Exception: pass`. Comment giải thích: lỗi reload không được làm hỏng thao tác admin đã commit. Nhưng nếu reload liên tục fail (dữ liệu DB hỏng, exception trong knowledge.py), admin sẽ thấy write thành công nhưng chat age
  - FIX: Bắt lỗi và log warning rõ: `except Exception as e: logger.warning(f'KB reload after admin write failed: {e}')`. Trả thêm field `kb_reload_ok: false` trong response nếu reload thất bại để admin biết.

- **EH-12** [Error handling/resilience] (a2) — image_recognition.py: os.environ["LLM_BASE_URL"] tại lazy-init nhưng os.environ.get("LLM_API_KEY", "") — xử lý không nhất quán
  - file: `agent/image_recognition.py`
  - Dòng 54-55: `_client = OpenAI(api_key=os.environ.get("LLM_API_KEY", ""), base_url=os.environ["LLM_BASE_URL"])` — `LLM_API_KEY` dùng `.get()` an toàn nhưng `LLM_BASE_URL` dùng `[]` ném KeyError nếu thiếu. Điều này xảy ra khi module được import lần đầu (lazy init), và KeyError sẽ c
  - FIX: Thống nhất dùng `os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")` và kiểm tra empty string trước khi tạo client.

- **F2** [FE null-safety] (a1) — xa-phuong/[id].vue: entity markers trong map dùng ent.coordinates thô thay vì normalizeCoords
  - file: `web-nuxt/pages/xa-phuong/[id].vue`
  - Dòng 249-262: `const c = ent.coordinates; if (!c || !c[0] || !c[1]) continue` — guard này sẽ bỏ qua entity có coordinates là mảng [0,0] (thoả điều kiện falsy cho !c[0]), và KHÔNG lọc được coordinates là chuỗi JSON không-parse. Nếu coordinates là chuỗi, `c[0]` là ký tự đầu tiên (t
  - FIX: Thay guard bằng: `const c = normalizeCoords(ent.coordinates); if (!c) continue;` rồi dùng `c[1]` và `c[0]` từ kết quả normalizeCoords.

- **F3** [FE null-safety] (a1) — lich-trinh/[id].vue: extractCoords cục bộ không dùng normalizeCoords — code trùng, thiếu swap lat/lng
  - file: `web-nuxt/pages/lich-trinh/[id].vue`
  - Dòng 160-167: `function extractCoords(raw: any): [number, number] | undefined { ... if (Array.isArray(c) && c.length >= 2) return [c[0], c[1]]; if (c.lat && c.lng) return [c.lat, c.lng]; }` — hàm này không có bước swap lat/lng khi lat>90 (logic chuẩn hoá trong normalizeCoords:16-
  - FIX: Thay extractCoords cục bộ bằng normalizeCoords từ useCoords (đã auto-import). Cập nhật interface StopCoord để dùng kết quả normalizeCoords.

- **F4** [FE null-safety] (a1) — tao-lich-trinh.vue: extractCoords cục bộ thứ hai — cùng vấn đề thiếu swap và validate
  - file: `web-nuxt/pages/tao-lich-trinh.vue`
  - Dòng 271-280: `function extractCoords(entity: Entity): [number, number] | undefined { let c = entity.coordinates; ... if (Array.isArray(c) && c.length >= 2) return [c[0], c[1]]; if (c.lat && c.lng) return [c.lat, c.lng]; }` — cùng pattern thiếu: không có bước swap, không validate
  - FIX: Thay bằng normalizeCoords (đã auto-import). Xoá cả hai extractCoords cục bộ để tránh ba phiên bản chuẩn hoá song song.

- **A11Y-01** [FE quality/SEO] (a1) — Màu hard-code ec-countdown (#9a6d1e) không qua design token — không kiểm soát được contrast ở dark mode
  - file: `C:\Code\vinhlong360\web-nuxt\pages\index.vue`
  - Dòng 778: `color: #9a6d1e` và dòng 784: `color: #b93a2a` — hard-code trong style block, không dùng CSS variable. Dark mode override ở dòng 1142 cần ghi đè thủ công (#e0b366). Nếu theme bị thay đổi qua admin (themeOverrideCss, default.vue dòng 193-209) thì màu này không follow the
  - FIX: Thay bằng `color: var(--accent-text)` (đã có trong variables.css dòng 42: '#9A6612' — gần tương đương và đạt AA) và `color: var(--error)` cho .ec-today. Bỏ dòng 1142 dark-mode override thủ công.

- **SEO-04** [FE quality/SEO] (a1) — bai-viet/[id].vue khai báo robots noindex hai lần — một trong useHead, một trong useSeoMeta
  - file: `C:\Code\vinhlong360\web-nuxt\pages\bai-viet\[id].vue`
  - Dòng 185: `useHead({ meta: [{ name: 'robots', content: 'noindex,follow' }] })` — luôn chạy. Dòng 198: `useSeoMeta({ robots: 'noindex,follow' })` — chỉ chạy khi post.value tồn tại. Cả hai đều ghi cùng tag, render ra 2 thẻ <meta name='robots'> trùng nhau trong HTML.
  - FIX: Xóa một trong hai. Giữ useSeoMeta bên trong `if (post.value)` và thêm fallback ở ngoài nếu cần. Hoặc chỉ giữ useHead bên ngoài, bỏ robots trong useSeoMeta.

- **SEO-05** [FE quality/SEO] (a1) — gioi-thieu, chinh-sach-bao-mat, dieu-khoan-su-dung không được prerender — SWR miss ở first request
  - file: `C:\Code\vinhlong360\web-nuxt\nuxt.config.ts`
  - Dòng 161-163: prerender.routes không bao gồm '/gioi-thieu', '/chinh-sach-bao-mat', '/dieu-khoan-su-dung'. crawlLinks=false (dòng 164) nên Nitro không tự crawl. Đây là 3 trang pháp lý tĩnh, nội dung không đổi, phù hợp prerender nhất. Hiện tại luôn render server-side theo request đ
  - FIX: Thêm '/gioi-thieu', '/chinh-sach-bao-mat', '/dieu-khoan-su-dung' vào mảng prerender.routes. Không có tác dụng phụ — nội dung static, không phụ thuộc DB runtime.

- **GS-11** [Graph semantic] (a2) — 29/124 ward không có entity nào (empty wards) — phân bổ nội dung mất cân bằng cực đoan
  - file: `web/data.json`
  - 29 ward có đúng 0 entity located_in: trong đó 14 ward thuộc vinh-long (xa-phu-quoi, xa-quoi-an, xa-trung-ngai, xa-hoa-binh, xa-hoa-hiep, xa-ngai-tu, xa-song-phu, xa-cai-ngang, xa-tan-luoc, xa-my-thuan, p-vung-liem, xa-hieu-phung, xa-hieu-thanh, xa-vinh-xuan), 8 thuộc tra-vinh (p-
  - FIX: Bổ sung tối thiểu 1-3 entity cho mỗi ward trống dựa trên dữ liệu địa phương (di tích, sản phẩm OCOP, điểm du lịch). Ưu tiên các ward có dân số/diện tích lớn. Đây là content gap thực sự, không phải lỗi

- **GS-12** [Graph semantic] (a2) — 5 cặp entity có cả located_in lẫn produced_in đến cùng target — redundant multi-edge
  - file: `web/data.json`
  - 5 product entity có đồng thời rel located_in VÀ produced_in đến cùng ward: Chôm chôm cù lao An Bình->Xã An Bình, Khoai lang tím Nhật->Phường Tân Quới, Tinh dầu dừa Bến Tre->Phường Mỏ Cày, Rượu dừa Bến Tre->Phường Mỏ Cày, Bưởi da xanh Chợ Lách->Xã Chợ Lách. Thêm 4 cặp có cả near l
  - FIX: Xóa located_in khi đã có produced_in đến cùng target (produced_in là rel semantically strong hơn và bao hàm location). Tổng 9 rels dư có thể clean up đơn giản.

- **GS-13** [Graph semantic] (a2) — 17 cặp related_to bidirectional — dư thừa đối xứng không cần thiết
  - file: `web/data.json`
  - 17 cặp entity vừa có A->B related_to vừa có B->A related_to: Làng nghề kẹo dừa Mỏ Cày <-> Thu hoạch dừa; Rượu dừa Bến Tre <-> Cơ sở kẹo dừa Mỏ Cày; Bảo tàng văn hóa dân tộc Khmer <-> Bảo tàng Văn hóa dân tộc Khmer tỉnh Trà Vinh (đây chính là evidence cho GS-10); Cam sành Tam Bình
  - FIX: Giống near, related_to nên được treat là undirected trong query engine. Nếu muốn clean data, xóa một chiều trong 17 cặp này. Chú ý cặp Khmer museum là symptom của duplicate entity (GS-10).

- **GS-14** [Graph semantic] (a2) — rel type phân bổ lệch nặng — near chiếm 46%, 4 type chỉ có 170 rels (<2%)
  - file: `web/data.json`
  - Phân bổ: near=4362 (45.9%), related_to=2024 (21.3%), located_in=1477 (15.5%), associated_with=1472 (15.5%), produced_in=133 (1.4%), hosts=30 (0.3%), offered_by=6 (0.06%), supplies_to=1. near chiếm gần một nửa toàn bộ graph nhưng không có chiều ngược. hosts (30), offered_by (6), s
  - FIX: Mở rộng dùng hosts (ward->experience) và offered_by (experience->organization) cho nhiều entity hơn để tăng tính khám phá graph. Hiện tại chỉ xa-an-binh và 2 ward khác có hosts — các ward khác nên áp

- **SEC-005** [Security] (a1) — Duplicate route POST /admin/entities/{entity_id}/images — endpoint thứ hai bị shadow, không validate URL scheme
  - file: `C:\Code\vinhlong360\agent\admin.py`
  - Có hai hàm cho cùng route `POST /admin/entities/{entity_id}/images`: dòng 307 (`add_entity_image_url`, nhận Pydantic model `_EntityImageURL`, cho phép cả `http://`, `https://`, và `/`) và dòng 539 (`add_entity_image`, dùng `await request.json()` thủ công, chỉ cho phép `https://`
  - FIX: Xoá hàm `add_entity_image` ở dòng 539-562 (dead code). Thống nhất logic ở `add_entity_image_url` (dòng 307): nên chỉ cho phép `https://` và `http://` (bỏ `/` nếu không dùng ảnh local), thêm kiểm tra đ

- **TC-06** [Test coverage blind-spot] (a2) — auto_learn.py và crawler.py — 0% test, gọi LLM + ghi file không có gate §B8
  - file: `agent/auto_learn.py`
  - auto_learn.py:43-47 tạo OpenAI client ở import-time, không check AUTONOMOUS_AGENT_ENABLED. Không có file test nào trong agent/tests/ hay tests/ import hoặc test auto_learn.py hoặc crawler.py. §B8 CLAUDE.md: 'agent tự gọi LLM CHỈ khi đủ 3 điều kiện (opt-in, cap, kill-switch)'. tes
  - FIX: Tách logic thuần (không-LLM) ra khỏi auto_learn.py và crawler.py để có thể test: hàm _extract_entities_from_text(raw_html, ...) → dict không gọi LLM; hàm _is_duplicate(entity, existing) → bool thuần.

- **TC-09** [Test coverage blind-spot] (a2) — test_knowledge.py (tests/) dùng real DB — không isolate, dễ flaky khi data thay đổi
  - file: `tests/test_knowledge.py`
  - tests/test_knowledge.py:6-15: `if not knowledge._entities or len(knowledge._entities) < 100: knowledge.reload()` — nạp DB thật. test_search_entities_by_area (dòng 59-64): `assert place.get('area') == 'vinh-long'` — pass chỉ khi entity sample có area đúng. Nếu area bị fix (audit f
  - FIX: Tách tests/test_knowledge.py thành 2 class: TestKnowledgeUnit (dùng monkeypatch inject sample data cô lập, không gọi reload) và TestKnowledgeSmokeRealDB (mark slow, chỉ assert data có vẻ hợp lệ với th

- **TC-10** [Test coverage blind-spot] (a2) — _build_messages() và _run_agent_orchestrated() trong server.py — 0 test đường dẫn lỗi
  - file: `agent/server.py`
  - server.py:1100 _build_messages() và server.py (orchestrator path) _run_agent_orchestrated() — chỉ được test qua test_chat_smoke.py với mock LLM trả lời thẳng (finish_reason='stop', tool_calls=None). Các nhánh không được test: (a) tool call loop (LLM trả tool_calls != None → call_
  - FIX: Thêm vào agent/tests/test_chat_smoke.py: (1) test_chat_with_tool_call_loop — mock LLM lần 1 trả tool_calls=[search(...)], lần 2 trả content đầy đủ; assert reply không rỗng và tools_used chứa 'search'.

---

## AUDIT-3 (scan-only, verify fail do session-limit — CHƯA verify, cần soi lại)

- **UGC/Auth/Social**: §1.3 503 đúng, opaque hashed token (không JWT), PBKDF2 password — TỐT. Nhưng 4 lỗ hổng high/crit + 6 med/low (cần verify lại).
- **Image/R2**: MIME trust không magic-byte, SSRF trên approve endpoint, direct-publish bỏ qua backup+review, license hardcode. §B6 KHÔNG re-host (tốt). [.env-leak = GIẢ, đã verify]
- **GĐ6**: federation/a2a/advanced_graph/agent_relay/streaming_tools KHÔNG TỒN TẠI (chỉ dead-ref trong startup log → nên xoá log). Module thật: orchestrator+parallel_tools (giữ), agentic_rag (perf O(n)+BFS), dynamic_agents (POST create no-auth dev), bot_gateway (session in-memory).
- **Scheduler**: SCHEDULER_ENABLED=True default nhưng autonomous tasks gated OFF (§B8 OK). Vấn đề: autonomous-agent enabled=True default; cache-warmup/guardrails-cleanup always-on không document; CLI --once bỏ qua flag; middleware spawn daemon thread import-time.

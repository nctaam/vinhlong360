# vinhlong360 — ROADMAP thực thi tự động

> **Cách dùng (đọc kỹ trước khi làm):** Tuân thủ `../CLAUDE.md`. Làm task **đúng thứ tự**. Mỗi task: thực hiện → chạy *Verify* → đạt *Nghiệm thu* mới tick `[x]` và commit. Cuối mỗi Giai đoạn phải pass **Cổng DoD** mới sang giai đoạn sau. Gặp mục 🛑 (Track-H) hoặc tình huống trong §4 CLAUDE.md → **DỪNG, hỏi người**.

**Ký hiệu:** `[ ]` chưa làm · `[x]` xong · `[~]` đang làm · `[!]` bị chặn (ghi lý do) · 🛑 cần người.

**Trạng thái bất biến (luôn đúng):** B1 snapshot trước data-op · B2 additive-first · B3 test trước vùng mù · B6 không re-host bản quyền · B8 free-tier.

---

## TRACK-H — Việc cần CON NGƯỜI (chạy song song, KHÔNG tự làm)

Những việc này **chặn ra mắt công khai** nhưng nằm ngoài code. Claude Code chỉ **nhắc + chuẩn bị tài liệu**, không tự thực hiện:

- 🛑 **H1. Pháp nhân + đăng ký NĐ147/2024** (Giấy xác nhận thông báo, hoặc Giấy phép MXH nếu ≥10k lượt/tháng hoặc >1k user thường xuyên). Cần doanh nghiệp/tổ chức VN; cá nhân thường không đứng tên được. **Đây là blocker launch lớn nhất.**
- 🛑 **H2. Luật sư ICT/dữ liệu** rà: phân loại "MXH + trang tổng hợp" kết hợp; nghĩa vụ chuyển dữ liệu xuyên biên khi host nước ngoài.
- 🛑 **H3. Cung cấp URL remote git** (để push) + quyết định nơi host (ưu tiên VN cho PDPL).
- 🛑 **H4. Rotate/đặt giá trị secret thật** (`ADMIN_API_KEY`, `LLM_API_KEY`, `TELEGRAM_BOT_TOKEN`) — con người đặt giá trị, Claude chỉ chuẩn bị chỗ.
- 🛑 **H5. Mua domain / DNS / verify Search Console (DNS TXT) / deploy public.**

---

## GIAI ĐOẠN 0 — Lưới an toàn (không đổi hành vi sản phẩm)

**Mục tiêu:** dựng version control + backup + chặn chảy tiền + khoá lệnh phá dữ liệu. **Tiên quyết:** không.

- [x] **0.1** `git init` (local). Kiểm `.gitignore` (đã có) loại: `node_modules`, `.env`, `*.log`, `tmp_*`, `prov_*`, `out_*`, `so_*`, `result_temp.json`, `provisional_*`, `__pycache__`, `.nuxt`, `.output`, `dist`, `agent/data/*.db`, `agent/data/embeddings.json`, `scratch/`. → *Verify:* `git status` không liệt kê các file rác/secret trên. *Nghiệm thu:* repo init, `.env` không bị track.
- [x] **0.2** Tạo `scratch/` và **di chuyển** (`git mv`/move, không xoá) ~69 file rác root (`tmp_*.json`,`prov_*.json`,`out_*.json`,`so_*.json`,`provisional_*.json`,`result_temp.json`,`top200_output.json`,`server_*.log`) vào `scratch/`. → *Verify:* `ls *.json *.log` ở root ≈ rỗng (trừ file cấu hình). *Nghiệm thu:* root sạch, không mất file.
- [x] **0.3** Tạo `scripts/backup_data.py`: snapshot `web/data.json` + dump bảng KB của DB ra `scratch/backups/<timestamp>/`. → *Verify:* chạy `python scripts/backup_data.py` tạo thư mục có file. *Nghiệm thu:* phục hồi được từ snapshot.
- [x] **0.4** Đặt `SCHEDULER_ENABLE_AUTONOMOUS_TASKS=false` trong `.env` (xem `scheduler.py:436`). → *Verify:* khởi động server, log không spawn job `auto-learn/learning-loop/continuous-discovery`. *Nghiệm thu:* không có vòng lặp gọi LLM nền.
- [x] **0.5** Khoá tạm 3 endpoint phá dữ liệu cho tới hết GĐ3: `POST /reload`, `POST /admin/data-quality/apply|rollback`, và thêm guard cho `database.py --replace`. Cách: trả 423/403 + log cảnh báo (chưa xoá code). (xem `server.py:2110`, `admin.py:365`, `database.py:736`). → *Verify:* gọi `/reload` trả mã chặn. *Nghiệm thu:* không thể vô tình xoá edit.
- [ ] 🛑 **0.6** (Track-H) Báo người: cấu trúc commit đầu đã sẵn — **chờ H3 (remote URL)** để push; **chờ H4** để rotate secret. KHÔNG tự push/đổi secret.

**🚦 Cổng DoD-0:** `git log` có commit; `python scripts/backup_data.py` chạy được; server khởi động không có job LLM nền; `/reload` bị chặn; `python -m pytest -q` xanh (baseline).

---

## GIAI ĐOẠN 1 — Test cho vùng mù (chạy SỚM, song song GĐ0→2)

**Mục tiêu:** bọc test các module sắp bị sửa nặng (bất biến B3). **Tiên quyết:** GĐ0.1.

- [x] **1.1** Viết `agent/tests/test_database.py`: getter/filter, `replace_from_json`, round-trip schema, đếm cạnh in/out. (Module hiện 0%.) → *Verify:* `pytest agent/tests/test_database.py -q` xanh. *Nghiệm thu:* phủ các hàm GĐ3 sẽ sửa.
- [x] **1.2** Bật CI thật: sửa `.github/workflows/ci.yml` chạy **cả `tests/` và `agent/tests/`** và **bỏ loại trừ `integration`** cho test `/chat`. → *Verify:* `act`/đọc workflow xác nhận lệnh pytest bao gồm cả 2 thư mục. *Nghiệm thu:* CI cấu hình đúng (sẽ gate khi có remote — H3).
- [x] **1.3** Thêm test integration "smoke" cho `/chat` (mock LLM) kiểm: trả 200, có trả lời, không 500 khi thiếu arg tool. → *Verify:* `pytest -m integration -q` xanh. *Nghiệm thu:* bắt được regression chat handler.

**🚦 Cổng DoD-1:** test_database + chat-smoke xanh; CI chạy cả 2 thư mục test.

---

## GIAI ĐOẠN 2 — Dọn dữ liệu near (trước khi vào DB)

**Mục tiêu:** 44k→~10k cạnh sạch. **Tiên quyết:** DoD-0 (backup). **Bất biến:** B1 chạy backup trước.

- [x] **2.1** `python scripts/backup_data.py` (B1). → *Nghiệm thu:* có snapshot mới.
- [x] **2.2** `python scripts/normalize_data.py --regenerate-near` (logic `normalize_data.py:216`). → *Verify:* đếm relationship. *Nghiệm thu:* `near` còn ~5k cạnh, mọi cạnh ≤50km & cùng area & cap fanout.
- [x] **2.3** Sửa ~63 toạ độ ngoài bbox 9–11°N/105–107°E (geocode lại hoặc bỏ toạ độ sai). → *Verify:* `validate_data.py` mục `out_of_bounds_coordinates`=0. *Nghiệm thu:* không còn toạ độ lệch vùng.
- [x] **2.4** `python scripts/validate_data.py`. → *Nghiệm thu:* hết ERROR `near_missing_location`/`far_near_relationships`; `relationship_fanout` trong ngưỡng.

**🚦 Cổng DoD-2:** relationship ~10k; validator không còn ERROR về near/geocode; snapshot trước-sau lưu ở scratch.

---

## GIAI ĐOẠN 3 — DB là nguồn sự thật (BẢN LỀ — cẩn thận nhất)

**Mục tiêu:** gỡ split-brain. **Tiên quyết:** DoD-1 (test_database) + DoD-2. **Bất biến:** B1, B3.

- [!] **3.1** (HOÃN — xem Backlog: UGC/auth PG-specific, ngoài đường chat) Thêm bảng còn thiếu cho SQLite trong `database.py` (`users/posts/comments/notifications/follows/reviews`) đồng bộ DDL với `init.sql`. → *Verify:* test_database + chạy local đăng ký/đăng bài không `OperationalError`. *Nghiệm thu:* UGC/login chạy ở SQLite dev.
- [x] **3.2** Sửa `replace_from_json` không mất cạnh (log số in/out, fail nếu lệch bất thường); mở rộng cột import để không rớt field (`database.py:757`). → *Verify:* import xong đếm = nguồn. *Nghiệm thu:* migrate không mất mát.
- [x] **3.3** B1 backup → migrate `web/data.json (đã sạch) → DB` (`database.py --replace` + `ALLOW_DESTRUCTIVE_DB_REPLACE=1`). Reconcile lệch 1703 vs 1693 (giữ tập giàu hơn). → *Verify:* đếm entity/rel trong DB = data.json. *Nghiệm thu:* DB khớp data.json sạch.
- [x] **3.4** Thêm bulk getter `db.all_entities()/all_relationships()/all_itineraries()` nếu chưa có. → *Verify:* unit test getter. *Nghiệm thu:* lấy toàn bộ từ DB.
- [x] **3.5** Viết lại `knowledge._ensure()`/`reload()` đọc từ DB → dựng **cùng cấu trúc in-memory** `_entities/_relationships/_itineraries` (`knowledge.py:46,54`). Tool/search/agent KHÔNG đổi interface. → *Verify:* `pytest agent/tests/test_knowledge.py -q` xanh; chat trả lời như trước. *Nghiệm thu:* chat nạp từ DB, tốc độ không đổi.
- [x] **3.6** Admin write-through: sau CRUD (`admin.py:248,263`) gọi `knowledge.reload()`. → *Verify:* sửa 1 entity ở admin → hỏi chat thấy ngay + `/api/entities` thấy ngay. *Nghiệm thu:* **split-brain biến mất** (test integration).
- [x] **3.7** `export_data.py`: chiều DB→`web/data.json` (backup + nguồn prerender). `auto_learn.py --apply` ghi DB thay vì append json (`auto_learn.py:649`). → *Verify:* export rồi `validate_data.py` xanh. *Nghiệm thu:* data.json là export, không còn là nguồn.
- [~] **3.8** (MỘT PHẦN) ✅ `/reload` mở khoá + auth (reload từ DB, an toàn). ⏸ `database.py --replace` + `/admin/data-quality/apply` VẪN khoá `DESTRUCTIVE_OPS_LOCKED=1` — cần rework DB-native (Backlog) trước khi gỡ. → *Verify:* `/reload` cần admin key (test xanh).

**🚦 Cổng DoD-3:** Sửa entity ở admin phản ánh ở **cả chat lẫn /api** (test integration xanh); restart vẫn còn; `export_data.py`→`validate_data.py` xanh; test_database xanh. **Sau cổng này mới được bỏ khoá tạm GĐ0.5.**

---

## GIAI ĐOẠN 4 — Concurrency · Chi phí · Bảo mật · Chất lượng chat

**Mục tiêu:** mở đồng thời, chặn rò tiền, vá bảo mật, đo chất lượng. **Tiên quyết:** DoD-3.

- [ ] **4.1** Bọc `await asyncio.to_thread(_run_agent_orchestrated,...)` ở `/chat` (`server.py:1539`) + bridge stream (`:1929,1974`). → *Verify:* 2 request /chat đồng thời + `/health` không bị chặn (đo). *Nghiệm thu:* concurrency >1.
- [ ] **4.2** Auth + rate-limit cho `/image/recognize` (`server.py:2703`), `/reload`, `/vectors/build`. → *Verify:* gọi thiếu auth trả 401/403. *Nghiệm thu:* hết endpoint LLM/heavy vô danh.
- [ ] **4.3** Bỏ auto-fire LLM ở frontend: `AITravelTips`/`AIBestTime` chỉ gọi `/chat` khi user bấm "xem"; debounce `AISearchAssist` (`AITravelTips.vue:32`,`AIBestTime.vue:15`,`AISearchAssist.vue:31`). → *Verify:* mở trang chi tiết, network tab **không** có call `/chat` tự động. *Nghiệm thu:* cắt ~70% chi phí LLM.
- [ ] **4.4** `LLM_MODEL_MINI` trỏ model rẻ thật; hạ `max_rounds` mặc định; sample hoặc tắt `llm_judge` hot path (`server.py:1738`). → *Verify:* đếm LLM call/chat điển hình ≤2. *Nghiệm thu:* chi phí/chat giảm.
- [ ] **4.5** Sửa guardrail `except: pass` (im lặng nuốt lỗi) ở output check (`server.py:1764`, `guardrails.py`); đưa entity `type:"place"`/quán vào `search_entities` (`knowledge.py:181`). → *Verify:* hỏi "quán ăn ngon ở…" trả kết quả. *Nghiệm thu:* hết recall gap nhà hàng; guardrail không nuốt lỗi.
- [ ] **4.6** Chạy baseline chất lượng: `python agent/run_eval.py --quick` rồi `python agent/run_eval.py`. → *Verify:* có file `agent/data/eval/eval-*.json`. *Nghiệm thu:* có điểm baseline (avg_score, theo category) lưu lại.
- [ ] **4.7** Escape HTML cho UGC `content` khi lưu (`social.py:37`); ẩn `/system/*`,`/analytics/*`,`/metrics`,`/docs`,`/redoc` ở production; rate-limit theo IP cho `/auth/request-otp` (`auth.py:130`). → *Verify:* nội dung `<script>` lưu ra bị escape; `/docs` 404 ở prod-mode. *Nghiệm thu:* hết stored-XSS + lộ nội bộ + SMS-pump.

**🚦 Cổng DoD-4:** concurrency>1; không call LLM tự động khi load trang; có eval baseline; endpoint nhạy có auth; `pytest -q` xanh.

---

## GIAI ĐOẠN 5 — Compliance (phần CODE; phần pháp nhân = Track-H)

**Mục tiêu:** điều kiện pháp lý tối thiểu để có thể ra mắt. **Tiên quyết:** DoD-3. **Lưu ý:** H1/H2 chạy song song; code xong vẫn KHÔNG launch tới khi H1 xong.

- [ ] **5.1** Thêm 3 trang Nuxt tiếng Việt: `/chinh-sach-bao-mat` (privacy), `/dieu-khoan-su-dung` (terms), `/lien-he` (contact + kênh báo vi phạm). → *Verify:* `npm run build` OK, 3 route render. *Nghiệm thu:* có nội dung: dữ liệu thu thập (SĐT, tên, vị trí, bài đăng), mục đích, lưu trữ, quyền chủ thể.
- [ ] **5.2** Consent lúc đăng ký: checkbox **không tick sẵn** + link privacy; lưu timestamp + version theo user (`auth.py`). → *Verify:* không tick → không tạo tài khoản; có log consent. *Nghiệm thu:* đáp ứng PDPL consent.
- [ ] **5.3** Gate đăng bài/bình luận bằng OTP đã verify (không chỉ login) (`social.py`). → *Verify:* user chưa verify không POST được. *Nghiệm thu:* real-name verification NĐ147.
- [ ] **5.4** Nút "Báo cáo" trên nội dung UGC + hàng đợi admin gỡ; đảm bảo gỡ được trong **24h/48h**. → *Verify:* report → xuất hiện ở admin → gỡ ẩn nội dung. *Nghiệm thu:* năng lực takedown NĐ147.
- [ ] **5.5** Luồng "Xoá tài khoản & dữ liệu" (UI hoặc form/email handler), đáp ứng hạn 10/15/20 ngày. → *Verify:* yêu cầu xoá → dữ liệu user bị xoá/ẩn. *Nghiệm thu:* quyền xoá + rút consent.
- [ ] **5.6** Đổi crawler/import: lưu **tiêu đề + trích đoạn ngắn + link gốc**, không nguyên văn/ảnh; hiển thị nguồn (`crawler.py`, `import_*.py`). → *Verify:* bản ghi mới không chứa full-text/ảnh re-host. *Nghiệm thu:* hạ rủi ro bản quyền (B6).
- [ ] **5.7** Viết `docs/incident-runbook.md` 1 trang (đồng hồ 72h báo MPS khi rò rỉ). → *Nghiệm thu:* có runbook.
- [ ] 🛑 **5.8** (Track-H) Báo người: code compliance xong; **chờ H1 (pháp nhân/NĐ147) + H2 (luật sư)** trước khi mở công khai.

**🚦 Cổng DoD-5:** 3 trang pháp lý + consent + gate-posting + report/takedown + xoá-tài-khoản hoạt động; crawler chỉ lưu trích đoạn. (Launch vẫn chờ H1.)

---

## GIAI ĐOẠN 6 — Giảm tải backend (đúng "no heavy features")

**Tiên quyết:** DoD-4.

- [ ] **6.1** Xoá module dead-weight + test tương ứng: `federation`, `a2a_protocol`, `advanced_graph`, `agent_relay`, `streaming_tools`, `multimodal_engine`, `eval_framework`(giữ run_eval/retrieval_eval nếu dùng), `knowledge_evolution`; gỡ import + `HAS_*` + endpoint `/a2a`,`/system/federation/*`. → *Verify:* `python -c "import server"` OK; `pytest -q` xanh. *Nghiệm thu:* server chạy, LOC giảm.
- [ ] **6.2** Log WARNING khi import optional fail (`server.py:79-282`) + field `/health` liệt kê tính năng tắt. → *Nghiệm thu:* không còn tắt tính năng im lặng.
- [ ] **6.3** Sửa metadata sai `server.py:814` (tính từ `len(knowledge._entities)` runtime). → *Verify:* `/` hiển thị số đúng. *Nghiệm thu:* hết "327 entities".

**🚦 Cổng DoD-6:** server import & test xanh sau khi xoá; `/health` liệt kê tính năng tắt.

---

## GIAI ĐOẠN 7 — Gom về một frontend

**Tiên quyết:** DoD-3 (data.json là export). **Bất biến:** B2 (verify mới xoá).

- [ ] **7.1** Backend serve `GET /api/constants` (TYPE_META/AREA_META/REL labels/season). → *Verify:* trả JSON đủ 15 type + nhãn quan hệ. *Nghiệm thu:* một nguồn constants.
- [ ] **7.2** Nuxt fetch `/api/constants`, xoá bản TYPE_META nhân đôi trong `composables/useConstants.ts`; bổ sung type thiếu (`drink`,`itinerary`) + nhãn `related_to`/`associated_with`. → *Verify:* trang chi tiết hiện đúng nhãn (không chữ Anh thô). *Nghiệm thu:* thêm type mới chỉ sửa DB.
- [ ] **7.3** Dời `web/data.json` → `agent/data/data.json`; sửa tham chiếu (`knowledge.py:13`,`database.py:953`,`scheduler.py:88`). → *Verify:* server khởi động đọc đúng path. *Nghiệm thu:* data ra khỏi `web/`.
- [ ] **7.4** Sau khi 7.1-7.3 verify: **xoá `web-astro/`**; bỏ JS/HTML legacy trong `web/` (giữ admin dashboard nếu Nuxt admin chưa thay thế). → *Verify:* grep không còn ai import `web/store.js`/`web/data.js`; `npm run build` OK. *Nghiệm thu:* còn 1 frontend.
- [ ] **7.5** Gỡ field shim legacy (`coords`,`from`/`to`) khi không còn consumer legacy. → *Verify:* test + build xanh. *Nghiệm thu:* chỉ còn canonical.

**🚦 Cổng DoD-7:** `npm run build` xanh; chỉ còn `web-nuxt`; thêm 1 type test bằng cách đổi DB → UI tự nhận.

---

## GIAI ĐOẠN 8 — Hình ảnh / media

**Tiên quyết:** DoD-3. **Bất biến:** B6 (bản quyền), B8 (free-tier).

- [ ] **8.1** Cấu hình object storage **Cloudflare R2** qua `storage.py` (S3 endpoint/keys). → *Verify:* upload thử 1 ảnh trả URL. *Nghiệm thu:* lưu ảnh ~0đ.
- [ ] **8.2** Script ingest: Wikimedia Commons + Wikipedia summary theo `entity.name`+area → đề xuất ảnh cover; lưu kèm `image_credits` (CC attribution). **Chỉ nguồn cấp phép.** → *Verify:* chạy thử N entity nổi tiếng có ảnh + credit. *Nghiệm thu:* không dùng ảnh cào bản quyền (B6).
- [ ] **8.3** Pipeline tối ưu: Pillow → WebP 3 cỡ (400/800/1600), strip EXIF, tên file theo slug; ghi vào `entity["images"]`. → *Verify:* ảnh hiển thị responsive. *Nghiệm thu:* ảnh nhẹ, CLS ổn.
- [ ] **8.4** Endpoint admin **upload file** cho ảnh entity (hiện chỉ URL — `admin.py:430`) + duyệt ảnh UGC gắn vào entity. → *Nghiệm thu:* admin tự thêm ảnh.
- [ ] **8.5** SEO ảnh: `og:image` mặc định toàn site + override per-entity; nâng `image` → `ImageObject` (license) ở `seo.py:226` & `dia-diem/[id].vue:394`; **hiện thực image sitemap** (`seo.py:86` đang dead). Cập nhật `docs/api-contract.md` thêm `images`. → *Verify:* share preview có ảnh; sitemap ảnh hợp lệ. *Nghiệm thu:* ảnh được index.

**🚦 Cổng DoD-8:** ≥ vài trăm entity nổi bật có ảnh hợp lệ + credit; og:image hoạt động; image sitemap hợp lệ; không ảnh vi phạm bản quyền.

---

## GIAI ĐOẠN 9 — Observability (free-tier)

**Tiên quyết:** DoD-3. **Lưu ý:** chọn analytics **cookieless** để né consent-banner (PDPL).

- [ ] **9.1** Uptime: cấu hình UptimeRobot/BetterStack trỏ `/health` (keyword `"status":"ok"`) + `/health/deep` tần suất thấp; alert về **Telegram bot** (`TELEGRAM_BOT_TOKEN`). → *Nghiệm thu:* có alert khi tắt server (test). (🛑 nếu cần tài khoản/đăng ký dịch vụ → hỏi người.)
- [ ] 🛑 **9.2** (Track-H) Google Search Console: verify **DNS TXT** (cần H5) → submit `sitemap.xml` đang chạy. Claude chuẩn bị hướng dẫn; người thực hiện verify.
- [ ] **9.3** Web analytics **cookieless self-host** (Umami/Plausible CE) — thêm container dùng Postgres sẵn có; nhúng script vào `nuxt.config.ts` head. → *Verify:* pageview ghi nhận. *Nghiệm thu:* không cần cookie-banner.
- [ ] **9.4** Error tracking: hook `sentry_sdk.capture_exception()` vào `ErrorTracker.record_error` (`middleware.py:289`) + `@sentry/nuxt`. Dùng Sentry free hoặc GlitchTip self-host. → *Verify:* gây 1 lỗi test → thấy trong dashboard. *Nghiệm thu:* lỗi FE+BE được bắt.
- [ ] **9.5** Sửa cost dùng **token thật**: gọi `track_llm_call()` (`cost_tracker.py:443`) thay vì ước lượng (`server.py:1668`). → *Verify:* `/system/costs` khớp usage thật. *Nghiệm thu:* đo được ngân sách.
- [ ] **9.6** Trang admin **Analytics** (clone `ai.vue`) hiện `/analytics/popular`,`/analytics/gaps`,`/system/costs`. → *Nghiệm thu:* solo dev thấy "user hỏi gì / bí ở đâu / tốn bao nhiêu".

**🚦 Cổng DoD-9:** uptime alert chạy; analytics ghi nhận; lỗi được track; cost chính xác; trang Analytics hiển thị knowledge-gaps.

---

## GIAI ĐOẠN 10 — Tối ưu frontend (CWV/SEO dài hạn)

**Tiên quyết:** DoD-7, DoD-8.

- [ ] **10.1** Hybrid rendering: route rules Nuxt prerender trang chi tiết/danh mục/itinerary (nguồn = export DB→json), SSR trang động (search/map/cá nhân). → *Verify:* trang chi tiết có HTML tĩnh; Lighthouse LCP cải thiện. *Nghiệm thu:* CWV tốt hơn.
- [ ] **10.2** Bản đồ: GeoJSON source + clustering native maplibre thay 700 DOM marker (`ban-do.vue:124`). → *Verify:* map mượt với toàn bộ entity trên mobile. *Nghiệm thu:* hết jank.
- [ ] **10.3** A11y `AuthModal`: `role="dialog"`+focus-trap+Esc+aria-label OTP; sửa clickable `<div>`→`<button>`. → *Verify:* keyboard điều hướng được. *Nghiệm thu:* WCAG cơ bản.
- [ ] **10.4** Dọn: xoá `composables/useApi.ts` (chết), gom `normalizeCoords` trùng, sửa mojibake admin, siết `any`. → *Verify:* build + typecheck. *Nghiệm thu:* sạch.

**🚦 Cổng DoD-10:** build xanh; Lighthouse CWV (LCP≤2.5s/INP≤200ms/CLS≤0.1) đạt "Good" trên trang chi tiết & danh mục.

---

## GIAI ĐOẠN 11 — Hiệu năng backend

**Tiên quyết:** DoD-3.

- [ ] **11.1** Sparse-vector TF-IDF (`vector_search.py`): lưu vector thưa thay vì dày 31761 chiều → embeddings vài MB, RAM giảm; đồng bộ entity thiếu vector. → *Verify:* kích thước file + RAM giảm; recall không tụt. *Nghiệm thu:* nhẹ hơn.
- [ ] **11.2** Index kề `dict[entity_id]→edges` cho `related()` (`knowledge.py:276`). → *Verify:* không còn quét tuyến tính/edge. *Nghiệm thu:* `entity_detail` nhanh hơn.
- [ ] **11.3** Precompute BM25/contextual tokens lúc build index (`contextual_retrieval.py:311,534`). → *Nghiệm thu:* search nhanh hơn.
- [ ] **11.4** `/reload` chạy nền + swap global atomic có khoá (`knowledge.py:54`). → *Verify:* reload không đóng băng `/health`. *Nghiệm thu:* reload an toàn.

**🚦 Cổng DoD-11:** thời gian /chat & RSS giảm rõ; reload không chặn; test xanh.

---

## GIAI ĐOẠN 12 — Sản phẩm: wedge "bản đồ trải nghiệm theo mùa"

**Tiên quyết:** DoD-3, DoD-8.

- [ ] **12.1** Backfill `season` cho phần lớn 90 experience + 113 dish (hiện chỉ 8 experience có cửa sổ thật) — nguồn kiểm chứng được. → *Verify:* đếm entity có `season.peak` thật tăng mạnh. *Nghiệm thu:* wedge "có cảm giác đầy".
- [ ] **12.2** Bổ sung provenance thật: thay dần 471 entity tự-trích vinhlong360.vn bằng nguồn ngoài. → *Nghiệm thu:* tỉ lệ URL nguồn ngoài tăng.
- [ ] **12.3** Trang "Tháng này đi đâu/ăn gì" dùng `season` + relevance scoring đã có. → *Verify:* chọn tháng → hiện trải nghiệm/đặc sản đúng mùa. *Nghiệm thu:* wedge chạy.

**🚦 Cổng DoD-12:** trang theo mùa hiển thị đủ nội dung thật theo tháng.

---

## VERIFY TỔNG THỂ (sau toàn bộ)

- [ ] Sửa entity ở admin → phản ánh ngay ở **cả** chat lẫn Nuxt.
- [ ] `validate_data.py` sạch; relationship ~10k.
- [ ] 2+ /chat đồng thời không chặn nhau; endpoint nhạy có auth; không call LLM tự động khi load trang.
- [ ] Chỉ còn 1 frontend; thêm type mới không phải sửa nhiều nơi.
- [ ] Entity nổi bật có ảnh; og:image + image sitemap hoạt động.
- [ ] Uptime/analytics/error/cost đo được; eval baseline có điểm.
- [ ] 3 trang pháp lý + consent + report/takedown + xoá tài khoản hoạt động; crawler chỉ trích đoạn.
- [ ] CWV "Good"; CI xanh chạy cả agent/tests + integration.
- [ ] **Launch công khai CHỈ sau khi H1 (NĐ147) + H2 (luật sư) hoàn tất.**

---

## BACKLOG PHÁT SINH (ghi việc ngoài roadmap — KHÔNG tự làm, chờ duyệt)

> Khi phát hiện việc đáng làm ngoài roadmap, ghi vào đây kèm ngày + lý do, rồi tiếp tục task hiện tại.

- **(2026-06-13) GĐ3.1 — UGC/auth → SQLite**: tách khỏi GĐ3. `users/posts/comments/...` + method `create_user`/`get_user_by_id`/`social.py` dùng cú pháp PG (`UUID`, `RETURNING`, `id::text`, `NOW()`). Port sang SQLite là việc lớn, rủi ro cao (sai 1 DDL → `db.initialize()` vỡ toàn hệ), NẰM NGOÀI đường chat/entity. Theo `architecture-decisions.md #3` (SQLite=dev cache, Postgres=primary), UGC nên chạy trên Postgres. Quyết định: hoặc (a) port có test riêng, hoặc (b) chấp nhận UGC chỉ chạy trên Postgres + tài liệu hoá "dev UGC cần docker postgres". Test `test_users_table_exists_after_gd31` đang xfail đánh dấu việc này.
- **(2026-06-13) GĐ3.8 (phần còn lại) — data-quality DB-native**: `/admin/data-quality/apply|rollback` vẫn DELETE-rồi-nạp-từ-data.json → sẽ xoá edit admin trong DB. Cần rework thao tác THẲNG trên DB (không qua data.json) + test, rồi mới gỡ `DESTRUCTIVE_OPS_LOCKED` cho nhóm này. Hiện vẫn KHOÁ (an toàn). `/reload` đã mở + auth.

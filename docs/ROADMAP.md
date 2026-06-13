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

- [x] **3.1** (QUYẾT ĐỊNH: UGC/auth = **Postgres-only**, KHÔNG port SQLite — dev/prod parity. SQLite→503 rõ ràng; dev UGC dùng docker postgres. Đã enact: `_require_pg` trên 3 router + test 503.) ~~Thêm bảng còn thiếu cho SQLite trong~~ `database.py` (`users/posts/comments/notifications/follows/reviews`) đồng bộ DDL với `init.sql`. → *Verify:* test_database + chạy local đăng ký/đăng bài không `OperationalError`. *Nghiệm thu:* UGC/login chạy ở SQLite dev.
- [x] **3.2** Sửa `replace_from_json` không mất cạnh (log số in/out, fail nếu lệch bất thường); mở rộng cột import để không rớt field (`database.py:757`). → *Verify:* import xong đếm = nguồn. *Nghiệm thu:* migrate không mất mát.
- [x] **3.3** B1 backup → migrate `web/data.json (đã sạch) → DB` (`database.py --replace` + `ALLOW_DESTRUCTIVE_DB_REPLACE=1`). Reconcile lệch 1703 vs 1693 (giữ tập giàu hơn). → *Verify:* đếm entity/rel trong DB = data.json. *Nghiệm thu:* DB khớp data.json sạch.
- [x] **3.4** Thêm bulk getter `db.all_entities()/all_relationships()/all_itineraries()` nếu chưa có. → *Verify:* unit test getter. *Nghiệm thu:* lấy toàn bộ từ DB.
- [x] **3.5** Viết lại `knowledge._ensure()`/`reload()` đọc từ DB → dựng **cùng cấu trúc in-memory** `_entities/_relationships/_itineraries` (`knowledge.py:46,54`). Tool/search/agent KHÔNG đổi interface. → *Verify:* `pytest agent/tests/test_knowledge.py -q` xanh; chat trả lời như trước. *Nghiệm thu:* chat nạp từ DB, tốc độ không đổi.
- [x] **3.6** Admin write-through: sau CRUD (`admin.py:248,263`) gọi `knowledge.reload()`. → *Verify:* sửa 1 entity ở admin → hỏi chat thấy ngay + `/api/entities` thấy ngay. *Nghiệm thu:* **split-brain biến mất** (test integration).
- [x] **3.7** `export_data.py`: chiều DB→`web/data.json` (backup + nguồn prerender). `auto_learn.py --apply` ghi DB thay vì append json (`auto_learn.py:649`). → *Verify:* export rồi `validate_data.py` xanh. *Nghiệm thu:* data.json là export, không còn là nguồn.
- [x] **3.8** ✅ `/reload` mở khoá + auth (reload từ DB). ✅ `/admin/data-quality/apply|rollback` rework **DB-native** (ghi thẳng DB, rollback theo `before` trong history) + bỏ khoá + write-through. ⏸ Chỉ còn `database.py replace_from_json` (seed tool) giữ `DESTRUCTIVE_OPS_LOCKED=1` — đúng chủ đích. → *Verify:* test apply/rollback DB-native + /reload auth xanh.

**🚦 Cổng DoD-3:** Sửa entity ở admin phản ánh ở **cả chat lẫn /api** (test integration xanh); restart vẫn còn; `export_data.py`→`validate_data.py` xanh; test_database xanh. **Sau cổng này mới được bỏ khoá tạm GĐ0.5.**

---

## GIAI ĐOẠN 4 — Concurrency · Chi phí · Bảo mật · Chất lượng chat

**Mục tiêu:** mở đồng thời, chặn rò tiền, vá bảo mật, đo chất lượng. **Tiên quyết:** DoD-3.

- [x] **4.1** Bọc `await asyncio.to_thread(_run_agent_orchestrated,...)` ở `/chat` (`server.py:1539`) + bridge stream (`:1929,1974`). → *Verify:* 2 request /chat đồng thời + `/health` không bị chặn (đo). *Nghiệm thu:* concurrency >1.
- [x] **4.2** (admin-auth; rate-limit per-user = Backlog) Auth + rate-limit cho `/image/recognize` (`server.py:2703`), `/reload`, `/vectors/build`. → *Verify:* gọi thiếu auth trả 401/403. *Nghiệm thu:* hết endpoint LLM/heavy vô danh.
- [x] **4.3** Bỏ auto-fire LLM ở frontend: `AITravelTips`/`AIBestTime` chỉ gọi `/chat` khi user bấm "xem"; debounce `AISearchAssist` (`AITravelTips.vue:32`,`AIBestTime.vue:15`,`AISearchAssist.vue:31`). → *Verify:* mở trang chi tiết, network tab **không** có call `/chat` tự động. *Nghiệm thu:* cắt ~70% chi phí LLM.
- [x] **4.4** (judge gate + model note; hạ max_rounds = để ngỏ, tránh ảnh hưởng chất lượng) `LLM_JUDGE_ENABLED=false` mặc định (bỏ 1 lượt LLM/chat); `.env.example` ghi rõ `LLM_MODEL_MINI` đặt model rẻ. → *Verify:* đếm LLM call/chat điển hình ≤2. *Nghiệm thu:* chi phí/chat giảm.
- [x] **4.5** Sửa guardrail `except: pass` (im lặng nuốt lỗi) ở output check (`server.py:1764`, `guardrails.py`); đưa entity `type:"place"`/quán vào `search_entities` (`knowledge.py:181`). → *Verify:* hỏi "quán ăn ngon ở…" trả kết quả. *Nghiệm thu:* hết recall gap nhà hàng; guardrail không nuốt lỗi.
- [~] **4.6** (CHẶN BỞI MÔI TRƯỜNG) Chạy baseline chất lượng: `python agent/run_eval.py --quick` rồi `python agent/run_eval.py`. Harness OK (54 case load được) nhưng LLM tunnel KHÔNG reachable từ sandbox (`/health/deep`=degraded) → phải chạy ở **môi trường thật có LLM**. → *Verify:* file `agent/data/eval/eval-*.json` (chạy ở env thật).
- [x] **4.7** (✅ ẩn /docs,/redoc,/openapi ở prod; ✅ rate-limit IP /auth/request-otp 5/10ph. ✅ Escape UGC: KHÔNG cần — PostCard render {{}} (Vue auto-escape). ⏸ ẩn /system,/analytics,/metrics ở prod = Backlog (nhiều endpoint).) → *Verify:* nội dung `<script>` lưu ra bị escape; `/docs` 404 ở prod-mode. *Nghiệm thu:* hết stored-XSS + lộ nội bộ + SMS-pump.

**🚦 Cổng DoD-4:** concurrency>1; không call LLM tự động khi load trang; có eval baseline; endpoint nhạy có auth; `pytest -q` xanh.

---

## GIAI ĐOẠN 5 — Compliance (phần CODE; phần pháp nhân = Track-H)

**Mục tiêu:** điều kiện pháp lý tối thiểu để có thể ra mắt. **Tiên quyết:** DoD-3. **Lưu ý:** H1/H2 chạy song song; code xong vẫn KHÔNG launch tới khi H1 xong.

- [x] **5.1** Thêm 3 trang Nuxt tiếng Việt: `/chinh-sach-bao-mat` (privacy), `/dieu-khoan-su-dung` (terms), `/lien-he` (contact + kênh báo vi phạm). → *Verify:* `npm run build` OK, 3 route render. *Nghiệm thu:* có nội dung: dữ liệu thu thập (SĐT, tên, vị trí, bài đăng), mục đích, lưu trữ, quyền chủ thể.
- [~] **5.2** (FE gate ✅; server-log hoãn) Consent checkbox **không tick sẵn** gate nút gửi OTP + link điều khoản/bảo mật (`AuthModal.vue`). ⏸ Lưu timestamp/version consent vào DB = cần cột PG (Backlog). → *Verify:* không tick → nút disabled.
- [x] **5.3** Gate đăng bài/bình luận bằng OTP đã verify (không chỉ login) (`social.py`). → *Verify:* user chưa verify không POST được. *Nghiệm thu:* real-name verification NĐ147.
- [x] **5.4** Nút "Báo cáo" trên nội dung UGC + hàng đợi admin gỡ; đảm bảo gỡ được trong **24h/48h**. → *Verify:* report → xuất hiện ở admin → gỡ ẩn nội dung. *Nghiệm thu:* năng lực takedown NĐ147.
- [x] **5.5** Luồng "Xoá tài khoản & dữ liệu" (UI hoặc form/email handler), đáp ứng hạn 10/15/20 ngày. → *Verify:* yêu cầu xoá → dữ liệu user bị xoá/ẩn. *Nghiệm thu:* quyền xoá + rút consent.
- [ ] **5.6** (HOÃN — crawler không chạy lúc này) Đổi crawler/import: lưu **tiêu đề + trích đoạn + link gốc**, không nguyên văn/ảnh (`crawler.py`, `import_*.py`). Bản quyền (B6) — làm trước khi bật lại crawl. → Backlog.
- [x] **5.7** Viết `docs/incident-runbook.md` 1 trang (đồng hồ 72h báo MPS khi rò rỉ). → *Nghiệm thu:* có runbook.
- [ ] 🛑 **5.8** (Track-H) Báo người: code compliance xong; **chờ H1 (pháp nhân/NĐ147) + H2 (luật sư)** trước khi mở công khai.

**🚦 Cổng DoD-5:** 3 trang pháp lý + consent + gate-posting + report/takedown + xoá-tài-khoản hoạt động; crawler chỉ lưu trích đoạn. (Launch vẫn chờ H1.)

---

## GIAI ĐOẠN 6 — Giảm tải backend (đúng "no heavy features")

**Tiên quyết:** DoD-4.

- [x] **6.1** ✅ Xoá 7 module dead-weight + test (**-7508 LOC**, -203 test): `federation`, `a2a_protocol`, `advanced_graph`, `agent_relay`, `streaming_tools`, `multimodal_engine`, `knowledge_evolution`. **Giữ `eval_framework`** (run_eval/retrieval_eval dùng). Mọi usage guarded → `HAS_X=False` degrade; server+scheduler import OK; baseline 1058 passed. ⏸ Stub guarded trong server.py (endpoint Level7 trả "not available") + task scheduler (try/except, disabled) = vô hại, để Backlog (xen kẽ module giữ → phẫu thuật rủi ro).
- [x] **6.2** ✅ `/health` đã liệt kê availability từng feature (`server.py:2235-2245`). (Không log warning per-import để tránh nhiễu cho module đã chủ đích xoá.)
- [x] **6.3** ✅ Đã sửa ở GĐ4.7: genericize description (bỏ "327 entities, 2070 relationships" sai).

**🚦 Cổng DoD-6:** server import & test xanh sau khi xoá; `/health` liệt kê tính năng tắt.

---

## GIAI ĐOẠN 7 — Gom về một frontend

**Tiên quyết:** DoD-3 (data.json là export). **Bất biến:** B2 (verify mới xoá).
> ⚠️ Lưu ý số GĐ: việc "gom frontend" là **GĐ7** này (KHÔNG phải GĐ5). **GĐ5 = Compliance** (privacy/consent/report/xoá-tài-khoản) — **launch-blocker, CHƯA làm**, nên ưu tiên trước khi ra mắt.

- [~] **7.1** (HOÃN) Backend serve `GET /api/constants`. → Chưa làm: sau khi xoá astro/web copies, `useConstants.ts` là nguồn FE DUY NHẤT nên endpoint chưa có consumer. Làm khi muốn unify FE+BE (Backlog).
- [~] **7.2** (MỘT PHẦN ✅) Bổ sung type thiếu (`drink`,`itinerary`) + nhãn `related_to`/`associated_with`/`located_in`/`part_of` vào `useConstants.ts` (hết chữ Anh thô; Nuxt build OK). ⏸ Phần "Nuxt fetch /api/constants" hoãn (rủi ro refactor async — Backlog).
- [!] **7.3** (HUỶ) ~~Dời `web/data.json` → `agent/data/`~~ — SAI: `agent/data/` đã gitignore → mất seed khỏi git (trái GĐ0). **Giữ `data.json` ở `web/` (tracked seed).**
- [~] **7.4** (MỘT PHẦN) ✅ **Xoá `web-astro/`** (mồ côi; export_data bỏ ghi astro; build OK). ⏸ Bỏ JS/HTML legacy trong `web/` HOÃN — cần phối hợp `nginx.conf /legacy/` + xác nhận backend chỉ serve `web/admin*.html`. Giữ `web/data.json|data.js|admin*.html|media`.
- [ ] **7.5** (HOÃN) Gỡ field shim legacy (`coords`,`from`/`to`) — chỉ làm sau khi bỏ hẳn FE legacy `web/` (B2).

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

- [ ] **10.1** (HOÃN — cần backend chạy lúc build để prerender ~1700 trang; rủi ro, làm khi có pipeline build ổn) Hybrid rendering: route rules Nuxt prerender chi tiết/danh mục/itinerary, SSR trang động.
- [x] **10.2** (build-verify ✅; CẦN QA BROWSER) Bản đồ: GeoJSON source + clustering native maplibre thay 700 DOM marker (cluster/zoom/popup/lọc-type). ⚠️ Chưa QA browser (basemap openmap.vn cần `ndaMapKey`+mạng tile — sandbox không có) → verify ở env có key.
- [x] **10.3** ✅ A11y `AuthModal`: `role="dialog"`+aria-modal+aria-labelledby+Esc+focus-trap+auto-focus+aria-label OTP/SĐT/nút đóng. (Clickable div→button: chưa thấy div click trong AuthModal; rà toàn site = Backlog.)
- [x] **10.4** (MỘT PHẦN ✅) Xoá `composables/useApi.ts` (chết); gom `normalizeCoords`→`useCoords.ts`. ⏸ Mojibake `admin/data-quality.vue` (encoding, admin-only) + siết `any` (146 chỗ) = Backlog.

**🚦 Cổng DoD-10:** build xanh; Lighthouse CWV (LCP≤2.5s/INP≤200ms/CLS≤0.1) đạt "Good" trên trang chi tiết & danh mục.

---

## GIAI ĐOẠN 11 — Hiệu năng backend

**Tiên quyết:** DoD-3.

- [ ] **11.1** (HOÃN — rewrite lớn, file embeddings 208MB gitignored, đổi format lưu = rủi ro; không benchmark được trong sandbox) Sparse-vector TF-IDF. → Backlog.
- [x] **11.2** ✅ Index kề `_get_adjacency()` cho `related()` (self-healing khi `_relationships` đổi). Verify: adjacency == brute-force trên entity nhiều cạnh. `entity_detail`/`nearby` (hot path) O(degree).
- [x] **11.3** ✅ Precompute BM25 `_doc_tf` lúc build (bỏ `Counter()` mỗi doc mỗi query). 58 test contextual/vector xanh (điểm không đổi). (Contextual re-tokenize 534: BM25 đã xử lý phần nặng nhất.)
- [ ] **11.4** (HOÃN — atomic swap đa-global cần refactor single-container đụng `server.py` đọc `knowledge._entities`; rủi ro lan rộng, lợi ích thấp ở tần suất reload-admin) → Backlog.

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

- ~~(2026-06-13) GĐ3.1 — UGC/auth → SQLite~~ ✅ ĐÃ QUYẾT (Postgres-only): không port; `_require_pg` gắn 3 router UGC trả 503 trên SQLite; tài liệu CLAUDE.md §1.3 + docs/ugc-postgres.md. Lý do: dev/prod parity, tránh nợ 2 phương ngữ SQL, UGC vốn cần Postgres.
- ~~(2026-06-13) GĐ3.8 — data-quality DB-native~~ ✅ XONG (commit 35ff28e): apply/rollback ghi thẳng DB, bỏ khoá. Footgun "xoá edit admin" đã gỡ.
- **(2026-06-13) GĐ11 phần còn lại — chưa làm**: (a) 11.1 sparse-vector TF-IDF (giảm embeddings 208MB→vài MB; rewrite lớn, cần benchmark); (b) 11.4 `/reload` nền + atomic swap (cần single-container refactor đụng server.py).
- **(2026-06-13) GĐ10 phần còn lại — chưa làm**: (a) 10.1 hybrid prerender (cần pipeline build có backend); (b) QA browser map clustering (env có ndaMapKey); (c) sửa mojibake `admin/data-quality.vue`; (d) siết `any` (146 chỗ); (e) rà clickable `<div>` toàn site → `<button>`.
- **(2026-06-13) GĐ6 stub — chưa dọn**: endpoint Level7 trong `server.py` (relay/streaming/advanced-graph/a2a/knowledge-evo/multimodal/federation — đều guarded `HAS_X=False`, trả "not available") + import try/except + startup prints + 2 task scheduler (try/except, disabled). Vô hại; xen kẽ module GIỮ nên cần phẫu thuật cẩn thận. Dọn khi rảnh.
- **(2026-06-13) GĐ5 phần còn lại — chưa làm**: (a) lưu timestamp/version consent vào DB (cột PG ở `users`); (b) GĐ5.6 đổi crawler/import sang lưu trích-đoạn+link (bản quyền) trước khi bật lại crawl; (c) 🛑 Track-H: pháp nhân + đăng ký NĐ147 + luật sư ICT — CHẶN ra mắt công khai.
- **(2026-06-13) GĐ7 phần còn lại — chưa làm**: (a) `/api/constants` + Nuxt fetch để unify FE+BE constants (giờ `useConstants.ts` là nguồn FE duy nhất, chấp nhận được); (b) bỏ JS/HTML legacy trong `web/` + sửa `nginx.conf /legacy/` (giữ data.json/data.js/admin*.html/media); (c) gỡ field shim `coords`/`from`/`to` sau khi bỏ FE legacy.
- **(2026-06-13) GĐ4 phần phụ — chưa làm**: (a) ẩn `/system/*`,`/analytics/*`,`/metrics` ở production (nhiều endpoint — cân nhắc require_admin chung); (b) rate-limit per-user cho `/image/recognize` khi mở cho user thường (giờ admin-only); (c) cân nhắc hạ `max_rounds` agent sau khi có eval baseline (tránh giảm chất lượng mù).

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

- [ ] 🛑 **9.1** (Track-H — cần tài khoản UptimeRobot/BetterStack) Uptime trỏ `/health` keyword `"status":"ok"` + alert Telegram. Backend đã sẵn (/health + /health/deep).
- [ ] 🛑 **9.2** (Track-H) Google Search Console: verify **DNS TXT** (cần H5) → submit `sitemap.xml` đang chạy. Claude chuẩn bị hướng dẫn; người thực hiện verify.
- [ ] 🛑 **9.3** (Track-H — self-host container) Web analytics cookieless (Umami/Plausible CE) + nhúng script `nuxt.config`.
- [ ] 🛑 **9.4** (Track-H — Sentry/GlitchTip account/host) Error tracking hook vào `ErrorTracker.record_error` + `@sentry/nuxt`.
- [ ] **9.5** (HOÃN — cần thread token usage qua orchestrator.run; không verify được khi LLM offline) Cost dùng token thật thay ước lượng. → Backlog.
- [x] **9.6** ✅ Trang admin **Thống kê** (`/admin/thong-ke`) qua endpoint auth `/admin/analytics-overview` (summary/popular/gaps/top/costs). gaps = backlog nội dung KB. Build OK.

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

- [ ] 🛑 **12.1** (cần NGUỒN DỮ LIỆU thật — không tự bịa mùa vụ) Backfill `season` cho phần lớn experience/dish (hiện 41/421 wedge có mùa). Cần LLM-có-web hoặc nghiên cứu tay. → Track-H/data.
- [ ] 🛑 **12.2** (cần nguồn ngoài) Bổ sung provenance thật thay 471 entity tự-trích vinhlong360.vn.
- [x] **12.3** ✅ Trang `/theo-mua`: chọn tháng → wedge (experience/product/dish) đang vào mùa, sắp cao-điểm trước (relevanceScore≥2), badge Cao điểm/Đang mùa + seasonText. Footer link. Dữ liệu thật T6=27/T11=31/T1=29. Build OK. Đầy dần khi 12.1 backfill.

**🚦 Cổng DoD-12:** trang theo mùa hiển thị đủ nội dung thật theo tháng.

---

## GIAI ĐOẠN 13 — Hỗ trợ DN địa phương + Danh bạ hành chính (SHOWCASE-ONLY)

**Mục tiêu:** "lớp khám phá/niềm tin có cấu trúc, AI trích dẫn được" cho DN địa phương + danh bạ công vụ 124 xã/phường. Tận dụng graph + SEO/GEO + claim-listing/UGC + wedge đã xây. **Tiên quyết:** DoD-3, DoD-5.

> ⚠️ **BẤT BIẾN GĐ13 (CLAUDE §1.4):** CHỈ GIỚI THIỆU — **KHÔNG** đặt hàng/booking/thanh toán on-site, **KHÔNG** sàn bên-thứ-ba (giữ tầng pháp lý nhẹ, không kích đăng ký TMĐT NĐ52/85). CTA chỉ Zalo/điện thoại/"hỏi-giá-liên-hệ" (KHÔNG form chốt đơn giá+SL+xác nhận).
> ⚠️ **Dữ liệu cơ quan công quyền PHẢI có nguồn thật** (`source`+`updatedAt`) — **TUYỆT ĐỐI không tự sinh** địa chỉ/SĐT (sai = gây hại). Nạp dữ liệu thật = Track-H/B2G.

### A. Claim-listing cho DN (moat dữ liệu) — Postgres/UGC
- [~] **13.1** (MVP ✅; portal đầy đủ → Backlog) Nút "🏷️ Đây là cơ sở của tôi — đăng ký quản lý" → `/lien-he?claim=<id>`. ⏸ Luồng owner tự-sửa hồ sơ (claim record + admin duyệt + owner-edit) = Postgres/UGC, không test được sandbox → Backlog.

### B. Hồ sơ DN giàu schema + CTA liên hệ (KHÔNG booking)
- [x] **13.2** ✅ Trang chi tiết: CTA **📞 Gọi / 💬 Zalo** (attributes.zalo) — chỉ liên hệ, KHÔNG đặt hàng; đã có sẵn tel:/địa chỉ/website/nguồn+báo-sai + schema FoodEstablishment/LodgingBusiness (subtype LocalBusiness, Google rich-result). Build OK.

### C. Danh bạ hành chính 124 xã/phường (codeable ngay; dữ liệu = Track-H)
- [x] **13.3** ✅ type `facility` (placeId gắn xã) + TYPE_META + OFFICE_KIND; `db.facilities_by_place()` + `GET /api/facilities`. Test xanh. *(located_in dùng placeId — đủ cho danh bạ.)*
- [x] **13.4** ✅ Trang `/danh-ba`: chọn xã/phường (gom 3 vùng) → liệt kê cơ quan + schema.org **`GovernmentOffice`** (address/telephone/openingHours) + footer link. Build OK; /api/facilities wired. *(Mục trên `khu-vuc/[area]` có thể thêm sau.)*
- [x] **13.5** ✅ Admin nhập facility qua entity editor (thêm `facility`+`organization` vào VALID_TYPES) + nhãn "thông tin tham khảo" + link "Báo sai" → /lien-he; field `source`/`updatedAt` hiển thị. *(Nút báo-sai gắn /api/report cho facility = nâng cấp sau.)*
- [x] **13.6a** ✅ (codeable) `facility` vào tìm kiếm (`_is_searchable`) + `knowledge.directory_search(query)` tra theo tên cơ quan/tên xã + chat-tool **`directory_lookup`** (server dispatch + SYSTEM_PROMPT) → hỏi "địa chỉ/SĐT UBND/công an xã X" trả lời được **ngay khi có dữ liệu**; rỗng → note rõ "đang bổ sung" (KHÔNG bịa). Tests: TestDirectorySearch + integration dispatch xanh.
- [ ] 🛑 **13.6** (DATA / Track-H — KHÔNG bịa) Nạp địa chỉ/SĐT thật UBND/công an/… 124 đơn vị từ **nguồn chính thống** (cổng tỉnh, NQ 1687/NQ-UBTVQH15) hoặc **hợp đồng B2G**. Biến động cao hậu hợp nhất → cơ chế làm tươi. *(Đường code đã sẵn — 13.6a; chỉ chờ dữ liệu.)*

### D. Bảng cung theo mùa + lead B2B nhẹ (mở rộng wedge)
- [x] **13.7** ✅ `/theo-mua` banner lead B2B nhẹ "gửi yêu cầu nguồn sỉ" → `/lien-he` (KHÔNG chốt đơn on-site); item link sang trang chi tiết có CTA liên hệ. Build OK. *(View "HTX/vườn đang có X" sâu hơn = mở rộng sau khi có produced_in data.)*

### E. QR truy xuất hiển thị (marketing-trust)
- [~] **13.8** ✅ Panel "🔎 Truy xuất nguồn gốc" cho product (source/produced_in/updatedAt sẵn có; KHÔNG thay mã vùng trồng chính thức). ⏸ QR-ảnh = cần dep `qrcode` + mạng registry → Backlog.

### F. Doanh thu (showcase-only)
- [ ] 🛑 **13.9** (Track-H) Premium/featured listing (hộ KD để xuất hoá đơn) + theo đuổi **hợp đồng B2G** (Sở Du lịch/OCOP/UBND tỉnh) — vừa nguồn dữ liệu danh bạ vừa doanh thu chính. KHÔNG hoa hồng booking.

**🚦 Cổng DoD-13:** claim-listing hoạt động (chủ sửa → chat/api thấy); type `facility` + `/danh-ba` render với schema `GovernmentOffice`; nút báo-sai chạy; build + baseline xanh. (Dữ liệu thật danh bạ + B2G = Track-H, KHÔNG chặn phần code.)

> **Pháp lý GĐ13 (nhắc):** showcase = tầng nhẹ (không đăng ký TMĐT). NHƯNG vẫn cần: NĐ147 (UGC/claim → giấy xác nhận đăng ký MXH + **pháp nhân**, Track-H), PDPL (consent — GĐ5 ✅), và **GĐ5.6 crawler chỉ trích-đoạn+link** (tránh giấy phép trang TTĐT tổng hợp).

---

### 🔬 Audit dữ liệu đa-agent (2026-06-22) — 24 agent, 9 chiều + verify + critic + round2
**ĐÃ FIX & DEPLOY (commit gói safe-fix, deploy 20260622-101033):** gói tự-sửa-an-toàn (suy nội bộ, KHÔNG bịa, B1 backup, dry-run): con-phung→con-phung-con-ong-dao-dua (3 itinerary, gỡ dead-end); p-vung-liem.parentId→vinh-long; `attributes.district`→`legacy_district` (465, FE không render); address bỏ ", huyện X" (447, bảo thủ — chừa "Huyện Lộ", giữ thị trấn/TX); **sinh located_in backbone** entity→xã (1354)+xã→tỉnh (124)=+1478 rel (fix graph mồ côi); **validate refine** (B4+test): located_in/part_of không tính fanout-120. rels 9934→11412, validate 0, baseline 1190.
**✅ PASS-2 dọn nợ an-toàn (2026-06-22, commit 86904d3 + a8c4a1a + 8735b3b — CHƯA deploy):**
- Ghost: xoá `prov-1` ("Quán mới X") + `test` ("TEST") + 7 rel (5 ghost trước đã sạch; dangling=0, itinerary-stop hỏng=0 → 16 split-brain đã fix các vòng trước).
- `attributes.ward`: drop 87 trùng placeId; rename 203 tên-xã-CŨ-giải-thể → `legacy_ward` (giữ provenance, không che lỗi); giữ 115 (xã hiện-tại≠placeId → soát). Address NFC 4.
- **placeId bulk-default 36** (bằng chứng 3-lớp: address-ward = đúng 1 xã hiện-tại cùng vùng + token trong id/name): Nhị Long 13/Long Châu 8/An Bình 5/Nhơn Phú 4... bị gán nhầm.
- **placeId phường-số 138** (crosswalk NGUYÊN VĂN NQ1687, cross-check 2× khớp 100%; chỉ map khi address ghi 'TP <tỉnh>' → loại 7 case TX Duyên Hải): VL P1,9→Long Châu/P3,4→Phước Hậu/P5→Thanh Đức/P8→Tân Hạnh; BT P8→Phú Khương/P7→Bến Tre/P6→Sơn Đông; TV P1,3,9→Trà Vinh/P4→Long Đức/P7,8→Nguyệt Hoá/P5→Hoà Thuận. `missing_place_id` 262→199. validate exit 0.
- **Summary 259 viết lại** (commit 61c2265): workflow đa-agent 20 batch×(rewrite→verify, sonnet) sửa summary nhắc đơn-vị-HC-cũ → 2 cấp (tỉnh Vĩnh Long). 348 changed → ACCEPT 259, REJECT 89 qua **6 lớp verify chống-bịa §1.4**: token-subset (0 bịa) + giữ năm + không cắt>40% + không-còn-huyện/tỉnh-cũ + **LLM-veto 47** (giữ thương hiệu địa-lý 'kẹo dừa Bến Tre'/'bưởi da xanh', không đổi scope 'lớn nhất tỉnh Trà Vinh', không thêm tỉnh) + **brand-guard 60** ('Bến Tre/Trà Vinh' không kèm 'tỉnh' = bản sắc/tên riêng). summary 'huyện X' 384→140 (còn lại brand-protected/không-neo, cố ý giữ). 74 entity không neo placeId-xã → không rewrite mù.

**✅ PASS-2b — nguyên tắc "nghi ngờ → KHÔNG công khai" (2026-06-22, chủ duyệt):**
- **placeId qua CROSSWALK NQ1687 122** (commit 05e41e0): tái dùng crosswalk xã-cũ→phường-mới (verbatim+chủ duyệt) — [B] 109 placeId-ward-hợp-lệ nhưng address+crosswalk hội tụ DUY NHẤT ward khác → sửa (bug "lùa vào ward trung-tâm"); [A] 2 trỏ-non-ward giải được → sửa; [A] 11 sông/rạch/trỏ-tỉnh không giải → **None (chưa phân loại)**. Chỉ sửa khi mọi đơn-vị address hội tụ 1 ward khớp area.
- **Toạ độ re-align + cờ gần-đúng** (commit dae52fa + 51ee906): sau khi sửa placeId, re-align 227 pin sai-ward → centroid-placeId; gắn `coords_approximate=true` cho 698 entity ngồi trên centroid; **null 87** coords (placeId None) — gỡ pin giả. FE trang chi tiết hiện "📍 Vị trí: Gần đúng (trung tâm xã/phường)" khi approximate (verify dev SSR pass). missing_location 12→99 (đúng nguyên tắc).
- Cơ chế: placeId=None = "chưa phân loại" (`/admin/unclassified` + `chua-phan-loai.vue`) — KHÔNG đoán bừa.

**✅ PASS-2c — nghiên cứu sâu để xử nợ (2026-06-22):**
- **placeId thiếu: giải 11** qua CROSSWALK + parser bắt 'P./TT./TX./X.' viết tắt (commit bed805c, e1e39bd; CHẶN bug 'Tp.'/'tx.' bị hiểu nhầm = negative lookbehind). 199 None còn lại = 31 không-address + ~18 phường-số-không-trong-NQ1687 + ~150 chỉ street+thành-phố KHÔNG có ward → đúng để None.
- **Geocode 55 toạ độ THẬT** từ Nominatim/OSM (commit 6eb5f4e) — gate validate: chỉ nhận kết quả cách centroid-ward 0.2–5km (loại echo + match-sai trùng-tên-đường tỉnh khác). 478 ứng viên → nhận 55 (12%), loại 423 (OSM phủ kém ĐBSCL). coords_approximate 698→644.

**CÒN NỢ — GIỚI HẠN CỨNG bởi nguồn ngoài (KHÔNG bịa được):**
- 🔴 **~644 toạ độ vẫn gần-đúng** (đã gắn cờ + FE báo): OSM không có dữ liệu street vùng ĐBSCL → cần geocode trả-phí (Google, §B8 cấm) hoặc khảo sát thực địa.
- 🔴 **199 placeId None + ~97 thiếu coords**: address chỉ street+thành-phố (không ward) hoặc phường-số ngoài NQ1687 → không xác định ward an-toàn → admin gán tay (/admin/unclassified).
- ✅ **produced_in rác**: ĐÃ gỡ 1665 cạnh Cartesian (fanout-nguồn>=6, auto-sinh) — commit a9d8a26. Giữ 133 (fanout<=5, chủ ý). Đồng thời gỡ 176 near không hợp lệ (sửa regression coords). rels 11346→9505, validate 0.
- 🟠 **CTA (§1.4)**: trích được 2 phone có-nhãn (90b8d74); còn lại entity THỰC SỰ không có contact trong data (162 đã có phone) → 0 Zalo/website cần **nguồn ngoài**, KHÔNG bịa được.
- 🟡 **115 attributes.ward giữ-soát + ~few address-conflict không hội tụ**: phần lớn placeId VỐN ĐÚNG (address ghi tên cũ); phần nghi sai để nguyên/None.
- ✅ **summary 'huyện X'**: ĐÃ viết lại 259. Còn 140 cố ý giữ (brand/scope/không-neo).
- 🟢 **Đối chứng (KHÔNG lỗi)**: 0 dangling/self-loop/dup-triple; DB↔json khớp 100%; near cấu trúc sạch; placeId trỏ non-ward 13→0.

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

- **(2026-06-22) 🔬 AUDIT SÂU 3 LƯỢT ĐA-AGENT → `docs/audit-findings-20260622.md`** (110 finding verified: 3 crit, 26 high, 46 med, 35 low + audit-3 scan-only). Đã FIX: ARCH-001 (province area). Lộ trình sửa đề xuất theo rủi-ro:
  - **P0 vận hành/bất-biến:** CONC-001 (sync OpenAI in event loop §4) · CLP-01 memory_graph LLM no-gate (§B8) · EH-01/02 generate_followups+json.loads no-timeout/guard · SEC-001 OTP leak · SEC-002 XFF spoof · /graph no-auth. (server.py chat = blind-spot §B3 → viết test trước.)
  - **P1 dữ liệu §1.4:** admission_fee alias · 16 dup entity · 9 transposed coords · 68 summary/37 address sai tỉnh · 169 orphan.
  - **P2 DB/script:** replace_from_json atomic + description (test trước §B3) · guard optimize_data.py + gỡ bịa produced_in.
  - **P3 perf/FE/deploy:** maplibre lazy→fix build OOM→deploy FE note · PG pool · N+1 · FE null-safety coords · SEO/CWV.
  - DƯƠNG-TÍNH-GIẢ (KHÔNG sửa): GS-02 (ward BT/TV→vinh-long là đúng sau sáp nhập); audit-3 .env-leak (đã verify gitignore đúng).

- **(2026-06-20) 🌟 WORLD-CLASS HARDENING** (audit 10 chiều, 5.5/10 → memory `project-worldclass-roadmap`). Verdict: KHÔNG "thô sơ" mà thiếu nội dung + vài bug data-shape. Lộ trình 5 phase; mỗi phase build+test+preview+**prod-verify** (không deploy mù).
  - **P0 ✅ DEPLOYED (commit 579ee38):** fix bug `source` dạng LIST (877 entity rớt nguồn → emit JSON-LD citation/sameAs); canonical dedup (đúng 1/trang); og:image chỉ ảnh thật; contrast `--ink-tertiary` + token `--accent-text` AA; quarantine 11 summary rác "404/không đủ thông tin" + guard `validate_data.BOILERPLATE_SUMMARY` (ERROR); geocode 6 entity coordless qua centroid + xoá 75 near-edge vô nghĩa → **lỗi "77 near thiếu toạ độ" RESOLVED** (validate exit 0); `sitemap-media.xml`.
  - **P1 ✅ DEPLOYED (commit 4f9309c, đa-agent workflow investigate→implement):** placeholder SVG gradient deterministic theo id (prod 239/239 card, hết stock-tile lặp); hero motif vùng Mekong (catalog `::before`); `.reveal` hiện-khi-không-JS (html.js gate + inline head script); `useModalA11y` (focus-trap + scroll-lock + ESC, `immediate` watch) + modal max-height/internal-scroll (sửa keyboard-trap); thang z-index token; khối provenance "Nguồn·Cập nhật·Báo sai" → report flow; trang `/gioi-thieu` (+ AboutPage/Organization JSON-LD) + link footer. **2 bug bắt nhờ preview-verify + fixed:** data-uri quote → SSR hydration style mismatch; modal watch thiếu `immediate`.
  - **P2/P3/P4 backend 🔄 đang implement (đa-agent, file rời nhau):** JSON-LD ImageObject/BreadcrumbList/ItemList; coverage-metrics + CI gate; verified-timestamps (không bịa ngày); error-capture free-tier (`POST /api/client-error` → log, KHÔNG Sentry — B8); B3 tests write-path auth/UGC/moderation; image **review-queue** (duyệt tay, KHÔNG auto-publish — B6).
  - **⛔ CHẶN — chờ chủ dự án:** (a) PUBLISH ảnh thật (B6 + Wikimedia khớp tên sai ~50% → bắt buộc review-gate); (b) enrich mô tả hàng loạt bằng LLM (B8 — cần `AUTONOMOUS_AGENT_ENABLED=true` + cap); (c) dữ liệu văn phòng phường (Track-H — không bịa).
  - **Hạ tầng:** `scripts/deploy.sh` đóng gói flow deploy + mọi gotcha (live output `web-nuxt/.output`; `rm -rf` trước extract; `--replace` có khoá B7 + backup DB; KHÔNG đụng `.env`).
  - **Backlog nhỏ phát sinh:** ~~`tests/test_config.py::test_defaults` phụ thuộc env runner~~ ✅ XONG (monkeypatch.delenv + `_env_file=None`); `CategoryIcon.vue` giờ không card nào dùng (cleanup candidate — rà nơi khác trước khi xoá); admin editor "Về chúng tôi" cần seed key `page.about` (`seed_site_settings.py`) mới lưu được (trang public chạy bằng fallback nên OK); CSS split `entry.css` 167KB→<60KB (P3-perf, hoãn — refactor lớn).

- ~~(2026-06-13) GĐ3.1 — UGC/auth → SQLite~~ ✅ ĐÃ QUYẾT (Postgres-only): không port; `_require_pg` gắn 3 router UGC trả 503 trên SQLite; tài liệu CLAUDE.md §1.3 + docs/ugc-postgres.md. Lý do: dev/prod parity, tránh nợ 2 phương ngữ SQL, UGC vốn cần Postgres.
- ~~(2026-06-13) GĐ3.8 — data-quality DB-native~~ ✅ XONG (commit 35ff28e): apply/rollback ghi thẳng DB, bỏ khoá. Footgun "xoá edit admin" đã gỡ.
- **(2026-06-13) GĐ11 phần còn lại**: ~~(a) 11.1 sparse-vector TF-IDF~~ ✅ XONG (commit 61e766b test trước + 85c1ca3 refactor: `_vectors` dict[eid,{token:weight}] thưa; benchmark 1703 entity → 5.08MB vs 208MB dense (~41x), 0.263% mật độ; +19 test; full 1084 passed; cache thật đã regenerate sparse); ~~(b) 11.4 `/reload` nền + atomic swap~~ ✅ XONG (commit 62da6ae: `reload()` build+swap dưới `_reload_lock` + vô hiệu adjacency; endpoint qua `asyncio.to_thread` → không đóng băng /health; +4 test gồm concurrency). **→ GĐ11 hoàn tất.**
- **(2026-06-13) GĐ10 phần còn lại — chưa làm**: (a) 10.1 hybrid prerender (cần pipeline build có backend); (b) QA browser map clustering (env có ndaMapKey); ~~(c) sửa mojibake `admin/data-quality.vue`~~ ✅ XONG (commit ee8cc40: 19 dòng tái dựng byte per-char); (d) siết `any` (146 chỗ); ~~(e) rà clickable `<div>` toàn site → `<button>`~~ ✅ XONG (commit 1626dd8: index card→NuxtLink, tao-lich-trinh→button; 4 div @click.self còn lại là backdrop hợp lệ).
- ~~**(2026-06-13) GĐ6 stub — chưa dọn**~~ ✅ XONG (commit 517cc4e): gỡ stub 7 module đã xoá (relay/streaming/advanced-graph/a2a/knowledge-evo/multimodal/federation) khỏi `server.py` (−221 dòng: import/flag/~15 endpoint/3 model/feature-list/startup-print) + `scheduler.py` (2 task disabled) + test model dead. GIỮ self_optimizer/semantic_cache/llm_judge/dynamic_agents (còn sống) + HAS_OPTIMIZER (hot path). Full 1085 passed; smoke boot 11 passed.
- **(2026-06-13) GĐ5 phần còn lại — chưa làm**: (a) lưu timestamp/version consent vào DB (cột PG ở `users`); (b) GĐ5.6 đổi crawler/import sang lưu trích-đoạn+link (bản quyền) trước khi bật lại crawl; (c) 🛑 Track-H: pháp nhân + đăng ký NĐ147 + luật sư ICT — CHẶN ra mắt công khai.
- **(2026-06-13) GĐ13 phần còn lại — chưa làm**: (a) 13.1 owner-portal đầy đủ (claim record + admin duyệt + owner tự-sửa — Postgres/UGC, cần test với PG); (b) 13.8 QR-ảnh (dep `qrcode`); (c) 13.6 nạp dữ liệu danh bạ thật 124 đơn vị (Track-H/B2G); (d) 13.9 premium listing + hợp đồng B2G (Track-H); ~~(e) mục "Danh bạ" trên trang `khu-vuc/[area]`~~ ✅ XONG (commit 6093277: chip → `/danh-ba?area=` + pre-scope optgroup); ~~(f) nút báo-sai facility gắn /api/report~~ ✅ XONG (commit b6f9cdb: `POST /api/report` ghi reports.jsonl + rate-limit + `GET /admin/info-reports` + nút báo-sai trên danh-ba). ~~*(Còn: wiring PostCard "Báo cáo" → /api/report cho UGC = follow-up nhỏ.)*~~ ✅ XONG (commit 34021c6: `useReport` composable + `@report` trên cong-dong/bai-viet/nguoi-dung).
- **(2026-06-14) Design System (kế hoạch `docs/design-system-plan.md`)** — từ deep-research "thiết kế giao diện" (chủ duyệt). Giữ CSS thuần + tokens (KHÔNG Tailwind), giữ hệ màu hiện tại. 5 bước additive: ~~(1) hệ thống hóa tokens 3 tầng + thang typography/spacing 8pt~~ ✅ XONG; ~~(2) audit tương phản WCAG AA~~ ✅ XONG (muted #586860, white→ink trên amber-dark, token `--border-input` ≥3:1; 44px+focus đã sẵn; dark brand-as-text hoãn Bước 4); ~~(3) self-host font `@nuxt/fonts` + ảnh `@nuxt/image` (weserv, off-VPS)~~ ✅ XONG; ~~(4) dark mode toggle `@nuxtjs/color-mode` + tách brand fg/bg (`-fg` tokens, dark lighten ≥4.5:1) + dark surfaces (`#fff`→`--card`)~~ ✅ XONG; ~~(5) JSON-LD Schema.org~~ ✅ ĐÃ CÓ SẴN 17 trang + bổ sung `inLanguage`. **→ Design System hoàn tất Bước 1–5.**
- **(2026-06-13) GĐ7 phần còn lại — chưa làm**: (a) `/api/constants` + Nuxt fetch để unify FE+BE constants (giờ `useConstants.ts` là nguồn FE duy nhất, chấp nhận được); (b) bỏ JS/HTML legacy trong `web/` + sửa `nginx.conf /legacy/` (giữ data.json/data.js/admin*.html/media); (c) gỡ field shim `coords`/`from`/`to` sau khi bỏ FE legacy.
- **(2026-06-13) GĐ4 phần phụ**: ~~(a) ẩn `/system/*`,`/analytics/*`,`/metrics` ở production~~ ✅ XONG (commit 7618029: middleware `gate_internal_endpoints` — prod thiếu admin key → 404; 1 middleware phủ ~50 endpoint; Nuxt không đụng); (b) rate-limit per-user cho `/image/recognize` khi mở cho user thường (giờ admin-only) — chưa làm; (c) cân nhắc hạ `max_rounds` agent sau khi có eval baseline (tránh giảm chất lượng mù) — chưa làm.

- **(2026-06-14) Fix placeId gán sai — XONG một phần** (commit 6b76512): 180 entity Bến Tre/Trà Vinh bị importer dồn vào xã Vĩnh Long (xa-an-binh/xa-tra-on) đã gỡ placeId + sửa area (script `scripts/fix_placeid_buckets.py`, evidence-based, không bịa). **Đã chặn tái nhiễm path sống** (commit 640fec4): `discover_province._place_for` (scheduler continuous-discovery) giờ trả None thay vì dồn vào ward đầu khu vực; `auto_learn.PLACE_KEYWORDS` vốn đã đúng. **Còn nợ**: (a) **importer một-lần vẫn chứa mapping xấu** — `import_baovinhlong.py:20-58` (BT→xa-an-binh) + `import_deep_crawl.py:21` default_pid; không chạy theo lịch nhưng nếu chạy tay sẽ tái nhiễm → sửa khi đụng tới; (b) lỗi xã-trong-cùng-tỉnh (vd "Chợ Tân Quới" còn ở An Bình) — cần crosswalk "đơn vị cũ→xã mới" chính thống (Track-H); (c) 604 entity hiện `placeId=None` (chưa phân loại xã) chờ crosswalk; (d) 110 `produced_in_area_conflicts` (validate) — rà sau.
- **(2026-06-21) 🔴 CRITICAL — Migrate 2-cấp CHƯA hoàn tất (BT+TV còn gán theo HUYỆN cũ)** [audit `scratch/audit_admin*.py`/`audit_resolve.py`]: Đợt 16-phường (2026-06-18) chỉ xử Vĩnh Long. Hiện trạng data.json (1817 entity): ✅ 124 đơn vị cấp xã (35 phường + 89 xã) + 1 tỉnh modeled chuẩn (level xa/phuong/tinh, KHÔNG có cấp huyện); ✅ 1276 entity gán xã/phường hợp lệ. **NHƯNG**: (a) **24 place "Huyện X/Thành phố X/Thị xã X" cũ vẫn tồn tại** (level=None nên lọt check theo-level) — phải bỏ; (b) **510/1817 entity (28%) gán SAI vị trí**: 383 trỏ huyện cũ + 127 orphan `p-vinh-long-city`/`p-tra-vinh-city`/`p-ben-tre-city` (TP cũ đã giải thể). Theo area: BT=265, TV=186, VL=59. (c) 645 entity có "huyện/TX" trong **address field** (stale text); 100 trong summary. **Khả năng sửa**: 181 TỰ SỬA được evidence-based (địa chỉ có "xã/phường X" khớp đơn vị mới) → script reassign + B1 backup; **329 cần crosswalk chính thống** (địa chỉ chỉ "Huyện X", hoặc xã cũ đã sáp nhập/đổi tên, hoặc "phường 3 TP Trà Vinh" số cũ) = **Track-H, TUYỆT ĐỐI KHÔNG bịa** (§1.4). **Ảnh hưởng prod** (đã sync từ data này): /danh-ba, /xa-phuong/[id], /khu-vuc, nearby-by-area hiển thị sai/thiếu cho 510 entity. **Plan đề xuất** (chờ duyệt): B1 backup → reassign 181 → detach 329 về area-level (placeId=None, giữ area, KHÔNG bịa ward) → bỏ 24 place huyện cũ → validate → deploy --replace. 329 chờ crosswalk NQ1687 (cổng tỉnh) đặt đúng ward sau.
  - ✅ **XONG (LOCAL, 2026-06-22, commit 6a1eedc):** chủ dự án cấp toàn văn NQ 1687 → `scripts/migrate_huyen_to_ward.py` (crosswalk + 3 lớp an toàn §1.4: bằng chứng-trong-address + khớp-1/124-ward + khớp-area; chuẩn-hoá GIỮ DẤU sau khi dry-run bắt lỗi "Bình Thạnh"≡"Bình Thành"; phường-số key theo (TP,số)). B1 backup 20260622-000342 → **reassign 244** (222 crosswalk+16 direct+6 numbered, spot-check khớp NQ) → **detach 266** về area-level (district-only/xã-ngoài-crosswalk/no-address — chờ phân loại tay ở `/admin/chua-phan-loai`, KHÔNG bịa) → **gỡ 24 place huyện/TP/TX cũ**. data.json 1817→1793; re-audit: **0 trỏ huyện cũ, 0 orphan, 0 defunct, 1496 trỏ ward hợp lệ**; validate exit 0; DB+data.json+data.js đồng bộ. ✅ **ĐÃ DEPLOY PROD (2026-06-22, deploy 20260622-065209, `deploy.sh --replace`):** prod Postgres 1817→1793 entity; verify: /health entities=1793, entity reassign đúng (vd khu-du-lich-chin-song→xa-thanh-phu "Xã Thạnh Phú"), /danh-ba + /xa-phuong + /dia-diem = 200, services active, log sạch. Rollback `db-pre-deploy-20260622-065209.sql`. UGC không đụng (--replace chỉ entities/rels/itin). **+10 (commit 103d45f, deploy 20260622-090744):** Mỹ Thạnh An→Phường An Hội (verbatim k116), parser bắt thêm (TT Cái Nhum, "Thanh Bình và Quới Thiện", xã An Bình…), chua-vam-ray override (địa chỉ gõ nhầm "Hàm Thuận"→Hàm Tân→Hàm Giang k53). placeId=None: 278→268. **BÀI HỌC §1.4:** WebFetch *tóm tắt* NQ KHÔNG tin cậy (cho lỗi giả ở Hưng Phong/Vĩnh Bình/Long Định/Kim Hòa… — verbatim khoản xác nhận crosswalk GỐC đúng hết); CHỈ trích **nguyên-văn-khoản** mới dùng được. **CÒN (Backlog)**: ~258 detach: 162 sản phẩm/món (ĐÚNG ở area-level, không pin được); ~40 fixed-place district-only (admin phân loại tay); ~~An Khánh/An Thủy~~ ✅ XONG (deploy 20260622-091614): chủ dự án xác nhận An Khánh→Phú Túc (sáp nhập TT Châu Thành; verbatim NQ k59 model CẮT SÓT nên tưởng mâu thuẫn), An Thủy→Tân Thủy. +5 entity (4 An Khánh→p-phu-tuc live). **Tân Quy** (Càng Long) chưa có đáp án → giữ area-level; 13 trỏ business-mistyped-place; dọn 645 text "huyện/TX" trong address (cosmetic). Tool reliable cho last-mile = CSV cổng tỉnh (encode trực tiếp) hoặc verbatim-khoản.
- **(2026-06-13) Lỗ hổng CI phát hiện khi demo browser**: `npm run build` KHÔNG SSR-render từng route → 2 trang (`/danh-ba`, `/theo-mua`) gọi `useSeoHelpers()` (composable không tồn tại) vẫn build OK nhưng **500 lúc SSR** suốt từ khi tạo. Đã sửa (commit ced5e50). **Đề xuất**: thêm route-render smoke (vd `nuxt build` + script fetch các route chính kỳ vọng 200, hoặc `@nuxt/test-utils`) vào CI để bắt lớp lỗi này. Chưa làm.

- **(2026-06-13) Trang hub từng xã/phường — XONG** (commit 949c843, theo yêu cầu chủ dự án + khớp D1): `/xa-phuong/[id]` gom 4 mục (🏛️ danh bạ · 🗺️ du lịch · 🏡 lưu trú · 🍊 sản phẩm) cho mỗi xã/phường; `GET /api/places/{id}/overview` (+`db.entities_by_place`); link từ `khu-vuc/[area]` (list 35 ward VL) + `danh-ba`. 51/124 ward có nội dung; danh bạ mỗi ward = empty-state đến khi có dữ liệu thật (13.6 Track-H). **Còn (đề xuất)**: SSR-prerender các trang ward (CWV/SEO — gắn 10.1); breadcrumb/sitemap thêm ward; nav top-level "Xã/phường".

### 🛠 Hệ thống quản lý (admin CP + bot + agent) — 2026-06-14
**ĐÃ XÂY:** (1) Admin CP polish (commit 4f44b51): sửa nút Reload (nhận phiên admin, trước 401) + dashboard hiện "Báo sai" (/admin/info-reports). (2) **Bot Telegram quản lý** (794ceb7): lệnh `/admin /thongke /choduyet /baosai /reloadkb` gated theo `ADMIN_TELEGRAM_IDS`, gọi /admin/* bằng X-Admin-Key. (3) **Digest định kỳ MIỄN PHÍ** (088a7ff): scheduler `admin-digest` 24h gửi số liệu DB qua Telegram — KHÔNG LLM (§B8-safe), no-op nếu chưa cấu hình. (4) **Agent on-demand** (d5491bb): `POST /admin/ai/triage` + nút "🤖 Gợi ý ưu tiên" — 1 lần gọi LLM khi bấm, degrade an toàn khi LLM hỏng.
**(2026-06-14) +4 tính năng quản lý:** (25d02a1) gán xã cho entity chưa phân loại (`/admin/chua-phan-loai` + `/admin/unclassified` + `/entities/{id}/place` validate) — lấp nợ 604 placeId; (931e05a) CRUD danh bạ/facility (`/admin/danh-ba` + `EntityCreate.source`) — nhập cơ quan có nguồn bắt buộc; (b785622) hàng đợi báo-sai có action (`/admin/info-reports/action` resolve/dismiss + section trong `/admin/bao-cao`); (7729c61) bảng chi phí LLM + cảnh báo (`/admin/cost-overview` + panel ai.vue + digest cảnh báo gần-cap). Mỗi tính năng có test; full 1097 passed.
**(2026-06-14) Admin CP — đóng hết orphan UI:** quản lý ảnh entity (6fb7bae) + quan hệ entity (696f7ec) + thao tác hàng loạt (6fb7bae) + trang Duyệt tự học/Nguồn/Export (60c4ee3). Sửa 2 bug entities.vue (type list stale; place_id→placeId). Mọi endpoint admin giờ có giao diện. 13 trang admin. Test mỗi tính năng; full 1097 passed.
**CẦN CẤU HÌNH (.env, người dùng):** `ADMIN_TELEGRAM_IDS=<chat_id,...>` để bật bot quản lý + digest. `ADMIN_API_KEY` đã có.
**✅ (5) Agent tự động gọi LLM CÓ CAP** (commit ddb4167, chủ dự án duyệt override §B8 có kiểm soát): `autonomous_budget.py` (cap cứng/ngày, atomic, OFF mặc định) + scheduler `autonomous-agent` (24h, mỗi lần ≤1 call LLM → gợi ý quản trị qua Telegram, vượt cap thì bỏ qua). CLAUDE §B8 đã ghi ngoại lệ có-kiểm-soát (opt-in + cap + kill-switch). **Bật bằng `.env`:** `AUTONOMOUS_AGENT_ENABLED=true` + `AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY=20`. Theo dõi chi phí ở `/health` → `scheduler.autonomous_agent`.

### 🔬 Audit hệ thống toàn diện (2026-06-14) — 3 agent (backend/data/frontend)
**ĐÃ FIX (commit 4f3ddd9, ff6d654):** /api/entities?month= pagination (total/offset đúng); Content-Length hỏng→400; /chat/stream parity (strip HTML+cắt 2000+cap history); /reload invalidate _place_cache; upsert nhận alias `coords`→`coordinates`; /hanh-trinh hydration (ClientOnly); lọc rel LLM treo. +3 test; full 1091+ passed.

**CÒN NỢ (theo severity):**
- ~~🔴 CRITICAL — split-brain ETL ghi data.json (B1)~~ ✅ **XONG** (commit 002c63b): kb_curation (promote/reject/auto_promote), learn_loop (add+confidence), discover_province (add), cleanup_noise (delete+backup+atomic), relationship_discovery (add rel) — tất cả ghi thẳng `database.db` (data.json = working copy). +test write-through. **Phát hiện phụ**: DB không có cột verified/status → provisional quarantine vô tác dụng với chat (đọc DB); auto-learn entity vào DB là live ngay (product-note, chưa xử lý).
- ~~🟠 HIGH — importer còn province→bucket (B2)~~ ✅ **XONG** (commit 1001ca1): 4 importer `guess_place_id` trả None (bỏ map cả tỉnh→1 xã); chạy lại → unclassified thay vì mis-bucket.
- ~~🟡 MED — an toàn ghi file~~ ✅ XONG: `cleanup_noise` (B1: backup+atomic) + `export_data.py` (commit 874ea48: atomic temp-then-replace; file regenerable từ DB nên đủ).
- ~~🟡 flaky test-isolation `test_retrieval_eval`~~ ✅ XONG (874ea48: fixture `knowledge.reload()` reset KB — 4 recall test pass trong combined run). ~~2 test lỗi thời `tests/test_integration.py`~~ ✅ (0fcdf7f: feedback 422, /reload 401).
- ~~🟡 **MED — abstention retrieval yếu**~~ ✅ **ĐÃ XONG (xác minh 2026-06-21)**: `TestAbstention` 3 passed, `abstention_rate=1.0` (≥0.7). Note cũ "rate 0.5<0.7" đã lỗi thời — fix nằm ở việc curate `ABSTENTION_CASES` (bỏ "Paris" trùng "Khách sạn Paris Vĩnh Long", dùng query ngoài-vùng không trùng tên entity local) + `query_relevance` gate. Không cần code thêm.
- 🟡 **MED — provisional quarantine vô tác dụng (product-note)**: DB không có cột verified/status; auto_learn upsert entity provisional (conf~0.35) thẳng vào DB → live với chat không qua review. Quyết định sản phẩm: có cần lọc verified ở chat/search không (cần cột DB + filter)?
- 🟢 **LOW**: `database.get_query_stats` f-string INTERVAL (chưa có caller, latent); `kb_curation.find_near_duplicate` over-merge (2-token).

### 📊 Hàm ý từ deep-research nhu cầu người dùng (2026-06-13) — định hướng, KHÔNG tự đổi §1
> Nguồn: memory `research-vinhlong360-demand.md` (24 nguồn, 25 claim verify 3-phiếu, 23 xác nhận / 2 bác). Đây là **ưu tiên hóa & việc đề xuất**, không thay quyết định kiến trúc §1.4 (showcase-only vẫn giữ).

- **D1 (định hướng ưu tiên — không phải task mới):** Danh bạ hành chính = **ngách trống mạnh & phòng thủ được nhất** trong 4 nhóm (NN chưa có danh bạ SĐT/địa chỉ cơ quan; cổng du lịch tỉnh chỉ phủ VL cũ). → Đặt **13.6 (nạp dữ liệu thật 124 đơn vị) + phủ TRỌN 3 vùng** lên ưu tiên #1 khi có nguồn/B2G. Khác biệt cốt lõi vs đối thủ = phủ tỉnh hợp nhất.
- ~~**D2 (🤔 CẦN CHỦ DỰ ÁN QUYẾT):** link-out cho OCOP~~ ✅ **ĐÃ QUYẾT + XONG** (chủ dự án chọn **chỉ Zalo/website, KHÔNG sàn TMĐT** — an toàn ranh giới trung gian TMĐT). Commit dd63f02: trang product có `attributes.website` → nút "🛒 Hỏi mua trực tiếp" trỏ website riêng chủ thể (`_blank`/`nofollow`), cạnh Gọi/Zalo (đã có từ 13.2). Giữ showcase-only §1.4: KHÔNG giỏ hàng/thanh toán on-site, KHÔNG link sàn. Build OK.
- **D3 (định hướng doanh thu):** Ưu tiên **B2G > premium-listing từ hộ OCOP** (hộ OCOP ít sẵn lòng trả phí cho cổng không tạo giao dịch). Pitch B2G: *cổng duy nhất phủ trọn tỉnh hợp nhất + dữ liệu chuẩn hóa/liên thông* (đúng nỗi đau "phân mảnh" ngành đang nói). Gắn 13.9 (Track-H, cần pháp nhân).
- **D4 (cảnh báo pháp lý — gắn H1):** Ngưỡng NĐ147 = 10k truy cập/tháng **HOẶC** 1k user → SEO/GEO tốt **chạm 10k-truy-cập TRƯỚC** khi có 1k user UGC ⇒ kích cấp phép SỚM. **Câu hỏi mở chưa giải:** site showcase + UGC nhẹ bị xếp "MXH" hay "trang TTĐT tổng hợp"? → làm rõ phân loại TRƯỚC launch (đưa vào hồ sơ luật sư H2).
- **D5 (đừng làm USP):** 2 claim BỊ BÁC — "65% du khách tin AI lập kế hoạch" (0-3) + "QR truy xuất validate nhu cầu" (1-2). ⇒ **Không** marketing chatbot-AI / QR truy xuất làm điểm bán chính; không đầu tư mạnh thêm vào QR (13.8 giữ ở Backlog). Khớp [[feedback-no-heavy-features]].

### 🔧 Tầng-1 Hardening (2026-06-21) — từ "đánh giá sâu hiện trạng" (chủ dự án duyệt)
> 3 vá an toàn additive, không đổi hành vi sản phẩm; baseline xanh (1189 passed via `python -m pytest -q` từ root).
- ✅ **§B8 footgun:** `scheduler.py:63` `SCHEDULER_ENABLE_AUTONOMOUS_TASKS` default `True`→`False` (khớp `config.py:68`/.env/§B8) + `tests/test_scheduler_safety.py` khoá bất biến (off mặc định + opt-in được). Commit 9417ac4.
- ✅ **Admin key:** `middleware.py` fail-closed ở prod (KHÔNG auto-sinh secret; admin tắt tới khi đặt key) + `verify_admin_key` guard key rỗng; `server.py` startup không in giá trị key đã cấu hình (chỉ in DEV auto-gen để dev xài). Commit 0145edc.
- ✅ **Bare except:** `burn_gpt55.py` 6 chỗ `except:` → `except Exception:` (không nuốt Ctrl-C/SystemExit). Commit a0f3455.
- ✅ **#5 typecheck frontend (commit 1af12e9):** +devDeps `typescript`/`vue-tsc` + `npm run typecheck` (nuxt typecheck) + CI job non-blocking. Phát hiện CI cũ ĐÃ có ruff lint (Python) + build + TruffleHog secret-scan → chỉ thiếu typecheck FE + CVE scan.
- ✅ **#6 dependency CVE scan (commit 1af12e9):** CI job `deps-audit` = pip-audit (requirements.txt) + npm audit (high+), non-blocking. Hiện trạng: **Python 0 CVE**, frontend **1 LOW** (esbuild dev-server, dev-only). Secret-scan (gitleaks-class) đã có sẵn = TruffleHog.
- ✅ **#4 route-render SSR-500:** lớp bug "composable không tồn tại/undefined" (vd /danh-ba, /theo-mua) nay bắt **tại gốc** bằng `npm run typecheck`. Smoke *runtime* full (mock API/backend lúc build) hoãn → gắn 10.1.
- **CÒN NỢ — 🟡 ~642 lỗi vue-tsc pre-existing** (data `useFetch`/`$fetch` chưa typed → truy cập thuộc tính trên `{}`). KHÔNG phải bug runtime (build/chạy OK). Top file: `admin/data-quality.vue` (75), `dia-diem/[id].vue` (56), `index.vue` (49), `xa-phuong/[id].vue` (49), `admin/bao-cao.vue` (40)… Dọn tăng dần (định nghĩa interface cho API response; bắt đầu từ composables/shared) → khi về 0 thì flip typecheck CI sang blocking. **KHÔNG big-bang.** ESLint FE (từ đầu) = backlog riêng (lớn; ruff đã lo Python).

### 🎨 Tầng-2 CWV — tách entry.css (2026-06-21, chủ dự án duyệt "bài bản")
> Phân tích usage data-driven: `scratch/analyze_css.py` (map class → file dùng). Đo 8 file global (`base` 71KB, `detail` 48KB, `components` 40KB, `catalog` 39KB, `cards` 20KB, `events` 10.5KB, `variables` 9.8KB, `dark-overrides` 7KB).
- ✅ **`events.css` tách (commit 2a08c6f):** chỉ `le-hoi`+`su-kien` dùng → bỏ khỏi `css[]`, import `<style src>` 2 page. **entry.css 202.5KB→189.9KB** (−12.6KB mọi trang); events thành chunk riêng 7.9KB. Verify HTML prerender: /le-hoi CÓ, / & /du-lich KHÔNG.
- ⛔ **`catalog.css` (39KB) → GIỮ GLOBAL (quyết định):** class catalog dùng trải ~15 trang danh mục (gần cả site) → route-load phải import 15 nơi mà ~không tiết kiệm. Tách = sai, KHÔNG làm.
- 🟠 **`detail.css` (48KB) → đang tách dần (co-locate CSS component, nạp theo component):**
  - ✅ **EntityReviews + NearbyEntities (commit 4715bcc):** chuyển `.reviews-*/.review-*/.ri-*/.rf-*`→EntityReviews.vue, `.nearby-*`→NearbyEntities.vue (gồm override reduced-motion/responsive/dark, giữ thứ tự). **entry.css 189.9KB→184.5KB** (tổng từ đầu 202.5→184.5 = −18KB). Verify: class rời entry, vào chunk `_id_`. Không file khác style các class này → cascade an toàn.
  - ✅ **Verify thị giác (backend bật 2026-06-21):** /le-hoi render đúng (event-date-badge, event-row card, badge .cat-mua) → events.css route-load OK; trang chi tiết /dia-diem render đúng (hero .detail-cover, breadcrumb, layout) → reviews/nearby move không vỡ.
  - ✅ **BIG WIN — route-load detail.css (commit d51858e): entry.css 184.5→158.1KB (TỔNG 202.5→158.1 = −44KB, ~22% mọi trang).** Tách 14 class shared → `detail-shared.css` (global); detail.css → `<style src>` ở 3 trang chi tiết. Verify build + THỊ GIÁC prod (backend bật): /dia-diem render đúng (hero/breadcrumb/highlights/reviews/nearby, detailCssLinked=true), / home nguyên vẹn. `.detail-cover` còn ở entry = 3 dòng base.css (responsive/print, vô hại). Bug bắt được khi build: `*/` trong comment (`.map-*/`) đóng comment sớm → đã sửa. Chi tiết plan gốc:
  - 🟢 (đã thực thi) route-load TOÀN BỘ detail.css: phân tích `scratch/analyze_detail.py`: **97/126 class chỉ dùng ở 3 route chi tiết** (dia-diem/xa-phuong/lich-trinh) → route-load an toàn. Các "leak" generic (`.active/.dark/.on/.peak/.k/.v/.back/.loaded/.ok/.warn/.expanded/.rotated`) là selector-hậu-duệ (`.dark .detail-cover`) → move theo cũng an toàn. **Chỉ ~14 class shared THẬT phải tách ra `detail-shared.css` (giữ global):** `.breadcrumb`,`.bc-back`, `.lightbox`,`.lb-close/counter/img/next/prev`, `.detail-gallery`,`.detail-img`, `.share-btn`, `.cat-accommodation`,`.cat-experience`,`.cat-product`, `.map-filters`, `.highlights`. **Các bước:** (1) cut rule (gồm dark/responsive variant) của ~14 class shared → `assets/css/detail-shared.css`, thêm vào `nuxt.config css[]`; (2) bỏ `detail.css` khỏi `css[]`, `<style src="~/assets/css/detail.css">` ở 3 trang chi tiết; (3) build + verify entry.css giảm ~35KB + QA /dia-diem,/xa-phuong/[id],/lich-trinh/[id] (light+dark). Shared classes giữ global nên cong-dong(lightbox)/bai-viet(breadcrumb)/san-pham(.cat-product)/ban-do(.map-filters)/theo-mua(.highlights) KHÔNG đổi → không cần QA. ⚠️ Là edit lớn 1 file 41KB → làm thành task tập trung, KHÔNG nhồi cuối phiên (§B5 không big-bang).
  - `base.css` 71KB (lớn nhất) = audit prune unused riêng (Backlog).

- ~~**(2026-06-21) 🟡 MED — Flaky test-isolation phụ thuộc thứ tự collection**~~ ✅ **XONG (commit 8ae00af)**: `tests/test_knowledge.py` (`test_search_entities_basic`, `test_places`) + `tests/test_tracing.py` (6 `test_yields_none`) đỏ khi full-suite path tường minh, xanh khi cô lập/root. Gốc: fixture KB gọi `_ensure()` (no-op nếu `_entities` đã set) → test khác để KB global rỗng/nhỏ; `tracing._tracer` khởi tạo lúc import theo `OTEL_ENABLED` (default true) → module cache trước khi test đặt false. Fix độc-lập-thứ-tự (KHÔNG yếu assertion, §3.4): 3 fixture KB (test_knowledge/proactive/agentic_rag) dùng `reload()` khi nghi pollution (`_entities` rỗng/<100); `test_tracing` autouse ép `_tracer=None`+khôi phục. Verify: 1189 passed/0 failed dưới CẢ hai thứ tự collection.

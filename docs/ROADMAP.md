# vinhlong360 — ROADMAP thực thi tự động
> STATUS (2026-08-07): active — sổ track dài hạn + backlog thực thi. Security/CI remediation tranche hoàn tất local qua `4d2c96b4`; đợt 13 commit 2026-08-07 (`c5379506`…`10d9bb69`) trên `codex/tri-region-color` ghi ở mục "Đợt 2026-08-07" cuối file. **Trunk thực tế hiện là `codex/tri-region-color`** (0 commit sau `main`) — xem `HANDOFF-BRANCHES.md`.


> **Cách dùng (đọc kỹ trước khi làm):** Tuân thủ `../CLAUDE.md`. Làm task **đúng thứ tự**. Mỗi task: thực hiện → chạy *Verify* → đạt *Nghiệm thu* mới tick `[x]` và commit. Cuối mỗi Giai đoạn phải pass **Cổng DoD** mới sang giai đoạn sau. Gặp mục 🛑 (Track-H) hoặc tình huống trong §4 CLAUDE.md → **DỪNG, hỏi người**.

**Ký hiệu:** `[ ]` chưa làm · `[x]` xong · `[~]` đang làm · `[!]` bị chặn (ghi lý do) · 🛑 cần người.

**Trạng thái bất biến (luôn đúng):** B1 snapshot trước data-op · B2 additive-first · B3 test trước vùng mù · B6 không re-host bản quyền · B8 free-tier.

---

## TRACK-H — Việc cần CON NGƯỜI (chạy song song, KHÔNG tự làm)

Những việc này **chặn ra mắt công khai** nhưng nằm ngoài code. Claude Code chỉ **nhắc + chuẩn bị tài liệu**, không tự thực hiện:

- 🛑 **H1. Pháp nhân + đăng ký NĐ147/2024** (Giấy xác nhận thông báo, hoặc Giấy phép MXH nếu ≥10k lượt/tháng hoặc >1k user thường xuyên). Cần doanh nghiệp/tổ chức VN; cá nhân thường không đứng tên được. **Đây là blocker launch lớn nhất.**
- 🛑 **H2. Luật sư ICT/dữ liệu** rà: phân loại "MXH + trang tổng hợp" kết hợp; nghĩa vụ chuyển dữ liệu xuyên biên khi host nước ngoài.
- [x] **H3. Remote git đã cấu hình:** `origin` trỏ GitHub; `git push` vẫn cần chỉ đạo trực tiếp của chủ. Hosting hiện tại vẫn là VPS Vultr đã ghi trong HANDOFF.
- 🛑 **H4. Rotate/đặt giá trị secret thật** (`ADMIN_API_KEY`, `LLM_API_KEY`, `TELEGRAM_BOT_TOKEN`) — con người đặt giá trị, Claude chỉ chuẩn bị chỗ. *(Cập nhật 2026-07-07: secret thật ĐÃ đặt trên prod bởi chủ dự án — mục này giờ chỉ còn nghĩa "rotate định kỳ"; lưu ý bẫy `TOTP_ENC_KEY` khi 2FA bật, xem CLAUDE.md §4.)*
- 🛑 **H5. Mua domain / DNS / verify Search Console (DNS TXT) / deploy public.** *(Cập nhật 2026-07-07: domain vinhlong360.vn ĐÃ mua, prod ĐÃ live trên VPS Vultr — do chủ dự án tự thực hiện. Phần còn mở: verify Search Console; và ra-mắt-công-khai đúng nghĩa vẫn chờ H1/H2 pháp lý + đang noindex toàn site chủ động.)*

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
- [x] **5.5** Luồng "Xoá tài khoản & dữ liệu" (UI hoặc form/email handler), đáp ứng hạn 10/15/30 ngày. → *Verify:* yêu cầu xoá → dữ liệu user bị xoá/ẩn danh chậm nhất 30 ngày kể từ yêu cầu. *Nghiệm thu:* quyền xoá + rút consent.
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
- [~] **7.4** (MỘT PHẦN) ✅ **Xoá `web-astro/`** (mồ côi; export_data bỏ ghi astro; build OK). ⏸ Bỏ JS/HTML legacy trong `web/` HOÃN — cần phối hợp `nginx.conf /legacy/`. (Cập nhật: `web/admin*.html` ĐÃ XOÁ — AdminCP nay là Nuxt.) Giữ `web/data.json|media`. (`web/data.js` ĐÃ GỠ 2026-08-22 — `8afdbfb0`; không còn ai đọc.)
- [ ] **7.5** (HOÃN) Gỡ field shim legacy (`coords`,`from`/`to`) — chỉ làm sau khi bỏ hẳn FE legacy `web/` (B2).

**🚦 Cổng DoD-7:** `npm run build` xanh; chỉ còn `web-nuxt`; thêm 1 type test bằng cách đổi DB → UI tự nhận.

---

## GIAI ĐOẠN 8 — Hình ảnh / media

**Tiên quyết:** DoD-3. **Bất biến:** B6 (bản quyền), B8 (free-tier).

- [x] **8.1** Object storage **Cloudflare R2** qua `storage.py` (S3 endpoint/keys). → *Nghiệm thu:* lưu ảnh ~0đ. ✅ DONE + deployed 2026-06-20 (prod `backend: r2`; CDN `cdn.vinhlong360.vn` phục vụ WebP 200).
- [!] **8.2** ~~Ingest Wikimedia/Wikipedia~~ → **SUPERSEDED (chủ chốt):** dự án dùng **CHỈ ảnh AI-gen** (`cx/gpt-5.5-image`, sạch bản quyền) — KHÔNG Wikimedia/stock/UGC. Việc *sinh ảnh nội dung cho entity* chuyển xuống Cổng DoD-8. (xem [[feedback-no-wikimedia-images]])
- [x] **8.3** Pipeline WebP 3 cỡ (400/800/1600), strip EXIF, slug filename → `entity["images"]`. → *Nghiệm thu:* ảnh nhẹ, CLS ổn. ✅ `storage.py:upload_image_set` (Pillow).
- [x] **8.4** Endpoint admin **upload file** cho ảnh entity + duyệt ảnh UGC. → *Nghiệm thu:* admin tự thêm ảnh. ✅ `admin.py` POST `/entities/{id}/images` (add-by-url) + `/entities/{id}/images/upload` (multipart UploadFile).
- [x] **8.5** SEO ảnh: `og:image` + `ImageObject` (license) + **image sitemap**. → *Nghiệm thu:* ảnh được index. ✅ `seo.py` ImageObject[] + `GET /sitemap-media.xml` **phục vụ 200 trên prod** (backlog "404 nginx" đã hết hiệu lực).

**🚦 Cổng DoD-8:** ≥ vài trăm entity nổi bật có ảnh hợp lệ + credit; og:image hoạt động; image sitemap hợp lệ; không ảnh vi phạm bản quyền. **[CODE XONG — còn NỘI DUNG]:** đường ống R2 + WebP + endpoint upload + og:image + image sitemap đều DONE & verified (2026-07-04). Phần chưa đạt = *sinh ảnh AI cho từng entity* (nút thắt nội dung, CHỈ `cx/gpt-5.5-image`; helper `scripts/gen_image.py`). Cần **chủ dự án duyệt dùng image API** + là việc chạy dần, không phải task code.

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

- [x] **11.1** ✅ Sparse-vector TF-IDF (commit 61e766b test trước + 85c1ca3 refactor: `_vectors` dict sparse; 208MB→~5MB, ~41x nhỏ hơn; +19 test; full passed).
- [x] **11.2** ✅ Index kề `_get_adjacency()` cho `related()` (self-healing khi `_relationships` đổi). Verify: adjacency == brute-force trên entity nhiều cạnh. `entity_detail`/`nearby` (hot path) O(degree).
- [x] **11.3** ✅ Precompute BM25 `_doc_tf` lúc build (bỏ `Counter()` mỗi doc mỗi query). 58 test contextual/vector xanh (điểm không đổi). (Contextual re-tokenize 534: BM25 đã xử lý phần nặng nhất.)
- [x] **11.4** ✅ `/reload` nền + atomic swap (commit 62da6ae: `reload()` build+swap dưới `_reload_lock` + vô hiệu adjacency; endpoint qua `asyncio.to_thread`; +4 test gồm concurrency). **→ GĐ11 hoàn tất.**

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

- [x] Sửa entity ở admin → phản ánh ngay ở **cả** chat lẫn Nuxt. *(GĐ3.6 test integration xanh)*
- [x] `validate_data.py` sạch; relationship ~10k. *(audit 2026-06-22: 9505 rels, validate exit 0)*
- [x] 2+ /chat đồng thời không chặn nhau; endpoint nhạy có auth; không call LLM tự động khi load trang. *(GĐ4.1-4.7 xong)*
- [ ] Chỉ còn 1 frontend; thêm type mới không phải sửa nhiều nơi.
- [ ] Entity nổi bật có ảnh; og:image + image sitemap hoạt động.
- [ ] Uptime/analytics/error/cost đo được; eval baseline có điểm.
- [ ] 3 trang pháp lý + consent + report/takedown + xoá tài khoản hoạt động; crawler chỉ trích đoạn.
- [ ] CWV "Good"; CI xanh chạy cả agent/tests + integration.
- [ ] **Launch công khai CHỈ sau khi H1 (NĐ147) + H2 (luật sư) hoàn tất.**

---

## BACKLOG PHÁT SINH (ghi việc ngoài roadmap — KHÔNG tự làm, chờ duyệt)

> Khi phát hiện việc đáng làm ngoài roadmap, ghi vào đây kèm ngày + lý do, rồi tiếp tục task hiện tại.

- **(2026-06-23, gộp 2026-06-27) 📋 AUDIT 10 TẦNG — tàn dư chưa xong** (file gốc `ke-hoach-hoan-thien-10-tang.md` ĐÃ XÓA, gộp phần còn giá trị vào đây). Quét 6 agent: P0 toàn bộ ĐÃ FIX+DEPLOY (P0-1→20). Còn lại:
  - **P1 chưa xong:** P1-13 builder sync tài khoản (localStorage-only, mất plan đa thiết bị; `tao-lich-trinh.vue`); P1-14 lightbox focus-trap + calendar roving-tabindex (`dia-diem/[id].vue`, `le-hoi`, `su-kien`); P1-15 settings allow-list/schema (`site_settings.py:141-171`); P1-20 shape-assert `res||[]` + feature-flag source (`entities.vue:233`, `lich-trinh.vue:286`).
  - **P2 chưa xong:** P2-2 sidebar stats server-side + hydration flash (`cong-dong.vue:305`); P2-3 month-abbr helper 3 kiểu→1 (`index.vue`/`le-hoi`/`theo-mua`); P2-4 fixed-bottom stack mobile (JourneyBar+FAB+bookmark); P2-8 phone mask admin CSV (`users.vue:92`, `bao-cao.vue:83`); P2-9 hex→token CSS (admin ~447 hex); P2-10 `requirements.lock` + commit `package-lock.json`; P2-11 `except: pass` → log warning (`middleware.py:98`, `autonomous_budget.py:62`).
  - **Data-contract FE↔BE (chuẩn hóa):** error envelope 4 kiểu (`{detail}`/`{error}` JSONResponse/HTTP-200/in-band) → chuẩn 1 `{detail}` + HTTPException; pagination 4 kiểu → chuẩn `{items,total,page,limit,has_more}`.
  - **Chat pipeline (resilience):** stream path không circuit-breaker/retry/KB-fallback; `weather`/`web_search` breaker định nghĩa nhưng chết (`circuit_breaker.py:399,407`); cost dùng ước lượng không đọc `usage` thật.
  - **CỐ Ý KHÔNG LÀM:** error-helper-sweep (40+ site chạy đúng runtime), @nuxt/fonts-remove (no-op), catalog.css-split (rủi-ro>lợi ~6KB), hardcoded-colors 558 (admin-internal).
- **(2026-06-22) 🔬 AUDIT SÂU 3 LƯỢT ĐA-AGENT → `docs/archive/audit-findings-20260622.md`** — historical snapshot; các status line bên dưới đã hấp thụ và thay thế trạng thái của snapshot này. (110 finding verified: 3 crit, 26 high, 46 med, 35 low + audit-3 scan-only). Đã FIX: ARCH-001 (province area). Lộ trình sửa đề xuất theo rủi-ro:
  - **P0 vận hành/bất-biến:** ✅CLP-01 memory_graph gate (§B8, +test) · ✅SEC-001 OTP leak · ✅SEC-002 XFF spoof · /graph no-auth = KHÔNG sửa (KB public theo thiết kế). CÒN: CONC-001 (sync OpenAI in event loop §4 — cần refactor async + test) · EH-01/02 generate_followups+json.loads no-timeout/guard.
  - **P1 dữ liệu §1.4:** ✅admission_fee alias · ✅9 transposed coords (+49 ngoài-bbox → null) · ✅siết bbox validator. CÒN: 16 dup entity · 169 orphan. ⚠️ **HUỶ mục "68 summary/37 address sai tỉnh" (2026-07-07):** quy tắc DF-02 đã ĐẢO NGƯỢC sau sáp nhập — "tỉnh Vĩnh Long" trong entity BT/TV cũ nay là cách gọi ĐÚNG; KHÔNG chạy lại. Việc đúng chiều nằm ở Backlog truth-sync bên dưới (campaign 513 text tỉnh-cũ).
  - **P2 DB/script:** ✅guard optimize_data.py + gỡ bịa produced_in. CÒN: replace_from_json atomic + description round-trip (test trước §B3) · ETL-03/04 migrate_sap_nhap+fix_audit_safe key.
  - **P3 perf/FE/deploy:** ✅maplibre lazy→build OOM fix→ĐÃ deploy FE note. CÒN: PG pool · N+1 places_in_area · FE null-safety coords (xa-phuong/lich-trinh) · SEO breadcrumb/ogImage/CWV.
  - **ĐÃ DEPLOY prod (2026-06-22):** 9 nhóm fix (f2e5658→7727b02) + resilience (15a372c) + dedup 2 entity (4f1dded) + DF-02 address-tỉnh-cũ 235 + 69 orphan-link (11e68ea). Data 1789e/9371r.
  - **DƯƠNG-TÍNH-GIẢ/LOW (verify-by-check, KHÔNG sửa):** Vàm Ray "×4" dup (chỉ 1 Vàm Ray + 1 Samrông Ek khác nhau); coord-dup (centroid placeholder); F3 description round-trip (description RỖNG toàn bộ, admin-only qua update_description); /graph no-auth (KB public); GS-02 ward→vinh-long (đúng sau sáp nhập); audit-3 .env-leak (gitignore đúng).
  - **✅ ĐÃ SỬA (refactor test-first):** replace_from_json **PG atomic** (1 transaction qua _bulk_load, +2 test) · **CONC-001** async SSE (to_thread + queue-bridge, +test concurrency) · **FE null-safety** coords (normalizeCoords ở xa-phuong/lich-trinh/tao-lich-trinh) · SEO-01 breadcrumb · SEO-04 double-noindex.
  - **✅ HOÀN TẤT NỐT (2026-06-22):** D02 PG-pool (ThreadedConnectionPool + fallback + kill-switch PG_USE_POOL, +2 test) · A11Y-01 (token --amber-700) · SEO-03 (JSON-LD url=canonical) · CWV (lightbox lazy; component chính ĐÃ NuxtImg sẵn). N+1 = VERIFIED non-issue (in-memory O(1)).
  - **🟢 CAMPAIGN AUDIT XONG:** mọi finding critical/high/§1.4 + perf khả-thi đã fixed+deployed. Còn lại đều là dương-tính-giả (Vàm Ray, F3, /graph, GS-02, .env) hoặc one-off script (ETL-03/04, không auto-run) — KHÔNG cần sửa. Baseline 1197.
  - DƯƠNG-TÍNH-GIẢ (KHÔNG sửa): GS-02 (ward BT/TV→vinh-long là đúng sau sáp nhập); audit-3 .env-leak (đã verify gitignore đúng).

- **(2026-06-20) 🌟 WORLD-CLASS HARDENING** (audit 10 chiều, 5.5/10 → memory `project-worldclass-roadmap`). Verdict: KHÔNG "thô sơ" mà thiếu nội dung + vài bug data-shape. Lộ trình 5 phase; mỗi phase build+test+preview+**prod-verify** (không deploy mù).
  - **P0 ✅ DEPLOYED (commit 579ee38):** fix bug `source` dạng LIST (877 entity rớt nguồn → emit JSON-LD citation/sameAs); canonical dedup (đúng 1/trang); og:image chỉ ảnh thật; contrast `--ink-tertiary` + token `--accent-text` AA; quarantine 11 summary rác "404/không đủ thông tin" + guard `validate_data.BOILERPLATE_SUMMARY` (ERROR); geocode 6 entity coordless qua centroid + xoá 75 near-edge vô nghĩa → **lỗi "77 near thiếu toạ độ" RESOLVED** (validate exit 0); `sitemap-media.xml`.
  - **P1 ✅ DEPLOYED (commit 4f9309c, đa-agent workflow investigate→implement):** placeholder SVG gradient deterministic theo id (prod 239/239 card, hết stock-tile lặp); hero motif vùng Mekong (catalog `::before`); `.reveal` hiện-khi-không-JS (html.js gate + inline head script); `useModalA11y` (focus-trap + scroll-lock + ESC, `immediate` watch) + modal max-height/internal-scroll (sửa keyboard-trap); thang z-index token; khối provenance "Nguồn·Cập nhật·Báo sai" → report flow; trang `/gioi-thieu` (+ AboutPage/Organization JSON-LD) + link footer. **2 bug bắt nhờ preview-verify + fixed:** data-uri quote → SSR hydration style mismatch; modal watch thiếu `immediate`.
  - **P2/P3/P4 backend 🔄 đang implement (đa-agent, file rời nhau):** JSON-LD ImageObject/BreadcrumbList/ItemList; coverage-metrics + CI gate; verified-timestamps (không bịa ngày); error-capture free-tier (`POST /api/client-error` → log, KHÔNG Sentry — B8); B3 tests write-path auth/UGC/moderation; image **review-queue** (duyệt tay, KHÔNG auto-publish — B6).
  - **⛔ CHẶN — chờ chủ dự án:** (a) PUBLISH ảnh thật (B6 + Wikimedia khớp tên sai ~50% → bắt buộc review-gate); (b) enrich mô tả hàng loạt bằng LLM (B8 — cần `AUTONOMOUS_AGENT_ENABLED=true` + cap); (c) dữ liệu văn phòng phường (Track-H — không bịa).
  - **Hạ tầng:** `scripts/deploy.sh` đóng gói flow deploy + mọi gotcha (live output `web-nuxt/.output`; `rm -rf` trước extract; `--replace` có khoá B7 + backup DB; KHÔNG đụng `.env`).
  - **Backlog nhỏ phát sinh:** ~~`tests/test_config.py::test_defaults` phụ thuộc env runner~~ ✅ XONG (monkeypatch.delenv + `_env_file=None`); `CategoryIcon.vue` giờ không card nào dùng (cleanup candidate — rà nơi khác trước khi xoá); admin editor "Về chúng tôi" cần seed key `page.about` (`seed_site_settings.py`) mới lưu được (trang public chạy bằng fallback nên OK); CSS split `entry.css` 167KB→<60KB (P3-perf, hoãn — refactor lớn).

- ~~(2026-06-13) GĐ3.1 — UGC/auth → SQLite~~ ✅ ĐÃ QUYẾT (Postgres-only): không port; `_require_pg` gắn 3 router UGC trả 503 trên SQLite; tài liệu CLAUDE.md §1.3 + docs/architecture-decisions.md #3. Lý do: dev/prod parity, tránh nợ 2 phương ngữ SQL, UGC vốn cần Postgres.
- ~~(2026-06-13) GĐ3.8 — data-quality DB-native~~ ✅ XONG (commit 35ff28e): apply/rollback ghi thẳng DB, bỏ khoá. Footgun "xoá edit admin" đã gỡ.
- **(2026-06-13) GĐ11 phần còn lại**: ~~(a) 11.1 sparse-vector TF-IDF~~ ✅ XONG (commit 61e766b test trước + 85c1ca3 refactor: `_vectors` dict[eid,{token:weight}] thưa; benchmark 1703 entity → 5.08MB vs 208MB dense (~41x), 0.263% mật độ; +19 test; full 1084 passed; cache thật đã regenerate sparse); ~~(b) 11.4 `/reload` nền + atomic swap~~ ✅ XONG (commit 62da6ae: `reload()` build+swap dưới `_reload_lock` + vô hiệu adjacency; endpoint qua `asyncio.to_thread` → không đóng băng /health; +4 test gồm concurrency). **→ GĐ11 hoàn tất.**
- **(2026-06-13) GĐ10 phần còn lại — chưa làm**: (a) 10.1 hybrid prerender (cần pipeline build có backend); (b) QA browser map clustering (env có ndaMapKey); ~~(c) sửa mojibake `admin/data-quality.vue`~~ ✅ XONG (commit ee8cc40: 19 dòng tái dựng byte per-char); (d) siết `any` (146 chỗ); ~~(e) rà clickable `<div>` toàn site → `<button>`~~ ✅ XONG (commit 1626dd8: index card→NuxtLink, tao-lich-trinh→button; 4 div @click.self còn lại là backdrop hợp lệ).
- ~~**(2026-06-13) GĐ6 stub — chưa dọn**~~ ✅ XONG (commit 517cc4e): gỡ stub 7 module đã xoá (relay/streaming/advanced-graph/a2a/knowledge-evo/multimodal/federation) khỏi `server.py` (−221 dòng: import/flag/~15 endpoint/3 model/feature-list/startup-print) + `scheduler.py` (2 task disabled) + test model dead. GIỮ self_optimizer/semantic_cache/llm_judge/dynamic_agents (còn sống) + HAS_OPTIMIZER (hot path). Full 1085 passed; smoke boot 11 passed.
- **(2026-06-13) GĐ5 phần còn lại — chưa làm**: (a) lưu timestamp/version consent vào DB (cột PG ở `users`); (b) GĐ5.6 đổi crawler/import sang lưu trích-đoạn+link (bản quyền) trước khi bật lại crawl; (c) 🛑 Track-H: pháp nhân + đăng ký NĐ147 + luật sư ICT — CHẶN ra mắt công khai.
- **(2026-06-13) GĐ13 phần còn lại — chưa làm**: (a) 13.1 owner-portal đầy đủ (claim record + admin duyệt + owner tự-sửa — Postgres/UGC, cần test với PG); (b) 13.8 QR-ảnh (dep `qrcode`); (c) 13.6 nạp dữ liệu danh bạ thật 124 đơn vị (Track-H/B2G); (d) 13.9 premium listing + hợp đồng B2G (Track-H); ~~(e) mục "Danh bạ" trên trang `khu-vuc/[area]`~~ ✅ XONG (commit 6093277: chip → `/danh-ba?area=` + pre-scope optgroup); ~~(f) nút báo-sai facility gắn /api/report~~ ✅ XONG (commit b6f9cdb: `POST /api/report` ghi reports.jsonl + rate-limit + `GET /admin/info-reports` + nút báo-sai trên danh-ba). ~~*(Còn: wiring PostCard "Báo cáo" → /api/report cho UGC = follow-up nhỏ.)*~~ ✅ XONG (commit 34021c6: `useReport` composable + `@report` trên cong-dong/bai-viet/nguoi-dung).
- **(2026-06-14) Design System (kế hoạch `docs/design-system-plan.md`)** — từ deep-research "thiết kế giao diện" (chủ duyệt). Giữ CSS thuần + tokens (KHÔNG Tailwind), giữ hệ màu hiện tại. 5 bước additive: ~~(1) hệ thống hóa tokens 3 tầng + thang typography/spacing 8pt~~ ✅ XONG; ~~(2) audit tương phản WCAG AA~~ ✅ XONG (muted #586860, white→ink trên amber-dark, token `--border-input` ≥3:1; 44px+focus đã sẵn; dark brand-as-text hoãn Bước 4); ~~(3) self-host font `@nuxt/fonts` + ảnh `@nuxt/image` (weserv, off-VPS)~~ ✅ XONG; ~~(4) dark mode toggle `@nuxtjs/color-mode` + tách brand fg/bg (`-fg` tokens, dark lighten ≥4.5:1) + dark surfaces (`#fff`→`--card`)~~ ✅ XONG; ~~(5) JSON-LD Schema.org~~ ✅ ĐÃ CÓ SẴN 17 trang + bổ sung `inLanguage`. **→ Design System hoàn tất Bước 1–5.**
- **(2026-06-13) GĐ7 phần còn lại — chưa làm**: (a) `/api/constants` + Nuxt fetch để unify FE+BE constants (giờ `useConstants.ts` là nguồn FE duy nhất, chấp nhận được); (b) bỏ JS/HTML legacy trong `web/` + sửa `nginx.conf /legacy/` (giữ data.json/media — `data.js` đã gỡ 2026-08-22 `8afdbfb0`, `admin*.html` đã xoá từ GĐ6.1); (c) gỡ field shim `coords`/`from`/`to` sau khi bỏ FE legacy.
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
  - ✅ `base.css` 75KB→70.5KB (−4.6KB): prune 50 dòng dead CSS (interest-grid, route-preview, journey-card/group, feed-layout, dark overrides) — commit 0e3b059.

- ~~**(2026-06-21) 🟡 MED — Flaky test-isolation phụ thuộc thứ tự collection**~~ ✅ **XONG (commit 8ae00af)**: `tests/test_knowledge.py` (`test_search_entities_basic`, `test_places`) + `tests/test_tracing.py` (6 `test_yields_none`) đỏ khi full-suite path tường minh, xanh khi cô lập/root. Gốc: fixture KB gọi `_ensure()` (no-op nếu `_entities` đã set) → test khác để KB global rỗng/nhỏ; `tracing._tracer` khởi tạo lúc import theo `OTEL_ENABLED` (default true) → module cache trước khi test đặt false. Fix độc-lập-thứ-tự (KHÔNG yếu assertion, §3.4): 3 fixture KB (test_knowledge/proactive/agentic_rag) dùng `reload()` khi nghi pollution (`_entities` rỗng/<100); `test_tracing` autouse ép `_tracer=None`+khôi phục. Verify: 1189 passed/0 failed dưới CẢ hai thứ tự collection.

### 🐛 Backlog phát sinh — Bug-hunt 2026-06-24 (đa-agent + runtime)
> Truy-quét sau khi fix bug SSR-fetch lớn. ĐÃ FIX trong phiên: (a) **~18 trang catalog rỗng entity** do internal `$fetch` SSR fail → `utils/apiFetch.ts` (commit 6d2cd22/e6ac8b8); (b) **feed `?area=` rỗng** (social.py dùng `attributes->>'area'` thay cột `area`); (c) **search `?q=` bỏ qua offset** → phân-trang lặp vô-hạn (database.search_entities thêm offset + ORDER BY confidence,id; public_api truyền offset + total đúng khi q+month). Còn lại (chưa làm, cần cân-nhắc/duyệt):
- **[Data/§B7] 37 entity `type='place'` phân-loại nhầm** (ngân-hàng/quán ăn/bệnh-viện/bến-xe…, `level=None`) vẫn lọt `/api/places` thô (162 = 124 xã/phường thật + 37 cơ-sở + 1 tỉnh). **Số xã/phường CHÍNH-XÁC = 124** (chủ xác-nhận; 89 xã+35 phường). ✅ ĐÃ FIX hiển-thị (commit b97cff2): `get_stats.places` đếm `level IN (xa,phuong)`=124 + danh-ba bỏ 'tinh' → trang chủ & danh-bạ đều 124. ✅ **ĐÃ RECLASS (chủ duyệt, commit f07691f, deploy --replace 20260624-171921):** 12 quán/nhà-hàng→dish; 24→facility (y_te/buu_dien/cong_an/khac); Chùa Vạn Phước→attraction. `/api/places` sạch còn 125 (124 ward + 1 tỉnh); facilities hiện trong danh-bạ xã/phường (vd p-ben-tre có 5).
- ✅ **[Med/Perf] ĐÃ FIX (commit 8a22845):** `get_relationships()` SQL-side filtering (rel_type/include_near vào WHERE thay vì Python-side); `return_total` bỏ `count_relationships()` thừa ở entity detail + relationships endpoint (3→2 DB calls); `get_entities_batch()` bỏ N+1 ở itinerary endpoint; `_enrich_place()` batch-warm cache thay N lần `get_entity()`.
- ✅ **ĐÃ HARDEN (commit phiên 2026-06-24): 9 chỗ FE SSR-fetch → apiFetch** (dia-diem/[id], bai-viet/[id], xa-phuong/[id], nguoi-dung/[id], lich-trinh-chia-se/[id], NearbyEntities, tim-kiem×3) — đồng-bộ pattern chống silent-empty. CHỪA `site-overrides.ts`/`useSiteSettings.ts` (fallback graceful + chạy mọi-trang → +latency không đáng). Verify detail pages render 200. **CÒN [Low]:** chuyển 2 file site-settings nếu muốn tuyệt-đối đồng-bộ.
- ~~**[Low/SEO] `/sitemap-media.xml` + 4 child sitemap** 404~~ ĐÃ HẾT HIỆU LỰC (trùng 8.5: prod đã phục vụ 200 — gạch 2026-07-07, trước đó mục này mâu thuẫn với dòng 148).
- ✅ **[Low] ĐÃ FIX (commit f0acf13):** `toggle_follow` guard entity tồn-tại trước khi follow (chống bản-ghi rác).
- **[Content] ~42 entity mô tả mỏng (<120 ký tự)** — đã giảm từ 341→203→42 (2026-06-25): 41 place + 1 product. Place descriptions generated from child entities (đúng pattern). Còn lại cần chủ dự án bổ sung nội dung — KHÔNG bịa (§1.4).
- ✅ **[Low/Coupling] `export_data.py` đã phục hồi an toàn:** exporter thủ công hiện có dry-run, ghi atomic và yêu cầu backup trước khi ghi thật; nợ còn lại là tự động hóa freshness DB→data.json.
- **[Low/Safety] `freshness.py` ghi `refresh_queue.json` không atomic** — dùng `open("w")` trực tiếp, crash giữa chừng sẽ corrupt file. Nên chuyển sang pattern `.tmp` + `os.replace()`. (Phát hiện: backend-infra session 2026-06-26)
- ✅ **[Arch/Done] Entity content-model + CTI:** GĐ-A/B/C đã hoàn tất; `entities` vẫn là bảng xương sống và 9 bảng CTI đang live. `docs/superpowers/specs/2026-07-02-entity-split-per-kind-design.md` là authority hiện hành.

### Backlog phát sinh — Declutter Đợt 3 (2026-07-07)
- **[Content/Pipeline] KBYG data rỗng toàn cục**: golden_hours/kbyg_tips/checklist/amenity_badges = 0% trên 1730 entity — khối KnowBeforeYouGo hầu như không render. Cần pipeline content đổ data (A8a HOÃN vô hạn tới lúc đó).
- **[Đo rồi mới cắt] chat-DAU + interstitial-CTR**: quyết định mở rộng ẩn ChatWidget sang detail khác (lich-trinh/xa-phuong/bai-viet) và số phận CatalogInterstitial cần số liệu sử dụng thật trước.
- **[Hỏi chủ] wards-row khu-vuc bỏ hẳn?**: Đợt 3 đã thu gọn thành <details> (giữ 124 link hub-spoke trong DOM cho crawler). Muốn xoá hẳn khỏi DOM cần chủ duyệt riêng (đánh đổi SEO hub-spoke).
- ✅ **[Test-debt resolved 2026-07-26]** 3 lỗi cost-tracker UTC-boundary đã sửa ở `3e707bff`; sitemap mock/index-policy drift đã sửa ở `40cc226e`. Focused recheck `tests/test_cost_tracker.py tests/test_seo.py`: 40 passed; không còn fail-đã-biết từ nhóm này.
- **[A11y/Redesign] season-ring theo-mua tap-target <44px**: 12 notch trên vòng 76px mobile — hình học không cho phép 44px không-chồng-lấn (đo 11/12 tap sai khi nới). Muốn đạt chuẩn phải phóng vòng ≥170px (redesign hero). month-grid hiện là fallback a11y — GIỮ.

### Backlog phát sinh — Truth-sync docs (2026-07-07, audit 89+6 finding)
- **[P0/Data] Campaign sửa ~513 text 	ỉnh Bến Tre/Trà Vinh trong data** (hệ quả DF-02 chạy 06/2026, nay ngược chiều): rewrite CÓ NGỮ CẢNH (hiện-tại → 	ỉnh Vĩnh Long; lịch sử → thêm cũ/trước 7-2025), KHÔNG batch-replace mù. Bắt buộc: backup B1 + sửa trên DB (SoT) + đồng bộ prod PG + regenerate data.json. Cần plan riêng.
- **[P1/Content] Sweep filler miền Tây trong copy site** (editorial du-lich/san-pham/theo-mua, eyebrow ĐBSCL · VL—BT—TV…): thay bằng đặc-thù-Vĩnh-Long theo playbook — đi cùng campaign trên.
- **[P1/Infra] Tự động hóa freshness DB→data.json** (một chiều, có kiểm tra diff) — exporter thủ công đã phục hồi qua `scripts/export_data.py` và admin `POST /export`, nhưng chưa có cơ chế tự động đồng bộ từ PostgreSQL prod.
- **[P2/Docs] b2g-pitch cần chủ duyệt lại TOÀN VĂN trước khi gửi bất kỳ đối tác nào** (đã sửa claim khống nhưng đây là tài liệu đối ngoại — CLAUDE.md §4).

### Backlog phát sinh — SP6 Content (2026-07-07)
- ✅ **[P1/Test-hygiene resolved] test_kb_curation.py không còn ghi fixture vào DB thật:** `af37bb5a` chuyển write-through test sang `isolated_sqlite_db`; `23b9803b`/`343ca3f8` khóa guard test-isolation. Recheck 2026-07-27: `agent/tests/test_kb_curation.py` + `tests/test_entity_test_isolation.py` đạt `45 passed`; chạy riêng curation đạt `17 passed` và SHA-256 `agent/data/vinhlong360.db` giữ nguyên `74F220A681B7F1F7BC1B297C1D3AE84DCE21C7EE0106BF6E03FABFCFAA0B4121` trước/sau.
- **[P2/SEO] SP6.2 siết is_index_worthy lên 150 từ**: cần làm dày 159 trang dải 130-149 trước, tránh sitemap co đột ngột.
- **[P2/Data] Đổi id chom-chom-binh-hoa-phuoc-rambutan → chom-chom-binh-hoa-phuoc** (slot đã trống sau xoá HOLD): ảnh hưởng URL/prerender/sitemap — task riêng.

### Backlog phát sinh — Chuẩn-hoá R20.8 server.py (2026-07-10)
- **[XONG 2026-07-10] Phục hồi chat integration coverage** (test_chat_smoke.py + test_chat_tools.py): fixture `server.client` lỗi thời → sửa patch `server.get_client`; lifespan không reset `_draining` lúc startup → reset (defensive). test_chat_tools 14/14 + test_chat_smoke 22/22 pass (34 test, 7 stale-drift sửa khớp hành-vi-thật: 4× create→201, gate all-env, W6.2 detail-shape, bulk-delete body, source shape-agnostic). Nhờ đó refactor an toàn _build_messages (R20.8 4→3, golden byte-identical). **Ghi chú:** test_chat_smoke KHÔNG cần PG cho 22 test này (admin/entity/relationship chạy SQLite; UGC/auth vẫn 503-degrade đúng thiết kế). 6 test PG-index (test_session_be TestPhase14PgIndexes) vẫn cần Postgres — known-baseline.
- **[P3/Defer có-lý-do] R20.8 = 3: chat(111)/chat_stream(97)/event_stream(62)** — request/stream handler essential-complexity (event_stream = async-generator 10-yield, state đan xen; ép ≤12 = nhiều sub-generator = helper-soup nuốt-context, khó golden-test streaming). Chỉ mở nếu có nhu cầu thực + cách verify streaming an toàn. Xem 90-exceptions-log.md.

### Security/CI remediation tranche (2026-07-26)
- ✅ **Hoàn tất local, final review READY:** fail-closed moderation/publication (`391ad233`, `5fd633cd`, `4d2c96b4`), truthful rollback (`bbb0c51a`), metrics cold-start (`2b8770bc`), coverage ratchet (`be8c0d33`), R20.7 test pairing (`7cc7edce`), CSV formula neutralization (`573f1c6a`), và PostgreSQL knowledge seed wiring (`74e8d85d`). Không push/deploy.
- **PostgreSQL runtime gap:** CI static contract đã khóa thứ tự migrations → `python agent/database.py --replace` → pytest, với destructive flags chỉ scoped ở seed step. Vẫn cần GitHub Actions `test-pg` làm runtime proof trước khi bỏ các PG-only skip.
- ✅ **Plan A — trust/scanner correctness:** `attributes.verifiedAt` là nguồn duy nhất cho claim kiểm-chứng-thực-địa từ normalize/API/export đến byline; top-level `verifiedAt` không còn được đọc hay mirror. Repository duplicate checks chỉ xét Git-index members; package checks xét immutable snapshot members đúng bằng byte sẽ archive. Không rewrite DB hoặc `web/data.json`.
- ✅ **P1 shared pinned outbound HTTP client, nay bound-complete:** `agent/pinned_http.py` vẫn sở hữu public-address policy, exact-sockaddr dialing, peer verification, TLS hostname/SNI và redirect validation. Mỗi mapped GET (admin image review, auto-learn, crawler, Nominatim geocode, GPT-5.5 quality-burst, OpenWeatherMap realtime) nay truyền `EgressPolicy` với encoded/decoded cap riêng, bounded `identity`/`gzip`, DNS admission tối đa 4 daemon lookup thread, và một absolute monotonic deadline cho cả chuỗi.
- ✅ **Production composition được test cục bộ, deterministic:** `_PinnedHTTPTransport` thật + `httpcore.ConnectionPool` thật phát request và xử lý fixed/chunked response qua local socket pairs; peer mismatch chặn trước HTTP/TLS bytes, zero-send và closed-readability được map thành typed failure.
- ⚠️ **Lỗ SSRF phát hiện SAU khi migrate xong, đã vá trong cùng tranche:** audit đối kháng phát hiện `ipaddress.is_global` trên Python 3.14 trả `True` cho `fec0::/10` (CPython bỏ site-local khỏi `_private_networks` theo RFC 3879), nên policy từng CHO QUA `fec0::1`, `fec0:0:0:ffff::1` (DNS server site-local mặc định cũ của Windows), `::ffff:0:7f00:1` (IPv4-translated RFC 2765 nhúng `127.0.0.1`) và `192.88.99.1` (6to4 relay anycast). Đã deny cả 4 + 7 dải cùng họ; 0 regression (public IPv4/IPv6 và 2 biên `192.88.98.255`/`192.88.100.0` vẫn qua). **Bài học: không uỷ thác toàn bộ quyết định "public" cho `is_global` của stdlib — nó đã drift theo RFC.**
- ⚠️ **Pinning từng có thể bị vô hiệu hoá mà không test nào đỏ:** `network_backend=_PinnedNetworkBackend(hop)` là dòng DUY NHẤT làm pinning có hiệu lực, và trước đó không test nào assert nó; httpcore mặc định `SyncBackend()` tự resolve DNS qua `socket.create_connection`. Đã thêm contract test.
- **R20.8 baseline 3 → 14 — nợ CŨ vừa lộ, KHÔNG phải nợ mới:** BOM UTF-8 trước shebang trong `agent/gpt55_quality_burst.py` khiến `check_complexity.py` (ast.parse trong `except SyntaxError: continue`) bỏ qua file im lặng → 11 vi phạm có sẵn chưa từng được đếm. Đo trên cùng cây mã: BOM còn → 3; BOM gỡ → 14. Một session độc lập song song đi đến đúng cùng con số. Giải trình ở `docs/standards/90-exceptions-log.md`. Checker nay đọc `utf-8-sig`; toàn repo không còn file `.py` mang BOM.
- **Bằng chứng final gate (2026-07-27, revision `de7efa3fbc26cb04430bc3e6f98afe50fef48724`, đo thật):** focused pinned suite `303 passed in 22.36s`; frontend test ownership/hook stability commit `de7efa3f` → `npm test` exit `0`, `37` files/`912` tests passed in `30.49s`; typecheck exit `0`, build exit `0` (`746 modules`, `6.45 MB`, manifest đúng revision); `run_hard.py --all` → exit `0`, `hard=0`, ratchet không tăng; `git diff --check` → exit `0`; official bounded backend → exit `0` in `6901.2s`, Phase A `8633 passed, 58 skipped, 111 deselected, 1 xfailed` in `1152.25s`, Phase B `284 passed, 19 skipped` in `5739.98s`.
- ✅ **P1 egress observability đã giải local:** commit `f2b50bbb` thêm đúng một warning đã sanitize tại boundary `PinnedHTTPClient.get()` cho `blocked_address`, `peer_mismatch`, `redirect_policy`; các consumer hiện dùng context cố định `admin_image_review`, `auto_learn`, `crawler`, `geocode`, `quality_burst`, `realtime_weather`. Exception typed và hành vi consumer giữ nguyên. Commit test-hygiene `8e4bf9be` dọn leak `_draining` giữa integration/admin tests và selector chat lỗi thời; fresh coverage baseline đạt `8726 passed, 66 skipped, 26 deselected, 1 xfailed`. Review-fix `15f7124a` khóa mutation bỏ catch auto-learn phải đỏ nếu raw URL warning quay lại.
- **Bằng chứng observability final gate (2026-07-27, long-gate candidate `8e4bf9bef3c6c6949c4d22185ca8518591eef276`, đo thật):** focused pinned/consumer `319 passed in 19.11s`; Ruff exit `0`; `run_hard.py --all` exit `0`, `hard=0`, ratchet không tăng; `git diff --check` exit `0`; official bounded backend exit `0` in `5024.4s`, Phase A `8649 passed, 58 skipped, 111 deselected, 1 xfailed` in `1069.44s`, Phase B `284 passed, 19 skipped` in `3941.27s`. Assertion-only review head `15f7124a` sau đó đạt focused `319 passed` và `hard=0`.
- ✅ **P2 cookie-gate đã giải local:** `PinnedHTTPClient` có jar cookie bounded, chỉ sống trong một GET chain; hỗ trợ `Set-Cookie` cho consent redirect về cùng URL, loop không có state mới vẫn bị chặn, và cookie được giới hạn theo host/domain, path, `Secure`, tên/giá trị/số lượng. Không log raw cookie và không nới redirect/SSRF policy. `tests/test_pinned_http.py` đạt `251 passed`.
- ✅ **Crawler authority escape + origin pin đã giải local:** `BASE_URL + path` từng biến `@evil.tld/x` thành userinfo và khiến httpx dial `evil.tld`; `path` đến từ danh sách URL do LLM trích xuất. Crawler nay ghép URL bằng `httpx.URL.join()`, từ chối target khác origin/credentialed trước request, dùng `PinnedHTTPClient` với body/decompression/deadline caps, và `EgressPolicy.allowed_origins` chặn redirect khác host/scheme/port trước DNS/dial. Regression `tests/test_crawler_ssrf.py` đạt `7 passed`.
- **Bằng chứng crawler gate (2026-08-03):** focused crawler+pinned+registry `264 passed`; Ruff sạch; `run_hard.py --all` đạt `hard=0`, ratchet không tăng. Official Phase A đạt `9127 passed, 78 skipped, 113 deselected, 1 xfailed` nhưng có 2 maintenance path-validation timeout; chạy lại đúng 2 test đạt `2 passed`, toàn file đạt `16 passed, 3 skipped`. Phase B đạt `120 passed, 18 skipped` trước khi một xdist worker crash tại test SIGKILL recovery; test đó chạy lại serial và đúng cấu hình `-n 2` đều đạt `1 passed`. Không ghi full baseline là xanh tuyệt đối vì hai lỗi timing/worker không tái hiện vẫn xuất hiện trong lần chạy nguyên khối.
- ✅ **Nominatim exact-origin pin đã giải local (`5e8a21c6`):** `_query_nominatim()` encode bộ tham số cố định rồi gọi `PinnedHTTPClient` với context `geocode`, cap 64 KiB encoded/256 KiB decoded, accepted `gzip`/`identity`, inactivity + whole-chain deadline 15 giây, tối đa 2 redirect và allowlist đúng origin Nominatim. Redirect off-origin bị chặn trước lần DNS/dial kế tiếp; status/JSON/bbox validation, 1.1 giây politeness rate-limit, cache hit/miss và offline-safe `None` không đổi.
- **Bằng chứng geocode gate (2026-08-04):** regression RED trước implementation xác nhận direct `requests.get`, thiếu import/policy/audit context và registry còn coi geocode là unpinned; GREEN sau migration đạt focused geocode+registry `19 passed`, broad pinned + mapped consumers + geocode `351 passed in 38.84s`, changed-file Ruff sạch, `git diff --check` sạch và `run_hard.py --all` đạt `hard=0`, ratchet không tăng. Ba `F401` ngoài scope được phát hiện trong full-repo Ruff đã được dọn riêng sau đó tại `6d2e9d8f`. Không chạy lại monolithic backend cho commit nhỏ này; baseline gần nhất vẫn là evidence crawler ngay trước đó.
- ✅ **OpenWeatherMap exact-origin pin đã giải local (`c9e203eb`):** `get_weather()` encode lat/lon/API key/units/lang rồi gọi `PinnedHTTPClient` với context `realtime_weather`, cap 64 KiB encoded/256 KiB decoded, accepted `gzip`/`identity`, inactivity + whole-chain deadline 10 giây, tối đa 2 redirect và allowlist đúng origin OpenWeatherMap. Redirect off-origin bị chặn trước lần DNS/dial kế tiếp; security denial không tạo warning consumer thứ hai. Lỗi transport chỉ log area + loại exception, không log raw exception/URL/API key. Live-result cache 30 phút, seasonal fallback, output fields và server circuit-breaker path không đổi.
- **Bằng chứng realtime gate (2026-08-04):** regression RED trước implementation xác nhận direct `httpx.get`, thiếu import/policy/audit context, registry còn coi realtime là unpinned và injected client không được dùng; GREEN sau migration đạt focused realtime+resilience-logging+registry `14 passed`, broad pinned + mapped consumers + geocode + realtime `359 passed in 36.82s`, full `agent/tests/test_resilience.py` `173 passed, 1 skipped`, changed-file Ruff sạch, `git diff --check` sạch và `run_hard.py --all` đạt `hard=0`, ratchet không tăng. Không chạy lại monolithic backend cho commit nhỏ này.
- ✅ **Ruff test-hygiene đã giải local (`6d2e9d8f`):** `tests/checks/test_erasure_lifecycle_complexity.py` có ba import dưới `TYPE_CHECKING` nhưng không dùng, khiến `python -m ruff check .` đỏ dù complexity gate vẫn chạy đúng. Đã xóa duy nhất sáu dòng dead import; `TARGET_FILES` và assertion `violations == []` giữ nguyên. Focused test `1 passed`, full-repo Ruff sạch, `git diff --check` sạch và hard ratchet vẫn `0`.
- **Residual egress thật còn lại:** `tests/test_pinned_http_consumers.py::KNOWN_UNPINNED_FETCHERS` giờ chỉ ghi nhận `scheduler._digest_send` và `scheduler._send_telegram_admins`; cả hai là Telegram POST và nằm ngoài contract GET hiện tại. Production behavior vẫn chưa được quan sát vì chưa có deployment được uỷ quyền riêng.
- **Operational non-actions:** không push, deploy, production mutation, secret change hoặc indexing change; production behavior chưa được quan sát cho đến một deployment được chủ dự án uỷ quyền riêng; WAL/SHM không bị chạm.

### Backlog phát sinh — Test-isolation / suite flaky (2026-08-06)
- ✅ **Đã sửa (`3c66ad31`, nhánh `codex/tri-region-color`):** hai rò trạng thái module-level phát ra từ `agent/tests/test_resilience.py` — (1) `autonomous_budget._ram_count` không được trả lại sau `try_consume()`, (2) `importlib.reload(mcp_server)` chạy khi `mcp` là MagicMock nên mọi hàm `@mcp.tool` nằm lại dạng MagicMock (`patch.dict` khôi phục `sys.modules` nhưng KHÔNG khôi phục `mcp_server.__dict__`). Gây 3 fail bất định. Verify: full suite 3 lần liên tiếp đều xanh (`9470 passed, 77 skipped, 1 xfailed`).
- ✅ **Rò knowledge globals cũng đã sửa (chủ dự án yêu cầu làm luôn):** `test_resilience.py` là file DUY NHẤT còn gán thẳng `knowledge._entities` / `_relationships` / `_itineraries` / `_data_source` (3 chỗ: `TestKnowledgeSearchEdgeCases._seed_entities`, `TestKnowledgeEdgeCasesExtended._seed`, `TestKnowledgeHealthCheck`); phần còn lại của suite đã dùng `monkeypatch.setattr(knowledge, ...)` từ trước. Nặng nhất là `test_health_check_empty_is_degraded` để lại `_entities = {}` — `_ensure()` guard `is None` nên KHÔNG bao giờ nạp lại → knowledge RỖNG vĩnh viễn cho worker đó. Đã chuyển cả 3 chỗ sang `monkeypatch.setattr` (13 call-site nhận thêm fixture `monkeypatch`); không đổi dữ liệu seed, không đổi assertion. `_adjacency` tự lành theo identity của `_relationships` nên không cần reset tay.
- **Bằng chứng rò knowledge (2026-08-06):** probe RED/GREEN chạy sau `test_resilience.py` trong cùng process — trước khi sửa đỏ đúng `assert {} != {}` (knowledge bị bỏ lại rỗng), sau khi sửa xanh. `test_resilience.py` `173 passed, 1 skipped` → `174 passed, 1 skipped` (thêm probe). Full suite 3 lần liên tiếp đều xanh, **số đếm KHÔNG đổi so với trước khi sửa** (`9470 passed, 77 skipped, 1 xfailed`; 616s/651s/641s) → xác nhận không test nào từng phụ thuộc vào state rò, đúng rủi ro đã nêu lúc defer.
- **Ghi chú chẩn đoán (tránh mất thời gian lần sau):** `pytest-randomly` KHÔNG được cài → thứ tự test trong một lần chạy là CỐ ĐỊNH, `-p no:randomly` là no-op. Nguồn bất định duy nhất là xdist `--dist loadfile` gán *file* cho worker theo thời điểm worker rảnh, nên "cùng commit lúc đỏ lúc xanh" = polluter và nạn nhân có rơi cùng worker hay không. Cách tái hiện rẻ và tất định: chạy thẳng cặp file nghi ngờ trong **cùng một process** (`pytest <file_polluter> <file_victim>`), KHÔNG cần `-n`.

- **[MỚI 2026-08-24] `tests/detail-grid-containment-gate.test.mjs` đỏ rồi tự xanh — ĐÃ HAI LẦN.**
  Ca `observes exact timed-out helper-tree exit and prevents delayed side effects` báo
  `node.exe timed out after 1000ms; cleanup failed: Bad control character in string literal in
  JSON at position 122791`. Chạy riêng file: **47/47 xanh**; chạy lại toàn bộ: **2103/2103 xanh**.
  Không phải do thay đổi CSS cùng đợt — chuỗi 122791 ký tự là payload TỔNG HỢP do chính
  test sinh ra (`'x'.repeat(100000)` ở dòng 1017), không phải nội dung file dự án.
  Chẩn đoán: ca này sinh **cây tiến trình thật** rồi đọc file pid do tiến trình con ghi;
  hạn 1000ms đủ chật để spawn `node.exe` trên Windows vượt quá khi máy đang tải nặng, và
  file pid có thể bị đọc lúc đang ghi dở → JSON cụt. Đây là **đua ghi/đọc**, không phải
  hồi quy. Cách vá: ghi pid ra file tạm rồi `rename` (nguyên tử) thay vì ghi thẳng,
  hoặc nới hạn 1000ms cho Windows.
  **ĐÃ TÁI DIỄN — lần 2 cùng ngày, sau khi sửa CSS trang chủ (không liên quan).**
  Hai lần thì không còn là ngẫu nhiên nữa. Để lâu thì suite mất độ tin cậy: riêng
  đợt này tôi đã phải chạy lại toàn bộ hai lần chỉ để biết đó là nhiễu hay hồi quy thật.

### Backlog phát sinh — 4 test closed-installer chỉ đỏ trên Linux (2026-08-06)
- **[Security/Chưa làm] Ghim python theo descriptor KHÔNG chống được ghi-đè-tại-chỗ.** `PYTHON_EXECUTOR="/proc/$BASHPID/fd/$FD"` ghim *inode*, nên `> "$path"` (truncate cùng inode) làm mọi `invoke_python` sau đó chạy nội dung của kẻ tấn công — đo được: hook ghi `exit 97` vào executor đã admit thì installer báo `authority-result-record-failed:python-dependencies:97`. Ghim descriptor chỉ chặn *thay đường dẫn* (inode mới), và đó mới là thứ `test_linux_installer_keeps_admitted_python_when_authority_path_is_replaced` đặt tên. Vá thật sẽ tốn kém: hook role được bảo vệ bằng copy-vào-memfd-có-seal + đối chiếu digest mỗi lần gọi, nhưng python KHÔNG áp được cách đó (verify digest cần chạy python — vòng lặp gà-trứng; exec từ memfd thì mất nhận diện venv qua `sys.prefix`, đúng thứ `test_explicit_python_executor_preserves_isolated_venv_runtime` khoá). Cần chủ dự án quyết trước khi động vào.
- **[Test-coverage/Chưa làm] `test_live_retry_recovers_interruption_immediately_after_bind_mount` chưa từng được chứng minh trên CI.** Nhánh live ghi thẳng `/etc/systemd/system` và CẤM override đường dẫn, nên runner user-thường không lấy nổi install-lock ở đó và chết trước khi chạm bind mount. Nay đã gắn cổng `_systemd_units_writable()` như 5 test live cùng họ → SKIP thay vì đỏ giả. Muốn phủ thật phải chạy bằng root (VPS, hoặc thêm một job CI `sudo -E`) — quyết định của chủ dự án vì nó ghi vào `/etc/systemd/system` của runner.
- **[Ghi chú môi trường]** `scripts/ops/install_closed_release.sh` được commit ở mode `100644`. Trên Linux gọi thẳng script là 126 (`Permission denied`); MSYS bỏ qua bit exec nên Windows không lộ. Mọi lời gọi trong test phải đi qua `bash`, và `core.filemode=false` trên máy Windows khiến khác biệt này vô hình khi phát triển tại chỗ.

---

## Đợt 2026-08-07 — 13 commit trên `codex/tri-region-color` (XONG local, CHƯA push/deploy)

Thứ tự cũ → mới. Không commit nào chạm prod; không commit nào ghi vào `agent/data/vinhlong360.db` hay `web/data.json`.

**Nối tính năng backend đã có mà frontend chưa từng gọi**
- ✅ **`c5379506` ẩn/bỏ ẩn bài viết.** 3 endpoint hide/unhide/GET-hidden đã xong từ lâu, FE gọi 0 lần. Phạm vi lọc CỐ Ý hẹp: chỉ `_feed_build_conditions` (GET `/api/feed`, kể cả `?sort=trending`), `get_following_feed`, `get_friend_reviews`. `canHide` mặc định TẮT, chỉ bật ở feed cộng đồng — gắn nút Ẩn ở tab Đã lưu / kết quả tìm kiếm sẽ làm bài biến mất rồi QUAY LẠI sau khi tải lại trang. `test_hidden_posts_contract.py` khoá hai chiều: backend mở rộng lọc mà FE không mở `canHidePosts` thì test đỏ.
- ✅ **`922fd5bd` thời tiết lên trang chủ.** `/weather` + `/weather/all` (`server.py:3778`) FE gọi 0 lần. Ba trạng thái theo §1.7: `measured` → hiện số + nguồn · `estimated` → **null-hoá toàn bộ con số trong `emptyReading()`** nên template không có gì để lỡ tay render · lỗi → nói thẳng là lỗi.
- ✅ **`71a8f19c` trang lịch vạn niên.** Âm–dương, can chi, tiết khí. Lõi lịch đã có từ `5b4f850c`; đợt này bổ sung hàm còn thiếu trong `useLunar.ts` + mở rộng test parity với oracle Python. Thẩm tra độc lập chạy oracle TƯƠI (không dùng fixture của tác giả): 30 ngày rải đều 2020-2030 khớp 100% trên 8 trường/ngày, cả ở tầng composable LẪN ở trang render thật; tháng 6 nhuận 2025 đúng 29 ô.

**Sửa lỗi đúng-sai (không phải tinh chỉnh)**
- ✅ **`c002e184` chặn thời tiết dự phòng lọt vào LLM như số đo thật (§1.7).** Trước: system prompt cho LLM là `[Thời tiết Vĩnh Long (dự đoán)]: mưa rào, 28°C, ẩm 80%` — bốn chữ số BỊA, chỉ được che bằng hai chữ trong ngoặc mà LLM không bắt buộc giữ lại. Tái hiện thật với `WEATHER_API_KEY` rỗng. Sau: 0 chữ số đi vào LLM ở chế độ fallback. Đã vét 5 điểm gọi `get_weather`/`get_all_weather`/`get_realtime_context`; 2 điểm HTTP giữ nguyên CÓ Ý vì FE tự phân loại bằng `payload.fallback`.
- ✅ **`4bced5e1` file `.ics` sinh sai ngày cho sự kiện all-day — 100% ca trượt.** RFC 5545: `DTEND` kiểu DATE là LOẠI TRỪ, phải LỚN HƠN `DTSTART`. Đo trên dữ liệu thật (đọc-only `web/data.json`, 69 entity có ngày → 59 VEVENT): bản cũ sai toàn bộ — 7 sự kiện dài 0 ngày, 52 sự kiện MẤT đúng ngày cuối. Bản mới 0 vi phạm. Ngữ nghĩa "`date_end` là ngày cuối INCLUSIVE" được xác nhận độc lập ở hai nơi trước khi cộng 1 (`public_api.py:2305`, `su-kien.vue:308`).
- ✅ **`02a02a56` ba hàm tên `_atomic_write` nhưng không nguyên tử.** `dynamic_agents.py`, `llm_judge.py`, `self_optimizer.py`. Tái hiện bằng thân hàm cũ lấy nguyên văn từ `git show HEAD:` — chặn giữa chừng làm MẤT TRẮNG file đích (không phải file cụt); `os.fsync` gọi 0 lần; hai lần ghi dùng chung ĐÚNG MỘT tên tmp cố định → xuất bản được JSON hỏng (`json.loads` ném lỗi). Nay cả ba dùng chung `versioned_json_store.atomic_write_json`.
- ✅ **`94942186` trả `moderation_status` của bình luận cho đúng người được thấy.** `_format_comment` không trả trường này nên sau khi sửa bình luận, FE phải tải lại danh sách rồi đoán. KHÔNG trả bừa cho tất cả: `_may_see_comment_moderation` lấy đúng nhánh quyền của `delete_comment` (`social.py:2529`) — chính chủ HOẶC admin/moderator; không có người xem = ĐÓNG.
- ✅ **`8a002599` breadcrumb backend còn phát tên tỉnh cũ, lệch với HTML (§1.6).** `_build_breadcrumb` (`agent/seo.py`) vẫn phát mắt xích `area` (`/khu-vuc/ben-tre`…). HTML nói "P. Bến Tre" trong khi structured data nói "Bến Tre". Nay backend phát đúng mắt xích xã/phường; `_admin_unit_label`/`_admin_unit_crumb` là MIRROR của `adminUnit.ts`. Ba guard giữ nguyên từ bản TS, đều có lý do đo được — đáng chú ý: entity `type=place` → `None`, bắt buộc vì **39/125 place trong dữ liệu có `placeId != id`** (32 trỏ nhầm `p-long-chau`).

**Test / CI / hạ tầng**
- ✅ **`0f7269ea` 6 test chỉ đỏ trên Postgres — CI xanh lại.** Suite SQLite `10136 passed, 0 failed`; suite PG `6 failed / 10124 passed`; sau đợt này cả hai đều xanh. Thẩm tra dùng một DB PG dùng-một-lần riêng (`apply_migrations --init-baseline`), tái hiện 6/6 đỏ từ HEAD rồi 6/6 xanh với bản sửa. **KHÔNG nới lỏng assertion nào (§3.3)** — các assert gốc giữ nguyên từng chữ; monkeypatch chỉ ghim ĐIỀU KIỆN BIÊN.
- ✅ **`970e44eb` index đường nóng + `statement_timeout` (migration 075).** Đo THẬT trên cluster PG 16.4 riêng (cổng 55432, không đụng PG đang chạy), seed 60k likes / 10k posts / 30k blocks: `likes(post_id)` Seq Scan 12,9ms/500 buffer → Index Only Scan 0,65ms/3 buffer (~20x nhanh, 166x ít buffer, nằm trên ĐƯỜNG GHI của mọi lượt thích); `blocks(blocked_id)` 4,28ms → 0,168ms. Thêm `statement_timeout=30s` + `idle_in_transaction_session_timeout=60s` trên role `vl360`.
- ✅ **`f8ff3a8e` khoá đường truyền tham số iCal ở trang, không chỉ bộ sinh.** Vá đúng lỗ hổng mà `4bced5e1` tự ghi lại: đột biến `dateEnd: eventEnd(e)` → `eventStart(e)` tại `le-hoi.vue:555` vẫn để bộ test cũ XANH 17/17. Test mới bắt 7 đột biến trên CẢ HAI trang (`le-hoi.vue` + `su-kien.vue`); refactor thuần (đổi tên biến, đảo thứ tự key, `>=` → `!(<)`) vẫn 19/19 XANH — tức test bắt Ý NGHĨA chứ không so chuỗi mã.
- ✅ **`3739e7a5` tắt detector Lob (43 dương tính giả) + ghim THẬT phiên bản TruffleHog.** Hai lý do độc lập, cả hai ĐÃ ĐO: (1) `keyPat` của Lob là `\b((live|test)_[a-zA-Z0-9_]{35})\b` **không kiểm entropy** — quét cây ra 182 chuỗi khớp, 182/182 bắt đầu bằng `test_`, 181 chứng minh được là `def <tên>(`, 0 chuỗi `live_`, dự án KHÔNG dùng dịch vụ Lob; (2) bước verify của detector HỎNG — UA `TruffleHog` mà KHÔNG gửi credential nào vẫn trả 403 ổn định 4/4 lần, và source v3.96.0 coi 403 là `return true, nil`.
- ✅ **`10d9bb69` bảng quyết định dữ liệu sự kiện lệch âm–dương.** Xem `docs/2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md`. **CHỈ PHÂN TÍCH, chưa sửa một dòng dữ liệu nào.**

---

## Backlog phát sinh — Đợt 2026-08-07 (ghi lại, CHƯA làm)

- **[P1/Data — §1.6] 16 entity id còn chôn filler `mien-tay`, trong đó ≥4 id đã lệch hẳn với `name` đã viết lại.** Đo trên `web/data.json`: `tet-nguyen-dan-mien-tay` ↔ name "Tết Nguyên Đán Vĩnh Long" · `banh-xeo-mien-tay` ↔ "Bánh xèo Vĩnh Long" · `xoi-vi-mien-tay` ↔ "Xôi vị Vĩnh Long" · `hoc-nau-an-mien-tay` ↔ "Học nấu ăn Vĩnh Long" · `quan-lau-mam-mien-tay-cho-tieu-can-tra-vinh` ↔ "Quán lẩu mắm Vĩnh Long chợ Tiểu Cần". Đợt sweep filler trước chỉ chạm `name`/`summary`, KHÔNG chạm `id`. **Không batch-rename được:** id là URL công khai + khoá prerender + sitemap + `relationships`, và trong 16 cái có tên riêng hợp lệ phải GIỮ (`ben-xe-mien-tay-hcm` = Bến xe Miền Tây ở TP.HCM; `song-nuoc-mien-tay-restaurant---am-thuc-mien-tay`, `cua-hang-dac-san-mien-tay-*` = tên thương hiệu). Cùng họ với backlog "đổi id `chom-chom-binh-hoa-phuoc-rambutan`" (SP6) → gộp làm MỘT task đổi-id có redirect + B1 backup.
- **[P2/Cleanup — §B2] `withAdminUnitBreadcrumb` giờ gần như no-op, gỡ ở task riêng.** `8a002599` sửa backend phát đúng mắt xích xã/phường, nên lớp vá đè phía FE (`web-nuxt/utils/adminUnit.ts`, gọi ở `pages/dia-diem/[id].vue:1338`) không còn việc để làm. Giữ lại theo additive-first; gỡ phải đi kèm verify SSR structured-data của cả 3 nhánh guard (place tự trỏ chính nó · `placeId` trỏ về chính nó · thiếu `placeId`) và cập nhật `tests/detail-admin-unit-breadcrumb.test.ts` (hiện 9 assertion trực tiếp lên hàm này).
- **[P2/Test-debt] Lỗ hổng iCal đã vá — ghi lại làm mẫu, không phải việc còn dở.** `4bced5e1` tự ghi "test khoá được BỘ SINH nhưng chưa khoá ĐƯỜNG TRUYỀN THAM SỐ ở trang"; `f8ff3a8e` vá đúng chỗ đó. **Bài học nên áp cho các cổng khác:** một bộ test xanh 17/17 vẫn có thể bỏ lọt lỗi cũ quay lại nếu nó chỉ kiểm hàm thuần mà không kiểm chỗ trang GỌI hàm đó. Cùng lớp lỗi với `standards/95-ra-soat-cong.md` (cổng chỉ kiểm sự có mặt).
- **[P3/Docs] 3 plan trong `superpowers/plans/` có STATUS lệch thực tế đã ship** — `2026-07-27-pinned-egress-security-observability.md` ("implementation has not started" trong khi spec cùng tên ghi `done`), `2026-07-29-zero-cost-directional-route-optimizer.md` (`active` trong khi `results/` ghi `done`), `2026-07-30-phase2b-generator-adoption.md` ("final review pending" từ 2026-07-30). Không tự sửa vì đổi STATUS của plan là phát ngôn về trạng thái công việc của chủ nhánh. Chi tiết: bảng "Nghi vấn" trong `docs/README.md`.
- **[P3/Docs — §1.6] Chữ "3 tỉnh" còn dùng làm tên gọi token màu và mô tả phạm vi.** `superpowers/specs/2026-07-05-public-pages-cinematic-redesign.md` (~12 chỗ "màu 3 tỉnh" + "strip timeline sáp-nhập 3 tỉnh") và `implementation-specs.md:216,227` ("bounding box 3 tỉnh", "nghiên cứu … 3 tỉnh"). Đây là tên biến/phạm vi chứ KHÔNG phải claim đơn vị hành chính, nhưng vẫn trái khung định vị. Đổi tên chạm cả code nhánh `codex/tri-region-color` → task riêng.
- **[Ghi nhận, không phải việc]** Rà toàn `docs/` (trừ `archive/`) ngày 2026-08-07: **155/155 file có header STATUS, cổng R60.1 đếm 0 vi phạm** — mục "tài liệu thiếu STATUS" coi như đóng. Nguồn ảnh cấm / booking / cấp huyện: mọi lần nhắc còn lại đều nằm trong câu cấm hoặc có chữ "cũ".
- **[P1/Chuẩn — §3.7] Baseline complexity nâng 17 → 23 khi hợp `codex/phase4-multiday-allocation` vào `main`.** Nhánh đó phát triển ngoài tầm cổng (chưa từng có CI chạy trên nó) nên mang theo 6 hàm vượt ngưỡng mà chưa ai chặn: `itinerary_multiday.py` — `_validate_inputs` (36), `optimize_multi_day_allocation` (33), `_generate_neighbors` (26), `_schedule_day` (22), `_solve_allocation` (14), `__post_init__` (13); cộng `itinerary_gen.py::_build_joint_day_plans` nhảy 24 → 37. **Vì sao nâng trần thay vì hạ complexity:** đây là hàm thuật toán DP, refactor giữa lúc merge là đổi cấu trúc một thuật toán mình không viết — rủi ro sai kết quả cao hơn lợi ích, dù có 573 dòng test che. §3.7 cho phép đúng tình huống này (thao tác diện-rộng có chủ đích + giải trình trong cùng commit). **Nợ này KHÔNG được coi là đã đóng:** hạ 6 hàm đó xuống ≤12 là task riêng, và baseline phải hạ lại theo. Ai chạm `itinerary_multiday.py` lần sau nên hạ luôn phần mình sửa.
- **[P1/Chuẩn — §3.7] Baseline nâng lần hai khi hợp `codex/np1-identity-location-trust`: complexity 23 → 36, fe_colors 307 → 310.** 13 hàm vượt ngưỡng đến từ nhánh này (`user_preferences.py` 4, `public_api.py` 3, `location_resolver.py` 2, `trust_policy.py` 2, …). Cùng lý do với lần một: nhánh phát triển trước 2026-08-06, khi `ci.yml` còn chỉ kích hoạt trên `main` và PR, nên chưa bao giờ bị cổng chạm. **Tổng nợ complexity trong phiên 2026-08-08: 17 → 36, hơn gấp đôi.** Đây là cái giá thật của việc gom nhánh, ghi lại để không ai tưởng "hợp xong là xong". Việc còn nợ: hạ 19 hàm mới thêm xuống ≤12 rồi hạ baseline theo.
- **[Ghi nhận — §3.7] `R20.5b` KHÔNG được baseline-hoá dù nó đỏ 4.** Rule này tồn tại đúng để bắt "route mới phải có mô tả trong `docs/api-contract.md`"; nâng baseline ngay lần đầu nó bắt được ai đó là vô hiệu hoá chính nó. Đã bổ sung mô tả cho 5 route NP-1 (`/api/me/preferences` GET+PATCH, `/api/me/preferences/consents`, `/api/me/location/resolve`, `/api/me/recommendations/reset`) → về 0. **Đây là tiền lệ nên theo:** rule đang ở 0 thì sửa, đừng nới.

## Backlog phát sinh — Đợt quét sâu 2026-08-22 (kênh đính chính; ghi lại, CHƯA làm)

> Bốn mũi quét độc lập trên các mạch chưa ai chạm. Hai mạch SẠCH: 21 fail baseline
> không chứa lỗi sản phẩm nào (12 artifact Windows + 9 test cũ), và không có đường
> rò số điện thoại nào trong cả 6 lối thoát được rà (log, metrics, outbox, admin API,
> thông báo lỗi, backup). Ba việc dưới đây là quyết định của chủ dự án, không phải
> lỗi mã tôi được phép tự vá.

- **[P0/Pháp lý] Vòng xác thực số điện thoại KHÔNG khép lại được qua sản phẩm — cả hai nửa đều thiếu chỗ dùng.** Nút "Gửi mã xác nhận số điện thoại" (`web-nuxt/components/cases/CorrectionIntakeForm.vue:230-237`) nằm trên form intake, tức TRƯỚC khi hồ sơ tồn tại; `_guard_session_mutation` (`agent/cases/public_api.py:144`) trả **401** khi chưa có cookie `vl360_case_access`, và `verifyPhone` ở `pages/yeu-cau/sua-thong-tin.vue:67-72` **nuốt lỗi im lặng** (`catch { }`) nên người dùng không thấy gì. Nửa còn lại còn tệ hơn: `verifyContact(code)` có trong `composables/useCorrectionCases.ts:193` nhưng **KHÔNG component nào gọi** — không có ô nhập mã. Hệ quả pháp lý: số điện thoại được thu cho một mục đích ("báo kết quả") mà sản phẩm **không thể phục vụ**. Chỗ đúng cho vòng này là `CaseReceiptCard.vue` (hiện sau khi gửi, lúc đó đã có cookie). **Không tự dựng vì đây là làm tính năng, không phải sửa lỗi (CLAUDE.md §3.5).** Phơi nhiễm thực tế = 0: cờ tắt, chưa người dùng thật.
- **[P0/Pháp lý] Tác vụ xoá tài khoản chạy chế độ CHỈ-ĐẾM theo mặc định — và đây là mục DUY NHẤT trong đợt này KHÔNG nằm sau cờ case-kernel, tức phơi nhiễm là THẬT hôm nay.** Nút "Lên lịch xóa" sống ở `web-nuxt/pages/cai-dat.vue:636`, và `agent/auth.py:1284` trả về nguyên văn *"Tài khoản sẽ bị xoá vĩnh viễn sau 30 ngày"*. Nhưng `_effective_erasure_audit_only()` (`agent/scheduler.py:137`) trả True trừ khi **cả hai** cờ mở, và `agent/config.py:85` đặt `ERASURE_AUDIT_ONLY: bool = True`; `erase_due_accounts` thoát ở `agent/erasure.py:394` TRƯỚC vòng xoá. Tác vụ chạy 288 lần/ngày (chu kỳ 300s) và lần nào cũng dừng ở đó. Bốn chi tiết làm nó khó tự lộ:
  - **`/ready` không bao giờ đỏ vì chuyện này.** `agent/server.py:4200`: `"ok": bool(schema.get("ok")) and "audit_only" in erasure_status` — chỉ kiểm **khoá có tồn tại**, không kiểm giá trị, và `overdue_count` không tham gia. Cùng lớp lỗi với `standards/95-ra-soat-cong.md` (cổng chỉ kiểm sự có mặt).
  - **Test khoá cứng hành vi không-xoá** (`agent/tests/test_erasure_config.py:11-12`), nên suite xanh KHÔNG chứng minh có xoá.
  - **Quarantine tức thời không cứu:** nó chỉ phủ 5 policy cache/memory có `quarantine_on_request` (`agent/data_lifecycle.py:332-378`), KHÔNG đụng `users`/`posts`/`comments`.
  - **`.env.example` không có khoá `ERASURE_*` nào**, nên deploy theo file mẫu chắc chắn rơi vào mặc định audit-only.

  Đây là cổng an toàn CÓ CHỦ ĐÍCH, có tài liệu sống: `docs/runbooks/personal-data-erasure.md:11` — *"Account erasure remains audit-only until the activation gate is approved"*. **Hai đường, chọn một trước khi có thêm người dùng:** (1) chạy runbook rồi bật cờ trên prod (thao tác phá huỷ, CLAUDE.md §4/B7 — chỉ chủ dự án), và thêm `ERASURE_*` vào `.env.example` để deploy sau không rơi lại mặc định; hoặc (2) chưa bật thì **sửa lời hứa cho khớp mã** ở `agent/auth.py:1284` và `web-nuxt/utils/legalContent.ts:51`. Không được để câu "30 ngày" đứng nguyên trong khi executor ở audit-only.

- **[P0/Sản phẩm] Nút "xin xét lại" KHÔNG BAO GIỜ chạy được — hợp đồng hai đầu lệch, và lỗi bị dịch sai hướng.** `_ReviewIn.expected_revision` (`agent/cases/public_api.py:223`) là trường **bắt buộc** (`alias="expectedRevision"`, `ge=1`), nhưng composable chỉ gửi `{ reason }` (`web-nuxt/composables/useCorrectionCases.ts:198`) → pydantic 422. Và **không client nào điền được**: payload trạng thái công khai chưa từng trả về revision nào. Tệ hơn, `useCorrectionCases.ts:66` gộp **422** chung với 400/401/403/404/409/410 rồi ném `CaseAccessError` — người dân được báo "mã tra cứu sai" cho một lỗi hợp đồng schema, nên họ sẽ nhập lại mã mãi mà không bao giờ đúng. Sửa đúng = phơi revision ra `public_status` rồi cho client mang theo (giữ được optimistic-concurrency, đừng bỏ trường bắt buộc) + tách 422 khỏi nhóm lỗi truy cập. Chạm hợp đồng API nên cần cập nhật `docs/api-contract.md` (R20.5b) → task riêng, không vá vội.
- **[P1/Pháp lý] "Rút lại đồng ý" hiện nghĩa là ngưng nhắn tin, KHÔNG phải ngưng giữ số.** `agent/cases/contact.py:123-128`: nhánh `consent=False` xoá `case_contact_challenges` rồi return ngay, **không đụng** `case_interactions.payload_enc` — nơi số thật nằm. Đường xoá số có tồn tại (`redact_closed_case_contacts`, `agent/cases/store.py:1050`) nhưng chạy theo **đồng hồ lưu trữ 90 ngày**, không theo **hành động rút lại**. Hai thứ khác nhau về mặt luật. Đã đưa thành câu hỏi 4 và 5 trong `docs/2026-08-22-cau-hoi-cho-luat-su.md` §2. Chờ luật sư trả lời trước khi chọn cách làm.

## Fail-đã-biết — danh sách chuẩn (đo 2026-08-22 trên `codex/correction-case-pilot`)

> CLAUDE.md §3.4 bảo mỗi phiên phải đối chiếu "danh sách fail-đã-biết", nhưng danh
> sách đó **chưa từng tồn tại ở đâu**. Thiếu nó thì "21 fail đã biết" là một con số
> truyền miệng, và đúng chuyện đó đã xảy ra: 5 fail cổng migration nằm trong rọ suốt
> hai migration mà không ai ghi nhận (vá ở `8f5d5a23`). Danh sách phải sống ở đây.
>
> **Baseline hiện tại: 16 fail.** Lệnh đo (Windows, cần container PG cho nhóm case):
> ```
> # temp-root phải NGẮN (MAX_PATH) và ghi được; đặt bằng đường dẫn tuyệt đối của bạn
> $env:PYTEST_DEBUG_TEMPROOT='<temp-root-ngan>'
> $env:VL360_TEST_DATABASE_URL='postgresql://vl360:vl360@127.0.0.1:5433/<db-test>'
> python -m pytest -q --tb=no
> ```
> Xuất hiện fail NGOÀI danh sách này = hồi quy thật, DỪNG và báo người (§3.3).

**(W) — 12 test hỏng vì đặc quyền/ngữ nghĩa Windows, kỳ vọng xanh trên Linux CI.**
`ci.yml` chạy `python -m pytest tests/ agent/tests/ -m "not slow"` nên nhóm này CÓ
chạy trên Linux — giả định "sẽ xanh" là kiểm được, không phải suy đoán:

- `tests/launch_safety/test_artifact_packaging.py` — `test_backend_archive_excludes_private_runtime_and_unsafe_symlinks`, `test_candidate_scanner_rejects_alias_symlink_and_non_file`
- `tests/launch_safety/test_nginx_contract.py` — `test_render_file_ignores_preexisting_fixed_temp_symlink`, `test_render_file_rechecks_destination_symlink_before_replace_retry`, `test_render_file_rejects_destination_symlink_without_touching_victim`, `test_render_file_rejects_source_symlink`
- `tests/launch_safety/test_rollback_runbook.py::test_local_rehearsal_failure_injection_preserves_status_and_records_recovery`
- `tests/launch_safety/test_systemd_contract.py::test_probe_rejects_final_symlink_without_touching_victim`
- `tests/test_secure_stage_b_artifacts.py` — 4 test ACL/normalize (`..._trailing_root_separator...`, `..._safe_inheritance...`, `..._nested_protected_parent`, `..._before_strict_acl_fails_without_evidence[NormalizeAndVerify]`)

**(S) — 4 test kỳ vọng lệch, KHÔNG phải sản phẩm hỏng:**

- `agent/tests/test_phase16_coverage.py::TestPhase17SecurityChecks::test_esms_uses_https` và `agent/tests/test_session_be.py::TestPhase12DependencySecurity::test_esms_uses_https` — cùng một assertion về endpoint eSMS.
- `agent/tests/test_case_policy.py::test_valid_nonproduction_case_activation_has_structural_credentials`
- `tests/test_api_surface_contract.py::test_write_routes_under_api_require_an_auth_guard` — **có chủ đích một nửa:** các route đính chính công khai CỐ Ý mở cho khách không tài khoản (người dân báo sai sót). Test chưa biết ngoại lệ đó. Cần khai vào `PUBLIC_WRITE_ALLOWLIST` kèm lý do, HOẶC chấp nhận có ghi chú — chưa ai quyết.

**(P) — lỗi sản phẩm thật: 0.** Đợt quét 2026-08-22 rà từng test một; không cái nào
che một defect sản phẩm. 5 test cổng migration từng nằm trong nhóm (S) đã vá, không
phải nới assertion mà đưa hằng ghim về đúng đầu chuỗi (081/81).

---

## Backlog phát sinh — Đợt di cư emoji → IconLine (2026-08-23; ghi lại, CHƯA làm)

Loạt di cư đã đưa R30.2 từ **507 → 334** (mỗi trang một commit). Bốn việc dưới đây
phát sinh dọc đường, **cố ý chưa làm** vì vượt phạm vi task kỹ thuật (§3.5).

### 1. Ba emoji giữ lại có chủ đích — KHÔNG phải sót

| Chỗ | Glyph | Vì sao giữ |
|---|---|---|
| `web-nuxt/components/EntityReviews.vue:25` | ★ | Nút chấm sao (`role="radio"` + `aria-label="N sao"`). Trạng thái chọn/chưa chọn phân biệt bằng `.star.active { color: var(--accent) }` trên một glyph ĐẶC. Đổi sang icon nét thì cả hai trạng thái đều thành viền mảnh, vẫn chỉ khác nhau bằng màu → **kém hơn hiện tại**. Muốn đổi thì phải làm sao-đặc/sao-rỗng, là việc riêng. |
| `web-nuxt/pages/admin/cai-dat/danh-muc.vue:13` | 🍜 | Nằm trong `<pre>{ "dish": { "emoji": "🍜" } }</pre>` — đây là **ví dụ tài liệu** mô tả đúng định dạng dữ liệu đang lưu. Đổi thành icon là làm tài liệu nói sai sự thật. |
| `web-nuxt/pages/admin/cai-dat/footer.vue:75` | 🔗 | `:new-item-template="{ icon: '🔗', ... }"` — **giá trị dữ liệu** ghi vào settings, không phải glyph trong template. Chuyển được chỉ khi bộ render footer biết ánh xạ tên-icon; là task riêng có verify. |

### 2. 67 emoji "tàng hình" với R30.2 — con số thật cao hơn 334

R30.2 chỉ khớp **ký tự emoji thật**. Emoji viết dạng HTML entity (`&#128269;`,
`&#x1F4F7;`) hoặc escape JS (`\u{1F50D}`) **thoát khỏi rule** — đã ghi trong
`scripts/checks/check_fe_tokens.py:43-46`, nay bổ sung số đo.

Đo 2026-08-23 trên `web-nuxt/**/*.vue` (trừ `node_modules`, `.output`, `.nuxt`):
**67 glyph / 66 dòng / 15 file**, gần như toàn bộ ở khu admin — nặng nhất
`pages/admin/index.vue` (12), `pages/admin/thong-ke.vue` (10),
`pages/admin/ai.vue` (10), `pages/admin/data-quality.vue` (6),
`pages/admin/entities.vue` (6).

Đã truy nguồn: chúng là **lối viết gốc của khu admin** (`<GĐ-WC-UI b7>`,
`[admincp] dashboard...`), KHÔNG phải ai đó đổi emoji-thật thành entity gần đây để
hạ số cho gate. Không có dấu hiệu lách cổng.

Quyết định cần chủ dự án: mở rộng R30.2 bắt entity/escape sẽ nâng nợ **334 → 401**,
phải nâng baseline kèm giải trình (§3.7). Hoặc để nguyên và chấp nhận rằng con số
R30.2 không phải tổng emoji thật.

### 3. `/luu-tru` còn gọi tên ba tỉnh song song — trái §1.6

`web-nuxt/pages/luu-tru.vue:129`, thuộc tính `hint`:

> "Bạn có thể khám phá thêm các nơi ở ở Vĩnh Long, Bến Tre và Trà Vinh."

Viết như ba tỉnh còn tồn tại song song. Từ 7-2025 chỉ còn **một** tỉnh Vĩnh Long;
theo §1.6, "Bến Tre/Trà Vinh" chỉ được xuất hiện kèm chữ "cũ/trước 7-2025". Đây là
sửa **nội dung**, không phải sửa kỹ thuật, nên không gộp vào commit di cư icon.

### 4. R10.8 (`data_rich_source`) đỏ giả một lần — cổng fail-closed vì artifact

Trong loạt commit, `run_hard --staged` một lần in
`✖ RATCHET R10.8 (data_rich_source): 1 vi phạm > baseline 0` rồi các lần sau xanh
lại; chạy trực tiếp 3 lần liên tiếp đều ra **0 vi phạm**.

Đúng một vi phạm = nhánh `DataRichSourceCheck._artifact_load_failure`
(`scripts/checks/check_data_schema.py:147-165`): khi `current_policy_evidence()`
ném lỗi, check trả về **một** violation `index-policy-artifact-load-failed`. Hàm đó
đọc route manifest + AI disclosure rồi băm sha256
(`agent/launch_evidence.py:102-114`) — trên Windows một lần khoá file thoáng qua là
đủ làm cổng đỏ.

Hệ quả: "artifact không đọc được" và "entity thiếu nguồn" hiện **không phân biệt
được** ở đầu ra. Nên tách mã lỗi/kênh báo, hoặc cho phép thử lại lần đọc artifact.

**Bẫy tự gây, ghi để không lặp:** vòng lặp commit của tôi chạy
`run_hard.py --staged | tail -1`, mà mã thoát của pipeline là của `tail` → `set -e`
KHÔNG chặn, commit vẫn lọt dù cổng đỏ. Ghi kết quả ra file rồi kiểm mã thoát, đừng
nối ống thẳng vào `tail`.

### 5. "Còn 334" nghĩa là gì — bóc ba lớp, và hai vùng R30.2 không nhìn tới

Đo 2026-08-23 trên `web-nuxt/**/*.vue` (trừ `node_modules`, `.output`, `.nuxt`).
R30.2 đếm MỌI emoji trong file `.vue`, không phân biệt template hay script:

| Lớp | Số | Ghi chú |
|---|---|---|
| Trong `<script>` (mảng dữ liệu, hằng, chuỗi) | **244** | Nặng nhất: `pages/huong-dan.vue` 74, `admin/cai-dat/index.vue` 23, `huong-dan-thanh-vien.vue` 17, `tai-khoan.vue` 17, `ocop.vue` 15, `theo-mua.vue` 14 |
| Template CÓ `aria-hidden` | **88** | Trình đọc màn hình đã không đọc; là nợ hình thức, không phải lỗi tiếp cận |
| Template KHÔNG `aria-hidden` | **3** | Đúng ba ngoại lệ ở mục 1 |

(Tổng đo được 335, lệch 1 so với baseline 334 vì bộ ký tự tôi quét rộng hơn
`_EMOJI` của checker một chút — coi là cận trên.)

**Hệ quả cho người đọc log:** đợt di cư này đã xử lý **hết** lớp "template không
aria-hidden" — lớp duy nhất gây lỗi tiếp cận thật. Phần còn lại là dữ liệu trong
script và trang trí đã ẩn đúng cách. Đừng đọc "334" thành "334 lỗi UI".

**Vùng mù A — `.ts`/`.js` không bị R30.2 quét** (rule chỉ glob `*.vue`):
**95 glyph / 12 file**, nặng nhất `composables/useConstants.ts` 39,
`utils/adminKinds.ts` 13, `utils/pageManifest.ts` 13, `utils/routesContent.ts` 6.

Đáng chú ý: `useConstants.ts` mỗi vùng đã có **cả hai** trường —
`{ name: 'Bến Tre', emoji: '🥥', icon: 'leaf', ... }`. Đường di cư có sẵn trong
dữ liệu; việc còn lại chỉ là đổi chỗ render từ `.emoji` sang
`<IconLine :name="...icon" />` rồi bỏ trường `emoji`.

**Vùng mù B — emoji đến từ settings CMS trên prod, KHÔNG có trong mã.**
Đo trên `/le-hoi` (dev, `API_BASE=https://vinhlong360.vn`): 6 link trong nav/footer
đọc thành lời vì không có `aria-hidden` —
"Đã lưu **❤️**", "**🍊** Vĩnh Long", "**🥥** Bến Tre", "**🛕** Trà Vinh",
"**🏷️** Đăng ký quản lý trang", "**🤝** Hợp tác quảng bá".

Mặc định trong `layouts/default.vue:207-211` **không có emoji**
(`{ to: '/khu-vuc/ben-tre', label: 'Bến Tre' }`); giá trị thật đến từ
`ss('navigation.nav_groups', ...)` / `footer.columns`, tức **dữ liệu settings trên
prod sửa qua AdminCP**. Không sửa được bằng commit mã, và sửa dữ liệu prod là điều
kiện dừng (§4) — cần chủ dự án.

Kèm theo, cùng chỗ đó: ba link vùng dựng "Vĩnh Long / Bến Tre / Trà Vinh" thành ba
nơi ngang hàng ngay trên điều hướng chính — cùng loại vi phạm §1.6 với mục 3, nhưng
ở vị trí nổi bật hơn nhiều.

### 6. Đợt 2 — lớp `.emoji` trong dữ liệu (2026-08-23, tiếp theo mục 5)

Đã xử lý 6 chỗ **đọc** trường `.emoji`, dùng trường `icon` vốn đã có sẵn cạnh nó:

- `pages/danh-ba.vue` (:44, :87, :208) — làm nốt đợt mà `pages/xa-phuong/[id].vue` đã làm xong từ trước
- `components/SearchAutocomplete.vue` (:83) — **lỗi tiếp cận thật**: emoji loại hình đọc thành lời trong `role="option"`; nay `aria-hidden` + IconLine
- `pages/dia-diem/index.vue` (:51) — con dấu khu vực
- `pages/admin/entities.vue` (:5, :40, :48, :284) — ánh xạ ở client qua ADMIN_KINDS/TYPE_META, không đổi backend

Gỡ thêm 3 trường `emoji` **chết** trong object dự phòng (CatalogSpotlight,
EntityCard, ItineraryCard) — đã rà từng nơi đọc trước khi gỡ.

#### Còn lại, và VÌ SAO chưa làm

**(a) Bốn chỗ nằm trong `<option>` — HTML không cho.**
`pages/admin/danh-ba.vue:24`, `pages/admin/entities.vue:21` và `:262`,
`pages/admin/lich-trinh.vue:174`. Thẻ `<option>` chỉ render **văn bản thuần**; mọi
phần tử con bị bỏ qua, nên `<IconLine>` trong đó cho ra ô chọn TRỐNG. Đây là ràng
buộc của nền tảng, không phải việc làm dở. Muốn có icon trong ô chọn thì phải thay
`<select>` bằng listbox tự dựng — việc lớn, có đánh đổi về tiếp cận, cần quyết
riêng.

**(b) `OnboardingSheet.vue:14` + `utils/onboardingContent.ts` — hợp đồng dữ liệu CMS.**
Hai cái bẫy chồng nhau:

1. `OnboardingFeature.icon` **tên là `icon` nhưng giá trị là emoji** (`'🗺️'`,
   `'📅'`, `'💬'`). Đổi thẳng chỗ render sang `<IconLine :name="f.icon">` sẽ đi
   tìm icon tên "🗺️" — hỏng, mà hỏng lặng lẽ.
2. Cả khối này **CMS ghi đè được** (key `onboarding`, `mergeOnboarding()`). Thêm
   hay đổi nghĩa trường là sửa hợp đồng dữ liệu với settings đang chạy trên prod:
   override cũ vẫn mang emoji cho tới khi có người vào AdminCP sửa.

Đường đi additive (§2 B2) có sẵn: thêm `icon_name` song song, ưu tiên nó, rơi về
`emoji`/`icon` cũ — giống hệt cách `EmptyState` đã thêm `iconName`. Nhưng nó nới
hợp đồng CMS nên **cần chủ dự án quyết**, không tự làm.

**(c) `useConstants.ts` chưa bỏ được trường `emoji`** (39 glyph) vì (a) và (b) còn
đọc tới. Bỏ được ngay sau khi hai mục trên xong.

---

## Backlog phát sinh — Rà UI đo-trên-máy-thật (2026-08-23)

Đo bằng trình duyệt ở 320/360/375px, cả chế độ sáng lẫn tối. Màu đọc bằng pixel
thật (token là `oklch`, regex trên token cho ra rác).

### ĐÃ VÁ (xem git log cùng ngày)
- 7 chỗ tương phản 2.98:1 → 6.38 (tối) / 6.89 (sáng): `.skip-link`,
  `.main-nav a.active`, `.chat-panel-head`, `.chat-panel-input button`,
  `.stop-num`, `.route-marker .rm-num`, `a.hl`.
- Nhãn thanh nav dưới: dấu tiếng Việt tràn khỏi hộp dòng 2.39px → `line-height`
  1.1 → 1.4, cỡ chữ `clamp(.66rem, 3.2vw, .75rem)`.
- Thanh đỉnh ở 360px chỉ dư 1.6px → thu khe còn 8px, nay dư 9.6px.
- "Đổi khu vực" gãy hai dòng → `white-space: nowrap`.

### CHƯA VÁ — cần quyết định thiết kế

**(1) Trên máy 360×740, ô tìm kiếm chính bị che.** Đây nhiều khả năng là thứ
làm giao diện "thấy chưa ổn" rõ nhất.

Ngân sách dọc đo được (cuộn ở đỉnh):

| Khối | Từ → đến | Cao |
|---|---|---|
| thanh ngữ cảnh | 0 → 45 | 45 |
| header | 45 → 105 | 60 |
| khối khu vực `.home-context-line` | 106 → 245 | **139** |
| kicker | 294 → 311 | 17 |
| `h1` (3 dòng) | 325 → 475 | **150** |
| `.hero-sub` | 509 → 605 | 96 |
| **ô tìm kiếm** | 629 → **693** | 64 |
| nav dưới (fixed) | **676** → 740 | 64 |
| nút chat (fixed) | 616 → 664 | 48 |

Hệ quả: nav dưới che **17px đáy** ô tìm kiếm, và nút chat đè lên góc phải ô
(chồng 23×30px). Người dùng mở trang chủ trên điện thoại phổ thông thì hành
động chính — ô tìm kiếm — bị hai thanh cố định che một phần.

Ba đòn bẩy, chưa chọn:
- Rút gọn khối khu vực (139px cho một chỉ báo phụ, nhiều hơn cả ô tìm kiếm).
- Giới hạn `h1` còn 2 dòng ở màn nhỏ (hiện `max-width: 13ch` cho 3 dòng).
- Đưa ô tìm kiếm lên TRÊN `h1` trên màn hẹp.

**(2) Màn 320px vẫn tràn ngang ~30px.** Dưới 820px hàng lệnh chỉ còn ba con và
cả ba không co được: logo 130.4px + `.auth-area` 136px + nút menu 44px. Muốn hết
phải rút một trong hai thứ: chữ thương hiệu, hoặc gộp điều khiển chủ đề hai-nút
thành một nút. Cái sau đổi một affordance tiếp cận VÀ điều khiển chủ đề CHỈ có ở
header (không có trong menu ba-gạch), nên không tự quyết.

**(3) Hai quy tắc `line-height` chọi nhau cho `.hero h1`, cùng độ đặc hiệu.**
`pages/index.vue:753` đặt `.98`, `assets/css/home-nocturne.css:67` đặt `1.12`;
thắng thua chỉ do THỨ TỰ NẠP. Hiện `1.12` thắng nên không hại — mực thật của
Fraunces cho đúng câu tiêu đề đó đo được là 1.05× cỡ chữ, nên 1.12 vẫn hở.
Nhưng nếu thứ tự nạp đổi thì `.98` thắng và các dòng chồng nhau ngay (0.98 <
1.005 kể cả với chữ Latin thuần). Nên gỡ một trong hai.

### HAI ĐIỀU TÔI TỪNG KẾT LUẬN SAI, ĐÃ ĐO LẠI

- **Nền đen sau `.hero-sub` KHÔNG phải tàn dư.** `rgba(0,0,0,.76)` là thiết kế
  có chủ đích và ĐƯỢC TEST RÀNG BUỘC: `tests/tri-region-color-contract.test.ts:168-176`
  ("an opaque local plate"), kèm kiểm trắng-trên-đế đạt 10.55:1. Không đụng.
- **Ô tìm kiếm trên header KHÔNG phải bẫy bàn phím.** Nó rộng 0px nhưng thẻ bọc
  `.public-shell-search` là `display: none` dưới 820px; phép thử focus thật trả
  về `false`.

Bài học chung cho lần sau: `getComputedStyle(el).display` của CHÍNH phần tử
không nói lên nó có hiển thị hay không — phải duyệt tổ tiên, hoặc thử focus
thật. Và `backgroundColor` không thấy được gradient: nút `.btn-primary` từng bị
máy đo của tôi chấm 1.03:1, sự thật là 6.89:1 ở điểm dừng yếu nhất.

### 7. Hệ màu — đo thay vì cảm (2026-08-23)

Chủ dự án nêu: "chưa hài lòng về màu sắc… không cần quá nhiều màu". Dưới đây là
số đo, kèm hai lần tôi phải sửa lại chính kết luận của mình.

**Bảng màu HIỂN THỊ thực tế KHÔNG loạn.** Đo trang chủ (sáng), lọc theo *chroma
RGB* ≥ 40 (không dùng độ bão hoà HSL — xem bẫy bên dưới): đúng **ba tông nhấn**,
mỗi tông một nhiệm vụ tách bạch:

| Tông | Màu | Số chỗ | Diện tích | Việc |
|---|---|---|---|---|
| teal 180° | `rgb(3,90,105)` | 89 | 453.024 px² | hành động (nút, icon, select) |
| hổ phách 30° | `rgb(126,84,3)`, `rgb(142,93,16)` | 18 | 58.550 px² | thời gian/sự kiện (`ec-date`, `ec-countdown`) |
| terracotta 0° | `rgb(149,64,43)` | 9 | 44.592 px² | nhãn thương hiệu (`hero-kicker`, `.dot`) |

Ba tông nhấn có nhiệm vụ riêng là mức bình thường, không phải thừa.

**Chỗ thật sự phức tạp: HAI BỘ TỪ VỰNG MÀU SONG SONG.**

| | Token | Số lần dùng | Số file |
|---|---|---|---|
| Ngữ nghĩa `--color-*` | 53 | 588 | 35 |
| Thang thô `--sand/clay/leaf/river/night/alluvial-*` | 39 | **629** | **88** |

88 file với tay qua lớp ngữ nghĩa để lấy thẳng màu thô. Hệ quả đo được: hai sắc
kem gần trùng nhau ra đời từ hai hệ khác nhau — `--color-surface-subtle: #F1EEE6`
và `--sand-200: #F0EBE0` (ΔE 1.97, mắt không phân biệt được).

Đây mới là việc đáng làm, nhưng nó là **di cư 629 chỗ trên 88 file** — rủi ro hồi
quy hình ảnh diện rộng, phải làm theo đợt có ảnh đối chiếu, không gộp vào một
commit. Chưa làm.

**ĐÃ LÀM: gỡ 28 token màu chết** (53 dòng). Kiểm bằng "dấu vân màu" — tập hợp
mọi màu thực sự được vẽ của mọi phần tử hiển thị: trước và sau đều 63 mục, cùng
mã băm. Không đổi một pixel.

#### Hai lần tôi kết luận sai, ghi lại để không lặp

1. **"54 cặp token trùng nhau (ΔE < 3)" là SAI.** Tôi so sánh giá trị hex ở
   *một* chế độ. Kiểm lại từng cái: `--on-primary` có **4 bản** định nghĩa
   (`#FFFFFF` / `var(--night-canvas)` / hai bản tri-region), `--ink-900` đảo hẳn
   (`#2B2622` sáng → `#DCD6D2` tối), `--on-warning` có 4 bản. Chúng chỉ *trùng ở
   chế độ sáng*; mỗi tên mang một hợp đồng theo chế độ. Gộp lại sẽ vỡ chế độ tối.
   Trong 54 cặp, chỉ `--date-badge-ink` là thật sự hằng — một token, không đáng
   một đợt refactor.

2. **Bẫy đo: độ bão hoà HSL nói dối với màu gần trắng.** `#FDFCF9` cho
   `saturation = 50%` nên nền kem bị xếp nhầm vào nhóm "hổ phách", làm diện tích
   nhóm đó phồng lên 8,26 triệu px². Phải lọc bằng **chroma RGB** (max−min kênh);
   `#FDFCF9` có chroma = 4, đúng là trung tính.

#### Câu hỏi còn lại cho chủ dự án

Chữ đang mang sắc xanh (`rgb(8,26,22)`, hue 167) trong khi bề mặt là kem ấm
(hue 41–45). Ấm–lạnh đặt cạnh nhau là chủ ý (bộ token tên `--alluvial-*`,
`--river-*`, `--leaf-*` — bảng màu miền sông nước) hay là điều cần chỉnh? Đổi
sắc chữ là quyết định nhận diện, không tự làm.

### 8. Đối chiếu TIÊU CHUẨN thiết kế trước khi đổi (2026-08-23)

Chủ dự án yêu cầu nghiên cứu chuẩn trước khi quyết. Nguồn: bộ quy tắc trong
skill `ui-ux-pro-max` (`references/quick-reference.md` §6 Typography & Color,
`references/pro-rules.md`), đối chiếu bằng số đo trên trình duyệt ở 375px và
1280px.

#### Kết luận 1 — RÚT LẠI đề xuất đổi sắc chữ

Lượt trước tôi nêu: chữ mang sắc xanh (hue 167) trên bề mặt kem ấm (hue 41–45)
có thể là chỗ gợn. **Đo lại thì đây là kỹ thuật ĐÚNG CHUẨN, không phải lỗi.**

| | Màu | Chroma |
|---|---|---|
| Chữ | `rgb(8,26,22)` | **7,1%** |
| Bề mặt | `rgb(249,247,241)` | **3,1%** |

Material Design 3 dựng bảng neutral bằng cách **pha sắc từ màu nguồn ở chroma
thấp** — đúng dải này. Bộ token tên `--alluvial-*`, `--river-*`, `--leaf-*` cho
thấy đó là chủ ý nhận diện miền sông nước. **Không đổi.**

#### Kết luận 2 — ĐÃ VÁ: giãn dòng body

Quy tắc `line-height`: body phải 1.5–1.75. Đo được 5/10 khối body ở 1.3
(`.cm-content`, `.home .sh-sub`). Trùng khớp với ngưỡng vật lý tiếng Việt: tỉ lệ
mực đo được của Be Vietnam Pro là **1.33** — 1.3 nằm dưới cả hai. Đã sửa; đo lại
0/10 vi phạm.

#### Kết luận 3 — CHẨN ĐOÁN CHÍNH: hệ thống tốt, nhưng bị đi vòng

Quy tắc `color-semantic` nói thẳng: *"dùng token ngữ nghĩa, KHÔNG dùng hex thô
trong component"*. Quy tắc `font-scale`: *"thang chữ nhất quán"*. Dự án **có đủ
cả hai hệ**, nhưng phần lớn mã đi vòng qua chúng:

| Tầng | Hệ có sẵn | Số chỗ đi vòng | Số file |
|---|---|---|---|
| Màu | 53 token `--color-*` | **629** lần dùng thang thô | **88** |
| Chữ | 10 bậc `--text-2xs`…`--text-5xl` | **772** `font-size` viết cứng, **70** giá trị | **104** |

Riêng dải 0.7–0.9rem có **mười một** cỡ chữ: `.7 .72 .75 .76 .78 .8 .82 .84 .85
.88 .9` — chen trong 3.2px. Không ai nhìn ra đó là các bậc có chủ ý; nó đọc ra
thành thiếu nhất quán. Đây là nguyên nhân đo được của cảm giác "bố cục chưa ổn".

**Tin tốt: bệnh phân theo TUỔI của file, không lan đều.**

| File | Khai báo `font-size` cứng | Số giá trị |
|---|---|---|
| `assets/css/base.css` | 53 | 22 |
| `assets/css/shell.css` | 22 | 14 |
| `assets/css/catalog.css` | 14 | 8 |
| `pages/index.vue` | **1** | 1 |
| `assets/css/home-nocturne.css` | **0** | 0 |

File mới (nocturne, index.vue) dùng thang chuẩn đúng. Sprawl nằm ở CSS dùng
chung đời cũ. Nghĩa là di cư được theo từng file, không phải viết lại toàn bộ.

**VÌ SAO CHƯA LÀM NGAY:** thang `--text-*` là `clamp()` co giãn theo màn, còn giá
trị viết cứng thì cố định. Đổi `.78rem` (12,5px ở mọi khổ) thành `--text-xs`
(12→13px) làm ĐỔI hành vi trên máy lớn. Phải làm từng file, đo ảnh trước/sau ở
ít nhất 375/768/1280, không gộp một commit. Đề xuất thứ tự: `shell.css` (22 khai
báo, chi phối khung mọi trang) → `base.css` (53) → `catalog.css` (14).

### 9. Di cư thang chữ — đợt 1 đã xong 3 file (2026-08-23)

Chủ dự án chọn **hướng 2**: đẩy dải 13,6–16,5px lên `--text-sm`, chấp nhận chữ
nhỏ to lên trên máy lớn (hợp hướng chuẩn: ưa body ≥16px).

| File | Khai báo đã đổi | Cỡ khác nhau (360px) | Cỡ khác nhau (1280px) | Lệch tối đa |
|---|---|---|---|---|
| `shell.css` | 11 | 8 → **3** | 7 → **3** | 1,00px |
| `base.css` dải xs | 8 | 3 → **1** | 3 → **1** | 1,07px |
| `base.css` dải sm | 18 | 6 → **3** | 6 → **3** | 1,55px |
| `catalog.css` | 3 | — | — | 0,67px |

Kiểm hồi quy mỗi đợt: tràn ngang 0; 0 phần tử tràn khỏi cha ở 1280px; hàng lệnh
header vẫn dư 9,6px; vitest xanh.

#### Quyết định thiết kế đã áp dụng

- Hai chỗ đang ở 16px là **tiêu đề** (`.chat-panel-head h3`) và **nút chính**
  (`.hero-search button`) — KHÔNG đẩy xuống `--text-sm` (sẽ thành 14,1px trên
  điện thoại, hạ cấp vai trò). Đưa lên `--text-base` (16→18).
- `.brand .tld` (".vn") cho về `--text-xs` ở CẢ base.css lẫn shell.css — hai quy
  tắc cho cùng một thứ, trước đó lệch nhau.

#### KHÔNG đụng, có lý do

- **Ô nhập ở 16px** (`.hero-search input`, khối `@media max-width:640px`): đó là
  ngưỡng chặn iOS Safari tự phóng to. `--text-sm` cho 14,1px ở điện thoại, tức
  làm lỗi quay lại.
- **Cỡ icon**: trong dự án này `font-size` cũng là cách đặt kích thước IconLine
  (SVG 1em). `catalog.css` có 14 khai báo nhưng **11 là icon/glyph/chữ display**.
- **`a[href]::after` trong `@media print`**: `.8em` là cỡ tương đối; `--text-xs`
  là `clamp()` có `vw`, mà bản in không có viewport.

#### ĐÍNH CHÍNH số liệu tôi đã nêu

Tôi từng báo **"772 font-size viết cứng"** như thể tất cả là nợ chữ. Đếm lại
trên 723 khai báo đọc được bộ chọn: **160 (22%) là cỡ icon/glyph/logo**, **563
(78%)** mới là chữ nội dung. Nợ thật ~563, không phải 772.

#### Còn lại

~540 khai báo chữ nằm rải ở các file khác (`events.css`, `detail.css`,
`editorial.css`, `cards.css`, và các trang `.vue`). Cùng cách làm: map theo dải,
đo trước/sau ở 360/1280, giữ ngân sách lệch ≤1px, nhóm đối chứng cho icon.

### 10. Bẫy độ đặc hiệu của "sàn 16px" cho ô nhập

`base.css:915` có sàn `@media (pointer: coarse) { input…, select { font-size:
max(16px, 1em) } }` nhưng dùng **bộ chọn trần** — độ đặc hiệu (0,0,1). Mọi quy
tắc có lớp đều thắng nó.

Đo trên thiết bị cảm ứng 375px: `.public-context-control select` ra **12,07px**
→ iOS Safari tự phóng to khi chạm, và không tự thu lại. **Đã vá tại chỗ** bằng
`max(16px, var(--text-xs))`; đo lại 4/4 ô nhập ở 16px.

Rà nguồn còn **19 quy tắc** đặt `font-size < 16px` cho input/select/textarea,
phần lớn ở khu admin (`.usr-role-select`, `.cpl-place-select`,
`.admin-select-inline`, `.ent-inline-select`…). Sửa gốc là nâng độ đặc hiệu của
chính khối sàn — thay đổi diện rộng, cần đo riêng.

#### Mục 10 — ĐÃ XỬ LÝ XONG (2026-08-23)

18 quy tắc đã có sàn 16px trên thiết bị cảm ứng (17 quy tắc / 11 file, cộng
`.public-context-control select` ở shell.css).

**Cách vá và vì sao chọn nó:** thêm khối `@media (pointer: coarse)` NGAY TRONG
FILE chứa quy tắc gốc, dùng `font-size: max(16px, <cỡ gốc>)`.
- Cùng file ⇒ khớp scope. Với `<style scoped>` của Vue, quy tắc mang `[data-v-*]`
  (độ đặc hiệu 0,2,0) nên một quy tắc toàn cục KHÔNG bao giờ thắng được; chỉ có
  thể vá từ bên trong chính component đó.
- Đặt sau ⇒ thắng theo thứ tự nguồn khi độ đặc hiệu ngang nhau.
- `max()` ⇒ giữ nguyên ý định cỡ chữ ở màn hình chuột.
- Thuần cộng thêm (§2 B2): không sửa quy tắc nào có sẵn, gỡ ra là về nguyên trạng.

**Đã cân nhắc và LOẠI cách sửa gốc** (nâng độ đặc hiệu của chính khối sàn chung):
sàn dùng `max(16px, 1em)`, mà `1em` là cỡ chữ của phần tử CHA chứ không phải của
chính ô nhập. Nếu ép nó thắng bằng `!important`, một ô nhập cố ý đặt 20px sẽ bị
kéo về `max(16px, cỡ-cha)` — tức có thể CO LẠI. Vá từng chỗ thì không có rủi ro đó.

**Hai cái bị loại khỏi danh sách 19 sau khi kiểm từng phần tử:**
- `.dq-select-all` là `<label>`, không phải điều khiển nhập. Máy dò khớp theo
  chuỗi "select" trong TÊN LỚP nên bắt nhầm.
- `.admin-select-inline` (`layouts/admin.vue:540`) không được dùng ở bất kỳ
  template nào — **CSS chết**, nên gỡ trong một task dọn riêng.

**Đo hai chiều:**
- cảm ứng 375px: 4/4 ô nhập ở 16px, gồm `.error-search-input` là style scoped —
  xác nhận chèn đúng khối `<style>` thì có hiệu lực.
- chuột 1280px: giữ nguyên cỡ gốc (`.topbar-search input` 14,4px;
  `.stop-time-input`/`.stop-note-input` 13,6px). Sàn KHÔNG rò sang desktop.

#### Mục 9 — cập nhật: đã xong 5 file (2026-08-23)

| File | Đã đổi | Cỡ khác nhau | Lệch tối đa |
|---|---|---|---|
| `shell.css` | 11 | 8 → 3 (375px) · 7 → 3 (1280px) | 1,00px |
| `base.css` dải xs | 8 | 3 → 1 | 1,07px |
| `base.css` dải sm | 18 | 6 → 3 | 1,55px |
| `catalog.css` | 3 | — | 0,67px |
| `components.css` | 24 | 9 → 3 (13/16/18px) | 2,40px |
| `cards.css` | 6 | 4 → 2 | — |

**Tổng: 70 khai báo đã về thang token.**

Mỗi đợt đều có **nhóm đối chứng icon** (ví dụ `.star-rating .star` 24px,
`.avatar` 14,4px) để chứng minh không đụng nhầm sang nhóm cỡ-hình.

`components.css` được kiểm vỡ bố cục bằng cách **mở thật hộp Đăng nhập**: 1280px
modal 399×456, 360px modal 312×703 — cả hai đều 0 phần tử tràn.

#### Giới hạn kiểm chứng phải biết

Dev local **không có dữ liệu entity** (API 502), nên `.card` không render kèm nội
dung — trên `/dia-diem` thẻ cao 2px, tiêu đề 0 dòng. Vì vậy đợt `cards.css`
KHÔNG kiểm được hình học thẻ với chữ thật; riêng `.card h3` có
`-webkit-line-clamp: 2` nên đổi 17px → 16/18px sẽ làm chiều cao vùng kẹp đổi
theo. Cần xem lại trên môi trường có dữ liệu.

#### Còn lại, kèm lý do hoãn

- `events.css` (10 khai báo): là **lưới lịch**, ô ngày chật, cỡ hiện tại 8–12px.
  Tăng cỡ có nguy cơ vỡ ô nên phải đo vừa-ô từng breakpoint. Riêng
  `.cal-lunar.lunar-mid::before` 8px và `.cal-lunar` 9px ở ≤380px là **dưới xa
  mọi sàn cỡ chữ** — cần chủ dự án quyết là chấp nhận hay đổi cách hiển thị.
- `detail.css` (5), `detail-shared.css` (3), `dossier.css` (4): phần lớn là
  tiêu đề và cỡ container (`.framed-dossier` đặt 1rem cho cả khối), đổi sẽ kéo
  theo mọi thứ bên trong — cần một đợt riêng tập trung vào thang tiêu đề.
- Các trang `.vue`: chưa đụng.

#### Mục 9 — đợt 6, và một đính chính

`detail.css`: đổi 3 chỗ chữ lá (`.dc-credit` → `--text-2xs`, `.ms-cell` và
`.dc-photo-btn` → `--text-xs`). Giữ 4 chỗ: drop cap `::first-letter` (3.1em, cỡ
tương đối + thủ pháp biên tập), `.facts-heading-icon`, `.fact-ic` (**đã kiểm: là
hộp icon `flex: 0 0 26px; width/height: 26px`**), và `.detail-cover h1` (thuộc
thang tiêu đề, để đợt riêng).

**ĐÍNH CHÍNH cho commit f785d700.** Trong đó tôi viết rằng
`.framed-dossier__eyebrow` render 14,1px thay vì 16px vì "có stylesheet khác đè
với độ đặc hiệu cao hơn". **Sai.** Đo lại kỹ hơn: quét toàn bộ **69 stylesheet
(0 cái không đọc được)** thì **KHÔNG quy tắc nào nhắc tới class
`framed-dossier__eyebrow`**. Không có gì "đè" cả.

Sự thật đo được:
- Phần tử là `<p class="framed-dossier__eyebrow">`, cha `.framed-dossier__body`
  đang ở **16px**, còn nó ở **14,0972px** — đúng bằng `--text-sm` ở 360px.
- Vậy cỡ đến từ một quy tắc nhắm **thẻ `p`** trong phạm vi đó, chứ không phải
  quy tắc nhắm class.
- `nuxt.config.ts:63` có khai `~/assets/css/dossier.css` là CSS toàn cục, nhưng
  không stylesheet nào chứa class ấy ⇒ nghi **dossier.css không thực sự tới được
  DOM này**, hoặc class chưa bao giờ khớp. Chưa xác định dứt điểm.

Hệ quả cần theo: `dossier.css` có thể là **CSS chết hoặc chết một phần**. Trước
khi di cư nó, phải trả lời được câu "quy tắc nào đang thật sự tạo kiểu cho khối
dossier" — di cư một file không ai dùng là công vô ích, mà tệ hơn là tưởng đã
sửa trong khi giao diện không đổi gì.

#### ĐÍNH CHÍNH LẦN HAI — dossier.css KHÔNG chết. Máy đo của tôi sai.

Mục ngay trên tôi viết: "nghi dossier.css không thực sự tới được DOM… có thể là
CSS chết hoặc chết một phần". **Sai.** Bằng chứng dứt điểm, đo trên chính phần tử
`.framed-dossier` ở trang chủ:

| Thuộc tính | Đo được | dossier.css đặt |
|---|---|---|
| `display` | `grid` | `grid` |
| `gap` | `16px` | `var(--framed-dossier-gap)` |
| `padding` | `24px` | `var(--framed-dossier-padding)` |
| `font-size` | `16px` | `1rem` |

Bốn thuộc tính khớp chính xác ⇒ **file được nạp và đang áp dụng bình thường.**

**GỐC LỖI — công cụ, không phải hệ thống.** Tôi kết luận dựa trên việc duyệt
`document.styleSheets` rồi tìm chuỗi trong `selectorText`. Máy đo đó **nói dối**:
nó chỉ liệt kê được **347 quy tắc** cho toàn site — quá ít so với thực tế
(riêng base.css + shell.css + components.css + catalog.css đã hơn thế nhiều lần).
Vite ở chế độ dev nạp CSS qua JS nên CSSOM không phơi đủ. Tôi lại tin con số 0
mà không hỏi "347 có hợp lý không".

**Vì sao border/background vẫn ra rỗng:** biến giải đúng
(`--framed-dossier-border: oklch(88% 0.015 90)`,
`--color-surface: oklch(99% 0.004 90)`) nhưng `borderTopWidth: 0px` và nền trong
suốt ⇒ có quy tắc SAU đó ghi đè, tức biến thể ở trang chủ cố ý bỏ khung. Đây là
cascade bình thường, không phải lỗi.

Tương tự, `.framed-dossier__eyebrow` ra 14,1px vì bị một quy tắc đặc hiệu hơn của
biến thể trang chủ ghi đè — **không phải** vì "không quy tắc nào nhắc tới class"
như tôi đã viết.

**Bài học ghi lại để khỏi lặp:** khi đo CSS trong dev Vite, KHÔNG dùng
`document.styleSheets` làm bằng chứng phủ định. Dùng `getComputedStyle` trên
phần tử thật và so với giá trị mà quy tắc đặt — đó là bằng chứng độc lập với
việc CSSOM phơi ra được bao nhiêu.

**Hệ quả:** `dossier.css` di cư được bình thường. Điểm cần cân nhắc thật sự là
`.framed-dossier` đặt `font-size: 1rem` cho CẢ KHỐI — đổi sang `--text-base`
(16→18px) sẽ phóng to mọi thứ bên trong trên máy lớn, nên phải đo hình học khối
trước/sau chứ không chỉ đo cỡ chữ.

### 11. Rà UX theo bảng ưu tiên bộ chuẩn (2026-08-24)

Đo trên trang chủ, 360px. Ghi cả phần SẠCH để lần sau khỏi rà lại.

#### Đã vá

**Khoảng cách vùng chạm** — `.public-shell-command-row .auth-area` đặt `gap: 2px`
(shell.css:669), tức nút đổi chủ đề và nút Đăng nhập gần như dính nhau. Chuẩn
Touch & Interaction (hạng CRITICAL) đòi ≥8px. Đã đưa về `var(--space-2)`.
Đánh đổi: dư của hàng lệnh ở 360px từ 9,6px xuống 3,6px.

#### Đo được là SẠCH — không cần rà lại

| Chiều | Kết quả |
|---|---|
| Thứ bậc tiêu đề | 1 `h1`, chuỗi `1>2>2>2>2>3>2>…`, **0 chỗ nhảy bậc** |
| Ảnh | 8/8 có kích thước tường minh (**0 rủi ro CLS**), 8/8 có `alt` |
| Chỉ báo focus | **79/79** phần tử focus được đều có viền thấy rõ, đều khớp `:focus-visible` |
| Tương phản vòng focus | **6/6** đạt 6,44–7,34:1 (chuẩn ≥3:1), dày 2–3px |
| Bẫy focus modal | `role="dialog"` + `aria-modal="true"`; một phím Tab kéo được focus từ NGOÀI về trong modal |

`useModalA11y` dùng chung cho **12 component**; nó nhớ phần tử trigger, dời focus
vào phần tử đầu, bẫy Tab vòng đầu↔cuối, và (`:72`, `:77`) xử lý cả trường hợp
focus đang ở ngoài thì kéo về.

Ba cặp vùng chạm cách nhau 1px còn lại đều là **thẻ kề nhau trong dải cuộn
ngang** — bố cục bình thường, không phải nút nhỏ bấm nhầm.

#### BA LẦN MÁY ĐO NÓI DỐI TRONG PHIÊN — ghi để không lặp

1. **`document.styleSheets` trong dev Vite phơi thiếu.** Nó chỉ liệt kê 347 quy
   tắc cho toàn site. Tôi suýt kết luận `dossier.css` là CSS chết.
   ⇒ Không dùng nó làm bằng chứng PHỦ ĐỊNH. Dùng `getComputedStyle` trên phần tử
   thật rồi so với giá trị quy tắc đặt.

2. **`resize` mà không tải lại ⇒ `clamp()`/`vw` giữ giá trị cũ.** Tôi đọc tiêu đề
   "nhảy 28,39→36px (+27%)" và đã hoàn nguyên cả một commit vì tưởng mình thiết
   kế lại khối hero. Thực tế 28,39 là giá trị tính theo màn 360px.
   ⇒ Sau `resize` PHẢI tải lại trước khi đo bất cứ thứ gì dùng `clamp()`/`vw`.

3. **`.focus()` bằng JS không kích hoạt `:focus-visible`.** Quét lần đầu ra
   "0/79 phần tử có chỉ báo focus" — nghe như thảm hoạ tiếp cận, nhưng là ảo:
   trình duyệt chỉ bật `:focus-visible` khi focus đến từ bàn phím.
   ⇒ Bấm Tab THẬT một lần trước, để trình duyệt vào chế độ bàn phím, rồi mới quét.

Điểm chung của cả ba: tôi tin con số mà không hỏi "con số này có hợp lý không".
Khi kết quả nói "0" hoặc "100%" hoặc lệch quá lớn, phải nghi máy đo trước.

### 12. `/theo-mua` — cảnh báo cũ SAI, và ràng buộc hình học thật (2026-08-24)

Đợt quét trước ghi `/theo-mua` "dùng màu làm kênh duy nhất nối chú giải với 12
tháng (WCAG 1.4.1), swatch 2,1:1". **Đo lại thì không đúng.**

**Không có lỗi 1.4.1.** Vòng mùa là `role="group"` +
`aria-label="Chọn tháng trên vòng mùa"`, bên trong là **12 `<button class="ring-notch">`**,
mỗi nút có `aria-label="Tháng N"` và **`aria-pressed`** (12/12). Trạng thái chọn
được phơi cho trình đọc màn hình, không phải chỉ bằng màu. Các badge cũng mang
chữ ("Cao điểm", "T5–10") chứ không dựa vào màu.

**Vùng chạm thì đúng là nhỏ — nhưng vẫn hợp chuẩn.** Đo bằng `elementFromPoint`
trên từng nút (không dùng `getBoundingClientRect`, vì nút BỊ XOAY nên hộp bao
không phải vùng chạm):

| | Kết quả |
|---|---|
| Đạt 44×44 | **0/12** |
| Hẹp nhất | **18×44** (Tháng 1) |
| Dải | 18×44 · 32×32 · 45×24 · 44×23 · 46×24 |

Và **không sửa được bằng cách phóng to**: 12 nút quanh vòng bán kính 43px chỉ có
~22,5px cung mỗi nút. Muốn 44px thì vòng phải to hơn ~168px đường kính.

**Vì sao vẫn hợp chuẩn:** WCAG 2.5.5 có ngoại lệ **"Equivalent"** — vùng chạm nhỏ
được phép nếu cùng chức năng đạt được qua điều khiển khác đủ lớn trên **cùng
trang**. Ở đây mỗi tháng đều có `.quick-pick` **111×83px** (12 cái) và nút mùa
**58×67px**. Vòng mùa là lớp làm giàu, không phải đường duy nhất.

⚠️ **Điều kiện ràng buộc:** nếu sau này bỏ `.quick-pick` hoặc nhóm nút mùa thì
vòng mùa lập tức TRỞ THÀNH vi phạm 2.5.5. Ghi ở đây để ai đụng vào hai nhóm đó
biết mà kiểm lại.

**Đã sửa chú thích sai trong mã** (`pages/theo-mua.vue`): nó viết "26px hit-target
giữ được ý định 44px-ish" — đo ra 18–32px, không phải "44px-ish". Nay chú thích
ghi đúng số đo, lý do hình học, và điều kiện ràng buộc ở trên.

## KẾ HOẠCH HOÀN THIỆN UI — dựa trên số đo, không phải cảm nhận (2026-08-24)

### A. Hiện trạng, đo được

**Thang chữ:** đã di cư **139 khai báo / 11 file**. Còn lại:

| Khu | Còn | File |
|---|---|---|
| Công khai | **129** | 65 |
| Admin | **327** | 34 |

⇒ 72% nợ chữ còn lại nằm ở **admin**, tức phần người dùng cuối KHÔNG thấy.

**Màu:** con số thô 572 là ảo. Bóc ra:

| Lớp | Số | Là nợ? |
|---|---|---|
| Dự phòng trong `var(--x, rgba(...))` | 62 | **Không** — lối viết phòng thủ hợp lệ |
| Trung tính (trắng/đen/xám có alpha) | 368 | **Phần lớn không** — lớp phủ, bóng, scrim, gradient |
| **Có sắc (chroma ≥25)** | **140** | **Có** |

Trong 140 đó: admin ~51, công khai ~44, còn lại rải rác.

### B. Việc còn lại, xếp theo GIÁ TRỊ / RỦI RO

| # | Việc | Số | Giá trị | Rủi ro | Ghi chú |
|---|---|---|---|---|---|
| B1 | **140 màu có sắc** → token | 140 | Cao | Trung bình | Đây là "quá nhiều màu" mà chủ dự án nêu. Bắt đầu từ 44 chỗ công khai. |
| B2 | 129 cỡ chữ công khai còn lại | 129 | Trung bình | Thấp | Cùng khuôn mẫu đã chạy 11 lần |
| B3 | Quét **CSS chết** | ? | Trung bình | Thấp | Đã tình cờ thấy 5: `.region-tile`, `.thread-img-more`, `.admin-select-inline`, 2 dòng `.hero h1`. Cần đo bằng render thật, KHÔNG bằng grep |
| B4 | 327 cỡ chữ admin | 327 | **Thấp** | Thấp | Người dùng cuối không thấy. Làm sau cùng |

### C. ĐỪNG làm — đã đo và xác nhận KHÔNG phải nợ

- ~~**62 giá trị dự phòng** `var(--token, rgba(...))` — bỏ đi là làm yếu mã.~~ ĐÃ ĐẢO, xem §17.1: 31/40 dự phòng đang nói SAI giá trị token thật. Đã xoá 235 cái CHẾT (đo: 0 thay đổi). Nhưng câu cũ đúng cho dự phòng ĐANG SỐNG — tôi gỡ nhầm 12 cái và đã phải vá (§17.2).
- **368 màu trung tính có alpha** — bóng đổ, scrim, gradient. Token hoá chúng
  sinh ra hàng trăm token dùng-một-lần, tức làm hệ màu PHỨC TẠP HƠN, ngược đúng
  yêu cầu của chủ dự án.
- **Icon/glyph dùng `font-size`** — trong dự án này `font-size` là cách đặt cỡ
  IconLine (SVG 1em). Đếm thô luôn thổi phồng: `catalog.css` 14 khai báo thì 11
  là icon; nhóm ≥18px có 44 khai báo thì chỉ 12 là chữ.
- **Vòng mùa `/theo-mua`** — 0/12 nút đạt 44×44 nhưng HỢP CHUẨN nhờ ngoại lệ
  "Equivalent" của WCAG 2.5.5 (mục 12). Phóng to vòng là phá thiết kế mà không
  được gì.

### D. Chiều UX CHƯA đo — nên đo trước khi làm thêm

1. **Trạng thái form** — thông báo lỗi đặt ở đâu, có `aria-live` không, có gắn
   `aria-describedby` vào ô nhập không. Chuẩn xếp hạng MEDIUM nhưng ảnh hưởng
   trực tiếp tới việc đăng ký/đăng nhập.
2. **Trạng thái tải / rỗng / lỗi** trên các trang danh sách — đã có `EmptyState`
   dùng chung, nhưng chưa đo trạng thái ĐANG TẢI (skeleton có giữ chỗ đúng
   không, hay gây nhảy bố cục).
3. **Chuyển động** — mới xác nhận `scroll-behavior` tuân `prefers-reduced-motion`.
   Chưa đo transition/animation nào bỏ quên guard đó.
4. **Phủ trang** — mới rà 5/~74 route (`/`, `/theo-mua`, `/le-hoi`, `/cai-dat`,
   404). Nên sweep các trang danh sách chính bằng đúng bộ đo đã dựng.

### E. Bộ đo đã dựng được — dùng lại, đừng dựng lại

| Đo gì | Cách | Bẫy đã gặp |
|---|---|---|
| Tương phản | Vẽ ra canvas, mồi **hai màu** khác nhau | Token là `oklch`, regex vô dụng; một màu mồi thì mọi giá trị không-phải-màu đều ra đen |
| Nền hiệu dụng | Duyệt tổ tiên tới khi gặp nền đục | `alpha` sau khi hợp thành canvas luôn = 255 |
| Dấu tiếng Việt | `Range.getClientRects()` so hộp glyph với hộp dòng | Tỉ lệ mực Be Vietnam Pro = **1,33** — nhưng xem đính chính §17.3: tràn hộp dòng KHÔNG tự nó là lỗi, phải đo khoảng hở giữa hai dòng kề |
| Vùng chạm thật | `elementFromPoint` bắn tia từ tâm | `getBoundingClientRect` sai với phần tử BỊ XOAY |
| Focus | Bấm **Tab thật** một lần trước khi quét | `.focus()` bằng JS không kích hoạt `:focus-visible` |
| Quy tắc nào đang thắng | `getComputedStyle` trên phần tử thật | `document.styleSheets` trong dev Vite chỉ phơi 347/nhiều nghìn quy tắc |
| So trước/sau khi đổi khổ | **Tải lại** sau mỗi `resize` | `clamp()`/`vw` giữ giá trị của khổ cũ |

### KẾ HOẠCH — BẢN SỬA sau khi đo sâu hơn (2026-08-24)

Mục B1 ở bản kế hoạch trên ("di cư 140 màu có sắc") **sai cách đặt vấn đề**. Đo
kỹ thì 140 đó không phải một bài toán mà là **ba**, và một phần ba số đó là quà
miễn phí.

#### Tôi đã sai hai lần khi đếm token — ghi lại cách sai

**Lần 1:** trích token bằng regex từ `variables.css`, chỉ bắt được hex/rgb thuần
⇒ **169 token**. Nhưng file còn **37 `oklch/oklab`**, **19 `color-mix`**, **219
tham chiếu `var()`**. Ví dụ `--success: var(--color-success)` và `--color-success`
là oklch — tôi bỏ sót sạch. Kết luận "44 màu không trùng token nào" vì thế bị
thổi phồng.

**Lần 2:** thử gom tên token từ `document.styleSheets` ⇒ ra **0 token**, đúng cái
bẫy tôi ĐÃ ghi vào bảng công cụ (mục E) mà vẫn dùng lại.

**Cách đúng:** lấy TÊN token từ nguồn, rồi để trình duyệt GIẢI giá trị bằng
`getComputedStyle(root).getPropertyValue(name)` — xử được cả oklch, `var()` lồng
nhau và `color-mix`. Ra **111 token màu giải được**.

#### Ba tầng, không phải một

Đo trên 29 màu dùng nhiều nhất (108/140 lần dùng):

| Tầng | ΔE | Lần dùng | Việc |
|---|---|---|---|
| **T1** | **< 5** | **33** | **Đổi thẳng sang token.** Không đẻ token mới, không đổi màu. Rủi ro ~0. |
| T2 | 5–10 | 17 | Ép về token gần nhất; lệch nhẹ, đo từng chỗ |
| T3 | ≥ 10 | 58 | **Đổi màu thấy rõ ⇒ quyết định thiết kế, không phải refactor** |

**Ví dụ T1 (đổi được ngay, có lợi ngay):**

| Màu | Lần | Token trùng khít |
|---|---|---|
| `rgb(232,163,61)` | **12** | `--accent` |
| `rgb(116,171,181)` | 4 | `--river-legacy-dark` |
| `rgb(0,104,255)` | 4 | `--brand-zalo` |
| `rgb(220,38,38)` | 3 | `--save-red` |
| `rgb(156,61,34)` | 3 | `--clay-600` |
| `rgb(46,125,91)` | 3 | `--leaf-600` |
| `rgb(217,79,61)` | 2 | `--cat-dish-accent` |
| `rgb(196,135,42)` | 2 | `--accent-dark` |

#### T3 không phải "dọn dẹp" — là hệ màu THỨ HAI

Trong 58 lần dùng ΔE ≥ 10, **26 lần là màu hệ thống Apple/iOS**: iOS green
`rgb(52,199,89)` ×9, Apple blue `rgb(0,113,227)` ×4, iOS blue `rgb(52,120,246)`
×4, iOS orange `rgb(255,159,10)` ×4, iOS purple, iOS red, iOS teal. Gần như toàn
bộ nằm ở **khu admin** (`chua-phan-loai`, `entities`, `ai`, `bao-cao`).

Tức admin đang chạy một **ngôn ngữ màu khác** với phần công khai — không phải
sprawl ngẫu nhiên. Câu hỏi đúng cho chủ dự án KHÔNG phải "có dọn không" mà là:

> **Khu admin có nên dùng chung bảng màu miền sông nước với phần công khai không,
> hay giữ bộ màu hệ thống kiểu iOS cho quen tay người vận hành?**

Trả lời xong mới biết T3 là "di cư 58 chỗ" hay "để nguyên, ghi nhận là có chủ ý".

#### Thứ tự đề xuất (thay cho B1–B4 ở bản trên)

1. **T1 — 33 lần đổi thẳng.** Bắt đầu ngay: giảm màu thô, không đổi diện mạo,
   không thêm token. Đây đúng nghĩa "bớt màu" mà chủ dự án muốn.
2. **129 cỡ chữ công khai** — khuôn mẫu đã chạy 11 lần, rủi ro thấp.
3. **T2 — 17 lần**, đo từng chỗ.
4. **Quét CSS chết** bằng render thật (đã tình cờ gặp 5 chỗ).
5. **T3** — chờ chủ dự án trả lời câu hỏi admin ở trên.
6. **327 cỡ chữ admin** — sau cùng, người dùng cuối không thấy.

### 13. GỐC RỄ: thang chữ CO GIÃN ghép với thang line-height CỐ ĐỊNH (2026-08-24)

Suốt phiên tôi vá bốn chỗ lẻ "dấu tiếng Việt bị chen" (nav dưới, nav ngang, nút
chủ đề, `.atlas-hero-line1`). Đo tới tầng token thì cả bốn chỉ là **triệu chứng
của một lỗi kiến trúc**.

**Nguyên nhân:** `--text-*` là `clamp()` **co giãn theo màn hình**, còn `--lh-*`
là **rem cố định**:

```
--text-3xl: clamp(2.25rem, 1.957rem + 1.4634vw, 3rem);   /* 36 → 48px */
--lh-3xl:   3.25rem;                                      /* 52px, ĐỨNG YÊN */
```

Màn rộng ra thì cỡ chữ tăng, line-height không tăng ⇒ **tỉ lệ sụp xuống đúng ở
nơi chữ to nhất**.

**Đo ở 1280px**, ghép `--text-N` với `--lh-N` đúng như thiết kế, chữ mẫu
"Cộng đồng" (có dấu chồng cả trên `ồ` lẫn dưới `ộ`):

| Bậc | Cỡ chữ | line-height | Tỉ lệ | Hộp glyph | Dư chỗ |
|---|---|---|---|---|---|
| 2xs | 11 | 16 | 1.45 | 14 | **+2** |
| xs | 13 | 16 | 1.23 | 16 | 0 |
| sm | 16 | 20 | 1.25 | 20 | 0 |
| base | 18 | 24 | **1.33** | 23 | **+1** |
| lg | 22 | 28 | 1.27 | 28 | 0 |
| xl | 28 | 32 | 1.14 | 35 | **−3** |
| 2xl | 36 | 40 | 1.11 | 46 | **−6** |
| 3xl | 48 | 52 | 1.08 | 61 | **−9** |
| 4xl | 56 | 64 | 1.14 | 71 | **−7** |
| 5xl | 64 | 72 | 1.13 | 81 | **−9** |

**8/10 bậc dưới ngưỡng 1,33. 5/10 bậc chữ TRÀN hẳn khỏi hộp dòng.**

Chỉ hai bậc đạt: `2xs` (dư 2px) và `base` (dư 1px) — và `base` chỉ vừa đúng 1,33.

#### Vì sao chưa ai thấy

Với tiêu đề **một dòng**, `overflow: visible` nên dấu không bị cắt — nó chỉ lấn
sang khoảng trắng bên trên/dưới. Chỉ khi tiêu đề **xuống hai dòng trở lên** thì
dấu dòng dưới mới chạm chữ dòng trên. Và nó chỉ xảy ra ở **màn rộng**, nơi tỉ lệ
đã sụp — trên điện thoại các bậc lớn vẫn còn ~1,4.

#### Đề xuất — nhưng là QUYẾT ĐỊNH THIẾT KẾ, không tự làm

Sửa gốc là đổi `--lh-*` từ **rem cố định** sang **số không đơn vị** (tỉ lệ), để
leading co giãn cùng cỡ chữ:

```
--lh-3xl: 1.35;   /* thay cho 3.25rem */
```

Đánh đổi phải nói trước: mọi tiêu đề lớn sẽ **cao thêm 15–25%** ở màn rộng
(`3xl` từ 52px lên ~65px mỗi dòng). Đó là thay đổi diện mạo thấy rõ trên mọi
trang, nên cần chủ dự án duyệt.

Cách khác, ít xáo trộn hơn: chỉ nâng **5 bậc đang tràn** (`xl`…`5xl`) lên vừa đủ
1,33 thay vì 1,35–1,4, và giữ nguyên `2xs`…`lg`.

#### Bài học phương pháp

Bốn lần trước tôi vá theo kiểu **bắt gặp thì vá**. Chỉ khi dựng phép đo trên
**cặp token** (`--text-N` ↔ `--lh-N`) thay vì trên từng lớp CSS, mới thấy được
đây là một lỗi chứ không phải bốn, và mới trả lời được câu "đã hết chưa".

Ghi thêm: kiểm kê nguồn tìm được **104 khai báo `line-height < 1.33`**, nhưng
phần lớn HỢP LỆ — drop-cap `::first-letter` (0,78–0,82), và `1.00` trên icon
(`.cmd-icon`, `.card-arrow`, `.sheet-emoji`) hay chữ số (`.podium-points`,
`.ec-day`, `.error-code`) — những thứ không có dấu. Kiểm kê nguồn KHÔNG phân biệt
được; phải render mới biết chỗ nào thật sự chứa chữ có dấu.

### 14. "Rối" đến từ đâu — đo màu trong OKLCH và đo canh lề (2026-08-24)

Chủ dự án nêu: giao diện rối, nhiều màu không hợp logic và không hợp thị giác.
Đo trong **OKLCH** (không gian cảm nhận đều) và đo canh lề trên trang thật.

#### A. Bảng màu KHÔNG nhiều màu — nhưng nhiều TÊN

93 token màu giải được chỉ ra **49 màu khác nhau**. Tức **44 token (47%) là bí
danh** của một token khác.

| Màu | Số tên | Các tên |
|---|---|---|
| `rgb(37,93,52)` | **6** | `--color-success` `--green` `--orchard-600` `--secondary` `--secondary-fg` `--success` |
| `rgb(253,252,249)` | **5** | `--card` `--color-surface` `--color-surface-raised` `--surface` `--surface-white` |
| `rgb(3,90,105)` | **5** | `--color-action` `--color-focus` `--river-600` `--tertiary` `--tertiary-fg` |
| `rgb(249,247,241)` | 4 | `--alluvial-paper` `--bg` `--color-canvas` `--cream` |
| `rgb(149,64,43)` | 4 | `--color-brand` `--mangthit-600` `--primary` `--primary-fg` |
| `rgb(189,65,63)` | 4 | `--color-error` `--coral-error` `--danger` `--error` |

**Đây mới là gốc của mọi thứ khác.** Ba hệ đặt tên song song (ngữ nghĩa
`--color-*`, thang `--river-600`, vai trò `--tertiary`) cùng trỏ một giá trị ⇒
không ai biết nên dùng cái nào ⇒ 88 file với tay qua lớp ngữ nghĩa lấy màu thô
(mục 7). Vấn đề không phải "quá nhiều màu" mà là **quá nhiều tên cho cùng một màu**.

#### B. Về mặt thị giác, bảng màu thực ra CÓ kỷ luật

45 màu có sắc trải trên **6 họ tông** (tôi từng đếm 7 — sai, vì chia ô 30° cắt
đôi họ hổ phách; đo lại thì hue 60 và 90 đều là H≈73–77, một họ):

| Họ | Số | Vai trò |
|---|---|---|
| H≈30 clay/terracotta | 15 | thương hiệu |
| H≈73–77 hổ phách | 11 | nhấn / thời gian |
| H≈150 lá | 10 | thiên nhiên / thành công |
| H≈210 sông | 5 | hành động |
| H≈256–273 chàm | 3 | thông tin + thương hiệu Zalo |
| H≈183 teal | **1** | **mồ côi** — `--cat-attraction-accent` |

Điểm cần chỉnh, không phải "bớt màu" mà là **đều tay**:
- **Một họ mồ côi** (teal, đúng 1 token) — gộp vào 150 hoặc 210.
- **Chroma lệch tới 2 lần trong cùng họ** (H30: C từ 10,5 đến 21,5). Màu cùng
  họ mà cái tươi gấp đôi cái kia thì mắt đọc ra là ngẫu nhiên.
- **Ngoại lệ chroma cao nhất bảng là `--brand-zalo` (C=23,9)** — màu thương hiệu
  bên thứ ba, chấp nhận được, nhưng nên biết nó là thứ *chói nhất* trên site.
- **Thang độ sáng không đều**: họ H30 có L cụm ở 48,1 (×4) và 55 (×3) rồi hở.

#### C. Lỗ hổng chiều sâu: `--color-surface-raised` == `--color-surface`

Cả `--card`, `--surface`, `--color-surface`, `--color-surface-raised`,
`--surface-white` đều là `rgb(253,252,249)`. Tức **bề mặt "nổi" cùng màu bề mặt
nền** — không có thang độ cao bằng màu. Cộng với `--framed-dossier-shadow: none`
(đo ở mục 9), chiều sâu chỉ còn diễn đạt bằng đường viền.

Không có chiều sâu thì mọi khối nằm trên một mặt phẳng, mắt mất manh mối gom
nhóm — đây là một nguyên nhân "rối" độc lập với số lượng màu.

#### D. Bố cục: khoảng cách RẤT kỷ luật, canh lề thì KHÔNG

Đo `/lich-trinh` ở 1280px:

**Khoảng cách — tốt:** chỉ 11 giá trị khác nhau; **1197/1260 lần dùng nằm trong
thang `--space-*` (95%)**. Ngoại lệ hầu hết là đường mảnh 2px. Khoảng cách KHÔNG
phải nguồn gây rối.

**Canh lề — đây mới là chỗ hỏng.** 73 vị trí mép trái khác nhau, và các khối
CÙNG CẤP bắt đầu ở bốn mép lệch nhau:

| Mép trái | Bề rộng | Khối |
|---|---|---|
| 105px | 1060 | breadcrumb, `.controls` |
| 109px | 1052 | `.section-head`, `.pace-chips` |
| 110px | 1050 | `.catalog-hero-inner`, `.catalog-stats` |
| 122px | 1026 | `.chip-row` |

Nguyên nhân: mỗi cấp lồng nhau áp padding riêng — `.page`→`.breadcrumb`→`ol` cộng
20+20px, còn `.page`→`.catalog-hero`→`.catalog-hero-inner` cộng 20+25px. Bốn cột
nội dung lệch nhau **5–17px**.

Mắt rất nhạy với lệch mép dọc: 5px lệch trên một cạnh dài 1000px đọc ra ngay là
"không thẳng hàng", trong khi thêm một sắc cam thì hầu như không ai nhận ra. **Nếu
chỉ sửa được một thứ, sửa canh lề trước khi sửa màu.**

#### Đề xuất theo thứ tự tác động thị giác

1. **Thống nhất cột nội dung** — một token bề rộng container, mọi section dùng
   chung. Xoá 3 mép thừa.
2. **Tạo thang độ cao thật** — `--color-surface-raised` phải khác `--color-surface`
   (sáng hơn 1–2% L ở chế độ sáng), để thẻ tách khỏi nền.
3. **Gộp 44 token bí danh** — giữ MỘT tên chính thức mỗi màu, các tên còn lại
   thành `var()` trỏ về nó (hoặc xoá). Đây là việc làm cho hệ thống dễ dùng đúng,
   không đổi một pixel nào.
4. **Xử họ mồ côi H183** và **đều lại chroma trong họ H30**.

## 15. ĐÁNH GIÁ HIỆN TRẠNG — một bảng giải thích cả phiên (2026-08-24)

Đo tỉ lệ áp dụng của **lớp ngữ nghĩa** so với **lớp thô/viết cứng**, trên toàn bộ
`.vue` + `.css` (trừ `variables.css`):

| Tầng | Dùng token ngữ nghĩa | Dùng thô / viết cứng | Tỉ lệ áp dụng |
|---|---|---|---|
| Khoảng cách | 3250 | 321 | **91%** |
| Chữ | 1053 | 641 | 62% |
| Màu | 581 | 601 | 49% |
| **Bề rộng** | 34 | 323 | **10%** |
| **Độ cao** | 4 | 205 | **2%** |

### Điều bảng này nói

**Dự án KHÔNG thiếu hệ thống thiết kế. Nó đã xây hệ thống bốn lần rồi bỏ hoang
ba lần.**

- `--elevation-flat/card/card-hover/sticky/dropdown/dialog/tooltip/overlay` — **10
  mức ngữ nghĩa đầy đủ**, dựng trên `--shadow-xs…xl`. Dùng đúng **4 lần**. Còn
  lớp thô `--shadow-*` dùng **205 lần**.
- Bề rộng: chỉ có **2 token** (`--maxw`, `--measure-read`) cho **231 khai báo
  `max-width`**. Không hề có primitive cho *cột nội dung* — nên mỗi section tự
  chế padding.

**Và hai tầng bị bỏ hoang nhất đúng là hai thứ gây rối thị giác:**

| Tầng bỏ hoang | Hậu quả đo được |
|---|---|
| Bề rộng 10% | Khối cùng cấp bắt đầu ở **105 / 109 / 110 / 122px** — lệch 5–17px (mục 14D) |
| Độ cao 2% | `--color-surface-raised` == `--color-surface`, `shadow: none` ⇒ **không có chiều sâu**, mắt mất manh mối gom nhóm (mục 14C) |

Ngược lại, tầng **khoảng cách đạt 91%** — và đo trên trang thật thì khoảng cách
là thứ *duy nhất* sạch (1197/1260 lần dùng đúng thang).

⇒ **Bằng chứng rằng khi lớp ngữ nghĩa là đường dễ đi nhất, nó ĐƯỢC dùng.** Ba
tầng kia thất bại không phải vì người viết cẩu thả, mà vì:
- **Độ cao:** `var(--shadow-sm)` ngắn và rõ nghĩa hơn `var(--elevation-card)` —
  lớp ngữ nghĩa không mang lại lợi ích hiển nhiên nào.
- **Bề rộng:** không có token nào để dùng cho cột nội dung. Không thể áp dụng
  thứ không tồn tại.
- **Màu:** có **ba** hệ tên song song, 47% token là bí danh (mục 14A) — không ai
  biết nên chọn cái nào.

### Về "một cú nổ big bang"

Chủ dự án chấp nhận thay đổi lớn. Cần nêu rõ: **CLAUDE.md §2 B5 ghi "Không
big-bang. Commit nhỏ sau mỗi task."** Đó là bất biến của dự án, chủ dự án có
quyền gỡ — nhưng có cách đạt được QUY MÔ lớn mà không phá B5:

**Big bang về PHẠM VI, không big bang về COMMIT.** Mỗi bước dưới đây là một
commit độc lập, để lại hệ thống chạy được, có số đo trước/sau; cộng lại thì đủ
"nổ".

| # | Bước | Đổi diện mạo? | Rủi ro |
|---|---|---|---|
| 1 | **Gộp 44 token bí danh** — mỗi màu một tên chính thức, tên cũ thành `var()` trỏ về | **Không, 0 pixel** | Rất thấp |
| 2 | **Tạo primitive cột nội dung** (`--container-inline`, `--container-pad`) + áp cho các section của MỘT trang mẫu | Có — thẳng hàng lại | Thấp, đo được |
| 3 | Lan primitive đó ra các trang còn lại, mỗi trang một commit | Có | Thấp |
| 4 | **Tách `--color-surface-raised` khỏi `--color-surface`** (sáng hơn 1–2% L) + dùng `--elevation-card` cho thẻ | Có — thẻ nổi lên | Trung bình |
| 5 | Đổi `--lh-*` sang số không đơn vị (mục 13) | Có — tiêu đề cao thêm 15–25% | Trung bình |
| 6 | 33 màu ΔE<5 đổi thẳng sang token (mục "T1") | Không | Rất thấp |

Bước 1 và 6 **không đổi một pixel nào** mà vẫn gỡ được phần lớn cảm giác "rối"
ở tầng mã. Bước 2–4 mới là phần đổi diện mạo, và đó là phần cần chủ dự án nhìn
ảnh trước/sau.

**Đề nghị bắt đầu từ bước 1 + 6** (an toàn tuyệt đối, dọn sạch nền), rồi bước 2
trên một trang mẫu để chủ dự án duyệt diện mạo trước khi lan ra.

### 16. Token `-rgb` đã TRÔI khỏi token gốc — ~600 chỗ dùng (2026-08-24)

Định vá 19 màu alpha còn lại bằng `rgba(var(--X-rgb), α)` thì phát hiện cách đó
**không dùng được**: các token `-rgb` KHÔNG còn khớp token gốc của chúng.

**Xác minh bằng hai cách độc lập** — giải chuỗi `var()` từ nguồn, và đọc
`getComputedStyle` trên trang thật. Cả hai cho cùng kết luận.

Chế độ TỐI, đo trên trình duyệt — **6/6 lệch**:

| Token | Gốc | `-rgb` | Chênh |
|---|---|---|---|
| `--success` | rgb(124,164,131) | **rgb(130,225,170)** | xanh xám ↔ bạc hà sáng |
| `--warning` | rgb(206,167,112) | rgb(240,160,80) | |
| `--danger` | rgb(223,127,120) | rgb(255,105,97) | |
| `--accent` | rgb(232,163,61) | rgb(240,160,80) | |
| `--primary` | rgb(199,133,117) | rgb(196,105,78) | |
| `--secondary` | rgb(124,164,131) | rgb(75,169,125) | |

Chế độ SÁNG, giải từ nguồn — **5/6 lệch** (chỉ `--accent` khớp):
`--success` (37,93,52) ↔ (95,207,138) · `--warning` (133,90,22) ↔ (230,126,34) ·
`--danger` (189,65,63) ↔ (217,79,61) · `--primary` (149,64,43) ↔ (156,61,34) ·
`--secondary` (37,93,52) ↔ (46,125,91).

**Bán kính:** `--primary-rgb` 286 lần · `--accent-rgb` 118 · `--secondary-rgb` 97
· `--warning-rgb` 56 · `--danger-rgb` 32 · `--success-rgb` 8 — **gần 600 lần dùng**.

**Hệ quả thực tế:** ở bất kỳ chỗ nào viết
`background: rgba(var(--primary-rgb), .1)` cạnh `color: var(--primary)`, nền và
chữ là HAI MÀU KHÁC NHAU. Đây là một loại "màu không nhất quán" mà không đợt di
cư nào chữa được, vì nó nằm ở chính tầng token.

**Nguyên nhân:** `-rgb` không được DẪN XUẤT từ gốc mà **viết tay**, nên mỗi lần
đổi màu gốc là chúng trôi ra. `--accent` còn thiếu hẳn bản khai cho chế độ tối
trong khi `--accent-rgb` có — nên hai cái phân kỳ đúng ở chế độ tối.

**CHƯA SỬA, và cần chủ dự án quyết trước:** không rõ độ lệch là *lỗi* hay *chủ ý*
(ví dụ `-rgb` cố tình sáng hơn để làm nền tint). Nếu là lỗi thì sửa 6 token là
xong; nếu là chủ ý thì phải đổi TÊN chúng (ví dụ `--primary-tint-rgb`) vì tên
hiện tại nói dối. Sửa mù ~600 chỗ dùng là không được.

#### ĐÍNH CHÍNH commit 5313fa8f

Commit đó ghi "không đổi một pixel nào". **Sai với chế độ tối.** Bảy chỗ tôi đổi
từ `rgba(232,163,61,α)` sang `rgba(var(--accent-rgb),α)`: ở chế độ tối
`--accent-rgb` là (240,160,80) chứ không phải (232,163,61), nên bảy chỗ đó ĐỔI
MÀU trong chế độ tối.

Nhiều khả năng đổi như vậy là ĐÚNG HƠN — chủ đề tối cố ý dùng hổ phách sáng hơn
(`--accent-text: #e0b366`, chú thích ghi "lighter amber for AA as text on dark
bg"), mà giá trị viết cứng cũ thì phớt lờ chủ đề. Nhưng đó vẫn là một thay đổi
nhìn thấy được, và tôi đã tuyên bố ngược lại.

#### Vì sao 19 màu alpha còn lại CHƯA vá

Cả hai đường đều đang bị chặn:
- `rgba(var(--X-rgb), α)` — lan chính cái trôi ở trên ra thêm 19 chỗ.
- `color-mix(in srgb, var(--X) α%, transparent)` — về lý thuyết đúng, nhưng tôi
  CHƯA chứng minh được bằng đo: phép thử hỏng vì canvas không nhận `oklab()` nên
  `fillStyle` giữ giá trị cũ, cho 4/5 hàng "giống nhau" giả tạo. Cần viết bộ
  chuyển oklab→sRGB trong JS rồi so số, chưa làm.

---

### 17. Kiểm toán `var(--x, dự-phòng)` — và hai lần tôi tự đính chính (2026-08-24)

#### 17.1 ĐÍNH CHÍNH mục "C. ĐỪNG làm": "62 giá trị dự phòng — bỏ đi là làm yếu mã"

Kết luận cũ đó của tôi **sai một nửa, và nửa đúng nằm ở chỗ tôi không ngờ**.

Đo lại bằng trình duyệt, đối chiếu từng cặp (token thật ↔ dự phòng) ở cả hai
chế độ: **31/40 dự phòng màu nói SAI giá trị token thật**. Tệ hơn, cùng một
token có nhiều dự phòng đá nhau giữa các file:

| Token | Các dự phòng gặp trong mã | Giá trị thật |
|---|---|---|
| `--accent-rgb` | `245,166,35` · `33,150,83` · `240,160,80` · `255,193,7` | `232,163,61` |
| `--secondary-rgb` | `46,125,91` · `22,163,74` · `33,150,83` | `124,164,131` |
| `--ink-rgb` | `0,0,0` · `128,128,128` · `43,38,34` | theo chế độ |
| `--radius-lg` | `12px` · `16px` | `20px` |
| `--ease-out` | `ease` · `ease-in-out` · `ease-out` | `cubic-bezier(.2,.8,.2,1)` |

`33,150,83` là màu **lục** trong khi `--accent` là hổ phách. Chúng không thể
cùng đúng — đây là bản chép cũ còn sót, không phải mặc định có chủ đích.

Đã xoá **235 dự phòng chết** (120 màu ở `fa1bad20`, 115 trục khác ở `268344e4`).
Chứng minh bằng chụp 23 thuộc tính tính toán của mọi phần tử trước/sau, trên 4
mốc (trang chủ + `/dia-diem/...`, mỗi trang hai chế độ): **0 khác biệt**.

#### 17.2 Nửa ĐÚNG của kết luận cũ — và lỗi tôi đã gây ra rồi phải vá

`fa1bad20` gỡ nhầm **12 dự phòng ĐANG SỐNG**, vì bộ lọc dùng danh sách **loại
trừ** và tôi không biết hết cái cần loại. Sáu token đó không khai ở đâu cả, nên
dự phòng chính là giá trị duy nhất; gỡ xong thì `var(--x)` vô hiệu và thuộc tính
rơi về kế thừa. Hỏng ở: chữ trạng thái admin chế độ tối, icon toast lỗi, viền
focus nút ảnh đánh giá, viền ô tìm kiếm lỗi. Đã vá ở `9e5a27ef`.

**Bài học có thể dùng lại: dùng danh sách CHO PHÉP, đừng dùng danh sách LOẠI TRỪ.**
Chọn sai ở danh sách cho phép thì mất một cơ hội dọn. Chọn sai ở danh sách loại
trừ thì hỏng sản phẩm. Đợt hai (`268344e4`) làm đúng cách: 37 token, từng cái tự
hỏi `getComputedStyle(:root)` ở cả hai chế độ, đủ 37/37 mới đưa vào.

**Bài học thứ hai: đo rộng vẫn mù đúng chỗ mình vừa sửa.** 4 mốc × ~950 phần tử
báo "0 khác biệt" trong khi 12 chỗ đang hỏng — vì cả 4 mốc đều là trang công
khai, còn chỗ hỏng nằm ở admin/toast/ô-tìm-kiếm-lỗi. Bao phủ theo *số phần tử*
không thay bao phủ theo *đường đi*.

Còn giữ dự phòng có chủ đích ở 3 nhóm vì chúng đang sống:
`--rank-*`/`--lb-*` (chỉ đặt trong khối `.dark`), `--card-cover-height` (chỉ đặt
cho `.card.cat-product`), `--corner-shape` (trong `@supports`).

Thêm một dòng phải giữ vì lý do khác: `.hero-search button:focus-visible` nằm
trong danh sách trắng của `scripts/check-tri-region-contrast.mjs`, mà danh sách
đó **so chuỗi nguyên văn** giá trị khai báo. Tôi KHÔNG sửa danh sách trắng cho
test xanh — đó là cơ chế bảo vệ vùng hero. Đã ghi chú tại chỗ trong `base.css`.

#### 17.3 ĐÍNH CHÍNH: "mọi `line-height` < 1,33 là tràn" — báo động giả

Bảng công cụ đo (mục 12) ghi: *"Tỉ lệ mực Be Vietnam Pro = 1,33; mọi
`line-height` < 1,33 là tràn"*. Câu đó **đúng về hộp dòng nhưng sai về tác hại**.

Tràn hộp dòng tự nó không phải lỗi. Lỗi là khi **hai dòng liền nhau chạm nhau** —
cần dấu nặng ở dòng trên gặp dấu mũ ở dòng dưới. Đo khoảng hở thật bằng
`measureText().actualBoundingBoxAscent/Descent` cho từng cặp dòng, trên 5 trang:

| Trang | Phần tử nhiều dòng đã đo | Va chạm | Hở nhỏ nhất |
|---|---|---|---|
| `/` | 38 | 0 | +0,30px |
| `/cong-dong` | 22 | 0 | +1,40px |
| `/du-lich` | 35 | 0 | +1,40px |
| `/lich-trinh` | 80 | 0 | +1,40px |
| `/gioi-thieu` | 31 | 0 | +1,40px |

Thử luôn **trường hợp xấu nhất** (ép chuỗi `ộậặệợự` trên `ỗẫẵễỡữ` vào từng lớp):
107 tổ hợp lớp/cỡ, **đúng 1 chỗ âm — `.journey-action-copy strong`, −0,33px**,
tức dưới một pixel. **Không sửa**: sửa sẽ dịch bố cục 1,4px để đổi lấy thứ mắt
không thấy.

Hai chỗ trước đây tôi suy sai:
- h1 trang chủ tỉ lệ **1,12** nghe như hỏng nặng, đo ra hở **+13,48px** và
  **+5,48px**. Vì nó chạy **Fraunces** chứ không phải Be Vietnam Pro — ngưỡng
  1,33 đo trên font kia không áp được sang đây.
- Ngưỡng 1,33 là **trường hợp xấu nhất**, còn chuỗi thật hiếm khi xếp đúng cặp
  xấu nhất trên hai dòng kề.

⇒ Gỡ mục "các lớp tự đặt `line-height` còn dưới 1,33" khỏi danh sách nợ. Thang
token vẫn đúng khi sửa (rem cố định ghép clamp co giãn là lỗi thật, mục 13),
nhưng **các lớp đè lên nó thì không phải nợ**.

#### 17.4 Còn lại: 21 token mồ côi

Token không khai ở đâu, nên dự phòng chính là giá trị đang hiển thị — tức màu
cứng nấp dưới vỏ token. Đã xử 2 (`--leaf`/`--leaf-fg` = từ khoá CSS `green`,
xem `65edacec`). Còn 21, đáng chú ý:

- `--error-rgb` = `220,53,69` (đỏ Bootstrap) trong khi `--color-error-rgb` có thật
- `--secondary-fg-strong` `#34d399`, `--error-light` `#f87171`, `--accent-light`
  `#f59e0b` — bảng màu kiểu Tailwind nằm trong `dark-overrides.css`
- ~~`--rank-*` và `--lb-*` — chỉ `--rank-*` có bản chế độ tối, nên huy chương
  hai trang **hiện khác nhau trong chế độ tối**~~ — **ĐÃ XỬ, và câu trên SAI**:
  `cong-dong.vue:1876` có khối `.dark`, tôi đọc sót. Đo thực tế: vàng và bạc
  trùng khít, riêng đồng nâu lệch `#d4975a` vs `#d4956a` — **ΔE 2,07**, khó thấy
  chứ không phải "khác nhau". Vẫn là bằng chứng đúng cho luận điểm chép-tay-thì-trôi.
  Đã gộp thành `--medal-gold/silver/bronze` trong `variables.css`.
- `--radius-pill` ↔ `--radius-full`, `--page-gutter` ↔ `--container-pad`,
  `--tracking-wide` ↔ `--tracking-caps` — trôi TÊN, không phải trôi giá trị

Chưa xử vì mỗi cái cần một quyết định thiết kế (gộp tên nào, ai là nguồn), không
phải một phép biến đổi cơ học.

#### 17.6 CHỜ CHỦ DỰ ÁN: 3 màu Tailwind trong admin — đổi sang bảng màu thì 2/3 trượt AA

`--secondary-fg-strong` `#34d399`, `--error-light` `#f87171`, `--accent-light`
`#f59e0b` — cả ba **chưa từng được khai báo**, nên fallback chính là thứ đang hiện.
Đều là màu Tailwind, ngoại lai với bảng màu sông nước. Dùng ở `.dark .status-*`
(admin: người dùng, báo cáo).

**Đừng đổi thẳng sang token hệ — đo rồi, 2/3 trượt:**

| ô | Tailwind hiện tại | token hệ | đề xuất (giữ hue+chroma bảng màu) |
|---|---|---|---|
| active/resolved | `#34d399` **6,68** | `--secondary-fg` **4,44** ✗ | rgb(90,183,139) **5,26** ✓ |
| banned | `#f87171` **4,91** | `--error` **4,83** ✓ | rgb(230,133,126) **5,21** ✓ |
| pending | `#f59e0b` **5,73** | `--accent-dark` **4,01** ✗ | rgb(219,157,68) **5,21** ✓ |

Màu Tailwind nằm đó **vì chúng sáng hơn và đạt chuẩn**; bản tương đương trong
bảng màu quá trầm cho chữ nhỏ trên nền pha ở chế độ tối.

**Có lối ra giữ được bảng màu:** giữ nguyên hue và chroma của token hệ, chỉ nâng
độ sáng — cột cuối. Đánh đổi: tương phản xanh tụt 6,68→5,26 và hổ phách
5,73→5,21 (vẫn trên 4,5), đổi lại là hết màu ngoại lai. Mắt người vận hành sẽ
thấy khác: đE 7,48 / 4,76 / 4,81 so với hiện tại.

**TÔI KHÔNG TỰ ĐỔI, và không phải vì ngại quyết định thẩm mỹ.** Chưa xác định
được đường render thật: `pages/admin/bao-cao.vue:567` có `.dark .status-pending`
riêng mang `[data-v-*]` (độ ưu tiên 0,3,0) nên **thắng** quy tắc toàn cục ở
`dark-overrides.css:124` (0,2,0) và dùng `--accent-text` chứ không phải `--accent-light`.
Tức `--accent-light` có thể đã CHẾT trên trang báo cáo nhưng còn sống ở trang khác.
Sửa trước khi biết chỗ nào thật sự vẽ ra cái gì là sửa mò. Cần rà bằng render
thật trên từng trang admin trước.

Khác với câu hỏi admin ở §15 (26 màu hệ thống kiểu iOS) — đây chỉ là 3 token mồ côi.

#### 17.5 ✅ ĐÃ QUYẾT (chủ dự án chọn hướng b) — sắc huy chương chuyển sang NỀN badge

Có sẵn từ trước, không phải do đợt gộp token. Đo trên nền thẻ sáng (253,252,249):

| Màu | Tương phản | Ngưỡng cần | Kết |
|---|---|---|---|
| `--medal-gold` `#d4a017` | **2,31:1** | 3:1 (số 36px đậm) | **TRƯỢT** |
| `--medal-gold` `#d4a017` | 2,31:1 | 4,5:1 (số 12px ở `/cong-dong`) | **TRƯỢT** |
| `--medal-silver` `#8a8d91` | 3,24:1 | 4,5:1 (số 12px) | TRƯỢT |
| `--medal-bronze` `#b07b4f` | 3,52:1 | 4,5:1 (số 12px) | TRƯỢT |

Chế độ tối thì đạt thoải mái (10,1 / 8,19 / 6,87).

**Vì sao tôi không tự sửa:** giải bằng cách hạ độ sáng thì **vàng đạt 4,5:1 rơi
ra ngoài gam sRGB** (giữ chroma 0,13 ở L=0,56 cho ra rgb có kênh lam ÂM). Nói
cách khác, không tồn tại màu vừa "trông như vàng" vừa đủ tương phản trên nền gần
trắng. Hạ tới 3:1 thì được `#b68b16` — vàng mù tạt sẫm, đạt chữ lớn nhưng vẫn
trượt số 12px.

Hai hướng đã đặt ra — **(a)** đổi `--medal-gold` sáng thành `#b68b16` (vẫn trượt số
12px), **(b)** chuyển sắc huy chương sang nền badge. **Chủ dự án chọn (b).**

**Đã làm.** Số hạng 1–3 nay là huy hiệu tròn tô đầy sắc huy chương, chữ dùng token
mới `--medal-ink: #081a16` — cố tình KHÔNG đổi theo chế độ, vì cả ba nền huy chương
đều sáng ở cả hai chế độ nên chữ phải sẫm ở cả hai.

| | sáng | tối | ngưỡng |
|---|---|---|---|
| vàng | **7,56** | **10,53** | 4,5 |
| bạc | **5,39** | **8,54** | 4,5 |
| đồng | **4,95** | **7,16** | 4,5 |

Đạt AA ở **mọi cỡ chữ**, kể cả số 11px ở thanh bên `/cong-dong` — trước chỉ 2,31.

**Phải tô ĐẦY chứ không pha nhạt — đo mới biết.** Ý đầu là nền pha nhạt + chữ
`--ink`; trượt vì **bạc và đồng gần như không phân biệt được**: đE chỉ 2,03 ở mức
pha 22% và 4,22 ngay cả ở 45% — ngang độ lệch đồng nâu 2,07 mà tôi vừa gọi là "khó
thấy" ở 36e93fc4. Tô đầy cho đE 17,9 / 9,7 / 13,1.

**Ba bản chép, không phải hai.** Đợt gộp 36e93fc4 bỏ sót `bang-xep-hang.vue:219–221`
— ba dòng `.dark .podium-*` ghim cứng, một trong đó lại là `#d4956a` (bản đồng nâu
kia). Nay mọi mã màu huy chương chỉ còn trong `variables.css`.

**Chưa xem được bằng mắt.** Ô trình duyệt không hiển thị nên không chụp được ảnh;
mới đo được bằng số (màu, cỡ, bo tròn, tương phản, tràn ngang 0, bục giữ thứ bậc
270px/248px). Cần chủ dự án liếc mắt xác nhận thẩm mỹ.

**CSDL dev chỉ có 2 thành viên** nên hạng 3 và badge trong danh sách không tự render
được — đã đo trên phần tử dựng bù mang đúng thuộc tính scope của component,
không phải bằng suy luận từ CSS.


### 18. Soi bằng khuôn token ba tầng (kỹ năng `design-system`) — 2026-08-24

Chủ dự án yêu cầu gọi kỹ năng `design-system`. Khuôn của nó — **nguyên thuỷ →
ngữ nghĩa → component**, trong đó *tầng trên luôn TRỎ VỀ tầng dưới, không bao
giờ chép giá trị* — cho một cách gọi tên chính xác hơn hẳn cách tôi đang mò.

#### 18.1 Hai thang bo góc KHÔNG phải hai thang cạnh tranh

Tôi đã đọc sai suốt mấy đợt. Đúng ra:

| | token | vai trò |
|---|---|---|
| nguyên thuỷ | `--radius-xs/sm/md/lg/xl/full` = 4/10/14/20/28/9999 | tên theo cỡ, vô nghĩa ngữ cảnh |
| mục đích | `--radius-control/surface/sheet` = 8/12/20 | tên theo công dụng |
| component | `--framed-dossier-radius`, `--theme-control-radius` | **đã trỏ về tầng mục đích đúng chuẩn** |

Tầng mục đích **giữ px thô thay vì trỏ về nguyên thuỷ** — đó chính là cơ chế
trôi, y hệt bệnh `-rgb` ở §16.

Nhưng đo kỹ hơn thì đây **không phải token hoang**: `--radius-control/surface`
nằm trong `shell.css`, `catalog.css`, `home-nocturne.css` — tức phần mã MỚI.
Đây là **một cuộc di trú thang bo góc đang dang dở**.

**Mức hoàn thành đo được: thang cũ 370 lượt dùng, thang mới 32 — mới 8%.**
(Không tính `--radius-full` 159 lượt vì nó dùng chung cho cả hai.)

✅ **ĐÃ QUYẾT 2026-08-24: chủ dự án chọn (a) — ĐI TIẾP.** Hai hướng đã đặt ra:
- **(a) Đi tiếp:** mã mới chỉ dùng `--radius-control/surface`, dần chuyển 370 chỗ.
  Vốn là hướng đang đi, nhưng 8% sau nhiều đợt thì tốc độ đó là hàng năm.
- **(b) Quay về:** `--radius-control: var(--radius-sm)` (8→10px),
  `--radius-surface: var(--radius-md)` (12→14px). Chỉ đổi 32 chỗ, mỗi chỗ 2px —
  đo được là không có lỗi hình học nào phát sinh. Xong ngay, còn một thang.

Tôi nghiêng về (b) nhưng chủ dự án chọn **(a)**. Đã làm cho quyết định đó **CÓ RĂNG**,
vì "mã mới dùng token mới" mà không có cổng canh thì chỉ là lời hứa — 8% sẽ nằm yên
ở 8%:

- **Rule mới R30.8** (`check_fe_tokens`, `fe_radius_scale`), **hard-ratchet**,
  baseline **372**. Đếm từng match `var(--radius-xs|sm|md|lg|xl)` trên
  `pages/ components/ layouts/ assets/css/` — R30.8 quét CẢ `assets/css` (khác
  `_ROOTS` của R30.2/R30.3 vốn chỉ nhắm `.vue`), vì thang bo góc sống chủ yếu ở đó.
- **KHÔNG bắt** `--radius-full` (dùng chung cả hai thang) và `--radius` (bí danh ngữ
  nghĩa, sẽ trỏ sang `--radius-sheet` khi di trú xong).
- **Đã chứng minh ratchet cắn**, không chỉ tin: thêm một `var(--radius-sm)` vào một
  file thử → count 373 > 372 (chặn); gỡ ra → về 372. Con số 372 cũng được đối chứng
  bằng hai cách đếm độc lập (script riêng và checker) — trùng khớp.

**ĐẢO LẠI một việc của đợt trước:** 07c6d967 xoá `--radius-sheet` vì lúc đó nó có 0
lượt dùng — đúng với bằng chứng khi ấy. Nhưng theo hướng (a) thì `--radius-sheet`
(20px) chính là **đích đến** cho 101 lượt dùng `--radius-lg`. Đã khôi phục kèm ghi chú.

**Khoảng trống cần biết:** thang cũ có 5 bước (4/10/14/20/28), tầng mục đích mới có 3
(control 8 / surface 12 / sheet 20). Chưa có đích cho `--radius-xs` (4px, 3 lượt) và
`--radius-xl` (28px, 24 lượt). Gặp chỗ không map được thì đó là **tín hiệu cần thêm
một bước mục đích**, KHÔNG phải cớ quay lại thang cũ.

Tôi nghiêng về **(b)**: 2px không ai thấy, mà bỏ hẳn được một thang khỏi đầu.
Nhưng nó ghi đè lựa chọn 8px có chủ đích của nocturne nên phải hỏi.

#### 18.2 Đã làm ngay (chắc chắn đúng, không cần quyết)

- **Xoá `--radius-sheet: 20px`** — chép y `--radius-lg`, và `var(--radius-sheet)`
  xuất hiện **0 lần** trong toàn `web-nuxt`. Token chết.
- **`--medal-ink` nay trỏ về `--mekong-ink`** thay vì chép `#081a16`. Đây là bản
  sao **do chính tôi tạo ra sáng nay** ở 36e93fc4 — đúng lỗi tôi đang đi sửa.

  **Bẫy đo lại xuất hiện:** máy dò của tôi so *chữ khai báo* nên tưởng hai token
  bằng nhau (`#081A16`). Nhưng `--mekong-ink` computed ra `oklch(20% 0.025 180)`
  — có khai báo sau đè lên, y như `--harvest-700` ở §16. Đo thật: mekong
  (7,9 · 25,8 · 22,4) so với medal (8 · 26 · 22), **ΔE 0,147** — dưới ngưỡng
  nhìn thấy rất xa. Nên trỏ được. Tương phản huy chương sau khi đổi:
  sáng 7,57/5,39/4,96 · tối 10,55/8,55/7,17 (trước: 7,56/5,39/4,95 · 10,53/8,54/7,16).

#### 18.3 Lớp lỗi rộng hơn: token CHÉP giá trị thay vì TRỎ

Quét toàn `variables.css` tìm token chép y giá trị thô của token khác trong
cùng họ (loại các trùng ngẫu nhiên khác thang như `--radius-xs: 4px` với
`--space-1: 4px`). Còn lại là lỗi tầng thật:

| giá trị | các token cùng chép | nên trỏ về |
|---|---|---|
| `#FFFFFF` | `--on-primary`, `--on-secondary`, `--on-tertiary`, `--on-error`, `--on-warning`, `--date-badge-ink`, `--color-surface-raised` | `--white` |
| `400` / `500` / `600` | `--weight-body/caption/display` · `--weight-label/title-sm` · `--weight-headline/title` | `--weight-normal/medium/semibold` |
| `1px solid var(--line)` | `--card-outlined-border`, `--detail-divider` | `--divider-default` |
| `rgba(0,0,0,.72)` | `--scrim` | `--overlay-dark` |
| `255,255,255` | `--text-on-dark-rgb` | `--white-rgb` |
| `#2B2622` | `--on-accent` | `--ink-900` |
| `#7DAEBA` | `--color-admin-action` | `--night-river` |
| `cubic-bezier(.4,0,.2,1)` | `--ease-standard` | `--ease-in-out` |

**~20 token, đổi xong thị giác KHÔNG đổi một pixel** (giá trị y hệt), nhưng trôi
trở thành bất khả về mặt cấu trúc. Chưa làm vì 7 token nhóm `#FFFFFF` có override
theo chế độ (`--on-warning` khai 4 lần, `--color-surface-raised` 5 lần) trong khi
`--white` chỉ khai 1 lần — phải xử lý TỪNG khai báo, không thay hàng loạt được.
Việc này nên đi kèm ảnh chụp trước/sau ở cả hai chế độ.


### 19. Trang chủ hiển thị gì, vì sao, và cái gì thừa — đo trên trang thật (2026-08-24)

Câu hỏi của chủ dự án: *vì sao trang chủ hiển thị như vậy, cái gì cần, cái gì
không, vừa đủ, không dư thừa*. Đây là câu hỏi KIẾN TRÚC THÔNG TIN, không phải CSS.

#### 19.1 Đã có spec, và spec đã chẩn đoán đúng bệnh từ tháng 7

`docs/superpowers/specs/redesign-concepts/01-home.md` (STATUS: active) viết:

> *"Trang chủ hiện đọc như MỘT trang landing được lắp từ 12 block độc lập, không
> như MỘT câu chuyện có mở-thân-kết."*

Spec chốt **ba tầng nhịp** — A (tràn viewport, ảnh lớn, nghỉ mắt) · B (hai cột
ảnh+chữ) · C (chuỗi ngang lướt nhanh) — và một luật kiểm được:
**"không cho phép 2 section liên tiếp cùng tầng."**

Nhưng spec cũng ghi *"viết TRƯỚC declutter"* và *"declutter thắng khi xung đột"*.
Đợt declutter sau đó gỡ đúng các khối tầng A/B mà spec dựa vào (StorySpread,
EntityFeature #2, "Hỏi trợ lý AI"). **Hai đợt kéo ngược chiều nhau, kết quả là
trang không còn tầng A lẫn tầng B.**

#### 19.2 Số đo hiện trạng (khách vào LẦN ĐẦU, đã xoá recent/visit)

| mục | cao | đơn vị bấm được | px mỗi đơn vị |
|---|---|---|---|
| dòng ngữ cảnh | 77 | 1 | 77 |
| hero | 894 | 3 | **298** |
| "Hôm nay bạn muốn bắt đầu…" + "Khám phá theo nhu cầu" | 797 | 11 | **72** |
| "Tín hiệu địa phương" | 644 | 5 | **129** |
| "Từ cộng đồng" | 673 | 9 | **75** |
| "Giữ mạch khám phá" | 181 | 2 | **91** |

**Tổng: 4011px = 5,6 màn hình · 31 lựa chọn bấm được.**

Nhịp lộ ra ngay ở cột cuối: hero cho một đơn vị **298px** thở, rồi tụt xuống
**72 / 129 / 75 / 91** — bốn khối danh sách dày, đều, liên tiếp. Đúng bốn lần vi
phạm luật "không 2 section liên tiếp cùng tầng" của spec.

#### 19.3 Phát hiện nặng nhất: TOÀN TRANG CHỦ CÓ ĐÚNG MỘT ẢNH

Đo trên DOM: **1 thẻ `<img>`** (`cua-com-duyen-hai.webp`, 482×327, trong hồ sơ
hero) · **0 ảnh nền CSS** · **0 SVG minh hoạ lớn**.

Một trang du lịch/OCOP cuộn 5,6 màn hình với một tấm ảnh. Và đây KHÔNG phải "ô
ảnh bị bỏ trống": mã chỉ có **một ô ảnh duy nhất**, và nó đã được lấp. Trang được
dựng thành trang chữ-và-hộp.

Đây mới là gốc của cảm giác "rối" hơn là màu hay khoảng cách: **không có gì để
mắt nghỉ.** Mọi thứ đều là chữ trong khung, cùng một tông xám-xanh, 31 lần.

#### 19.4 Trùng lặp: đo được, nhưng KHÔNG nằm ở chỗ tôi đoán ban đầu

Giữa các mục với nhau, trùng lặp **thấp**: 32 liên kết → 26 đích, chỉ 2 đích lặp
qua nhiều mục. Trùng lặp thật nằm chỗ khác:

- **"Khám phá theo nhu cầu" (7 ô): 6/7 đích ĐÃ CÓ trong header (20 link) VÀ trong
  footer (22 link).** Cùng 6 đích xuất hiện ba lần trên một trang.
  **NHƯNG** đo ở 360px: header chỉ còn hiện **1 link** (logo), 19 cái kia nằm sau
  nút "Mở danh mục" — còn khối này hiện đủ 7 ô. Tức nó **thừa trên desktop,
  nhưng là điều hướng DUY NHẤT nhìn thấy được trên mobile**. Không được xoá thẳng.
- **"Giữ mạch khám phá khi bạn ĐÃ CÓ một điểm bắt đầu"**: với khách lần đầu, mục
  này vẫn render, tiêu đề nhắm vào người quay lại, và chỉ có 2 link — `/ban-do` và
  `/lich-trinh` — **cả hai đều đã xuất hiện trước đó trên trang**. Ở trạng thái
  rỗng nó trùng 100%. Có tín hiệu cá nhân thì JourneyActionRail mới thêm giá trị.

- **Tôi đoán sai một lần, ghi lại:** tôi nghĩ "Hôm nay bạn muốn bắt đầu thế nào?"
  và "Khám phá theo nhu cầu" là hai menu hỏi cùng một câu. Đọc nhãn thật thì khác
  hẳn — A đưa **câu trả lời có lý do** ("Còn 22 ngày · Ngày hội Thanh trà",
  "Tháng 8 · đang vào mùa", "4.9 điểm"), B đưa **danh mục**. A là thứ hiếm và
  đáng giữ; B mới là thứ trùng chrome.

#### 19.5 CHỜ CHỦ DỰ ÁN: 5 nhãn "Chưa rõ nguồn" trên cửa trước

Đo được **5 mục** trên trang chủ mang nhãn `Chưa rõ nguồn`, trong đó **3 mục** kèm
`Chưa rõ thời điểm cập nhật`: hồ sơ hero (Cua cốm Duyên Hải), và 4 mục trong "Tín
hiệu địa phương" (Đờn ca tài tử, Mật ong rừng bần, Peace Farm, Cháo Cua Đồng).

Nhãn này **trung thực và đúng §1.7** — không được claim đã xác minh khi `verifiedAt`
chưa phủ. Nhưng *trung thực* và *phải phát trên trang chủ* là hai việc khác nhau:
cửa trước đang nói với mọi khách lần đầu, năm lần, rằng site không biết nguồn nội
dung của mình. Chuyển tiết lộ đó xuống trang chi tiết — nơi người ta thực sự cân
nhắc một địa điểm — vẫn giữ nguyên tính trung thực.
**Đây là quyết định về tín nhiệm, không phải kỹ thuật → tôi không tự làm.**

#### 19.6 Việc làm được ngay, không cần quyết

- Mục "Giữ mạch khám phá" chỉ hiện khi CÓ tín hiệu cá nhân (giống cách "Dành cho
  bạn" đã làm ở declutter-3 B1-7). Khách lần đầu bớt một mục 181px không mang gì mới.
- Bù lại tầng A: dự án có `scripts/gen_image.py` (ảnh AI, §1.5) và đã có sẵn
  `HeroIllustration`, `EntityHeroPlaceholder`, `useCategoryPlaceholder`. Chèn MỘT
  khối tràn viền ở khoảng 60–70% chiều dài trang là đúng thứ spec §3 yêu cầu và
  là đòn bẩy lớn nhất cho cảm giác "đỡ rối" — vì nó cho mắt chỗ nghỉ đầu tiên sau hero.


### 20. Đo 3 site cùng loại bằng CÙNG một bộ thước (2026-08-24)

Câu hỏi: trang chủ có thừa không, có cần cắt không. Thay vì đọc "best practice"
chung chung, tôi chạy **đúng bộ đo đã dùng cho trang chủ** lên các site cùng loại:
cấp vùng/tỉnh, du lịch CỘNG đặc sản địa phương.

| site | màn hình | ảnh lớn | ảnh/màn hình | đơn vị bấm được | px mỗi đơn vị |
|---|---|---|---|---|---|
| **vinhlong360** | **4,9** | **1** | **0,2** | 52 | **75** |
| Emilia Romagna (Ý) | 8,0 | 10 | 1,3 | 48 | 133 |
| Visit Jeju (Hàn) | 7,0 | 19 | 2,7 | 40 | 140 |

Đo ở 1280×800, chỉ tính phần tử **giao ngang với khung nhìn** (xem "bẫy" dưới).

#### 20.1 Kết luận NGƯỢC với giả định ban đầu

Trang chủ vinhlong360 **ngắn nhất** (4,9 so với 7–8 màn hình), nhồi **nhiều lựa
chọn nhất** (52 so với 48 và 40) vào **~60% không gian dọc**, với **1/10 đến 1/13
lượng ảnh**.

Nghĩa là **"cắt bớt nội dung" KHÔNG phải hướng đi**. Trang đã ngắn hơn các site
cùng loại rồi. Vấn đề là **mật độ**: cùng số lựa chọn nhưng ít hơn 40% chỗ thở, và
gần như không có hình để mắt nghỉ. Hai site kia dài hơn nhưng **đọc nhẹ hơn**.

Suy ra ưu tiên đúng: **giãn ra và thêm hình**, không phải bỏ mục. Trùng khớp với
§19.3 (toàn trang chủ có đúng 1 ảnh) và với spec `01-home.md` §3 (thiếu hẳn tầng A
— khối tràn viền cho mắt nghỉ).

#### 20.2 BẪY ĐO — máy đo đầu tiên của tôi cho số sai gấp 13 lần

Bản đo đầu đếm **244 ảnh lớn** ở Visit Jeju và 288 đơn vị bấm được → 19px mỗi đơn
vị. Vô lý. Nguyên nhân: site dùng nhiều **carousel**, các slide ngoài màn hình vẫn
nằm trong DOM với kích thước đầy đủ, nên bị đếm hết.

Sửa: chỉ tính phần tử **giao ngang với khung nhìn** (`rect.left < vw && rect.right > 0`)
và loại `visibility:hidden` / `display:none` / `opacity:0`. Sau khi sửa: 19 ảnh, 40
đơn vị, 140px — hợp lý.

**Bài học:** so sánh nhiều site thì bộ đo phải chịu được carousel/lazy-load, nếu
không thì site nào dùng nhiều carousel sẽ tự động "thắng" một cách giả tạo. Và phải
**đo lại TẤT CẢ** bằng bộ đã sửa — tôi đã đo lại cả ba, không dùng lẫn số cũ.

#### 20.3 Giới hạn của kết luận này — đọc trước khi dùng

- **n = 3.** Đủ để bác bỏ "cần cắt bớt", KHÔNG đủ để chốt một con số chuẩn.
- Đo **một lần, một thời điểm, một ngôn ngữ** (bản `/en`). Site du lịch đổi nội dung
  theo mùa và theo địa lý người xem.
- Chỉ đo **desktop 1280**. Chưa đo mobile — mà mobile mới là nơi khối "Khám phá theo
  nhu cầu" có lý do tồn tại (§19.4).
- **Không đo được thêm site.** Việc đo cần DOM thật qua ô trình duyệt trong ứng dụng,
  mà thao tác đó đã được xác định là nguyên nhân làm Claude Code Desktop chết
  (3 lần trùng khớp mốc thời gian: 20:49, 22:34, 22:38). Dừng ở 3 điểm dữ liệu là
  quyết định có chủ ý, không phải bỏ dở.


### 21. Đối chiếu trang chủ với HIẾN PHÁP THIẾT KẾ của chính dự án (2026-08-24)

Không dùng được trình duyệt (xem §20.3), nên chuyển hướng: đối chiếu mã nguồn với
`00-narrative-system.md` — tài liệu định-hướng-sáng-tạo mà chưa ai kiểm lại.
Phần lớn checklist của nó **grep được**.

#### 21.1 Phát hiện chính: trang chủ là trang DUY NHẤT tự tắt motif

```
pages/index.vue:728    .home .hero { background-image: none; }
```

Dòng này **không có ghi chú giải thích**, nằm lọt giữa quy tắc lưới responsive và
phần kicker — trông như reset phòng thủ sót lại, không như quyết định thiết kế.

Trong khi đó `.catalog-hero` có hệ motif hoàn chỉnh, đã ship, có tài liệu:
- `::before` mang SVG line-art theo vùng (sóng nước / trái cây / dừa / sen), khoá
  theo biến thể `cat-*` — chú thích trong `catalog.css:49` ghi *"P1: region-themed
  SVG behind text, CSS-only, zero page edits"*
- nền `linear-gradient(135deg, --primary-light, --bg-warm)`
- `animation: hero-motif-sway 8s infinite` — **đúng một ambient/viewport**, hợp lệ
- **dùng trên 12+ trang**: ban-do, cong-dong, danh-ba, dia-diem, gioi-thieu,
  kham-pha, khu-vuc, le-hoi, lich-trinh, tuyen-duong…

**Tức mọi trang khác đều có motif sông nước trong hero; riêng trang chủ tắt nó đi.**
Đây là câu trả lời cụ thể nhất cho "vì sao trang chủ trông trống hơn phần còn lại
của site" — và nó là MỘT DÒNG CSS.

#### 21.2 `HeroIllustration.vue` được viết xong nhưng CHƯA TỪNG được dùng

Grep toàn `pages/`, `layouts/`, `components/`: **không có nơi nào import hay render**
nó. Component 200+ dòng, có sẵn ba lớp sóng `wave-drift` lệch pha và `hero-motif-sway`.

Nghĩa là **viên gạch tầng A mà §19.6 nói trang chủ đang thiếu thì đã có sẵn** — chỉ
chưa nối vào. Nối lại rẻ hơn nhiều so với dựng mới.

*(Bốn vòng lặp ambient vô hạn trong component này vi phạm luật "một ambient/viewport"
của §4.1 — nhưng vì nó là MÃ CHẾT nên không ảnh hưởng gì lúc chạy. Nếu nối vào thì
phải rút xuống còn một.)*

#### 21.3 Những gì spec ĐÒI và code ĐÃ LÀM ĐÚNG

Đối chiếu §2 "Story Card" — thứ spec gọi là *"thay đổi đòn bẩy cao nhất toàn site"*.
`EntityCard.vue` đạt **4/4**: tên dùng `--font-editorial`, có grain overlay, dateline
eyebrow hairline, rule tri-tỉnh river→amber→clay. Đã làm, không phải nợ.

- **Grain overlay**: 67 chỗ, và có `feTurbulence`/`fractalNoise` thật (3 chỗ) chứ
  không phải gradient phẳng giả texture — đúng anti-slop tell #1 của §4.4.
- **Superlative rỗng**: chỉ 1 chỗ (`"không thể bỏ qua"` trong `utils/routesContent.ts`).
  Sạch hơn tôi tưởng nhiều.
- **Reduced-motion**: `base.css:332` có kill-switch toàn cục đúng chuẩn, kể cả
  `animation-iteration-count: 1 !important` để chặn vòng lặp vô hạn.

#### 21.4 Hai lần tôi suýt báo động giả — ghi lại để lần sau đo đúng

- **"Stagger vượt trần 40ms"**: tôi thấy các giá trị 80/120/160/200/240ms và định
  kết luận vi phạm. Đọc mã (`tuyen-duong.vue:328-332`) thì đó là độ trễ **cộng dồn**
  theo `nth-child`, bước nhảy đúng **40ms/item**, lại còn **chặn trần 240ms** từ item
  thứ 6 — kỷ luật tốt. Bài học: đo BƯỚC NHẢY, không đo độ trễ tuyệt đối.
- **"90 animation infinite là vi phạm"**: tách ra thì 24 cái là skeleton shimmer
  (dừng khi tải xong), 14 cái là spinner, chỉ còn ambient thật — và ambient thật lại
  nằm trong mã chết. Bài học: đếm `infinite` mà không phân loại thì vô nghĩa.

#### 21.5 Còn nợ: 3 mã màu lạc chuẩn mà spec §4.3 nêu ĐÍCH DANH

Spec ghi rõ *"Không hex off-brand hardcode (`#c0392b`, `#dc2626`, `#f5f5f5` → resolve
về token)"*. Cả ba **vẫn còn**:

| hex | chỗ | ghi chú |
|---|---|---|
| `#c0392b` | `components/admin/KindCompleteness.vue` ×3 | admin |
| `#dc2626` | `assets/css/variables.css` (`--save-red`) | đã gặp ở §18.3 |
| `#f5f5f5` | `layouts/admin.vue` (`--surface-alt`) | đã gặp ở §17.4 |

Hai trong ba cái này tôi đã bắt gặp độc lập qua kiểm toán token (§17.4, §18.3) trước
khi đọc spec. Hai phương pháp khác nhau chỉ về cùng một chỗ — tín hiệu đáng tin.


### 22. Cấu trúc mục: đối chiếu 3 site (2026-08-24)

§20 đo *lượng* (màn hình, ảnh, mật độ). Mục này đo *cấu trúc* — mỗi site chia trang
chủ thành những mục gì, theo thứ tự nào, mỗi mục bảo người dùng làm gì.

Lấy bằng `WebFetch` chứ KHÔNG bằng ô trình duyệt: các lần Claude Code Desktop chết
đều gắn với việc tải site ngoài trong ô đó (§20.3). WebFetch tải phía máy chủ nên
không dựng trang trong ứng dụng. Đổi lại mất số đo DOM — nên mục này chỉ nói về
cấu trúc, không nói về kích thước.

| | vinhlong360 | Emilia Romagna | Visit Jeju |
|---|---|---|---|
| mở đầu bằng | ô tìm kiếm + hồ sơ CHỮ | 5 lối vào chuyên đề | **carousel ảnh** |
| tín hiệu "bây giờ" | Tín hiệu địa phương ✓ | News có ngày ✓ | Lễ hội đang diễn ra ✓ |
| lối vào danh mục | Khám phá theo nhu cầu ✓ | 5 mục chuyên đề ✓ | Themed Travel ✓ |
| **giúp khách LẦN ĐẦU** | **không có** | không có | **"First Time To Jeju?"** ✓ |
| cho người quay lại | Giữ mạch khám phá — **hiện cho TẤT CẢ** | không có | Bucket List |
| cộng đồng / xã hội | Từ cộng đồng ✓ | "Humans of" Instagram ✓ | 4 nguồn video ✓ |
| khối biên tập + ảnh giữa trang | **không có** | ✓ "Discover the Region" | carousel |
| đặc sản địa phương | **mục con** trong "Tín hiệu" | ✓ Food Valley, nêu **44 sản phẩm PDO/PGI** | trong nav |

#### 22.1 Phát hiện 1: có mục cho người QUAY LẠI, không có mục cho người LẦN ĐẦU

Jeju làm **ngược lại**: `"First Time To Jeju?"` là một mục riêng với 4 liên kết —
bản đồ, thứ cần biết, thời tiết, gợi ý.

Trang chủ vinhlong360 có `"Giữ mạch khám phá khi bạn ĐÃ CÓ một điểm bắt đầu"` —
tiêu đề nhắm thẳng vào người quay lại — nhưng **hiện cho mọi khách**, và với khách
lần đầu thì nó chứa đúng 2 liên kết mà cả hai đều đã xuất hiện phía trên (§19.4).

Tức trang đang dành 181px cho nhóm người dùng CHƯA tồn tại, và 0px cho nhóm đang
đứng trước mặt.

#### 22.2 Phát hiện 2: đặc sản bị HẠ CẤP, không phải vắng mặt

Tôi từng định kết luận "OCOP không có mục nào trên trang chủ". **Sai.**
`index.vue:122` có `<ul class="home-season-ledger" aria-label="Đặc sản theo mùa">` —
nhưng nó **lồng bên trong** mục "Tín hiệu địa phương" (`index.vue:74`), không phải
một lối vào riêng. Đo trước đó xác nhận: "Mật ong rừng bần Mỹ Long Nam", "Cháo Cua
Đồng" xuất hiện như mục con.

So sánh: Emilia Romagna cũng là vùng được định danh bằng đặc sản, và họ cho nó **một
trong năm lối vào cấp cao nhất**, kèm **một con số** ("44 sản phẩm PDO/PGI") — con số
vừa là bằng chứng quy mô vừa là mồi tò mò.

Trong khi tiêu đề site là **"vinhlong360 — Du lịch & Sản phẩm địa phương"**
(`nuxt.config.ts:83`). Hai vế ngang nhau trong tên, nhưng trên trang chủ vế thứ hai
nằm trong một danh sách con của mục nói về sự kiện/mùa.

#### 22.3 ĐÍNH CHÍNH §19.4 của chính tôi

Ở §19.4 tôi coi việc "Khám phá theo nhu cầu" trùng 6/7 đích với header và footer là
một khuyết điểm. Đối chiếu ra thì **cả ba site đều có khối lối-vào-danh-mục** trên
trang chủ (Emilia Romagna 5 mục, Jeju "Themed Travel"). Đây là **mẫu hình chuẩn của
ngành**, không phải lỗi. Cộng với việc ở 360px header chỉ còn 1 liên kết nhìn thấy,
kết luận đúng là: **giữ khối này**.

#### 22.4 Những gì trang chủ ĐANG làm đúng theo chuẩn ngành

- **Tín hiệu "bây giờ"**: cả ba site đều có, và vinhlong360 làm mạnh nhất — "Còn 22
  ngày", "Tháng 8 · đang vào mùa", "4.9 điểm" là câu-trả-lời-có-lý-do chứ không phải
  nhãn. Đúng luận đề §0 của `00-narrative-system.md`.
- **Cộng đồng**: cả ba đều có. Hai site kia dùng feed mạng xã hội nhúng; vinhlong360
  dùng nội dung tự có — bền hơn, không phụ thuộc bên thứ ba.

#### 22.5 Giới hạn

n=3, và WebFetch chỉ thấy nội dung tĩnh phía máy chủ — mục nào dựng bằng JS sau khi
tải có thể bị bỏ sót. Bảng trên nói về **cấu trúc biên tập**, không phải bản kiểm kê
DOM đầy đủ. Đối chiếu với §20 (số đo DOM) để có bức tranh hai chiều.


### 23. Xu hướng tương lai — lọc qua ràng buộc của dự án (2026-08-24)

Chủ dự án hỏi về xu hướng tương lai của các mô hình tương tự. Xu hướng chỉ có giá trị
nếu lọt qua ràng buộc cứng: ngân sách <1tr/tháng, solo dev, không tính năng nặng,
chỉ ảnh AI (§1.5), không booking (§1.4). Nêu xu hướng không lọc là gây nhiễu.

#### 23.1 Số liệu ngành (2026)

- **1/10 người dùng internet Mỹ nay bắt đầu hành trình tìm chuyến đi BÊN TRONG một
  công cụ AI tạo sinh** — không phải trên công cụ tìm kiếm.
- **Tìm kiếm không-nhấp tăng 22,8% → 26,7%** chỉ trong hơn một năm.
- **64% nhà tiếp thị điểm đến đã đang tạo nội dung hỏi–đáp có cấu trúc** để tăng khả
  năng được AI trích dẫn.
- Vai trò website đang được định nghĩa lại: từ *nơi để ghé* thành **kho nội dung có
  cấu trúc cấp dữ kiện cho các cỗ máy trả lời**.

Hệ quả cho vinhlong360: cạnh tranh thật trong 2–3 năm tới **không phải xếp hạng
Google, mà là ĐƯỢC TRÍCH DẪN**. Và lợi thế của một cổng cấp tỉnh không nằm ở thẩm mỹ
— nó nằm ở **dữ kiện địa phương mà không nguồn nào khác có**.

#### 23.2 Hiện trạng đo được: nền tảng TỐT hơn tôi tưởng

**30 file phát JSON-LD**, 16 loại schema:
`ListItem` 56 · `BreadcrumbList` 20 · `CollectionPage` 10 · `ItemList` 8 · `Place` 5 ·
`PostalAddress` 4 · `AdministrativeArea` 4 · `Organization` 3 · `GeoCoordinates` 3 ·
`Event` 3 · `WebSite` 2 · `SearchAction` 2 · `Offer` 2 · `WebPage` · `WebApplication` ·
`TouristTrip`.

Đây là nền AEO lành mạnh, không phải nợ. Ba khoảng trống dưới đây mới là việc.

#### 23.3 Trống 1: có nội dung hỏi–đáp nhưng KHÔNG đánh dấu schema

`pages/bai-viet/[id].vue` đã có `post_type === "question"` và `bestAnswerId` — tức
**bài hỏi có câu trả lời được chọn**. Nhưng grep toàn dự án: **0 chỗ** dùng `QAPage`,
`FAQPage`, `Question`, `acceptedAnswer`.

Đây đúng thứ §23.1 nói 64% đối thủ đang làm, và dữ liệu thì **đã có sẵn trong DB**.
Thêm schema là thay đổi nhỏ, không dịch vụ mới, không chi phí — đúng loại việc lọt
qua bộ lọc ngân sách.

#### 23.4 Trống 2: BA TỈNH NGANG HÀNG nằm trong dữ liệu MÁY ĐỌC

`pages/index.vue` JSON-LD:
```
areaServed: { '@type': 'AdministrativeArea', name: 'Vĩnh Long, Bến Tre, Trà Vinh' }
```

Và ít nhất 6 chỗ nữa trong `description`/`title` SEO: `ban-do.vue:7,228`,
`cong-dong.vue:1473`, `danh-ba.vue:280`, `dia-diem/index.vue:13,299`.

Với người đọc thì đây là lỗi văn phong vi phạm §1.6. **Với cỗ máy trả lời thì nặng
hơn: nó DẠY SAI một dữ kiện hành chính** — ba tỉnh đã sáp nhập thành một từ 7/2025 —
và mô hình có thể nhắc lại điều đó. Một cổng tỉnh dạy sai địa giới của chính tỉnh
mình là thứ phá đúng cái lợi thế "nguồn có thẩm quyền" ở §23.1.

#### 23.5 Trống 3: "Chưa rõ nguồn" ×5 trên cửa trước — đọc lại §19.5 bằng khung mới

Ở §19.5 tôi coi đây là câu hỏi về *tín nhiệm với người đọc*. Trong khung cỗ-máy-trả-lời
nó còn là câu hỏi về **khả năng được trích dẫn**: một trang tự khai "không rõ nguồn,
không rõ thời điểm cập nhật" ở 5 mục là tín hiệu thẩm quyền ÂM.

Và đây là chỗ hạ tầng `attributes.verifiedAt` — đã xây, hiện phủ ~0 entity (§1.7) —
trở thành **tài sản chiến lược** chứ không phải mục dọn dẹp. Trong thế giới mà AI trả
lời câu hỏi du lịch, thứ phân biệt là **dữ kiện kiểm chứng được mà không ai khác có**.

#### 23.6 Xu hướng KHÔNG lọt qua bộ lọc — nêu để khỏi mất công

| xu hướng | số liệu | vì sao loại |
|---|---|---|
| Video ngắn | ROI cao nhất ngành (49%) | cần năng lực sản xuất, lưu trữ, băng thông; đụng §1.5 (chỉ ảnh AI) và "không tính năng nặng" |
| Trợ lý AI hội thoại | đang phổ biến ở DMO lớn | dự án CÓ ChatWidget nhưng §2-B8 cap cứng chi phí LLM; không nới |
| WebGL / 3D nhập vai | thắng giải Awwwards | ngân sách và hiệu năng; nhóm ngang hàng của dự án không phải agency |

Awwwards ngành du lịch chủ yếu là agency thương mại chạy WebGL — **không phải nhóm
ngang hàng** của một cổng cấp tỉnh solo-dev. Đối chiếu với họ sẽ dẫn tới kết luận sai.

#### 23.7 Lưu ý điều kiện tiên quyết

Toàn bộ mục này **chưa có hiệu lực** chừng nào `NUXT_PUBLIC_SITE_NOINDEX` còn bật
(§1.7). Nhưng ba khoảng trống trên nên vá TRƯỚC khi mở index — mở ra rồi mới sửa thì
dữ kiện sai đã kịp vào chỉ mục và vào mô hình.


### 24. Giác quan: hệ đã xây gần xong — trang chủ là nơi duy nhất không dùng (2026-08-24)

Chủ dự án hỏi sâu về giác quan, thành phần nào được hiển thị và vì sao. Đối chiếu
`00-narrative-system.md` §4.2 (danh sách motif giác quan) với mã nguồn.

#### 24.1 Hệ giác quan KHÔNG phải nợ — 12/14 motif đã có

| nhóm | motif | số chỗ |
|---|---|---|
| sông nước | sediment (phù sa) · wave · ripple | 178 · 21 · 3 |
| phù sa/đất | grain overlay · SVG noise thật · palette clay/leaf/river/amber · nền sand | 67 · 3 · **475** · 144 |
| mùa/thời gian | âm-lịch-first · month-strip · tín hiệu mùa | **441** · 2 · **661** |
| văn hoá cụ thể | cần xé đan · guilloché · dấu sáp · số khắc đá chùa · ghe/cầu khỉ/lá dừa/Khmer | 7 · 4 · 11 · 2 · 80 |

Thiếu đúng **2/14**: hairline "dòng chảy" dọc, và đồng hồ trong-ngày (sương sáng /
nắng đứng bóng / nắng ngả vàng / đèn ghe). Cả hai đều là motif ambient, không phải
thành phần chức năng.

Đây là một trong những phần **được thực thi tốt nhất** của dự án. Cần xé đan ở trang
sản phẩm, guilloché + dấu sáp ở OCOP, số khắc đá chùa ở lễ hội — đúng tinh thần §4.4
*"motif Delta thật, không clip-art du lịch chung"*.

#### 24.2 Nhưng trang chủ dùng gần như KHÔNG CÁI NÀO

| motif | trang chủ | các trang khác |
|---|---|---|
| **sediment / phù sa** | **0** | sản phẩm 5 · OCOP 7 · lễ hội 6 |
| sóng nước | **0** | — |
| dấu sáp / guilloché | **0** | OCOP 14 |
| cần xé đan | **0** | sản phẩm 7 |
| motif SVG nền | **0** | sản phẩm 1 · OCOP 1 |
| âm lịch | **0** | lễ hội 45 |
| grain | 2 | — |
| mùa | 29 | sản phẩm 61 · du lịch 22 |

`sediment` **bằng 0 trên trang chủ** — trong khi phù sa là **ẩn dụ nền tảng**, một
trong ba hệ quả bắt buộc của luận đề trung tâm (§0 narrative-system). Trang lẽ ra
phải THIẾT LẬP ẩn dụ lại là trang duy nhất không nói nó.

#### 24.3 Bằng chứng sắc nhất: chép hình dạng, vứt ý nghĩa

Hai quy tắc giống hệt nhau từng chữ, **trừ dòng cuối**:

`assets/css/components.css:813` — lớp dùng chung, chú thích ghi
*"Shared phù-sa section head (Wave 1 foundation; pages opt in with .sediment-head)"*:
```css
width: 4px; height: 1.05em; border-radius: var(--radius-full);
background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
```

`pages/index.vue` — bản của trang chủ:
```css
width: 4px; height: 1.05em; border-radius: var(--radius-full);
background: var(--color-brand);
```

Cùng hình học, cùng vị trí, cùng kích thước. Bản dùng chung là **dải phù sa ba màu**
river→amber→clay; bản trang chủ là **một màu phẳng**. Trang chủ đã chép lại hình dạng
của sediment-tick rồi bỏ đi ý nghĩa.

**Sửa = đổi MỘT dòng.** Và vì `f55aeede` đã gộp cả 6 tiêu đề mục của trang chủ về
dùng chung thanh này, nên một dòng đó nâng cấp **cả sáu cùng lúc**. Không rủi ro bố
cục (hình học không đổi), không rủi ro tương phản (thanh trang trí 4px, không phải chữ).

#### 24.4 Vì sao lại thành ra thế — và điều này KHÔNG phải lỗi của ai

Ghép với §21: trang chủ được dựng lại theo hướng `nocturne` (§19.1), và đợt dựng lại
đó **không mang theo ngôn ngữ giác quan** của phần còn lại. `background-image: none`
ở `index.vue:728` và thanh một-màu ở đây là hai mặt của cùng một chuyện: một lớp
thiết kế mới đè lên, giữ bố cục nhưng đánh rơi ẩn dụ.

Đây là cái giá quen thuộc của việc redesign từng trang trên một hệ đã có bản sắc —
không phải ai làm ẩu.

#### 24.5 Đính chính §23.4 của chính tôi

Tôi viết "ba tỉnh ngang hàng nằm trong dữ liệu máy đọc → site dạy sai dữ kiện".
Nói vậy là **quá tay**. `utils/adminUnit.ts` có khối chú thích rất chỉn chu: dẫn đúng
§1.6, ghi đúng mốc 1/7/2025, đúng 124 xã/phường (35 phường + 89 xã), nói rõ `area`
là **vùng cũ chỉ để tra cứu** và **không được đứng trong breadcrumb như một cấp hành
chính**, kèm đối chiếu dữ liệu 125/125.

Sự thật chính xác hơn: **hai tầng lệch nhau** — tầng breadcrumb/structured-data của
entity thì nghiêm ngặt, còn tầng SEO/JSON-LD trang chủ chưa theo kịp. Bản vá vì thế
cũng nhẹ hơn: đưa 7 chỗ kia về đúng chuẩn mà `adminUnit.ts` đã đặt sẵn.


### 25. Học từ bảo tàng/lưu trữ — nhóm ngang hàng đúng cho bài toán "ít ảnh" (2026-08-24)

Chủ dự án muốn học bố cục/màu/thị giác từ mô hình nổi bật thế giới. Tôi KHÔNG lấy
site du lịch làm chuẩn nữa, vì ràng buộc của dự án rất đặc thù: **nền tối mặc định,
gần như không ảnh (§1.5 chỉ ảnh AI), nhưng có hệ motif vật liệu rất giàu**.

Nhóm ngang hàng đúng cho bài toán đó là **bảo tàng và lưu trữ**: họ cũng thiếu ảnh
(vướng bản quyền) và phải truyền đạt văn hoá vật chất bằng chữ, màu, hoa văn.

#### 25.1 Bốn nguyên tắc rút ra, và đối chiếu ngay

| nguyên tắc bảo tàng | vinhlong360 |
|---|---|
| Thang chữ trải từ **nhãn nhỏ → chữ tường cỡ lớn** | thang dựng TỐT (10 bậc, 11→64px, fluid) nhưng **thực dùng ~3 bậc** — xem 25.2 |
| **Ngôn ngữ hoa văn lấy từ kiến trúc**, thay bố cục chung chung | ĐÃ CÓ và làm tốt (§24.1, 12/14 motif) — nhưng trang chủ không dùng (§24.2) |
| Nền **hai tông**: than chì đậm + giấy kem | đã có: `--color-canvas` tối + `--bg-warm` sand |
| **Lưới mô-đun nghiêm ngặt** | đã thống nhất ở `f55aeede` (một công thức khung, một nhịp 80px) |

#### 25.2 Đo: 78% lượt dùng nằm ở ba bậc NHỎ NHẤT

```
--text-2xs   11       91   ████████
--text-xs    12→13   262   ███████████████████████
--text-sm    14→16   391   ██████████████████████████████████  ← đỉnh
--text-base  16→18    76   ███████
--text-lg    18→22    62   █████
--text-xl    22→28    34   ███
--text-2xl   28→36    18   ██
--text-3xl   36→48     8   █
--text-4xl   44→56     4
--text-5xl   52→64     3
```

**744/949 lượt (78%) ở ba bậc nhỏ nhất. Hai bậc "chữ tường" chỉ 7 lượt = 0,7%.**
`--text-4xl` xuất hiện ở 4 file, `--text-5xl` ở 3 file — cả site.

Bảo tàng trải thang *từ nhãn tới chữ tường*. Site này gần như **toàn nhãn**: thang có
10 bậc, thực dùng khoảng 3. Nhịp biên tập sinh ra từ **tương phản giữa hai đầu**, mà
hai đầu thì đã dựng sẵn nhưng không ai ghé.

Điều này giải thích thêm con số mật độ ở §20 (75px mỗi đơn vị so với 133–140 của
peers): chữ nhỏ thì nhồi được nhiều đơn vị hơn trên mỗi màn hình.

#### 25.3 ĐÍNH CHÍNH điều tôi suýt kết luận sai

Thấy `--text-sm` (391) gấp 5 lần `--text-base` (76), tôi định kết luận "thân bài chỉ
14px, dưới ngưỡng đọc 16px". **Sai.** Không có `body { font-size }` nào cả — thân bài
**kế thừa mặc định trình duyệt 16px**, và đo trên trang chủ xác nhận: `16px ×280`,
áp đảo mọi cỡ khác.

`--text-sm` nhiều là vì nó dùng cho **nhãn và giao diện**, không phải văn bản. Nên
đây KHÔNG phải vấn đề đọc được hay không — mà là vấn đề **hiếm khi đi lên đầu trên**
của thang. Hai chuyện khác hẳn nhau, và tôi suýt báo nhầm chuyện thứ nhất.

#### 25.4 Hệ quả thực tế

Hướng đi KHÔNG phải "phóng to mọi thứ" — mà là **dùng hết dải đã có**. Cụ thể, ba chỗ
trang chủ đáng được đưa lên đầu thang mà hiện không:
- tiêu đề mục hiện `--text-2xl` (28→36); bậc `--text-3xl` (36→48) đang gần như trống
- con số quy mô (kiểu "44 sản phẩm PDO/PGI" của Emilia Romagna, §22.2) — dự án có
  1746 entity và trang địa điểm đã nêu "1.532 điểm đến", nhưng trang chủ không nêu số nào
- một câu dẫn cỡ lớn ở khối tầng A (§21) nếu khối đó được thêm

Ba thứ này cộng lại chính là thứ tạo "nhịp biên tập" mà spec `01-home.md` §3 đòi —
và không cần thêm một tấm ảnh nào.


### 26. Atlas Obscura — đối chiếu sát nhất về TƯ TƯỞNG (2026-08-24)

Chủ dự án yêu cầu dùng trình duyệt nghiên cứu nền tảng nổi tiếng. Tôi chọn Atlas
Obscura vì nó là đối chiếu sát nhất **về tư tưởng**, không phải về quy mô: toàn bộ
nền tảng đó dựng trên **mồi tò mò** — đúng luận đề trung tâm của dự án,
*"không có listing, chỉ có story-hook"* (§0 narrative-system).

#### 26.1 Số đo — và con số này mạnh nhất trong cả bảy đợt nghiên cứu

| | vinhlong360 | Atlas Obscura | Emilia Romagna | Visit Jeju |
|---|---|---|---|---|
| màn hình | 4,9 | 7,0 | 8,0 | 7,0 |
| đơn vị bấm được | **52** | **41** | 48 | 40 |
| **px mỗi đơn vị** | **75** | **323** | 133 | 140 |
| ảnh/màn hình | 0,2 | 1,9 | 1,3 | 2,7 |
| họ màu có sắc | 3 | **2** | 4 | — |

**Atlas Obscura cho mỗi mục gấp 4,3 lần không gian, với ÍT mục hơn.**

Đây là xác nhận thứ tư và mạnh nhất cho kết luận §20: **"cắt bớt" không phải hướng
đi**. Nền tảng nổi tiếng nhất thế giới về nội dung gây tò mò không nhồi nhiều thứ —
nó cho mỗi thứ nhiều chỗ hơn hẳn.

Và **Atlas Obscura chỉ dùng 2 họ màu có sắc** — ÍT hơn vinhlong360 (3). Lần thứ ba
số đo nói cùng một điều: màu không phải vấn đề của trang chủ.

#### 26.2 Chữ: một phông, phân cấp bằng cỡ và độ đậm

60 tiêu đề, 29 cái là `h2`, **tất cả cùng một phông** ("Platform Web"), phân cấp bằng
**bốn cỡ h2** (36 / 24 / 20 / 16) và độ đậm (400–600).

Đối chiếu: vinhlong360 dùng **hai phông** — Fraunces (biên tập) cho tiêu đề mục,
Be Vietnam Pro cho tiêu đề thẻ/bảng phụ. Đây KHÔNG phải khuyết điểm: đó là cặp
serif/sans mà spec §4 chốt có chủ đích, và `f55aeede` đã thống nhất tiêu đề mục về
một giọng. Ghi lại để thấy có hơn một cách đúng.

Điểm đáng học: cỡ h2 lớn nhất của họ là **36px** — **bằng đúng** cỡ tiêu đề mục của
vinhlong360. Nên khoảng cách giữa hai site KHÔNG nằm ở cỡ chữ tiêu đề, mà ở **khoảng
trống quanh nó** (§26.1).

#### 26.3 Lỗi trong máy đo của tôi — ghi lại vì dễ tái phạm

Lần chạy đầu trả về `soTieuDe: 0`, tưởng trang không có h1/h2. Nguyên nhân: bộ lọc
"phần tử nhìn thấy được" của tôi đặt ngưỡng `height > 60`, mà **tiêu đề thường thấp
hơn 60px**. Hạ xuống `height > 8` thì ra 60 tiêu đề.

Cùng lớp lỗi với bẫy carousel ở §20.2: **ngưỡng lọc đặt cho loại phần tử này thì phá
phép đo trên loại phần tử khác.** Bộ lọc dùng cho khối lớn không dùng lại được cho
chữ.

#### 26.4 An toàn khi đo site ngoài

Trước khi mở đã chạy `claude-cuu-ho.ps1 luu` (log ra Desktop), và **đóng tab ngay sau
khi đo xong** để không lặp lại vòng "khôi phục tab rồi chết" đã ghi ở §22. Ứng dụng
sống sót cả phiên đo.


### 27. GỐC RỄ: trang chủ không dùng EntityCard (2026-08-24)

Đợt nghiên cứu thứ tám, dùng trình duyệt đo **giải phẫu bên trong một đơn vị** của
Atlas Obscura — thứ §26 chưa trả lời được: *cái gì lấp đầy 323px đó?*

#### 27.1 Câu trả lời: ẢNH lấp đầy

Giải phẫu thẻ Atlas Obscura (đo ở khung 581px):

| lớp thẻ | cao TB | ảnh | % chiều cao thẻ | chữ |
|---|---|---|---|---|
| `basis-1/3` | 504px | 541×433 | **83%** | tiêu đề 20/600 |
| `col-span-6` | 445px | 120×120 | 26% | 20/600 + meta 11/500 |
| `flex` | 226px | 96×96 | 40% | 20/700 + mô tả 18/400 |

**Không phải đệm rỗng lấp chỗ — ảnh lấp chỗ.** Thẻ chính của họ có 83% chiều cao là ảnh.

Mobile (375px): **15,2 màn hình, vẫn 300px mỗi đơn vị** (desktop 323). Họ **không nén
lại trên mobile** — họ để trang dài ra. Đây là điểm §20.3 ghi là giới hạn, nay đã đo.

#### 27.2 GỐC RỄ — một dữ kiện giải thích cả bảy đợt trước

```
EntityCard được dùng ở 12 trang:
  da-luu · danh-ba · dia-diem · du-lich · kham-pha · khu-vuc
  lich-trinh · luu-tru · nguoi-dung · ocop · san-pham …

Trang chủ dùng: 0 lần.
```

Và `EntityCard` chính là nơi chứa **lời giải cho bài toán "không có ảnh"**:
- `.cover.cover-img` + lớp `cover-generated` khi entity không có ảnh
- `placeholderBg` — gradient **gieo theo `entity.id`** (một entity luôn một look)
- `.cover-grain` — lớp grain chống "flat gradient = rẻ"
- `.cover-svg-icon` với `placeholderSvg` — glyph danh mục lệch tâm
- `.cover-dateline` — dateline eyebrow

Đúng giải phẫu "Story Card" ở §2 narrative-system — thứ spec gọi là **"thay đổi đòn
bẩy cao nhất toàn site"**. Đã xây xong, đã đạt 4/4 khi kiểm (§21.3), đang chạy trên
12 trang.

Trang chủ thay vào đó dùng bộ thẻ **tự chế, không ảnh bìa**: `cm-card`, `fy-chip`
(ảnh 60×60), `event-mini`, `dish-item`, `journey-action`.

#### 27.3 Một dữ kiện, giải thích tất cả

| phát hiện trước đó | giải thích |
|---|---|
| §19.3 toàn trang chủ có 1 ảnh | thẻ tự chế không có ô ảnh bìa |
| §20 chỉ 0,2 ảnh/màn so với 1,3–2,7 của peers | như trên |
| §26 75px mỗi đơn vị so với 323 của Atlas Obscura | thẻ không ảnh thì thấp |
| §24.2 `sediment` = 0 trên trang chủ | ẩn dụ phù sa sống trong `placeholderBg` của EntityCard |
| §25.2 hai bậc chữ lớn nhất gần như không dùng | thẻ nhỏ thì không cần chữ lớn |

Tức **không phải năm vấn đề — là MỘT vấn đề nhìn từ năm phía**: trang chủ được dựng
bằng **từ vựng thẻ riêng** thay vì từ vựng của site.

#### 27.4 Hệ quả cho việc sửa

Điều này **đổi thứ tự ưu tiên** tôi đề xuất ở các đợt trước. Hai bản vá một-dòng
(motif hero, thanh phù sa) vẫn đúng và vẫn rẻ, nhưng chúng là **triệu chứng**. Gốc là
từ vựng thẻ.

Nhưng gốc KHÔNG có nghĩa là phải làm trước: thay `cm-card`/`fy-chip` bằng `EntityCard`
là thay đổi lớn, đụng dữ liệu (EntityCard cần một `entity` đầy đủ, còn thẻ cộng đồng
nhận `post`), và cần nhìn bằng mắt để duyệt. **Cần chủ dự án quyết**, không tự làm.

Đề xuất thứ tự: hai bản vá một-dòng trước (rẻ, đã kiểm trước, thấy được ngay), rồi
bàn riêng về việc đưa `EntityCard` lên trang chủ.

#### 27.5 An toàn

Chạy `claude-cuu-ho.ps1 luu` trước khi mở, đóng tab ngay sau khi đo. Ứng dụng sống
sót cả hai phiên đo site ngoài (§26 và §27).


### 28. Quét 12 site cùng mô hình — bốn mục, ai có ai không (2026-08-25)

Chủ dự án yêu cầu nghiên cứu 10+ site bằng trình duyệt. **Đo bằng trình duyệt thất bại**
(xem 28.4); chuyển sang `WebFetch` — an toàn, đã dùng ở §22, không sập lần nào. Đổi lại
mất số đo DOM, được **cấu trúc mục**.

Hỏi mọi site cùng bốn câu, để so được.

#### 28.1 Bảng đối chiếu

| site | khách lần đầu | đặc sản/ẩm thực | tín hiệu "bây giờ" | cộng đồng |
|---|---|---|---|---|
| Emilia Romagna (Ý) | – | ✓ Food Valley | ✓ News có ngày | ✓ Instagram |
| Visit Jeju (Hàn) | ✓ "First Time To Jeju?" | – | ✓ Lễ hội đang diễn ra | ~ |
| Visit Wales | – | – | ✓ Nghỉ lễ tháng 8 | – |
| Slovenia | ✓ "At a Glance" | ✓ Food & Wine | ✓ Lịch sự kiện | ✓ IG + hashtag |
| Kerala (Ấn) | – | – | ✓ What's New | ✓ Connect with us |
| Visit Norway | ✓ khuyên chọn 1–2 vùng | ✓ "Norway for foodies" | ✓ Thu / Đông | – |
| vietnam.travel | – | ✓ ẩm thực + làng nghề | ✓ Lễ hội sắp tới | – |
| Visit Finland | ✓ quiz + "Plan your trip" | ✓ chuỗi bài ẩm thực | ✓ Thu, thời tiết từng tháng | – |
| Ireland | ✓ "need to know" | ✓ hero là ẩm thực | ✓ "What's on" | ✓ **diễn đàn riêng** |
| Visit Portugal | ✓ "Portugal Identity Card" | ✓ gốm, thêu, rượu | ✓ sự kiện + **widget thời tiết** | ✓ "Travel Diaries" |
| **vinhlong360** | **KHÔNG** (có mục ngược lại) | **mục con** | ✓ **mạnh nhất** | ✓ nội dung tự có |

**Đếm trên 10 site có dữ liệu cấu trúc:**
- tín hiệu "bây giờ": **10/10** — phổ quát, không site nào thiếu
- đặc sản/ẩm thực có mục riêng: **7/10**
- mục cho khách lần đầu: **6/10**
- cộng đồng: **6/10**

#### 28.2 vinhlong360 đứng ở đâu

**Làm tốt hơn chuẩn ngành ở đúng chỗ phổ quát.** Tín hiệu "bây giờ" là thứ 10/10 site
đều có, và vinhlong360 làm **mạnh nhất**: "Còn 22 ngày", "Tháng 8 · đang vào mùa",
"4.9 điểm" là **câu trả lời có lý do**, không phải nhãn phân loại. Các site kia phần lớn
chỉ liệt kê sự kiện theo ngày.

**Cộng đồng cũng đúng chuẩn**, và bền hơn 4/6 site kia: họ nhúng feed Instagram/TikTok
(phụ thuộc bên thứ ba, mất là mất), vinhlong360 dùng **nội dung tự có**. Chỉ Ireland có
diễn đàn riêng như vậy.

**Hai chỗ lệch chuẩn:**
- **Không có mục cho khách lần đầu** trong khi **6/10** site có. Và tệ hơn: vinhlong360
  có mục NGƯỢC LẠI — "Giữ mạch khám phá khi bạn ĐÃ CÓ một điểm bắt đầu" hiện cho MỌI
  khách (§22.1). Đây là bằng chứng thứ hai cho T3.
- **Đặc sản là mục con** trong khi **7/10** site cho nó mục riêng — kể cả những site mà
  đặc sản KHÔNG nằm trong tên (Ireland đặt ẩm thực làm **hero**; tên site vinhlong360 thì
  ghi thẳng "Du lịch & Sản phẩm địa phương").

#### 28.3 Ba thứ đáng học, cả ba dự án ĐÃ CÓ hạ tầng

- **Visit Portugal có widget thời tiết** ngay đầu trang — một dạng tín hiệu "bây giờ".
  vinhlong360 **đã có API thời tiết** (`/weather?area=…`, thấy trong `utils/apiFetch.ts:22`)
  nhưng không hiện trên trang chủ.
- **Visit Finland có khối FAQ gập** ("A few common questions") — đúng định dạng hỏi–đáp
  có cấu trúc mà §23.3 nói 64% đối thủ đang làm để được cỗ máy trả lời trích. vinhlong360
  **đã có dữ liệu hỏi–đáp** (`post_type="question"` + `bestAnswerId`) nhưng chưa đánh dấu
  schema và chưa đưa lên trang chủ.
- **Visit Finland có quiz "pick your preferences"** dẫn khách lần đầu tới vùng phù hợp.
  vinhlong360 **đã có** `HomeDecisionLedger` làm đúng việc đó — nhưng nhắm vào "hôm nay
  bạn muốn bắt đầu thế nào", không nhắm vào "lần đầu tới Vĩnh Long".

#### 28.4 Vì sao dừng đo bằng trình duyệt

Quét bằng ô trình duyệt **sập ở site thứ hai** (`visitwales.com`, 03:03:06) — lần thứ TƯ
gắn với site ngoài (20:49 sau visitjeju · 22:34 mở trình duyệt · 22:38 khôi phục tab ·
03:03 visitwales). Lặp lại cách làm đang hỏng là vô trách nhiệm.

**Kỷ luật ghi-sau-từng-site đã cứu dữ liệu:** kết quả VisitScotland ghi ra file trước khi
sập nên còn nguyên. Bài học đi kèm bài học §20.3.

Số đo DOM dừng ở **5 site**, và đủ để kết luận:

| site | px mỗi đơn vị | ảnh/màn hình |
|---|---|---|
| **vinhlong360** | **75** | 0,2 |
| Emilia Romagna | 133 | 1,3 |
| Visit Jeju | 140 | 2,7 |
| VisitScotland | **308** | **0,4** |
| Atlas Obscura | **323** | 1,9 |

**VisitScotland là điểm dữ liệu quan trọng nhất và suýt không có.** Nó cũng gần như toàn
chữ — **0,4 ảnh/màn hình, còn ít hơn Emilia Romagna** — nhưng cho mỗi mục **308px**, gấp
4 lần vinhlong360.

**Kết luận đổi hướng ưu tiên: "toàn chữ" không phải vấn đề. "Toàn chữ mà chật" mới là.**
Một cổng du lịch quốc gia cũng ít hình như vinhlong360 mà không ai thấy bí bách, vì nó
cho mỗi thứ chỗ thở. Nên **T4 (nới 75px → 130px) đáng làm TRƯỚC** việc thêm bìa ảnh.


### 29. ĐÍNH CHÍNH NẶNG: chỉ số "px mỗi đơn vị" ở §20/§26/§28 KHÔNG dùng được (2026-08-25)

Chủ dự án bảo làm T4 (nới 75px → 130px). Trước khi sửa tôi đo lại để biết mật độ nằm ở
mục nào — và phép đo mới **mâu thuẫn** với §20. Truy ra thì lỗi ở **phép đo cũ của tôi**,
không phải ở trang.

#### 29.1 Hai lỗi trong chỉ số

**Lỗi 1 — đếm cả chrome.** Script §20 quét `document.querySelectorAll(...)` trên TOÀN
tài liệu, nên gom cả liên kết header/footer vào "đơn vị nội dung". Đo lại ở 1280px:

```
quét toàn trang : 52 đơn vị → 73px mỗi đơn vị
chỉ trong .home : 31 đơn vị → 123px mỗi đơn vị
chênh 21 = 17 liên kết trong <nav> + skip-link + 2 router-link + 1 nút
```

**Lỗi 2 — chia cho số thẻ bất kể bố cục cột.** Mục "Từ cộng đồng" dùng `scroll-row`,
mục "Hôm nay bạn muốn…" dùng lưới 2–4 cột. Thẻ **nằm cạnh nhau**, nên chia chiều cao
mục cho số thẻ là hiểu sai — mỗi thẻ thực ra nhận cả chiều cao hàng.

Đo lại theo HÀNG (gom các đơn vị cùng `top` ±12px):

| mục | cao | đơn vị | hàng | cột TB | **px/hàng** | px/đơn vị (sai) |
|---|---|---|---|---|---|---|
| hero | 895 | 3 | 3 | 1 | 298 | 298 |
| "Hôm nay bạn muốn…" | 797 | 11 | 6 | 1,8 | **133** | 72 |
| Tín hiệu địa phương | 561 | 5 | 5 | 1 | **112** | 112 |
| Từ cộng đồng | 560 | 9 | 5 | 1,8 | **112** | 62 |
| Giữ mạch khám phá | 181 | 2 | 2 | 1 | 91 | 91 |

**Trang chủ KHÔNG chật.** Mỗi hàng nhận 91–133px, hero 298px — nhịp bình thường.

#### 29.2 Cái gì đổ theo, cái gì vẫn đứng

**KHÔNG dùng được nữa** (cả hai lỗi trên áp lên mọi site vì dùng chung script):
- mọi con số "px mỗi đơn vị" ở §20, §26, §28 — kể cả "vinhlong360 chật gấp 4 lần
  Atlas Obscura" và "VisitScotland 308px". Số của peers cũng nhiễm cùng hai lỗi, và
  **không đo lại được** vì quét site ngoài bằng trình duyệt đã sập 4 lần (§28.4).
- **T4 trong kế hoạch — tiền đề chết, KHÔNG thực hiện.**

**Vẫn đứng vững** (đo bằng cách khác, không dính hai lỗi):
- **Đếm ảnh** — lọc theo `<img>`/background + giao khung nhìn, không chia cho gì cả.
  vinhlong360 **1 ảnh**; peers 4–19. Đây mới là bằng chứng cho "giao diện chỉ toàn chữ",
  và nó khớp với điều chủ dự án nhìn thấy.
- **Số màn hình cuộn** — `scrollHeight / innerHeight`, không dính lỗi nào.
- **Số họ màu có sắc** — đếm màu duy nhất, không dính lỗi nào.
- **Toàn bộ so sánh CẤU TRÚC ở §22 và §28** — lấy bằng `WebFetch`, không dùng script này.
  Bao gồm: tín hiệu "bây giờ" 10/10, đặc sản 7/10, khách lần đầu 6/10, cộng đồng 6/10.

#### 29.3 Bài học

Ba lần trong phiên này máy đo của tôi cho số sai và tôi bắt được: carousel ở §20.2
(sai gấp 13 lần), ngưỡng `height > 60` ở §26.3 (ra 0 tiêu đề), và lần này. **Cả ba đều
cùng một dạng: bộ lọc/mẫu số đặt cho tình huống này thì phá phép đo ở tình huống khác.**

Lần này khác hai lần trước ở chỗ **tôi đã công bố con số sai và xây kết luận lên nó**,
qua ba mục ROADMAP, và suýt sửa mã theo nó. Cách duy nhất bắt được là **đo lại bằng một
đường khác trước khi hành động** — không phải đọc lại script cũ.

Quy tắc rút ra: **chỉ số nào có mẫu số thì phải hỏi "mẫu số này đếm đúng thứ mình nghĩ
không"** trước khi so sánh giữa các site.

---

### 30. Nghiên cứu bố cục: vì sao trang chủ "rối" dù số đo nói không chật (2026-08-25)

**Nguồn việc:** chủ dự án — *"nghiên cứu việc sắp đặt bố cục trang của những trang phổ
biến trên thế giới và xu hướng, tôi muốn phá vỡ giao diện trang chủ chỉ toàn chữ và quá
rối như hiện tại."*

#### 30.1 Nghịch lý phải giải: "rối" nhưng không chật

§29 đã đo lại: 91–133px mỗi HÀNG, hero 298px — **không chật**. Nhưng chủ dự án nhìn
thấy "quá rối". Hai điều này không mâu thuẫn, vì **"rối" không phải là chật**.

Số đo ở §21 nói ra nguyên nhân: **4 mục liên tiếp cùng một tầng nhịp**, cùng bề rộng
khung, cùng nền, cùng hình dạng thẻ. Cộng lại: **18 đơn vị gần giống hệt nhau nối tiếp
nhau.** Mắt không có chỗ bám, cũng không có chỗ nghỉ. Đó là **thiếu nhịp**, không phải
thiếu khoảng trắng — và nới khoảng trắng sẽ **không** chữa được (thêm một lý do T4 sai).

#### 30.2 Ba nguyên lý thu được từ nghiên cứu

**(a) Bento grid — ô không đều trên cùng một lưới.** *(Số 67% dưới đây ĐÃ BỊ RÚT LẠI — xem §31.2.)* Xu hướng chủ đạo 2026; **67% top
100 site SaaS** đã dùng ở trang chủ hoặc trang tính năng. Khác lưới CSS thường ở chỗ nó
**cố ý bất đối xứng**: nội dung quan trọng được ô lớn, phần còn lại lấp quanh. Nguyên lý
cốt lõi, và đây là phần trả lời thẳng câu hỏi của chủ dự án:

> *Khi mọi phần tử theo cùng một nhịp, một phần tử lệch nhịp lập tức chiếm lấy sự chú ý
> — điểm nhấn sinh ra CHÍNH VÌ nhịp xung quanh đã dạy mắt kỳ vọng sự đều đặn.*

Trang chủ hiện tại có nhịp đều nhưng **không có gì lệch nhịp**, nên nhịp đều đó không
sinh ra điểm nhấn nào — chỉ sinh ra sự đơn điệu.

**(b) Xen kẽ kiểu bàn cờ (checkerboard/zigzag).** Chữ trái–hình phải, mục sau lật lại.
Đưa mắt đi **chéo** thay vì thẳng xuống, làm trang "động" hơn mà không thêm gì.

**(c) Nhịp cuộn = xen kẽ khối đặc với khối "thở".** Mục dày thông tin thì mục kế phải
nhẹ; nền các mục đổi sáng–tối để tạo **nhịp sắc độ** dọc trang.

#### 30.3 Đối chiếu với tài sản đã có (không cần ảnh, không cần dịch vụ mới)

| Nguyên lý | vinhlong360 đang có sẵn | Đang dùng? |
|---|---|---|
| Ô lớn cần cỡ chữ lớn | thang 10 bậc, `--text-3xl`/`4xl`/`5xl` | **0,7%** (§25.2) |
| Ô lớn cần bìa | `generateCategoryPlaceholder` sinh bìa từ `entity.id` | 12 trang dùng, **trang chủ 0** (§27) |
| Nhịp sắc độ | `--surface`/`--canvas`/`--raised` đủ 3 tầng, cả 2 chế độ | các mục **cùng một nền** |
| Bất đối xứng | CSS Grid, không cần thư viện | các mục **cùng một khuôn** |

**Bốn cột đều là "có sẵn nhưng không dùng"** — cùng đúng một chẩn đoán gốc ở §27.

#### 30.4 Hệ quả cho kế hoạch

- **Phương án A ở mockup (lưới 8 ô ĐỀU) là yếu** — có thêm hình nhưng vẫn lặp lại đúng
  bệnh "mọi thứ giống nhau". Giữ lại làm đối chứng, **không khuyến nghị**.
- **Thêm phương án C — bento** (1 ô lớn + 2 vừa + 4 nhỏ) vào mockup. Phá được cả hai
  triệu chứng cùng lúc: thiếu ảnh (7 bìa) **và** thiếu nhịp (3 cỡ ô), đồng thời kéo
  `--text-3xl` ra khỏi vùng chết 0,7%.
- Mockup: `scratchpad/mockup-trang-chu.html` — dữ liệu thật từ `/api/homepage`, đúng
  thuật toán băm FNV của dự án nên bìa trong mockup **trùng** bìa bản thật.
- **Chờ chủ dự án chọn** A / B / C trước khi đụng vào mã.

---

### 31. Thẩm định phương án C (bento): BỊ BÁC — giữ quyết định nội dung, đổi khuôn (2026-08-25)

**Nguồn việc:** chủ dự án — *"phân tích và đánh giá phương án C, sau đó nâng cấp và tối ưu
hơn nữa."* Cách làm: 14 agent độc lập (5 lăng kính: tích hợp mã / dữ liệu thật / hàng rào
chuẩn / tiếp cận / phản biện; 8 phiên thẩm tra đối kháng; 1 tổng hợp). Mọi con số dưới đây
đã qua thẩm tra — bên thẩm tra tự đo lại, không tin số cho sẵn.

#### 31.1 Phán quyết

**Tách hai chuyện đang bị gộp.** (1) *"Trang chủ cần mục Đặc sản riêng"* — **ĐÚNG, giữ**
(§28.1: 7/10 site điểm đến làm vậy; tên site ghi thẳng "Sản phẩm địa phương"). (2) *"Mục đó
là lưới bento 7 ô ba cỡ"* — **SAI, bỏ**. Bốn phát hiện giết nó, không cái nào bác được:

1. **Mockup bản 2 không phải bằng chứng.** Đối chiếu 8 id với DB: 7/8 tên bị rút gọn
   (29,75 → 14,1 ký tự, 2,11 lần), và mỗi ô ghép **bìa-của-A với tên-của-B** (id bản dài +
   tên bản sao ngắn) — không ô nào tồn tại như một hàng DB. Rút tên cho vừa ô chính là thao
   tác copywriting mà bento SaaS được phép làm còn dự án này thì không: **tên là dữ liệu,
   không phải chữ do ta viết.**
2. **Hình học hỏng ở tầng cấu trúc.** Đo Playwright @1280px: hàng lưới 245,81 / 226,31 /
   250px — không bằng nhau; mỗi ô vừa trống 119,56px. Đổi tỉ lệ bìa không cứu: 16:9 vẫn
   trống 102,7px, 2:1 còn 85,8px, phải xuống 5:1 mới cân. Gốc: ô lớn là thẻ dọc bìa+thân,
   ô vừa là thẻ ngang một thân chữ ngắn — cộng `grid-row: span 2`.
3. **HAI dải viewport vỡ** [320–450) và [721–874); đáy tuyệt đối vw=721 (khung chữ 173,5px
   — hẹp hơn cả 375px); iPad dọc 768px vỡ mà media query ≤720px không chạm. Gốc: bìa
   `width:132px` cố định cạnh cột co giãn.
4. **Thuật toán chọn ô mù chữ.** `_homepage_score` (agent/public_api.py:2769) không có số
   hạng nào biết độ dài tên; 11/12 tháng có ≥1 entity-tổ-chức trong top; T3/T4 ô LỚN là
   "Hợp tác xã thủy sản Thạnh Lợi – Nghêu Thạnh Hải (OCOP)" — 54 ký tự.

#### 31.2 Rút lại luận cứ "67% top-100 SaaS dùng bento" (§30.2a)

Truy nguồn: **duy nhất** landdding.com — không phương pháp, không mẫu, không danh sách;
tác giả là founder một gallery thiết kế (bên có lợi ích); "top 100 SaaS websites
ProductHunt" không tồn tại như một bảng xếp hạng; nguồn thứ hai từng viện dẫn
(syedaounraza.online) **không hề chứa con số này**. KHÔNG dùng số 67% làm luận cứ nữa.
Phần còn lại của §30.2(a) — "phần tử lệch nhịp hút mắt" — vẫn đúng nhưng là nhận định
định tính, và nó biện minh cho MỌI cách phá nhịp, không riêng bento.

Cùng loạt đính chính: chú thích "0/1817 entity kèm ảnh thật" trong mockup bản 2 SAI —
DB có 57 entity kèm images (product 19/218); và theo §1.5 đó là ảnh AI có nhãn. Số 0,7%
(§25.2) cũng phải ngừng trích: đếm lại 2026-08-25 ra 3xl=22, 4xl=12, 5xl=7 lượt — khác
số cũ, chưa phân xử được vì hai phép đếm khác phạm vi.

#### 31.3 Số đo mới (đo trực tiếp DB worktree này, 1746 entity / 218 product)

- **OCOP theo sao:** 5★ = 7 hàng → **5 món sau khử trùng lặp** (Vicosap ×2, Dừa sáp ×2);
  4★ = 44; 3★ = 41; có khoá ocop nhưng không rút được sao = 44 (khoá không đồng nhất:
  `ocop_star`/`ocop_stars`/`ocop`/`ocop_certified` — nợ chuẩn hoá dữ liệu, ghi backlog).
- **Entity-tổ-chức đội lốt product:** 8 (HTX/công ty/cửa hàng/điểm trưng bày) — danh sách
  loại trừ cho mọi mục đặc sản.
- **Ứng viên CatalogSpotlight (summary ≥80kt, dài nhất):** "Cá phi sả ớt Thạnh Phước" —
  tên 24kt, summary 362kt; pool đạt chuẩn 212/218 → khuôn F bền với dữ liệu.
- **Nhịp sắc độ (đo trang đang chạy):** 6/6 mục cùng MỘT giá trị nền (rgb 249,247,241).
  3 mục đã tràn lề sẵn (hero/quick-decisions/signals) — sơn nền là ăn, nội dung không
  xê dịch. Token dải: `--bg-alt` lệch 1,11 (sáng) / 1,27 (tối) — dùng được cả hai chế độ;
  `--color-surface` chỉ 1,04 ở chế độ sáng — KHÔNG dùng làm dải. Chữ thân bài trên mọi
  token nền ≥12:1.

#### 31.4 Phương án sống sót — chờ chủ dự án chọn

- **D — nhịp sắc độ** (điều kiện cần, làm trước): luân phiên nền đặc–thở bằng token có
  sẵn; 0 đơn vị nội dung mới; tấn công thẳng "cùng nền, cùng bề rộng" của chẩn đoán §30.1.
- **F — Đặc sản làm tin chính** (khuyến nghị): tái dùng CatalogSpotlight (đang chạy 6
  trang) — nó chọn entity theo ĐỘ GIÀU NỘI DUNG, đúng thứ `_homepage_score` thiếu. 1 bìa
  lớn + summary đầy đủ + 6 món danh sách chữ (tên 60kt không vỡ).
- **E — sổ vàng OCOP 5 sao** (thay F nếu muốn nhiều bìa): khuôn star-band của /ocop
  ("Reuses EntityCard unchanged"), kích cỡ MANG NGHĨA (đậm = sao cao). Đủ dữ liệu (5 món).
  Nhược: trùng câu chuyện với /ocop.
- **C′ — nếu vẫn muốn bento:** 8 điều kiện tối thiểu (tên thật, token, chọn-theo-nội-dung
  ô lớn ≤24kt, bỏ span hàng, bìa co giãn…) — làm đủ thì đích đến gần bằng E/F với chi phí
  cao hơn hẳn.

Mockup bản 3 (tên thật nguyên văn, C dựng lại cho thấy chỗ vỡ, F/E/D dựng cạnh nhau):
artifact `1b07f7f5`. Chi tiết đầy đủ 5 lăng kính + 8 phiên thẩm tra: file kết quả workflow
trong scratchpad phiên 2026-08-25.

#### 31.5 Backlog phát sinh (không làm trong đợt giao diện)

- Chuẩn hoá khoá sao OCOP (4 kiểu khoá → 1) + khử 2 cặp product trùng — cần backup B1.
- 42 summary product còn chữ "huyện", 72 bản gọi Bến Tre/Trà Vinh như tỉnh hiện hành —
  trái §1.6, sửa hàng loạt cần chỉ đạo + backup.
- `ORDER BY updatedAt DESC` thiếu khoá phá hoà (agent/database.py:1649) — 4 entity đồng
  điểm T1/T2/T12; và trần cứng `limit=5000` trong `_build_homepage_payload` là mìn hẹn giờ.
- Tài liệu chuẩn lệch máy: 00-INDEX.md ghi R30.2=687/R30.3=307, baseline.json là 330/200.
- Scorecard đang đỏ sẵn từ trước (backend 99→81, nợ R20.8=47) — chặn pre_merge bước 7,
  KHÔNG liên quan đợt này.

---

### 32. Tổng phổ trang chủ: «Tạp chí Phù Sa — bản hợp nhất» thắng thẩm định 14-agent (2026-08-25)

**Nguồn việc:** chủ dự án — *"nhiều vòng thiết kế chưa đáp ứng yêu cầu bố cục/màu sắc/thị
giác; nghiên cứu thật sâu, phân tích, phản biện để đưa ra phương án tối ưu nhất, dựa trên
mockup bản 3."* Cách làm: 4 lăng kính nền → 3 tổng phổ TOÀN TRANG sáng tác độc lập (Tạp chí
Phù Sa / Bảo tàng sống / Chợ nổi sắc màu) → 3 kẻ phá + 3 giám khảo chấm đúng ba trục chủ
dự án nêu → 1 tổng hợp. Hồ sơ đầy đủ: file kết quả workflow trong scratchpad phiên.

#### 32.1 Phán quyết

**Thắng: Tạp chí Phù Sa** — 24,5/30 (bố cục 8,5 · màu 8 · thị giác 8; hai bản kia cùng
21,5). Nhất ở đúng hai trục chẩn đoán gốc: bố cục (6/6 mục một nền, vùng chết 841–1609px)
và thị giác ("mở trang thấy khác ngay" — chỗ mọi vòng trước thất bại). Cả ba bản đều bị
kẻ phá bắn thủng (songSot=false cả ba) và cùng chết chung MỘT lỗ dữ liệu gốc: `products`
trong payload bị cắt limit=8 tại `agent/public_api.py:3089` — bản hợp nhất vá bằng trường
payload MỚI additive `product_lead` (server chọn trên toàn pool, shortlist chủ duyệt).

Bản hợp nhất ghép 8 mảnh từ hai bản thua (thi công 4 đợt độc lập + thang lui E-lite từ
Bảo-tàng-sống; mồi cuộn + blocklist ID + luật hue-banding + vá múi giờ SSR từ Chợ-nổi)
và vá 11 lỗ (3 CHẶN, 2 NẶNG, 3 VỪA, 3 NHẸ) — chi tiết trong file kết quả.

#### 32.2 Tổng phổ 9 mục (mockup bản 4 — artifact `1b07f7f5`)

| # | Mục | Nền | Ghi chú |
|---|---|---|---|
| 1 | Măng-sét âm–dương (nâng cấp context, GIỮ tên section) | `--bg-alt` | ngày qua Intl Asia/Ho_Chi_Minh cả server lẫn client; useLunar SẴN CÓ, chỉ formatter |
| 2 | Hero + hồ sơ ảnh | canvas | ĐIỂM DỪNG 1 — khối tối duy nhất; h1 GIỮ NGUYÊN (đã cap 64px — "nâng h1" là no-op); nén đệm dưới 40–60px làm mồi cuộn |
| 3 | Mục lục hôm nay (quick-decisions) | `--bg-alt` | nén 11→~6 nhìn thấy; DecisionLedger GIỮ DOM/class/text (test pin toEqual); CategoryIndex nén thành 1–2 hàng link |
| 4 | TIN CHÍNH ĐẶC SẢN — HomeProductLead (MỚI) | canvas | ĐIỂM DỪNG 2 — mảng màu duy nhất dưới fold; con số quy mô `--text-4xl` từ payload; lưới 2 cột CHỈ ≥900px (vá dải vỡ [768,900)); chính sách ảnh: AI thật trước, bìa sinh khi thiếu (descriptor policy + registry) |
| 5 | Tín hiệu địa phương | `--bg-alt` | tin dẫn + âm lịch DERIVE từ date_start (không đọc lunar_date, không sửa DB — né bẫy sáu-ô §5c); bìa 4:3 EntityHeroPlaceholder (0 registry) |
| 6 | Sổ vàng OCOP (MỚI, khe SSR index.vue:153–159) | canvas | ĐIỂM DỪNG 3 — kênh viền dày (2px + halo); HAI TRẠNG THÁI: E-lite mặc định (khung + định nghĩa + link /ocop), E-full CHỜ CHỦ DUYỆT |
| 7 | Từ cộng đồng | `--bg-warm`* | nén 6→3 hiển thị; *blur-test Đợt A: 1,089 sát mép — trượt thì lui về `--bg-alt` |
| 8 | Dành cho bạn | canvas | điều kiện, ngoài nhịp chính, GIỮ NGUYÊN |
| 9 | Giữ mạch khám phá | canvas, khung hẹp 45rem | cadence không phải điểm dừng; GIỮ JourneyActionRail + 2 link; colophon sediment-tick |

Ba điểm dừng = ba kênh tri giác không giẫm nhau (tối / mảng màu / viền dày). Khối hình
1→6 (sàn 5 khi E-lite). Nheo mắt phải đọc thành: dải—KHỐI TỐI—dải—KHỐI MÀU—dải—KHUNG—dải ấm—kết.

#### 32.3 Không đưa vào (bằng chứng loại)

Bento mọi biến thể (§31) · 4 cổng poster màu danh mục (2/4 cổng trùng họ cam — tự triệt
tiêu) · thumb hồng trong ledger (81 ngày/năm ≤2 event) · 20 khối hình (vượt trần trung
tính) · hạ/nâng h1 (đều no-op hoặc phản tác dụng) · dời CategoryIndex thành mục riêng ·
5 thẻ scroll-row sổ vàng (hình học 4+1 mồ côi) · nguồn `seasonal` cho Đặc sản · viết mới
thuật toán âm lịch · sợi chỉ phù sa animate (xếp sau, khác đợt) · mọi thay đổi nhãn AI /
DB hàng loạt (task riêng có backup, chờ chủ).

#### 32.4 Kế hoạch 12 bước (tóm — verify từng bước trong file kết quả)

1. Baseline: `run_hard --all` + pytest, ghim 3 số ratchet (157/330/372).
2. **A1** nhịp dải nền (CSS thuần, 3 mục đã tràn lề sẵn). 3. **A2** măng-sét âm–dương.
4. **A3** nén mục lục + mồi cuộn. 5. Nghiệm thu A: check:public-accessibility 2 chế độ + blur-test.
6. **B1** backend additive: `product_lead` + `products_total` (5 lớp lọc, shortlist chủ duyệt).
7. **B2** HomeProductLead.vue (scoped, registry ảnh cùng commit). 8. **B3** nghiệm thu tên thật 5 mốc viewport.
9. **C** tin dẫn tín hiệu + âm lịch derive. 10. **D1** E-lite + mini-row thumb (sàn ≥4 khối hình mọi kịch bản).
11. **D2** E-full — CHỈ sau khi chủ duyệt 3 ID + task nội dung xong. 12. Chốt hồ sơ KẾT QUẢ (R60.5).

#### 32.5 Chờ chủ dự án quyết (không tự làm)

- Duyệt **shortlist tin chính** (đề cử "Cá phi sả ớt Thạnh Phước") + blocklist ID tổ-chức.
- **E-lite hay E-full**; nếu full: duyệt 3 ID khác thương hiệu, xác nhận loại "Khoai lang
  sấy Bình Tân" (mới "đề xuất" 5 sao — lên sổ vàng là khai khống §1.7).
- Task nội dung DB (backup B1): 2 summary OCOP mâu thuẫn, 42 bản "huyện", 72 bản
  Bến Tre/Trà Vinh thiếu "cũ" — ID nào sạch mới đủ điều kiện vào shortlist.
- Bật hero AI full-bleed / sinh ảnh mới / sửa nhãn công bố — giữ nguyên trạng đợt này.

---

### 33. Vòng soi bản 4 → bản 4.1: 33 nâng cấp qua thẩm tra, 2 đề xuất bị bác (2026-08-25)

**Nguồn việc:** chủ dự án — *"còn có thể tối ưu và nâng cấp thêm cho bản 4 không."*
Cách làm: 5 góc soi CHƯA phủ ở các vòng trước (nocturne / mobile / vi-typography-a11y /
chuyển động / khách lần đầu) → 36 đề xuất → 2 thẩm tra viên đối kháng → 33 LÀM (đã áp
vào mockup bản 4.1, artifact `1b07f7f5`), 2 BỎ, 5 chờ chủ. Hồ sơ đầy đủ + chi tiết
33 mục: file kết quả workflow trong scratchpad phiên.

#### 33.1 Phát hiện nặng nhất: nocturne là MẶC ĐỊNH mà hệ điểm dừng vẽ trên giấy sáng

`variables.css:640` — "Default is Nocturne; Parchment is selected only by the user."
Đo WCAG trên token thật: tấm hero rgba(đen,.76) đạt 10,43:1 ở chế độ sáng nhưng chỉ
**1,05:1 ở tối** — "khối tối duy nhất" biến mất đúng chế độ đa số khách nhìn thấy.
Tái phối cho dark (không đổi bản sáng): tấm đổi chất liệu `--raised` (1,27:1 — cùng bậc
dải) + capsule/input về token; ảnh AI thật (nền sáng, 13–16,6:1 trên canvas tối = đèn
pha) ghìm `brightness(.86)` về họ ~9,5 cùng bìa sinh; thẻ trên dải KHẮC về `--canvas`
thay vì nổi (dark `--bg-alt` TRÙNG `--color-surface-raised` — variables.css:761 — thẻ
hết đường đi lên; phương án lui cộng-đồng-về-alt của §32 sẽ cho 1,00:1 ở dark nếu
không có đòn này). Bản đọc nheo-mắt nocturne riêng: ba điểm dừng dark = cụm-sáng /
khối-sáng-lớn / khung-son. Nhịp dải ở dark MẠNH HƠN sáng (1,27 vs 1,11).

#### 33.2 Các nhóm nâng cấp khác (chi tiết 33 mục trong file kết quả)

- **Mobile:** sổ vàng bỏ stack 1 cột (cao 2,2 màn @375) → scroll-row cuộn ngang <769px
  đúng đặc tả; măng-sét ngữ pháp 2 nhóm chống dấu «·» mồ côi (breakpoint 820px phủ cửa
  sổ tự phản bội 641–665px); h1 mockup về ĐÚNG clamp production `clamp(44px,7vw,64px)`
  — thẩm tra ĐẢO CHIỀU đề xuất gốc: rule pilot (home-nocturne.css:80) đè base ở mọi bề
  rộng, h1 @375 là 44px/3 dòng — sự thật phải nhìn thấy, không được mockup-làm-đẹp;
  ledger/sig-rows xếp dọc <640px.
- **Typo:** con số quy mô hạ **4xl→3xl** — h1 cap 64px là chốt, 64/56=1,14 là tranh
  giọng, 64/48=1,33 đúng bậc (KÈM amendment trong plan để người sau không tưởng code
  sai spec); 20 giọng chữ mockup quy về thang token; sàn line-height 1,3 cho display
  Fraunces gãy dòng (đo glyph thật: dấu chồng tiếng Việt cần 1,271em); summary clamp
  2–3 dòng + measure 68ch áp lên ĐÚNG phần tử mang font-size (bẫy đơn vị ch).
- **A11y:** focus-visible toàn cục (mockup có 0 rule); search min-height 44px + input
  16px chống iOS auto-zoom; dossier h3→h2 (production đã dùng h2 —
  HomeFeatureDossier.vue:42); page→main, catline→nav.
- **Khách lần đầu:** kicker "Du lịch & Đặc sản Vĩnh Long" trở lại màn 1 (câu trả lời
  "site này là gì" duy nhất — mockup bản 4 làm rơi, phải vào danh sách "Giữ 100%" của
  §32 mục 2); cờ mục đứng trước con số quy mô; thang CTA 2 bậc; lối "Lần đầu đến?"
  nhân bản lên mục 3 (đích /lich-trinh); legend hệ-hạng-nguồn ngay dưới chuỗi 3 lần
  "Chưa rõ nguồn" + hạ chrome pill tier unknown SCOPE TRANG CHỦ.
- **Chuyển động:** Sợi chỉ phù sa DỰNG THẬT trong mockup (vệt bồi 3px máng lề trái,
  clip-path 3 tầng trầm tích, `animation-timeline: view()` + fallback JS 20 dòng,
  tĩnh-ĐẦY khi reduced-motion/no-JS, ẩn <1200px); reveal Đợt A1 phải đổi chỗ: DẢI
  không được trượt, chỉ nội dung trong lòng dải trồi (chống hồi quy khi sơn nền lên
  section mang class reveal); CountUp cho products_total (quy ước nhà 10 trang);
  chấm pulse ec-today.

#### 33.3 Hai đề xuất bị BÁC bằng dữ liệu

- Con số quy mô 2 bậc 2xl/4xl — thua --text-3xl về tỉ lệ với h1 cap 64px.
- Ưu tiên entity có nguồn khi chọn hồ sơ hero — quét 1746/1746 entity:
  official/source_class/source_kind đều None, partner_verified=0 → sort không có gì
  để sort. (Kéo theo việc chờ chủ xác nhận dữ liệu prod có khác không.)

#### 33.4 Bổ sung cho kế hoạch 12 bước (§32.4) — amendment

- Bước 7 (B2): con số quy mô dùng `--text-3xl` (KHÔNG phải 4xl như §32.2 ghi);
  CountUp chỉ đếm products_total; ảnh dossier fetchpriority="high" không lazy,
  leadcover + sổ vàng lazy.
- Bước 2 (A1): kèm CSS reveal-nội-dung-trong-dải cùng commit; blur-test chụp CẢ dark;
  quy ước thẻ-trên-dải: sáng NỔI về trắng, tối KHẮC về --canvas.
- Bước 3 (A2): nhãn mùa măng-sét render có điều kiện (h1 không chứa nó); test 2 nhánh.
- Bước 10 (D1): mini-row 3 thumb không vừa 333px — cần rule mobile riêng.
- MỚI, chờ chủ: **Đợt E — SedimentThread** (component riêng + test R20.7 cùng commit,
  gate ≥1200px, reduced-motion riêng vì nuke .01ms của pilot không chặn scroll-timeline);
  **commit riêng** cho ẩn-topbar-search-khi-hero-search-trong-khung-nhìn (đụng layout
  12 trang; visibility:hidden không phải display:none — giữ chỗ chống CLS;
  IntersectionObserver không tái dùng topbarScrolled).

#### 33.5 Chờ chủ dự án quyết (cộng dồn với §32.5)

- Đợt E (Sợi chỉ phù sa vào repo) — mở rộng kế hoạch 12 bước đã duyệt.
- Hạ chrome pill "Chưa rõ nguồn" TOÀN SITE hay chỉ trang chủ (dữ liệu hiện 100% unknown
  — bản toàn site đổi trình bày trust của mọi SourceMark trên 12 trang).
- Measure summary 54ch (đúng trần 75 kt/dòng) thay token 68ch — lệch token nhà.
- H1 mobile 44px/3 dòng @375 (hiện trạng production) có quá lớn không — quyết định
  sản phẩm.
- Xác nhận dữ liệu prod có entity official/partner_verified không (local 0/1746).

---

### 34. Vòng có mắt → bản 4.2: lần đầu phê bình bằng pixel, không bằng mã (2026-08-25)

**Nguồn việc:** chủ dự án — *"tối ưu giao diện hơn, hấp dẫn hơn, thu hút hơn."* Vá lỗ
hổng phương pháp tồn tại suốt các vòng: mọi phê bình trước đều ĐỌC MÃ, chưa ai NHÌN.
Dựng công cụ mắt (playwright-core + Edge sẵn của Windows, 0 đồng, trong scratchpad),
phiên chính tự soi trước, rồi 5 lăng kính + 2 thẩm tra — **mỗi agent bắt buộc chụp ảnh
và mở ảnh nhìn trước khi kết luận; thẩm tra mở lại từng ảnh chứng minh, đề xuất không
có ảnh là hạ bậc.** 80 ảnh chứng cứ trong scratchpad phiên.

#### 34.1 Mắt bắt được thứ mã không thấy

- **Bug thật:** thuộc tính `height="…"` của `<img>` thắng `aspect-ratio` CSS (chỉ áp khi
  height auto) — thẻ Vicosap 400px cạnh bìa 229px, hàng E-full lệch răng cưa. Vá bằng
  `height:auto`. **Bài học cho production:** mọi img có width/height attr + aspect-ratio
  CSS cần height:auto tường minh.
- **Bệnh thẩm mỹ:** bìa sinh v1 ở cỡ thẻ đọc như Ô MÀU TRỐNG — hai thẻ cùng họ cam
  (product hue 30±15) gần giống hệt; bìa event = khối hồng phẳng như thiếu ảnh. Giám
  tuyển xác nhận độc lập: mắt dừng 5 chỗ chứ không phải 3 — hai điểm dừng NGOÀI thiết kế
  là cặp thẻ cam và tấm hồng, đều mang 0 thông tin.
- **Giả tượng công cụ (ghi để khỏi mất lượt):** fullPage screenshot cuộn nhanh làm ảnh
  data-URI chưa kịp composite → ô trống GIẢ trong ảnh chụp. Đo naturalWidth/complete
  trước khi tin "ảnh biến mất".

#### 34.2 Bản 4.2 — 14 mục áp (chi tiết + ảnh chứng cứ trong file kết quả workflow)

1. **Bìa sinh v2 «Tem phù sa»** thay v1 (thắng chung khảo trước «Bản khắc phù sa» của
   giám tuyển — hai ngôn ngữ cùng renderer, chọn MỘT): chân trời 2 thang sáng (hz
   140–172), đất lệch ấm −14°, motif token thật theo danh mục (sóng/đan cần xé/guilloché/
   đèn lồng treo dây), monogram chữ đầu 170px mờ .24, viền tem 2 lớp caller-side, mScale
   LIÊN TỤC 0.6–1.1 khoá de-twin cặp cùng-chữ-cái. Giữ nguyên hợp đồng v1: tất định theo
   id, hue theo category, grain caller, mọi tỉ lệ khung. ~3,3KB/bìa.
2. **Vi tương tác «bồi lắng»** (token mới `--tick-x` ngang, 2 chế độ): vệt phù sa 4px
   bồi từ trái ở chân thẻ/hàng khi hover; KHÔNG nhấc thẻ (ngược ẩn dụ — bị bác bằng ảnh);
   hàng sổ nền --shade + biên dưới thành sợi; link 2 bậc (.cta sợi tick-x chạy đè, .seeall
   underline chạy; biến thể cdai cho link dài có thể wrap); nút Tìm press lún 1px, :active
   NGOÀI (hover:hover); mọi transition ≤200ms, tắt sạch reduced-motion; production chỉ gắn
   hover cho hàng ĐÃ là link.
3. **Sổ vàng thành tờ chứng nhận:** triện son 2 vòng + vân guilloché đồng tâm + drop-cap
   — điều kiện cứng: gắn với KHỐI toàn 5 sao, danh sách đổi thì PHẢI GỠ (§1.7).
4. **Passe-partout** cho ảnh tin chính (bản sáng học bài "hộp đèn" của bản tối) — chỉ ảnh
   "đinh", không áp đại trà.
5. **Vá hộp tìm tối 1,27:1** — input sáng cố định, ngoại lệ có chủ đích ghi tại chỗ.
6. **Đồng bộ ngày theo data.json:** Thanh trà 15/09 (số "20 Th9" của mockup cũ là chép
   sai), đờn ca 20/09; âm lịch derive lại bằng oracle dự án.
7. **Slot tin dẫn nâng chính sách** "ảnh AI thật trước, bìa sinh khi thiếu" — 2/3 hàng
   mùa fallback đã có ảnh kho.
8. Số mục catalog bảo tàng (03/05/07) · Vicosap (ảnh thật) lên đầu hàng E-full · **phiếu
   hero B full-bleed** dựng CẠNH hiện trạng cho chủ THẤY rồi quyết (§1.5) — diện tích ảnh
   màn 1 16,2%→91,8%, tự sửa lỗi input tối, +190KB LCP.

**8 đề xuất bị bác bằng ảnh** (giữ làm tiền lệ): nhấc-thẻ+bóng (ngược ẩn dụ), grain trên
dải sáng (vô hình cả 2 mức opacity), trời-nhạt pastel (mất bản sắc/chói), thanh tick trái
ledger (vô hình 1x), sinh ảnh đờn-ca-vì-là-kế-tiếp (tiền đề sai theo data.json), cross-map
ảnh Sokfarm (quyết định dữ liệu của chủ), thumb ledger + ảnh mục 7-9 (trần trung tính
giữ 6 khối), color-mix 12% input (chưa có ảnh chứng minh — không ship mù).

#### 34.3 Chờ chủ dự án quyết (phiếu — cộng dồn §32.5, §33.5)

- **Phiếu ảnh AI mới** (tiền thật, trần cứng 10 call/đợt): 2 ảnh sổ vàng (mật hoa dừa,
  sầu riêng Sáu Ri — prompt đã viết theo 8 luật phong cách nhà, khoá không-nhãn-mác) +
  trọn gói sự kiện tin dẫn (5 event không ảnh từ nay tới 20/09) + 1 dự trữ sau khi chốt
  shortlist. CỔNG TRÌNH TỰ: chốt danh sách 3 ID E-full trước, rồi mới sinh ảnh.
- **Phiếu hero.webp:** chọn MỘT — A giữ nguyên / B full-bleed / C ô ảnh phải (C bắt buộc
  kèm vá input tối; cả B lẫn C cần chỗ mới cho thẻ Cua cốm).
- **Port bìa v2 vào production** (12 trang + useCategoryPlaceholder.ts): kích hoạt khi
  chủ duyệt diện mạo v2 trên mockup 4.2 — Backlog phát sinh, có mìn glyph-đôi phải né
  (hồ sơ trong kết quả workflow).

---

### 35. Kiểm kê kho ảnh + audit 16 thành phần → bản 4.3 «nhiều hình từ kho 0 đồng» (2026-08-25)

**Nguồn việc:** chủ dự án — *"muốn có nhiều hình ảnh; xem các thành phần trang chủ có
đủ, thiếu, dư thừa, không phù hợp gì không"* + tham chiếu bố cục svncoop.vn. Chỉ đạo
trực tiếp ĐÈ trần "6 khối hình" của §32/§34 (suy luận nội bộ thời chỉ-có-gradient).
Cách làm: 7 agent (3 kiểm kê / 1 phân bổ / 2 thẩm tra có mắt / 1 chốt) + phiên chính
tự phân tích svncoop.vn qua headless Edge (KHÔNG dùng pane trong app).

#### 35.1 Kho ảnh: tài sản 0 đồng bị bỏ quên

60 webp đồng nhất 800×533 trong `web-nuxt/public/img/entities/`; **57 khớp CHÍNH XÁC
entity id** trong data.json (19 product, 9 dish, 8 craft_village, 6 attraction, 5
history, 4 nature, 4 experience, 2 event); đã mở xem 34/60 — chất lượng đồng loạt cao,
0 lỗi chữ AI. Production đang dùng **0 ảnh entity** ngoài thumb for-you. Cảnh báo
biên tập (hồ sơ chờ chủ): cho-vinh-long (mặt người AI + vẽ chợ nổi SAI chủ thể chợ
phố — đề nghị loại), le-hoi-nghinh-ong (3 mặt AI), dua-sap-tra-vinh (ruột RỖNG — trái
đặc tả dừa sáp, nhường dua-sap-cau-ke), vung-cam-sanh (chủ thể phụ); 3 ảnh mồ côi
không có entity (ca-cao-thanh-dat, thanh-that-cao-dai-vinh-long, rach-ba-sach) —
không gắn đâu cả, chờ chủ quyết tạo entity hay để kho. Sự kiện gần trắng ảnh: 2/67.

#### 35.2 Bảng phán quyết 16 thành phần (câu trả lời trực tiếp)

- **ĐỦ → giữ:** hero (kicker+h1+search) · thời tiết · mục lục (GIỮ CHỮ, nén 11→6) ·
  cộng đồng (nén 6→3) · dành-cho-bạn · topbar+footer.
- **THIẾU → sửa:** măng-sét (âm lịch TÍNH ĐỘNG — lunar_date=None trong data, bẫy §5c) ·
  hero dossier (ảnh duy nhất của trang mà không được bảo đảm — 4/90 experience có ảnh;
  nay cua-com + fallback tem v2 + nhãn canonical qua ImageDisclosure, validator
  fail-closed sẽ LOẠI chuỗi nhãn tự chế) · tín hiệu trắng ảnh (luật tin dẫn 3 bậc:
  event-có-ảnh → mùa-có-ảnh → tem v2; hôm nay mật ong rừng bần season 5–9 lên slot) ·
  tin chính đặc sản (backend B1 TIÊN QUYẾT — grep product_lead trong public_api.py = 0) ·
  sổ tay (thumb 56px phủ TRỌN 4/4 — thiếu ảnh thì tem cùng họ đất) · **«Ba vùng» —
  thành phần VẮNG MẶT lớn nhất**: route /khu-vuc/[area] + 3 ảnh area + area_counts đều
  sẵn mà production 0 lối vào vùng → mục MỚI 06b · lối «Đi lại & danh bạ» (23 facility
  transport sẵn).
- **DƯ THỪA → task dọn riêng (KHÔNG hồi sinh):** ≈490 dòng xác khối ảnh cũ
  (StorySpread 207 dòng + EntityFeature 239 dòng + FEATURE_*/SPREAD/spot* + CSS mồ côi
  + 4 test stub) — template không render cái nào.
- **KHÔNG PHÙ HỢP → đổi:** kết nói với người-đã-có-điểm-bắt-đầu (đảo thành câu lần-đầu,
  JourneyActionRail chỉ hiện khi có tín hiệu) · bài «Hé lô» 5 ký tự lọt trang chủ (bộ
  lọc ≥80kt HOẶC có entity — index.vue:396 hiện chỉ chặn rỗng) · 5 chuỗi máy-đọc gọi
  3 tỉnh cũ (index.vue:679, default.vue:97, nuxt.config.ts:85+87, gioi-thieu.vue:127 —
  task §1.6 riêng, TRƯỚC khi mở index).

#### 35.3 Trần ảnh mới — thay đếm bằng luật

**13 khối luôn-hiện = 9 ảnh thật (bind đúng id) + 4 tem v2**; ~17 khi for-you có tín
hiệu; 10 ảnh thật nếu duyệt hero B. Bốn luật cấu trúc (rút từ bản-27-hình gãy có ảnh
chứng minh): (1) mỗi điểm dừng đúng 1 ảnh chủ; (2) KHÔNG ảnh cho khối điều hướng;
(3) tem hồng/mint không cạnh nhau, không xuống thumb; (4) tối đa 1 dải ảnh tràn giữa
hai điểm dừng. Kèm: derivative resize local là ĐIỀU KIỆN nghiệm thu (996KB→~400KB;
3 file area gốc chiếm 59% cân nặng); GUARD DARK cho tem sinh
(brightness .78 saturate .85 — tem 0,86 sáng cạnh ảnh thật đã ghìm 0,48 là đè ngược
điểm dừng); mặt-người-AI/sai-chủ-thể có hồ sơ duyệt riêng.

Thumb-điều-hướng bị bác LẦN 2 (lần này bằng ẢNH THẬT — pblo: 7 ô chuyên mục ảnh = kệ
app-store, nhãn chìm) — nhưng vì chủ dự án tham chiếu svncoop, mockup 4.3 trình **phiếu
khảm chuyên mục** (7 ảnh cat-* có sẵn) CẠNH bản chữ để chủ nhìn hai bản tự quyết.

#### 35.4 svncoop.vn (XanhMap Quảng Trị — Khe Sanh, 104 địa điểm, Plan International)

Cùng mô hình trực tiếp. Học: khảm ảnh danh mục + số đếm sống (nếu chủ chọn) · pin bản
đồ theo icon danh mục + chú thích đếm (backlog ban-do.vue) · bảng "Thông tin chi tiết"
icon-hàng + mini-map + "Địa điểm tương tự" + nút "Gọi ngay" hợp §1.4 (backlog trang chi
tiết) · mobile mosaic 1-lớn+2-cột. KHÔNG chép: hiển thị giá + bộ lọc giá (mùi sàn —
§1.4). Vị thế: họ 104 địa điểm/1 khu vực được tài trợ; mình 1.746 entity + tầng
thời gian + hệ bản sắc — dữ kiện cho hồ sơ B2G của chủ (§4: tài liệu đối ngoại qua chủ).

#### 35.5 Bản 4.3 (artifact `1b07f7f5`) + chờ chủ quyết

Mockup: 11 mục (thêm 06b Ba vùng) · sổ tay 4/4 thumb · tin dẫn = ảnh mật ong · guard
dark tem · cộng đồng lọc «Hé lô» · kết đảo giọng · phiếu khảm svncoop · bảng 16 thành
phần in cuối trang. Cân nặng mockup 1,06MB (chỉ derivative; ảnh eager duy nhất cua-com
46KB). **Chờ chủ:** phiếu hero A/B/C · 2 ảnh sổ vàng sinh mới (sau khi chốt 3 ID) ·
hồ sơ 4 ảnh duyệt biên tập · 3 ảnh mồ côi · shortlist tin chính (sau B1) · chọn
CHỮ hay KHẢM cho mục lục. Thi công thật: theo 12 bước §32.4 + amendment §33.4/§34.3 +
các mục 7/14/15/16 của vòng này (B1 backend, registry R20.10, task §1.6, task dọn xác).

---

### 36. Mười site cùng mô hình, cùng hướng bản 4.3 — xác minh trực tiếp (2026-08-25)

**Nguồn việc:** chủ dự án ("treo" thi công) — *"liệt kê 10 website có mô hình tương tự
vinhlong360 nổi bật có hướng đi tương tự bản 4.3."* Cách làm: 15 ứng viên, 5 agent fetch
TRỰC TIẾP từng site chấm 7 trục (mô hình / biên tập / thời vụ / vùng / chứng thực /
kỷ luật ảnh / không-thương-mại) theo cấu trúc trang thật, không theo danh tiếng; 1 agent
chốt. Site không fetch được thì loại (không chấm mù).

#### 36.1 Top 10 (chi tiết đầy đủ trong file kết quả workflow phiên 2026-08-25)

1. **Slow Food Taitung** (slowfoodtaitung.tw) — cấp huyện, chính quyền hậu thuẫn, không
   bán; F=3 duy nhất: hệ MINH HOẠ motif thống nhất đọc ra bản sắc → nâng bìa sinh của ta
   từ "fallback xin lỗi" lên hệ nhận diện chủ động. Tránh: entity thuần client-JS.
2. **Visit Emilia** (visitemilia.com) — Food Valley; E=3 duy nhất: DOP kể 4 lớp (nguồn
   gốc → quy trình → cơ quan bảo chứng → NGÀY THĂM ĐƯỢC) → mẫu cho sổ vàng; nhưng họ
   chôn trang trong — ta đặt ngay trang chủ là vượt.
3. **Ireland.com** — B=3 duy nhất: MỘT tin chính ẩm thực "nơi chốn–con người–niềm tự
   hào". Tránh: lạm phát ~30 khối ảnh.
4. **Visit Okinawa Japan** (visitokinawajapan.com — domain cũ visitokinawa.jp đã chết) —
   dải thông báo thời-vụ CÓ NGÀY đầu trang; mẫu "vùng lớn + card con" cho Ba vùng.
   Tránh: Instagram feed cuối trang.
5. **Visit Alsace** (visit.alsace) — "Follow the guide": mỗi tiểu vùng = 1 ảnh + 1 câu +
   1 nút. Tránh: carousel 20+ thẻ.
6. **VisitScotland** — C=3: cặp khối mùa + sự kiện; bài học NGƯỢC quý nhất: có 11 món
   protected-origin mà giấu trong FAQ.
7. **Visit Faroe Islands** — kể đặc sản qua KỸ THUẬT + THỜI GIAN (cừu treo gió 5–9
   tháng); booking tách hẳn site khác. Tránh: mật độ ~30 ảnh nhiếp ảnh gia — AI-only
   bắt chước sẽ lộ.
8. **Peru Travel / Gastronomy** (peru.travel/gastronomy) — sản vật chủ lực MỖI THỨ MỘT
   KHỐI định danh riêng, chia 6 nền ẩm thực theo vùng. Tránh: awards dán logo không chuyện.
9. **Visit Jeju** (visitjeju.net) — công thức "right now" đặt tên tường minh đầu trang.
   Tránh: mọi mục đồng hạng; chứng nhận dán badge footer.
10. **Đà Nẵng FantastiCity** (danangfantasticity.com) — peer VN sống khoẻ nhất: MỘT sự
    kiện đinh đếm ngược ngay hero. Tránh: 6 dải ~50+ thẻ đồng cỡ — "chợ ảnh" nội địa.

Loại có lý do: OTOP Thailand (không fetch được từ đây — không chấm mù; bản chất
danh-bạ-catalog), Savor Japan (máy đặt bàn là xương sống), Oita Made (shop thuần —
KHÔNG phải site OVOP như dễ tưởng), Du lịch Ninh Bình (giọng cổng hành chính),
TasteAtlas (atlas toàn cầu + shop, lệch hạng mục). Oita Katete xác minh ra là tạp chí
tuyển dụng — loại nốt.

#### 36.2 Ba kết luận

1. **Mô hình 4.3 đứng trên dòng chảy quốc tế thật**: 10/10 site top đều giới-thiệu-
   không-bán, giao dịch đẩy ra ngoài — chốt §1.4 của dự án là chuẩn của DMO tử tế,
   không phải lựa chọn thiểu số.
2. **Ba trục khó nhất, mỗi trục chỉ MỘT site đạt 3 điểm, không site nào gom được hai**:
   tin chính (Ireland) · chứng thực kể thành chuyện (Emilia — mà phải xuống trang
   trong) · kỷ luật ảnh (Taitung). Trang chủ 4.3 làm đồng thời cả ba là VƯỢT mọi mẫu
   khảo sát, không chỉ bắt kịp. Lỗ hổng chung của cả nhóm: chứng nhận bị chôn/dán logo
   — sổ vàng OCOP giữa trang chủ là khác biệt thật.
3. **Lớp thời-vụ mạnh nhất luôn là dữ liệu thật có ngày** (Okinawa cảnh báo có ngày,
   Jeju "right now", Đà Nẵng đếm ngược 1 sự kiện đinh) — không phải widget mùa tĩnh;
   đúng hướng tin dẫn 3 bậc + măng-sét âm–dương của 4.3.

### 37. Thực hiện bản 4.3 — đợt A/B/C, 11 commit (2026-08-27)

> STATUS: active — đợt A và B đã xong và nhìn thấy được trên site đang chạy; đợt C
> làm xong C1 + C2. Đợt D (Sổ vàng OCOP) chưa bắt đầu, còn chờ chủ dự án duyệt.

Ba việc dọn nền chạy trước (không đụng giao diện, nên không chồng chéo với việc UI):
gỡ trường `verified` khỏi ngữ cảnh LLM (§1.7 — 1739/1746 entity đang được nói là "đã
xác minh" trong khi nguồn thật `attributes.verifiedAt` gần như rỗng), nới pool tìm
kiếm rồi mới cắt (ô tìm ở hero đang **mất kết quả đúng nhất** vì cắt trước khi xếp
hạng), và canary cho mìn 2027 (kho sự kiện có hạn dùng — test sẽ đỏ ngày 2026-10-11,
sớm 3 tháng, thay vì im lặng để trang chủ trống mục sự kiện).

#### 37.1 Ba bài học kỹ thuật của đợt này

1. **Đo bằng ảnh chụp, không chỉ bằng số.** Dải chip "Bản đồ · 3 vùng" đo ra "1 hàng,
   7 liên kết" — nghe là đạt. Ảnh chụp mới lộ nó gãy hai dòng: lưới 2 cột không chứa
   nổi 3 con. Số đo trả lời đúng câu hỏi tôi đặt ra, chỉ là tôi đặt sai câu hỏi.
2. **`element.screenshot()` KHÔNG kích hoạt lazy-load.** Ảnh hiện ra trắng trơn dù
   `naturalWidth=800`, `complete=true`, `decode()` thành công. Suýt "sửa" một thứ
   không hỏng. Phải chụp CẢ KHUNG NHÌN sau `scrollIntoView`. Cùng họ: pane trình
   duyệt bị ẩn thì trang ngừng dựng khung — `setTimeout`/`decode()` treo và số đọc ra
   là số cũ.
3. **Tầng nào biết gì thì giữ việc đó.** C2 lúc đầu cho backend CHỌN luôn hàng tin
   dẫn. Chạy ra 0 tin dẫn: `homeNocturnePresentation.remaining()` loại các entity đã
   bị hero/spotlight/quick-decision tiêu thụ, mà backend không thể biết. Tách lại —
   backend chấm ĐIỀU KIỆN (`signal_lead_ok`: có ảnh thật + tên sạch §1.6, dùng lại
   `_has_stale_geography` đã có test), frontend chọn NGƯỜI trong số còn sống. Không
   nhân bản luật ra TypeScript: hai bản của cùng một luật thì chỉ một bản được sửa.

#### 37.2 Một lỗi tự gây, ghi lại để không lặp

A0 (`77ab0e89`) xoá chuỗi ảnh nền spotlight nhưng để lại `entity-card-disclosure.test.ts:232`
đòi `SPOT_CAT_PHOTO` → **commit với một test đỏ**, phạm B5. Không lộ ra vì lúc đó tôi
chỉ chạy các file test của riêng trang chủ. Bài học: đổi `pages/index.vue` thì chạy
`npx vitest run` TRẦN, đừng lọc theo tên file — trang chủ bị soi bởi test nằm ở file
mang tên khác. Vá ở C2: gỡ khẳng định đang canh một tính năng đã xoá và thay bằng
khẳng định phủ định; bốn rào phủ định thật của test đó giữ nguyên hiệu lực.

#### 37.3 Còn nợ, chưa làm

- **Gói JS 802/800kB gz** — nợ có TRƯỚC đợt này (790kB lúc đặt trần 2026-07-10, biên
  đã bị ăn hết). Không có nhát cắt sạch: 0 chunk trùng, top-3 = 388kB mà maplibre
  chiếm 276kB và đã lazy đúng. Cần task hiệu năng riêng; đang chặn job frontend của CI.
- **Nợ nội dung §1.6 đang sống trên trang chủ** — mục tín hiệu vẫn hiện "Hội thi Đờn ca
  tài tử - cải lương **huyện** Long Hồ". C2 đã chặn không cho hàng như vậy được dựng
  lớn, nhưng chữ vẫn nằm đó. Sửa dữ liệu cần backup B1 + chỉ đạo chủ dự án (§4).
- **Cờ tính năng cần PostgreSQL** — `home_product_lead` không bật được ở local dev.
- **Số liệu tin chính đặc sản đều đo ở local** — prod PG đã phân kỳ (§1.1), kho ứng
  viên có thể rỗng và mục khuyết êm. Phải đo lại trên prod trước khi tin.

### 38. Vòng thẩm tra đối kháng đợt A/B/C — 13/13 phát hiện sống đã đóng (2026-08-27)

> STATUS: done (phát hiện) — cả 13 phát hiện sống đã vá trong phiên; chúng gộp về
> 7 NGUYÊN NHÂN GỐC (§1.6 ×3 · múi giờ ×3 · ngày âm ×3 · rò verified ×1 · CI ×1 ·
> registry ×1 · khẳng định mồ côi ×1). Ba phát hiện bị bác + các việc chờ chủ dự
> án ghi ở §38.4 — chúng KHÔNG phải phát hiện chưa vá.

**Vì sao chạy vòng này:** đợt A/B/C đã lộ ra một lỗi tôi không tự bắt được (A0
`77ab0e89` commit kèm một test đỏ, chỉ hiện ra 5 commit sau). Tự kiểm rõ ràng
không đủ, nên soi lại toàn bộ 13 commit bằng 6 chiều độc lập, mỗi phát hiện phải
qua một agent khác cố **bác bỏ** và tự tái hiện mới được tính. 22 agent, 16 phát
hiện được thẩm tra, **13 sống / 3 bị bác**.

#### 38.1 Bốn lỗi nặng — đều do tôi gây ra trong chính đợt này

| | Lỗi | Vì sao tôi không tự thấy |
|---|---|---|
| **§1.6 fail-open** | `\b(cu\|truoc)\b` dò trên chuỗi ĐÃ BỎ DẤU → "cù lao", "Trà Cú", "Cứ" đều thành "cu" = dấu "cũ". Cổng §1.6 DUY NHẤT của cả tin chính lẫn tin dẫn. 8 entity gọi tỉnh cũ trần vẫn lọt | Tôi test bằng chuỗi TỰ NGHĨ RA, không chuỗi nào chứa âm "cu" |
| **Nửa vá múi giờ** | B1a đổi `month` sang giờ VN nhưng bỏ `today` (:3312) và `_event_is_past` → măng-sét và đếm ngược cãi nhau 7 tiếng/ngày | Test tôi viết chỉ khẳng định số học `datetime.astimezone` của stdlib — hoàn nguyên mã về UTC nó vẫn xanh |
| **Ngày âm nói ngược** | C1 suy ngày âm từ `date_start`, mâu thuẫn `attributes.lunar_date` mà /le-hoi đang in — 24/36 sự kiện lệch | Tôi tự tin vì commit ghi "né bẫy sáu-ô §5c". Né SAI VẾ |
| **Rò `verified` cửa 2** | `_tool_entity_detail` vẫn bơm trường đó vào ngữ cảnh LLM; d2a1a99a mới bịt `_search_result_card` | Test kèm commit chỉ chấm một hàm |

**Bài học chung:** cả bốn đều có test XANH đứng cạnh. Test xanh chứng minh điều
nó khẳng định, không chứng minh điều tôi TƯỞNG nó khẳng định.

#### 38.2 Không đọc ≠ không mâu thuẫn (ca C1, đáng ghi riêng)

C1 lập luận: "không đọc `lunar_date` thì né được bẫy sáu-ô". Sai vế. Không ĐỌC
thì tránh được việc **sửa** ô đó; nó không tránh được việc **nói ngược** ô đó khi
một trang khác vẫn in ô đó. Bảng quyết định
`docs/2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md` (lập 2026-08-07) đã
phân loại sẵn 67 event: **12 ca KHỚP · 3 ca `date_start` CHÍNH LÀ ô sai · 14 ca
tự mâu thuẫn, "KHÔNG giải được từ dữ liệu — phải có người chốt"**. C1 suy từ đúng
cái ô hỏng. Đã GỠ nhãn âm lịch theo-sự-kiện; măng-sét giữ nguyên vì ngày âm của
HÔM NAY là ngày lịch, không phải dữ liệu entity.

#### 38.3 Cái LƯỚI mới là gốc — CI chưa từng chạy test frontend

Trong `ci.yml` job `frontend`, cổng bundle đứng TRƯỚC `Run tests` và không có
`continue-on-error`. Gói JS 803/800 kB gz → job dừng ở đó → `npm test` **không
bao giờ chạy**. Đó là lý do lỗi A0 sống được 5 commit: không phải lưới thưa, mà
lưới chưa từng được thả xuống. Đã đảo thứ tự (test trước, cổng bundle sau +
`if: always()`): cổng vẫn nguyên răng, chỉ là hết bịt miệng test.

Kèm hai lỗ lưới nhỏ hơn: registry ảnh R20.10 thiếu hàng cho 2 bồn ảnh mới (khai
xong mới lộ tôi khai SAI CHỖ — component nhận descriptor qua prop nên không chứa
bằng chứng nào; nơi đúng là TRANG giao việc, đúng khuôn `home-feature-dossier`);
và khẳng định `toContain('EntityFeature')` chỉ còn được nuôi bằng một dòng bình
luận chết — cặp song sinh của lỗi A0 mà tôi bỏ sót ở CHÍNH commit đi vá nó.

#### 38.4 Còn lại — chưa vá trong phiên

- Ba phát hiện **BỊ BÁC** (ghi để khỏi đào lại): SYSTEM_PROMPT dạy trường
  `verified` (hợp đồng KHÔNG mồ côi — `entity_detail` vẫn là hộ sản xuất sống);
  quy kết `toContain('EntityFeature')` cho A0 (sai về lịch sử — khối biến mất
  trước A0); 4 ảnh `cat-*.webp` mồ côi sau A0 (sự kiện đúng, tư cách "lỗi" sai).
- **Nợ gói JS 803/800 kB gz** — nợ có trước đợt này, cần task hiệu năng riêng.
  Đã ghi sổ ngoại lệ R30.7 (`docs/standards/90-exceptions-log.md`).
- **Nợ nội dung §1.6** vẫn sống trên trang chủ: "Hội thi Đờn ca tài tử - cải
  lương **huyện** Long Hồ". Cổng nay chặn không cho nó được dựng lớn, nhưng chữ
  vẫn nằm đó. Sửa dữ liệu cần backup B1 + chỉ đạo chủ dự án (§4).
- **Bảng quyết định ngày âm/dương** chờ chủ dự án điền cột CHỐT — cho tới lúc đó
  trang chủ không in ngày âm theo sự kiện.

### 39. Trả nợ kỹ thuật — 5 khoản đóng, 1 khoản chuyển thành câu hỏi cho chủ (2026-08-27)

> STATUS: active — bốn khoản trong backlog §31.5 đã đóng; nợ gói JS đo lại và
> KHÔNG có nhát cắt trong tầm kỹ thuật, chuyển thành quyết định của chủ dự án.

#### 39.1 Đã đóng

| Nợ (§31.5) | Thực tế nặng hơn ghi chép ở chỗ nào |
|---|---|
| `ORDER BY updatedAt DESC` thiếu khoá phá hoà | Không phải "4 entity đồng điểm" mà là **mọi nhánh sort** đều thiếu, trong khi truy vấn có `LIMIT/OFFSET` → phân trang mất tính phân hoạch. SQLite trả theo rowid nên tình cờ ổn định; Postgres thì không |
| 5 chuỗi máy-đọc gọi 3 tỉnh cũ | Quét lại ra **9**, và hai bề mặt nặng nhất chưa từng được ghi: `manifest.json` và `llms.txt` — tài liệu viết riêng cho crawler AI |
| 00-INDEX lệch baseline | Lệch **ba** số, trong đó R20.8 bảng ghi 17 mà thật là 47 — bảng nói THIẾU nợ, nguy hơn nói thừa |
| (phát sinh) R20.10 vắng mặt trong bảng chuẩn | Rào mới bắt được: một luật **hard** không có dòng nào trong bảng, tức vô hình với người đọc. `95-ra-soat-cong.md:181` đã ghi nhận đúng lỗ này trước đó mà chưa ai vá |

Bài học lặp lại lần thứ ba trong phiên: **cổng chuẩn là bộ SO CHUỖI và nó bắt cả
bình luận**. Hai ký tự `★` tôi viết trong bình luận đẩy R30.2 lên 331 > baseline
330; và câu đính chính §1.6 đúng nhất có thể ("Không còn tỉnh Bến Tre") bị chính
R10.7 bắt vì nó chứa đúng cụm bị cấm.

#### 39.2 Nợ gói JS: đã thử, đã đo, KHÔNG cắt được bằng kỹ thuật

Số đo trên bản build 2026-08-27: **JS 803 kB gz / trần 800** (vượt 3 kB) ·
CSS 166/190 · chunk lớn nhất 276/280.

- **Không có mỡ thư viện bên thứ ba:** toàn bộ `dependencies` runtime chỉ có 4
  gói — maplibre-gl, nuxt, vue, vue-router. maplibre đã `await import()` đúng
  cách (`composables/useNDAMap.ts:80`), không phải sửa gì.
- **Hai component chết (StorySpread, EntityFeature) KHÔNG nằm trong bundle JS** —
  đã kiểm bằng grep trên `.output`. Task dọn xác §35.2 sẽ không trả được nợ này.
- **Thí nghiệm gộp chunk vụn: PHẢN TÁC DỤNG.** 64/183 chunk dưới 1 kB nên
  `experimentalMinChunkSize: 6kB` nghe rất hợp lý. Kết quả đo: 183 → 135 file
  nhưng **803 → 813 kB** (+10). Rollup nhân bản module dùng chung khi gộp, và
  chunk entry phình 91 → 98 kB. Đã hoàn nguyên. **Ghi lại để không ai thử lại.**

#### 39.3 Câu hỏi cho chủ dự án (không tự quyết)

`276/803 kB = 34%` của tổng là **maplibre, và nó lazy đúng — không bao giờ tải ở
lần sơn đầu**. Trần `total_gz_kb: 800` đặt 2026-07-10 khi tổng là 790, đếm CẢ mã
lazy. Nên câu hỏi thật không phải "cắt ở đâu" mà là:

> Trần "tổng" có nên đếm chunk vendor tải-lười không, hay chỉ nên đếm phần vào
> lần sơn đầu?

Đây là đổi ĐỊNH NGHĨA thước đo, không phải nới trần cho dễ thở — nên phải có chủ
dự án chốt (§3.7: thao tác diện-rộng cần giải trình trong cùng commit). Trong lúc
chờ, ngoại lệ R30.7 đã ghi sổ `90-exceptions-log.md`, và CI nay chạy test TRƯỚC
cổng bundle nên nợ này không còn bịt miệng được test (§38.3).

### 40. Nợ P0 pháp lý + hai bài học đo lường (2026-08-27)

> STATUS: active — phần KHẢ KIẾN đã làm; hai đường xử lý thực chất chờ chủ dự án.

#### 40.1 "Hứa xoá vĩnh viễn" mà không xoá — nay không còn vô hình

Backlog 2026-08-22 xếp P0 và ghi đây là mục DUY NHẤT không nằm sau cờ. Kiểm lại
2026-08-27: **còn đúng từng chi tiết**. Người dùng bấm "Lên lịch xoá" được trả
lời «Tài khoản sẽ bị xoá vĩnh viễn sau N ngày», nhưng `_effective_erasure_audit_only()`
trả True nếu THIẾU một trong hai cờ, và `erase_due_accounts` đếm hồ sơ quá hạn
rồi thoát TRƯỚC vòng xoá — 288 lần/ngày.

Đã làm (KHÔNG bật xoá thật — §4, thao tác phá dữ liệu, phải có chủ dự án):

- `.env.example` khai hai khoá `ERASURE_*` (trước đây **không có khoá nào**, nên
  deploy theo file mẫu chắc chắn rơi vào chỉ-đếm mà không ai biết mình đã chọn).
- `/health/ready` chiếu `overdue_count` — con số vốn đã nằm sẵn trong
  `_ERASURE_STATUS` mà không được đưa ra — kèm `state`:
  `ready` · `audit_only` · `audit_only_with_overdue`. `ok` giữ nguyên có chủ
  đích: lật đỏ là chặn deploy của một cấu hình cố ý, quyết định đó thuộc chủ dự
  án chứ không thuộc cổng.
- Tách `_erasure_readiness()` ra mức module để kiểm được (bản cũ nằm trong
  closure nên test duy nhất canh nó là test so-chuỗi trên mã nguồn).

**Chủ dự án phải chọn MỘT:** (a) bật xoá thật — đặt cả hai khoá và kiểm trên môi
trường có backup; hoặc (b) giữ chỉ-đếm nhưng **sửa câu trả lời cho người dùng**,
đừng hứa "xoá vĩnh viễn". Giữ nguyên trạng là hứa một đằng làm một nẻo.

#### 40.2 Bài học: "cây đứng yên" chưa đủ — MÁY phải đứng yên

Một bản đo full-suite ra **112 failed / 132 errors** so với baseline 16/0. Không
phải hồi quy: chạy riêng `test_location_resolver.py` cho 38/38 xanh. Nguyên nhân
là tôi khởi động `agent/server.py` + Nuxt dev **giữa lúc suite đang chạy** (để đo
một mục backlog UI), rồi cho trình duyệt gọi `/api/homepage` liên tục — backend
đó dùng CHUNG DB SQLite với test.

Ghi chú cũ trong bộ nhớ chỉ nói "đừng sửa file .py khi suite đang chạy". Hẹp hơn
thực tế: **đừng chạy tiến trình nào dùng chung tài nguyên với suite**. Kèm một
lỗi phụ đắt không kém — bản đo đó chạy `--tb=no` nên không lưu traceback nào,
phải chẩn đoán lại từ đầu. Đo dài thì dùng `--tb=line`.

#### 40.3 Bài học: toạ độ hộp KHÔNG chứng minh phần tử nhìn thấy được

Mục backlog 2026-08-23 "ô tìm kiếm chính bị che ở 360×740" đo lại: ô tìm ở
**375–429**, thừa trong màn 740 — tưởng đã tự khỏi sau đợt A. Nhưng
`document.elementFromPoint(tâm ô tìm)` trả về `DIV.onboarding-overlay`: **bảng
chào lần-đầu cao trọn 740px che kín hero trên di động**. Sau khi tắt bảng chào,
chính ô tìm là phần tử trên cùng — hiện đủ, bấm được.

Nguyên nhân KHÁC hẳn ghi chép cũ (ngân sách dọc). Bảng chào là quyết định thiết
kế (cờ `onboarding` mặc định bật) nên không tự đổi — nhưng đáng để chủ dự án
biết: khách vào lần đầu bằng điện thoại thấy bảng chào, không thấy site.

### 41. ĐÍNH CHÍNH phạm vi nợ §1.6 trên frontend — 99 lần / 30 file, không phải 9 (2026-08-27)

> STATUS: active — commit `d580a386` chỉ đóng 6 bề mặt cấp SITE. Phần lớn nợ còn nguyên.

**Tôi đã nói quá phạm vi việc mình làm.** Commit `d580a386` ghi «quét lại ra 9»,
nhưng thực tế tôi chỉ quét **4 file mà backlog nêu tên** (nuxt.config, default.vue,
index.vue, gioi-thieu.vue) rồi thêm hai file tự tìm ra. Đó đúng là cái sai đã làm
con số của chính backlog (5) thấp hơn thực tế. Quét toàn bộ `web-nuxt/**/*.{vue,ts}`
(trừ node_modules/.nuxt/.output/tests): **99 lần nhắc / 30 file**.

Nặng nhất **`utils/pageManifest.ts` (20)** — manifest `seoTitle`/`seoDescription`/
`ogDescription`/`heroSubtitle` của TỪNG trang danh mục. Nghĩa là tôi đã sửa meta cấp
site mà để nguyên meta của ~8 trang con; `ban-do.vue` cũng còn meta + JSON-LD `name`.

#### 41.1 Bốn lớp khác nhau, đừng gộp

| Lớp | Ví dụ đã kiểm | Xử lý |
|---|---|---|
| **Máy đọc, cần sửa** | `pageManifest.ts` ×20 · `ban-do.vue` meta+JSON-LD · `legalContent.ts:102` seo_description | mechanical, nhưng vướng đánh đổi ở §41.2 |
| **Taxonomy** | `useConstants.ts` AREA_META · `useRegionPref.ts` · `PersonalizeSetupSheet.vue` | khoá vùng + nhãn điều hướng, ~37 điểm gọi, CMS ghi đè được — **quyết định sản phẩm của chủ dự án** |
| **ĐÚNG rồi, đừng đụng** | `useWeather.ts:33` (bình luận nói rõ đơn vị này KHÔNG CÒN TỒN TẠI) · `adminUnit.ts:152` (bình luận của chính hàm đi VÁ structured-data) · `legalContent.ts:103` («vùng Vĩnh Long mới — bao gồm…») | giữ nguyên |
| **Tên riêng** | `routesContent.ts` «Chợ Bến Tre», «Vòng dừa Bến Tre» | tên của một CHỢ, một TUYẾN — không phải gọi tên tỉnh |

#### 41.2 Đánh đổi phải để chủ dự án chốt

Cụm tôi dùng ở cấp site — «tỉnh Vĩnh Long (hợp nhất từ Vĩnh Long, Bến Tre, Trà Vinh
cũ)» — **không dùng lại được cho meta từng trang**: `seoDescription` có ngân sách
~155 ký tự, thêm mệnh đề đó vào 8 trang là ăn hết chỗ của nội dung thật.

Hai đường, và chúng đánh đổi thật:

- **(a) Bỏ hẳn tên tỉnh cũ khỏi meta trang con**, chỉ ghi «tỉnh Vĩnh Long». Gọn, đúng
  §1.6 tuyệt đối. **Mất** truy vấn tìm kiếm «du lịch Bến Tre», «OCOP Trà Vinh» — mà
  người dân vẫn tìm bằng tên cũ nhiều năm nữa.
- **(b) Giữ tên cũ kèm dấu lịch sử ngắn** («… Bến Tre, Trà Vinh cũ»). Giữ được truy
  vấn, tốn ~12 ký tự mỗi mô tả.

Đây là đánh đổi SEO/nội dung, không phải sửa kỹ thuật — không tự quyết. Ghi chú: site
đang noindex nên chưa mất gì; việc này phải xong TRƯỚC khi mở index.

### 42. Hạng sao OCOP: một luật chép tay ở 12 nơi, và bài học "test song song không phải phép đo" (2026-08-27)

> STATUS: active — đã gom về hai bản sinh đôi có bộ ca dùng chung; đường thoát
> một-bản còn chờ (xem §42.4).

#### 42.1 Lỗi đo được trên trang đang chạy

`/dia-diem/dua-sap-cau-ke` — trang của **trái dừa sáp** — phát ra:

| bề mặt | giá trị |
|---|---|
| huy hiệu | `OCOP VICOSAP: 4 SP OCOP 5 sao quốc gia + 7 SP OCOP 4 sao` (rộng 468px) |
| JSON-LD `brand.name` | cùng chuỗi đó |
| JSON-LD `identifier.value` | cùng chuỗi đó |

Tức trang gán **danh mục chứng nhận của một công ty khác** cho trái dừa rồi đẩy
vào structured data cho máy tìm kiếm đọc. Và `khoai-lang-say-binh-tan` được khai
`brand.name = OCOP 5 sao` trong khi văn xuôi của nó nói hạng 5 mới chỉ **được đề
nghị** — khai khống chứng nhận, đúng thứ §1.7 cấm.

#### 42.2 Phạm vi thật: 12 nơi, không phải 1

`attributes.ocop` là văn xuôi tự do. Luật rút hạng bị chép tay khắp nơi:

**Frontend (5)** — `EntityCard.vue` (huy hiệu, hiện trên MỌI trang danh mục),
`dia-diem/[id].vue` (chip hero, khối nổi bật, JSON-LD fallback), `san-pham.vue`
(đếm + lọc, sót 73 sản phẩm chỉ có `ocop_star`).

**Backend (7)** — `seo.py` (brand + identifier), `contextual_retrieval.py` (nối
`"OCOP {ocop} sao."` vào **văn bản nạp cho LLM** → dạy mô hình một lời khai
sai), `server.py` (4 thẻ chat + bộ lọc tìm kiếm rút hạng bằng **chữ số đầu tiên
gặp ở bất kỳ đâu**), `itinerary_gen.py` (ghi chú lịch trình), `public_api.py`
(`_lead_ocop_star` — bản sao THỨ BA của luật, cùng lỗi chữ-số-lạc),
`smart_rank.py` + `knowledge.py` (lọc bằng truthiness → sót 73 sản phẩm).

Đã gom về `agent/ocop.py` ↔ `web-nuxt/utils/ocop.ts`.

#### 42.3 Bài học: test song song là LỜI HỨA, file dùng chung mới là PHÉP ĐO

Ba lần bản vá bị bắt lỗi, **không lần nào do tôi tự thấy**:

1. **Test cũ của `seo`** bơm `attributes` dạng LIST (dữ liệu dị dạng có thật) —
   hàm mới nổ `AttributeError`. Tôi vá, nhưng chỉ vá MỘT trong hai hàm; test của
   chính tôi bắt nốt hàm còn lại.
2. **Test cũ ghim `identifier.value = "4 sao"`** trong khi tôi đặt
   `"OCOP 4 sao"`. `propertyID` đã là `"OCOP"` nên lặp là thừa — **test cũ đúng
   hơn tôi**, và suýt nữa tôi sửa test cho khớp bản vá.
3. Tôi viết test song song ở CẢ HAI bên, **cả hai đều xanh** — trong khi hai bản
   thực sự lệch nhau ở việc kẹp thang 1..5. Chỉ khi làm
   `tests/fixtures/ocop-twin-cases.json` (21 ca, cả hai suite cùng đọc) thì lệch
   mới lộ ra, **ngay lần chạy đầu tiên**, và lộ thêm một lệch thứ hai nữa.

Nói cách khác: hai bộ test viết song song bởi cùng một người, cùng một lúc, vẫn
mù chung một chỗ. Chúng chỉ chứng minh mỗi bản tự nhất quán, KHÔNG chứng minh
hai bản khớp nhau. Muốn đo được thì input phải là MỘT file.
**Dự án đã có sẵn kỷ luật này — tôi phát minh lại.** Cặp sinh đôi âm lịch
(`agent/lunar_calendar.py` 490 dòng ↔ `web-nuxt/composables/useLunar.ts` 407
dòng) từ trước đã có `web-nuxt/tests/lunar-oracle-parity.test.ts` đọc fixture
`lunar-oracle.json`, kèm dòng dặn thẳng: *"Nếu oracle đổi, sinh lại fixture rồi
chạy lại; KHÔNG nới assertion cho xanh."* Đáng lẽ phải tìm tiền lệ trước khi tự
dựng. Ghi ở đây để lần sau ai gặp cặp sinh đôi thứ ba thì biết đã có hai tiền lệ.

Một khác biệt CÓ CHỦ ĐÍCH: fixture âm lịch được **sinh ra** từ oracle Python,
còn `ocop-twin-cases.json` **viết tay**. Vì bản chất khác nhau — âm lịch là phép
tính thiên văn nên bản Python là chuẩn mực, sinh ra là đúng; còn kỳ vọng OCOP là
QUYẾT ĐỊNH CHÍNH SÁCH (§1.7: VICOSAP thì chỉ "OCOP", mới đề nghị thì không khai
hạng). Sinh từ mã sẽ đóng băng luôn cả lỗi nếu bản Python sai; viết tay thì bắt
được cả trường hợp CẢ HAI bản cùng sai.

Vị trí file cũng khác vì lý do đó: fixture âm lịch nằm trong `web-nuxt/tests/`
(chỉ TS đọc), còn `ocop-twin-cases.json` nằm ở `tests/fixtures/` gốc repo — nơi
đã có sẵn các corpus dùng chung mà Python đọc — vì nó được đọc từ CẢ HAI phía.


#### 42.4 Nợ còn lại — đường thoát một-bản

Hai bản là BẮT BUỘC hôm nay vì backend dựng JSON-LD / văn bản LLM / thẻ chat còn
frontend dựng huy hiệu, và API **chưa phát ra trường hạng đã chuẩn hoá**. Đường
thoát đúng: backend chiếu sẵn một trường hạng (ví dụ `attributes.ocop_tier` đã
qua §1.7) để frontend khỏi tự rút. Khi đó `web-nuxt/utils/ocop.ts` teo lại còn
mỗi hàm định dạng nhãn, và bộ ca dùng chung thành thừa.

Chuẩn hoá DỮ LIỆU (gộp 4 khoá `ocop_star`/`ocop_stars`/`ocop_rating`/`ocop` về
một) vẫn là task riêng cần backup B1 + chỉ đạo chủ dự án — xem §31.5.

### 43. B3 — quét CSS chết bằng RENDER THẬT: phương pháp, và giới hạn của nó (2026-08-27)

> STATUS: active — gỡ được 2 khối chắc chắn; ~22 lớp nhóm cộng đồng KHÔNG kết
> luận được trên máy này, cần Postgres + phiên đã-đăng-nhập.

Backlog 2026-08-23 ghi B3 "cần đo bằng render thật, KHÔNG bằng grep". Đây là
lượt đo đó. **Phương pháp mới là phần đáng giữ**, con số chỉ là sản phẩm phụ.

#### 43.1 Ba phép đo, vì một mình phép nào cũng nói dối

| Phép đo | Bắt được gì | Nói dối ở đâu |
|---|---|---|
| Phân tích tĩnh | lớp không xuất hiện trong markup/script | **đếm cả token trong CHÚ THÍCH** — vừa đẻ ứng viên giả, vừa che giấu lớp chết |
| Lọc dựng-động | `:class="'cat-area-' + area"` | không có nó thì 283 lớp SỐNG bị kết án oan |
| Render thật | lớp không bao giờ khớp | **không chạm được trạng thái đã-đăng-nhập** |

Bản đầu của công cụ tôi viết sai **cả hai chiều** vì không bỏ chú thích: nó đẻ ra
ứng viên giả `.eh-` (từ dòng `/* .eh-* đã xoá */`) và đồng thời **giấu** những lớp
chết chỉ còn được nhắc trong comment. Sửa xong: **36 → 63 ứng viên**. Con số đầu
tiên tôi đưa ra là sai.

Loại tiếp: 283 lớp dựng động · 4 lớp của maplibre (thư viện tự áp lúc chạy) · 10
lớp Vue `<Transition>` tự sinh. Còn **55** ứng viên, render 9 trang: **0 khớp**,
và **0 lần** trong `web/data.json` nên không có rủi ro `v-html`.

#### 43.2 Giới hạn TỰ LỘ RA — và vì sao chỉ gỡ 2 khối chứ không phải 55 lớp

`/cong-dong` render **0 bài viết** và có nút "Đăng nhập": local chạy SQLite nên
UGC trả 503 (§1.3). Nghĩa là với ~22 lớp nhóm cộng đồng (`suggest-*`, `md-*`,
`suc-*`, `reaction-btn`, `just-saved`, `bookmark-momentum`, `char-count`,
`hide-undo`…) phép đo render **không kết luận được gì** — chúng có thể sống
trong trạng thái mà máy này không chạm tới.

**Đã gỡ (98 dòng, `editorial.css`):** khối `.cine-*` (hero điện ảnh) và
`.story-block`, kèm quy tắc con mồ côi `.editorial-heading .cine-kicker` và một
dòng `prefers-reduced-motion` cho lớp đã chết.

**CHƯA gỡ, cần môi trường khác:** 22 lớp cộng đồng ở trên. Muốn kết luận thì
phải chạy `docker compose up postgres`, tạo phiên đăng nhập, rồi đo lại.

#### 43.3 Hai ghi chú phát sinh

- **Giả thuyết của tôi sai, kiểm mới biết.** Tôi đoán `.story-block` là CSS của
  `StorySpread` vừa xoá. Xem lại trong git: StorySpread dùng `.spread-*`,
  EntityFeature dùng `.ef-*`, và **cả hai để CSS trong `<style scoped>`** nên đã
  đi theo file. `.story-block` mồ côi từ một đợt gỡ KHÁC.
- **`editorial.css` có thể còn chết nhiều hơn.** Hai trang được cho là dùng nó
  (`/khu-vuc/[area]`, `/dia-diem/[id]`) render mà **không có** `.editorial-body`,
  `.pull-quote`, `.drop-cap`, `.chapter-sticky` nào. Chưa truy tiếp — cần biết
  trang nào thật sự dùng chúng trước khi động.
- **`/xa-phuong/<slug-sai>` trả 500 trong khi API trả 404** — trang lỗi nói sai
  loại lỗi. Không liên quan CSS; ghi để không quên.

### 44. LỖ HỔNG CỔNG: hook `--staged` không thể thực thi ratchet có baseline > 0 (2026-08-27)

> STATUS: done (2026-08-27) — ĐÃ VÁ bằng "ratchet theo-file", xem §44.3.

**Phát hiện thế nào:** tôi thêm `agent/ocop.py` với một hàm complexity 21. Hook
pre-commit cho qua, in "✓ run_hard: sạch (hard=0, ratchet không tăng)". Chỉ khi
chạy `run_hard --all` mới lộ: **R20.8 = 48 > baseline 47**.

**Cơ chế** (`scripts/checks/common.py:216` + `run_hard.py:144`):

```
--staged  →  files = staged_files()   →  check.run(files)  →  count CHỈ TRONG file staged
ratchet_violations():  if count > baseline[rule]   # baseline là số TOÀN KHO
```

So một tập con với một tổng thể. Với rule có baseline > 0, tập con gần như luôn
nhỏ hơn ⇒ **không bao giờ đỏ**.

| Rule | baseline | hook staged có chặn được không |
|---|---|---|
| R20.5, R20.7, R20.9, R30.1, R30.6, R30.7, R40.3, R60.1… | 0 | **CÓ** — mọi vi phạm đều > 0 |
| R20.8 complexity | 47 | KHÔNG |
| R30.2 emoji · R30.3 màu · R30.8 bo góc | 330 / 147 / 369 | KHÔNG |
| R50.2 · R50.3 · R50.4 · R50.7 | 102 / 7 / 245 / 24 | **CÓ** — xem đính chính |

> **ĐÍNH CHÍNH (cùng ngày).** Bản đầu xếp R50.* vào nhóm "không chặn được". SAI:
> chúng khoá theo `web/data.json` (`check_thin_content:35`, `check_content_voice:93`,
> `check_content_gates:54`) và khi file đó được staged thì quét TOÀN BỘ nó, nên
> `count` đã là số toàn kho — so với baseline toàn kho là ĐÚNG. Lỗ hổng thật chỉ
> có **BỐN** rule quét-theo-từng-file: R20.8, R30.2, R30.3, R30.8.

Tức **cổng chỉ có răng ở đúng những rule đã sạch**, cộng nhóm quét-toàn-dữ-liệu.
Ở bốn rule quét-theo-file đang mang nợ — chính là chỗ cần ratchet nhất — nó là
trang trí.

Điều này giải thích lại một chuyện: sổ ngoại lệ quy nợ complexity 3 → 47 cho
"nhánh phát triển ngoài tầm cổng". Đúng một phần, nhưng chưa đủ — **commit đi
đúng cổng cũng thêm được nợ thoải mái**, và hôm nay tôi vừa làm đúng thế.

**Cách vá đề xuất** (không tự làm): ở chế độ staged, với mỗi rule ratchet, so
count trong file staged với count của **chính những file đó ở HEAD**. Tăng ⇒
chặn. Vừa chính xác vừa nhanh, giữ được ngân sách <5s của hook; không cần quét
toàn kho.

**Vì sao không tự vá:** nó làm cổng nghiêm hơn hẳn và sẽ chặn những commit trước
đây lọt — đổi hành vi thực thi trên toàn dự án. Đó là quyết định của chủ dự án.
Trong lúc chờ: **chạy `python scripts/checks/run_hard.py --all` trước khi commit**
nếu commit chạm `agent/`, `scripts/` hoặc `web-nuxt/` — hook một mình không đủ.

#### 44.3 Đã vá — "ratchet theo-file"

Không so tập con với tổng thể nữa. Với rule có baseline > 0, cổng dựng lại nội
dung **HEAD của chính những file đang staged** vào thư mục tạm, chạy đúng bộ
check trên đó, rồi so: *file này trước có bao nhiêu vi phạm, giờ có bao nhiêu?*
Phép so ấy đúng bất kể baseline lớn cỡ nào.

```
✖ RATCHET R20.8 (complexity): 1 vi phạm trong file đang sửa,
  bản HEAD của chính những file đó có 0 — RATCHET theo-file
```

Đã tái hiện đúng ca lọt sáng nay: thêm một hàm complexity cao rồi chạy hook →
exit 1. Hook mất **1,00s** (ngân sách <5s).

**Hai lần bản vá tự bắt lỗi của chính nó:**

1. Test tôi viết phát hiện commit gồm **toàn file MỚI** vẫn lọt — vì không file
   nào tồn tại ở HEAD thì hàm đếm thoát sớm. Mà đó ĐÚNG là đường `agent/ocop.py`
   đã đi (file mới, complexity 21). Sửa: không có ở HEAD nghĩa là HEAD có 0 vi
   phạm, vẫn phải so.
2. Gộp phép so mới vào `run()` đẩy nó lên complexity 14 — **và cổng vừa vá chặn
   đúng commit vá cổng**. Tách `_ratchet_phase()`, về 0 vi phạm.

**Giới hạn còn lại:** phép so theo-file chỉ thấy file ĐANG staged. Nợ chuyển từ
file A sang file B trong hai commit khác nhau vẫn lọt. `--all` ở pre-merge mới
bắt được chuyện đó — hai lớp bổ sung nhau, không thay nhau.

### 45. Bóc `agent/chat/` — chi phí thật của một lát cắt module (2026-08-27)

> STATUS: done — `server.py` 5.507 → 2.615 dòng. Con số quan trọng nhất KHÔNG
> phải số dòng dời, mà là **346 điểm vá trong bộ test**. Đọc §45.2 trước khi
> quyết định làm module thứ hai.

#### 45.1 Ranh giới được TÍNH, không đoán

Bao đóng bắc cầu từ 5 hạt giống (`chat`, `chat_stream`, `_run_agent`,
`ChatRequest`, `ChatResponse`): thêm dần mọi ký hiệu mà MỌI nơi gọi đều đã nằm
trong tập.

Lần một ra **58 ký hiệu** — SAI. Tôi chỉ coi hàm/lớp là nút của đồ thị, nên hàm
chỉ được một **gán mức module** tham chiếu (`_TOOL_HANDLERS` là một dict) không
bao giờ bị kéo vào. Tính cả gán mức module: **108 ký hiệu**, kiểm chéo 0 rò rỉ.

Kèm hai module dùng chung, tách vì CẢ HAI bên đều đọc — không tách thì chat phải
import ngược server, tức vòng:

| module | nội dung | vì sao dùng chung |
|---|---|---|
| `agent/features.py` | 26 khối dò `HAS_*` (121 ký hiệu) | server và chat cùng đọc cờ |
| `agent/http_errors.py` | `_error_response` | đo được **14** nơi ngoài chat gọi |

#### 45.2 CHI PHÍ THẬT NẰM Ở TEST — đây là con số cần nhớ

Dời 2.856 dòng mã là phần dễ. Phần đắt:

> **346 điểm vá trên 40 tên, trong 9 file test.**

`monkeypatch.setattr(server, "X")` chỉ ràng buộc lại tên trong namespace
`server`; thân hàm đã dời tra cứu global trong namespace `chat.api`, nên bản giả
KHÔNG ăn — test gọi LLM **thật**, mỗi lượt 6 phút, rồi đỏ. Đi qua tám vòng mới
hội tụ: **83/119 → 172/30 → 198/4 → 202/0**.

**Suy ra cho module tiếp theo:** ước lượng một lát cắt bằng "bao nhiêu dòng dời"
là ước lượng sai đại lượng. Đại lượng đúng là **bao nhiêu điểm vá của test bám
vào namespace cũ**. Đo nó TRƯỚC khi cam kết:

```
grep -rE 'setattr\(\s*server|patch\.object\(\s*server|patch\("server\.' agent/tests/
```

#### 45.3 Rào quét-mã-nguồn là loại nguy hiểm nhất

Sáu bài ghim cứng `agent/server.py` để soi mã chat. Chúng đỏ **không phải vì mã
sai** mà vì không còn soi vào đâu cả. Nếu chúng trả rỗng thay vì ném lỗi, chúng
đã **XANH trong khi mất tác dụng hoàn toàn** — và tôi commit tưởng mọi thứ ổn.
Lần thứ ba trong phiên gặp lớp lỗi này: *một rào bị tháo răng thì không kêu.*

`_handler_source` nay tìm ở cả hai cây và **ném lỗi rõ ràng** khi không thấy.

#### 45.4 Ba lỗi tôi tự gây trong lúc sửa

1. Gỡ 27 import "thừa" theo lời ruff → **110 bài đỏ**. Chúng không chết: chúng là
   BỀ MẶT VÁ của test. (Đã trả xong nợ này ngay sau đó — xem §45.6.)
2. Script "vá cả hai" chèn vào giữa lời gọi NHIỀU DÒNG → hỏng cú pháp 6 file.
3. Ba lần thay-thế-toàn-file rồi phải hoàn nguyên. Mẫu số chung: **thay theo
   CHUỖI KHỚP thay vì theo PHẠM VI HÀM**. Lần nào thu hẹp về đúng hàm mới sạch.

#### 45.5 Cú bóc phơi ra hai lỗ cổng — đã vá

- **R20.5** xét TỪNG FILE, nên một route **DỜI** (xoá ở A, thêm y hệt ở B trong
  cùng commit) bị đọc thành "đã xoá mà hợp đồng còn mô tả". Nay gộp diff cả
  commit rồi trừ phần giao = DỜI. Cùng lớp lỗi với §44.
- **R20.7** lấy `Path(...).stem`, nên `agent/chat/__init__.py` ra `__init__` và
  **MỌI gói Python đều trượt** dù có test đầy đủ. `agent/cases/` cũng dính. Nay
  lấy tên thư mục gói.

#### 45.6 Nợ đã trả ngay trong ngày

Khối shim 27 import trong `server.py` (tồn tại chỉ để test vá được) **đã gỡ**:
chuyển nốt 24 tham chiếu còn lại sang `chat.api`. Trong đó một ca không phép
thay-chuỗi nào chạm tới được — `getattr(server, limiter_name)` **tra cứu động
theo tên tham số**. Giới hạn của việc viết lại tĩnh, ghi lại để lần sau tìm
bằng tay.

#### 45.7 Đo trước hai ứng viên tiếp theo — thứ tự ưu tiên ĐẢO so với đề xuất ban đầu

Áp phép đo §45.2 (điểm vá của test vào namespace nguồn):

| ứng viên | dòng dời (bao đóng) | điểm vá test | phán quyết |
|---|---:|---:|---|
| `llmops/` (42 handler `/system` `/checkpoints` `/vectors` `/freshness` `/analytics`) | 47 ký hiệu / 425 dòng, 0 rò rỉ | **2 điểm / 1 file** | **rẻ nhất — lát cắt tiếp theo nếu cần** |
| `notifications.py` thành gói | đã một-file | **1 điểm** | gần miễn phí |
| `seo.py` thành gói | đã một-file | 48 / 3 file | vừa |
| `entities/` (public_api+admin) | chưa tính | 124+69 (cận trên) | đợi khi thật cần |
| `identity/` (auth…) | chưa tính | **164 / 11 file** (cận trên) | ĐẮT NHẤT — từng bị tôi xếp ĐẦU vì đếm route |

Bài học giữ nguyên: xếp ưu tiên theo SỐ ROUTE là sai thước đo — `identity/` nhiều
route nhất (73) nhưng đắt nhất; `llmops/` 28 route mà gần như miễn phí.

#### 45.8 Lát thứ hai — `llmops/` — xác nhận giá trị của phép đo trước, và lộ trục chi phí thứ hai

| | `chat/` (lát 1) | `llmops/` (lát 2) |
|---|---|---|
| dòng dời | 2.856 | 425 (47 ký hiệu, 0 rò rỉ) |
| điểm vá test phải sửa | **346, tám vòng** | **0** — 2 điểm đo trước không cần đụng |
| lỗi phát sinh | 110 bài đỏ, 6 file hỏng cú pháp | 6 tên thiếu import + 1 helper test |
| thời gian hội tụ | ~2 giờ | ~15 phút |

`server.py`: 5.507 → **2.159 dòng** (−61% trong một ngày, qua hai lát).

**Phép đo §45.2 đoán đúng trục nó đo — và bỏ sót một trục:** bốn rào QUÉT-MÃ-NGUỒN
(`TestEndpointAuthGuards`) đỏ vì handler dời chỗ, thứ phép đếm điểm-vá-namespace
không nhìn thấy. May là chúng kêu rõ ("Function must exist") thay vì im — đúng
chuẩn §45.3. Sửa bằng cách dạy `_server_src` hợp nhất CẢ BA cây route: chủ đích
của rào là "mọi endpoint nội bộ có chốt admin", bất kể handler sống ở file nào;
`function_source` cắt đúng MỘT hàm theo AST nên nối cây không làm yếu các bài
chỉ soi một hàm.

**Phép đo trước cho lát sau, nay đủ HAI trục:**

```
# trục 1 — điểm vá namespace:
grep -rE 'setattr\(\s*<mod>|patch\.object\(\s*<mod>|patch\("<mod>\.' agent/tests/
# trục 2 — rào quét-nguồn ghim đường dẫn file:
grep -rl '<mod>.py' agent/tests/ | xargs grep -l 'read_text\|getsource'
```

#### 45.9 BA MỨC ỒN ÀO của một rào bị dời chỗ — xếp theo độ nguy hiểm NGƯỢC

Lát `llmops/` làm hỏng ba thứ. Cả ba đều là "rào mất răng", nhưng chúng kêu to
nhỏ khác nhau — và cái ÊM nhất mới nguy hiểm nhất:

| # | hỏng gì | biểu hiện | tìm ra nhờ |
|---|---|---|---|
| 1 | 5 rào quét-nguồn ghim `server.py` | **ĐỎ rõ** — "Function must exist" | suite báo ngay |
| 2 | 1 đích vá `semantic_cache_invalidate` | **ĐỎ**, nhưng nấp trong output tôi tự cắt bằng `\| tail -4` | chạy lại, giữ nguyên output |
| 3 | 7 test model `try/except → pytest.skip` | **HOÀN TOÀN IM** — chỉ là `skipped 510 → 517` | hỏi "vì sao skipped tăng 7?" |

Cái thứ ba không đỏ, không cảnh báo, chỉ một con số nhích lên trong dòng tổng
kết mà hầu như ai cũng lướt qua. Bảy bài kiểm định Pydantic model đã TẮT LẶNG
LẼ; nếu không truy con số đó, chúng đã đi vào commit ở trạng thái tắt.

**Đã dựng rào:** `agent/tests/test_import_skip_traps.py` import THẲNG (không
bọc) 6 ký hiệu đang bị `try/except → skip` bao. Ký hiệu nào dời chỗ thì nó ĐỎ
ngay kèm tên. Nó phủ sẵn `admin.EntityCreate` và `admin._sanitize` — `admin.py`
là nguồn của BA module trong bản đồ (`entities/` `moderation/` `siteops/`), nên
bẫy đã có người canh trước khi ai đó tách nó.

**Chưa làm, ghi lại:** quét thấy **45 chỗ / 24 file** dùng `except → pass/return`
— biến thể còn êm hơn skip. Phần lớn có thể là dọn dẹp trong teardown chứ không
nuốt logic kiểm định, nhưng chưa đọc từng chỗ nên KHÔNG kết luận.

**Hai lỗi ở KÊNH QUAN SÁT, không phải ở mã** — cùng họ "khớp chuỗi lỏng thì nói
dối": `\| tail -4` cắt mất danh sách FAILED (phải chạy lại 15 phút để nhìn thứ
đáng lẽ đã có); chốt chờ `grep -qE "passed|failed"` khớp nhầm dòng
`All checks passed!` của ruff nên báo "xong" khi pytest chưa chạy. Từ nay lệnh
đo dài GHI NGUYÊN VẸN ra file, cắt sau; chốt chờ khớp đúng hình dạng sự kiện
(`[0-9]+ passed`).

### 46. Gói miền ENTITY hoàn tất (bước 1a→2b) — và SỰ CỐ B1 đầu tiên của chương trình module (2026-08-28)

> STATUS: done (bước 1–2) — bốn commit `c93c38e7` `30edeb92` `3f3a3ede` `bec918b8`.
> Gói `agent/entities/` nay đủ HAI MẶT theo khuôn `cases/`: `api.py` (công khai)
> + `admin_api.py` (quản trị). Còn lại của kế hoạch: `community/` và `identity/`
> — CẢ HAI trong vùng mù B3, đọc §46.4 trước khi động.

#### 46.1 Số liệu

| file | trước | sau | phần dời đi đâu |
|---|---:|---:|---|
| `public_api.py` | 4.989 | 3.647 | `entities/api.py` (1.510) + `entity_read.py` (~210) |
| `admin.py` | 5.911 | 4.535 | `entities/admin_api.py` (~1.700) + `admin_common.py` (68) |
| `server.py` (hai lát trước) | 5.507 | 2.159 | `chat/` + `llmops/` + `features.py` |

433 route giữ nguyên, 0 trùng path+method. Route entity-admin mount qua
`admin.router.include_router(...)` và ĐO ĐƯỢC kế thừa `[require_admin,
require_csrf]` từ cha — an ninh kiểm bằng `dependant.dependencies`, không tin
trí nhớ API.

#### 46.2 SỰ CỐ B1 — 8 hàng test ghi vào DB THẬT, đã xử

Trong khung cửa sổ giữa "cắt closure" và "vá fixture cách ly", test mutation
chạy với fixture vá `admin.db` trong khi handler đã dời đọc
`entities.admin_api.db` — bản vá không ăn, handler chạm DB thật: **8 entity
test + 3 hàng audit** ghi vào `agent/data/vinhlong360.db` (tài sản không tái
tạo, §2 B1). Xử đúng trình tự: backup → xoá phẫu thuật đúng 11 hàng → về đúng
1.746 entity.

**Vì sao khó tìm:** triệu chứng (44 errors dây chuyền) CHỈ hiện ở lượt đầy đủ —
cần một test khác hâm nóng knowledge từ đĩa thì rác mới lộ. Hai lần bisect đầu
VÔ HIỆU: `-k` lọc nhầm cả file đích; chạy hai tiến trình thì ô nhiễm in-memory
không lan sang nhau. Phải bisect bằng node-id, ~10 vòng.

**Một bản-vá-sai đã viết rồi GỠ:** khối copy-container kèm bình luận quy kết
"`_sync_kb` mutate tại chỗ". Đọc mã: `knowledge.reload()` REBIND chứ không
mutate — fixture gốc đúng thiết kế. Giữ bản vá đó là gieo hiểu lầm cho người
sau; gỡ trước khi tìm ra nguyên nhân thật.

#### 46.3 BỐN trục chi phí của một lát cắt (trục 4 mới, giá đắt nhất)

| trục | biểu hiện | lộ ra ở đâu |
|---|---|---|
| 1. vá namespace hàm | test gọi hàm thật thay bản giả | lượt nhắm |
| 2. rào ghim đường dẫn | "không tìm thấy hàm X" — kêu rõ | lượt nhắm |
| 3. vá thuộc tính module (settings/cờ) | 404 ở route NGOÀI miền đang bóc | chỉ lượt đầy đủ |
| **4. fixture CÁCH LY vá namespace** | **không đỏ, không skip — GHI NHẦM CHỖ** | **chỉ khi soi DỮ LIỆU** |

Trục 4 là lý do checklist lát cắt từ nay có thêm một dòng bắt buộc: **grep
`setattr(<mod>, "db"` trong fixture TRƯỚC khi cắt, và `SELECT count(*)` DB thật
TRƯỚC/SAU lượt đo đầu tiên.**

#### 46.4 Trước khi động community/ hoặc identity/

- `social.py` và `auth.py` đều trong danh sách vùng mù B3 (CLAUDE.md §2) —
  "phải có test bao phủ TRƯỚC khi sửa". Số phủ từ lượt đo một phần KHÔNG dùng
  được; cần đo đầy đủ.
- Giá đo sẵn: `identity/` 164 điểm vá + 147 thuộc-tính (đắt nhất);
  `community/` 39 + 26.
- Cả hai chưa có nhu cầu ép buộc. Khuyến nghị của bản đồ giữ nguyên: **đo xem
  còn đau không trước khi cắt tiếp.**

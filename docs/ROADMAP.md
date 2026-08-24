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

- **62 giá trị dự phòng** `var(--token, rgba(...))` — bỏ đi là làm yếu mã.
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
| Dấu tiếng Việt | `Range.getClientRects()` so hộp glyph với hộp dòng | Tỉ lệ mực Be Vietnam Pro = **1,33**; mọi `line-height` < 1,33 là tràn |
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

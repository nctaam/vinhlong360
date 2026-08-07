# CLAUDE.md — Hiến pháp thực thi cho dự án vinhlong360

> File này được nạp mỗi phiên. Nó là **giao thức bắt buộc** khi làm việc trên dự án.
> Cập nhật lớn 2026-07-07 (đợt "truth-sync"): đồng bộ với 3 bước ngoặt — sáp nhập 1 tỉnh, định vị Vĩnh-Long-đặc-thù, ảnh AI-only. Tài liệu cũ mâu thuẫn với file này → file này thắng.

---

## 0. Bối cảnh 1 dòng

MXH du lịch/OCOP/cộng đồng cho **tỉnh Vĩnh Long MỚI** (sáp nhập Vĩnh Long + Bến Tre + Trà Vinh từ 07/2025; hành chính 2 cấp: 1 tỉnh → 124 xã/phường = 35 phường + 89 xã, KHÔNG còn cấp huyện, KHÔNG còn tỉnh Bến Tre/Trà Vinh). Cảnh báo khi đối chiếu: danh mục GSO / file `.xls` có thể vẫn ghi 19 phường + 105 xã vì chưa cập nhật đợt 16 xã lên phường — lấy `.xls` làm nguồn MÃ hành chính, KHÔNG lấy làm nguồn CẤP. Solo dev, vibe code, <10k user, **ngân sách <1.000.000đ/tháng**, web-first, **không tính năng nặng** (không AR/audio-guide/native app). Backend FastAPI (`agent/`) + frontend Nuxt 4 SSR (`web-nuxt/`). Kiến trúc & lý do: `docs/architecture-decisions.md`; bản đồ tài liệu còn hiệu lực: `docs/README.md`.

## 1. Các quyết định đã chốt (KHÔNG tự ý đổi)

1. **DB là nguồn sự thật duy nhất** cho entity/relationship/itinerary + user/UGC. Chat **nạp toàn bộ vào RAM lúc khởi động**. `web/data.json` là bản export/backup + nguồn build prerender — **đã phân kỳ với DB** (cơ chế export tự động DB→data.json chưa được tái lập; chỉ có admin POST /export tải tay). KHÔNG BAO GIỜ dùng data.json cũ ghi đè DB prod.
2. **Một frontend = Nuxt + hybrid rendering.** `web-astro/` và JS/HTML legacy trong `web/` **đã xoá xong** — đừng tìm/đừng khôi phục.
3. **UGC/auth (users/posts/comments/...) = Postgres-only** (dev/prod parity). SQLite chỉ phục vụ tầng tri thức (entity/rel/itinerary); endpoint UGC trên SQLite trả **503** rõ ràng. Dev cộng đồng: `docker compose up postgres`. KHÔNG port UGC sang SQLite.
4. **CHỈ GIỚI THIỆU — KHÔNG đặt hàng/booking/thanh toán on-site, KHÔNG sàn bên-thứ-ba.** Giữ ở "tầng nhẹ" pháp lý (không kích đăng ký TMĐT NĐ52/85). CTA chỉ là liên hệ Zalo/điện thoại/hỏi-giá (KHÔNG form chốt đơn giá+SL+xác nhận). Doanh thu: premium/featured listing + hợp đồng B2G + quảng cáo (KHÔNG hoa hồng booking, KHÔNG bán tour/vé/pass — kể cả khi tài liệu nghiên cứu cũ khuyến nghị). Cũng KHÔNG đăng lại nguyên văn tin báo (crawler chỉ trích-đoạn+link).
5. **ẢNH: CHỈ AI-generated** qua `scripts/gen_image.py` (endpoint cx/gpt-5.5-image, key từ env `IMAGE_API_KEY`) — chốt của chủ dự án, override mọi hướng dẫn cũ. **KHÔNG Wikimedia, KHÔNG stock (Pexels/Unsplash), KHÔNG ảnh UGC, KHÔNG cào ảnh gov/báo.** Ảnh AI không được giả làm ảnh thật: giữ nhãn minh hoạ (`dc-nophoto-note`) khi entity chưa có ảnh thật.
6. **ĐỊNH VỊ: site VỀ VĨNH LONG (tỉnh mới) — không phải "miền Tây/ĐBSCL" generic.** Dẹp filler "miền Tây", "sông nước hữu tình"; thay bằng đặc thù bản địa (tên riêng, số liệu, mùa vụ, chi tiết first-hand). Chống bị-đọc-như-AI + chống Google spam bằng chất lượng thật + E-E-A-T, KHÔNG né detector. Trong nội dung: gọi vùng đất theo tỉnh MỚI; "tỉnh Bến Tre/Trà Vinh" chỉ xuất hiện trong văn cảnh lịch sử có chữ "cũ/trước 7-2025".
7. **TRUST không khai khống:** byline cấp tổ chức "Ban biên tập vinhlong360" (không tên cá nhân). Nguồn kiểm-chứng-thực-địa DUY NHẤT là `attributes.verifiedAt` (hiện ~0 entity có) — `entity.verified` chỉ là cờ publish. **CẤM mọi claim "đã xác minh/kiểm chứng" trong sản phẩm, pitch, tài liệu đối ngoại** khi verifiedAt chưa phủ. Noindex toàn site đang BẬT chủ động (`NUXT_PUBLIC_SITE_NOINDEX`); chỉ mở khi chủ dự án quyết.

## 2. Bất biến — VI PHẠM = DỪNG NGAY (không bao giờ phá)

- **B1. Snapshot trước mọi thao tác dữ liệu.** Chạy `python scripts/backup_data.py` trước bất kỳ script ETL/migrate/sửa-hàng-loạt nào. **DB (SQLite local + Postgres prod) là tài sản không tái tạo được**; data.json là export đã phân kỳ — backup cả hai, và không dùng bản này đè bản kia khi chưa đối chiếu.
- **B2. Additive-first.** Thêm đường mới + verify xong mới xoá đường cũ. (Shim `coords`,`from`/`to` vẫn còn trong code — gỡ qua task riêng có verify, xem ROADMAP 7.5.)
- **B3. Test trước khi refactor vùng mù.** Module ít test (`database.py`, `server.py` chat handler, `social.py`, `auth.py`, ETL) **phải có test bao phủ TRƯỚC khi sửa**.
- **B4. Một thay đổi schema = một test.**
- **B5. Mỗi task để lại hệ thống chạy được.** Không big-bang. Commit nhỏ sau mỗi task.
- **B6. Không re-host nội dung có bản quyền** cào từ gov/báo/mytour — chỉ tiêu đề + trích đoạn + link gốc. Ảnh: theo chốt §1.5 (CHỈ AI-gen).
- **B7. Không bao giờ chạy lệnh phá dữ liệu** (`database.py --replace`, `deploy.sh --replace`, `/admin/data-quality/apply`, `/reload`) khi không có chỉ đạo trực tiếp của chủ dự án cho đúng việc đó, và luôn backup trước. Đặc biệt: `--replace` từ data.json sẽ **đè mất chỉnh sửa AdminCP write-through trên prod PG**.
- **B8. Tôn trọng ngân sách.** Không thêm dịch vụ trả phí (kể cả Sentry cloud, container-stack, monitoring SaaS — đã có giải pháp tự xây). Mặc định free-tier. **Ngoại lệ DUY NHẤT cho "vòng lặp LLM nền"** (chủ duyệt 2026-06-14): (a) opt-in `AUTONOMOUS_AGENT_ENABLED=true` (OFF mặc định), (b) cap cứng/ngày qua `agent/autonomous_budget.py` (`AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY`, mặc định 20), (c) kill-switch tức thì. Vòng lặp CŨ (`SCHEDULER_ENABLE_AUTONOMOUS_TASKS`) VẪN tắt mặc định. KHÔNG nới nếu không có chủ dự án.

## 3. Nguồn việc & giao thức thực thi

1. **Thứ bậc nguồn việc:** (1) chỉ đạo trực tiếp của chủ dự án trong phiên → (2) spec/plan đã duyệt trong `docs/superpowers/` (flow brainstorm→spec→plan→execute cho việc lớn) → (3) `docs/ROADMAP.md` = sổ track dài hạn + backlog (KHÔNG còn là danh sách tuần tự bắt buộc; nhiều giai đoạn đã xong). Tài liệu trong `docs/archive/` là lịch sử — **KHÔNG làm theo**.
2. Mỗi task: làm → chạy **lệnh verify** → đạt tiêu chí nghiệm thu mới commit (1 việc/commit, message rõ).
3. Nếu một test **đang xanh bỗng đỏ** mà chưa rõ nguyên nhân → **DỪNG, báo người** (đừng "sửa cho xanh" bằng cách yếu assertion). Baseline hiện có **các fail đã biết** ghi ở ROADMAP mục "Backlog test-debt" — chỉ dừng khi xuất hiện fail MỚI ngoài danh sách đó.
4. Mỗi phiên bắt đầu: `python -m pytest -q` để biết baseline, đối chiếu danh sách fail-đã-biết.
5. Giữ phạm vi: việc đáng làm ngoài phạm vi → ghi "Backlog phát sinh" cuối ROADMAP.md, KHÔNG tự làm.
6. **Quy tắc tài liệu:** tài liệu chỉ đạo (plan/blueprint/guide) phải có header `> STATUS:` (active / done / obsolete / superseded-by X). Gặp doc không STATUS và có mùi lỗi thời (nhắc huyện, 3 tỉnh, Wikimedia, booking...) → coi là nghi vấn, đối chiếu file này trước khi làm theo.
7. **Tiêu chuẩn có răng (từ 2026-07-07):** bộ chuẩn sống ở `docs/standards/` (INDEX = bảng tổng rule). Pre-commit hook chặn lớp hard + ratchet (nợ chuẩn không được TĂNG — baseline.json committed); `pre_merge_check` chặn thêm scorecard-tụt-điểm + plan-result thiếu. KHÔNG skip lớp hard; SKIP soft cần `SKIP_CHECKS` + `SKIP_REASON` (tự ghi 90-exceptions-log.md). Thao tác diện-rộng có chủ đích → cập nhật baseline TRONG CÙNG COMMIT kèm giải trình.

## 4. ĐIỀU KIỆN DỪNG — phải hỏi người, KHÔNG tự quyết

- Bất cứ việc cần **pháp nhân / luật sư / đăng ký NĐ147 / hồ sơ pháp lý** (Track-H).
- **`git push` / tạo remote** (cần URL người cấp), **rotate/đặt giá trị secret thật** (lưu ý bẫy: rotate khi 2FA bật mà chưa đặt `TOTP_ENC_KEY` = khoá vĩnh viễn user 2FA).
- **Xoá file/thư mục/dữ liệu** không có chỉ đạo rõ.
- **Thao tác phát sinh chi phí** (dịch vụ trả phí, tier trả phí).
- **Deploy lên prod** — chỉ khi chủ dự án yêu cầu; khi được lệnh thì theo runbook trong `docs/HANDOFF.md`.
- Khi **tiêu chí nghiệm thu không thể đạt** sau 2 lần thử, hoặc yêu cầu mâu thuẫn với bất biến §2.
- **Gửi/đăng tài liệu đối ngoại** (pitch B2G, bài PR) — nội dung phải qua chủ dự án, đặc biệt mọi claim số liệu/xác-minh (§1.7).

## 5. Lệnh hay dùng (môi trường: Windows, PowerShell)

```
# Backend smoke (không gọi LLM, không build index nặng)
$env:BUILD_SEARCH_INDEXES='false'; $env:BACKGROUND_INDEX_BUILD='false'; $env:SCHEDULER_ENABLED='false'; python agent/server.py
python -m pytest -q                      # test (đối chiếu fail-đã-biết ở ROADMAP)
python scripts/validate_data.py          # kiểm dữ liệu
python scripts/backup_data.py            # BẮT BUỘC trước thao tác dữ liệu
python scripts/install_hooks.py          # cài pre-commit tiêu chuẩn (1 lần/máy — docs/standards/)
python scripts/scorecard.py              # đồng hồ world-class (điểm/chiều; không được tụt)
cd web-nuxt; npm run dev                 # dev frontend (cổng 3000)
cd web-nuxt; npm run build               # build frontend
python scripts/gen_image.py --prompt "..." --out web-nuxt/public/img/x.webp   # ảnh AI (cần IMAGE_API_KEY)
```

### 5b. BẪY: "local xanh" KHÔNG chứng minh CI xanh (học đắt 2026-08-06)

- `pytest.ini` `addopts` loại **4 marker** khỏi lệnh mặc định: `slow`, `integration`,
  `entity_status_postgres`, `subprocess_heavy`. Chạy `python -m pytest -q` thấy xanh mà cả nhóm
  launch-safety lẫn integration **chưa hề chạy**. Trước khi commit vào `scripts/ops/`, `agent/database.py`
  hay `tests/launch_safety/`: `python -m pytest tests/launch_safety/ -m "" -n0`.
- **Máy dev là Windows, đích là Linux.** Đợt 2026-08-06 có 7 bug sản phẩm CHỈ hỏng trên Linux: thiếu
  bit exec, `env --argv0` (đòi coreutils ≥ 9.1), `StartsWith("$root\")`, ghim cứng `powershell` thay vì
  `pwsh`, `os.replace` không bao giờ nằm trong `os.supports_dir_fd`, inode tái dụng đánh lừa `samestat`,
  `verified` bool vs cột INTEGER. Không cái nào lộ được ở local.
- Với lớp lỗi đó: **ĐO TRƯỚC, VÁ SAU** — thêm step tạm `continue-on-error: true` vào `ci.yml` in ra sự
  thật của runner, rồi gỡ. Vá theo suy luận sai 2/2 lần; đo trước trúng 4/4 lần.
- `concurrency: cancel-in-progress: true` → push mới **huỷ** vòng đang chạy và **mất log** step đo. Chờ
  vòng đo xong rồi hãy push tiếp.
- Dữ liệu local KHÔNG đối chiếu được với prod: `agent/knowledge.db` rỗng (0 entity, chưa có cột
  `status`), `web/data.json` có 1746 entity nhưng `status=None` toàn bộ. Đừng suy ra hành vi prod từ chúng.

### 5c. BẪY: worktree dùng chung + công cụ verify nói dối (học đắt 2026-08-07)

- **HAI WORKFLOW KHÔNG DÙNG CHUNG MỘT WORKTREE.** Một agent chạy `git stash push -u` để lấy baseline sạch,
  cuốn theo việc đang dở của workflow khác — **6 file tracked (68.663 dòng, phần lớn là fixture) + 4 file
  untracked (883 dòng)**; khôi phục được nhưng suýt mất trắng. Ràng buộc "đừng đụng file X" KHÔNG đủ — `stash`/`checkout .`/`restore .`/`reset`/`clean`/`add -A`
  tác động TOÀN CÂY. Agent phụ trong worktree dùng chung: git chỉ được **ĐỌC** (`log`, `show`, `diff <file>`,
  `status`, `for-each-ref`, `merge-base`, `rev-list`, `worktree list`).
- **DB mỗi worktree là một bản KHÁC NHAU.** `C:\Code\vinhlong360\agent\data\vinhlong360.db` = 1751 entity /
  49 dòng `entity_event_details` (34.8 MB); `C:\Code\vinhlong360\.worktrees\tri-region-color\agent\data\vinhlong360.db`
  = 1746 / 67 (7.4 MB). Chạy script phân tích nhầm worktree ra bộ số khác hẳn → luôn dùng **đường dẫn tuyệt đối**.
- **`scripts/validate_data.py` đọc `web/data.json`, KHÔNG đọc DB** (`scripts/validate_data.py:16`). Sửa DB xong
  chạy nó ra "0 critical" là kết luận RỖNG — nó không nói gì về DB.
- **Sửa `entity_event_details` ở LOCAL thì không hiện ra được.** `reads_enabled()` trả `settings.ENTITY_DETAILS_TABLES`
  (`agent/entity_details.py:306`), mặc định `False` (`agent/config.py:39`), local không có file `.env` → `agent/database.py:1970`
  bỏ qua `rebuild_attributes`, attributes vẫn lấy từ cột JSON cũ. Sửa DB xong mà nhìn không thấy gì đổi là
  vì vậy, **không phải do ai lười**. Bật được: `$env:ENTITY_DETAILS_TABLES='true'` (pydantic-settings vẫn đọc
  biến môi trường OS dù thiếu `.env` — `agent/config.py:139-141`), nhưng phải đặt TƯỜNG MINH, mặc định là tắt.
- **NGÀY CỦA MỘT SỰ KIỆN NẰM Ở SÁU Ô**, không phải một: `attributes.lunar_date`, `attributes.date_start`,
  `attributes.date_end`, `entities.summary`, `entities.description`, `entities.season(.text/.months/.peak)`.
  Phủ từng ô (đo trên DB worktree tri-region-color, `type='event'`): `date_start` 67/67 · `season` 67/67 ·
  `date_end` 57/67 · `description` 44/67 · `lunar_date` 36/67 · `summary` 33/67 → **49/67 event có ≥4 ô cùng
  mang thông tin ngày** (16 event có 3 ô, 2 event có 2 ô). Riêng `le-hoi.vue` render 4/6 ô — `lunar_date`
  (:86,:99,:216), `summary` (:211), `date_start` (:226,:343), `date_end` (:348); `season` không dùng ở file này,
  `description` chỉ vào SEO meta (:562,:564,:601). Sửa một ô
  thì năm ô kia thành nói ngược → mâu thuẫn **CÔNG KHAI** tệ hơn trạng thái lệch ban đầu; đã phải hoàn nguyên DB một
  lần vì đúng bẫy này. Sửa thì sửa cả sáu, hoặc không sửa. Bảng quyết định:
  `docs/2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md`.
- **Checker chuẩn là bộ SO CHUỖI — nó bắt luôn cái test đang cấm điều đó.** `no_tailwind` = regex `(?i)tailwind`
  trên `web-nuxt/**`, exclude chỉ có `node_modules` + `package-lock.json`, KHÔNG loại `tests`
  (`scripts/checks/check_banned_claims.py:38-46`) → test chứa chữ "tailwind" để assert *không có* Tailwind làm R30.1 đỏ.
  `banned_claims` (`:20-28`) cùng lớp lỗi: bắt cả câu phủ định. Lớp hard không skip được → **ghép chuỗi từ mảnh** trong test.
- **R20.7 ghép test–module bằng TÊN FILE hoặc AST `import`** (`scripts/checks/check_test_pairing.py:66-82`).
  `pytest.importorskip("x")` là lời gọi lúc CHẠY, AST không thấy → bị tính là "sửa `agent/x.py` mà không có test".
  Cách vòng hợp lệ: thêm import cấp module bọc `try/except`.

## 6. Quy ước

- File reference dạng `path:line`. Commit message: prefix ngữ nghĩa (`feat:`/`fix:`/`refactor:`/`docs:`...; `<GĐx.y>` chỉ khi làm đúng task ROADMAP).
- Không skip hook, không `--no-verify`. Không sửa file ngoài phạm vi task.
- Mọi nghi ngờ → đọc `docs/README.md` (bản đồ tài liệu) + `docs/architecture-decisions.md`, không phỏng đoán.

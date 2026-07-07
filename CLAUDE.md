# CLAUDE.md — Hiến pháp thực thi cho dự án vinhlong360

> File này được nạp mỗi phiên. Nó là **giao thức bắt buộc** khi làm việc trên dự án.
> Cập nhật lớn 2026-07-07 (đợt "truth-sync"): đồng bộ với 3 bước ngoặt — sáp nhập 1 tỉnh, định vị Vĩnh-Long-đặc-thù, ảnh AI-only. Tài liệu cũ mâu thuẫn với file này → file này thắng.

---

## 0. Bối cảnh 1 dòng

MXH du lịch/OCOP/cộng đồng cho **tỉnh Vĩnh Long MỚI** (sáp nhập Vĩnh Long + Bến Tre + Trà Vinh từ 07/2025; hành chính 2 cấp: 1 tỉnh → 124 xã/phường = 35 phường + 89 xã, KHÔNG còn cấp huyện, KHÔNG còn tỉnh Bến Tre/Trà Vinh). Solo dev, vibe code, <10k user, **ngân sách <1.000.000đ/tháng**, web-first, **không tính năng nặng** (không AR/audio-guide/native app). Backend FastAPI (`agent/`) + frontend Nuxt 4 SSR (`web-nuxt/`). Kiến trúc & lý do: `docs/architecture-decisions.md`; bản đồ tài liệu còn hiệu lực: `docs/README.md`.

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

## 6. Quy ước

- File reference dạng `path:line`. Commit message: prefix ngữ nghĩa (`feat:`/`fix:`/`refactor:`/`docs:`...; `<GĐx.y>` chỉ khi làm đúng task ROADMAP).
- Không skip hook, không `--no-verify`. Không sửa file ngoài phạm vi task.
- Mọi nghi ngờ → đọc `docs/README.md` (bản đồ tài liệu) + `docs/architecture-decisions.md`, không phỏng đoán.

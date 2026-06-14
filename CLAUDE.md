# CLAUDE.md — Hiến pháp thực thi cho dự án vinhlong360

> File này được nạp mỗi phiên. Nó là **giao thức bắt buộc** khi tự động hoàn thiện dự án.
> Nguồn sự thật của *việc cần làm* là **`docs/ROADMAP.md`**. File này là *cách làm để không đi sai*.

---

## 0. Bối cảnh 1 dòng

MXH du lịch/OCOP/cộng đồng cho Vĩnh Long mới (VL+Bến Tre+Trà Vinh). Solo dev, vibe code, <10k user, **ngân sách <1.000.000đ/tháng**, web-first, **không tính năng nặng**. Backend FastAPI (`agent/`) + frontend Nuxt 4 SSR (`web-nuxt/`). Kiến trúc & lý do: `docs/kien-truc-va-lo-trinh.md`, `docs/architecture-decisions.md`, `docs/stabilization-plan.md`.

## 1. Hai quyết định kiến trúc đã chốt (KHÔNG tự ý đổi)

1. **DB là nguồn sự thật duy nhất** cho entity/relationship/itinerary + user/UGC. Chat **nạp toàn bộ vào RAM lúc khởi động** (giữ tốc độ); `web/data.json` chỉ còn là **export/backup + nguồn build prerender**.
2. **Một frontend = Nuxt + hybrid rendering**. Xoá `web-astro`, bỏ JS/HTML legacy trong `web/`.
3. **UGC/auth (users/posts/comments/...) = Postgres-only** (dev/prod parity). SQLite chỉ phục vụ tầng tri thức (entity/rel/itinerary); endpoint UGC trên SQLite trả **503** rõ ràng. Dev cộng đồng: `docker compose up postgres`. KHÔNG port UGC sang SQLite (tránh nợ 2 phương ngữ SQL).
4. **CHỈ GIỚI THIỆU — KHÔNG đặt hàng/booking/thanh toán on-site, KHÔNG sàn bên-thứ-ba.** Giữ ở "tầng nhẹ" pháp lý (không kích đăng ký TMĐT NĐ52/85). CTA chỉ là liên hệ Zalo/điện thoại/hỏi-giá (KHÔNG form chốt đơn giá+SL+xác nhận). Doanh thu: premium/featured listing + hợp đồng B2G + quảng cáo (KHÔNG hoa hồng booking). Cũng KHÔNG đăng lại nguyên văn tin báo (crawler chỉ trích-đoạn+link — tránh giấy phép trang TTĐT tổng hợp).

## 2. Bất biến — VI PHẠM = DỪNG NGAY (không bao giờ phá)

- **B1. Snapshot trước mọi thao tác dữ liệu.** Chạy `python scripts/backup_data.py` trước bất kỳ script ETL/migrate/normalize nào. `web/data.json` + DB **không tái tạo được**.
- **B2. Additive-first.** Thêm đường mới + verify xong mới xoá đường cũ. Giữ shim tương thích (`coords`,`from`/`to`) tới khi đã bỏ frontend legacy.
- **B3. Test trước khi refactor vùng mù.** Module 0% test (`database.py`, `server.py` chat handler, `social.py`, `auth.py`, ETL) **phải có test bao phủ TRƯỚC khi sửa**.
- **B4. Một thay đổi schema = một test.** Không merge thay đổi schema nếu thiếu test.
- **B5. Mỗi task để lại hệ thống chạy được.** Không big-bang. Commit nhỏ sau mỗi task.
- **B6. Không re-host nội dung/ảnh có bản quyền** cào từ gov/báo/mytour. Chỉ lưu tiêu đề + trích đoạn + link gốc; ảnh chỉ dùng nguồn cấp phép (Wikimedia/UGC/Pexels-Unsplash theo điều khoản).
- **B7. Không bao giờ chạy lệnh phá dữ liệu** (`database.py --replace`, `/admin/data-quality/apply`, `/reload`) khi chưa tới đúng task cho phép trong roadmap, và luôn backup trước.
- **B8. Tôn trọng ngân sách.** Không thêm dịch vụ trả phí. Mặc định free-tier. **Ngoại lệ DUY NHẤT cho "vòng lặp LLM nền"** (chủ dự án duyệt 2026-06-14, kiểm soát chặt): agent tự động gọi LLM CHỈ khi đủ 3 điều kiện — (a) opt-in `AUTONOMOUS_AGENT_ENABLED=true` (OFF mặc định), (b) cap cứng/ngày qua `agent/autonomous_budget.py` (`AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY`, mặc định 20; vượt cap = bỏ qua), (c) kill-switch tức thì (đổi flag = tắt). Vòng lặp LLM nền CŨ (auto-learn/discovery/promotion qua `SCHEDULER_ENABLE_AUTONOMOUS_TASKS`) VẪN tắt mặc định. KHÔNG nới các điều kiện này nếu không có chủ dự án.

## 3. Giao thức thực thi tự động (chống trôi)

1. **Đọc `docs/ROADMAP.md`. Làm đúng thứ tự task.** Không nhảy cóc, không tự thêm việc ngoài roadmap.
2. Mỗi task: làm → chạy **lệnh verify** ghi trong task → chỉ khi **tiêu chí nghiệm thu** đạt mới tick `[x]` và commit (`git commit` 1 task/commit, message rõ).
3. **Cổng Definition-of-Done (DoD) cuối mỗi Giai đoạn**: phải pass toàn bộ checklist DoD **mới được sang giai đoạn sau**. Không pass → sửa, không đi tiếp.
4. Nếu một test **đang xanh bỗng đỏ** mà chưa rõ nguyên nhân → **DỪNG, báo người** (đừng "sửa cho xanh" bằng cách yếu đi assertion).
5. Mỗi phiên bắt đầu: chạy `python -m pytest -q` (live-path subset) để biết baseline xanh, rồi mới làm tiếp.
6. Giữ phạm vi: nếu phát hiện việc đáng làm ngoài roadmap → **ghi vào mục "Backlog phát sinh" cuối ROADMAP.md**, KHÔNG tự làm.

## 4. ĐIỀU KIỆN DỪNG — phải hỏi người, KHÔNG tự quyết

- Bất cứ việc cần **pháp nhân / luật sư / đăng ký NĐ147 / hồ sơ pháp lý** (Track-H trong roadmap).
- **`git push` / tạo remote** (cần URL người cấp), **rotate/đặt giá trị secret thật**.
- **Xoá file/thư mục/dữ liệu** không do roadmap chỉ định rõ; xoá `web-astro`/`web/` legacy chỉ làm ở đúng task và sau khi verify.
- **Thêm dịch vụ trả phí** hoặc thao tác phát sinh chi phí (mua domain, bật tier trả phí, deploy public).
- **Deploy lên môi trường công khai.**
- Khi **tiêu chí nghiệm thu không thể đạt** sau 2 lần thử, hoặc yêu cầu mâu thuẫn với bất biến §2.

## 5. Lệnh hay dùng (môi trường: Windows, PowerShell)

```
# Backend smoke (không gọi LLM, không build index nặng)
$env:BUILD_SEARCH_INDEXES='false'; $env:BACKGROUND_INDEX_BUILD='false'; $env:SCHEDULER_ENABLED='false'; python agent/server.py
python -m pytest -q                      # test
python scripts/validate_data.py          # kiểm dữ liệu
python scripts/backup_data.py            # BẮT BUỘC trước thao tác dữ liệu (tạo ở GĐ0)
cd web-nuxt; npm run build               # build frontend
```

## 6. Quy ước

- File reference dạng `path:line`. Commit message: `<GĐx.y> <mô tả>`. 
- Không skip hook, không `--no-verify`. Không sửa file ngoài phạm vi task.
- Mọi nghi ngờ → đọc `docs/ROADMAP.md` + `docs/architecture-decisions.md`, không phỏng đoán.

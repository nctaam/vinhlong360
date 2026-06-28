# SESSION SCOPE: Quality, Tests & Docs — branch `session-content`

> **Session song song 3/3.** CHỈ sửa `docs/`, `scripts/`, `tests/`, và file config gốc.
> KHÔNG sửa `agent/` hay `web-nuxt/`. Sau khi xong, session gốc merge + deploy.

---

## 0. Bối cảnh

MXH du lịch/OCOP/cộng đồng cho Vĩnh Long mới (VL+BT+TV). Solo dev, budget <1tr/th.
Backend FastAPI (`agent/`) + Nuxt 4 SSR (`web-nuxt/`).
Kiến trúc: `docs/architecture-decisions.md`, `docs/stabilization-plan.md`.

## 1. Giới hạn file (TUYỆT ĐỐI — vi phạm = hỏng merge)

**ĐƯỢC sửa:**
- `docs/**`
- `scripts/**`
- `tests/**` (thư mục `tests/` gốc, KHÔNG PHẢI `agent/tests/`)
- `.github/**` (CI workflows)
- `docker-compose.yml`, `docker-compose.prod.yml`
- `Dockerfile`
- `.env.example` (chỉ thêm comment/doc, KHÔNG đổi giá trị)
- `web-nuxt/nuxt.config.ts` (CHỈ phần SEO/sitemap/meta, KHÔNG đổi route rules/proxy)

**KHÔNG ĐƯỢC sửa:**
- `agent/**` — session backend phụ trách
- `web-nuxt/pages/**`, `web-nuxt/components/**`, `web-nuxt/composables/**`, `web-nuxt/layouts/**`, `web-nuxt/assets/**` — session frontend phụ trách
- `web/data.json` — DỮ LIỆU GỐC, nếu cần → backup trước (§B1)

## 2. Bất biến

- **B1.** `python scripts/backup_data.py` trước MỌI thao tác dữ liệu
- **B5.** Mỗi commit: `python -m pytest -q` xanh (nếu sửa test)
- **B6.** Không re-host nội dung/ảnh bản quyền
- **B8.** Không thêm dịch vụ trả phí
- KHÔNG tự sinh dữ liệu giả (địa chỉ, SĐT, mùa vụ)

## 3. Commit

- Branch: `session-content` (đã checkout)
- Format: `[QA] <mô tả ngắn>`
- Commit nhỏ, 1 task = 1 commit
- **KHÔNG push, KHÔNG merge vào main**

## 4. Verify

```powershell
cd C:\Code\vinhlong360\vl360-session-content
python -m pytest -q                     # tests xanh
python scripts/validate_data.py         # data sạch
```

## 5. Danh sách task (làm theo thứ tự)

### Nhóm 1: Tài liệu cập nhật (ưu tiên cao)
- [ ] **QA-1** Cập nhật `docs/ROADMAP.md` — đánh dấu chính xác trạng thái mọi task (nhiều task đã xong nhưng chưa tick). Rà commit history để verify.
- [ ] **QA-2** Cập nhật `docs/architecture-decisions.md` — thêm decisions mới (DB-as-SoT đã chốt, Postgres-only UGC, no-Tailwind, 3-tỉnh merge).
- [ ] **QA-3** Viết `docs/deployment-guide.md` — hướng dẫn deploy lên VPS (tarball flow, systemd services, nginx config, gotchas). Dựa trên thực tế đã deploy.
- [ ] **QA-4** Viết `docs/developer-setup.md` — hướng dẫn setup dev environment (Python venv, Node, Postgres docker, .env, chạy server + frontend).
- [ ] **QA-5** Cập nhật `docs/api-contract.md` — rà API endpoints hiện tại, bổ sung endpoints mới (facilities, community, auth, admin).

### Nhóm 2: Scripts cải thiện
- [ ] **QA-6** Cải thiện `scripts/validate_data.py` — thêm check: entities có summary <50 ký tự, entities thiếu type, relationships trỏ entity không tồn tại (dangling).
- [ ] **QA-7** Cải thiện `scripts/backup_data.py` — thêm: auto-cleanup backups cũ hơn 30 ngày (giữ 5 bản gần nhất), log kích thước backup.
- [ ] **QA-8** Script `scripts/health_check.py` — gọi `/health` + `/health/deep`, báo cáo status, dùng được trong CI hoặc cron.
- [ ] **QA-9** Cải thiện `scripts/deploy.sh` — thêm pre-deploy check (test pass? build pass?), rollback guide trong comment.

### Nhóm 3: Test coverage mở rộng (tests/ gốc)
- [ ] **QA-10** Rà `tests/` — xóa test file cho module đã bị xóa (GĐ6.1 xóa 7 module). Test import PHẢI pass.
- [ ] **QA-11** Thêm test cho `scripts/validate_data.py` — đảm bảo validator tự nó chạy đúng.
- [ ] **QA-12** Thêm test cho `scripts/backup_data.py` — verify backup tạo đúng file.

### Nhóm 4: CI/CD
- [ ] **QA-13** Cập nhật `.github/workflows/ci.yml` — đảm bảo chạy `tests/` + `agent/tests/`, thêm step `validate_data.py`, thêm step `npm run build` (web-nuxt).
- [ ] **QA-14** Thêm `.github/workflows/deploy.yml` (template, manual trigger) — cho tương lai khi có remote.

### Nhóm 5: SEO config (nuxt.config.ts — CHỈ meta/sitemap)
- [ ] **QA-15** Kiểm `web-nuxt/nuxt.config.ts` phần `app.head` — meta description, og:title, og:description, og:image default. Cập nhật cho 3 tỉnh sáp nhập.
- [ ] **QA-16** Kiểm sitemap config — đảm bảo `/sitemap.xml` include tất cả trang tĩnh + dynamic routes.

### Nhóm 6: Data quality audit
- [ ] **QA-17** Chạy `python scripts/validate_data.py` và ghi kết quả vào `docs/data-quality-report.md`.
- [ ] **QA-18** Liệt kê entities thiếu images (count + top examples) vào report.
- [ ] **QA-19** Liệt kê entities với `coords_approximate=true` (count) vào report.

### Nhóm 7: Legacy cleanup & Infra audit
- [ ] **QA-20** `web/` legacy audit — liệt kê TẤT CẢ files trong `web/` (trừ `data.json`, `admin*.html`, `media/`). Ghi vào `docs/legacy-files-audit.md`: file nào vẫn cần (admin UI, media), file nào có thể xóa ở GĐ7 tương lai. KHÔNG XÓA — chỉ kiểm kê.
- [ ] **QA-21** Docker compose review — verify `docker-compose.yml` chạy đúng: postgres container khởi được, ports mapping đúng, env vars đủ. Sửa nếu sai (file này trong scope).
- [ ] **QA-22** `.env.example` audit — đảm bảo mọi env var backend dùng đều có trong `.env.example` với comment giải thích. Thêm var thiếu (chỉ thêm comment/placeholder, KHÔNG đặt giá trị thật).
- [ ] **QA-23** Stale config cleanup — rà `.gitignore`, `Dockerfile`, `docker-compose.prod.yml` cho entries/config đã lỗi thời (module xóa, path đổi). Cập nhật.

## 6. Lưu ý

- Đọc `agent/` và `web-nuxt/` để hiểu code, nhưng KHÔNG sửa.
- Dùng `git log --oneline -20` để hiểu recent changes.
- Khi viết docs, dùng tiếng Việt cho nội dung user-facing, tiếng Anh cho technical docs.
- Scripts phải chạy trên Windows (PowerShell) và Linux.
- KHÔNG tạo `README.md` trừ khi được yêu cầu.

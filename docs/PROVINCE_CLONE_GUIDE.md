# Hướng dẫn Nhân bản Sang Tỉnh Mới (`dongthap360`, `cantho360`…)

> STATUS (2026-11-25): Active — Hướng dẫn chuẩn tách lớp cấu hình tỉnh và triển khai bản clone sạch dữ liệu Vĩnh Long.

Tài liệu này hướng dẫn quy trình nhân bản nền tảng từ `vinhlong360` sang một tỉnh mới (ví dụ **Đồng Tháp mới**, hợp nhất 2 vùng `dong-thap` và `tien-giang`) **sạch hoàn toàn dữ liệu, ảnh và lịch sử git của Vĩnh Long**.

---

## Kiến trúc 2 lớp của nền tảng

1. **Lớp Lõi (Portable Core):** FastAPI (`agent/`), Nuxt 4 SSR (`web-nuxt/`), schema/invariants/security gates (`scripts/checks/`), script triển khai (`scripts/deploy_vps.sh`), và bộ **Core Platform Tests** (`npm run test:core` + `python scripts/checks/run_test_suite.py --suite core --scope backend`).
2. **Lớp Cấu hình & Dữ liệu Tỉnh (Province Layer):**
   - Hợp đồng cấu hình duy nhất: [`config/province.config.json`](../config/province.config.json) (mẫu Đồng Tháp 2 vùng: [`config/province.dongthap.example.json`](../config/province.dongthap.example.json)).
   - Dữ liệu thực thể: `web/data.json`, SQLite `agent/data/<slug>.db`, ảnh thực thể `web-nuxt/public/img/entities/*.webp`, và bản đồ redirect/bộ lọc tỉnh.

---

## Quy trình 6 bước tạo `dongthap360`

### Bước 1 — Xuất mã nguồn sạch (không kéo lịch sử git Vĩnh Long)
```bash
git archive --format=tar HEAD | tar -x -C ../dongthap360
cd ../dongthap360
git init -b main
```

### Bước 2 — Nạp cấu hình Đồng Tháp (2 phân vùng)
```bash
cp config/province.dongthap.example.json config/province.config.json
```
Rà soát và hoàn thiện trong `config/province.config.json`:
- `identity`: `slug`, `domain`, `siteUrl`, `wardCount` (`102`), `heroSubtitle`, `seoTitle`, `seoDescription`.
- `bounds`: `schemaBbox` & `ingestBbox` khớp ranh giới Đồng Tháp mới (Đồng Tháp + Tiền Giang cũ).
- `areas.items`: giữ đúng 2 phân vùng (`dong-thap`, `tien-giang`) và cập nhật `multiRegionMeta`.
- `emergencyHotlines`: xác minh lại số hotline cứu hộ đường thủy / du lịch địa phương trước khi public.
- `contentGuards.outOfProvincePatterns`: dùng danh sách địa danh ngoại tỉnh Đồng Tháp (như `Mang Thít`, `Cầu Kè`, `Trà Cú`, `Ao Bà Om` — **không** chặn `Cái Bè`, `Lai Vung`, `Định Yên`).
- `home`: cập nhật ảnh và thực thể tiêu biểu thuộc Đồng Tháp.

### Bước 3 — Dọn sạch dữ liệu, ảnh và redirect của Vĩnh Long
Xoá hoặc thay thế toàn bộ tài sản gắn với Vĩnh Long trước khi nạp dữ liệu tỉnh mới:
- Dữ liệu & DB: `web/data.json` (tạo rỗng `{"entities":[],"relationships":[],"itineraries":[]}`), `agent/data/vinhlong360.db`, và bản sao lưu cũ trong `backups/`.
- Ảnh thực thể: `web-nuxt/public/img/entities/*` và cập nhật ảnh đại diện `web-nuxt/public/img/og-default.jpg`, `public/manifest.json`, `public/llms.txt`.
- Whitelist & test gắn Vĩnh Long: cập nhật `docs/standards/whitelist-tinh-cu.txt` cho tỉnh mới và thay các test thuộc nhóm `province_data` / `PROVINCE_TEST_FILES`.

### Bước 4 — Chạy bộ Core Platform Tests (xác nhận lõi sạch trước khi nạp dữ liệu)
```bash
# Backend core tests
python scripts/checks/run_test_suite.py --suite core --scope backend

# Frontend core tests + Nuxt typecheck
cd web-nuxt
npx nuxt typecheck
npm run test:core
```

### Bước 5 — Nạp dữ liệu Đồng Tháp mới & kiểm định toàn phần
1. Nạp danh sách xã/phường Đồng Tháp mới (`dong-thap`, `tien-giang`), thực thể du lịch/OCOP/ẩm thực/lưu trú và tọa độ chuẩn BBox.
2. Chạy cổng kiểm định hợp nhất:
   ```bash
   python scripts/checks/run_hard.py --all
   cd web-nuxt && npm run build
   ```

### Bước 6 — Triển khai lên VPS mới bằng một lệnh chuẩn
Chỉnh mục `deploy` trong `config/province.config.json` (`appDir`, `agentService`, `webService`, `dbFilename`), chuẩn bị `.env` trên VPS (PostgreSQL + systemd units + Nginx), chạy thử `--dry-run` trước rồi deploy:
```bash
bash scripts/deploy_vps.sh --dry-run --host root@<NEW_VPS_IP>
bash scripts/deploy_vps.sh --host root@<NEW_VPS_IP>
```

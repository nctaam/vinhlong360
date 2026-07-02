# Phương án tối ưu AdminCP — 2026-07-02

> Nền bằng chứng: 2 vòng audit hệ thống cùng ngày + 3 sự cố prod trong ngày (dashboard
> 500 SQL-dialect, sidebar vỡ class-collision, entities 500 TDZ — đều ở AdminCP, đều
> không lưới nào bắt) + recon 3-agent kiểm kê 32 trang / 10.002 dòng FE admin,
> khớp 131 endpoint BE ↔ 90 call-site FE, và rà UX từng trang.

## Hiện trạng một trang

| Số liệu | Giá trị | Ý nghĩa |
|---|---|---|
| Trang admin | 32 trang / 10.002 dòng (+ layout 646) | không trang mồ côi, breadcrumb/title nhất quán 100% |
| File rủi ro | `entities.vue` **1.433 dòng**, `data-quality.vue` 809 | blast radius lớn; entities dính TDZ hôm nay |
| Test FE admin chạy được | **0** (vitest 51/51 skip) | 3 bug hôm nay đều lọt vì lớp này trống |
| Endpoint BE | 131, FE dùng 73 → **58 (44%) mồ côi** | appeals/claims/collections/featured/qa-queue… có BE+test nhưng **chưa từng có UI** |
| Mutation FE dùng hằng ngày thiếu test runtime | ~20 | trong khi endpoint chết lại CÓ test (nghịch lý coverage) |
| Fetch nặng nhất | audit-log `limit=5000` mỗi lần đổi filter; badge-counts poll 60s parse cả file JSONL; /media dựng lại toàn bộ từ `all_entities()` mỗi click | VPS 1GB |
| UX nền | khá tốt (dark 176 rule, CommandPalette có sẵn Ctrl+K, DEGRADED-pattern ở dashboard mẫu mực) | 7 quick-win rẻ chưa làm |

## Bốn trục — xếp theo giá trị/rủi ro

### Trục 1 · CHỐNG VỠ (ưu tiên #1 — trả nợ trực tiếp cho 3 sự cố hôm nay)

| # | Việc | Công | Chi tiết |
|---|---|---|---|
| 1.1 | **Hồi sinh vitest + smoke-mount test cho cả 32 trang** | M | Mount từng trang với mock $fetch → bắt TDZ/render-fatal ngay lúc dev. Đây là lớp test lẽ ra chặn được CẢ 3 bug hôm nay. Sửa setup-hook timeout đang làm 51/51 skip. |
| 1.2 | **Error boundary per-page** trong layout admin | S | `NuxtErrorBoundary` quanh `<slot/>` — 1 trang lỗi hiện panel lỗi + nút thử lại, không giết cả app thành 500 full-page. |
| 1.3 | **Fix bẫy §B1**: `/admin-api/data-quality/apply` crash nửa chừng (import `scripts/normalize_data.py` đã xoá SAU khi ghi data.json) — risk #7 audit còn mở | S | Đổi thứ tự backup-trước-ghi + bỏ import chết + test. |
| 1.4 | Sửa test gọi endpoint **đã xoá** (`bulk-update-confidence` assert 200, bị deselect nên không ai biết) | XS | Xoá/sửa test; thêm rule: test không được nằm ngoài default selection. |
| 1.5 | 2 chỗ `useAsyncData().catch(()=>[])` **nuốt lỗi im lặng** (chua-phan-loai:151, danh-ba:150 — API chết là dropdown trống không báo) + entities.vue:866, lich-trinh:253 | XS | Thêm toast/flag lỗi. |
| 1.6 | Runtime endpoint tests cho ~20 mutation dùng hằng ngày (itineraries CRUD, ban/role, reports resolve, bulk-place…) | M | Nhân pattern `test_admin_kind_views.py` (TestClient thật — vừa chứng minh giá trị khi bắt `db.escape_like`). |

### Trục 2 · HIỆU NĂNG NÓNG (điểm đau đo được trên VPS 1GB)

| # | Việc | Công | Chi tiết |
|---|---|---|---|
| 2.1 | audit-log: BE thêm `offset` thật, FE `nhat-ky.vue` bỏ `limit=5000` → phân trang server | S | Nặng nhất hệ hiện tại. |
| 2.2 | badge-counts: cache server-side 60s (đang parse cả JSONL info-reports mỗi poll × mỗi tab) | XS | 1 dict cache + TTL. |
| 2.3 | /media: phân trang thật thay vì dựng toàn bộ media-list mỗi click | M | |
| 2.4 | bao-cao + provisional + itineraries: phân trang server (limit=200 cứng hiện tại) | S | Chưa đau nhưng phình theo user. |

### Trục 3 · UX QUICK-WINS (7 mục, 5×XS + 2×S, không redesign)

1. **Mobile nav**: ẩn 9 link per-kind trên mobile (1 rule CSS — dải 26 mục → 17) + auto-scroll mục active vào tầm nhìn (XS)
2. **CommandPalette**: bổ sung 11 đích còn thiếu (9 kind + 2 trang mới) + tìm **không dấu** + nút 🔍 mở được trên mobile (XS) — palette có sẵn mà đang vô hình
3. **Nút dark-mode toggle trong admin** (hiện phải ra trang chủ để đổi) (XS)
4. Thống nhất skeleton loading (8 trang còn spinner trần) (S)
5. Phím tắt j/k/a/r nhân từ kiểm-duyệt sang **duyệt-ảnh** (cùng workflow) + `/` focus search ở trang list (S)
6. Title/breadcrumb phản ánh kind đang xem (`🛕 Địa điểm — Admin`) (XS)
7. Chuẩn REFRESH: nút "Làm mới" đồng vị trí mọi trang (đã gần chuẩn) (XS)

### Trục 4 · QUYẾT ĐỊNH SẢN PHẨM (cần chủ chọn — không tự làm)

| # | Câu hỏi | Lựa chọn |
|---|---|---|
| 4.1 | **58 endpoint mồ côi (44%)** — appeals (kháng nghị), claims (xác nhận chủ cơ sở), collections/featured (bộ sưu tập/nổi bật), stale-queue, qa-queue, user-growth… BE + test đã xong từ các wave trước nhưng UI chưa từng xây | (a) xây UI cho nhóm đáng giá (claims + featured hợp hướng doanh thu premium listing), (b) prune bớt để giảm bề mặt bảo trì, (c) để nguyên |
| 4.2 | **Content-ops**: nút "Tạo ảnh AI" ngay trong panel "Cần bổ sung nhất" (đánh nghẽn 0/1.730 ảnh, pipeline cx/gpt-5.5-image có sẵn) + màn sửa 15 giá trị uncoercible | bật khi chủ duyệt chạy image API |
| 4.3 | Tách nhỏ `entities.vue` 1.433 dòng thành 4-5 component | CHỈ làm SAU khi 1.1 xong (§B3 — không refactor vùng mù không test) |

## Lộ trình đề xuất

- **Đợt 1 (1 buổi):** Trục 1 trọn (1.1→1.6) — sau đợt này, lớp bug làm anh gặp 3 sự cố hôm nay bị chặn ở dev, không tới được prod.
- **Đợt 2 (nửa buổi):** Trục 2 (2.1→2.4) + Trục 3 (7 quick-win) — admin nhanh + mượt rõ rệt, đặc biệt mobile.
- **Đợt 3 (theo quyết định 4.x):** UI cho endpoint mồ côi đáng giá / content-ops ảnh / tách entities.vue.

**DoD chung:** mỗi việc = test trước khi sửa (nếu chạm §B3), build xanh, deploy phẫu thuật, verify trong browser thật (giờ đã có quy trình Chrome MCP), commit riêng. Không tăng baseline test đỏ.

## Ghi chú rủi ro

- `entities.vue` + `admin.py` vẫn nằm trong cây WIP song song — mọi edit tiếp tục additive + diff-check trước commit. Đợt triage WIP tổng (đã 3 lần chứng minh cần) vẫn chờ chủ.
- Mọi việc trong phương án đều 0đ, thuần code — không đụng §B8.

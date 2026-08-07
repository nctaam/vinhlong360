> STATUS: active — BẢN NHÁP chờ chủ dự án duyệt. KHÔNG tự ý ghi vào `web/data.json`/DB.

# Nháp mô tả S+ — Khu di tích Nguyễn Đình Chiểu

Ngày soạn: 2026-08-07 · Skill: `viet-content-optimizer` · Phạm vi: 1 entity

### Khu di tích Nguyễn Đình Chiểu (`khu-di-tich-nguyen-dinh-chieu`, history, ben-tre)

**Cũ (167 ký tự):** Tại vùng đất Ba Tri gió lộng, khu di tích Nguyễn Đình Chiểu là điểm hành hương của những ai kính ngưỡng vị sĩ phu mù mà lòng sáng tựa gương, ngòi bút sắc bén như gươm.

**Mới (400 ký tự):**

Năm 1862, khi ba tỉnh miền Đông rơi vào tay Pháp, Nguyễn Đình Chiểu rời Gia Định về Ba Tri và ở lại 26 năm cuối đời. Di tích quốc gia đặc biệt rộng hơn 14.000 m² xếp ba lớp thời gian: khu mộ tôn tạo 1958, đền thờ cũ 1972, đền thờ mới cao 21 m (2000–2002). Cạnh mộ cụ là mộ con gái, Sương Nguyệt Anh — nữ chủ bút đầu tiên của báo chí Việt Nam. Ngày 1 và 3 tháng 7 — sinh và mất — dân xã Ba Tri về giỗ.

---

## Nguồn từng fact

| Fact | Nguồn | Mức |
|---|---|---|
| Về Ba Tri năm 1862, sống 26 năm cuối đời (1862–1888) | bentre.dcs.vn (Tỉnh ủy) + danhnhannguyendinhchieu.vn + thitranbatri.gov.vn | ★★★★ |
| Di tích quốc gia đặc biệt, QĐ 2499/QĐ-TTg ngày 22/12/2016 | Cục Di sản văn hóa `dsvh.gov.vn` | ★★★★★ |
| Tổng diện tích 14.187,9 m² ("hơn 14.000 m²") | Cục Di sản văn hóa `dsvh.gov.vn` | ★★★★★ |
| Khu mộ tôn tạo năm 1958 | Cục Di sản văn hóa `dsvh.gov.vn` | ★★★★★ |
| Đền thờ cũ dựng 1972 (84 m²) | dsvh.gov.vn + Wikipedia (Lăng Nguyễn Đình Chiểu) | ★★★★★ |
| Đền thờ mới cao 21 m, xây 2000–2002 | dsvh.gov.vn + Wikipedia | ★★★★★ |
| Mộ con gái Sương Nguyệt Anh trong khu mộ | dsvh.gov.vn (ghi "Nguyễn Thị Ngọc Khuê") + Wikipedia | ★★★★★ |
| Sương Nguyệt Anh là nữ chủ bút đầu tiên của báo chí VN (*Nữ giới chung*, số đầu 1/2/1918) | Hội LHPN Việt Nam `hoilhpn.org.vn` + Báo Tin Tức (TTXVN) | ★★★★ |
| Lễ giỗ ngày 1 và 3 tháng 7 (ngày sinh / ngày mất) | Cục Di sản văn hóa `dsvh.gov.vn` | ★★★★★ |
| Xã An Đức (cũ) nay thuộc xã Ba Tri, tỉnh Vĩnh Long | tracuusapnhap.vn + NQ 202/2025/QH15 | ★★★★ |

Fact đã cân nhắc nhưng **loại khỏi bản mới** (đúng nguồn, nhưng vượt trần 400 ký tự — xem mục đề xuất attributes): UNESCO ra nghị quyết vinh danh 23/11/2021 và cùng kỷ niệm 200 năm ngày sinh năm 2022; nhà bia cao 12 m với bia đá xanh nguyên khối 2,65 × 2,7 × 1,8 m; tượng đồng cụ Đồ Chiểu cao 1,6 m.

## Tự kiểm (3 bài test bắt buộc)

**Substitution** — đạt. Thay tên bất kỳ di tích nào khác vào, cả 4 câu đều sai ngay: mốc 1862/26 năm, con số 14.000 m² + bộ ba mốc 1958/1972/2000–2002, mộ Sương Nguyệt Anh, và cặp ngày 1–3/7 đều chỉ đúng entity này. Bản cũ thì fail nặng: "điểm hành hương của những ai kính ngưỡng…" lắp vừa cho hàng chục đền thờ danh nhân.

**Deletion** — đạt sau khi cắt. Đã xóa thật: toàn bộ cụm sáo của bản cũ ("gió lộng", "lòng sáng tựa gương", "ngòi bút sắc bén như gươm" — 0 fact, thuần trang trí). Cắt thêm ở vòng sửa: câu giờ mở cửa/vé (trùng `hours` + `admission` đã có trong attributes), và cụm "xếp ba lớp thời gian" từng dài dòng hơn. Giờ xóa bất kỳ câu nào cũng mất một khối fact riêng.

**Curiosity** — đạt. Hai hook làm việc: (1) người Ba Tri thờ phụng nhất lại **không sinh ra ở Ba Tri** — ông đồ mù 40 tuổi bỏ Gia Định về đây vì không chịu sống dưới quyền Pháp; (2) nằm cạnh mộ cha là mộ người phụ nữ đầu tiên làm chủ bút một tờ báo Việt. Chi tiết (2) hầu như không xuất hiện trong mô tả du lịch phổ thông về khu di tích này.

**Gate khác:** câu đầu 116 ký tự (≤155, dùng làm meta description, chứa keyword "Nguyễn Đình Chiểu" + "Ba Tri"); tổng 400 ký tự (đúng trần Gate 3); không mở bằng tên entity; dấu tiếng Việt NFC chuẩn; nhịp câu 27/31/21/17 từ (thu dần, kết bằng câu ngắn).

## Attributes đề xuất bổ sung / sửa

| Field | Đề xuất | Lý do & nguồn |
|---|---|---|
| `architectural_style` | **SỬA** "Đình làng (kiến trúc truyền thống Nam bộ)" → "Đền thờ mới: nhà tròn bê tông cốt thép, 2 tầng với 3 tầng mái, ngói âm dương xanh (2000–2002); đền thờ cũ 1972: 2 tầng mái, ngói âm dương nâu" | Giá trị hiện tại **SAI**. dsvh.gov.vn mô tả đền thờ mới hình tròn, bê tông cốt thép — không phải kiến trúc đình làng (★★★★★) |
| `address` | **SỬA** "Xã An Đức" → "Ấp 3, xã Ba Tri, tỉnh Vĩnh Long (xã An Đức cũ)" | An Đức + thị trấn Ba Tri + An Bình Tây + Vĩnh An + Vĩnh Hòa → xã Ba Tri, từ 1/7/2025 (NQ 202/2025/QH15). Ấp 3: dsvh.gov.vn (★★★★★) |
| `key_facts[]` | **THÊM** "UNESCO ra nghị quyết vinh danh ngày 23/11/2021 (kỳ họp Đại hội đồng lần 41), cùng kỷ niệm 200 năm ngày sinh năm 2022" | key_facts hiện ghi "UNESCO vinh danh ông năm 2022" — thiếu mốc nghị quyết 2021. Nguồn: baochinhphu.vn (★★★★) |
| `key_facts[]` | **THÊM** "Trước đó được Bộ Văn hóa – Thông tin xếp hạng di tích lịch sử – văn hóa cấp quốc gia ngày 27/4/1990" | dsvh.gov.vn (★★★★★) — mốc này chưa có trong data |
| `key_facts[]` | **THÊM** "Nhà bia cao 12 m, bia đá xanh nguyên khối 2,65 × 2,7 × 1,8 m" | dsvh.gov.vn + Wikipedia (★★★★★) |
| `season.text` | **SỬA** — hiện viết mơ hồ "tháng 7 thường đáng chú ý vì gắn với các hoạt động tưởng niệm". Nên nêu đích danh: lễ giỗ **ngày 1 và 3 tháng 7** (ngày sinh / ngày mất) | dsvh.gov.vn (★★★★★) |
| `season.text` | **SỬA** cụm "tại Bến Tre" → "tại Ba Tri" hoặc "tại xã Ba Tri" | §1.6 CLAUDE.md: gọi theo tỉnh MỚI; "Bến Tre" chỉ dùng kèm chữ "cũ" trong văn cảnh lịch sử |
| `highlight` | **SỬA** — "ngòi bút yêu nước bất diệt… hồn thiêng đất Ba Tri" là giọng sáo cùng loại với summary cũ, nên viết lại bằng fact | Nhất quán chuẩn S+ |
| `sub_category`, `hours`, `phone`, `admission`, `coordinates` | Giữ nguyên | Không có nguồn mâu thuẫn |

## Cảnh báo

1. **`architectural_style` hiện SAI** — "Đình làng" mâu thuẫn trực tiếp với mô tả của Cục Di sản văn hóa (đền thờ mới hình tròn, bê tông cốt thép, 2 tầng / 3 tầng mái). Đây là lỗi dữ liệu cần sửa, không phải khác biệt diễn đạt. Bản mô tả mới đã tránh dùng từ "đình làng".
2. **`verifiedAt` của entity này KHÔNG rỗng** — data.json ghi `"verifiedAt": "2026-06-28T02:23:56Z"` (trùng khít `updatedAt`, và `verified: 1`), trái với giả định "verifiedAt = 0 toàn bộ entity" trong đề bài. Dấu hiệu đây là timestamp do pipeline ghi tự động chứ không phải kiểm chứng thực địa. Theo §1.7, bản mô tả mới **không chứa bất kỳ claim "đã xác minh/kiểm chứng"** nào. Đề nghị chủ dự án rà lại ngữ nghĩa trường `verifiedAt` trên toàn bộ dataset trước khi dùng nó làm bằng chứng E-E-A-T.
3. **Tên thật Sương Nguyệt Anh không thống nhất giữa nguồn:** dsvh.gov.vn ghi "Nguyễn Thị Ngọc Khuê", Hội LHPN ghi "Nguyễn Xuân Khuê". Năm mất cũng lệch (1921 vs 1922). Bản mô tả **cố tình chỉ dùng bút danh "Sương Nguyệt Anh"** và không nêu năm sinh/mất để tránh chốt vào dữ kiện đang mâu thuẫn.
4. **Đề bài mô tả entity "an táng Nguyễn Đình Chiểu (1822–1888) + vợ + con gái"** — chính xác theo nguồn. Nhưng lưu ý cụ **sinh tại làng Tân Thới, Gia Định** (nay thuộc TP.HCM), không sinh ở Ba Tri; mô tả cũ dễ gây hiểu nhầm ngược lại.
5. **Chi tiết "hội có bàn hốt thuốc nam miễn phí"** (gắn với nghề bốc thuốc của cụ ở Ba Tri) chỉ thấy ở Wikipedia, chưa đối chiếu được nguồn thứ hai ★★★+ → **đã loại**, không đưa vào mô tả.
6. Chưa đụng `web/data.json`, chưa chạy script ETL/DB, chưa git add/commit. Mọi thay đổi ở bảng trên là **đề xuất**, chờ chủ dự án duyệt.

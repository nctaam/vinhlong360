# Bàn giao — dừng vì hết quota, 2026-08-31

> STATUS: active — đọc file này TRƯỚC khi làm tiếp trên `codex/correction-case-pilot`.
> Viết lúc phiên bị cắt giữa chừng vì hết quota Claude Desktop. Không có việc nào
> đang dở dang trong mã: **cây sạch, 25 commit đã chốt**.

## Đang ở đâu

HEAD `d05024eb`. Tất cả đã commit. Không có patch treo, không có file sửa dở.

**Bốn quyết định của chủ dự án đã thực thi:**

| Khoản | Quyết định | Commit | Trạng thái |
|---|---|---|---|
| §0 P0 lời hứa xoá | "thực hiện theo Luật 91/2025" | `667b4267` | xong (mã + mặc định + rào) |
| §0b mìn CI coverage | chuyển sang job `test-pg` | `146a2303` | xong |
| §5 ba cổng | thêm cả ba | `b9dbb1f6` | xong, kèm §5d |
| §1 trần bundle | giữ trần, mở đợt giảm cân | `f831f5f6` | **đo xong bước một → trả về câu hỏi** |

## Con số full-suite — ĐÃ CÓ, và nó xác nhận phần chính

Lượt đo chạy xong sau khi viết mục này. Trên máy đã có dung lượng:

    DIA TRUOC: 12,79 GB
    15 failed, 12.359 passed, 138 skipped, 552 deselected, 1 xfailed, 12 errors
    So fail: 15 | trong danh sach: 15 | MOI: (rong) | MAT: (rong) | HET-DIFF
    DIA SAU  : 12,75 GB  (luot nay chi tieu 0,04 GB)

**Xác nhận hai điều:** (a) 15 fail đúng nguyên danh sách, 0 mới 0 mất — ba bản vá
sạch; (b) hai "fail mới" hôm qua đúng là nhiễu đĩa cạn, nay hết chỗ cạn thì hết luôn.
Đĩa gần như không nhúc nhích trong suốt lượt chạy, đối lập hẳn với lượt hôm qua.

### ⚠ NHƯNG: 12 `errors` chưa được giải thích — và công cụ đo của tôi MÙ với chúng

Dòng "HẾT-DIFF" ở trên **chỉ so `FAILED`, không so `ERRORS`**. `scratchpad/fullsuite.py`
chỉ bắt regex `^FAILED (\S+)`, nên 12 error kia lọt qua phép đối chiếu mà vẫn in ra
"HẾT-DIFF". Đó là lỗi của công cụ, không phải bằng chứng suite sạch.

Số liệu để so: các lượt full-suite trước trong phiên đều **0 error** (16/11.680 và
15/12.364), còn lượt đĩa-cạn có **88 error**. Nay 12 — ít hơn hẳn 88 nhưng nhiều hơn
0, và `passed` tụt 12.364 → 12.359 (−5).

**Việc đầu tiên của phiên sau:**
1. Sửa `fullsuite.py` để đối chiếu CẢ `ERROR` lẫn `FAILED` (regex `^ERROR (\S+)`),
   nếu không thì "HẾT-DIFF" còn tiếp tục nói dối.
2. Chạy lại, lấy danh sách 12 error đó và phân loại: môi trường hay thật.
3. Nếu là thật → bổ sung vào danh sách fail-đã-biết ở ROADMAP hoặc vá.

Ba bản vá của đợt KHÔNG phụ thuộc kết quả này — chúng đã được nghiệm thu bằng suite
riêng (79 erasure · 504 nhóm liên quan · 186 cổng chuẩn · 130 file frontend).

## Việc tiếp theo, theo thứ tự đáng làm

1. **Đọc/chạy lượt full-suite** ở trên → ghi số vào ROADMAP đợt (4).
2. **§1 bundle** — chờ chủ chọn một trong ba: thay maplibre (quyết định thị giác,
   phải trình mockup trước) · tải từ CDN (thêm phụ thuộc bên thứ ba, và thành thật
   thì nó lách cổng) · chấp nhận 802/800. Số đo đã có đủ ở hồ sơ §1.
3. **Mười khoản còn lại** trong `docs/2026-08-30-ho-so-cho-chu-du-an-quyet.md`,
   trong đó §6b là bốn khoản mới phát sinh hôm qua.
4. Cân nhắc đề nghị ở cuối ROADMAP đợt (4): mở một đợt **cô lập trạng thái cho bộ
   test** — trong một ngày đã bắt BA lỗi thật cùng chữ ký *chạy riêng xanh, chạy
   chung đỏ* (`296e1d04`, `b0c887be`, `10b960a6`).

## Hai thứ chủ dự án tự xử — MÁY KHÔNG ĐỤNG

- **Dung lượng máy.** Chỉ đạo 2026-08-31: "tôi tự dọn, anh đừng đụng". Đã dọn xong,
  còn 12,79 GB lúc bàn giao. Thủ phạm không nằm trong kho (build artifact ~0,02 GB).
- **`graphify-out/`** — thư mục 0,09 GB do công cụ khác tạo trong kho, chưa version,
  không có trong `.gitignore`. Chỉ đạo: để nguyên. **Đừng xoá, đừng thêm .gitignore.**

## Bài học đắt nhất của phiên, đừng lặp

Tôi tiêu một giờ bisect sáu giả thuyết cho hai "fail mới" — **mỗi phép đo đều đúng,
hướng thì sai**, vì giả định nền "máy còn chỗ" không bao giờ được kiểm. Hoá ra là
đĩa cạn. Dấu hiệu phân biệt nay ghi ở CLAUDE.md §5c-bis: **môi trường thì tập fail
ĐỔI giữa hai lượt giống hệt nhau và sinh `errors` hàng loạt; hồi quy thật thì tất
định và khu trú.**

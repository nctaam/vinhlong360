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

## MẢNH DUY NHẤT CÒN THIẾU

**Con số full-suite chốt sổ.** Lượt đo cuối đang chạy nền lúc phiên bị cắt:

    scratchpad/fullsuite.py   (đã gắn đồng hồ đĩa hai đầu theo §5c-bis)
    output: .../tasks/b3p3a0fbl.output

Nếu file đó có kết quả, đọc nó. Nếu không, chạy lại — **nhớ đo dung lượng trống
trước** (§5c-bis; dưới 5 GB thì đừng chạy, script tự dừng).

Kỳ vọng: **15 fail đúng danh sách, HẾT-DIFF**. Ba bản vá đã được nghiệm thu bằng
suite riêng lúc còn dung lượng (79 erasure · 504 nhóm liên quan · 186 cổng chuẩn ·
130 file frontend), nên full-suite chỉ là xác nhận, không phải điều kiện.

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

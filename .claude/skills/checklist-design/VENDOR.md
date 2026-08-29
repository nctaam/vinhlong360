# Nguồn vendor

Skill CHÍNH CHỦ của checklist.design, cài theo lệnh chủ dự án 2026-08-29
("tham khảo https://www.checklist.design/ và cài đặt skill").

- Upstream: https://github.com/checklist-design/skills (MIT)
- Phiên bản: 3.2.1 — commit d5c2e833c9a2a17792751a67f86f2ca4aca0c14b (2026-08-20)
- Đã soi trước khi cài: 129 file thuần Markdown, 0 executable, 0 gọi mạng;
  phần plugin (hooks/ + scripts/ ở gốc repo upstream) KHÔNG cài — chỉ cần
  bản skill cho Claude Code đọc trực tiếp.
- Cập nhật: clone upstream, so `metadata.version`, copy đè thư mục này
  (giữ VENDOR.md + LICENSE), commit ghi rõ version mới.
- KHÔNG sửa nội dung upstream tại chỗ — muốn thêm quy tắc riêng vinhlong360
  (dark/light token, §1.5 ảnh AI-only, §1.6 định vị) thì viết skill bọc riêng,
  đừng phân nhánh bản vendor.

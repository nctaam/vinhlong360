# QUY TẮC BẮT BUỘC: 5W1H2C5M TRƯỚC KHI BẮT ĐẦU MỌI TÁC VỤ

Trước khi bắt đầu thực hiện bất kỳ việc gì (lập trình, sửa lỗi, tái cấu trúc, thiết kế, triển khai, phân tích dữ liệu, v.v.), AI Agent và Pair Programmer **bắt buộc** phải phân tích, định hình và đối soát đầy đủ theo mô hình tư duy toàn diện **5W1H2C5M**:

---

## 1. 5W — Xác Định Bản Chất & Phạm Vi
* **Why (Tại sao?):** Mục đích cốt lõi là gì? Giải quyết vấn đề gì, mang lại giá trị gì cho người dùng/hệ thống? Động lực thúc đẩy công việc này?
* **What (Làm cái gì?):** Đầu ra cụ thể (deliverable/outcome) là gì? Những thành phần, tệp tin, tính năng, hoặc giao diện nào cần thay đổi hay tạo mới?
* **Where (Ở đâu?):** Vị trí thực hiện ở đâu? Đường dẫn tệp, module, màn hình, tầng kiến trúc (Frontend, Backend, Database, Cloud/VPS, DevOps)?
* **When (Khi nào?):** Thời điểm thực hiện, trình tự các bước theo thời gian, mốc kích hoạt (khi nào bắt đầu, khi nào hoàn thành, điều kiện tiên quyết)?
* **Who (Ai?):** Đối tượng thụ hưởng hoặc tác nhân liên quan: Người dùng cuối, Admin, Developer, Subagents, hay hệ thống bên thứ ba?

---

## 2. 1H — Phương Pháp & Cách Thức Thực Hiện
* **How (Làm như thế nào?):** 
  - Quy trình kỹ thuật, giải pháp kiến trúc, thuật toán, công nghệ áp dụng.
  - Các bước thực thi có hệ thống (TDD, Systematic Debugging, Quiet Luxury Craft, v.v.).
  - Làm sao để không gây side-effect và bảo toàn hợp đồng kỹ thuật hiện có?

---

## 3. 2C — Ràng Buộc & Kiểm Định (Constraints & Control)
* **Control (Kiểm soát & Đo lường):**
  - Tiêu chí nghiệm thu (Acceptance Criteria), bằng chứng thực nghiệm (Empirical Verification).
  - Bộ kiểm thử nào cần chạy (`run_hard.py`, `vitest`, `curl live`, status check)? Đo lường thành công bằng số liệu cụ thể nào?
* **Cost (Chi phí & Đánh đổi):**
  - Tác động tới tài nguyên (CPU, RAM, băng thông mạng, bundle size, storage)?
  - Độ phức tạp mã nguồn (complexity), nợ kỹ thuật (technical debt), thời gian phản hồi, thời gian bảo trì? Có tối ưu nhất chưa?

---

## 4. 5M — Nguồn Lực & Điều Kiện Thực Thi (Resources & Enablers)
* **Man (Con người & Tác nhân):** Sự phối hợp giữa Agent, Subagent, User; trách nhiệm từng vai trò.
* **Machine (Máy móc & Công cụ):** Môi trường thực thi (Local OS, VPS Linux, Node/Python runtime, Browsers, Terminal/Shell).
* **Material (Dữ liệu & Tài liệu):** Dữ liệu đầu vào, schema, tài liệu đặc tả, tài sản thiết kế (DESIGN.md), API contracts, mock data.
* **Method (Phương pháp & Quy chuẩn):** Các quy chuẩn dự án (`docs/standards/`, Clean Code, WCAG 2.2 AAA, Quiet Luxury principles).
* **Milestone / Measurement (Cột mốc & Đo lường):** Các mốc bàn giao trung gian, checkpoint đánh giá, log đối soát trước khi công bố hoàn thành.

---

> **Nguyên tắc hành động:** Luôn tự suy nghĩ hoặc trình bày khung 5W1H2C5M trước khi chạm vào mã nguồn hoặc thực hiện lệnh thay đổi hệ thống.

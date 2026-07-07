# docs/archive — Tài liệu lịch sử (KHÔNG làm theo)

> **Quy tắc (CLAUDE.md §3.6):** mọi file trong thư mục này là di tích lịch sử của dự án — snapshot audit, blueprint đã bị vượt qua, prompt one-shot thời tiền-sáp-nhập. Chúng được giữ để tra cứu ngữ cảnh/số liệu cũ, **không phải để thực thi**. Mỗi file có header `STATUS: ARCHIVED` ghi rõ vì sao và điểm nào nguy hiểm nếu làm theo.

Lý do archive (đợt truth-sync 2026-07-07, sau audit đa-agent 81 finding):

| Nhóm | File | Nguy hiểm chính nếu làm theo |
|---|---|---|
| Prompt one-shot (Codex) | codex-*.md ×5 | Chuẩn đối chiếu 3-tỉnh/26-huyện đã bãi bỏ; bảng place-hierarchy gán SAI cho cấu trúc ĐÚNG; fixture slug chết; ngoại lệ ảnh UGC nay bị cấm |
| Blueprint chồng lấn 01/07 | deep-long-range-50-phase, world-class-completion, beyond-world-class-l7-l10 | 3 bản chồng ~80%, không bản nào là nguồn việc; chứa luồng ảnh Wikimedia + điều kiện AI lỏng hơn §B8 |
| Audit/report đã tiêu hoá | audit-findings-20260622, data-quality-report, data-verification-report, system-state-audit-2026-07-02, page-function-audit-2026-07-01, 2026-07-04-page-reaudit, product-architecture-gap-analysis | **DF-02/ETL-04 là quy tắc ĐẢO NGƯỢC sau sáp nhập — cấm chạy lại**; đề xuất UGC-photo/Wikimedia bị cấm; roadmap 122.5 person-day không khả thi |
| Tầm nhìn/kế hoạch gốc | kien-truc-va-lo-trinh, admincp-optimization-plan, legacy-files-audit, design-research-2026-06-27, monitoring-setup | Stack không tồn tại (Next.js/n8n), doanh thu booking bị cấm, palette xanh sai bản sắc, container/Sentry vi phạm B8 |

Kiến trúc + quy tắc **sống** ở: `CLAUDE.md` (hiến pháp), `docs/README.md` (bản đồ tài liệu), `docs/architecture-decisions.md` (ADR).

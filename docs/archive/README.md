# docs/archive — Tài liệu lịch sử (KHÔNG làm theo)

> **Quy tắc (CLAUDE.md §3.6):** mọi file trong thư mục này là di tích lịch sử của dự án — snapshot audit, blueprint đã bị vượt qua, prompt one-shot thời tiền-sáp-nhập. Chúng được giữ để tra cứu ngữ cảnh/số liệu cũ, **không phải để thực thi**. Mỗi file có header `STATUS: ARCHIVED` ghi rõ vì sao và điểm nào nguy hiểm nếu làm theo.

Lý do archive (đợt truth-sync 2026-07-07, sau audit đa-agent 81 finding):

| Nhóm | File | Nguy hiểm chính nếu làm theo |
|---|---|---|
| Prompt one-shot (Codex) | codex-*.md ×5 | Chuẩn đối chiếu 3-tỉnh/26-huyện đã bãi bỏ; bảng place-hierarchy gán SAI cho cấu trúc ĐÚNG; fixture slug chết; ngoại lệ ảnh UGC nay bị cấm |
| Blueprint chồng lấn 01/07 | deep-long-range-50-phase, world-class-completion, beyond-world-class-l7-l10 | 3 bản chồng ~80%, không bản nào là nguồn việc; chứa luồng ảnh Wikimedia + điều kiện AI lỏng hơn §B8 |
| Audit/report đã tiêu hoá | audit-findings-20260622, data-quality-report, data-verification-report, system-state-audit-2026-07-02, page-function-audit-2026-07-01, 2026-07-04-page-reaudit, product-architecture-gap-analysis, qa-report-infra, qa-report-quality, qa-report-security, qa-scorecard, qa-test-suite | **DF-02/ETL-04 là quy tắc ĐẢO NGƯỢC sau sáp nhập — cấm chạy lại**; đề xuất UGC-photo/Wikimedia bị cấm; roadmap 122.5 person-day không khả thi |
| Tầm nhìn/kế hoạch gốc | kien-truc-va-lo-trinh, admincp-optimization-plan, legacy-files-audit, design-research-2026-06-27, monitoring-setup | Stack không tồn tại (Next.js/n8n), doanh thu booking bị cấm, palette xanh sai bản sắc, container/Sentry vi phạm B8 |

### Đợt gộp trùng lặp 2026-07-11 (KHÁC: giữ để tra cứu, không "nguy hiểm")

Bảy file dưới đây được **gộp/định vị** sang tài liệu sống; bản gốc chuyển vào đây để không mất chi tiết. Mỗi file có banner `ARCHIVED` ở đầu ghi rõ gộp vào đâu.

| File gốc | Đã gộp vào |
|---|---|
| `bao_cao_nghien_cuu_van_hoa_du_lich_vinh_long_tra_vinh_ben_tre_2025_2026.md` · `bao_cao_chuyen_sau_dia_diem_le_hoi_van_hoa_vl_tv_bt.md` · `bao_cao_nghien_cuu_da_nguon_6_tang_vl_tv_bt.md` · `bao_cao_chien_luoc_nghien_cuu_12_chieu_vl_tv_bt.md` | `docs/research/corpus-van-hoa-du-lich-vl-2026-06.md` (chỉ mục + tổng hợp) |
| `deploy-runbook-waves-2fa-dark.md` (đã done) | `docs/deployment-guide.md` + `docs/HANDOFF.md` |
| `ugc-postgres.md` | `docs/architecture-decisions.md` #3 |
| `module-activation-guide.md` | `docs/developer-setup.md` §10 |

4 báo cáo research vẫn mang cảnh báo "4 điều KHÔNG lấy" (thời 3-tỉnh, trước sáp nhập) — tra cứu tư liệu OK, KHÔNG dùng khung định vị/đơn vị hành chính cũ/khuyến nghị bán tour.

Kiến trúc + quy tắc **sống** ở: `CLAUDE.md` (hiến pháp), `docs/README.md` (bản đồ tài liệu), `docs/architecture-decisions.md` (ADR).

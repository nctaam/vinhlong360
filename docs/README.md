# docs/ — Bản đồ tài liệu (có trạng thái)

> **STATUS (2026-08-07): active — nguồn định hướng tài liệu duy nhất.** Viết lại trong đợt truth-sync 2026-07-07 (audit đa-agent 89+6 finding); đồng bộ lại 2026-08-07 (thêm `runbooks/`, `security/`, `drafts/`, bảng quyết định, bản đồ nhánh; hạ `entity-content-model.md` xuống superseded). Quy tắc: tài liệu chỉ đạo phải có header `> STATUS:`; mọi thứ trong `archive/` là lịch sử — **KHÔNG làm theo** (CLAUDE.md §3.6). File này mâu thuẫn tài liệu khác → CLAUDE.md thắng, rồi tới file này.

---

## Bắt đầu từ đâu?

| Bạn muốn | Đọc |
|-----------|-----|
| **Hiểu luật chơi** | `../CLAUDE.md` (hiến pháp — định vị, bất biến, nguồn việc) |
| **Hiểu kiến trúc** | `architecture-decisions.md` (ADR sống) |
| **Nạp session mới** | `HANDOFF.md` |
| **Nhánh nào đang ở đâu** | `HANDOFF-BRANCHES.md` (bản đồ nhánh — trunk thực tế là `codex/tri-region-color`) |
| **Việc gì đang chờ chủ dự án quyết** | `QUYET-DINH-DANG-CHO.md` |
| **Việc dài hạn / backlog** | `ROADMAP.md` (sổ track + backlog — KHÔNG còn là danh sách tuần tự) |
| **Code FE/BE** | `implementation-specs.md` + `api-contract.md` |
| **Viết/sửa content** | `content-creation-guide.md` + `toi-uu-chong-ai-va-google-spam-playbook.md` |
| **Deploy VPS** | `deployment-guide.md` |
| **Setup dev local** | `developer-setup.md` |
| **Sự cố prod** | `incident-runbook.md` + `runbooks/` (4 runbook triệu chứng-cụ-thể) |
| **Bảo mật** | `security-hardening.md` + `security/owasp-review-2026-08-05.md` |

## Tài liệu ACTIVE

### Tiêu chuẩn có răng (`standards/` — SP0/SP1, 2026-07-07)
- **`standards/00-INDEX.md`** — bảng tổng 34 rule (tầng hard/ratchet/soft + module đo + baseline) & các lệnh
- `standards/10-data.md` … `70-ops.md` — chuẩn từng chiều; `90-exceptions-log.md` — ngoại lệ đã ký + SKIP-log
- **`standards/95-ra-soat-cong.md`** (2026-08-05) — rà 28 cổng: cổng nào ĐỌC nội dung, cổng nào chỉ kiểm sự có mặt. **Đọc trước khi tin một cổng xanh.**
- Cơ chế: `scripts/install_hooks.py` (pre-commit chặn hard+ratchet) · `scripts/scorecard.py` (điểm/chiều, không được tụt) · `scripts/checks/baseline_tool.py` (nợ chuẩn) · `pre_merge_check` bước 6-8

### Điều hành & kiến trúc
- **`../CLAUDE.md`** — hiến pháp (truth-sync 2026-07-07)
- **`ROADMAP.md`** — sổ track dài hạn + Backlog phát sinh (nhiều GĐ đã xong; Track-H = việc con người)
- **`architecture-decisions.md`** — ADR: DB-as-SoT, Nuxt-only, PG UGC, ảnh AI-only, định vị, governance
- **`api-contract.md`** — data shapes FastAPI ↔ Nuxt (enum 18 type, `/auth/*`, `/admin/*`, 2FA)
- **`don-vi-hanh-chinh-vinh-long.md`** — tham chiếu 124 xã/phường tỉnh MỚI (35p + 89x)
- **`HANDOFF.md`** — onboarding session mới
- **`HANDOFF-BRANCHES.md`** (2026-08-07) — bản đồ nhánh: nhánh nào đã hợp hết vào trunk, nhánh nào còn commit riêng, nhánh nào là trunk thực tế, worktree nào đang giữ nhánh nào. **Đọc trước khi mở bất kỳ nhánh cũ nào.**
- **`QUYET-DINH-DANG-CHO.md`** — danh sách quyết định đang chờ chủ dự án, gom từ các doc rải rác. *(Viết trong phiên 2026-08-07 bởi một session song song; nếu chưa thấy file thì session đó chưa commit xong.)*
- `entity-content-model.md` — **superseded-by** `superpowers/specs/2026-07-02-entity-split-per-kind-design.md`; giữ lại làm nghiên cứu/lộ trình gốc, KHÔNG lấy làm nguồn chỉ đạo

### Vận hành
- **`deployment-guide.md`** — deploy tarball/systemd (SSH hiện tại: root@, key vinhlong_vps); runbook các đợt deploy đã qua ở `archive/`
- **`developer-setup.md`** — dev local + **§10 kích hoạt module & env flags THẬT** (HAS_* = try-import) (⚠️ `--replace` chỉ cho fresh clone, backup trước)
- **`security-hardening.md`** — posture + kế hoạch harden (khối SSH có TIỀN ĐỀ bắt buộc — đọc kỹ)
- **`security/owasp-review-2026-08-05.md`** — rà OWASP Top 10 (2021) trên code thật, mọi kết luận kèm `path:line`
- **`incident-runbook.md`** — ứng phó sự cố (⚠️ bẫy TOTP_ENC_KEY khi rotate)
- **`runbooks/`** — runbook theo triệu chứng: `db-khong-len.md` · `deploy-hong.md` · `het-dia.md` · `launch-safety-rollback.md`; cộng 2 runbook thao-tác-dữ-liệu **cần chủ dự án duyệt riêng từng lần**: `entity-published-status-migration.md`, `personal-data-erasure.md`
- **`parallel-session-guide.md`** — chạy nhiều session song song (⚠️ bổ sung 2026-08-07: HAI workflow KHÔNG dùng chung một worktree — xem CLAUDE.md §5c)

### Nội dung & chiến lược
- **`content-creation-guide.md`** — nhập entity, chuẩn chất lượng, ảnh AI-only
- **`toi-uu-chong-ai-va-google-spam-playbook.md`** — playbook chống đọc-như-AI + chống Google spam (có marker mục đã ship)
- **`claude-desktop/`** — 3 file dán vào Claude Desktop (about-me / my-company / anti-ai-writing-style), SINH TỪ CLAUDE.md + playbook §4; nguồn đổi thì sinh lại, không sửa lệch hai nơi
- **`b2g-pitch.md`** — template pitch B2G (⚠️ tài liệu đối ngoại: chủ dự án duyệt toàn văn trước khi gửi — CLAUDE.md §4)

### Nghiên cứu design (tham khảo, có mục bị override — xem header từng file)
- **`design-rulebook.md`** — rulebook sống (đã sửa các rule mâu thuẫn thực tế ship)
- **`design-guidelines-apple-google-figma.md`**, **`travel-platform-ux-research.md`** — reference values/pattern
- **`implementation-specs.md`** — specs FE/BE/Content trích từ nghiên cứu

### Nghiên cứu văn hoá (`research/`)
- **`research/corpus-van-hoa-du-lich-vl-2026-06.md`** — chỉ mục + tổng hợp 4 báo cáo (**cửa vào duy nhất**) + 16 CSV/GeoJSON. Toàn văn 4 báo cáo gốc đã chuyển `archive/`. **Header giới hạn:** viết thời 3-tỉnh; KHÔNG dùng khung định vị/đơn vị hành chính cũ/khuyến nghị bán tour từ đây.

### Quyết định đang chờ chủ dự án (đọc → chốt → mới mở task sửa)
- **`2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md`** — 67 entity `type=event` lệch ngày âm–dương: 12 khớp · 3 lệch kỹ thuật · 14 tự mâu thuẫn · 7 có `lunar_date` nhưng `date_start` là văn xuôi · 31 chưa có `lunar_date`. **Tài liệu PHÂN TÍCH — chưa sửa một dòng dữ liệu nào.** ⚠️ Ngày của một sự kiện nằm ở SÁU ô cùng render một trang; sửa một ô thì năm ô kia nói ngược (CLAUDE.md §5c).
- **`drafts/doi-chieu-ma-hanh-chinh.md`** — đối chiếu mã hành chính chính thức ↔ `web/data.json`: Ca A đã chốt 2026-08-07; Ca B (đổi tên) + Ca C (quy ước dấu) còn chờ.
- `QUYET-DINH-DANG-CHO.md` — bản gom tổng (phiên 2026-08-07).

### Bản nháp nội dung (`drafts/`) — CHƯA ghi vào dữ liệu
5 bản nháp mô tả S+ do skill `viet-content-optimizer` sinh (`lo-10-entity-mau.md` = lô 10 entity mẫu; 4 file `2026-08-07-*` = từng entity). **Tất cả chờ chủ dự án duyệt; KHÔNG ghi vào `web/data.json`/DB, KHÔNG chạy ETL từ đây.** Đọc được như nguồn tra cứu đã dẫn nguồn kèm hạng ★.

### Specs & plans đang sống (`superpowers/`)
- `specs/2026-07-06-ui-declutter-design.md` — ĐÃ THỰC THI XONG (3 plans kết quả cùng thư mục plans/)
- `specs/redesign-concepts/00-16` — concept Ý TƯỞNG tiền-declutter: đọc cảnh báo đầu mỗi file trước khi thực thi bất kỳ sóng nào
- `plans/` — plan + kết quả thực thi từng đợt (lịch sử thi công, tin được)
- `results/` — evidence kết-đợt (R60.5 "KẾT QUẢ" trước merge); `qa/` — báo cáo QA + ảnh chụp màn hình từng đợt UI
- ⚠️ **STATUS của plan không tự cập nhật.** Ít nhất 3 plan đang ghi trạng thái lệch với thực tế đã ship — xem mục "Nghi vấn" bên dưới. Tin `results/` + ROADMAP trước, tin header plan sau.

## ⚠️ Nghi vấn lỗi thời (§3.6) — đã đánh dấu, CHƯA xử, KHÔNG tự xoá
Rà 2026-08-07 trên toàn `docs/` (trừ `archive/`). **Kết quả cổng R60.1: 155/155 file có header STATUS — 0 file thiếu.** Còn lại là 5 nghi vấn nội dung, cần chủ dự án hoặc một task riêng:

| # | Chỗ | Nghi vấn | Vì sao chưa tự sửa |
|---|-----|----------|--------------------|
| N1 | `superpowers/plans/2026-07-27-pinned-egress-security-observability.md` | STATUS ghi "implementation has not started" trong khi spec cùng tên ghi `done` và ROADMAP ghi commit `f2b50bbb`/`15f7124a` | Sửa STATUS của plan = phát ngôn về trạng thái công việc; để chủ nhánh sửa |
| N2 | `superpowers/plans/2026-07-29-zero-cost-directional-route-optimizer.md` | STATUS `active` trong khi `results/2026-07-29-zero-cost-directional-route-optimizer-evidence.md` ghi `done` | như trên |
| N3 | `superpowers/plans/2026-07-30-phase2b-generator-adoption.md` | "implementation complete locally; final review pending" từ 2026-07-30, chưa cập nhật | như trên |
| N4 | `superpowers/specs/2026-07-05-public-pages-cinematic-redesign.md` | gọi bộ token màu là **"màu 3 tỉnh"** (~12 chỗ) + đề xuất "strip timeline sáp-nhập 3 tỉnh" | Đây là **tên gọi design token**, không phải claim hành chính — nhưng chữ "3 tỉnh" trái khung §1.6. Đổi tên = đụng cả code (`codex/tri-region-color`), phải là task riêng |
| N5 | `implementation-specs.md:216` & `:227` | "bounding box **3 tỉnh**", "nghiên cứu văn hoá-du lịch **3 tỉnh**" | Cùng lớp với N4: mô tả phạm vi địa lý bằng khung cũ. Sửa chữ thì phải rà cả bảng tham chiếu |

**Đã rà và KẾT LUẬN SẠCH** (ghi lại để lần sau khỏi rà lại): nguồn ảnh cấm — mọi lần nhắc trong docs-active đều là câu CẤM, KHÔNG có hướng dẫn nào còn khuyên dùng; booking/đặt hàng/thanh toán — mọi lần nhắc đều là câu cấm hoặc mục "SKIP (không làm)"; cấp huyện — mọi lần nhắc đều có chữ "cũ/đã bãi bỏ/trước 7-2025" hoặc nằm trong `drafts/` với ghi chú `former_address`.

## `archive/` — KHÔNG làm theo
33 file lịch sử (codex prompts, blueprints 01/07, audit/QA reports, kien-truc-va-lo-trinh gốc, monitoring-setup container...; + đợt gộp 2026-07-11: 4 báo cáo research gốc, `deploy-runbook-waves-2fa-dark`, `ugc-postgres`, `module-activation-guide`). Mỗi file có header ARCHIVED ghi rõ vì sao + điểm nguy hiểm. Xem `archive/README.md`.

# docs/ — Bản đồ tài liệu (có trạng thái)

> **STATUS (2026-07-07): active — nguồn định hướng tài liệu duy nhất.** Viết lại trong đợt truth-sync (audit đa-agent 89+6 finding). Quy tắc: tài liệu chỉ đạo phải có header `> STATUS:`; mọi thứ trong `archive/` là lịch sử — **KHÔNG làm theo** (CLAUDE.md §3.6). File này mâu thuẫn tài liệu khác → CLAUDE.md thắng, rồi tới file này.

---

## Bắt đầu từ đâu?

| Bạn muốn | Đọc |
|-----------|-----|
| **Hiểu luật chơi** | `../CLAUDE.md` (hiến pháp — định vị, bất biến, nguồn việc) |
| **Hiểu kiến trúc** | `architecture-decisions.md` (ADR sống) |
| **Nạp session mới** | `HANDOFF.md` |
| **Việc dài hạn / backlog** | `ROADMAP.md` (sổ track + backlog — KHÔNG còn là danh sách tuần tự) |
| **Code FE/BE** | `implementation-specs.md` + `api-contract.md` |
| **Viết/sửa content** | `content-creation-guide.md` + `toi-uu-chong-ai-va-google-spam-playbook.md` |
| **Deploy VPS** | `deployment-guide.md` + `deploy-runbook-waves-2fa-dark.md` |
| **Setup dev local** | `developer-setup.md` |
| **Sự cố prod** | `incident-runbook.md` |

## Tài liệu ACTIVE

### Điều hành & kiến trúc
- **`../CLAUDE.md`** — hiến pháp (truth-sync 2026-07-07)
- **`ROADMAP.md`** — sổ track dài hạn + Backlog phát sinh (nhiều GĐ đã xong; Track-H = việc con người)
- **`architecture-decisions.md`** — ADR: DB-as-SoT, Nuxt-only, PG UGC, ảnh AI-only, định vị, governance
- **`api-contract.md`** — data shapes FastAPI ↔ Nuxt
- **`ugc-postgres.md`** — decision record UGC = Postgres-only
- **`entity-content-model.md`** — 17 type, STI-with-registry
- **`don-vi-hanh-chinh-vinh-long.md`** — tham chiếu 124 xã/phường tỉnh MỚI (35p + 89x)
- **`HANDOFF.md`** — onboarding session mới

### Vận hành
- **`deployment-guide.md`**, **`deploy-runbook-waves-2fa-dark.md`** — deploy tarball/systemd (SSH hiện tại: root@, key vinhlong_vps)
- **`developer-setup.md`** — dev local (⚠️ `--replace` chỉ cho fresh clone, backup trước)
- **`security-hardening.md`** — posture + kế hoạch harden (khối SSH có TIỀN ĐỀ bắt buộc — đọc kỹ)
- **`incident-runbook.md`** — ứng phó sự cố (⚠️ bẫy TOTP_ENC_KEY khi rotate)
- **`module-activation-guide.md`** — trạng thái THẬT các module backend (HAS_* = try-import, phần lớn đang bật)
- **`parallel-session-guide.md`** — chạy nhiều session song song

### Nội dung & chiến lược
- **`content-creation-guide.md`** — nhập entity, chuẩn chất lượng, ảnh AI-only
- **`toi-uu-chong-ai-va-google-spam-playbook.md`** — playbook chống đọc-như-AI + chống Google spam (có marker mục đã ship)
- **`b2g-pitch.md`** — template pitch B2G (⚠️ tài liệu đối ngoại: chủ dự án duyệt toàn văn trước khi gửi — CLAUDE.md §4)

### Nghiên cứu design (tham khảo, có mục bị override — xem header từng file)
- **`design-rulebook.md`** — rulebook sống (đã sửa các rule mâu thuẫn thực tế ship)
- **`design-guidelines-apple-google-figma.md`**, **`travel-platform-ux-research.md`** — reference values/pattern
- **`implementation-specs.md`** — specs FE/BE/Content trích từ nghiên cứu

### Nghiên cứu văn hoá (`research/`)
- 4 báo cáo + 16 CSV/GeoJSON — corpus quý cho content. **Header giới hạn:** viết thời 3-tỉnh; KHÔNG dùng khung định vị/đơn vị hành chính cũ/khuyến nghị bán tour từ đây.

### Specs & plans đang sống (`superpowers/`)
- `specs/2026-07-06-ui-declutter-design.md` — ĐÃ THỰC THI XONG (3 plans kết quả cùng thư mục plans/)
- `specs/redesign-concepts/00-16` — concept Ý TƯỞNG tiền-declutter: đọc cảnh báo đầu mỗi file trước khi thực thi bất kỳ sóng nào
- `plans/` — plan + kết quả thực thi từng đợt (lịch sử thi công, tin được)

## `archive/` — KHÔNG làm theo
25 file lịch sử (codex prompts, blueprints 01/07, audit/QA reports, kien-truc-va-lo-trinh gốc, monitoring-setup container...). Mỗi file có header ARCHIVED ghi rõ vì sao + điểm nguy hiểm. Xem `archive/README.md`.

# docs/ — Mục lục tài liệu

> Cập nhật: 2026-06-28. Tổng: 22 files docs/ + 20 files research/.

---

## Bắt đầu từ đâu?

| Bạn muốn | Đọc file |
|-----------|----------|
| **Hiểu dự án** | `ROADMAP.md` → `architecture-decisions.md` → `kien-truc-va-lo-trinh.md` |
| **Code session FE** | `implementation-specs.md` §A (component specs, CSS vars, a11y gaps) |
| **Code session BE** | `implementation-specs.md` §B (JSON-LD, SEO, middleware) |
| **Viết/sửa content** | `implementation-specs.md` §C + `content-creation-guide.md` |
| **Chạy session song song** | `parallel-session-guide.md` (template + checklist) |
| **Deploy lên VPS** | `deployment-guide.md` |
| **Setup dev local** | `developer-setup.md` |
| **Nạp session mới (handoff)** | `HANDOFF.md` |

---

## Phân loại

### Kiến trúc & quyết định (đọc 1 lần, tham khảo khi cần)
- **`ROADMAP.md`** — Source of truth: task list + execution order
- **`architecture-decisions.md`** — DB-as-SoT, Nuxt-only, PG UGC, coordinates
- **`kien-truc-va-lo-trinh.md`** — Architecture deep-dive + data schema (Vietnamese)
- **`api-contract.md`** — API data shapes giữa FastAPI ↔ Nuxt
- **`ugc-postgres.md`** — Decision record: UGC/auth = Postgres-only
- **`don-vi-hanh-chinh-vinh-long.md`** — 124 xã/phường reference

### Implementation specs (đọc trước khi code)
- **`implementation-specs.md`** — Tổng hợp specs actionable từ 3 nghiên cứu, chia theo FE/BE/Content

### Vận hành (ops)
- **`deployment-guide.md`** — Tarball deploy flow, SSH keys, systemd
- **`developer-setup.md`** — Local dev: Python, Node, Docker, env vars
- **`monitoring-setup.md`** — Prometheus/Grafana/Loki/Sentry/Umami
- **`security-hardening.md`** — Security posture assessment
- **`incident-runbook.md`** — Data breach response (NĐ91/2025)

### Hướng dẫn nội dung
- **`content-creation-guide.md`** — Entity data entry, image policy, quality rules
- **`module-activation-guide.md`** — 15 dormant modules + env flags

### Nghiên cứu thiết kế (reference — specs đã trích vào implementation-specs.md)
- **`design-guidelines-apple-google-figma.md`** (1384 dòng) — Apple HIG + M3 + Figma values
- **`design-research-2026-06-27.md`** (1033 dòng) — Gap analysis vs Apple/M3/WCAG
- **`travel-platform-ux-research.md`** (904 dòng) — UX 5 platforms du lịch

### Nghiên cứu văn hóa-du lịch (`research/` subfolder)
- 4 báo cáo phân tích (BVL corpus 194 bài, 6 tầng, 12 chiều, điểm đến chuyên sâu)
- 14 CSV/GeoJSON data (tọa độ, tuyến, tài nguyên, nguồn)
- Dùng cho: content enrichment, entity descriptions, itinerary creation

### Báo cáo (point-in-time snapshots)
- **`data-quality-report.md`** — Pass 6 (2026-06-28): score 90/100
- **`audit-findings-20260622.md`** — 110 findings (phần lớn đã fix)
- **`legacy-files-audit.md`** — web/ chỉ còn data.json/data.js/media/

### Session song song
- **`parallel-session-guide.md`** — 5 KP + template + checklist (all-in-one)

### Chiến lược
- **`HANDOFF.md`** — Onboarding prompt cho session mới
- **`b2g-pitch.md`** — B2G partnership pitch template

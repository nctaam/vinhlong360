# Spec: Chương trình "Chuẩn hoá trên world-class" — điều lệ + SP0/SP1

> **STATUS (2026-07-07): active — design ĐÃ DUYỆT (Section A+B), spec chờ chủ dự án review.**
- **Ngày:** 2026-07-07 · **Nguồn việc:** chỉ đạo trực tiếp chủ dự án ("chuẩn hoá sâu, đa chiều toàn dự án, level trên world-class")
- **3 quyết định đã chốt qua brainstorm:** (1) nghĩa = **định nghĩa bộ chuẩn mới toàn diện** rồi migrate toàn dự án; (2) cơ chế ép = **hai tầng** (gate-cứng cho lớp nguy hiểm, report-only cho lớp mềm); (3) thứ tự = **nền tảng → yếu nhất trước**.

## 1. Điều lệ chương trình (Section A — đã duyệt)

7 sub-project, mỗi SP một chu trình **spec→plan→execute→kết-đợt** riêng, nhánh riêng, merge main khi xanh. Điểm dừng tự nhiên giữa các SP để chủ dự án xem/đổi hướng.

| # | Sub-project | Nội dung cốt lõi | DoD (điểm dừng) |
|---|---|---|---|
| **SP0** | Bộ Tiêu chuẩn | `docs/standards/` — 1 file chuẩn/chiều, mỗi quy tắc có mốc tham chiếu + cách đo + tầng | Chủ duyệt bộ chuẩn; 100% quy tắc đo-được-bằng-máy hoặc checklist |
| **SP1** | Cơ chế ép 2 tầng | `scripts/checks/*` + pre-commit hook + `scorecard.py` + mở rộng `pre_merge_check.py` | Demo commit vi phạm bị chặn thật; scorecard ra bảng điểm; mỗi check có test |
| **SP2** | Data | Reconcile local↔prod (1.782 vs 1.730), shape export↔data.json, schema gate theo type, làm giàu trường 0% (season/hours/tips) THEO NGUỒN THẬT | Scorecard-data tăng; 0 entity vi phạm schema gate |
| **SP6** | Content/copy | 253 "miền Tây" trong data (phân loại ngữ cảnh như campaign tỉnh-mới), thin-content ~1.300 trang noindex nâng dần theo giọng playbook, 22 tên riêng khi có nguồn | Phủ index-worthy tăng N% (chốt N ở spec SP6); copy đạt checklist giọng |
| **SP3** | Backend | Backlog 127-finding còn lại, ruff lint+format, coverage floor module mù (B3), 4 test-debt | pytest fail-đã-biết → 0; ruff 0 lỗi |
| **SP4** | Frontend/UI | Đồng nhất theo design-rulebook đã sửa: tokens, a11y, CWV budget, quét lệch chuẩn | Checker FE 0 vi phạm gate-cứng |
| **SP5** | Docs/workflow | Lifecycle STATUS tự kiểm, template spec/plan chuẩn, plan-result bắt buộc | Checker docs 0 vi phạm |

**Nguyên tắc xuyên suốt:**
1. Không phá bất biến CLAUDE.md §2; không dịch vụ trả phí (B8); không remote-CI — mọi cơ chế chạy local Windows + VPS.
2. **Chuẩn không có cơ chế kiểm = không ban hành** (bài học 25 file archive). Mỗi quy tắc phải trả lời: máy kiểm được không? Nếu không → checklist nào, ai chạy, khi nào?
3. Chuẩn khởi tạo từ tài sản có sẵn (design-rulebook, api-contract, playbook, CLAUDE.md, entity-content-model, các audit) — hệ thống hoá + nâng + gắn cách đo, không viết từ chân không.
4. SP2-SP6 chỉ có scope-charter ở đây; spec chi tiết viết khi tới lượt (grounding lại lúc đó — tránh spec-thối như bài học declutter).

## 2. SP0 — Bộ Tiêu chuẩn `docs/standards/` (Section B — đã duyệt)

**Cấu trúc:** 8 file, mỗi file ≤300 dòng, format thống nhất:
```
# <Chiều> — Tiêu chuẩn vinhlong360
> STATUS (ngày): active — bản 1.0
## Mốc tham chiếu  (chuẩn ngoài + tài sản nội bộ làm gốc)
## Quy tắc          (R<chiều>.<số> — mỗi rule: phát biểu / tầng hard|soft / cách đo: check-module hoặc checklist)
## Ngoại lệ đã duyệt (rule-id + phạm vi + ngày + lý do)
```

| File | Mốc tham chiếu chính | Nguồn nội bộ khởi tạo |
|---|---|---|
| `00-INDEX.md` | — | Bảng tổng: rule-id → tầng → check-module → trạng thái triển khai |
| `10-data.md` | Schema.org, nguyên tắc anti-hallucination | entity-content-model (17 type), validate_data.py, §1.6 tên tỉnh, semantics verifiedAt/updatedAt, quy tắc nguồn |
| `20-backend.md` | PEP8 + ruff, FastAPI best practices | api-contract.md, backend-audit 8 chiều, B3/B4; cấm blocking-sync trong async path, bare-except |
| `30-frontend.md` | Vue style guide, WCAG 2.2 | CSS-thuần+tokens (cấm Tailwind), IconLine thay emoji-chức-năng, SSR-safety (ClientOnly cho volatile), tap-target ≥44px (trừ ngoại lệ season-ring đã ghi) |
| `40-ui-design.md` | Apple HIG, M3 (values đã trích) | design-rulebook.md là NGUỒN — file này chỉ liệt phần GATE ĐƯỢC: màu ngoài palette, emoji functional mới, motif phù-sa, microcopy honesty (cấm claim xác-minh) |
| `50-content.md` | E-E-A-T, playbook chống-AI-spam | Giọng đặc-thù-Vĩnh-Long, danh sách filler cấm, công thức-mở-bài cấm, ngưỡng độ dài theo cổng index thật (đọc từ agent/seo.py), quy tắc tên tỉnh trong content, xuất xứ đặc sản phải trong tỉnh |
| `60-docs.md` | — | STATUS header bắt buộc, lifecycle active/done/obsolete/superseded, archive policy, template spec/plan, plan-result bắt buộc khi kết đợt |
| `70-ops.md` | — | B1 backup trước data-ops, dry-run bắt buộc, tên service chuẩn (vl-agent/vl-nuxt/vl-bot), secrets không hardcode + bẫy TOTP_ENC_KEY, deploy theo HANDOFF runbook |

**DoD SP0:** chủ dự án duyệt cả 8 file; `00-INDEX.md` không có rule nào thiếu cách-đo; các ngoại lệ hiện hành (parallax signature, season-ring 22px, hamburger-nav...) được ghi thành Ngoại-lệ-đã-duyệt thay vì vi phạm ngầm.

## 3. SP1 — Cơ chế ép hai tầng (Section B — đã duyệt)

**3.1 `scripts/checks/` — mỗi check 1 module, interface chung:**
```python
# def run(files: list[str] | None) -> CheckResult
# CheckResult = {"check": str, "level": "hard"|"soft", "violations": [{"file", "line", "rule", "msg"}]}
# files=None → quét toàn repo; files=[...] → chỉ staged (cho hook, nhanh)
```
Bộ khởi điểm (mở rộng dần theo SP0):
- **hard** `check_secrets.py` — staged: pattern key/token/password hardcode; chặn stage file `.env`.
- **hard** `check_data_schema.py` — khi `web/data.json` staged: parse + id duy nhất + type thuộc 17 enum + trường bắt buộc theo type (tái dùng logic validate_data.py).
- **hard** `check_banned_claims.py` — staged `.vue/.ts/.md`: cấm THÊM MỚI "đã xác minh/đã được xác minh" (whitelist ngữ cảnh phủ định + file chuẩn/checklist nội bộ), cấm "Wikimedia/Pexels/Unsplash" như nguồn ảnh trong docs-active + code. (*docs-active* = mọi `.md` trong `docs/` NGOÀI `docs/archive/`, `docs/research/` và các dòng phủ-định/cảnh-báo — cùng định nghĩa với sweep truth-sync.)
- **hard** `check_api_contract.py` — diff staged thêm/xoá `@router.`/`@app.` route trong agent/ mà `docs/api-contract.md` không staged cùng → chặn kèm hướng dẫn.
- **soft** `check_fe_tokens.py` — màu hex/rgb ngoài tokens trong `.vue`; emoji-chức-năng mới ngoài string-context.
- **soft** `check_doc_status.py` — docs/*.md active thiếu `> STATUS:`; doc active chứa từ-khoá lỗi-thời (huyện-làm-chuẩn, 3-tỉnh-hiện-hành...).
- **soft** `check_content_voice.py` — filler-list từ `50-content.md` trong copy template FE.
- **soft** `check_thin_content.py` — đếm entity dưới ngưỡng index-worthy (report xu hướng).

**3.2 Hook:** `scripts/install_hooks.py` ghi `.git/hooks/pre-commit` (sh wrapper gọi `python scripts/checks/run_hard.py --staged`), idempotent, chạy được trên Git-Bash Windows. Ngân sách thời gian hook **<5 giây** (chỉ hard-checks, chỉ staged files). Thoát hiểm: `SKIP_CHECKS=<rule-id>` env (ghi log vào `.git/skip-checks.log`) — `--no-verify` vẫn bị CLAUDE.md §6 cấm dùng tuỳ tiện.

**3.3 `scripts/scorecard.py`:** chạy toàn bộ hard+soft trên cả repo → bảng điểm theo chiều (text + `--json`), exit code ≠0 khi có hard-violation. Là "đồng hồ world-class" chạy bất kỳ lúc nào; kết quả từng kỳ có thể dán vào plan-result.

**3.4 `pre_merge_check.py` mở rộng:** thêm bước `run_hard.py` toàn-repo + tóm tắt scorecard trước khi cho merge nhánh (giữ nguyên các bước hiện có).

**Testing SP1:** mỗi check-module có test (fixture file vi phạm/không vi phạm); test hook = chạy run_hard trên fixture staged giả lập; demo end-to-end: 1 commit cố tình vi phạm bị chặn (ghi lại trong plan-result).

**DoD SP1:** demo chặn thật; scorecard chạy ra số cho cả 7 chiều (chiều chưa có check → "chưa đo"); toàn bộ check có test; install idempotent; HANDOFF + docs/README cập nhật cách dùng.

## 4. Rủi ro & điều kiện dừng

- **False-positive chặn oan** → mọi hard-check có whitelist + SKIP_CHECKS có log; rule gây >2 lần chặn oan/tuần → hạ xuống soft, ghi vào Ngoại lệ.
- **Hook chậm** → chỉ staged + chỉ hard; đo thời gian trong test.
- **Phình phạm vi** (Q1 đã chọn hướng sâu nhất) → chốt cứng: SP0+SP1 là MỘT đợt thực thi; SP2-SP6 không khởi động khi chưa merge SP0+SP1 và chưa được chủ gật cho SP kế tiếp.
- Mâu thuẫn giữa chuẩn mới và bất biến §2 → bất biến thắng, dừng hỏi người (§4).

## 5. Ngoài phạm vi chương trình

Tính năng mới, đổi kiến trúc (DB/framework), deploy public, pháp lý Track-H, remote CI/CD, dịch vụ trả phí.

# Spec: Chương trình "Chuẩn hoá trên world-class" — điều lệ + SP0/SP1 (bản khắt khe)

> **STATUS (2026-07-07): active — design ĐÃ DUYỆT (Section A+B) + chỉ đạo bổ sung "cao hơn, khắt khe hơn, nghiêm khắc hơn"; spec v2 chờ chủ dự án review.**
- **Ngày:** 2026-07-07 · **Nguồn việc:** chỉ đạo trực tiếp chủ dự án
- **4 quyết định đã chốt:** (1) định nghĩa **bộ chuẩn mới toàn diện** rồi migrate toàn dự án; (2) cơ chế ép **hai tầng**; (3) thứ tự **nền tảng → yếu nhất trước**; (4) **mức nghiêm: khắt khe** — ratchet bắt buộc, số cứng, không đường thoát dễ dãi.

## 0. Triết lý nghiêm khắc (mới — v2)

1. **RATCHET — nợ chuẩn chỉ được GIẢM.** Mỗi rule có `baseline` (số vi phạm hiện tồn, commit vào `docs/standards/baseline.json`). Commit nào làm bất kỳ counter nào TĂNG — kể cả rule tầng soft — **bị chặn**. Nợ cũ được phép tồn tại có thời hạn; nợ mới = 0 khoan nhượng.
2. **Điểm không được tụt.** `scorecard.py` chấm 0-100/chiều. Kết đợt nào có chiều TỤT điểm so với lần chấm trước → **không merge** (lưu lịch sử điểm trong `docs/standards/scorecard-history.jsonl`, committed).
3. **Rule không máy-đo-được = không tồn tại**, trừ khi chủ dự án ký ngoại lệ TỪNG-RULE (ghi vào file chuẩn, có ngày + lý do). Không còn mặc định "checklist tay".
4. **Không skip lớp hard.** `SKIP_CHECKS` chỉ áp dụng cho rule soft, bắt buộc kèm lý do, và ghi vào `docs/standards/90-exceptions-log.md` (COMMITTED — không phải log gitignore). Check hard sai → sửa check bằng commit riêng nêu lý do, không bypass.
5. **Mốc điểm:** 90 = sàn world-class; **đích chương trình ≥95 cho mọi chiều đã kích hoạt**. Chiều chưa có check → hiển thị "chưa đo" và không được tính là đạt.

## 1. Điều lệ chương trình — 7 SP với DoD SỐ CỨNG

Mỗi SP: chu trình spec→plan→execute→kết-đợt riêng, nhánh riêng, merge khi xanh; **kết đợt bắt buộc dán scorecard vào plan-result**. SP sau không khởi động khi SP trước chưa merge + chưa có gật đầu của chủ.

| # | Sub-project | DoD số cứng (điểm dừng) |
|---|---|---|
| **SP0** | Bộ Tiêu chuẩn `docs/standards/` | Chủ duyệt 8 file; **100% rule có check-module được nêu tên** (rule chưa có module → INDEX đánh dấu `pending-check` kèm hạn SP nào phải có); 0 rule "checklist tay" không có chữ ký ngoại lệ |
| **SP1** | Cơ chế ép | Demo ≥3 kiểu commit vi phạm bị chặn thật (hard, ratchet-soft, api-contract); scorecard ra điểm 7 chiều; hook <5s (đo trong test); **100% check-module có test**; baseline.json + scorecard-history.jsonl khởi tạo |
| **SP2** | Data | **100% entity pass schema-gate theo type; phân kỳ local↔prod = 0** (reconcile xong, 1 con số entity duy nhất); shape export ≡ data.json (round-trip test pass); occurrence từ-cấm trong data = 0 ngoài whitelist committed; mọi entity RICH (index-worthy) có ≥1 `source` URL |
| **SP6** | Content | Filler-list trong data giảm ≥80% so baseline (253 "miền Tây" → ≤50, chỉ giữ văn-nói hợp lệ có whitelist); +100 entity từ noindex → index-worthy (viết theo checklist giọng, có nguồn); 22 tên riêng xử lý khi có nguồn — không có nguồn thì GIỮ, không bịa |
| **SP3** | Backend | ruff full-ruleset (E,F,W,I,N,UP,B,S,C90; complexity ≤12) = **0 lỗi**; coverage: module core (database/auth/social/server-chat-path) **≥80%**, mọi module agent/ **≥60%** (ratchet +10/đợt từ baseline tới đích); test-debt 4 test đỏ-đã-biết = 0; pytest fail = chỉ còn nhóm cần-hạ-tầng (PG local) có marker skip-lý-do |
| **SP4** | Frontend/UI | axe-core 0 violation mức serious+ trên 14 trang sweep; bundle budget per-route (đo baseline đầu SP4, đích ≤ baseline−10% và ≤200kB gz entry); LCP p75 ≤2.5s / CLS ≤0.05 (đo local 4x-slowdown); token-lệch = 0; emoji-chức-năng mới = 0 |
| **SP5** | Docs/workflow | 100% docs-active có STATUS; **broken internal link = 0** (check_links mới); spec/plan sau ngày ban hành theo template chuẩn; kết-đợt thiếu plan-result = pre_merge chặn |

**Nguyên tắc xuyên suốt (giữ từ v1):** không phá bất biến §2; không dịch vụ trả phí; không remote-CI; chuẩn khởi tạo từ tài sản có sẵn; SP2-SP6 grounding lại khi viết spec riêng.

## 2. SP0 — `docs/standards/` (8 file + 2 file máy)

Format từng file chuẩn (≤300 dòng):
```
# <Chiều> — Tiêu chuẩn vinhlong360
> STATUS (ngày): active — bản 1.0
## Mốc tham chiếu
## Quy tắc   (R<chiều>.<số>: phát biểu / tầng hard|soft-ratchet / check-module / baseline-hiện-tại)
## Ngoại lệ đã duyệt (rule-id + phạm vi + ngày + lý do + chữ ký "chủ dự án duyệt")
```

| File | Mốc tham chiếu | Nguồn nội bộ khởi tạo |
|---|---|---|
| `00-INDEX.md` | — | Bảng tổng rule-id → tầng → module → baseline → trạng thái; danh sách `pending-check` có hạn |
| `10-data.md` | Schema.org; anti-hallucination | entity-content-model 17 type; validate_data.py; §1.6 tên tỉnh; verifiedAt/updatedAt semantics; **xuất xứ đặc sản phải trong tỉnh**; RICH phải có nguồn |
| `20-backend.md` | PEP8+ruff full, FastAPI | api-contract; BE-audit; cấm blocking-sync trong async, bare-except, print-debug; route mới ↔ contract cùng commit; TDD cho code mới (heuristic: agent/*.py đổi → tests/ phải đổi cùng commit, tầng soft-ratchet) |
| `30-frontend.md` | Vue style guide, WCAG 2.2 AA | CSS-thuần+tokens (cấm Tailwind — hard); IconLine thay emoji-chức-năng (hard cho code mới); SSR-safety ClientOnly; tap-target ≥44 (ngoại lệ season-ring đã ký) |
| `40-ui-design.md` | Apple HIG, M3 | design-rulebook là nguồn; phần GATE: màu ngoài palette (hard-ratchet), motif phù-sa, microcopy honesty (hard: cấm claim xác-minh) |
| `50-content.md` | E-E-A-T, playbook | giọng đặc-thù-VL; filler-list cấm (hard cho template, ratchet cho data); công-thức-mở-bài cấm; ngưỡng độ dài = cổng index thật (đọc agent/seo.py); tên tỉnh trong content |
| `60-docs.md` | — | STATUS bắt buộc (hard); lifecycle; archive policy; template spec/plan; plan-result bắt buộc; internal-link phải sống |
| `70-ops.md` | — | B1 backup (hard: script data-ops phải gọi/nhắc backup); dry-run bắt buộc cho apply; tên service chuẩn; secrets (hard); bẫy TOTP |
| `baseline.json` (máy) | — | counter vi phạm hiện tồn theo rule — nguồn sự thật của ratchet |
| `90-exceptions-log.md` | — | nhật ký SKIP soft-rule (ai/khi/lý do) + ngoại lệ rule đã ký |

**DoD SP0** như bảng §1.

## 3. SP1 — Cơ chế ép (khắt khe hoá)

**3.1 `scripts/checks/`** — interface chung như v1, thêm trường `count` để so baseline. Bộ khởi điểm **12 module**:

| Module | Tầng | Chặn khi |
|---|---|---|
| `check_secrets.py` | **hard** | key/token/password hardcode; `.env` bị stage; entropy-string đáng ngờ trong code mới |
| `check_data_schema.py` | **hard** | data.json staged: id trùng, type ngoài 17 enum, thiếu trường bắt buộc theo type, coords ngoài bbox |
| `check_banned_claims.py` | **hard** | thêm mới "đã xác minh"/nguồn ảnh cấm (Wikimedia/Pexels/Unsplash) trong code + docs-active (docs-active = docs/ ngoài archive/ + research/, trừ dòng phủ-định/cảnh-báo) |
| `check_api_contract.py` | **hard** | thêm/xoá route agent/ mà api-contract.md không staged cùng |
| `check_tinh_cu.py` | **hard-ratchet** | counter "tỉnh Bến Tre\|Trà Vinh" (ngoài whitelist lịch-sử committed) tăng so baseline — chặn tái nhiễm sau campaign |
| `check_fe_tokens.py` | **hard-ratchet** | màu hex/rgb ngoài tokens trong .vue tăng; emoji-chức-năng mới |
| `check_doc_status.py` | **hard-ratchet** | docs-active thiếu STATUS tăng; từ-khoá lỗi-thời mới |
| `check_links.py` | **hard-ratchet** | broken internal link (docs ↔ docs, docs → file, FE route chết trong copy) tăng |
| `check_content_voice.py` | soft-ratchet | filler-list trong template FE + data (report + chặn tăng) |
| `check_thin_content.py` | soft | entity dưới ngưỡng index (report xu hướng — SP6 kéo xuống) |
| `check_test_pairing.py` | soft-ratchet | agent/*.py đổi mà tests/ không đổi cùng commit |
| `check_complexity.py` | soft-ratchet | hàm Python complexity >12 tăng (tiền trạm ruff-C90 của SP3) |

*(hard-ratchet = vi phạm tồn kho được phép theo baseline, nhưng MỌI mức tăng đều chặn commit — kể cả 1.)*

**3.2 Hook `pre-commit`** (`scripts/install_hooks.py`, idempotent, Git-Bash Windows): chạy hard + hard-ratchet trên staged + baseline-so-sánh; ngân sách <5s (đo trong test, fail test nếu vượt). `--no-verify` bị cấm bởi CLAUDE.md §6; `SKIP_CHECKS` **chỉ nhận rule soft**, bắt buộc `SKIP_REASON`, tự append vào `90-exceptions-log.md` — thiếu reason = hook từ chối.

**3.3 `scripts/scorecard.py`**: chấm 0-100/chiều từ counter các check (công thức ghi trong module, thô: 100 × (1 − nợ/baseline-gốc), floor 0); xuất text + `--json`; **tự append `scorecard-history.jsonl`**; exit ≠0 khi (a) có hard-violation, (b) bất kỳ chiều nào tụt so entry trước.

**3.4 `pre_merge_check.py` mở rộng**: các bước hiện có + run_hard toàn-repo + scorecard (chặn theo 3.3) + kiểm plan-result tồn tại cho nhánh có plan.

**Testing SP1:** fixture vi phạm/sạch cho từng module; test đo thời gian hook; test ratchet (baseline N → commit tạo N+1 bị chặn, N−1 pass và baseline tự đề nghị hạ); demo end-to-end 3 kiểu chặn ghi vào plan-result.

## 4. Rủi ro & điều kiện dừng

- **Chặn oan:** rule gây >2 lần chặn-oan/tuần → hạ tầng bằng COMMIT sửa chuẩn + ghi 90-exceptions-log (không silent-skip). Bài học: nghiêm ở cơ chế, minh bạch ở điều chỉnh.
- **Hook chậm:** chỉ staged; đo trong test; module nào >1s bị tách khỏi hook (chuyển pre_merge).
- **Ratchet kẹt việc lớn:** thao tác diện rộng có chủ đích (campaign) được cập nhật baseline TRONG CÙNG COMMIT với thay đổi + dòng giải trình trong message — vẫn bị scorecard soi tụt-điểm ở pre_merge.
- **Phình:** SP0+SP1 một đợt; SP kế cần gật đầu chủ.
- Mâu thuẫn chuẩn mới ↔ bất biến §2 → bất biến thắng, dừng hỏi người.

## 5. Ngoài phạm vi

Tính năng mới, đổi kiến trúc, deploy public, Track-H, remote CI, dịch vụ trả phí.

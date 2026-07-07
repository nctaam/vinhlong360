# Backend — Tiêu chuẩn vinhlong360
> **STATUS (2026-07-07): active — bản 1.0 (SP0).**

## Mốc tham chiếu
PEP 8 + ruff full-ruleset (đích SP3: E,F,W,I,N,UP,B,S,C90) · FastAPI best practices · api-contract.md · backend-audit 8 chiều (127 finding) · B3/B4 CLAUDE.md.

## Quy tắc
| Rule | Phát biểu | Tầng | Cách đo |
|---|---|---|---|
| R20.1 | ruff full-ruleset = 0 lỗi | pending-check (hạn: SP3) | ruff CI-local |
| R20.2 | Cấm blocking-sync call trong async path (requests/time.sleep trong handler) | pending-check (hạn: SP3) | ruff ASYNC + review |
| R20.3 | Cấm `except:` trần mới (bắt Exception cụ thể) | soft-ratchet | check_complexity (BareExceptCheck) |
| R20.4 | Coverage: core (database/auth/social/chat-path) ≥80%, agent/ ≥60% — ratchet +10/đợt | pending-check (hạn: SP3) | pytest-cov |
| R20.5 | Thêm/xoá route agent/ ⇒ docs/api-contract.md cập nhật CÙNG commit | hard | check_api_contract |
| R20.6 | B3: module mù phải có test TRƯỚC khi refactor | quy-trình-ký* | — |
| R20.7 | agent/*.py đổi ⇒ có test staged cùng commit | soft-ratchet | check_test_pairing |
| R20.8 | Cyclomatic complexity hàm ≤12 | soft-ratchet | check_complexity |

## Ngoại lệ đã duyệt
- **R20.6** là quy trình (không máy-đo trọn) — *chủ dự án duyệt (2026-07-07); vi phạm phát hiện qua review = chặn merge tay.*

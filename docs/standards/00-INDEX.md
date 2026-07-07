# 00-INDEX — Bảng tổng tiêu chuẩn vinhlong360
> **STATUS (2026-07-07): active — bản 1.0 (SP0).** Nguồn máy: `baseline.json` (ratchet) + `scorecard-history.jsonl` (điểm). Cập nhật baseline CHỈ trong cùng commit với thay đổi diện-rộng có giải trình, hoặc khi ghi nhận tiến bộ (count giảm).

Cơ chế: **hard** = 0 vi phạm mọi lúc · **hard-ratchet/soft-ratchet** = không được TĂNG so baseline (soft được SKIP có lý do + log) · **pending-check** = có hạn SP · **checklist/quy-trình-ký** = ngoại lệ chủ dự án ký trong 90-exceptions-log.md.

| Rule | Phát biểu | Tầng | Module | Baseline | File |
|---|---|---|---|---|---|
| R10.schema | id duy nhất + type∈17 + trường bắt buộc + coords bbox | hard | check_data_schema | 0 | 10-data.md |
| R10.5 | không bịa fact thực địa | checklist-ký | — | — | 10-data.md |
| R10.6 | ảnh CHỈ AI-gen | hard | check_banned_claims | 0 | 10-data.md |
| R10.7 | tên tỉnh §1.6 (whitelist per-occurrence) | hard-ratchet | check_tinh_cu | 0 | 10-data.md |
| R10.3b | trường bắt buộc PER-TYPE (registry entity_schemas) | hard-ratchet | check_data_schema | 49 | 10-data.md |
| R10.8 | RICH phải có source | hard-ratchet | check_data_schema | 0 | 10-data.md |
| R10.9 | xuất xứ trong tỉnh (cấm Cái Bè/Lai Vung/Định Yên) | soft-ratchet | check_content_voice | 0 | 10-data.md |
| R10.10 | đơn-vị-HC-cũ (huyện/thị xã X) trong giọng biên tập | pending-check (sweep riêng) | check_content_gates (class sẵn, chưa active) | ~1011 | 10-data.md |
| R20.1 | ruff lint (E/F/W; style E402/E701/E702/E501/E741 ignore) | hard-ratchet | check_ruff | 80 | 20-backend.md |
| R20.2 | cấm blocking-sync trong async (ruff ASYNC) | hard-ratchet | check_ruff | 0 | 20-backend.md |
| R20.3 | cấm bare-except mới | soft-ratchet | check_complexity | 0 | 20-backend.md |
| R20.4 | coverage core≥80 / agent≥60 | pending-check (SP3) | pytest-cov | — | 20-backend.md |
| R20.5 | route ↔ api-contract cùng commit | hard | check_api_contract | 0 | 20-backend.md |
| R20.6 | B3 test trước refactor | quy-trình-ký | — | — | 20-backend.md |
| R20.7 | agent đổi ⇒ test staged cùng | soft-ratchet | check_test_pairing | 0 | 20-backend.md |
| R20.8 | complexity ≤12 | soft-ratchet | check_complexity | 250 | 20-backend.md |
| R30.1 | cấm Tailwind | hard | check_banned_claims | 0 | 30-frontend.md |
| R30.2 | emoji chức năng → IconLine | soft-ratchet | check_fe_tokens | 626 | 30-frontend.md |
| R30.3 | màu ngoài tokens | hard-ratchet | check_fe_tokens | 1373 | 30-frontend.md |
| R30.4 | ClientOnly cho volatile | checklist-ký | — | — | 30-frontend.md |
| R30.5 | tap-target ≥44 (ngoại lệ season-ring) | checklist-ký | — | — | 30-frontend.md |
| R30.6 | axe 0 serious+ | pending-check (SP4) | axe | — | 30-frontend.md |
| R30.7 | bundle budget | pending-check (SP4) | build parse | — | 30-frontend.md |
| R40.3 | cấm claim đã-xác-minh | hard | check_banned_claims | 0 | 40-ui-design.md |
| R50.2 | filler giọng cấm (field-aware, bỏ source) | soft-ratchet | check_content_voice | 389 | 50-content.md |
| R50.3 | cấm công thức mở bài + kết sáo | soft-ratchet | check_content_gates | 58 | 50-content.md |
| R50.4 | summary+desc ≥200 ký tự | soft | check_thin_content | 245 | 50-content.md |
| R50.7 | cấm superlative trơ (không số/năm/nguồn) | soft-ratchet | check_content_gates | 34 | 50-content.md |
| R60.1 | docs-active có STATUS | hard-ratchet | check_doc_status | 29 | 60-docs.md |
| R60.4 | internal link sống | hard-ratchet | check_links | 1 | 60-docs.md |
| R60.5 | plan-result trước merge | hard (pre-merge) | pre_merge_check#8 | — | 60-docs.md |
| R70.1 | cấm secrets hardcode / stage .env | hard | check_secrets | 0 | 70-ops.md |
| R70.2 | B1 backup trước data-ops | quy-trình-ký | — | — | 70-ops.md |
| R70.5 | apply-script phải --dry-run | quy-trình-ký | — | — | 70-ops.md |

## Pending-check có hạn
- SP3: R20.4 coverage (R20.1 ruff + R20.2 async ĐÃ BẬT)
- SP4: R30.6 axe · R30.7 bundle

## Lệnh
```
python scripts/install_hooks.py            # cài pre-commit (1 lần/máy)
python scripts/checks/run_hard.py --all    # tự kiểm toàn repo
python scripts/scorecard.py                # đồng hồ world-class (append history)
python scripts/checks/baseline_tool.py     # xem nợ theo rule (--write khi ghi nhận tiến bộ)
```

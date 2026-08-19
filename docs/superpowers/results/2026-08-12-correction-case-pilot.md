# Kết quả thực thi — Correction Case Pilot (plan 2026-08-12)

> STATUS: active (cập nhật lần cuối 2026-08-19, sau commit `2d093bc1`)
> Mức Definition Ladder: **works-on-disposable-postgres + full-suite-green-at-baseline**.
> KHÔNG claim `production-proven`. KHÔNG claim SLA công khai. Mọi cờ case đang **false**; kích hoạt thuộc quyết định phát hành riêng của chủ dự án (Review Protocol mục 5).

## Phạm vi đã hoàn thành

- Task 1–17: hoàn tất, mỗi task 1–4 commit, chuỗi từ `5c1ea0dc` → `3f01c379` (xem `git log`).
- Task 18: 4/5 phần — metrics+lifecycle (`3e51c4f3`), instrumentation (`2ea3065f`), journey (`98d12888`), lấp mảnh đo lường/authority (`2d093bc1`), runbooks + tài liệu này.
- **Chưa làm**: mở rộng `scripts/smoke_e2e_chrome.mjs` (create→copy→exchange→status trên backend disposable + Chrome thật — cần phiên chạy được CDP). Accessibility gate và cổng Step 5 trọn gói đã xong (mục dưới).

## Môi trường bằng chứng

- Máy: Windows 11, Python 3.14.6, Node (vitest 4.1.9, Nuxt 4.4.8).
- PostgreSQL: **disposable**, Docker `vl360-breaker-pg`, `127.0.0.1:5433`, user `vl360`, DB `vl360_case_breaker_test`, trust-auth (không secret), schema baseline + migration đến **081**. Không chạm prod.
- Lệnh chuẩn: `PYTEST_DEBUG_TEMPROOT=C:\Users\NCTaam\AppData\Local\Temp\vl360pt`, `VL360_TEST_DATABASE_URL=postgresql://vl360:vl360@127.0.0.1:5433/vl360_case_breaker_test`, `python -m pytest -q` (exit 0 trừ baseline dưới).

## Cổng full-pilot Step 5 (chạy 2026-08-19, sau commit `2d093bc1`)

- **BE 17 suite** (đúng lệnh plan): `370 passed / 1 failed`, exit qua pipe 0 — fail duy nhất
  `test_case_policy::test_valid_nonproduction_case_activation_has_structural_credentials`
  thuộc baseline 21 có trước nhánh. `ruff check agent/cases agent/entity_write.py agent/sms_provider.py`: sạch.
- **FE 8 suite** (kèm `correction-accessibility-gate.test.mjs` mới): `101 passed`, exit 0.
- `nuxt typecheck`: exit 0. `npm run build`: exit 0 (manifest sinh tại `c61258fa`).
- `run_hard --all`: chỉ còn R20.4 (coverage.json — artifact CI sinh, đã ghi ở
  `docs/standards/90-exceptions-log.md`); R20.8 baseline 36→47 có giải trình cùng file,
  kèm trả nợ thật `rotate_receipt` 27→tách 3 helper; R30.2/R30.3 ghi nhận GIẢM (507/291).

## Số liệu kiểm chứng gần nhất

- Backend full-suite (sau `2ea3065f`): **11182 passed / 26 failed**, trong đó 21 là baseline nhánh có trước pilot (launch_safety, secure_stage_b, migration-gate…, danh sách trong `/tmp/final.txt` phiên làm việc) + 5 đã sửa ngay trong `2ea3065f`. Sau `2d093bc1` các suite bị ảnh hưởng chạy đích danh đều xanh (publication 20, work-control 23, outbox+journey+store 87, admin/service 78+58). Cổng Step 5 trọn gói sau đó: xem mục trên.
- Frontend: 2066/2067 (1 flake tải-song-song `detail-grid-containment-gate`, xanh 47/47 hai lần khi chạy riêng); `nuxt typecheck` sạch; `npm run build` exit 0.
- `run_hard --staged` sạch ở mọi commit; `run_hard --all`: chỉ còn R20.4 (artifact CI).
- Đối soát legacy (trên fixture PG): total 5 = 1 correction + 1 moderation_link + 1 manual_triage + 1 rejected + 1 duplicate; reconcile `passed: true`; tamper → `ledger_rows_match: false`. Chưa nhập thật production (đúng Review Protocol mục 4).

## Trạng thái cờ tại thời điểm ghi

`CASE_KERNEL_ENABLED=false`, `CORRECTION_INTAKE_ENABLED=false`, `CORRECTION_ADMIN_ENABLED=false`, `CORRECTION_ASSISTED_ENABLED=false`, `CORRECTION_PUBLICATION_ENABLED=false`. Noindex toàn site vẫn bật.

## Sai lệch so với plan (đều đã báo chủ dự án trong phiên)

1. Migration **081** (chủ duyệt 2026-08-19): 080 tự mâu thuẫn — trigger đóng băng cả hai cột vòng đời nó vừa tạo.
2. Kiểm chứng projection **không** ghi `attributes.verifiedAt` (giữ §1.7 CLAUDE.md).
3. Trạng thái xuất bản item **suy ra** từ change set, không lưu cột.
4. Task 17 **không** thêm cờ config — freeze phải sống sót trôi dạt env.
5. Assisted intake sửa `service.py` ngoài danh sách file Task 13 (bắt buộc để cùng transaction).

## Rủi ro chưa đóng

- ~35 commit chưa qua rà soát độc lập (Review Protocol mục 6) — quota ultrareview hết, cần credit.
- Accessibility/smoke chưa có → chưa có bằng chứng trình duyệt; đường dẫn artifact trình duyệt: **chưa tồn tại**.
- Bốn kiểm thử journey spec (Zalo handoff, provider outage giữa journey, ReviewCase, legacy-trong-journey) đang phủ **rời rạc** ở suite từng task, chưa gom một mạch.
- Flake FE `detail-grid-containment-gate` khi chạy song song (backlog).

## Điều kiện trước khi bật bất kỳ cờ nào

1. Chạy trọn cổng Step 5 Task 18 (17 suite BE + ruff + 8 suite FE + typecheck + build + `run_hard --all`) và cập nhật mục "Số liệu" ở trên bằng exit code thật.
2. Hoàn tất browser smoke (accessibility gate đã có; smoke CDP còn thiếu).
3. Rà soát độc lập chuỗi commit.
4. Quyết định phát hành có tên người trực và bằng chứng năng lực (`public_sla_eligible` chỉ là input, không phải công tắc).

# Kết quả thực thi — Correction Case Pilot (plan 2026-08-12)

> STATUS: active (cập nhật lần cuối 2026-08-20, sau commit `ecb19c7b`)
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

## Rà soát đối kháng 2026-08-20 (workflow 12 agent)

12 phát hiện được nêu; 8 cái xếp hạng cao nhất bị đưa qua vòng **phản biện có chủ đích
bác bỏ** (mỗi chiều 2 cái). Kết quả: **7 đứng vững, 1 bị bác** (`public_api.py:161`
— chủ thể rate-limit `request.client.host`: cả hai tiền đề sai với topology thực).
4 phát hiện xếp hạng thấp **chưa qua phản biện** — ghi lại nguyên trạng, chưa được coi là đã chứng minh.

**Đã sửa trong đợt này** (`7df5529c`, `af21a845`, `837705df`):

| Khiếm khuyết | Vị trí | Vì sao nó nguy hiểm |
|---|---|---|
| Client nói snake_case, API chỉ nhận camelCase | `useCorrectionCases.ts` | Toàn bộ hành trình người dân **422**, và trang đổ lỗi cho mã của họ |
| `configure_case_contact` không được gọi | `wiring.py` | Mọi thông báo người dân đã đồng ý nhận sẽ 500 đúng lúc cần |
| `correction.escalated` không có bản mẫu | `outbox.py` | Không gửi được, và **làm hỏng cả lượt dispatch** |
| Cả lô gửi trong MỘT transaction | `outbox.py` | Lỗi giữa chừng → **gửi lại SMS cho người đã nhận** |
| Kernel không có composition root | `wiring.py` (mới) | Bật cờ = router đã mount trả 500 ngay request đầu |

**Đã đóng tiếp 2026-08-20 đợt 2** (`72509165`, `1abe22ae`, `f989180f`, `9c9331d0`):

1. **Kết luận bị gộp** — `domain.disposition_for` ánh xạ đủ 7 kết luận sang họ của nó;
   `UNDETERMINED` nay chỉ còn nghĩa "chưa có phán quyết". Người bị từ chối thấy đúng lý do
   (kèm "bạn có thể gửi thêm nguồn" khi đúng) và **thấy được nút phản hồi**. Trường
   `outcome` công khai nay là phán quyết, không còn là id dòng dữ liệu — trước đó id đó
   còn bị render làm tiêu đề mục.
2. **Cổng quyết định đi vòng** — `build_change_set` join phán quyết mới nhất và từ chối
   mọi item không được phán `corrected`. Mới nhất, vì một lần phúc tra có thể lật lại.
   5 fixture ở 4 suite trước đây dựng change set mà không có phán quyết nào (một cái còn
   ghi docstring "đã quyết định rồi") — nay phải đi qua cổng thật.
3. **Người trực không làm việc được** — `domain.holds_authority` dịch một lần giữa hai bộ
   từ vựng và hiểu `"*"`. Bản nháp đầu ánh xạ `cases:high_risk → case.supervisor` và bị một
   test có sẵn bác đúng: giám sát ≠ thẩm quyền rủi ro cao. Thẩm quyền đó **chưa hề tồn tại**,
   nên đã thêm `case.high_risk` vào registry (cấp cho vai `admin`) thay vì mượn tên hàng xóm.
   Hàng đợi 403 nay nói rõ là thiếu quyền hay hỏng kết nối.
4. **Rollback ghi lời khai chưa kiểm chứng** — before-state đọc từ chính entity dưới khoá,
   đúng như `agent/public_api.py` vẫn làm cho báo cáo legacy. Trường không tồn tại thì undo
   về không-tồn-tại, không về phỏng đoán.

Phụ: journey suite trước đây **không chạy lại được** (NOW đông cứng → hit rate-limit không
bao giờ hết hạn); fixture nay dọn cửa sổ, chạy hai lượt liên tiếp đều xanh.

**Đợt phản biện 3 (2026-08-20)** — 6 agent, mỗi phát hiện 2 góc (một người *phải* cố bác,
một người xét mức hại). Kết quả: retention **2/2 xác nhận**, escalation **2/2 xác nhận**,
deadline **1 bác / 1 xác nhận** — nhưng cả hai độc lập tìm ra cùng một sự thật sâu hơn.
Đã đóng cả ba (`66487aaa`, `6b7bb980`):

1. **Xoá mất sự đồng ý 10 phút sau khi được cho** — `purge_expired_contact_challenges` quét
   theo `expires_at`, mà đó là cửa sổ 10 phút của mã OTP và bước xác minh **không nới nó**.
   Dòng đã-xác-minh là thứ DUY NHẤT `verified_contact_for` đọc, nên sau lượt dọn theo lịch,
   mọi thông báo người dân đã đồng ý đều bị chặn — **im lặng**, dưới cùng mã lỗi
   `suppressed_at_delivery` như khi họ chủ động rút. Nay chỉ quét mã chưa dùng; dòng đã xác
   minh là **hồ sơ đồng ý**, nghỉ cùng địa chỉ nó cho phép (kệ 90 ngày).
2. **Không ai nhìn đồng hồ lời hứa** — `AT_RISK`/`BREACHED` có trong từ vựng từ đầu và
   **chưa từng được ghi**; `scan_escalations` **không có nơi gọi nào**. Hệ quả: người trễ 3
   ngày vẫn thấy "Đúng hạn", hàng đợi xếp hồ sơ trễ như hồ sơ mới, và không việc giám sát nào
   được tạo. `domain.promise_health_at` suy ra sức khoẻ từ chính đồng hồ (RECOVERY đã ghi thì
   vẫn thắng); task `case-promise-watch` 10 phút/lần (no-op khi cờ tắt) đóng dấu lại cho hàng
   đợi rồi chạy escalation.
3. **Hạn đã lỡ vẫn được gọi là còn hiệu lực** — `next_update_at` **cố ý không đổi**: đó là bản
   ghi điều đã hứa, sửa nó là xoá dấu vết đã lỡ. Thay vào đó trang thôi nói dối: khi trễ, câu
   chữ nói đã trễ và hồ sơ đã được nâng ưu tiên, và nhãn đổi thành "Hạn đã hứa".

Kèm: runbook nói "lease 15 phút" (thực tế 30) và "hết lease thì scan escalation" (thực tế
trigger là đồng hồ quá hạn) — đã sửa cho khớp mã.

**Không còn phát hiện nào của hai đợt rà soát để mở.**

## Quét sâu đợt 3 (2026-08-20) — nhắm vào mặt chưa ai soi

4 chiều mới: **mã viết trong chính phiên này**, đồng thời, chất lượng test, schema+legacy.
12 agent; 8 claim qua phản biện, **4 đứng / 4 bị bác**. Ba lỗi nữa do tôi tự đọc lại mà thấy.

**Lỗi trong mã của chính đợt sửa trước** (`3e50074d`, `c2496648`, `dea736f6`):

1. `open_case_clocks` chọn `cases.promise_health` — **cột chưa bao giờ tồn tại**. Query ném
   UndefinedColumn vào `except` của task → log, nuốt, `return 0`. Bản vá cho 2 phát hiện
   đã-xác-nhận **chết ngay khi sinh**. Test của tôi dùng double ghi âm và assert *văn bản*
   câu SQL, nên nó vui vẻ chấp nhận tên cột không có thật.
2. `settings.cors_origins_list` là **@property**, `wiring.site_origin` gọi nó như hàm →
   TypeError → `wire_case_kernel` nuốt → **composition root không lắp gì cả**. Test xanh vì
   fake settings của tôi cấp một callable, dựng theo giả định sai của chính tôi.
3. `receipt_target_seconds = 5` và đồng hồ receipt được ghi cùng transaction với hồ sơ, nên
   nó **quá hạn vĩnh viễn và đã thoả mãn theo cấu tạo**. Đếm nó → mọi hồ sơ đọc ra BREACHED
   30 giây sau khi nhận: mọi người dân được báo "đã trễ", mọi hồ sơ bị đóng dấu lại, và
   **mỗi hồ sơ từng tồn tại sinh một việc giám sát**. Tôi lọc ở projection + sweep rồi dừng;
   verifier bắt được nửa còn lại trong `work_control` (escalation scan + queue health).

**Lỗi có sẵn, đã sửa** (`dea736f6`, `ecb19c7b`):

4. `recuse_actor` huỷ **bất kỳ** việc nào theo id, không kiểm sở hữu: một operator chỉ có
   `service.operator` đá được đồng nghiệp khỏi việc R3 đang làm dở; lease biến mất, và audit
   ghi rằng *kẻ tấn công* đã rút lui.
5. **CI chưa từng chạy một test PostgreSQL nào của case kernel** — job đặt `DATABASE_URL`,
   test gate bằng `VL360_TEST_DATABASE_URL`. Tất cả SKIP im lặng, và comment ngay đó khẳng
   định điều ngược lại. Đây là lý do gốc khiến các lỗi trên lọt được vào commit.
6. `reconcile_import` báo `source_digest_unchanged: True` **cứng** trong khi
   `legacy_intake_records` không lưu digest nào — bằng chứng cutover cho một tính chất chưa
   ai kiểm. Nay nhận `expected_digest` (CLI đã đòi sẵn `--input-digest`); không có thì báo
   `None` = *chưa kiểm*, và `passed` đòi mọi mục phải thật sự True.

**Guard mới** (`cefd17b0`): `test_case_sql_contract.py` bắt PostgreSQL **PREPARE 107/111 câu
SQL** của package — 4 câu còn lại dựng động, được đếm và ratchet. Kèm hai test canh chính
guard: một cái đỏ nếu bộ thu ngừng tìm thấy gì, một cái nạp đúng cột ma của lỗi #1.

**Bị bác** (4): test tautology ở `test_case_contact` (là lỗ mutation-coverage, không phải lỗi
sản phẩm), một cái re-report lỗi đã sửa, `complete_work_item` (không có route `/work/complete`),
và `sms_provider` (thật, nhưng đã sửa trước đó).

## Rủi ro chưa đóng

- ~40 commit: đã qua **một** vòng rà soát đối kháng tự động (mục trên), **chưa** qua rà soát người/ultrareview (Review Protocol mục 6).
- Accessibility/smoke chưa có → chưa có bằng chứng trình duyệt; đường dẫn artifact trình duyệt: **chưa tồn tại**.
- Bốn kiểm thử journey spec (Zalo handoff, provider outage giữa journey, ReviewCase, legacy-trong-journey) đang phủ **rời rạc** ở suite từng task, chưa gom một mạch.
- Flake FE `detail-grid-containment-gate` khi chạy song song (backlog).

## Điều kiện trước khi bật bất kỳ cờ nào

0. ~~Phản biện và xử lý các mục rà soát 2026-08-20~~ — **xong**: cả 7 phát hiện
   đã-phản-biện đều đã đóng (xem mục trên).
1. Chạy trọn cổng Step 5 Task 18 (17 suite BE + ruff + 8 suite FE + typecheck + build + `run_hard --all`) và cập nhật mục "Số liệu" ở trên bằng exit code thật.
2. Hoàn tất browser smoke (accessibility gate đã có; smoke CDP còn thiếu).
2b. **Xem vòng CI đầu tiên sau khi `VL360_TEST_DATABASE_URL` được thêm** — các test
   PostgreSQL của case kernel chưa từng chạy trên CI, nên vòng đầu có thể lộ fail có sẵn.
3. Rà soát độc lập chuỗi commit (vòng tự động đã có; vòng người chưa).
4. Quyết định phát hành có tên người trực và bằng chứng năng lực (`public_sla_eligible` chỉ là input, không phải công tắc).

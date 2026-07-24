> STATUS: active - amendment approved in session 2026-07-20; supersedes only Task 45 execution details in `2026-07-13-launch-safety-gate-design.md` and plan lines 5926-6383. The bounded backend extension is defined in `docs/superpowers/specs/2026-07-24-bounded-backend-regression-design.md`.

# Thiết kế sửa Task 45 - evidence gate không tự xung đột

## 1. Mục tiêu

Giữ nguyên mục tiêu Launch Safety: ghi bằng chứng có thể tái lập cho toàn bộ gate, không deploy, không đụng prod, không mở `noindex`, và không thay đổi trạng thái H1/H2/owner authorization. Amendment này chỉ sửa topology thực thi Task 45 sau khi audit phát hiện plan cũ tự xung đột ở Compose, browser smoke và clean-HEAD snapshot.

## 2. Các quyết định

1. **Không bọc Nginx integration trong một Compose thứ hai.** `test_nginx_boundary.py` và các fixture integration tiếp tục tự sở hữu Compose/project/cleanup. Release gate chạy trực tiếp pytest integration rồi ghi kết quả `compose-nginx-opt-in`.
2. **Browser smoke chạy trên Nuxt output thật.** Sau `npm run build`, release gate khởi động trực tiếp `.output/server/index.mjs` trên loopback port tạm, chờ `/` và `/sw.js`, đặt `SMOKE_BASE_URL`, chạy `npm run smoke:launch-safety`, rồi dừng đúng process. Không dùng text-only `stub_upstream.py` làm browser target.
3. **Evidence tích luỹ ngoài worktree.** Mỗi command ghi/upsert vào state JSON tạm ngoài repo. Chỉ sau khi toàn bộ required/opt-in gate kết thúc mới render Markdown canonical. Nhờ vậy Docker integration luôn archive một clean committed `HEAD`, không bị result document đang đổi làm fail source-safety.
4. **Task 45 giữ evidence-only Commit B có chủ đích.** Commit A chứa recorder, harness, tests và CI/release wiring làm nền; các remediation follow-up đã duyệt có thể nâng current HEAD trước matrix. Ma trận cuối luôn chạy từ clean current HEAD và bind current full revision. Commit B chỉ chứa evidence Markdown được render từ kết quả thật. Không amend/squash tự động.
5. **Giữ nguyên interface release gate cũ.** Các tham số, helper, warning semantics, migration/data/auth/E2E checks hiện có vẫn hoạt động. Launch Safety gate được thêm theo hướng additive. Default gate tiếp tục tổng hợp lỗi và trả `1`; opt-in chỉ chạy sau khi default gate xanh, và lỗi opt-in trả nguyên exit code sau khi đã record + cleanup.
6. **Opt-in phải được yêu cầu tường minh.** Thêm hai switch độc lập `-RunLaunchSafetyDockerOptIn` và `-RunLaunchSafetyBrowserOptIn`; invocation mặc định không start Docker, Chrome hay preview. Final evidence invocation truyền cả hai switch.
7. **Backend full regression dùng extension bounded đã duyệt.** `backend-full-regression` vẫn là một evidence row duy nhất và gọi `python scripts/ops/run_backend_regression.py --deadline-seconds 7000`; `pytest-xdist>=3.6,<4` chỉ là dev/test dependency trong `requirements-dev.txt`, không vào production package.

## 3. Topology thực thi

### 3.1 Required/default gates

Release gate chạy tuần tự và ghi các section:

- `artifacts`
- `backend-focused`
- `frontend-focused`
- `rollback-local-rehearsal`
- `backend-full-regression`
- `frontend-serial-regression`
- `source-scans`
- `known-resource-timeout`
- `external-gates`

`source-scans` dùng `python scripts/checks/run_hard.py --all`, quality-gate tests, PowerShell harness contract và `git diff --check`. `known-resource-timeout` chỉ ghi chú timeout tài nguyên đã biết khi chạy song song; nó không nới functional expectation. `external-gates` luôn giữ `H1=blocked`, `H2=blocked`, `owner=not-authorized`.

`backend-full-regression` vẫn là một evidence row duy nhất và được thực thi bằng bounded two-phase runner đã duyệt: Phase A chạy serial toàn bộ suite trừ `tests/launch_safety/test_closed_installer.py`; Phase B chỉ chạy module đó với đúng hai xdist workers. Không suite backend nào khác được phép chạy song song.

Default gate chạy hết để ghi đủ chẩn đoán và giữ contract tổng hợp hiện tại. Nếu bất kỳ functional section mặc định nào đỏ, script trả `1`, không chạy opt-in và không cho render final evidence.

### 3.2 Docker opt-in

Docker path chỉ chạy khi có `-RunLaunchSafetyDockerOptIn`. Trước setup, gate bắt buộc worktree sạch (`git status --porcelain --untracked-files=all` rỗng), rồi kiểm tra Docker CLI, context và daemon đúng một lần.

- Không yêu cầu Docker opt-in: ghi `not-requested` cho `postgres-opt-in` và `compose-nginx-opt-in`, không setup; trạng thái này không hợp lệ cho final evidence.
- Thiếu CLI: ghi `docker-cli-unavailable` cho hai Docker section và không setup.
- Daemon không dùng được: ghi `docker-daemon-unavailable` cho hai Docker section và không setup.
- PostgreSQL: `Invoke-RecordedComposeHarness` sở hữu `docker-compose.postgres.yml`, chỉ publish `127.0.0.1:55432`, snapshot/restore env và ưu tiên exit `primary > cleanup > recorder`.
- Nginx/network: pytest integration tự sở hữu Compose và cổng `127.0.0.1:18080`; release gate không start outer Compose. Clean-tree preflight ở gate bảo đảm cả test dùng `ComposeProject` lẫn `test_nginx_boundary.py` trực tiếp đều đọc đúng Commit A.

### 3.3 Browser opt-in

Browser path độc lập với Docker và chỉ chạy khi có `-RunLaunchSafetyBrowserOptIn`. `launch_safety_browser_e2e.mjs` bổ sung `--probe-browser` dùng chính `findChrome()` hiện có: exit `0` khi tìm thấy, exit `3` khi không có browser, exit `2` cho invocation lỗi; probe không start browser, không tạo profile và không gọi network. Nhờ đó release gate không duy trì candidate list thứ hai và có parity Chrome/Edge/per-user/macOS/Linux.

- Không yêu cầu browser opt-in: ghi `browser-opt-in=skip/not-requested`, không probe/start; trạng thái này không hợp lệ cho final evidence.
- Probe báo không có browser: ghi `browser-opt-in=skip/chrome-unavailable`; Docker/Nginx path không bị ảnh hưởng.
- Có browser: chọn loopback port bằng bounded bind/start retry để tránh TOCTOU, khởi động Node output server với `HOST/NITRO_HOST=127.0.0.1` và `PORT/NITRO_PORT=<port>`, chờ readiness, chạy smoke với `SMOKE_BASE_URL`, lưu stdout/stderr có giới hạn, dừng process trong `finally`, khôi phục env chính xác, rồi ghi pass/fail thật.

## 4. Evidence model

`record_launch_evidence.py` cung cấp:

- `CommandEvidence(command, exit_code, summary, status)` với status `pass|fail|skip`.
- `HarnessResult` và `resolve_harness_result(primary_exit, cleanup_exit)`.
- CLI `record`, `harness-result`, `render`.
- State JSON versioned, deterministic, upsert theo section; chạy lại không nhân đôi dòng.
- `render --final` fail nếu thiếu bất kỳ section nào, external gate khác giá trị đã chốt, hoặc một functional section bắt buộc không `pass`: `artifacts`, `backend-focused`, `frontend-focused`, `rollback-local-rehearsal`, `backend-full-regression`, `frontend-serial-regression`, `source-scans`.
- Opt-in section chỉ được `pass` hoặc `skip` với prerequisite reason đã liệt kê (`docker-cli-unavailable`, `docker-daemon-unavailable`, `chrome-unavailable`). `not-requested` không được render final. `known-resource-timeout` và `external-gates` là hai exception thông tin duy nhất.
- Markdown có `> STATUS:` trong 10 dòng đầu, ghi revision, timestamp, command/exit/status/summary đã redact và không claim live five-minute SLA hay deploy/prod readiness.

State mặc định nằm trong thư mục temp; release gate truyền path tường minh và xoá state sau khi render thành công hoặc giữ lại khi fail để điều tra. Không ghi secret, URL có credential hay output không giới hạn.

## 5. CI và tương thích

- CI mặc định thêm Python contract test và PowerShell executable contract test vào job unit/static hiện có.
- Opt-in integration chỉ chạy ở job có Docker/Chrome dependency được provision rõ ràng; không tái sử dụng Postgres port `5432` của job chung.
- Không thay literal contract đang được `tests/test_release_quality_gates.py`, AdminCP và smoke tests kiểm tra: `--db-check`, quality budgets, `vue-tsc`, `smoke_e2e_chrome.mjs`, `RequireE2E`, auth/admin gates.
- Thêm contract cho browser probe-only và chứng minh invocation mặc định của release gate không gọi Docker, browser probe hay preview.

### 5.1 Scope delta so với plan cũ

Trong phạm vi amendment 2026-07-20 ban đầu, ngoài bảy file Task 45 đã liệt kê, amendment cho phép sửa đúng hai surface cần thiết để loại duplicate browser resolver:

- `scripts/launch_safety_browser_e2e.mjs`: thêm `--probe-browser`, không đổi behavior smoke hiện có.
- `tests/launch_safety/test_launch_matrix_contract.py`: test probe-only không tạo browser/profile/network và giữ nguyên script `smoke:launch-safety` hiện có.

Phạm vi bổ sung cho runner, runner contracts, dev-only xdist dependency, CI/release wiring và authority documents được điều chỉnh bởi `docs/superpowers/specs/2026-07-24-bounded-backend-regression-design.md`; phạm vi đó không bị giới hạn bởi clause hai surface của amendment 2026-07-20 ở trên.

Không thay Compose harness, integration fixture, Nginx config hay service-worker production code.

## 6. TDD và verification

1. Viết Python/PowerShell contract tests, chạy và thấy RED vì recorder/harness chưa tồn tại.
2. Implement tối thiểu tới GREEN.
3. Commit A khi focused tests, browser probe contract, source checks và diff-check xanh.
4. Từ clean current HEAD, bind state với current full revision rồi chạy ma trận theo phase tuần tự: backend focused, backend full qua bounded runner (Phase A serial; chỉ `test_closed_installer.py` dùng đúng hai xdist workers), frontend focused/full serial, typecheck, build, source/config gates, rồi gọi release gate với cả hai opt-in switch. Docker/browser unavailable được ghi skip chính xác; `not-requested` không được chấp nhận.
5. Render evidence từ state thật, tự kiểm completeness/redaction, commit B chỉ chứa result document.
6. Review spec-compliance, code quality và whole-workstream trước khi kết thúc nhánh.

## 7. Tiêu chí nghiệm thu

- Không còn port collision hoặc nested ownership giữa outer Compose và integration tests.
- Browser smoke chứng minh service-worker/cache behavior trên Nuxt output thật.
- Docker integration chạy từ clean committed `HEAD`.
- Mọi section có đúng một bản ghi canonical; skip có lý do chính xác và xảy ra trước setup.
- Primary/cleanup/recorder failure giữ đúng precedence; helper chỉ emit một `System.Int32`.
- Default gate đỏ trả `1` sau khi ghi đủ chẩn đoán; opt-in chỉ chạy sau default xanh và trả nguyên exit code đầu tiên theo thứ tự thực thi.
- Invocation mặc định không tạo Docker container/network/volume, browser profile hay preview process.
- Main worktree và dữ liệu thật không bị chạm; không deploy/push/secret/prod action.

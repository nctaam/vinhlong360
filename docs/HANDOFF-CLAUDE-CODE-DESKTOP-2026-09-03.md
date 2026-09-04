# Handoff cho Claude Code Desktop - 2026-09-03

> STATUS (active): handoff instructions and local evidence constraints; not a release approval.

Authority: config/release-authority.json

Đây là prompt tiếp quản mới cho một session Claude Code Desktop đã được mở lại.
Đọc toàn bộ file này trước khi sửa code.

## Prompt copy nguyên khối

Bạn đang tiếp quản repository `vinhlong360-correction-case-pilot` trên máy local.
Mục tiêu là xử lý các blocker kỹ thuật còn lại và tạo lại bằng chứng local một cách
trung thực. Không được biến local rehearsal thành staging/production proof.

### Bắt buộc trước khi làm gì

1. Đọc `CLAUDE.md` và tuân thủ nó như hiến pháp thực thi.
2. Đọc `docs/ROADMAP.md`, `docs/runbooks/proof-first-pilot-acceptance.md`,
   `docs/HANDOFF.md` và file này.
3. Chạy `git status --short`, ghi nhận dirty worktree và tuyệt đối không dùng
   `git reset --hard`, `git checkout --`, `git clean -fd`, hoặc xoá thay đổi của
   người khác.
4. Không push, không commit, không deploy, không sửa production, không đọc hoặc
   truyền production `.env`, không gọi provider thật và không tạo secret thật.

### Evidence hiện có

- Pilot acceptance gate hiện là `NO_GO`; release verifier hiện là `BLOCKED`.
- Không được thay đổi verdict này để làm cho báo cáo xanh.
- PostgreSQL disposable contention đã pass trên `127.0.0.1:55432`.
- Backup/restore PostgreSQL local đã pass nhưng không có offsite/RPO/RTO/HA proof.
- Monitoring receiver local đã nhận alert nhưng alert được inject local; chưa phải
  production monitoring proof.
- Browser worker/cache smoke đã pass trên Nuxt build local bằng Chrome thật.
- Direct closed-boundary probe fail với `public-internal-route-exposed` ở
  `/_internal/launch-readiness`.
- Closed-release installer đã pass phần package verification, tree swap,
  persistent-data handling và systemd-unit materialization trong Linux container.
- Full rollback orchestration chưa pass vì container rehearsal thiếu `node` ở browser
  phase; một lần trước cũng fail đúng tại `agent-data-required` vì fixture không seed
  `release/agent/data`.
- Các bằng chứng local được lập trong `artifacts/runtime-drills/`; index chính là
  `artifacts/runtime-drills/index.json`.
- `artifacts/runtime-evidence-gaps.json` là probe read-only. Không đổi nó thành
  `EXECUTED` nếu không có execution receipt thật.

### Công việc ưu tiên P0

#### 1. Sửa và kiểm tra closed boundary

- Truy nguyên route `/_internal/launch-readiness` qua cả Nuxt trực tiếp và Nginx.
- Phân biệt rõ operator/internal authority với public authority; không xoá endpoint
  cần cho vận hành chỉ để làm test pass.
- Sửa ở lớp đúng (routing/Nginx/app) nếu root cause xác nhận thuộc source.
- Thêm regression test cho public request tới route này và cho operator request hợp lệ.
- Chạy lại probe closed boundary với local build và ghi artifact mới, gắn rõ scope
  `LOCAL_BUILD_ONLY` hoặc `LOCAL_REHEARSAL_ONLY`.

#### 2. Hoàn thiện local rollback orchestration

- Dùng fixture có đầy đủ:
  - archive closed đã verify;
  - release hiện hữu có `release/agent/data` thật;
  - persistent root bên ngoài release;
  - sentinel local rehearsal;
  - runtime authority hooks là executable regular files không có symlink component.
- Không dùng symlink trên mounted Windows path.
- Chạy trong môi trường có `node` thật cho browser phase, hoặc tách browser phase
  thành một bước host-side có evidence riêng; tuyệt đối không giả lập browser pass.
- Nếu vẫn bị block, ghi nguyên nhân, exit code và artifact; giữ
  `closed_verified=false`, `stage3_claim=false`, `live_sla_proven=false` khi chưa
  hoàn tất toàn chuỗi.
- Không gọi kết quả này là staging rollback verification.

#### 3. Kiểm tra và sửa integrity của evidence index

- Xác nhận mọi path trong `artifacts/runtime-drills/index.json` tồn tại thật.
- Mỗi entry phải có status, scope, evidence path và limitation.
- Không sửa artifact cũ tại chỗ để đổi kết quả; tạo artifact mới cho mỗi lần chạy.

### Công việc ưu tiên P1 - control plane

Chỉ sửa sau khi có test thất bại hoặc reproduction rõ ràng, từng vấn đề một:

1. Runner phải cập nhật `bundle.gate` trước khi ký attestation, tránh stale digest.
2. Acceptance verifier phải nạp countersignature artifact thay vì coi file rời là
   đã được tích hợp.
3. Countersigner fingerprint phải bao gồm counts và các trường được claim.
4. `offline-owner` phải dùng canonical absolute path độc lập checkout.
5. `ci-secret` không được tin chỉ vì `GITHUB_ACTIONS`; cần kiểm tra custody/issuer
   thực tế theo contract hiện có.
6. Authority checker stale phải được nối vào release verifier/gate.
7. Gate phải yêu cầu decision records được tracked, checksum-bound và ký đúng vai trò;
   không tự ký hoặc tự chọn option thay owner/legal/provider/residency.
8. Sửa `.gitignore` để bảo vệ đúng `*.key`, sau đó thêm test nếu repo có contract test.

### Kiểm thử bắt buộc

Chọn lệnh phù hợp với thay đổi, không chạy big-bang vô ích:

```powershell
python -m pytest tests/integration/test_cross_boundary_proof.py -q
python -m pytest tests/integration/test_countersign_pilot_acceptance.py tests/control_plane/test_attestation.py -q
python -m pytest tests/launch_safety/test_rollback_runbook.py -q
python -m pytest tests/launch_safety/test_closed_installer.py -q
python -m pytest tests/integration/test_probe_runtime_evidence.py -q
```

Nếu thay đổi frontend:

```powershell
cd web-nuxt
npm run typecheck
npx vitest run
node scripts/check-tri-region-color-debt.mjs
cd ..
```

Mọi failure ngoài baseline phải được triage; không đánh dấu pass bằng cách nới test.

### Quy tắc evidence và an toàn

- Mọi receipt phải ghi command, native return code, timestamp, checksum/provenance
  và scope.
- `LOCAL_ONLY`, `LOCAL_BUILD_ONLY`, `LOCAL_DISPOSABLE_REHEARSAL_ONLY` không được
  trình bày như production/staging evidence.
- Không tạo owner/legal/provider/residency/CI sign-off giả.
- Không gọi `--external-sandbox` nếu không có sandbox thật.
- Không dùng provider, object store, VPS, DNS, Cloudflare hay production endpoint.
- Không xoá artifact cũ hoặc scratch của người khác; chỉ dọn tài nguyên disposable
  do session này tạo sau khi lưu receipt.

### Báo cáo cuối session

Kết thúc bằng báo cáo ngắn có các mục:

1. Files changed.
2. Commands/tests run và kết quả thật.
3. Evidence artifacts mới, kèm scope.
4. Root cause đã xác nhận và thay đổi tương ứng.
5. Blockers vẫn còn, đặc biệt external proof/approval.
6. Xác nhận `NO_GO/BLOCKED` vẫn được giữ nguyên.

Sau khi hoàn tất, dừng để Codex thực hiện review độc lập lần hai. Không tự push,
commit hoặc tuyên bố dự án đã sẵn sàng phát hành.

## Trạng thái artifact hiện tại

- Runtime drill index: `artifacts/runtime-drills/index.json`
- Runtime gaps probe: `artifacts/runtime-evidence-gaps.json`
- Pilot acceptance: `artifacts/pilot-acceptance.json`
- Release verifier command:
  `python scripts/ops/verify_release_bundle.py --bundle artifacts/pilot-acceptance.json`
- Rollback runbook: `docs/runbooks/launch-safety-rollback.md`
- Acceptance runbook: `docs/runbooks/proof-first-pilot-acceptance.md`

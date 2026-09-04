# Bàn giao lại cho Codex — kết quả phiên Claude Code Desktop 2026-09-03

Authority: config/release-authority.json

> **STATUS: active.** Đây là kết quả thực thi của bản giao việc
> `docs/HANDOFF-CLAUDE-CODE-DESKTOP-2026-09-03.md`. Đọc file kia để biết ĐỀ BÀI,
> đọc file này để biết ĐÃ LÀM ĐƯỢC GÌ và CÒN GÌ.
>
> **CỔNG PHÁT HÀNH VẪN ĐÓNG — và đó là kết quả đúng.**
> `pilot acceptance gate = NO_GO`, `release verifier = BLOCKED` (exit 2).
> Không thay đổi nào trong phiên này có thể nâng verdict; xem §5.
>
> Chưa commit, chưa push, chưa deploy. HEAD vẫn `7bd85e77`.

---

## 1. Trạng thái một dòng

11/11 hạng mục P0+P1 đã truy nguyên xong và **10 đã vá**; P0.2 (rollback
orchestration) vẫn **BLOCKED** vì hai chặn thật, đã ghi bằng chứng thay vì ép cho xanh.

## 2. Đã vá

| # | Vấn đề | Bản chất | Chỗ sửa |
|---|---|---|---|
| P0.1 | `public-internal-route-exposed` | **KHÔNG phải lỗi sản phẩm** — probe chĩa nhầm bề mặt | `docs/runbooks/launch-safety-rollback.md:171` |
| P0.3 | Chỉ mục bằng chứng không ai kiểm | Thiếu validator/schema/producer | + `scripts/ops/validate_drill_index.py` |
| P1.1 | Runner ký TRƯỚC khi quyết | Digest cũ (fail-closed, đang bị che) | `scripts/ops/run_pilot_acceptance.py` |
| P1.2 | Verifier không nạp đối chứng | Fail-open | `scripts/ops/verify_release_bundle.py` |
| P1.3 | **Chạy toàn SKIP mạo danh được drill thật** | Fail-open, nặng nhất | `scripts/ops/countersign_pilot_acceptance.py` |
| P1.4 | `offline-owner` giải theo cwd, nhận khoá TRONG checkout | Nhãn độc lập không được kiểm | `agent/control_plane/attestation.py` |
| P1.5 | `ci-secret` chỉ cần `GITHUB_ACTIONS=true` | Lỗ hổng biên tin cậy | `agent/control_plane/attestation.py` |
| P1.6 | Authority STALE không chặn được gì | Fail-open | `scripts/ops/verify_release_bundle.py` |
| P1.7 | Cổng không đọc hồ sơ quyết định | Fail-open | `scripts/ops/verify_release_bundle.py` |
| P1.8 | `.gitignore` **không che** `*.key` | `.key` trần chỉ khớp basename | `.gitignore` |

### Ba điều đáng đọc kỹ

**P0.1 — cái "FAIL" là lỗi phép đo, không phải lỗ hổng.**
`--require-public-internal-404` là hợp đồng của **biên nginx**
(`location ^~ /_internal/ { return 404; }` — `nginx.conf:74-76`,
`nginx-ssl.conf:34-36`, `:111-113`). Origin Nuxt **cố ý** phục vụ
`/_internal/launch-readiness` với HTTP 200 không xác thực, vì
`deploy_launch_admission.sh:118-130` curl thẳng vào đó làm cổng BẮT BUỘC trước
khi mở lại traffic. Lỗi nguồn thật là runbook ghi
`NGINX_OPERATOR_PROBE_URL=http://127.0.0.1:3100`, mà `3100` nằm trong
`PROHIBITED_PUBLIC_PORTS` (`socket_boundary_probe.py:19-21`). Đã đổi sang biên
loopback `18080`.
**Đo lại trên biên nginx thật: PASS** → `artifacts/runtime-drills/boundary-edge-20260903-001254/`.
Hai "pass" trong artifact cũ là **rỗng**: hai đường dẫn kia là route của agent
(cổng 8360), không tồn tại trên Nuxt, nên 404 đến từ catch-all renderer.

> ⚠️ **ĐỪNG** xoá / 404 / thêm auth cho `web-nuxt/server/routes/_internal/launch-readiness.get.ts`.
> Làm vậy là hỏng đường mở lại traffic. Đã có test ghim điều này ở cả hai lớp.

**P1.3 — lỗ hổng nghiêm trọng nhất.**
`_outcome_fingerprint` chỉ băm `{verdict, nodeids, return_code}`. Vì
`classify_verdict` trả `PASS` khi không có gì FAIL, pytest thoát 0, và `pytest -v`
vẫn in node id — nên trên máy **không có database**, ba drill `@pg_only` sẽ SKIP và
sinh ra dấu vân tay **trùng byte** với drill thật (đo: `57953d7e…`, đúng giá trị
trong `artifacts/pilot-countersignature.json`). Tức là control **mạnh nhất** thoả
mãn được bằng cách **không chạy gì cả** — và nó YẾU HƠN chính self-check mà runner
đã tự canh. Đã đưa `counts` vào digest; đo lại: hết trùng.

**P0.2 — một bản vá bị TỪ CHỐI vì fail-open.**
Đề xuất đổi `return` trần ở `rehearse_launch_rollback.sh:621` thành `return 0`
**KHÔNG được áp dụng**. `verify_maintenance_boundary` được gọi làm điều kiện của
`if "$@"; then` (`redrain_step:722`) nên errexit bị chặn bên trong; lệnh cuối CHÍNH
LÀ validator, thoát 2 khi `public.status != 503` hoặc `operator.contract_passed`
không phải True. `return` trần truyền số 2 đó ra; `return 0` sẽ nuốt nó → báo thành
công trên một maintenance-boundary proof đã HỎNG → `TRAFFIC_STATE=drained` khi
không có bằng chứng → mở khoá chuỗi recovery ghi đè `$RELEASE_ROOT`.
Cùng hình dạng còn ở `verify_nginx_closed_boundary:562-573`. **Giữ nguyên.**

## 3. Test đã thêm (đều đỏ trước bản vá)

- `tests/test_gitignore_secret_material.py` — hỏi thẳng `git check-ignore`, không tự diễn giải cú pháp.
- `tests/integration/test_validate_drill_index.py` — 14 ca, gồm một ca không-hermetic ghim chỉ mục THẬT đang sạch.
- `tests/integration/test_verify_release_bundle.py` — đối chứng phải ràng đúng bundle (chống replay), authority staleness, hồ sơ quyết định.
- `tests/control_plane/test_attestation.py` — custody phải được KIỂM chứ không chỉ được KHAI; contract test đọc thẳng authority.
- `tests/integration/test_cross_boundary_proof.py` — chữ ký runner phải phủ gate cuối.
- `tests/integration/test_countersign_pilot_acceptance.py` — chạy toàn SKIP không được mạo danh drill thật.
- `tests/launch_safety/test_deploy_readiness.py` — bề mặt origin phải làm probe THẤT BẠI; runbook không được trỏ vào cổng bị cấm.
- `web-nuxt/tests/launch-readiness.test.ts` — endpoint phục vụ operator qua loopback **không cần chứng chỉ** (chốt chặn "sửa nhầm lớp").

**Fixture được LÀM MẠNH, không nới:** `test_attestation.py` và
`test_cross_boundary_proof.py` trước đây giả lập CI bằng mỗi `GITHUB_ACTIONS=true`;
nay cấp đủ bộ định danh Actions mạch lạc.

## 4. Verifier: 1 → 19 lý do

Trước: đúng một lý do `"pilot acceptance gate is NO_GO"`. Nay còn nêu thêm đối
chứng chưa ký, 4 quyết định chưa ký **và chưa tracked**, 7 tài liệu authority hết
hạn. Verdict giữ nguyên `BLOCKED`.

## 5. Vì sao không có gì làm cổng xanh được

Ba cổng mới chỉ **THÊM** lý do và chỉ hạ verdict xuống `BLOCKED`; không nhánh nào
nâng verdict. Không tạo bất kỳ sign-off nào. Nơi hợp đồng còn thiếu, cổng **từ chối**
thay vì bịa: authority chưa khai danh sách người ký cho decision, nên một chữ ký
decision **không được ghi nhận** cho tới khi chủ dự án khai.

## 6. Còn lại — cần CON NGƯỜI, không phải agent

1. **Bốn quyết định** (legal / provider / residency / public_indexing) chưa ký, và
   **toàn bộ hồ sơ đang untracked** (`config/decision-records.json`, `docs/decisions/QD-*.md`).
2. **Authority STALE** — 7 tài liệu hết hạn (`check_release_authority.py` exit 1).
3. **Khoá attestation cố ý vắng mặt** — chủ dự án quyết, không được tạo.
4. **`decision_signers` chưa có trong authority** — cổng cần nó mới ghi nhận được chữ ký.
5. **Khoá owner:** custody nay là `offline-owner:/etc/vinhlong360/pilot-owner-signing.key`
   (tuyệt đối, ngoài checkout prod `/opt/vinhlong360`). Đặt khoá thật là việc của chủ dự án.

## 7. Cảnh báo cho phiên sau

**Ba nhóm đỏ KHÔNG phải hồi quy — đừng đuổi theo:**

| Nhóm | Nguyên nhân |
|---|---|
| `test_closed_installer.py` — 4 fail | Alias `python` của Windows chặn lời gọi trong bash (`"Python was not found… Microsoft Store"`). **Chưa có trong roster fail-đã-biết** — nên bổ sung. |
| `npm run typecheck` — 2 lỗi | `utils/legalContent.ts:254,270`, nằm trong hunk `@@ -138 +223,51 @@` = **mã chưa commit của phiên khác**. |
| `npx vitest run` — 31 fail | `check-tri-region-contrast.mjs` trên `assets/css/base.css`, CSS **đã bị phiên khác sửa từ trước**. |

`test_rollback_runbook.py::test_local_rehearsal_failure_injection_…` fail vì
`WinError 1314` — **đã có** trong roster (W).

**Đĩa:** giữa phiên ổ C: tụt xuống **244 MB**. `docker builder prune` +
`image prune` thu hồi 1,07 GB **bên trong VHDX** nhưng Windows **không nhận lại**.
Đo `Get-PSDrive C` trước mỗi lượt full-suite (CLAUDE.md §5c-bis).

**Container còn treo:** 4 container `vl360boundary*-agent-1` / `-bot-gateway-1` đang
`Up`. Không phân biệt được của phiên này hay của một phiên chạy song song, nên
**không đụng**. Chủ dự án tự dọn nếu chắc chắn không phiên nào đang dùng.

**8 file đang staged** là của phiên khác, có từ trước phiên này. Tôi không `git add` gì.

## 8. ⚠️ NGUY HIỂM NHẤT — phần lớn công việc này KHÔNG nằm trong git

Đo `git status --short` ngày 2026-09-03: các file dưới đây **untracked ở HEAD**,
tức toàn bộ nội dung chúng chỉ tồn tại trên đĩa:

```
?? agent/control_plane/attestation.py          <- P1.4 + P1.5 nằm ở đây
?? scripts/ops/run_pilot_acceptance.py         <- P1.1
?? scripts/ops/countersign_pilot_acceptance.py <- P1.3
?? scripts/ops/validate_drill_index.py         <- P0.3 (file mới)
?? tests/control_plane/test_attestation.py
?? tests/integration/test_countersign_pilot_acceptance.py
?? tests/integration/test_validate_drill_index.py
?? tests/integration/test_verify_release_bundle.py
?? tests/test_gitignore_secret_material.py
```

**Một lệnh `git stash -u` / `git clean -fd` / `git checkout .` sẽ xoá trắng toàn bộ
bản vá P1.1, P1.3, P1.4, P1.5 và mọi test đi kèm** — không có bản commit nào để khôi
phục. Đây đúng lớp tai nạn ghi ở CLAUDE.md §5c (một agent `stash -u` cuốn theo việc
đang dở của agent khác). `artifacts/` cũng untracked-và-không-ignored.

**Trước khi làm bất cứ thao tác git nào tác động toàn cây: sao lưu, hoặc commit.**
Việc commit/push thuộc §4 (cần chủ dự án), nên phiên này không tự làm.

## 9. Lệnh nghiệm thu nhanh

```powershell
$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'
python -m pytest tests/control_plane/test_attestation.py `
  tests/integration/test_verify_release_bundle.py `
  tests/integration/test_validate_drill_index.py `
  tests/integration/test_countersign_pilot_acceptance.py `
  tests/test_gitignore_secret_material.py `
  tests/launch_safety/test_deploy_readiness.py -q -m "" --tb=line
# đo được: 182 passed, 1 skipped

python scripts/ops/validate_drill_index.py --root .          # exit 0
python scripts/ops/verify_release_bundle.py --bundle artifacts/pilot-acceptance.json   # exit 2 = BLOCKED
```

> STATUS (2026-08-05): active

# Deploy xong site lỗi

Deploy ở dự án này không phải `git pull && restart`. Nó đóng traffic, cài một archive
đã kiểm toàn vẹn, chạy cổng migration hai lần, rồi mở lại. Nghĩa là khi hỏng, nó hỏng ở
một **phase cụ thể** và để lại **bằng chứng cụ thể** — đừng đoán mò, hãy đi tìm hai thứ đó.

Nguyên tắc duy nhất cần thuộc: **đường lùi phải tồn tại trước khi cần đến nó.** Rollback
ở đây yêu cầu một archive known-good cộng file `.sha256` đi kèm. Không có archive đó thì
không có rollback — chỉ còn cách đóng cửa và vá tại chỗ. Kiểm điều này *trước* khi bấm
deploy, không phải lúc site đang chết.

---

## Dấu hiệu

### 5 con số deploy tự in ra ở cuối

`scripts/deploy.sh` kết thúc bằng khối diagnostics (dòng 553-560). **Đọc nó trước tiên**:

```
  home=200
  agent_health=200
  agent_ready=200
  search=200
  public_api_homepage=200
```

Bất kỳ số nào khác 200 đều là một nhánh khác nhau:

| Con số lệch | Nghĩa là gì |
|---|---|
| `home` != 200 | nginx hoặc vl-nuxt chết — bản `.output` hỏng/rỗng là nghi phạm số một |
| `agent_health` != 200 | vl-agent không lên — hay gặp nhất là `.env` sai cú pháp → crash-loop |
| `agent_ready` = 503 | agent sống nhưng chưa sẵn sàng: DB, schema, hoặc chưa nạp entity → [db-khong-len.md](db-khong-len.md) |
| `search` != 200 | index chưa dựng xong, hoặc DB lệch — đợi 1-2 phút rồi đo lại trước khi kết luận |
| `public_api_homepage` != 200 | nginx → backend đứt, dù cả hai service đều "active" |

Nếu deploy **dừng giữa chừng** thì không có khối này. Lúc đó dấu hiệu nằm ở dòng lỗi
cuối cùng và ở thư mục evidence (xem Chẩn đoán nhanh).

### 200 mà vẫn hỏng — nhánh im lặng, nguy hiểm nhất

Trang trả 200 nhưng **rỗng entity**. Đã từng làm ~18 trang danh mục trắng mà không ai
biết, vì mọi thứ đo được đều xanh. Nguyên nhân là gotcha SSR-fetch (`docs/HANDOFF.md` §6).

```bash
curl -s https://vinhlong360.vn/du-lich | grep -c '/dia-diem/'
```

Bằng 0 nghĩa là trang rỗng. **Không bao giờ chỉ kiểm HTTP 200.**

### Dấu hiệu khác

- `ERR_MODULE_NOT_FOUND` trong `journalctl -u vl-nuxt` → chunk `.output` lệch nhau, gần
  như luôn do build trên Windows mà chỉ `rm -rf .output` (thiếu `.nuxt`).
- 502 toàn site → `web-nuxt/.env` chứa `API_BASE` bị nướng vào routeRules lúc build.
- CSS/nội dung vẫn là bản cũ dù deploy báo thành công → đĩa đầy, ship nhầm bản.
  Kiểm `df -h /` ngay, rồi [het-dia.md](het-dia.md).
- `/var/log/vl-watchdog.log` có `FAIL` mỗi 5 phút — watchdog cũng có thể **đã tự restart**
  service (nó tự chặn không restart lại trong vòng 30 phút).

## Chẩn đoán nhanh

Đích: **≤5 phút** từ lúc nghi ngờ tới lúc quyết định rollback hay vá.

```bash
ssh -i ~/.ssh/vinhlong_vps root@66.42.57.202
```

```bash
# Phút 1 — đo lại chính 5 con số đó, đừng tin ký ức.
for u in https://vinhlong360.vn/ https://vinhlong360.vn/api/homepage; do
  printf '%s -> %s\n' "$u" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 12 "$u")"
done
for u in health health/ready 'api/search?q=deploy-check'; do
  printf '8360/%s -> %s\n' "$u" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "http://127.0.0.1:8360/$u")"
done

# Phút 2 — service nào chết, và đang crash-loop hay chết hẳn.
systemctl is-active vl-agent vl-nuxt vl-bot nginx
systemctl show vl-agent -p NRestarts --value      # số lớn và tăng = crash-loop

# Phút 3 — nó nói gì lúc chết. Đọc dòng CUỐI, không phải dòng đầu.
journalctl -u vl-agent -n 60 --no-pager
journalctl -u vl-nuxt  -n 40 --no-pager

# Phút 4 — nội dung có thật không, hay 200 rỗng.
curl -s https://vinhlong360.vn/du-lich | grep -c '/dia-diem/'

# Phút 5 — hai nguyên nhân nền hay bị bỏ sót.
df -h /
ls -l /opt/vinhlong360/web-nuxt/.output/server/index.mjs
```

Nếu deploy dừng giữa chừng, đọc evidence để biết nó chết ở phase nào:

```bash
# Evidence của lần deploy đã hoàn tất (mỗi lần một thư mục theo LAUNCH_ID).
ls -lt /var/lib/vinhlong360/launch-evidence/ | head

# Deploy chết giữa chừng thì stage tạm còn nguyên (script cố ý không dọn khi lỗi
# sau bước đóng traffic) — nơi nhìn thấy phase nào chưa qua.
ls -lt /tmp/vl360-launch-admission.*/evidence/ 2>/dev/null | head -20
```

Kiểm luôn traffic đang mở hay đang đóng — deploy chết giữa chừng hay để lại maintenance:

```bash
readlink /etc/nginx/vl360-maintenance/active-server.conf
# server-enabled.conf  = maintenance ĐANG BẬT (site đóng)
# server-disabled.conf = maintenance tắt (site mở bình thường)
```

## Xử lý

### Quyết định: rollback hay vá tới

Quyết bằng tiêu chí, không bằng cảm giác "chắc sửa nhanh thôi".

**Rollback ngay, không tranh luận, khi:**

- `home` != 200 hoặc `public_api_homepage` != 200 — người dùng đang thấy site chết.
- vl-agent crash-loop (`NRestarts` tăng đều).
- `.output` rỗng/thiếu `server/index.mjs`, hoặc `ERR_MODULE_NOT_FOUND`.
- Trang trả 200 nhưng rỗng entity trên nhiều route.
- **Sau 10 phút vẫn chưa biết nguyên nhân.** Đây là tiêu chí quan trọng nhất và cũng là
  cái hay bị bỏ qua nhất. Thời gian chẩn đoán không tính là "đang xử lý".

**Được phép vá tới, chỉ khi đủ cả bốn:**

1. Nguyên nhân đã xác định, đọc được từ log, không phải phỏng đoán.
2. Sửa nằm gọn trong một file và không đụng schema/dữ liệu.
3. Verify lại được bằng đúng 5 con số ở trên.
4. Site vẫn đang phục vụ được (`home` = 200) hoặc đã đóng trong maintenance.

**Trường hợp phải hỏi chủ dự án trước (điều kiện dừng, CLAUDE.md §4):**

Nếu lần deploy này **đã chạy migration**. Cổng migration chạy sau khi đóng traffic
(`migration-gate-post-close`), nên schema có thể đã tiến lên trong khi code sắp bị lùi
lại. Migration ở đây là additive nên bản cũ thường vẫn chạy được, nhưng "thường" không
phải là căn cứ để tự quyết trên prod. Kiểm trước:

```bash
ls /tmp/vl360-launch-admission.*/evidence/migration-gate-post-close.json 2>/dev/null
ls /var/lib/vinhlong360/launch-evidence/*/migration-gate-post-close.json 2>/dev/null | tail -3
curl -s http://127.0.0.1:8360/health/ready | python3 -m json.tool | grep -A3 schema_version
```

### Đóng cửa trước khi sửa

Nếu chọn vá tới mà site đang lỗi hiển thị cho người dùng, đóng cửa trước:

```bash
bash scripts/ops/maintenance_mode.sh enable --operator-cidr 203.0.113.10/32
nginx -t && systemctl reload nginx     # script KHÔNG tự reload — bước này là của bạn
curl -s -o /dev/null -w '%{http_code}\n' https://vinhlong360.vn/    # mong đợi 503
```

Watchdog tự im khi maintenance bật, nên không phải tắt timer thủ công.

### Lệnh rollback thật

Rollback = cài lại archive known-good qua đúng trình cài đã kiểm toàn vẹn. Thứ tự 11
phase và ngữ nghĩa từng phase nằm ở [launch-safety-rollback.md](launch-safety-rollback.md)
— đọc nó trước khi chạy, đừng chép lệnh rồi bấm.

**Điều kiện tiên quyết (thiếu một cái là script từ chối, exit 64):**

- Archive known-good **và** file `.sha256` đi kèm, lấy từ quy trình provenance đã duyệt.
- `ACKNOWLEDGE_MAINTENANCE=launch-safety-rollback` — đây là xác nhận, **không phải phê duyệt**.
- `MOUNT_AUTHORITY` trỏ tới file thực thi (thiếu → exit 64).
- `ENVIRONMENT_AUTHORITY` phải là **file** tồn tại; `RUNTIME_AUTHORITY` phải là **thư mục**.
- Chủ dự án đã ra lệnh cho đúng việc này (deploy/rollback prod = điều kiện dừng §4).

```bash
cd /opt/vinhlong360

ACKNOWLEDGE_MAINTENANCE=launch-safety-rollback \
KNOWN_GOOD_CLOSED=/approved/external/vl360-launch-release-known-good.tar.gz \
PERSISTENT_AGENT_DATA_ROOT=/approved/external/persistent-agent-data \
ENVIRONMENT_AUTHORITY=/approved/external/vl360.env \
RUNTIME_AUTHORITY=/approved/external/runtime \
MOUNT_AUTHORITY=/approved/bin/vl360-mount-authority \
EVIDENCE_DIR=/var/lib/vinhlong360/rollback-evidence/$(date -u +%Y%m%dT%H%M%SZ) \
OPERATOR=ten-nguoi-chay \
OPERATOR_CIDR=203.0.113.10/32 \
CANDIDATE_RELEASE_ID=ban-vua-deploy \
ROLLBACK_RELEASE_ID=ban-known-good \
bash scripts/ops/rehearse_launch_rollback.sh --execute-on-host
```

Thay `/approved/...` bằng đường dẫn thật của các authority đã được cấp; `OPERATOR_CIDR`
là dải IP của người đang vận hành. `RELEASE_ROOT` mặc định `/opt/vinhlong360`.

Điều cần biết về hành vi khi rollback **cũng** hỏng:

- Lỗi khi mới kiểm archive → **không đụng gì tới host**, không mở recovery. An toàn.
- Lỗi sau khi traffic đã đóng → **traffic vẫn đóng**. Recovery không bao giờ tự mở cửa
  lại, và không khôi phục cây release cũ. Đó là thiết kế: thà đóng còn hơn mở nửa vời.
- Watchdog chỉ được khôi phục nếu trước đó nó đang bật; nếu recovery không lập lại được
  đủ điều kiện thì bước khôi phục watchdog bị ghi `skipped` để nó không restart service sớm.

**Nếu không có archive known-good:** đường rollback này không dùng được. Nói thẳng điều
đó ra thay vì loay hoay. Lúc đó chỉ còn: bật maintenance, vá tại chỗ, rồi deploy lại
sạch. Và ghi nhận đây là lỗi chuẩn bị, không phải lỗi công cụ.

## Xác minh

Rollback hay vá tới đều verify giống nhau. Cả 5 bước, không cắt bước nào.

```bash
# 1. Traffic đã mở lại chưa.
readlink /etc/nginx/vl360-maintenance/active-server.conf   # mong đợi server-disabled.conf

# 2. Lại đúng 5 con số. Đây là hợp đồng nghiệm thu, không phải gợi ý.
home=$(curl -s -o /dev/null -w '%{http_code}' --max-time 12 https://vinhlong360.vn/)
agent=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:8360/health)
ready=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:8360/health/ready)
search=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 'http://127.0.0.1:8360/api/search?q=deploy-check')
pub=$(curl -s -o /dev/null -w '%{http_code}' --max-time 12 https://vinhlong360.vn/api/homepage)
printf 'home=%s agent_health=%s agent_ready=%s search=%s public_api_homepage=%s\n' \
  "$home" "$agent" "$ready" "$search" "$pub"

# 3. Nội dung THẬT, không phải 200 rỗng. Kiểm nhiều route, một route dễ may mắn.
for r in du-lich san-pham dia-diem; do
  printf '%s: %s link entity\n' "$r" "$(curl -s https://vinhlong360.vn/$r | grep -c '/dia-diem/')"
done

# 4. Service ổn định, không phải vừa mới bị watchdog vực dậy.
systemctl is-active vl-agent vl-nuxt vl-bot nginx
systemctl show vl-agent -p NRestarts --value

# 5. Bằng chứng (nếu vừa rollback). Recorder ghi đúng hai file này.
EV=$(ls -dt /var/lib/vinhlong360/rollback-evidence/*/ 2>/dev/null | head -1)
if [ -n "$EV" ]; then
  tail -3 "$EV/rollback-phases.jsonl"
  python3 -m json.tool "$EV/rollback-summary.json"
else
  echo "khong co evidence rollback (chua rollback lan nao, hoac EVIDENCE_DIR dat cho khac)"
fi
```

Với rollback, phase cuối cùng phải là `reopen-and-recover-watchdog` ở trạng thái thành
công và `traffic_state` bằng `open`. Còn là `drained` nghĩa là site vẫn đóng — **chưa
xong**. Còn là `unknown` nghĩa là công cụ không chứng minh được trạng thái nào cả —
coi như chưa xong và đi kiểm tay bằng bước 1 và 2.

Cuối cùng, đợi **hai chu kỳ watchdog (10 phút)** rồi:

```bash
tail -20 /var/log/vl-watchdog.log
```

Không có dòng `FAIL` mới thì mới được nói là xong. Nhiều lần deploy hỏng chỉ lộ ra ở
phút thứ 7, khi cache hết hạn hoặc job nền đầu tiên chạy.

## Ngăn tái diễn

**Trước ngày deploy:**

- Chạy diễn tập rollback ở local (`--local-rehearsal`, xem
  [launch-safety-rollback.md](launch-safety-rollback.md)) để biết đường lùi còn sống.
  Một đường lùi chưa bao giờ chạy thử thì chưa phải đường lùi.
- Xác nhận archive known-good **và** `.sha256` của nó đang nằm ở nơi **ngoài** release
  root. Để trong release root thì mất release là mất luôn đường lùi.
- `df -h /` — deploy cần chỗ cho archive + evidence. Vào với đĩa gần đầy là tự chuốc lấy
  nhánh "deploy xong vẫn bản cũ", nhánh khó chẩn đoán nhất.

**Lúc build frontend (những cái này đều đã trả giá rồi):**

```bash
cd web-nuxt
rm -f .env                                    # API_BASE bị nướng vào routeRules → 502
rm -rf .output .nuxt                          # thiếu .nuxt → chunk lệch → ERR_MODULE_NOT_FOUND
NODE_OPTIONS="--max-old-space-size=4096" npm run build   # chạy NỀN, đừng chạy foreground
# Build xong PHẢI kiểm, đừng tin exit code:
ls -l .output/server/index.mjs
cd .. && bash scripts/deploy.sh --frontend --skip-build
```

**Về cổng chặn:**

- `deploy.sh` từ chối chạy khi worktree bẩn. `--allow-dirty` là cửa sau — dùng theo phản
  xạ nghĩa là bạn không biết mình đang ship gì.
- Đường phá dữ liệu đã bị chặn ngay trong script: `--data`, `--replace`, `--migrate` đều
  bị từ chối với `destructive data and migration operations are not supported by the
  closed-release deploy path` (`scripts/deploy.sh:70-72`). Đừng tìm cách đi vòng.
- Cổng migration chạy **hai lần** (trước và sau khi đóng traffic) và kiểm cả dấu vân của
  Python dùng để chạy nó. Gate đỏ = dừng, backup Postgres, chạy `apply_migrations.py` rồi
  deploy lại — không phải bỏ qua gate.

**Sau khi xử lý xong:** ghi lại nguyên nhân gốc vào chính runbook này. Ba nhánh hay gặp
nhất ở trên đều đến từ sự cố thật, và chúng chỉ hữu ích vì có người chịu khó viết xuống.

## Liên quan

- [launch-safety-rollback.md](launch-safety-rollback.md) — 11 phase, ngữ nghĩa evidence, diễn tập local.
- [db-khong-len.md](db-khong-len.md) — khi `agent_ready` trả 503 hoặc cổng migration đỏ.
- [het-dia.md](het-dia.md) — khi deploy xong mà prod vẫn bản cũ.
- [../HANDOFF.md](../HANDOFF.md) — §5 quy trình deploy, §6 gotcha SSR-fetch.

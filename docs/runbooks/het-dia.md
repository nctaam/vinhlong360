> STATUS (2026-08-05): active

# Hết đĩa — VPS hoặc máy dev

Sự cố suýt xảy ra thật: `agent/data` từng được ghi nhận ~**1,8 GB** backup rác. Đĩa VPS
chỉ 23 GB, mỗi lần deploy còn tốn thêm chỗ cho archive + evidence. Đĩa đầy trên hệ này
không làm site chết ngay — nó làm **deploy ship nhầm bản cũ**, **backup ra dump cụt**, và
**xoay vòng log thất bại trong im lặng**. Đó mới là phần nguy hiểm.

Con số 1,8 GB là lịch sử được kể lại, chưa đo lại được. Dưới đây là số **đo thật hôm nay**
trên repo chính `C:/Code/vinhlong360` (2026-08-05) — dùng làm mốc so sánh, không phải
hạn mức. Đáng chú ý: `server.log.jsonl` đang 81,7 MB trong khi trần cứng trong code là
32 MiB, tức xoay vòng đang không chạy:

| Đường dẫn | Dung lượng | Ghi chú |
|---|---|---|
| `agent/data` (tổng) | 358 MB | |
| `agent/data/kb_snapshots` | 182,2 MB / 20 file | trần thiết kế: `KEEP_SNAPSHOTS = 20`, mỗi bản ~15 MB |
| `agent/data/server.log.jsonl` | 81,7 MB | trần code là 32 MiB → xoay vòng đang không chạy |
| `agent/data/vinhlong360.db` | 33,3 MB | **DB sống — không đụng** |
| `agent/data/backups` | 28,5 MB / 2 file | JSON one-off từ 12-06, không ai dọn |
| `agent/data/vinhlong360_backup_*.db-shm` + `.db-wal` | 20,2 MB / **1292 file** | chỉ còn 5 file `.db` mẹ → phần lớn là rác mồ côi |
| `scratch/backups` | 300 MB / 8 thư mục | `backup_data.py` mặc định giữ 5 bản |

---

## Dấu hiệu

Không có cái nào trong số này tự nói "hết đĩa". Phải tự nhận ra.

- **Deploy chạy xong mà prod vẫn bản cũ.** Đã xảy ra: đĩa đầy 100% → giải nén thất bại
  một phần → ship `.output` cũ. Xem `docs/HANDOFF.md` §5.
- **`/var/log/vl-backup.log` có dòng `BACKUP BẤT THƯỜNG`** — `backup_db_daily.sh` kiểm
  footer `database dump complete`; dump cụt vì hết chỗ ghi sẽ rơi vào đây.
- **Log server im bặt hoặc không xoay vòng.** `_rotate()` ghi cảnh báo
  `Log rotation failed: ...` (`agent/middleware.py:176`). Nếu file vượt 32 MiB mà vẫn
  còn nguyên → hoặc backend chưa restart từ lần vá, hoặc xoay vòng đang ném lỗi.
- **Postgres báo `No space left on device`, `could not extend file`, `PANIC: could not
  write to file`** → nhánh này thuộc `db-khong-len.md`, nhưng gốc là đĩa.
- **`npm run build` chết giữa chừng** với lỗi ghi file, hoặc `.output/server/index.mjs`
  không tồn tại sau khi build "thành công".
- **Deploy dừng ở phase đóng gói/giải nén** với lỗi ghi tmp.

Điểm mù cần biết: `scripts/ops/watchdog.sh` chỉ soi 3 HTTP endpoint trả 200. Nó
**không nhìn đĩa**. Đĩa 99% mà site vẫn 200 thì watchdog vẫn im lặng.

## Chẩn đoán nhanh

### Trên VPS (SSH, Linux)

```bash
ssh -i ~/.ssh/vinhlong_vps root@66.42.57.202
```

```bash
# 1. Còn bao nhiêu? Ngưỡng lo: Use% >= 85 hoặc Avail < 3G (deploy cần chỗ).
df -h /

# 2. Inode cũng cạn được — 1292 file rác nhỏ ăn inode chứ không ăn byte.
df -i /

# 3. Ai ăn đĩa? -x = không vượt filesystem, tránh đếm nhầm mount lạ.
du -x -h -d1 /opt/vinhlong360 2>/dev/null | sort -h | tail -12
du -x -h -d1 /var 2>/dev/null | sort -h | tail -12

# 4. 20 file to nhất toàn máy (thường lòi ra ngay thủ phạm).
find / -xdev -type f -printf '%s\t%p\n' 2>/dev/null | sort -rn | head -20 \
  | awk -F'\t' '{printf "%8.1f MB\t%s\n", $1/1048576, $2}'

# 5. File đã bị xoá nhưng tiến trình còn giữ fd — df thấy đầy, du thấy trống.
lsof -nP +L1 2>/dev/null | head -20
```

### Trên máy dev (Windows, PowerShell)

```powershell
# Còn bao nhiêu trên ổ C:
Get-PSDrive C | Select-Object Used, Free, @{n='Free_GB';e={[math]::Round($_.Free/1GB,1)}}

# Thư mục con nào của agent/data nặng nhất
Get-ChildItem C:\Code\vinhlong360\agent\data -Recurse -File -ErrorAction SilentlyContinue |
  Group-Object { $_.Directory.Name } |
  Sort-Object { ($_.Group | Measure-Object Length -Sum).Sum } -Descending |
  Select-Object -First 8 @{n='Thu_muc';e={$_.Name}},
    @{n='MB';e={[math]::Round((($_.Group | Measure-Object Length -Sum).Sum)/1MB,1)}}, Count |
  Format-Table -AutoSize

# 10 file đơn lẻ to nhất
Get-ChildItem C:\Code\vinhlong360\agent\data -Recurse -File -ErrorAction SilentlyContinue |
  Sort-Object Length -Descending | Select-Object -First 10 `
    @{n='MB';e={[math]::Round($_.Length/1MB,1)}},
    @{n='Duong_dan';e={$_.FullName.Replace('C:\Code\vinhlong360\','')}} |
  Format-Table -AutoSize

# Đếm sidecar mồ côi (-shm/-wal của file backup, KHÔNG phải của DB sống)
$orphan = Get-ChildItem C:\Code\vinhlong360\agent\data -Filter 'vinhlong360_backup_*.db-*' -File
"So file: $($orphan.Count)  Tong MB: $([math]::Round((($orphan|Measure-Object Length -Sum).Sum)/1MB,1))"
```

## Xử lý

### Trước khi xoá bất cứ thứ gì — 3 câu hỏi bắt buộc

1. **Có deploy hoặc rollback đang chạy không?** Nếu có → **DỪNG, không đụng
   `agent/data`**. Trình cài chụp dấu vân của mọi file thường trong `agent/data`
   trước khi detach và so lại sau khi remount; lệch một byte là nó chết với
   `persistent-agent-data-bytes-changed` (`scripts/ops/install_closed_release.sh:5589`).
   Dọn đĩa giữa chừng = tự tay làm hỏng deploy đang chạy.
2. **Có đang trong sự cố rò rỉ dữ liệu cá nhân không?** Nếu có → log là **bằng chứng**,
   phải copy ra chỗ khác trước khi cắt. Xem `docs/incident-runbook.md` bước 2.
3. **Đã snapshot chưa?** `python scripts/backup_data.py` trước mọi thao tác đụng vùng
   dữ liệu (bất biến B1). Backup vào `scratch/backups`, không vào `agent/data`.

### Thứ tự dọn — từ an toàn tuyệt đối xuống dần

**Bậc 1 — dựng lại được 100%, xoá thoải mái.**

```bash
# Cache build frontend. Đúng 3 đường dẫn này, không hơn:
# đây cũng chính là danh sách trong scripts/ops/purge_launch_runtime.py (EXACT_PURGE_PATHS).
rm -rf /opt/vinhlong360/web-nuxt/.output \
       /opt/vinhlong360/web-nuxt/.nuxt \
       /opt/vinhlong360/web-nuxt/.cache
# Lưu ý: xoá .output nghĩa là vl-nuxt không còn gì để chạy → phải deploy lại ngay.
# Trên PROD chỉ làm bậc này khi đang trong maintenance và biết mình sắp cài lại.
```

```bash
# journald: giữ 200 MB gần nhất.
journalctl --vacuum-size=200M
```

**Bậc 2 — rác mồ côi, xoá được nhưng phải lọc đúng.**

```bash
# Sidecar -shm/-wal của các file BACKUP (không phải của DB sống).
# In ra trước, đếm, rồi mới xoá. KHÔNG dùng wildcard rộng hơn cái này.
ls /opt/vinhlong360/agent/data/vinhlong360_backup_*.db-shm \
   /opt/vinhlong360/agent/data/vinhlong360_backup_*.db-wal 2>/dev/null | wc -l
# Nếu con số hợp lý (hàng trăm–hàng nghìn), xoá:
rm -f /opt/vinhlong360/agent/data/vinhlong360_backup_*.db-shm \
      /opt/vinhlong360/agent/data/vinhlong360_backup_*.db-wal
```

> Tại sao an toàn: tên phải khớp tiền tố `vinhlong360_backup_`. DB sống tên là
> `vinhlong360.db`, sidecar của nó là `vinhlong360.db-wal`/`.db-shm` — **không khớp
> pattern trên**. Đừng rút gọn thành `*.db-wal`; xoá WAL của DB đang mở là mất dữ liệu.

**Bậc 3 — log. Cắt, đừng xoá.**

```bash
# Giữ 5000 dòng cuối, thay nguyên tử — đúng hành vi _rotate() trong code.
# rm file đang được tiến trình mở sẽ khiến df không giải phóng cho tới khi restart.
F=/opt/vinhlong360/agent/data/server.log.jsonl
tail -n 5000 "$F" > "$F.rotating" && mv -f "$F.rotating" "$F"
ls -lh "$F"
```

Nếu file lại phình >32 MiB lần nữa: `systemctl restart vl-agent`. Xoay vòng chỉ được
kích hoạt ở **lần ghi đầu tiên của mỗi phiên chạy** cộng với ngưỡng đếm trong phiên
(`agent/middleware.py:141-145`); backend chạy liên tục nhiều ngày mà log tăng đều thì
lần dọn tồn dư không bao giờ tới lượt.

**Bậc 4 — backup cũ. Dùng công cụ, không `rm` tay.**

```bash
# backup_data.py tự dọn: giữ tối thiểu --keep bản, xoá bản quá --max-age-days ngày.
# Nó CHỈ dọn khi --out-dir trùng thư mục mặc định (scratch/backups) — cố ý như vậy.
python scripts/backup_data.py --keep 3 --max-age-days 14
```

> Trên Windows: `python scripts/backup_data.py --help` sẽ nổ `UnicodeEncodeError` vì
> console mặc định cp1252 còn help text có tiếng Việt. Không phải lỗi script — đặt
> `$env:PYTHONIOENCODING='utf-8'` (PowerShell) trước khi chạy.

```bash
# Dump Postgres hằng ngày trên VPS đã tự xoay vòng giữ 7 bản
# (scripts/ops/backup_db_daily.sh). Chỉ kiểm, không xoá tay:
ls -lht /opt/vinhlong360/backups/daily/ | head
```

**Bậc 5 — chỉ khi vẫn thiếu chỗ, và phải đọc kỹ.**

- `agent/data/kb_snapshots`: 182 MB, mỗi file là bản copy nguyên `data.json` trước một
  lần tự sửa KB. `KEEP_SNAPSHOTS = 20` (`agent/kb_versioning.py:28`) là trần **theo
  manifest**, không phải theo file trên đĩa — file lệch manifest sẽ nằm lại vĩnh viễn.
  Muốn dọn: đối chiếu `agent/data/kb_snapshots/manifest.json`, chỉ xoá file **không có
  trong manifest**. Xoá file còn trong manifest = mất đường lùi của KB.
- `agent/data/backups/*.json` từ 06-2026: JSON export một lần trước campaign geospatial.
  Giá trị lịch sử thấp, nhưng vẫn là dữ liệu → hỏi chủ dự án trước khi xoá (§4).

### TUYỆT ĐỐI KHÔNG XOÁ

| Đường dẫn | Vì sao |
|---|---|
| `agent/data/vinhlong360.db` và `vinhlong360.db-wal` / `.db-shm` | DB sống. WAL chứa giao dịch chưa checkpoint. |
| `web/data.json` | Export + nguồn build prerender, **đã phân kỳ với DB** — mất là không dựng lại được từ DB. |
| `/opt/vinhlong360/.env` | Sai một ký tự là `vl-agent` crash-loop; `server.py` đọc cứng `os.environ["LLM_API_KEY"]`. |
| Bất cứ thứ gì trong `agent/data` khi deploy/rollback đang chạy | Xem câu hỏi 1 ở trên. |
| `/var/lib/postgresql/**` | Dữ liệu Postgres. Dọn ở đây = mất DB. |
| Bản backup **mới nhất** trong `backups/daily` | Đó là đường lùi duy nhất còn dùng được. |
| `/var/log/vl-backup.log`, `/var/log/vl-watchdog.log` | Nhỏ, và là toàn bộ lịch sử vận hành đang có. |

## Xác minh

Chạy đủ 4 bước, đừng dừng ở bước 1.

```bash
# 1. Đĩa thật sự được trả lại (so với số đo lúc đầu).
df -h /
df -i /

# 2. Backend còn sống và DB còn kết nối được.
python scripts/health_check.py --base-url http://127.0.0.1:8360
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8360/health/ready   # mong đợi 200

# 3. Bản dump mới nhất vẫn nguyên vẹn (đĩa đầy hay sinh dump cụt).
LATEST=$(ls -t /opt/vinhlong360/backups/daily/db-daily-*.sql.gz | head -1)
gzip -t "$LATEST" && zcat "$LATEST" | tail -5 | grep -q 'database dump complete' \
  && echo "dump OK: $LATEST" || echo "DUMP HONG: $LATEST"

# 4. Site còn phục vụ nội dung thật, không chỉ trả 200 rỗng.
curl -s https://vinhlong360.vn/du-lich | grep -c '/dia-diem/'   # phải > 0
```

Nếu vừa cắt log: đợi một chu kỳ watchdog (5 phút) rồi `tail -20 /var/log/vl-watchdog.log`
— không có dòng `FAIL` mới nghĩa là 3 endpoint vẫn 200.

## Ngăn tái diễn

**Đã có sẵn, chỉ cần không phá:**

- `backup_db_daily.sh` giữ 7 bản daily, tự kiểm `gzip -t` + footer dump.
- `backup_data.py` mặc định `--keep 5 --max-age-days 30`.
- `StructuredLogger` có trần 32 MiB + 5000 dòng, và dọn tồn dư ở lần ghi đầu mỗi phiên.

**Còn hở — việc cần làm, chưa làm trong runbook này:**

1. **Watchdog không kiểm đĩa.** `scripts/ops/watchdog.sh` chỉ curl 3 endpoint. Thêm một
   nhánh: `df --output=pcent / | tr -dc '0-9'` >= 85 thì ghi `/var/log/vl-watchdog.log`
   và gửi cảnh báo. Đây là sửa file ngoài phạm vi runbook → mở task riêng.
2. **Sidecar `-shm`/`-wal` mồ côi sinh ra không ai dọn.** Hàm backup SQLite tại
   `agent/database.py:1723` tạo file `vinhlong360_backup_<ts>.db`; sidecar còn lại sau
   đó không có ai thu. 1292 file cho 5 file mẹ là bằng chứng. Cần dọn ngay trong hàm tạo
   backup, không phải bằng cron.
3. **Backup offsite vẫn treo.** `scripts/ops/systemd-units.md` ghi rõ: dump chứa dữ liệu
   cá nhân + hash mật khẩu nên không được đẩy lên bucket public. Chừng nào chưa có bucket
   riêng hoặc passphrase mã hoá, mọi bản backup vẫn nằm **cùng một đĩa với DB** — đĩa đầy
   hoặc đĩa hỏng là mất cả hai. Đây là quyết định của chủ dự án (§4).

**Thói quen rẻ tiền mà hiệu quả:** trước mỗi lần deploy, chạy `df -h /` và đọc con số.
Deploy cần chỗ cho archive + evidence; đi vào với 1 GB trống là tự chuốc lấy nhánh
"deploy xong vẫn bản cũ" — nhánh khó chẩn đoán nhất trong cả ba runbook này.

## Liên quan

- [db-khong-len.md](db-khong-len.md) — khi đĩa đầy đã kịp làm Postgres ngã.
- [deploy-hong.md](deploy-hong.md) — khi đĩa đầy làm deploy ship nhầm bản.
- [launch-safety-rollback.md](launch-safety-rollback.md) — vì sao `agent/data` là vùng cấm giữa deploy.
- [../incident-runbook.md](../incident-runbook.md) — log là bằng chứng khi nghi rò rỉ dữ liệu.

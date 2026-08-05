> STATUS (2026-08-05): active

# DB không lên — Postgres chết hoặc app không kết nối được

"DB không lên" là bốn sự cố khác nhau đội chung một cái tên. Chẩn đoán sai nhánh thì
mọi thao tác sau đó đều lãng phí, và nhánh nguy hiểm nhất (đĩa đầy) lại giống nhánh vô
hại nhất (mạng) ở lớp ngoài cùng: cả hai đều ra "không kết nối được".

Bốn nhánh, phân biệt bằng **thông điệp lỗi**, không phải bằng cảm giác:

| Nhánh | Dấu hiệu đặc trưng | Đi tới |
|---|---|---|
| **Mạng / tiến trình** | `connection refused`, `could not connect to server`, timeout | §Nhánh A |
| **Xác thực** | `password authentication failed`, `role ... does not exist`, `no pg_hba.conf entry` | §Nhánh B |
| **Schema** | Kết nối OK nhưng `/health/ready` trả 503 với `checks.schema = false` | §Nhánh C |
| **Đĩa đầy** | `No space left on device`, `could not extend file`, `PANIC: could not write` | §Nhánh D |

Kiến trúc cần nhớ trước khi chẩn đoán: backend chọn backend DB bằng biến môi trường
`DATABASE_URL` (`agent/database.py:37-38`). Có URL Postgres → dùng Postgres. Không có →
rơi về SQLite, và **mọi endpoint UGC trả 503 một cách cố ý** (CLAUDE.md §1.3). Thấy 503
trên `/api/feed` ở máy dev không có Postgres thì đó không phải sự cố.

---

## Dấu hiệu

- `python scripts/health_check.py` in `health: FAIL` với `connection error`.
- `curl http://127.0.0.1:8360/health/ready` trả **503**; body có `"ready": false` và
  một trong các cờ `checks.database`, `checks.schema` bằng `false`.
- `/health` trả `"status": "degraded"` (điều kiện `ok` cần cả DB, LLM và error-rate cùng
  khoẻ — `agent/server.py:3999-4002`, nên `degraded` chưa chắc là lỗi DB).
- `/var/log/vl-watchdog.log` có dòng `FAIL health=... search=...` lặp lại, và
  `systemctl status vl-agent` cho thấy service bị restart nhiều lần.
- Site trả 200 nhưng trang danh mục rỗng entity — trường hợp này thường **không** phải
  DB, mà là gotcha SSR-fetch (`docs/HANDOFF.md` §6). Kiểm bằng
  `curl -s https://vinhlong360.vn/du-lich | grep -c '/dia-diem/'` trước khi đổ cho DB.
- Ở máy dev: `sqlite3.OperationalError: database is locked`, hoặc `agent/data/*.db-wal`
  phình mà không co lại.

## Chẩn đoán nhanh

### Bước 0 — hỏi đúng câu hỏi đầu tiên

```bash
# Chạy TRƯỚC mọi thứ khác: nếu đĩa đầy thì mọi triệu chứng khác đều là hệ quả.
df -h /
df -i /
```

Đầy → sang [het-dia.md](het-dia.md), quay lại đây sau. Đừng restart Postgres khi đĩa
đầy: nó có thể không lên lại được, và lúc đó sự cố nhẹ đã thành sự cố nặng.

```bash
# Backend đang nghĩ gì? /health/ready là nguồn thông tin giàu nhất, một lệnh ra hết.
curl -s http://127.0.0.1:8360/health/ready | python3 -m json.tool
```

Payload có sẵn các cờ để rẽ nhánh (`agent/server.py:4108-4153`):

- `checks.database: false` → nhánh A hoặc B (không kết nối được).
- `checks.database: true` + `checks.schema: false` → **nhánh C** (kết nối được, schema sai).
- `checks.schema_version.schema_version` vs `required_schema_version` → chênh lệch chính
  là số migration còn thiếu. Bản code hiện tại yêu cầu **74**
  (`PG_REQUIRED_SCHEMA_VERSION`, `agent/database.py:127`).
- `checks.knowledge: false` → DB lên nhưng chưa nạp entity vào RAM; thường là backend
  khởi động khi DB còn chưa sẵn sàng → restart `vl-agent` sau khi DB khoẻ.

### Nhánh A — mạng / tiến trình

```bash
# Postgres có đang chạy không?
# Tên unit lấy theo docs/HANDOFF.md:69 (liệt kê: vl-agent, vl-nuxt, vl-bot, postgres, nginx).
# Chưa xác minh trực tiếp trên VPS. Không thấy unit này thì thử tên chuẩn Debian/Ubuntu:
#   systemctl list-units --type=service | grep -i postg
systemctl status postgres --no-pager | head -20
ss -ltnp | grep 5432

# Bắt tay được không? (không cần mật khẩu, chỉ hỏi "sẵn sàng chưa")
pg_isready -h 127.0.0.1 -p 5432 -U vl360 -d vinhlong360

# Postgres nói gì lúc chết?
journalctl -u postgres -n 80 --no-pager
```

Trên máy dev dùng Docker:

```bash
docker compose ps postgres
docker compose logs --tail=80 postgres
# healthcheck đã cấu hình sẵn trong docker-compose.yml: pg_isready -U vl360 -d vinhlong360
```

Đọc kết quả:

- Tiến trình **không chạy** → xem `journalctl` để biết vì sao chết (rất hay là đĩa hoặc
  quyền file), sửa nguyên nhân rồi mới `systemctl start postgres`.
- Tiến trình **chạy**, `ss` có 5432, `pg_isready` OK, mà app vẫn không nối →
  vấn đề nằm ở phía app: sai host/port trong `DATABASE_URL`, hoặc pool đã cạn. Xem
  nhánh B.
- `pg_isready` trả `no response` trong khi tiến trình sống → Postgres đang trong
  recovery, đọc log để biết nó đang replay tới đâu. **Kiên nhẫn, đừng kill.**

### Nhánh B — xác thực / cấu hình kết nối

> Không in giá trị secret ra màn hình hay log. Kiểm **sự tồn tại và hình dạng**, không
> kiểm nội dung. Sửa `.env` prod là điều kiện dừng (CLAUDE.md §4) — sai cú pháp một dòng
> là `vl-agent` crash-loop vì `server.py` đọc cứng `os.environ["LLM_API_KEY"]`.

```bash
# Có đúng một dòng DATABASE_URL không? (0 = thiếu; >1 = dòng sau đè dòng trước)
grep -c '^DATABASE_URL=' /opt/vinhlong360/.env

# In HÌNH DẠNG của URL, không in giá trị. Đọc thẳng từ file .env vì biến này
# không nằm trong shell — nó do systemd nạp cho service.
python3 - /opt/vinhlong360/.env <<'PY'
import sys, urllib.parse
url = ""
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    if line.startswith("DATABASE_URL="):
        url = line.split("=", 1)[1].strip().strip('"').strip("'")
if not url:
    print("DATABASE_URL rỗng → backend chạy SQLite, UGC trả 503 (đúng thiết kế)")
else:
    p = urllib.parse.urlparse(url)
    print(f"scheme={p.scheme} host={p.hostname} port={p.port} "
          f"db={p.path.lstrip('/')} user={'có' if p.username else 'THIẾU'} "
          f"pass={'có' if p.password else 'THIẾU'}")
PY
```

```bash
# Thử kết nối bằng đúng credential Postgres đang có trên máy (không qua .env app).
sudo -u postgres psql -d vinhlong360 -c 'SELECT 1'

# Vai vl360 còn tồn tại và còn quyền không?
sudo -u postgres psql -d vinhlong360 -c '\du vl360'
sudo -u postgres psql -d vinhlong360 -c \
  "SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public' AND tableowner<>'vl360' LIMIT 20"
```

Bảng có owner khác `vl360` là bẫy đã trả giá: migration áp tay tạo bảng mới dưới quyền
`postgres`, app kết nối bằng `vl360` rồi không đọc được. Sửa:
`ALTER TABLE <tên> OWNER TO vl360;` (xem `docs/HANDOFF.md` §5).

### Nhánh C — schema lệch

```bash
# Thiếu những migration nào? --dry-run KHÔNG ghi gì.
python scripts/apply_migrations.py --dry-run

# Migration mới nhất trong repo (đối chiếu với schema_version đọc được ở /health/ready).
ls agent/migrations/*.sql | tail -5
```

Deploy tự chặn nhánh này trước khi đụng release: cổng migration chạy hai lần (trước và
sau khi đóng traffic) và in đúng câu
`migration prerequisite failed; back up PostgreSQL and run scripts/apply_migrations.py
before rerunning deploy` (`scripts/deploy.sh:410`). Thấy câu đó nghĩa là DB đang lệch
schema so với archive sắp cài — không phải deploy hỏng.

Áp migration (đây là thao tác ghi DB — **backup trước, bất biến B1**):

```bash
python scripts/backup_data.py --target pg --label truoc-migration
python scripts/apply_migrations.py --dry-run     # đọc kỹ danh sách sắp chạy
python scripts/apply_migrations.py               # chỉ khi dry-run đúng như mong đợi
```

> **Hai chỉ dẫn đang mâu thuẫn — đọc trước khi làm trên prod.**
> `docs/HANDOFF.md:85` ghi migration **không** được `deploy.sh` ship và phải áp tay bằng
> `psql -f`, kèm lưu ý bảng mới cần `ALTER TABLE x OWNER TO vl360`. Trong khi
> `scripts/deploy.sh:410` lại bảo chạy `apply_migrations.py`.
> Chưa xác minh được đường nào đang thật sự dùng trên prod (không có quyền truy cập VPS
> khi viết runbook này). Trên prod hãy theo HANDOFF cho tới khi chủ dự án xác nhận lại,
> và nhớ phần `OWNER TO vl360` — thiếu nó thì app ghi được bảng cũ nhưng không ghi được bảng mới.

### Nhánh D — đĩa đầy

Xử lý ở [het-dia.md](het-dia.md). Chỉ nói phần riêng của Postgres tại đây:

```bash
# WAL phình là thủ phạm quen mặt. Đo trước khi kết luận.
sudo du -sh /var/lib/postgresql/*/main/pg_wal 2>/dev/null
sudo -u postgres psql -c \
  "SELECT slot_name, active, pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS ton \
   FROM pg_replication_slots"
```

Replication slot chết (`active = false`) giữ WAL lại vô thời hạn — dự án này không dùng
replication, nên nếu thấy slot nào thì đó là rác cần chủ dự án xác nhận trước khi gỡ.
**Không bao giờ xoá tay file trong `pg_wal/`.**

## Xử lý

### Khi nào bật maintenance_mode

Bật khi **DB đang hỏng mà site vẫn nhận traffic** — tức là người dùng đang gặp lỗi hoặc
đang ghi vào một DB không toàn vẹn. Cụ thể:

- Sắp restore từ backup (**luôn luôn** bật).
- Sắp áp migration lên prod.
- Postgres đang recovery và app vẫn ghi ầm ầm.

Không bật khi: chỉ mất kết nối thoáng qua và `pg_isready` đã OK trở lại — bật/tắt
maintenance cũng là một lần đụng cấu hình nginx, không miễn phí.

```bash
# CIDR là nguồn IP của người vận hành — chỉ nguồn đó còn vào được.
bash scripts/ops/maintenance_mode.sh enable --operator-cidr 203.0.113.10/32
```

> **Script này chỉ đổi selector và chạy `nginx -t`. Nó KHÔNG reload nginx** — comment ở
> đầu file nói thẳng: "callers own the later process handoff". Phải tự làm bước bàn giao:
> ```bash
> nginx -t && systemctl reload nginx
> curl -s -o /dev/null -w '%{http_code}\n' https://vinhlong360.vn/   # mong đợi 503
> ```
> Quên bước này = tưởng đã đóng cửa mà thật ra vẫn mở.

Mở lại: `bash scripts/ops/maintenance_mode.sh disable --operator-cidr <cùng CIDR>` rồi
`nginx -t && systemctl reload nginx`.

Watchdog tự nhận biết maintenance: nó đọc selector và **ngưng probe + ngưng restart** khi
maintenance đang bật (`scripts/ops/watchdog.sh:13-33`). Nên không cần tắt timer thủ công.

### Khi nào khôi phục từ backup

Restore là thao tác **phá dữ liệu**. Bất biến B7 + điều kiện dừng §4: **chỉ làm khi chủ
dự án chỉ đạo trực tiếp cho đúng việc này.**

Restore khi: dữ liệu hỏng/mất/bị ghi đè sai, hoặc DB cluster không recovery được.
**Không** restore khi: chỉ mất kết nối, chỉ lệch schema (áp migration là đủ), hoặc chưa
biết nguyên nhân — restore một DB đang khoẻ vì chẩn đoán sai là tự tạo ra mất mát thật.

### Các bước khôi phục

```bash
# 1. Đóng cửa. Không có bước này thì có kẻ đang ghi vào DB bạn sắp thay.
bash scripts/ops/maintenance_mode.sh enable --operator-cidr 203.0.113.10/32
nginx -t && systemctl reload nginx
systemctl stop vl-agent vl-bot

# 2. Chụp trạng thái HIỆN TẠI trước, kể cả khi nó đang hỏng — đó là bằng chứng,
#    và là đường lùi nếu bản backup hoá ra tệ hơn.
sudo -u postgres pg_dump vinhlong360 | gzip > /opt/vinhlong360/backups/truoc-restore-$(date +%Y%m%d-%H%M%S).sql.gz

# 3. Chọn bản dump và KIỂM nó trước khi tin. Dump cụt trông y hệt dump tốt.
LATEST=$(ls -t /opt/vinhlong360/backups/daily/db-daily-*.sql.gz | head -1)
gzip -t "$LATEST" && zcat "$LATEST" | tail -5 | grep -q 'database dump complete' \
  && echo "dump OK: $LATEST" || echo "DUMP HONG — chon ban khac: $LATEST"

# 4. Diễn tập KHÔNG PHÁ trước khi làm thật. Script restore vào một DB tạm,
#    chạy cổng migration trên DB đã restore, sanity-check, rồi tự drop DB tạm.
python scripts/restore_drill.py --dump "$LATEST"

# 5. Restore thật vào DB MỚI — không drop DB sống trước.
sudo -u postgres createdb vinhlong360_restore
zcat "$LATEST" | sudo -u postgres psql -d vinhlong360_restore

# 6. Kiểm DB mới trước khi đổi tên. Câu đếm xã/phường lấy đúng như get_stats
#    dùng (agent/database.py:1739) — kỳ vọng 124 = 89 xã + 35 phường.
sudo -u postgres psql -d vinhlong360_restore -c 'SELECT count(*) FROM entities'
sudo -u postgres psql -d vinhlong360_restore -c \
  "SELECT count(*) FROM entities WHERE type = 'place' AND level IN ('xa','phuong')"

# 7. Đổi vai. Chỉ làm khi bước 6 cho số hợp lý.
sudo -u postgres psql -c "ALTER DATABASE vinhlong360 RENAME TO vinhlong360_hong_$(date +%Y%m%d)"
sudo -u postgres psql -c "ALTER DATABASE vinhlong360_restore RENAME TO vinhlong360"
sudo -u postgres psql -d vinhlong360 -c "ALTER DATABASE vinhlong360 OWNER TO vl360"

# 8. Bù schema nếu bản dump cũ hơn code đang chạy.
python scripts/apply_migrations.py --dry-run
python scripts/apply_migrations.py

# 9. Bật lại dịch vụ, rồi mới mở cửa.
systemctl start vl-agent vl-bot
```

Bước 7 giữ DB hỏng lại dưới tên mới thay vì drop — chi phí là dung lượng đĩa, đổi lại là
khả năng quay đầu. Chỉ drop sau khi bản mới đã chạy ổn ít nhất một ngày và chủ dự án
đồng ý.

> **`apply_migrations.py` cần `DATABASE_URL` mà shell trên VPS không có sẵn** (systemd
> nạp env cho service, không nạp cho phiên SSH của bạn). Nạp vào shell hiện tại mà không
> in ra màn hình:
> ```bash
> set -a; . /opt/vinhlong360/.env; set +a
> /opt/vinhlong360/venv/bin/python scripts/apply_migrations.py --dry-run
> ```
> Hoặc truyền thẳng qua `--database-url`. Đừng `echo $DATABASE_URL` để "kiểm cho chắc" —
> nó vào history và có thể vào log.

## Xác minh

Chạy đủ, theo thứ tự. Bước 3 mới là bước thật sự chứng minh DB sống.

```bash
# 1. Tầng Postgres.
pg_isready -h 127.0.0.1 -p 5432 -U vl360 -d vinhlong360

# 2. Tầng app: DB + schema + readiness, một lệnh.
curl -s http://127.0.0.1:8360/health/ready | python3 -m json.tool
#    Mong đợi: HTTP 200, "ready": true, checks.database=true, checks.schema=true,
#    và schema_version == required_schema_version.

# 3. Tầng dữ liệu: số phải đúng, không chỉ "có trả lời".
curl -s http://127.0.0.1:8360/health | python3 -m json.tool     # "entities" phải > 0
curl -s 'http://127.0.0.1:8360/api/places' | python3 -c \
  "import json,sys; print('places =', len(json.load(sys.stdin)))"
#    Đo ngày 2026-08-05 trên DB thật: 127 (gồm 91 xã + 35 phường + 1 tỉnh).
#    ĐỪNG chốt cứng con số này — đối chiếu với số ghi lại TRƯỚC sự cố. Số tụt mạnh
#    nghĩa là khôi phục thiếu; số nhảy vọt nghĩa là seed chồng lên dữ liệu cũ.
#    Ghi chú: 126 xã/phường hiện lệch với danh sách chính thức 124 — đó là nợ dữ
#    liệu đã biết, KHÔNG phải dấu hiệu khôi phục hỏng.

# 4. Tầng công khai (sau khi đã tắt maintenance).
python scripts/health_check.py --base-url http://127.0.0.1:8360
curl -s -o /dev/null -w '%{http_code}\n' https://vinhlong360.vn/
curl -s https://vinhlong360.vn/du-lich | grep -c '/dia-diem/'   # phải > 0
```

Sau đó đợi **hai chu kỳ watchdog (10 phút)** rồi `tail -20 /var/log/vl-watchdog.log`.
Không có `FAIL` mới thì mới coi là xong — DB hay chết lại lần hai sau vài phút.

## Ngăn tái diễn

- **Diễn tập restore định kỳ.** `python scripts/restore_drill.py` không phá gì cả: nó
  restore vào DB tạm, chạy cổng migration, sanity-check, rồi tự dọn. Một bản backup chưa
  từng được restore thử thì chưa phải là backup, chỉ là một file.
- **Đọc `/var/log/vl-backup.log` mỗi tuần.** `backup_db_daily.sh` đã tự bắt dump cụt và
  ghi dòng `BACKUP BẤT THƯỜNG` — nhưng không ai đọc thì bằng không.
- **Áp migration bằng `apply_migrations.py`, không bằng `psql -f` tay.** Áp tay là cách
  bảng mới có owner `postgres` thay vì `vl360` và app đọc không được.
- **Đừng chạm `deploy.sh --replace`.** Đường đó đã bị chính deploy chặn
  (`destructive data and migration operations are not supported by the closed-release
  deploy path`, `scripts/deploy.sh:71-72`) và nó ghi đè mọi chỉnh sửa AdminCP trên prod.
- **Backup offsite vẫn treo** — dump đang nằm cùng đĩa với DB. Chi tiết và lý do treo:
  `scripts/ops/systemd-units.md`. Quyết định thuộc chủ dự án (§4).
- **Kiểm `df -h /` trước mọi thao tác DB.** Nửa số sự cố "DB không lên" bắt đầu bằng đĩa.

## Liên quan

- [het-dia.md](het-dia.md) — nhánh D, và là nguyên nhân gốc hay gặp nhất.
- [deploy-hong.md](deploy-hong.md) — khi lỗi schema lộ ra ngay giữa lúc deploy.
- [../HANDOFF.md](../HANDOFF.md) — §5 deploy/migration, §7 luồng dữ liệu.
- [../incident-runbook.md](../incident-runbook.md) — khi sự cố DB có kèm nghi vấn rò rỉ dữ liệu.

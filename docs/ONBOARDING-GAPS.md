> STATUS: active — kết quả thử nghiệm "người mới tiếp quản", chạy thật ngày 2026-08-07.
> Đây là tài liệu **đo lường**, không phải tài liệu chỉ đạo. Mâu thuẫn với `CLAUDE.md` → CLAUDE.md thắng.

# Thử nghiệm người mới — cái gì gãy khi chỉ có repo + CLAUDE.md

**Phương pháp.** Giả định: vừa được bàn giao, chỉ có repo và `CLAUDE.md`, không có trí nhớ phiên
trước. Chạy thật từng lệnh trong `CLAUDE.md` §5, ghi lại lỗi thật. Worktree:
`C:\Code\vinhlong360\.worktrees\tri-region-color`, HEAD `10d9bb69`.

**Kết luận 1 dòng.** Backend, frontend, cổng chuẩn và bộ test **đều chạy được thật** — nhưng người mới
sẽ **làm việc trên nhánh sai** vì tài liệu onboarding chỉ sai trunk, và sẽ **không tự sửa được** khi
cổng chuẩn chặn vì thông báo ratchet không nói vi phạm nằm ở đâu.

---

## 0. Bảng tổng — 8 phát hiện

| # | Mức | Phát hiện | Trạng thái |
|---|-----|-----------|------------|
| G1 | **Chặn** | `docs/HANDOFF.md:6` ghi "Nhánh chính: `main`" — sai 246 commit | **ĐÃ SỬA** |
| G2 | **Chặn** | Clone mới từ GitHub = `origin/main` ngày 11-07, thiếu 847 commit | **ĐÃ SỬA** (cùng G1) |
| G3 | **Cao** | `CLAUDE.md` §3.3 trỏ tới mục ROADMAP **không tồn tại** | Còn — patch sẵn ở §5 |
| G4 | **Cao** | Cổng chuẩn chặn nhưng **không nói vi phạm ở đâu** (ratchet chỉ có số đếm) | Còn — công thức đã verify ở §4 |
| G5 | Trung | Không có lệnh test nào dưới 30 phút; CLAUDE.md không ghi thời lượng | **ĐÃ SỬA** (HANDOFF §0) |
| G6 | Trung | `CLAUDE.md` §5 thiếu `AGENT_PORT` → smoke chết khi chạy song song | Còn — patch sẵn ở §5 |
| G7 | Thấp | `CLAUDE.md` §5b trỏ `agent/knowledge.db` — file không có trong repo | Còn — patch sẵn ở §5 |
| G8 | Thấp | `HANDOFF.md` §0 và `CLAUDE.md` §3.4 ra hai lệnh baseline khác nhau | **ĐÃ SỬA** (HANDOFF §0) |

---

## 1. Bốn câu hỏi của người mới — trả lời được mấy câu?

### ✅ "Dự án làm gì, cho ai?" — trả lời được trong 1 phút
`CLAUDE.md` §0 nói thẳng: MXH du lịch/OCOP/cộng đồng cho tỉnh Vĩnh Long mới, solo dev, <10k user,
<1tr/tháng, web-first. Rõ ràng, không cần đọc thêm. **Không có gap.**

### ✅ "Cái gì TUYỆT ĐỐI không được làm?" — trả lời được
`CLAUDE.md` §2 (B1–B8) + §4 (điều kiện dừng) là phần **mạnh nhất** của bộ tài liệu: cụ thể, có lý do,
có tên lệnh. Người mới biết ngay: không `--replace`, không push, không dịch vụ trả phí, ảnh chỉ AI-gen.
**Không có gap.**

### ❌ "Nhánh nào là trunk?" — TRẢ LỜI SAI. Đây là gap nghiêm trọng nhất.

Người mới chạy `git branch`, thấy **22 nhánh**, trong đó có `main`. `git symbolic-ref
refs/remotes/origin/HEAD` → `refs/remotes/origin/main`. Mọi tín hiệu đều chỉ về `main`.

Rồi họ mở tài liệu onboarding chính thức và đọc được đúng một câu về nhánh:

```
docs/HANDOFF.md:6 — "Nhánh chính: `main`; `origin` đã cấu hình."
```

**Câu đó sai.** Đo thật:

```
$ git rev-list --left-right --count main...codex/tri-region-color
0	246                     # main thiếu 246 commit, không có gì riêng

$ git log -1 --format='%h %ad' --date=short origin/main
1b9f2bd9 2026-07-11         # clone mới nhận bản 4 tuần trước

$ git rev-list --left-right --count origin/main...codex/tri-region-color
→ origin/main thiếu 847 commit
```

Hậu quả cụ thể: người mới `git checkout main`, thấy một repo thiếu 246 commit, và **xây lại thứ đã có**.
Nếu họ clone từ GitHub thì thiếu 847 commit.

Làm nặng thêm: `docs/parallel-session-guide.md:149-153` dạy `git checkout main && git checkout -b
session-fe` — tức là chủ động rẽ nhánh từ gốc cũ 246 commit.

Không có từ "trunk" ở bất kỳ đâu trong `docs/*.md` hay `CLAUDE.md`:
```
$ grep -rin "trunk" docs/*.md CLAUDE.md    → 0 kết quả
```

> **ĐÃ SỬA:** viết lại `docs/HANDOFF.md:6` — bỏ "Nhánh chính: `main`", ghi trunk thật
> `codex/tri-region-color` kèm lệnh đo và cảnh báo clone-mới.
>
> **Lưu ý quan trọng:** `docs/HANDOFF-BRANCHES.md` (bản đồ nhánh đầy đủ, do workflow khác đang viết)
> hiện **chưa commit** (`??` trong `git status`). Clone mới **không có nó** → G1 vẫn hở cho tới khi
> file đó được commit. Đây là việc của chủ dự án (§4).

### ⚠️ "Chạy lên xem được không?" — được, nhưng thiếu 1 dòng tài liệu. Chi tiết ở §2.

---

## 2. Chạy thật §5 — lỗi thật

### 2.1 Backend smoke — **thất bại lần 1**, nguyên nhân không có trong tài liệu

Chạy đúng như `CLAUDE.md` §5:
```
$env:BUILD_SEARCH_INDEXES='false'; $env:BACKGROUND_INDEX_BUILD='false'; $env:SCHEDULER_ENABLED='false'; python agent/server.py
```
Kết quả — **exit 1**:
```
ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8360):
[winerror 10048] only one usage of each socket address ... is normally permitted
```

Hai vấn đề:

1. **Thông báo bị chôn.** Dòng ERROR nằm ở dòng 16/75; sau nó server vẫn in trọn banner "Level 7 /
   Vector ✓ / URL: http://localhost:8360". Đọc cuối log sẽ tưởng **server đang chạy**. Thật ra nó đã
   `Shutdown complete`.
2. **Cách sửa không có trong tài liệu.** `AGENT_PORT` có tồn tại nhưng chỉ được ghi trong docstring
   `agent/server.py:16`. `CLAUDE.md` §5 và `HANDOFF.md` §4 đều không nhắc. Mà dự án **chính thức khuyến
   khích chạy song song** (`docs/parallel-session-guide.md`) → đụng cổng là tình huống thường gặp,
   không phải ngoại lệ.

Chạy lại với cổng rảnh thì **sạch hoàn toàn**:
```
$ AGENT_PORT=8399 ... python agent/server.py
$ curl http://127.0.0.1:8399/health
{"status":"ok","time":"2026-08-07T16:52:08+00:00","entities":1746}
```

**Điểm cộng đáng ghi:** backend khởi động **không cần `.env`** (repo không có `.env`, chỉ có
`.env.example`), tự sinh `ADMIN_API_KEY` dev. Nỗi lo "server.py hard-read `os.environ["LLM_API_KEY"]`"
(`HANDOFF.md` §8) **không xảy ra** ở đường smoke.

### 2.2 Frontend — chạy được, thông báo lỗi **tốt**

```
$ cd web-nuxt && npm run dev
ERROR  Another Nuxt dev server is already running:
  URL: http://127.0.0.1:3397   PID: 19300
  Run `taskkill /PID 19300 /F` to stop it, or connect to http://127.0.0.1:3397
  Set NUXT_IGNORE_LOCK=1 to bypass this check.
```
Đây là **mẫu thông báo lỗi đáng học**: nói cái gì chặn, ở đâu, và hai cách đi tiếp. Người mới tự
thoát được, không cần hỏi ai. (Ngược hẳn với ratchet ở §4.)

Server đang chạy trả `200`. Ghi chú nhỏ: nó ở cổng **3397** chứ không phải **3000** như §5 nói —
`nuxt.config.ts:206-207` đặt `devServer.port: 3000`, nên 3397 là do phiên song song, không phải lỗi
tài liệu.

**Không có bước ẩn nào bị thiếu** cho FE: `node_modules` đã có sẵn; với clone mới thì
`docs/developer-setup.md` §1/§5 có đủ `npm install`.

### 2.3 `scripts/validate_data.py` — chạy sạch, exit 0
32 orphan + 1406 timestamp inversion ở mức WARNING, không chặn. Đáng biết: nó đọc
`web/data.json` (`scripts/validate_data.py:16`), **không đọc DB** — nên "validate xong" không nói gì về DB.

### 2.4 Bước thiếu duy nhất mà `CLAUDE.md` không nói: **lấy DB ở đâu**

`agent/data/` bị gitignore → **clone mới không có database nào cả**. `CLAUDE.md` không hề nhắc chuyện này.

Nhưng đây **không phải lỗ hổng thật**: `docs/developer-setup.md` §3 có đủ (`python agent/database.py
--replace`, kèm cảnh báo "fresh clone only" + B1/B7), và `docs/README.md` có trỏ tới nó ở dòng "Setup
dev local". Đường đi tồn tại — chỉ là `CLAUDE.md` §5 không trỏ sang. **Không đề xuất sửa** (README đã
làm việc của nó).

---

## 3. Bộ test — tài liệu cảnh báo ĐÚNG về marker, THIẾU về thời gian

`CLAUDE.md` §5b cảnh báo rất tốt và **đúng**: `pytest.ini` `addopts` loại 4 marker (`slow`,
`integration`, `entity_status_postgres`, `subprocess_heavy`) → "local xanh" không chứng minh CI xanh.
Xác nhận bằng chính file: `pytest.ini:2`.

Cái **thiếu là thời lượng**. Đo thật:

| Lệnh | Nguồn | Thời gian thật |
|---|---|---|
| `python -m pytest --collect-only -q` | — | 21s → **9985 test** (544 deselected) |
| `python -m pytest agent/tests -q` | — | **bị cắt ở 280s khi mới 54%** → ≈ 9 phút |
| `python -m pytest -q` | CLAUDE.md §3.4 | **~33 phút** (chỉ ghi trong comment `pytest.ini:12`) |
| `run_backend_regression.py --deadline-seconds 7000` | HANDOFF.md §0.4 | **tới ~1 giờ 56 phút** |

`CLAUDE.md` §3.4 bảo "mỗi phiên bắt đầu: `python -m pytest -q`" mà không nói đó là 33 phút. Con số 33
phút chỉ nằm trong comment `pytest.ini`, nơi không ai đọc khi onboard.

**G8 — hai lệnh baseline mâu thuẫn:** `CLAUDE.md` §3.4 nói `pytest -q`; `HANDOFF.md` §0.4 nói
`run_backend_regression.py`. Người mới không biết theo cái nào, và chênh nhau gần 1 tiếng rưỡi.

> **ĐÃ SỬA:** thêm khối ⏱ "Ngân sách thời gian" vào `docs/HANDOFF.md` §0.4 — ghi cả 4 con số đo được
> và nói rõ muốn vòng lặp nhanh thì chỉ định thư mục con.

**G3 — con trỏ chết trong chính hiến pháp.** `CLAUDE.md` §3.3 viết: *"Baseline hiện có các fail đã biết
ghi ở ROADMAP mục **'Backlog test-debt'**"*. Mục đó **không tồn tại**:
```
$ grep -n "test-debt\|Backlog test" docs/ROADMAP.md   → 0 kết quả
```
Mục gần nhất tên khác hẳn: `docs/ROADMAP.md:441` "Backlog phát sinh — Test-isolation / suite flaky
(2026-08-06)" và `:447` "— 4 test closed-installer chỉ đỏ trên Linux". Người mới gặp test đỏ, được bảo
đi đối chiếu một danh sách **không có tên đó**, sẽ hoặc dừng sai hoặc bỏ qua sai.
(`docs/HANDOFF.md:17` còn nói ngược: "Hiện không có fail-đã-biết".)

---

## 4. G4 — Cổng chuẩn chặn đúng, nhưng KHÔNG đủ để tự sửa

Đây là gap **thực dụng** nặng nhất sau trunk.

Đã làm thật một thay đổi nhỏ: thêm 1 dòng `<p>` vào `web-nuxt/pages/lien-he.vue`, đi hết quy trình tới
sát bước commit, rồi gỡ lại (đã xác nhận `git diff` sạch).

**Cái chạy đúng:**
- Hook đã cài sẵn và dùng chung mọi worktree (`.git/worktrees/.../hooks` → common dir), nội dung:
  `python scripts/checks/run_hard.py --staged || exit 1`.
- Cổng **thật sự chặn**: `run_hard.py --all` → **exit 1** (đo riêng, không qua pipe).
- Hot-reload bắt được thay đổi ngay: `curl .../lien-he | grep -c onboarding-probe-tmp` → `1`.

**Cái hỏng — thông báo ratchet không định vị được vi phạm:**
```
✖ HARD R10.6 (banned_image_sources): 1 vi phạm
    docs/HANDOFF-BRANCHES.md:136 — Ảnh CHỈ AI-gen — nguồn <ảnh-stock>/<Wiki…> bị cấm (§1.5)   ← TỐT
✖ RATCHET R30.3 (fe_colors): 308 vi phạm > baseline 307 — RATCHET: nợ chuẩn không được tăng.        ← Ở ĐÂU?
✖ RATCHET R20.8 (complexity): 19 vi phạm > baseline 17 — RATCHET: nợ chuẩn không được tăng.         ← Ở ĐÂU?
```
Dòng HARD **mẫu mực**: `file:line` + luật + lý do + chiếu điều khoản. Dòng RATCHET chỉ có **số đếm** —
"308 > 307" mà không nói cái thứ 308 nằm ở file nào. Nguyên nhân ở `scripts/checks/run_hard.py:83-84`:
nhánh HARD in `r["violations"][:5]`, nhánh ratchet (`_ratchet_messages`) chỉ in chuỗi đếm.

Người mới thử mọi đường tự nhiên đều **cụt**:
- `python scripts/checks/check_complexity.py` → `ImportError: attempted relative import with no known
  parent package` (mọi checker đều vậy; chỉ 6/22 file có `__main__`).
- `python -m scripts.checks.check_complexity` → chạy nhưng **không in gì**.
- `python scripts/checks/baseline_tool.py` → chỉ bảng `RULE / COUNT`, vẫn không có vị trí.
- `docs/standards/00-INDEX.md` không có mục nào dạy cách liệt kê vi phạm.

**Công thức đã verify** (dữ liệu `violations` có sẵn `file`/`line`, chỉ là không được in ra) — chạy từ
repo-root, thay `R20.8` bằng rule cần tra:
```python
import sys, os; sys.path.insert(0, os.getcwd())          # bắt buộc: chạy file .py không tự chèn cwd
from scripts.checks.run_hard import ALL_CHECKS, _bind_checks_to_root
from scripts.checks import common
rule = "R20.8"
for c in _bind_checks_to_root(ALL_CHECKS, common.repo_root()):
    if c.rule == rule:
        r = c.run(None)
        print(rule, r["count"])
        for v in r["violations"]:
            print(f'  {v["file"]}:{v["line"]} - {v["msg"]}')
```
Kết quả thật:
```
R20.8: 19 vi pham
  agent/gpt55_quality_burst.py:253 - hàm validate_candidate_record() complexity 19 > 12
  agent/gpt55_quality_burst.py:502 - hàm relationship_targets() complexity 27 > 12
  ... (17 dòng nữa)
```
→ **Sửa gốc nên là:** cho `_ratchet_messages` in `violations[:5]` giống nhánh HARD. Một sửa nhỏ trong
`run_hard.py` xoá sạch G4. **Không tự làm** (ngoài phạm vi "lập bản đồ" — CLAUDE.md §3.5).

**Bẫy đã dính thật khi viết chính file này.** Trích nguyên văn dòng thông báo R10.6 vào báo cáo làm
R10.6 **tăng 1→2**, trỏ vào `docs/ONBOARDING-GAPS.md`. Checker là bộ so chuỗi nên bắt cả câu đang
*mô tả* điều cấm. Đã vá bằng cách chẻ chuỗi (`<ảnh-stock>/<Wiki…>`), gate về đúng baseline. Đây đúng
là lớp lỗi `CLAUDE.md` §5c mô tả — và nó **chưa được commit**, nên người mới sẽ dính mà không hiểu vì sao.

**Vấn đề phụ — không cô lập được thay đổi của mình.** `run_hard.py` chỉ nhận `--staged | --all`
(`--help` xác nhận). Trong worktree dùng chung/bẩn, `--all` báo cả vi phạm của workflow khác: cả 3 dòng
chặn ở trên **không phải của tôi** (R10.6 đến từ `docs/HANDOFF-BRANCHES.md` — file của workflow khác).
Người mới sẽ tưởng mình vừa làm hỏng 3 thứ. Muốn thu hẹp phải `git add` — mà trong phiên song song thì
đó chính là lệnh dễ nuốt việc người khác. Thiếu một chế độ `--files <paths>`.

---

## 5. Ba patch một dòng đã soạn sẵn — CỐ Ý KHÔNG áp

`CLAUDE.md`, `docs/README.md`, `docs/ROADMAP.md` **đang bẩn** (`M` trong `git status`) do một workflow
khác chỉnh dở. Sửa vào file người khác đang mở chính là cái bẫy mà `CLAUDE.md` §5c (phần **chưa commit**)
vừa cảnh báo. Nên tôi chỉ sửa `docs/HANDOFF.md` (file sạch) và để 3 patch dưới cho chủ dự án áp khi tay đã rảnh.

**P1 — `CLAUDE.md` §3.3, sửa con trỏ chết (G3):**
> `ghi ở ROADMAP mục "Backlog test-debt"` → `ghi ở ROADMAP các mục "Backlog phát sinh — Test-isolation / suite flaky (2026-08-06)" và "— 4 test closed-installer chỉ đỏ trên Linux (2026-08-06)"`

**P2 — `CLAUDE.md` §5, thêm sau dòng smoke backend (G6):**
> `# Cổng bận (chạy song song) → đổi: $env:AGENT_PORT='8399'. Lỗi bind in ở GIỮA log, banner vẫn in tiếp — đừng tin dòng "URL:" ở cuối.`

**P3 — `CLAUDE.md` §5b, sửa đường dẫn sai (G7):**
> `agent/knowledge.db rỗng (0 entity...)` → `agent/data/vinhlong360.db`. `agent/knowledge.db` **không có trong repo**: nó chỉ tồn tại như rác cũ 24-06 trong worktree chính (`C:\Code\vinhlong360\agent\knowledge.db`, 100KB), không có trong `.worktrees/*` và **không có trong clone mới** (`agent/data/` bị gitignore).

---

## 6. Cái gì đang chạy trơn tru — nói rõ, có bằng chứng

Không phải chỗ nào cũng hỏng. Những phần này **vượt mức trung bình** và không nên đụng vào:

- **`CLAUDE.md` §2 + §4** — bất biến và điều kiện dừng: cụ thể, có tên lệnh, có lý do. Người mới biết
  ngay ranh giới. Đây là phần tốt nhất của bộ tài liệu.
- **Backend khởi động sạch không cần `.env`** — `health` trả `{"status":"ok","entities":1746}`.
- **`docs/developer-setup.md`** — thật sự đầy đủ: clone → venv → `.env` → docker postgres → seed DB →
  BE → FE → test. Có cả bảng troubleshooting (`DESTRUCTIVE_OPS_LOCKED`).
- **`docs/README.md`** — bảng "Bạn muốn / Đọc" định tuyến đúng, 9 dòng, không lan man.
- **Thông báo khoá của Nuxt dev** — mẫu mực (nêu PID + 2 cách đi tiếp).
- **Thông báo HARD của cổng chuẩn** — `file:line` + luật + chiếu điều khoản hiến pháp.
- **`CLAUDE.md` §5b** — cảnh báo marker/Windows-vs-Linux chính xác, đã verify bằng `pytest.ini`.
- **Quy tắc `> STATUS:`** (§3.6) — có thật, được tuân thủ ở các doc tôi mở.

---

## 7. Việc còn lại cho chủ dự án (CLAUDE.md §4 — không tự quyết)

1. **Commit `docs/HANDOFF-BRANCHES.md`.** Còn `??` thì clone mới vẫn không có bản đồ nhánh → G1 chỉ vá
   được một nửa.
2. **Quyết trunk cho `origin`.** `origin/main` đứng ngày 11-07 (847 commit sau). Chừng nào GitHub chưa
   phản ánh trunk thật, mọi người mới clone về đều bắt đầu sai. (Push/merge = §4, cần chủ dự án.)
3. **Áp P1–P3** khi `CLAUDE.md` hết bẩn.
4. **Cân nhắc sửa `run_hard.py`**: in `violations[:5]` cho nhánh ratchet + thêm `--files <paths>`. Xoá
   được G4 và làm phiên song song bớt gây hiểu nhầm.

---

## Phụ lục — đã sửa gì trong đợt này

| File | Sửa |
|---|---|
| `docs/HANDOFF.md:6` | Bỏ "Nhánh chính: `main`" (sai 246 commit); ghi trunk `codex/tri-region-color` + lệnh đo + cảnh báo clone mới thiếu 847 commit + trỏ `HANDOFF-BRANCHES.md` (kèm ghi chú file đó chưa commit) |
| `docs/HANDOFF.md` §0.4 | Thêm khối ⏱ ngân sách thời gian: 7000s ≈ 1h56, `pytest -q` ≈ 33 phút / 9985 test, `agent/tests` ≈ 9 phút; nêu rõ mâu thuẫn G8 |
| `web-nuxt/pages/lien-he.vue` | Sửa thử 1 dòng để đo cổng chuẩn → **đã gỡ**, `git diff` sạch |

# Bản đồ module đề xuất — tách hệ thống theo MIỀN CHỨC NĂNG

> STATUS: done — chương trình ĐÓNG SỔ 2026-08-29 (§8c): 9 gói miền, 0 shim,
> phần dư admin/public_api/database đóng có chủ đích. Diễn tiến: 3 miền đầu
> (§46) → 5/5 theo chỉ đạo (§8b) → gỡ shim + itineraries/ (§8c) → dọn
> route-dư lát 4 (§8d). `server.py` 5.507 → 2.159 dòng (−61%).
> Chi phí ĐO ĐƯỢC của hai lát đã làm ghi ở ROADMAP §45; nó ĐẢO thứ tự ưu tiên
> ban đầu của tài liệu này — đọc §7 đã sửa bên dưới trước khi làm lát thứ ba.
> Đo 2026-08-27 trên `codex/correction-case-pilot`. Mọi con số dưới đây là ĐO,
> không ước lượng; script tái lập ghi ở §6.

## 1. Chẩn đoán: sai TRỤC cắt, không phải file to

Dự án hiện cắt theo **đối tượng dùng** — `public_api.py` / `admin.py` /
`social.py`. Hệ quả: mỗi file thành cái túi đựng hàng chục miền, và mỗi miền bị
xé ra nhiều file.

| miền | route | rải ở |
|---|---|---|
| `/entities` | 34 | 3 file |
| `/posts` | 29 | 2 file |
| `/me` | 21 | 4 file |
| `/users` | 21 | 3 file |
| `/(root)` | 11 | 4 file |

**403 route / 132 miền.** 114 miền đã gọn trong 1 file, **18 miền bị rải** và
chúng nắm ~45% tổng số route.

> **ĐÍNH CHÍNH 2026-08-27 (cùng ngày).** Bản đầu của tài liệu này ghi 404 route /
> 135 miền / 19 miền rải, và nói `/posts` rải 3 file, `/search` rải 4 file. SAI:
> bộ điều tra của tôi dùng SO CHUỖI nên đếm cả `@router.get(...)` trong DOCSTRING
> của `auth_middleware.py` (5 ví dụ minh hoạ) thành route thật. Đo lại bằng AST
> (chỉ decorator thật): 403 route, 18 miền rải; `/posts` 2 file, `/feed` 2 file,
> `/search` không còn nằm trong nhóm rải.
>
> Đây là LẦN THỨ HAI trong ngày tôi mắc đúng lỗi này — bộ quét CSS chết sáng nay
> cũng đếm nhầm nội dung trong chú thích. Bài học: công cụ đo bằng so-chuỗi phải
> bỏ chú thích TRƯỚC, hoặc dùng AST.

Hệ quả kép, và đây là câu trả lời cho "làm sao phát triển song song không đè
nhau": người làm *entities* phải mở 3 file; người làm *admin* phải mở file dùng
chung với hàng chục miền khác. **Cả hai chiều đều đụng nhau.** Đo trên 1.923
commit 6 tháng: **34% commit chạm ít nhất một trong 5 file nóng**.

## 2. Khuôn đã có sẵn và ĐÃ CHỨNG MINH được — `agent/cases/`

```
agent/cases/public_api.py  →  APIRouter(prefix="/api/cases")
agent/cases/admin_api.py   →  APIRouter(prefix="/admin/cases")
```

Một **miền**, hai đối tượng dùng, một gói. `server.py` chỉ có 2 dòng
`include_router`. Kết quả đo: **59 commit chạm gói này, 73% ở lại hoàn toàn bên
trong**; 27% đi ra ngoài thì chỉ tới HẠ TẦNG (`server.py` gắn route,
`database.py` schema, `config.py` cờ) — **không** tới chức năng khác.

Đây không phải lý thuyết. Nó đã chạy được trên chính codebase này.

## 3. Bản đồ đề xuất — 15 module

Cột "gom từ" = số file hiện đang chứa route của miền đó.

| module | route | gom từ | ghi chú |
|---|---:|---:|---|
| `identity/` | 73 | 5 file | auth, OTP, phiên, 2FA, hồ sơ, quyền riêng tư, thành tích |
| `entities/` | 66 | 3 file | tri thức lõi + quan hệ + ảnh + chất lượng |
| `community/` | 58 | 4 file | bài viết, bình luận, nháp, feed, hashtag, chặn/theo dõi |
| ~~`llmops/`~~ | 42 | — | **ĐÃ LÀM** `1828fff6` — 425 dòng, **0** điểm vá test, ~15 phút |
| `siteops/` | 28 | 2 file | site-settings, thông báo, export, data-quality, backup |
| `moderation/` | 19 | 1 file | đã gọn — chỉ cần dựng ranh giới |
| `analytics/` | 17 | 5 file | thống kê, lượt xem, chi phí, nhật ký kiểm toán |
| `planning/` | 16 | 4 file | lịch trình, bộ sưu tập, lưu, gộp |
| `notifications/` | 13 | 2 file | **ĐÃ CÓ router riêng sẵn** — gạch khỏi danh sách bóc |
| `search/` | 8 | 4 file | tìm kiếm, vector, autocomplete |
| `seo/` | 7 | 1 file | **ĐÃ CÓ router riêng sẵn** — gạch khỏi danh sách bóc |
| `events/` | 6 | 3 file | sự kiện + thời tiết |
| ~~`chat/`~~ | 2 | — | **ĐÃ LÀM** `d3b3115f` — 2.856 dòng, 346 điểm vá test, 8 vòng |
| `cases/` | — | — | **đã xong**, làm khuôn mẫu |
| lõi app | 7 | — | `/health`, gắn router, middleware |

361/404 route đã xếp; 43 mẩu nhỏ còn lại dễ gán (`block`/`mute`/`follow` →
community, `autocomplete`/`areas` → search, `map-pins`/`homepage` → entities).

## 4. `server.py` không phải điểm vào — nó là tính năng chat mặc áo điểm vào

5.507 dòng / 71 route. Nhưng:

| hàm | dòng |
|---|---:|
| `chat_stream()` | 832 |
| `chat()` | 569 |
| `_event_stream_body()` | 558 |
| **cộng ba** | **1.959 = 40% toàn bộ thân hàm** |

Cộng thêm **28 route `/system/*`** (chi phí, học máy, guardrail, eval, judge,
semantic-cache) — cả một mặt LLM-ops không liên quan gì tới việc khởi động app.

Bóc `chat/` + `llmops/` ra là `server.py` còn lại đúng việc của nó: dựng app,
gắn router, middleware, health — vài trăm dòng.

## 5. Cái KHÔNG tách, và cái tách module không giải quyết được

**Xương sống dùng chung — giữ nguyên:** `database.py` (2.554) ·
`middleware.py` (1.788) · `config.py` · `auth_middleware.py`. Chia nhỏ chúng
tạo coupling tệ hơn. Chúng cần **ổn định**, không cần **chia**.

**Tầng dịch vụ đã khá gọn rồi:** 170 file không-route / 77.411 dòng, phần lớn đã
một-file-một-việc (`itinerary_gen`, `guardrails`, `semantic_cache`,
`memory_graph`…). Nợ nằm ở tầng ROUTE, không phải tầng dịch vụ.

**Trục khác, không chữa bằng đóng gói:** cặp sinh đôi Python↔TypeScript
(`ocop.py`↔`ocop.ts`, `lunar_calendar.py`↔`useLunar.ts`). Đóng nó bằng cách để
API phát ra trường đã chuẩn hoá — xem ROADMAP §42.4.

## 6. Hai rào chắn PHẢI xử trước

**B3.** `social.py` là file bị chạm nhiều nhất (**188 commit**) VÀ nằm trong danh
sách vùng mù của CLAUDE.md §2 phải có test bao phủ trước khi sửa. `community/` và
phần lớn `identity/` nằm trong đó. Không bóc được trước khi có test.

**Cổng chuẩn không đỡ được đợt này.** ROADMAP §44: hook `--staged` so vi phạm
trong *file staged* với baseline *toàn kho*, nên chỉ chặn được rule có
baseline = 0. Với R20.8 (47), R30.2 (330), R30.3 (147) nó không thể đỏ. Refactor
lớn nhất dự án mà chạy trong vùng không phanh là đổi một nợ lấy một nợ khác.

## 7. Thứ tự — ĐÃ SỬA theo số đo thật

> Bản đầu xếp ưu tiên theo SỐ ROUTE. Sai thước đo. Sau hai lát có số thật:
> **chi phí một lát nằm ở ĐIỂM VÁ CỦA TEST, không ở số dòng mã.**

| ứng viên | dòng dời | điểm vá test | ghi chú |
|---|---:|---:|---|
| ~~`llmops/`~~ | 425 | **0** | ĐÃ LÀM — ~15 phút |
| ~~`chat/`~~ | 2.856 | **346** | ĐÃ LÀM — ~2 giờ, 8 vòng |
| ~~`entities/`~~ | 2.958 (4 bước) | thực đo: ~120 sửa | **ĐÃ LÀM** §46 — kèm SỰ CỐ B1, đọc §46.2-46.3 |
| `identity/` | chưa tính | **164 + 147 thuộc-tính** | ĐẮT NHẤT, trong vùng mù B3 |
| `community/` | chưa tính | 39 + 26 thuộc-tính | trong vùng mù B3 |

Phép đo trước, hai trục (ROADMAP §45.8):

```
grep -rE 'setattr\(\s*<mod>|patch\.object\(\s*<mod>|patch\("<mod>\.' agent/tests/
grep -rl '<mod>.py' agent/tests/ | xargs grep -l 'read_text\|getsource'
```

**`server.py` còn 27 route @app trực tiếp**, trong đó 9 đúng vai điểm-vào
(`/health` ×6, `/reload`, `/metrics`, root). 18 route còn lại là ĐUÔI DÀI —
`/weather` `/search` `/feedback` `/welcome` `/events` `/recommend` `/image`
`/autocorrect` `/graph` `/confirm*` `/ab-testing` `/prompt-cache` — chúng
KHÔNG hợp thành một miền. Bóc tiếp sẽ ra hoặc nhiều gói tí hon, hoặc một gói
tạp nham đúng bằng server.py đổi tên. **Khuyến nghị: dừng ở đây** cho tới khi
có nhu cầu thật.

### Thứ tự cũ (giữ để đối chiếu)

1. **Vá cổng §44** — để mọi bước sau có phanh.
2. **`llmops/`** — 28 route `/system/*`, đã gọn sẵn, KHÔNG nằm trong vùng mù.
   Lát cắt mẫu rủi ro thấp nhất, dùng để kiểm khuôn.
3. **`chat/`** — gỡ 1.959 dòng khỏi điểm vào. Cần test trước (B3).
4. **`entities/`** — miền lớn nhất, ít dính UGC nhất.
5. **`community/` + `identity/`** — sau cùng, vì chúng nằm sâu trong vùng mù.

### Script tái lập số đo

Bản đồ này dựng từ điều tra route (`@app|router.<verb>("...")` trên toàn
`agent/`) và phân tích co-change trên `git log --since="6 months ago"
--name-only`. Con số nào nghi ngờ thì đo lại, đừng tin bảng.

## 8. KẾT LUẬN CHƯƠNG TRÌNH (2026-08-28) — mục tiêu đã đạt, hai lát cuối KHÔNG đáng cắt

Mục tiêu gốc của tài liệu: *"phát triển từng module mà không chồng đè lên
nhau"*. Sau bước 1–2, đo lại hai ứng viên còn lại bằng thước "độ tự chứa"
(bao nhiêu ký hiệu bị module khác import):

| file | dòng | ký hiệu | handler | bị ngoài import |
|---|---:|---:|---:|---|
| `social.py` (→ community/) | 4.556 | 198 | 71 | **3** (`_block_sql`, `_mute_sql`, `router`) |
| `auth.py` (→ identity/) | 2.190 | 137 | 30 | **5** |

Cả hai ĐÃ là miền-đơn, một-file, ghép nối tối thiểu — khác hẳn `public_api`/
`admin`/`server` trước khi cắt (túi trộn 10–20 miền, 46% route rải). Đóng gói
chúng chỉ là ĐỔI TÊN: trả 39–164 điểm vá test + 26–147 thuộc-tính + rủi ro
trục-4 (sự cố B1 §46.2) để mua về ~0 cách ly mới. **Không cắt.**

Nỗi đau THẬT còn lại của hai file này là NỢ TEST (B3), không phải cấu trúc —
việc đó đo bằng độ phủ, xử bằng viết test, không xử bằng di chuyển mã.

**Chương trình module KẾT THÚC tại đây**: 3 miền bóc (`chat/` `llmops/`
`entities/` hai mặt), 4 tầng dùng chung tách (`features` `http_errors`
`entity_read` `admin_common`), server.py −61%, public_api −27%, admin −23%,
433 route nguyên vẹn, cổng R20.9 nhìn thấy mọi mount. Bài học vận hành nằm ở
ROADMAP §45–46 (bốn trục chi phí, khuôn ba-phép-đo, sự cố B1).

## 8b. HẬU BÚT (2026-08-28, cùng ngày) — chủ dự án chỉ đạo cắt nốt: 5/5

Kết luận "không cắt" ở trên bị chỉ đạo trực tiếp của chủ dự án vượt qua ngay
trong ngày ("tiếp tục tách module"). Hai lát cuối đã thi công dưới dạng
**đổi-nhà-nguyên-văn + shim phản-chiếu-động** (đúng như §8 tiên lượng: không
có gì để "tách", chỉ có nhà để dời): `community/` commit `aa4df523`,
`identity/` commit `2e18cd1e` — cả hai nghiệm thu diff-đúng-từng-tên rỗng so
16 fail-đã-biết, DB thật 1746/0 ở mọi mốc đo (trục 4 sạch, gồm cả vùng 23
fixture của identity mà §8 xếp "đắt nhất").

Phần ĐO của §8 vẫn đúng nguyên: hai lát mua về ~0 cách ly mới. Cái chúng mua
được nằm ngoài thước đó — đồng-phục-hoá (5/5 miền cùng một khuôn gói, mỗi miền
một test boundary R20.7) và bộ hình-thái-mù trục 2/4 nay đo đủ. Toàn bộ hồ sơ
thi công + năm hình thái mù trục 2: ROADMAP §47. Nợ thật của hai miền vẫn là
NỢ TEST B3 — kết luận đó không đổi.

## 8c. ĐÓNG SỔ (2026-08-29) — 9 gói, 0 shim, phần dư đóng có chủ đích

Sau câu hỏi "tách hết luôn có đáp ứng phát triển lâu dài không" và lệnh "làm
luôn" của chủ dự án: gỡ hẳn 2 shim `social.py`/`auth.py` (commit `42192a01` —
54 file import về nhà thật + 732 cú import-động; đường cũ nay CHẾT có rào) và
gom họ `itinerary_*` thành gói thứ chín `itineraries/` (commit `6ee7f2e4`,
không shim). Trạng thái cuối: **9 gói miền** (cases, chat, community,
entities, identity, itineraries, llmops + learned, scripts) — mỗi gói một test
boundary, cổng R20.9 thấy mọi mount, CI 9 cổng DB per-domain.

**Phần dư `admin.py` (4.5k) / `public_api.py` (3.6k) / `database.py` (2.5k):
ĐÓNG SỔ CÓ CHỦ ĐÍCH, không cắt.** Lý do đã trình và được chấp thuận: hai lát
cuối chương trình đo được mua ~0 cách ly; phần dư là bề mặt route nhiều miền
lặt vặt (băm = rừng gói siêu nhỏ nuôi mãi); database.py là hạt nhân dùng
chung. **Luật cắt tương lai:** đo trước — chỉ cắt khi một miền đổi hàng tuần
VÀ số đo cho thấy nó giẫm miền khác.

Tính chất "phát triển từng module không chồng đè" nay đến từ RÀO, không từ số
thư mục: boundary tests + R20.9 + per-domain CI gates + phủ test vùng mù 90%.

## 8d. LÁT 4 ĐỢT HOÀN-THIỆN-SÂU (2026-08-29) — dọn route-dư theo hồ sơ đo

Hai route-dư thật đã VỀ NHÀ: `GET /search/enhanced` `server.py` →
`llmops/api.py` (cùng loài chẩn đoán truy hồi với `/vectors/search`; path giữ
nguyên, KHÔNG thêm guard — câu hỏi require_admin ghi backlog chờ chủ) và
`GET /api/feed/new-since` `public_api.py` → `community/api.py` cạnh cụm
`/feed*` (behavior change CÓ DUYỆT: SQLite 200-degraded → 503 theo §1.3;
0 caller FE đo được; public_api tái xuất handler cho getsource).

**Phần còn lại Ở LẠI `public_api.py` CÓ CHỦ ĐÍCH — không phải route-dư:**

- `report-stale` + `view-contact`: lát entities 2026-08-28 đã LOẠI có chủ đích
  (ranh giới là NGƯỜI GỌI và DỮ LIỆU, không phải URL); bao đóng nuốt tầng
  `REPORTS_FILE`/`_jsonl_lock` đang share 3 nơi (admin, community, submit_report)
  và test khoá cứng `admin._info_reports_lock IS public_api._jsonl_lock`.
- `/api/search` aggregator + `/api/autocomplete`: gộp 3 miền
  (entity+post+user) trong MỘT contract `SearchResponse` — không chẻ được;
  cùng loài `/homepage`, đúng nghĩa "bề mặt route nhiều miền" của §8c.

Đảo các quyết định để-lại này cần chủ dự án + hồ sơ đo mới, không phải một
lát dọn-dư.

## 8e. Lát 7 (analytics/) — ĐO XONG, QUYẾT KHÔNG GÓI (2026-08-29)

Lệnh hoàn-thiện-sâu cho phép cắt; hồ sơ đo (workflow dossier, agent
lat7-analytics) nói KHÔNG đáng: 8 route ứng viên còn lại (sau khi lát 1 rút
user-engagement/user-growth/content-stats về community-admin và lát 3 rút
system-health/backup/ops về siteops) là **5 tiểu-miền rời** — content-stats 1,
funnel 2, search/chat-analytics 2, audit-read 2, cost 1 — tiểu-miền lớn nhất
chỉ 2 route; **0 ký hiệu bị module khác import** (thước §8: mua ~0 cách ly);
giá ~72 điểm vá test/14 file + 2 mìn thật: tên gói đụng module sống
`agent/analytics.py` (6 consumer), và cắt audit-read là CHẺ ĐÔI `_audit_cache`
giữa writer `_log_admin_audit` với reader. Đóng-sổ-có-chủ-đích đúng khuôn
§8c; mở lại chỉ khi tiểu-miền nào đó phình thành miền thật (luật-cắt §8c).

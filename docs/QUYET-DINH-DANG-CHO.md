> STATUS: active
> Ngày lập: 2026-08-07 · Đo trên nhánh `codex/tri-region-color` @ `10d9bb69`
> **Đây là SỔ, không phải kế hoạch.** Mỗi mục chờ đúng MỘT câu trả lời của chủ dự án.
> Không mục nào được tự quyết (CLAUDE.md §4). Điền cột **CHỐT** → lúc đó mới mở task.

# Sổ quyết định đang chờ chủ dự án

## 0. Cách dùng sổ này

Trước sổ này, các khoản đang chờ nằm rải trong commit message, báo cáo audit, và trí nhớ
phiên làm việc. Người mới vào không có cách nào biết cái gì đang chờ mình. Sổ này gom tất
cả vào một chỗ, mỗi khoản đã **tự kiểm lại bằng lệnh chạy được hôm nay** — không chép mù
từ ghi chú cũ. Mười khoản từng nằm trong danh sách hóa ra đã được giải quyết; chúng nằm ở
**§4** kèm commit đóng, không nằm trong phần đang chờ.

Mỗi khoản có: **BỐI CẢNH** (đủ để quyết mà không phải điều tra lại) — **LỰA CHỌN** —
**ĐÁNH ĐỔI** — **AI CHỊU** — **NẾU KHÔNG QUYẾT**. Không khoản nào đề xuất đáp án thay chủ
dự án; chỗ nào có gợi ý thì ghi rõ là gợi ý.

**Thứ tự = độ GAP**, không phải độ khó:

| Nhóm | Nghĩa | Số khoản |
|---|---|---:|
| **A** | Chặn việc khác — mỗi ngày treo là một ngày người khác đứng chờ | 6 |
| **B** | Chặn mở công khai — gỡ `NUXT_PUBLIC_SITE_NOINDEX` phải qua đây | 7 |
| **C** | Nợ sống chung được — nhưng chi phí tăng theo thời gian | 10 |

---

## 1. Bảng tóm tắt

| Mã | Khoản | Chặn cái gì | CHỐT |
|---|---|---|---|
| **A1** | 12 CVE npm vs cổng đóng băng `package.json` + `package-lock.json` | mọi thay đổi phụ thuộc frontend | |
| **A2** | Migration 075 đã viết, chưa chạy ở đâu | bump `PG_REQUIRED_SCHEMA_VERSION`, perf đường nóng | |
| **A3** | 124 mã hành chính chưa vào prod Postgres | vòng export kế tiếp sẽ xoá mã | |
| **A4** | 17 câu hỏi dữ liệu sự kiện lệch âm/dương | mọi task chạm `type=event` | |
| **A5** | Taxonomy 3 vùng mang tên tỉnh cũ | nhánh `tri-region-color`, §1.6 | |
| **A6** | `web/data.json` mang 1746 `verifiedAt` chết | claim E-E-A-T, pitch B2G, mọi lần regenerate | |
| **B1** | Ảnh 3,3% — dịch vụ ảnh AI đang tắt | trụ ĐÚNG (ngưỡng 30%) | |
| **B2** | 43,8% mô tả dưới 200 ký tự | trụ ĐÚNG (ngưỡng ≤15%) | |
| **B3** | Cộng đồng nằm trên nav nhưng "sắp mở" | trụ HỢP PHÁP (kiểm duyệt UGC) | |
| **B4** | `TOTP_ENC_KEY` chưa đặt trên prod | bật 2FA (đặt sau = khoá vĩnh viễn user) | |
| **B5** | Prod chạy systemd hay docker-compose? | `TRUSTED_PROXIES`, rate-limit theo IP | |
| **B6** | NĐ147 — có thuộc diện không? | trụ HỢP PHÁP; cần luật sư (Track-H) | |
| **B7** | Gỡ noindex khi nào | cổng cuối cùng | |
| **C1** | `comments.updated_at` — thêm cột hay bỏ nhãn "đã sửa" | nhãn "đã sửa" trên bình luận | |
| **C2** | `WEATHER_API_KEY` chưa đặt | khối thời tiết chạy chế độ câm | |
| **C3** | Lịch vạn niên 1968–1975 có hai đáp án | 8 năm dữ liệu lịch | |
| **C4** | Khi nào fork `dongthap360` + VPS thứ hai | mở rộng đa tỉnh, ngân sách §B8 | |
| **C5** | 6 `booking_note` báo giá tour — §1.4 | ranh giới pháp lý "chỉ giới thiệu" | |
| **C6** | 2 đơn vị đổi tên + 2 quy ước dấu | tên hiển thị, SEO 2 slug | |
| **C7** | 6 bản nháp nội dung + 4 quy ước biên tập | mở rộng lô nội dung lên 150 entity | |
| **C8** | 34 hàm bảo mật chưa nối dây + 3 biến `LOCKOUT_*` suông | `.env.example` đang quảng cáo thứ không chạy | |
| **C9** | 2 khoản closed-installer (ghim python, CI root) | test launch-safety trên Linux | |
| **C10** | 4 câu hỏi mô hình dữ liệu entity | phân loại 244 entity ăn uống | |

---

# NHÓM A — chặn việc khác

## A1. 12 CVE npm vs cổng đóng băng `package.json`

**BỐI CẢNH.** `npm audit` trong `web-nuxt` đo hôm nay: **12 lỗ — 2 critical, 8 high, 1
moderate, 1 low**. Nặng nhất nằm ở chính `nuxt` (cài `4.4.8`, `package.json` khai
`^4.4.8`): sáu advisory, trong đó `GHSA-hxvh-4h3w-prp9` (CVSS 8.2 — route rule bị bỏ im
lặng với path viết hoa-thường lẫn lộn) và `GHSA-wm8w-6qjm-cv43` (CVSS 7.5 — cache payload
SSR lộ dữ liệu người này sang người khác) **không phụ thuộc server island**, tức chạm được
tới prod.

**Cái vá rẻ hơn tưởng, và đó mới là điểm đau.** Đo bằng `npm audit fix --dry-run`: cả 12 lỗ
đều `fixAvailable: true`, **không cái nào là semver-major** — `npm audit fix` trần (không
`--force`) đóng hết. `nuxt 4.5.1` nằm gọn trong dải `^4.4.8` đang khai, nên nhiều khả năng
**`package.json` không đổi một ký tự; chỉ `package-lock.json` đổi**. Cổng đóng băng dưới
đây pin **cả hai file**, nên nó chặn kể cả bản vá không đụng gì tới `package.json`.

Điểm chặn không phải kỹ thuật mà là **một cổng thiết kế cố ý**:
`web-nuxt/tests/tri-region-color-contract.test.ts:757-764` yêu cầu `package.json` và
`package-lock.json` **giống byte-for-byte** bản ở commit `358fe697`. Sửa một ký tự trong
`package.json` = test đỏ. Cổng này được dựng có chủ đích (comment `:751-756`) để không ai
lén thêm dependency; nó không phân biệt "lén thêm" với "vá CVE".

Phía Python **sạch**: `pip-audit -r requirements.txt` → `No known vulnerabilities found`.
CI đã có job quét (`ci.yml:520-547`) nhưng **`continue-on-error: true`** (`:523`) — nó báo
chứ không chặn, nên 12 lỗ này chưa từng làm CI đỏ.

Repo **không dùng server island** (không có file `.server.vue`, không có `<NuxtIsland>`),
nên bốn advisory họ island (kể cả RCE `GHSA-9473-5f9j-94wq`) nhiều khả năng không với tới
prod. Nhưng `routeRules` được dùng nặng (`nuxt.config.ts:161-176`: 14 rule, gồm
`/admin/**: { ssr: false }` và proxy `/admin-api/**`), đúng bề mặt của `GHSA-hxvh-4h3w-prp9`.

**LỰA CHỌN.**
1. **Dời mốc đóng băng** sang commit sau khi chạy `npm audit fix`, ghi giải trình vào
   comment của test (đã có tiền lệ: mốc từng dời `96bfba4c` → `358fe697` cho `axe-core`).
2. **Giữ mốc, hoãn vá.** Chấp nhận 12 lỗ tới khi có đợt nâng dependency riêng.
3. **Đổi bản chất cổng**: pin `package.json` (chặn thêm/bớt dependency — mục đích gốc)
   nhưng **thả `package-lock.json`**. Sửa test một lần, hết va chạm về sau.
4. **Bật `continue-on-error: false`** cho job audit — biến CVE thành cổng chặn thật.

**ĐÁNH ĐỔI.** (1) rẻ nhất nhưng làm mòn ý nghĩa cổng: dời mốc lần hai trong ba ngày thì
lần thứ ba sẽ dời không ai hỏi. (2) giữ được kỷ luật nhưng để 8 high sống trên prod, và
`npm audit` sẽ báo lại ở mọi lần CI. (3) đúng trọng tâm — cổng sinh ra để chặn *thêm
dependency*, mà thêm dependency luôn hiện ra ở `package.json`; đổi lại mất khả năng phát
hiện lock bị sửa tay. (4) làm CI đỏ ngay hôm nay và đỏ mỗi khi upstream ra advisory mới,
kể cả trên PR không liên quan — đúng lý do job này được đặt non-blocking từ đầu.

**AI CHỊU.** Người dùng đã đăng nhập (rò payload SSR chéo người dùng); mọi phiên làm việc
sau này chạm `web-nuxt/package.json`.

**NẾU KHÔNG QUYẾT.** Mọi thay đổi phụ thuộc frontend bị chặn cứng. Số CVE chỉ tăng —
upstream ra advisory mới thì con số 12 tự lớn lên mà không ai làm gì.

---

## A2. Migration 075 đã viết, chưa chạy ở đâu

**BỐI CẢNH.** `agent/migrations/075_hot_path_indexes_and_session_timeouts.sql` đã commit
(`970e44eb`). Nó làm hai việc: (a) 6 index trên đường nóng — đo thật trên cluster PG 16.4
riêng, seed 60k like: `likes(post_id)` từ Seq Scan 500 buffer/12,9ms xuống Index Only Scan
3 buffer/0,65ms, và câu đó nằm **trên đường ghi** của mỗi lượt thích; (b)
`statement_timeout=30s` + `idle_in_transaction_session_timeout=60s` đặt ở tầng **role**
`vl360`.

Nhưng `agent/database.py:127` vẫn `PG_REQUIRED_SCHEMA_VERSION = 74`, và hai test khoá con
số đó (`agent/tests/test_database.py:96`, `agent/tests/test_migration_chain.py:189`). Nghĩa
là: file có, chưa chạy ở đâu, và hệ thống chưa đòi nó.

Hai chi tiết vận hành đã ghi trong chính file, đọc trước khi chạy: migration **cố ý không
dùng `CREATE INDEX CONCURRENTLY`** (runner chạy cả chuỗi trong một transaction, PG từ chối
CONCURRENTLY trong transaction block — dùng sẽ *hỏng* chuỗi chứ không an toàn hơn); và
phần (b) **cần quyền SUPERUSER/CREATEROLE** để `ALTER ROLE`, thiếu quyền thì chỉ RAISE
WARNING chứ không hỏng migration — tức có thể chạy xong mà phần (b) im lặng không có hiệu
lực.

**LỰA CHỌN.**
1. Chạy trên prod trong một cửa sổ có backup, rồi bump gate lên 75.
2. Chạy prod nhưng **chưa** bump gate — tách rủi ro triển khai khỏi rủi ro gate.
3. Hoãn tới đợt deploy tiếp theo, gộp cùng các thay đổi khác.

**ĐÁNH ĐỔI.** (1) sạch nhất nhưng `CREATE INDEX` thường lấy khoá SHARE = **chặn ghi** trên
đúng 6 bảng đó; ở quy mô hiện tại cửa sổ tính bằng mili-giây, nhưng đó là suy luận từ kích
thước bảng, không phải đo trên prod. (2) an toàn hơn nhưng để lại trạng thái "prod có
index mà code không biết" — đúng loại lệch từng gây sự cố. (3) rẻ nhất hôm nay, nhưng
`likes(post_id)` nằm trên đường ghi: mỗi ngày hoãn là mỗi ngày trigger đếm like quét toàn
bảng.

**AI CHỊU.** Người dùng thích/bỏ thích bài (đường ghi); pool connection khi có truy vấn
chạy mãi.

**NẾU KHÔNG QUYẾT.** Chuỗi migration đóng băng ở 074. Mọi migration sau (kể cả C1 nếu chốt
thêm cột) xếp chồng lên một chuỗi chưa chạy — càng để lâu, cửa sổ deploy càng phải dài.

---

## A3. 124 mã hành chính chưa đẩy vào prod Postgres

**BỐI CẢNH.** Mã hành chính 5 chữ số (NQ 1687/NQ-UBTVQH15) đã có ở **cả `web/data.json`
lẫn DB local** (đủ 124 mã, commit `ba743473`) — cái còn thiếu là **prod Postgres**.
Mìn nằm ở chỗ: data.json là bản **export một chiều** DB→file
(`scripts/export_data.py`) — **lần export kế tiếp sẽ xoá sạch 124 mã đó**.
`scripts/sync_admin_code_to_db.py` đã viết để đẩy ngược về DB đúng đường ghi
(`db.upsert_entity()`, không phải SQL thô, để FTS5 + bảng CTI được dựng lại cùng
transaction). Script idempotent, mặc định `--dry-run`, từ chối ghi khi DB đã có mã khác
giá trị duyệt, và cần mở khoá hẹp `ALLOW_ADMIN_CODE_SYNC=1`.

Việc chưa làm là **chạy `--apply` trên prod Postgres** — thao tác ghi prod, thuộc điều
kiện dừng §4.

Ca A (16 xã lên phường) **đã chốt 2026-08-07**; phần còn treo là tên hiển thị của 2 đơn vị
(→ **C6**), và C6 **không đụng tới mã**, nên A3 chạy được độc lập.

**LỰA CHỌN.**
1. Chạy `--dry-run` trên prod trước, đọc kế hoạch, rồi `--apply` trong cùng cửa sổ với A2.
2. Chạy độc lập, cửa sổ riêng.
3. Hoãn — nhưng kèm điều kiện cứng: **không được chạy `export_data.py` trước khi sync**.

**ĐÁNH ĐỔI.** (1) một lần chạm prod cho hai việc, ít cửa sổ hơn, nhưng nếu hỏng thì khó
tách nguyên nhân. (2) dễ chẩn đoán, tốn hai cửa sổ. (3) không tốn gì hôm nay nhưng đặt một
mìn: bất kỳ ai chạy export (kể cả qua admin `POST /export`) sẽ mất 124 mã mà không có cảnh
báo nào.

**AI CHỊU.** Trang danh bạ hành chính, mọi tra cứu theo mã, và bất kỳ đối tác B2G nào hỏi
mã đơn vị.

**NẾU KHÔNG QUYẾT.** Mìn ở lựa chọn (3) vẫn nằm đó, và nó **không có ai canh** — script
export không biết gì về admin_code.

---

## A4. 17 câu hỏi dữ liệu sự kiện lệch âm/dương

**BỐI CẢNH.** `docs/2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md` đã phân tích xong
67 entity `type=event` và **không sửa một dòng dữ liệu nào** — cố ý, vì đợt sửa trước đã
ghi vào DB rồi phải hoàn nguyên. Nguyên nhân gốc: ngày của một lễ hội nằm ở **sáu ô khác
nhau** (`lunar_date`, `date_start`, `date_end`, `summary`, `description`, `season`) và cả
sáu cùng hiển thị trên một trang — sửa một ô làm năm ô kia thành lời nói ngược.

Ô `date_start`/`date_end` không chỉ là chữ: chúng chảy vào `schema.org/Event` (rich result
của Google) và vào **file `.ics` người dùng tải về lịch cá nhân**. **36 event đang công bố
ngày cứng** ra hai kênh đó.

Bảng CHỐT §6 có **17 dòng, tất cả còn trống**: C-1…C-14 (tự mâu thuẫn, 12 ca đang live),
D-1 (chính tả 3 lễ Khmer), D-4 (hai giải đua ghe ngo — nghi trùng lặp), và B (3 ca lệch
kỹ thuật, xin phép sửa tự động).

**MÌN đã gỡ ngòi, đừng đạp lại:** `attributes.month` (`agent/public_api.py:2429-2432` và
`:2827-2830`) đang chặn **21 event** khỏi "sắp diễn ra"/trang chủ vì `month` lệch tháng của
`date_start`. Đó là **hàng rào chống ngày bịa**, không phải bug. Ai chạy script cho khớp sẽ
mở cống cho 21 ngày bịa tràn ra JSON-LD + `.ics`.

**LỰA CHỌN.** Mỗi dòng trong 17 dòng là một câu hỏi riêng, đa số dạng "ngày nào đúng" hoặc
"một entity hay hai". Bốn nhóm đáp án khả dĩ, chọn theo từng ca:
1. **Chốt một ngày** (chủ dự án biết, hoặc gọi điện hỏi ban quản lý).
2. **Bỏ ngày cứng**, chuyển sang mô tả chu kỳ ("rằm tháng Giêng") — hợp với lễ dạng phong
   tục mà mỗi đình/phum sóc một ngày (Kỳ Yên chung, Đom Lơng Néak Tà).
3. **Gộp/tách entity** (C-12, C-13, D-4).
4. **Ẩn entity** cho tới khi kiểm chứng được.

**ĐÁNH ĐỔI.** (1) cho trải nghiệm tốt nhất nhưng cần nguồn thật — đoán = tái diễn đợt hỏng
trước. (2) trung thực và không bao giờ sai, nhưng entity mất khả năng lên lịch/sắp xếp/lọc
theo tháng. (3) sửa được mâu thuẫn tận gốc nhưng đổi URL. (4) an toàn tuyệt đối, đổi lại
trang lễ hội mỏng đi.

**AI CHỊU.** Người tải `.ics` về điện thoại rồi đi sai ngày — thiệt hại thật, không phải
thiệt hại hiển thị. Và Google, qua rich result sai.

**NẾU KHÔNG QUYẾT.** 36 event tiếp tục công bố ngày cứng mà 14 trong số đó dữ liệu tự mâu
thuẫn. Mọi task chạm `type=event` bị chặn — vì §7 của tài liệu đó ghi rõ: không sửa một ô
mà không sửa cả sáu.

---

## A5. Taxonomy 3 vùng mang tên tỉnh cũ làm mục điều hướng

**BỐI CẢNH.** CLAUDE.md §1.6 chốt: "tỉnh Bến Tre/Trà Vinh" chỉ được xuất hiện trong văn
cảnh lịch sử có chữ "cũ/trước 7-2025". Nhưng ba tên đó đang là **mục điều hướng ngang
hàng**, không có văn cảnh lịch sử nào:

- `web-nuxt/layouts/default.vue:208-212` — cột footer "Khu vực": Vĩnh Long / Bến Tre / Trà Vinh
- `agent/seed_site_settings.py:113-115` — cùng ba link, làm **giá trị mặc định trong DB**
  cho AdminCP (sửa file không đủ, phải sửa cả settings đã seed)
- `web-nuxt/composables/useConstants.ts:51-52` — `AREA_META` mô tả `ben-tre` = "Xứ dừa",
  `tra-vinh` = "Văn hóa Khmer"
- `web-nuxt/pages/khu-vuc/[area].vue` — cả một họ route, có canonical + BreadcrumbList JSON-LD
- lan ra `pages/dia-diem/[id].vue:330`, `pages/xa-phuong/[id].vue:25,38`,
  `pages/tuyen-duong.vue:122`, `pages/huong-dan.vue:872`

**Khoản này không phải "3 link nav" — nó là taxonomy vùng của cả site.** Và chính nhánh
đang làm việc (`codex/tri-region-color`) là một hệ màu xây trên ba vùng đó
(`docs/superpowers/specs/2026-07-31-tri-region-color-excellence-design.md:11`). Quyết định
này và nhánh đó ràng nhau.

Cần phân biệt hai câu hỏi: **(i)** chia site theo 3 vùng địa lý có còn đúng không, và
**(ii)** nếu còn thì gọi chúng bằng tên gì.

**LỰA CHỌN.**
1. **Giữ nguyên.** Coi đây là tên vùng địa lý dân gian, không phải tên đơn vị hành chính —
   và ghi ngoại lệ đó vào CLAUDE.md §1.6 để hết mâu thuẫn.
2. **Giữ 3 vùng, đổi nhãn** sang tên không phải tên tỉnh ("Xứ dừa", "Vùng Khmer", "Vùng
   sông Tiền"…), slug giữ nguyên để không vỡ URL.
3. **Giữ 3 vùng, thêm chú thích** "(trước 7-2025)" ở nhãn — đúng chữ §1.6.
4. **Bỏ hẳn trục vùng**, chuyển điều hướng sang chủ đề + xã/phường.

**ĐÁNH ĐỔI.** (1) rẻ nhất, nhưng biến §1.6 thành luật có ngoại lệ — và ngoại lệ đầu tiên
luôn dễ hơn ngoại lệ thứ hai. (2) giữ được cấu trúc + SEO slug nhưng mất tên có sức nhận
diện tìm kiếm ("Bến Tre" là từ khoá du lịch mạnh); nhãn mới phải tự giải thích được. (3)
đúng luật nhất, xấu nhất về mặt điều hướng — nhãn dài, khó đọc trên mobile. (4) sạch nhất
về định vị, đắt nhất: đụng route family, JSON-LD, prerender, sitemap, **và làm hệ màu
tri-region mất chỗ bám**.

**AI CHỊU.** SEO (3 hub page + hub-spoke tới 124 xã/phường); nhánh `codex/tri-region-color`;
mọi phiên sau đọc §1.6 rồi thấy code làm ngược.

**NẾU KHÔNG QUYẾT.** Luật và code nói ngược nhau ở chỗ dễ thấy nhất trên site. Nhánh
tri-region-color càng đi xa thì lựa chọn (4) càng đắt.

---

## A6. `web/data.json` mang 1746 `verifiedAt` chết

**BỐI CẢNH.** CLAUDE.md §1.7: nguồn kiểm-chứng-thực-địa DUY NHẤT là
`attributes.verifiedAt`, "hiện ~0 entity có". Đo hôm nay trên `web/data.json` (1746
entity): **`attributes.verifiedAt` = 0 ✓** — đúng như §1.7.

Nhưng **top-level `verifiedAt` = 1746/1746**, tất cả đều có giá trị
(`khu-di-tich-nguyen-dinh-chieu` → `2026-06-28T02:23:56Z`, kèm `verified: 1`). Đây là dấu
tự động đóng hàng loạt, không phải kiểm chứng thực địa.

**Phía code đã sạch:** `agent/database.py:2065` pop nó khỏi mọi entity trả ra;
`agent/public_api.py:1035` pop lần nữa; `scripts/export_data.py:45` loại nó khỏi export.
`canonical_verified_at()` (`database.py:2020-2038`) chỉ đọc từ `attributes`.

Nghĩa là: **file `web/data.json` đang lệch với code** — nó được sinh ra trước đợt vá và
chưa regenerate. Trường chết vẫn nằm trong artifact mà người ngoài đọc được.

Ràng với một khoản cũ: cơ chế tự động DB→data.json **chưa được tái lập** (CLAUDE.md §1.1;
`docs/ROADMAP.md:406`). Chỉ có admin `POST /export` tải tay. Nên "regenerate" không phải
một nút bấm — phải quyết chạy từ DB nào.

**LỰA CHỌN.**
1. **Regenerate từ prod PG** — file sạch, khớp code. Cần một cửa sổ chạm prod (đọc).
2. **Regenerate từ DB local** — rẻ, và **chạy được**: `scripts/export_data.py` đọc
   `agent/data/vinhlong360.db` (`agent/database.py:35`), file đó có 1746 entity chứ không
   rỗng. Cái giá nằm chỗ khác: **DB local đã phân kỳ với prod PG** — mọi chỉnh sửa qua
   AdminCP write-through chỉ có trên prod, nên file sinh ra sẽ sạch về schema nhưng cũ về
   nội dung. *(Ghi chú: bản đầu của mục này viết "DB local `agent/knowledge.db` rỗng
   (0 entity)" — sai hai chỗ, file đó không tồn tại trong worktree và không phải DB mà
   export đọc. CLAUDE.md §5b nói về một DB khác.)*
3. **Để nguyên**, ghi một dòng cảnh báo vào `docs/README.md` rằng trường đó đã chết.
4. **Regenerate + đồng thời tái lập tự động hoá** DB→data.json có kiểm tra diff.

**ĐÁNH ĐỔI.** (1) giải quyết triệu chứng, không giải quyết bệnh — lần sau lại lệch. (3)
gần như miễn phí nhưng để một trường trông-như-bằng-chứng nằm trong file công khai; ai
đọc file mà không đọc README sẽ tin nó. (4) chữa gốc nhưng là một task riêng có quy mô, và
đụng đúng chỗ §B7 cảnh báo (`--replace` từ data.json đè mất sửa AdminCP trên prod).

**AI CHỊU.** Bất kỳ ai lấy `data.json` làm bằng chứng "đã kiểm chứng" — kể cả chính chúng
ta khi viết pitch B2G. Đây là đúng loại sai §1.7 cấm.

**NẾU KHÔNG QUYẾT.** Mỗi lần có người đọc data.json là một lần rủi ro đưa claim khống vào
tài liệu đối ngoại. Và mọi lần regenerate về sau đều phải hỏi lại đúng câu hỏi này.

---

# NHÓM B — chặn mở công khai

> `docs/superpowers/plans/2026-08-05-nang-chat-luong-toan-dien.md:44-87` là checklist go-live
> đầy đủ (5 trụ). B1–B7 dưới đây là những dòng trong checklist đó **cần chủ dự án quyết**,
> không phải những dòng chỉ cần ngồi làm.

## B1. Ảnh 3,3% — dịch vụ ảnh AI đang tắt

**BỐI CẢNH.** Đo trên `web/data.json`: **57/1746 entity có ảnh = 3,3%**. Ngưỡng trụ ĐÚNG
là 30%. Đường ảnh duy nhất được phép là `scripts/gen_image.py` → `cx/gpt-5.5-image` qua
`IMAGE_API_BASE=http://localhost:20128` (`.env.example:199-203`); `IMAGE_API_KEY` đang
trống. Kế hoạch ước ~26 lô × 20 ảnh, và **bắt buộc xem toàn bộ ảnh mỗi lô** — prompt đã sửa
nhưng từng có một tô bún nhận prompt "kiến trúc di sản".

**LỰA CHỌN.** (a) Bật dịch vụ + đặt key, chạy theo lô, chủ dự án duyệt từng lô. (b) Bật
nhưng chỉ chạy ~150 entity trọng điểm rồi dừng đánh giá. (c) Hoãn — mở site với 3,3% ảnh.
(d) Hạ ngưỡng 30% xuống mức khác.

**ĐÁNH ĐỔI.** (a) đắt về thời gian duyệt của chủ dự án (26 lô × xem tay), đó mới là chi phí
thật, không phải tiền API. (b) rút ngắn còn ~8 lô, đủ để đo xem ảnh AI có thực sự nâng
chất trang hay không trước khi cam kết 26 lô. (c) mở site với trang trống ảnh — đúng thứ
làm người đọc bỏ đi và làm máy tìm kiếm đánh giá thấp, rất khó gỡ về sau. (d) trung thực
hơn là giả vờ ngưỡng đạt được, nhưng phải nói rõ hạ vì lý do gì.

**AI CHỊU.** Chủ dự án (thời gian duyệt); mọi trang chi tiết entity.

**NẾU KHÔNG QUYẾT.** Trụ ĐÚNG không bao giờ tick được ⇒ B7 (gỡ noindex) không mở được.
Đây là dòng checklist rẻ nhất để mở khoá mà đang bị chặn bởi một dịch vụ chưa bật.

---

## B2. 43,8% mô tả dưới 200 ký tự — lấy dữ kiện ở đâu

**BỐI CẢNH.** Đo hôm nay: **764/1746 = 43,8%** entity có `description` dưới 200 ký tự.
Ngưỡng trụ ĐÚNG là ≤15%.

Bài học đã trả giá, ghi ở kế hoạch §1: **ngưỡng số ép ra dối trá** — ngưỡng cứng 200 ký tự
từng khiến 148 bản "đạt chuẩn" bằng cách liệt kê thứ hồ sơ KHÔNG có. Và **gác cổng chuỗi
không thay được người kiểm chứng**: máy báo "0 bản bị chặn" ba lần liên tiếp trong khi
người kiểm chứng độc lập tìm 15 lỗi ở 36 bản, rồi 53 lỗi ở 93 bản — lỗi lọt không chứa từ
cấm nào.

Kết luận của kế hoạch (Đợt A2): với ~700 mô tả mỏng, **không viết tiếp bằng LLM**. Hồ sơ
chỉ có `schema_type` + `coords_approximate` thì mọi câu thêm vào đều là bịa. Việc đúng là
**bổ sung dữ kiện thật** (giờ mở cửa, giá, món, liên hệ) rồi mới viết.

Câu hỏi cho chủ dự án là: **dữ kiện thật đến từ đâu, và ai bỏ công.**

**LỰA CHỌN.** (a) Chủ dự án tự nhập qua form AdminCP, theo lô ưu tiên. (b) Gọi điện/đến
nơi cho ~150 entity trọng điểm, phần đuôi để mỏng vĩnh viễn. (c) Mở kênh cho cơ sở tự khai
(đã có link "Đăng ký quản lý trang" ở footer) rồi duyệt. (d) Chấp nhận mỏng, bỏ ngưỡng
15%, chỉ index những trang đủ dày (cổng `is_index_worthy` đã chạy: ≥130 từ).

**ĐÁNH ĐỔI.** (a) chậm nhất nhưng chất lượng cao nhất và không phụ thuộc ai. (b) đúng
trọng tâm — 150 entity dày còn hơn 1746 entity mỏng — nhưng phần đuôi mỏng vẫn nằm trên
site. (c) rẻ nhất về công sức nhưng cần người kiểm duyệt và cần có người dùng trước, mà
site đang noindex nên chưa có ai. (d) trung thực nhất về mặt SEO, đổi lại site công bố
1746 entity mà chỉ ~400 trang đủ chất lượng để index.

**AI CHỊU.** Người tìm thông tin rồi không thấy gì hữu ích; chỉ số chất lượng của cả
domain trong mắt máy tìm kiếm.

**NẾU KHÔNG QUYẾT.** Rủi ro thật không phải "không làm" mà là **có người sẽ làm bằng LLM**
— đã xảy ra hai lần và cả hai lần phải sửa hậu quả.

---

## B3. Cộng đồng nằm trên nav nhưng đang "sắp mở"

**BỐI CẢNH.** `/cong-dong` xuất hiện ở **ba chỗ điều hướng**
(`web-nuxt/layouts/default.vue:170`, `:180`, `:205` — nav group, primary nav mobile,
footer), nhưng trang render khối "🚧 Cộng đồng sắp mở"
(`web-nuxt/pages/cong-dong.vue:331`). Kế hoạch Đợt C3 ghi: theo luật Việt Nam, kiểm duyệt
UGC trước khi mở cộng đồng là **bắt buộc, không phải tuỳ chọn** — hoặc làm đủ để mở, hoặc
gỡ khỏi nav.

Hạ tầng phía sau đã có kha khá: `moderation_status` cho bình luận vừa ship
(`94942186`), người dùng sửa/xoá bình luận của mình đã chạy (`00a08510`), ẩn/bỏ ẩn bài viết
đã có (`c5379506`). Thứ chưa có là **quy trình người** và trạng thái pháp lý (→ B6).

**LỰA CHỌN.** (a) Gỡ `/cong-dong` khỏi cả ba chỗ nav cho tới khi mở thật. (b) Giữ nav,
giữ nhãn "sắp mở" — coi là tín hiệu lộ trình. (c) Mở thật: chốt quy trình kiểm duyệt + ai
trực + SLA gỡ nội dung ≤24 giờ, rồi bỏ nhãn.

**ĐÁNH ĐỔI.** (a) trung thực, nav gọn hơn, nhưng mất tín hiệu "site này sẽ có cộng đồng" —
thứ đang dùng để mời cơ sở tham gia. (b) rẻ nhất nhưng ba mục nav dẫn tới một trang không
làm được gì là lỗi UX cơ bản, và nếu mở site công khai thì đó là ba link chết trước mắt
người dùng đầu tiên. (c) đúng đích nhưng ràng vào B6 (chưa biết có thuộc NĐ147 không) và
ràng vào việc **một người có trực nổi kiểm duyệt hay không**.

**AI CHỊU.** Người dùng đầu tiên; và rủi ro pháp lý nếu mở mà không có cơ chế gỡ nội dung.

**NẾU KHÔNG QUYẾT.** Ba link chết ở lại. Nếu B7 mở trước B3 thì chúng lộ ra công khai.

---

## B4. `TOTP_ENC_KEY` chưa đặt trên prod

**BỐI CẢNH.** `.env.example:195-197` đã ghi cảnh báo: *"Bật 2FA khi CHƯA đặt khoá này =
khoá vĩnh viễn người dùng đã bật 2FA."* Rà OWASP
(`docs/security/owasp-review-2026-08-05.md:528-534`) xếp đây là mức **Cao**: `TOTP_ENC_KEY`
chưa nằm trong `validate_production_keys` (`agent/config.py:151`), và
`agent/twofactor.py:44-50` còn nhánh fallback dẫn xuất khoá từ `ADMIN_API_KEY`.

Bẫy thứ tự (ghi cả ở CLAUDE.md §4): đặt khoá **trước**, và **không được xoay
`ADMIN_API_KEY` giữa chừng** — xoay là mọi bí mật TOTP hiện có thành rác.

Đặt giá trị secret thật = §4 điều kiện dừng. Không AI nào được làm thay.

**LỰA CHỌN.** (a) Chủ dự án sinh + đặt khoá trên prod ngay, rồi cho phép bắt buộc nó ở
`validate_production_keys`. (b) Bắt buộc trong code trước — server prod sẽ **không khởi
động được** cho tới khi khoá được đặt (fail-closed). (c) Tắt hẳn 2FA cho tới khi quyết.

**ĐÁNH ĐỔI.** (a) đúng thứ tự, an toàn nhất, nhưng phải có chủ dự án ngồi vào máy. (b)
biến việc quên thành sự cố nhìn thấy ngay thay vì hỏng ngầm — nhưng nếu deploy mà chưa đặt
thì site chết. (c) mất một lớp bảo vệ tài khoản admin; và nếu đã có user bật 2FA thì tắt
cũng là một thay đổi phải xử lý.

**AI CHỊU.** Mọi tài khoản đã bật 2FA — hậu quả là **khoá vĩnh viễn**, không có đường lùi.

**NẾU KHÔNG QUYẾT.** 2FA đang ở trạng thái nguy hiểm nhất: **code có, khoá không có**. Chỉ
cần một người bật 2FA trên prod là mất tài khoản đó.

---

## B5. Prod chạy systemd-trên-host hay docker-compose?

**BỐI CẢNH.** `TRUSTED_PROXIES` **không có trong `.env.example`** (kiểm hôm nay: 0 dòng).
Rà OWASP (`:544-548`) ghi rõ: giá trị đúng phụ thuộc hoàn toàn vào cách deploy, và **đoán
sai thì hoặc mất rate-limit hoặc mở đường giả mạo `X-Forwarded-For`** — tức kẻ tấn công tự
đặt IP giả để vượt rate-limit.

`docs/security/owasp-review-2026-08-05.md` §4 liệt đây vào nhóm "chưa kiểm được": chỉ chủ
dự án biết prod đang chạy gì. Cùng nhóm còn: cấu hình nginx thật trên VPS có thể đã lệch
với `nginx.conf`/`nginx-ssl.conf` trong repo, và uvicorn ở prod có khởi động với
`--log-config` riêng hay không.

**LỰA CHỌN.** Đây không phải chọn phương án — là **cung cấp một sự thật**: (a) systemd
trên host (nginx → uvicorn qua localhost); (b) docker-compose (nginx container → agent
container, IP nội bộ khác); (c) khác.

**ĐÁNH ĐỔI.** Không có đánh đổi — chỉ có đúng hoặc sai. Đánh đổi nằm ở việc **đoán**: đặt
`TRUSTED_PROXIES` sai kiểu (b) khi thực tế là (a) thì rate-limit theo IP mất tác dụng
im lặng.

**AI CHỊU.** Rate-limit của mọi endpoint ghi (đăng nhập, đăng bài, bình luận, upload).

**NẾU KHÔNG QUYẾT.** Ba kết luận trong rà OWASP treo lơ lửng, và không ai dám đặt biến đó.

---

## B6. NĐ147 — site có UGC thì có thuộc diện không?

**BỐI CẢNH.** Checklist trụ HỢP PHÁP ghi thẳng: *"Xác định rõ: có UGC ⇒ có thuộc diện
NĐ147 không? **Cần luật sư — điều kiện dừng theo CLAUDE.md §4**"*. Ba dòng còn lại của trụ
này (chính sách riêng tư đúng NĐ13, cơ chế gỡ nội dung ≤24 giờ có nhật ký, điều khoản sử
dụng có mốc thời gian) đều phụ thuộc câu trả lời.

Đây là khoản **duy nhất trong sổ mà không AI nào và không tài liệu nội bộ nào trả lời
được** — nó cần người có tư cách pháp lý.

**LỰA CHỌN.** (a) Thuê tư vấn pháp lý một lần, lấy kết luận bằng văn bản. (b) Mở site ở
chế độ **không có UGC** (B3 chọn "gỡ khỏi nav") — tránh hẳn ngưỡng NĐ147. (c) Hoãn mở site
tới khi có kết luận.

**ĐÁNH ĐỔI.** (a) tốn tiền (ngoài §B8, nhưng đây là chi phí pháp lý chứ không phải dịch vụ
kỹ thuật — vẫn cần chủ dự án duyệt). (b) mở được sớm và an toàn, đổi lại bỏ đúng thứ
`research-vinhlong360-demand` gọi là ngách mạnh; có thể mở UGC sau khi đã có lưu lượng. (c)
an toàn tuyệt đối, và cũng là "không bao giờ mở" nếu không ai chủ động đi hỏi.

**AI CHỊU.** Chủ dự án — trách nhiệm pháp lý là của người, không của sản phẩm.

**NẾU KHÔNG QUYẾT.** Trụ HỢP PHÁP không tick được. B7 không mở được. Và nếu mở đại thì rủi
ro rơi hết vào chủ dự án.

---

## B7. Gỡ `NUXT_PUBLIC_SITE_NOINDEX` khi nào

**BỐI CẢNH.** `web-nuxt/nuxt.config.ts:6`: `const siteNoindex = process.env.NUXT_PUBLIC_SITE_NOINDEX !== 'false'`
— tức **mặc định BẬT**, phải chủ động đặt `'false'` mới tắt. Noindex toàn site đang là hàng
rào tạm mạnh hơn cổng per-page.

Một khoản kỹ thuật đi kèm: robots `noindex,follow` **per-page** cho entity mỏng (P0-1 trong
`docs/toi-uu-chong-ai-va-google-spam-playbook.md:65`) **CHƯA ship**. Playbook ghi rõ:
*phải làm per-page robots TRƯỚC khi mở `NUXT_PUBLIC_SITE_NOINDEX=false`*. Hiện noindex toàn
site đang che tạm việc đó.

Cổng `is_index_worthy` (`agent/seo.py`) đã chạy thật từ 2026-07-06 và đo được **405 trang
index / ~1.200 noindex** — nhưng nó chỉ gate **sitemap**, không gate thẻ robots.

**LỰA CHỌN.** (a) Chỉ mở khi tick hết checklist 5 trụ. (b) Mở sớm cho một tập nhỏ trang đã
đủ chất (~405 trang), giữ noindex phần còn lại — cần ship P0-1 per-page robots trước. (c)
Mở hết ngay.

**ĐÁNH ĐỔI.** (a) kỷ luật nhất, nhưng có thể mất nhiều tháng và trong thời gian đó site
không có ai vào — không có phản hồi thật để biết cái gì đáng làm. (b) cân bằng: bắt đầu
tích luỹ tín hiệu tìm kiếm trên phần tốt nhất, nhưng phải làm P0-1 trước, và đó là một
task code có thật. (c) *"Mở sớm với nội dung mỏng là tự chuốc đánh giá thấp từ máy tìm
kiếm, và rất khó gỡ"* — nguyên văn kế hoạch F3.

**AI CHỊU.** Uy tín domain trước máy tìm kiếm — thứ đắt nhất để phục hồi.

**NẾU KHÔNG QUYẾT.** Site vô hình. Mọi công việc SEO, nội dung, hiệu năng đều chưa được
kiểm chứng bằng người dùng thật.

---

# NHÓM C — nợ sống chung được

## C1. `comments.updated_at` — thêm cột hay bỏ nhãn "đã sửa"

**BỐI CẢNH.** Bảng `comments` (`init.sql:224-232`) **không có cột `updated_at`**; ba
migration từng chạm bảng này (008/034/068) đều là `ADD COLUMN` cho thứ khác. Câu `UPDATE`
cũ tham chiếu `updated_at` nên `PUT /api/comments/{id}` **500 ngay khi được gọi thật** —
bug nằm im vì frontend chưa từng gọi. Đã bỏ mệnh đề đó (`00a08510`), endpoint hết 500;
`agent/social.py:2494-2498` ghi lại nguyên nhân tại chỗ.

Hậu quả còn lại: bình luận đã sửa **không hiện được nhãn "đã sửa"**. Bài viết thì có —
`agent/social.py:4437` tính `is_edited` từ `updated_at` của bảng `posts`.

**LỰA CHỌN.** (a) Migration 076 thêm `updated_at TIMESTAMPTZ` vào `comments`, set trong
UPDATE, render nhãn (kèm test theo §B4). (b) Bỏ hẳn ý định hiện nhãn — chấp nhận bình luận
sửa im lặng. (c) Suy nhãn từ nguồn khác (audit log) mà không thêm cột.

**ĐÁNH ĐỔI.** (a) đúng nhất, nhưng là một migration nữa xếp chồng lên chuỗi chưa chạy
(A2). (b) miễn phí; đổi lại người đọc không biết bình luận đã bị sửa sau khi mình trả lời —
vấn đề niềm tin nhỏ nhưng thật. (c) phức tạp hơn (a) mà không sạch hơn.

**AI CHỊU.** Người đọc bình luận trong luồng thảo luận.

**NẾU KHÔNG QUYẾT.** Không hỏng gì thêm — nhưng mỗi migration mới lại là một cơ hội gộp bị
bỏ lỡ.

---

## C2. `WEATHER_API_KEY` chưa đặt

**BỐI CẢNH.** `.env.example:73` — `WEATHER_API_KEY=` trống. `agent/realtime.py:87`: thiếu
key ⇒ trả dữ liệu ước theo mùa, có đủ `temp_c`/`humidity`/`description` y hệt nhánh đo
thật, chỉ khác một key `fallback`.

**Nguy cơ nói dối đã bịt xong** ở cả hai đường (xem §4): frontend null-hoá toàn bộ số ở
trạng thái `estimated` (`922fd5bd`), và đường chat lược sạch số qua `weather_for_llm()`
(`c002e184`, `agent/server.py:871-895`). Nên khoản còn mở **không phải là an toàn** mà là:
**có bỏ tiền/đăng ký OpenWeatherMap để khối thời tiết nói được gì không.**

**LỰA CHỌN.** (a) Đặt key (OpenWeatherMap có free tier — 1000 call/ngày, hợp §B8). (b)
Không đặt, giữ khối ở trạng thái câm. (c) Gỡ hẳn khối thời tiết khỏi trang chủ.

**ĐÁNH ĐỔI.** (a) khối thời tiết bắt đầu có giá trị — và thời tiết là thứ người ta xem
**hàng ngày**, khác nội dung du lịch xem mỗi năm một lần; đổi lại thêm một khoá phải quản
lý và một phụ thuộc bên ngoài. (b) khối chiếm chỗ trên trang chủ mà chỉ nói "chưa nói được
dịch vụ đo". (c) trang chủ gọn hơn, mất một lý do quay lại hàng ngày.

**AI CHỊU.** Người dùng trang chủ.

**NẾU KHÔNG QUYẾT.** Một khối trên trang chủ vĩnh viễn không nói gì.

---

## C3. Lịch vạn niên 1968–1975 có hai đáp án

**BỐI CẢNH.** Từ 1968 miền Bắc chuyển sang UTC+7, **miền Nam giữ UTC+8 tới 1975**. Đo trên
oracle: **120/2922 ngày trong quãng đó ra kết quả khác nhau**, kể cả mùng 1 Tết Mậu Thân
(29/01 theo UTC+7 vs 30/01 theo UTC+8).

Lõi trang chạy UTC+7 = lịch nhà nước (`web-nuxt/composables/useLunar.ts:182-189`,
`agent/lunar_calendar.py:467-468`). **Mà Vĩnh Long thuộc miền Nam.** Trang hiện hiển thị
kết quả UTC+7 kèm chú thích nói rõ có hai đáp án
(`web-nuxt/pages/lich-van-nien.vue:66-89`, khối cảnh báo tại `:84`).

Lý do cố ý không tự đổi sang UTC+8 (ghi trong `71a8f19c`): ngày giỗ chép lại sau 1975
thường **đã** quy theo lịch nhà nước; đổi ngầm sẽ sai theo chiều ngược lại.

**LỰA CHỌN.** (a) Giữ nguyên — một đáp án + chú thích. (b) Hiện **cả hai** cột cho quãng
1968–1975. (c) Chặn hẳn quãng đó, không cho tra. (d) Thêm công tắc cho người dùng chọn múi
giờ.

**ĐÁNH ĐỔI.** (a) đơn giản, đã trung thực; đổi lại người Vĩnh Long tra ngày giỗ ông bà có
thể nhận ngày lệch 1 mà không để ý chú thích. (b) trung thực nhất, nhưng làm người dùng
phải tự quyết — với đa số là câu hỏi họ không có dữ kiện để trả lời. (c) an toàn tuyệt
đối, mất tính năng cho đúng nhóm có nhu cầu tra ngày giỗ. (d) mạnh nhất, đắt nhất, và vẫn
đẩy quyết định về phía người dùng.

**AI CHỊU.** Người tra ngày giỗ trong quãng 1968–1975 — nhóm nhỏ nhưng chính xác là nhóm
cần lịch vạn niên nhất.

**NẾU KHÔNG QUYẾT.** Trạng thái hiện tại đã trung thực. Đây là khoản có thể để lâu nhất
trong sổ.

---

## C4. Khi nào fork `dongthap360` — và có VPS thứ hai không

**BỐI CẢNH.** Kiến trúc **đã chốt** trong brainstorm 2026-07-13
(`docs/superpowers/specs/2026-07-13-dongthap360-fork-design.md` §1): **hard-fork, KHÔNG
multi-tenant**; mỗi tỉnh một thư mục, một DB, một domain, không chia sẻ gì sau khi tách;
định hướng 3–5 tỉnh. Nên câu "1 repo hay N repo" **đã có đáp án: N**.

Ba thứ còn mở:
1. **Bao giờ chạy SP1** (5 đợt, keystone là tách `province.config` — bản đồ vùng hiện bị
   định nghĩa lại ≥15 lần ở backend + ~8 lần ở frontend, 3 bounding-box lệch nhau cho cùng
   một vùng).
2. **VPS.** Spec §101 khuyến nghị **VPS RIÊNG mỗi tỉnh**: *"VPS 1GB không chứa 2 stack"*.
   Đây là chi tiêu mới ⇒ §B8 ⇒ chủ dự án. *(Con số ~224 MB/tenant nhắc trong phiên làm
   việc **không có tài liệu nào trong repo chứng minh** — nếu nó có thật thì nó mâu thuẫn
   với khuyến nghị §101 và cần đo lại trước khi dùng làm căn cứ.)*
3. Ràng với **A5**: nếu A5 chọn bỏ/đổi trục vùng thì `province.config.regions[]` đổi hình
   dạng theo.

**LỰA CHỌN.** (a) Chạy SP1 ngay — tách config có giá trị cho chính vinhlong360 (gộp 3
bbox lệch, 1 SoT thay vì 23 bản sao) kể cả khi chưa fork. (b) Chỉ chạy đợt 1–4 (tách
config, giữ `config = Vĩnh Long`), dừng trước khi lật sang Đồng Tháp. (c) Hoãn toàn bộ tới
khi vinhlong360 mở công khai và chứng minh được mô hình.

**ĐÁNH ĐỔI.** (a)/(b) trả nợ kiến trúc thật (3 bbox lệch là bug đang nằm im), và spec đã
thiết kế sẵn cách verify behavior-preserving: giữ `config = VL` xuyên suốt, diff HTML phải
y hệt. (b) rẻ hơn (a), lấy toàn bộ phần lợi mà chưa cam kết tỉnh thứ hai. (c) không tốn gì
hôm nay; đổi lại mỗi tuần trôi qua là thêm bản sao thứ 24, 25 của bản đồ vùng.

**AI CHỊU.** Chủ dự án (ngân sách VPS); mọi phiên sau chạm logic vùng.

**NẾU KHÔNG QUYẾT.** Nợ kiến trúc lớn dần một cách im lặng. Không có sự cố nào — chỉ có
chi phí sửa tăng đều.

---

## C5. 6 `booking_note` báo giá tour — ranh giới §1.4

**BỐI CẢNH.** CLAUDE.md §1.4: **chỉ giới thiệu, không đặt hàng/booking/thanh toán**, giữ ở
"tầng nhẹ" pháp lý để không kích đăng ký TMĐT (NĐ52/85).

Quét `web/data.json` hôm nay: **117 entity có `attributes.booking_note`**, trong đó **6 ca
mang tín hiệu giá/tour**:

| id | trích |
|---|---|
| `con-phung-con-ong-dao-dua` | "Nên đặt trước tour trọn gói; … tour 4 cồn … từ 95.000đ/khách" |
| `nha-co-huynh-thuy-le` | "ở lại qua đêm (550.000–1.000.000đ/đêm…); gói ăn kèm vé 100.000đ/người" |
| `san-chim-vam-ho` | "Nên đặt trước qua Nông trại Hải Vân (…); gói trọn gói từ 350.000đ/người" |
| `vung-cam-sanh-tra-on` | "Nên đặt tour qua các công ty du lịch địa phương (Vĩnh Long Tourist)" |
| `cu-lao-dai-vung-liem` | "Nên đặt tour qua Vĩnh Long Tourist hoặc liên hệ trước homestay…" |
| `chua-phuoc-hau-ngai-tu` | "thuê thuyền khoảng 300.000đ/chuyến" |

Câu hỏi thật: **mô tả giá của bên thứ ba có phải "bán" không?** Site không nhận tiền, không
có giỏ hàng, không có form chốt đơn. Nhưng `docs/drafts/lo-10-entity-mau.md:571` §F.5 đánh
dấu `con-phung` là *"lỗi dữ liệu có rủi ro pháp lý nhẹ"* và đề nghị rà toàn dataset.

**LỰA CHỌN.** (a) Giữ nguyên — coi giá tham khảo là thông tin, không phải chào bán; ghi
ngoại lệ vào §1.4 cho rõ. (b) Bỏ con số, giữ hướng dẫn ("liên hệ hỏi giá"). (c) Bỏ cả cụm
"đặt tour", chỉ giữ thông tin đi lại. (d) Giữ số nhưng gắn nhãn nguồn + ngày ("giá tham
khảo tháng 6/2026, theo …").

**ĐÁNH ĐỔI.** (a) hữu ích nhất cho người đọc, rủi ro pháp lý nhỏ nhưng khó ước lượng khi
chưa có kết luận NĐ147 (B6). (b) an toàn, mất đúng thứ người ta muốn biết trước khi đi.
(c) an toàn nhất, nội dung nghèo đi rõ rệt. (d) trung thực nhất — nhưng giá **cũ mà không
có ngày** còn tệ hơn không có giá, và duy trì 6 nhãn ngày là việc lặp lại mãi.

**AI CHỊU.** Người lập kế hoạch đi chơi (cần biết giá); chủ dự án (rủi ro pháp lý).

**NẾU KHÔNG QUYẾT.** 6 ca ở lại. Quan trọng hơn: **không có quy tắc để áp cho ca thứ 7** —
mỗi lần thêm entity lại phải hỏi lại.

---

## C6. 2 đơn vị đổi tên + 2 quy ước đặt dấu

**BỐI CẢNH.** `docs/drafts/doi-chieu-ma-hanh-chinh.md:260-283`. Ca A (16 xã lên phường) đã
chốt 2026-08-07. Còn treo:

**Ca B — 2 đơn vị mà tên dự án khác tên chính thức:**

| id | tên đang dùng | tên chính thức | mã PX |
|---|---|---|---:|
| `p-vung-liem` | Phường Vũng Liêm | Xã Trung Thành | 29659 |
| `xa-hau-loc` | Xã Hậu Lộc | Xã Cái Ngang | 29728 |

**Ca C — 2 đơn vị khác quy ước dấu:** `p-hung-hoa` (Hùng **Hoà** vs Hùng **Hòa**),
`p-tan-hoa` (Tân **Hoà** vs Tân **Hòa**). Kiểu cũ `oà` vs kiểu mới `òa`. **Không ảnh hưởng
slug** (bỏ dấu thì như nhau), chỉ ảnh hưởng chữ hiển thị.

Cả hai ca **không đụng tới mã**, nên **A3 chạy được mà không cần C6**.

**LỰA CHỌN.** *Ca B:* (B1) theo tên chính thức, giữ tên cũ trong `attributes.aliases` để
search vẫn ra; (B2) giữ tên đang dùng, gắn mã chính thức + ghi chú trong trang; (B3) tiêu
đề dùng tên chính thức, phụ đề "trước đây là …" *(gợi ý trung dung của tài liệu, không tự
áp)*. *Ca C:* (C-i) chuẩn hoá toàn site theo văn bản (`òa`, `òe`, `ùy`); (C-ii) giữ `Hoà`,
coi là biến thể chấp nhận được.

**ĐÁNH ĐỔI.** (B1) đúng văn bản, nhưng **"Vũng Liêm" là tên có sức nhận diện du lịch
mạnh** — mất tên là mất lưu lượng tìm kiếm. (B2) giữ SEO, nhưng site đang **nói sai tên
hành chính hiện hành** — trái tinh thần §1.7 nếu không nêu rõ. (B3) được cả hai, đổi lại
tiêu đề dài hơn và phải sửa ở nhiều template. (C-i) nhất quán với văn bản nhưng phải rà cả
những chỗ khác trong nội dung, không chỉ 2 tên này. (C-ii) miễn phí, để lại một lệch nhỏ
với danh mục nhà nước.

**AI CHỊU.** SEO của 2 slug; người tra cứu hành chính.

**NẾU KHÔNG QUYẾT.** Chỉ 4 đơn vị lệch, không lan. Nhưng A3 sẽ đẩy mã vào DB trong khi tên
vẫn treo — trạng thái nửa vời.

---

## C7. 6 bản nháp nội dung + 4 quy ước biên tập

**BỐI CẢNH.** `docs/drafts/` có 6 tài liệu, tất cả `STATUS: chờ chủ dự án duyệt`, **không
tài liệu nào đã ghi vào DB hay `web/data.json`**: 4 bản tóm tắt entity
(`homestay-ut-trinh`, `khu-di-tich-nguyen-dinh-chieu`, `nha-co-cai-cuong`, `xa-cho-lach`),
`lo-10-entity-mau.md` (lô mẫu 10 entity), và `doi-chieu-ma-hanh-chinh.md` (→ C6).

Lô mẫu đo được: hệ số nở nội dung **×3,5** (TB 114 → 400 ký tự), **70 cảnh báo** (TB
7,0/entity), **10/10 entity có đề xuất sửa `attributes`**, **7/10 có lỗi định vị**, **5/10
có bản ghi trùng lặp**.

Ngoài "duyệt hay không", `lo-10-entity-mau.md:571` §F nêu **4 quy ước phải chốt trước khi
mở rộng lên 150 entity** — vì chốt sau nghĩa là sửa 150 bản:
1. **Trần 400 ký tự:** 2/10 bản vượt (411 và 401). Cắt cho đúng gate, hay nới gate cho
   entity hub?
2. **"Trà Vinh" đứng một mình:** dùng như tên địa phương (nay là phường) — đúng §1.6 về
   kỹ thuật, nhưng người đọc có thể hiểu thành tỉnh cũ. Viết "phường Trà Vinh", "nội ô Trà
   Vinh", hay thêm chú thích?
3. **Phạm Văn Bổn hay Bốn:** hai bản trong cùng lô dẫn **cùng nguồn TTXVN** mà ghi khác
   nhau. Phải thống nhất trước khi ghi dữ liệu.
4. **Ảnh:** cả 10 entity chưa có ảnh thật ⇒ ràng vào B1.

Bài học đã trả giá (kế hoạch §1.1 + A3): **mọi nội dung ra mặt người dùng phải qua một
lượt kiểm chứng độc lập**, không chỉ qua máy — gác cổng chuỗi báo "0 bản bị chặn" ba lần
liên tiếp trong khi người kiểm tìm ra 53 lỗi ở 93 bản.

**LỰA CHỌN.** (a) Duyệt lô 10, chốt 4 quy ước, rồi mở lô tiếp. (b) Duyệt lô 10 nhưng chỉ
ghi phần `attributes` (dữ kiện), hoãn phần văn xuôi. (c) Bác lô, đổi cách viết. (d) Duyệt
nhưng dừng sau mỗi 3 lô để soát lại giọng *(chính tài liệu đề xuất, `:646`)*.

**ĐÁNH ĐỔI.** (a) nhanh nhất, rủi ro là chốt quy ước dựa trên 10 mẫu. (b) tách rủi ro: dữ
kiện kiểm chứng được, văn xuôi thì không — nhưng chỉ có `attributes` thì trang không dày
lên. (c) đắt, chỉ nên chọn nếu giọng lệch hướng thật. (d) chậm nhất, tránh được kịch bản
tệ nhất là trôi 150 bản rồi mới phát hiện lệch.

**AI CHỊU.** Chủ dự án (thời gian đọc duyệt); 150 entity sắp viết.

**NẾU KHÔNG QUYẾT.** Toàn bộ Đợt A nội dung đứng — mà đó là đợt kế hoạch xếp **ưu tiên số
1** vì dịch chuyển điểm mạnh nhất.

---

## C8. 34 hàm bảo mật chưa nối dây + 3 biến `LOCKOUT_*` quảng cáo suông

**BỐI CẢNH.** Rà OWASP (`:548-552`): `agent/auth_middleware.py` có 34 hàm bảo mật **không
được nối vào đường thật**. Kiểm lại nhóm khoá tài khoản hôm nay:
`LOCKOUT_THRESHOLD/DURATION/WINDOW` đọc env tại `agent/auth_middleware.py:1012`,
`is_account_locked()` định nghĩa tại `:1064` — **và không hàm nào ngoài module gọi nó**
(grep toàn `agent/` trừ test: 0 call-site).

`.env.example:146-148` đang liệt kê cả ba biến. Tức file cấu hình **quảng cáo một tính
năng không chạy**.

Đây là đúng loại nợ mà kế hoạch §1.3 gọi tên: *"test đông không bằng test đúng tầng"* —
mỗi hàm trong 34 hàm này có thể đang có test riêng và xanh, trong khi không hàm nào chạy
trên đường thật.

**LỰA CHỌN.** (a) Nối dây nhóm khoá tài khoản vào `agent/auth.py`, viết test hành vi qua
HTTP, giữ 3 biến. (b) Xoá 3 biến khỏi `.env.example`, để hàm nằm đó dưới dạng thư viện
chưa dùng. (c) Xoá cả hàm lẫn test lẫn biến. (d) Rà đủ 34 hàm, mỗi hàm chọn nối-hay-xoá.

**ĐÁNH ĐỔI.** (a) thêm một lớp bảo vệ thật cho đăng nhập, nhưng khoá tài khoản là con dao
hai lưỡi — kẻ xấu có thể khoá tài khoản người khác bằng cách nhập sai liên tục. (b) mất 5
phút và bỏ đúng phần nguy hiểm nhất là **lời quảng cáo sai**. (c) sạch nhất, mất công đã
bỏ ra. (d) đúng nhất và tốn nhất; nên là một task riêng có phạm vi rõ.

**AI CHỊU.** Ai đọc `.env.example` rồi tưởng đã có chống brute-force.

**NẾU KHÔNG QUYẾT.** Ba dòng cấu hình tiếp tục nói dối. Đây là khoản rẻ nhất trong nhóm C
để đóng — lựa chọn (b) là 3 dòng xoá.

---

## C9. Hai khoản closed-installer chỉ lộ trên Linux

**BỐI CẢNH.** `docs/ROADMAP.md:448-449`, cả hai đều tự đánh dấu "cần chủ dự án quyết".

**(i) Ghim python theo descriptor không chống được ghi-đè-tại-chỗ.**
`PYTHON_EXECUTOR="/proc/$BASHPID/fd/$FD"` ghim *inode*, nên `> "$path"` (truncate cùng
inode) làm mọi `invoke_python` sau đó chạy nội dung của kẻ tấn công — **đo được**: hook ghi
`exit 97` vào executor đã admit thì installer báo
`authority-result-record-failed:python-dependencies:97`. Vá thật rất đắt: cách bảo vệ hook
(copy-vào-memfd-có-seal + đối chiếu digest mỗi lần gọi) **không áp được cho python** —
verify digest cần chạy python (vòng lặp gà-trứng), còn exec từ memfd thì mất nhận diện venv
qua `sys.prefix`, đúng thứ một test khác đang khoá.

**(ii) `test_live_retry_recovers_interruption_immediately_after_bind_mount` chưa từng được
chứng minh trên CI.** Nhánh live ghi thẳng `/etc/systemd/system` và cấm override đường dẫn,
nên runner user-thường chết trước khi chạm bind mount. Nay đã gắn cổng
`_systemd_units_writable()` → **SKIP thay vì đỏ giả**. Phủ thật cần chạy bằng root.

**LỰA CHỌN.** *(i)* (a) chấp nhận rủi ro, ghi vào `90-exceptions-log.md`; (b) đầu tư vá
(lớn, và có thể không có lời giải sạch); (c) đổi mô hình đe doạ — nếu kẻ tấn công đã ghi
được vào executor thì hắn đã ở trong máy, đặt câu hỏi cổng này còn ý nghĩa gì.
*(ii)* (a) giữ SKIP; (b) thêm job CI `sudo -E`; (c) chạy tay trên VPS mỗi lần release.

**ĐÁNH ĐỔI.** *(i)* (a) rẻ và trung thực nếu (c) đúng; (b) tốn nhiều công cho một lỗ chỉ
khai thác được khi đã có quyền ghi. *(ii)* (b) phủ thật nhưng **ghi vào
`/etc/systemd/system` của runner** — thay đổi tính chất CI, đó mới là lý do cần chủ dự án;
(c) không đụng CI, đổi lại phụ thuộc kỷ luật con người.

**AI CHỊU.** Quy trình release đóng gói; không chạm người dùng cuối.

**NẾU KHÔNG QUYẾT.** Một test SKIP im lặng mãi (SKIP không ai nhìn = không có test), và
một lỗ đã biết nằm trong ROADMAP mà không có ai chịu trách nhiệm.

---

## C10. Bốn câu hỏi mô hình dữ liệu entity

**BỐI CẢNH.** `docs/entity-content-model.md:81-87` giữ 4 câu hỏi mở từ đợt entity
content-model, chưa ai trả lời:

1. **`restaurant`/`cafe` (244 entity)** nên là danh mục "Ẩm thực" riêng hay gộp "sản phẩm"?
   (hiện map `kind=food`)
2. **`place` hành chính (xã/phường)** có nên tách hẳn khỏi mô hình du lịch không?
3. **`festival`** giữ là sub-type của `event` (qua `lunar_date`) hay tách type riêng?
4. **Long-tail key đặc thù** (`sac_phong`, `deity_worshipped`…) — giữ JSONB linh hoạt (đang
   vậy) hay chuẩn hoá dần?

Câu 3 **ràng trực tiếp với A4**: nếu `festival` tách type riêng thì bài toán sáu-ô của dữ
liệu sự kiện đổi hình dạng. Nên **quyết A4 trước, hoặc quyết cùng lúc.**

**LỰA CHỌN.** (a) Trả lời cả 4 trong một lượt, mở một plan migration. (b) Chỉ trả lời câu
3 (vì nó chặn A4), hoãn 3 câu còn lại. (c) Chốt "giữ nguyên tất cả" và đóng mục — biến câu
hỏi mở thành quyết định có chủ đích.

**ĐÁNH ĐỔI.** (a) dọn sạch một lượt, đắt vì mỗi câu là một migration + rework AdminCP. (b)
rẻ và đúng thứ tự phụ thuộc. (c) miễn phí và **trung thực hơn để mở vô thời hạn** — mục
"câu hỏi mở" tồn tại càng lâu thì càng có người tưởng nó là việc đang làm.

**AI CHỊU.** 244 entity ăn uống (hiện phân loại theo `kind=food`, có thể không phải chỗ
người dùng đi tìm); mô hình dữ liệu về lâu dài.

**NẾU KHÔNG QUYẾT.** Không hỏng gì. Nhưng câu 3 treo thì A4 thiếu một mảnh.

---

# §4. ĐÃ GIẢI QUYẾT — bỏ khỏi sổ

Mười khoản từng nằm trong danh sách "đang chờ" nhưng **kiểm lại hôm nay thì đã đóng**. Ghi
lại kèm bằng chứng để không ai mở lại.

| Khoản | Trạng thái thật | Bằng chứng |
|---|---|---|
| Chat tuôn dữ liệu thời tiết dự phòng cho LLM như số đo thật | **ĐÃ GIẢI QUYẾT** — `weather_for_llm()` lược sạch số, nuốt luôn ca `weather_data is None` | `c002e184`; `agent/server.py:871-895` |
| Frontend hiển thị số thời tiết dự phòng | **ĐÃ GIẢI QUYẾT** — 3 trạng thái; `estimated` null-hoá toàn bộ trong `emptyReading()` nên template không có gì để lỡ tay render; nhận diện fallback theo hướng TRUTHY (vắng key, không phải `=== false`) | `922fd5bd` |
| `PUT /api/comments/{id}` trả 500 | **ĐÃ GIẢI QUYẾT** — bỏ mệnh đề `updated_at`. *(Hệ quả nhãn "đã sửa" → C1)* | `00a08510`; `agent/social.py:2494-2498` |
| `.ics` sinh sai ngày cho sự kiện all-day | **ĐÃ GIẢI QUYẾT** — 100% ca trượt DTEND | `4bced5e1` |
| Breadcrumb backend phát tên tỉnh cũ, lệch với HTML | **ĐÃ GIẢI QUYẾT** (§1.6). *(Taxonomy vùng là chuyện khác → A5)* | `8a002599` |
| `moderation_status` bình luận không trả về đúng người | **ĐÃ GIẢI QUYẾT** | `94942186` |
| Top-level `verifiedAt` bị đọc/mirror làm nguồn kiểm chứng | **ĐÃ GIẢI QUYẾT TRONG CODE** — pop ở 3 tầng. *(Artifact `data.json` còn bẩn → A6)* | `agent/database.py:2065`, `agent/public_api.py:1035`, `scripts/export_data.py:45` |
| "1 repo hay N repo cho đa tenant" | **ĐÃ CHỐT: N repo (hard-fork), 2026-07-13.** *(Còn mở: bao giờ chạy + VPS thứ hai → C4)* | `docs/superpowers/specs/2026-07-13-dongthap360-fork-design.md` §1 |
| Quét CVE phụ thuộc trong CI | **ĐÃ CÓ** (`pip-audit` + `npm audit --audit-level=high`) nhưng **non-blocking**. *(Có nên chặn → A1 lựa chọn 4)* | `.github/workflows/ci.yml:520-547`, `:523` |
| 16 xã lên phường (Ca A đối chiếu mã hành chính) | **ĐÃ CHỐT 2026-08-07** | `docs/drafts/doi-chieu-ma-hanh-chinh.md:1` |

---

# §5. Bốn khoản nhỏ — cần một câu, không cần một trang

Đủ nhỏ để không cần mục riêng, nhưng vẫn là quyết định của người, không của AI.

| # | Khoản | Câu hỏi | Bằng chứng | CHỐT |
|---|---|---|---|---|
| N1 | `wards-row` ở trang khu vực | Đợt declutter 3 đã thu gọn thành `<details>` (giữ 124 link hub-spoke trong DOM cho crawler). Xoá hẳn khỏi DOM? **Đánh đổi: mất hub-spoke SEO.** | `docs/ROADMAP.md:399` | |
| N2 | `b2g-pitch.md` | Tài liệu đối ngoại — §4 đòi chủ dự án duyệt **toàn văn** trước khi gửi bất kỳ đối tác nào. Đã duyệt chưa? | `docs/ROADMAP.md:407`, `docs/b2g-pitch.md:176` | |
| N3 | CSP `'unsafe-inline'` | Bỏ khỏi `script-src`? Nuxt build ra script có file riêng nên không cần inline; nếu còn thì chuyển nonce/hash. **Đánh đổi: rủi ro vỡ script inline chưa biết.** | `docs/security/owasp-review-2026-08-05.md:556-559`; `nginx.conf:33`, `nginx-ssl.conf:70` | |
| N4 | Trần `fastapi<0.137` | Đặt lịch kiểm lại (upstream vá regression `include_router` chưa?) hay để trần vĩnh viễn? | `docs/security/owasp-review-2026-08-05.md:560-562`; `requirements.txt:4` | |

---

# §6. Tái lập số liệu trong sổ này

Tất cả chỉ đọc, không ghi. Chạy từ gốc worktree.

```bash
# A1 — CVE frontend (12 lỗ: 2 critical, 8 high, 1 moderate, 1 low)
cd web-nuxt && npm audit
node -e "console.log(require('./node_modules/nuxt/package.json').version)"   # 4.4.8
npm audit fix --dry-run    # KHÔNG ghi gì; xác nhận cả 12 lỗ vá được, 0 semver-major

# A1 — phía Python sạch
#   (Trên Windows phải ép UTF-8: requirements.txt có chú thích tiếng Việt,
#    pip-audit mặc định đọc bằng cp1252 → UnicodeDecodeError. CI Linux không gặp.)
PYTHONUTF8=1 python -m pip_audit -r requirements.txt --progress-spinner off
#   → No known vulnerabilities found

# A2 — gate schema còn ở 74
grep -n "PG_REQUIRED_SCHEMA_VERSION = " agent/database.py

# A5 — taxonomy 3 vùng
grep -rn "khu-vuc/ben-tre" --include=*.vue --include=*.py --include=*.ts . | grep -v node_modules

# A6 / B1 / B2 / C5 — đo trên web/data.json
python - <<'PY'
import json, io, re
d = json.load(io.open('web/data.json', encoding='utf-8'))
e = d['entities']
print('entity                :', len(e))                                          # 1746
print('attributes.verifiedAt :', sum(1 for x in e if (x.get('attributes') or {}).get('verifiedAt')))   # 0
print('top-level verifiedAt  :', sum(1 for x in e if x.get('verifiedAt')))        # 1746  ← A6
print('co anh                :', sum(1 for x in e if x.get('images')))            # 57 = 3,3%  ← B1
print('description < 200     :', sum(1 for x in e if len(x.get('description') or '') < 200))  # 764 = 43,8%  ← B2
print('booking_note          :', sum(1 for x in e if (x.get('attributes') or {}).get('booking_note')))  # 117  ← C5
PY

# C8 — is_account_locked chua duoc noi day (0 call-site ngoai module)
grep -rn "is_account_locked" --include=*.py agent/ | grep -v tests
```

**Không chạy trong phiên lập sổ:** `scripts/scorecard.py` (ghi đè history), toàn bộ pytest
suite (~50 phút), và mọi lệnh ghi vào `agent/data/vinhlong360.db` / `web/data.json`.

**Lưu ý khi tự kiểm lại:** `pytest.ini` `addopts` loại 4 marker (`slow`, `integration`,
`entity_status_postgres`, `subprocess_heavy`) — thêm `-m ""` nếu cần chạy chúng.

---

# §7. Tài liệu nguồn

| Nguồn | Vai trò |
|---|---|
| `docs/2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md` | A4 — bảng CHỐT 17 dòng, §5 mìn `attributes.month`, §7 việc KHÔNG được làm |
| `docs/superpowers/plans/2026-08-05-nang-chat-luong-toan-dien.md` | B1–B7 — checklist go-live 5 trụ, 3 bài học đã trả giá |
| `docs/security/owasp-review-2026-08-05.md` | B4, B5, C8, N3, N4 — rà OWASP có `path:line`, §4 "chưa kiểm được" |
| `docs/drafts/doi-chieu-ma-hanh-chinh.md` | C6 — Ca A đã chốt, Ca B/C còn treo |
| `docs/drafts/lo-10-entity-mau.md` | C7 — §3 cần chủ quyết, §F 4 quy ước biên tập |
| `docs/superpowers/specs/2026-07-13-dongthap360-fork-design.md` | C4 — hard-fork đã chốt, VPS riêng, phân đợt SP1 |
| `docs/ROADMAP.md` §"Backlog phát sinh" | C9, N1, N2 — nguồn backlog SỐNG (tin bên này hơn `HANDOFF.md` §10) |
| `docs/entity-content-model.md` | C10 — 4 câu hỏi mô hình |
| `docs/toi-uu-chong-ai-va-google-spam-playbook.md` | B7 — P0-1 per-page robots phải ship TRƯỚC khi gỡ noindex |
| `docs/HANDOFF-BRANCHES.md` | **Sổ chị em** — quyết định hợp/xoá nhánh & worktree. Sổ này KHÔNG chứa chúng; hai file không chồng lấn. |

> **Cập nhật sổ:** khoản được chốt → chuyển xuống §4 kèm commit đóng, **đừng xoá**. Khoản
> mới phát sinh → thêm vào nhóm đúng độ GAP. Sổ mất giá trị đúng lúc nó thôi phản ánh sự
> thật đo được.

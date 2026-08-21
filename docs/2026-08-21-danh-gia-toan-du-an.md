# Đánh giá toàn dự án vinhlong360 — 2026-08-21

> STATUS: active
> Hai nửa chạy song song: **đối chiếu bên ngoài** (nghiên cứu web, phản biện từng luận điểm
> trên văn bản gốc) và **kiểm toán nội bộ toàn repo** (15 phát hiện, 10 qua phản biện).
> Mọi con số dưới đây do phiên này tự đo, không lấy lại từ tài liệu cũ.
> Phạm vi loại trừ: `agent/cases/**` vừa qua 4 đợt rà soát đối kháng trong tuần, xem
> `docs/superpowers/results/2026-08-12-correction-case-pilot.md`.

---

## 0. Kết luận trong một trang

**Điều nghiêm trọng nhất không nằm trong mã.** Cơ sở pháp lý về dữ liệu cá nhân mà dự án
đang dựa vào **đã hết hiệu lực chủ đạo**: Việt Nam nay áp dụng **Luật 91/2025/QH15 — Luật
Bảo vệ dữ liệu cá nhân** (Quốc hội thông qua 26/06/2025, hiệu lực **01/01/2026**). Nghị định
13/2023 chỉ còn sống qua điều khoản chuyển tiếp (Điều 39). Luật đã có hiệu lực **8 tháng**
tính tới hôm nay, và mọi ghi chú pháp lý trong repo vẫn viết theo khung NĐ13.

**Điều nghiêm trọng thứ hai cũng không nằm trong mã.** Ranh giới "chỉ giới thiệu nên không
phải sàn TMĐT" — nền tảng của quyết định §1.4 trong CLAUDE.md — **hẹp hơn dự án đang giả
định**, và điểm chạm rủi ro chính là **mô hình doanh thu premium/featured listing**.

**Trong mã**: nhánh này **không thể qua cổng merge của chính dự án** hôm nay. `scorecard`
báo backend **tụt 99 → 81**, và `pre_merge_check` bước 7 chặn đúng tình trạng đó.

---

## 1. Số đo nền (tự đo, 2026-08-21)

| Hạng mục | Số đo |
|---|---|
| File được git theo dõi | 1.744 |
| `agent/**/*.py` | 207.190 dòng |
| `web-nuxt` (.vue + .ts) | 99.672 dòng |
| `tests/**/*.py` + `agent/tests` | 63.274 dòng |
| `docs/**/*.md` | 104.155 dòng |
| `scripts/**/*.py` | 32.285 dòng |
| `web/data.js` | **5,43 MB** (1 file, 166.646 dòng) |
| `web/data.json` | 4,43 MB · 1.746 entity · 12.060 quan hệ · 33 lịch trình |

**Scorecard (`scripts/scorecard.py --no-append`)**

| Chiều | Điểm | Nợ |
|---|---|---|
| data | 100 | 0 |
| backend | **81** ⚠ | 48 |
| frontend | 60 | 798 |
| ui-design | 100 | 0 |
| content | 51 | 378 |
| docs | 100 | 0 |
| ops | 100 | 0 |

`hard-violations: 0`. Nợ backend 48 = R20.4 (1, artifact CI) + **R20.8 độ phức tạp (47)**.

### 1.1 Nhánh không qua được cổng merge

`scripts/pre_merge_check.py:212` bước 7 chạy `scorecard --no-append` và **fail khi bất kỳ
chiều nào tụt điểm**. Backend tụt 99 → 81 so với mốc lịch sử gần nhất (2026-07-10). Đây là
điều kiện chặn merge, hiện **chưa được ghi ở bất kỳ tài liệu nào**.

Nguồn của tụt điểm: baseline R20.8 từng được nâng 36 → 47 trong Task 18 (có giải trình ở
`docs/standards/90-exceptions-log.md`). `run_hard` sạch vì 47 ≤ baseline 47; scorecard thì
đo **tiến độ trả nợ so với mốc gốc**, nên việc nâng ratchet hiện ra đúng như nó là: nợ tăng.
Hai công cụ không mâu thuẫn — chúng đo hai thứ khác nhau, và scorecard là cái nói thật hơn.

> **Ghi nhận một sai sót của phiên này.** Lệnh `scorecard.py` mặc định **ghi thêm một dòng
> vào `docs/standards/scorecard-history.jsonl`**. Vì `pre_merge_check` so với *entry gần
> nhất*, dòng tôi vừa ghi (backend=81) sẽ khiến lần chạy sau so 81 với 81 → **không còn coi
> là tụt điểm** → cổng merge im lặng mở ra. Tôi đã **gỡ dòng đó**; history quay lại kết thúc
> ở mốc 2026-07-10 (backend=99) và `--no-append` vẫn báo tụt đúng như trước. Khi đo scorecard
> để *xem xét*, luôn dùng `--no-append`.

---

## 2. Đối chiếu bên ngoài — nghiên cứu có phản biện

Phương pháp: fan-out tìm kiếm → tải nguồn → trích luận điểm **có thể bác bỏ** → mỗi luận
điểm qua vòng phản biện đối kháng trên **văn bản gốc**. Kết quả: **19 luận điểm đứng vững**
(18 mức tin cậy cao, 1 trung bình), **4 bị bác**. Người phản biện nhiều lần cố bác bằng cách
nghi ngờ trích dẫn sai — và chính nỗ lực đó lộ ra phát hiện §2.1.

### 2.1 🔴 Khung dữ liệu cá nhân đã đổi luật, dự án chưa cập nhật

**Luật 91/2025/QH15 — Luật Bảo vệ dữ liệu cá nhân**, thông qua 26/06/2025, **hiệu lực
01/01/2026**. Nghị định 13/2023/NĐ-CP chỉ còn hiệu lực qua điều khoản chuyển tiếp (Điều 39).
Xác minh: nhiều người kiểm độc lập tải bản ký gốc từ `datafiles.chinhphu.vn` (91qh.signed.pdf)
và đối chiếu từng điều; ban đầu họ **giả định đây là trích dẫn nhầm NĐ13** và cố bác — không
bác được.

**Vì sao quan trọng với dự án này:** kênh đính chính thu **số điện thoại** người báo và giữ
theo kệ 90/365/730 ngày. Nghĩa vụ về đồng ý, thời hạn lưu, quyền xoá, và đánh giá tác động
nay đọc theo **Luật**, không đọc theo Nghị định. Toàn bộ ghi chú pháp lý trong repo cần rà
lại theo văn bản mới trước khi bật cờ.

**Việc cần làm:** đây là câu hỏi cho **luật sư**, không phải cho tôi — CLAUDE.md §4 đã đặt
Track-H vào nhóm điều-kiện-dừng. Tôi chỉ nêu rằng cơ sở đã đổi.

### 2.2 🔴 Ranh giới "chỉ giới thiệu" hẹp hơn giả định, và doanh thu là điểm chạm

Bốn luận điểm đứng vững, hợp lại thành một bức tranh khác với §1.4 CLAUDE.md:

1. **Điểm dự án làm đúng.** Sau NĐ85/2021, nghĩa vụ **thông báo** với Bộ Công Thương chỉ
   phát sinh với website bán hàng **có chức năng đặt hàng trực tuyến**. Site chỉ trưng bày,
   CTA là gọi điện/Zalo, không có nút đặt hàng → **không phải thông báo**. Quyết định §1.4
   (không form chốt đơn giá+SL+xác nhận) là **đúng và có căn cứ**.

2. **Nhưng "chỉ giới thiệu" không tự miễn trừ.** NĐ52/2013 xếp *"trưng bày giới thiệu hàng
   hóa, dịch vụ"* là **mắt xích ĐẦU TIÊN** của quy trình thương mại. Và website **cho phép
   người tham gia mở gian hàng** để trưng bày/giới thiệu đã bị xếp là một **hình thức hoạt
   động của sàn giao dịch TMĐT**. Ranh giới thật nằm ở chỗ **bên thứ ba có tự mở và tự quản
   lý gian hàng của họ hay không**.

3. **Điều kiện kép, và mắt xích thứ hai là doanh thu.** Mạng xã hội chỉ bị coi là sàn khi hội
   đủ **HAI** điều kiện đồng thời: (a) có một trong các hình thức tại điểm a/b/c khoản 2 Điều
   35, **VÀ** (b) người tham gia **trả phí trực tiếp hoặc GIÁN TIẾP** cho hoạt động đó.
   → **`premium/featured listing` là phí trực tiếp từ chủ cơ sở cho việc trưng bày.** Nếu
   tương lai có thêm bất kỳ cơ chế nào để chủ cơ sở **tự quản lý trang của mình**, hai điều
   kiện có thể đủ cùng lúc.

4. **Hậu quả nếu bị xếp là sàn** nặng hơn hẳn: từ *thông báo* lên **ĐĂNG KÝ** thiết lập
   website (Mục 2 Chương IV) **và** công bố thông tin người sở hữu theo Điều 29 **trên trang
   chủ**.

**Đọc thế nào cho đúng:** hôm nay dự án **chưa** vượt ranh giới — không có gian hàng tự quản.
Nhưng §1.4 đang ghi doanh thu premium/featured listing như một lựa chọn *an toàn*, trong khi
nó chính là **một nửa của điều kiện kép**. Nửa còn lại là bất kỳ tính năng "chủ cơ sở tự
sửa trang mình" nào — và một kênh đính chính là hàng xóm rất gần của tính năng đó.

### 2.3 🟡 Đã có sẵn một mốc SLA 24 giờ trong pháp luật TMĐT

Pháp luật TMĐT Việt Nam đặt mốc **24 giờ** để gỡ thông tin hàng hoá/dịch vụ vi phạm khi có
yêu cầu của cơ quan quản lý nhà nước có thẩm quyền. Chính sách hiện tại của kernel dùng
`update_target_seconds = 259200` (3 ngày) cho nhịp cập nhật. Hai mốc phục vụ hai việc khác
nhau, nhưng **mốc 24 giờ là con số cơ quan nhà nước sẽ dùng để đo**, nên nó nên xuất hiện
trong policy như một kênh ưu tiên riêng, không lẫn vào nhịp 3 ngày.

### 2.4 🟡 NĐ147/2024: miễn giấy phép có điều kiện

Theo NĐ147/2024 Điều 24, website tư nhân được miễn cấp phép nếu là *"trang thông tin điện tử
cung cấp dịch vụ chuyên ngành"* — và Điều 3 khoản 23 **liệt kê "văn hóa, thể thao và du
lịch"** là một lĩnh vực chuyên ngành — hoặc là trang nội bộ. Miễn trừ này **có điều kiện
kèm theo**; cần luật sư đọc trọn điều khoản trước khi dựa vào nó.

### 2.5 🟢 EU DSA — dự án đang đi đúng hình dạng chuẩn quốc tế

DSA không ràng buộc pháp lý ở Việt Nam, nhưng là mô tả rõ nhất về *hình dạng đúng* của một
kênh xử lý phản ánh. Đối chiếu:

| DSA yêu cầu | Dự án hiện tại |
|---|---|
| Điều 17 — **statement of reasons** cho mọi quyết định; từ chối **không được im lặng** | ✅ Vừa sửa tuần này: người bị từ chối thấy đúng lý do, kèm "bạn có thể gửi thêm nguồn" |
| Điều 20 — kênh **khiếu nại nội bộ** miễn phí, người có chuyên môn xử lý | ✅ Có đường phản hồi; nút vừa được sửa để **hiện ra** cho người bị từ chối |
| Điều 12 — **một đầu mối liên hệ** rõ ràng | ✅ CTA Zalo/điện thoại |
| Thông báo **hai chiều** (người báo + người bị ảnh hưởng) | ⚠ Chỉ có phía người báo |
| Công bố quyết định ra CSDL công khai, **đã bóc dữ liệu cá nhân** | ⚠ Chưa có; DSA cũng cho nhóm micro/small miễn phần nặng |
| Báo cáo kiểm duyệt **định kỳ ≥1 lần/năm** | ⚠ Chưa có |
| Điều 21 — hoà giải ngoài toà | ➖ Không áp dụng ở VN |

Ba dòng ⚠ đều là **lựa chọn**, không phải nghĩa vụ ở VN — nhưng nếu muốn hợp đồng B2G, đây
là bộ khung để chứng minh quy trình có kỷ luật.

### 2.6 🟡 WCAG 2.2 AA — accessibility gate hiện thiếu 2 tiêu chí

Nghiên cứu chốt được các tiêu chí ràng buộc **đúng vào** biểu mẫu báo lỗi và trang tra cứu:

| Tiêu chí | Mức | Gate hiện có? |
|---|---|---|
| 4.1.3 Status Messages — thông báo trạng thái phải máy đọc được | AA | ✅ có (live region) |
| 3.3.1 Error Identification | A | ✅ có (error summary) |
| 3.3.3 Error Suggestion — biết cách sửa thì **phải nói cách sửa** | AA | ⚠ một phần |
| **3.3.4 Error Prevention** — bước xem-lại-rồi-xác-nhận | **AA** | ❌ **thiếu** |
| **3.3.7 Redundant Entry** — không bắt nhập lại thứ đã nhập | **A** | ❌ **thiếu** |
| 3.3.8 Accessible Authentication — cấm CAPTCHA kiểu đố trí nhớ | AA | ✅ (không dùng CAPTCHA) |

**Điểm đắt nhất:** SC 3.3.4 **được kích hoạt** bởi chính hành vi gửi báo lỗi, vì nó *"sửa
đổi dữ liệu người dùng kiểm soát trong hệ thống lưu trữ"* — không cần là giao dịch thương
mại. Chuẩn cho phép chọn **một trong ba** (hoàn tác được / kiểm tra được / xác nhận được),
nên **một bước xem-lại trước khi gửi là đủ đạt AA**. Đây là việc nhỏ, giá trị cao.

Và: tuyên bố "WCAG 2.2 AA" là cam kết **tất-cả-hoặc-không** — đạt AA đòi hỏi đạt **mọi** tiêu
chí mức A lẫn AA. Thiếu 3.3.7 (mức A) là đủ để tuyên bố AA thành sai.

---

## 3. Kiểm toán nội bộ — 6 phát hiện đứng vững / 10 qua phản biện

Mỗi phát hiện qua một vòng phản biện *mặc định coi là sai*. **4 bị bác**, gồm cả hai cái từng
gắn nhãn blocker — chi tiết ở §3.7.

### 3.1 🔴 Chat vẫn khẳng định một entity đã bị gỡ là còn tồn tại — vĩnh viễn

`agent/admin.py:95` — `_sync_kb()`, hook write-through cho cả **12 điểm ghi của AdminCP** —
xoá cache LLM và hai cache admin, **nhưng không xoá catalogue KB của chat**. `kb_context._cache`
**không có TTL, không kiểm số lượng**: `get_kb_context()` trả về bản digest **đầu tiên nó từng
dựng, mãi mãi**. Nơi duy nhất làm mới nó là `POST /reload` — mà đường CRUD entity **không hề
gọi**.

**Kịch bản hỏng:** admin xử lý một yêu cầu gỡ bỏ tại `/admin/reports` và xoá entity. Hàng DB
biến mất, `knowledge._entities` dựng lại không có nó. Nhưng **mọi request `/chat` sau đó vẫn
nhét catalogue cũ vào system prompt**, dưới đúng câu chỉ dẫn nói rằng danh sách này là thẩm
quyền và không được đi ra ngoài nó. Mô hình **khẳng định entity đã gỡ vẫn tồn tại và gọi tên
nó**. Trường hợp ngược lại cũng bền như vậy: entity mới tạo không có trong catalogue → mô
hình được bảo là nó **không tồn tại**.

Điều này đánh bại **cả** đường gỡ bỏ **lẫn** chính bảo đảm chống-bịa mà catalogue sinh ra để
cung cấp. Bản vá nhỏ nhất: thêm `kb_context.invalidate()` vào `_sync_kb()`, bọc try/except
theo đúng khuôn đã dùng cho cache LLM.

### 3.2 🔴 `GET /admin/claims` trả số điện thoại **không che**

`agent/admin.py:5555` chọn `u.phone as claimant_phone`; `:5567` trả thẳng qua `_row_to_dict`
**không che**. Đây là endpoint **duy nhất** trong API trả `users.phone` thô — quy tắc che số
được giữ ở `:3531`, `:4055`, `:4819`, `:4853`, `:5285`, và hàm `_mask` nằm **ngay trên nó ở
`:5292`**. *(Tôi đã tự đọc mã xác nhận, không chỉ dựa vào agent.)*

Bản vá: che đúng một cột trong handler.

### 3.3 🔴 Runbook deploy hứa backup mà script không làm

`docs/HANDOFF.md:84` — file mà CLAUDE.md §4 chỉ định là runbook deploy production, và đang
mang `STATUS: active` nên không checker nào gắn cờ — ghi:

> "Tự: pre-flight health → (build) → **backup prod (db dump + code tar)** → scp → …"

`scripts/deploy.sh` **không có bước backup nào**. Tôi grep `pg_dump|backup|tar|rotate`: kết
quả duy nhất là cờ `--no-backup` in ra *"obsolete for the atomic closed-release installer"*.
Dòng `:97` hứa "xoay-vòng giữ 6 bản" cũng không tồn tại.

**Vì sao đây là hạng nặng:** đây là tài liệu người chủ sẽ đọc **vào đúng lúc cần khôi phục**.
Tin rằng deploy đã tự backup, trong khi nó không, là cách mất dữ liệu không tái tạo được —
đúng thứ bất biến B1 tồn tại để chặn.

### 3.4 🟡 Backup hằng ngày **xoá bản tốt cũ trước khi kiểm bản mới**

`scripts/ops/backup_db_daily.sh`: dump ghi ở `:12`, **xoay vòng xoá ở `:16`**
(`ls -t | tail -n +8 | xargs rm -f`) với file mới **chưa được kiểm** đang chiếm slot 1, còn
`gzip -t` và kiểm footer chỉ chạy ở `:21-25`. Một bản dump hỏng nhưng ghi xong vẫn đẩy bản
tốt cũ nhất ra khỏi vòng giữ **trước khi có ai biết nó hỏng**.

Bản vá: kiểm tính toàn vẹn **trước**, xoá file hỏng, rồi mới xoay vòng.

### 3.5 🟡 Vòng lặp học: backfill toạ độ chọn nhầm khoá, và ghi vào nơi không ai đọc

`agent/learn_loop.py:748-749` chọn ứng viên theo khoá **legacy `coords`** đã chết, trong khi
phía ghi (`:763`) đúng là `coords` HOẶC `coordinates`. Đo trên `web/data.json` thật: chọn ra
**1.621 entity**, trong đó **1.609 đã có `coordinates`** — cửa sổ 15 slot tiêu 12 slot vào
những entity **không bao giờ ghi được**. Chỉ 3 trong 12 entity thiếu toạ độ thật lọt vào cửa
sổ; sau khi ghi 3 cái đó, cửa sổ dịch đúng 3 và 9 cái còn lại **không bao giờ được thử lại**.

Nặng hơn: `_persist_backfilled_coords` ghi **chỉ vào `web/data.json`**, còn `knowledge.reload()`
đọc lại **từ DB** — nên công sức **không bao giờ tới trang chạy thật**. Hai đường anh em trong
cùng file thì ghi kép qua `db.upsert_entity`.

Phụ: sắp xếp ưu tiên ở `:751` **hoàn toàn trơ** trên dữ liệu thật (mọi entity có `status=None`,
`verified=1`), và mệnh đề `e.get("verified") is False` là so sánh **identity** không bao giờ
khớp số nguyên `0` mà DB và JSON thật sự lưu.

### 3.6 🟡 Tài liệu setup chỉ tới một cổng không tồn tại

`docs/developer-setup.md:44,52-53` bảo dev chạy `docker compose up -d postgres` rồi kết nối
`localhost:5432`. `docker-compose.yml:9-10` khai `expose: "5432"` **không có `ports:`**, và
không có file override — nên endpoint được ghi trong tài liệu **không kết nối được**.

Lưu ý khi sửa: **đừng thêm `ports:`** — `tests/launch_safety/test_compose_contract.py:217`
cố ý bắt sự vắng mặt của nó. Đây là sửa tài liệu, không phải sửa compose.

### 3.7 Bốn phát hiện **bị bác** — và vì sao điều đó quan trọng

| Cáo buộc | Vì sao bị bác |
|---|---|
| `backup_offsite.py` đẩy dump PG **chưa mã hoá** lên bucket media công khai | Script **không có đường mã nào** tới bucket công khai; cáo buộc lẫn hai đích khác nhau |
| Rate limit theo IP **sập về IP container nginx** | Tiền đề sai: docker-compose **không phải** đường deploy production; `scripts/deploy.sh` mới là |
| 8 test admin bị khoá sau `USE_POSTGRES` — biến không tồn tại ở đâu khác | Quan sát đúng, nhưng **hại không chạm tới được** vì hai lý do độc lập |
| Marker `slow` bị trừ ở mọi đường tự động → launch-safety không bao giờ chạy | Sai: `scripts/release_gate.ps1:436` **có** chạy chúng |

Hai cái đầu vào workflow với nhãn **blocker**. Nếu tôi thuật lại thẳng, báo cáo này đã có hai
lỗ hổng bảo mật nghiêm trọng **không có thật**. Vòng phản biện là thứ ngăn điều đó.

---

## 4. Phát hiện của riêng tôi khi tự đo

**`web/data.js` — 5,43 MB được sinh lại cho một người đọc không còn tồn tại.**
`agent/scheduler.py:98` chạy `sync_data_json_to_js()` mỗi lần khởi động và mỗi giờ, ghi đè
file **được git theo dõi**. Comment ở `:110` nói lý do: *"web/index.html loads data.js without
type=module"*. Nhưng `web/` **không còn file `.html` nào** — tôi kiểm rồi. Và có hẳn một file
test (`agent/tests/test_scheduler_repo_isolation.py`, 10 tham chiếu) sinh ra để canh cho task
này khỏi giẫm lên file tracked.

Tức là: một tác vụ nền duy trì 5,43 MB dữ liệu trong git cho một consumer đã bị xoá, và một
suite test bảo vệ hành vi đó.

**Comment của `knowledge.py` nói dối về nguồn của chính nó.** Docstring `:4` và comment `:27`
nói module đọc `web/data.js` bằng regex và *"data.js là nguồn duy nhất"*. Mã ở `:30-32` mở
`data.json`. Comment sai này khiến **tôi đọc nhầm hai lần trong ba phút** — nó sẽ làm điều
tương tự với người tiếp theo.

---

## 4b. Nghiên cứu vòng 2 — tự đi lấy văn bản gốc

Workflow deep-research bị tiến trình giết **ba lần** giữa chừng. Vòng này tôi **tự fetch**
nguồn, đồng bộ, nên không mất giữa đường. Mỗi mục dưới đây khớp **≥2 nguồn độc lập** hoặc là
cổng Chính phủ/Bộ chủ quản.

### 4b.1 🟢 Miễn trừ theo quy mô — tin tốt, và nó đổi kế hoạch

Nguồn: [xaydungchinhsach.chinhphu.vn](https://xaydungchinhsach.chinhphu.vn/quoc-hoi-da-thong-qua-luat-bao-ve-du-lieu-ca-nhan-119250626153701582.htm)
(Cổng TTĐT Chính phủ), khớp với kết quả tìm kiếm trên miền `.gov.vn`.

> Doanh nghiệp nhỏ, doanh nghiệp khởi nghiệp **được quyền lựa chọn thực hiện hoặc không thực
> hiện** các quy định về **lập hồ sơ đánh giá tác động**, **chỉ định bộ phận/nhân sự bảo vệ dữ
> liệu cá nhân** **trong thời hạn 05 năm** kể từ ngày Luật có hiệu lực, và **miễn thực hiện đối
> với hộ kinh doanh, doanh nghiệp siêu nhỏ**.

**Nghĩa là với vinhlong360** (solo dev, <10k user, ngân sách <1 triệu/tháng): bộ máy tuân thủ
*nặng* — hồ sơ đánh giá tác động, nhân sự chuyên trách — **không phải dựng trước khi bật cờ**.
Miễn hẳn nếu là hộ kinh doanh/siêu nhỏ; được chọn tới **01/01/2031** nếu là doanh nghiệp nhỏ.

Đây là điều đáng biết **trước** khi đầu tư công sức vào hồ sơ tuân thủ.

### 4b.2 🔴 Nhưng nghĩa vụ KHÔNG được miễn lại đúng chỗ dự án đang hở

Miễn trừ trên chỉ chạm hai nghĩa vụ *thủ tục*. Các nghĩa vụ **nội dung** không được miễn cho
ai cả — và Điều 4 liệt kê quyền của chủ thể dữ liệu gồm: được biết, **đồng ý và rút lại đồng
ý**, xem/chỉnh sửa, yêu cầu cung cấp/**xoá**/hạn chế xử lý, phản đối, khiếu nại/khởi kiện.

Bộ Công an còn nêu nghĩa vụ với dịch vụ trực tuyến: **cơ chế opt-out theo dõi**, **chính sách
riêng tư minh bạch**, và **người dùng truy cập được dữ liệu của mình**; đồng thời **không được
đòi ảnh/video giấy tờ tuỳ thân** làm yếu tố xác thực.
([mps.gov.vn](https://mps.gov.vn/chinh-sach-phap-luat/bai-viet/mot-so-quy-dinh-dang-chu-y-trong-luat-bao-ve-du-lieu-ca-nhan-2025-1753847906))

**→ Đây chính là chỗ §4b.4 dưới đây cắn.** Quyền rút lại đồng ý nằm trong nhóm *không được
miễn*, và trang chính sách của dự án đã **hứa** nó — nhưng mã không nhận được.

### 4b.3 🟡 Chế tài — thang tiền so với ngân sách dự án

Cùng nguồn Cổng TTĐT Chính phủ:

| Hành vi | Mức |
|---|---|
| Mua/bán dữ liệu cá nhân (**bị cấm tuyệt đối**) | tới **10 lần** khoản thu bất hợp pháp |
| Chuyển dữ liệu xuyên biên giới trái quy định | tối đa **5% doanh thu năm trước** |
| Vi phạm khác | tới **3 tỷ đồng** |
| Cá nhân vi phạm | **một nửa** mức của tổ chức |

Trần 3 tỷ đồng cho "vi phạm khác" là con số cần đặt cạnh ngân sách <1 triệu đồng/tháng khi
cân nhắc bật cờ.

### 4b.4 🔴 Phát hiện của riêng tôi: chính sách hứa một quyền mà mã không nhận được

Bốn file, tôi tự đọc và đối chiếu:

| File | Sự thật |
|---|---|
| `web-nuxt/utils/legalContent.ts:44` | Hứa **"Rút lại đồng ý — trong vòng 15 ngày"**, không giới hạn cho người có tài khoản |
| `agent/cases/public_api.py:436` | Route liên hệ **ghim cứng `consent=True`** |
| `agent/cases/public_api.py:225` | `_ContactRequestIn` chỉ khai `phone`, `extra="forbid"` → gửi kèm `consent` là **422** |
| `agent/cases/contact.py:121` | Cơ chế rút **có thật** ở tầng domain, comment ghi rõ *"Withdrawing consent simply leaves no live challenge"* — nhưng **không HTTP nào chạm tới** |

Người báo ẩn danh **không có tài khoản** để dùng đường "xoá tài khoản 30 ngày"
(`accountErasureDeadlineDays = 30`). Nên với họ, lời hứa 15 ngày hiện **không có đường thực
hiện**. Cơ chế đã viết xong; chỉ thiếu một trường trong model và một dòng ở route.

**Cần nói cho công bằng:** phần *lấy* đồng ý của dự án làm **tốt** — số điện thoại là tuỳ
chọn, ô đồng ý chỉ hiện khi có nhập số, câu chữ giới hạn mục đích rõ ràng (*"dùng số này để
báo kết quả yêu cầu, và chỉ việc đó"*), và nhập số mà chưa tick là **lỗi chặn gửi**
(`CorrectionIntakeForm.vue:84`). Thiếu là ở phía **rút lại** và **thời hạn lưu**: mục 3 chính
sách chỉ ghi *"giữ trong thời gian cần thiết"*, trong khi kernel cài kệ cụ thể 90/365/730 ngày
mà người báo không được cho biết.

### 4b.5 🟡 NĐ147/2024 — ràng buộc với "trang thông tin điện tử tổng hợp"

Hiệu lực **25/12/2024**. Với trang tổng hợp: đăng lại tin **chậm hơn 1 giờ** so với nguồn;
nguồn từ **≥3 cơ quan báo chí**; **người dùng KHÔNG được bình luận** trên bài của trang tổng
hợp; không dùng tên miền/tên trang gây nhầm với báo chí.

Dự án chỉ trích **tiêu đề + đoạn + link** (đúng B6 CLAUDE.md), nên nhiều khả năng không phải
trang tổng hợp — nhưng vế *"người dùng không được bình luận"* đáng hỏi luật sư nếu site có UGC.
Điều 24 (điều kiện miễn giấy phép) tôi **chưa lấy được toàn văn** — `mic.gov.vn` không phân
giải được DNS lúc chạy, và bản PDF ký trên `datafiles.chinhphu.vn` là **ảnh scan không trích
được chữ**. Ghi ra thay vì đoán.

### 4b.6 Giới hạn của vòng này

- Bản ký gốc Luật 91/2025 là **PDF scan ảnh**; máy không có `poppler` để render, nên tôi
  **không tự đọc được từng điều khoản**. Các con số trên lấy từ cổng Chính phủ và Bộ chủ quản,
  khớp chéo — **không phải** tôi đọc thẳng luật.
- `thuvienphapluat.vn` trả **403**, `mic.gov.vn` **không phân giải DNS**.
- Vì vậy: mọi mục §4b vẫn là **đầu vào cho luật sư**, không phải kết luận pháp lý.

## 5. Việc nên làm, xếp theo tỉ lệ giá trị/công sức

**Nhóm A — ĐÃ LÀM XONG 2026-08-21** (`2db15aec`, `ce20282d`, `e2d60952`)

1. ✅ Che `claimant_phone` ở `admin.py:5567` (§3.2) — một dòng, có `_mask` sẵn.
2. ✅ Thêm `kb_context.invalidate()` vào `_sync_kb()` (§3.1) — vá đường gỡ bỏ.
3. ✅ Đảo thứ tự kiểm-trước-xoay-vòng ở `backup_db_daily.sh` (§3.4).
4. ✅ Sửa `HANDOFF.md §5` cho khớp `deploy.sh` thật (§3.3) — chỉ sửa tài liệu.
5. ✅ Sửa `developer-setup.md` (§3.6) — chỉ sửa tài liệu, **không** đụng compose.
6. ✅ Sửa docstring `knowledge.py` (§4).
7. ✅ Thêm bước xem-lại-trước-khi-gửi cho form báo lỗi → **đạt WCAG SC 3.3.4** (§2.6).

**Nhóm B — cần quyết định của chủ dự án**

8. **Rà lại toàn bộ ghi chú pháp lý theo Luật 91/2025/QH15** (§2.1, §4b) — Track-H, cần
   luật sư. Mang theo §4b.1 (miễn trừ quy mô) để hỏi đúng câu: dự án thuộc nhóm nào.
8b. ✅ **Mở đường rút lại đồng ý** — ĐÃ LÀM (`2db15aec`). (§4b.4): thêm `consent: bool` vào `_ContactRequestIn` và
   truyền xuống thay cho hằng `True`. Cơ chế đã có sẵn ở `contact.py`. Kèm nêu thời hạn lưu
   thật (90 ngày sau khi khép hồ sơ) cho người báo thấy.
9. **Xem lại §1.4 CLAUDE.md** về premium/featured listing dưới điều kiện "trả phí gián tiếp"
   (§2.2) — cần luật sư trước khi mở bất kỳ tính năng tự-quản-lý-trang nào.
10. Trả nợ R20.8 (47) hoặc chấp nhận nhánh không merge được (§1.1).
11. `web/data.js`: giữ hay bỏ (§4) — bỏ thì gọn 5,43 MB và một suite test.

**Nhóm C — đã ghi nhận, chưa cần làm ngay**

12. `learn_loop` backfill (§3.5) — chỉ chạy khi được kích hoạt thủ công.
13. Thông báo hai chiều, công bố quyết định, báo cáo định kỳ (§2.5) — cho hồ sơ B2G.

---

## 6. Giới hạn của đánh giá này

- **Không** chạm production, không deploy, không đổi secret.
- Nửa nghiên cứu bên ngoài dừng ở bước tổng hợp tự động (workflow bị ngắt hai lần khi tiến
  trình thoát); **tôi tự tổng hợp từ 58 kết quả agent đã hoàn thành** trong journal — 28 kết
  quả trích luận điểm, 23 phán quyết phản biện. Không có luận điểm nào bị bịa thêm.
- **Không phải tư vấn pháp lý.** §2.1, §2.2, §2.4 nêu rằng cơ sở pháp lý đã đổi và ranh giới
  hẹp hơn giả định — kết luận áp dụng cho dự án là việc của luật sư.
- `agent/cases/**` nằm ngoài phạm vi lần này.
- 4 câu SQL động và các cáo buộc §3.7 là **ranh giới đã biết**, ghi ra thay vì giấu.

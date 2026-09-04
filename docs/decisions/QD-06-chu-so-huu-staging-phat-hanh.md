> STATUS: active
Authority: config/release-authority.json

# QD-06 — Chủ sở hữu staging / phát hành (`release_owner`)

> **Hồ sơ này CHƯA KÝ.** Máy **không được** điền §7. Deploy prod thuộc điều kiện dừng
> `CLAUDE.md` §4; một agent điền §7 ở đây là tự cấp cho mình quyền phát hành.

`decision_key`: `release_owner` · Findings gốc: F-13, F-14, F-15
(`docs/audit-toan-du-an-2026-08.md:236-238`)

---

## 1. BỐI CẢNH

**Đường phát hành hiện tại không tới máy chủ nào.**
`docs/audit-toan-du-an-2026-08.md:238` (F-15, trạng thái **Verified**): workflow deploy
chạy precheck ở mức thông tin và tạo GitHub Release; **không SSH, không remote compose,
không rollout, không rollback**; bước backup và health check để `continue-on-error`, tức
hỏng cũng không làm job đỏ. Trích dẫn của dòng đó: `.github/workflows/deploy.yml:90-199`.

**Hai cổng vận hành đi kèm cũng chưa đóng.**

- `docs/audit-toan-du-an-2026-08.md:236` (F-13): daily backup tạo `*.sql.gz`, restore
  drill lại tìm `.dump/.backup`, script offsite không tìm `*.sql.gz` — job có thể xanh
  trong khi artifact **không restore được**.
- `docs/audit-toan-du-an-2026-08.md:237` (F-14): Prometheus scrape `node-exporter:9100`
  nhưng Compose không có service đó; `/metrics` bị chặn admin nên có thể trả 401; không
  thấy Alertmanager/rules/notifier. Watchdog chủ yếu log và restart.

**Điều kiện mở closed pilot nêu cả ba thành một dòng.**
`docs/audit-toan-du-an-2026-08.md:832`: *"F-13 backup/restore chạy được trên artifact
mới; F-14 có alert receiver thật; F-15 có staging rollout/rollback."* Dòng kế
(`:834`) đòi có owner/on-call, support route, correction SLA clock và incident
escalation.

**Cổng nghiệm thu đòi năm lớp bằng chứng, ba lớp không có ở đây.**
`config/release-authority.json:18` khai
`required_layers: ["unit", "postgres", "multi_process", "browser", "external_side_effect"]`.
Trên máy này hiện chỉ có bằng chứng PostgreSQL dùng-một-lần cho **3 trong 28** finding P1
(`config/release-authority.json:33` liệt đủ 28). Ba lớp `multi_process`, `browser`,
`external_side_effect` cần một môi trường khác — đó chính là thứ mà một chủ sở hữu
staging phải cung cấp.

**Bộ công cụ nghiệm thu hiện chưa được đưa vào lịch sử phiên bản.** Tại HEAD
(`7bd85e77`), bốn đường sau **chưa được git theo dõi** (kiểm bằng
`git ls-files --error-unmatch`, cả bốn đều báo không khớp):
`scripts/ops/run_pilot_acceptance.py`, `artifacts/pilot-acceptance.json`,
`artifacts/pilot-countersignature.json`, `docs/runbooks/proof-first-pilot-acceptance.md`.
Nghĩa là bộ chứng cứ phát hành đang sống ngoài lịch sử phiên bản — ai đó clone repo sẽ
không có nó.

**Cổng đang NO_GO, và đó là kết quả đúng.** Ảnh chụp Task 14
(`docs/audit-toan-du-an-2026-08.md:837`) ghi verdict **NO_GO** ở `:842`, liệt từng lớp
bằng chứng còn thiếu (PostgreSQL, tranh chấp đa tiến trình, browser, retry
provider/object) và ghi rõ ở `:843` rằng đây là ảnh chụp cục bộ có thời hạn 24 giờ,
**không phải** một tuyên bố mở công khai.

**Ràng buộc ngân sách.** `CLAUDE.md` §B8: không thêm dịch vụ trả phí, mặc định free-tier;
mọi khoản chi mới cần chủ dự án. `docs/QUYET-DINH-DANG-CHO.md` mục C4 đã có sẵn câu hỏi
"có VPS thứ hai không" và ghi rõ đó là chi tiêu mới thuộc §B8.

**Chưa kiểm được:** repo không nói prod thật đang chạy systemd hay docker-compose —
`docs/QUYET-DINH-DANG-CHO.md` mục B5 đang treo đúng câu hỏi đó, và câu trả lời quyết định
hình dạng của mọi kịch bản rollout/rollback.

## 2. LỰA CHỌN

1. **Chỉ định chủ sở hữu phát hành + dựng staging thật.** Một người chịu trách nhiệm
   phát hành, có một máy chủ staging (VPS thứ hai hoặc host dùng-một-lần) để chạy
   rollout → smoke → rollback thật, và một lượt restore drill từ artifact mới. Đóng được
   cả F-13, F-14, F-15.
2. **Chỉ định chủ sở hữu phát hành, chưa dựng staging.** Có người và có quy trình viết
   ra; ba lớp bằng chứng `multi_process` / `browser` / `external_side_effect` vẫn thiếu,
   cổng vẫn NO_GO, nhưng ít nhất có ai đó chịu trách nhiệm cho việc thiếu đó.
3. **Thuê host staging dùng-một-lần chỉ trong cửa sổ pilot.** Bật lên, chạy đủ ma trận,
   thu bằng chứng, tắt đi. Chi phí có giới hạn và biết trước.
4. **Tuyên bố dự án không có staging.** Ghi thành văn bản rằng F-15 ở lại mở, cổng ở lại
   NO_GO, và pilot không mở cho người thật. Đây là một quyết định hợp lệ, miễn là nó được
   ghi ra thay vì để trôi.

## 3. ĐÁNH ĐỔI

- **(1)** là đường duy nhất đóng được cả ba finding và ba lớp bằng chứng còn thiếu. Đổi
  lại: một VPS thứ hai là chi phí thường xuyên, chạm thẳng `CLAUDE.md` §B8, và
  `docs/QUYET-DINH-DANG-CHO.md` mục C4 đã ghi khuyến nghị "VPS 1GB không chứa 2 stack".
  Ngoài ra staging chỉ có giá trị nếu nó **giống prod** — mà hình dạng prod chính là câu
  hỏi B5 đang treo.
- **(2)** rẻ nhất trong ba đường có hành động, và nó đóng đúng phần
  `docs/audit-toan-du-an-2026-08.md:834` phàn nàn (thiếu người, thiếu escalation). Đổi
  lại: một chủ sở hữu không có staging thì không phát hành được gì — chức danh mà không
  có công cụ dễ trở thành chức danh trên giấy.
- **(3)** giới hạn được chi phí và vẫn cho ra bằng chứng thật. Đổi lại: bằng chứng
  dùng-một-lần hết hạn cùng cái host — lần phát hành sau phải dựng lại từ đầu, và
  `config/release-authority.json:19` đặt `max_age_hours: 24` nên bằng chứng vốn đã có
  thời hạn ngắn.
- **(4)** trung thực và không tốn gì. Đổi lại: mọi công việc kỹ thuật của pilot đứng yên
  vô thời hạn, và ba finding F-13/F-14/F-15 ở lại mở trong khi vẫn có một đường deploy
  chạy được — tức vẫn có khả năng ai đó deploy tay mà không qua cổng nào.

## 4. AI CHỊU ẢNH HƯỞNG

- **Dữ liệu prod**: F-13 (`docs/audit-toan-du-an-2026-08.md:236`) nói backup có thể xanh
  mà artifact không restore được. Đây là rủi ro mất dữ liệu không tái tạo được, đúng thứ
  `CLAUDE.md` §B1 gọi là tài sản không tái tạo.
- **Thời gian phát hiện sự cố**: F-14 (`:237`) — không có alert receiver thật thì sự cố
  được phát hiện bằng cách có người tình cờ nhìn vào.
- **Chủ dự án**: chi phí VPS thứ hai (`CLAUDE.md` §B8) và quyết định deploy prod
  (`CLAUDE.md` §4).
- **Toàn bộ cổng nghiệm thu pilot**: ba trong năm lớp bằng chứng ở
  `config/release-authority.json:18` không thu được nếu không có môi trường.

## 5. NẾU KHÔNG QUYẾT

Cổng ở lại NO_GO — đúng. Nhưng hai thứ xấu đi theo thời gian mà không phát ra tiếng động
nào. Thứ nhất: bộ công cụ nghiệm thu vẫn nằm ngoài git (bốn đường liệt ở §1), nên nó có
thể biến mất khỏi máy mà không ai biết, và không ai ngoài máy này tái lập được kết quả.
Thứ hai: `.github/workflows/deploy.yml` để backup và health check ở `continue-on-error`
(`docs/audit-toan-du-an-2026-08.md:238`) — một cổng luôn xanh là một cổng không ai còn
nhìn, đúng lớp lỗi mà `docs/QUYET-DINH-DANG-CHO.md` mục A1 đã mô tả cho một job đỏ quen
mắt.

## 6. BẰNG CHỨNG PHẢI KÈM KHI KÝ

1. Tên người chịu trách nhiệm phát hành và quan hệ của người đó với `QD-01` (cùng người
   hay hai người khác nhau — nếu khác thì đây cũng là hai vai trò `owner` và
   `countersign` ở `config/release-authority.json:27,29`).
2. Câu trả lời cho mục B5 của `docs/QUYET-DINH-DANG-CHO.md`: prod chạy systemd trên host
   hay docker-compose. Không có nó thì kịch bản rollback không viết đúng được.
3. Một lượt restore drill thật: backup → kiểm tính toàn vẹn → offsite → restore vào DB
   rỗng → đối chiếu số dòng/checksum, trên **một artifact mới**, đóng F-13.
4. Một alert rule bắn thật vào một notifier thật, kèm tên người nhận, đóng F-14.
5. Một lượt rollout → smoke → rollback trên staging, kèm URL bằng chứng, đóng F-15; và
   bỏ `continue-on-error` khỏi các bước đã trở thành cổng bắt buộc.
6. Bốn đường công cụ nghiệm thu ở §1 được đưa vào git (hoặc một quyết định ghi rõ vì sao
   chúng ở ngoài) — **việc đưa vào git cần chỉ đạo của chủ dự án**, máy không tự thêm.
7. Mục `release_owner` trong `config/decision-records.json` được cập nhật cùng lúc, kèm
   `record_sha256` băm từ chính file này tại thời điểm ký.

## 7. CHỐT CỦA CHỦ DỰ ÁN

Trạng thái: CHƯA KÝ

| Trường | Giá trị (chỉ chủ dự án điền) |
|---|---|
| decision_key | |
| chosen_option | |
| signed_by | |
| signed_at | |
| signature | |

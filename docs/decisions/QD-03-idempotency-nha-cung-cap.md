> STATUS: active
Authority: config/release-authority.json

# QD-03 — Idempotency nhà cung cấp SMS, hay chấp nhận rủi ro at-least-once (`provider`)

> **Hồ sơ này CHƯA KÝ.** Máy **không được** điền §7. Đợt rà soát đòi *"provider-side
> idempotency hoặc risk acceptance **được ký**"* — một agent điền chữ ký vào đó là tạo ra
> một bản chấp nhận rủi ro mà không có ai thật sự chấp nhận rủi ro.

`decision_key`: `provider` · Finding gốc: F-53 (`docs/audit-toan-du-an-2026-08.md:250`)

---

## 1. BỐI CẢNH

**Mã nguồn tự khai đúng vấn đề, không giấu.**

`agent/cases/outbox.py:90-99` — hàm `delivery_key()` có docstring nói thẳng:

- nó **cố ý không được gọi là** idempotency token, vì payload eSMS **không có trường nào
  mang được token đó**, nên phía nhà cung cấp không khử trùng lặp giúp;
- "at-most-once" vì thế phải đến từ chính module này: ghi nhận (commit) từng kết quả
  trước khi đi tiếp.

`agent/sms_provider.py:134-136` lặp lại cùng sự thật ở tầng transport: delivery key được
**ghi log, không gửi đi**; nó chỉ dùng để truy vết một khiếu nại về ngược tới dòng đã gửi.

**Cửa sổ sự cố nằm ở đâu.**

- `agent/cases/outbox.py:213` — `result = _PROVIDER.send(contact, message, delivery_key=delivery_key(outbox_id))`.
- `agent/cases/outbox.py:194` — `conn.commit()` nằm trong `settle()`, tức **sau** lời gọi
  gửi.
- `agent/cases/outbox.py:20` — `LEASE_SECONDS = 900`. Lease hết hạn thì dòng đó được nhận
  lại và gửi lại.
- Docstring `_deliver_one` (`agent/cases/outbox.py:180-186`) giải thích vì sao commit nằm
  *trong* vòng lặp: một transaction bao cả lô sẽ cuộn lại cả những tin **đã gửi thật**,
  và lượt chạy sau sẽ gửi lại chúng.

Ghép lại: thiết kế đã chặn trùng lặp **giữa các worker đang sống** (commit lease trước
khi gửi), nhưng sập máy **sau** `send()` và **trước** `commit()` để lại một tin đã rời hệ
thống mà bảng không biết — lease hết hạn, tin gửi lần hai. Đây đúng là kết luận của F-53
(`docs/audit-toan-du-an-2026-08.md:250`), trạng thái ghi **Verified residual risk**.

**Tầng transport có retry riêng.** `agent/sms_provider.py:25` đặt `MAX_RETRIES = 3`, vòng
lặp ở `:147-162` với `backoff_seconds()`. Vòng này chỉ lặp lại khi `outcome.delivered` là
sai — nhưng "không nhận được phản hồi thành công" và "nhà cung cấp không nhận tin" là hai
việc khác nhau, và không có gì trong payload để phân biệt. *(Đây là suy luận từ mã, chưa
đo bằng một lượt chạy thật đối với eSMS — không có bằng chứng nhà cung cấp cho ca này.)*

**Một nhánh đã được xử lý đúng, đừng nhầm nó với vấn đề này.**
`agent/sms_provider.py:125-129`: thiếu khoá ở môi trường production thì **từ chối gửi**
(`provider_unconfigured`) chứ không giả vờ thành công — vì giả vờ sẽ settle outbox thành
"sent" trong khi người báo chờ một tin không bao giờ rời khỏi hệ thống.

**Điểm cuối là bên thứ ba.** `agent/sms_provider.py:23` ghim endpoint
`https://rest.esms.vn/...`. `config/release-authority.json:24` đặt
`"external_policy": "sandbox-only-no-provider-calls"`, nên không lượt nghiệm thu nào được
gọi thật vào đó.

**Điều kiện mở cổng.** `docs/audit-toan-du-an-2026-08.md:831` — trong 28 P1, *"F-53 phải
có provider-side idempotency hoặc risk acceptance được ký"*. `:879` nhắc lại: bật
idempotency nếu có; nếu không thì ghi risk acceptance cho at-least-once SMS **và metric
duplicate**.

**Chưa kiểm được:** repo không chứa tài liệu API của eSMS. Việc nhà cung cấp có hỗ trợ
tham số khử trùng lặp hay không **chưa xác định được từ trong repo** — phải hỏi nhà cung
cấp.

## 2. LỰA CHỌN

1. **Bật khử trùng lặp phía nhà cung cấp.** Hỏi eSMS xem có trường idempotency /
   client-reference / dedup-window không; nếu có thì đưa `delivery_key(outbox_id)` vào
   payload (`build_payload` trong `agent/sms_provider.py`), đổi docstring ở
   `agent/cases/outbox.py:90-99` cho khớp sự thật mới, và thêm test cửa sổ sập máy.
2. **Đổi nhà cung cấp** sang bên có idempotency key trong hợp đồng API. Giữ nguyên kiến
   trúc outbox; chỉ thay lớp `EsmsProvider`, vốn đã tách sẵn sau interface
   `SmsProvider` (`agent/sms_provider.py:174`).
3. **Biên nhận bền trước khi có tác dụng phụ.** Ghi ý định gửi + mã tin của nhà cung cấp
   vào DB **trước** khi settle, để lần chạy sau nhìn thấy dấu vết. Giảm cửa sổ nhưng
   **không đóng được** nếu nhà cung cấp không trả mã trong cùng lời gọi.
4. **Ký chấp nhận rủi ro at-least-once.** Giữ nguyên mã. Đổi câu chữ/UX để nói rõ một tin
   có thể tới hai lần, thêm metric đếm trùng lặp, và thêm test cửa sổ sập máy để con số
   đó không tụt xuống mà không ai biết.
5. **Tắt kênh SMS trong pilot.** Chỉ trả biên nhận tra cứu; không gửi tin nào. Rủi ro
   trùng lặp bằng 0 vì không có tác dụng phụ nào.

## 3. ĐÁNH ĐỔI

- **(1)** đóng đúng gốc và là đường duy nhất biến "at-least-once" thành "at-most-once"
  thật. Đổi lại: phụ thuộc câu trả lời của một bên ngoài dự án, và có thể câu trả lời là
  "không có". Cũng là đường duy nhất **không kiểm được trên máy này** — chính sách
  `sandbox-only-no-provider-calls` (`config/release-authority.json:24`) cấm gọi thật, nên
  bằng chứng phải đến từ môi trường khác.
- **(2)** giải quyết được kể cả khi eSMS trả lời "không". Đổi lại: đổi nhà cung cấp là
  đổi hợp đồng, đổi brandname, đổi giá — thuộc `CLAUDE.md` §B8 (chi phí) và §4 (chủ dự án
  quyết). Và một nhà cung cấp mới là một tập lỗi mới chưa ai đo.
- **(3)** làm được hoàn toàn trong repo, không phụ thuộc ai. Đổi lại nó **thu hẹp chứ
  không đóng** cửa sổ, và một biện pháp thu hẹp dễ bị đọc nhầm thành đã đóng — đúng loại
  nhầm mà F-53 đang cảnh báo. Nếu chọn (3) thì vẫn phải ký (4).
- **(4)** trung thực nhất với hiện trạng, rẻ nhất, và là đúng cái
  `docs/audit-toan-du-an-2026-08.md:831` cho phép. Đổi lại: người báo tin có thể nhận
  hai tin cho một hồ sơ, và mỗi tin trùng là tiền thật trả cho nhà cung cấp. Metric
  duplicate là bắt buộc, không phải tuỳ chọn — không có nó thì đây là chấp nhận rủi ro mà
  không đo rủi ro.
- **(5)** rủi ro bằng 0 và mở pilot được ngay. Đổi lại bỏ mất vòng khép của kênh đính
  chính: người báo tin không được báo lại kết quả, phải tự quay lại tra biên nhận.

## 4. AI CHỊU ẢNH HƯỞNG

- **Người báo tin qua kênh đính chính**: nhận tin trùng, hoặc (nếu chọn 5) không nhận
  tin nào.
- **Chủ dự án**: chi phí SMS trùng lặp, và niềm tin của người báo tin nếu hệ thống nhắn
  lặp mà không giải thích.
- **Đường vận hành `dispatch_case_outbox`** (`agent/cases/outbox.py:231`) và mọi topic
  thông báo đi qua nó.
- **Cổng nghiệm thu pilot**: F-53 là một trong 28 P1 phải đóng
  (`config/release-authority.json:33`).

## 5. NẾU KHÔNG QUYẾT

F-53 ở lại **Verified residual risk**, cổng ở lại NO_GO, và kênh SMS không mở được cho
người thật. Nguy hiểm hơn: hiện trạng "không ai gửi tin nào" khiến rủi ro trông như bằng
0, nên khoản này rất dễ bị coi là đã ổn. Nó chỉ ổn **vì cờ tính năng đang tắt**, không
phải vì mã đã đúng. Ngày ai đó bật cờ mà chưa qua hồ sơ này là ngày rủi ro chuyển thẳng
sang người dùng.

## 6. BẰNG CHỨNG PHẢI KÈM KHI KÝ

1. **Nếu chọn (1) hoặc (2):** trả lời bằng văn bản của nhà cung cấp về trường khử trùng
   lặp — tên trường, cửa sổ dedup, hành vi khi trùng. Không có văn bản thì không được coi
   là có idempotency.
2. **Nếu chọn (3) hoặc (4):** một test cửa sổ sập máy — mô phỏng tiến trình chết giữa
   `agent/cases/outbox.py:213` và `:194` — chứng minh hệ thống hành xử đúng như hồ sơ
   này mô tả, và một metric đếm tin trùng có tên cụ thể.
3. **Nếu chọn (4):** câu chữ/UX nói rõ với người báo tin rằng một thông báo có thể tới
   hai lần, kèm đường dẫn tới nơi câu chữ đó sống.
4. Bằng chứng lớp `external_side_effect` (`config/release-authority.json:18`) chạy trên
   môi trường cho phép — **không** trên máy này, vì `"external_policy": "sandbox-only-no-provider-calls"`
   (`:24`) cấm gọi nhà cung cấp.
5. Mục `provider` trong `config/decision-records.json` được cập nhật cùng lúc, kèm
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

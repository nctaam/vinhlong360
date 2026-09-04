> STATUS: active
Authority: config/release-authority.json

# QD-04 — Nơi lưu trữ dữ liệu (`residency`)

> **Hồ sơ này CHƯA KÝ.** Máy **không được** điền §7. Nơi lưu trữ là một tuyên bố pháp lý
> về hạ tầng thật, không phải một giá trị cấu hình đọc ra được từ mã — một agent điền §7
> ở đây là khai một sự thật hạ tầng mà nó không có cách nào kiểm chứng.

`decision_key`: `residency` · Finding gốc: F-16 (`docs/audit-toan-du-an-2026-08.md:239`)

---

## 1. BỐI CẢNH

**Backend lưu trữ được chọn theo biến môi trường, ba nhánh, ba giá trị vùng khác nhau.**
`agent/storage.py:51-64`:

| Điều kiện | `_BACKEND` | `_REGION` | Dòng |
|---|---|---|---|
| Có `R2_ACCESS_KEY_ID` + `R2_SECRET_ACCESS_KEY` | `"r2"` | `"auto"` | `:51-55` |
| Có `S3_ENDPOINT` + khoá S3 | `"s3"` | `S3_REGION` | `:56-60` |
| Không có gì | `"local"` | `""` | `:61-64` |

Giá trị đó đi thẳng vào client S3: `agent/storage.py:77` truyền `region_name=_REGION`.

**Nhánh mặc định trỏ ra ngoài Việt Nam.** `agent/storage.py:37` ghim endpoint mặc định là
một host `*.r2.cloudflarestorage.com`; `agent/storage.py:41` đặt base công khai mặc định
`https://cdn.vinhlong360.vn`. Chú thích ngay trên đó (`:36`) nói rõ ý đồ: các giá trị
không-bí-mật được nướng sẵn để prod chỉ cần đặt hai khoá `*_KEY` trong `.env`. Nghĩa là
**chỉ cần đặt hai khoá là hệ thống lặng lẽ chạy nhánh R2**.

**`"auto"` không phải một vị trí.** `agent/storage.py:54` đặt `_REGION = "auto"` cho R2.
Đợt rà soát nói thẳng ở `docs/audit-toan-du-an-2026-08.md:239` (F-16): *"R2 region `auto`
không tự chứng minh lưu trữ Việt Nam."* Trạng thái của dòng đó là **Decision required**,
chủ thể **Owner + legal/DPO**.

**`"hn"` cũng không phải một chứng minh.** `agent/storage.py:48` đặt mặc định
`S3_REGION = "hn"` cho nhánh S3 kế thừa. Đó là một nhãn vùng do nhà cung cấp đặt tên; nó
là **đầu vào** gửi cho nhà cung cấp, không phải **bằng chứng** dữ liệu nằm ở đâu.

**Sản phẩm tự khai là chưa quyết.** `web-nuxt/utils/legalContent.ts:65` — khoản
`residency` trong khối `decisionRequired`: nơi lưu trữ dữ liệu cần được kiểm theo hạ tầng
thực tế trước khi công bố. Khoản kế bên, `:66` `processors_subprocessors`, đòi danh sách
bên xử lý / bên xử lý phụ được phê duyệt và công bố theo hợp đồng — hai khoản này đi
cùng nhau: nếu media nằm trên hạ tầng của một bên thứ ba thì bên đó là một processor.

**Vì sao khoản này đắt nếu sai.** `docs/2026-08-22-cau-hoi-cho-luat-su.md` §4 xếp
"chuyển dữ liệu xuyên biên giới trái quy định" ở mức **tối đa 5% doanh thu năm trước** —
một dòng riêng, nặng hơn nhóm "vi phạm khác".

**Chưa kiểm được (ghi thẳng):** hạ tầng prod thật đang chạy nhánh nào **không xác định
được từ trong repo**. `agent/storage.py` chỉ khai luật chọn nhánh; giá trị biến môi
trường trên máy chủ thật thì chỉ chủ dự án biết. Đây cùng lớp với khoản B5 của
`docs/QUYET-DINH-DANG-CHO.md` (prod chạy systemd hay docker-compose — chỉ chủ dự án biết).

## 2. LỰA CHỌN

1. **Giữ Cloudflare R2, lấy tuyên bố bằng văn bản.** Xin nhà cung cấp xác nhận vùng lưu
   trữ thật (và điều kiện để ghim vùng, nếu có), cộng danh sách bên xử lý phụ; công bố
   theo đúng khoản `processors_subprocessors` ở `web-nuxt/utils/legalContent.ts:66`, kèm
   căn cứ pháp lý cho việc chuyển dữ liệu ra ngoài lãnh thổ nếu vùng nằm ngoài Việt Nam.
2. **Chuyển media sang nhà cung cấp ghim được vùng Việt Nam trong hợp đồng.** Nhánh
   `"s3"` (`agent/storage.py:56-60`) đã tồn tại và nhận `S3_REGION` tường minh, nên đây
   là đổi cấu hình chứ không phải đổi kiến trúc.
3. **Chỉ dùng backend `local` trong suốt pilot.** `agent/storage.py:61-64` đã có sẵn
   nhánh này (`_PUBLIC_BASE = "/media"`); media nằm trên chính máy chủ, không có bên thứ
   ba nào trong đường lưu trữ.
4. **Chưa quyết, và chặn cứng.** Đặt điều kiện: hệ thống từ chối khởi động nếu
   `_BACKEND` không phải `"local"` mà chưa có hồ sơ này được ký. Biến việc quên thành một
   sự cố nhìn thấy được thay vì một mặc định im lặng.

## 3. ĐÁNH ĐỔI

- **(1)** rẻ nhất về kỹ thuật — không đụng một dòng mã nào. Đổi lại: phụ thuộc vào việc
  nhà cung cấp có chịu ra văn bản không, và nếu câu trả lời là "dữ liệu có thể nằm ở
  nhiều vùng" thì `"auto"` (`agent/storage.py:54`) chính là mô tả trung thực của một
  trạng thái không công bố được. Khi đó (1) tự chuyển thành (2).
- **(2)** cho ra một câu trả lời viết được vào chính sách mà không phải rào đón. Đổi lại:
  di trú media, đổi base URL công khai, và có thể phát sinh chi phí — `CLAUDE.md` §B8.
  Ngoài ra `S3_REGION` là nhãn của nhà cung cấp; ghim nhãn không thay được điều khoản hợp
  đồng, nên (2) vẫn cần phần văn bản của (1).
- **(3)** đơn giản nhất và không có bên thứ ba nào để công bố. Đổi lại: mất CDN, mất
  `https://cdn.vinhlong360.vn` (`agent/storage.py:41`), media phục vụ trực tiếp từ VPS —
  và bài toán sao lưu media đổ về chính máy chủ đó, tức chạm F-13
  (`docs/audit-toan-du-an-2026-08.md:236`, backup/restore chưa cùng định dạng).
- **(4)** không giải quyết gì nhưng ngăn được lớp lỗi nguy nhất ở khoản này: hai khoá
  `*_KEY` được đặt cho tiện, hệ thống lặng lẽ chuyển sang R2, và không ai biết mình vừa
  chọn một nơi lưu trữ. Đổi lại: thêm một cổng fail-closed, và fail-closed đặt sai chỗ
  thì làm chết dịch vụ lúc deploy.

## 4. AI CHỊU ẢNH HƯỞNG

- **Người gửi ảnh/chứng cứ kèm hồ sơ đính chính**: dữ liệu của họ nằm ở đâu là một câu
  hỏi họ có quyền được trả lời, và chính sách hiện chưa trả lời được
  (`web-nuxt/utils/legalContent.ts:65`).
- **Chủ dự án**: mức chế tài chuyển dữ liệu xuyên biên giới ở
  `docs/2026-08-22-cau-hoi-cho-luat-su.md` §4 tính theo phần trăm doanh thu.
- **Trang chính sách bảo mật**: không công bố được nơi lưu trữ và danh sách bên xử lý cho
  tới khi có hồ sơ này.
- **F-16** (`docs/audit-toan-du-an-2026-08.md:239`) — một trong 28 P1 ở
  `config/release-authority.json:33`.

## 5. NẾU KHÔNG QUYẾT

`residency` ở lại trong `decision_required_items` (`config/release-authority.json:23`),
cổng ở lại NO_GO. Nhưng rủi ro thật không nằm ở cổng: nó nằm ở
`agent/storage.py:36` — thiết kế "chỉ cần hai khoá là chạy" khiến một lần đặt biến môi
trường cho tiện là đã chọn xong nơi lưu trữ, không có bước nào hỏi lại, không có dòng log
nào nói "bạn vừa chọn R2". Mìn đó nằm im cho tới lần deploy đầu tiên có media thật.

## 6. BẰNG CHỨNG PHẢI KÈM KHI KÝ

1. Nhánh backend mà prod thật đang chạy: `"r2"`, `"s3"` hay `"local"` — kèm cách biết
   (giá trị biến môi trường trên máy chủ), không suy từ mặc định trong mã.
2. Tuyên bố bằng văn bản của nhà cung cấp về vùng lưu trữ thật, nếu chọn (1) hoặc (2).
   `"auto"` (`agent/storage.py:54`) và `"hn"` (`:48`) **không được tính** là bằng chứng.
3. Danh sách bên xử lý / bên xử lý phụ được phê duyệt, theo đúng khoản
   `processors_subprocessors` (`web-nuxt/utils/legalContent.ts:66`).
4. Nếu vùng nằm ngoài Việt Nam: căn cứ pháp lý cho việc chuyển dữ liệu xuyên biên giới —
   phần này đi cùng `docs/decisions/QD-02-phap-ly-dpo.md`, không ký rời được.
5. Câu chữ sẽ thay thế `web-nuxt/utils/legalContent.ts:65` sau khi ký, và nơi câu chữ đó
   hiển thị cho người dùng.
6. Mục `residency` trong `config/decision-records.json` được cập nhật cùng lúc, kèm
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

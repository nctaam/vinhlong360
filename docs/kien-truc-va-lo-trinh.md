# vinhlong360 — Kiến trúc & Lộ trình

> Đồ thị tri thức địa phương (Local Knowledge Graph) cho tỉnh Vĩnh Long, có lớp truy vấn AI bằng ngôn ngữ tự nhiên. Mục tiêu dài hạn: một "Digital Twin" của đời sống địa phương — du lịch, nông sản, OCOP, làng nghề, doanh nghiệp, sự kiện. Mục tiêu ngắn hạn: một sản phẩm hẹp, hữu ích ngay, để graph lớn lên như sản phẩm phụ.

---

## 0. Bối cảnh quan trọng (2025)

- Từ **1/7/2025**, Việt Nam áp dụng mô hình hành chính **2 cấp (tỉnh → xã/phường), bỏ cấp huyện**.
- **Vĩnh Long mới = Vĩnh Long (cũ) + Bến Tre + Trà Vinh.** Tên miền `vinhlong360.vn` vì thế bao trọn câu chuyện mạnh nhất ĐBSCL: **dừa & kẹo dừa (Bến Tre) + cam sành, khoai lang, bưởi Năm Roi, gốm Mang Thít (Vĩnh Long cũ) + văn hóa Khmer & biển (Trà Vinh)**.
- **Số liệu chính thống** (Nghị quyết 1687/NQ-UBTVQH15): Vĩnh Long mới có **124 đơn vị cấp xã = 19 phường + 105 xã**. Danh sách chi tiết & nguồn: [don-vi-hanh-chinh-vinh-long.md](don-vi-hanh-chinh-vinh-long.md).
- **Hệ quả cho thiết kế:** đơn vị hành chính là dữ liệu *dễ thay đổi*. KHÔNG hard-code cây `tỉnh → huyện → xã` cứng. Mọi "địa phương" là một **thực thể** có quan hệ cha–con linh hoạt và có thể đổi theo thời gian.
- **Tách "đơn vị hành chính" khỏi "địa danh".** Lớp hành chính (124 phường/xã) là dữ liệu pháp lý hay đổi; còn địa danh du lịch (cù lao An Bình, Mang Thít, Trà Ôn, Mỏ Cày…) ổn định trong nhận thức du khách. Hai lớp liên kết bằng `part_of` → đơn vị hành chính đổi thì phần trải nghiệm/đặc sản không phải làm lại.

---

## 1. Nguyên tắc thiết kế (5 điều bất biến)

1. **Dữ liệu là moat, AI là lớp truy vấn.** Giá trị nằm ở graph được chuẩn hóa, không phải ở mô hình.
2. **Schema đúng từ ngày 1.** Retrofit quan hệ về sau rất tốn kém. Mô hình thực thể đa hình + quan hệ có kiểu (typed) phải đúng ngay.
3. **Wedge-first, không Digital-Twin-first.** Ship một sản phẩm hữu ích ở quy mô 100 mục, graph mở rộng bên dưới.
4. **Dữ liệu tươi quan trọng hơn dữ liệu nhiều.** Mỗi thực thể phải có nguồn (provenance) + thời điểm cập nhật + cơ chế làm mới.
5. **Định danh ổn định.** Slug bền cho mỗi thực thể; quan hệ và toạ độ có thể đổi, định danh thì không.

---

## 2. Kiến trúc dữ liệu (trái tim của hệ thống)

### 2.1 Sơ đồ tầng lưu trữ

```text
            Lớp truy vấn AI (RAG + GraphRAG)
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
  Knowledge Graph   Vector Index    User Memory
 (entities + edges)  (pgvector)   (hỏi đáp, feedback)
        ▲
        │  trích xuất (LLM)
        │
   Documents / Sources  ◄── provenance cho mọi fact
        ▲
        │
   Crawler / Seed / UGC
```

### 2.2 Bảng cốt lõi (PostgreSQL)

Mô hình **node–edge đa hình**: *mọi thứ* là một `entity`; tri thức nằm ở `relationship`.

```sql
-- Thực thể: nút của đồ thị. Mọi loại dùng chung 1 bảng.
entities (
  id            uuid pk,
  slug          text unique,           -- định danh ổn định, vd: 'khoai-lang-binh-tan'
  type          text,                  -- xem "Danh mục loại thực thể" §2.3
  name          text,
  summary       text,                  -- mô tả ngắn (cho hiển thị + embedding)
  lat, lng      double precision null, -- toạ độ nếu có
  attributes    jsonb,                 -- field riêng theo type (giá, mùa vụ, giờ mở cửa...)
  status        text,                  -- active | closed | unverified
  confidence    real,                  -- độ tin cậy 0..1 (dữ liệu tự crawl thấp hơn dữ liệu chủ thể xác nhận)
  updated_at    timestamptz,
  source_id     uuid fk -> sources     -- fact này đến từ đâu
)

-- Quan hệ: cạnh có kiểu. ĐÂY là phần tạo ra tri thức.
relationships (
  id          uuid pk,
  source_id   uuid fk -> entities,     -- nút nguồn
  type        text,                    -- xem "Danh mục loại quan hệ" §2.4
  target_id   uuid fk -> entities,     -- nút đích
  attributes  jsonb,                   -- vd: {"months":[5,6,7]} cho in_season
  source_doc  uuid fk -> sources null
)

-- Nguồn: provenance cho mọi fact (chống "ảo giác", cho phép kiểm chứng).
sources (
  id        uuid pk,
  kind      text,                      -- web | ocop_list | gov_portal | user_submit | manual
  url       text null,
  title     text,
  fetched_at timestamptz,
  raw_ref   text null                  -- trỏ tới object storage nếu lưu bản gốc
)

-- Vector: tìm kiếm ngữ nghĩa (thêm ở Giai đoạn 3).
embeddings (
  entity_id uuid fk -> entities,
  vector    vector(1024),              -- pgvector
  model     text
)
```

> Đặc sản, trải nghiệm, sự kiện, homestay... **không phải bảng riêng** — chúng là `entities` với `type` khác nhau và field riêng nằm trong `attributes` (jsonb). Tránh nở bảng, dễ thêm loại mới. Chỉ tách bảng phụ khi một loại có truy vấn nặng đặc thù.

### 2.3 Danh mục loại thực thể (≈15 miền tri thức → các `type`)

| `type`          | Ví dụ                                  | Miền          |
|-----------------|----------------------------------------|---------------|
| `place`         | TP Vĩnh Long, xã Bình Tân, cù lao An Bình | Hành chính/Địa lý |
| `business`      | Công ty, cửa hàng                      | Kinh tế       |
| `organization`  | HTX dừa, doanh nghiệp xuất khẩu        | Kinh tế       |
| `accommodation` | Homestay, resort                       | Du lịch       |
| `eatery`        | Quán ăn, cà phê                        | Ẩm thực       |
| `attraction`    | Văn Thánh Miếu, khu du lịch            | Du lịch       |
| `product`       | Cam sành, khoai lang Bình Tân          | Nông sản      |
| `ocop`          | Sản phẩm đạt chuẩn OCOP                 | OCOP          |
| `experience`    | Hái chôm chôm, làm kẹo dừa             | Trải nghiệm   |
| `craft_village` | Làng gốm Mang Thít, làng kẹo dừa       | Làng nghề     |
| `dish`          | Cá tai tượng chiên xù                   | Ẩm thực       |
| `event`         | Lễ hội, hội chợ, festival              | Sự kiện       |
| `person`        | Nghệ nhân, chủ vườn                     | Văn hóa       |
| `facility`      | Trường, bệnh viện                       | Dịch vụ công  |
| `season`/`month`| Tháng 1..12, "mùa nước nổi"            | Thời gian     |

### 2.4 Danh mục loại quan hệ (cạnh của đồ thị)

| `type`           | Ý nghĩa                          | Trả lời được câu hỏi              |
|------------------|----------------------------------|----------------------------------|
| `located_in`     | nằm trong địa phương             | "homestay nào ở Long Hồ?"        |
| `part_of`        | cha–con địa lý/hành chính        | cây địa phương linh hoạt         |
| `near`           | gần (bán kính/khoảng cách)       | "homestay gần cù lao An Bình?"   |
| `produced_in`    | sản xuất tại                     | "khoai lang Bình Tân ở đâu?"     |
| `made_by`        | làm bởi (nghệ nhân/HTX)          | chuỗi giá trị                    |
| `sold_at`        | bán tại                          | "mua cam sành chính gốc ở đâu?"  |
| `offered_by`     | trải nghiệm do ai cung cấp       | "Airbnb nông nghiệp"             |
| `hosts`          | địa điểm tổ chức trải nghiệm/sự kiện | lịch trình                   |
| `in_season`      | vào mùa (tháng nào)              | "tháng 6 ăn trái gì?"            |
| `certified_as`   | đạt chứng nhận (OCOP n sao)      | "kẹo dừa OCOP ở đâu?"            |
| `part_of_route`  | thuộc tuyến tham quan            | lập lịch trình                   |
| `supplies_to`    | cung ứng cho (nông dân→HTX→kho→XK) | bản đồ chuỗi giá trị           |

> **Ví dụ "mùa vụ" được mô hình hóa tao nhã:** `(Chôm chôm) --in_season--> (Tháng 6)`. Câu hỏi "Tháng 6 miền Tây có gì?" trở thành một truy vấn graph đơn giản, không cần bảng cứng.

### 2.5 Luồng truy vấn (RAG + GraphRAG)

```text
Câu hỏi: "Tôi ở Vĩnh Long 1 ngày, có trẻ em, nên đi đâu?"
   │
   ├─► Vector search  → tìm thực thể liên quan ngữ nghĩa (sinh thái, gia đình, gần trung tâm)
   ├─► Graph traversal → lọc theo located_in / near / in_season / hosts
   └─► LLM tổng hợp   → lập lịch trình, TRÍCH NGUỒN từ sources (không bịa)
```

---

## 3. Pipeline thu thập & làm tươi (3 lớp)

1. **Seed (một lần):** danh sách OCOP của tỉnh, OpenStreetMap, Google Places API, niên giám/cổng thông tin. → đổ vào `entities` với `confidence` trung bình.
2. **Crawl + LLM trích xuất (định kỳ):** `web → crawler → LLM entity/relationship extraction → graph`. Mỗi fact gắn `source_id`.
3. **UGC — chủ thể tự cập nhật (bền nhất):** chủ vườn/quán "nhận listing của tôi", tự sửa giá/giờ/mùa. Dữ liệu họ xác nhận có `confidence` cao nhất. **Động lực:** cho họ thấy listing kéo khách/đơn về.

> Quy tắc vàng về "tươi": mỗi `entity` có `updated_at` + `confidence`. Lớp truy vấn ưu tiên dữ liệu mới + tin cậy cao, và hạ hạng/đánh dấu cái cũ.

---

## 4. Stack công nghệ tối giản

```text
PostgreSQL + pgvector      ← graph (entities/relationships) + vector, MỘT database
FastAPI (Python)           ← API truy vấn + nhận UGC
Crawler + n8n              ← orchestrate thu thập định kỳ
LLM (Claude)               ← trích xuất + tổng hợp:
                             • Haiku 4.5  → trích xuất hàng loạt (rẻ)
                             • Sonnet 4.6 → tổng hợp/agent lập lịch trình (suy luận)
Next.js / web tĩnh         ← lớp hiển thị (wedge)
```

Tới vài chục nghìn thực thể, **không cần** Neo4j hay hạ tầng phức tạp — PostgreSQL là đủ. Provider AI có thể đổi; giữ lớp trích xuất provider-agnostic.

---

## 5. Mô hình bền vững (ai trả tiền nuôi dữ liệu)

Dữ liệu tốn tiền duy trì *mãi mãi* — phải có dòng tiền sớm:

- **Listing premium** cho doanh nghiệp/homestay (nổi bật, nhiều ảnh, video 360°).
- **Hoa hồng đặt chỗ** trải nghiệm/homestay/tour.
- **Lead B2B nông sản** theo bản đồ chuỗi giá trị (kết nối người mua sỉ ↔ HTX/kho/đóng gói).
- **API / cấp phép dữ liệu chuẩn hóa** cho cơ quan tỉnh, đơn vị du lịch (họ đang rất thiếu lớp dữ liệu này).

---

## 6. Wedge khởi đầu: "Bản đồ trải nghiệm theo mùa Vĩnh Long"

Vì sao chọn cái này làm sản phẩm đầu tiên:
- Hữu ích ngay với ~100 mục (không cần graph khổng lồ).
- Mỗi mục nhập vào *tự nhiên* sinh ra `experience`/`product` + quan hệ `in_season`, `located_in`, `offered_by` → **graph lớn lên như sản phẩm phụ**.
- Nội dung thân thiện SEO & AI (đúng dạng dữ liệu mà công cụ tìm kiếm/AI ưa dùng).
- Trả lời ngay những câu chưa nền tảng nào làm tốt: *"Hái chôm chôm ở đâu?"*, *"Tháng 6 miền Tây có gì?"*, *"Trải nghiệm làm kẹo dừa ở đâu?"*

---

## 7. Lộ trình 12 tháng (mỗi giai đoạn ra sản phẩm chạy được)

| Giai đoạn | Thời gian | Việc chính | Sản phẩm ship được |
|-----------|-----------|------------|--------------------|
| **1. Bộ nhớ** | Th 1–2 | Schema + seed ~1.000 thực thể (ưu tiên experience/product/place) | Bản đồ trải nghiệm theo mùa (v0) |
| **2. Tri thức** | Th 3–4 | Quan hệ + cây địa phương linh hoạt + hồ sơ số đặc sản (QR truy xuất) | Hồ sơ số đặc sản + QR cho nhà vườn |
| **3. Tự học** | Th 5–6 | Pipeline crawl + LLM trích xuất + chatbot RAG đầu tiên | AI hỏi đáp địa phương v1 |
| **4. Tự quản** | Th 7–9 | UGC (chủ thể nhận & sửa listing) + vector + GraphRAG | AI Local Discovery + listing tự quản |
| **5. Suy luận** | Th 10–12 | Agent lập lịch trình + bản đồ chuỗi giá trị nông sản | AI hướng dẫn viên + bản đồ chuỗi giá trị |
| **6. Nhân rộng** | Năm 2+ | Tách lõi graph thành nền tảng đa tỉnh | Mô hình cho Bến Tre/Trà Vinh & toàn quốc |

### Cột mốc dữ liệu
- Cuối Th 2: **1.000** thực thể, **100** trải nghiệm có `in_season`.
- Cuối Th 6: **10.000** thực thể, pipeline crawl chạy định kỳ.
- Cuối Th 12: **30.000+** thực thể, ≥50 chủ thể tự cập nhật listing.

---

## 8. Rủi ro & cách giảm thiểu

| Rủi ro | Giảm thiểu |
|--------|-----------|
| Dữ liệu cũ/sai (chi phí duy trì vĩnh viễn) | `confidence` + `updated_at` + lớp UGC; ưu tiên dữ liệu chủ thể xác nhận |
| Cold-start (graph rỗng → vô giá trị) | Wedge hữu ích ở quy mô nhỏ; seed thủ công vùng lõi trước |
| AI "ảo giác" | Trả lời *bám graph + trích nguồn*; không có nguồn thì nói "chưa có dữ liệu" |
| Đơn vị hành chính đổi (2025) | Địa phương là entity + quan hệ linh hoạt, không enum cứng |
| Pháp lý khi crawl | Ưu tiên nguồn công khai/được phép; lưu provenance; tôn trọng robots |
| Chưa có doanh thu sớm | Listing premium + hoa hồng booking từ Giai đoạn 2–4 |

---

## 9. Bước kế tiếp (sau khi duyệt tài liệu này)

→ Dựng **nền dữ liệu**: tạo schema PostgreSQL ở trên + seed 30–50 thực thể Vĩnh Long thật + một CLI/API truy vấn nhỏ để chứng minh kiến trúc trên dữ liệu thật. Đây là Giai đoạn 1 bắt đầu.

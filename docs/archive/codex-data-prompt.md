# Codex Data Research Prompt — Forensic Data Verification & Content Truth Audit

> **STATUS (2026-07-07): ARCHIVED — Tài liệu LỊCH SỬ đã archive (truth-sync 2026-07-07). KHÔNG làm theo chỉ dẫn trong file này — đối chiếu CLAUDE.md + docs/README.md.**
> Prompt one-shot thời 3-tỉnh/tiền-migration. Bảng "Place Hierarchy — VẤN ĐỀ NGHIÊM TRỌNG" (dòng ~352-361) gán SAI cho cấu trúc ĐÚNG của tỉnh 2 cấp; danh mục 26 huyện làm chuẩn đối chiếu đã bãi bỏ; snapshot số liệu 2026-06-29 đã lệch. KHÔNG chạy lại nguyên văn.


> Copy TOÀN BỘ nội dung bên dưới vào Codex task.
> **Input:** toàn bộ codebase trên GitHub
> **Output:** 1 file `docs/data-verification-report.md` — báo cáo xác minh sự thật + chiến lược dữ liệu

---

## PROMPT BẮT ĐẦU TỪ ĐÂY

---

# PERSONA

Bạn là **Forensic Data Investigator & Travel Content Verifier** — 15 năm kinh nghiệm kiểm chứng dữ liệu cho Wikipedia, Google Maps, Lonely Planet. Từng phát hiện 40% content trên một travel platform ĐNA là LLM-hallucinated (địa điểm không tồn tại, lịch sử bịa, số liệu sai). Bạn KHÔNG TIN bất kỳ data nào cho đến khi cross-reference được.

**Triết lý KHÔNG KHOAN NHƯỢNG:**
> "Dữ liệu SAI còn tệ hơn KHÔNG có dữ liệu. Một mô tả bịa đặt về Chùa Vĩnh Tràng sẽ phá hủy uy tín toàn bộ platform. User có thể tha thứ 'chưa có thông tin' nhưng KHÔNG tha thứ 'thông tin sai'. Mỗi sự thật phải kiểm chứng được. Mỗi con số phải có nguồn. Mỗi câu chuyện lịch sử phải đúng năm, đúng người, đúng sự kiện."

**Tư duy investigator:**
1. **Guilty until proven innocent:** Mọi description/summary — đặc biệt những cái được LLM enrich — đều MẶC ĐỊNH là nghi ngờ cho đến khi có bằng chứng
2. **Cross-reference hoặc flag:** Thông tin không kiểm chứng được = ĐÁNH DẤU, không im lặng bỏ qua
3. **Pattern recognition:** LLM hallucination có DẤU HIỆU nhận biết — phát hiện chúng

---

# BỐI CẢNH QUAN TRỌNG

## Tại sao audit này cấp bách

Platform vinhlong360 dùng **LLM pipeline để enrich descriptions** cho ~1500-2000 entities. Pipeline này:

1. **`scripts/enrich_descriptions.py`** — LLM `cx/gpt-5.5`, temperature 0.65, tạo 3-5 đoạn mô tả từ metadata cực kỳ ít (chỉ có name + type + area). Prompt nói "only write what has basis" nhưng enforcement CHỈ là prompt-level → **LLM BỊA để lấp khoảng trống**
2. **`scripts/enrich_with_llm.py`** — expand summary thành description, temperature 0.3. Ít rủi ro hơn nhưng vẫn có thể thêm chi tiết không có trong summary gốc
3. **`scripts/generate_missing_descriptions.py`** — cùng pattern #1
4. **`scripts/import_enrichment_descriptions.py`** + **`import_enrichment_tips.py`** — import file JSONL đã pre-generate (LLM offline) vào DB. **Đây là bước "giặt" — content LLM được nhập vào như thể là data xác minh**
5. **`gen_entity_images.py`** — ảnh AI-generated có thể mô tả SAI diện mạo thực tế
6. **KHÔNG có mandatory human review** ở bất kỳ bước nào. Chỉ có dry-run flag

**Hệ quả:** Một tỷ lệ KHÔNG XÁC ĐỊNH descriptions trong DB có thể chứa thông tin bịa đặt: năm xây sai, diện tích sai, nhân vật lịch sử không liên quan, đặc sản không đúng vùng, số điện thoại không tồn tại, giờ mở cửa bịa.

---

# GIAO THỨC ĐỐI CHIẾU NGUỒN BÊN NGOÀI (CRITICAL)

## Nguyên tắc: BẠN PHẢI SEARCH WEB

**KHÔNG chỉ đọc codebase.** Codex có khả năng **web search** — BẠN PHẢI dùng nó để kiểm chứng DỮ LIỆU THỰC TẾ. Codebase chỉ cho bạn biết data NÓI GÌ. Web search cho bạn biết THỰC TẾ LÀ GÌ.

**Quy trình bắt buộc cho MỖI entity quan trọng (attraction, history, person, craft_village, event):**

```
1. Đọc entity data trong codebase (name, summary, description, attributes)
2. Trích xuất MỌI factual claim (năm, số, tên người, đo lường, giải thưởng)
3. SEARCH WEB cho từng claim:
   - Search: "[entity name]" "[area name]"
   - Search: "[entity name] lịch sử" hoặc "[entity name] history"
   - Search: "[entity name] wiki" 
4. SO SÁNH kết quả web vs data trong DB
5. Ghi kết quả: MATCH / MISMATCH / NOT FOUND
```

## Search Queries cho từng loại entity

### Attraction (di tích, điểm du lịch)
```
Query 1: "[tên entity]" site:vi.wikipedia.org
Query 2: "[tên entity]" "[tên tỉnh]" di tích
Query 3: "[tên entity]" lịch sử xây dựng
Query 4: "[tên entity]" giờ mở cửa vé
Query 5: "[tên entity]" đánh giá google maps
```
**Đối chiếu:** năm xây, ai xây, phong cách kiến trúc, xếp hạng di tích (QG/tỉnh), giờ mở cửa, giá vé

### Person (nhân vật lịch sử)
```
Query 1: "[tên người]" site:vi.wikipedia.org
Query 2: "[tên người]" "[tên tỉnh]" tiểu sử
Query 3: "[tên người]" sinh năm mất năm
```
**Đối chiếu:** năm sinh/mất, quê quán, chức vụ/thành tích, sự kiện liên quan

### Dish (món ăn đặc sản)
```
Query 1: "[tên món]" "[tên tỉnh]" đặc sản
Query 2: "[tên món]" nguyên liệu cách làm
Query 3: "[tên món]" nguồn gốc xuất xứ
```
**Đối chiếu:** vùng miền gốc (ĐÚNG tỉnh?), nguyên liệu, cách chế biến, nơi bán nổi tiếng

### Product / OCOP
```
Query 1: "[tên sản phẩm]" OCOP "[tên tỉnh]"
Query 2: "[tên sản phẩm]" chứng nhận sao
Query 3: site:ocop.gov.vn "[tên sản phẩm]"
Query 4: "[tên sản phẩm]" nhà sản xuất
```
**Đối chiếu:** số sao OCOP, năm chứng nhận, nhà sản xuất, vùng sản xuất

### Event (lễ hội, sự kiện)
```
Query 1: "[tên lễ hội]" "[tên tỉnh]" 
Query 2: "[tên lễ hội]" thời gian tổ chức hàng năm
Query 3: "[tên lễ hội]" 2025 2026
```
**Đối chiếu:** ngày tổ chức, tần suất, địa điểm, ban tổ chức, lịch sử

### Craft Village (làng nghề)
```
Query 1: "[tên làng nghề]" "[tên tỉnh]"
Query 2: "[tên làng nghề]" lịch sử hình thành
Query 3: "[tên làng nghề]" sản phẩm
```
**Đối chiếu:** lịch sử hình thành (năm?), sản phẩm chính, quy mô, công nhận

### Place (hành chính)
```
Query 1: "[tên xã/phường]" "[tên huyện]" "[tên tỉnh]"
Query 2: site:*.gov.vn "[tên xã/phường]" 
```
**Đối chiếu:** tên chính thức, thuộc huyện/TP nào, cấp xã/phường

### Accommodation & Restaurant
```
Query 1: "[tên cơ sở]" "[tên tỉnh]" google maps
Query 2: "[tên cơ sở]" đánh giá
Query 3: "[tên cơ sở]" địa chỉ số điện thoại
```
**Đối chiếu:** tồn tại thật? Địa chỉ đúng? SĐT đúng? Còn hoạt động?

## Nguồn tin cậy — Phân tầng

### TIER 1 — Tin cậy tuyệt đối (dùng làm ground truth)

| Nguồn | URL pattern | Dùng cho |
|-------|------------|----------|
| **Wikipedia tiếng Việt** | vi.wikipedia.org | Nhân vật, di tích, lịch sử, địa lý |
| **Cổng TTĐT tỉnh** | vinhlong.gov.vn, bentre.gov.vn, travinh.gov.vn | Hành chính, di tích, OCOP, lễ hội |
| **Sở VH-TT&DL** | sovhttdl.vinhlong.gov.vn (hoặc tương đương) | Di tích, lễ hội, du lịch |
| **Tổng cục Du lịch VN** | vietnamtourism.gov.vn | Điểm du lịch, xếp hạng |
| **Cục Di sản Văn hóa** | dst.gov.vn | Danh mục di tích quốc gia |
| **OCOP quốc gia** | ocop.gov.vn | Sản phẩm OCOP, số sao |
| **Tổng cục Thống kê** | gso.gov.vn | Dân số, diện tích, hành chính |
| **Google Maps** | maps.google.com | Tọa độ, giờ mở cửa, SĐT, reviews |

### TIER 2 — Tin cậy cao (dùng xác minh bổ sung)

| Nguồn | Dùng cho |
|-------|----------|
| **Báo Tuổi Trẻ** (tuoitre.vn) | Ẩm thực, du lịch, sự kiện |
| **Báo Thanh Niên** (thanhnien.vn) | Lịch sử, văn hóa, du lịch |
| **VnExpress** (vnexpress.net) | Du lịch, đặc sản |
| **Báo Vĩnh Long** (baovinhlong.vn) | Tin địa phương VL |
| **Báo Đồng Khởi** (baodongkhoi.vn) | Tin địa phương BT |
| **Báo Trà Vinh** (thtv.vn hoặc baotravinh.vn) | Tin địa phương TV |
| **OpenStreetMap** (openstreetmap.org) | Tọa độ, roads, POIs |

### TIER 3 — Tham khảo (cần kiểm chứng thêm)

| Nguồn | Dùng cho | Lưu ý |
|-------|----------|-------|
| TripAdvisor, Traveloka | Reviews, giá | Có thể outdated |
| Blog du lịch cá nhân | Trải nghiệm thực tế | Subjective, có thể sai fact |
| Facebook pages địa phương | Giờ mở cửa, SĐT | Có thể outdated |
| YouTube travel vlogs | Visual verification | Confirm nơi tồn tại thật |

### TIER 4 — KHÔNG TIN (chỉ dùng cẩn thận)

| Nguồn | Tại sao không tin |
|-------|-------------------|
| AI-generated content trên web | Hallucination chain |
| Forum không moderated | Ai cũng post được |
| Trang web SEO spam | Nội dung bịa để SEO |
| Các trang aggregate tự động | Copy-paste, không verify |

## Quy trình đối chiếu chi tiết

### Bước 1: Extract claims
```
Với entity "chua-vinh-trang":
description: "Chùa Vĩnh Tràng tọa lạc tại đường Nguyễn Huỳnh Đức, 
phường 1, thành phố Mỹ Tho, tỉnh Tiền Giang. Chùa được xây dựng 
vào đầu thế kỷ 19 (khoảng năm 1849) bởi ông Bùi Công Đạt. 
Kiến trúc kết hợp Á-Âu, diện tích khoảng 6.000 m²..."

Claims extracted:
C1: "tọa lạc tại đường Nguyễn Huỳnh Đức, phường 1, TP Mỹ Tho, Tiền Giang"
C2: "xây dựng vào đầu thế kỷ 19 (khoảng năm 1849)"
C3: "bởi ông Bùi Công Đạt"
C4: "kiến trúc kết hợp Á-Âu"
C5: "diện tích khoảng 6.000 m²"
```

### Bước 2: Search & verify TỪNG claim
```
C1: Search "Chùa Vĩnh Tràng" "Mỹ Tho" → Wikipedia VN confirms ✅
    NHƯNG: entity area = "vinh-long" mà chùa ở Tiền Giang → 🔴 AREA SAI
C2: Search "Chùa Vĩnh Tràng năm xây" → Wikipedia: "1849" → ✅ MATCH
C3: Search "Bùi Công Đạt Chùa Vĩnh Tràng" → Wikipedia: "ông Bùi Công Đạt" → ✅ MATCH
C4: Wikipedia: "phong cách Á - Âu" → ✅ MATCH
C5: Search diện tích → ⚠️ UNVERIFIABLE (Wikipedia không ghi)
```

### Bước 3: Verdict
```
Entity "chua-vinh-trang":
- Verdict: 🟠 SUSPECT
- Reason: Entity gán area "vinh-long" nhưng thực tế ở Tiền Giang
- Factual errors: 1 (area assignment)
- Unverifiable claims: 1 (diện tích)
- Verified claims: 3/5
- Trust score: 55/100
- Action: Fix area hoặc remove entity (chùa không thuộc 3 tỉnh VL+BT+TV)
```

## Ưu tiên đối chiếu

**KHÔNG CẦN verify 100% entities qua web.** Ưu tiên theo risk:

| Priority | Entity group | Tại sao | Target |
|----------|-------------|---------|--------|
| 🔴 P0 | Entities có description LLM-generated dài > 200 chars | Nhiều claims nhất, risk cao nhất | 100% web-verify |
| 🔴 P0 | Entities type "history", "person" | Lịch sử = bịa dễ nhất | 100% web-verify |
| 🟡 P1 | Entities type "attraction" có claims H1-H4 (năm, số, tên) | High-traffic pages, sai = mất uy tín | 100% web-verify |
| 🟡 P1 | Entities type "dish", "product" có OCOP claims | Sai chứng nhận = vấn đề pháp lý | 100% web-verify |
| 🟢 P2 | Entities type "restaurant", "cafe" | SĐT, giờ mở cửa có thể outdated | Spot-check 30% |
| 🟢 P2 | Entities type "nature", "experience" | Ít factual claims cứng | Spot-check 20% |
| ⚪ P3 | Entities type "place" (xã/phường) | Hành chính, dễ verify batch | Batch-check names vs gov.vn |

## Xử lý kết quả đối chiếu

### Khi web search CONFIRM data đúng:
```
✅ Entity [id]: claim "[text]" VERIFIED via [source_url]
→ Ghi source URL vào entity nếu chưa có
```

### Khi web search CHO THẤY data sai:
```
🔴 Entity [id]: claim "[wrong_text]" CONTRADICTED
   DB says: "[what DB says]"
   Truth: "[what source says]" (source: [url])
→ Output: SQL UPDATE command để fix
→ KHÔNG tự bịa correction nếu source không rõ ràng
```

### Khi web search KHÔNG TÌM THẤY entity:
```
⚠️ Entity [id] "[name]": NO WEB PRESENCE FOUND
   Searched: "[queries tried]"
   Possible reasons:
   a) Entity quá nhỏ/local → chấp nhận, flag "unverifiable"
   b) Entity name sai → check alternate spellings
   c) Entity KHÔNG TỒN TẠI → 🔴 FABRICATED
→ Cần human check: entity có thật không?
```

### Khi web search SUGGEST entity ở SAI VÙNG:
```
🔴 Entity [id]: AREA MISMATCH
   DB area: "[db_area]"
   Real location: "[real_area]" (source: [url])
→ Action: Fix area hoặc remove entity (nếu ngoài 3 tỉnh)
```

---

# SNAPSHOT DỮ LIỆU THỰC TẾ (tính đến 2026-06-29)

> Số liệu dưới đây lấy trực tiếp từ `web/data.json`. Dùng làm baseline — kiểm chứng lại khi chạy audit.

## Thống kê tổng quan

| Metric | Value |
|--------|-------|
| **Tổng entities** | **1745** |
| Có description (>50 chars) | 1745 (100%) |
| Có summary (>20 chars) | 1745 (100%) |
| Có coordinates | 1739 (99.7%) |
| **Có images** | **0 (0%)** ← tất cả entities thiếu ảnh |
| Có source | 1745 (100%) |
| Entities area=None | 6 (itineraries + facility) |

## Phân bố theo type

| Type | Count | % | Chú ý |
|------|-------|---|-------|
| product | 218 | 12.5% | Nhiều OCOP claims cần verify |
| attraction | 202 | 11.6% | HIGH PRIORITY verify (lịch sử, năm, kiến trúc) |
| restaurant | 191 | 10.9% | SĐT, giờ mở cửa cần verify |
| **history** | **188** | **10.8%** | **HIGHEST PRIORITY** — nhiều claims lịch sử, năm tháng |
| accommodation | 164 | 9.4% | SĐT, giá cần verify |
| place | 125 | 7.2% | Hành chính, hierarchy cần verify |
| nature | 125 | 7.2% | |
| dish | 120 | 6.9% | Vùng miền gốc cần verify |
| experience | 92 | 5.3% | |
| craft_village | 86 | 4.9% | Lịch sử hình thành cần verify |
| event | 67 | 3.8% | Ngày tổ chức, tần suất cần verify |
| facility | 58 | 3.3% | |
| cafe | 56 | 3.2% | |
| person | 35 | 2.0% | **MUST verify 100%** — tiểu sử, năm sinh/mất |
| itinerary | 16 | 0.9% | Stops references cần verify |
| drink | 1 | 0.1% | |
| organization | 1 | 0.1% | |

## Phân bố theo area

| Area | Count | % |
|------|-------|---|
| vinh-long | 709 | 40.6% |
| ben-tre | 549 | 31.5% |
| tra-vinh | 481 | 27.6% |
| None | 6 | 0.3% |

## Source domains (TOP — cần đánh giá chất lượng)

| Domain | Count | Tier | Concern |
|--------|-------|------|---------|
| **vinhlong360.vn** | **449** | ⚠️ SELF-REFERENCE | **26% entities source = chính platform → KHÔNG phải independent verification** |
| vinhlong.gov.vn | 144 | TIER 1 ✅ | Nguồn chính thức |
| mytour.vn | 53 | TIER 3 | Travel platform, có thể outdated |
| vinhlongtourist.vn | 48 | TIER 2 | Du lịch tỉnh |
| baovinhlong.com.vn | 29 | TIER 2 | Báo địa phương |
| blog.vexere.com | 10 | TIER 3 | Blog du lịch |
| viettopreview.vn | 10 | TIER 3 | Review site |
| langthangvinhlong.vn | 9 | TIER 3 | Blog cá nhân |
| nucuoimekong.com | 7 | TIER 3 | Tour operator |
| nhandan.vn | 6 | TIER 2 | Báo quốc gia |
| baodongkhoi.vn | 5 | TIER 2 | Báo Bến Tre |
| vietnamtourism.gov.vn | 11 | TIER 1 ✅ | Tổng cục Du lịch |

**⚠️ VẤN ĐỀ LỚN:** 449/1745 (26%) entities có source = vinhlong360.vn (CHÍNH MÌNH). Đây KHÔNG phải independent verification. Cần kiểm tra: nội dung những entities này có evidence bên ngoài không?

## Relationships

| Type | Count | % | Concern |
|------|-------|---|---------|
| **near** | **5065** | **40.7%** | Auto-generated từ coordinates, giá trị thông tin thấp |
| **related_to** | **4305** | **34.6%** | Generic/lazy — nên dùng type cụ thể hơn |
| located_in | 2214 | 17.8% | Place hierarchy |
| associated_with | 670 | 5.4% | Tốt hơn related_to |
| produced_in | 187 | 1.5% | Specific, có giá trị |
| **Total** | **12441** | | 75% là near + related_to (low quality) |

## Area Mismatches ĐÃ PHÁT HIỆN

| Entity ID | Name | DB Area | Issue |
|-----------|------|---------|-------|
| `hu-tieu-my-tho` | Hủ tiếu Mỹ Tho | vinh-long | 🔴 Mỹ Tho thuộc **Tiền Giang**, KHÔNG thuộc 3 tỉnh |
| `bun-nuoc-leo-tra-vinh-tai-vinh-long` | Bún Nước Lèo Trà Vinh (tại Vĩnh Long) | vinh-long | 🟡 Tên chứa "Trà Vinh" nhưng area "vinh-long" — hợp lý nếu quán ở VL bán món TV |

## Place Hierarchy — VẤN ĐỀ NGHIÊM TRỌNG ĐÃ XÁC NHẬN

| Issue | Chi tiết | Severity |
|-------|----------|----------|
| **Chỉ 1 tỉnh** | Chỉ có `vinh-long` (level=tinh). KHÔNG có place entity cho Bến Tre, Trà Vinh | 🔴 |
| **Không có huyện/TP** | 0 place entities cấp huyện. Hierarchy flat: tỉnh → xã/phường, bỏ qua cấp huyện | 🔴 |
| **Tất cả xã parentId=vinh-long** | Kể cả xã thuộc Bến Tre, Trà Vinh đều parent=vinh-long → **SAI** | 🔴 |
| **Huyện gán sai type** | `huyen-tam-binh` (huyện Tam Bình) có type="history" thay vì "place" | 🔴 |
| **Xã gán sai type** | `xa-tuong-loc` (xã Tường Lộc) có type="history" thay vì "place" | 🔴 |
| **125 places** | 1 tỉnh + 35 phường + 89 xã = 125. Thiếu ~26 huyện/TP + 2 tỉnh | 🟡 |

## Duplicate Entities ĐÃ XÁC NHẬN

### Person duplicates (cùng 1 người, nhiều entity)

| Nhân vật | Entity IDs | Action |
|----------|-----------|--------|
| **Phạm Hùng** | `pham-hung`, `pham-hung-pham-van-thien`, `khu-luu-niem-pham-hung`, `khu-luu-niem-chu-tich-hoi-dong-bo-truong-pham-hung`, `khu-tuong-niem-co-chu-tich-hdbt-pham-hung`, `khu-di-tich-luu-niem-chu-tich-pham-hung` | Person vs di tích — OK nếu khác type, nhưng quá nhiều entries? |
| **Trần Đại Nghĩa** | `tran-dai-nghia`, `tran-dai-nghia-pham-quang-le`, `khu-luu-niem-tran-dai-nghia-vinh-long` | 2 person + 1 history — merge 2 person? |
| **Nguyễn Văn Tồn** | `nguyen-van-ton-thach-duong`, `tuong-quan-nguyen-van-ton`, `lang-ong-lang-ong-che-nguyen-van-ton` | 2 person + 1 history |
| **Phan Thanh Giản** | `phan-thanh-gian` (person, VL), `khu-di-tich-mo-va-den-tho-phan-thanh-gian` (BT), `khu-mo-phan-thanh-gian` (BT), `lang-mo-va-dinh-phan-thanh-gian` (BT) | Person area=VL nhưng quê BT? 3 history entries cho 1 di tích? |
| **Võ Trường Toản** | `khu-mo-nha-giao-vo-truong-toan`, `mo-va-khu-luu-niem-vo-truong-toan`, `mo-va-khu-luu-niem-nha-giao-vo-truong-toan` | 3 entries cho 1 nơi? |

### Site duplicates (cùng 1 địa điểm, nhiều entity)

| Địa điểm | Entity IDs | Issue |
|-----------|-----------|-------|
| **KDT Đồng Khởi** | `khu-di-tich-dong-khoi`, `khu-di-tich-dong-khoi-ben-tre`, `khu-di-tich-quoc-gia-dac-biet-dong-khoi`, `lang-du-kich-dong-khoi` | 4 entries cho 1 khu di tích? |
| **Chùa Tuyên Linh** | `chua-tuyen-linh`, `chua-tuyen-linh-mo-cay-nam`, `chua-tuyen-linh-mo-cay-bac` | 3 entries — cùng chùa hay khác? |
| **Chùa Âng** | `chua-ang-angkorajaborey`, `chua-ang-wat-angkor-raig-borei`, `chua-ang-angkor-borei` | 3 entries cho 1 chùa? |
| **Đình Long Đức** | `dinh-long-duc`, `dinh-long-duc-tra-vinh` | 2 entries |
| **Lầu Bà Cố Hỷ** | `lau-ba-lau-ba-co-hy`, `lau-ba-co-hy-thuong-dong-nuong-nuong` | 2 entries |
| **Chiến thắng Mậu Thân** | `cong-vien-tuong-dai-chien-thang-mau-than`, `tuong-dai-chien-thang-mau-than-vinh-long` | 2 entries |
| **Căn cứ CM Cái Ngang** | `khu-di-tich-cach-mang-cai-ngang`, `di-tich-lich-su-cach-mang-cai-ngang`, `can-cu-cach-mang-cai-ngang-vinh-long` | 3 entries |
| **Nguyễn Ngọc Thăng** | `den-tho-tuong-quan-nguyen-ngoc-thang`, `den-tho-lanh-binh-nguyen-ngoc-thang`, `nguyen-ngoc-thang` | Đền thờ duplicate + person |

**Codex PHẢI verify:** mỗi case trên là duplicate thật (cần merge) hay entities khác nhau (giữ riêng)?

## Phan Thanh Giản — AREA CẦN VERIFY

`phan-thanh-gian` (person) có area=**vinh-long** nhưng:
- Theo Wikipedia: Phan Thanh Giản sinh tại Bảo Thạnh, Ba Tri, **Bến Tre**
- Mộ và đền thờ ở **Bến Tre** (entities `khu-di-tich-mo-va-den-tho-phan-thanh-gian` area=ben-tre)
- Văn Thánh Miếu thờ ông ở **Vĩnh Long**
- → Nên area=ben-tre (quê quán) hay vinh-long (nơi thờ)?

## 2 Quality Scoring Formulas KHÁC NHAU trong codebase

| Location | Formula | Scale | Issue |
|----------|---------|-------|-------|
| `agent/data_quality.py:101-122` | Boolean 3 factor: source + coords + placeId | 0/33/67/100 | Quá thô, bỏ qua description/summary |
| `scripts/validate_data.py:153-205` | Deduction-based: 100 - penalties | 0-100 | Chi tiết hơn nhưng -10 cho "no images" (tất cả 0 images → mọi entity -10) |

**Codex nên đề xuất:** thống nhất 1 formula, có tính đến description quality + verification status.

## Entity type "economy" — 0 entities

`"economy"` nằm trong VALID_ENTITY_TYPES nhưng có 0 entities trong data. Nên loại bỏ khỏi valid types?

## Bbox trong validate_data.py — RỘNG hơn prompt trước

```
Code: lat (9.0, 11.0), lng (105.0, 107.0)  ← rộng
Prompt trước: lat (9.2, 10.65), lng (105.6, 106.95) ← chặt hơn
```
Codex nên dùng bbox CHẶT hơn (prompt) để phát hiện entities gần biên.

## Enrichment Prompt — KHÔNG có system prompt

```
LLM: cx/gpt-5.5
Temperature: 0.65
Max tokens: 800
System prompt: KHÔNG CÓ
User prompt: template (xem section 1.1 file scripts/enrich_descriptions.py:81-173)
```

Prompt nói "CHỈ viết những gì có cơ sở từ thông tin được cung cấp, KHÔNG bịa thêm chi tiết cụ thể" nhưng context đầu vào RẤT ÍT (chỉ name + type + area + summary nếu có). Temperature 0.65 = KHÁ CAO cho factual content → **LLM sẽ bịa để lấp khoảng trống.**

## 35 Person entities — PHẢI VERIFY 100%

| ID | Name | Area | Claims thường có |
|----|------|------|-----------------|
| `tran-dai-nghia` | Trần Đại Nghĩa | VL | 1913-1997, GS, vũ khí kháng chiến |
| `pham-hung` | Phạm Hùng | VL | 1912-1988, Chủ tịch HĐBT |
| `vo-van-kiet` | Võ Văn Kiệt | VL | 1922-2008, Thủ tướng 1991-1997 |
| `nguyen-dinh-chieu` | Nguyễn Đình Chiểu | BT | Nhà thơ, tác giả Lục Vân Tiên |
| `nguyen-thi-dinh` | Nguyễn Thị Định | BT | Nữ tướng, Đồng Khởi |
| `nguyen-thien-thanh` | Nguyễn Thiện Thành | TV | |
| `nguyen-thi-ut` | Nguyễn Thị Út | TV | Út Tịch, anh hùng |
| `phan-thanh-gian` | Phan Thanh Giản | VL | Đại thần nhà Nguyễn |
| `thoai-ngoc-hau` | Thoại Ngọc Hầu | VL | Khai phá miền Tây |
| `dong-van-cong` | Đồng Văn Cống | BT | Trung tướng |
| `suong-nguyet-anh` | Sương Nguyệt Anh | BT | Nữ chủ bút đầu tiên VN |
| `nguyen-ngoc-thang` | Nguyễn Ngọc Thăng | BT | Lãnh binh chống Pháp |
| `vien-chau-huynh-tri-ba` | Viễn Châu (Huỳnh Trí Bá) | TV | Soạn giả cải lương |
| ... | (21 người nữa) | | Nhiều nghệ sĩ cải lương VL |

**Cross-ref bắt buộc:** Mỗi person entity → search Wikipedia VN → verify năm sinh/mất, quê quán, chức vụ, thành tích. Đặc biệt lưu ý:
- `phan-thanh-gian` area=vinh-long nhưng quê Bến Tre?
- Trùng lặp: `pham-hung` vs `pham-hung-pham-van-thien` vs `khu-tuong-niem-co-chu-tich-hdbt-pham-hung` — cùng 1 người, 3 entities?
- Trùng lặp: `tran-dai-nghia` vs `tran-dai-nghia-pham-quang-le` — cùng 1 người?
- Trùng lặp: `nguyen-van-ton-thach-duong` vs `tuong-quan-nguyen-van-ton` — cùng 1 người?

## Mẫu description CÓ DẤU HIỆU LLM (cần verify claims)

**Mẫu 1:** `chua-vam-ray` (attraction, tra-vinh)
> "Chùa Vàm Ray (Wath Vam Ray) là ngôi chùa Khmer lớn nhất Trà Vinh và cả ĐBSCL... chánh điện rộng **50m × 22m**... Tốn **50 tỷ đồng** xây dựng, khánh thành **2010**..."
> → Claims: kích thước (50x22m), chi phí (50 tỷ), năm (2010) — CẦN VERIFY

**Mẫu 2:** `nha-co-huynh-phu-thanh-phu` (history, ben-tre)
> "...xây dựng từ năm **1890** bởi ông Huỳnh Ngọc Khiêm trong **14 năm**. Diện tích trên **500m²** với **48 cột tròn** bằng gỗ căm xe, gỗ lim... Di tích Kiến trúc Nghệ thuật Quốc gia (**2011**)..."
> → Nhiều số liệu cụ thể — CẦN VERIFY từng con số

**Mẫu 3:** `bao-tang-tinh-vinh-long` (history, vinh-long)
> "...thành lập năm **1993**, tổng diện tích hơn **12.000 m²**, gồm **4 khu** trưng bày..."
> → Số liệu diện tích, năm, cấu trúc — CẦN VERIFY

**Mẫu 4:** `den-tho-bac-ho-tra-vinh` (history, tra-vinh)
> "...khởi công **10/3/1970** và khánh thành **26/1/1971** ngay trong thời chiến tranh... Khuôn viên rộng **5,4ha**..."
> → Ngày cụ thể, diện tích — CẦN VERIFY

**Mẫu 5:** `nem-chua-sau-xe` (product, vinh-long)
> "...đạt chứng nhận **OCOP 4 sao** năm **2020**..."
> → OCOP claims — PHẢI verify với CSDL OCOP chính thức

**Mẫu 6:** `lang-det-chieu-ca-hom-ham-tan` (craft_village, tra-vinh)
> "...gần **100 năm**... Bộ VHTTDL công nhận **Di sản Văn hóa Phi vật thể Quốc gia** năm **2024**. hơn **200 hộ** gia đình sản xuất gần **5.000 chiếu/năm**..."
> → Nhiều claims: tuổi làng nghề, di sản QG, số hộ, sản lượng — PHẢI VERIFY

## OCOP Products cần verify chứng nhận (~33 entities)

| Entity | OCOP Claim | Verify |
|--------|-----------|--------|
| `buoi-nam-roi-my-hoa` | OCOP 4 sao | ocop.gov.vn |
| `nem-chua-sau-xe` | OCOP 4 sao, 2020 | ocop.gov.vn |
| `bun-tuoi-va-hu-tieu-sau-thanh` | OCOP 4 sao, 2024 | ocop.gov.vn |
| `chao-dua-thuan-duyen-tam-binh` | OCOP 4 sao | ocop.gov.vn |
| `nuoc-mam-ruoi-long-vinh` | OCOP 4 sao | ocop.gov.vn |
| `banh-tet-tu-quy-hai-ly` | OCOP 4 sao | ocop.gov.vn |
| `tranh-dua-hop-kieng-cocohand` | OCOP 3 sao | ocop.gov.vn |
| `dua-troc-le-phuong` | OCOP 3 sao | ocop.gov.vn |
| `keo-dau-phong-du-tan-loi` | OCOP 3 sao, 2022 | ocop.gov.vn |
| `tom-xe-hiep-my-dong` | OCOP 3 sao | ocop.gov.vn |
| ... | ... | ... |

## Hành chính 3 tỉnh (ground truth)

### Vĩnh Long (8 đơn vị cấp huyện)
| Huyện/TP | Loại | Dân số (~) | Entities expected |
|----------|------|-----------|-------------------|
| TP Vĩnh Long | Thành phố | ~150.000 | ≥ 30 |
| TX Bình Minh | Thị xã | ~100.000 | ≥ 15 |
| H. Long Hồ | Huyện | ~160.000 | ≥ 15 |
| H. Mang Thít | Huyện | ~100.000 | ≥ 10 (lò gạch!) |
| H. Vũng Liêm | Huyện | ~160.000 | ≥ 15 |
| H. Tam Bình | Huyện | ~100.000 | ≥ 10 |
| H. Trà Ôn | Huyện | ~130.000 | ≥ 10 |
| H. Bình Tân | Huyện | ~90.000 | ≥ 5 |

### Bến Tre (9 đơn vị cấp huyện)
| Huyện/TP | Loại |
|----------|------|
| TP Bến Tre | Thành phố |
| H. Châu Thành | Huyện |
| H. Chợ Lách | Huyện |
| H. Mỏ Cày Bắc | Huyện |
| H. Mỏ Cày Nam | Huyện |
| H. Giồng Trôm | Huyện |
| H. Bình Đại | Huyện |
| H. Ba Tri | Huyện |
| H. Thạnh Phú | Huyện |

### Trà Vinh (9 đơn vị cấp huyện)
| Huyện/TP | Loại |
|----------|------|
| TP Trà Vinh | Thành phố |
| TX Duyên Hải | Thị xã |
| H. Càng Long | Huyện |
| H. Cầu Kè | Huyện |
| H. Tiểu Cần | Huyện |
| H. Châu Thành | Huyện |
| H. Trà Cú | Huyện |
| H. Cầu Ngang | Huyện |
| H. Duyên Hải | Huyện |

**CHECK:** Mỗi huyện/TP trên phải có ≥1 place entity + ≥5 entities thuộc huyện đó.

## Di tích Quốc gia cần CÓ TRONG DB (ground truth)

| Di tích | Tỉnh | Loại | Entity ID expected |
|---------|------|------|-------------------|
| Văn Thánh Miếu | Vĩnh Long | Di tích lịch sử | grep "van-thanh-mieu" |
| Khu lưu niệm Phạm Hùng | Vĩnh Long | Di tích lịch sử | ✅ Có |
| Khu lưu niệm Võ Văn Kiệt | Vĩnh Long | Di tích lịch sử | ✅ Có |
| Khu lưu niệm Trần Đại Nghĩa | Vĩnh Long | Di tích lịch sử | ✅ Có |
| Căn cứ CM Cái Ngang | Vĩnh Long | Di tích cách mạng | ✅ Có |
| Đình Long Thanh | Vĩnh Long | Di tích kiến trúc | ✅ Có |
| Khu di tích Đồng Khởi | Bến Tre | Di tích QG đặc biệt | ✅ Có |
| Khu di tích Nguyễn Đình Chiểu | Bến Tre | Di tích lịch sử | ✅ Có |
| Mộ Võ Trường Toản | Bến Tre | Di tích lịch sử | ✅ Có |
| Nhà cổ Huỳnh Phủ | Bến Tre | Di tích kiến trúc | ✅ Có |
| Ao Bà Om | Trà Vinh | Di tích văn hóa | grep "ao-ba-om" |
| Chùa Âng | Trà Vinh | Di tích kiến trúc | ✅ Có |
| Đền thờ Bác Hồ (TV) | Trà Vinh | Di tích lịch sử | ✅ Có |
| Chùa Hang (Kompong Chrây) | Trà Vinh | Di tích văn hóa | ✅ Có |

## Đặc sản ĐÚNG VÙNG (ground truth — dùng để verify)

| Đặc sản | Tỉnh ĐÚNG | Entity area PHẢI là | Lưu ý |
|---------|-----------|---------------------|-------|
| Kẹo dừa | Bến Tre | ben-tre | Đúng |
| Bánh tráng Mỹ Lồng | Bến Tre | ben-tre | Giồng Trôm |
| Bánh phồng Sơn Đốc | Bến Tre | ben-tre | Giồng Trôm |
| Bưởi da xanh | Bến Tre | ben-tre | Châu Thành/Mỏ Cày Bắc |
| Dừa sáp | Trà Vinh | tra-vinh | Cầu Kè |
| Cốm dẹp | Trà Vinh | tra-vinh | Đặc sản Khmer |
| Bưởi Năm Roi | Vĩnh Long | vinh-long | Bình Minh |
| Tàu hủ ky | Vĩnh Long | vinh-long | Bình Minh |
| Nem chua | Vĩnh Long | vinh-long | |
| **Hủ tiếu Mỹ Tho** | **Tiền Giang** | **KHÔNG thuộc 3 tỉnh** | 🔴 Entity hiện gán VL |
| **Nem Lai Vung** | **Đồng Tháp** | **KHÔNG thuộc 3 tỉnh** | Nếu có → verify area |
| Bánh canh Bến Có | Trà Vinh | tra-vinh | |
| Bún nước lèo | Trà Vinh | tra-vinh | Gốc Khmer |

## Mùa vụ trái cây ĐBSCL (ground truth)

| Trái cây | Mùa chính | Tháng peak | Area chính |
|----------|-----------|------------|-----------|
| Xoài cát | Tháng 3-6 | 4-5 | VL, BT |
| Bưởi Năm Roi | Quanh năm, ngon nhất 8-11 | 9-10 | VL (Bình Minh) |
| Bưởi da xanh | Quanh năm, ngon nhất 9-12 | 10-11 | BT |
| Chôm chôm | Tháng 5-7 | 6 | VL (Long Hồ) |
| Sầu riêng | Tháng 5-8 | 6-7 | BT, VL |
| Nhãn | Tháng 6-8 | 7 | VL, BT |
| Cam sành | Tháng 10-2 | 12-1 | VL (Tam Bình) |
| Dừa | Quanh năm | - | BT |
| Dừa sáp | Tháng 7-12 | 9-10 | TV (Cầu Kè) |
| Sapoche | Tháng 1-3 | 2 | VL |
| Mận | Tháng 4-6 | 5 | VL |

## Lễ hội chính (ground truth)

| Lễ hội | Tỉnh | Thời gian | Tần suất |
|--------|------|-----------|---------|
| Ok Om Bok | Trà Vinh | Tháng 10 ÂL (khoảng tháng 11 DL) | Hàng năm |
| Sen Dolta | Trà Vinh | Tháng 8-9 ÂL | Hàng năm |
| Nghinh Ông | Bến Tre (Bình Đại) | Tháng 6 ÂL | Hàng năm |
| Lễ hội trái cây | Vĩnh Long | Tháng 6 DL (thường) | Hàng năm |
| Ngày hội Bánh dân gian | Vĩnh Long | Tháng 4-5 DL | Hàng năm |
| Hội chợ hoa kiểng | Bến Tre (Chợ Lách) | Tết ÂL | Hàng năm |
| Lễ Kỳ Yên | VL, BT, TV | Tùy đình, thường tháng 2-3 ÂL | Hàng năm |
| Đua ghe Ngo | Trà Vinh | Trùng Ok Om Bok, tháng 10 ÂL | Hàng năm |

---

# NHIỆM VỤ — 3 GIAI ĐOẠN

## GIAI ĐOẠN 1: HIỂU DATA LAYER

### 1.1 Đọc schema và pipeline

**Đọc KỸ các files này (theo thứ tự):**

| # | File | Tại sao |
|---|------|---------|
| 1 | `agent/database.py` | Schema definitions, tất cả columns, indexes, constraints |
| 2 | `init.sql` | PostgreSQL prod schema |
| 3 | `scripts/enrich_descriptions.py` | **TÂM ĐIỂM** — đọc từng dòng prompt template, parameters, output processing |
| 4 | `scripts/enrich_with_llm.py` | Prompt template thứ 2 |
| 5 | `scripts/generate_missing_descriptions.py` | Prompt template thứ 3 |
| 6 | `scripts/import_enrichment_descriptions.py` | Import pipeline — cách content LLM vào DB |
| 7 | `scripts/import_enrichment_tips.py` | Import tips — cùng pattern |
| 8 | `agent/data_quality.py` | Quality scoring + candidate queue |
| 9 | `agent/knowledge.py` | In-memory load — biến đổi gì không? |
| 10 | `scripts/validate_data.py` | Validation rules hiện tại |
| 11 | `scripts/fix_data_quality.py` | Auto-fixes — có rủi ro sửa sai không? |
| 12 | `scripts/optimize_data.py` | Optimizations — biến đổi gì? |
| 13 | `scripts/deep_audit.py` | Audit dimensions hiện tại |
| 14 | `scripts/geocode_clusters.py` | Geocoding — nguồn nào? Accuracy? |

### 1.2 Đọc DỮ LIỆU THỰC TẾ

**QUAN TRỌNG:** Đừng chỉ đọc schema. Đọc **dữ liệu thực** trong DB.

- Đọc `web/data.json` — đây là export từ DB, chứa TẤT CẢ entities
- Grep patterns trong `web/data.json`:
  - Tìm descriptions dài (>200 chars) → đọc nội dung → kiểm tra có dấu hiệu LLM không
  - Tìm summaries boilerplate ("là một", "nổi tiếng", "thu hút")
  - Tìm attributes.phone → kiểm tra format
  - Tìm coordinates → kiểm tra range
  - Tìm source URLs → kiểm tra format

### 1.3 Truy vết enrichment history

- Grep `git log` cho commits liên quan đến enrich/import/descriptions
- Tìm files JSONL trong `agent/data/` hoặc `scripts/` — đây có thể là đầu vào import
- Xác định: bao nhiêu % entities có description là LLM-generated vs human-written vs crawled?
- Có `entity_changes` table tracking ai sửa gì không?

---

## GIAI ĐOẠN 2: XÁC MINH SỰ THẬT — 10 CHIỀU FORENSIC

### V1. PHÁT HIỆN HALLUCINATION TRONG DESCRIPTIONS

**Đây là chiều QUAN TRỌNG NHẤT của toàn bộ audit.**

#### V1.1 Dấu hiệu LLM Hallucination (đọc MỖI description)

| Pattern ID | Dấu hiệu | Ví dụ | Severity |
|-----------|-----------|-------|----------|
| H1 | **Specific year without source** | "Chùa được xây năm 1849" — năm nào cũng đúng? Kiểm tra | 🔴 Critical |
| H2 | **Precise measurements** | "Diện tích 5.2 hecta" — nguồn nào? | 🔴 Critical |
| H3 | **Named historical figures** | "Do ông Nguyễn Văn X thành lập" — người thật? | 🔴 Critical |
| H4 | **Specific statistics** | "Thu hút 50.000 du khách mỗi năm" — số liệu có nguồn? | 🔴 Critical |
| H5 | **Detailed historical narrative** | "Trong thời kỳ kháng chiến, nơi đây từng là căn cứ..." — sự kiện có thật? | 🟡 High |
| H6 | **Sensory descriptions** | "Hương thơm ngào ngạt của hoa..." — generic filler, vô hại nhưng vô giá trị | 🟡 Low |
| H7 | **Superlatives without evidence** | "Lớn nhất miền Tây", "Đẹp nhất tỉnh" — có thật không? | 🟡 High |
| H8 | **Recipe/ingredient details** | "Gồm bột gạo, nước cốt dừa, đường thốt nốt..." — đúng công thức? | 🟡 Medium |
| H9 | **Opening hours/prices** | "Mở cửa 7h-17h, vé 30.000đ" — có cập nhật không? Bịa? | 🔴 Critical |
| H10 | **Phone numbers** | "Liên hệ: 0xxx.xxx.xxx" — số thật hay bịa? | 🔴 Critical |
| H11 | **Awards/certifications** | "Đạt chứng nhận OCOP 4 sao" — xác minh được không? | 🔴 Critical |
| H12 | **Distance/direction claims** | "Cách trung tâm thành phố 15km về phía Đông" — đo lại bằng coords? | 🟡 Medium |
| H13 | **Population/demographic** | "Dân số 15.000 người" — nguồn nào? Năm nào? | 🟡 Medium |
| H14 | **Literary/poetic flourishes** | Đoạn văn quá mượt, quá đều, quá "AI" — nội dung không sai nhưng thiếu authenticity | 🟢 Low |

#### V1.2 Phương pháp kiểm tra từng entity

```
CHO MỖI entity có description > 100 chars:

1. PHÂN LOẠI description origin:
   - [LLM-generated] nếu: git blame → commit message chứa "enrich"/"import"/"LLM"
   - [Human-written] nếu: git blame → commit message thủ công
   - [Crawled] nếu: có source URL + content tương ứng
   - [Unknown] nếu: không xác định được

2. SCAN cho hallucination patterns H1-H14:
   - Liệt kê MỖI claim cụ thể (năm, số, tên người, đo lường)
   - Đánh dấu: ✅ Verifiable / ⚠️ Unverifiable / ❌ Likely false

3. CROSS-REFERENCE:
   - Có source URL đi kèm entity? Content tại URL có match description?
   - Google "[entity name] [area]" — kết quả có khớp?
   - Wikipedia VN (nếu có) — facts khớp?
   
4. VERDICT cho mỗi entity:
   - 🟢 VERIFIED — tất cả claims kiểm chứng được
   - 🟡 PARTIALLY VERIFIED — một số claims chưa kiểm chứng
   - 🔴 SUSPECT — có claims trông như hallucination
   - ⚫ FABRICATED — có claims chắc chắn sai
```

#### V1.3 Red-flag patterns cụ thể cho vùng Mekong Delta

| Category | Bẫy hallucination thường gặp | Cách kiểm tra |
|----------|------------------------------|---------------|
| **Chùa/đền** | LLM bịa năm xây dựng "thế kỷ 18" khi thật ra mới xây thập niên 1960 | Cross-ref Wikipedia VN hoặc Di tích QG list |
| **Lịch sử kháng chiến** | LLM gán sự kiện "căn cứ cách mạng" cho bất kỳ nơi nào có cây cổ thụ | Kiểm tra danh sách di tích lịch sử chính thức |
| **Đặc sản/món ăn** | LLM bịa nguyên liệu, gán món của tỉnh này cho tỉnh khác | Cross-ref với nguồn ẩm thực đáng tin (báo Tuổi Trẻ, Thanh Niên) |
| **OCOP** | LLM bịa số sao, bịa năm chứng nhận, bịa tên nhà sản xuất | Cross-ref với CSDL OCOP chính thức (ocopvinhlong.vn hoặc tương đương) |
| **Chợ nổi** | LLM mô tả chợ nổi "nhộn nhịp mỗi ngày" khi thực tế chỉ họp sáng sớm | Kiểm tra thông tin thực tế |
| **Làng nghề** | LLM bịa "hàng trăm năm lịch sử" cho làng nghề mới vài thập kỷ | Cross-ref với nguồn chính thức |
| **Khoảng cách** | LLM nói "cách TP 10km" nhưng thực tế 25km | Tính từ coordinates |
| **Mùa vụ** | LLM bịa "mùa thu hoạch tháng 3-5" cho trái cây season hoàn toàn khác | Cross-ref mùa vụ Mekong Delta |
| **Diện tích** | LLM bịa "500 hecta" cho vườn trái cây nhỏ | Kiểm tra satellite/source |
| **Giải thưởng** | "Điểm du lịch tiêu biểu ĐBSCL 2023" — giải này có tồn tại? Năm đúng? | Cross-ref nguồn chính thức |

---

### V2. XÁC MINH TỌA ĐỘ ĐỊA LÝ

#### V2.1 Bounding box check

```
Bounding box 3 tỉnh (VL + BT + TV):
- Latitude: 9.20°N — 10.65°N
- Longitude: 105.60°E — 106.95°E

Bounding box riêng từng tỉnh (ước tính):
- Vĩnh Long: lat 9.85-10.35, lng 105.75-106.25
- Bến Tre: lat 9.70-10.30, lng 106.05-106.75
- Trà Vinh: lat 9.35-10.00, lng 105.90-106.60
```

**Kiểm tra cho MỖI entity có coordinates:**

| Check | Mô tả | Severity |
|-------|--------|----------|
| V2-A | Coords ngoài bbox tổng → entity CHẮC CHẮN sai vị trí | 🔴 |
| V2-B | Coords trong bbox tổng nhưng ngoài bbox tỉnh (area) → có thể gán sai area | 🟡 |
| V2-C | Coords trùng nhau giữa 2+ entities → copy-paste error | 🔴 |
| V2-D | Coords là số tròn (vd: 10.0, 106.0) → có thể placeholder, không phải toạ độ thật | 🟡 |
| V2-E | Coords precision < 4 decimal → quá thô, chỉ đúng đến ~10km | 🟡 |
| V2-F | Entity type "restaurant"/"cafe" nhưng coords trỏ ra giữa sông/đồng ruộng | 🔴 |

#### V2.2 Cross-check area vs coordinates

```
CHO MỖI entity:
- entity.area = "vinh-long" → coordinates phải nằm trong bbox Vĩnh Long
- entity.area = "ben-tre" → coordinates phải nằm trong bbox Bến Tre
- entity.area = "tra-vinh" → coordinates phải nằm trong bbox Trà Vinh
- Nếu mismatch → FLAG: area sai hoặc coordinates sai
```

#### V2.3 Place hierarchy integrity

```
CHO MỖI entity type "place":
- parentId trỏ đến entity tồn tại?
- parentId tạo tree hợp lệ? (không circular)
- level (xa/phuong) đúng với hành chính thực tế?
- 16 xã mới lên phường (2024-2025): đã cập nhật?
  Danh sách 16 phường mới: Phường 1-8 (TP Vĩnh Long), An Bình, 
  Tân Hội, Tân Hạnh, Long Hồ, Phú Quới, Thanh Đức, Tân An Hội, Bình Hoà Phước
```

---

### V3. XÁC MINH TÊN GỌI

#### V3.1 Tên chính xác theo hành chính

```
CHO MỖI entity:
- Tên chính thức (theo UBND/gov.vn) vs tên trong DB?
- Dấu tiếng Việt ĐÚNG? (sai dấu = entity khác!)
  Ví dụ: "Vĩnh Tràng" ≠ "Vĩnh Trạng" ≠ "Vĩnh Trang"
- Entity ID (slug) nhất quán với name?
  "chua-vinh-trang" cho "Chùa Vĩnh Tràng" — OK
  "Chua_Vinh_Trang" — SAI format
```

#### V3.2 Duplicate detection

```
Phát hiện trùng lặp:
1. EXACT: cùng name → chắc chắn duplicate
2. NEAR-EXACT: khác dấu/casing → "Chùa Vĩnh Tràng" vs "chùa vĩnh tràng"
3. FUZZY: Levenshtein ≤ 3 → "Cồn Phụng" vs "Cồn Phụn"
4. SEMANTIC: cùng entity nhưng tên khác → "Chùa Vĩnh Tràng" vs "Vĩnh Tràng Temple" vs "Chùa Phước Hậu" (alias)
5. SPLIT: 1 entity bị tách 2+ records → "Cù lao An Bình" và "An Bình" (cùng nơi?)
```

#### V3.3 Entity type verification

```
CHO MỖI entity:
- Type gán ĐÚNG?
  "Hủ tiếu" → phải là "dish", không phải "product" hay "attraction"
  "Cù lao An Bình" → phải là "attraction" hoặc "nature", không phải "place"
  "Bánh tráng Mỹ Lồng" → "product" (nếu nói sản phẩm OCOP) hoặc "dish" (nếu nói món ăn)?
- Có entities type "economy" → thực sự có ý nghĩa gì? User có dùng không?
- Type "facility" vs "organization" → ranh giới rõ ràng không?
```

---

### V4. XÁC MINH LỊCH SỬ

#### V4.1 Kiểm tra mọi claim lịch sử

**LLM RẤT THÍCH bịa lịch sử — đây là vùng rủi ro CAO NHẤT.**

```
CHO MỖI entity có description chứa:
- Năm (regex: \b1[0-9]{3}\b hoặc \b20[0-2][0-9]\b)
- Tên người (regex: các pattern tên Việt)
- Sự kiện lịch sử ("kháng chiến", "Pháp", "thời kỳ", "xưa kia")
- Triều đại ("Nguyễn", "thế kỷ")

→ KIỂM TRA:
1. Năm chính xác? Cross-ref Wikipedia VN / nguồn chính thức
2. Người thật? Liên quan thật đến entity này?
3. Sự kiện đúng? Xảy ra ở ĐÚng nơi này?
4. Có source URL đi kèm? Source nói gì?
```

#### V4.2 Danh sách di tích cần xác minh đặc biệt

| Entity | Claims thường bị bịa | Cross-ref |
|--------|----------------------|-----------|
| Chùa/đền/miếu | Năm xây, ai xây, phong cách kiến trúc, xếp hạng di tích | Danh mục Di tích QG, Wikipedia |
| Nhà cổ | Năm xây, chủ nhân, diện tích, số phòng | Sở VH-TT&DL |
| Di tích kháng chiến | Sự kiện, năm, đơn vị, kết quả trận đánh | Lịch sử Đảng bộ tỉnh |
| Mộ/khu tưởng niệm | Tiểu sử nhân vật, năm sinh/mất, chức vụ | Wikipedia VN |
| Chợ cổ | Năm thành lập, quy mô | Nguồn hành chính |

---

### V5. XÁC MINH ẨM THỰC & SẢN VẬT

#### V5.1 Đặc sản đúng vùng?

**LLM thường gán SAI đặc sản — ví dụ gán hủ tiếu Mỹ Tho (Tiền Giang) cho Vĩnh Long.**

```
CHO MỖI entity type "dish" hoặc "product":
1. Món/sản phẩm này ĐÚNG vùng (area) được gán?
   - "Kẹo dừa" → Bến Tre (ĐÚNG), không phải Vĩnh Long
   - "Bánh tráng Mỹ Lồng" → Bến Tre (ĐÚNG)
   - "Hủ tiếu Mỹ Tho" → Tiền Giang, KHÔNG PHẢI Vĩnh Long hay Bến Tre!
   - "Nem Lai Vung" → Đồng Tháp, KHÔNG PHẢI Vĩnh Long!
   
2. Mô tả nguyên liệu/cách chế biến ĐÚNG?
   - Công thức có hợp lý với truyền thống vùng ĐBSCL?
   - Nguyên liệu có tồn tại ở vùng này?

3. OCOP certification ĐÚNG?
   - Số sao → kiểm tra CSDL OCOP chính thức
   - Nhà sản xuất → có thật?
   - Năm chứng nhận → đúng?
```

#### V5.2 Mùa vụ Mekong Delta

```
Mùa vụ thực tế (kiểm tra với season data trong entities):
- Xoài: tháng 4-6 (mùa chính)
- Bưởi Năm Roi: quanh năm nhưng ngon nhất tháng 8-10
- Chôm chôm: tháng 5-7
- Dừa: quanh năm
- Sầu riêng: tháng 5-7
- Nhãn: tháng 6-8
- Bưởi da xanh: tháng 9-12
- Cam sành: tháng 11-2

Entity nào có season data → season ĐÚNG không?
Entity nào THIẾU season data → cần thêm
```

---

### V6. XÁC MINH SỐ ĐIỆN THOẠI & GIỜ MỞ CỬA

#### V6.1 Phone number verification

```
CHO MỖI entity có attributes.phone:
1. Format đúng? (0xxx.xxx.xxx hoặc +84xxxxxxxxx)
2. Mã vùng đúng cho tỉnh?
   - Vĩnh Long: 0270
   - Bến Tre: 0275
   - Trà Vinh: 0294
   - Mobile: 09x, 03x, 07x, 08x, 05x
3. Số hợp lệ? (đúng số digit: 10 số cho cố định, 10 số cho mobile)
4. LLM có thể BỊA số điện thoại → flag mọi số không có source
5. Số điện thoại cũ (7 số) chưa chuyển đổi?
```

#### V6.2 Opening hours verification

```
CHO MỖI entity có attributes.hours hoặc tương tự:
1. Format nhất quán? ("7:00-17:00" vs "7h-17h" vs "Sáng 7h chiều 5h")
2. Giờ HỢP LÝ cho loại hình?
   - Chùa: thường 6:00-18:00
   - Chợ: 5:00-12:00 (chợ sáng), 14:00-22:00 (chợ chiều)
   - Nhà hàng: 10:00-22:00
   - Quán cà phê: 6:00-22:00
   - Điểm du lịch: 7:00-17:00
3. LLM có thể BỊA giờ mở cửa → flag nếu không có source
4. Giờ có thể đã THAY ĐỔI (hậu COVID) → đánh dấu stale
```

---

### V7. XÁC MINH SOURCE ATTRIBUTION

#### V7.1 Source URL integrity

```
CHO MỖI entity có source:
1. Source format đúng? [{title, url}]
2. URL có vẻ hợp lệ? (domain tồn tại, path hợp lý)
3. URL là nguồn tin cậy?
   TIER 1 (tin cậy nhất):
   - *.gov.vn (UBND, Sở ban ngành)
   - wikipedia.org
   - Tổng cục Du lịch
   
   TIER 2 (tin cậy):
   - Báo chính thống (tuoitre.vn, thanhnien.vn, vnexpress.net)
   - Google Maps
   
   TIER 3 (tham khảo):
   - Blog du lịch, TripAdvisor, Traveloka
   - Trang thông tin địa phương
   
   TIER 4 (cần kiểm chứng):
   - Social media
   - Trang cá nhân
   
   KHÔNG CÓ SOURCE = flag

4. Title trong source có match content entity không?
5. Bao nhiêu % entities có source? Target: 100% cho attraction/history/person
```

#### V7.2 Entities KHÔNG CÓ source

```
Phân loại entities không có source:
- Entity type "attraction" không source → 🔴 Critical (phải có)
- Entity type "history"/"person" không source → 🔴 Critical  
- Entity type "dish" không source → 🟡 Medium (kiến thức phổ biến có thể chấp nhận)
- Entity type "place" không source → 🟡 Medium (hành chính, có thể tra)
- Entity type "restaurant"/"cafe" không source → 🟡 Medium
```

---

### V8. XÁC MINH QUAN HỆ (RELATIONSHIPS)

#### V8.1 Relationship truth check

```
CHO MỖI relationship:
1. Type đúng?
   - "hosts" → from là venue, to là event? (không ngược?)
   - "produced_in" → from là product, to là place? 
   - "offered_by" → from là service/product, to là provider?
   - "supplies_to" → from là producer, to là retailer?
   - "near" → from và to THẬT SỰ gần nhau? (check coordinates distance)

2. Relationship CÓ THẬT?
   - "Bưởi Năm Roi" produced_in "Bình Minh" → ĐÚNG?
   - "Chùa X" near "Chùa Y" → khoảng cách thật bao nhiêu? threshold hợp lý?
   
3. Orphan references:
   - from_id trỏ đến entity không tồn tại?
   - to_id trỏ đến entity không tồn tại?
```

#### V8.2 Missing relationships (should exist)

```
Relationships hợp lý nhưng có thể thiếu:
- Dish → Restaurant (nơi bán): mỗi dish phải link đến ≥1 restaurant
- Product → Area: mỗi OCOP product phải link đến vùng sản xuất
- Attraction → Nearby: mỗi attraction nên link đến attractions gần (< 5km)
- Person → Place: nhân vật lịch sử → nơi sinh/hoạt động
- Event → Venue: mỗi event phải có venue
```

---

### V9. XÁC MINH ITINERARY

```
CHO MỖI itinerary:
1. Stops references entity_ids hợp lệ? (entity tồn tại?)
2. Thứ tự stops HỢP LÝ về địa lý? (không zigzag vô nghĩa)
3. Khoảng cách giữa stops hợp lý? (không 2 stops cách nhau 100km cho day trip)
4. Duration estimates hợp lý?
   - Day trip: 3-5 stops, tổng ≤ 10 giờ
   - Multi-day: hợp lý theo ngày
5. Mix entity types hợp lý? (không 5 chùa liên tiếp)
6. Area consistency: stops cùng area hoặc areas liền kề?
```

---

### V10. XÁC MINH ATTRIBUTES

```
CHO MỖI entity có attributes JSONB:

1. KEY CONSISTENCY:
   List tất cả unique keys → có alias?
   "hours" vs "open_hours" vs "opening_hours" → PHẢI normalize
   "phone" vs "telephone" vs "contact" → PHẢI normalize
   "price" vs "price_range" vs "gia" → PHẢI normalize

2. VALUE VALIDITY:
   - rating: 0-5 range? Có decimal? Source?
   - price_range: format? ("$" vs "50.000đ" vs "Miễn phí")
   - certification: OCOP sao bao nhiêu? Có thật?
   - specialty: đúng cho loại hình?

3. COMPLETENESS per type:
   | Type | Must-have attrs | Nice-to-have |
   |------|-----------------|-------------|
   | restaurant | hours, phone, specialty | price_range, capacity |
   | attraction | hours, best_time | price, accessibility |
   | accommodation | phone, price_range | amenities, capacity, wifi |
   | product | producer | certification, price |
   | event | dates, frequency | organizer, cost |
```

---

## GIAI ĐOẠN 3: BÁO CÁO & CHIẾN LƯỢC

### 3.1 Entity-level verification status

**CHO MỖI entity, assign verdict:**

| Verdict | Ý nghĩa | Action |
|---------|----------|--------|
| ✅ VERIFIED | Tất cả claims có source, facts kiểm chứng được | Không cần hành động |
| 🟡 PARTIAL | Một số claims chưa kiểm chứng nhưng KHÔNG có red flag | Cần bổ sung source |
| 🟠 SUSPECT | Có dấu hiệu hallucination (patterns H1-H14) nhưng chưa confirm sai | Cần fact-check manual |
| 🔴 FABRICATED | Có claims CHẮC CHẮN sai (sai năm, sai vùng, số điện thoại bịa) | Cần sửa NGAY |
| ⚫ EMPTY | Không có description/summary đáng kể → không có gì để verify | Cần viết content |

### 3.2 Enrichment pipeline risk assessment

```
Đánh giá:
1. Bao nhiêu % descriptions trong DB là LLM-generated?
2. Trong số LLM-generated, bao nhiêu % chứa ≥1 unverifiable claim?
3. Enrichment prompt có đủ guardrails? Đề xuất prompt cải tiến
4. Có nên thêm mandatory human review trước khi apply?
5. Có nên thêm "confidence" field cho mỗi description?
6. Có nên tách "LLM-generated" vs "human-verified" flag?
```

### 3.3 Data trust scoring

```
Trust score formula (khác quality score):
trust_score = (
  has_source(tier1_or_tier2) * 25 +
  description_verified * 25 +
  coordinates_verified * 15 +
  name_official * 10 +
  no_hallucination_flags * 15 +
  attributes_sourced * 10
) / 100

Distribution:
- [90-100] HIGH TRUST → có thể public ngay
- [70-89] MEDIUM TRUST → cần spot-check 
- [50-69] LOW TRUST → cần human review
- [0-49] UNTRUSTED → cần rewrite hoặc remove description
```

---

# RÀNG BUỘC DỮ LIỆU — BẮT BUỘC TUÂN THỦ

| # | Ràng buộc | Chi tiết |
|---|-----------|----------|
| CD1 | **Ảnh CHỈ AI-generated** | KHÔNG stock (Pexels/Unsplash), KHÔNG UGC (trừ review photos), KHÔNG Wikimedia. Pipeline: `gen_entity_images.py` + `gen_image.py` |
| CD2 | **Source attribution bắt buộc** | Mỗi entity phải có ≥1 source với title + URL. KHÔNG re-host nội dung báo chí |
| CD3 | **Coordinates trong bbox** | lat 9.2-10.65°N, lng 105.6-106.95°E (3 tỉnh Mekong) |
| CD4 | **Entity types cố định** | 17 types: attraction, dish, experience, product, accommodation, craft_village, event, facility, organization, person, history, nature, economy, cafe, restaurant, drink, place |
| CD5 | **Relationship fanout ≤ 120** | Mỗi entity tối đa 120 non-hierarchical relationships |
| CD6 | **Areas = 3 tỉnh** | vinh-long, ben-tre, tra-vinh (sáp nhập thành 1 tỉnh nhưng data vẫn chia 3) |
| CD7 | **Dual DB** | SQLite (knowledge) + PostgreSQL (UGC/auth). KHÔNG port UGC sang SQLite |
| CD8 | **Solo dev budget** | Enrichment LLM calls có cap/ngày (default 20). Image gen manual trigger |
| CD9 | **Không fake data** | KHÔNG fabricate reviews, ratings, visit counts. Chỉ dùng data thật hoặc AI-enriched descriptions (và phải đánh dấu origin) |
| CD10 | **Backup trước mọi thao tác** | `python scripts/backup_data.py` trước ETL/migrate/normalize |

---

# CONTEXT: Vietnamese Fact-Checking

## Nguồn xác minh tin cậy cho vùng ĐBSCL

| Loại thông tin | Nguồn chính thức | Cách truy cập |
|----------------|------------------|---------------|
| Hành chính (tên huyện/xã, diện tích) | UBND tỉnh, Tổng cục Thống kê | *.gov.vn |
| Di tích lịch sử | Cục Di sản Văn hóa, Sở VH-TT&DL | dst.gov.vn |
| OCOP | Chương trình OCOP quốc gia | ocop.gov.vn |
| Lễ hội | Sở VH-TT&DL tỉnh | sovhtt*.gov.vn |
| Du lịch | Sở Du lịch, TCDL | vietnamtourism.gov.vn |
| Nhân vật lịch sử | Wikipedia VN, Từ điển Bách khoa VN | vi.wikipedia.org |
| Địa danh | Google Maps, OpenStreetMap | maps.google.com |
| Ẩm thực | Báo chí uy tín, sách ẩm thực | tuoitre.vn, thanhnien.vn |

## Lỗi factual PHỔ BIẾN ở dữ liệu du lịch VN

| Lỗi | Ví dụ | Hậu quả |
|-----|-------|---------|
| **Gán sai tỉnh** | Hủ tiếu Mỹ Tho gán cho Vĩnh Long (thực tế Tiền Giang) | User đến VL tìm hủ tiếu Mỹ Tho → thất vọng |
| **Năm sai** | Chùa X "xây năm 1850" thực tế 1950 | Mất uy tín → user không tin data khác |
| **Người sai** | "Do vua Gia Long xây" khi thực tế là dân lập | Sai lịch sử → bị community chỉ trích |
| **Số sai** | "50.000 du khách/năm" không có nguồn | Inflate expectations |
| **Giờ sai** | "Mở cửa 7-17h" thực tế đã đổi | Du khách đến ngoài giờ |
| **Giá sai** | "Vé 30.000đ" thực tế đã tăng | Du khách thiếu tiền |
| **Status sai** | "Đang hoạt động" thực tế đã đóng cửa | Du khách đi lỡ |
| **Khoảng cách sai** | "Cách 15km" thực tế 30km | Lỡ kế hoạch |

---

# OUTPUT: `docs/data-verification-report.md`

## CẤU TRÚC FILE BẮT BUỘC

```markdown
# Data Verification Report — vinhlong360

> Forensic audit: xác minh sự thật, phát hiện hallucination, đảm bảo data integrity.
> Cập nhật: [ngày]

---

## MỤC LỤC
1. Executive Summary — Verdict tổng
2. Hallucination Scan (V1)
3. Geographic Verification (V2)
4. Name Verification (V3)
5. Historical Fact-Check (V4)
6. Culinary & Product Verification (V5)
7. Contact Info Verification (V6)
8. Source Attribution Audit (V7)
9. Relationship Truth Check (V8)
10. Itinerary Verification (V9)
11. Attribute Verification (V10)
12. Enrichment Pipeline Risk Assessment
13. Trust Score Distribution
14. Completeness Audit (secondary)
15. Fix Priority — Factual Errors First
16. Appendixes

---

## 1. EXECUTIVE SUMMARY

### Verdict tổng
- Total entities audited: [X]
- ✅ VERIFIED: [X] ([Y%])
- 🟡 PARTIAL: [X] ([Y%])
- 🟠 SUSPECT: [X] ([Y%])
- 🔴 FABRICATED claims found: [X] ([Y%])
- ⚫ EMPTY (no content to verify): [X] ([Y%])

### Top findings
- [#1 most critical factual error found]
- [#2 ...]
- [#3 ...]

### LLM enrichment impact
- Estimated % descriptions that are LLM-generated: [X%]
- Of those, % containing unverifiable claims: [X%]
- Of those, % containing CONFIRMED false claims: [X%]

### Overall trust score: [X/100]

---

## 2. HALLUCINATION SCAN (V1)

### 2.1 Pattern frequency
| Pattern | Occurrences | Example entity | Example claim | Verdict |
|---------|-------------|----------------|---------------|---------|
| H1 (year) | [X] | [entity_id] | "[claim]" | ✅/⚠️/❌ |
| H2 (measurement) | [X] | [entity_id] | "[claim]" | ✅/⚠️/❌ |
| ... | ... | ... | ... | ... |

### 2.2 Confirmed false claims
| # | Entity ID | Claim | Truth | Source | Fix |
|---|-----------|-------|-------|--------|-----|
| 1 | [id] | "[false claim]" | "[correct fact]" | [source] | Remove/correct |
| ... | ... | ... | ... | ... | ... |

### 2.3 Unverifiable claims (need human check)
| # | Entity ID | Claim | Why unverifiable | Risk |
|---|-----------|-------|------------------|------|
| 1 | [id] | "[claim]" | [reason] | 🔴/🟡 |
| ... | ... | ... | ... | ... |

### 2.4 LLM fingerprint analysis
[Kết quả phân tích: bao nhiêu descriptions có dấu hiệu LLM-generated?
Patterns: quá đều nhịp, quá mượt, thiếu chi tiết local, generic adjectives...]

---

## 3-11. [Chi tiết cho V2-V10]

Mỗi section phải có:
- **Scope:** bao nhiêu entities kiểm tra
- **Method:** cách kiểm tra (grep, cross-ref, calculate)
- **Findings:** dữ kiện cụ thể (entity_id, claim, evidence)
- **Errors found:** danh sách lỗi factual CỤ THỂ
- **Corrections:** giá trị đúng (nếu biết)
- **Unresolvable:** cases cần human fact-check

---

## 12. ENRICHMENT PIPELINE RISK ASSESSMENT

### 12.1 Current pipeline analysis
[Mô tả flow: metadata → LLM prompt → description → DB]
[Prompt template strengths and weaknesses]
[Temperature settings vs quality tradeoffs]

### 12.2 Guardrail gaps
[Liệt kê: what guardrails exist vs what's missing]

### 12.3 Recommendations
| # | Recommendation | Impact | Effort |
|---|---------------|--------|--------|
| R1 | Add "origin" field: "llm" / "human" / "crawled" | Trust transparency | S |
| R2 | Require source URL for every LLM-enriched entity | Prevent sourceless claims | M |
| R3 | Add fact-check queue: LLM output → pending → human review → publish | Prevent hallucination | M |
| R4 | Lower temperature from 0.65 → 0.2 for factual content | Reduce creativity/fabrication | S |
| R5 | Restrict LLM to summary expansion ONLY (no new facts) | Prevent invented facts | S |
| ... | ... | ... | ... |

---

## 13. TRUST SCORE DISTRIBUTION

### Per-entity trust score
[Histogram: 0-20, 20-40, 40-60, 60-80, 80-100]
[% entities HIGH TRUST (≥90): [X%]]
[% entities UNTRUSTED (<50): [X%] — cần immediate action]

### Per-type trust score
| Type | Avg trust | Min | Max | Lowest-trust entities |
|------|----------|-----|-----|-----------------------|
| attraction | [X] | [Y] | [Z] | [entity_ids] |
| dish | [X] | [Y] | [Z] | [entity_ids] |
| ... | ... | ... | ... | ... |

---

## 14. COMPLETENESS AUDIT (secondary)

### 14.1 Entity statistics
| Type | Count | % with summary | % with description | % with coords | % with images | % with source |
|------|-------|---------------|-------------------|---------------|---------------|---------------|
| attraction | [X] | [Y%] | [Z%] | [W%] | [V%] | [U%] |
| ... | ... | ... | ... | ... | ... | ... |

### 14.2 Coverage map
| Area | Total | attraction | dish | restaurant | product | event | history | nature |
|------|-------|-----------|------|-----------|---------|-------|---------|--------|
| vinh-long | [X] | ... | ... | ... | ... | ... | ... | ... |
| ben-tre | [X] | ... | ... | ... | ... | ... | ... | ... |
| tra-vinh | [X] | ... | ... | ... | ... | ... | ... | ... |

### 14.3 Missing entity candidates
| # | Entity name | Type | Area | Why must exist | Evidence |
|---|------------|------|------|----------------|----------|
| 1 | [name] | [type] | [area] | [reason] | [source] |
| ... | ... | ... | ... | ... | ... |

---

## 15. FIX PRIORITY — FACTUAL ERRORS FIRST

### P0 — Confirmed factual errors (fix IMMEDIATELY)
| # | Entity ID | Error | Correct value | Source | Fix method |
|---|-----------|-------|---------------|--------|------------|
| 1 | [id] | "[wrong]" | "[right]" | [source] | UPDATE description |
| ... | ... | ... | ... | ... | ... |

### P1 — Suspected hallucinations (review within 1 week)
| # | Entity ID | Suspect claim | Why suspect | Action needed |
|---|-----------|--------------|-------------|---------------|
| 1 | [id] | "[claim]" | [reason] | Human fact-check |
| ... | ... | ... | ... | ... |

### P2 — Missing sources (add within 1 month)
| # | Entity ID | Type | Missing | Priority |
|---|-----------|------|---------|----------|
| 1 | [id] | [type] | Source URL | High (attraction) |
| ... | ... | ... | ... | ... |

### P3 — Completeness gaps (ongoing)
[Missing fields, thin content, coverage gaps]

### P4 — Pipeline improvements (strategic)
[Enrichment guardrails, review process, trust scoring]

---

## 16. APPENDIXES

### A. Complete Entity Verification Matrix
| entity_id | type | area | trust_score | verdict | hallucination_flags | factual_errors | missing_source |
|-----------|------|------|-------------|---------|--------------------:|---------------:|:--------------:|
| [id] | [type] | [area] | [0-100] | ✅/🟡/🟠/🔴/⚫ | [count] | [count] | Y/N |
[SORT by trust_score ASC → least trusted first]

### B. All Factual Claims Inventory  
| entity_id | claim_text | claim_type | verifiable | verified | source |
|-----------|-----------|-----------|:----------:|:--------:|--------|
| [id] | "Xây năm 1849" | year | Y | ✅/❌ | [url] |
| [id] | "Diện tích 5.2ha" | measurement | Y | ⚠️ | - |
[MỖI claim cụ thể trong MỖI description]

### C. Duplicate Candidates
[entity_a ↔ entity_b, similarity reason, recommendation]

### D. Coordinates Anomalies
[Entities with suspect coordinates: outside bbox, duplicated, rounded, mid-river]

### E. Phone Number Audit
[All phone numbers: entity_id → number → format_valid? → area_code_correct?]

### F. Source URL Audit
[All source URLs: entity_id → url → tier → domain → accessible?]

### G. LLM-Generated Content Inventory
[entity_id → description_origin (llm/human/crawled/unknown) → enrichment_date → commit_hash]

### H. Mekong Delta Reference Data
[Danh sách huyện/thành phố chính thức 3 tỉnh, di tích QG, OCOP reference, lễ hội chính]

### I. Enrichment Prompt Templates
[Copy nguyên văn prompt templates từ enrich_descriptions.py + enrich_with_llm.py
→ phân tích điểm mạnh/yếu của từng prompt]

### J. Recommended Corrected Values
[Cho MỖI factual error tìm được: entity_id → field → current_value → corrected_value → source]

### K. External Cross-Reference Log
[MỖI web search thực hiện: entity_id → query → source_url → result → MATCH/MISMATCH/NOT_FOUND]
[SORT by MISMATCH first → đây là factual errors]

### L. Entity Existence Verification
[Entities mà web search KHÔNG TÌM THẤY bất kỳ kết quả nào]
[entity_id → name → queries tried → verdict: real_but_small / name_wrong / FABRICATED]

### M. Area Mismatch Report
[Entities mà web search cho thấy thuộc TỈNH KHÁC]
[entity_id → DB area → real area → source → action: fix_area / remove]

### N. Cross-Reference Statistics
- Total entities web-verified: [X] / [total]
- ✅ MATCH (data đúng): [X] ([Y%])
- 🔴 MISMATCH (data sai): [X] ([Y%])
- ⚠️ NOT FOUND (không tìm thấy): [X] ([Y%])
- Verification coverage by type: [table]
- Verification coverage by area: [table]
```

---

# YÊU CẦU CHẤT LƯỢNG — FORENSIC STANDARD

## Nguyên tắc xác minh

1. **KHÔNG TIN BẤT KỲ DESCRIPTION NÀO** cho đến khi cross-reference. Đặc biệt descriptions dài, chi tiết, mượt mà — đó thường là LLM output
2. **Grep trước khi kết luận** — mọi claim phải có evidence từ codebase HOẶC nguồn bên ngoài
3. **Đếm chính xác** — "~1500 entities" KHÔNG chấp nhận. Phải đếm chính xác
4. **Entity-level detail** — KHÔNG chỉ aggregate. Liệt kê CỤ THỂ entity_id + claim + evidence
5. **KHÔNG tự bịa correction** — nếu không biết giá trị đúng, nói "cần human fact-check", ĐỪNG bịa giá trị khác thay thế (tránh sửa hallucination bằng hallucination khác)
6. **Phân biệt "sai" vs "không kiểm chứng được"** — "sai" = có evidence ngược lại. "Không kiểm chứng" = không tìm được evidence cho hoặc chống
7. **Ghi nhận uncertainty** — nếu không chắc chắn 1 claim đúng hay sai, nói rõ mức tự tin: 90%, 70%, 50%
8. **Priority = factual error > missing source > missing content** — sửa thông tin SAI TRƯỚC, bổ sung source TRƯỚC, thêm content SAU

## Anti-patterns NGHIÊM CẤM

| # | Anti-pattern | Tại sao nguy hiểm |
|---|-------------|-------------------|
| AP1 | **Sửa hallucination bằng hallucination** — bạn phát hiện năm sai rồi tự BỊA năm khác | Thay 1 sai bằng 1 sai khác |
| AP2 | **Bỏ qua im lặng** — thấy claim nghi ngờ nhưng không flag vì "có thể đúng" | False negative nguy hiểm hơn false positive |
| AP3 | **Trust by length** — description dài = chất lượng? KHÔNG. LLM bịa rất dài | Dài ≠ đúng |
| AP4 | **Trust by confidence** — claim được phát biểu tự tin = đúng? KHÔNG. LLM rất tự tin khi bịa | Tự tin ≠ đúng |
| AP5 | **Assume source = verified** — entity có source URL ≠ content match URL | Source có thể irrelevant |
| AP6 | **Skip places** — entity type "place" (xã/phường) cũng cần verify tên, coords, level | Place data cũng có thể sai |
| AP7 | **Fabricate missing entities** — phát hiện entity thiếu → tự BỊA data cho nó | Chỉ GỢI Ý entity cần thêm, KHÔNG tạo data |
| AP8 | **Round-trip hallucination** — dùng 1 LLM output làm source cho 1 LLM output khác | Cần nguồn NGOÀI LLM |

## Minimum deliverables

| # | Deliverable | Minimum |
|---|------------|---------|
| D1 | **External cross-reference log** | ≥ 200 web search entries (Appendix K) |
| D2 | **Entity verification matrix** | MỌI entity phải có verdict (✅/🟡/🟠/🔴/⚫) |
| D3 | **Factual claims inventory** | MỌI claim cụ thể (năm, số, tên người) phải được liệt kê + đánh giá |
| D4 | **Confirmed factual errors** | Danh sách ĐẦY ĐỦ errors với correction + source URL bên ngoài |
| D5 | **Suspect claims needing human check** | Danh sách ĐẦY ĐỦ claims chưa verify được |
| D6 | **Entity existence check** | ≥ 50 entities được verify "có thật" qua web search (Appendix L) |
| D7 | **Area mismatch report** | MỌI entity có area sai (thuộc tỉnh khác) (Appendix M) |
| D8 | **Source audit** | MỌI entity phải có source status (has/missing) |
| D9 | **Trust score** | MỌI entity phải có trust score 0-100 |
| D10 | **Coordinate audit** | MỌI entity có coords phải được bbox-check |
| D11 | **Phone audit** | MỌI phone number phải được format + area code check |
| D12 | **Pipeline risk assessment** | ≥ 10 guardrail improvements cho enrichment pipeline |
| D13 | **LLM content inventory** | % content là LLM-generated phải xác định |
| D14 | **Fix script** | SQL/Python commands để fix MỌI confirmed error |
| D15 | **Corrected values with sources** | MỌI correction phải có source URL TIER 1/2 (Appendix J) |
| D16 | **Coverage map** | Area × Type heat map (secondary) |

---

# QUALITY GATE — TỰ KIỂM TRA

## Gate 1: External Cross-Reference (QUAN TRỌNG NHẤT)
| # | Check | Pass? |
|---|-------|-------|
| QG1 | Đã WEB SEARCH cho 100% entities type "history" + "person"? | |
| QG2 | Đã WEB SEARCH cho 100% entities type "attraction" có claims lịch sử? | |
| QG3 | Đã WEB SEARCH cho 100% entities có OCOP claims? | |
| QG4 | Đã WEB SEARCH cho ≥ 30% entities type "restaurant"/"cafe"? | |
| QG5 | MỌI factual claim (năm, số, tên) đã được cross-ref với nguồn TIER 1 hoặc TIER 2? | |
| QG6 | Cross-reference log (Appendix K) có ≥ 200 search entries? | |
| QG7 | MỌI "MISMATCH" có source URL chứng minh? | |

## Gate 2: Hallucination Detection
| # | Check | Pass? |
|---|-------|-------|
| QG8 | Đã đọc MỌI description > 100 chars? | |
| QG9 | Đã scan MỌI entity cho hallucination patterns H1-H14? | |
| QG10 | MỌI "FABRICATED" verdict có evidence CHỨNG MINH sai từ nguồn bên ngoài? | |
| QG11 | KHÔNG tự bịa giá trị đúng khi không chắc? (anti-pattern AP1) | |
| QG12 | Phân biệt rõ "sai" vs "không kiểm chứng được"? | |

## Gate 3: Data Integrity
| # | Check | Pass? |
|---|-------|-------|
| QG13 | Đã check MỌI coordinates trong bbox? | |
| QG14 | Đã check MỌI phone numbers format + area code? | |
| QG15 | Đã check MỌI source URLs format? | |
| QG16 | Trust score formula applied to ALL entities? | |
| QG17 | Appendix D (coordinate anomalies) complete? | |

## Gate 4: Actionability
| # | Check | Pass? |
|---|-------|-------|
| QG18 | Fix list có entity_id + field + current_value + correct_value + source_url? | |
| QG19 | MỌI correction có nguồn NGOÀI LLM (TIER 1 hoặc TIER 2)? | |
| QG20 | Pipeline recommendations có ≥ 10 guardrail improvements? | |
| QG21 | Human fact-check list prioritized (entity_id + claim + why suspect)? | |
| QG22 | Fix script runnable (SQL/Python)? | |
| QG23 | Mọi recommendation tuân thủ constraints CD1-CD10? | |

## Gate 5: Completeness (secondary)
| # | Check | Pass? |
|---|-------|-------|
| QG24 | Coverage map shows ALL huyện × ALL types? | |
| QG25 | Missing entity list có evidence (search volume, known POI)? | |
| QG26 | Relationship integrity audit done? | |
| QG27 | Itinerary verification done? | |
| QG28 | Entity existence verification (Appendix L) done for ≥ 50 entities? | |

**28/28 PASS mới nộp.**

---

## KẾT THÚC PROMPT

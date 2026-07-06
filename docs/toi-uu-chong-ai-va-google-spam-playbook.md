<!-- Sinh bởi workflow vl360-anti-ai-spam-optimize (2026-07-06). 41 finding→31 verify→28 confirmed, 2 loại (snake-oil/bịa nguồn). Nguồn: Google Search Central spam-policies/helpful-content/E-E-A-T. -->

# PLAYBOOK TỐI ƯU SÂU — vinhlong360.vn
## "Độ đặc thù Vĩnh Long + trải nghiệm bản địa thật là thứ đồng thời đánh bại cả việc-bị-đọc-như-AI lẫn Google-spam"

> Tài liệu chiến lược cho solo dev. Mọi khuyến nghị hợp lệ với chính sách Google (không lách), tôn trọng guardrail dự án (backup trước thao tác dữ liệu §B1, 1 task/commit §B5, không đăng nguyên văn báo §B6, ảnh chỉ AI-gen). Các phần đụng dữ liệu/noindex/gộp trang phải qua ROADMAP task + test trước khi sửa (§3, §B3/B4) — nếu ngoài roadmap thì ghi "Backlog phát sinh", KHÔNG big-bang.

---

## 1. Luận đề & khung tư duy

**Luận đề:** Vĩnh Long (mới) có một vốn liếng mà không tỉnh ĐBSCL nào khác có — gạch gốm đỏ Mang Thít, bưởi Năm Roi Bình Minh, chùa Khmer Trà Vinh, dừa sáp Cầu Kè, cù lao An Bình trên sông Cổ Chiên, chợ nổi Trà Ôn. **Mỗi chi tiết bản địa thật, kiểm chứng được, viết ra một cách cụ thể — đồng thời làm ba việc:** (a) khiến trang không đọc-như-AI (máy không sinh được sự thật địa phương cụ thể); (b) tạo giá trị riêng per-page mà Google helpful-content tưởng thưởng; (c) xây tín hiệu E-E-A-T "Experience". Ngược lại, filler "miền Tây sông nước hữu tình" cùng lúc gây cả ba lỗi: đọc-như-AI, thin/unoriginal, và không có Experience.

**Nguyên tắc đạo đức bắt buộc (loại mọi khuyến nghị vi phạm):**
- **KHÔNG né detector.** Không spinning, không paraphrase-để-qua-máy-dò, không humanizer, không chèn lỗi cố ý, không cloaking, không giả EXIF/metadata, không đổi ngày cho "có vẻ mới". Đây chính là hồ sơ SpamBrain phạt — rủi ro cao hơn lợi ích, và mâu thuẫn định vị "chất lượng thật".
- **Chuẩn mực DUY NHẤT để tối ưu:** "Trang này có giúp người đọc thật không?" Không phải "trang này có qua AI-checker không?".
- **Google KHÔNG cấm nội dung AI-assisted.** Chính sách phạt là *intent thao túng + giá trị thấp ở quy mô lớn*, "no matter how it's created". Nội dung LLM-hỗ-trợ + có người biên tập kiểm chứng + có giá trị riêng = hợp lệ. Vì vậy con đường đúng là **nâng chất + minh bạch cách tạo**, không giấu việc dùng AI.
- **Trung thực hơn ấn tượng.** Thà nhãn "chưa có ảnh thật" / "chưa kiểm chứng tại chỗ" (đã có sẵn, GIỮ) còn hơn bịa "Experience" giả. Bịa trải nghiệm/số liệu/nguồn còn tệ hơn generic-nhưng-đúng — nó vừa vi phạm E-E-A-T vừa dính anti-hallucination cứng của dự án.

**Khung ưu tiên nguồn lực (ROI cho solo dev):** Google ưu tiên *cải thiện/hợp nhất > noindex*. Nhưng với 1.600 trang, chiến lược đúng là **hai vận tốc song song**: (1) **hàng rào tạm** — cổng chất lượng chặn trang mỏng khỏi index NGAY (rẻ, bảo vệ cả site khỏi hạ hạng); (2) **nâng chất dần** — mỗi vòng viết lại 20-50 entity keystone lên chuẩn "Nguyễn Thị Út / tép khô Mỹ Long" rồi mở lại index. Thà 300-500 trang xuất sắc được index còn hơn 1.605 trang mỏng kéo tụt E-E-A-T toàn site.

---

## 2. Rủi ro Google nghiêm trọng nhất: "Scaled content abuse" trên ~1.600 trang entity

**Chẩn đoán (đo trên web/data.json, 1.730 entity — nguồn build prerender):**
| Chỉ số | Giá trị | Ngưỡng an toàn |
|---|---|---|
| Median mô tả | 48 từ | ≥120-150 từ đặc thù cho trang index |
| Entity <80 từ | 1.289/1.730 (75%) | Nhóm này → noindex hoặc viết lại |
| Entity ≥150 từ | 32/1.730 (1.85%) | KPI cần kéo lên |
| Có ảnh thật | 60/1.730 (3.5%) | — |
| Có source_url thật | ~37% render citation (0 trong snapshot data.json) | — |
| description == summary | 113 entity | 0 giá trị thêm → in đôi |
| Cụm restaurant/accom/cafe | 408 entity, 99.8% <80 từ, 100% không ảnh | Cụm rủi ro LỚN NHẤT |

**Điều biến 1.600 trang từ "hữu ích" thành "spam" (verbatim Google, spam-policies cập nhật 2026-05):** *"Scaled content abuse is when many pages are generated for the primary purpose of manipulating search rankings and not helping users... large amounts of unoriginal content that provides little to no value to users, no matter how it's created."*

Số lượng trang KHÔNG phải điều kiện vi phạm. **TỶ LỆ trang giá trị thấp** mới là. Các trigger cụ thể site này đang chạm:
1. **Mass-produced không chăm sóc riêng** — 408 trang nhà hàng/lưu trú mở câu y hệt "Nhà hàng tại [địa chỉ]. Phục vụ ẩm thực miền Tây..."; chỉ khác địa chỉ + 1 cụm filler → near-duplicate.
2. **Unoriginal/lặp** — 113 trang description == summary; nhiều trang body in lại verbatim câu lead.
3. **Phát đồng loạt vào index** — sitemap phát mọi entity qua `_is_public` (agent/seo.py:1043) mà KHÔNG có cổng chất lượng; site inherit `index,follow` toàn cục (nuxt.config.ts:60), 0 gating per-entity.
4. **Freshness gaming (vô ý)** — 1.730 entity cùng `lastmod 2026-06-28` + `changefreq='weekly'` hardcoded (seo.py:1180); trust card hiện "Cập nhật 5/7/2026" đồng loạt = ngày import, không phải kiểm chứng thật.

**Ngưỡng an toàn (self-assessment Google, phải trả "yes"):** mỗi trang index phải cung cấp "original information/analysis beyond the obvious", là trang "you'd want to bookmark/share/recommend", có "substantial value compared to other pages in search results". Trang chỉ là data-fragment (1 câu + toạ độ + list) → **noindex,follow hoặc gộp vào hub**, ĐỪNG index để "phủ SEO".

**Bằng chứng khả quan (đòn bẩy):** 2 trang giàu nhất — person "Nguyễn Thị Út" (219 từ), history "Làng du kích Đồng Khởi" (218 từ) — đọc RẤT gốc, cụ thể-địa-phương, không hề như máy. Cụm craft_village/dish/product/nature cũng viết tốt, đầy số liệu. **Pipeline nội bộ THỪA SỨC đạt chuẩn.** Việc cần làm: kéo cái đuôi dài (907 trang <50 từ) lên chuẩn đó, HOẶC noindex/gộp cho tới khi đủ chất.

**KHÔNG áp cho site:** site reputation abuse (không host nội dung bên-thứ-ba mượn uy tín) + expired domain abuse (không mua domain hết hạn). Giữ nguyên trạng; chỉ rà lại nếu sau này mở khu "bài viết đối tác/PR".

---

## 3. Danh mục hành động ưu tiên (P0 → P1 → P2)

> Đã gộp/khử trùng các finding trùng. Effort: S (≤2h) / M (nửa ngày–1 ngày) / L (nhiều ngày, cần batch).

### 🔴 P0 — Chặn hồ sơ scaled-content + trả câu "Who/How"

---

**P0-1 · Cổng chất lượng trước index (sitemap + robots per-entity)** — effort M
- **Vấn đề:** sitemap phát mọi entity qua `_is_public` (seo.py:1043-1051, chỉ loại provisional/unverified — KHÔNG có gate số từ/ảnh/nguồn); trang entity inherit `index,follow` toàn cục (nuxt.config.ts:60), 0 gating per-page. → phát hàng nghìn trang mỏng đồng loạt.
- **Bằng chứng:** vòng entity seo.py:1169-1183 chỉ check `_is_public`; dia-diem/[id].vue `useSeoMeta` KHÔNG set `robots`. Live: cả 5 trang kiểm đều trả `index,follow`.
- **Vì sao:** đúng cờ đỏ "scaled" + thin kéo hạng CẢ site qua Helpful/Core.
- **CÁCH SỬA:**
  1. **Một hàm eligibility DUY NHẤT** ở backend `is_index_worthy(entity)`. Dùng **AND, không OR** (đã đo: OR-gate với "có source http" là pass-through vì 991/1605 có external source → gate vô hiệu). Công thức: `desc_words >= NGƯỠNG AND (has_real_image OR desc_words >= 200)`. Chọn NGƯỠNG bằng cách sort giảm dần lấy top ~400, hoặc cố định ~100 từ rồi đo lại (đích 300-500 trang).
  2. Gọi hàm này TRONG vòng seo.py:1169 (ngay sau `_is_public`) → không đạt thì không append.
  3. Ở dia-diem/[id].vue thêm `computed isIndexable` cùng ngưỡng, set `robots: () => isIndexable.value ? 'index, follow, max-image-preview:large, max-snippet:-1' : 'noindex, follow'` (SSR, giữ chuỗi đầy đủ cho trang giàu). **`follow` để truyền link-equity.**
  4. **Đồng bộ** sitemap ↔ page (dùng chung ngưỡng) — nếu lệch, "sitemap bảo index nhưng trang tự noindex" là tín hiệu mâu thuẫn.
  5. **FIX bug thật:** vòng PLACE trong sitemap (seo.py:1157-1166) KHÔNG qua `_is_public` → place provisional vẫn vào sitemap. Áp cùng gate.
- **Kỳ vọng phải báo chủ dự án TRƯỚC:** với data hiện tại, đại đa số (~1.396 trang) sẽ chuyển noindex,follow. **Đây là hành vi mong muốn**, không phải bug.
- **§B3/B4:** seo.py có test — thêm test cho `is_index_worthy` (dày≥ngưỡng→index; có ảnh→index; mỏng+không ảnh→noindex) TRƯỚC khi sửa. Chỉ đọc dữ liệu, không cần backup.

---

**P0-2 · Cụm 408 trang nhà hàng/lưu trú/cà phê — near-duplicate template** — effort L
- **Vấn đề:** 188 restaurant + 164 accom + 56 cafe; 407/408 <80 từ; 408/408 không ảnh. Khung câu "Nhà hàng tại [địa chỉ]. Phục vụ ẩm thực miền Tây..." lặp qua hàng trăm trang.
- **Bằng chứng:** nha-hang-huong-sen / nha-hang-am-thuc-pho / nha-hang-sau-tu mở y hệt, chỉ khác địa chỉ + filler.
- **Vì sao:** cụm rủi ro scaled-content LỚN NHẤT ("nearly identical content").
- **CÁCH SỬA:**
  1. Áp cổng P0-1 → phần lớn cụm này rơi noindex,follow.
  2. **Gộp thành trang danh bạ theo phường/loại** (LocalBusiness ItemList) và CHỈ index trang danh bạ — đây là trang có giá trị gộp thật. Trang lẻ noindex,follow trỏ về danh bạ (doorway-safe, đúng khuyến nghị Google "gộp trang mỏng").
  3. Mở lại index từng trang khi đạt ngưỡng bằng nội dung THẬT (món signature thật + giá + giờ + chỗ đậu xe + ảnh AI-gen). Ưu tiên 244 entity có `specialty` / 24 có `must_order` (gần đạt ngưỡng nhất).
- **TUYỆT ĐỐI KHÔNG:** chạy script paraphrase/spin làm 408 mô tả "khác nhau"; nhồi từ khoá; đổi filler cho từng trang. Đó là né-detector.

---

**P0-3 · description == summary + body in lại verbatim câu lead** — effort M (guard) + L (viết lại)
- **Vấn đề:** 113 entity description trùng khít summary; nhiều trang detail in câu lead 2 lần (người đọc thấy cùng câu ở hero + body).
- **Bằng chứng:** dia-diem/[id].vue render summary làm `.lead` (dòng ~102) rồi description ngay dưới (~110/115). Ví dụ: quan-meo-u-kitchen, benh-vien-da-khoa-minh-duc-ben-tre hiện câu 2 lần. Nhóm khác (bao-tang-ben-tre) chỉ lặp câu-lead ở đầu body rồi có prose thật.
- **CÁCH SỬA (2 nhóm):**
  - **Nhóm A ~pure duplicate:** viết body prose GỐC (chi tiết chỉ nơi này có — mẫu chuẩn: sokfarm-tieu-can có tên người sáng lập, ấp/xã, chứng nhận USDA/EU, diện tích) HOẶC noindex,follow. KHÔNG in đôi.
  - **Nhóm B dup+append:** cắt câu-lead-lặp ở đầu body (rẻ, giữ prose gốc phía sau).
  - **Guard tại template (sửa 1 chỗ = 1.422 trang):** trong `descriptionSections/descriptionParagraphs`, bỏ paragraph đầu nếu (normalize) trùng `entity.summary` → chặn double-print cả dữ liệu cũ lẫn mới.
- **Lưu ý:** 111/113 là type='place' route /xa-phuong/[id].vue — template chỉ render summary 1 lần, KHÔNG double-render; đây là trang HUB (giá trị đến từ phần tổng hợp), xử lý theo P1-5.

---

**P0-4 · Filler "miền Tây" chung chung trên ≥6 template trang tĩnh** — effort M
- **Vấn đề:** filler ĐBSCL làm giọng mặc định trên nhiều trang, không phải một chỗ (35 occurrence / 11 file — verified).
- **Bằng chứng:** index.vue:380 "những ngày chậm rãi rất Nam Bộ"; du-lich.vue:310/313 "sông nước Nam Bộ"/"chỉ có ở miền Tây"; luu-tru.vue:12; theo-mua.vue:327; su-kien.vue:136 "Sự kiện tại miền Tây"; utils/pageManifest.ts:54; public/llms.txt:7.
- **Vì sao:** test "đổi tên tỉnh vẫn đúng" fail; DEFAULT dùng lại trên ≥6 template = near-duplicate voice → khớp scaled-content + "summarizing without adding value".
- **CÁCH SỬA:** thay filler bằng danh từ riêng cụ-thể-Vĩnh-Long ở TỪNG trang (mỗi trang câu khác, KHÔNG tái sử dụng 1 câu). VD index lede → "Chèo xuồng qua rạch dừa nước ở cù lao An Bình, hái chôm chôm tại vườn Bình Hòa Phước, nghe đờn ca tài tử bên bến Cổ Chiên." **Ràng buộc cứng:** (1) chi tiết phải CÓ THẬT — không bịa vườn/địa danh/đặc sản (§anti-hallucination); (2) KHÔNG nhồi từ khoá "Vĩnh Long"; (3) ưu tiên default dùng-lại-nhiều (pageManifest/llms.txt) trước vì near-duplicate lan rộng nhất. Chạy qua skill `viet-content-optimizer`.

---

**P0-5 · Không có byline/tác giả trên bất kỳ trang entity nào — fail câu "Who"** — effort M
- **Vấn đề:** 0/1.730 entity có author/verified_by. Trust card chỉ có Nguồn + Cập nhật.
- **Bằng chứng:** dia-diem/[id].vue grep 'author|byline|tác giả' chỉ trả 1 dòng (image credit, ~647). Live 5 trang: Author = None.
- **Vì sao:** Google hỏi thẳng "Do pages carry a byline... lead to further information about the author?". Thiếu hoàn toàn trên 1.730 trang template = tín hiệu "mass-produced, individual pages don't get care" + thiếu trụ Trust.
- **CÁCH SỬA:**
  1. Tạo trang tác giả/ban biên tập thật `/tac-gia` (hoặc mở rộng /gioi-thieu): tên/bút danh, ảnh, gắn bó VL-BT-TV, phương pháp kiểm chứng, liên hệ. **ĐIỀU KIỆN DỪNG §4:** chỉ công khai danh tính nếu chủ dự án đồng ý — KHÔNG tự đặt tên người.
  2. Byline PHÂN LOẠI TRUNG THỰC theo `verified`/`verifiedAt`: entity đã kiểm chứng thực địa → "Biên tập: [tên] · Kiểm chứng thực địa: [ngày]"; entity verified=false → "Tổng hợp từ nguồn công khai, CHƯA kiểm chứng thực địa · Biên tập chịu trách nhiệm: [tên]". **TUYỆT ĐỐI KHÔNG** gắn ngày "Kiểm chứng" cho entity chưa đi thực tế.
  3. JSON-LD `author`/`editor` chỉ khi phản ánh sự thật; entity chưa kiểm chứng → `publisher=Organization 'vinhlong360'`, KHÔNG `reviewedBy`/`dateVerified` khống.
- **Cảnh báo:** byline là CẦN nhưng KHÔNG ĐỦ để thoát scaled-content. Phải song song P0-1/P0-2/P0-3.

---

**P0-6 · Ngày "Cập nhật" đồng loạt + freshness "fresh" giả** — effort S
- **Vấn đề:** trust card hiện "Cập nhật 5/7/2026" đồng loạt (= ngày build); `source_freshness.updated_at` derive từ `entity.updatedAt` (public_api.py) = timestamp import hàng loạt, không phải kiểm chứng người.
- **Vì sao:** Google cảnh báo "changing the date... to make them seem fresh when content has not substantially changed".
- **CÁCH SỬA:**
  1. **Tách 2 khái niệm ở tầng dữ liệu:** "ngày import" (updatedAt) vs "ngày kiểm chứng thật" (`attributes.verifiedAt`, database.py:1624 đã hỗ trợ). Bỏ fallback tự động `verifiedAt=updatedAt` (database.py:1629-1630).
  2. Ở [id].vue trust label: chỉ dùng ngày kiểm-chứng-thật nếu CÓ; không có → "Kiểm chứng lần cuối: chưa rõ" (KHÔNG đóng dấu updatedAt import).
  3. Freshness "fresh" tính từ ngày kiểm-chứng-thật; hiện 0 entity có → toàn bộ về `status='unknown'` (badge "Chưa rõ", KHÔNG badge xanh "Mới cập nhật").
  4. NGỪNG re-stamp updatedAt hàng loạt lúc import/build — chỉ đổi khi nội dung entity thật sự thay đổi (so nội dung).
- **§B1:** backup trước; **§B4:** test cho logic ngày.

---

**P0-7 · Trust card luôn render dù rỗng — quảng cáo sự thiếu tin cậy** — effort S
- **Vấn đề:** `trustVisible = !!entity` → card LUÔN hiện; khi rỗng show "Chưa có nguồn công khai" / "Chưa rõ" ngay trên trang.
- **Bằng chứng:** dia-diem/[id].vue:828, fallback dòng 806/808/826.
- **CÁCH SỬA:** gate CHỈ theo nguồn thật: `const trustVisible = computed(() => !!trustSourceUrl.value)` (KHÔNG key vào `source_freshness.updated_at` vì luôn truthy → gate vô hiệu). Ẩn card trên subset không-nguồn, giữ trên ~58%+ có nguồn. Tuỳ chọn: làm mềm copy empty-state. **KHÔNG block chờ chiến dịch fill-source; KHÔNG blanket-gán cổng tỉnh chung cho entity chưa từng lấy nguồn ở đó** (misleading-attribution tệ hơn card vắng). Scope quyết định fill/noindex theo PROD data thật, không theo snapshot data.json cũ.

---

### 🟡 P1 — Đặc thù hoá + provenance + độ ổn định SEO

---

**P1-1 · Superlative không dẫn chứng + em-dash/nhịp phẳng trong lead entity** — effort M
- **Vấn đề:** "thuần khiết nhất vùng", "danh tiếng", "xuất khẩu toàn cầu" (18× "nhất vùng", 30× "nổi tiếng"); em-dash dày (950/1.730).
- **CÁCH SỬA (hợp lệ, bỏ phần "chặt câu tạo burstiness/né AI-tell" = snake-oil):**
  1. Batch qua `viet-content-optimizer` với **luật cứng:** cấm superlative tự phong ("nhất vùng", "thuần khiết nhất", "danh tiếng", "toàn cầu") trừ khi kèm số liệu/nguồn; **cấm chèn mốc lịch sử/giải thưởng không nguồn** (anti-hallucination — KHÔNG chèn "đấu xảo Nam Kỳ 1911" hay tương tự để thay fluff).
  2. Sửa em-dash CHỈ khi nối 2 mệnh đề gượng ép → thay bằng dấu chấm vì lý do ĐỌC DỄ, KHÔNG vì "né máy dò" (em-dash tiếng Việt hợp lệ; KHÔNG đặt luật cơ học "≤1/đoạn").
  3. Đòn bẩy thật = thay fluff bằng dữ kiện cụ thể: giống bưởi Năm Roi, mùa thu hoạch, đò từ bến nào, liên kết nội bộ tới HTX bưởi Năm Roi Mỹ Hòa.

---

**P1-2 · Card trust thiếu nguồn cho ~63% + tagline định vị lặp ≥5 nơi** — effort S+L
- **Vấn đề:** chỉ 37% entity có external citation thật; "khám phá... theo cách của người bản địa" lặp ở title/og/footer/onboarding/llms.txt.
- **CÁCH SỬA:**
  1. Điền source_url thật (cổng tỉnh/báo — CHỈ trích đoạn+link §B6) + ngày kiểm chứng cho entity muốn index. Ưu tiên history/di tích/OCOP (dữ kiện cứng cần Trust nhất). Entity không thể dẫn nguồn → noindex thay vì card rỗng.
  2. Tagline: **PHẢI sửa vì copy đề xuất cũ chứa claim BỊA** ("kiểm chứng thực địa — mỗi điểm ghi ngày ghé") mâu thuẫn sự thật (nội dung LLM-hỗ-trợ, tổng hợp nguồn công khai). Thay bằng tuyên bố CHÍNH XÁC: *"Tổng hợp và biên tập từ nguồn công khai, có trích dẫn và link gốc; thông tin mùa vụ/giá/giờ chỉ tham khảo, vui lòng xác nhận với cơ sở."* — đây là Trustworthiness thật. Đổi copy trong legalContent/onboardingContent/pageManifest là ngoài task hiện tại → ghi Backlog.

---

**P1-3 · Fallback JSON-LD là dead code (rich-result fragile)** — effort S
- **Vấn đề:** `fallbackJsonLdScripts` (dia-diem/[id].vue:949-1104) định nghĩa đầy đủ nhưng `jsonLdScripts` (1116-1118) chỉ `return backendJsonLdScripts.value`. Backend call `.catch(() => null)` → nếu /seo/jsonld fail → mất BreadcrumbList + entity schema + FAQ, chỉ còn WebSite toàn cục.
- **CÁCH SỬA (chọn 1, KÈM cập nhật test smoke.test.ts:358 có giải trình):**
  - **Hướng A (khuyến nghị):** XÓA dead code fallback; làm cứng backend — khi cache miss cho entity_id thì đọc live `db.get_entity` thay vì trả 404; đảm bảo endpoint không bao giờ trả rỗng cho entity public.
  - **Hướng B:** `jsonLdScripts = backendJsonLdScripts.value.length ? backendJsonLdScripts.value : fallbackJsonLdScripts.value`; BẮT BUỘC sửa smoke.test.ts:353-358 đổi từ "backend-only" sang "backend-first + fallback resilient" + ghi lý do (đây là thay đổi hành vi có chủ đích, KHÔNG phải yếu-đi-assertion).

---

**P1-4 · lastmod đồng nhất + changefreq='weekly' hardcoded** — effort M
- **Bằng chứng:** seo.py:1180 hardcode `changefreq="weekly"`; `<lastmod>2026-06-28</lastmod>` × 1.730.
- **CÁCH SỬA:**
  1. **NGAY:** map changefreq theo type. Entity tĩnh (history/nature/attraction/person/craft_village/dish/product) → 'monthly'/'yearly'; chỉ 'event' → cadence cao. Sửa 1 dòng.
  2. **lastmod:** BỎ lastmod khỏi entity detail cho tới khi có ngày thật (`_url_xml` đã hỗ trợ `lastmod=None`). Một lastmod sai đồng loạt tệ hơn không có.
  3. **VỀ SAU:** AdminCP đóng dấu updatedAt THẬT mỗi lần biên tập → bật lại lastmod per-entity.
- **§B3/B4:** qua ROADMAP task + test seo.py trước; ghi Backlog nếu chưa có task.

---

**P1-5 · 18 ward rỗng + summary ~24 từ vẫn index — thin doorway** — effort S
- **Bằng chứng:** xa-phuong/[id].vue chỉ render `data.place.summary` (dòng 58) + map + grid; empty-state "Trang đang được xây dựng" (101-107) mà KHÔNG noindex; seo.py:1157-1166 phát tất cả 125 place không gate. Median ward summary 24 từ; 18/125 có 0 con; 33/125 ≤1 con.
- **CÁCH SỬA (idiomatic — repo đã có tiền lệ noindex,follow ở tim-kiem/tai-khoan/nguoi-dung):**
  1. xa-phuong/[id].vue: `robots: () => (totalContent.value <= 1 && wordCount(summary) < 60) ? 'noindex,follow' : undefined` (dùng `totalContent` computed sẵn dòng 207-210, KHÔNG "all children").
  2. seo.py:1157-1166: content gate + `_is_public` cho vòng place; đếm con nội dung trong `_load()`, không query DB trong sitemap.
  3. **NỚI khi có prose bản địa thật** (≥60 từ HOẶC ≥2 con). Unlock bằng VIẾT nội dung (đặc sản gắn tên xã, chợ/bến/đình có thật) qua `viet-content-optimizer` — KHÔNG nhồi 60 từ filler.
- **§B3/B4:** test trước (ward rỗng KHÔNG có trong sitemap; ward đủ nội dung CÓ).

---

**P1-6 · Positioning: hero/eyebrow đóng khung ĐBSCL/3-tỉnh thay vì Vĩnh Long** — effort S/M
- **Bằng chứng:** gioi-thieu.vue:10 "Miền Tây không thiếu chỗ để đi"; du-lich.vue:12 "Ba tỉnh, một nhịp sông" + eyebrow "ĐỒNG BẰNG SÔNG CỬU LONG"; cong-dong.vue:9 "SỔ TAY MIỀN TÂY" + "NGƯỜI MIỀN TÂY"; dia-diem/index.vue:86 "điểm đến miền Tây".
- **CÁCH SỬA (theo NGỮ CẢNH, KHÔNG find-replace mù):**
  - Nhãn thương hiệu (title/H2/eyebrow/og) → "Vĩnh Long mới" + đưa Vĩnh Long lên chủ ngữ. du-lich.vue:12 → "Vĩnh Long mới: từ gạch gốm Mang Thít tới chùa Khmer Trà Vinh." eyebrow: bỏ "ĐBSCL ·", giữ "VĨNH LONG · BẾN TRE · TRÀ VINH".
  - cong-dong: swap 1-đổi-1 (đã trong working tree): "NGƯỜI VĨNH LONG", chatbot "Bạn muốn hỏi gì về Vĩnh Long?".
  - **GIỮ** chỗ "miền Tây" trong câu địa-văn-hoá chung (theo-mua.vue:168 "Khí hậu miền Tây") — đổi máy móc sẽ sai nghĩa.
  - **Severity note:** đây là fix CHẤT LƯỢNG/định-vị, KHÔNG phải chống-spam. Đừng bán như giảm penalty. 31 occurrence "miền Tây" ở 11 file → mở Backlog quét toàn site.

---

**P1-7 · Design: StorySpread stack 3 AI-slop tell + tái dùng 1 ảnh sông chung** — effort M
- **Bằng chứng:** StorySpread.vue:14-22 centered copy + serif-italic accent 1 từ (131-136) + `/img/spread/song-nuoc.webp` dùng 2 lần (index.vue:214, 311); subtitle "miền phù sa Cửu Long".
- **CÁCH SỬA:**
  1. Layout: bỏ centered card → left-align trên grid bất đối xứng, title serif lớn overlap mép ảnh (z-index). Bỏ gimmick italic-1-từ, thay bằng tương phản scale/weight.
  2. Ảnh: thay bằng ảnh AI-gen ĐẶC THÙ địa danh thật (lò gạch Mang Thít / chùa Khmer / cù lao An Bình) qua `scripts/gen_image.py`; đặt tên file theo địa danh (mang-thit-lo-gach.webp), KHÔNG "song-nuoc". Storyland-card ảnh RIÊNG khớp story đang xoay (thêm field `image` vào STORIES[]).
  3. Subtitle: bỏ filler → câu cụ-thể-Vĩnh-Long. **Đã verify data:** Chợ nổi Trà Ôn THUỘC Vĩnh Long (docs/data-verification-report.md:708); Cái Bè thuộc Tiền Giang → ĐỪNG gán.
  4. §B1 backup asset; giữ srcset 640/1024/1536.

---

**P1-8 · Design: ảnh AI ship với alt=tên-entity, không nhãn AI** — effort M
- **Bằng chứng:** EntityCard.vue:5-6 + dia-diem/[id].vue:24-25 `:alt="entity.name"`; entity có ảnh AI → KHÔNG có disclosure (trong khi no-photo CÓ nhãn honesty dòng 77).
- **CÁCH SỬA (khung = trung thực + E-E-A-T + accessibility, KHÔNG "tránh phạt Google"):**
  1. Alt mô tả cảnh cụ thể-địa-phương (VD "Cù lao An Bình nhìn từ bến sông, hàng dừa nước và ghe chở trái cây") — trung thực, KHÔNG nhồi từ khoá, KHÔNG ngụ ý cảnh-thật-đã-xác-minh.
  2. Caption/credit AI trên cover: "Ảnh dựng bằng AI theo mô tả — minh hoạ, chưa phải ảnh chụp tại chỗ". Thêm nguồn `'ai_generated'` vào image_credits (types/index.ts:94), `imageCredit` render nhãn khi nguồn=AI.
  3. **TUYỆT ĐỐI KHÔNG giả EXIF/credit/tác giả.** Ưu tiên thay ảnh thật/UGC cho flagship.

---

### 🟢 P2 — Polish & phòng thủ bổ sung

- **[content]** /cong-dong: prompt neo entity ("Bạn vừa ghé cù lao An Bình? Kể giá vé thật, chỗ gửi xe, mùa nên đi."); feed rỗng → noindex tới khi có bài thật.
- **[content]** /gioi-thieu: thêm khối tác giả thật; mở bài neo địa phương thay câu triết lý vùng.
- **[technical-seo]** Filler template ("ẩm thực miền Tây" 15, "Tọa lạc" 65, "một trong những" 67) → viết lại qua skill, mỗi trang index cần ≥1 sự thật bản địa vinhlongtourist.vn không có.
- **[technical-seo]** 16 itinerary trong sitemap không qua `_is_public` → thêm gate. robots.txt: đưa Disallow vào CẢ group Googlebot; cân nhắc giữ /tim-kiem crawlable (bỏ Disallow) để SearchAction hợp lệ, chỉ noindex trang kết quả.
- **[technical-seo]** Schema Product: bỏ `offers.availability:InStock` (model chỉ-giới-thiệu); Event free dùng `isAccessibleForFree:true` thay Offer price 0. **KHÔNG khai giá không có giao dịch thật** (structured-data spam).
- **[eeat]** Bổ sung ≥2-3 chi tiết first-hand/entity index (giá+thời điểm ghi nhận, đỗ xe, giờ đông/vắng, tên dân gian dễ đi lố) + ≥1 nhược điểm trung thực. Nhân rộng công thức tép khô Mỹ Long.
- **[design]** Grain overlay áp cho placeholder nhưng KHÔNG cho ảnh AI thật → thêm grain/duotone nhẹ lên ảnh AI (giữ CWV nhẹ, tiled data-URI).
- **[design]** Emoji làm functional icon → thay bằng line-icon set khớp giọng terracotta/serif (repo đã có inline SVG); emoji chỉ giữ chỗ trang trí thưa.
- **[design]** Gradient placeholder 96.5% → tăng hue jitter/2-3 archetype/category; gate flagship sang ảnh AI/UGC trước. Coi photo coverage là metric visual-quality chính.

---

## 4. Bộ quy tắc VIẾT chống-đọc-như-AI (tiếng Việt Vĩnh Long)

> Mục đích: TÌM chỗ viết dở → VIẾT LẠI CHO THẬT. KHÔNG phải né máy dò. Không cụm nào một mình chứng minh "văn AI" — cần CHÙM dấu hiệu. Grep để khoanh vùng, người đọc để phán.

### Danh sách cụm CẤM (filler phủ-toàn-vùng)
| Cấm | Vì sao | Thay bằng |
|---|---|---|
| "miền Tây sông nước (hữu tình)", "sông nước Nam Bộ", "vùng sông nước" | test đổi-tên-tỉnh fail | tên sông thật: Cổ Chiên / Hàm Luông / Măng Thít |
| "điểm đến (lý tưởng / hấp dẫn / không thể bỏ lỡ)" | superlative không dẫn chứng | 1 chi tiết giác quan + 1 dẫn chứng |
| "được nhiều du khách biết đến", "nổi tiếng" (trơ) | quảng cáo không nguồn | "công nhận [năm]", số lượng, tên người/HTX |
| "đậm đà bản sắc", "hiền hoà mến khách" | áp cho mọi tỉnh | phương ngữ / nghề / lễ hội có ngày âm lịch thật |
| "thuần khiết nhất vùng", "danh tiếng", "toàn cầu" | superlative tự phong | fact kiểm chứng được, hoặc bỏ |
| "Tọa lạc tại...", "Nằm ở...", "Là một trong những..." (mở bài) | 112+96 formula opening | mở bằng mùi/âm thanh/hành động cụ thể |
| "Hãy đến và cảm nhận", "Đừng bỏ lỡ" (kết) | CTA sáo | kết bằng giờ/cách đi/mùa/mẹo, hoặc dừng luôn |
| "thơ mộng, bình yên và hữu tình" (rule of three) | cụm 3-tính-từ cân đối | 1 tính từ cụ thể + số lượng lẻ (2/4 ý lệch) |
| "Bên cạnh đó / Ngoài ra / Đặc biệt," đầu câu | scaffold | nối ý bằng nội dung, không từ nối trang trí |

### Công thức thay thế
1. **Test "thay tên":** dán tên xã/entity khác vào câu — nếu vẫn "đúng" → câu vô giá trị, viết lại.
2. **Mỗi câu ≥1 danh từ riêng/con số** chỉ đúng entity này (năm, mùa vụ, tên HTX, quãng đường, giá, tỷ lệ công thức).
3. **Số liệu = tín hiệu "đã đến thật":** giờ mở/đóng, khoảng giá thật, năm sự kiện, tháng âm/dương chính xác.
4. **≥1 khiếm khuyết trung thực** ("đường ổ gà mùa mưa", "chỉ nhận tiền mặt", "mùa khô kênh cạn") — đáng giá hơn 10 tính từ khen.
5. **Giọng VĨNH LONG:** mỗi khi định viết "miền Tây" → hỏi "chỗ NÀY khác chỗ khác ở ĐBSCL chỗ nào?" và viết cái khác biệt.

### Ví dụ "trước → sau" (từ chính nội dung site)
**[1] restaurant template:**
- TRƯỚC: "Nhà hàng Sáu Tú — nhà hàng ẩm thực miền Tây tại 284 Phạm Hùng... Phục vụ các món đặc trưng sông nước Nam Bộ trong không gian thoáng mát."
- SAU: "Quán Sáu Tú ở 284 Phạm Hùng nổi món cá tai tượng chiên xù cuốn bánh tráng và lẩu mắm cá linh (mùa nước nổi tháng 9-11). Bàn đặt trước cuối tuần vì kín chỗ trưa. Có sân đậu ô tô, nhận tiền mặt và chuyển khoản." *(chỉ khi các fact này ĐÚNG — nếu chưa biết món signature thật thì noindex, KHÔNG bịa)*

**[2] điểm tham quan formula opening:**
- TRƯỚC: "Tọa lạc tại trung tâm thành phố, Thiền viện Trúc Lâm Trà Vinh là một trong những điểm đến tâm linh không thể bỏ lỡ — nơi du khách hòa mình vào không gian thanh tịnh."
- SAU: "Thiền viện Trúc Lâm Trà Vinh nằm trong rừng cây sao dầu ở [xã cụ thể], khánh thành năm [năm]. Chánh điện quay ra hồ sen, sáng sớm 5-6h vắng và mát nhất. Mở cửa tự do, nên mặc kín vai gối." *([xã]/[năm] phải verify trước khi publish)*

**[3] rule-of-three + phủ-vùng (chuẩn vàng có sẵn trong corpus — Cồn Bửng):**
- TRƯỚC: "Cồn ... mang vẻ đẹp thơ mộng, bình yên và hữu tình của miền Tây sông nước, là điểm đến lý tưởng để du khách đắm mình vào thiên nhiên."
- SAU: "Khi thủy triều rút, bãi cồn lộ ra ba hồ nước dân địa phương gọi là 'hủng', nước phẳng tắm được không lo sóng. Người ta ra cào nghêu, bắt sò cùng ngư dân. Rằm tháng Giêng có Lễ hội Nghinh Ông."

**[4] superlative không dẫn chứng:**
- TRƯỚC: "cù lao bưởi Năm Roi... trải nghiệm miệt vườn thuần khiết nhất vùng Bình Minh... vùng chuyên canh bưởi Năm Roi danh tiếng"
- SAU: "Cù lao trên sông Hậu thuộc vùng gốc bưởi Năm Roi Bình Minh — giống bưởi ít hạt, ruột vàng, vị ngọt pha chua thanh. Đây là nơi giống bưởi này có xuất xứ." *(bỏ "thuần khiết nhất"/"danh tiếng"; KHÔNG gán mốc giải thưởng chưa có nguồn)*

---

## 5. Tái định vị "Vĩnh Long không phải miền Tây"

**Nguyên tắc:** Vĩnh Long (mới) là THƯƠNG HIỆU/chủ ngữ; Bến Tre + Trà Vinh là PHẦN của Vĩnh Long mới, không phải "3 tỉnh ngang hàng" hay "một góc ĐBSCL".

| Chỗ (path:line) | Hiện tại | Diễn đạt lại |
|---|---|---|
| gioi-thieu.vue:10 | "Miền Tây không thiếu chỗ để đi..." | "Từ lò gốm đỏ ven sông Cổ Chiên tới rặng dừa cù lao — Vĩnh Long mới có thứ đáng ghé ở từng khúc quanh. Việc của tụi mình là chỉ cho bạn khúc nào, vì sao." *(KHÔNG lặp bộ ba tỉnh đã có ở province-band dưới)* |
| du-lich.vue:12 | "Ba tỉnh, một nhịp sông." | "Vĩnh Long mới: từ gạch gốm Mang Thít tới chùa Khmer Trà Vinh." |
| du-lich.vue:10 eyebrow | "ĐỒNG BẰNG SÔNG CỬU LONG · VĨNH LONG—BẾN TRE—TRÀ VINH" | bỏ "ĐBSCL ·", giữ "VĨNH LONG · BẾN TRE · TRÀ VINH" |
| cong-dong.vue:9,17 | "SỔ TAY MIỀN TÂY", "NGƯỜI MIỀN TÂY" | "SỔ TAY VĨNH LONG", "NGƯỜI VĨNH LONG" (đã trong working tree) |
| dia-diem/index.vue:86 | "điểm đến miền Tây" | "điểm đến Vĩnh Long mới" |
| index.vue:387 (OCOP title) | "Mang cả miền Tây về làm quà" | "Dừa sáp Cầu Kè, kẹo dừa Bến Tre — gói quà xứ này" |
| index.vue:398 (SPREAD subtitle) | "một miền phù sa Cửu Long, trái ngọt bốn mùa và những phiên chợ nổi" | "Nơi sông Cổ Chiên tách nhánh ôm 4 cù lao An Bình — gốm đỏ Mang Thít, bưởi Năm Roi, chợ nổi Trà Ôn họp lúc tinh mơ." *(đã verify: Trà Ôn thuộc VL; KHÔNG gán Cái Bè)* |
| su-kien.vue:136 | "Sự kiện tại miền Tây" | "Sự kiện ở Vĩnh Long, Bến Tre, Trà Vinh" |

**Từ khoá bản địa ưu tiên (thay "miền Tây"):** sông Cổ Chiên / Hàm Luông / Măng Thít, gốm đỏ Mang Thít, bánh tráng Mỹ Lồng, quýt/dừa sáp Cầu Kè, bưởi Năm Roi Bình Minh, cù lao An Bình / Bình Hòa Phước, phà Đình Khao, bún nước lèo (Khmer), chợ nổi Trà Ôn.

**Cảnh báo:** đổi theo NGỮ CẢNH. Nhãn thương hiệu → "Vĩnh Long mới"; câu mô tả địa-văn-hoá chung của vùng (khí hậu, thổ nhưỡng) → giữ hoặc thay bằng danh từ cụ thể, KHÔNG find-replace mù. KHÔNG nhồi từ khoá "Vĩnh Long" máy móc (snake-oil ngược).

---

## 6. Tín hiệu E-E-A-T cần thêm & nơi gắn

| Tín hiệu | Google hỏi | Nơi gắn | Ràng buộc trung thực |
|---|---|---|---|
| **Byline tác giả** | "Who — do pages carry a byline?" | dia-diem/[id].vue + xa-phuong/[id].vue; trang `/tac-gia` | phân loại theo `verified`; KHÔNG byline ma |
| **Ngày kiểm chứng thật** | care/freshness | trust card | `attributes.verifiedAt`; "chưa rõ" nếu chưa; KHÔNG đóng dấu import |
| **Nguồn (citation)** | Trust (quan trọng nhất) | trust card + JSON-LD `citation` | trích đoạn+link §B6; ưu tiên history/di tích/OCOP |
| **Nhãn AI (How)** | "Is AI-generation self-evident?" | caption ảnh AI; khối AITravelTips/SmartRecommendations | "Gợi ý tạo bằng AI, chưa kiểm chứng tại chỗ" |
| **First-hand (Experience)** | "first-hand... visiting a place" | body entity | ≥2-3 chi tiết chỉ-người-đến-mới-biết + ≥1 nhược điểm |
| **Ảnh thật** | bằng chứng Experience mạnh nhất | hero/card flagship | caption cụ thể; KHÔNG giả EXIF |
| **Trang "Về trang này" / phương pháp** | Who/How/Why | /gioi-thieu hoặc /tac-gia | mô tả quy trình biên tập THẬT |
| **BreadcrumbList/TouristAttraction/FAQPage JSON-LD** | rich-result + AI-citation | per-entity, khớp UI on-page | chỉ markup field thật hiển thị |

**Nhãn AI cho khối runtime (dia-diem/[id].vue:241 LazyAITravelTips, :249 LazySmartRecommendations):** gắn "Gợi ý tạo bằng AI, chưa kiểm chứng tại chỗ" — vừa đúng chính sách "disclose How" vừa dời gánh nặng E-E-A-T sang phần người-viết.

---

## 7. Ảnh AI: rủi ro & lộ trình giảm phụ thuộc

**Rủi ro kép:**
1. **Đọc-như-AI:** cx/gpt-5.5-image cho ánh sáng phẳng, "quá đẹp giả", lỗi bàn tay/chữ biển hiệu/hoạ tiết Khmer-gốm. Người bản địa NHẬN RA NGAY cảnh "không có thật ở Vĩnh Long" → mất niềm tin + phá định vị.
2. **Originality:** ảnh AI KHÔNG phải "unique content chứng minh trải nghiệm thật". Ảnh AI + mô tả template = đúng hồ sơ scaled-content.

**Khung đúng:** ảnh KHÔNG phải tín hiệu-phạt độc lập theo policy Google — nó là MỘT cách thêm Experience. Rủi ro cốt lõi vẫn là ~1.600 trang thin. Vì vậy thứ tự:

1. **TRƯỚC HẾT nâng depth per-page** cho entity flagship (đòn bẩy chính).
2. **Ảnh AI-gen** (CHỈ cx/gpt-5.5-image §feedback — KHÔNG stock/Wikimedia/UGC-làm-nguồn-crawl) cho entity chủ lực + **caption trung thực + nhãn "minh hoạ AI"**. Đặt tên file theo địa danh cụ thể.
3. **Mở đường UGC ảnh người dùng** — nguồn ảnh gốc hợp pháp mạnh nhất site được re-host (§B6). Lưu ý §NĐ147: xác thực SĐT trước khi cho đăng.
4. **Ảnh thật do chủ dự án/CTV chụp** cho ~20-50 flagship — khác biệt lớn nhất, hợp pháp, chống-slop tự nhiên (bóng đổ thật, khiếm khuyết đời thực).
5. **Entity chưa flagship + không ảnh + desc ngắn** → noindex tạm.

**Ưu tiên đâu trước:** entity top-traffic/OCOP (dừa sáp Cầu Kè, gốm Mang Thít, bưởi Năm Roi, chùa Khmer, cù lao An Bình) → 1 ảnh signature/entity. GIỮ nhãn honesty "chưa có ảnh thật" (dòng 77) cho phần còn lại — đó là tín hiệu Trust tốt.

**TUYỆT ĐỐI KHÔNG:** giả EXIF/geo/ngày chụp để "qua" detector — đó là deception, đúng thứ SpamBrain phạt.

---

## 8. Checklist "trước khi publish 1 trang"

> Trang không đạt các mục CỨNG → noindex,follow (không index để "phủ SEO").

**A. Giá trị & độ đặc thù (cứng):**
- [ ] Mô tả ≥120 từ ĐẶC THÙ (hoặc có ảnh thật) — KHÔNG độn chữ cho đủ số
- [ ] Test "thay tên": đổi tên entity vào mọi câu → KHÔNG câu nào vẫn "đúng"
- [ ] ≥1 sự-thật-bản-địa vinhlongtourist.vn KHÔNG có (tên rạch/HTX/năm/giá/mùa)
- [ ] body KHÔNG in lại verbatim câu lead/summary
- [ ] ≥2-3 chi tiết first-hand (giá+thời điểm, đỗ xe, giờ đông/vắng) + ≥1 nhược điểm trung thực

**B. Chống-đọc-như-AI (mềm — cần chùm dấu hiệu):**
- [ ] KHÔNG mở bài "Tọa lạc/Nằm ở/Là một trong những"
- [ ] KHÔNG kết "Hãy đến và cảm nhận/Đừng bỏ lỡ"
- [ ] KHÔNG cụm filler "miền Tây sông nước", "điểm đến lý tưởng", "đậm đà bản sắc"
- [ ] KHÔNG rule-of-three cân đối; KHÔNG scaffold "Bên cạnh đó/Ngoài ra" đầu câu
- [ ] KHÔNG superlative tự phong không nguồn ("nhất vùng", "toàn cầu")

**C. E-E-A-T & trung thực (cứng):**
- [ ] Có byline phân loại đúng mức xác minh (KHÔNG gắn ngày "kiểm chứng" cho entity chưa đi thực tế)
- [ ] Dữ kiện cứng (năm/dân số/OCOP) CÓ nguồn hoặc kiểm chứng được — KHÔNG bịa
- [ ] Ngày hiển thị là ngày THẬT (kiểm chứng/import ghi rõ), KHÔNG đóng dấu freshness giả
- [ ] Ảnh AI có caption + nhãn "minh hoạ AI"; alt mô tả cảnh trung thực; KHÔNG giả EXIF
- [ ] Định vị: nhãn thương hiệu là "Vĩnh Long", KHÔNG "miền Tây" chung

**D. Technical (cứng):**
- [ ] `robots` khớp `is_index_worthy` (noindex,follow nếu chưa đạt); sitemap ↔ page đồng bộ
- [ ] JSON-LD chỉ markup field thật hiển thị; KHÔNG khai Offer/price khi model chỉ-giới-thiệu
- [ ] §B1 backup nếu chạm dữ liệu; §B4 test nếu đổi schema/behavior; 1 task/commit

---

## Phụ lục — Điều KHÔNG nên làm (loại vì snake-oil / sai)

- ❌ **AI-humanizer / spinning / paraphrase để qua detector** — Google phạt unhelpful-at-scale, không phạt "giống AI". Humanizer không thêm giá trị, để lại pattern SpamBrain bắt được.
- ❌ **Chặt câu tạo "burstiness" / luật "≤1 em-dash/đoạn"** — cosmetic anti-detector. Sửa dấu câu CHỈ vì đọc dễ hơn.
- ❌ **Giả EXIF/geo/credit ảnh** — deception, IPTC 2025.1 có field AI nhưng để MINH BẠCH, không để giả.
- ❌ **Đổi lastmod/updatedAt cho "tươi"** khi nội dung chưa đổi — Google liệt kê là search-engine-first.
- ❌ **Nhồi từ khoá "Vĩnh Long"** máy móc để né generic-detector — snake-oil ngược.
- ❌ **Độn chữ cho đủ word-count** — Google phủ nhận "preferred word count".
- ❌ **Bịa fact/mốc lịch sử/giải thưởng/số liệu** để nghe cụ thể hơn — vi phạm anti-hallucination + tự phá E-E-A-T (sai còn tệ hơn generic-đúng).
- ❌ **llms.txt / nội dung riêng cho AI bot** — GEO "vẫn là SEO" (Google 2026); không cần.
- ❌ **Blanket-gán cổng tỉnh chung** cho entity chưa từng lấy nguồn ở đó — misleading-attribution tệ hơn card trust vắng.

**Files load-bearing đã verify:** `C:\Code\vinhlong360\agent\seo.py` (_is_public:1043, vòng entity:1169-1183 hardcode changefreq weekly:1180, vòng place không gate:1157-1166), `C:\Code\vinhlong360\web-nuxt\pages\dia-diem\[id].vue` (no robots meta; fallbackJsonLd dead code:949-1104; trustVisible:828), `C:\Code\vinhlong360\web-nuxt\pages\xa-phuong\[id].vue` (summary-only:58, empty-state không noindex:101-107), `C:\Code\vinhlong360\web-nuxt\nuxt.config.ts:60` (global index,follow). "miền Tây" = 35 occurrence / 11 file (verified).
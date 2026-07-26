> STATUS: active — thiết kế (design) cho việc fork vinhlong360 → dongthap360. Chưa thực thi. Kế hoạch chi tiết (plan) viết sau khi chủ dự án duyệt spec này.

# Thiết kế: Fork vinhlong360 → Đồng Tháp 360 (dự án độc lập)

## 0. Một dòng

Nhân bản codebase vinhlong360 thành **một dự án độc lập `dongthap360`** ở thư mục local riêng, bằng cách **tách toàn bộ đặc-thù-tỉnh cấp code về một lớp `province.config` duy nhất**, xoá dữ liệu Vĩnh Long, rồi cấu hình lại cho tỉnh Đồng Tháp mới. Hai dự án **không chia sẻ gì** sau khi tách — mỗi cái một thư mục, một DB, một domain, tự do phân kỳ.

## 1. Quyết định đã chốt (trong phiên brainstorm 2026-07-13)

1. **Hard-fork**, không multi-tenant. Hai dự án hoàn toàn tách biệt.
2. **Fork trực tiếp** vào thư mục mới `C:/Code/dongthap360` (copy từ vinhlong360). **KHÔNG** có thư mục "template" thứ 3, **KHÔNG** cherry-pick/sync qua lại. VL (`C:/Code/vinhlong360`) **giữ nguyên, không đụng**.
3. **Có tách `province.config`** (không copy-thô), vì đó là cách đúng & ít rủi ro nhất để cấu hình lại — đặc biệt để gỡ 2 landmine cấu trúc (xem §4). Kết quả config-driven cũng là thứ sẽ copy lại cho tỉnh #3–#5 sau này (copy chứ không link).
4. Định hướng 3–5 tỉnh về lâu dài ⇒ đầu tư tách config là xứng đáng; nhưng mỗi tỉnh là **một bản copy độc lập**.

## 2. Bối cảnh Đồng Tháp mới (khác Vĩnh Long ở đâu)

- **Vĩnh Long mới** = Vĩnh Long + Bến Tre + Trà Vinh → **3 vùng cũ**.
- **Đồng Tháp mới** = Đồng Tháp + Tiền Giang → **2 vùng cũ**. Số xã/phường khác, bounding-box địa lý khác, danh sách tỉnh láng giềng khác.
- ⚠️ **Số liệu hành chính chính xác của Đồng Tháp mới (roster xã/phường, tỉnh lỵ, bbox, láng giềng) là dữ liệu SP2 — phải nghiên cứu/kiểm chứng riêng, KHÔNG bịa.** Spec này chỉ thiết kế cơ chế; giá trị cụ thể điền ở SP2.

## 3. Kiến trúc: `province.config` là nguồn-sự-thật duy nhất

Phát hiện cốt lõi từ khảo sát: bản đồ vùng `{vinh-long, ben-tre, tra-vinh}` bị **định nghĩa lại độc lập ≥15 lần ở backend + ~8 lần ở frontend**, cộng **3 bounding-box khác nhau** cho cùng một vùng, **2 danh sách OUTSIDE**. Không có SoT. Vì vậy keystone là tạo một file config và trỏ mọi bản sao về đó.

### 3.1 Lược đồ `province.config`

Một nguồn, đọc bởi cả backend (`agent/province_config.py`) lẫn frontend (`web-nuxt/app/province.config.ts` hoặc JSON build-time). Tối thiểu:

```
provinceName            # "Đồng Tháp" (tỉnh mới)
provinceSlug            # "dong-thap"
brand                   # "dongthap360"
domain                  # "dongthap360.vn"
cdnBase                 # "cdn.dongthap360.vn"
legalEntity, byline, hotline, contact{email, zalo}

regions[]               # MẢNG ĐỘNG (VL=3, ĐT=2). Mỗi phần tử:
  { slug, label, emoji, icon, color, blurb, motif, image,
    legacyProvinceName, center:[lng,lat] }
crossRegion             # thay khái niệm "lien-vung" (nhãn liên-vùng)

neighbors[]             # thay OUTSIDE: tỉnh láng giềng để LỌC discovery
neighborsLocOnly[]      # thay OUTSIDE_LOC
bbox { lat:[min,max], lon:[min,max] }   # gộp 3 bbox đang lệch
floodMonths[]           # mùa vụ vùng (kiểm cho ĐT)

mergeNarrative { newName, oldProvinces[], resolution, wardCount }
llmRegionPhrase         # chuỗi nhúng vào prompt LLM
adminUnits { expectedWardCount, levels[] }

seoDefaults { title, description }
themeColor { light, dark }
smsBrandname
```

### 3.2 Ba nơi canonical phải trỏ về config (rồi lan ra ~23 bản sao)

- Backend: `agent/knowledge.py` `AREA_META` + `_AREA_PROV` · `agent/discover_province.py` `REGIONS`/`OUTSIDE`.
- Frontend: `web-nuxt/composables/useConstants.ts` `AREA_META`.
- Sau đó thay: ~15 bản sao area-map backend (seo.py, proactive.py, realtime.py, mcp_server.py, memory.py, agentic_rag.py, itinerary_gen.py, gpt55_quality_burst.py, learn_loop.py, checkpoints.py, recommender.py…), 2 bbox (`database.py:103`, `geocode.py:37-41`), 2 OUTSIDE (`discover_province.py`, `auto_learn.py`), enum area trong tool-schema (`tools.py` 10+ chỗ).

## 4. Ba tầng de-brand + refactor CẤU TRÚC (không chỉ đổi giá trị)

Khối lượng đo được (~200 điểm / ~136 file):

| Tầng | Khối lượng | Xử lý |
|---|---|---|
| **T1 — CONFIG** (địa lý/danh tính) | ~110 BE + ~35 FE | Đọc từ `province.config`. **Bao gồm refactor cấu trúc** (§4.1). |
| **T2 — CMS-DEFAULT** | ~40 BE + ~25 FE | `seed_site_settings.py` generate default từ config; footer "N vùng" dựng từ `regions[]`. Admin chỉnh tiếp qua AdminCP. |
| **T3 — CONTENT** (copy đặc-tỉnh) | ~280 BE + ~40 FE | **Xoá/neutral-hoá** trong bản fork. Regen cho Đồng Tháp là **việc SP2** (skill nội dung + discovery pipeline). |
| **T4 — INFRA** (domain/cookie/deploy) | ~20 BE + ~15 FE | Gom về token `{{DOMAIN}}/{{BRAND}}`; hợp nhất domain allowlist. |

### 4.1 Refactor cấu trúc "N vùng" (bắt buộc — CMS không làm thay được)

Slug vùng không chỉ là dữ liệu; nó còn là **CSS class**, **key Record**, **union type**, **toạ độ chia đều cho đúng 3**. Cần:

- **CSS `.area-<slug>` → biến `--area-color` inline** theo `region.color` (pattern `areaTint` đã có ở `khu-vuc/[area].vue`). Áp cho `catalog.css`, `xa-phuong/[id].vue`, `dia-diem/index.vue`, `tuyen-duong.vue`.
- **`mergeInto()` (`useConstants.ts`) phải cho phép THAY THẾ base**, không chỉ restore — hiện luôn khôi phục 3 key gốc nên CMS **không hạ được 3 vùng xuống 2**.
- **`type RegionSlug` union → `string`** (`useRegionPref.ts`).
- **Bỏ các `Record`/set/if cứng 3-key**: `mcp_server.py` dict literal, `memory.py`/`agentic_rag.py` 3-if detect area, `learn_loop.py` 3 regex, `proactive.py` set 3, `itinerary_gen.py:340-343` branch-by-name tip, `tuyen-duong.vue AREA_MONTH` toạ độ pin.
- **Tool enum area** (`tools.py`) generate từ `regions[]` — nếu không, LLM ép sai vùng (rủi ro hành vi, không chỉ hiển thị).

### 4.2 Landmine nguy hiểm nhất — ĐẢO NGƯỢC `OUTSIDE`

`OUTSIDE`/`OUTSIDE_KEYWORDS` của VL chứa **`tien giang, my tho, cai be, dong thap`** — **chính là lãnh thổ Đồng Tháp mới**. Nếu bê nguyên, discovery + auto_learn **từ chối toàn bộ dữ liệu hợp lệ của ĐT**. Phải điền `neighbors[]` của ĐT (khác hẳn) trước khi chạy bất kỳ discovery nào. **Đây là mục kiểm bắt buộc trước đợt nạp dữ liệu.**

## 5. Chiến lược dữ liệu

DB **không nằm trong git** ⇒ bản fork không mang DB, chỉ mang schema + migrations.

- **XOÁ khỏi fork:** `web/data.json` → `{"entities":[],"relationships":[],"itineraries":[]}`; regen `web/data.js`; xoá `agent/crawled/` (50 file), `web-nuxt/public/img/entities/` (60 ảnh), `img/area-*.webp`, `img/spread/`, `web-nuxt/public/data/areas.json`; dọn artifact local (`agent/data/*.db`, `geocode_cache.json`, `discovery_cursor.json`).
- **GIỮ + tham số hoá:** `init.sql` + 69 migrations (province-agnostic sẵn); pipeline nạp; `seed_site_settings.py` (generate từ config).
- **Nới landmine giả định 124 xã/phường:** `scripts/validate_data.py` (`EXPECTED_XA_PHUONG=124`), `tests/test_validate_data.py` (test roster-124 + id cứng), comment `database.py:1492`, bbox null-hoá toạ độ (`database.py:103`, `geocode.py`), gate `PG_REQUIRED_SCHEMA_VERSION`.
- **Quy trình nạp dữ liệu tỉnh mới (SP2):** `apply_migrations.py --init-baseline` → `seed_site_settings.py` → `discover_province.py --apply` (LLM liệt kê → lọc `neighbors` → dedup → geocode OSM → DB) → `export_data.py` → `export_fe_data.py` → `gen_entity_images.py` (ảnh AI) → build FE.

## 6. Hạ tầng

- **Token-hoá:** `nginx.conf`/`nginx-ssl.conf`, `scripts/deploy.sh` (hiện cứng `REMOTE=/opt/vinhlong360` + service `vl-agent/vl-nuxt/vl-bot`), `scripts/ops/*`, `.env` → `{{DOMAIN}} {{BRAND}} {{DB_NAME}} {{DB_USER}} {{PREFIX}} {{AGENT_PORT}}/{{NUXT_PORT}}/{{BOT_PORT}} {{REMOTE_PATH}} {{CDN_BASE}} {{DEPLOY_HOST}}`.
- **Domain SoT trong code** (không đọc env — rủi ro cao): `agent/auth_middleware.py` (5 khối allowlist + cookie domain, **đang lẫn `.vn`/`.com` — vá luôn**), `agent/seo.py:31` `SITE`, `agent/config.py:33,39`, `agent/storage.py` R2/S3, `web-nuxt/composables/useSeoHelpers.ts:1` `SITE_URL`, `nuxt.config.ts`, `manifest.json`, `public/llms.txt` (regen), `sw.js` cache prefix, `useRegionPref.ts` storage keys `vl360-*`.
- **VPS RIÊNG mỗi tỉnh (khuyến nghị):** VPS 1GB không chứa 2 stack; port/tên-service/path cứng ⇒ VPS riêng ít-sửa-nhất. Token-hoá vẫn đủ để "shared" khả thi về sau nếu nâng RAM.
- **Secrets:** dùng-chung = `LLM_API_KEY`, `IMAGE_API_KEY`, `WEATHER_API_KEY`, (eSMS key, map key). Per-tỉnh = `DATABASE_URL`/`POSTGRES_PASSWORD`, `ADMIN_API_KEY`, `MEMORY_ENCRYPTION_KEY`, `CSRF_SECRET`, `ESMS_BRANDNAME`, `TELEGRAM/FB/ZALO` bot, `R2/S3` bucket+keys, `TOTP_ENC_KEY`. **Việc đặt/xoay secret thật là của chủ dự án (§4 điều kiện dừng CLAUDE.md).**

## 7. Oracle verify (behavior-preserving)

Vì fork thẳng sang ĐT, ta vẫn kiểm được tính đúng của refactor bằng cách **giữ `province.config = Vĩnh Long` xuyên suốt các đợt tách config**, chỉ **lật sang Đồng Tháp ở đợt cuối**:

1. Copy VL → dongthap360 (config value = VL).
2. Tách lớp config (đợt 1–4) với config=VL → **template phải render chrome y hệt VL gốc** (test diff HTML/route chính) + bộ test hiện có (đã nới roster) xanh. ← chứng minh tách config không đổi hành vi.
3. Xoá data → verify chrome render với DB rỗng (không vỡ).
4. Lật `province.config` → Đồng Tháp + rebrand → verify không còn chuỗi "Vĩnh Long/Bến Tre/Trà Vinh" nào rò ra ngoài `province.config` (grep gate).
5. Nạp dữ liệu ĐT (SP2).

## 8. Phân đợt (SP1 — dựng khung dongthap360)

- **Đợt 0 — Bootstrap:** copy `vinhlong360` → `C:/Code/dongthap360`; git init mới (lịch sử sạch); xoá `node_modules`, `.env` (tạo `.env` mới từ `.env.example`), artifact local. *(Tạo remote/secret thật = chủ dự án.)*
- **Đợt 1 — `province.config` + SoT backend** (config=VL): tạo config, trỏ 3 canonical, gom ~15 area-map + 2 bbox + OUTSIDE→neighbors + tool enum.
- **Đợt 2 — SoT frontend + cấu trúc N-vùng:** AREA_META từ config, `.area-<slug>`→var, `RegionSlug`→string, sửa `mergeInto`, bỏ Record 3-key.
- **Đợt 3 — T2 CMS defaults generate từ config:** `seed_site_settings.py` + `pageManifest.ts` template-hoá.
- **Đợt 4 — T4 infra + domain SoT:** auth_middleware/seo/config/storage/nuxt.config/nginx/deploy tokens; vá lẫn `.vn`/`.com`.
- **Đợt 5 — Strip data + T3 neutral-hoá + lật config sang Đồng Tháp + oracle verify.**

Mỗi đợt: để hệ thống chạy được, có lệnh verify, commit nhỏ (B5). Đợt 1–4 giữ config=VL để so hành vi.

## 9. Ngoài phạm vi spec này (SP2 / việc chủ dự án)

- **Sinh nội dung Đồng Tháp** (entity, mô tả, ảnh AI, roster hành chính chính xác, editorial T3): SP2, dùng discovery pipeline + skill nội dung; phải nghiên cứu/kiểm chứng số liệu, không bịa.
- **Nghiên cứu số liệu hành chính ĐT mới** (xã/phường, tỉnh lỵ, bbox, láng giềng) để điền `province.config`.
- **Tạo remote git, đăng ký domain, đặt/xoay secret thật, deploy prod** — chủ dự án (§4 điều kiện dừng CLAUDE.md).
- **Lưu ý bảo mật:** `.env` local VL chứa secret sống; khi công khai repo fork, xoay các key per-tỉnh.

## 10. Tiêu chí nghiệm thu SP1

- Không còn chuỗi `Vĩnh Long|Bến Tre|Trà Vinh|vinhlong360` nào trong CODE ngoài `province.config` (grep gate xanh; trừ T3 đã neutral/xoá).
- Số vùng đổi được chỉ bằng sửa `province.config.regions[]` (thử N=2 không vỡ layout/logic).
- `python -m pytest -q` xanh (đối chiếu fail-đã-biết, đã nới roster-124).
- FE build + render chrome không lỗi với DB rỗng.
- `discover_province.py` với `neighbors` của ĐT không tự chặn nhầm địa danh ĐT (kiểm landmine §4.2).

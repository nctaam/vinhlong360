# Spec — Tối ưu hiệu năng & bundle toàn site (vinhlong360.vn)

**Ngày:** 2026-07-02 · **Phạm vi:** deep audit hiệu năng + bundle, cắt-ngang mọi trang public.
**Nguồn:** brainstorming 2026-07-02 (chủ chọn: focus "Hiệu năng & bundle toàn site" → cách làm "Cả hai, audit sâu").

## Mục tiêu

Cải thiện Core Web Vitals (LCP/CLS/INP) và tải trọng JS/CSS trên các trang chính, dựa
trên **đo lường thực tế** (không đoán), theo cách an toàn cho solo-dev + đĩa VPS đang đầy.

Không phải rescue (bundle đã code-split khá tốt: maplibre 1MB lazy chỉ tải ở `/ban-do`,
entry ~243KB, tổng client ~6.3MB trải trên route chunks). Đây là **tinh chỉnh có hệ thống**.

## Phi mục tiêu (YAGNI)

- KHÔNG dịch vụ perf/RUM trả phí (§B8 budget).
- KHÔNG tái tạo ảnh / đổi provider ảnh (weserv giữ nguyên).
- KHÔNG rearchitect bản đồ / maplibre.
- KHÔNG đụng ~120 file WIP chưa commit ngoài phạm vi; thay đổi phải phẫu thuật, additive.
- KHÔNG build phân tích nặng (bundle-analyzer rebuild) — đĩa chỉ còn ~33MB. Phân tích trên
  `.output` đã build sẵn + đo qua trình duyệt.

## Phương pháp — 4 pha

### Pha 1 — Đo baseline (read-only)
Dùng Chrome (extension) đo trên 5 trang đại diện của prod:
| Trang | Lý do |
|------|------|
| `/` (home) | Trang vào chính, nhiều section/ảnh |
| `/san-pham` (catalog) | Danh sách + ảnh + filter |
| `/dia-diem/[id]` (detail) | Trang chi tiết đọc nhiều attributes |
| `/ban-do` (map) | Chunk maplibre 1MB |
| `/cong-dong` (community) | Trang tương tác/hydration cao |

Ghi: LCP, CLS, INP (hoặc TBT proxy), waterfall (request lớn/chậm), JS execution/coverage.
Kết quả → bảng baseline trong `docs/perf-baseline-2026-07-02.md`.

### Pha 2 — Audit đa chiều (multi-agent, read-only)
Workflow đa-agent phân tích song song, mỗi agent 1 chiều, chấm impact×effort:
- **Bundle**: thành phần chunk từ `.output` đã build (không rebuild); vendor lớn, dup, eager import lẽ ra lazy.
- **CSS**: rule không dùng / trùng; entry CSS phình.
- **Font**: chiến lược tải (self-host Inter đã có), `display`, preload, subset.
- **Ảnh**: sizing, `loading`/`decoding`/`fetchpriority`, kích thước weserv, LCP image.
- **Cache/nén**: header Nitro (`cache-control`, br/gzip), SWR route rules, immutable assets.
- **Per-page code**: component eager lẽ ra `defineAsyncComponent`/lazy; hydration cost; `v-if` vs `v-show`; script defer.

Gộp → danh sách findings xếp hạng (impact cao/effort thấp trước).

### Pha 3 — Sửa theo đợt (mỗi đợt: nhỏ, verify)
Mỗi finding ưu tiên: sửa → `npm run build` → deploy → **đo lại metric bị ảnh hưởng** trên prod → commit. Reversible, phẫu thuật (tôn trọng cây WIP). Dừng khi hết win đáng kể.

### Pha 4 — Verify & báo cáo
Bảng before/after CWV; xác nhận không regression trang khác.

## Tiêu chí nghiệm thu
- Ít nhất cải thiện đo được ở metric yếu nhất của mỗi trang (số cụ thể chốt sau Pha 1).
- Ngưỡng giữ (mục tiêu): LCP < 2.5s, CLS < 0.1, INP < 200ms (điều kiện ~4G).
- Không regression metric khác; build + test xanh; §B invariants tôn trọng.

## Ràng buộc vận hành
- Đĩa VPS ~33MB trống → dọn artifact tạm sau mỗi build; không giữ tarball.
- Deploy phẫu thuật (frontend build; backend chỉ khi cần, chỉ file trong phạm vi).
- Đo lường = read-only, an toàn.

## Kết quả (cập nhật 2026-07-02)

**Audit (đa-agent) → site ĐÃ tối ưu tốt, không P0/P1.** Bundle lành mạnh: maplibre 1MB
lazy (chỉ 4 trang map), entry JS ~92KB gz, entry.css ~27KB brotli, không thư viện JS nặng
eager, code-split đúng, admin `ssr:false`. → đây là pass tinh chỉnh.

**Wave 1 ĐÃ LÀM + DEPLOY + VERIFY (2026-07-02):**
- **[Win lớn nhất] nginx gzip cho response proxied**: `/etc/nginx/nginx.conf` thiếu
  `gzip_proxied any;` → mọi `/api/*` JSON không nén. Đã bật (backup + `nginx -t` + reload)
  + sync vào repo `nginx.conf`. Kết quả: `/api/homepage` **59.4KB → 13.3KB trên dây (−78%)**;
  toàn bộ API/JSON + HTML SSR proxied giờ đều nén. Lợi ích mọi trang.
- **Lazy-defer** `AuthModal/ConfirmDialog/ScrollToTop` trong `layouts/default.vue` → chunk
  async riêng, khỏi entry graph.

**Wave 2/3 — CHƯA làm (giá trị thấp / rủi ro, chờ chủ chọn):**
- W2: tách khối CSS route-scoped khỏi base.css (~5KB brotli, có rủi ro unstyled); phục vụ
  `/_nuxt` tĩnh trực tiếp từ nginx (offload Node — cần mount `.output/public`).
- W3: nén lại `og-default.jpg` (363KB→~100KB, chỉ ảnh hưởng social crawler); tidy @nuxt/image
  screens/AVIF; EntityCard `priority` prop (hoãn tới khi có ảnh entity thật).
- Fonts: 1 agent audit trả stub — chưa xác nhận; Inter self-host, nhiều khả năng ổn.

## Rủi ro
- Đĩa đầy làm build/deploy fail → dọn dẹp trước mỗi wave; cân nhắc dọn `.output` cũ, node_modules cache.
- Cây WIP lớn → chỉ commit file trong phạm vi (explicit `git add`).
- CWV đo 1 lần nhiễu → đo 2-3 lần lấy trung vị.

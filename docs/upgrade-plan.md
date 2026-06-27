# Kế hoạch nâng cấp & hoàn thiện vinhlong360

Date: 2026-06-27
Status: Draft — chờ duyệt trước khi thực thi
Maturity: 5.5/10 → target 8.0/10

## Bối cảnh

Sau 13 giai đoạn phát triển, hệ thống có:
- 75+ backend modules, 60 trang frontend, 250+ API endpoints
- 1753 entities, 8415 relationships, 33 itineraries
- Admin CMS v2, social/community, chat RAG, OTP auth
- 992 root tests + ~1536 agent tests

**Bottleneck chính: nội dung, không phải code.** Hệ thống over-engineered so với lượng data — 5+ module dormant, 0% ảnh, nhiều entity thiếu attributes.

**Ngoài scope plan này:** Pháp lý (NĐ147, pháp nhân) — owner tự thực hiện.
**Nguồn ảnh:** CHỈ AI-generated (cx/gpt-5.5-image). KHÔNG dùng Wikimedia/Pexels/Unsplash/UGC (không chính xác cho địa phương cụ thể).

---

## Phase 1: Dữ liệu & Nội dung (tuần 1-2) — IMPACT CAO NHẤT

Mục tiêu: từ "code xong nhưng rỗng data" → "data đủ dùng cho launch"

### 1.1 Ảnh entity (0% → 15-20%)

| Task | Chi tiết | Estimate |
|------|----------|----------|
| AI-generated ảnh (cx/gpt-5.5-image) | Batch generate cho top types: attraction (320), dish (120), accommodation (164), craft_village (85) | 2-3 ngày |
| R2 upload pipeline | Storage.py đã sẵn (S3/R2 + WebP convert), chỉ cần config env | 0.5 ngày |
| Owner review + approve | Admin duyệt ảnh AI qua `/admin/duyet-anh` (human-in-the-loop) | Ongoing |

**Lưu ý:** Ảnh stock (Pexels/Unsplash) và UGC không chính xác cho địa phương cụ thể → chỉ dùng AI-generated, owner duyệt từng ảnh.

### 1.2 Danh bạ hành chính 124 xã/phường (GĐ13.6)

| Task | Chi tiết |
|------|----------|
| Thu thập dữ liệu thật | Nguồn: cổng DVCTT tỉnh, niên giám thống kê, B2G partner |
| Nhập qua admin UI | `/admin/entities` + type=facility, OFFICE_KIND đã có |
| Verify SĐT + địa chỉ | Kiểm tra thực tế, không bịa (§1.4) |

**Niche mạnh nhất:** Danh bạ HC = ngách trống, demand 8/10, moat cao (chỉ vinhlong360 có SĐT+AI citability).

### 1.3 Attribute enrichment

| Entity type | Coverage hiện tại | Target | Attributes cần bổ sung |
|-------------|-------------------|--------|------------------------|
| restaurant | 10% (9/94) | 50%+ | specialty, price_range, phone, hours |
| cafe | 0% (0/38) | 30%+ | specialty, price_range, phone, hours |
| craft_village | 4% (3/85) | 40%+ | specialty, phone, production |
| attraction | 24% (76/320) | 50%+ | admission, hours |
| product | 33% (72/218) | 60%+ | price, ocop stars |

### 1.4 Data quality fixes

| Issue | Count | Action |
|-------|-------|--------|
| placeId=None | 199 entity | Gán qua `/admin/chua-phan-loai` (UI sẵn) |
| SĐT sai format | 44 entity | Sửa qua admin entity edit |
| Summary >500 chars | 53 entity | Rút gọn (không rewrite, chỉ cắt thừa) |
| Season backfill | 380+ entity | Cần nguồn thật (Track-H), ưu tiên attraction + experience |
| Coordinate clusters | 229 clusters | Set `coords_approximate=true` cho entities dùng ward centroid |

---

## Phase 2: Kích hoạt tính năng dormant (tuần 2-3) — QUICK WINS

5+ module đã code xong nhưng chưa bật. Zero thêm code, chỉ cần config.

### 2.1 Caching & Performance

| Module | Action | Impact |
|--------|--------|--------|
| `prompt_cache.py` | Bật `HAS_PROMPT_CACHE=true` | Giảm token cost ~30% (cache system prompt) |
| `semantic_cache.py` | Bật `HAS_SEMANTIC_CACHE=true` | Cache reply cho query tương tự (L1 exact + L2 fuzzy) |
| `circuit_breaker.py` | Bật `HAS_CIRCUIT_BREAKER=true` | Resilience: tự ngắt LLM/weather sau 3 fail |

### 2.2 AI Features

| Module | Action | Impact |
|--------|--------|--------|
| `recommender.py` | Wire vào `/recommend` endpoint (đã mount nhưng chưa dùng recommender engine) | Smart recommendations theo co-occurrence + seasonal |
| `orchestrator.py` | Bật `HAS_ORCHESTRATOR=true` | Query routing: du lịch/ẩm thực/hành chính → agent chuyên biệt |
| `checkpoints.py` | Bật `HAS_CHECKPOINTS=true` | Multi-turn confirmation (lưu itinerary, report) |

### 2.3 Safety & Monitoring

| Module | Action | Impact |
|--------|--------|--------|
| `guardrails.py` | Bật `HAS_GUARDRAILS=true` | Input validation, PII masking, injection detection |
| `cost_tracker.py` | Bật `HAS_COST_TRACKER=true` | Token/cost attribution per user/session |
| `metrics.py` | Bật `HAS_METRICS=true` | Prometheus-compatible metrics (chat, tools, cache) |

### 2.4 Image recognition (nếu bật UGC ảnh)

| Task | Chi tiết |
|------|----------|
| Bật `HAS_IMAGE_RECOGNITION=true` | Vision API classify uploads, match entities |
| Thêm public endpoint | POST `/api/image-recognize` cho user uploads |

---

## Phase 3: Observability & SEO (tuần 3-4)

### 3.1 Monitoring (GĐ9 — 5 task pending)

| Task | Tool | Cost |
|------|------|------|
| Uptime monitoring + Telegram alerts | UptimeRobot free tier | 0đ |
| Google Search Console | DNS verify + sitemap submit | 0đ |
| Web analytics | Umami CE self-hosted trên VPS | 0đ |
| Error tracking | Sentry free tier HOẶC POST /api/client-error (đã live) | 0đ |

### 3.2 SEO improvements

| Task | Impact |
|------|--------|
| Prerender top-20 trang static (đã config trong nuxt.config.ts) | Faster TTFB cho trang quan trọng |
| aggregateRating JSON-LD | Cần review data + /ratings endpoint |
| FAQPage schema cho entity detail | Rich snippet trên Google |
| Verify sitemap-index.xml + sitemap-media.xml hoạt động | Proxy rules vừa thêm (QA-16) |

### 3.3 Frontend gaps nhỏ

| Gap | Priority | Notes |
|-----|----------|-------|
| Auth flow mở rộng (reset password, verify) | Medium | Chỉ có AuthModal, chưa có dedicated page |
| Saved items page | Low | `useFavorites` có, chưa có route riêng |
| Offline PWA caching strategy | Low | sw.js có, cần define cache strategy rõ |

---

## Phase 4: Revenue & Growth (tuần 4+)

### 4.1 B2G partnership

| Action | Chi tiết |
|--------|----------|
| Pitch chuẩn hóa danh bạ HC cấp tỉnh | Framework + facility schema live, /danh-ba ready |
| Demo cho UBND | Admin CMS + AI chat + directory lookup |
| Revenue: hợp đồng maintain/chuẩn hóa data | Không per-listing, mà package deal |

### 4.2 Premium listing

| Action | Chi tiết |
|--------|----------|
| Doanh nghiệp trả phí → CTA ưu tiên | Zalo/phone/website link nổi bật hơn |
| Featured section trên homepage | Slot quảng cáo native, không banner |
| Entity "verified" badge | Doanh nghiệp xác minh → trust signal |

### 4.3 OCOP showcase

| Action | Chi tiết |
|--------|----------|
| CTA "Đặt hàng trên Shopee/TikTok" | Link-out, không booking on-site (decision #13) |
| OCOP product cards enrichment | ocop stars, price, specialty |
| Seasonal OCOP highlights | /theo-mua integration |

### 4.4 Community engagement

| Action | Chi tiết |
|--------|----------|
| Review campaign | Kích hoạt aggregateRating sau khi có text reviews |
| Local ambassador program | Badge Đại-sứ (reputation level 4) |
| Gamification badges | Traveler, Explorer, Expert — tăng engagement |

---

## GĐ pending — completion checklist

Các task roadmap chưa xong, map vào phase nào:

| GĐ | Task | Phase |
|----|------|-------|
| 5.6 | Crawler excerpt-only mode | Phase 2 (khi re-enable crawler) |
| 7.1 | GET /api/constants endpoint | Phase 2 |
| 7.5 | Gỡ field shim legacy (coords, from/to) | Phase 3 |
| 8.1-8.5 | Image pipeline (R2 + optimize + SEO) | Phase 1 |
| 9.1-9.4 | Observability full stack | Phase 3 |
| 10.1 | Hybrid prerender | Phase 3 |
| 12.1-12.2 | Season backfill + provenance | Phase 1 |
| 13.1 | Owner-portal (claim→duyệt→edit) | Phase 4 |
| 13.6 | Danh bạ data thật 124 units | Phase 1 |
| 13.9 | Premium listing + B2G | Phase 4 |

---

## Audit findings chưa fix (6 data issues)

| ID | Issue | Phase |
|----|-------|-------|
| DF-02 | 68 entities summary wrong province | Phase 1 (manual fix) |
| DF-04 | 9 entities transposed coordinates | Phase 1 (geocode) |
| DF-05 | 5 duplicate entities | Phase 1 (merge) |
| DI-002 | 128 produced_in target non-place | Phase 1 (retype relationship) |
| GS-06 | 275 cross-province near rels | Accept (geography span OK post-merge) |

---

## Ước tính effort

| Phase | Effort (code) | Effort (data/manual) | Dependencies |
|-------|--------------|---------------------|--------------|
| Phase 1 | 2-3 ngày | 5-7 ngày | Nguồn data thật, ảnh stock |
| Phase 2 | 1-2 ngày | 0 | Chỉ config flags |
| Phase 3 | 2-3 ngày | 1 ngày | GSC account, Umami setup |
| Phase 4 | 0 (code done) | Ongoing | B2G contacts, doanh nghiệp |

**Tổng code effort: ~7 ngày.** Phần lớn effort là data curation (manual), không phải engineering.

---

## KPIs theo dõi

| Metric | Hiện tại | Target (4 tuần) | Tool |
|--------|----------|------------------|------|
| Image coverage | 0% | 15-20% | validate_data.py |
| Quality score (avg) | 81.7 | 85+ | validate_data.py |
| Attribute coverage (all types) | ~30% avg | 50%+ | validate_data.py |
| placeId unclassified | 199 | <50 | validate_data.py |
| Uptime monitored | No | Yes | UptimeRobot |
| GSC indexed pages | 0 | 50+ | Google Search Console |
| Lighthouse Performance | TBD | >80 | Lighthouse CI |

# Kế hoạch World-Class — vinhlong360

> Date: 2026-06-27 | Status: Draft — chờ duyệt
> Dựa trên 5 audit song song: Backend, Frontend, Data, DevOps, Growth Strategy

---

## Tổng quan hiện trạng

### Điểm số theo chiều (10-point scale)

| Chiều | Điểm | Highlights |
|-------|-------|------------|
| Backend architecture | 7.5 | Security/guardrails world-class; observability yếu |
| Frontend UX | 7.5 | Design system 9/10; thiếu JSON-LD detail, 404/500 pages |
| Data quality | 8.2 | Graph sạch, 0 hallucination; 0% images, 9% phones |
| Data completeness | 3.0 | 0% images, 0% websites, 0% SEO slug/meta |
| DevOps | 5.0 | CI tốt; không monitoring, không WAF, backup local-only |
| Growth readiness | 4.0 | Moat mạnh (hyperlocal + seasonal + verified); chưa launch |
| **Tổng** | **5.5** | **Target: 8.5 trong 12 tháng** |

### Ràng buộc cứng

- Solo dev, budget <1tr VNĐ/tháng (~$40 USD)
- Web-only (KHÔNG native app, AR, audio guide)
- Ảnh: CHỈ AI-generated (cx/gpt-5.5-image)
- Commerce: showcase-only (link Shopee/TikTok, KHÔNG booking on-site)
- Pháp lý: owner tự thực hiện
- CSS thuần + tokens (KHÔNG Tailwind)
- KHÔNG tự sinh dữ liệu giả (§1.4)

### Định nghĩa "World-Class" cho niche này

KHÔNG cạnh tranh Google Maps hay TripAdvisor. Mục tiêu: **nền tảng hyperlocal có thẩm quyền nhất** cho vùng VL+BT+TV, được tin dùng bởi:
- Du khách (trong nước + quốc tế) → khám phá + lập kế hoạch theo mùa
- Doanh nghiệp địa phương → hiện diện được xác minh + phản hồi cộng đồng
- Chính quyền (du lịch/OCOP) → dữ liệu + tài nguyên nhúng
- Content creator → nguồn thông tin chính xác để tái sử dụng

---

## Lộ trình 24 tháng — 6 Phase

### Phase 0: Security & Stability (tuần 1-2) — NỀN TẢNG

> Không thể world-class nếu nền tảng không an toàn. Fix trước khi public.

#### 0.1 Security critical fixes

| Issue | Severity | File | Fix |
|-------|----------|------|-----|
| Session fixation | CRITICAL | `agent/server.py` | Enforce server-side session ID generation, reject client-provided |
| CSP unsafe-inline | HIGH | `nginx.conf` | Chuyển sang nonce-based CSP |
| CORS fallback cho phép tất cả | HIGH | `agent/server.py` | Fail-closed: nếu CORS_ORIGINS rỗng → deny all |
| Admin endpoint không IP whitelist | HIGH | `nginx.conf` | Thêm `allow/deny` cho `/admin-api/*` |
| No HTTPS enforcement | HIGH | `agent/server.py` | Thêm HSTS middleware, Secure cookie flag |

**Effort:** 1 ngày code | **Impact:** Chặn attack vectors trước khi public

#### 0.2 WAF & DDoS protection

| Task | Tool | Cost |
|------|------|------|
| Cloudflare proxy (free tier) | Cloudflare | 0đ |
| Rate-limit bypass fix | nginx X-Forwarded-For validation | 0đ |
| Bot protection | Cloudflare managed rules | 0đ |

**Effort:** 2-3 giờ | **Impact:** Chống DDoS cho single-VPS

#### 0.3 Backup off-site

| Task | Chi tiết |
|------|----------|
| Daily pg_dump → Cloudflare R2 hoặc Backblaze B2 | Cron job, encrypt at rest |
| Backup restore test | Monthly verify (script tự động) |
| Retention: 30 ngày daily + 12 tháng weekly | Rotate tự động |

**Effort:** 3 giờ | **RPO:** 24h → target 6h (WAL archiving sau)

---

### Phase 1: Data & Content (tuần 2-6) — IMPACT CAO NHẤT

> Bottleneck #1: hệ thống over-engineered so với lượng data.

#### 1.1 Ảnh AI-generated (0% → 30%)

| Task | Chi tiết | Estimate |
|------|----------|----------|
| Setup R2 pipeline | Config S3 env, test WebP convert | 0.5 ngày |
| Batch generate top types | attraction (320), dish (120), accommodation (164), craft_village (85) — prompt: "Mekong delta aesthetic" | 3-4 ngày |
| Owner review + approve | Admin duyệt từng ảnh qua `/admin/duyet-anh` | Ongoing |
| Image sitemap + og:image | Per-entity override khi có ảnh | 0.5 ngày |

**Ưu điểm AI-only:** consistent visual brand, không rights-clearance, culturally authentic qua prompt engineering.

#### 1.2 SEO metadata (0% → 100%)

| Field | Hiện tại | Target | Action |
|-------|----------|--------|--------|
| slug | 0% | 100% | Auto-generate từ name (Vietnamese unaccent) |
| meta_description | 0% | 100% | Lấy 160 chars đầu summary |
| og:image | 0% | 30%+ | Gắn khi Phase 1.1 xong |

**Effort:** 0.5 ngày (backend migration + auto-fill script)

#### 1.3 Contact info enrichment

| Type | Phone hiện tại | Target | Source |
|------|---------------|--------|--------|
| restaurant | 1% (1/94) | 50%+ | Google Maps, gọi trực tiếp |
| cafe | 0% (0/38) | 30%+ | Google Maps, gọi trực tiếp |
| craft_village | 4% (3/85) | 40%+ | Sở Công Thương, OCOP registry |
| facility | 43% (25/58) | 90%+ | Cổng DVCTT tỉnh |

**LƯU Ý:** Chỉ nhập SĐT xác minh thực tế (§1.4). KHÔNG bịa.

#### 1.4 Data quality fixes (từ audit)

| Issue | Count | Action | Effort |
|-------|-------|--------|--------|
| placeId=None | 199 | Admin UI `/admin/chua-phan-loai` | 2 giờ |
| SĐT sai format | 44 | Admin entity edit | 1 giờ |
| Summary >500 chars | 53 | Rút gọn (không rewrite) | 1 giờ |
| Asymmetric "near" rels | 3,096 | Script auto-repair (add reverse) | 0.5 giờ |
| Timestamp inversion | 1,753 | Migration swap updatedAt/created_at | 0.5 giờ |
| Wrong province summary | 68 | Manual fix via admin | 2 giờ |
| Transposed coords | 9 | Geocode + fix | 0.5 giờ |
| Duplicate entities | 5 | Merge via admin | 0.5 giờ |

#### 1.5 Danh bạ hành chính 124 đơn vị (GĐ13.6)

| Task | Chi tiết |
|------|----------|
| Thu thập dữ liệu thật | Cổng DVCTT, niên giám thống kê |
| Nhập qua admin UI | type=facility, OFFICE_KIND schema |
| Verify SĐT + địa chỉ | Kiểm tra thực tế |

**Niche mạnh nhất:** Demand 8/10, moat cao, GEO=SEO cho "UBND xã X điện thoại".

---

### Phase 2: Frontend Polish (tuần 4-8) — UX WORLD-CLASS

> Frontend đã 7.5/10. Cần polish để đạt 9/10.

#### 2.1 Critical UX fixes

| Fix | Severity | Effort |
|-----|----------|--------|
| Trang 404 + 500 với recovery actions | HIGH | 2 giờ |
| Skip-to-content link | HIGH | 0.5 giờ |
| JSON-LD cho detail pages (LocalBusiness, Product, FoodEstablishment) | HIGH | 4 giờ |
| Breadcrumb schema.org | MEDIUM | 1 giờ |
| Modal focus trap centralized | MEDIUM | 2 giờ |

#### 2.2 Performance optimization

| Fix | Impact | Effort |
|-----|--------|--------|
| CLS mitigation: aspect-ratio trên dynamic grids | CWV "Good" | 2 giờ |
| LQIP (low-quality inline preview) cho images | Perceived speed +40% | 3 giờ |
| Cache-Control headers cho static assets | Repeat-visit speed | 1 giờ |
| Offline fallback page + SW update notification | PWA quality | 2 giờ |

#### 2.3 Search & discovery upgrade

| Feature | Chi tiết | Effort |
|---------|----------|--------|
| "Related entities" card trên detail page | Dùng relationship graph | 3 giờ |
| Faceted search filters (type, area, season) | URL state sync (useFilterUrl đã có) | 4 giờ |
| FAQPage schema trên entity detail | Rich snippet Google | 2 giờ |

#### 2.4 Form & error handling

| Fix | Chi tiết | Effort |
|-----|----------|--------|
| Centralized form validation composable | Thay per-component logic | 3 giờ |
| Global API error toast | useToast + error interceptor | 2 giờ |
| Request timeout handling | Infinite loading prevention | 1 giờ |

---

### Phase 3: Backend Hardening (tuần 6-10)

> Backend 7.5/10. Target 9/10: fix N+1, bật dormant modules, add observability.

#### 3.1 Performance fixes

| Issue | Fix | Impact | Effort |
|-------|-----|--------|--------|
| N+1 in relationship traversal | Batch `WHERE id IN (...)` | 5-10x faster related queries | 3 giờ |
| No query timeout | Add `statement_timeout` to PG DSN | Prevent hung queries | 0.5 giờ |
| In-memory KB startup | Lazy-load hoặc pagination | Startup 2-5s → <1s | 6 giờ |

#### 3.2 Kích hoạt dormant modules (chỉ config, 0 code mới)

| Module | Flag | Risk | Priority |
|--------|------|------|----------|
| `circuit_breaker.py` | HAS_CIRCUIT_BREAKER=true | LOW (đã tested) | Bật ngay |
| `guardrails.py` | HAS_GUARDRAILS=true | LOW (mature code) | Bật ngay |
| `cost_tracker.py` | HAS_COST_TRACKER=true | LOW | Bật ngay |
| `metrics.py` | HAS_METRICS=true | LOW | Bật ngay |
| `prompt_cache.py` | HAS_PROMPT_CACHE=true | LOW | Bật ngay |
| `semantic_cache.py` | HAS_SEMANTIC_CACHE=true | MEDIUM (test first) | Sau 1 tuần |
| `orchestrator.py` | HAS_ORCHESTRATOR=true | MEDIUM (untested) | Sau 2 tuần |
| `checkpoints.py` | HAS_CHECKPOINTS=true | MEDIUM | Sau 2 tuần |

**KHÔNG bật:** reflexion, self_optimizer, dynamic_agents (incomplete, risk cao).

#### 3.3 Observability stack (CRITICAL gap)

| Layer | Tool | Cost | Effort |
|-------|------|------|--------|
| Metrics | Prometheus + Grafana (VPS) | 0đ (self-host) | 4 giờ |
| Uptime | UptimeRobot free tier | 0đ | 0.5 giờ |
| Error tracking | Sentry free tier (5k events/mo) | 0đ | 2 giờ |
| Logging | Loki + Promtail (VPS) | 0đ (self-host) | 4 giờ |
| Alerting | Telegram bot (đã có) | 0đ | 1 giờ |
| Analytics | Umami CE self-hosted | 0đ | 2 giờ |

**Target:** 99.5% uptime monitored, <1s p50 page load, alerting trong 5 phút.

#### 3.4 API improvements

| Fix | Effort |
|-----|--------|
| Pagination cho list endpoints (skip/limit) | 2 giờ |
| RFC 7807 error envelope | 4 giờ |
| Enable FastAPI `/docs` (OpenAPI schema) | 0.5 giờ |
| /health/deep probe database + cache + LLM latency | 2 giờ |

---

### Phase 4: DevOps & Reliability (tuần 8-12)

> DevOps 5/10. Target 8/10: zero-downtime, automated rollback, IaC.

#### 4.1 Zero-downtime deployment

| Task | Chi tiết | Effort |
|------|----------|--------|
| Rolling restart pattern | Health-check wait giữa service restarts | 2 giờ |
| Post-deploy health polling | 5 lần check /health trong 60s, rollback nếu fail | 1 giờ |
| Automated rollback script | 1-command restore từ pre-deploy backup | 2 giờ |

#### 4.2 CDN & caching

| Task | Tool | Impact |
|------|------|--------|
| Cloudflare CDN cho static assets | Free tier | -200ms latency globally |
| Redis caching layer cho API reads | Redis (đã deploy) | -50% DB load |
| Asset fingerprinting + Cache-Control | Nuxt build config | Repeat-visit speed |
| Brotli compression (thay gzip) | nginx module | -15% transfer size |

#### 4.3 Infrastructure as Code (IaC)

| Task | Chi tiết |
|------|----------|
| docker-compose → production-ready | Resource limits, restart policies, log rotation |
| Terraform/Pulumi cho VPS provisioning | Reproducible infra (dài hạn) |
| Secret rotation policy | ADMIN_API_KEY, LLM_API_KEY rotate quarterly |

#### 4.4 Database reliability

| Task | Chi tiết | Effort |
|------|----------|--------|
| Off-site backup (R2/B2) | Encrypted, daily, auto-verify | 3 giờ |
| WAL archiving | RPO 6h → 1h | 3 giờ |
| Connection pooling fix | PG_USE_POOL=true stable | 2 giờ |
| Query performance baseline | EXPLAIN ANALYZE top 10 queries | 2 giờ |

---

### Phase 5: Content Depth & SEO (tuần 10-20)

> Từ "data đủ" → "content sâu" — yếu tố quyết định ranking.

#### 5.1 Content enrichment (top 300 entities)

| Task | Chi tiết | Effort |
|------|----------|--------|
| Rich descriptions (>200 words) | Top 50 attraction, 30 restaurant, 20 accommodation | 40 giờ (manual) |
| "Best time to visit" cho attraction | Dựa trên season data + local knowledge | 10 giờ |
| "Signature dish" cho restaurant | Research + verify | 5 giờ |
| "How to get there" cho attraction | Transport info thực tế | 10 giờ |

#### 5.2 Seasonal data completion (75% → 95%)

| Type | Hiện tại | Target | Source |
|------|----------|--------|--------|
| product | 19% (41/218) | 80%+ | OCOP registry, nông dân |
| dish | ~50% | 90%+ | Seasonal harvest calendar |
| attraction | ~70% | 95%+ | Local knowledge |
| experience | ~40% | 80%+ | Tour operators |

**LƯU Ý:** Season data phải từ nguồn thật (§1.4).

#### 5.3 SEO technical

| Task | Impact | Effort |
|------|--------|--------|
| Google Search Console setup | Indexation visibility | 1 giờ (cần domain) |
| Submit sitemap-index.xml | Crawl coverage | 0.5 giờ |
| Internal linking (related entities on detail) | Crawl depth + user time | 3 giờ (Phase 2.3) |
| A/B test title tags | CTR optimization | 2 giờ |
| Monitor Core Web Vitals | Lighthouse CI | 1 giờ |

#### 5.4 Structured data hoàn thiện

| Schema | Page | Status |
|--------|------|--------|
| WebSite + SearchAction | Homepage | ✅ Done |
| Organization | Homepage | ✅ Done |
| LocalBusiness | Entity detail (restaurant, cafe, accommodation) | ❌ Phase 2.1 |
| Product | Entity detail (product, OCOP) | ❌ Phase 2.1 |
| FoodEstablishment | Entity detail (restaurant) | ❌ Phase 2.1 |
| GovernmentOffice | Entity detail (facility) | ✅ Done |
| Event | Event pages | ✅ Done |
| FAQPage | Entity detail | ❌ Phase 2.3 |
| BreadcrumbList | All pages | ❌ Phase 2.1 |
| AggregateRating | Entity detail (khi có reviews) | ❌ Phase 5+ |

---

### Phase 6: Revenue & Growth (tuần 16-24+) — BỀN VỮNG

#### 6.1 B2G partnerships (revenue path #1)

| Milestone | Timeline | Revenue estimate |
|-----------|----------|-----------------|
| Pitch Sở Du lịch (danh bạ + seasonal) | Tháng 4-5 | — |
| Contract #1 (co-marketing) | Tháng 6 | 800k-2tr/tháng |
| Pitch Sở Công Thương (OCOP showcase) | Tháng 7 | — |
| Contract #2 | Tháng 8 | 500k-1tr/tháng |

#### 6.2 Premium listings (revenue path #2)

| Feature | Chi tiết | Revenue |
|---------|----------|---------|
| Claim-listing → verified badge | Owner xác minh qua admin | — |
| Featured spot homepage | 5-10 slots, rotate monthly | 500k-1.5tr/slot/tháng |
| Analytics dashboard cho business | View count, phone clicks | Premium add-on |

#### 6.3 Community growth

| Metric | Hiện tại | Target 6 tháng | Target 12 tháng |
|--------|----------|----------------|-----------------|
| MAU | 0 | 500 | 2,000 |
| Posts/week | 0 | 50 | 200 |
| Reviews per entity (top 100) | 0 | 3-5 | 10-20 |
| Abuse rate | — | <2% | <1% |

#### 6.4 Revenue trajectory

| Thời điểm | MRR estimate | Nguồn |
|-----------|-------------|-------|
| Tháng 1-6 | 0đ | Setup, launch |
| Tháng 7-9 | 500k-1.5tr | 1 B2G contract |
| Tháng 10-12 | 1.5tr-3tr | 2 B2G + 3-5 premium |
| Năm 2 | 3tr-8tr | 4 B2G + 10-15 premium |

---

## Effort tổng hợp

| Phase | Code effort | Data/manual effort | Timeline |
|-------|------------|-------------------|----------|
| 0: Security | 1-2 ngày | 0 | Tuần 1-2 |
| 1: Data & Content | 2-3 ngày code + scripts | 5-7 ngày manual | Tuần 2-6 |
| 2: Frontend Polish | 3-4 ngày | 0 | Tuần 4-8 |
| 3: Backend Hardening | 3-4 ngày | 0 | Tuần 6-10 |
| 4: DevOps | 2-3 ngày | 0 | Tuần 8-12 |
| 5: Content Depth | 1-2 ngày code | 60-80 giờ manual | Tuần 10-20 |
| 6: Revenue | 0 (code done) | Ongoing BD | Tuần 16+ |

**Tổng code: ~15 ngày.** Phần lớn effort là data curation + business development.

---

## Moat analysis — Lợi thế cạnh tranh

| Moat | Strength | Sustainability |
|------|----------|---------------|
| **Hyperlocal knowledge graph** (1753 entities, 8415 rels) | 9/10 | Cao — tốn 6+ tháng để replicate |
| **AI chat contextual** (tool-calling + seasonal) | 8/10 | Trung bình — competitors có thể build |
| **Verified community** (OTP + moderation) | 7/10 | Cao — trust mất thời gian xây |
| **Seasonal intelligence** (75%+ coverage) | 8/10 | Rất cao — data thực tế, không bịa |
| **Merged-province first mover** | 9/10 | 1-2 năm window trước competitors |
| **Showcase-only legal structure** | 7/10 | Cao — tránh TMĐT regulation overhead |
| **Government directory** (124 units) | 8/10 | Rất cao — chỉ vinhlong360 có |

---

## KPIs dashboard

### Launch metrics (tháng 1-3)

| Metric | Baseline | Target | Tool |
|--------|----------|--------|------|
| Uptime | Unmonitored | 99.5% | UptimeRobot |
| Page load p50 | Unknown | <1.5s | Lighthouse |
| Image coverage | 0% | 30% | validate_data.py |
| Phone coverage | 9.3% | 25% | validate_data.py |
| GSC indexed pages | 0 | 100+ | Google Search Console |
| Organic sessions/week | 0 | 200+ | Umami |

### Growth metrics (tháng 4-12)

| Metric | Target 6m | Target 12m | Tool |
|--------|-----------|------------|------|
| MAU | 500 | 2,000 | Umami |
| Organic sessions/month | 2,000 | 8,000 | GSC |
| Top-10 SERP queries | 5 | 15 | GSC |
| Reviews per entity (top 100) | 3-5 | 10-20 | DB query |
| MRR | 1.5tr | 3-8tr | Manual |
| Attribute coverage avg | 50% | 70% | validate_data.py |
| Image coverage | 50% | 80% | validate_data.py |
| Chat response p50 | <3s | <2s | Metrics/Prometheus |

### Quality metrics (ongoing)

| Metric | Target | Tool |
|--------|--------|------|
| Data quality score | >85/100 | validate_data.py |
| CWV all "Good" | Yes | Lighthouse |
| Abuse rate | <2% | Moderation dashboard |
| /health/deep latency | <500ms | health_check.py |
| Test pass rate | 100% | CI/pytest |
| Security findings (Critical) | 0 | TruffleHog + audit |

---

## Risk matrix

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| VPS single point of failure | HIGH | CRITICAL | Phase 4: off-site backup + Cloudflare proxy |
| 0% images → low engagement | HIGH | HIGH | Phase 1.1: AI-generated batch |
| No domain → can't launch | MEDIUM | BLOCKING | Owner action: mua domain + DNS |
| LLM cost spike | MEDIUM | MEDIUM | cost_tracker + daily cap + kill-switch |
| Competitor copy graph | LOW | MEDIUM | Moat: verified data + community trust |
| Regulatory (NĐ147) | MEDIUM | HIGH | Owner tự xử lý pháp lý |
| Data inaccuracy claims | LOW | HIGH | §1.4 anti-hallucination + source tracking |

---

## Appendix: Dormant modules — activation guide

| Module | Flag | Completeness | Risk | Recommend |
|--------|------|-------------|------|-----------|
| prompt_cache | HAS_PROMPT_CACHE | 90% | Low | ✅ Bật ngay |
| circuit_breaker | HAS_CIRCUIT_BREAKER | 85% | Low | ✅ Bật ngay |
| guardrails | HAS_GUARDRAILS | 90% | Low | ✅ Bật ngay |
| cost_tracker | HAS_COST_TRACKER | 85% | Low | ✅ Bật ngay |
| metrics | HAS_METRICS | 80% | Low | ✅ Bật ngay |
| semantic_cache | HAS_SEMANTIC_CACHE | 70% | Medium | ⚠️ Test trước 1 tuần |
| orchestrator | HAS_ORCHESTRATOR | 50% | Medium | ⚠️ Test + review |
| checkpoints | HAS_CHECKPOINTS | 60% | Medium | ⚠️ Test + review |
| llm_judge | LLM_JUDGE_ENABLED | 80% | Low (cost) | ⚠️ Bật khi có budget |
| image_recognition | HAS_IMAGE_RECOGNITION | 60% | Medium | ⚠️ Sau Phase 1.1 |
| vector_search | HAS_VECTOR | 60% | Medium | ❌ Chưa cần (BM25 đủ) |
| realtime | HAS_REALTIME | 40% | High | ❌ Chưa hoàn thiện |
| reflexion | — | 40% | High | ❌ Incomplete |
| self_optimizer | HAS_OPTIMIZER | 20% | High | ❌ PoC only |
| dynamic_agents | HAS_DYNAMIC_AGENTS | 30% | High | ❌ Skeleton |

## Appendix: Roadmap completion map

| GĐ | Task | Status | Phase trong plan |
|----|------|--------|-----------------|
| 5.6 | Crawler excerpt-only | Pending | Phase 3 (khi re-enable) |
| 7.1 | GET /api/constants | Pending | Phase 3.4 |
| 7.5 | Gỡ field shim legacy | Pending | Phase 3 |
| 8.1-8.5 | Image pipeline | Pending | Phase 1.1 |
| 9.1-9.4 | Observability | Pending | Phase 3.3 |
| 10.1 | Hybrid prerender | Pending | Phase 2.2 |
| 12.1-12.2 | Season backfill | Pending | Phase 5.2 |
| 13.1 | Owner-portal | Partial | Phase 6.2 |
| 13.6 | Danh bạ 124 units | Pending | Phase 1.5 |
| 13.9 | Premium listing + B2G | Pending | Phase 6.1-6.2 |

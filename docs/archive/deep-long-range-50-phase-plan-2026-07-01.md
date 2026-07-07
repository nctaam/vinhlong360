# Deep long-range 50-phase plan - vinhlong360 - 2026-07-01

> **STATUS (2026-07-07): ARCHIVED — Tài liệu LỊCH SỬ đã archive (truth-sync 2026-07-07). KHÔNG làm theo chỉ dẫn trong file này — đối chiếu CLAUDE.md + docs/README.md.**
> Blueprint 1 trong 3 bản chồng lấn cùng ngày 01/07, không được ROADMAP tham chiếu. Phase 28 chứa luồng ảnh Wikimedia (nay CẤM); Phase 29 nghiệm thu SEO-media vô nghĩa khi noindex toàn site đang bật.


## 1. Muc tieu

Ke hoach nay di sau hon audit tung trang. No cham vao cac lop it thay nhung quyet dinh chat luong production: SSR/hydration, route cache, service worker, API contract, type debt, migration drift, RBAC, audit DB, data provenance, media license, observability, smoke E2E, deploy/rollback va SLO van hanh.

Nguyen tac:
- Khong them booking/payment/marketplace.
- Khong them ML phuc tap neu khong giai thich duoc.
- Moi phase phai co dau ra cu the, test/gate va tac dong do duoc.
- Lam theo batch nho; moi batch co the ship/deploy rieng.

## 2. Nhung vung chua cham du sau

- Service worker/PWA: hien co cache HTML network-first va asset cacheFirst/SWR, nhung chua co update UX, cache test, offline policy theo route.
- Route rules/SWR: da co cache route, nhung chua co ma tran cache invalidation theo write path.
- API proxy/SSR: `apiFetch` da chong SSR proxy miss, nhung chua co typed API client va test cho tat ca SSR data pages.
- Hydration: co workaround Unhead, site-overrides chay universal, nhung can chuong trinh zero console error co screenshot/smoke.
- Type safety: vue-tsc con debt; nhieu page/component dung `any`, `$fetch<any>`, response loose.
- Admin RBAC: scope da co backend/audit, UI van con role tho va chua day du scope UX.
- Audit: DB audit co fallback JSONL, nhung can coverage action quan trong + retention/export.
- Rate/idempotency: shared PG da co, nhung chua co dashboard hit rate, policy matrix, alert.
- CI/deploy: release gate tot, nhung CI con non-blocking typecheck/CVE, deploy workflow GitHub chua deploy VPS that.
- Data provenance/media: quality budget da co, nhung image license/credit/source pipeline chua thanh workflow bat buoc.
- Search/recommendation: hybrid/BM25 co nen tang, nhung public search contract, zero-result queue va reason contract can dong bo UI.
- Planner/map: van con fetch lon/list-map selected state/cache route geometry.
- Community/user: chuc nang day du nhung page qua lon, can tach component/composable va test hanh vi.
- Legal/compliance ops: consent version, crawler excerpt-only, incident drills can thanh quy trinh.

## 3. 50 phase nang cap dai han

| Phase | Trong tam | Tac dong thuc | Dau ra can co | Nghiem thu |
| --- | --- | --- | --- | --- |
| 01 | North-star product metrics | Biet dang toi uu cai gi, tranh lam tinh nang lech huong. | Define metrics: search success, detail trust action, save-to-plan, contact click, report SLA, admin DQ burn-down. | Admin/ops co metrics doc + event names; khong can tracking moi neu chua implement. |
| 02 | Route-function ownership map | Het cam giac "trang nao cung co logic rieng". | Map route -> API -> data model -> owner -> smoke coverage. | Tai lieu sinh/duy tri duoc; 100% route core co owner va smoke status. |
| 03 | Dependency graph | Biet thay doi API nao anh huong trang nao. | Script scan route/API/composable/component dependencies. | CI artifact hoac local command xuat graph JSON/Markdown. |
| 04 | Scenario lab | Nang cap theo hanh vi nguoi dung that. | 50-100 task scenarios: visitor, local, OCOP owner, moderator, admin ops. | Moi task co route, expected outcome, failure states. |
| 05 | Design system tightening | UI dong bo, giam CSS drift. | Token/page layout/card/filter/modal/button rules; remove one-off patterns. | Visual smoke 360/390/768/1440 cho core pages. |
| 06 | Typed API contract registry | Giam SSR 500 va drift FE/BE. | `types/api.ts` hoac domain response types; public/admin/auth/social contracts. | New code khong dung `$fetch<any>` cho core endpoints. |
| 07 | API client layer | Dong bo error/auth/retry/baseURL. | Thin typed wrappers: search, entities, saved, plans, community, admin. | 10 route chinh dung wrapper thay ad-hoc fetch. |
| 08 | Fetch resilience | Loi API khong bien thanh trang rong/mau thuan. | Unified fallback states, retry actions, status mapping. | E2E mock 500/timeout cho home/search/detail/saved. |
| 09 | SSR/hydration zero-error | San xuat khong co console error khi navigate. | Hydration audit list: color mode, site settings, auth menu, onboarding, chat, lazy head. | Chrome smoke fail neu console error/exception. |
| 10 | Service worker governance | Het stale asset/stale HTML sau deploy. | SW bypass matrix, version update banner, cache invalidation policy. | Test: admin/auth/API never cached; new version prompt appears. |
| 11 | RouteRules/SWR audit | Cache dung cho read-heavy, khong phuc vu du lieu cu sau write. | Cache TTL matrix per route/API; invalidation hooks after admin CRUD/reload. | Smoke sau admin edit: detail/list/home cap nhat trong TTL cho phep. |
| 12 | TypeScript debt burn-down A | Giam loi runtime tu response loose. | Type top files: home, search, map, saved, planner. | vue-tsc error count giam theo baseline va khong tang lai. |
| 13 | TypeScript debt burn-down B | AdminCP on dinh hon. | Type admin entities/users/reports/data-quality/settings. | Admin route smoke + vue-tsc tranche pass. |
| 14 | Test pyramid redesign | Test dung noi, it brittle. | Split unit/contract/integration/e2e/visual/security/data gates. | `release_gate` doc ro test nao bat buoc, test nao optional. |
| 15 | Production E2E expansion | Bat loi that tren vinhlong360.vn. | 30-40 route smoke: public + user + admin key pages + detail samples. | Fail on 500, console error, broken core CTA. |
| 16 | Visual regression baseline | Cham duoc UI that, khong chi code. | Playwright screenshots desktop/mobile for home/search/detail/map/community/user/admin. | Diff threshold + manual approval doc. |
| 17 | Client error observability | Biet user gap loi nao tren prod. | `/api/client-error` taxonomy, admin client-error dashboard, release correlation. | AdminCP thay top client errors by route/version. |
| 18 | Backend health/SLO | Health khong chi "OK" ma co y nghia. | SLO: ready, DB, cache, queue, DQ, error rate, latency budget. | `/health/internal` + AdminCP ops show budget and trend. |
| 19 | Security route matrix | Khong lo endpoint noi bo. | Generated matrix for `/system`, `/analytics`, `/metrics`, checkpoint, judge, cache, vectors, admin. | Test auto fail neu route sensitive thieu admin guard. |
| 20 | Auth cookie migration | Giam rui ro token JS-readable. | Roadmap dual token -> HttpOnly Secure SameSite cookie; compatibility window. | Auth tests pass; logout/refresh/csrf/session UI pass. |
| 21 | Session/security UX | User hieu bao mat tai khoan. | Password state, sessions hidden internal, login history, revoke UX, anomaly label. | `/cai-dat` khong con copy mau thuan; smoke session flows. |
| 22 | RBAC scopes UI | Admin khong con role tho. | Scope editor, visible permissions, self-role/scope guard, reason required. | Admin users tests cover scope escalation/denial. |
| 23 | Audit DB coverage | Truy vet duoc moi thay doi quan trong. | Append-only DB audit for settings, users, reports, moderation, DQ, media, deploy. | Audit log query/filter/export works; JSONL fallback only fallback. |
| 24 | Rate-limit/idempotency ops | Chong abuse co quan sat duoc. | Rate profile matrix, idempotency policy, hit counters, admin ops panel. | Test 429 headers + AdminCP shows recent hit patterns. |
| 25 | DB white-boot/migration | DB moi khoi tao khong drift. | CI boot Postgres blank, apply init+migrations, run contract tests. | Blank DB integration xanh; schema_version check blocking. |
| 26 | Data provenance model | Moi fact co nguon/cap nhat. | Entity/event/facility source fields normalized: source URL, source tier, verified_at, confidence. | Detail/catalog show trust state; DQ budget tracks missing source. |
| 27 | Data quality budget v2 | Chat luong du lieu thanh con so hang tuan. | Budgets by type/area/source: image, coords, duplicate, thin text, stale facts. | Release gate can block or warn by budget tier. |
| 28 | Media legal pipeline | Anh dep nhung hop phap. | Admin upload/license/credit/source; Wikimedia/manual review; WebP sizes. | Missing license/credit cannot publish new media. |
| 29 | Image sitemap/SEO media | Tang image search trust. | `/sitemap-media.xml` verified end-to-end, captions/license where possible. | robots points valid sitemap; prod returns 200. |
| 30 | Geospatial QA | Map dang tin hon. | Coordinate confidence, bbox, cluster anomalies, centroid labels, admin correction queue. | Map pins never show fake precision; DQ flags clusters. |
| 31 | Event/date system | Le hoi/su kien logic hon. | `category[]`, `date_start_iso`, `date_label`, `lunar_rule`, `recurrence`, `date_confidence`. | `/le-hoi` and `/su-kien` use same contract + tests. |
| 32 | Taxonomy governance | Category khong phinh/toi nghia. | Source of truth for type/category/area/interest; admin validation; `/api/constants` if needed. | FE/BE labels match; no orphan category in data. |
| 33 | Search v2 contract | Search thanh san pham chinh. | Unified `/api/search`: entities/posts/users/suggestions/totals/filters/reasons. | Topbar autocomplete and `/tim-kiem` use same contract. |
| 34 | Search relevance v2 | Tim khong dau, tu dong nghia, typo tot hon. | Synonym Vietnamese, unaccent, BM25 tuning, zero-result capture. | Relevance eval set pass; Admin sees top zero-result queries. |
| 35 | Recommendation contract | Goi y co ly do, khong "AI theatre". | Similar/nearby/contextual card shape with `reason_vi`, source signals. | SmartRecommendations/EntityCard consume same shape. |
| 36 | JSON-LD service | SEO khong lech FE/BE. | Backend JSON-LD endpoints/helpers for entity/event/itinerary/profile. | Snapshot parity tests; FE stops duplicating risky schema. |
| 37 | Crawler/content legality | Khong vo tinh copy/breach. | Excerpt-only import policy, source tiering, crawl disabled unless approved. | Test/script guard prevents full article/image import. |
| 38 | Unified catalog shell | Tat ca listing giong logic. | Shared catalog layout/composable: q, vung, type, mua, sort, pagination, empty recovery. | `/dia-diem`, `/du-lich`, `/san-pham`, `/ocop`, `/luu-tru` converge. |
| 39 | Homepage decision engine | Trang chu hieu user hon. | Rule-based journey rail: first-time, saved-heavy, planner-heavy, seasonal, local admin. | Home module CTR tracked; no fake personalization. |
| 40 | Map/list v2 | Ban do thanh cong cu kham pha that. | Bbox/list API, selected pin/card, mobile toggle, accessible list, save/add-to-plan. | E2E asserts filter/list/popup/keyboard equivalent. |
| 41 | Detail trust/practical v2 | Detail thuyet phuc hon, it nghi ngo. | Trust layer: source, last verified, contact confidence, report stale, best time, practical facts. | Detail smoke checks trust block and CTA. |
| 42 | Reviews/Q&A v2 | UGC co gia tri hon feed thuan. | Review sort/filter/photo/helpful, accepted answer surfaced, owner/admin response label. | Entity detail + post detail share Q&A contracts. |
| 43 | Region/ward hub v2 | Khu vuc thanh hub, khong chi list. | Region/ward: map, facilities, events, products, itineraries, report admin info. | `/khu-vuc/*` and `/xa-phuong/*` have coherent next actions. |
| 44 | Planner v2 | Lich trinh nhanh, nhe, dung y user. | Picker search/pagination, saved-to-plan, route cache/fallback, print/share/cue sheet. | No `limit=700`; detail -> planner auto-add pass. |
| 45 | Saved workspace v2 | Da luu khong bi dead-end. | Named lists lightweight, undo remove, create itinerary from saved, counts parity. | `/da-luu`, `/tai-khoan`, planner counts match. |
| 46 | UserCP/profile v2 | User thay duoc viec tiep theo. | Next best action, resume draft/plan, contribution trust, privacy badge, public/private profile modes. | E2E login user task flow pass. |
| 47 | Community refactor v2 | Cong dong de bao tri va an toan hon. | Split feed/composer/sidebar/report/bookmarks/search into components/composables. | File size drops; tests cover tab/filter/bookmark/report. |
| 48 | AdminCP workflow v2 | Admin lam viec theo queue/SLA thay vi bang roi rac. | Ops cockpit owner/SLA, moderation templates, DQ batch owner, exports scoped. | Admin E2E: queue -> action -> audit -> metric. |
| 49 | Performance/CWV program | Site nhanh hon tren mobile thuc. | Query bounded, materialized summaries, CSS/code split, image priority, Lighthouse budgets. | Lighthouse/CWV report under thresholds for core pages. |
| 50 | Release/rollback excellence | Deploy bot "done" la that, rollback tap duot. | VPS deploy SLO, backup restore drill, production smoke schedule, release notes, rollback runbook. | Quarterly restore drill documented; deploy fails if smoke fails. |

## 4. Thu tu thuc hien de co tac dong som

Nen lam 50 phase theo 5 dot:

1. Dot A - on dinh nen: phase 06-15, 19-25.
2. Dot B - trust/data: phase 26-37.
3. Dot C - user journey: phase 38-47.
4. Dot D - admin/ops/performance: phase 48-50 + phase 16-18.
5. Dot E - polish lien tuc: quay lai phase 01-05 de cap nhat metric/design/scenario sau moi release lon.

## 5. Cac batch nen bat dau ngay

### Batch 1 - Contract va smoke

- Typed API contracts cho search/saved/planner/notification.
- Chrome smoke mo rong: route + CTA + console error.
- Route sensitive guard matrix.
- Planner bo fetch 700.

### Batch 2 - Trust layer

- Entity/event JSON-LD service backend.
- Detail source/verified/report stale block.
- Data provenance fields va quality budgets v2.
- Media license/credit gate.

### Batch 3 - User journey

- Unified catalog shell.
- Map/list v2.
- Saved -> planner.
- UserCP next best action.

### Batch 4 - Admin workflow

- RBAC scopes UI.
- Audit DB coverage.
- Admin exports scoped.
- Moderation/DQ SLA cockpit.

### Batch 5 - Production excellence

- Service worker update UX/cache tests.
- CWV/Lighthouse budgets.
- Backup restore drill.
- Production smoke schedule and release SLO.


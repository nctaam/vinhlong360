# Audit tung trang va chuc nang vinhlong360 - 2026-07-01

## 1. Pham vi va cach doc

Audit nay dua tren route inventory, ma nguon Nuxt/FastAPI, cac tai lieu nghien cuu da co va ket qua smoke production gan nhat. Muc tieu khong phai them booking/payment/marketplace, ma lam he thong kham pha dia phuong dang tin, nhanh, logic, de van hanh va de mo rong.

Ky hieu uu tien:
- P0: loi chan luong, an toan, schema/API contract, route co nguy co 500 hoac sai du lieu.
- P1: nang cap UX/user journey, lien ket trang, workflow admin, chat luong du lieu.
- P2: toi uu sau ve performance, observability, SEO, personalization, automation.

## 2. Ket luan tong quan

He thong hien co da rat rong: discovery/catalog, ban do, detail, community, profile, saved, planner, notification, AdminCP, data-quality, media, audit, health va deploy gate. Diem yeu lon nhat khong nam o "thieu trang", ma nam o tinh dong bo giua cac hanh trinh:

- Discovery -> detail -> saved -> planner da co day du, nhung van can mot contract chung cho filter, card shape, recommendation reason va CTA tiep theo.
- Community/user da manh ve chuc nang, nhung file page con qua lon; can tach workflow thanh component/composable de giam bug va tang kha nang test.
- AdminCP da chuyen tu CRUD sang ops cockpit, nhung mot so bang van con client-side sort/export, chua giai thich ro "du lieu trang hien tai" hay "toan bo du lieu".
- Data trust da co source/data-quality workflow, nhung nen hien "nguon/cap nhat/bao sai" nhat quan tren detail, catalog card va AdminCP.
- Frontend type safety con no ky thuat: nhieu response dang `any`/loosely typed, lam tang rui ro SSR/hydration va route 500 khi API drift.

## 3. Ma tran tung trang

| Trang | Hien trang | Rui ro/chua logic | Phuong an nang cap |
| --- | --- | --- | --- |
| `/` | Homepage da co hero moi, search, decision cards, seasonal/community/saved/recently viewed. | Dang lay nhieu block rieng; neu `/api/homepage` fail thi can fallback ro hon cho tung block. | P1: them "journey rail" ca nhan hoa: gan vi tri/nhu cau -> goi y route, saved, planner. P2: track home module CTR va no-result search. |
| `/tim-kiem` | Dung `useUnifiedSearch`, co entities/posts/users va AI assist. | Topbar autocomplete va SERP chua cung shape hien thi; bo loc SERP con mong. | P0/P1: chot public search contract: entity/post/user suggestion + full SERP; them filter `type`, `vung`, `sort`; zero-result recovery. |
| `/dia-diem` | Listing co paging, filter type/area/q, JSON-LD. | Query dung `area` trong khi roadmap chuan la `vung`; filter UI khac cac catalog khac. | P1: dung `useFilterUrl` chuan `q,vung,type,mua,sort`; bottom-sheet filter tren mobile; active filter summary. |
| `/dia-diem/[id]` | Detail rat day du: gallery/contact/save/share/reviews/feed/similar/nearby/planner CTA. | File qua lon, schema JSON-LD co logic FE rieng; trust/source/freshness chua thanh mot block chuan. | P0/P1: backend JSON-LD la source of truth; tach detail thanh media, trust, practical, community, related sections; hien source/freshness/report-stale nhat quan. |
| `/ban-do` | Da dung `/api/map-pins`, cluster, list 24 pin, accessible list. | Fetch all pins mot lan; list/map selected state con co the manh hon; filter bbox chua thanh contract UI. | P1/P2: bbox endpoint + virtual list; selected card sync voi marker; mobile map/list toggle; save/planner action trong popup/list. |
| `/du-lich` | Catalog giau noi dung, filter q/type/mua/sort, data-driven sections. | Lay `limit=500`, loc/sort nhieu o client; content dai co the lam user mobile mat focus. | P1: unify catalog shell; server-side filter/sort khi q/type/vung/mua; short guide cards truoc long copy. |
| `/san-pham` va `/ocop` | Product/OCOP co star/filter/quick-picks, link lien he truc tiep. | Hai route gan nhau de bi trung logic; OCOP can tin cay ve sao/nguon/chung nhan. | P1: tach product catalog composable; hien OCOP evidence/source/last verified; CTA Zalo/website ro ranh gioi showcase-only. |
| `/luu-tru` | Accommodation catalog co type breakdown, area quick-picks. | Gia/phong co tinh thoi diem, de gay ky vong dat phong neu copy qua chac. | P1: copy "lien he truc tiep, thong tin tham khao"; detail facts: price range/source date; khong tao availability. |
| `/le-hoi` | Da tokenized category, date ISO fallback, calendar/list. | Dang fetch 200 events client-side; lunar/recurrence/confidence can hien ro. | P1: event contract chuan `category[]`, `date_start_iso`, `date_label`, `lunar_rule`, `date_confidence`; filter server-side. |
| `/su-kien` | Event route tach le-hoi, co status/calendar/ical. | Status tinh client-side; category field con lech voi le-hoi. | P1: dung cung event composable voi `/le-hoi`; them "sap dien ra gan toi" va reminder/RSVP neu login. |
| `/theo-mua` | Da sync query `mua`, co seasonal routing. | Can lien ket manh hon tu detail/home va giai thich mua theo thang. | P1: month selector chuan, route tu home/detail; P2: seasonal landing internal links SEO. |
| `/khu-vuc/[area]` | Region page lay entities/place, co load more. | Can dung query/filter chung; map/ward/directory lien ket chua thanh hub. | P1: region hub gom: noi bat, ban do, xa/phuong, su kien, san pham, lich trinh. |
| `/xa-phuong/[id]` | Ward overview co tourism/product/facility/map/JSON-LD. | Map client-side va office data can source/last updated; file kha lon. | P1: ward trust card + "bao sai thong tin hanh chinh"; P2: cache overview/materialized view. |
| `/kham-pha/[interest]` | Landing theo interest co entity list. | Neu interest khong du data de thanh trang rieng se mong. | P2: chi index SEO khi du nguong content; them curated intro va fallback search. |
| `/danh-ba` | Danh ba hanh chinh/facility, report flow. | Tim kiem/filter can server-side khi du lieu lon; can mask PII neu co. | P1: chuan hoa office kind, source, last verified; bulk report/update queue AdminCP. |
| `/tuyen-duong` | Static/curated route page. | Neu route khong linked voi planner/map thi thanh noi dung doc lap. | P1: route -> planner "dung lich trinh nay"; map preview va stop IDs. |
| `/lich-trinh` | Public itinerary catalog, cards. | Can filter theo thoi luong/vung/mua/chu de va share preview. | P1: itinerary card shape chuan, OG share, filter chuan; P2: save-to-plan analytics. |
| `/lich-trinh/[id]` | Detail itinerary co route, stops, save/share, AI recs. | Need offline/print/export; route calculation phu thuoc OSRM public demo. | P1: print/share/cue sheet; P2: cache route geometry, graceful fallback khi OSRM fail. |
| `/lich-trinh-chia-se/[id]` | Shared plan route gon. | Trang qua mong so voi hanh trinh public; can CTA copy/use. | P1: them "sao chep vao lich trinh cua toi", OG image/title, stop cards day du. |
| `/tao-lich-trinh` | Planner co saved/source tabs, auto-add `?add=`, local+server plans, map route. | Fetch `/api/entities?limit=700`; logic lon; nested interactions/a11y can tiep tuc tach. | P0/P1: endpoint picker search/paginated; saved/import from detail/list; keyboard DnD; conflict merge ro rang. |
| `/da-luu` | Da co `savedItemPath`, tab entity/post/itinerary, search, smart recs. | Saved counts/bookmarks/plans den tu nhieu API; remove/undo can tot hon. | P1: named lists lightweight, undo snackbar, "tao lich trinh tu da luu"; P2: save-to-plan conversion metric. |
| `/cong-dong` | Feed rat day du: latest/trending/following/bookmarks/search/composer/report/suggested follows. | Page 1500+ dong, qua nhieu state trong mot file; community trust can manh hon de tranh test/demo/noise. | P0/P1: tach feed/composer/sidebar/report; an seed/test posts prod; empty onboarding theo persona; moderation reason feedback. |
| `/bai-viet/[id]` | Post detail co comments/best answer/related. | Can surface accepted answer/Q&A tren entity detail va community; SEO/noindex policy can can nhac. | P1: thread type-specific layout: question/review/update; related entity/post cards cung contract. |
| `/nguoi-dung/[id]` | Profile route da fix username/id, posts/saved/follow/block/report/modal. | Privacy/saved/activity state phuc tap; route noindex tat ca profile co the han che community SEO. | P1: profile trust card, contribution areas, privacy badges; P2: index public expert profiles neu phap ly/consent ok. |
| `/tai-khoan` | UserCP dashboard co score, counts, next actions, activity, recommendations. | Score can giai thich bang hanh dong thuc te; counts saved co the chi bookmarks post/entity, chua phan biet itinerary. | P1: "today next best action" theo hanh vi; thong nhat saved/plans counts; quick resume planner. |
| `/cai-dat` | Settings lon: profile, security, sessions, privacy, blocked, notifications, export/delete. | File >1000 dong; copy password/session can tiep tuc lam ro; lazy tabs can tach. | P0/P1: tach tabs thanh components; security status tu `has_password`; session internal hidden; destructive action confirmation 2-step. |
| `/thong-bao` | Notifications list/read/dismiss/filter. | Notification target resolver can drift neu ref_type moi; no realtime fallback can fine. | P1: dung route resolver chung; group theo ngay/type; empty state goi y follow/save. |
| `/bang-xep-hang` | Leaderboard don gian. | Gamification de tao dong luc ao neu metric khong tin cay. | P2: xep hang theo dong gop huu ich, co giai thich, chong spam. |
| Static pages | Legal/about/contact/help/member guide co day du. | Noi dung dai can update theo phap ly; contact/report route can gan AdminCP. | P1: versioned policy, consent version, contact form -> info reports. |

## 4. AdminCP

| Trang admin | Hien trang | Rui ro/chua logic | Phuong an nang cap |
| --- | --- | --- | --- |
| `/admin` | Dashboard da co health, ops summary, release/deploy/queue/rollback/audit. | Can bien status thanh action ro: ai lam gi tiep theo. | P1: ops checklist co owner, SLA, link toi queue; P2: trend chart health/data quality. |
| `/admin/entities` | CRUD, inline edit, images, relationships, duplicate check, export current page. | File lon, sort client-side, export de hieu nham page/all. | P0/P1: server-side sort/filter/export scope label; form schema typed; bulk edit with dry-run. |
| `/admin/users` | Search/filter/role/ban/detail/posts/self-role guard. | Role tho user/mod/admin; RBAC scope chua hien o UI. | P1: scope editor `content.editor`, `moderation.manager`, `ops.deploy`, `settings.admin`, `security.admin`; audit reason bat buoc. |
| `/admin/kiem-duyet` | Moderation queue, batch approve/reject, notes/history. | Can SLA, reason template, appeal visibility. | P1: moderation cockpit: overdue, repeat offender, evidence preview, policy reason. |
| `/admin/bao-cao` | Reports + info reports, bulk resolve/dismiss. | Filter/paging client-side voi du lieu lon; action audit reason can ro hon. | P1: server-side filters; SLA 24/48h; bat buoc note khi dismiss. |
| `/admin/data-quality` | Summary, review candidates, dry-run/apply/decision/rollback/history. | Tot nhung can quality budget trend va ownership. | P1/P2: budget per field/source, batch owner, diff preview better, rollback drill. |
| `/admin/media` va `/admin/duyet-anh` | Media library/approval/remove. | Media license/credit pipeline can chuan hoa. | P2: license required, WebP sizes, image sitemap, broken image queue. |
| `/admin/lich-trinh` | Itinerary CRUD. | Planner/public itinerary contracts can lech. | P1: validate stops IDs/coords/areas, preview public detail, share status. |
| `/admin/danh-ba` va `/admin/chua-phan-loai` | Facility/places mapping, unclassified assignment. | Du lieu hanh chinh can nguon va audit manh. | P1: source required, last verified, bulk assignment dry-run. |
| `/admin/ai` | Cost/agent health/triage/trigger learn. | Can bao ve chi phi va khong tao ky vong AI tu dong qua muc. | P1: budget cap visible, last run/result, manual approval queue. |
| `/admin/thong-ke` | Analytics overview. | Can funnel metrics gan voi san pham: search, save, contact, plan. | P2: self-hosted funnel dashboard, zero-result queue, CWV trend. |
| `/admin/nhat-ky` | Audit log page. | Neu audit DB chua phu het action quan trong thi kho truy vet. | P0/P1: DB append-only audit cho role/scope/content/settings/report/data-quality/deploy. |
| `/admin/cai-dat/*` | Site settings forms, settings page/component. | Nhieu cau hinh co the gay SSR/hydration neu client/server lech. | P1: preview + validation + rollback per setting; publish draft vs live. |

## 5. Chuc nang ngang he thong

| Chuc nang | Hien trang | Phuong an |
| --- | --- | --- |
| Auth/session/password | Bearer token + cookie, CSRF token, password hash status, sessions hidden internal. | P0: tiep tuc roadmap HttpOnly cookie, copy has_password ro rang, session anomaly UI than thien. |
| Saved/favorites | Saved kind entity/post/itinerary da co route resolver. | P1: named lists/to-plan, undo, consistent counts across account/saved/planner. |
| Search/autocomplete | `useUnifiedSearch`, public `/api/search`, SearchAutocomplete. | P0/P1: contract typed, synonyms tieng Viet, SERP filters, zero-result queue. |
| Map | `/api/map-pins`, cluster/list. | P1/P2: bbox/list contract, selected state, accessible list, cache/index. |
| Reviews/Q&A/feed | First-party UGC, comments, best answer, reports, follow/block. | P1: accepted-answer surfacing, helpful/photo filters, owner/admin response labels. |
| Notifications | Read/read-all/dismiss/preferences/SSE route. | P1: target resolver typed; notification grouping; unread count consistency. |
| Data quality | Validation scripts + Admin DQ workflow. | P1/P2: trend budgets, duplicate source URL, image coverage, coordinate clusters, content duplication. |
| SEO/schema | Many pages build JSON-LD in frontend; backend also has data contracts. | P0/P1: backend schema source of truth for detail/event; snapshot tests. |
| Performance | CSS splitting done, lazy components, smoke tests. | P2: query bounded, materialized summaries, map/event/home cache, Lighthouse/CWV budgets. |
| Security/ops | Health/internal, deploy gate, route guards, audit tests. | P0: keep route guard test matrix; edge block internal paths; deploy least-privilege env. |
| Type safety | Many response shapes loose/`any`; vue-tsc debt known. | P1/P2: typed API response modules per domain, flip typecheck to blocking after debt reduction. |

## 6. Lo trinh thuc thi de toi uu tung phan

### Batch P0 - dong bo contract va chan loi

1. Search/saved/notification route resolver typed: entity/post/user/itinerary card shape chung.
2. Detail JSON-LD/backend source of truth va snapshot test.
3. Planner picker bo `limit=700`, dung search/paginated endpoint.
4. Admin export/sort scope labels + server-side sort cho entities/users/reports.
5. Route guard/security smoke cho internal/system/admin/write paths.

### Batch P1 - nang cap hanh trinh nguoi dung

1. Unified catalog shell cho `/dia-diem`, `/du-lich`, `/san-pham`, `/ocop`, `/luu-tru`, `/le-hoi`, `/su-kien`, `/theo-mua`.
2. Detail trust layer: source, last verified, report stale, contact confidence.
3. Map/list split: selected card, bbox, mobile toggle, save/add-to-plan action.
4. Saved -> planner: tao lich trinh tu danh sach da luu, undo/remove, counts dong bo.
5. Community/user split components; onboarding theo persona; hide seed/test in production.
6. UserCP "next best action" va resume planner/saved/activity.
7. AdminCP ops workflow: owner, SLA, reason templates, quality budget.

### Batch P2 - world-class polish

1. Personalization nhe, giai thich duoc: season, area preference, recently viewed, saved categories.
2. Performance: materialized home/map/event/review stats; SWR cache; bounded SQL; CWV budgets.
3. SEO: media sitemap, event/season landing internal links, OG for shared itinerary.
4. Observability: zero-result search, save-to-plan, contact funnel, moderation SLA trend.
5. Media trust: legal/free upload pipeline, WebP sizes, credit/license, broken image queue.

## 7. Tieu chi nghiem thu

- Core smoke: `/`, `/tim-kiem`, `/dia-diem`, `/ban-do`, `/cong-dong`, `/nguoi-dung/testuser09`, `/tai-khoan`, `/cai-dat`, `/da-luu`, `/lich-trinh`, `/tao-lich-trinh`, AdminCP key pages khong 500 va khong console error.
- UX smoke: detail -> planner auto-add, saved itinerary path, map list/popup, search autocomplete/SERP parity, le-hoi category tokenized, account password/session copy.
- Admin smoke: entities CRUD, users self-role guard, moderation batch, reports bulk, data-quality dry-run/apply/rollback, media approve/reject.
- Data gates: `validate_data.py`, quality budgets, JSON-LD snapshot parity, duplicate content/source/coordinate checks.
- Deploy gates: migration gate, health/ready/home smoke blocking, rollback readiness, production smoke tren `vinhlong360.vn`.


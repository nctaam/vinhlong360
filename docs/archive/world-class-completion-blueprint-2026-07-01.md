# World-class completion blueprint - vinhlong360 - 2026-07-01

> **STATUS (2026-07-07): ARCHIVED — Tài liệu LỊCH SỬ đã archive (truth-sync 2026-07-07). KHÔNG làm theo chỉ dẫn trong file này — đối chiếu CLAUDE.md + docs/README.md.**
> Blueprint chồng lấn (2/3). Chẩn đoán code-infra đã bị vượt bởi re-audit 04/07 + chốt "bottleneck = content/ảnh"; license-gate đa nguồn media đã chết tiền đề (ảnh CHỈ AI-gen).


## 1. Cau tra loi ngan

Co the dao sau hon nua. Tang sau nhat khong phai them nhieu trang hon, ma la bien vinhlong360 tu "mot web app day tinh nang" thanh "mot he thong kham pha dia phuong dang tin, co tri nho, co quy trinh van hanh, co do luong, co kha nang tu cai thien".

World-class cho vinhlong360 khong nen la booking/payment hay AI phuc tap. World-class o day la:
- Tim thay dung thu nhanh.
- Tin duoc du lieu va biet vi sao tin.
- Chuyen tu cam hung sang hanh dong: xem, luu, lap lich trinh, lien he, bao sai.
- Admin van hanh duoc nhu mot newsroom + ops cockpit.
- Moi release an toan, co rollback, co quan sat, co thang do chat luong.

## 2. Maturity ladder

| Level | Trang thai | Mo ta | Dieu kien len level |
| --- | --- | --- | --- |
| L0 | Prototype | Co trang, co du lieu, co UI, co API. | Core route render duoc. |
| L1 | Stable product | Khong 500, khong console error, deploy co gate. | Smoke E2E, migration gate, health/ready. |
| L2 | Coherent journeys | Search, detail, saved, planner, community, user cp lien ket logic. | Contract chung + CTA tiep theo ro. |
| L3 | Trusted knowledge base | Moi fact co source/confidence/freshness; data-quality co budget. | Trust layer + provenance model + DQ trend. |
| L4 | Operational cockpit | AdminCP quan ly queue, SLA, audit, release, rollback, cost, data drift. | Ops summary thanh workflow co owner/action. |
| L5 | Adaptive experience | He thong hieu ngu canh nhe: mua, vung, saved, recently viewed, intent. | Rule-based personalization co reason, khong black-box. |
| L6 | Civic-grade local platform | Du de phuc vu cong dong/doanh nghiep/dia phuong: tin cay, phap ly, bao tri duoc. | Compliance ops, restore drill, audit export, data governance. |

Hien tai du an dang o giua L2-L3 cho user journey, L3 cho mot phan data quality, L3-L4 cho AdminCP/ops. De "cao hon, hoan thien hon", muc tieu nen la L5 truoc, sau do L6.

## 3. 12 he thong chien luoc can hoan thien

| He thong | Tinh trang hien tai | Nang cap cao hon |
| --- | --- | --- |
| 1. Experience intelligence | Co saved/recent/user events/contextual recommendations. | Tao "intent model" nhe: tourist/local/owner/admin, time budget, season, area preference. |
| 2. Discovery/search | Co unified search, BM25/contextual nen tang. | Search contract typed, synonym tieng Viet, zero-result queue, relevance eval hang tuan. |
| 3. Trust graph | Co source, confidence, DQ, report stale. | Fact-level provenance, source tier, verified_at, confidence reason, trust badge. |
| 4. Geospatial system | Co coords, approximate flag, map-pins, ward overview. | Bbox API, spatial QA, coordinate confidence, map/list synchronized state. |
| 5. Content architecture | Co catalog/detail/static docs. | Structured content blocks: practical facts, story, how-to-go, source, related routes. |
| 6. Planner engine | Co planner, my-plans, route OSRM, share. | Plan from saved, route cache/fallback, cue sheet, printable/exportable itinerary. |
| 7. Community knowledge | Co feed/posts/comments/follow/report/best answer. | Reputation by usefulness, accepted answers on detail, owner/admin responses, anti-seed-prod. |
| 8. User control plane | Co account/settings/privacy/security/saved/activity. | Next-best-action, resume workspace, privacy-aware profile, contribution portfolio. |
| 9. Admin operating system | Co dashboard, DQ, moderation, reports, users, media. | Workflow engine: owner, SLA, policy reason, batch diff, audit, rollback, metrics. |
| 10. Reliability/security | Co CSRF, route guards, shared rate, deploy gate. | Auth cookie migration, CSP, rate dashboards, route guard generation, restore drills. |
| 11. Observability/experiments | Co client-error endpoint, health, analytics overview. | Event taxonomy, funnels, SLO trend, no-result/search/contact/save-to-plan analytics. |
| 12. Delivery/governance | Co roadmap, release gate, deploy script. | Release train, changelog, risk register, phase scorecard, quarterly review. |

## 4. Cau hoi sau nhat can tra loi

1. Neu visitor chi co 3 phut tren mobile yeu, trang nao giup ho quyet dinh nhanh nhat?
2. Neu du lieu sai, user bao sai xong admin thay doi, bao lau trang public het sai?
3. Neu admin doi role/scope/setting nham, co audit va rollback du khong?
4. Neu search khong ra ket qua, he thong hoc duoc gap noi dung nao khong?
5. Neu deploy xong asset cu con trong service worker, user co cach reload phien ban moi khong?
6. Neu API mot block trang chu fail, trang co degrade thanh "trang trong" hay van huong user tiep?
7. Neu mot entity co anh khong license, release gate co chan khong?
8. Neu mot toa do la centroid xa, UI co ngan user hieu nham la toa do chinh xac khong?
9. Neu cong dong bi bai test/spam, production co tu an/flag khong?
10. Neu search/detail/planner/saved moi cai dung shape khac nhau, lam sao ngan drift trong 6 thang toi?

## 5. Kien truc muc tieu cap cao

```text
PostgreSQL source of truth
  -> migrations + schema_version gate
  -> data provenance + media license + quality budgets
  -> FastAPI typed contracts
      -> public discovery APIs
      -> user/social APIs
      -> admin workflow APIs
      -> health/ops APIs
  -> Nuxt SSR
      -> typed api client
      -> routeRules/SWR policy
      -> service worker governed cache
      -> accessible responsive UI
  -> Observability
      -> client errors
      -> search zero-result
      -> save/contact/plan funnels
      -> admin SLA/data quality trend
  -> Release system
      -> migration gate
      -> test gate
      -> production smoke
      -> backup + restore drill
```

## 6. Chuong trinh nang cap cap 2

| Program | Muc tieu | Ket qua khi hoan thanh |
| --- | --- | --- |
| P-A. Product intelligence | Bien cam nhan user thanh metric. | Biet search nao fail, CTA nao duoc bam, route nao gay loi, module nao co gia tri. |
| P-B. Contract-first system | FE/BE khong drift. | API shape typed, snapshot, smoke, docs auto-updated. |
| P-C. Trust-first data | User biet nguon va do tin cay. | Moi detail co source/freshness/confidence/report path. |
| P-D. Local discovery engine | Kham pha theo mua/vung/nhu cau. | Search, catalog, map, season, region, planner cung noi mot ngon ngu. |
| P-E. Planner workspace | Saved va detail khong bi dead-end. | User tao duoc lich trinh tu saved/detail/map/search rat nhanh. |
| P-F. Community knowledge | UGC thanh tri thuc, khong chi feed. | Cau hoi hay, review huu ich, owner/admin response, profile uy tin. |
| P-G. Admin workflow engine | AdminCP thanh noi lam viec hang ngay. | Queue/SLA/owner/batch/reason/audit/rollback ro rang. |
| P-H. Media/data legality | Khong so anh/nguon sai phap ly. | License gate, credit/source, excerpt-only crawler, image sitemap. |
| P-I. Reliability lab | Moi release co bang chung on dinh. | Visual/E2E/security/data/perf gates theo route. |
| P-J. Performance lab | Mobile nhanh, khong phinh JS/CSS. | CWV budget, route chunk, query bounded, cache policy. |
| P-K. Security/compliance ops | Du an san sang van hanh cong khai nghiem tuc. | Auth cookie, CSP, admin IP/VPN, audit retention, consent version, incident drill. |
| P-L. Governance | Khong mat phuong huong khi du an lon len. | Scorecard, risk register, release notes, phase review, decision log. |

## 7. Scorecard world-class

Cham diem moi release theo 10 nhom, thang 0-5:

| Nhom | 0 | 3 | 5 |
| --- | --- | --- | --- |
| Stability | Hay 500/console error. | Smoke core pass. | Smoke + visual + SLO trend pass. |
| Trust | Co noi dung nhung thieu nguon. | Source/freshness tren detail. | Fact-level provenance + budget trend. |
| Discovery | Tim co ket qua co ban. | Search/filter/map/planner lien ket. | Search hoc zero-result + rec reason. |
| Mobile UX | Dung duoc. | Touch/filter/CTA tot. | 360px-414px polished, offline/update UX. |
| Accessibility | Co aria rahi rac. | Keyboard core flows. | Axe + manual screen reader route core. |
| Admin ops | CRUD duoc. | Queue/action/audit co ban. | SLA/owner/rollback/cost/data drift cockpit. |
| Security | Guard co ban. | CSRF/rate/route guard. | Cookie auth/CSP/audit retention/drills. |
| Performance | Build chay. | CSS split/cache. | CWV budgets + bounded queries. |
| Data quality | Validate pass. | Quality budget. | Trend/ownership/source tier/media legal. |
| Delivery | Deploy script. | Gate fail hard. | Scheduled prod smoke + restore drill. |

Muc tieu 3 thang: moi nhom >=3.5. Muc tieu 6-9 thang: moi nhom >=4.5.

## 8. 30 nang cap "cao hon" nen uu tien sau 50 phase

1. Generated route/API dependency graph.
2. Typed API client generator tu OpenAPI hoac schema noi bo.
3. Contract snapshot test cho all public response shapes.
4. Service worker update banner va cache test.
5. Visual regression baseline 7 route x 4 viewport.
6. Axe + keyboard audit cho search/detail/map/planner/community/usercp/admin.
7. Event taxonomy cho analytics: search, save, plan, contact, report, share, follow.
8. Zero-result queue trong AdminCP.
9. Contact funnel by entity/source/referrer.
10. Save-to-plan conversion dashboard.
11. Trust badge engine based on source/freshness/confidence.
12. Fact-level stale queue.
13. Media license required before publish.
14. Image broken/slow/missing queue.
15. Coordinate confidence heatmap.
16. Map bbox API with list sync.
17. Planner route cache and print cue sheet.
18. Named saved lists.
19. Profile contribution portfolio.
20. Community accepted answer surfaced on entity detail.
21. Owner/admin response workflow.
22. RBAC scope editor and policy docs.
23. HMAC chain or append-only audit verification.
24. Audit export/retention/backup.
25. Rate-limit hit dashboard.
26. Restore drill script and quarterly report.
27. Release notes generated from merged phases.
28. Data-quality trend report by type/area.
29. Content freshness calendar before seasonal peaks.
30. "World-class score" visible in AdminCP ops cockpit.

## 9. Thu tu thuc thi neu muon len level nhanh

1. Build measurement spine: event taxonomy, client errors, zero-result, contact/save/plan funnels.
2. Build contract spine: typed API client, route/API graph, snapshot tests.
3. Build trust spine: provenance, freshness, media license, detail trust block.
4. Build workflow spine: AdminCP queue/SLA/audit/rollback.
5. Build experience spine: unified catalog, map/list, saved-to-planner, user next-best-action.
6. Build delivery spine: SW governance, visual regression, CWV, restore drill.

## 10. Dinh nghia "hoan thien"

Du an duoc coi la hoan thien o muc world-class khi:
- 95% core user tasks pass E2E tren production.
- 0 console error tren route core trong smoke.
- 0 known P0/P1 security route gap.
- 100% entity public co source/freshness/confidence state.
- 100% anh publish co license/credit/source hoac fallback hop le.
- Search zero-result co queue va giam theo thang.
- Admin reports/moderation/DQ co SLA va audit.
- Backup restore drill thanh cong trong thoi gian dinh muc.
- Moi release co changelog, gate, smoke, rollback note.
- User co the di tu search -> detail -> save -> plan -> contact/report trong mot dong chay khong dut.


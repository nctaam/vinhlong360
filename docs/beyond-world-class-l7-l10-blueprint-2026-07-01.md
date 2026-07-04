# Beyond world-class L7-L10 blueprint - vinhlong360 - 2026-07-01

## 1. Direction

The next level is not "more pages". The next level is turning vinhlong360 into a local intelligence platform: trusted knowledge, coherent journeys, measurable quality, and operations that can improve the product without guesswork.

Keep the existing product boundary:
- No booking/payment/marketplace.
- Vietnamese-first, web-first.
- Keep FastAPI, PostgreSQL, Nuxt SSR, VPS/tarball deployment.
- AI is allowed only when it is explainable, observable, and reversible.

## 2. L7-L10 maturity model

| Level | Name | What changes | Acceptance |
| --- | --- | --- | --- |
| L7 | Trusted local knowledge graph | Entities, events, posts, areas, seasons, routes, media, sources, and user signals share one graph contract. | Search/detail/map/planner/recommendation can explain why a result appears. |
| L8 | Adaptive journey system | Home/search/map/detail/saved/planner/community react to user intent and context without fake personalization. | First-time, returning, saved-heavy, planner-heavy, local, tourist, and admin journeys have different next-best actions. |
| L9 | Autonomous quality and ops | The system detects stale data, weak sources, missing media license, coordinate doubt, spam/test content, broken routes, and release risk. | AdminCP shows queues with owner, SLA, evidence, diff, approval, rollback, and quality budget trend. |
| L10 | Civic-grade local platform | The system is reliable enough for public local discovery and operational reporting. | Audit/export/restore/release/security/privacy workflows are documented, tested, and measured. |

## 3. Strategic systems

### 3.1 Local knowledge graph

Core objects:
- Entity: place, product, food, accommodation, attraction, facility.
- Event: festival, seasonal event, recurring local activity.
- Area: province, district legacy area, ward/commune.
- Route/itinerary: curated route, user plan, shared plan.
- Post/Q&A/review: community knowledge attached to entity/area/topic.
- Media asset: image/video with license, credit, source, derivatives.
- Source/fact: provenance, confidence, verified_at, freshness policy.

Graph edges:
- `located_in`, `near`, `belongs_to_route`, `best_in_season`, `serves`, `hosts_event`, `mentions`, `reviewed_by`, `reported_by`, `verified_by`, `source_supports`.

Acceptance:
- Public cards use one card contract.
- Similar/nearby/contextual recommendations return `reason_vi`.
- Detail pages show trust and practical facts from the same source of truth.

### 3.2 Adaptive journey system

Intent model, rule-based first:
- `visitor_first_time`
- `visitor_mobile_fast_decision`
- `tourist_weekend`
- `local_today`
- `saved_heavy`
- `planner_active`
- `community_contributor`
- `admin_operator`
- `owner_or_local_business`

Signals:
- Current route, query, filters, saved count, recent views, active plan, season/month, area preference, login state, device class.

Actions:
- Continue plan.
- Create plan from saved.
- Show nearby/on-map.
- Report stale data.
- Ask community.
- View trusted source.
- Open admin queue.

Acceptance:
- Every major page has a clear "next action".
- No page is a dead-end after save/search/detail/map/community.
- Personalization is explainable and can be disabled or ignored.

### 3.3 Autonomous quality engine

Quality signals:
- Missing or weak source.
- Old `verified_at`.
- Missing image/license/credit.
- Duplicate text, broken sentence join, overlong description.
- Approximate or suspicious coordinates.
- Stale event date.
- Community seed/test/spam content in production.
- Search zero-result and low-result queries.
- CTA click failure or user bounce after search/detail.

Admin workflow:
- Queue item with severity, owner, SLA, evidence, suggested fix, dry-run diff, approval, rollback pointer.

Acceptance:
- Quality budget is visible in AdminCP and release gate.
- New content cannot publish without minimum source/media/trust requirements when applicable.
- Admin can see what changed, why, by whom, and how to revert.

### 3.4 Civic-grade reliability

Reliability contracts:
- Public `/health` is minimal.
- `/health/internal` and `/system/*` are guarded.
- Release gate blocks schema drift, frontend smoke, backend guards, data quality, and production smoke when required.
- Service worker has version/update policy.
- Backup/restore drill is documented and periodically tested.

Acceptance:
- No deploy is called done until health/ready/home/smoke pass.
- Internal paths are blocked at app and edge layers.
- Every release has affected routes, risk notes, rollback state, and smoke outcome.

## 4. Implementation batches

### Batch A - Contract and safety foundation

Output:
- Typed public API contracts for search, entities, saved, planner, notification targets.
- Thin public API client using `apiFetch`.
- Planner no longer fetches `/api/entities?limit=700`.
- Sensitive route guard matrix script in release gate.
- Chrome smoke checks core controls, 500s, console errors, and route contracts.

Acceptance:
- `vitest` smoke passes.
- Planner auto-add from `?add=<entityId>` works through direct entity lookup.
- Release gate includes guard matrix.

### Batch B - Trust graph foundation

Output:
- Source/fact/media contract documentation and first backend response shape.
- Detail trust block uses source, verified date, confidence, stale report.
- Recommendation contract normalizes cards and `reason_vi`.

Acceptance:
- Detail/recommendation cards explain trust/reason.
- Data quality budget tracks missing source/media/license.

### Batch C - Adaptive journeys

Output:
- Home decision engine.
- Saved workspace next action.
- Search zero-result recovery.
- Detail to planner/map/community/report flows.

Acceptance:
- Core visitor tasks have one obvious next step.
- UserCP shows resume/continue actions instead of static dashboard only.

### Batch D - Admin intelligence cockpit

Output:
- Admin queues by severity/SLA.
- RBAC scope UI parity.
- Audit DB coverage for settings/users/content/DQ/media/deploy.
- Dry-run/approve/rollback workflow for quality fixes.

Acceptance:
- Admin action path is queue -> evidence -> action -> audit -> metric.

### Batch E - Production excellence

Output:
- Visual regression baseline.
- Search relevance eval set.
- Service worker update UX.
- Backup restore drill.
- Release risk score.

Acceptance:
- Production smoke on vinhlong360.vn is part of release acceptance.
- Quality and reliability improve by trend, not opinion.

## 5. Immediate execution rule

Start with Batch A because it reduces drift and unlocks safer future work. Do not wait for perfect architecture. Ship small contracts, move pages onto them, and make gates catch regressions.


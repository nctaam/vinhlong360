# NP-1 Stitch verification

> STATUS (2026-07-29): verification complete with rendered-runtime limitation.

Date: 2026-07-29 (Asia/Bangkok)

Status: automated behavior, type and build gates pass; rendered Browser/Chrome evidence is blocked by the local browser/server runtime described below. No screenshot or visual pass is claimed.

## Scope and target flow

Target flow: `/cai-dat#khu-vuc-de-xuat` -> explicit user gesture for manual region or approximate location -> personalized recommendation -> open WhyThis/source trust -> observe the dialog and state.

The committed Chrome runner uses the real Nuxt pages and components with a complete deterministic API fixture at the network boundary. It contains no credential and keeps its Chrome profile and screenshots in the operating-system temporary directory or in memory.

## Stitch reference mapping

Live Stitch retrieval was unavailable in this session. Tool discovery exposed no Stitch callable tool, resource, or resource template, so the table records mapping intent from the already verified screen IDs without claiming fresh Stitch evidence.

| Role | Screen ID | Borrowed anatomy | Deliberate adaptation | Result |
| --- | --- | --- | --- | --- |
| Detail V2 | `6a86654f63f243679ebe997ea340172b` | Source evidence hierarchy, right-side disclosure and freshness grouping | `SourceTrustDrawer` keeps Nuxt tokens, semantic `dl`, focus management, report action and real official/verified evidence rules | Mounted behavior PASS; rendered visual unverified |
| Saved itinerary | `db76e318f0354ee3b1b8e3a0860443a5` | Dense grouped controls and compact workspace rhythm | `/cai-dat` preference summary, manual-region group, controls and reset stay inside the existing settings system | Mounted behavior PASS; rendered visual unverified |
| Community | `dc2a7a19958e442a990f548953a042e9` | Community identity and moderation context | Community remains a distinct trust tier and never inherits official semantics | Mounted behavior PASS; rendered visual unverified |
| Mobile dark premium | `9dac45c42bd7470797ff912060690909` | Bottom-sheet anatomy, dark surface hierarchy and sticky action | `PersonalizeSetupSheet`, `WhyThisDrawer` and `SourceTrustDrawer` preserve 44px controls, safe-area padding and reduced-motion CSS | Component/A11y behavior PASS; rendered visual unverified |
| Search | `41df1bef12c443fe8247a62b3f50f419` | Compact explanation density and secondary disclosure controls | `WhyThisDrawer` shows only allowlisted broad signals and links to `/cai-dat#khu-vuc-de-xuat` | Mounted behavior PASS; rendered visual unverified |

## Behavior evidence

- `SmartRecommendations` is mounted with the real `WhyThisDrawer`; a response containing only `reason_vi: "Cùng khu vực bạn chọn"` opens the drawer and renders the privacy-safe canonical broad reason rather than the generic fallback.
- `/dia-diem/[id]` is mounted with a complete official-source entity; its real source trigger opens `SourceTrustDrawer`, displays `Cổng thông tin tỉnh Vĩnh Long`, and invokes report navigation.
- Settings state coverage distinguishes `unknown`, `manual`, `gps`, `ip`, `off`, `denied`, `expired`, `offline`, and `conflict` without exposing raw GPS/IP or exact age.
- The consumer boundary covers manual, GPS, IP, and default region sources; disabled GPS is ignored while disabled manual selection stays active.
- An offline failed mutation preserves the cached manual region and explicit interest; explicit retry performs a refresh and does not replay the mutation.
- The stale `USER_EVENTS_FILE` source-text check was replaced by mounted `useUserEvents` behavior that normalizes and de-duplicates the event while leaving the rendered surface usable.

## Viewport and accessibility matrix

The Chrome script defines and captures these baselines in memory:

| Viewport | Light | Dark | Reduced motion | 200% text |
| --- | --- | --- | --- | --- |
| Desktop 1440 x 1000 | Scripted, not reached | Scripted, not reached | Not required separately | Not required separately |
| Desktop 1024 x 768 | Scripted, not reached | Scripted, not reached | Not required separately | Not required separately |
| Mobile 390 x 844 | Scripted, not reached | Scripted, not reached | Scripted, not reached | Scripted, not reached |

The runner checks page identity, non-blank content, target interactions, dialog state, console/runtime failures, horizontal overflow, reduced-motion emulation, and in-memory PNG capture. None of those rendered checks is marked PASS because Nuxt dev did not expose its HTTP listener in this runtime.

## Browser and Chrome runtime

- Browser classification: invocation failed.
- Browser setup through the required `browser-client.mjs` succeeded, but `getForUrl("http://localhost:3000/cai-dat#khu-vuc-de-xuat")` returned `No browser is available`.
- Required bootstrap troubleshooting was read; `agent.browsers.list()` returned `[]`.
- MCP resources contained only Codex Security UI resources and no Stitch resource/template.
- Chrome fallback is explicitly permitted by the task's required Chrome script. `node scripts/smoke_personalization_chrome.mjs` was attempted before and after the production build. Each run ended after 90 seconds with:

```text
Error: Timed out waiting for http://127.0.0.1:3199: |
```

- Direct Nuxt startup diagnostic `node node_modules\nuxt\bin\nuxt.mjs dev --host 127.0.0.1 --port 3199` timed out after 34 seconds with no output or listening socket. Adding `--no-fork --logLevel info` did not change the smoke result.
- The exact diagnostic process tree created by this task was stopped and verified absent. No screenshot, Chrome profile, trace, or build artifact is tracked.

## Commands and results

```text
npm test -- tests/smoke.test.ts tests/personalization-preferences.test.ts tests/location-consent.test.ts tests/why-this-trust.test.ts
PASS: 4 files, 150 tests

npm test
PASS: 41 files, 991 tests

npm run typecheck
PASS: exit 0

npm run build
PASS: exit 0, build complete, launch readiness manifest generated
Warnings: existing module-preload sourcemap warning, chunk-size warning, and Node DEP0155 warning

node --check scripts/smoke_personalization_chrome.mjs
PASS: exit 0, no output

node scripts/smoke_personalization_chrome.mjs
BLOCKED: Nuxt HTTP startup timeout shown above
```

## Limitations

- No live Browser or Chrome-rendered screenshot evidence is available, so visual fidelity, console health in a rendered browser, viewport layout, theme rendering, reduced motion and 200% text zoom remain unverified.
- The fixture represents an already registered authenticated session; the runner verifies skip/configure-later behavior but intentionally does not automate OTP registration or store a credential.
- Stitch comparison is anatomy mapping only. No generated Stitch HTML or live Stitch response was used.

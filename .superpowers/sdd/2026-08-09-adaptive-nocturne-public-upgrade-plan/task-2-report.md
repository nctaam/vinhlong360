# Task 2 implementation report

## Files changed

- `web-nuxt/assets/css/base.css`
- `web-nuxt/components/shell/PublicBottomNav.vue`
- `web-nuxt/components/shell/PublicContextBar.vue`
- `web-nuxt/components/shell/ThemeModeControl.vue`
- `web-nuxt/layouts/default.vue`
- `web-nuxt/tests/theme-mode-control.test.ts`
- `web-nuxt/tests/ui-foundation-shell.test.ts`

## Implementation

- Exposed one stable `data-public-shell="nocturne"` marker and one reusable `data-public-context-line` marker in the rendered public shell.
- Connected the context line to the privacy-safe Task 1 `ContextEnvelope` and exposed only its location mode; rendered HTML remains coordinate-free and region changes preserve the current route.
- Added stable markers for all five mobile navigation destinations without changing routes or active-state behavior.
- Synchronized the semantic document theme marker (`nocturne` or `parchment`) with hydration, explicit selection, and later `useColorMode()` preference changes. The exact accessible name `Nền sáng dễ đọc` now matches the contract.
- Mapped semantic theme markers to native `color-scheme`; existing Nocturne/Parchment semantic tokens, shell reduced-motion rules, forced-colors rules, and mobile safe-area padding remain the shared foundation.

## Verification

- `npm --prefix web-nuxt test -- nocturne-theme-contract.test.ts theme-mode-control.test.ts ui-foundation-shell.test.ts` - PASS (3 files, 26 tests).
- `npm --prefix web-nuxt run typecheck` - PASS (exit 0).
- `git diff --check -- <Task 2 files>` - PASS (exit 0; only repository line-ending warnings).

## Responsive checks

Terminal recovery did not use the unavailable browser/tunnel path. The required manual follow-up matrix is 390x844, 768x1024, and 1440x900 in Nocturne and Parchment, checking navigation overlap, Escape focus restoration, and Vietnamese text/action clipping at 200% zoom. Reduced-motion and forced-colors shell fallbacks are present in `assets/css/shell.css`; their visual result remains part of that manual matrix.

## Scope and concerns

- Existing unrelated dirty and untracked files were preserved and excluded from staging.
- False-404 behavior and feature kill-switch tests are assigned to later detail/rollout tasks in the authoritative plan; Task 2 has no detail-fetch or rollout-flag implementation surface.
- Raw-location redaction is an explicit Task 2 rendered-shell assertion. The responsive/200% zoom matrix remains manually unverified in this terminal-only recovery.

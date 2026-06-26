# Session 9: Shared FE — Layouts, Composables, CSS, Shared Components

> Paste toàn bộ nội dung này làm message đầu tiên.

## Bối cảnh

Worktree `C:/Code/vl360-shared-fe`, nhánh `dev/shared-fe`. Dự án vinhlong360. **Đọc `CLAUDE.md` + `docs/PARALLEL-BRANCHES.md`.**

## Phạm vi file SỞ HỮU

**Layouts:**
- `web-nuxt/layouts/default.vue` — Main layout (header/nav/footer)

**CSS:**
- `web-nuxt/assets/css/base.css` — Design system tokens + global styles

**Shared components (không thuộc session khác):**
- `ToastContainer.vue`, `ConfirmDialog.vue`
- `ErrorBoundary.vue`, `EmptyState.vue`
- `SkeletonGrid.vue`, `SkeletonList.vue`
- `ScrollToTop.vue`

**Shared composables (không thuộc session khác):**
- `useToast.ts`, `useConfirm.ts`, `useConstants.ts`
- `useCoords.ts`, `useClientError.ts`
- `useFavorites.ts`, `useRecentlyViewed.ts`
- `useReveal.ts`, `useScrollFade.ts`
- `useFilterUrl.ts`, `useInfiniteScroll.ts`
- `useModalA11y.ts`, `useSeason.ts`
- `useLunar.ts`, `useTimeAgo.ts`
- `useSeoHelpers.ts`, `useRouting.ts`
- `useSiteSettings.ts`, `usePageContent.ts`
- `useFeature.ts`, `useCategoryPlaceholder.ts`
- `useRegionPref.ts`, `useAdminPrefs.ts`

**App-level:**
- `web-nuxt/app.vue`, `web-nuxt/error.vue`

**KHÔNG SỬA:** page files, admin layout, agent/*.py, nuxt.config.ts.

## Công việc — Audit 10 tầng shared infrastructure

### Layout (`default.vue`):
- T3: Header/footer consistency, nav active state, mobile hamburger
- T4: Skip-to-content, landmark roles, focus management on route change
- T9: Mobile nav, responsive breakpoints

### CSS (`base.css`):
- T3: Token consistency (colors, spacing, typography)
- T4: Focus-visible styles, reduced-motion, dark mode
- T6: Unused CSS cleanup (đã làm 1 pass — kiểm tra lại)

### Shared components:
- ToastContainer: stacking, dismiss, screen reader announcement
- ConfirmDialog: focus trap, keyboard (Enter/Escape)
- ErrorBoundary: fallback rendering, retry
- Skeleton: shimmer animation, dark mode

### Composables:
- useInfiniteScroll: edge cases (empty list, rapid scroll)
- useModalA11y: focus trap completeness
- useFavorites/useRecentlyViewed: localStorage quota handling

## Verify

```bash
python -m pytest -q
cd web-nuxt && npm run build
```

## Commit prefix: `[shared-fe]`

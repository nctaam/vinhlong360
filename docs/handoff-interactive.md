# Session 3: Bản đồ, Tìm kiếm & Lịch trình
<!-- Phạm vi: Bản đồ, tìm kiếm, tạo lịch trình, chat AI, khám phá theo sở thích, bảng xếp hạng + component riêng (ChatWidget, SearchAutocomplete, ItineraryCard, AI*.vue) -->

> Paste toàn bộ nội dung này làm message đầu tiên.

## Bối cảnh

Worktree `C:/Code/vinhlong360/vl360-interactive`, nhánh `dev/interactive`. Dự án vinhlong360. **Đọc `CLAUDE.md` + `docs/PARALLEL-BRANCHES.md`.**

## Phạm vi file SỞ HỮU

**Pages:**
- `web-nuxt/pages/ban-do.vue` — Bản đồ
- `web-nuxt/pages/tim-kiem.vue` — Tìm kiếm
- `web-nuxt/pages/tao-lich-trinh.vue` — Tạo lịch trình (builder)
- `web-nuxt/pages/lich-trinh/index.vue` — Danh sách lịch trình
- `web-nuxt/pages/lich-trinh/[id].vue` — Chi tiết lịch trình
- `web-nuxt/pages/lich-trinh-chia-se/[id].vue` — Lịch trình shared
- `web-nuxt/pages/kham-pha/[interest].vue` — Khám phá theo sở thích
- `web-nuxt/pages/bang-xep-hang.vue` — Bảng xếp hạng

**Components:**
- `ChatWidget.vue` — AI chat
- `SearchAutocomplete.vue` — Typeahead
- `ItineraryCard.vue`
- `AIBestTime.vue`, `AIRecommendations.vue`, `AISearchAssist.vue`, `AITravelTips.vue`

**KHÔNG SỬA:** agent/*.py (backend), base.css, layouts/, admin/**, user pages, EntityCard.

## Công việc — Audit 10 tầng

**Ưu tiên:**
1. **Search** (`tim-kiem.vue`) — core UX, typeahead, results display
2. **Map** (`ban-do.vue`) — fallback khi không có API key, mobile height, tile error
3. **Itinerary builder** — drag-drop, mobile UX, save flow
4. **Chat widget** — error handling, abort, mobile
5. **Khám phá** — content rendering, empty states

**Kiểm tra:**
- T1: Search returns relevant results, map loads, itinerary save works
- T3: Search UX (debounce, clear, empty state), map controls
- T4: Keyboard nav in search results, focus management
- T8: Offline/error fallback cho map tiles, API timeout
- T9: Mobile map height, touch controls, search input

## Verify

```bash
python -m pytest -q
cd web-nuxt && npm run build
```

## Commit prefix: `[interactive]`

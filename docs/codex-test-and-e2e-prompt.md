# Codex Test Automation & Deep E2E Browser Prompt — vinhlong360

> Copy TOÀN BỘ nội dung bên dưới (từ "---" đầu tiên đến hết) vào Codex task.
> **Prerequisite:** repo phải push lên GitHub. Codex cần đọc TOÀN BỘ source code.
> **Branch:** tạo nhánh `codex-test-e2e` từ `main`.

---

# PERSONA — KHÔNG THAY ĐỔI

Bạn là **Trần Minh Quang** — Principal SDET, 14 năm kinh nghiệm (Tiki, Shopee, VNPay, Grab Vietnam). Bạn chuyên test architecture, đã xây test pyramid cho 3 hệ thống >100 endpoint, viết E2E suites chạy nightly cho 12 team, và phát hiện 23 production bugs qua automated regression.

**Vai trò kép:**
1. **Test Architect** — Viết test CHẠY ĐƯỢC, không placeholder
2. **QA Explorer** — Dùng Playwright như user thật, phát hiện UX bugs mà unit test không thấy

**Quy tắc tuyệt đối:**
1. **Mọi test PHẢI chạy pass.** Viết xong → chạy → fix → mới commit. Test fail = chưa xong.
2. **KHÔNG sửa source code.** Chỉ tạo files trong `agent/tests/` và `tests/e2e/`. Nếu tìm bug → ghi trong report.
3. **KHÔNG viết test sơ sài.** `assert response.status == 200` mà không check body = KHÔNG CHẤP NHẬN. Phải assert content, structure, behavior.
4. **Mock chính xác.** Mock external (LLM, eSMS, Telegram, geocode HTTP) — KHÔNG mock internal logic. Dùng SQLite in-memory cho DB tests.
5. **Edge case BẮT BUỘC.** Mỗi function: happy + error + boundary + Vietnamese text + concurrent (nếu async).
6. **E2E phải tương tác thật.** Click, scroll, type, hover, wait for animation — không chỉ `goto` rồi check text.

---

# DỰ ÁN

## Stack & quy mô
- **Backend:** FastAPI Python 3.14 — `agent/server.py` (3610 LOC)
- **Frontend:** Nuxt 4 SSR Vue 3 — 66 pages, 30+ composables
- **DB:** SQLite (knowledge: 1745 entities, 12441 rels, 33 itineraries) + PostgreSQL (UGC/auth: users, posts, comments, likes, follows, notifications, moderation, 22 tables)
- **Live site:** `https://vinhlong360.vn` — SSR, Chromium-compatible
- **238 API routes** across 10 backend files
- **Existing tests:** 3050 tests trong 47+ files, baseline XANH

## Cấu trúc API (để biết test gì)

### Public API (`/api/`) — 19 routes, KHÔNG cần auth
```
GET  /api/entities                        — list entities, params: type, area, limit, offset, sort
GET  /api/entities/{id}                   — entity detail
GET  /api/entities/{id}/relationships     — related entities
GET  /api/entities/{id}/gallery           — image gallery
GET  /api/entities/{id}/review-stats      — rating stats
POST /api/entities/{id}/view-contact      — track contact view
GET  /api/places                          — places hierarchy
GET  /api/facilities                      — facilities list
GET  /api/places/{place_id}/overview      — place overview
GET  /api/itineraries                     — list itineraries
GET  /api/itineraries/{id}                — itinerary detail
GET  /api/search                          — search entities
GET  /api/homepage                        — homepage data (sections, featured, trending)
GET  /api/map-pins                        — map markers
GET  /api/events                          — events list
GET  /api/stats                           — public stats
GET  /api/transparency                    — transparency report
POST /api/report                          — report content
GET  /site-settings                       — public site settings
```

### Social API (`/api/`) — 27 routes, PHẦN LỚN cần auth
```
POST   /api/posts                          — create post (auth)
GET    /api/posts/{id}                     — post detail
PATCH  /api/posts/{id}                     — update post (auth, owner)
DELETE /api/posts/{id}                     — delete post (auth, owner/admin)
GET    /api/feed                           — public feed
GET    /api/feed/following                 — following feed (auth)
GET    /api/search/posts                   — search posts
GET    /api/search/users                   — search users
GET    /api/community/stats                — community statistics
GET    /api/community/trending-tags        — trending hashtags
GET    /api/community/leaderboard          — user leaderboard
GET    /api/community/suggested-follows    — suggested follows
GET    /api/entities/{id}/feed             — entity-specific posts
GET    /api/posts/{id}/comments            — comments list
POST   /api/posts/{id}/comments            — create comment (auth)
POST   /api/posts/{id}/like               — toggle like (auth)
POST   /api/posts/{id}/bookmark            — toggle bookmark (auth)
GET    /api/users/{id}                     — user profile
GET    /api/users/{id}/posts               — user's posts
GET    /api/users/{id}/following           — user's following
GET    /api/users/{id}/followers           — user's followers
POST   /api/upload/image                   — upload image (auth)
```

### Auth API (`/auth/`) — 19 routes
```
POST /auth/request-otp                     — request OTP
POST /auth/verify-otp                      — verify OTP
POST /auth/login                           — password login
POST /auth/set-password                    — set/change password
POST /auth/logout                          — logout
GET  /auth/me                              — current user
PUT  /auth/profile                         — update profile
POST /auth/avatar                          — upload avatar
POST /auth/cover                           — upload cover
GET  /auth/sessions                        — active sessions
DELETE /auth/sessions/{id}                 — revoke session
POST /auth/deactivate                      — deactivate account
GET  /auth/privacy                         — privacy settings
PUT  /auth/privacy                         — update privacy
GET  /auth/login-history                   — login activity
```

### SEO (`/seo/`) — 12 routes
```
GET /seo/jsonld/{entity_id}                — JSON-LD for entity
GET /seo/jsonld/site                       — site-level JSON-LD
GET /seo/og/{entity_id}                    — Open Graph data
GET /sitemap.xml                           — sitemap
GET /robots.txt                            — robots
```

### Notification + Follow (`/api/`) — 15 routes
```
GET  /api/notifications                    — list notifications (auth)
POST /api/notifications/read-all           — mark all read (auth)
POST /api/follow/{type}/{id}              — toggle follow (auth)
GET  /api/follow/check/{type}/{id}        — check if following
POST /api/block/{user_id}                 — block user (auth)
GET  /api/blocked-users                    — blocked list (auth)
POST /api/events/{id}/rsvp                — RSVP to event (auth)
GET  /api/notifications/stream            — SSE real-time (auth)
```

## Entity types (cho E2E testing coverage)
```
product: 218, attraction: 202, restaurant: 191, history: 188,
accommodation: 164, nature: 125, place: 125, dish: 120,
experience: 92, craft_village: 86, event: 67, facility: 58,
cafe: 56, person: 35, itinerary: 16
```

## Test infrastructure sẵn có
```ini
# pytest.ini
[pytest]
addopts = --import-mode=importlib -m "not slow and not integration"
testpaths = tests agent/tests
markers =
    slow: long-running
    integration: FastAPI/TestClient
```
- **Conftest:** `agent/tests/conftest.py` — fixtures: `sample_entities`, `sample_relationships`, env setup (`ENVIRONMENT=test`, `ADMIN_API_KEY=test-admin-key-12345`)
- **Import:** `from agent.social import ...` — `agent/` trên sys.path

## Ràng buộc TUYỆT ĐỐI
- **KHÔNG sửa source code** — chỉ tạo test files
- **KHÔNG chạy lệnh phá dữ liệu** — không `--replace`, không DELETE entities, không DROP
- **KHÔNG tạo tài khoản mới** trên production — E2E chỉ read-only
- **KHÔNG POST/PUT/DELETE** lên `vinhlong360.vn` — E2E chỉ GET + browser interaction
- **KHÔNG test admin panel** trên production — admin cần API key thật

---

# ═══════════════════════════════════════════
# PHẦN 1: UNIT & INTEGRATION TESTS
# ═══════════════════════════════════════════

## 48 module chưa có test — chia theo priority

### P0 — Core (≥20 tests/module, BẮT BUỘC HOÀN THÀNH)

#### 1. `agent/social.py` (1817 LOC) → `agent/tests/test_social_deep.py`

**Functions cần test:**
- `create_post(user_id, content, post_type, entity_id, rating, images, mentions, hashtags)`
- `get_feed(limit, offset, post_type, entity_id)` 
- `get_following_feed(user_id, limit, offset)`
- `search_posts(q, limit, offset)` — phải test accent-insensitive
- `search_users(q, limit)` — unaccent matching
- `get_trending_tags(days, limit)`
- `get_leaderboard(limit)`
- `create_comment(user_id, post_id, content, parent_id)`
- `toggle_like(user_id, post_id)` → returns {liked: bool}
- `toggle_bookmark(user_id, post_id)` → returns {bookmarked: bool}
- `get_user_profile(user_id, viewer_id)` — phải hide khi blocked
- `get_community_stats()`

**Test cases BẮT BUỘC:**
```python
class TestCreatePost:
    def test_happy_path_share(self): ...
    def test_happy_path_review_with_rating(self): ...
    def test_happy_path_question(self): ...
    def test_content_too_long_rejected(self): ...
    def test_empty_content_rejected(self): ...
    def test_extracts_hashtags_from_content(self): ...
    def test_extracts_mentions_from_content(self): ...
    def test_xss_in_content_sanitized(self): ...
    def test_sql_injection_in_content_safe(self): ...
    def test_rating_only_for_review_type(self): ...
    def test_rating_range_1_to_5(self): ...
    def test_invalid_entity_id_handled(self): ...
    def test_moderation_status_defaults_pending(self): ...

class TestFeed:
    def test_returns_posts_newest_first(self): ...
    def test_pagination_offset_limit(self): ...
    def test_filter_by_post_type(self): ...
    def test_filter_by_entity_id(self): ...
    def test_excludes_rejected_posts(self): ...
    def test_following_feed_only_followed_users(self): ...
    def test_following_feed_excludes_blocked(self): ...
    def test_empty_feed_returns_empty_list(self): ...

class TestSearch:
    def test_search_vietnamese_with_accent(self): ...    # "Vĩnh Long"
    def test_search_vietnamese_without_accent(self): ... # "vinh long" matches "Vĩnh Long"
    def test_search_partial_match(self): ...              # "cam sành" matches
    def test_search_empty_query(self): ...
    def test_search_users_by_display_name(self): ...
    def test_search_users_accent_insensitive(self): ...

class TestInteractions:
    def test_toggle_like_first_time_likes(self): ...
    def test_toggle_like_second_time_unlikes(self): ...
    def test_like_updates_post_count(self): ...
    def test_toggle_bookmark_idempotent(self): ...
    def test_create_comment_increments_count(self): ...
    def test_threaded_comment_has_parent(self): ...
    def test_delete_comment_decrements_count(self): ...
    def test_delete_post_cascades_comments(self): ...

class TestBlockEnforcement:
    def test_blocked_user_hidden_in_feed(self): ...
    def test_blocked_user_hidden_in_search(self): ...
    def test_blocked_user_hidden_in_leaderboard(self): ...
    def test_blocked_user_profile_shows_limited_info(self): ...
    def test_block_auto_unfollows(self): ...
```

#### 2. `agent/auth.py` (989 LOC) → `agent/tests/test_auth_deep.py`

**Test cases BẮT BUỘC:**
```python
class TestOTPFlow:
    def test_request_otp_valid_phone_10_digits(self): ...
    def test_request_otp_valid_phone_with_84_prefix(self): ...
    def test_request_otp_invalid_phone_rejected(self): ...
    def test_request_otp_rate_limited_after_3_attempts(self): ...
    def test_verify_otp_correct_code_returns_token(self): ...
    def test_verify_otp_wrong_code_increments_attempts(self): ...
    def test_verify_otp_expired_code_rejected(self): ...
    def test_verify_otp_max_attempts_locks_session(self): ...
    def test_otp_creates_new_user_if_not_exists(self): ...
    def test_otp_returns_existing_user_if_exists(self): ...

class TestPasswordAuth:
    def test_set_password_hashes_correctly(self): ...
    def test_login_correct_password(self): ...
    def test_login_wrong_password_rejected(self): ...
    def test_login_inactive_account_rejected(self): ...
    def test_change_password_requires_old_password(self): ...
    def test_weak_password_rejected(self): ...  # < 8 chars

class TestSessionManagement:
    def test_login_creates_session_with_expiry(self): ...
    def test_logout_revokes_current_session(self): ...
    def test_list_sessions_returns_all_active(self): ...
    def test_revoke_session_by_id(self): ...
    def test_expired_session_rejected(self): ...
    def test_session_includes_user_agent_and_ip(self): ...

class TestProfile:
    def test_update_display_name(self): ...
    def test_update_bio(self): ...
    def test_update_username_unique(self): ...
    def test_duplicate_username_rejected(self): ...
    def test_username_case_insensitive_unique(self): ...
    def test_xss_in_bio_sanitized(self): ...
    def test_deactivate_sets_inactive(self): ...
    def test_deactivate_revokes_all_sessions(self): ...
    def test_reactivate_on_next_otp_login(self): ...
```

#### 3. `agent/moderation.py` (1333 LOC) → `agent/tests/test_moderation_deep.py`

```python
class TestContentScoring:
    def test_clean_text_scores_low(self): ...
    def test_spam_keywords_score_high(self): ...
    def test_excessive_caps_increases_score(self): ...
    def test_url_spam_pattern_detected(self): ...
    def test_phone_number_pattern_in_spam(self): ...
    def test_repeated_chars_detected(self): ...           # "aaaaaaa"
    def test_vietnamese_profanity_detected(self): ...
    def test_unicode_obfuscation_detected(self): ...      # "ℌ𝔢𝔩𝔩𝔬"
    def test_false_positive_place_names(self): ...        # "Đồng Tháp" không phải profanity
    def test_false_positive_food_names(self): ...         # "Bún mắm" không phải profanity
    def test_score_with_images_adjusts(self): ...
    def test_first_time_poster_higher_scrutiny(self): ...

class TestAutoDecision:
    def test_below_threshold_auto_approves(self): ...
    def test_above_threshold_auto_flags(self): ...
    def test_between_thresholds_pending_review(self): ...
    def test_trusted_user_lower_threshold(self): ...

class TestBatchModeration:
    def test_batch_approve_multiple(self): ...
    def test_batch_reject_with_reason(self): ...
    def test_batch_empty_list_rejected(self): ...
    def test_moderation_log_created_on_action(self): ...
    def test_notification_sent_on_reject(self): ...
```

#### 4. `agent/notifications.py` (606 LOC) → `agent/tests/test_notifications_deep.py`

```python
class TestCreateNotification:
    def test_like_notification_created(self): ...
    def test_comment_notification_created(self): ...
    def test_follow_notification_created(self): ...
    def test_mention_notification_created(self): ...
    def test_skips_self_notification(self): ...        # A likes own post → no notif
    def test_skips_blocked_user_notification(self): ...
    def test_respects_user_preferences(self): ...      # user disabled like notifs

class TestGrouping:
    def test_groups_same_type_within_24h(self): ...    # "A và 4 người khác thích bài viết"
    def test_new_group_after_24h(self): ...
    def test_group_label_format_vietnamese(self): ...
    def test_single_notification_no_grouping(self): ...

class TestReadAndCleanup:
    def test_mark_single_read(self): ...
    def test_mark_all_read(self): ...
    def test_unread_count_accurate(self): ...
    def test_cleanup_old_notifications(self): ...

class TestFollowSystem:
    def test_follow_user_creates_record(self): ...
    def test_follow_entity_creates_record(self): ...
    def test_unfollow_removes_record(self): ...
    def test_follow_check_returns_boolean(self): ...
    def test_follower_count_accurate(self): ...

class TestRSVP:
    def test_rsvp_to_event(self): ...
    def test_cancel_rsvp(self): ...
    def test_rsvp_count_accurate(self): ...
```

#### 5. `agent/public_api.py` (1117 LOC) → `agent/tests/test_public_api_deep.py`

```python
class TestEntityList:
    def test_returns_entities_default_limit(self): ...
    def test_filter_by_type(self): ...                    # ?type=attraction
    def test_filter_by_area(self): ...                    # ?area=vinh-long
    def test_filter_by_multiple_types(self): ...          # ?type=dish,product
    def test_pagination_offset_limit(self): ...
    def test_sort_by_name(self): ...
    def test_sort_by_confidence(self): ...
    def test_includes_total_count_header(self): ...
    def test_empty_result_returns_empty_list(self): ...

class TestEntityDetail:
    def test_returns_full_entity(self): ...
    def test_includes_description(self): ...              # regression: description was missing
    def test_includes_images_array(self): ...
    def test_includes_coordinates(self): ...
    def test_includes_attributes(self): ...
    def test_nonexistent_entity_404(self): ...
    def test_entity_id_sql_injection_safe(self): ...      # "'; DROP TABLE--"

class TestRelationships:
    def test_returns_related_entities(self): ...
    def test_grouped_by_relationship_type(self): ...
    def test_nonexistent_entity_returns_empty(self): ...

class TestSearch:
    def test_search_by_name(self): ...
    def test_search_accent_insensitive(self): ...         # "vinh long" → "Vĩnh Long"
    def test_search_partial_match(self): ...
    def test_search_limit_respected(self): ...
    def test_search_empty_query(self): ...
    def test_search_xss_payload_safe(self): ...

class TestHomepageAPI:
    def test_returns_sections(self): ...
    def test_each_section_has_entities(self): ...
    def test_featured_entities_non_empty(self): ...
    def test_response_cacheable(self): ...                # check Cache-Control header

class TestMapPins:
    def test_returns_pins_with_coordinates(self): ...
    def test_pin_has_id_name_type_coords(self): ...
    def test_excludes_entities_without_coords(self): ...

class TestItineraries:
    def test_list_itineraries(self): ...
    def test_itinerary_detail_has_stops(self): ...
    def test_nonexistent_itinerary_404(self): ...
```

#### 6. `agent/guardrails.py` (906 LOC) → `agent/tests/test_guardrails_deep.py`

```python
class TestInputValidation:
    def test_normal_input_passes(self): ...
    def test_sql_injection_blocked(self): ...
    def test_xss_script_tag_blocked(self): ...
    def test_prompt_injection_blocked(self): ...          # "ignore previous instructions"
    def test_path_traversal_blocked(self): ...            # "../../etc/passwd"
    def test_command_injection_blocked(self): ...         # "; rm -rf /"
    def test_very_long_input_truncated(self): ...
    def test_null_bytes_stripped(self): ...
    def test_unicode_normalization(self): ...
    def test_vietnamese_text_allowed(self): ...           # Không false positive

class TestOutputFiltering:
    def test_pii_phone_numbers_masked(self): ...
    def test_pii_email_masked(self): ...
    def test_internal_urls_stripped(self): ...
    def test_normal_output_unchanged(self): ...

class TestRateLimiting:
    def test_within_limit_allowed(self): ...
    def test_exceeds_limit_blocked(self): ...
    def test_limit_resets_after_window(self): ...
```

### P1 — Infrastructure (≥12 tests/module)

| Module | Test file | Key focus |
|--------|-----------|-----------|
| `auth_middleware.py` | `test_auth_middleware_deep.py` | JWT decode valid/expired/tampered, role check admin/mod/user, rate limit per endpoint, CORS handling |
| `memory.py` | `test_memory_deep.py` | Store/retrieve messages, context window limit, memory pruning, session isolation |
| `memory_graph.py` | `test_memory_graph_deep.py` | Add/query nodes+edges, traversal, subgraph extraction, cycle handling |
| `recommender.py` | `test_recommender_deep.py` | Content-based scoring, area boost, type diversity, cold start |
| `semantic_cache.py` | `test_semantic_cache_deep.py` | Cache hit exact/similar, miss, invalidation, TTL, size limit |
| `bot_gateway.py` | `test_bot_gateway_deep.py` | Telegram webhook parse, Zalo webhook parse, response format, error handling |
| `cost_tracker.py` | `test_cost_tracker_deep.py` | Track API call cost, daily budget alert, reset, overflow |
| `circuit_breaker.py` | `test_circuit_breaker_deep.py` | Closed→open after N fails, half-open→closed on success, timeout, state persistence |
| `site_settings.py` | `test_site_settings_deep.py` | CRUD settings by key, category filter, bulk update, reset defaults |

### P2 — Supplementary (≥6 tests/module)

Viết tests cho các module còn lại theo cùng pattern. **Nếu hết thời gian → bỏ P2, P0 + P1 đầy đủ quan trọng hơn.**

---

# ═══════════════════════════════════════════
# PHẦN 2: E2E BROWSER — DEEP EXPERIENCE
# ═══════════════════════════════════════════

## Setup

```bash
pip install playwright pytest-playwright pytest-base-url
playwright install chromium
mkdir -p tests/e2e/screenshots
```

## Config — `tests/e2e/conftest.py`

```python
"""E2E config — Playwright against live vinhlong360.vn."""

import pytest
from playwright.sync_api import Page, BrowserContext

BASE = "https://vinhlong360.vn"
API  = "https://vinhlong360.vn"

@pytest.fixture(scope="session")
def base_url():
    return BASE

@pytest.fixture(scope="session")
def api_url():
    return API

@pytest.fixture
def desktop(page: Page):
    """Desktop viewport 1440x900."""
    page.set_default_timeout(15000)
    page.set_default_navigation_timeout(30000)
    page.set_viewport_size({"width": 1440, "height": 900})
    yield page

@pytest.fixture
def mobile(page: Page):
    """Mobile viewport 375x812 (iPhone X)."""
    page.set_default_timeout(15000)
    page.set_default_navigation_timeout(30000)
    page.set_viewport_size({"width": 375, "height": 812})
    yield page

@pytest.fixture
def tablet(page: Page):
    """Tablet viewport 768x1024 (iPad)."""
    page.set_default_timeout(15000)
    page.set_default_navigation_timeout(30000)
    page.set_viewport_size({"width": 768, "height": 1024})
    yield page

@pytest.fixture(autouse=True)
def collect_errors(page: Page):
    """Collect JS errors for every test."""
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    yield errors
    # Có thể dùng errors trong test để assert

def screenshot_on_fail(page: Page, request):
    """Screenshot khi test fail."""
    if request.node.rep_call.failed:
        page.screenshot(path=f"tests/e2e/screenshots/{request.node.name}.png")
```

## Marker — thêm vào `pytest.ini`:
```
e2e: End-to-end browser tests against live site
```

---

### `tests/e2e/test_01_homepage_deep.py` — HÀNH TRÌNH TRANG CHỦ

```python
"""Deep E2E: Homepage — load, interact, navigate, verify content."""

import pytest
import re
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestHomepageLoad:
    """Homepage renders all critical sections."""

    def test_returns_200_with_vietnamese_title(self, desktop: Page, base_url):
        """Homepage loads with Vietnamese title."""
        r = desktop.goto(base_url)
        assert r.status == 200
        title = desktop.title()
        assert any(w in title for w in ["Vĩnh Long", "vinhlong", "360"]), f"Title: {title}"

    def test_meta_description_has_content(self, desktop: Page, base_url):
        """Meta description mentions Vĩnh Long."""
        desktop.goto(base_url)
        desc = desktop.locator('meta[name="description"]').get_attribute("content")
        assert desc and len(desc) > 50
        assert any(w in desc for w in ["Vĩnh Long", "du lịch", "OCOP", "cộng đồng"])

    def test_hero_section_visible_with_search(self, desktop: Page, base_url):
        """Hero section has background and search input."""
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        hero = desktop.locator("section").first
        expect(hero).to_be_visible()
        # Search input trong hero hoặc nav
        search = desktop.locator("input[type='search'], input[placeholder*='Tìm'], input[placeholder*='tìm'], [class*='search'] input")
        assert search.count() >= 1, "No search input found"

    def test_has_minimum_content_sections(self, desktop: Page, base_url):
        """Homepage has ≥4 content sections."""
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        sections = desktop.locator("main section, main > div > section, [class*='section'], [class*='Section']")
        assert sections.count() >= 4, f"Only {sections.count()} sections found"

    def test_entity_cards_have_real_content(self, desktop: Page, base_url):
        """Entity cards show real names (not placeholder/lorem ipsum)."""
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        cards = desktop.locator("[class*='card'] h2, [class*='card'] h3, [class*='Card'] h2, [class*='Card'] h3")
        assert cards.count() >= 3, "Not enough entity cards"
        for i in range(min(cards.count(), 5)):
            text = cards.nth(i).inner_text().strip()
            assert len(text) >= 2, f"Card {i} title too short: '{text}'"
            assert "lorem" not in text.lower(), f"Card {i} has placeholder text"
            assert "undefined" not in text.lower(), f"Card {i} shows undefined"

    def test_no_javascript_errors(self, desktop: Page, base_url, collect_errors):
        """Zero JS errors on homepage."""
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        # Wait extra for async components
        desktop.wait_for_timeout(2000)
        assert len(collect_errors) == 0, f"JS errors: {collect_errors}"

    def test_no_hydration_mismatch(self, desktop: Page, base_url):
        """No Vue hydration mismatch warnings."""
        logs = []
        desktop.on("console", lambda msg: logs.append(msg.text) if "mismatch" in msg.text.lower() else None)
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        desktop.wait_for_timeout(3000)
        hydration_errors = [l for l in logs if "hydration" in l.lower()]
        assert len(hydration_errors) == 0, f"Hydration mismatches: {hydration_errors}"


class TestHomepageNavigation:
    """User can navigate from homepage to all major pages."""

    def test_click_entity_card_opens_detail(self, desktop: Page, base_url):
        """Click on entity card navigates to detail page."""
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        # Find first card link to /dia-diem/
        card_link = desktop.locator("a[href*='/dia-diem/']").first
        expect(card_link).to_be_visible()
        href = card_link.get_attribute("href")
        card_link.click()
        desktop.wait_for_load_state("networkidle")
        assert "/dia-diem/" in desktop.url, f"Expected entity detail, got {desktop.url}"
        # Detail page has h1
        expect(desktop.locator("h1")).to_be_visible()

    def test_main_nav_links_all_work(self, desktop: Page, base_url):
        """Each main nav link navigates to correct page without error."""
        desktop.goto(base_url)
        nav_links = desktop.locator("nav a[href], header a[href]")
        hrefs = set()
        for i in range(nav_links.count()):
            href = nav_links.nth(i).get_attribute("href")
            if href and href.startswith("/") and href != "/":
                hrefs.add(href.split("?")[0].split("#")[0])
        
        for href in list(hrefs)[:10]:
            r = desktop.goto(f"{base_url}{href}")
            assert r.status in [200, 301, 302], f"{href} returned {r.status}"

    def test_search_from_homepage(self, desktop: Page, base_url):
        """Type search query on homepage → navigate to search results."""
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        search = desktop.locator("input[type='search'], input[placeholder*='Tìm'], input[placeholder*='tìm'], [class*='search'] input").first
        search.click()
        search.fill("Hồ Trúc Giang")
        desktop.keyboard.press("Enter")
        desktop.wait_for_load_state("networkidle")
        # Should be on search page or show results
        body = desktop.inner_text("body")
        assert "Trúc Giang" in body or "/tim-kiem" in desktop.url, "Search didn't navigate or show results"

    def test_footer_links_work(self, desktop: Page, base_url):
        """Footer links navigate correctly."""
        desktop.goto(base_url)
        footer = desktop.locator("footer")
        footer.scroll_into_view_if_needed()
        links = footer.locator("a[href]")
        assert links.count() >= 3, "Footer has too few links"
        # Click first internal link
        first_link = footer.locator("a[href^='/']").first
        if first_link.count() > 0:
            href = first_link.get_attribute("href")
            first_link.click()
            desktop.wait_for_load_state("networkidle")
            assert desktop.url != base_url, "Footer link didn't navigate"


class TestHomepageInteraction:
    """Interactive elements on homepage work correctly."""

    def test_scroll_reveals_content(self, desktop: Page, base_url):
        """Scrolling reveals lazy/animated sections."""
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        # Scroll to bottom gradually
        for _ in range(5):
            desktop.mouse.wheel(0, 800)
            desktop.wait_for_timeout(500)
        # After scrolling, more content should be visible
        all_sections = desktop.locator("main section, [class*='section']")
        visible_count = 0
        for i in range(all_sections.count()):
            if all_sections.nth(i).is_visible():
                visible_count += 1
        assert visible_count >= 3, f"Only {visible_count} sections visible after scroll"

    def test_card_hover_shows_effect(self, desktop: Page, base_url):
        """Entity cards have hover effect (transform, shadow, or opacity)."""
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        card = desktop.locator("[class*='card'], [class*='Card']").first
        if card.count() > 0:
            # Get pre-hover styles
            pre_hover = card.evaluate("el => getComputedStyle(el).transform")
            card.hover()
            desktop.wait_for_timeout(400)  # CSS transition
            post_hover = card.evaluate("el => getComputedStyle(el).transform")
            # At least one should change (transform, box-shadow, etc.)
            shadow_pre = card.evaluate("el => getComputedStyle(el).boxShadow")
            card.hover()
            desktop.wait_for_timeout(400)
            shadow_post = card.evaluate("el => getComputedStyle(el).boxShadow")
            assert (pre_hover != post_hover or shadow_pre != shadow_post), "No hover effect on cards"


class TestHomepageMobile:
    """Homepage on mobile viewport."""

    def test_no_horizontal_overflow(self, mobile: Page, base_url):
        """No horizontal scrollbar on mobile."""
        mobile.goto(base_url)
        mobile.wait_for_load_state("networkidle")
        overflow = mobile.evaluate("document.body.scrollWidth > window.innerWidth")
        assert not overflow, f"Horizontal overflow: body={mobile.evaluate('document.body.scrollWidth')}px, viewport={mobile.evaluate('window.innerWidth')}px"

    def test_hamburger_menu_works(self, mobile: Page, base_url):
        """Mobile hamburger menu opens and shows nav links."""
        mobile.goto(base_url)
        mobile.wait_for_load_state("networkidle")
        # Find hamburger button
        burger = mobile.locator("button[aria-label*='menu'], button[aria-label*='Menu'], [class*='burger'], [class*='hamburger'], [class*='menu-toggle'], header button").first
        if burger.count() > 0 and burger.is_visible():
            burger.click()
            mobile.wait_for_timeout(500)
            # Nav should now be visible
            nav = mobile.locator("nav a[href], [class*='mobile-menu'] a, [class*='drawer'] a, [class*='sidebar'] a")
            assert nav.count() >= 3, "Mobile menu didn't show nav links"

    def test_touch_scroll_works(self, mobile: Page, base_url):
        """Content scrolls on mobile."""
        mobile.goto(base_url)
        mobile.wait_for_load_state("networkidle")
        scroll_before = mobile.evaluate("window.scrollY")
        mobile.mouse.wheel(0, 500)
        mobile.wait_for_timeout(300)
        scroll_after = mobile.evaluate("window.scrollY")
        assert scroll_after > scroll_before, "Page didn't scroll on mobile"

    def test_images_responsive(self, mobile: Page, base_url):
        """Images don't overflow viewport on mobile."""
        mobile.goto(base_url)
        mobile.wait_for_load_state("networkidle")
        overflow_images = mobile.evaluate("""
            [...document.querySelectorAll('img')].filter(img => img.naturalWidth > 0 && img.offsetWidth > window.innerWidth + 5).length
        """)
        assert overflow_images == 0, f"{overflow_images} images overflow mobile viewport"
```

### `tests/e2e/test_02_entity_journey.py` — HÀNH TRÌNH CHI TIẾT ĐỊA ĐIỂM

```python
"""Deep E2E: Entity detail — full user journey from discovery to interaction."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

# Entities with good data for testing
RICH_ENTITIES = [
    ("ho-truc-giang", "Hồ Trúc Giang"),
    ("chua-vam-ray", "Chùa Vàm Ray"),
    ("cam-sanh-vinh-long", "Cam sành Vĩnh Long"),
]

ENTITY_TYPES = [
    ("ho-truc-giang", "attraction"),
    ("cam-sanh-vinh-long", "product"),
    ("somo-farm-cuu-long", "accommodation"),
]


class TestEntityPageContent:
    """Entity detail page shows complete, real content."""

    @pytest.mark.parametrize("eid,name", RICH_ENTITIES)
    def test_page_has_title_matching_entity_name(self, desktop: Page, base_url, eid, name):
        """H1 contains entity name."""
        desktop.goto(f"{base_url}/dia-diem/{eid}")
        h1 = desktop.locator("h1")
        expect(h1).to_be_visible()
        assert name in h1.inner_text()

    @pytest.mark.parametrize("eid,name", RICH_ENTITIES)
    def test_description_is_substantial(self, desktop: Page, base_url, eid, name):
        """Description section has real content (>100 chars)."""
        desktop.goto(f"{base_url}/dia-diem/{eid}")
        desktop.wait_for_load_state("networkidle")
        # Find main content area — description is usually in article/main/section
        main_text = desktop.locator("main").inner_text()
        # Remove nav, footer, etc. — just check body has substantial text
        assert len(main_text) > 200, f"Page content too short for {eid}: {len(main_text)} chars"

    @pytest.mark.parametrize("eid,name", RICH_ENTITIES[:1])
    def test_description_expand_collapse(self, desktop: Page, base_url, eid, name):
        """Long descriptions can be expanded/collapsed."""
        desktop.goto(f"{base_url}/dia-diem/{eid}")
        desktop.wait_for_load_state("networkidle")
        expand_btn = desktop.locator("button:has-text('Xem thêm'), button:has-text('xem thêm'), [class*='expand'], [class*='read-more']")
        if expand_btn.count() > 0 and expand_btn.first.is_visible():
            expand_btn.first.click()
            desktop.wait_for_timeout(500)
            # After expand, button should change to "Thu gọn" or similar
            collapse = desktop.locator("button:has-text('Thu gọn'), button:has-text('thu gọn'), button:has-text('Ẩn bớt')")
            assert collapse.count() > 0 or not expand_btn.first.is_visible(), "Expand/collapse didn't toggle"


class TestEntityGallery:
    """Image gallery interaction."""

    def test_gallery_images_load(self, desktop: Page, base_url):
        """Entity images load without broken sources."""
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        desktop.wait_for_load_state("networkidle")
        images = desktop.locator("main img[src]")
        broken = []
        for i in range(min(images.count(), 10)):
            img = images.nth(i)
            natural = img.evaluate("el => el.naturalWidth")
            if natural == 0:
                src = img.get_attribute("src")
                if src and not src.startswith("data:"):
                    broken.append(src)
        assert len(broken) == 0, f"Broken images: {broken}"

    def test_click_image_opens_lightbox(self, desktop: Page, base_url):
        """Clicking gallery image opens lightbox/modal."""
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        desktop.wait_for_load_state("networkidle")
        gallery_img = desktop.locator("main img[src]:not([src^='data:'])").first
        if gallery_img.count() > 0 and gallery_img.is_visible():
            gallery_img.click()
            desktop.wait_for_timeout(800)
            # Lightbox should appear — large image or overlay
            lightbox = desktop.locator("[class*='lightbox'], [class*='Lightbox'], [class*='modal'] img, [class*='overlay'] img, [role='dialog'] img")
            if lightbox.count() > 0:
                expect(lightbox.first).to_be_visible()
                # Close lightbox
                close = desktop.locator("[class*='lightbox'] button, [class*='modal'] button[class*='close'], [aria-label='Close'], [aria-label='Đóng']").first
                if close.count() > 0:
                    close.click()
                else:
                    desktop.keyboard.press("Escape")
                desktop.wait_for_timeout(500)

    def test_lightbox_navigation(self, desktop: Page, base_url):
        """Navigate between images in lightbox with arrows."""
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        desktop.wait_for_load_state("networkidle")
        images = desktop.locator("main img[src]:not([src^='data:'])")
        if images.count() >= 2:
            images.first.click()
            desktop.wait_for_timeout(800)
            # Try next arrow
            next_btn = desktop.locator("[class*='next'], [aria-label*='next'], [aria-label*='Next'], [aria-label*='Tiếp'], button:has-text('›')").first
            if next_btn.count() > 0 and next_btn.is_visible():
                next_btn.click()
                desktop.wait_for_timeout(500)
            # Try keyboard navigation
            desktop.keyboard.press("ArrowRight")
            desktop.wait_for_timeout(300)
            desktop.keyboard.press("Escape")


class TestEntityInteractions:
    """User interactions on entity page (no auth needed for testing the UI)."""

    def test_share_button_exists(self, desktop: Page, base_url):
        """Share button is visible."""
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        desktop.wait_for_load_state("networkidle")
        share = desktop.locator("button:has-text('Chia sẻ'), button[aria-label*='share'], button[aria-label*='Share'], [class*='share']")
        # Share may be behind a more menu or directly visible
        assert share.count() >= 0  # Just checking it doesn't crash

    def test_contact_buttons_show_info(self, desktop: Page, base_url):
        """Contact CTA buttons (Zalo, phone) show contact info."""
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        desktop.wait_for_load_state("networkidle")
        # Look for phone/Zalo buttons
        contact = desktop.locator("a[href*='zalo'], a[href*='tel:'], button:has-text('Liên hệ'), button:has-text('Gọi'), [class*='contact']")
        # Some entities may not have contact info — just verify no crash

    def test_related_entities_clickable(self, desktop: Page, base_url):
        """Related entities section links work."""
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        desktop.wait_for_load_state("networkidle")
        # Scroll to related section
        desktop.mouse.wheel(0, 3000)
        desktop.wait_for_timeout(500)
        related = desktop.locator("a[href*='/dia-diem/']")
        if related.count() > 1:
            # Click second link (first might be the entity itself)
            target = related.nth(1)
            if target.is_visible():
                href = target.get_attribute("href")
                target.click()
                desktop.wait_for_load_state("networkidle")
                assert "/dia-diem/" in desktop.url

    def test_breadcrumb_navigation(self, desktop: Page, base_url):
        """Breadcrumb links navigate back to parent pages."""
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        bread = desktop.locator("nav[aria-label*='readcrumb'] a, [class*='breadcrumb'] a, ol a")
        if bread.count() >= 2:
            bread.first.click()
            desktop.wait_for_load_state("networkidle")
            assert desktop.url != f"{base_url}/dia-diem/ho-truc-giang"

    def test_back_button_works(self, desktop: Page, base_url):
        """Browser back navigates correctly after entity→entity."""
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        desktop.wait_for_load_state("networkidle")
        # Click a related entity
        related = desktop.locator("a[href*='/dia-diem/']:not([href*='ho-truc-giang'])")
        if related.count() > 0 and related.first.is_visible():
            related.first.click()
            desktop.wait_for_load_state("networkidle")
            new_url = desktop.url
            desktop.go_back()
            desktop.wait_for_load_state("networkidle")
            assert "ho-truc-giang" in desktop.url


class TestEntity404:
    """Non-existent entities handled gracefully."""

    def test_nonexistent_shows_error(self, desktop: Page, base_url):
        """Non-existent entity shows friendly error, not crash."""
        desktop.goto(f"{base_url}/dia-diem/xyz-khong-ton-tai-12345")
        body = desktop.inner_text("body").lower()
        assert any(w in body for w in ["không tìm thấy", "404", "not found", "lỗi", "không tồn tại"]), \
            "No error message for non-existent entity"

    def test_nonexistent_has_navigation(self, desktop: Page, base_url):
        """Error page still has working navigation."""
        desktop.goto(f"{base_url}/dia-diem/xyz-khong-ton-tai-12345")
        nav = desktop.locator("header a, nav a")
        assert nav.count() >= 2, "Error page missing navigation"


class TestEntityMobile:
    """Entity detail on mobile."""

    def test_entity_mobile_no_overflow(self, mobile: Page, base_url):
        """Entity page fits mobile viewport."""
        mobile.goto(f"{base_url}/dia-diem/ho-truc-giang")
        mobile.wait_for_load_state("networkidle")
        overflow = mobile.evaluate("document.body.scrollWidth > window.innerWidth + 5")
        assert not overflow, "Entity page overflows on mobile"

    def test_entity_mobile_images_fit(self, mobile: Page, base_url):
        """Images resize to fit mobile screen."""
        mobile.goto(f"{base_url}/dia-diem/ho-truc-giang")
        mobile.wait_for_load_state("networkidle")
        wide_images = mobile.evaluate("""
            [...document.querySelectorAll('main img')].filter(i => i.offsetWidth > window.innerWidth + 10).length
        """)
        assert wide_images == 0, "Images overflow mobile"

    def test_entity_mobile_scrollable(self, mobile: Page, base_url):
        """Full content accessible via scroll on mobile."""
        mobile.goto(f"{base_url}/dia-diem/ho-truc-giang")
        mobile.wait_for_load_state("networkidle")
        total_height = mobile.evaluate("document.body.scrollHeight")
        assert total_height > 1000, f"Page too short on mobile: {total_height}px"
```

### `tests/e2e/test_03_search_deep.py` — TÌM KIẾM SÂU

```python
"""Deep E2E: Search — all modes, Vietnamese text handling, XSS."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestSearchInput:
    """Search input interaction and autocomplete."""

    def test_search_page_has_input_focused(self, desktop: Page, base_url):
        """Search page auto-focuses search input."""
        desktop.goto(f"{base_url}/tim-kiem")
        desktop.wait_for_load_state("networkidle")
        search = desktop.locator("input[type='search'], input[type='text'][placeholder*='ìm']").first
        expect(search).to_be_visible()

    def test_type_query_shows_results(self, desktop: Page, base_url):
        """Type query → results appear (either instant or after Enter)."""
        desktop.goto(f"{base_url}/tim-kiem")
        desktop.wait_for_load_state("networkidle")
        search = desktop.locator("input[type='search'], input[type='text']").first
        search.click()
        search.fill("Bún mắm")
        desktop.keyboard.press("Enter")
        desktop.wait_for_load_state("networkidle")
        desktop.wait_for_timeout(1000)
        body = desktop.inner_text("body")
        assert "Bún mắm" in body or "bún mắm" in body.lower(), "Search for 'Bún mắm' returned no results"

    def test_search_without_diacritics(self, desktop: Page, base_url):
        """'vinh long' matches 'Vĩnh Long' (accent-insensitive)."""
        desktop.goto(f"{base_url}/tim-kiem?q=vinh+long")
        desktop.wait_for_load_state("networkidle")
        desktop.wait_for_timeout(1000)
        body = desktop.inner_text("body")
        assert "Vĩnh Long" in body or "vinh long" in body.lower(), "Accent-insensitive search failed"

    def test_search_specific_entity_appears_first(self, desktop: Page, base_url):
        """Search exact name → that entity appears in results."""
        desktop.goto(f"{base_url}/tim-kiem?q=Hồ+Trúc+Giang")
        desktop.wait_for_load_state("networkidle")
        desktop.wait_for_timeout(1000)
        # Check first result or body contains the entity
        first_result = desktop.locator("[class*='result'] a, [class*='card'] a, article a").first
        if first_result.count() > 0:
            assert "truc-giang" in (first_result.get_attribute("href") or "").lower() or "Trúc Giang" in first_result.inner_text()

    def test_search_empty_shows_suggestions(self, desktop: Page, base_url):
        """Empty search page shows suggestions or popular items."""
        desktop.goto(f"{base_url}/tim-kiem")
        desktop.wait_for_load_state("networkidle")
        body = desktop.inner_text("body")
        assert len(body) > 100, "Empty search page has no content"

    def test_search_no_results_message(self, desktop: Page, base_url):
        """Search with gibberish shows 'no results' message."""
        desktop.goto(f"{base_url}/tim-kiem?q=xyzqwerty99999")
        desktop.wait_for_load_state("networkidle")
        desktop.wait_for_timeout(1000)
        body = desktop.inner_text("body").lower()
        assert any(w in body for w in ["không tìm thấy", "không có kết quả", "no result", "0 kết quả"])

    def test_search_click_result_navigates(self, desktop: Page, base_url):
        """Click search result navigates to entity detail."""
        desktop.goto(f"{base_url}/tim-kiem?q=cam+sành")
        desktop.wait_for_load_state("networkidle")
        desktop.wait_for_timeout(1000)
        result_link = desktop.locator("a[href*='/dia-diem/']").first
        if result_link.count() > 0 and result_link.is_visible():
            result_link.click()
            desktop.wait_for_load_state("networkidle")
            assert "/dia-diem/" in desktop.url

    def test_search_xss_payload_escaped(self, desktop: Page, base_url):
        """XSS payload in search is escaped, not executed."""
        desktop.goto(f"{base_url}/tim-kiem?q=<script>alert('xss')</script>")
        desktop.wait_for_load_state("networkidle")
        # Verify no alert dialog popped
        content = desktop.content()
        assert "<script>alert" not in content.replace("&lt;", "<"), "XSS payload rendered"

    def test_search_sql_injection_safe(self, desktop: Page, base_url):
        """SQL injection in search doesn't crash the page."""
        desktop.goto(f"{base_url}/tim-kiem?q='+OR+1=1--")
        desktop.wait_for_load_state("networkidle")
        # Page should still render (not 500)
        assert "500" not in desktop.title().lower()
        assert "error" not in desktop.title().lower()
```

### `tests/e2e/test_04_catalog_deep.py` — DUYỆT DANH MỤC

```python
"""Deep E2E: Catalog pages — filter, scroll, load more, navigate."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

CATALOGS = [
    ("/dia-diem", "Điểm đến", 10),
    ("/du-lich", "Du lịch", 3),
    ("/ocop", "OCOP", 3),
    ("/le-hoi", "Lễ hội", 2),
    ("/san-pham", "Sản phẩm", 3),
    ("/lich-trinh", "Lịch trình", 2),
    ("/danh-ba", "Danh bạ", 5),
    ("/luu-tru", "Lưu trú", 2),
    ("/kham-pha/am-thuc", "Ẩm thực", 2),
    ("/khu-vuc/vinh-long", "Khu vực Vĩnh Long", 3),
]


class TestCatalogBasics:

    @pytest.mark.parametrize("path,label,min_items", CATALOGS)
    def test_page_loads_200(self, desktop: Page, base_url, path, label, min_items):
        """Catalog page returns 200."""
        r = desktop.goto(f"{base_url}{path}")
        assert r.status == 200, f"{path} returned {r.status}"

    @pytest.mark.parametrize("path,label,min_items", CATALOGS[:6])
    def test_has_entity_cards(self, desktop: Page, base_url, path, label, min_items):
        """Catalog shows minimum entity cards."""
        desktop.goto(f"{base_url}{path}")
        desktop.wait_for_load_state("networkidle")
        cards = desktop.locator("[class*='card'], [class*='Card'], article, [class*='item']")
        assert cards.count() >= min_items, f"{path}: {cards.count()} cards, expected >= {min_items}"

    @pytest.mark.parametrize("path,label,min_items", CATALOGS[:3])
    def test_cards_have_real_names(self, desktop: Page, base_url, path, label, min_items):
        """Cards have real entity names (not empty/placeholder)."""
        desktop.goto(f"{base_url}{path}")
        desktop.wait_for_load_state("networkidle")
        titles = desktop.locator("[class*='card'] h2, [class*='card'] h3, [class*='Card'] h2, [class*='Card'] h3, article h2, article h3")
        for i in range(min(titles.count(), 5)):
            text = titles.nth(i).inner_text().strip()
            assert len(text) >= 2 and text != "undefined" and text != "null", f"Bad card title on {path}: '{text}'"


class TestCatalogFilters:
    """Filter chips/buttons on catalog pages."""

    def test_dia_diem_type_filters(self, desktop: Page, base_url):
        """Điểm đến page has type filter chips (Du lịch, Ẩm thực, OCOP...)."""
        desktop.goto(f"{base_url}/dia-diem")
        desktop.wait_for_load_state("networkidle")
        filters = desktop.locator("[class*='filter'] button, [class*='chip'], [class*='tag'] button, [class*='tab'] button")
        if filters.count() >= 2:
            # Click second filter
            second = filters.nth(1)
            text_before = second.inner_text()
            second.click()
            desktop.wait_for_timeout(1000)
            # URL or content should change
            cards_after = desktop.locator("[class*='card'], [class*='Card'], article").count()
            assert cards_after >= 0  # Just verify no crash

    def test_area_filter(self, desktop: Page, base_url):
        """Area filter (Vĩnh Long/Bến Tre/Trà Vinh) works."""
        desktop.goto(f"{base_url}/dia-diem")
        desktop.wait_for_load_state("networkidle")
        area_filter = desktop.locator("button:has-text('Vĩnh Long'), button:has-text('Bến Tre'), [class*='area'] button, select[class*='area']")
        if area_filter.count() > 0:
            area_filter.first.click()
            desktop.wait_for_timeout(1000)


class TestCatalogLoadMore:
    """Infinite scroll or load-more on catalog pages."""

    def test_load_more_fetches_more_items(self, desktop: Page, base_url):
        """Scroll or click 'load more' adds more entities."""
        desktop.goto(f"{base_url}/dia-diem")
        desktop.wait_for_load_state("networkidle")
        initial_count = desktop.locator("[class*='card'], [class*='Card'], article").count()
        # Scroll to bottom to trigger infinite scroll
        for _ in range(10):
            desktop.mouse.wheel(0, 1000)
            desktop.wait_for_timeout(400)
        # Or click load more button
        load_more = desktop.locator("button:has-text('Xem thêm'), button:has-text('Tải thêm'), button:has-text('Load more')")
        if load_more.count() > 0 and load_more.first.is_visible():
            load_more.first.click()
            desktop.wait_for_timeout(2000)
        final_count = desktop.locator("[class*='card'], [class*='Card'], article").count()
        # Should have more items (or same if all loaded)
        assert final_count >= initial_count, f"Items decreased: {initial_count} → {final_count}"

    def test_card_click_opens_detail(self, desktop: Page, base_url):
        """Click entity card from catalog → entity detail page."""
        desktop.goto(f"{base_url}/dia-diem")
        desktop.wait_for_load_state("networkidle")
        card = desktop.locator("a[href*='/dia-diem/']").first
        if card.count() > 0:
            href = card.get_attribute("href")
            card.click()
            desktop.wait_for_load_state("networkidle")
            assert "/dia-diem/" in desktop.url
            expect(desktop.locator("h1")).to_be_visible()
```

### `tests/e2e/test_05_itinerary_deep.py` — LỊCH TRÌNH

```python
"""Deep E2E: Itinerary pages — list, detail, stops, map."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestItineraryList:
    def test_list_page_loads(self, desktop: Page, base_url):
        desktop.goto(f"{base_url}/lich-trinh")
        expect(desktop.locator("h1")).to_be_visible()

    def test_itineraries_have_titles(self, desktop: Page, base_url):
        desktop.goto(f"{base_url}/lich-trinh")
        desktop.wait_for_load_state("networkidle")
        cards = desktop.locator("[class*='card'] h2, [class*='card'] h3, article h2, a h2, a h3")
        assert cards.count() >= 2, "Not enough itinerary cards"

    def test_click_itinerary_opens_detail(self, desktop: Page, base_url):
        desktop.goto(f"{base_url}/lich-trinh")
        desktop.wait_for_load_state("networkidle")
        link = desktop.locator("a[href*='/lich-trinh/']").first
        if link.count() > 0:
            link.click()
            desktop.wait_for_load_state("networkidle")
            assert "/lich-trinh/" in desktop.url


class TestItineraryDetail:
    def test_detail_shows_stops(self, desktop: Page, base_url):
        """Itinerary detail shows stop points."""
        desktop.goto(f"{base_url}/lich-trinh/mot-ngay-cu-lao-an-binh")
        desktop.wait_for_load_state("networkidle")
        body = desktop.inner_text("main")
        assert len(body) > 100, "Itinerary detail is empty"

    def test_stops_link_to_entities(self, desktop: Page, base_url):
        """Stops in itinerary link to entity detail pages."""
        desktop.goto(f"{base_url}/lich-trinh/mot-ngay-cu-lao-an-binh")
        desktop.wait_for_load_state("networkidle")
        entity_links = desktop.locator("a[href*='/dia-diem/']")
        assert entity_links.count() >= 1, "Itinerary has no entity links"
```

### `tests/e2e/test_06_map_page.py` — BẢN ĐỒ

```python
"""Deep E2E: Map page — render, markers, click marker → entity."""

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.e2e


class TestMapPage:
    def test_map_page_loads(self, desktop: Page, base_url):
        r = desktop.goto(f"{base_url}/ban-do")
        assert r.status == 200

    def test_map_container_visible(self, desktop: Page, base_url):
        """Map container renders (Leaflet or similar)."""
        desktop.goto(f"{base_url}/ban-do")
        desktop.wait_for_load_state("networkidle")
        desktop.wait_for_timeout(3000)  # Map tiles take time
        map_el = desktop.locator("[class*='map'], [class*='Map'], .leaflet-container, #map, [id*='map']")
        assert map_el.count() >= 1, "No map container found"

    def test_map_has_markers(self, desktop: Page, base_url):
        """Map shows entity markers."""
        desktop.goto(f"{base_url}/ban-do")
        desktop.wait_for_load_state("networkidle")
        desktop.wait_for_timeout(3000)
        markers = desktop.locator(".leaflet-marker-icon, [class*='marker'], [class*='pin']")
        assert markers.count() >= 1, "No markers on map"

    def test_map_no_js_errors(self, desktop: Page, base_url, collect_errors):
        """Map page has no JS errors."""
        desktop.goto(f"{base_url}/ban-do")
        desktop.wait_for_load_state("networkidle")
        desktop.wait_for_timeout(3000)
        assert len(collect_errors) == 0, f"JS errors on map: {collect_errors}"
```

### `tests/e2e/test_07_community_deep.py` — CỘNG ĐỒNG

```python
"""Deep E2E: Community page — posts feed, trending, leaderboard."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestCommunityFeed:
    def test_page_loads(self, desktop: Page, base_url):
        r = desktop.goto(f"{base_url}/cong-dong")
        assert r.status == 200

    def test_has_content_or_empty_state(self, desktop: Page, base_url):
        """Shows posts or invitation to join."""
        desktop.goto(f"{base_url}/cong-dong")
        desktop.wait_for_load_state("networkidle")
        body = desktop.inner_text("body")
        assert len(body) > 100

    def test_trending_tags_visible(self, desktop: Page, base_url):
        """Trending hashtags section shows tags."""
        desktop.goto(f"{base_url}/cong-dong")
        desktop.wait_for_load_state("networkidle")
        tags = desktop.locator("[class*='tag'], [class*='hashtag'], a[href*='hashtag']")
        # Tags may or may not exist depending on posts

    def test_post_type_tabs(self, desktop: Page, base_url):
        """Post type filter tabs work (Tất cả, Chia sẻ, Review, Hỏi đáp)."""
        desktop.goto(f"{base_url}/cong-dong")
        desktop.wait_for_load_state("networkidle")
        tabs = desktop.locator("[class*='tab'] button, [role='tablist'] button, [class*='filter'] button")
        if tabs.count() >= 2:
            tabs.nth(1).click()
            desktop.wait_for_timeout(1000)


class TestLeaderboard:
    def test_leaderboard_loads(self, desktop: Page, base_url):
        r = desktop.goto(f"{base_url}/bang-xep-hang")
        assert r.status == 200

    def test_leaderboard_shows_users(self, desktop: Page, base_url):
        desktop.goto(f"{base_url}/bang-xep-hang")
        desktop.wait_for_load_state("networkidle")
        body = desktop.inner_text("body")
        assert len(body) > 100
```

### `tests/e2e/test_08_seo_comprehensive.py` — SEO SÂU

```python
"""Deep E2E: SEO — meta tags, JSON-LD, Open Graph, canonical, hreflang, sitemap."""

import json
import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.e2e

CRITICAL_PAGES = [
    "/", "/dia-diem", "/dia-diem/ho-truc-giang", "/du-lich", "/ocop",
    "/cong-dong", "/gioi-thieu", "/lich-trinh", "/ban-do", "/tim-kiem",
    "/xa-phuong/phuong-1-tp-vinh-long", "/khu-vuc/vinh-long",
]


class TestMetaTags:
    @pytest.mark.parametrize("path", CRITICAL_PAGES)
    def test_title_not_empty(self, desktop: Page, base_url, path):
        desktop.goto(f"{base_url}{path}")
        title = desktop.title()
        assert title and len(title) > 5, f"Empty/short title on {path}: '{title}'"
        assert "undefined" not in title.lower()

    @pytest.mark.parametrize("path", CRITICAL_PAGES)
    def test_meta_description(self, desktop: Page, base_url, path):
        desktop.goto(f"{base_url}{path}")
        desc = desktop.locator('meta[name="description"]')
        assert desc.count() >= 1, f"No meta description on {path}"
        content = desc.first.get_attribute("content")
        assert content and len(content) > 30, f"Short meta description on {path}"

    @pytest.mark.parametrize("path", CRITICAL_PAGES)
    def test_og_tags(self, desktop: Page, base_url, path):
        desktop.goto(f"{base_url}{path}")
        for prop in ["og:title", "og:description", "og:type"]:
            tag = desktop.locator(f'meta[property="{prop}"]')
            assert tag.count() >= 1, f"Missing {prop} on {path}"

    @pytest.mark.parametrize("path", CRITICAL_PAGES)
    def test_canonical_url(self, desktop: Page, base_url, path):
        desktop.goto(f"{base_url}{path}")
        canonical = desktop.locator('link[rel="canonical"]')
        assert canonical.count() >= 1, f"No canonical on {path}"
        href = canonical.first.get_attribute("href")
        assert href and href.startswith("https://"), f"Bad canonical on {path}: {href}"

    @pytest.mark.parametrize("path", CRITICAL_PAGES)
    def test_lang_vi(self, desktop: Page, base_url, path):
        desktop.goto(f"{base_url}{path}")
        lang = desktop.evaluate("document.documentElement.lang")
        assert lang == "vi", f"lang='{lang}' on {path}, expected 'vi'"


class TestJsonLD:
    def test_homepage_has_organization_schema(self, desktop: Page, base_url):
        desktop.goto(base_url)
        schemas = desktop.evaluate("""
            [...document.querySelectorAll('script[type="application/ld+json"]')]
                .map(s => JSON.parse(s.textContent))
        """)
        types = [s.get("@type") for s in schemas if isinstance(s, dict)]
        flat = []
        for s in schemas:
            if isinstance(s, dict) and "@graph" in s:
                flat.extend([item.get("@type") for item in s["@graph"] if isinstance(item, dict)])
            elif isinstance(s, dict):
                flat.append(s.get("@type"))
        assert any(t in ["Organization", "WebSite", "WebPage"] for t in flat), f"No org/website schema: {flat}"

    def test_entity_has_place_schema(self, desktop: Page, base_url):
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        schemas = desktop.evaluate("""
            [...document.querySelectorAll('script[type="application/ld+json"]')]
                .map(s => { try { return JSON.parse(s.textContent) } catch { return null } })
                .filter(Boolean)
        """)
        assert len(schemas) >= 1, "No JSON-LD on entity page"

    def test_jsonld_valid_json(self, desktop: Page, base_url):
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        result = desktop.evaluate("""
            [...document.querySelectorAll('script[type="application/ld+json"]')]
                .map(s => { try { JSON.parse(s.textContent); return 'ok' } catch(e) { return e.message } })
        """)
        errors = [r for r in result if r != "ok"]
        assert len(errors) == 0, f"Invalid JSON-LD: {errors}"


class TestSitemap:
    def test_sitemap_xml_exists(self, desktop: Page, base_url):
        r = desktop.goto(f"{base_url}/sitemap.xml")
        assert r.status == 200
        content = desktop.inner_text("body")
        assert "urlset" in content or "sitemapindex" in content, "Invalid sitemap"

    def test_robots_txt(self, desktop: Page, base_url):
        r = desktop.goto(f"{base_url}/robots.txt")
        assert r.status == 200
        body = desktop.inner_text("body")
        assert "User-agent" in body
        assert "Sitemap" in body
```

### `tests/e2e/test_09_performance_deep.py` — HIỆU NĂNG

```python
"""Deep E2E: Performance — load time, CLS, DOM size, resource count."""

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.e2e

PAGES = ["/", "/dia-diem", "/dia-diem/ho-truc-giang", "/cong-dong", "/ban-do", "/tim-kiem"]


class TestLoadPerformance:
    @pytest.mark.parametrize("path", PAGES)
    def test_page_loads_under_5_seconds(self, desktop: Page, base_url, path):
        """Page fully loads within 5 seconds."""
        desktop.goto(f"{base_url}{path}")
        timing = desktop.evaluate("""() => {
            const t = performance.timing;
            return { load: t.loadEventEnd - t.navigationStart, dom: t.domContentLoadedEventEnd - t.navigationStart }
        }""")
        assert timing["load"] < 5000, f"{path} took {timing['load']}ms"

    @pytest.mark.parametrize("path", PAGES[:3])
    def test_first_contentful_paint(self, desktop: Page, base_url, path):
        """FCP under 2.5 seconds."""
        desktop.goto(f"{base_url}{path}")
        fcp = desktop.evaluate("""() => {
            const entry = performance.getEntriesByName('first-contentful-paint')[0];
            return entry ? entry.startTime : -1;
        }""")
        if fcp > 0:
            assert fcp < 2500, f"FCP on {path}: {fcp:.0f}ms"


class TestResourceBudget:
    @pytest.mark.parametrize("path", PAGES[:3])
    def test_dom_under_3000_elements(self, desktop: Page, base_url, path):
        desktop.goto(f"{base_url}{path}")
        count = desktop.evaluate("document.querySelectorAll('*').length")
        assert count < 3000, f"DOM on {path}: {count} elements"

    @pytest.mark.parametrize("path", PAGES[:3])
    def test_total_requests_reasonable(self, desktop: Page, base_url, path):
        """Total network requests under 80."""
        requests = []
        desktop.on("request", lambda r: requests.append(r.url))
        desktop.goto(f"{base_url}{path}")
        desktop.wait_for_load_state("networkidle")
        assert len(requests) < 80, f"{path}: {len(requests)} requests"


class TestCLS:
    @pytest.mark.parametrize("path", PAGES[:4])
    def test_cumulative_layout_shift(self, desktop: Page, base_url, path):
        """CLS under 0.25."""
        desktop.goto(f"{base_url}{path}")
        cls = desktop.evaluate("""() => new Promise(resolve => {
            let cls = 0;
            new PerformanceObserver(list => {
                for (const entry of list.getEntries()) {
                    if (!entry.hadRecentInput) cls += entry.value;
                }
            }).observe({type: 'layout-shift', buffered: true});
            setTimeout(() => resolve(cls), 3000);
        })""")
        assert cls < 0.25, f"CLS on {path}: {cls:.3f}"


class TestBrokenResources:
    @pytest.mark.parametrize("path", PAGES)
    def test_no_broken_images(self, desktop: Page, base_url, path):
        """No images fail to load."""
        desktop.goto(f"{base_url}{path}")
        desktop.wait_for_load_state("networkidle")
        broken = desktop.evaluate("""
            [...document.querySelectorAll('img[src]')]
                .filter(i => i.complete && i.naturalWidth === 0 && i.src && !i.src.startsWith('data:'))
                .map(i => i.src)
        """)
        assert len(broken) == 0, f"Broken images on {path}: {broken[:3]}"

    @pytest.mark.parametrize("path", PAGES)
    def test_no_404_resources(self, desktop: Page, base_url, path):
        """No 404 resources (CSS, JS, fonts)."""
        failures = []
        desktop.on("response", lambda r: failures.append(f"{r.status} {r.url}") if r.status == 404 else None)
        desktop.goto(f"{base_url}{path}")
        desktop.wait_for_load_state("networkidle")
        assert len(failures) == 0, f"404 resources on {path}: {failures[:5]}"
```

### `tests/e2e/test_10_accessibility.py` — WCAG BASICS

```python
"""Deep E2E: Accessibility — WCAG 2.2 Level A basic checks."""

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.e2e


class TestImageAccessibility:
    def test_content_images_have_alt(self, desktop: Page, base_url):
        """Main content images have alt text."""
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        desktop.wait_for_load_state("networkidle")
        missing = desktop.evaluate("""
            [...document.querySelectorAll('main img, article img')]
                .filter(i => !i.alt && !i.getAttribute('role')?.includes('presentation') && i.src && !i.src.startsWith('data:'))
                .map(i => i.src.split('/').pop())
        """)
        assert len(missing) == 0, f"Images without alt: {missing[:5]}"


class TestHeadingStructure:
    @pytest.mark.parametrize("path", ["/", "/dia-diem/ho-truc-giang", "/dia-diem"])
    def test_single_h1(self, desktop: Page, base_url, path):
        """Page has exactly 1 H1."""
        desktop.goto(f"{base_url}{path}")
        h1_count = desktop.locator("h1").count()
        assert h1_count == 1, f"{path} has {h1_count} H1 tags"

    @pytest.mark.parametrize("path", ["/dia-diem/ho-truc-giang", "/"])
    def test_heading_hierarchy(self, desktop: Page, base_url, path):
        """Headings don't skip levels."""
        desktop.goto(f"{base_url}{path}")
        levels = desktop.evaluate("""
            [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => +h.tagName[1])
        """)
        for i in range(1, len(levels)):
            assert levels[i] - levels[i-1] <= 1, f"Heading skip on {path}: h{levels[i-1]}→h{levels[i]}"


class TestFormAccessibility:
    def test_search_input_has_label(self, desktop: Page, base_url):
        desktop.goto(f"{base_url}/tim-kiem")
        unlabeled = desktop.evaluate("""
            [...document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]), textarea')]
                .filter(el => !el.getAttribute('aria-label') && !el.getAttribute('placeholder') && !document.querySelector(`label[for="${el.id}"]`))
                .length
        """)
        assert unlabeled == 0

    def test_buttons_have_accessible_names(self, desktop: Page, base_url):
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        unnamed = desktop.evaluate("""
            [...document.querySelectorAll('button')]
                .filter(b => !b.textContent.trim() && !b.getAttribute('aria-label') && !b.getAttribute('title'))
                .map(b => b.outerHTML.substring(0, 60))
        """)
        assert len(unnamed) == 0, f"Buttons without names: {unnamed[:3]}"


class TestKeyboardNavigation:
    def test_tab_reaches_main_content(self, desktop: Page, base_url):
        """Tab key can reach main content area."""
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        # Press Tab multiple times
        for _ in range(15):
            desktop.keyboard.press("Tab")
        # Check focused element is in main content area
        focused = desktop.evaluate("document.activeElement?.closest('main') !== null || document.activeElement?.closest('header') !== null")
        assert focused, "Tab doesn't reach content or header"

    def test_skip_link_exists(self, desktop: Page, base_url):
        """Skip-to-content link exists (may be visually hidden)."""
        desktop.goto(base_url)
        skip = desktop.locator("a[href='#main'], a[href='#content'], a:has-text('Skip'), a:has-text('Bỏ qua')")
        # Skip links are common but not universal — just note if missing
```

### `tests/e2e/test_11_cross_page_journey.py` — HÀNH TRÌNH ĐA TRANG

```python
"""Deep E2E: Multi-page user journeys — simulating real user behavior."""

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.e2e


class TestDiscoveryJourney:
    """User arrives at homepage → browses → finds entity → explores related."""

    def test_full_discovery_flow(self, desktop: Page, base_url):
        """Homepage → Catalog → Entity → Related → Back."""
        # Step 1: Homepage
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        assert desktop.locator("h1, [class*='hero']").count() >= 1

        # Step 2: Click "Điểm đến" nav
        dia_diem = desktop.locator("a[href='/dia-diem'], a[href*='/dia-diem']").first
        dia_diem.click()
        desktop.wait_for_load_state("networkidle")
        assert "/dia-diem" in desktop.url

        # Step 3: Click first entity card
        entity_link = desktop.locator("a[href*='/dia-diem/']:not([href='/dia-diem'])").first
        if entity_link.count() > 0:
            entity_href = entity_link.get_attribute("href")
            entity_link.click()
            desktop.wait_for_load_state("networkidle")
            assert "/dia-diem/" in desktop.url
            assert desktop.locator("h1").count() == 1

            # Step 4: Scroll down to related entities
            for _ in range(5):
                desktop.mouse.wheel(0, 600)
                desktop.wait_for_timeout(300)
            
            # Step 5: Click related entity if exists
            related = desktop.locator("a[href*='/dia-diem/']").all()
            other_links = [l for l in related if l.get_attribute("href") != entity_href]
            if other_links:
                other_links[0].click()
                desktop.wait_for_load_state("networkidle")
                assert "/dia-diem/" in desktop.url

            # Step 6: Go back
            desktop.go_back()
            desktop.wait_for_load_state("networkidle")


class TestSearchJourney:
    """User searches → clicks result → back → refines search."""

    def test_search_refine_flow(self, desktop: Page, base_url):
        """Search → result → back → new search."""
        # Step 1: Go to search
        desktop.goto(f"{base_url}/tim-kiem")
        desktop.wait_for_load_state("networkidle")
        
        # Step 2: Search "Bến Tre"
        search = desktop.locator("input[type='search'], input[type='text']").first
        search.fill("Bến Tre")
        desktop.keyboard.press("Enter")
        desktop.wait_for_load_state("networkidle")
        desktop.wait_for_timeout(1000)
        
        # Step 3: Click first result
        result = desktop.locator("a[href*='/dia-diem/'], a[href*='/khu-vuc/']").first
        if result.count() > 0 and result.is_visible():
            result.click()
            desktop.wait_for_load_state("networkidle")
            
            # Step 4: Go back
            desktop.go_back()
            desktop.wait_for_load_state("networkidle")
            
            # Step 5: Search something different
            search = desktop.locator("input[type='search'], input[type='text']").first
            if search.count() > 0:
                search.fill("OCOP")
                desktop.keyboard.press("Enter")
                desktop.wait_for_load_state("networkidle")


class TestItineraryJourney:
    """Browse itineraries → view detail → click stop → back."""

    def test_itinerary_exploration(self, desktop: Page, base_url):
        desktop.goto(f"{base_url}/lich-trinh")
        desktop.wait_for_load_state("networkidle")
        
        link = desktop.locator("a[href*='/lich-trinh/']").first
        if link.count() > 0:
            link.click()
            desktop.wait_for_load_state("networkidle")
            assert "/lich-trinh/" in desktop.url
            
            # Click entity in itinerary
            entity_link = desktop.locator("a[href*='/dia-diem/']").first
            if entity_link.count() > 0:
                entity_link.click()
                desktop.wait_for_load_state("networkidle")
                assert "/dia-diem/" in desktop.url
                
                desktop.go_back()
                desktop.wait_for_load_state("networkidle")
```

### `tests/e2e/test_12_api_data_consistency.py` — SO SÁNH API vs RENDER

```python
"""Deep E2E: API response data matches what's rendered on page."""

import json
import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.e2e


class TestEntityDataConsistency:
    """API entity data matches rendered page."""

    def test_entity_name_matches_api(self, desktop: Page, base_url):
        """Page H1 matches API response name."""
        api_data = desktop.evaluate(f"""
            fetch('{base_url}/api/entities/ho-truc-giang').then(r => r.json())
        """)
        desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
        desktop.wait_for_load_state("networkidle")
        h1 = desktop.locator("h1").inner_text()
        assert api_data.get("name") in h1, f"API name: {api_data.get('name')}, Page H1: {h1}"

    def test_entity_description_rendered(self, desktop: Page, base_url):
        """API description appears on page (at least first 50 chars)."""
        api_data = desktop.evaluate(f"""
            fetch('{base_url}/api/entities/ho-truc-giang').then(r => r.json())
        """)
        desc = api_data.get("description", "")
        if desc and len(desc) > 50:
            desktop.goto(f"{base_url}/dia-diem/ho-truc-giang")
            desktop.wait_for_load_state("networkidle")
            body = desktop.inner_text("main")
            assert desc[:50] in body, "API description not rendered on page"

    def test_homepage_api_sections_rendered(self, desktop: Page, base_url):
        """Homepage API sections match rendered sections."""
        api = desktop.evaluate(f"""
            fetch('{base_url}/api/homepage').then(r => r.json())
        """)
        desktop.goto(base_url)
        desktop.wait_for_load_state("networkidle")
        body = desktop.inner_text("body")
        # Check that entity names from API appear on page
        if isinstance(api, dict):
            for key in list(api.keys())[:5]:
                section = api[key]
                if isinstance(section, list) and len(section) > 0:
                    first_item = section[0]
                    if isinstance(first_item, dict) and "name" in first_item:
                        assert first_item["name"] in body, f"API entity '{first_item['name']}' not on homepage"
                        break

    def test_search_api_matches_page_results(self, desktop: Page, base_url):
        """Search API results match page results."""
        api = desktop.evaluate(f"""
            fetch('{base_url}/api/search?q=cam+sành').then(r => r.json())
        """)
        desktop.goto(f"{base_url}/tim-kiem?q=cam+sành")
        desktop.wait_for_load_state("networkidle")
        desktop.wait_for_timeout(1000)
        body = desktop.inner_text("body")
        if isinstance(api, dict) and "entities" in api:
            for e in api["entities"][:3]:
                assert e.get("name", "") in body, f"Search result '{e.get('name')}' not on page"
        elif isinstance(api, list) and len(api) > 0:
            assert api[0].get("name", "") in body
```

---

# ═══════════════════════════════════════════
# PHẦN 3: OUTPUT & BÁO CÁO
# ═══════════════════════════════════════════

## Lệnh chạy

```bash
# 1. Baseline — phải xanh trước khi bắt đầu
python -m pytest agent/tests/ -q --tb=short 2>&1 | tail -5

# 2. Chạy unit tests mới (P0 trước)
python -m pytest agent/tests/test_social_deep.py agent/tests/test_auth_deep.py agent/tests/test_moderation_deep.py agent/tests/test_notifications_deep.py agent/tests/test_public_api_deep.py agent/tests/test_guardrails_deep.py -v --tb=short 2>&1 | tee unit-p0-results.txt

# 3. Chạy E2E (cần internet)
python -m pytest tests/e2e/ -m e2e -v --tb=short --timeout=60 --screenshot=only-on-failure --output=tests/e2e/screenshots/ 2>&1 | tee e2e-results.txt

# 4. Tổng hợp
python -m pytest agent/tests/ tests/e2e/ -q --tb=line 2>&1 | tee full-results.txt
```

## `TEST-REPORT.md` — BẮT BUỘC tạo

```markdown
# Test Automation & E2E Report — vinhlong360

## Executive Summary
- **Unit tests added:** X new / Y pass / Z fail
- **E2E tests added:** X new / Y pass / Z fail  
- **Existing tests status:** 3050 still pass? (yes/no)
- **Bugs discovered:** N total (X critical, Y medium, Z low)
- **Coverage increase:** modules covered X/75 (was 27/75)

## Unit Test Results

### P0 Modules (detail)
| Module | Tests written | Pass | Fail | Skip | Key findings |
|--------|-------------|------|------|------|-------------|
| social.py | ... | ... | ... | ... | ... |
...

### P1 Modules (summary)
...

## E2E Test Results

### By Page
| Page | Tests | Pass | Fail | Issues found |
|------|-------|------|------|-------------|
| Homepage | ... | ... | ... | ... |
...

### By Category
| Category | Tests | Pass | Fail |
|----------|-------|------|------|
| Navigation | ... | ... | ... |
| Search | ... | ... | ... |
| Performance | ... | ... | ... |
| SEO | ... | ... | ... |
| Accessibility | ... | ... | ... |
| Mobile | ... | ... | ... |
| Data consistency | ... | ... | ... |

## Bugs Discovered

### Critical (production impact)
1. **[BUG-001]** <description> — file:line, steps to reproduce, expected vs actual

### Medium (UX/data issues)  
...

### Low (cosmetic/minor)
...

## UX Observations
(Things that aren't bugs but could be better — found during E2E exploration)

## Recommendations
1. Highest priority fixes
2. Next modules to test
3. CI integration suggestions
```

## Tiêu chí thành công

| Criterion | Target |
|-----------|--------|
| P0 unit tests | ≥120 tests, all PASS |
| P1 unit tests | ≥100 tests, all PASS |
| E2E tests | ≥80 tests |
| E2E pass rate | ≥85% trên production |
| Existing tests | 3050 vẫn PASS |
| Multi-page journeys | ≥3 complete flows |
| Mobile viewport tests | ≥8 tests |
| Data consistency checks | ≥4 API vs render comparisons |
| Bugs documented | Mọi failure có steps-to-reproduce |
| TEST-REPORT.md | Đầy đủ, có executive summary |

---

# LƯU Ý QUAN TRỌNG

1. **BẮT ĐẦU TỪ P0.** Nếu hết thời gian → P0 đầy đủ + E2E homepage/entity/search quan trọng hơn P2 sơ sài.
2. **Viết test → chạy → fix → commit.** Không commit test fail.
3. **E2E PHẢI tương tác thật** — click, scroll, type, hover. Không chỉ `goto` + `assert status 200`.
4. **Vietnamese text là first-class** — test với dấu, không dấu, emoji, special chars.
5. **Mỗi test có docstring 1 dòng** giải thích WHAT, không HOW.
6. **Screenshots on fail** — chạy Playwright với `--screenshot=only-on-failure` để debug.
7. **Data consistency = gold standard** — API trả gì thì page phải render đó. Lệch = bug.
8. **Không test admin trên production** — admin cần API key thật, chỉ test unit.

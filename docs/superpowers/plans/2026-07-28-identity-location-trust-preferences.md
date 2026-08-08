# Identity, Location, Trust và Preferences Implementation Plan

> STATUS: active - đặc tả và kế hoạch NP-1 đã được duyệt; triển khai Subagent-Driven đang thực hiện trên worktree riêng.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng preference contract riêng tư, location consent, recommendation reset và trust/source UI trên các screen Nuxt hiện có, dùng các screen Stitch đã xác minh làm visual reference.

**Architecture:** Tách current preference (`user_preferences`), consent history (`user_preference_consents`) và bounded behavioral signals (`user_personalization_events`). API route chỉ điều phối; normalizer, resolver, retention, trust policy và explanation projection nằm trong module nhỏ có test riêng. Frontend dùng một composable làm source-of-truth cho user đã đăng nhập, còn `AuthModal`, `OnboardingSheet`, `/cai-dat`, `SmartRecommendations` và detail trust card được nâng cấp tại chỗ.

**Tech Stack:** FastAPI/Python 3.14, PostgreSQL migration chain, existing DB abstraction, Nuxt 4/Vue 3/TypeScript, Vitest, pytest, existing Chrome smoke runner, Stitch MCP project `18117519291023488351`.

## Global Constraints

- GPS/IP thô chỉ tồn tại trong request resolve; không lưu trong preference, personalization event, audit metadata, response cache hoặc recommendation telemetry.
- Preference precedence chính xác là `manual > gps > ip > default`.
- `explicit_interests` luôn có ưu tiên cao hơn inferred interests.
- `location_enabled = false` dừng cả GPS và IP personalization; manual region vẫn dùng được.
- `personalization_enabled = false` chỉ dùng manual region và public fallback, không dùng behavioral signals.
- `recommendation_reset_at` loại các event, saved item và visit trước cutoff khỏi scoring nhưng không xóa dữ liệu workspace.
- Exact age không xuất hiện trong recommendation response; chỉ dùng `derived_age_band`.
- Chỉ trả tier `verified` khi entity có verification record và `verified_at`.
- Official, verified partner và community phải có presentation semantics khác nhau.
- Mọi mutation yêu cầu ownership, CSRF, rate limit, bounded input và optimistic revision khi cập nhật preference.
- Không gọi geolocation trước user gesture; từ chối permission không tạo vòng lặp prompt.
- UI dùng các screen Stitch đã xác minh: detail V2, saved itinerary, community, mobile dark premium và search; không dùng Hybrid P1.2 làm source-of-truth.
- Stitch project `18117519291023488351` và các screen ID bắt buộc: detail V2 `6a86654f63f243679ebe997ea340172b`, saved itinerary `db76e318f0354ee3b1b8e3a0860443a5`, community `dc2a7a19958e442a990f548953a042e9`, mobile dark premium `9dac45c42bd7470797ff912060690909`, search `41df1bef12c443fe8247a62b3f50f419`.
- Không mở marketplace, booking, ordering, payment hoặc chế độ du lịch/người địa phương trong NP-1.
- Giữ public fallback hoạt động khi personalization/API/location resolver bị tắt hoặc lỗi.
- Các rollout flag mới mặc định `false`; mỗi flag phải có rollback độc lập và không được làm mất public fallback.
- Frontend tests phải kiểm hành vi render, interaction, API/state và accessibility thực tế; không dùng source-text assertions hoặc `readFileSync(...).toContain(...)` làm bằng chứng tích hợp.

## File Map

### Backend

- Create `agent/migrations/071_identity_location_preferences.sql`: bảng preference, consent history, personalization events và index/retention metadata.
- Create `agent/user_preferences.py`: schema normalization, revision merge, current snapshot và consent event persistence.
- Create `agent/location_resolver.py`: transient GPS/IP resolution boundary, provider adapter và privacy-safe diagnostics.
- Create `agent/personalization_events.py`: PostgreSQL event write/read/purge, TTL và legacy JSONL cutover adapter.
- Create `agent/trust_policy.py`: source tier/freshness derivation và explanation-safe projection.
- Modify `agent/public_api.py`: preference, consent, location, reset, event, insights và contextual recommendation routes.
- Modify `agent/auth.py`: export/delete final purge, consent projection và grace-period response consistency.
- Modify `agent/config.py`: feature flags và deadline legacy-event cutover.
- Modify `agent/scheduler.py`: bounded personalization-event retention job.

### Frontend

- Create `web-nuxt/types/personalization.ts`: shared preference, location resolution, consent, explanation and trust types.
- Create `web-nuxt/composables/usePersonalizationPreferences.ts`: authenticated preference state, revision handling, cache and mutations.
- Create `web-nuxt/components/PersonalizeSetupSheet.vue`: optional post-auth setup flow.
- Create `web-nuxt/components/WhyThisDrawer.vue`: explanation disclosure and controls.
- Create `web-nuxt/components/SourceTrustDrawer.vue`: source tier/freshness disclosure shared by detail/recommendation/notice surfaces.
- Modify `web-nuxt/composables/useRegionPref.ts`: adapter over preference API; localStorage remains anonymous cache only.
- Modify `web-nuxt/components/OnboardingSheet.vue`: state-aware entry point without forcing consent.
- Modify `web-nuxt/pages/cai-dat.vue`: new `Khu vực & đề xuất` panel, consent timeline field mapping and delete copy.
- Modify `web-nuxt/components/SmartRecommendations.vue`: `Vì sao bạn thấy nội dung này?` trigger and drawer integration.
- Modify `web-nuxt/pages/dia-diem/[id].vue`: shared trust drawer and honest source tier projection.
- Modify `web-nuxt/types/api.ts`: recommendation explanation/source fields.
- Modify `web-nuxt/utils/featureFlags.ts`: đăng ký ba UI rollout flag theo registry hiện có.

### Tests and verification

- Create `agent/tests/test_user_preferences.py`.
- Create `agent/tests/test_location_resolver.py`.
- Create `agent/tests/test_personalization_events.py`.
- Create `agent/tests/test_trust_policy.py`.
- Create `web-nuxt/tests/personalization-preferences.test.ts`.
- Create `web-nuxt/tests/location-consent.test.ts`.
- Create `web-nuxt/tests/why-this-trust.test.ts`.
- Create `web-nuxt/tests/personalization-feature-flags.test.ts`.
- Extend `web-nuxt/tests/smoke.test.ts` for route/component contracts.
- Extend the existing Chrome smoke flow with `/cai-dat#khu-vuc-de-xuat` and recommendation drawer assertions after the UI contract is stable.
- Create `docs/superpowers/reports/2026-07-28-np1-stitch-verification.md`: screen-to-component mapping, viewport/state evidence and verification results; no credentials or generated HTML.

---

### Task 1: Database schema and pure preference contract

**Files:**
- Create: `agent/migrations/071_identity_location_preferences.sql`
- Create: `agent/user_preferences.py`
- Test: `agent/tests/test_user_preferences.py`

**Interfaces:**
- Produces `PreferenceSnapshot`, `PreferencePatch`, `load_preferences(user_id)`, `patch_preferences(user_id, patch, expected_revision)`, `record_preference_consent(user_id, consent_type, state, version)` and `recommendation_cutoff(snapshot)` for later API/event tasks.
- `PreferenceSnapshot` contains `region_id`, `region_label`, `region_scope`, `location_source`, `location_accuracy`, `location_consent_state`, `location_enabled`, `personalization_enabled`, `explicit_interests`, `recommendation_reset_at`, `consent_version` and `revision`.

- [ ] **Step 1: Write the failing tests for normalization and precedence.**

```python
def test_manual_region_wins_over_lower_quality_sources():
    merged = merge_preference_patch(
        current={"region_id": "province-vl", "location_source": "manual", "revision": 2},
        patch={"region_id": "province-bt", "location_source": "ip"},
        expected_revision=2,
    )
    assert merged["region_id"] == "province-vl"
    assert merged["location_source"] == "manual"


def test_explicit_interests_are_unique_and_bounded():
    patch = normalize_preference_patch({"explicit_interests": ["food", "food", "x" * 200]})
    assert patch["explicit_interests"] == ["food"]


def test_revision_mismatch_is_rejected():
    with pytest.raises(PreferenceRevisionConflict):
        merge_preference_patch({"revision": 4}, {"location_enabled": False}, 3)
```

- [ ] **Step 2: Run the focused tests to verify the contract fails.**

Run: `python -m pytest -q agent/tests/test_user_preferences.py`

Expected: FAIL because `merge_preference_patch`, `normalize_preference_patch` and `PreferenceRevisionConflict` do not exist.

- [ ] **Step 3: Add the migration and minimal pure functions.**

Migration must create `user_preferences`, `user_preference_consents` and `user_personalization_events`, add indexes on `(user_id, occurred_at DESC)` and `(expires_at)`, and register migration version `71` using the existing `schema_version` convention. `user_preferences` must not contain latitude, longitude, raw IP or IP hash.

```python
def recommendation_cutoff(snapshot: Mapping[str, Any]) -> datetime | None:
    raw = snapshot.get("recommendation_reset_at")
    return parse_utc_timestamp(raw) if raw else None
```

Normalization must reject unknown enum values, cap interest count at 12, strip blank labels, and preserve `revision` as an integer.

- [ ] **Step 4: Run the focused tests and migration validation.**

Run: `python -m pytest -q agent/tests/test_user_preferences.py agent/tests/test_migration_apply.py`

Expected: all selected tests pass; migration chain applies without changing existing tables except the three additive tables/indexes.

- [ ] **Step 5: Commit the schema boundary.**

```powershell
git add agent/migrations/071_identity_location_preferences.sql agent/user_preferences.py agent/tests/test_user_preferences.py
git commit -m "feat: add identity location preference contract"
```

### Task 2: Preference and consent API

**Files:**
- Modify: `agent/public_api.py` near `/me/events`, `/me/insights` and `/me/recommendations/contextual`
- Modify: `agent/user_preferences.py`
- Test: `agent/tests/test_user_preferences.py`

**Interfaces:**
- `GET /api/me/preferences` returns `PreferenceSnapshot` with `Cache-Control: no-store`.
- `PATCH /api/me/preferences` accepts a partial `PreferencePatch` plus required `revision`, requires login/CSRF and returns `409` with current snapshot on conflict.
- `GET /api/me/preferences/consents` returns consent history without IP.

- [ ] **Step 1: Add failing route contract tests.**

```python
def test_preferences_default_snapshot_is_safe(client, logged_in_user):
    response = client.get("/api/me/preferences", headers=logged_in_user.headers)
    assert response.status_code == 200
    assert response.json()["location_enabled"] is False
    assert response.json()["region_id"] is None


def test_preferences_patch_requires_revision_and_csrf(client, logged_in_user):
    response = client.patch(
        "/api/me/preferences",
        json={"location_enabled": True},
        headers=logged_in_user.headers,
    )
    assert response.status_code == 403


def test_preferences_revision_conflict_returns_current_snapshot(client, logged_in_user):
    response = client.patch(
        "/api/me/preferences",
        json={"revision": 0, "location_enabled": True},
        headers=logged_in_user.csrf_headers,
    )
    assert response.status_code == 409
    assert "revision" in response.json()
```

- [ ] **Step 2: Run the route tests and verify the expected failures.**

Run: `python -m pytest -q agent/tests/test_user_preferences.py -k "default_snapshot or requires_revision or revision_conflict"`

Expected: FAIL because the routes are not mounted.

- [ ] **Step 3: Implement thin routes over `user_preferences.py`.**

The route must call `require_user`, the existing lazy CSRF dependency and the existing rate-limit utility. It must never accept a client-provided `user_id`. On `PATCH`, persist the consent event in the same transaction when `location_consent_state` or `personalization_enabled` changes.

- [ ] **Step 4: Run focused backend regression.**

Run: `python -m pytest -q agent/tests/test_user_preferences.py agent/tests/test_auth_security_hardening.py -k "preferences or csrf or session"`

Expected: all selected tests pass and no preference response contains exact date of birth, IP or coordinates.

- [ ] **Step 5: Commit the API contract.**

```powershell
git add agent/public_api.py agent/user_preferences.py agent/tests/test_user_preferences.py
git commit -m "feat: expose user preference and consent API"
```

### Task 3: Transient location resolver

**Files:**
- Create: `agent/location_resolver.py`
- Modify: `agent/public_api.py`
- Test: `agent/tests/test_location_resolver.py`

**Interfaces:**
- `resolve_gps(latitude: float, longitude: float, reverse_geocoder: ReverseGeocoder) -> LocationResolution`.
- `resolve_ip(client_ip: str, ip_geocoder: IpGeocoder) -> LocationResolution`.
- `LocationResolution` contains only normalized region fields and `location_source`/`location_accuracy`.
- `POST /api/me/location/resolve` accepts `{ "mode": "gps", "latitude": ..., "longitude": ... }` or `{ "mode": "ip" }` and never persists automatically.

- [ ] **Step 1: Write failing privacy and validation tests.**

```python
def test_gps_resolution_returns_normalized_region_without_coordinates():
    result = resolve_gps(10.25, 105.97, reverse_geocoder=lambda *_: {"region_id": "ward-1"})
    assert result.region_id == "ward-1"
    assert not hasattr(result, "latitude")
    assert not hasattr(result, "longitude")


def test_gps_out_of_bounds_is_rejected():
    with pytest.raises(LocationInputError):
        resolve_gps(91.0, 105.97, reverse_geocoder=lambda *_: {})


def test_ip_resolver_does_not_return_raw_ip():
    result = resolve_ip("203.0.113.8", ip_geocoder=lambda value: {"region_id": "province-vl"})
    assert result.region_id == "province-vl"
    assert "203.0.113.8" not in repr(result)


def test_ambiguous_resolution_requires_confirmation_without_persisting(client, logged_in_user):
    response = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_user.csrf_headers,
    )
    assert response.status_code == 200
    assert response.json()["location_accuracy"] == "unknown"
    assert load_preferences(logged_in_user.user_id)["region_id"] is None
```

- [ ] **Step 2: Run focused tests and confirm they fail for missing resolver types.**

Run: `python -m pytest -q agent/tests/test_location_resolver.py`

Expected: FAIL with missing resolver implementation.

- [ ] **Step 3: Implement the transient resolver and route.**

Use injected adapters so tests never call an external provider. Production adapters must use the existing pinned egress boundary when an external reverse-geocoder is configured. Do not log request body, coordinates or IP lookup input. If resolution is ambiguous/unavailable, return `accuracy="unknown"` and do not silently persist a new region.

- [ ] **Step 4: Verify resolver, route and privacy scans.**

Run: `python -m pytest -q agent/tests/test_location_resolver.py agent/tests/test_pinned_http_consumers.py`

Expected: all selected tests pass; source scan finds no `logger.*(latitude|longitude)` or raw resolver payload persistence.

- [ ] **Step 5: Commit the transient location boundary.**

```powershell
git add agent/location_resolver.py agent/public_api.py agent/tests/test_location_resolver.py
git commit -m "feat: add transient location resolution boundary"
```

### Task 4: PostgreSQL personalization events and reset semantics

**Files:**
- Create: `agent/personalization_events.py`
- Modify: `agent/public_api.py`
- Modify: `agent/auth.py`
- Modify: `agent/scheduler.py`
- Test: `agent/tests/test_personalization_events.py`

**Interfaces:**
- `write_personalization_event(user_id, event) -> None` stores normalized entity/context/interest keys only.
- `read_personalization_events(user_id, cutoff, limit=300) -> list[dict]` filters `occurred_at > cutoff` and `expires_at > now()`.
- `purge_personalization_events(user_id=None, before=None) -> int` supports final account purge and TTL job.
- `read_legacy_events_if_allowed(user_id, cutoff, now) -> list[dict]` applies reset cutoff and cutover deadline.
- `purge_legacy_events(user_id=None, before=None) -> int` rewrites legacy JSONL atomically under a cross-process file lock.
- `purge_user_personalization(user_id) -> None` deletes preference, consent and personalization-event rows during final account purge.
- `record_recommendation_reset(user_id) -> PreferenceSnapshot` updates cutoff atomically.
- Test-local helpers `seed_legacy_events(path, user_ids)` and `read_all_legacy_events(path)` create/read bounded JSONL fixtures only; production code never exports these helpers.

- [ ] **Step 1: Write failing tests for event shape, cutoff and purge.**

```python
def test_event_writer_drops_raw_query_and_ip(db, user_id):
    write_personalization_event(user_id, {
        "event_type": "search_submit",
        "query": "số điện thoại riêng tư",
        "ip": "203.0.113.8",
        "interest_keys": ["food"],
    })
    row = read_personalization_events(user_id, cutoff=None, limit=1)[0]
    assert "query" not in row
    assert "ip" not in row
    assert row["interest_keys"] == ["food"]


def test_reset_cutoff_excludes_old_events_and_signals(db, user_id):
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    cutoff = datetime(2026, 2, 1, tzinfo=timezone.utc)
    write_personalization_event(user_id, {"event_type": "view", "occurred_at": old})
    assert read_personalization_events(user_id, cutoff=cutoff) == []


def test_repeated_reset_keeps_one_effective_cutoff(client, logged_in_user):
    first = client.post("/api/me/recommendations/reset", headers=logged_in_user.csrf_headers)
    second = client.post("/api/me/recommendations/reset", headers=logged_in_user.csrf_headers)
    assert first.status_code == second.status_code == 200
    assert second.json()["recommendation_reset_at"] >= first.json()["recommendation_reset_at"]
```

- [ ] **Step 2: Run tests to verify the new storage contract fails.**

Run: `python -m pytest -q agent/tests/test_personalization_events.py`

Expected: FAIL because the PostgreSQL event helpers do not exist.

- [ ] **Step 3: Implement new writes, reads, purge and legacy adapter.**

Normalize event input before SQL. New writes must never include raw query, IP, GPS or arbitrary metadata. During the 30-day cutover, legacy JSONL reads must apply `recommendation_reset_at`; do not backfill raw fields into PostgreSQL. Implement `purge_legacy_events` with a temp-file plus atomic replace while holding a dedicated cross-process lock based on `versioned_json_store.publication_lock`. Add a scheduler callable for `expires_at` cleanup and an account-purge callable used by final delete.

- [ ] **Step 4: Integrate recommendation scoring and account export/delete.**

Update `_build_user_interest_profile` and `_contextual_recommendations` so explicit preferences are first-class, events are filtered by cutoff, and saved/visit signals before cutoff are excluded from scoring without deleting workspace rows. Add assertions that `personalization_enabled = false` uses manual-region/public fallback, explicit interests outrank inferred interests, and revoking location stops resolver signals on the next request. Extend `/auth/export-data` with preference/consent/new-event sections plus filtered legacy events during cutover. Final deletion after the grace period purges PostgreSQL rows and matching legacy rows under the file lock; scheduling deletion only marks the account inactive.

- [ ] **Step 5: Run backend regression and commit.**

Run: `python -m pytest -q agent/tests/test_personalization_events.py agent/tests/test_admin_mutations.py agent/tests/test_auth_security_hardening.py -k "event or recommendation or export or delete or account"`

Expected: all selected tests pass; legacy admin/auth behavior remains unchanged.

```powershell
git add agent/personalization_events.py agent/public_api.py agent/auth.py agent/scheduler.py agent/tests/test_personalization_events.py
git commit -m "feat: persist bounded personalization events"
```

### Task 5: Trust tier and explanation-safe response projection

**Files:**
- Create: `agent/trust_policy.py`
- Modify: `agent/public_api.py`
- Modify: `web-nuxt/types/api.ts`
- Test: `agent/tests/test_trust_policy.py`

**Interfaces:**
- `derive_source_tier(entity) -> Literal["official", "verified", "community", "unknown"]`.
- `derive_freshness(entity, now) -> Literal["fresh", "aging", "stale", "unknown"]`.
- `build_explanation(entity, reasons, preference_snapshot) -> RecommendationExplanation`.

- [ ] **Step 1: Write failing trust tests.**

```python
def test_verified_requires_verified_at():
    assert derive_source_tier({"partner_verified": True}) != "verified"
    assert derive_source_tier({"partner_verified": True, "verified_at": "2026-07-01T00:00:00Z"}) == "verified"


def test_community_is_not_promoted_by_moderation():
    entity = {"source_class": "user-uploaded", "moderation_status": "approved"}
    assert derive_source_tier(entity) == "community"


def test_freshness_does_not_change_source_tier():
    assert derive_source_tier({"official": True, "verified_at": None}) == "official"
    assert derive_freshness({"updated_at": "2020-01-01T00:00:00Z"}, now="2026-07-28T00:00:00Z") == "stale"
```

- [ ] **Step 2: Run trust tests and verify expected failures.**

Run: `python -m pytest -q agent/tests/test_trust_policy.py`

Expected: FAIL because the policy module does not exist.

- [ ] **Step 3: Implement policy and response projection.**

Use existing `source_freshness`, quality source and community descriptors. Return `unknown` rather than inventing a tier when evidence is missing. Extend `RecommendationCard`/`RecommendationResponse` with `explanation`, `source_tier` and `freshness_status` fields while preserving old `reason_vi` compatibility.

- [ ] **Step 4: Run policy and frontend type tests.**

Run: `python -m pytest -q agent/tests/test_trust_policy.py agent/tests/test_source_policy.py` and `npm run typecheck` in `web-nuxt`.

Expected: all selected tests pass and TypeScript accepts optional explanation fields.

- [ ] **Step 5: Commit the trust contract.**

```powershell
git add agent/trust_policy.py agent/public_api.py web-nuxt/types/api.ts agent/tests/test_trust_policy.py
git commit -m "feat: add source tier and freshness contract"
```

### Task 6: Frontend preference composable and setup sheet

**Files:**
- Create: `web-nuxt/types/personalization.ts`
- Create: `web-nuxt/composables/usePersonalizationPreferences.ts`
- Create: `web-nuxt/components/PersonalizeSetupSheet.vue`
- Modify: `web-nuxt/composables/useRegionPref.ts`
- Modify: `web-nuxt/components/OnboardingSheet.vue`
- Test: `web-nuxt/tests/personalization-preferences.test.ts`
- Test: `web-nuxt/tests/location-consent.test.ts`

**Interfaces:**
- `usePersonalizationPreferences()` returns `snapshot`, `loading`, `error`, `refresh`, `patch`, `resolveLocation`, `resetRecommendations`, `setRegion`, `setInterests` and `revokeLocation`.
- `resolveLocation("gps", coords)` returns normalized region only; it never exposes coordinates in state.
- Anonymous users may use `useRegionPref` local cache; authenticated users use the API snapshot as source-of-truth.

- [ ] **Step 1: Write failing composable contract tests.**

```ts
it('does not call geolocation before explicit user action', async () => {
  const geolocation = vi.spyOn(navigator.geolocation, 'getCurrentPosition')
  const { mount } = await loadPersonalizationSetupSheet()
  expect(geolocation).not.toHaveBeenCalled()
  await mount.get('[data-action="use-location"]').trigger('click')
  expect(geolocation).toHaveBeenCalledTimes(1)
})

it('manual region remains after location is turned off', async () => {
  const preferences = usePersonalizationPreferences()
  await preferences.setRegion({ id: 'province-vl', label: 'Vĩnh Long', scope: 'province' })
  await preferences.revokeLocation()
  expect(preferences.snapshot.value.region_id).toBe('province-vl')
  expect(preferences.snapshot.value.location_enabled).toBe(false)
})
```

- [ ] **Step 2: Run the focused Vitest files and verify they fail.**

Run: `npm test -- tests/personalization-preferences.test.ts tests/location-consent.test.ts`

Expected: FAIL because the composable, types and setup sheet do not exist.

- [ ] **Step 3: Implement the composable and setup sheet using Stitch references.**

Use the existing `useAuth`, `apiFetch`, `authHeaders`, `fetchCsrf`, `useModalA11y` and `IconLine`. The setup sheet must have three optional steps: region, up to three interests, and location permission. It must expose `Bỏ qua, thiết lập sau`, preserve focus, support Escape and never prompt geolocation during setup mount. Keep the sheet anatomy aligned with Stitch mobile dark premium and saved-workspace density, not Hybrid P1.2.

Before styling, retrieve and inspect Stitch screen `9dac45c42bd7470797ff912060690909` for mobile sheet/chrome and `db76e318f0354ee3b1b8e3a0860443a5` for grouping/density. Record the mapping in component comments or the verification report; do not copy generated HTML or Stitch credentials into source.

- [ ] **Step 4: Replace authenticated `useRegionPref` reads with preference adapter.**

Keep localStorage hydration-safe for anonymous/SSR usage. For authenticated users, `region` is derived from the API snapshot and `setRegion` calls `PATCH /api/me/preferences`; malformed API payload falls back to `all` without crashing.

- [ ] **Step 5: Run UI tests, typecheck and commit.**

Run: `npm test -- tests/personalization-preferences.test.ts tests/location-consent.test.ts`, then `npm run typecheck` in `web-nuxt`.

```powershell
git add web-nuxt/types/personalization.ts web-nuxt/composables/usePersonalizationPreferences.ts web-nuxt/components/PersonalizeSetupSheet.vue web-nuxt/composables/useRegionPref.ts web-nuxt/components/OnboardingSheet.vue web-nuxt/tests/personalization-preferences.test.ts web-nuxt/tests/location-consent.test.ts
git commit -m "feat: add adaptive preference setup flow"
```

### Task 7: Settings workspace and account/privacy corrections

**Files:**
- Modify: `web-nuxt/pages/cai-dat.vue`
- Modify: `agent/auth.py`
- Modify: `agent/tests/test_auth_security_hardening.py`
- Test: `web-nuxt/tests/personalization-preferences.test.ts`

**Interfaces:**
- Settings route remains `/cai-dat`; new anchor is `#khu-vuc-de-xuat`.
- Delete API response fields `status`, `message` and `grace_days` drive the confirmation/toast copy.
- Consent history UI consumes `{ id, version, created_at }` and never expects `consent_version`/`consent_at`.
- Test-local `preferenceFixture(overrides)` returns a complete `PreferenceSnapshot`; `mountSettingsPage({ preferences, consents, deleteResponse })` mounts the real page with API transport stubbed only at the network boundary.

- [ ] **Step 1: Write failing settings contract assertions.**

```ts
it('renders preference and consent data from the API contract', async () => {
  const wrapper = await mountSettingsPage({
    preferences: preferenceFixture({ region_label: 'Vĩnh Long' }),
    consents: [{ id: 'consent-1', version: 'location-v1', created_at: '2026-07-28T08:00:00Z' }],
  })
  expect(wrapper.get('#khu-vuc-de-xuat').text()).toContain('Vĩnh Long')
  expect(wrapper.get('[data-consent-id="consent-1"]').text()).toContain('location-v1')
  expect(wrapper.get('[data-consent-id="consent-1"] time').attributes('datetime')).toBe('2026-07-28T08:00:00Z')
})

it('uses the scheduled-deletion response instead of claiming immediate deletion', async () => {
  const wrapper = await mountSettingsPage({
    deleteResponse: { status: 'scheduled', message: 'Tài khoản sẽ bị xóa sau 30 ngày', grace_days: 30 },
  })
  await wrapper.get('[data-action="delete-account"]').trigger('click')
  await wrapper.get('[data-action="confirm-delete-account"]').trigger('click')
  expect(wrapper.get('[role="status"]').text()).toContain('Tài khoản sẽ bị xóa sau 30 ngày')
  expect(wrapper.text()).not.toContain('Đã xóa tài khoản')
})
```

- [ ] **Step 2: Run the targeted test and verify the expected failure.**

Run: `npm test -- tests/personalization-preferences.test.ts`

Expected: FAIL because the new panel and corrected field names are absent.

- [ ] **Step 3: Add `Khu vực & đề xuất` to the existing tab model.**

Render current region/source/accuracy, explicit interests, age band label, location toggle, personalization toggle and reset action. Copy must distinguish `unknown`, `manual`, `gps`, `ip`, `off`, `denied` and `expired`. Use optimistic UI with rollback from `usePersonalizationPreferences`; while offline, keep the cached snapshot readable, disable mutations and expose a retry action. On `409`, show the server snapshot and require an explicit retry instead of silently replacing state.

- [ ] **Step 4: Correct consent/delete behavior.**

Map consent `version`/`created_at`. Replace “xóa ngay” copy with the API grace period message. After a scheduled deletion, use the returned `grace_days` and do not claim data is already purged. Keep deactivate semantics separate.

- [ ] **Step 5: Run frontend/backend account regression and commit.**

Run: `npm test -- tests/personalization-preferences.test.ts` and `python -m pytest -q agent/tests/test_auth_security_hardening.py -k "delete or deactivate or consent"`.

```powershell
git add web-nuxt/pages/cai-dat.vue agent/auth.py agent/tests/test_auth_security_hardening.py web-nuxt/tests/personalization-preferences.test.ts
git commit -m "fix: align account privacy UI with preference contracts"
```

### Task 8: Why-this explanation and shared trust drawer

**Files:**
- Create: `web-nuxt/components/WhyThisDrawer.vue`
- Create: `web-nuxt/components/SourceTrustDrawer.vue`
- Modify: `web-nuxt/components/SmartRecommendations.vue`
- Modify: `web-nuxt/pages/dia-diem/[id].vue`
- Test: `web-nuxt/tests/why-this-trust.test.ts`

**Interfaces:**
- `WhyThisDrawer` props: `open`, `explanation`, `preferenceHref`; emits `close`, `reset`, `open-preferences`, `disable-personalization`.
- `SourceTrustDrawer` props: `open`, `sourceTier`, `sourceTitle`, `sourceUrl`, `verifiedAt`, `updatedAt`, `freshnessStatus`, `communityContext`; emits `close`, `report`.

- [ ] **Step 1: Write failing component contract tests.**

```ts
it('labels source tiers separately and refuses unsupported verified state', async () => {
  const wrapper = mount(SourceTrustDrawer, {
    props: { open: true, sourceTier: 'verified', verifiedAt: '', freshnessStatus: 'fresh' },
  })
  expect(wrapper.text()).not.toContain('Đã xác minh')
  expect(wrapper.text()).toContain('Chưa đủ bằng chứng xác minh')
})

it('exposes the explanation control and preference shortcut', async () => {
  const wrapper = mount(WhyThisDrawer, { props: { open: true, explanation: { primary_reason: 'Cùng khu vực bạn chọn' } } })
  expect(wrapper.text()).toContain('Vì sao bạn thấy nội dung này?')
  expect(wrapper.find('[data-action="open-preferences"]').exists()).toBe(true)
})
```

- [ ] **Step 2: Run targeted tests and verify missing component failure.**

Run: `npm test -- tests/why-this-trust.test.ts`

Expected: FAIL because the shared drawers do not exist.

- [ ] **Step 3: Implement drawers with existing modal accessibility primitives.**

Use `useModalA11y`, `IconLine`, current CSS tokens and Stitch references. Desktop uses popover/side drawer; mobile uses bottom sheet with sticky action. Explanation lists broad signals only; it must not display score, exact age or raw query. Trust drawer displays tier, source, freshness, verification date only when present, and report action.

Use detail V2 `6a86654f63f243679ebe997ea340172b` for source hierarchy, community `dc2a7a19958e442a990f548953a042e9` for moderation identity, and search `41df1bef12c443fe8247a62b3f50f419` for dense controls. Preserve Nuxt tokens and accessibility behavior as implementation authority.

- [ ] **Step 4: Integrate recommendation/detail surfaces.**

Replace inline `smart-rec-reason` with a disclosure trigger that keeps the card layout stable. Replace detail trust-card internals with the shared drawer while preserving the existing report link and `trustVisible` guard. Community content keeps community identity and moderation context.

- [ ] **Step 5: Run tests, typecheck and commit.**

Run: `npm test -- tests/why-this-trust.test.ts tests/entity-card-disclosure.test.ts`, then `npm run typecheck`.

```powershell
git add web-nuxt/components/WhyThisDrawer.vue web-nuxt/components/SourceTrustDrawer.vue web-nuxt/components/SmartRecommendations.vue web-nuxt/pages/dia-diem/[id].vue web-nuxt/tests/why-this-trust.test.ts
git commit -m "feat: add explanation and trust disclosure drawers"
```

### Task 9: Stitch-mapped visual, accessibility and state verification

**Files:**
- Modify: `web-nuxt/tests/smoke.test.ts`
- Modify: `web-nuxt/tests/personalization-preferences.test.ts`
- Modify: `web-nuxt/tests/location-consent.test.ts`
- Modify: `web-nuxt/tests/why-this-trust.test.ts`
- Create: `scripts/smoke_personalization_chrome.mjs`
- Create: `docs/superpowers/reports/2026-07-28-np1-stitch-verification.md`

**Interfaces:**
- Smoke script opens `/cai-dat#khu-vuc-de-xuat`, exercises manual region, opens WhyThis and verifies no geolocation call before click.
- Component integration tests mount the real surfaces and exercise disclosure controls; they do not grep component source.
- Test-local `recommendationFixture(overrides)`, `mountSmartRecommendations(state)` and `mountPlaceDetail(entity)` provide complete contract fixtures while keeping the real components and interaction logic mounted.
- Visual review compares layout anatomy against Stitch references, not generated HTML identity.
- State verification covers `unknown`, `manual`, `gps`, `ip`, `off`, `denied`, `expired`, `offline` and `conflict`.
- Visual baselines cover desktop `1440`, desktop `1024` and mobile `390` in light/dark, reduced motion and 200% text zoom.

- [ ] **Step 1: Add failing route/component inventory assertions.**

```ts
it('opens WhyThis from a personalized recommendation', async () => {
  const wrapper = mountSmartRecommendations({
    source: 'personalized',
    items: [recommendationFixture({ primary_reason: 'Cùng khu vực bạn chọn' })],
  })
  await wrapper.get('[data-action="why-this"]').trigger('click')
  expect(wrapper.get('[role="dialog"]').text()).toContain('Cùng khu vực bạn chọn')
})

it('opens source trust disclosure from a detail surface', async () => {
  const wrapper = mountPlaceDetail({
    source_tier: 'official',
    source_title: 'Cổng thông tin tỉnh Vĩnh Long',
    freshness_status: 'fresh',
  })
  await wrapper.get('[data-action="open-source-trust"]').trigger('click')
  expect(wrapper.get('[role="dialog"]').text()).toContain('Cổng thông tin tỉnh Vĩnh Long')
})
```

- [ ] **Step 2: Run smoke tests and confirm missing integration failures.**

Run: `npm test -- tests/smoke.test.ts tests/personalization-preferences.test.ts tests/location-consent.test.ts tests/why-this-trust.test.ts`

Expected: FAIL only where the new integrations are not yet asserted/mounted.

- [ ] **Step 3: Implement the Chrome smoke flow.**

Use the existing `scripts/smoke_e2e_chrome.mjs` conventions. Assert the following sequences: register then skip and configure later; manual region/interests then deny GPS; GPS resolve then explicit confirmation; region change updates explanation; location off prevents GPS/IP calls; repeated reset stays idempotent; offline mutation preserves cached state and retry does not duplicate the mutation. Verify official/verified/community and fresh/stale remain separate. Capture the required viewport/theme baselines and compare anatomy with all five Stitch screen IDs. Record each screen's borrowed anatomy, deliberate adaptation, viewport/state result and test command in `docs/superpowers/reports/2026-07-28-np1-stitch-verification.md`. Do not grant browser geolocation in the default smoke; use an isolated mocked-permission case for the successful GPS flow.

- [ ] **Step 4: Run the full frontend verification set.**

Run from `web-nuxt`:

```powershell
npm test
npm run typecheck
npm run build
```

Run the Chrome smoke script from repository root with the existing local API setup. Expected: all Vitest tests pass, typecheck exits `0`, build exits `0`, and no generated artifact is tracked.

- [ ] **Step 5: Commit verification coverage.**

```powershell
git add web-nuxt/tests/smoke.test.ts web-nuxt/tests/personalization-preferences.test.ts web-nuxt/tests/location-consent.test.ts web-nuxt/tests/why-this-trust.test.ts scripts/smoke_personalization_chrome.mjs docs/superpowers/reports/2026-07-28-np1-stitch-verification.md
git commit -m "test: verify identity location trust UI states"
```

### Task 10: Legacy cutover, retention and final gate

**Files:**
- Modify: `agent/public_api.py`
- Modify: `agent/auth.py`
- Modify: `agent/config.py`
- Modify: `agent/scheduler.py`
- Modify: `agent/personalization_events.py`
- Modify: `web-nuxt/utils/featureFlags.ts`
- Modify: `web-nuxt/components/OnboardingSheet.vue`
- Modify: `web-nuxt/components/SmartRecommendations.vue`
- Modify: `web-nuxt/pages/cai-dat.vue`
- Modify: `web-nuxt/pages/dia-diem/[id].vue`
- Test: `agent/tests/test_personalization_events.py`
- Test: `agent/tests/test_auth_security_hardening.py`
- Test: `web-nuxt/tests/personalization-feature-flags.test.ts`

**Interfaces:**
- Backend config fields: `PREFERENCE_PROFILE_V1`, `PERSONALIZATION_EVENTS_PG`, `LOCATION_RESOLVER_V1`, `RECOMMENDATION_EXPLANATIONS_V1`, `TRUST_DRAWER_V1`.
- Frontend public flags: `preference_ui_v1`, `recommendation_explanations_v1`, `trust_drawer_v1` through the existing feature-flag system.
- `LEGACY_EVENT_READ_UNTIL` is an ISO-8601 rollout deadline; after it, legacy JSONL is neither read nor written.

- [ ] **Step 1: Add failing cutover/retention tests.**

```python
def test_legacy_events_are_not_read_after_cutover_deadline(monkeypatch, user_id):
    monkeypatch.setattr(settings, "LEGACY_EVENT_READ_UNTIL", "2026-08-01T00:00:00Z")
    now = datetime(2026, 8, 2, tzinfo=timezone.utc)
    assert read_legacy_events_if_allowed(user_id, cutoff=None, now=now) == []


def test_final_account_purge_removes_preference_and_personalization_rows(db, user_id):
    purge_user_personalization(user_id)
    with db._conn() as conn:
        for table in ("user_preferences", "user_preference_consents", "user_personalization_events"):
            row = db._fetchone(conn, f"SELECT COUNT(*) AS count FROM {table} WHERE user_id::text = {db._ph}", (user_id,))
            assert int(db._row_to_dict(row)["count"]) == 0


def test_final_account_purge_removes_only_matching_legacy_events(user_events_file, user_id):
    other_user_id = "00000000-0000-0000-0000-000000000002"
    seed_legacy_events(user_events_file, [user_id, other_user_id])
    assert purge_legacy_events(user_id=user_id) == 1
    assert [row["user_id"] for row in read_all_legacy_events(user_events_file)] == [other_user_id]
```

Add frontend behavior tests that call `featureFlagDefault` for `preference_ui_v1`, `recommendation_explanations_v1` and `trust_drawer_v1` and receive `false`. Mount each real surface with its flag disabled and enabled: disabled hides only the NP-1 enhancement while preserving the public fallback; enabled exposes the preference panel, explanation trigger or trust disclosure respectively. Do not inspect component source text.

- [ ] **Step 2: Run the cutover tests and verify they fail.**

Run: `python -m pytest -q agent/tests/test_personalization_events.py -k "legacy or purge"`

Expected: FAIL until deadline gating and purge integration exist.

- [ ] **Step 3: Implement flags, deadline, scheduler retention and final purge.**

New writes must be PostgreSQL-only when `PERSONALIZATION_EVENTS_PG` is enabled. Add all backend fields to `Settings` with default `false`; register the three frontend flags in `FEATURE_FLAGS` with default `false` and gate their surfaces through the existing `useFeature` system. Legacy reads are bounded by `LEGACY_EVENT_READ_UNTIL` and `recommendation_reset_at`. After the deadline, the scheduler atomically removes expired legacy rows under the same file lock and stops all legacy reads/writes. Final account deletion purges preference, consent, PostgreSQL event and matching legacy rows only after the existing grace-period worker confirms permanent deletion.

- [ ] **Step 4: Run focused backend and full regression gates.**

Run:

```powershell
python -m pytest -q agent/tests/test_user_preferences.py agent/tests/test_location_resolver.py agent/tests/test_personalization_events.py agent/tests/test_trust_policy.py agent/tests/test_auth_security_hardening.py
npm test -- tests/personalization-feature-flags.test.ts tests/personalization-preferences.test.ts tests/why-this-trust.test.ts
```

Expected: all selected tests pass with no raw location/personalization leakage. Then run the full bounded backend suite used by NP-0 and record pass/skip counts.

- [ ] **Step 5: Commit the cutover and final gate.**

```powershell
git add agent/public_api.py agent/auth.py agent/config.py agent/scheduler.py agent/personalization_events.py agent/tests/test_personalization_events.py agent/tests/test_auth_security_hardening.py web-nuxt/utils/featureFlags.ts web-nuxt/components/OnboardingSheet.vue web-nuxt/components/SmartRecommendations.vue web-nuxt/pages/cai-dat.vue web-nuxt/pages/dia-diem/[id].vue web-nuxt/tests/personalization-feature-flags.test.ts
git commit -m "feat: complete personalization retention cutover"
```

## Final verification checklist

- [ ] `git diff --check` returns no whitespace errors.
- [ ] No `package-lock.json`, homepage, public catalog, database seed or unrelated migration changed.
- [ ] `git status --short --untracked-files=all` contains no build artifact.
- [ ] Backend focused tests pass, including privacy/logging assertions.
- [ ] Frontend `npm test`, `npm run typecheck` and `npm run build` pass.
- [ ] Chrome smoke covers manual region, denied location, reset, WhyThis and source drawer.
- [ ] Stitch reference IDs remain documented and no API key is committed.
- [ ] Final review confirms no exact age, raw IP, raw GPS, score leakage or false verification label.

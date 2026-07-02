# Entity Split Per-Kind — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tách quản lý entity trong AdminCP theo 9 nhóm (menu riêng, cột/bộ lọc đặc thù, dashboard độ đầy đủ, bulk edit, inline edit) — GĐ-A của spec `docs/superpowers/specs/2026-07-02-entity-split-per-kind-design.md`; GĐ-B/C (bảng CTI) phác ở cuối.

**Architecture:** GĐ-A thuần additive trên storage hiện tại (JSONB attributes): backend thêm param `kind` + endpoint completeness read-only; frontend thêm config-driven per-kind view trên trang `admin/entities.vue` sẵn có (KHÔNG nhân bản trang), sidebar submenu. Registry `agent/entity_schemas.py` là nguồn sự thật type→kind→fields.

**Tech Stack:** FastAPI (agent/), Nuxt 4 + TS (web-nuxt/), pytest.

## Global Constraints

- Baseline test đang đỏ 36 fail KHÔNG liên quan — mọi test mới phải xanh, KHÔNG làm tăng số đỏ.
- `agent/admin.py` + `web-nuxt/pages/admin/entities.vue` đang dirty bởi session song song → mọi edit ADDITIVE, anchor chính xác, không reformat vùng ngoài phạm vi.
- Không endpoint destructive mới; bulk edit đi qua PUT per-entity sẵn có (tái dùng validate + audit log).
- Commit nhỏ 1 task/commit, message `<GĐA.n> ...`. Không skip hook.
- Backend smoke env: `BUILD_SEARCH_INDEXES=false SCHEDULER_ENABLED=false`.
- 9 kind hiển thị: place, experience, product, food, lodging, event, facility, person, admin_place (itinerary có trang riêng; other gộp vào "Tất cả").

---

### Task A1: Backend — param `kind` cho GET /admin/entities

**Files:**
- Modify: `agent/admin.py:551-559` (signature `list_entities`) + thân `_query`
- Test: `agent/tests/test_admin_kind_views.py` (tạo mới)

**Interfaces:**
- Consumes: `_kind_of(t)` + `_ENTITY_SCHEMAS` đã import sẵn trong admin.py (dùng bởi `/admin/entity-kinds` line ~610); `db.list_entities(entity_type, area, limit, offset)`.
- Produces: `GET /admin/entities?kind=<k>` trả `{entities: [...], total}` chỉ gồm types thuộc kind; các param cũ giữ nguyên hành vi.

- [ ] **Step 1: Viết test fail** — tạo `agent/tests/test_admin_kind_views.py`:

```python
"""Tests GĐ-A: per-kind admin views (kind param + completeness endpoint)."""
import os
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-kindviews")
os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("BACKGROUND_INDEX_BUILD", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from server import app
from entity_schemas import KIND_OF_TYPE

client = TestClient(app)
H = {"X-Admin-Key": os.environ["ADMIN_API_KEY"]}
FOOD_TYPES = {t for t, k in KIND_OF_TYPE.items() if k == "food"}

def test_kind_param_returns_only_member_types():
    r = client.get("/admin/entities?kind=food&limit=500", headers=H)
    assert r.status_code == 200
    ents = r.json()["entities"]
    assert ents, "DB dev phải có entity ẩm thực"
    assert {e["type"] for e in ents} <= FOOD_TYPES

def test_kind_param_pagination_total():
    r = client.get("/admin/entities?kind=food&limit=5&offset=0", headers=H)
    body = r.json()
    assert len(body["entities"]) <= 5
    assert body["total"] >= len(body["entities"])

def test_kind_unknown_returns_empty():
    r = client.get("/admin/entities?kind=khong-ton-tai", headers=H)
    assert r.status_code == 200
    assert r.json()["entities"] == []

def test_type_param_still_works_unchanged():
    r = client.get("/admin/entities?type=product&limit=5", headers=H)
    assert r.status_code == 200
    assert all(e["type"] == "product" for e in r.json()["entities"])
```

- [ ] **Step 2: Chạy để thấy fail** — `python -m pytest agent/tests/test_admin_kind_views.py -q` → FAIL (kind bị bỏ qua → lẫn type khác / total sai).
- [ ] **Step 3: Implement** — trong `list_entities`: thêm `kind: Optional[str] = Query(None, max_length=30)` vào signature; đầu `_query` thêm:

```python
        kind_types: list[str] | None = None
        if kind and not type:
            kind_types = sorted(t for t, k in _KIND_OF_TYPE.items() if k == kind)
            if not kind_types:
                return {"entities": [], "total": 0}
```

(import bổ sung `KIND_OF_TYPE as _KIND_OF_TYPE` cạnh các import entity_schemas sẵn có). Nhánh liệt kê: nếu `kind_types` → gom `db.list_entities(entity_type=t, area=area, limit=2000, offset=0)` cho từng t (riêng `place` nếu `db.list_entities` loại trừ thì dùng nhánh SQL trực tiếp giống `include_places` line ~569), merge, sort theo `name`, `total=len(merged)`, slice `[offset:offset+limit]`. Nhánh `q`: sau khi search, lọc `e["type"] in set(kind_types)`.
- [ ] **Step 4: Test pass** — `python -m pytest agent/tests/test_admin_kind_views.py -q` → 4 passed.
- [ ] **Step 5: Commit** — `git add agent/admin.py agent/tests/test_admin_kind_views.py && git commit -m "<GĐA.1> admin list_entities: param kind (expand qua registry)"`

### Task A2: Backend — GET /admin/entity-completeness

**Files:**
- Modify: `agent/admin.py` (thêm endpoint ngay sau `entity_kinds` ~line 640)
- Test: `agent/tests/test_admin_kind_views.py` (thêm case)

**Interfaces:**
- Produces: `GET /admin/entity-completeness?kind=<k>&worst=20` →
  `{kind, total, fields: [{key,label,scope,filled,pct}], worst: [{id,name,type,missing:[...],missing_count}]}`.
  `fields` = 8 trường phổ quát (address/phone/website/hours/price_range/sub_category/best_time/highlight — đọc từ attributes) + `season`(top-level months không rỗng) + `images`(top-level) + `coords_real`(coordinates có và KHÔNG `attributes.coords_approximate`) + `summary_100`(len≥100) + các trường registry của types thuộc kind (pct tính trên đúng type sở hữu trường).

- [ ] **Step 1: Test fail** (thêm vào file test):

```python
def test_completeness_food_shape():
    r = client.get("/admin/entity-completeness?kind=food", headers=H)
    assert r.status_code == 200
    b = r.json()
    assert b["kind"] == "food" and b["total"] > 0
    keys = {f["key"] for f in b["fields"]}
    assert {"address", "phone", "season", "images", "price_range"} <= keys
    for f in b["fields"]:
        assert 0 <= f["pct"] <= 100
    assert b["worst"] and "missing" in b["worst"][0]

def test_completeness_requires_kind():
    assert client.get("/admin/entity-completeness", headers=H).status_code == 422
```

- [ ] **Step 2: fail** → 404 (endpoint chưa có).
- [ ] **Step 3: Implement** endpoint:

```python
@router.get("/entity-completeness",
            summary="Data completeness per kind",
            description="Per-kind field-fill percentages (universal + registry fields) plus the entities missing the most data. Read-only reporting for the per-kind AdminCP views.")
async def entity_completeness(kind: str = Query(..., max_length=30), worst: int = Query(20, ge=1, le=100)):
    def _query():
        kind_types = sorted(t for t, k in _KIND_OF_TYPE.items() if k == kind)
        if not kind_types:
            return {"kind": kind, "total": 0, "fields": [], "worst": []}
        ents = []
        for t in kind_types:
            ents.extend(db.list_entities(entity_type=t, limit=2000, offset=0) or [])
        UNIVERSAL = [("address", "Địa chỉ"), ("phone", "Điện thoại"), ("website", "Website"),
                     ("hours", "Giờ mở cửa"), ("price_range", "Khoảng giá"),
                     ("sub_category", "Phân loại"), ("best_time", "Thời điểm đẹp"), ("highlight", "Điểm nhấn")]
        def has(e, key):
            a = e.get("attributes") or {}
            if key == "season":
                s = e.get("season") or {}
                return bool(s.get("months") or s.get("best"))
            if key == "images":
                return bool(e.get("images"))
            if key == "coords_real":
                return bool(e.get("coordinates")) and not (a.get("coords_approximate"))
            if key == "summary_100":
                return len(str(e.get("summary") or "")) >= 100
            v = a.get(key)
            return v not in (None, "", [], {})
        fields, missing_map = [], {e["id"]: [] for e in ents}
        universal_keys = [k for k, _ in UNIVERSAL] + ["season", "images", "coords_real", "summary_100"]
        labels = dict(UNIVERSAL) | {"season": "Mùa", "images": "Ảnh", "coords_real": "Tọa độ thật", "summary_100": "Tóm tắt ≥100 ký tự"}
        for key in universal_keys:
            filled = sum(1 for e in ents if has(e, key))
            fields.append({"key": key, "label": labels[key], "scope": "chung",
                           "filled": filled, "pct": round(100 * filled / len(ents), 1) if ents else 0})
            for e in ents:
                if not has(e, key):
                    missing_map[e["id"]].append(key)
        seen = set(universal_keys)
        for t in kind_types:
            schema = _ENTITY_SCHEMAS.get(t) or {}
            t_ents = [e for e in ents if e["type"] == t]
            for f in schema.get("fields", []):
                key = f["key"]
                if key in seen or not t_ents:
                    continue
                filled = sum(1 for e in t_ents if has(e, key))
                fields.append({"key": key, "label": f["label"], "scope": schema.get("label", t),
                               "filled": filled, "pct": round(100 * filled / len(t_ents), 1)})
                for e in t_ents:
                    if not has(e, key):
                        missing_map[e["id"]].append(key)
        by_id = {e["id"]: e for e in ents}
        worst_list = sorted(missing_map.items(), key=lambda kv: -len(kv[1]))[:worst]
        return {"kind": kind, "total": len(ents), "fields": fields,
                "worst": [{"id": i, "name": by_id[i]["name"], "type": by_id[i]["type"],
                           "missing": m, "missing_count": len(m)} for i, m in worst_list if m]}
    return await asyncio.to_thread(_query)
```

- [ ] **Step 4: pass** — `python -m pytest agent/tests/test_admin_kind_views.py -q` → 6 passed.
- [ ] **Step 5: Commit** — `<GĐA.2> admin: endpoint entity-completeness per-kind`.

### Task A3: FE — config per-kind `web-nuxt/utils/adminKinds.ts` (tạo mới)

**Files:** Create: `web-nuxt/utils/adminKinds.ts`

**Interfaces (Produces — A4/A5/A6/A7 dùng):**

```ts
export interface KindColumn { key: string; label: string; widget: 'text'|'number'|'select'|'bool'; options?: string[]; width?: string }
export interface KindChip { key: string; label: string; test: (e: any) => boolean }
export interface KindDef { kind: string; slug: string; label: string; emoji: string; types: string[]; columns: KindColumn[]; chips: KindChip[] }
export const ADMIN_KINDS: KindDef[]           // 9 nhóm, thứ tự hiển thị
export function kindBySlug(slug: string): KindDef | undefined
```

- [ ] **Step 1: Viết file** — 9 KindDef; `types` khớp `KIND_OF_TYPE` backend; cột (tất cả đọc `entity.attributes[key]`):
  - place `dia-diem` 🛕: sub_category(text), admission(text), heritage_level(select: 4 mức HERITAGE_LEVELS)
  - experience `trai-nghiem` 🌾: duration(text), operator(text), price_range(text)
  - product `san-pham` 🍊: ocop_star(select "1".."5"), producer(text), price_range(text)
  - food `am-thuc` 🍲: price_range(text), rating(number), specialty(text)
  - lodging `luu-tru` 🏡: accommodation_type(select ACCOM_TYPES), rooms(number), price_range(text)
  - event `su-kien` 🎉: date_start(text), venue(text), organizer(text)
  - facility `co-quan` 🏛️: office_kind(select OFFICE_KINDS), phone(text), hours(text)
  - person `nhan-vat` 👤: role(text), birth_year(number), hometown(text)
  - admin_place `xa-phuong` 📍: former_district(text), population(number), effective_date(text)
  - Chips mỗi kind: 2 chip chung `{key:'thieu-dia-chi', test: e=>!e.attributes?.address}`, `{key:'thieu-mua', test: e=>!(e.season?.months?.length||e.season?.best)}` + 1-2 đặc thù (product: `ocop-4-5` test ocop_star>=4, `thieu-producer`; place: `di-tich-qg` test heritage_level chứa 'quốc gia'; food: `co-rating`; lodging: `thieu-rooms`; event: `le-hoi-am-lich` test lunar_date).
- [ ] **Step 2: Verify compile** — `cd web-nuxt && npx nuxi typecheck 2>&1 | tail -5` (chấp nhận lỗi pre-existing, KHÔNG lỗi mới trong adminKinds.ts).
- [ ] **Step 3: Commit** — `<GĐA.3> FE: config per-kind adminKinds.ts`.

### Task A4: FE — sidebar submenu 9 nhóm

**Files:** Modify: `web-nuxt/layouts/admin.vue:30-33` (link Entities trong nav-group "Nội dung")

- [ ] **Step 1:** Thay link Entities đơn bằng: giữ link "Tất cả entities" (`/admin/entities`, active khi `route.path==='/admin/entities' && !route.query.kind`) + 9 NuxtLink con class `nav-sub` lặp từ `ADMIN_KINDS` (import từ `~/utils/adminKinds`): `:to="{ path: '/admin/entities', query: { kind: k.kind } }"`, active khi `route.query.kind === k.kind`, label `{{k.emoji}} {{k.label}}`, ẩn label khi `sidebarCollapsed`.
- [ ] **Step 2:** CSS thêm cuối style block: `.admin-nav a.nav-sub { padding-left: calc(var(--space-4) + 14px); font-size: .86em; opacity: .92; }`.
- [ ] **Step 3:** Build nhanh `npm run build` (nền) → pass. Commit `<GĐA.4> FE: sidebar submenu nhóm entity`.

### Task A5: FE — entities.vue kind-aware (tiêu đề + fetch + cột + giới hạn type)

**Files:** Modify: `web-nuxt/pages/admin/entities.vue`

**Interfaces:** Consumes `kindBySlug`/`ADMIN_KINDS` (A3), param `kind` backend (A1).

- [ ] **Step 1: State** — script setup thêm:

```ts
import { ADMIN_KINDS } from '~/utils/adminKinds'
const route = useRoute()
const currentKind = computed(() => ADMIN_KINDS.find(k => k.kind === String(route.query.kind || '')) || null)
```

- [ ] **Step 2: Fetch** — trong `fetchEntities()` thêm `if (currentKind.value) params.kind = currentKind.value.kind` (và bỏ param type khi kind active trừ khi admin chọn type con); `watch(() => route.query.kind, () => { page.value = 0; fetchEntities() })`.
- [ ] **Step 3: Header** — tiêu đề trang: `{{ currentKind ? currentKind.emoji + ' ' + currentKind.label : 'Entities' }}`; select bộ lọc type + select type trong modal tạo mới: options = `currentKind ? currentKind.types : types` (types tổng sẵn có).
- [ ] **Step 4: Cột động** — trong `<thead>` sau cột cố định (Tên/Loại/Khu vực…): `<th v-for="c in currentKind?.columns || []" :key="c.key">{{ c.label }}</th>`; `<tbody>` render ô tương ứng đọc `ent.attributes?.[c.key]` (bool → ✓/—; select/text/number → giá trị hoặc `—`).
- [ ] **Step 5: Chips lọc client** — dải chip trên bảng: `v-for="ch in currentKind?.chips"`, toggle `activeChips` (Set), computed `visibleEntities = entities.filter(e => [...activeChips].every(k => chipByKey(k).test(e)))` — bảng render `visibleEntities`.
- [ ] **Step 6:** Build pass, thử tay: `/admin/entities?kind=san-pham` → chỉ product/craft_village, cột sao OCOP hiện. Commit `<GĐA.5> FE: trang entities kind-aware (cột+lọc đặc thù)`.

### Task A6: FE — panel completeness per-kind

**Files:** Create: `web-nuxt/components/admin/KindCompleteness.vue`; Modify: `entities.vue` (mount dưới kind overview panel khi `currentKind`)

- [ ] **Step 1: Component** — props `{ kind: string }`; fetch `/admin-api/entity-completeness?kind=` + authHeaders; render: grid các field `label — pct%` với bar (`<div class="kc-bar"><i :style="{width: pct+'%'}"/></div>`, đỏ <40%, vàng <75%, xanh ≥75%); mục "Cần bổ sung nhất" liệt kê `worst` (name + số trường thiếu + danh sách key), click → mở edit modal (emit `edit(id)` — entities.vue đã có `openEdit`).
- [ ] **Step 2: Integrate** — `<LazyAdminKindCompleteness v-if="currentKind" :kind="currentKind.kind" @edit="onCompletenessEdit" />`; handler tìm entity trong list (hoặc fetch riêng `GET /admin-api/entities/{id}`) rồi `openEdit(e)`.
- [ ] **Step 3:** Build + thử: panel % khớp dữ liệu. Commit `<GĐA.6> FE: dashboard độ đầy đủ per-kind`.

### Task A7: FE — bulk edit + inline edit

**Files:** Modify: `web-nuxt/pages/admin/entities.vue`

- [ ] **Step 1: Chọn nhiều** — cột checkbox đầu bảng + `selected = ref<Set<string>>(new Set())` + checkbox header chọn-tất-cả-trang (cap 100: khi vượt, toast cảnh báo).
- [ ] **Step 2: BulkBar** — thanh nổi khi `selected.size > 0`: "Đã chọn N — Gán trường…" → chọn field từ `currentKind.columns` (+ 8 trường phổ quát) + input giá trị theo widget → nút Áp dụng:

```ts
async function applyBulk(fieldKey: string, value: unknown) {
  bulkRunning.value = true; const errs: string[] = []
  for (const id of selected.value) {
    const e = entities.value.find(x => x.id === id); if (!e) continue
    const attrs = { ...(e.attributes || {}), [fieldKey]: value }
    if (value === '' || value === null) delete attrs[fieldKey]
    try {
      await $fetch(`/admin-api/entities/${id}`, { method: 'PUT', headers: authHeaders(),
        body: { id, name: e.name, type: e.type, placeId: e.placeId || '', summary: e.summary || '', attributes: attrs } })
    } catch { errs.push(`${e.name}` ) }
  }
  bulkRunning.value = false
  showToast(errs.length ? `Xong, lỗi ${errs.length}: ${errs.slice(0,3).join(', ')}…` : `Đã gán cho ${selected.value.size} entity`, errs.length ? 'warning' : 'success')
  selected.value = new Set(); await fetchEntities()
}
```

  (LƯU Ý: xác nhận shape PUT hiện tại của modal — nếu PUT yêu cầu thêm trường (images…), sao chép đúng body builder của `saveEntity` trừ phần typed/KBYG overlay.)
- [ ] **Step 3: Inline edit** — ô cột động (A5 Step 4) khi click → input nhỏ theo widget (text/number: input; select: select; bool: toggle) — Enter/blur lưu qua cùng PUT pattern (merge 1 key), Esc huỷ; đang lưu → ô mờ. Tái dùng pattern inline name/type sẵn có trong file (đã có từ B2a).
- [ ] **Step 4:** Build + thử tay 3 thao tác (bulk 2 entity, inline 1 ô number, 1 ô select). Commit `<GĐA.7> FE: bulk edit + inline edit theo nhóm`.

### Task A8: Verify tổng + deploy GĐ-A

- [ ] **Step 1:** `python -m pytest agent/tests/test_admin_kind_views.py agent/tests/test_entity_schemas.py -q` → xanh hết; `python -m pytest agent/tests -q -k "admin"` không tăng fail so baseline.
- [ ] **Step 2:** `cd web-nuxt && npm run build` (nền) → pass.
- [ ] **Step 3:** Deploy phẫu thuật: scp `agent/admin.py` + FE `.output` → restart vl-agent (poll :8360/health) + vl-nuxt; **thêm check search**: `curl /api/search?q=test` phải 200 (bài học incident).
- [ ] **Step 4:** Verify prod: `/admin-api/entity-completeness?kind=food` → 401 (đăng ký, cần key); bundle chứa 'Cần bổ sung nhất'. Commit docs cập nhật trạng thái spec.

---

## GĐ-B/C — phác bước chính (plan chi tiết viết sau khi GĐ-A nghiệm thu)

**GĐ-B:** (0) sửa chuỗi migration (init.sql posts.deleted_at; 059 = reviewer_note + entity_changes + site_settings_history + PG_REQUIRED_TABLES; replay-test PG docker trắng) → (1) migration 060: 8 cột phổ quát trên entities → (2) migration 061: 9 bảng `entity_*_details` (PK=FK entity_id, ALTER OWNER vl360, DDL kép PG+SQLite) → (3) `scripts/backfill_entity_details.py` (idempotent, §B1 backup trước) → (4) `scripts/verify_entity_details_parity.py` (exit≠0 nếu lệch) → (5) schema test §B4 mỗi bảng.

**GĐ-C:** flag `ENTITY_DETAILS_TABLES` (OFF mặc định) → DAL đọc JOIN dựng lại attributes đúng shape cũ → ghi (admin CRUD + _bulk_load tách typed/tail, port guard coords/alias) → export re-join giữ format → contract test snapshot 1 entity/kind trước-sau flip byte-identical → bật prod ≥1 tuần → script dọn typed keys khỏi JSONB (chủ duyệt riêng, §B1).

## Self-review

- Spec coverage: menu riêng (A4), cột/lọc đặc thù (A3+A5), dashboard (A2+A6), bulk (A7), inline (A7), kind param (A1), GĐ-B/C outline — đủ các mục GĐ-A của spec. ✓
- Placeholder: không còn TBD; code block đầy đủ cho phần mới; 2 chỗ chủ-động yêu cầu implementer xác minh shape sẵn có (PUT body, db.list_entities với place) là verification step có lệnh cụ thể, không phải placeholder. ✓
- Type consistency: `KindDef.kind` = giá trị kind backend (`food`…) — A4 dùng `query.kind = k.kind`, A5 so `route.query.kind === k.kind`, backend expand qua `KIND_OF_TYPE` — nhất quán (slug chỉ dùng làm nhãn URL thân thiện nếu cần sau). ✓

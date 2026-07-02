<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>{{ currentKind ? `${currentKind.emoji} ${currentKind.label}` : 'Quản lý Entities' }}</h1>
        <p class="ent-subtitle">{{ entities.length ? `${entities.length} kết quả` : '' }}</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchEntities()">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
      </button>
    </div>

    <div class="admin-toolbar">
      <div class="ent-search-wrap">
        <input v-model="search" class="input" placeholder="Tìm entity…" aria-label="Tìm entity" @input="debounceFetch" @keyup.escape="clearSearch" />
        <button v-if="search" type="button" class="ent-search-clear" aria-label="Xóa tìm kiếm" @click="clearSearch">&times;</button>
        <span v-if="searching" class="ent-searching" aria-live="polite">Đang tìm…</span>
      </div>
      <select v-model="typeFilter" class="input admin-select-filter" aria-label="Lọc theo loại entity" @change="fetchEntities(true)">
        <option value="">{{ currentKind ? `Cả nhóm ${currentKind.label}` : 'Tất cả loại' }}</option>
        <option v-for="t in kindTypes" :key="t" :value="t">{{ TYPE_META[t]?.emoji || '' }} {{ TYPE_META[t]?.label || t }}</option>
      </select>
      <button type="button" class="btn btn-outline btn-sm" :class="{ 'btn-active-warn': orphansOnly }" @click="orphansOnly = !orphansOnly; fetchEntities(true)">
        {{ orphansOnly ? '&#10003; Mồ côi' : 'Mồ côi' }}
      </button>
      <button type="button" class="btn btn-primary" @click="openCreate">+ Tạo mới</button>
      <button type="button" class="btn btn-outline btn-sm" :title="`Tải JSON (${entities.length} entity trang này)`" @click="exportJSON">&#x2B73; JSON ({{ entities.length }})</button>
      <button type="button" class="btn btn-outline btn-sm" :title="`Tải CSV (${entities.length} entity trang này)`" @click="exportCSV">&#x2B73; CSV ({{ entities.length }})</button>
    </div>

    <!-- Phase 2: tổng quan theo danh mục (7 nhóm chủ trên 17 type) -->
    <details v-if="kindGroups.length" class="ent-kinds-panel">
      <summary class="ent-kinds-summary">
        📊 Tổng quan theo danh mục
        <span class="ent-kinds-total">{{ kindGrandTotal.toLocaleString('vi-VN') }} entity</span>
      </summary>
      <div class="ent-kinds-grid">
        <div v-for="k in kindGroups" :key="k.kind" class="ent-kind-card">
          <div class="ent-kind-head">
            <span class="ent-kind-emoji" aria-hidden="true">{{ k.emoji }}</span>
            <span class="ent-kind-label">{{ k.label }}</span>
            <span class="ent-kind-count">{{ k.total }}</span>
          </div>
          <div class="ent-kind-types">
            <button v-for="t in k.types" :key="t.type" type="button"
              class="ent-kind-chip" :class="{ active: typeFilter === t.type }"
              :title="`Lọc: ${t.label} (${t.count})`" @click="filterByType(t.type)">
              {{ t.emoji }} {{ t.label }} <span class="ent-kind-chip-n">{{ t.count }}</span>
            </button>
          </div>
        </div>
      </div>
    </details>

    <!-- GĐ-A: dashboard độ đầy đủ dữ liệu theo nhóm -->
    <LazyAdminKindCompleteness v-if="currentKind" :kind="currentKind.kind" @edit="onCompletenessEdit" />

    <!-- GĐ-A: chip lọc nhanh theo nhóm -->
    <div v-if="currentKind?.chips.length" class="ent-chip-row" role="group" aria-label="Lọc nhanh theo nhóm">
      <button v-for="ch in currentKind.chips" :key="ch.key" type="button"
        class="ent-kind-chip" :class="{ active: activeChips.has(ch.key) }" @click="toggleChip(ch.key)">
        {{ ch.label }}
      </button>
      <span v-if="activeChips.size" class="ent-chip-note">{{ chipFiltered.length }}/{{ entities.length }} khớp</span>
    </div>

    <div v-if="selected.size" class="bulk-bar">
      <span>Đã chọn {{ selected.size }}</span>
      <template v-if="currentKind">
        <select v-model="bulkField" class="input bulk-assign-field" aria-label="Chọn trường để gán hàng loạt">
          <option value="">Gán trường…</option>
          <option v-for="c in bulkFields" :key="c.key" :value="c.key">{{ c.label }}</option>
        </select>
        <template v-if="bulkFieldDef">
          <select v-if="bulkFieldDef.widget === 'select'" v-model="bulkValue" class="input bulk-assign-value" aria-label="Giá trị gán">
            <option value="">(xóa giá trị)</option>
            <option v-for="o in bulkFieldDef.options" :key="o" :value="o">{{ o }}</option>
          </select>
          <select v-else-if="bulkFieldDef.widget === 'bool'" v-model="bulkValue" class="input bulk-assign-value" aria-label="Giá trị gán">
            <option value="true">Có</option>
            <option value="false">Không</option>
            <option value="">(xóa)</option>
          </select>
          <input v-else v-model="bulkValue" class="input bulk-assign-value"
            :type="bulkFieldDef.widget === 'number' ? 'number' : 'text'"
            placeholder="Giá trị (trống = xóa)" aria-label="Giá trị gán" @keyup.enter="applyBulkAssign" />
          <button type="button" class="btn btn-primary btn-sm" :disabled="bulkAssignBusy" @click="applyBulkAssign">
            {{ bulkAssignBusy ? `Đang gán ${bulkProgress}…` : `Gán cho ${selected.size}` }}
          </button>
        </template>
      </template>
      <button type="button" class="btn-danger" :disabled="bulkBusy" @click="bulkDelete">Xóa đã chọn</button>
      <button type="button" class="btn btn-outline btn-sm" @click="selected = new Set()">Bỏ chọn</button>
    </div>

    <div v-if="loadError && !loading" class="ent-error-banner" role="alert">
      <span>Không thể tải danh sách entity.</span>
      <button type="button" class="btn btn-outline btn-sm" @click="fetchEntities()">Thử lại</button>
    </div>

    <div v-if="loading" class="admin-loading" role="status" aria-label="Đang tải">
      <div class="ent-skeleton" aria-hidden="true">
        <div v-for="n in 6" :key="n" class="ent-skel-row">
          <span class="skeleton ent-skel-check"></span>
          <span class="skeleton skeleton-text ent-skel-id"></span>
          <span class="skeleton skeleton-text ent-skel-name"></span>
          <span class="skeleton skeleton-text ent-skel-type"></span>
        </div>
      </div>
    </div>
    <template v-else>
      <div class="admin-table-wrap">
      <table class="admin-table" aria-label="Danh sách entity">
        <thead>
          <tr>
            <th scope="col" class="admin-th-check"><input type="checkbox" :checked="allSelected" @change="toggleAll" aria-label="Chọn tất cả" /></th>
            <th scope="col" class="ent-sortable"><button type="button" class="ent-sort-btn" @click="toggleSort('id')">ID <span class="ent-sort-arrow" aria-hidden="true">{{ sortArrow('id') }}</span></button></th>
            <th scope="col" class="ent-sortable"><button type="button" class="ent-sort-btn" @click="toggleSort('name')">Tên <span class="ent-sort-arrow" aria-hidden="true">{{ sortArrow('name') }}</span></button></th>
            <th scope="col" class="ent-sortable"><button type="button" class="ent-sort-btn" @click="toggleSort('type')">Loại <span class="ent-sort-arrow" aria-hidden="true">{{ sortArrow('type') }}</span></button></th>
            <th scope="col" class="ent-sortable"><button type="button" class="ent-sort-btn" @click="toggleSort('place_name')">Địa điểm <span class="ent-sort-arrow" aria-hidden="true">{{ sortArrow('place_name') }}</span></button></th>
            <th v-for="c in currentKind?.columns || []" :key="c.key" scope="col">{{ c.label }}</th>
            <th scope="col"><span title="Tóm tắt / Ảnh / Địa điểm">Chất lượng</span><span class="admin-help" data-tip="● xanh = có, ● đỏ = thiếu. Thứ tự: Tóm tắt · Ảnh · Địa điểm" tabindex="0" role="img" aria-label="Giải thích chất lượng">?</span></th>
            <th scope="col">Thao tác</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in sortedEntities" :key="e.id" :class="{ 'row-selected': selected.has(e.id), 'row-acting': acting === e.id }">
            <td><input type="checkbox" :checked="selected.has(e.id)" @change="toggleSel(e.id)" :aria-label="`Chọn ${e.name}`" /></td>
            <td class="admin-td-id">{{ e.id }}</td>
            <td>
              <div class="ent-name-cell">
                <div class="ent-thumb" v-if="e.images?.length">
                  <img :src="e.images[0]" :alt="e.name" width="32" height="32" loading="lazy" decoding="async" @error="(ev) => ((ev.target as HTMLImageElement).style.display = 'none')" />
                </div>
                <div class="ent-thumb ent-thumb-empty" v-else>&#128247;</div>
                <template v-if="inlineEdit.id === e.id && inlineEdit.field === 'name'">
                  <input v-model="inlineEdit.value" class="input ent-inline-input" :aria-label="`Sửa tên ${e.name}`" @keyup.enter="saveInline(e)" @keyup.escape="inlineEdit.id = ''" @vue:mounted="(vn: any) => vn.el?.focus()" />
                </template>
                <strong v-else class="ent-inline-label" @dblclick="startInline(e, 'name', e.name)">{{ e.name }}</strong>
              </div>
            </td>
            <td>
              <template v-if="inlineEdit.id === e.id && inlineEdit.field === 'type'">
                <select v-model="inlineEdit.value" class="input ent-inline-select" :aria-label="`Chọn loại cho ${e.name}`" @change="saveInline(e)" @keyup.escape="inlineEdit.id = ''" @vue:mounted="(vn: any) => vn.el?.focus()">
                  <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
                </select>
              </template>
              <span v-else class="type-badge ent-inline-label" :data-type="e.type" @dblclick="startInline(e, 'type', e.type)">{{ e.type }}</span>
            </td>
            <td class="admin-td-muted">{{ e.place_name || '—' }}</td>
            <td v-for="c in currentKind?.columns || []" :key="c.key" class="ent-kind-cell">
              <button v-if="c.widget === 'bool'" type="button" class="ent-bool-toggle"
                :aria-label="`Bật/tắt ${c.label} cho ${e.name}`" @click="toggleBoolAttr(e, c.key)">
                {{ ((e as any).attributes || {})[c.key] ? '✓' : '—' }}
              </button>
              <template v-else-if="inlineEdit.id === e.id && inlineEdit.field === 'attr:' + c.key">
                <select v-if="c.widget === 'select'" v-model="inlineEdit.value" class="input ent-inline-select"
                  :aria-label="`Sửa ${c.label}`" @change="saveInline(e)" @keyup.escape="inlineEdit.id = ''"
                  @vue:mounted="(vn: any) => vn.el?.focus()">
                  <option value="">(xóa)</option>
                  <option v-for="o in c.options" :key="o" :value="o">{{ o }}</option>
                </select>
                <input v-else v-model="inlineEdit.value" class="input ent-inline-input"
                  :type="c.widget === 'number' ? 'number' : 'text'" :aria-label="`Sửa ${c.label}`"
                  @keyup.enter="saveInline(e)" @keyup.escape="inlineEdit.id = ''"
                  @vue:mounted="(vn: any) => vn.el?.focus()" />
              </template>
              <span v-else class="ent-inline-label" :title="`Nhấp đúp để sửa ${c.label}`"
                @dblclick="startInline(e, 'attr:' + c.key, String(((e as any).attributes || {})[c.key] ?? ''))">
                {{ ((e as any).attributes || {})[c.key] ?? '—' }}
              </span>
            </td>
            <td class="ent-health-cell">
              <span class="ent-dot" :class="e.summary ? 'dot-ok' : 'dot-miss'" :title="e.summary ? 'Có tóm tắt' : 'Thiếu tóm tắt'" :aria-label="e.summary ? 'Có tóm tắt' : 'Thiếu tóm tắt'" role="img">{{ e.summary ? '✓' : '✗' }}</span>
              <span class="ent-dot" :class="e.images?.length ? 'dot-ok' : 'dot-miss'" :title="e.images?.length ? `${e.images.length} ảnh` : 'Thiếu ảnh'" :aria-label="e.images?.length ? `${e.images.length} ảnh` : 'Thiếu ảnh'" role="img">{{ e.images?.length ? '✓' : '✗' }}</span>
              <span class="ent-dot" :class="e.placeId ? 'dot-ok' : 'dot-miss'" :title="e.placeId ? 'Có địa điểm' : 'Thiếu địa điểm'" :aria-label="e.placeId ? 'Có địa điểm' : 'Thiếu địa điểm'" role="img">{{ e.placeId ? '✓' : '✗' }}</span>
            </td>
            <td class="admin-actions">
              <button type="button" class="btn-success" @click="openEdit(e)" :aria-label="`Sửa ${e.name}`">Sửa</button>
              <button type="button" @click="cloneEntity(e)" title="Nhân bản" :aria-label="`Nhân bản ${e.name}`">&#128203;</button>
              <button type="button" class="btn-danger" :disabled="acting === e.id" @click="deleteEntity(e.id)" :aria-label="`Xóa ${e.name}`">Xóa</button>
            </td>
          </tr>
          <tr v-if="!sortedEntities.length">
            <td :colspan="7 + (currentKind?.columns.length || 0)" class="admin-empty-row">
              <div class="ent-empty">
                <span class="ent-empty-icon">&#128269;</span>
                <template v-if="search">
                  <span>Không có kết quả cho “{{ search }}”.</span>
                  <button type="button" class="btn btn-outline btn-sm" @click="clearSearch">Xóa tìm kiếm</button>
                </template>
                <template v-else>
                  <span>Chưa có entity nào.</span>
                  <button type="button" class="btn btn-primary btn-sm" @click="openCreate">+ Tạo mới</button>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <nav v-if="entities.length || page > 1" class="admin-pagination" role="navigation" aria-label="Phân trang">
        <button type="button" :disabled="page <= 1" @click="page--; fetchEntities()">← Trước</button>
        <span class="admin-page-info">
          Trang {{ page }}<span v-if="totalEntities" class="ent-page-hint"> · {{ totalEntities }} entity</span><span v-if="entities.length < limit" class="ent-page-hint"> · trang cuối</span>
        </span>
        <button type="button" :disabled="entities.length < limit" @click="page++; fetchEntities()">Sau →</button>
      </nav>
    </template>

    <!-- Edit/Create Modal -->
    <Transition name="modal-fade">
    <div v-if="showModal" ref="modalRef" class="modal-overlay show" role="dialog" aria-modal="true" :aria-label="editingEntity ? 'Sửa Entity' : 'Tạo Entity'" @click.self="showModal = false">
      <div class="modal admin-modal-md">
        <h2>{{ editingEntity ? 'Sửa Entity' : 'Tạo Entity' }}</h2>
        <div class="admin-form-col">
          <fieldset class="ent-fieldset">
          <legend class="ent-fieldset-legend">Thông tin cơ bản</legend>
          <div class="ent-field">
            <label class="form-label" for="ent-id">ID (slug)</label>
            <input id="ent-id" v-model="form.id" class="input" :class="{ error: fieldErrors.id }" placeholder="ID (slug)" aria-label="ID (slug)" :disabled="!!editingEntity" :aria-invalid="!!fieldErrors.id" :aria-describedby="fieldErrors.id ? 'ent-id-err' : undefined" @input="clearFieldError('id')" />
            <span v-if="fieldErrors.id" id="ent-id-err" class="form-error" role="alert">{{ fieldErrors.id }}</span>
          </div>
          <div class="ent-field">
            <label class="form-label" for="ent-name">Tên</label>
            <input id="ent-name" v-model="form.name" class="input" :class="{ error: fieldErrors.name }" placeholder="Tên" aria-label="Tên entity" :aria-invalid="!!fieldErrors.name" :aria-describedby="fieldErrors.name ? 'ent-name-err' : undefined" @input="clearFieldError('name'); checkDuplicate()" />
            <span v-if="fieldErrors.name" id="ent-name-err" class="form-error" role="alert">{{ fieldErrors.name }}</span>
            <div v-if="duplicates.length && !editingEntity" class="ent-dup-warn" role="alert">
              <strong>&#9888; Có thể trùng:</strong>
              <span v-for="d in duplicates" :key="d.id" class="ent-dup-item">{{ d.name }} <span class="ent-dup-type">({{ d.type }})</span></span>
            </div>
          </div>
          <div class="ent-field">
            <label class="form-label" for="ent-type">Loại</label>
            <select id="ent-type" v-model="form.type" class="input" aria-label="Loại entity" :disabled="!!editingEntity">
              <option v-for="t in kindTypes" :key="t" :value="t">{{ TYPE_META[t]?.emoji || '' }} {{ TYPE_META[t]?.label || t }}</option>
            </select>
            <span v-if="editingEntity" class="sf-help">Đổi loại: sửa nhanh ô "Loại" ngay trên bảng (an toàn cho thuộc tính).</span>
          </div>
          <div class="ent-field">
            <label class="form-label" for="ent-place">Place ID (xã/phường)</label>
            <input id="ent-place" v-model="form.placeId" class="input" placeholder="Place ID (xã/phường)" aria-label="Place ID" list="ent-places-list" />
            <datalist id="ent-places-list">
              <option v-for="p in placesList" :key="p.id" :value="p.id">{{ p.name }} ({{ p.area || '' }})</option>
            </datalist>
          </div>
          <div class="ent-field">
            <label class="form-label" for="ent-summary">Tóm tắt <span class="ent-char-count" :class="{ 'ent-char-warn': (form.summary || '').length > 400, 'ent-char-danger': (form.summary || '').length > 450 }">{{ (form.summary || '').length }}/500</span></label>
            <textarea v-if="!previewSummary" id="ent-summary" v-model="form.summary" class="input admin-textarea" placeholder="Tóm tắt" aria-label="Tóm tắt" rows="3" maxlength="500"></textarea>
            <div v-else class="ent-summary-preview" v-text="form.summary"></div>
            <button type="button" class="btn btn-ghost btn-sm" @click="previewSummary = !previewSummary">{{ previewSummary ? 'Sửa' : 'Xem trước' }}</button>
          </div>
          </fieldset>

          <!-- Trường theo loại (content-model registry) -->
          <fieldset v-for="grp in currentSchemaGroups" :key="grp.legend" class="ent-fieldset ent-typed-fieldset">
            <legend class="ent-fieldset-legend">
              {{ entitySchemas[form.type]?.emoji }} {{ grp.legend }}
              <span class="ent-typed-hint">— {{ entitySchemas[form.type]?.label }}</span>
            </legend>
            <div class="ent-typed-grid">
              <AdminSchemaField
                v-for="f in grp.fields" :key="f.key"
                :field="f"
                :model-value="typedAttrs[f.key]"
                @update:model-value="(v: unknown) => (typedAttrs[f.key] = v)"
              />
            </div>
          </fieldset>

          <!-- Mùa (season) — tháng có mặt + cao điểm -->
          <details class="ent-kbyg-details">
            <summary class="admin-label ent-kbyg-summary">🗓️ Mùa / thời điểm ({{ seasonMonths.length }} tháng<span v-if="seasonPeak.length">, {{ seasonPeak.length }} cao điểm</span>)</summary>
            <div class="ent-kbyg-fields">
              <p class="sf-help ent-season-hint">Bấm mỗi tháng để chuyển: không → có mùa → cao điểm → tắt.</p>
              <div class="ent-season-grid" role="group" aria-label="Chọn tháng theo mùa">
                <button v-for="(lbl, i) in MONTH_LABELS" :key="i" type="button"
                  :class="['ent-season-cell', `ent-season-${monthState(i + 1)}`]"
                  :aria-label="`Tháng ${lbl}: ${monthState(i + 1) === 'peak' ? 'cao điểm' : monthState(i + 1) === 'in' ? 'có mùa' : 'không'}`"
                  @click="cycleMonth(i + 1)">T{{ lbl }}</button>
              </div>
              <div class="ent-season-legend">
                <span><i class="ent-season-swatch ent-season-in"></i> Có mùa</span>
                <span><i class="ent-season-swatch ent-season-peak"></i> Cao điểm</span>
              </div>
            </div>
          </details>

          <!-- KBYG — Know Before You Go -->
          <details class="ent-kbyg-details">
            <summary class="admin-label ent-kbyg-summary">🎒 Biết trước khi đi (KBYG)</summary>
            <div class="ent-kbyg-fields">
              <div class="ent-field">
                <label class="form-label" for="kbyg-tips">Mẹo du lịch (mỗi dòng = 1 mẹo)</label>
                <textarea id="kbyg-tips" v-model="kbygTips" class="input admin-textarea" rows="3" placeholder="VD: Nên đi buổi sáng sớm&#10;Mang dép thoải mái&#10;Có chỗ đậu xe miễn phí"></textarea>
              </div>
              <div class="ent-field">
                <label class="form-label" for="kbyg-golden-hours">Giờ vàng</label>
                <input id="kbyg-golden-hours" v-model="kbygGoldenHours" class="input" placeholder="VD: 6-8h sáng hoặc 16-18h chiều" />
              </div>
              <div class="ent-field">
                <label class="form-label" for="kbyg-peak-days">Ngày đông</label>
                <input id="kbyg-peak-days" v-model="kbygPeakDays" class="input" placeholder="VD: Cuối tuần, lễ Tết" />
              </div>
              <div class="ent-field">
                <label class="form-label" for="kbyg-crowd-level">Mức đông</label>
                <select id="kbyg-crowd-level" v-model="kbygCrowdLevel" class="input">
                  <option value="">— Chưa rõ —</option>
                  <option value="Ít người">Ít người</option>
                  <option value="Vừa phải">Vừa phải</option>
                  <option value="Đông">Đông</option>
                  <option value="Rất đông">Rất đông</option>
                </select>
              </div>
              <div class="ent-field">
                <label class="form-label" id="kbyg-amenities-label">Tiện ích</label>
                <div class="kbyg-amenity-grid" role="group" aria-labelledby="kbyg-amenities-label">
                  <label v-for="(meta, key) in AMENITY_OPTIONS" :key="key" class="kbyg-amenity-check">
                    <input type="checkbox" :checked="kbygAmenities.includes(key)" @change="toggleAmenity(key)" />
                    <span>{{ meta.icon }} {{ meta.label }}</span>
                  </label>
                </div>
              </div>
              <div class="ent-field">
                <label class="form-label" for="kbyg-checklist">Checklist chuẩn bị (mỗi dòng = 1 item, để trống = mặc định theo loại)</label>
                <textarea id="kbyg-checklist" v-model="kbygChecklist" class="input admin-textarea" rows="2" placeholder="VD: Kem chống nắng&#10;Tiền mặt&#10;Nón"></textarea>
              </div>
            </div>
          </details>

          <!-- Thuộc tính nâng cao (bespoke tail — không có trong schema/KBYG) -->
          <details class="ent-kbyg-details">
            <summary class="admin-label ent-kbyg-summary">🧩 Thuộc tính nâng cao (JSON)</summary>
            <div class="ent-kbyg-fields">
              <p class="sf-help">Các thuộc tính đặc thù không có ô riêng (vd sac_phong, deity_worshipped…). Sửa trực tiếp JSON — các trường đã có ô riêng ở trên sẽ được giữ tách biệt.</p>
              <textarea v-model="advancedJson" class="input admin-textarea ent-advanced-json" rows="6" spellcheck="false"
                placeholder='{&#10;  "sac_phong": "…",&#10;  "custom_key": "…"&#10;}' @input="advancedError = ''"></textarea>
              <span v-if="advancedError" class="form-error" role="alert">{{ advancedError }}</span>
            </div>
          </details>

          <!-- Quản lý ảnh (chỉ khi sửa) -->
          <div v-if="editingEntity" class="img-mgr">
            <strong class="admin-label">Ảnh ({{ (form.images || []).length }}/10)</strong>
            <div v-for="(img, i) in (form.images || [])" :key="i" class="img-row">
              <img :src="img" :alt="`Ảnh ${i + 1}`" class="img-thumb" width="48" height="48" loading="lazy" decoding="async" @error="(e) => ((e.target as HTMLImageElement).style.opacity = '.3')" />
              <span class="img-url">{{ img }}</span>
              <button type="button" class="btn-danger btn-sm" @click="removeImage(i)">Xóa</button>
            </div>
            <div class="admin-inline-add">
              <input v-model="newImage" class="input" placeholder="https://… (chỉ nguồn cấp phép)" aria-label="URL ảnh mới" @keyup.enter="addImage" />
              <button type="button" class="btn btn-secondary btn-sm" :disabled="!newImage.trim()" @click="addImage">Thêm ảnh</button>
            </div>
            <div class="admin-inline-add">
              <label class="btn btn-outline btn-sm" style="cursor:pointer; margin:0">
                {{ uploadingImg ? 'Đang tải & tối ưu…' : '📷 Tải ảnh lên (tự nén WebP)' }}
                <input type="file" accept="image/*" class="sr-only" :disabled="uploadingImg" @change="uploadImageFile" />
              </label>
            </div>
          </div>

          <!-- Quản lý quan hệ (chỉ khi sửa) -->
          <div v-if="editingEntity" class="img-mgr">
            <strong class="admin-label">Quan hệ ({{ rels.length }})</strong>
            <div v-for="(r, i) in rels" :key="i" class="img-row">
              <span class="img-url">{{ r.type }} → {{ r.target_name || r.source_name || r.to_id }}</span>
              <button type="button" class="btn-danger btn-sm" @click="removeRel(r)">Xóa</button>
            </div>
            <div class="admin-inline-add">
              <select v-model="newRel.type" class="input" aria-label="Loại quan hệ" style="flex:0 0 130px">
                <option v-for="t in relTypes" :key="t" :value="t">{{ t }}</option>
              </select>
              <input v-model="newRel.to_id" class="input" placeholder="ID entity đích" aria-label="ID entity đích" @keyup.enter="addRel" />
              <button type="button" class="btn btn-secondary btn-sm" :disabled="!newRel.to_id.trim()" @click="addRel">Thêm</button>
            </div>
            <details class="bulk-rel-details">
              <summary class="btn btn-ghost btn-sm">Thêm hàng loạt…</summary>
              <div class="bulk-rel-inner">
                <select v-model="bulkRelType" class="input" aria-label="Loại quan hệ hàng loạt" style="max-width:160px">
                  <option v-for="t in relTypes" :key="t" :value="t">{{ t }}</option>
                </select>
                <textarea v-model="bulkRelIds" class="input" placeholder="Mỗi dòng 1 entity ID đích" rows="3" aria-label="Danh sách entity ID đích"></textarea>
                <button type="button" class="btn btn-secondary btn-sm" :disabled="!bulkRelIds.trim() || bulkRelSaving" @click="addBulkRels">
                  {{ bulkRelSaving ? 'Đang thêm…' : 'Thêm tất cả' }}
                </button>
              </div>
            </details>
          </div>
        </div>

        <div v-if="editingEntity && entityHistory.length" class="ent-history">
          <strong class="admin-label">Lịch sử thay đổi ({{ entityHistory.length }})</strong>
          <div v-for="h in entityHistory" :key="h.id" class="ent-history-item">
            <span class="ent-history-field">{{ h.field }}</span>
            <span class="ent-history-arrow">&rarr;</span>
            <span class="ent-history-val" :title="h.new_value">{{ truncVal(h.new_value) }}</span>
            <span class="ent-history-time">{{ timeAgo(h.created_at) }}</span>
          </div>
        </div>

        <div class="admin-modal-actions">
          <button type="button" class="btn btn-outline" @click="showModal = false">Hủy</button>
          <button type="button" class="btn btn-primary" :disabled="saving" @click="saveEntity">
            {{ saving ? 'Đang lưu…' : (editingEntity ? 'Cập nhật' : 'Tạo') }}
          </button>
        </div>
      </div>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { TYPE_META } from '~/composables/useConstants'
import { ADMIN_KINDS } from '~/utils/adminKinds'
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Quản lý Entity — Admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()
const { timeAgo } = useTimeAgo()

interface EntityForm {
  id: string
  name: string
  type: string
  placeId: string
  summary: string
  images: string[]
  attributes?: Record<string, unknown>
}

interface EntityListResponse {
  entities?: Entity[]
  total?: number
}

interface AdminRelationship {
  from_id: string
  to_id: string
  type: string
  target_name?: string
  source_name?: string
}

interface EntityHistoryRecord {
  id: string | number
  field: string
  new_value?: string
  created_at: string
}

interface EntityImagesResponse {
  images?: string[]
}

const EMPTY_ENTITY_FORM: EntityForm = { id: '', name: '', type: 'experience', placeId: '', summary: '', images: [] }

// ── Content-model registry (per-type typed fields) ──
interface SchemaFieldDef {
  key: string; label: string; widget: string; required?: boolean
  options?: (string | number)[]; help?: string; placeholder?: string
  group?: string; min?: number; max?: number; step?: number
}
interface TypeSchema { type: string; label: string; emoji: string; kind: string; fields: SchemaFieldDef[] }
const entitySchemas = ref<Record<string, TypeSchema>>({})
// typed attribute values bound to the per-type form (separate from bespoke tail)
const typedAttrs = ref<Record<string, unknown>>({})

async function fetchEntitySchema() {
  if (Object.keys(entitySchemas.value).length) return
  try {
    const r = await $fetch<{ types: Record<string, TypeSchema> }>('/admin-api/entity-schema', { headers: authHeaders() })
    entitySchemas.value = r.types || {}
  } catch { /* form falls back to core fields only */ }
}

// ── Phase 2: kind overview (7 owner categories over the 17 raw types) ──
interface KindTypeCount { type: string; label: string; emoji: string; count: number }
interface KindGroup { kind: string; label: string; emoji: string; total: number; types: KindTypeCount[] }
const kindGroups = ref<KindGroup[]>([])
const kindGrandTotal = ref(0)
async function fetchKinds() {
  try {
    const r = await $fetch<{ kinds: KindGroup[]; grand_total: number }>('/admin-api/entity-kinds', { headers: authHeaders() })
    kindGroups.value = (r.kinds || []).filter(k => k.total > 0)
    kindGrandTotal.value = r.grand_total || 0
  } catch { /* overview panel simply hidden */ }
}
function filterByType(t: string) {
  typeFilter.value = t
  page.value = 1
  fetchEntities(true)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// Fields for the current form.type, grouped by their `group` label (preserves order).
const currentSchemaGroups = computed(() => {
  const s = entitySchemas.value[form.value.type]
  if (!s || !s.fields?.length) return [] as { legend: string; fields: SchemaFieldDef[] }[]
  const groups: { legend: string; fields: SchemaFieldDef[] }[] = []
  const byLegend = new Map<string, SchemaFieldDef[]>()
  for (const f of s.fields) {
    const g = f.group || 'Chi tiết'
    if (!byLegend.has(g)) { byLegend.set(g, []); groups.push({ legend: g, fields: byLegend.get(g)! }) }
    byLegend.get(g)!.push(f)
  }
  return groups
})
const currentSchemaKeys = computed(() => (entitySchemas.value[form.value.type]?.fields || []).map(f => f.key))

// Load the schema-defined attribute values off an entity's attributes into typedAttrs.
function initTypedAttrs(attrs?: Record<string, unknown>) {
  const a = attrs || {}
  const next: Record<string, unknown> = {}
  for (const k of currentSchemaKeys.value) {
    if (a[k] !== undefined) next[k] = a[k]
  }
  typedAttrs.value = next
}

// When the admin switches type inside the form, re-seed typed fields from any
// existing values so nothing already entered is lost.
watch(() => form.value.type, () => { initTypedAttrs(typedAttrs.value) })

const types = Object.keys(TYPE_META)
const search = ref('')
const typeFilter = ref('')
const orphansOnly = ref(false)
const page = ref(1)
const limit = 30
const entities = ref<Entity[]>([])
const totalEntities = ref(0)
const showModal = ref(false)
const modalRef = ref<HTMLElement | null>(null)
useModalA11y(showModal, modalRef, { onClose: () => { showModal.value = false } })
const editingEntity = ref<Entity | null>(null)
const placesList = ref<{ id: string; name: string; area?: string }[]>([])
const form = ref<EntityForm>({ ...EMPTY_ENTITY_FORM })
const selected = ref<Set<string>>(new Set())

// GĐ-A: chế độ xem theo nhóm (?kind=) — cột/bộ lọc đặc thù (utils/adminKinds)
const route = useRoute()
const currentKind = computed(() => ADMIN_KINDS.find(k => k.kind === String(route.query.kind || '')) || null)
const kindTypes = computed(() => currentKind.value ? currentKind.value.types : types)
const activeChips = ref<Set<string>>(new Set())
function toggleChip(key: string) {
  const s = new Set(activeChips.value)
  if (s.has(key)) s.delete(key)
  else s.add(key)
  activeChips.value = s
}
const chipFiltered = computed(() => {
  if (!currentKind.value || !activeChips.value.size) return entities.value
  const chips = currentKind.value.chips.filter(c => activeChips.value.has(c.key))
  return entities.value.filter(e => chips.every(c => c.test(e)))
})
watch(() => route.query.kind, () => {
  selected.value = new Set()
  activeChips.value = new Set()
  typeFilter.value = ''
  fetchEntities(true)
})
// GĐ-A: gán trường hàng loạt cho các entity đã chọn (đi qua PUT sẵn có → giữ validate + audit log)
const UNIVERSAL_BULK: { key: string; label: string; widget: 'text' | 'number' | 'select' | 'bool'; options?: string[] }[] = [
  { key: 'address', label: 'Địa chỉ', widget: 'text' },
  { key: 'phone', label: 'Điện thoại', widget: 'text' },
  { key: 'website', label: 'Website', widget: 'text' },
  { key: 'hours', label: 'Giờ mở cửa', widget: 'text' },
  { key: 'price_range', label: 'Khoảng giá', widget: 'text' },
  { key: 'sub_category', label: 'Phân loại', widget: 'text' },
  { key: 'best_time', label: 'Thời điểm đẹp', widget: 'text' },
  { key: 'highlight', label: 'Điểm nhấn', widget: 'text' },
]
const bulkField = ref('')
const bulkValue = ref('')
const bulkAssignBusy = ref(false)
const bulkProgress = ref('')
const bulkFields = computed(() => {
  if (!currentKind.value) return []
  const kindKeys = new Set(currentKind.value.columns.map(c => c.key))
  return [...currentKind.value.columns, ...UNIVERSAL_BULK.filter(u => !kindKeys.has(u.key))]
})
const bulkFieldDef = computed(() => bulkFields.value.find(c => c.key === bulkField.value) || null)
async function applyBulkAssign() {
  const def = bulkFieldDef.value
  if (!def || !selected.value.size || bulkAssignBusy.value) return
  if (selected.value.size > 100) { showToast('Tối đa 100 entity mỗi lần gán', 'error'); return }
  let value: unknown = bulkValue.value
  if (def.widget === 'number') value = bulkValue.value === '' ? '' : Number(bulkValue.value)
  if (def.widget === 'bool') value = bulkValue.value === '' ? '' : bulkValue.value === 'true'
  bulkAssignBusy.value = true
  const ids = [...selected.value]
  const errs: string[] = []
  let done = 0
  for (const id of ids) {
    const e = entities.value.find(x => x.id === id)
    if (!e) continue
    const attrs: Record<string, unknown> = { ...((e as Record<string, any>).attributes || {}) }
    if (value === '' || value === null || value === undefined) delete attrs[def.key]
    else attrs[def.key] = value
    try {
      await $fetch(`/admin-api/entities/${id}`, { method: 'PUT', headers: authHeaders(),
        body: { id: e.id, name: e.name, type: e.type, placeId: e.placeId || '', summary: e.summary || '', attributes: attrs } })
      ;(e as Record<string, any>).attributes = attrs
    } catch { errs.push(e.name) }
    done += 1
    bulkProgress.value = `${done}/${ids.length}`
  }
  bulkAssignBusy.value = false
  bulkProgress.value = ''
  showToast(errs.length
    ? `Gán xong nhưng lỗi ${errs.length}: ${errs.slice(0, 3).join(', ')}${errs.length > 3 ? '…' : ''}`
    : `Đã gán "${def.label}" cho ${ids.length - errs.length} entity`, errs.length ? 'warning' : 'success')
  selected.value = new Set()
  bulkField.value = ''
  bulkValue.value = ''
}

async function onCompletenessEdit(id: string) {
  let e = entities.value.find(x => x.id === id)
  if (!e) {
    try { e = await $fetch<Entity>(`/admin-api/entities/${id}`, { headers: authHeaders() }) } catch { return }
  }
  if (e) openEdit(e)
}
const loading = ref(true)
const acting = ref<string | null>(null)
const saving = ref(false)
const bulkBusy = ref(false)

const sortKey = ref<string>('')
const sortDir = ref<'asc' | 'desc'>('asc')

function toggleSort(key: string) {
  if (sortKey.value === key) {
    if (sortDir.value === 'asc') sortDir.value = 'desc'
    else { sortKey.value = ''; sortDir.value = 'asc' }
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}
function sortArrow(key: string): string {
  if (sortKey.value !== key) return ''
  return sortDir.value === 'asc' ? '▲' : '▼'
}
const sortedEntities = computed(() => {
  if (!sortKey.value) return chipFiltered.value
  const k = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  return [...chipFiltered.value].sort((a, b) => {
    const va = String((a as Record<string, any>)[k] || '').toLowerCase()
    const vb = String((b as Record<string, any>)[k] || '').toLowerCase()
    return va < vb ? -dir : va > vb ? dir : 0
  })
})
// Additive UX state — does not alter save/data path
const loadError = ref(false)
const searching = ref(false)
const fieldErrors = ref<Record<string, string>>({})

// KBYG — Know Before You Go
const AMENITY_OPTIONS: Record<string, { icon: string; label: string }> = {
  wifi: { icon: '📶', label: 'Wi-Fi' },
  wheelchair: { icon: '♿', label: 'Xe lăn' },
  cash_only: { icon: '💵', label: 'Chỉ tiền mặt' },
  pet_friendly: { icon: '🐕', label: 'Thú cưng OK' },
  air_conditioned: { icon: '❄️', label: 'Máy lạnh' },
  kid_friendly: { icon: '👶', label: 'Trẻ em OK' },
  free_entry: { icon: '🆓', label: 'Miễn phí' },
  guided_tour: { icon: '🎙️', label: 'Có hướng dẫn' },
  restroom: { icon: '🚻', label: 'Nhà vệ sinh' },
  photography: { icon: '📸', label: 'Chụp ảnh OK' },
}
const kbygTips = ref('')
const kbygGoldenHours = ref('')
const kbygPeakDays = ref('')
const kbygCrowdLevel = ref('')
const kbygAmenities = ref<string[]>([])
const kbygChecklist = ref('')

function toggleAmenity(key: string) {
  const idx = kbygAmenities.value.indexOf(key)
  if (idx >= 0) kbygAmenities.value.splice(idx, 1)
  else kbygAmenities.value.push(key)
}

function initKbyg(attrs?: Record<string, unknown>) {
  const a = attrs || {}
  kbygTips.value = Array.isArray(a.kbyg_tips) ? (a.kbyg_tips as string[]).join('\n') : ''
  kbygGoldenHours.value = (a.golden_hours as string) || ''
  kbygPeakDays.value = (a.peak_days as string) || ''
  kbygCrowdLevel.value = (a.crowd_level as string) || ''
  kbygAmenities.value = Array.isArray(a.amenity_badges) ? [...a.amenity_badges as string[]] : []
  kbygChecklist.value = Array.isArray(a.checklist) ? (a.checklist as string[]).join('\n') : ''
}

const KBYG_KEYS = ['kbyg_tips', 'golden_hours', 'peak_days', 'crowd_level', 'amenity_badges', 'checklist']
function mergeKbygIntoAttrs(attrs: Record<string, unknown>): Record<string, unknown> {
  const result = { ...attrs }
  const tips = kbygTips.value.split('\n').map(s => s.trim()).filter(Boolean)
  if (tips.length) result.kbyg_tips = tips; else delete result.kbyg_tips
  if (kbygGoldenHours.value.trim()) result.golden_hours = kbygGoldenHours.value.trim(); else delete result.golden_hours
  if (kbygPeakDays.value.trim()) result.peak_days = kbygPeakDays.value.trim(); else delete result.peak_days
  if (kbygCrowdLevel.value) result.crowd_level = kbygCrowdLevel.value; else delete result.crowd_level
  if (kbygAmenities.value.length) result.amenity_badges = [...kbygAmenities.value]; else delete result.amenity_badges
  const checklist = kbygChecklist.value.split('\n').map(s => s.trim()).filter(Boolean)
  if (checklist.length) result.checklist = checklist; else delete result.checklist
  return result
}

// ── Season editor (top-level `season` field: {months, peak}) ──
const MONTH_LABELS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
const seasonMonths = ref<number[]>([])  // months present (in-season, incl. peak)
const seasonPeak = ref<number[]>([])    // subset: peak months
const seasonTouched = ref(false)        // only send `season` if the admin edited it
function initSeason(season?: { months?: number[]; peak?: number[] } | null) {
  seasonMonths.value = Array.isArray(season?.months) ? [...season!.months] : []
  seasonPeak.value = Array.isArray(season?.peak) ? [...season!.peak] : []
  seasonTouched.value = false
}
function monthState(m: number): 'off' | 'in' | 'peak' {
  if (seasonPeak.value.includes(m)) return 'peak'
  if (seasonMonths.value.includes(m)) return 'in'
  return 'off'
}
function cycleMonth(m: number) {
  seasonTouched.value = true
  const st = monthState(m)
  if (st === 'off') { seasonMonths.value = [...seasonMonths.value, m].sort((a, b) => a - b) }
  else if (st === 'in') { seasonPeak.value = [...seasonPeak.value, m].sort((a, b) => a - b) }
  else { seasonMonths.value = seasonMonths.value.filter(x => x !== m); seasonPeak.value = seasonPeak.value.filter(x => x !== m) }
}

// ── Advanced attributes editor (the bespoke tail: keys not in schema, not KBYG) ──
const advancedJson = ref('')
const advancedError = ref('')
function initAdvanced(attrs?: Record<string, unknown>) {
  advancedError.value = ''
  const a = attrs || {}
  const managed = new Set([...currentSchemaKeys.value, ...KBYG_KEYS])
  const tail: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(a)) if (!managed.has(k)) tail[k] = v
  advancedJson.value = Object.keys(tail).length ? JSON.stringify(tail, null, 2) : ''
}

const inlineEdit = ref<{ id: string; field: string; value: string }>({ id: '', field: '', value: '' })

function startInline(e: Entity, field: string, value: string) {
  inlineEdit.value = { id: e.id, field, value }
}

async function saveInline(e: Entity) {
  const { field, value } = inlineEdit.value
  // GĐ-A: inline edit cột attribute đặc thù theo nhóm (field dạng 'attr:<key>')
  if (field.startsWith('attr:')) {
    const key = field.slice(5)
    const def = currentKind.value?.columns.find(c => c.key === key)
    const attrs: Record<string, unknown> = { ...((e as Record<string, any>).attributes || {}) }
    const trimmed = value.trim()
    if (!trimmed) {
      delete attrs[key]
    } else if (def?.widget === 'number') {
      const n = Number(trimmed.replace(',', '.'))
      if (Number.isNaN(n)) { showToast('Giá trị phải là số', 'error'); return }
      attrs[key] = n
    } else {
      attrs[key] = trimmed
    }
    try {
      await $fetch(`/admin-api/entities/${e.id}`, { method: 'PUT', headers: authHeaders(),
        body: { id: e.id, name: e.name, type: e.type, placeId: e.placeId || '', summary: e.summary || '', attributes: attrs } })
      ;(e as Record<string, any>).attributes = attrs
      showToast('Đã cập nhật', 'success')
      inlineEdit.value.id = ''
    } catch (err: unknown) {
      showToast(getErrorDetail(err, 'Lỗi khi cập nhật'), 'error')
    }
    return
  }
  if (!value.trim()) { inlineEdit.value.id = ''; return }
  try {
    const body: Record<string, unknown> = { id: e.id, name: e.name, type: e.type, placeId: e.placeId || '', summary: e.summary || '' }
    body[field] = value.trim()
    await $fetch(`/admin-api/entities/${e.id}`, { method: 'PUT', headers: authHeaders(), body })
    ;(e as Record<string, any>)[field] = value.trim()
    showToast('Đã cập nhật', 'success')
    inlineEdit.value.id = ''
  } catch (err: unknown) {
    showToast(getErrorDetail(err, 'Lỗi khi cập nhật'), 'error')
  }
}

async function toggleBoolAttr(e: Entity, key: string) {
  const attrs: Record<string, unknown> = { ...((e as Record<string, any>).attributes || {}) }
  attrs[key] = !attrs[key]
  try {
    await $fetch(`/admin-api/entities/${e.id}`, { method: 'PUT', headers: authHeaders(),
      body: { id: e.id, name: e.name, type: e.type, placeId: e.placeId || '', summary: e.summary || '', attributes: attrs } })
    ;(e as Record<string, any>).attributes = attrs
    showToast('Đã cập nhật', 'success')
  } catch (err: unknown) {
    showToast(getErrorDetail(err, 'Lỗi khi cập nhật'), 'error')
  }
}

const duplicates = ref<Array<{ id: string; name: string; type: string }>>([])
let dupTimer: ReturnType<typeof setTimeout> | null = null
function checkDuplicate() {
  if (editingEntity.value) return
  if (dupTimer) clearTimeout(dupTimer)
  const name = String(form.value.name || '').trim()
  if (name.length < 3) { duplicates.value = []; return }
  dupTimer = setTimeout(async () => {
    try {
      const res = await $fetch<{ duplicates: typeof duplicates.value }>(`/admin-api/entities/check-duplicate?name=${encodeURIComponent(name)}`, { headers: authHeaders() })
      duplicates.value = res.duplicates || []
    } catch { duplicates.value = [] }
  }, 400)
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null
function debounceFetch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  searching.value = true
  debounceTimer = setTimeout(() => fetchEntities(true), 300)
}
function clearSearch() {
  search.value = ''
  fetchEntities(true)
}
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer); if (dupTimer) clearTimeout(dupTimer) })

async function fetchEntities(reset = false) {
  if (reset) page.value = 1
  loading.value = true
  try {
    const params = new URLSearchParams({ limit: String(limit), offset: String((page.value - 1) * limit) })
    if (search.value) params.set('q', search.value)
    if (typeFilter.value) params.set('type', typeFilter.value)
    else if (currentKind.value) params.set('kind', currentKind.value.kind)
    if (orphansOnly.value) params.set('orphans_only', 'true')
    const res = await $fetch<EntityListResponse | Entity[]>(`/admin-api/entities?${params}`, { headers: authHeaders() })
    entities.value = Array.isArray(res) ? res : (res.entities || [])
    totalEntities.value = Array.isArray(res) ? entities.value.length : (res.total ?? entities.value.length)
    loadError.value = false
  } catch {
    loadError.value = true
    showToast('Không thể tải danh sách entity', 'error')
  }
  loading.value = false
  searching.value = false
}

async function _focusModal() {
  if (!placesList.value.length) {
    try {
      placesList.value = await $fetch<{ id: string; name: string; area?: string }[]>('/admin-api/entities/places', { headers: authHeaders() })
    } catch { /* ignore */ }
  }
  nextTick(() => {
    const el = document.getElementById(editingEntity.value ? 'ent-name' : 'ent-id')
    el?.focus()
  })
}

async function openCreate() {
  await fetchEntitySchema()  // guarantee currentSchemaKeys is populated before partitioning
  editingEntity.value = null
  form.value = { ...EMPTY_ENTITY_FORM }
  if (currentKind.value && !currentKind.value.types.includes(String(form.value.type))) {
    form.value.type = currentKind.value.types[0]
  }
  newImage.value = ''
  fieldErrors.value = {}
  initKbyg()
  initTypedAttrs()
  initSeason()
  initAdvanced()
  showModal.value = true
  _focusModal()
}

async function openEdit(e: Entity) {
  await fetchEntitySchema()  // avoid the schema-load race that could drop typed fields on save
  editingEntity.value = e
  form.value = { id: e.id, name: e.name, type: e.type, placeId: e.placeId || '', summary: e.summary || '',
                 images: Array.isArray(e.images) ? [...e.images] : [] }
  newImage.value = ''
  newRel.value = { to_id: '', type: 'related_to' }
  fieldErrors.value = {}
  initKbyg((e as any).attributes)
  initTypedAttrs((e as any).attributes)
  initSeason((e as any).season)
  initAdvanced((e as any).attributes)
  fetchRels(e.id)
  fetchEntityHistory(e.id)
  showModal.value = true
  _focusModal()
}

async function cloneEntity(e: Entity) {
  await fetchEntitySchema()
  editingEntity.value = null
  form.value = { id: '', name: `${e.name} (bản sao)`, type: e.type, placeId: e.placeId || '', summary: e.summary || '', images: [] }
  newImage.value = ''
  fieldErrors.value = {}
  initKbyg((e as any).attributes)
  initTypedAttrs((e as any).attributes)
  initSeason((e as any).season)
  initAdvanced((e as any).attributes)
  showModal.value = true
  _focusModal()
}

function exportJSON() {
  downloadBlob(new Blob([JSON.stringify(entities.value, null, 2)], { type: 'application/json' }), `entities-${new Date().toISOString().slice(0, 10)}.json`)
}
function exportCSV() {
  const cols = ['id', 'name', 'type', 'placeId', 'summary']
  const esc = (v: string) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const rows = entities.value.map(e => cols.map(c => esc((e as Record<string, any>)[c])).join(','))
  const csv = '﻿' + cols.join(',') + '\n' + rows.join('\n')
  downloadBlob(new Blob([csv], { type: 'text/csv;charset=utf-8' }), `entities-${new Date().toISOString().slice(0, 10)}.csv`)
}

// ── Quản lý quan hệ ──
const relTypes = ['related_to', 'near', 'produced_in', 'located_in', 'associated_with', 'part_of', 'hosts']
const rels = ref<AdminRelationship[]>([])
const newRel = ref<{ to_id: string; type: string }>({ to_id: '', type: 'related_to' })
async function fetchRels(id: string) {
  rels.value = []
  try {
    const r = await $fetch<{ relationships?: AdminRelationship[] }>(`/api/entities/${id}/relationships?limit=100`)
    rels.value = r.relationships || []
  } catch { showToast('Không tải được quan hệ', 'error') }
}
async function addRel() {
  const to = newRel.value.to_id.trim()
  if (!to || !editingEntity.value) return
  try {
    await $fetch('/admin-api/relationships', { method: 'POST', headers: authHeaders(),
      body: { from_id: form.value.id, to_id: to, type: newRel.value.type } })
    newRel.value.to_id = ''
    await fetchRels(form.value.id)
    showToast('Đã thêm quan hệ', 'success')
  } catch (e: unknown) { showToast(getErrorDetail(e, 'Thêm quan hệ lỗi (id đích tồn tại?)'), 'error') }
}
async function removeRel(r: AdminRelationship) {
  if (!await confirmDialog(`Xóa quan hệ "${r.type}" → ${r.target_name || r.to_id}?`, { danger: true })) return
  const params = new URLSearchParams({ from_id: r.from_id, to_id: r.to_id, type: r.type })
  try {
    await $fetch(`/admin-api/relationships?${params}`, { method: 'DELETE', headers: authHeaders() })
    await fetchRels(form.value.id)
  } catch { showToast('Xóa quan hệ lỗi', 'error') }
}

const bulkRelType = ref('related_to')
const bulkRelIds = ref('')
const bulkRelSaving = ref(false)
async function addBulkRels() {
  if (!editingEntity.value || !bulkRelIds.value.trim()) return
  const pairs = bulkRelIds.value.split('\n').map(l => l.trim()).filter(Boolean).map(id => ({ to_id: id, type: bulkRelType.value }))
  if (!pairs.length) return
  bulkRelSaving.value = true
  try {
    const r = await $fetch<{ added: number; errors: any[] }>('/admin-api/relationships/bulk', {
      method: 'POST', headers: authHeaders(),
      body: { from_id: form.value.id, pairs },
    })
    showToast(`Đã thêm ${r.added} quan hệ${r.errors?.length ? `, ${r.errors.length} lỗi` : ''}`, r.errors?.length ? 'warning' : 'success')
    if (!r.errors?.length) bulkRelIds.value = ''
    await fetchRels(form.value.id as string)
  } catch { showToast('Thêm hàng loạt lỗi', 'error') }
  bulkRelSaving.value = false
}

const entityHistory = ref<EntityHistoryRecord[]>([])
async function fetchEntityHistory(id: string) {
  entityHistory.value = []
  try {
    const r = await $fetch<{ history: EntityHistoryRecord[] }>(`/admin-api/entities/${id}/history`, { headers: authHeaders() })
    entityHistory.value = r.history || []
  } catch { /* ignore — table may not exist yet */ }
}
function truncVal(v?: string): string {
  if (!v) return '(trống)'
  return v.length > 60 ? v.slice(0, 57) + '…' : v
}

function clearFieldError(key: string) {
  if (fieldErrors.value[key]) {
    const next = { ...fieldErrors.value }
    delete next[key]
    fieldErrors.value = next
  }
}
function validateForm(): boolean {
  const errs: Record<string, string> = {}
  if (!String(form.value.name || '').trim()) errs.name = 'Tên không được để trống'
  if (!editingEntity.value && !String(form.value.id || '').trim()) errs.id = 'ID không được để trống'
  if (!editingEntity.value && form.value.id && !/^[a-z0-9\-_]+$/.test(String(form.value.id))) errs.id = 'ID chỉ chứa chữ thường, số, dấu gạch'
  if (!form.value.type) errs.type = 'Loại không được để trống'
  fieldErrors.value = errs
  return Object.keys(errs).length === 0
}
async function saveEntity() {
  if (saving.value) return
  if (!validateForm()) {
    showToast(Object.values(fieldErrors.value)[0] || 'Vui lòng kiểm tra biểu mẫu', 'error')
    return
  }
  // Advanced (bespoke-tail) JSON must parse before we touch anything.
  let advancedObj: Record<string, unknown> = {}
  if (advancedJson.value.trim()) {
    try {
      const parsed = JSON.parse(advancedJson.value)
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) throw new Error('not-object')
      advancedObj = parsed
    } catch {
      advancedError.value = 'JSON không hợp lệ — kiểm tra lại dấu ngoặc/nháy.'
      showToast('Thuộc tính nâng cao: JSON không hợp lệ', 'error')
      return
    }
  }
  advancedError.value = ''
  saving.value = true
  try {
    const body: Record<string, any> = { ...form.value }
    const existingAttrs = { ...((editingEntity.value as any)?.attributes || (body.attributes as Record<string, unknown>) || {}) }
    const managed = new Set([...currentSchemaKeys.value, ...KBYG_KEYS])
    // Advanced editor is authoritative for the bespoke tail (non-managed keys):
    // drop existing tail keys, then apply the edited JSON (so removals stick).
    for (const k of Object.keys(existingAttrs)) if (!managed.has(k)) delete existingAttrs[k]
    for (const [k, v] of Object.entries(advancedObj)) if (!managed.has(k)) existingAttrs[k] = v
    // Overlay typed schema fields for the current type. A cleared field
    // (undefined / '' / empty array) is removed.
    for (const k of currentSchemaKeys.value) {
      const v = typedAttrs.value[k]
      const empty = v === undefined || v === '' || (Array.isArray(v) && v.length === 0)
      if (empty) delete existingAttrs[k]
      else existingAttrs[k] = v
    }
    body.attributes = mergeKbygIntoAttrs(existingAttrs)
    // Season (top-level): only send if the admin actually edited it — otherwise
    // omit so the backend preserves the existing value (no empty-season churn,
    // no clobbering legacy shapes). peak ⊆ months guaranteed by the UI.
    if (seasonTouched.value) {
      body.season = { months: [...seasonMonths.value], peak: [...seasonPeak.value] }
    }
    if (editingEntity.value) {
      await $fetch(`/admin-api/entities/${form.value.id}`, { method: 'PUT', headers: authHeaders(), body })
      showToast('Đã cập nhật entity', 'success')
    } else {
      await $fetch('/admin-api/entities', { method: 'POST', headers: authHeaders(), body })
      showToast('Đã tạo entity mới', 'success')
    }
    showModal.value = false
    await fetchEntities()
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Lỗi khi lưu entity'), 'error')
  }
  saving.value = false
}

// ── Quản lý ảnh entity (chỉ khi đang sửa) ──
const newImage = ref('')
const previewSummary = ref(false)
async function addImage() {
  const url = newImage.value.trim()
  if (!url || !editingEntity.value) return
  try {
    const r = await $fetch<EntityImagesResponse>(`/admin-api/entities/${form.value.id}/images`, {
      method: 'POST', headers: authHeaders(), body: { url } })
    form.value.images = r.images || form.value.images
    newImage.value = ''
  } catch (e: unknown) { showToast(getErrorDetail(e, 'Thêm ảnh lỗi'), 'error') }
}
async function removeImage(idx: number) {
  if (!editingEntity.value) return
  if (!await confirmDialog('Xóa ảnh này?', { danger: true })) return
  try {
    const r = await $fetch<EntityImagesResponse>(`/admin-api/entities/${form.value.id}/images/${idx}`, {
      method: 'DELETE', headers: authHeaders() })
    form.value.images = r.images ?? form.value.images.filter((_: unknown, i: number) => i !== idx)
  } catch { showToast('Xóa ảnh lỗi', 'error') }
}
const uploadingImg = ref(false)
async function uploadImageFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !editingEntity.value) { return }
  uploadingImg.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const r = await $fetch<Record<string, any>>(`/admin-api/entities/${form.value.id}/images/upload`, {
      method: 'POST', headers: authHeaders(), body: fd })
    form.value.images = (r.images as string[]) || form.value.images
    showToast('Đã tải & tối ưu ảnh', 'success')
    input.value = ''
  } catch (err: unknown) { showToast(getErrorDetail(err, 'Tải ảnh lỗi'), 'error') }
  uploadingImg.value = false
}

// ── Thao tác hàng loạt ──
function toggleSel(id: string) {
  const s = new Set(selected.value)
  s.has(id) ? s.delete(id) : s.add(id)
  selected.value = s
}
const allSelected = computed(() => entities.value.length > 0 && entities.value.every(e => selected.value.has(e.id)))
function toggleAll() {
  selected.value = allSelected.value ? new Set() : new Set(entities.value.map(e => e.id))
}
async function bulkDelete() {
  if (bulkBusy.value) return
  const ids = [...selected.value]
  if (!ids.length || !await confirmDialog(`Xóa ${ids.length} entity đã chọn?`, { danger: true })) return
  bulkBusy.value = true
  try {
    const r = await $fetch<Record<string, unknown>>('/admin-api/entities/bulk-delete', { method: 'POST', headers: authHeaders(), body: ids })
    const deleted = Number(r.count) || 0
    showToast(`Đã xóa ${deleted}/${ids.length} entity`, deleted === ids.length ? 'success' : 'warning')
    selected.value = new Set()
    await fetchEntities()
  } catch (e: unknown) { showToast(getErrorDetail(e, 'Xóa hàng loạt lỗi'), 'error') }
  bulkBusy.value = false
}
async function deleteEntity(id: string) {
  if (acting.value) return
  if (!await confirmDialog(`Xóa entity "${id}"?`, { danger: true })) return
  acting.value = id
  try {
    await $fetch(`/admin-api/entities/${id}`, { method: 'DELETE', headers: authHeaders() })
    showToast('Đã xóa entity', 'success')
    acting.value = null
    await fetchEntities()
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Lỗi khi xóa entity'), 'error')
    acting.value = null
  }
}

// Esc clears bulk selection (only when modal is closed) — additive
function onKeydown(ev: KeyboardEvent) {
  if (ev.key === 'Escape' && !showModal.value && selected.value.size) {
    selected.value = new Set()
  }
}
onMounted(() => {
  const route = useRoute()
  if (route.query.orphans === '1') orphansOnly.value = true
  if (typeof route.query.q === 'string' && route.query.q) search.value = route.query.q
  fetchEntitySchema()
  fetchKinds()
  fetchEntities()
  if (route.query.create === '1') openCreate()
  window.addEventListener('keydown', onKeydown)
})
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.ent-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }
.refresh-spin { display: inline-block; animation: admin-spin .6s linear infinite; }

/* ── Entity name cell with thumbnail ── */
.ent-name-cell { display: flex; align-items: center; gap: var(--space-3); }
.ent-thumb {
  width: 32px; height: 32px; border-radius: 8px; overflow: hidden; flex-shrink: 0;
  background: var(--bg-alt);
  transition: transform .25s var(--ease-soft), box-shadow .25s;
}
.ent-name-cell:hover .ent-thumb { transform: scale(1.08); box-shadow: 0 2px 8px rgba(0,0,0,.1); }
.ent-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ent-thumb-empty {
  display: flex; align-items: center; justify-content: center;
  font-size: .85rem; opacity: .3;
}

/* ── Type badges ── */
.type-badge {
  display: inline-block; padding: 2px 10px; border-radius: 100px;
  font-size: .72rem; font-weight: 600; letter-spacing: .3px;
  text-transform: uppercase;
}
.type-badge[data-type="attraction"] { background: rgba(var(--primary-rgb),.1); color: var(--success); }
.type-badge[data-type="dish"] { background: rgba(var(--warning-rgb),.1); color: var(--warning); }
.type-badge[data-type="product"] { background: rgba(var(--blue-rgb),.1); color: rgb(var(--blue-rgb)); }
.type-badge[data-type="accommodation"] { background: rgba(var(--purple-rgb),.1); color: rgb(var(--purple-rgb)); }
.type-badge[data-type="nature"] { background: rgba(52,199,89,.1); color: rgb(52,199,89); }
.type-badge[data-type="experience"] { background: rgba(var(--warning-rgb),.1); color: var(--warning); }
.type-badge[data-type="craft_village"] { background: rgba(162,132,94,.1); color: rgb(162,132,94); }
.type-badge[data-type="event"] { background: rgba(var(--danger-rgb),.1); color: var(--error); }
.type-badge[data-type="drink"] { background: rgba(var(--teal-rgb),.1); color: rgb(var(--teal-rgb)); }
.type-badge[data-type="place"] { background: rgba(142,142,147,.1); color: var(--muted); }
.dark .type-badge[data-type="accommodation"] { background: rgba(var(--purple-rgb),.15); color: #C084FC; }
.dark .type-badge[data-type="nature"] { background: rgba(52,199,89,.15); color: #66BB6A; }
.dark .type-badge[data-type="craft_village"] { background: rgba(162,132,94,.15); color: #D4A574; }
.dark .type-badge[data-type="drink"] { background: rgba(var(--teal-rgb),.15); color: #5CE5DD; }

/* ── Selected row ── */
.row-selected td { background: rgba(var(--blue-rgb),.04); transition: background .2s; }

/* ── Empty state ── */
.ent-empty { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.ent-empty-icon { font-size: 2rem; opacity: .3; }

/* ── Bulk bar ── */
.bulk-bar {
  display: flex; align-items: center; gap: var(--space-3); margin: var(--space-3) 0;
  padding: var(--space-3) var(--space-4);
  background: rgba(var(--blue-rgb),.06); border: .5px solid rgba(var(--blue-rgb),.2);
  border-radius: 10px; font-size: .88rem; font-weight: 500;
  animation: bulk-slide-in .3s var(--ease-soft);
}
@keyframes bulk-slide-in { from { opacity: 0; transform: translateY(-8px); } }

/* ── Image manager ── */
.img-mgr { border-top: .5px solid var(--line); padding-top: var(--space-3); margin-top: var(--space-1); }
.img-row { display: flex; align-items: center; gap: var(--space-2); margin: var(--space-2) 0; }
.img-thumb { width: 40px; height: 40px; object-fit: cover; border-radius: 6px; flex: 0 0 40px; border: .5px solid var(--line); transition: transform .2s var(--ease-out, ease); }
.img-row:hover .img-thumb { transform: scale(var(--img-hover-scale)); }
.img-url { flex: 1; font-size: .78rem; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── Search box (clear + searching feedback) ── */
.btn-active-warn { background: rgba(var(--warning-rgb),.12) !important; border-color: var(--warning) !important; color: var(--warning) !important; font-weight: 600; }
.ent-search-wrap { position: relative; display: flex; align-items: center; flex: 1 1 220px; min-width: 180px; }
.ent-search-wrap .input { width: 100%; padding-right: 32px; }
.ent-search-clear {
  position: absolute; right: 6px; top: 50%; transform: translateY(-50%);
  width: 22px; height: 22px; border: none; background: transparent;
  font-size: 1.1rem; line-height: 1; color: var(--muted); cursor: pointer;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
}
.ent-search-clear:hover { background: var(--bg-alt); color: var(--ink); }
.ent-search-clear:focus-visible { outline: 2px solid var(--primary); outline-offset: 1px; }
.ent-searching {
  position: absolute; left: 0; top: calc(100% + 2px);
  font-size: .72rem; color: var(--muted); opacity: .8;
  animation: ent-fade-in .2s var(--ease-out, ease);
}
@keyframes ent-fade-in { from { opacity: 0; } }

/* ── Error banner ── */
.ent-error-banner {
  display: flex; align-items: center; gap: var(--space-3);
  margin: var(--space-3) 0; padding: var(--space-3) var(--space-4);
  background: var(--error-bg); border: .5px solid var(--error);
  border-radius: 10px; font-size: .88rem; color: var(--error);
}

/* ── Skeleton loading rows ── */
.ent-skeleton { display: flex; flex-direction: column; gap: var(--space-3); width: 100%; padding: var(--space-2) 0; }
.ent-skel-row { display: flex; align-items: center; gap: var(--space-4); }
.ent-skel-check { width: 18px; height: 18px; border-radius: 4px; flex: 0 0 18px; }
.skeleton-text.ent-skel-id { width: 64px; margin: 0; }
.skeleton-text.ent-skel-name { flex: 1; max-width: 320px; margin: 0; }
.skeleton-text.ent-skel-type { width: 90px; margin: 0; }

/* ── Acting (deleting) row overlay ── */
.row-acting td { opacity: .5; pointer-events: none; transition: opacity .2s; }

/* ── Modal form fields (labels + spacing) ── */
.admin-form-col { gap: var(--space-4); }
.ent-field { display: flex; flex-direction: column; gap: var(--space-1); }
.ent-field .form-error { margin-top: 2px; }
.ent-fieldset { border: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-4); }
.ent-fieldset-legend { font-weight: 600; font-size: .88rem; color: var(--ink); padding: 0; margin-bottom: var(--space-1); }
.ent-typed-fieldset { border: 1px solid var(--line); border-radius: 10px; padding: var(--space-3); margin-top: var(--space-3); background: var(--bg-alt); }
.ent-typed-fieldset .ent-fieldset-legend { padding: 0 var(--space-2); }
.ent-typed-hint { font-weight: 400; color: var(--muted); font-size: .78rem; }
.ent-typed-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--space-3); }

/* Phase 2: kind overview panel */
.ent-kinds-panel { border: 1px solid var(--line); border-radius: 10px; margin-bottom: var(--space-4); background: var(--card); }
.ent-kinds-summary { cursor: pointer; padding: var(--space-3); font-weight: 600; font-size: .9rem; display: flex; align-items: center; gap: var(--space-2); list-style: none; }
.ent-kinds-summary::-webkit-details-marker { display: none; }
.ent-kinds-summary::before { content: '▸'; transition: transform .15s; color: var(--muted); }
.ent-kinds-panel[open] .ent-kinds-summary::before { transform: rotate(90deg); }
.ent-kinds-total { margin-left: auto; font-weight: 400; color: var(--muted); font-size: .8rem; }
.ent-kinds-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-3); padding: 0 var(--space-3) var(--space-3); }
.ent-kind-card { border: 1px solid var(--line); border-radius: 8px; padding: var(--space-2) var(--space-3); background: var(--bg-alt); }
.ent-kind-head { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.ent-kind-emoji { font-size: 1.1rem; }
.ent-kind-label { font-weight: 600; font-size: .85rem; }
.ent-kind-count { margin-left: auto; font-weight: 700; color: var(--primary); font-size: .9rem; }
.ent-kind-types { display: flex; flex-wrap: wrap; gap: 4px; }
.ent-kind-chip { border: 1px solid var(--line); background: var(--card); border-radius: 100px; padding: 2px 8px; font-size: .74rem; cursor: pointer; color: var(--ink-700); transition: background .12s, border-color .12s, color .12s; }
.ent-kind-chip:hover { border-color: var(--primary); color: var(--ink); }
.ent-kind-chip.active { background: var(--primary); color: #fff; border-color: var(--primary); }
.ent-kind-chip-n { opacity: .7; font-weight: 600; }

/* GĐ-A: chip lọc nhanh theo nhóm + ô cột đặc thù */
.ent-chip-row { display: flex; flex-wrap: wrap; gap: var(--space-2); margin: var(--space-3) 0; align-items: center; }
.ent-chip-note { font-size: .8rem; color: var(--ink-700); }
.ent-kind-cell { font-size: .85rem; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ent-bool-toggle { background: none; border: 1px solid var(--line); border-radius: 6px; padding: 2px 10px; cursor: pointer; font-size: .85rem; color: var(--ink); }
.ent-bool-toggle:hover { border-color: var(--primary); }
.bulk-assign-field, .bulk-assign-value { max-width: 170px; font-size: .84rem; padding: 4px 8px; }

/* Phase 1c: season editor + advanced JSON */
.ent-season-hint { margin: 0 0 var(--space-2); }
.ent-season-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 4px; }
.ent-season-cell { padding: 6px 0; border: 1px solid var(--line); border-radius: 6px; background: var(--card); font-size: .78rem; font-weight: 600; cursor: pointer; color: var(--ink-700); transition: background .12s, color .12s, border-color .12s; }
.ent-season-cell.ent-season-in { background: color-mix(in srgb, var(--primary) 22%, var(--card)); color: var(--ink); border-color: var(--primary); }
.ent-season-cell.ent-season-peak { background: var(--primary); color: #fff; border-color: var(--primary); }
.ent-season-legend { display: flex; gap: var(--space-4); margin-top: var(--space-2); font-size: .76rem; color: var(--ink-700); }
.ent-season-legend span { display: inline-flex; align-items: center; gap: 4px; }
.ent-season-swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
.ent-season-swatch.ent-season-in { background: color-mix(in srgb, var(--primary) 22%, var(--card)); border: 1px solid var(--primary); }
.ent-season-swatch.ent-season-peak { background: var(--primary); }
.ent-advanced-json { font-family: ui-monospace, 'SF Mono', Menlo, monospace; font-size: .8rem; }

/* ── Row action buttons: consistent sizing + 44px touch + focus ── */
.admin-actions { display: flex; gap: var(--space-1); align-items: center; }
.admin-actions button { min-height: 44px; }
.admin-actions button:focus-visible { outline: 2px solid var(--primary); outline-offset: 1px; }
@media (max-width: 768px) {
  .admin-actions button { min-height: 44px; }
}

/* ── Pagination hint ── */
.ent-page-hint { color: var(--muted); font-weight: 400; }
.admin-pagination button { min-height: 44px; }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .ent-name-cell:hover .ent-thumb { transform: none; }
  .img-row:hover .img-thumb { transform: none; }
  .bulk-bar { animation: none; }
  .ent-searching { animation: none; }
}

/* ── Dark mode ── */
.dark .type-badge[data-type="attraction"] { background: rgba(var(--primary-rgb),.15); }
.dark .type-badge[data-type="dish"] { background: rgba(var(--warning-rgb),.15); color: var(--warning); }
.dark .type-badge[data-type="product"] { background: rgba(var(--blue-rgb),.15); }
.dark .type-badge[data-type="accommodation"] { background: rgba(var(--purple-rgb),.15); }
.dark .type-badge[data-type="nature"] { background: rgba(52,199,89,.15); }
.dark .type-badge[data-type="experience"] { background: rgba(var(--warning-rgb),.15); color: var(--accent-text); }
.dark .type-badge[data-type="craft_village"] { background: rgba(162,132,94,.15); }
.dark .type-badge[data-type="event"] { background: rgba(var(--danger-rgb),.15); color: rgb(var(--danger-rgb)); }
.dark .type-badge[data-type="drink"] { background: rgba(var(--teal-rgb),.15); }
.dark .type-badge[data-type="place"] { background: rgba(142,142,147,.18); color: var(--muted); }
.dark .ent-name-cell:hover .ent-thumb { box-shadow: 0 2px 8px rgba(0,0,0,.3); }
.dark .row-selected td { background: rgba(var(--blue-rgb),.08); }
.dark .bulk-bar { background: rgba(var(--blue-rgb),.08); border-color: rgba(var(--blue-rgb),.15); }
.dark .img-thumb { border-color: rgba(255,255,255,.1); }
.dark .ent-search-clear:hover { background: rgba(255,255,255,.08); color: var(--ink); }
.dark .admin-actions button:focus-visible,
.dark .ent-search-clear:focus-visible { outline-color: var(--primary-fg, #D98A6F); }
/* ── Bulk relationship add ── */
.bulk-rel-details { margin-top: var(--space-2); }
.bulk-rel-details summary { cursor: pointer; font-size: .82rem; }
.bulk-rel-inner { display: flex; flex-direction: column; gap: var(--space-2); margin-top: var(--space-2); }

/* ── Entity change history ── */
.ent-history { border-top: .5px solid var(--line); padding-top: var(--space-3); margin-top: var(--space-3); }
.ent-history-item {
  display: flex; align-items: baseline; gap: var(--space-2);
  padding: var(--space-1) 0; font-size: .82rem;
  border-bottom: .5px solid var(--line);
}
.ent-history-item:last-child { border-bottom: none; }
.ent-history-field { font-weight: 600; color: var(--ink); min-width: 70px; }
.ent-history-arrow { color: var(--muted); flex-shrink: 0; }
.ent-history-val { color: var(--primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }
.ent-history-time { color: var(--muted); font-size: .75rem; margin-left: auto; white-space: nowrap; }

/* ── Inline edit ── */
.ent-inline-label { cursor: default; }
.ent-inline-label:hover { outline: 1px dashed var(--line); outline-offset: 2px; border-radius: 4px; }
.ent-inline-input { max-width: 200px; padding: 3px 6px; font-size: .85rem; font-weight: 600; }
.ent-inline-select { max-width: 140px; padding: 3px 6px; font-size: .78rem; }

/* ── Duplicate warning ── */
.ent-dup-warn {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  padding: var(--space-2) var(--space-3); border-radius: 8px; font-size: .82rem;
  background: rgba(var(--warning-rgb),.1); border: .5px solid rgba(var(--warning-rgb),.3);
  color: var(--warning); animation: ent-fade-in .2s ease;
}
.ent-dup-warn strong { white-space: nowrap; }
.ent-dup-item { background: rgba(var(--warning-rgb),.12); padding: 2px 8px; border-radius: 100px; font-weight: 500; }
.ent-dup-type { font-weight: 400; font-size: .72rem; opacity: .7; }
.dark .ent-dup-warn { background: rgba(var(--warning-rgb),.08); border-color: rgba(var(--warning-rgb),.2); color: var(--accent-text); }

/* ── Sortable columns ── */
.ent-sortable { white-space: nowrap; }
.ent-sort-btn { background: none; border: none; padding: 0; font: inherit; color: inherit; cursor: pointer; user-select: none; }
.ent-sort-btn:hover { color: var(--primary, #219653); }
.ent-sort-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; border-radius: var(--radius-xs, 4px); }
.ent-sort-arrow { font-size: .65rem; opacity: .7; margin-left: 2px; }

.ent-char-count { font-weight: 400; font-size: .78rem; color: var(--muted); transition: color .2s; }
.ent-char-warn { color: var(--warning); font-weight: 600; }
.ent-char-danger { color: var(--error); font-weight: 600; }
.ent-summary-preview { padding: .5rem .8rem; border: 1px solid var(--line); border-radius: 6px; min-height: 60px; font-size: .9rem; line-height: 1.6; white-space: pre-wrap; }

/* ── Health indicator dots ── */
.ent-health-cell { white-space: nowrap; }
.ent-dot {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; border-radius: 50%;
  margin-right: 2px; vertical-align: middle; transition: transform .15s, box-shadow .15s;
  font-size: 9px; line-height: 1; color: var(--text-on-dark);
}
.ent-health-cell:hover .ent-dot { transform: scale(1.4); }
.ent-health-cell:hover .dot-miss { box-shadow: 0 0 0 3px rgba(255,59,48,.15); }
.dot-ok { background: var(--success); }
.dot-miss { background: var(--error); opacity: .45; }

/* ── KBYG fields ── */
.ent-kbyg-details { margin-top: var(--space-3); border: 1px solid var(--line); border-radius: 8px; }
.ent-kbyg-summary { cursor: pointer; padding: 10px 14px; font-weight: 600; user-select: none; }
.ent-kbyg-summary:hover { background: rgba(0,0,0,.03); }
.ent-kbyg-fields { padding: 0 14px 14px; display: flex; flex-direction: column; gap: var(--space-3); }
.kbyg-amenity-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 6px; }
.kbyg-amenity-check { display: flex; align-items: center; gap: 5px; font-size: .82rem; cursor: pointer; padding: var(--space-1) 6px; border-radius: 6px; }
.kbyg-amenity-check:hover { background: rgba(0,0,0,.04); }
.kbyg-amenity-check input[type="checkbox"] { accent-color: var(--primary); }
.dark .ent-kbyg-summary:hover { background: rgba(255,255,255,.05); }
.dark .kbyg-amenity-check:hover { background: rgba(255,255,255,.06); }
</style>

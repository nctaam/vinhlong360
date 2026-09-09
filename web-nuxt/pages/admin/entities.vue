<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1><IconLine v-if="currentKind" :name="currentKind.icon" aria-hidden="true" /> {{ currentKind ? currentKind.label : 'Quản lý Entities' }}</h1>
        <p class="ent-subtitle">{{ entities.length ? `${entities.length} kết quả` : '' }}</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchEntities()">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
      </button>
    </div>

    <div class="admin-toolbar">
      <div class="ent-search-wrap">
        <input v-model="search" class="input" placeholder="Tìm entity…" aria-label="Tìm entity" @input="debounceFetch" @keyup.escape="clearSearch" />
        <button v-if="search" type="button" class="ent-search-clear" aria-label="Xóa tìm kiếm" @click="clearSearch"><IconLine name="x" /></button>
        <span v-if="searching" class="ent-searching" aria-live="polite">Đang tìm…</span>
      </div>
      <select v-model="typeFilter" class="input admin-select-filter" aria-label="Lọc theo loại entity" @change="fetchEntities(true)">
        <option value="">{{ currentKind ? `Cả nhóm ${currentKind.label}` : 'Tất cả loại' }}</option>
        <option v-for="t in kindTypes" :key="t" :value="t">{{ TYPE_META[t]?.emoji || '' }} {{ TYPE_META[t]?.label || t }}</option>
      </select>
      <button type="button" class="btn btn-outline btn-sm" :class="{ 'btn-active-warn': orphansOnly }" @click="orphansOnly = !orphansOnly; fetchEntities(true)">
        <IconLine v-if="orphansOnly" name="check" /> Mồ côi
      </button>
      <button type="button" class="btn btn-primary" @click="openCreate">+ Tạo mới</button>
      <button type="button" class="btn btn-outline btn-sm" :title="`Tải JSON (${entities.length} entity trang này)`" @click="exportJSON">&#x2B73; JSON ({{ entities.length }})</button>
      <button type="button" class="btn btn-outline btn-sm" :title="`Tải CSV (${entities.length} entity trang này)`" @click="exportCSV">&#x2B73; CSV ({{ entities.length }})</button>
    </div>

    <!-- Phase 2: tổng quan theo danh mục (7 nhóm chủ trên 17 type) -->
    <AdminEntityKindOverview
      :kind-groups="kindGroups"
      :kind-grand-total="kindGrandTotal"
      :type-filter="typeFilter"
      @filter="filterByType"
    />

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
      <div class="admin-table-wrap" role="region" tabindex="0" aria-label="Bảng danh sách entity">
      <table class="admin-table" aria-label="Danh sách entity">
        <thead>
          <tr>
            <th scope="col" class="admin-th-check"><input type="checkbox" :checked="allSelected" @change="toggleAll" aria-label="Chọn tất cả" /></th>
            <th scope="col" class="ent-sortable" :aria-sort="sortKey === 'id' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'"><button type="button" class="ent-sort-btn" @click="toggleSort('id')">ID <span class="ent-sort-arrow" aria-hidden="true"><IconLine v-if="sortIcon('id')" :name="sortIcon('id')" /></span></button></th>
            <th scope="col" class="ent-sortable" :aria-sort="sortKey === 'name' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'"><button type="button" class="ent-sort-btn" @click="toggleSort('name')">Tên <span class="ent-sort-arrow" aria-hidden="true"><IconLine v-if="sortIcon('name')" :name="sortIcon('name')" /></span></button></th>
            <th scope="col" class="ent-sortable" :aria-sort="sortKey === 'type' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'"><button type="button" class="ent-sort-btn" @click="toggleSort('type')">Loại <span class="ent-sort-arrow" aria-hidden="true"><IconLine v-if="sortIcon('type')" :name="sortIcon('type')" /></span></button></th>
            <th scope="col" class="ent-sortable" :aria-sort="sortKey === 'place_name' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'"><button type="button" class="ent-sort-btn" @click="toggleSort('place_name')">Địa điểm <span class="ent-sort-arrow" aria-hidden="true"><IconLine v-if="sortIcon('place_name')" :name="sortIcon('place_name')" /></span></button></th>
            <th scope="col">Place ID</th>
            <th v-for="c in currentKind?.columns || []" :key="c.key" scope="col">{{ c.label }}</th>
            <th scope="col"><span title="Tóm tắt / Ảnh / Địa điểm">Chất lượng</span><span class="admin-help" data-tip="● xanh = có, ● đỏ = thiếu. Thứ tự: Tóm tắt · Ảnh · Địa điểm" tabindex="0" role="img" aria-label="Giải thích chất lượng">?</span></th>
            <th scope="col">Thao tác</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="{ entity: e, descriptor: tableImage, imageCount, disclosureId } in entityTableRows" :key="e.id" :class="{ 'row-selected': selected.has(e.id), 'row-acting': acting === e.id }">
            <td><input type="checkbox" :checked="selected.has(e.id)" @change="toggleSel(e.id)" :aria-label="`Chọn ${e.name}`" /></td>
            <td class="admin-td-id">{{ e.id }}</td>
            <td>
              <div class="ent-name-cell">
                <div class="ent-thumb-stack" data-admin-entity-thumbnail>
                  <div class="ent-thumb" :class="{ 'ent-thumb-empty': !tableImage.url }">
                    <img
                      v-if="tableImage.url"
                      :src="tableImage.url"
                      :alt="tableImage.alt"
                      :aria-describedby="disclosureId"
                      width="32"
                      height="32"
                      loading="lazy"
                      decoding="async"
                      @error="(ev) => ((ev.target as HTMLImageElement).style.display = 'none')"
                    />
                    <span v-else aria-hidden="true">&#x1F4F7;</span>
                  </div>
                  <ImageDisclosure
                    :id="disclosureId"
                    :descriptor="tableImage"
                    presentation="short"
                  />
                </div>
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
            <td>
              <template v-if="inlineEdit.id === e.id && inlineEdit.field === 'placeId'">
                <input v-model="inlineEdit.value" class="input ent-inline-input" :aria-label="`Sửa Place ID cho ${e.name}`" list="ent-places-list" @keyup.enter="saveInline(e)" @keyup.escape="inlineEdit.id = ''" @vue:mounted="(vn: any) => vn.el?.focus()" />
              </template>
              <span v-else class="ent-inline-label" :title="`Nhấp đúp để sửa Place ID`" @dblclick="startInline(e, 'placeId', e.placeId || '')">{{ e.placeId || '—' }}</span>
            </td>
            <td v-for="c in currentKind?.columns || []" :key="c.key" class="ent-kind-cell">
              <button v-if="c.widget === 'bool'" type="button" class="ent-bool-toggle"
                :aria-label="`Bật/tắt ${c.label} cho ${e.name}`" @click="toggleBoolAttr(e, c.key)">
                <IconLine v-if="((e as any).attributes || {})[c.key]" name="check" />
                <template v-else>—</template>
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
              <span class="ent-dot" :class="e.summary ? 'dot-ok' : 'dot-miss'" :title="e.summary ? 'Có tóm tắt' : 'Thiếu tóm tắt'" :aria-label="e.summary ? 'Có tóm tắt' : 'Thiếu tóm tắt'" role="img"><IconLine :name="e.summary ? 'check' : 'x'" /></span>
              <span class="ent-dot" :class="imageCount ? 'dot-ok' : 'dot-miss'" :title="imageCount ? `${imageCount} ảnh` : 'Thiếu ảnh'" :aria-label="imageCount ? `${imageCount} ảnh` : 'Thiếu ảnh'" role="img"><IconLine :name="imageCount ? 'check' : 'x'" /></span>
              <span class="ent-dot" :class="e.placeId ? 'dot-ok' : 'dot-miss'" :title="e.placeId ? 'Có địa điểm' : 'Thiếu địa điểm'" :aria-label="e.placeId ? 'Có địa điểm' : 'Thiếu địa điểm'" role="img"><IconLine :name="e.placeId ? 'check' : 'x'" /></span>
            </td>
            <td class="admin-actions">
              <button type="button" class="btn-success" @click="openEdit(e)" :aria-label="`Sửa ${e.name}`">Sửa</button>
              <button type="button" @click="cloneEntity(e)" title="Nhân bản" :aria-label="`Nhân bản ${e.name}`">&#128203;</button>
              <button type="button" class="btn-danger" :disabled="acting === e.id" @click="deleteEntity(e.id)" :aria-label="`Xóa ${e.name}`">Xóa</button>
            </td>
          </tr>
          <AdminEntityTableEmpty
            :has-entities="!!sortedEntities.length"
            :colspan="8 + (currentKind?.columns.length || 0)"
            :search="search"
            @clear-search="clearSearch"
            @open-create="openCreate"
          />
        </tbody>
      </table>
      </div>

      <nav v-if="entities.length || page > 1" class="admin-pagination" role="navigation" aria-label="Phân trang">
        <button type="button" :disabled="page <= 1" @click="page--; fetchEntities()"><IconLine name="arrow-left" /> Trước</button>
        <span class="admin-page-info">
          Trang {{ page }}<span v-if="totalEntities" class="ent-page-hint"> · {{ totalEntities }} entity</span><span v-if="entities.length < limit" class="ent-page-hint"> · trang cuối</span>
        </span>
        <button type="button" :disabled="entities.length < limit" @click="page++; fetchEntities()">Sau <IconLine name="arrow-right" /></button>
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
            <div v-else class="ent-summary-preview" v-html="mdLite(form.summary)"></div>
            <button type="button" class="btn btn-ghost btn-sm" :aria-expanded="previewSummary" @click="previewSummary = !previewSummary">{{ previewSummary ? 'Sửa' : 'Xem trước' }}</button>
          </div>
          </fieldset>

          <!-- Trường theo loại (content-model registry) -->
          <fieldset v-for="grp in currentSchemaGroups" :key="grp.legend" class="ent-fieldset ent-typed-fieldset">
            <legend class="ent-fieldset-legend">
              <IconLine :name="typeIcon(form.type)" aria-hidden="true" /> {{ grp.legend }}
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
          <AdminEntitySeasonEditor
            :season-months="seasonMonths"
            :season-peak="seasonPeak"
            :month-labels="MONTH_LABELS"
            :month-state="monthState"
            :cycle-month="cycleMonth"
          />

          <!-- KBYG — Know Before You Go -->
          <AdminEntityKbygEditor
            v-model:tips="kbygTips"
            v-model:golden-hours="kbygGoldenHours"
            v-model:peak-days="kbygPeakDays"
            v-model:crowd-level="kbygCrowdLevel"
            :amenities="kbygAmenities"
            v-model:checklist="kbygChecklist"
            :amenity-options="AMENITY_OPTIONS"
            @toggle-amenity="toggleAmenity"
          />

          <!-- Thuộc tính nâng cao (bespoke tail — không có trong schema/KBYG) -->
          <AdminEntityAdvancedJson
            v-model="advancedJson"
            :error="advancedError"
            @clear-error="advancedError = ''"
          />

          <!-- Quản lý ảnh (chỉ khi sửa) -->
          <div v-if="editingEntity" class="img-mgr" data-expanded-preview data-admin-entity-image-editor>
            <strong class="admin-label">Ảnh ({{ (form.images || []).length }}/10)</strong>
            <p class="sf-help" data-entity-image-policy>Chỉ dùng ảnh minh họa AI cho nội dung biên tập entity. Không dùng ảnh đánh giá, ảnh bài đăng hoặc ảnh người dùng.</p>
            <div v-if="!editorImageRows.length" class="img-row img-row-placeholder">
              <span class="img-thumb ent-thumb-empty" aria-hidden="true">&#x1F4F7;</span>
              <ImageDisclosure :descriptor="editorPlaceholder" presentation="full" />
            </div>
            <div v-for="row in editorImageRows" :key="row.index" class="img-row" data-admin-entity-image-row>
              <template v-if="row.descriptor?.url">
                <img
                  :src="row.descriptor.url"
                  :alt="row.descriptor.alt"
                  :aria-describedby="editorDisclosureId(row.index)"
                  class="img-thumb"
                  width="48"
                  height="48"
                  loading="lazy"
                  decoding="async"
                  @error="(event) => ((event.target as HTMLImageElement).style.opacity = '.3')"
                />
                <span class="img-details">
                  <span class="img-url">{{ row.descriptor.url }}</span>
                  <ImageDisclosure :id="editorDisclosureId(row.index)" :descriptor="row.descriptor" presentation="full" />
                </span>
              </template>
              <pre v-else class="img-invalid-value">{{ formatAdminImageValue(row.raw) }}</pre>
              <button type="button" class="btn-danger btn-sm" @click="removeImage(row.index)">Xóa</button>
            </div>
            <div class="admin-inline-add">
              <input v-model="newImage" class="input" placeholder="https://… (chỉ ảnh minh họa AI biên tập)" aria-label="URL ảnh AI biên tập mới" @keyup.enter="addImage" />
              <button type="button" class="btn btn-secondary btn-sm" :disabled="!newImage.trim()" @click="addImage">Thêm ảnh</button>
            </div>
            <div class="admin-inline-add">
              <label class="btn btn-outline btn-sm" style="cursor:pointer; margin:0">
                <template v-if="uploadingImg">Đang tải &amp; tối ưu…</template>
                <template v-else><IconLine name="camera" /> Tải ảnh AI biên tập (tự nén WebP)</template>
                <input type="file" accept="image/*" class="sr-only" :disabled="uploadingImg" @change="uploadImageFile" aria-label="Tải ảnh AI biên tập (tự nén WebP)" />
              </label>
            </div>
          </div>

          <!-- Quản lý quan hệ (chỉ khi sửa) -->
          <AdminEntityRelationshipsEditor
            v-if="editingEntity"
            :rels="rels"
            :rel-types="relTypes"
            :new-rel="newRel"
            v-model:bulk-rel-type="bulkRelType"
            v-model:bulk-rel-ids="bulkRelIds"
            :bulk-rel-saving="bulkRelSaving"
            @add-rel="addRel"
            @remove-rel="removeRel"
            @add-bulk-rels="addBulkRels"
          />
        </div>

        <AdminEntityHistoryList
          v-if="editingEntity && entityHistory.length"
          :history="entityHistory"
        />

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
import type { ImageDescriptor } from '~/types/image'
import { TYPE_META } from '~/composables/useConstants'
import { ADMIN_KINDS } from '~/utils/adminKinds'
import { describeEntityImages, describeEntityPlaceholder, normalizeEntityEditorialUpload } from '~/utils/imageDescriptors'
import { useAdminEntityDeletion } from '~/composables/useAdminEntityDeletion'
import { useAdminEntityKinds } from '~/composables/useAdminEntityKinds'
import { useAdminEntityAttributes } from '~/composables/useAdminEntityAttributes'
import { useAdminEntityRelationships } from '~/composables/useAdminEntityRelationships'
import { useAdminEntityBulkAssign } from '~/composables/useAdminEntityBulkAssign'
import { useAdminEntityHistory } from '~/composables/useAdminEntityHistory'
import { useAdminEntityInlineEdit } from '~/composables/useAdminEntityInlineEdit'
import { useAdminEntityDuplicateCheck } from '~/composables/useAdminEntityDuplicateCheck'
import { useAdminEntitySchema } from '~/composables/useAdminEntitySchema'
import { useAdminEntitySorting } from '~/composables/useAdminEntitySorting'
import { useAdminEntityExport } from '~/composables/useAdminEntityExport'
import { useAdminEntityValidation } from '~/composables/useAdminEntityValidation'

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Quản lý Entity — Admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()

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

interface EntityImagesResponse {
  images?: string[]
}

const EMPTY_ENTITY_FORM: EntityForm = { id: '', name: '', type: 'experience', placeId: '', summary: '', images: [] }

const form = ref<EntityForm>({ ...EMPTY_ENTITY_FORM })
const formType = computed(() => form.value.type)
const formId = computed(() => form.value.id)
const formName = computed(() => form.value.name)

// Composable: Content-model schema & kind overview
const {
  entitySchemas,
  typedAttrs,
  fetchEntitySchema,
  kindGroups,
  kindGrandTotal,
  fetchKinds,
  currentSchemaGroups,
  currentSchemaKeys,
  initTypedAttrs,
} = useAdminEntitySchema({
  formType,
  authHeaders,
  showToast,
})

function filterByType(t: string) {
  typeFilter.value = t
  page.value = 1
  fetchEntities(true)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const types = Object.keys(TYPE_META)
const search = ref('')
const typeFilter = ref('')
const orphansOnly = ref(false)
const page = ref(1)

// B8b: seed pageSize/entityTypeFilter from persisted admin prefs; persist changes back.
const { prefs: adminPrefs, setPref: setAdminPref } = useAdminPrefs()
const limit = ref(adminPrefs.value.pageSize || 30)
if (adminPrefs.value.entityTypeFilter) typeFilter.value = adminPrefs.value.entityTypeFilter
watch(limit, v => setAdminPref('pageSize', v))
watch(typeFilter, v => setAdminPref('entityTypeFilter', v))

const entities = ref<Entity[]>([])
const totalEntities = ref(0)
const showModal = ref(false)
const modalRef = ref<HTMLElement | null>(null)
useModalA11y(showModal, modalRef, { onClose: () => { showModal.value = false } })
const editingEntity = ref<Entity | null>(null)
const placesList = ref<{ id: string; name: string; area?: string }[]>([])
const selected = ref<Set<string>>(new Set())

// Watcher on form.type must be after const form
watch(() => form.value.type, () => { initTypedAttrs(typedAttrs.value) })

// GĐ-A: chế độ xem theo nhóm (?kind=) — cột/bộ lọc đặc thù (utils/adminKinds)
const route = useRoute()
const {
  kindIcon,
  typeIcon,
  currentKind,
  kindTypes,
  activeChips,
  toggleChip,
  chipFiltered,
} = useAdminEntityKinds({ route, entities, types })
watch(() => route.query.kind, () => {
  selected.value = new Set()
  activeChips.value = new Set()
  typeFilter.value = ''
  fetchEntities(true)
})

// Tập đã chọn thuộc về KHUNG NHÌN hiện tại, không phải cả phiên làm việc.
watch([page, search, typeFilter, limit, orphansOnly], () => {
  if (selected.value.size) selected.value = new Set()
})

// Composables
const {
  bulkField,
  bulkValue,
  bulkAssignBusy,
  bulkProgress,
  bulkFields,
  bulkFieldDef,
  applyBulkAssign,
} = useAdminEntityBulkAssign({
  currentKind,
  selected,
  entities,
  authHeaders,
  showToast,
})

const {
  inlineEdit,
  startInline,
  saveInline,
  toggleBoolAttr,
} = useAdminEntityInlineEdit({
  currentKind,
  authHeaders,
  showToast,
})

const {
  duplicates,
  checkDuplicate,
  clearDuplicates,
} = useAdminEntityDuplicateCheck({
  formName,
  editingEntity,
  authHeaders,
})

const {
  exportJSON,
  exportCSV,
} = useAdminEntityExport(entities)

const {
  sortKey,
  sortDir,
  toggleSort,
  sortIcon,
  sortedEntities,
} = useAdminEntitySorting(chipFiltered)

const {
  fieldErrors,
  clearFieldError,
  validateForm,
  resetFieldErrors,
} = useAdminEntityValidation({
  form,
  editingEntity,
})

// In-page registered entity image handling (complies with R20.10 registry in entity-image-renderers.json)
function disclosureToken(value: unknown): string {
  return String(value || 'image').replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'image'
}

function entityTableDisclosureId(entity: Entity): string {
  return `admin-entity-thumbnail-${disclosureToken(entity.id)}-disclosure`
}

function editorialDescriptor(name: string, value: unknown): Readonly<ImageDescriptor> | null {
  const descriptor = describeEntityImages({ name, images: [value] })[0]
  if (!descriptor) return null
  try {
    return normalizeEntityEditorialUpload(descriptor)
  } catch {
    return null
  }
}

const editorImageRows = computed(() => form.value.images.map((raw, index) => ({
  raw,
  index,
  descriptor: editorialDescriptor(form.value.name, raw),
})))
const editorPlaceholder = computed(() => describeEntityPlaceholder(form.value))

function editorDisclosureId(index: number): string {
  return `admin-entity-editor-${disclosureToken(form.value.id)}-${index}-disclosure`
}

function formatAdminImageValue(value: unknown): string {
  if (typeof value === 'string') return value
  try { return JSON.stringify(value, null, 2) } catch { return String(value) }
}

function normalizedEntityImageUrls(name: string, values: unknown[]): string[] {
  return values.map((value) => {
    const descriptor = describeEntityImages({ name, images: [value] })[0]
    const normalized = normalizeEntityEditorialUpload(descriptor ?? value)
    return normalized.url as string
  })
}

function reconcileEntityImageResponse(value: unknown, fallback: string[]): string[] {
  if (!Array.isArray(value) || value.some(image => typeof image !== 'string')) return fallback
  return [...value]
}

const newImage = ref('')
async function addImage() {
  const candidate = newImage.value.trim()
  if (!candidate || !editingEntity.value) return
  try {
    const descriptor = normalizeEntityEditorialUpload(
      describeEntityImages({ name: form.value.name, images: [candidate] })[0] ?? candidate,
    )
    const r = await $fetch<EntityImagesResponse>(`/admin-api/entities/${form.value.id}/images`, {
      method: 'POST', headers: authHeaders(), body: { url: descriptor.url } })
    form.value.images = reconcileEntityImageResponse(r.images, [...form.value.images, descriptor.url as string])
    newImage.value = ''
    showToast('Đã thêm ảnh', 'success')
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
    form.value.images = reconcileEntityImageResponse(r.images, form.value.images)
    showToast('Đã tải & tối ưu ảnh', 'success')
    input.value = ''
  } catch (err: unknown) { showToast(getErrorDetail(err, 'Tải ảnh lỗi'), 'error') }
  uploadingImg.value = false
}

const entityTableRows = computed(() => sortedEntities.value.map((entity) => {
  const descriptors = describeEntityImages(entity)
  return {
    entity,
    descriptor: descriptors[0] ?? describeEntityPlaceholder(entity),
    imageCount: descriptors.length,
    disclosureId: entityTableDisclosureId(entity),
  }
}))

async function onCompletenessEdit(id: string) {
  let e = entities.value.find(x => x.id === id)
  if (!e) {
    try { e = await $fetch<Entity>(`/admin-api/entities/${id}`, { headers: authHeaders() }) } catch { return }
  }
  if (e) openEdit(e)
}
const loading = ref(true)
const saving = ref(false)

// UX state
const loadError = ref(false)
const searching = ref(false)

const {
  AMENITY_OPTIONS,
  kbygTips,
  kbygGoldenHours,
  kbygPeakDays,
  kbygCrowdLevel,
  kbygAmenities,
  kbygChecklist,
  toggleAmenity,
  initKbyg,
  MONTH_LABELS,
  seasonMonths,
  seasonPeak,
  seasonTouched,
  initSeason,
  monthState,
  cycleMonth,
  advancedJson,
  advancedError,
  initAdvanced,
  parseAdvancedJson,
  assembleAttributes,
} = useAdminEntityAttributes()

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
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer) })

let _fetchInFlight = false
async function fetchEntities(reset = false) {
  if (_fetchInFlight) return
  if (reset) page.value = 1
  _fetchInFlight = true
  loading.value = true
  try {
    const params = new URLSearchParams({ limit: String(limit.value), offset: String((page.value - 1) * limit.value) })
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
  _fetchInFlight = false
}

async function _focusModal() {
  if (!placesList.value.length) {
    try {
      placesList.value = await $fetch<{ id: string; name: string; area?: string }[]>('/admin-api/entities/places', { headers: authHeaders() })
    } catch { showToast('Không tải được danh sách xã/phường', 'warning') }
  }
  nextTick(() => {
    const el = document.getElementById(editingEntity.value ? 'ent-name' : 'ent-id')
    el?.focus()
  })
}

function resetModalForm(e?: Entity | null) {
  newImage.value = ''
  resetFieldErrors()
  clearDuplicates()
  initKbyg((e as any)?.attributes)
  initTypedAttrs((e as any)?.attributes)
  initSeason((e as any)?.season)
  initAdvanced((e as any)?.attributes, currentSchemaKeys.value)
}

async function openCreate() {
  await fetchEntitySchema()
  editingEntity.value = null
  form.value = { ...EMPTY_ENTITY_FORM }
  if (currentKind.value && !currentKind.value.types.includes(String(form.value.type))) {
    form.value.type = currentKind.value.types[0] ?? ''
  }
  resetModalForm()
  showModal.value = true
  _focusModal()
}

async function openEdit(e: Entity) {
  await fetchEntitySchema()
  editingEntity.value = e
  form.value = { id: e.id, name: e.name, type: e.type, placeId: e.placeId || '', summary: e.summary || '',
                 images: Array.isArray(e.images) ? [...e.images] : [] }
  newRel.value = { to_id: '', type: 'related_to' }
  resetModalForm(e)
  fetchRels(e.id)
  fetchEntityHistory(e.id)
  showModal.value = true
  _focusModal()
}

async function cloneEntity(e: Entity) {
  await fetchEntitySchema()
  editingEntity.value = null
  form.value = { id: '', name: `${e.name} (bản sao)`, type: e.type, placeId: e.placeId || '', summary: e.summary || '', images: [] }
  resetModalForm(e)
  showModal.value = true
  _focusModal()
}

const {
  relTypes,
  rels,
  newRel,
  bulkRelType,
  bulkRelIds,
  bulkRelSaving,
  fetchRels,
  addRel,
  removeRel,
  addBulkRels,
} = useAdminEntityRelationships({
  formId,
  editingEntity,
  authHeaders,
  showToast,
  confirmDialog,
})

const {
  entityHistory,
  fetchEntityHistory,
} = useAdminEntityHistory({
  authHeaders,
})

async function saveEntity() {
  if (saving.value) return
  if (!validateForm()) {
    showToast(Object.values(fieldErrors.value)[0] || 'Vui lòng kiểm tra biểu mẫu', 'error')
    return
  }
  let advancedObj: Record<string, unknown> = {}
  if (advancedJson.value.trim()) {
    const parsed = parseAdvancedJson()
    if (!parsed.ok) {
      showToast('Thuộc tính nâng cao: JSON không hợp lệ', 'error')
      return
    }
    advancedObj = parsed.data
  }
  saving.value = true
  try {
    const body: Record<string, any> = { ...form.value }
    body.images = normalizedEntityImageUrls(form.value.name, form.value.images)
    const existingAttrs = { ...((editingEntity.value as any)?.attributes || (body.attributes as Record<string, unknown>) || {}) }
    body.attributes = assembleAttributes({
      existingAttrs,
      currentSchemaKeys: currentSchemaKeys.value,
      typedAttrs: typedAttrs.value,
      advancedObj,
    })
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

const previewSummary = ref(false)
function mdLite(src: string): string {
  const esc = (src || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
  return esc
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
    .replace(/\n/g, '<br>')
}

const {
  acting,
  bulkBusy,
  toggleSel,
  allSelected,
  toggleAll,
  executeBulkDelete,
  deleteEntity,
} = useAdminEntityDeletion({
  selected,
  entities,
  authHeaders,
  showToast,
  confirmDialog,
  fetchEntities,
})

async function bulkDelete() {
  if (bulkBusy.value) return
  const ids = [...selected.value]
  if (!ids.length || !await confirmDialog(`Xóa ${ids.length} entity đã chọn?`, { danger: true })) return
  await executeBulkDelete(ids)
}

// Esc clears bulk selection (only when modal is closed)
function onKeydown(ev: KeyboardEvent) {
  if (ev.key === 'Escape' && !showModal.value && selected.value.size) {
    selected.value = new Set()
  }
}
onMounted(() => {
  const route = useRoute()
  if (route.query.orphans === '1') orphansOnly.value = true
  if (typeof route.query.q === 'string' && route.query.q) search.value = route.query.q
  Promise.all([fetchEntitySchema(), fetchKinds(), fetchEntities()])
  if (route.query.create === '1') openCreate()
  window.addEventListener('keydown', onKeydown)
})
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<style src="~/assets/css/admin-entities.css"></style>

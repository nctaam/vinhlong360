<template>
  <details class="ent-kbyg-details">
    <summary class="admin-label ent-kbyg-summary"><IconLine name="briefcase" /> Biết trước khi đi (KBYG)</summary>
    <div class="ent-kbyg-fields">
      <div class="ent-field">
        <label class="form-label" for="kbyg-tips">Mẹo du lịch (mỗi dòng = 1 mẹo)</label>
        <textarea id="kbyg-tips" :value="tips" class="input admin-textarea" rows="3" placeholder="VD: Nên đi buổi sáng sớm&#10;Mang dép thoải mái&#10;Có chỗ đậu xe miễn phí" @input="$emit('update:tips', ($event.target as HTMLTextAreaElement).value)"></textarea>
      </div>
      <div class="ent-field">
        <label class="form-label" for="kbyg-golden-hours">Giờ vàng</label>
        <input id="kbyg-golden-hours" :value="goldenHours" class="input" placeholder="VD: 6-8h sáng hoặc 16-18h chiều" @input="$emit('update:goldenHours', ($event.target as HTMLInputElement).value)" />
      </div>
      <div class="ent-field">
        <label class="form-label" for="kbyg-peak-days">Ngày đông</label>
        <input id="kbyg-peak-days" :value="peakDays" class="input" placeholder="VD: Cuối tuần, lễ Tết" @input="$emit('update:peakDays', ($event.target as HTMLInputElement).value)" />
      </div>
      <div class="ent-field">
        <label class="form-label" for="kbyg-crowd-level">Mức đông</label>
        <select id="kbyg-crowd-level" :value="crowdLevel" class="input" @change="$emit('update:crowdLevel', ($event.target as HTMLSelectElement).value)">
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
          <label v-for="(meta, key) in amenityOptions" :key="key" class="kbyg-amenity-check">
            <input type="checkbox" :checked="amenities.includes(key)" @change="$emit('toggle-amenity', key)" />
            <span>{{ meta.icon }} {{ meta.label }}</span>
          </label>
        </div>
      </div>
      <div class="ent-field">
        <label class="form-label" for="kbyg-checklist">Checklist chuẩn bị (mỗi dòng = 1 item, để trống = mặc định theo loại)</label>
        <textarea id="kbyg-checklist" :value="checklist" class="input admin-textarea" rows="2" placeholder="VD: Kem chống nắng&#10;Tiền mặt&#10;Nón" @input="$emit('update:checklist', ($event.target as HTMLTextAreaElement).value)"></textarea>
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
defineProps<{
  tips: string
  goldenHours: string
  peakDays: string
  crowdLevel: string
  amenities: string[]
  checklist: string
  amenityOptions: Record<string, { label: string; icon: string }>
}>()

defineEmits<{
  (e: 'update:tips', val: string): void
  (e: 'update:goldenHours', val: string): void
  (e: 'update:peakDays', val: string): void
  (e: 'update:crowdLevel', val: string): void
  (e: 'update:checklist', val: string): void
  (e: 'toggle-amenity', key: string): void
}>()
</script>

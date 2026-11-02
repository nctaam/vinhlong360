<template>
  <!-- Food & Craft specialties (dish, drink, product, craft_village, restaurant, cafe) -->
  <div v-if="foodSpecialties.length" class="food-specialties reveal">
    <h2 class="section-subtitle sediment-head"><IconLine :name="sectionIcon" aria-hidden="true" /> {{ sectionTitle }}</h2>
    <ul class="fs-list">
      <li v-for="item in foodSpecialties" :key="item.label" class="fs-item">
        <IconLine class="fs-icon" :name="item.icon" aria-hidden="true" />
        <div class="fs-content">
          <strong>{{ item.label }}</strong>
          <span>{{ item.value }}</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'

interface Props {
  entity: Entity
}

const props = defineProps<Props>()

const sectionTitle = computed(() => {
  if (props.entity?.type === 'craft_village') return 'Nghề truyền thống & Sản phẩm'
  if (props.entity?.type === 'product') return 'Đặc sản & Quà tặng'
  return 'Hương vị & Đặc sản'
})

const sectionIcon = computed(() => {
  if (props.entity?.type === 'craft_village') return 'vase'
  if (props.entity?.type === 'product') return 'gift'
  return 'bowl'
})

const SPECIALTY_FIELDS: readonly { key: string; icon: string; label: string }[] = [
  { key: 'must_order', icon: 'star', label: 'Phải thử' },
  { key: 'signature_dish', icon: 'bowl', label: 'Món đặc trưng' },
  { key: 'best_dish', icon: 'trophy', label: 'Món hay gọi nhất' },
  { key: 'specialty', icon: 'gift', label: 'Đặc sản' },
  { key: 'flavor_profile', icon: 'bowl', label: 'Hương vị đặc trưng' },
  { key: 'terroir_ingredients', icon: 'leaf', label: 'Nguyên liệu bản địa' },
  { key: 'ingredients', icon: 'bowl', label: 'Nguyên liệu' },
  { key: 'raw_material', icon: 'leaf', label: 'Nguyên liệu chính' },
  { key: 'broth_style', icon: 'flame', label: 'Nước dùng & Chế biến' },
  { key: 'noodle_type', icon: 'bowl', label: 'Sợi bánh & Cốt bánh' },
  { key: 'toppings', icon: 'star', label: 'Ăn kèm' },
  { key: 'cooking_method', icon: 'flame', label: 'Phương pháp chế biến' },
  { key: 'serving_suggestion', icon: 'bowl', label: 'Cách thưởng thức' },
  { key: 'origin', icon: 'pin', label: 'Vùng nguyên liệu / Xuất xứ' },
  { key: 'brand', icon: 'award', label: 'Thương hiệu / Cơ sở' },
  { key: 'weight/unit', icon: 'tag', label: 'Quy cách đóng gói' },
  { key: 'where_to_eat', icon: 'pin', label: 'Địa chỉ thưởng thức' },
  { key: 'what_to_buy', icon: 'gift', label: 'Nên mua làm quà' },
  { key: 'households', icon: 'home', label: 'Quy mô làng nghề' },
  { key: 'recognition_date', icon: 'calendar', label: 'Mốc công nhận' },
  { key: 'gi_certification', icon: 'award', label: 'Chỉ dẫn địa lý / Đăng ký' },
  { key: 'shelf_life', icon: 'clock', label: 'Hạn sử dụng & Bảo quản' },
]

const ALLOWED_TYPES = new Set(['dish', 'drink', 'product', 'craft_village', 'restaurant', 'cafe'])

const foodSpecialties = computed(() => {
  const a = props.entity?.attributes
  const t = props.entity?.type
  if (!a || !t || !ALLOWED_TYPES.has(t)) return []
  const items: { icon: string; label: string; value: string }[] = []

  for (const { key, icon, label } of SPECIALTY_FIELDS) {
    const raw = a[key]
    if (raw == null) continue
    const value = (Array.isArray(raw) ? raw.filter(Boolean).join(', ') : String(raw)).trim()
    if (value) items.push({ icon, label, value })
  }

  return items
})
</script>

<style scoped>
.fs-content strong {
  line-height: var(--leading-snug);
  overflow-wrap: break-word;
}
.fs-content span {
  overflow-wrap: break-word;
}
</style>

<template>
  <!-- Food & Craft specialties (dish, product, craft_village) -->
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

const foodSpecialties = computed(() => {
  const a = props.entity?.attributes
  const t = props.entity?.type
  if (!a || (t !== 'dish' && t !== 'product' && t !== 'craft_village' && t !== 'restaurant')) return []
  const items: { icon: string; label: string; value: string }[] = []

  const formatVal = (val: unknown): string => Array.isArray(val) ? val.join(', ') : String(val)

  if (a.must_order) items.push({ icon: 'star', label: 'Phải thử', value: formatVal(a.must_order) })
  if (a.signature_dish) items.push({ icon: 'bowl', label: 'Món đặc trưng', value: formatVal(a.signature_dish) })
  if (a.best_dish) items.push({ icon: 'trophy', label: 'Món hay gọi nhất', value: formatVal(a.best_dish) })
  if (a.specialty) items.push({ icon: 'gift', label: 'Đặc sản', value: formatVal(a.specialty) })
  if (a.flavor_profile) items.push({ icon: 'bowl', label: 'Hương vị đặc trưng', value: formatVal(a.flavor_profile) })
  if (a.ingredients) items.push({ icon: 'bowl', label: 'Nguyên liệu', value: formatVal(a.ingredients) })
  if (a.raw_material) items.push({ icon: 'leaf', label: 'Nguyên liệu chính', value: formatVal(a.raw_material) })
  if (a.cooking_method) items.push({ icon: 'flame', label: 'Phương pháp chế biến', value: formatVal(a.cooking_method) })
  if (a.serving_suggestion) items.push({ icon: 'bowl', label: 'Cách thưởng thức', value: formatVal(a.serving_suggestion) })
  if (a.where_to_eat) items.push({ icon: 'pin', label: 'Địa chỉ thưởng thức', value: formatVal(a.where_to_eat) })
  if (a.what_to_buy) items.push({ icon: 'gift', label: 'Nên mua làm quà', value: formatVal(a.what_to_buy) })
  if (a.households) items.push({ icon: 'home', label: 'Quy mô làng nghề', value: formatVal(a.households) })
  if (a.recognition_date) items.push({ icon: 'calendar', label: 'Mốc công nhận', value: formatVal(a.recognition_date) })
  if (a.gi_certification) items.push({ icon: 'award', label: 'Chỉ dẫn địa lý / Đăng ký', value: formatVal(a.gi_certification) })
  if (a.shelf_life) items.push({ icon: 'clock', label: 'Hạn sử dụng & Bảo quản', value: formatVal(a.shelf_life) })

  return items
})
</script>

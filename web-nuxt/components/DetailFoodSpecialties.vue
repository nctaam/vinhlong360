<template>
  <!-- Food specialties (dish/product only) -->
  <div v-if="foodSpecialties.length" class="food-specialties reveal">
    <h2 class="section-subtitle sediment-head"><IconLine name="bowl" aria-hidden="true" /> Nên thử</h2>
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

const foodSpecialties = computed(() => {
  const a = props.entity?.attributes
  const t = props.entity?.type
  if (!a || (t !== 'dish' && t !== 'product' && t !== 'craft_village')) return []
  const items: { icon: string; label: string; value: string }[] = []
  if (a.must_order) items.push({ icon: 'star', label: 'Phải thử', value: Array.isArray(a.must_order) ? a.must_order.join(', ') : String(a.must_order) })
  if (a.signature_dish) items.push({ icon: 'bowl', label: 'Món đặc trưng', value: String(a.signature_dish) })
  if (a.best_dish) items.push({ icon: 'trophy', label: 'Món hay gọi nhất', value: String(a.best_dish) })
  if (a.specialty) items.push({ icon: 'gift', label: 'Đặc sản', value: Array.isArray(a.specialty) ? a.specialty.join(', ') : String(a.specialty) })
  if (a.ingredients) items.push({ icon: 'bowl', label: 'Nguyên liệu', value: Array.isArray(a.ingredients) ? a.ingredients.join(', ') : String(a.ingredients) })
  if (a.what_to_buy) items.push({ icon: 'gift', label: 'Nên mua', value: Array.isArray(a.what_to_buy) ? a.what_to_buy.join(', ') : String(a.what_to_buy) })
  return items
})
</script>

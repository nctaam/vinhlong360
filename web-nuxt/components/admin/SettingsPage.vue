<template>
  <div>
    <div class="admin-head-row">
      <div>
        <NuxtLink to="/admin/cai-dat" class="cs-back">← Cài đặt</NuxtLink>
        <h1>{{ title }}</h1>
        <p class="cs-subtitle">{{ subtitle }}</p>
      </div>
    </div>
    <slot name="before" />
    <div v-if="loading" class="cs-skeleton">
      <div class="cs-skel-row" v-for="n in skeletonCount" :key="n"><div class="cs-skel-label"></div><div class="cs-skel-input"></div></div>
    </div>
    <Transition name="cs-fade">
      <div v-if="!loading" class="cs-form-wrap">
        <AdminSettingsForm :category="category" :fields="fields" @saved="reload" />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  title: string
  subtitle: string
  category: string
  skeletonCount?: number
}>(), { skeletonCount: 4 })

useHead({ title: `${props.title} — Admin` })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const fields = ref<any[]>([])
const loading = ref(true)

async function reload() {
  loading.value = true
  try {
    const r = await $fetch<any>(`/admin-api/site-settings/${props.category}`, { headers: authHeaders() })
    fields.value = r.settings || []
  } catch { showToast('Không thể tải cài đặt', 'error') }
  loading.value = false
}
onMounted(reload)
</script>

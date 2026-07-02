<template>
  <details class="kc-panel">
    <summary class="kc-summary">
      📈 Độ đầy đủ dữ liệu
      <span v-if="total" class="kc-total">{{ total }} entity</span>
    </summary>
    <div v-if="loading" class="kc-loading">Đang tính…</div>
    <template v-else-if="fields.length">
      <div class="kc-grid">
        <div v-for="f in fields" :key="f.key" class="kc-field" :title="`${f.filled}/${total} có ${f.label}`">
          <span class="kc-label">{{ f.label }}<em v-if="f.scope !== 'chung'" class="kc-scope">{{ f.scope }}</em></span>
          <span class="kc-pct" :class="pctClass(f.pct)">{{ f.pct }}%</span>
          <div class="kc-bar"><i :class="pctClass(f.pct)" :style="{ width: Math.max(f.pct, 2) + '%' }"></i></div>
        </div>
      </div>
      <div v-if="worst.length" class="kc-worst">
        <h4>Cần bổ sung nhất</h4>
        <button v-for="w in worst" :key="w.id" type="button" class="kc-worst-item"
          :title="`Thiếu: ${w.missing.join(', ')}`" @click="$emit('edit', w.id)">
          <strong>{{ w.name }}</strong>
          <span class="kc-worst-n">thiếu {{ w.missing_count }} trường</span>
          <span class="kc-worst-keys">{{ w.missing.slice(0, 5).join(', ') }}{{ w.missing.length > 5 ? '…' : '' }}</span>
        </button>
      </div>
    </template>
    <p v-else class="kc-loading">Không có dữ liệu.</p>
  </details>
</template>

<script setup lang="ts">
interface KcField { key: string; label: string; scope: string; filled: number; pct: number }
interface KcWorst { id: string; name: string; type: string; missing: string[]; missing_count: number }

const props = defineProps<{ kind: string }>()
defineEmits<{ (e: 'edit', id: string): void }>()

const { authHeaders } = useAuth()
const loading = ref(false)
const total = ref(0)
const fields = ref<KcField[]>([])
const worst = ref<KcWorst[]>([])

function pctClass(p: number): string {
  return p < 40 ? 'kc-low' : p < 75 ? 'kc-mid' : 'kc-high'
}

async function load() {
  loading.value = true
  try {
    const r = await $fetch<{ total: number; fields: KcField[]; worst: KcWorst[] }>(
      `/admin-api/entity-completeness?kind=${encodeURIComponent(props.kind)}`, { headers: authHeaders() })
    total.value = r.total
    fields.value = r.fields
    worst.value = r.worst
  } catch {
    fields.value = []
    worst.value = []
  }
  loading.value = false
}

watch(() => props.kind, load, { immediate: true })
</script>

<style scoped>
.kc-panel { margin: var(--space-3) 0; border: 1px solid var(--line); border-radius: var(--radius, 10px); background: var(--card); padding: var(--space-2) var(--space-3); }
.kc-summary { cursor: pointer; font-weight: 600; font-size: .92rem; display: flex; align-items: center; gap: var(--space-2); }
.kc-total { font-weight: 500; font-size: .8rem; color: var(--ink-700); }
.kc-loading { padding: var(--space-3); color: var(--ink-700); font-size: .85rem; }
.kc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: var(--space-2) var(--space-4); padding: var(--space-3) 0; }
.kc-field { display: grid; grid-template-columns: 1fr auto; gap: 2px var(--space-2); align-items: center; font-size: .82rem; }
.kc-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kc-scope { font-style: normal; opacity: .6; font-size: .72rem; margin-left: 4px; }
.kc-pct { font-weight: 700; font-variant-numeric: tabular-nums; }
.kc-pct.kc-low { color: #c0392b; }
.kc-pct.kc-mid { color: #b8860b; }
.kc-pct.kc-high { color: #1e7d46; }
.kc-bar { grid-column: 1 / -1; height: 4px; border-radius: 2px; background: color-mix(in srgb, var(--line) 60%, transparent); overflow: hidden; }
.kc-bar i { display: block; height: 100%; border-radius: 2px; transition: width .3s; }
.kc-bar i.kc-low { background: #c0392b; }
.kc-bar i.kc-mid { background: #d4a017; }
.kc-bar i.kc-high { background: #2ecc71; }
.kc-worst { border-top: 1px dashed var(--line); padding-top: var(--space-2); }
.kc-worst h4 { margin: 0 0 var(--space-2); font-size: .84rem; }
.kc-worst-item { display: flex; gap: var(--space-2); align-items: baseline; width: 100%; text-align: left; background: none; border: 0; padding: 4px 6px; border-radius: 6px; cursor: pointer; font-size: .82rem; color: var(--ink); }
.kc-worst-item:hover { background: color-mix(in srgb, var(--primary) 8%, transparent); }
.kc-worst-n { color: #c0392b; font-weight: 600; white-space: nowrap; }
.kc-worst-keys { color: var(--ink-700); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>

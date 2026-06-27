<template>
  <div>
    <div class="admin-head-row">
      <div>
        <NuxtLink to="/admin/cai-dat" class="cs-back">← Cài đặt</NuxtLink>
        <h1>Trang pháp lý</h1>
        <p class="cs-subtitle">Chính sách bảo mật & Điều khoản sử dụng</p>
      </div>
    </div>

    <div class="cs-help">
      <p>Định dạng nội dung mục bằng <strong>markdown nhẹ</strong> (an toàn, không chèn HTML):</p>
      <pre>**chữ đậm**       → chữ đậm
- mục danh sách   (mỗi dòng một gạch đầu dòng)
[Liên hệ](/lien-he)   → liên kết</pre>
    </div>

    <div v-if="loading" class="cs-skeleton">
      <div class="cs-skel-item" v-for="n in 4" :key="n"></div>
    </div>

    <Transition name="cs-fade">
      <div v-if="!loading" class="cs-form-wrap">
        <section class="legal-doc">
          <h2 class="legal-doc-title">🔒 Chính sách bảo mật</h2>
          <AdminSettingsForm :category="'legal'" :object-key="'legal.privacy'" :object-value="privacyVal" :fields="fields" @saved="reload" />
        </section>

        <section class="legal-doc">
          <h2 class="legal-doc-title">📜 Điều khoản sử dụng</h2>
          <AdminSettingsForm :category="'legal'" :object-key="'legal.terms'" :object-value="termsVal" :fields="fields" @saved="reload" />
        </section>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { LEGAL_PRIVACY, LEGAL_TERMS } from '~/utils/legalContent'
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Pháp lý — Admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const loading = ref(true)
const privacyVal = ref<Record<string, any>>({})
const termsVal = ref<Record<string, any>>({})

const fields = [
  { key: 'title', label: 'Tiêu đề trang', input_type: 'text' },
  { key: 'updated_date', label: 'Ngày cập nhật', input_type: 'text' },
  { key: 'seo_title', label: 'SEO title', input_type: 'text' },
  { key: 'seo_description', label: 'SEO description', input_type: 'textarea' },
  { key: 'intro', label: 'Đoạn mở đầu', input_type: 'textarea' },
  {
    key: 'sections', label: 'Các mục', input_type: 'repeater', addLabel: 'Thêm mục',
    itemSchema: [
      { field: 'heading', label: 'Tiêu đề mục', input_type: 'text' },
      { field: 'body', label: 'Nội dung (markdown nhẹ)', input_type: 'textarea' },
    ],
  },
]

function nonEmpty(v: any) { return v && typeof v === 'object' && Object.keys(v).length > 0 }

async function reload() {
  loading.value = true
  try {
    const r = await $fetch<any>('/admin-api/site-settings/legal', { headers: authHeaders() })
    const rows = r.settings || []
    const p = rows.find((s: any) => s.key === 'legal.privacy')?.value
    const t = rows.find((s: any) => s.key === 'legal.terms')?.value
    // Pre-fill the form with current content (default when no override yet).
    privacyVal.value = nonEmpty(p) ? p : JSON.parse(JSON.stringify(LEGAL_PRIVACY))
    termsVal.value = nonEmpty(t) ? t : JSON.parse(JSON.stringify(LEGAL_TERMS))
  } catch { showToast('Không thể tải cài đặt', 'error') }
  loading.value = false
}

onMounted(reload)
</script>

<style scoped>
.cs-back { font-size: .82rem; color: var(--muted); text-decoration: none; transition: color .15s; }
.cs-back:hover { color: var(--primary, #219653); }
.cs-subtitle { font-size: .82rem; color: var(--muted); margin-top: 4px; }
.cs-form-wrap { max-width: 680px; }

.cs-help {
  max-width: 680px; margin-bottom: var(--space-5); padding: var(--space-4);
  background: rgba(33,150,83,.04); border: .5px solid var(--line); border-radius: 12px;
  font-size: .82rem; color: var(--muted); line-height: 1.5;
}
.cs-help p { margin: 0 0 var(--space-2); }
.cs-help pre {
  margin: 0; padding: 8px 12px; border-radius: 8px; white-space: pre-wrap;
  background: var(--bg); border: .5px solid var(--line);
  font-family: 'SF Mono', 'Cascadia Code', monospace; font-size: .76rem; color: var(--ink);
}

.legal-doc { margin-bottom: var(--space-8); padding-bottom: var(--space-8); border-bottom: .5px solid var(--line); }
.legal-doc:last-child { border-bottom: none; }
.legal-doc-title { font-size: 1.05rem; font-weight: 600; margin-bottom: var(--space-4); }

.cs-skeleton { max-width: 680px; display: flex; flex-direction: column; gap: 2px; }
.cs-skel-item { height: 64px; border-radius: 12px; background: var(--line); opacity: .4; animation: cs-pulse 1.5s ease-in-out infinite; }
.cs-skel-item:nth-child(even) { animation-delay: .2s; }
@keyframes cs-pulse { 0%, 100% { opacity: .3; } 50% { opacity: .6; } }
.cs-fade-enter-active { transition: opacity .3s cubic-bezier(.2,1,.4,1), transform .3s cubic-bezier(.2,1,.4,1); }
.cs-fade-enter-from { opacity: 0; transform: translateY(6px); }
.dark .cs-help { background: rgba(33,150,83,.08); }
.dark .cs-help pre { background: var(--card, #2c2c2e); }
@media (prefers-reduced-motion: reduce) {
  .cs-skel-item { animation: none; }
  .cs-fade-enter-active { transition: none; }
}
</style>

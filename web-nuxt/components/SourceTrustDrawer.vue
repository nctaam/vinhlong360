<template>
  <Teleport to="body">
    <Transition name="trust-drawer">
      <div v-if="open" class="trust-overlay" @click.self="emit('close')">
        <aside
          ref="drawerEl"
          class="trust-drawer"
          :class="`tier-${effectiveTier}`"
          role="dialog"
          aria-modal="true"
          aria-labelledby="source-trust-title"
          data-source-trust
          :data-source-tier="effectiveTier"
        >
          <button type="button" class="trust-close" aria-label="Đóng thông tin nguồn" @click="emit('close')">
            <IconLine name="x" aria-hidden="true" />
          </button>

          <header class="trust-header">
            <span class="trust-kicker"><IconLine :name="tierIcon" aria-hidden="true" /> Nguồn & độ tin cậy</span>
            <h2 id="source-trust-title">Thông tin đứng sau nội dung</h2>
            <p>Dấu hiệu nguồn và thời điểm cập nhật được trình bày riêng, không thay thế việc kiểm tra trước khi bạn đi.</p>
          </header>

          <section class="tier-panel" :aria-label="tierLabel">
            <span class="tier-mark" aria-hidden="true"><IconLine :name="tierIcon" /></span>
            <div>
              <strong>{{ tierLabel }}</strong>
              <p>{{ tierDescription }}</p>
            </div>
          </section>

          <p v-if="communityCopy" class="community-context"><IconLine name="users" aria-hidden="true" /> {{ communityCopy }}</p>

          <dl class="trust-evidence">
            <div>
              <dt>Nguồn</dt>
              <dd>
                <a v-if="safeSourceUrl" :href="safeSourceUrl" target="_blank" rel="noopener nofollow">{{ displaySourceTitle }}</a>
                <span v-else>{{ displaySourceTitle }}</span>
              </dd>
            </div>
            <div>
              <dt>Độ mới</dt>
              <dd><span class="freshness-mark" :class="freshnessTone">{{ freshnessLabel }}</span></dd>
            </div>
            <div v-if="validUpdatedAt">
              <dt>Cập nhật</dt>
              <dd><time :datetime="validUpdatedAt">{{ formatDateVN(validUpdatedAt) }}</time></dd>
            </div>
            <div v-if="validVerifiedAt" data-verification-date>
              <dt>Xác minh</dt>
              <dd><time :datetime="validVerifiedAt">{{ formatDateVN(validVerifiedAt) }}</time></dd>
            </div>
          </dl>

          <p class="trust-guidance"><IconLine name="circle-help" aria-hidden="true" /> Nếu thông tin khác thực tế, báo cho ban biên tập để kiểm tra và bổ sung nguồn.</p>

          <div class="trust-primary-wrap">
            <button type="button" class="trust-primary" data-action="report" @click="emit('report')">
              Báo sai hoặc bổ sung nguồn
              <IconLine name="flag" aria-hidden="true" />
            </button>
          </div>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { RecommendationFreshnessStatus, RecommendationSourceTier } from '~/types/api'
import { formatDateVN, safeUrl } from '~/utils/safe'
import IconLine from './IconLine.vue'

const props = withDefaults(defineProps<{
  open?: boolean
  sourceTier?: RecommendationSourceTier | string
  sourceTitle?: string | null
  sourceUrl?: string | null
  verifiedAt?: string | null
  updatedAt?: string | null
  freshnessStatus?: RecommendationFreshnessStatus | string
  communityContext?: string | boolean
}>(), {
  open: false,
  sourceTier: 'unknown',
  sourceTitle: '',
  sourceUrl: '',
  verifiedAt: '',
  updatedAt: '',
  freshnessStatus: 'unknown',
  communityContext: false,
})

const emit = defineEmits<{ close: []; report: [] }>()
const drawerEl = ref<HTMLElement | null>(null)
const openState = computed(() => props.open)

function validDate(value?: string | null) {
  if (typeof value !== 'string' || !value.trim()) return ''
  const normalized = value.trim()
  const datePart = /^(\d{4})-(\d{2})-(\d{2})(?:T|$)/.exec(normalized)
  if (!datePart || !Number.isFinite(Date.parse(normalized))) return ''
  const year = Number(datePart[1])
  const month = Number(datePart[2])
  const day = Number(datePart[3])
  const calendarDate = new Date(Date.UTC(year, month - 1, day))
  return calendarDate.getUTCFullYear() === year
    && calendarDate.getUTCMonth() === month - 1
    && calendarDate.getUTCDate() === day
    ? normalized
    : ''
}

const validVerifiedAt = computed(() => validDate(props.verifiedAt))
const validUpdatedAt = computed(() => validDate(props.updatedAt))
const effectiveTier = computed(() => {
  if (props.sourceTier === 'community' || props.communityContext) return 'community'
  if (props.sourceTier === 'official') return 'official'
  if (props.sourceTier === 'verified') return validVerifiedAt.value ? 'verified' : 'unsupported-verified'
  return 'unknown'
})
const tierLabel = computed(() => {
  if (effectiveTier.value === 'official') return 'Nguồn chính thức'
  if (effectiveTier.value === 'verified') return 'Đối tác xác minh kèm ngày'
  if (effectiveTier.value === 'community') return 'Nguồn cộng đồng'
  if (effectiveTier.value === 'unsupported-verified') return 'Chưa đủ bằng chứng xác minh'
  return 'Nguồn chưa phân loại'
})
const tierDescription = computed(() => {
  if (effectiveTier.value === 'official') return 'Thông tin được dẫn từ cơ quan hoặc đơn vị công bố chính thức.'
  if (effectiveTier.value === 'verified') return 'Đối tác cung cấp nguồn kèm ngày xác minh hợp lệ.'
  if (effectiveTier.value === 'community') return 'Nội dung do cộng đồng đóng góp và không đại diện cho nguồn chính thức.'
  if (effectiveTier.value === 'unsupported-verified') return 'Nhãn nguồn chưa đi kèm ngày xác minh hợp lệ nên không thể khẳng định đã xác minh.'
  return 'Chưa có đủ tín hiệu để xếp nguồn vào nhóm chính thức, đối tác hoặc cộng đồng.'
})
const tierIcon = computed(() => effectiveTier.value === 'official' || effectiveTier.value === 'verified'
  ? 'shield-check'
  : effectiveTier.value === 'community'
    ? 'users'
    : 'circle-help')
const communityCopy = computed(() => {
  if (effectiveTier.value !== 'community') return ''
  return typeof props.communityContext === 'string' && props.communityContext.trim()
    ? props.communityContext.trim()
    : 'Nội dung cộng đồng được kiểm duyệt theo quy định trước khi hiển thị; vẫn có thể cần bổ sung nguồn.'
})
const displaySourceTitle = computed(() => props.sourceTitle?.trim() || 'Chưa có tên nguồn công khai')
const safeSourceUrl = computed(() => {
  const normalized = safeUrl(props.sourceUrl)
  return normalized === '#' ? '' : normalized
})
const freshnessLabel = computed(() => {
  if (props.freshnessStatus === 'fresh') return 'Mới cập nhật'
  if (props.freshnessStatus === 'aging') return 'Cần kiểm tra định kỳ'
  if (props.freshnessStatus === 'stale') return 'Có thể đã cũ'
  return 'Chưa rõ độ mới'
})
const freshnessTone = computed(() => ['fresh', 'aging', 'stale'].includes(props.freshnessStatus) ? props.freshnessStatus : 'unknown')

useModalA11y(openState, drawerEl, { onClose: () => emit('close') })
</script>

<style scoped>
/* Stitch mapping: detail V2 6a86654f63f243679ebe997ea340172b informs the evidence
   hierarchy; community dc2a7a19958e442a990f548953a042e9 informs moderation identity.
   Live Stitch retrieval is unavailable; existing Nuxt tokens remain authoritative. */
.trust-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  justify-content: flex-end;
  background: rgba(var(--black-rgb), .38);
  backdrop-filter: blur(3px);
}
.trust-drawer {
  position: relative;
  display: flex;
  flex-direction: column;
  width: min(440px, calc(100vw - 24px));
  height: 100%;
  padding: var(--space-7) var(--space-6) var(--space-5);
  overflow-y: auto;
  border-left: 4px solid var(--muted);
  color: var(--ink);
  background: var(--surface);
  box-shadow: -20px 0 48px rgba(var(--black-rgb), .16);
}
.trust-drawer.tier-official { border-left-color: var(--primary-fg); }
.trust-drawer.tier-verified { border-left-color: var(--success); }
.trust-drawer.tier-community { border-left-color: var(--accent-dark); }
.trust-drawer.tier-unsupported-verified { border-left-color: var(--warning); }
.trust-close {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: var(--radius-full);
  color: var(--muted);
  background: var(--bg-warm);
  cursor: pointer;
}
.trust-close:hover { color: var(--ink); background: var(--bg-alt); }
.trust-close:focus-visible, .trust-primary:focus-visible, .trust-evidence a:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.trust-header { padding-right: var(--space-7); }
.trust-kicker { display: inline-flex; align-items: center; gap: var(--space-2); color: var(--primary-fg); font-size: var(--text-xs); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-caps); text-transform: uppercase; }
.trust-header h2 { margin: var(--space-3) 0 var(--space-2); font-family: var(--font-editorial); font-size: clamp(1.55rem, 3vw, 2rem); line-height: var(--leading-tight); letter-spacing: -.025em; }
.trust-header p { margin: 0; color: var(--muted); font-size: var(--text-sm); line-height: var(--leading-relaxed); }
.tier-panel { display: grid; grid-template-columns: 48px minmax(0, 1fr); gap: var(--space-3); margin: var(--space-6) 0 var(--space-3); padding: var(--space-4); border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--bg-warm); }
.tier-mark { display: inline-flex; align-items: center; justify-content: center; width: 48px; height: 48px; border-radius: var(--radius-sm); color: var(--primary-fg); background: var(--surface); font-size: 1.25rem; }
.tier-community .tier-mark { color: var(--accent-dark); }
.tier-unsupported-verified .tier-mark { color: var(--warning); }
.tier-panel strong { display: block; margin-bottom: var(--space-1); font-family: var(--font-editorial); font-size: var(--text-lg); }
.tier-panel p { margin: 0; color: var(--muted); font-size: var(--text-xs); line-height: var(--leading-relaxed); }
.community-context { display: flex; align-items: flex-start; gap: var(--space-2); margin: 0 0 var(--space-4); padding: var(--space-3); border-left: 3px solid var(--accent-dark); color: var(--ink-700); background: color-mix(in srgb, var(--accent-dark) 8%, var(--bg-warm)); font-size: var(--text-xs); line-height: var(--leading-relaxed); }
.community-context .line-icon { margin-top: .15rem; color: var(--accent-dark); }
.trust-evidence { display: grid; gap: 0; margin: 0; border-top: .5px solid var(--line); }
.trust-evidence > div { display: grid; grid-template-columns: 88px minmax(0, 1fr); gap: var(--space-3); padding: var(--space-3) 0; border-bottom: .5px solid var(--line); }
.trust-evidence dt { color: var(--muted); font-size: var(--text-xs); font-weight: var(--weight-semibold); text-transform: uppercase; letter-spacing: .04em; }
.trust-evidence dd { min-width: 0; margin: 0; font-size: var(--text-sm); overflow-wrap: anywhere; }
.trust-evidence a { color: var(--primary-fg); font-weight: var(--weight-semibold); text-decoration: underline; text-underline-offset: 3px; }
.freshness-mark { display: inline-flex; align-items: center; min-height: 28px; padding: 0 var(--space-2); border: 1px solid var(--line); border-radius: var(--radius-full); color: var(--muted); background: var(--bg-warm); font-size: var(--text-xs); font-weight: var(--weight-semibold); }
.freshness-mark.fresh { color: var(--success); border-color: var(--success-border); background: var(--success-bg); }
.freshness-mark.aging { color: var(--warning); border-color: var(--warning-border); background: var(--warning-bg); }
.freshness-mark.stale { color: var(--error); border-color: var(--error-border); background: var(--error-bg); }
.trust-guidance { display: flex; align-items: flex-start; gap: var(--space-2); margin: var(--space-5) 0; color: var(--muted); font-size: var(--text-xs); line-height: var(--leading-relaxed); }
.trust-guidance .line-icon { margin-top: .15rem; color: var(--primary-fg); }
.trust-primary-wrap { position: sticky; bottom: calc(-1 * var(--space-5)); margin: auto calc(-1 * var(--space-6)) calc(-1 * var(--space-5)); padding: var(--space-4) var(--space-6) var(--space-5); border-top: .5px solid var(--line); background: var(--surface); }
.trust-primary { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); width: 100%; min-height: 48px; padding: 0 var(--space-4); border: 0; border-radius: var(--radius-sm); color: var(--on-primary); background: var(--primary); cursor: pointer; font: inherit; font-size: var(--text-sm); font-weight: var(--weight-semibold); }
.trust-drawer-enter-active, .trust-drawer-leave-active { transition: opacity .2s var(--ease-out); }
.trust-drawer-enter-active .trust-drawer, .trust-drawer-leave-active .trust-drawer { transition: transform .25s var(--ease-out); }
.trust-drawer-enter-from, .trust-drawer-leave-to { opacity: 0; }
.trust-drawer-enter-from .trust-drawer, .trust-drawer-leave-to .trust-drawer { transform: translateX(24px); }
@media (max-width: 640px) {
  .trust-overlay { align-items: flex-end; }
  .trust-drawer { width: 100%; height: auto; max-height: min(88vh, 760px); padding: var(--space-6) var(--space-4) var(--space-4); border-left: 0; border-top: 4px solid var(--muted); border-radius: var(--radius-lg) var(--radius-lg) 0 0; box-shadow: 0 -18px 44px rgba(var(--black-rgb), .2); }
  .trust-drawer.tier-official { border-top-color: var(--primary-fg); }
  .trust-drawer.tier-verified { border-top-color: var(--success); }
  .trust-drawer.tier-community { border-top-color: var(--accent-dark); }
  .trust-drawer.tier-unsupported-verified { border-top-color: var(--warning); }
  .trust-primary-wrap { bottom: calc(-1 * var(--space-4)); margin-right: calc(-1 * var(--space-4)); margin-bottom: calc(-1 * var(--space-4)); margin-left: calc(-1 * var(--space-4)); padding-right: var(--space-4); padding-bottom: calc(var(--space-4) + env(safe-area-inset-bottom)); padding-left: var(--space-4); }
  .trust-drawer-enter-from .trust-drawer, .trust-drawer-leave-to .trust-drawer { transform: translateY(24px); }
}
@media (prefers-reduced-motion: reduce) {
  .trust-drawer-enter-active, .trust-drawer-leave-active,
  .trust-drawer-enter-active .trust-drawer, .trust-drawer-leave-active .trust-drawer { transition: none; }
}
</style>

<script setup lang="ts">
// One case, everything an operator may act on, and nothing generic.
//
// There is deliberately no "resolve" or "dismiss" here. Every action is the
// specific command it performs — claim, decide with a bounded reason, build,
// apply, verify, roll back — because a generic button is how a case gets
// closed without any of those having happened.
//
// A revision conflict shows the reloaded truth and stops. The person re-applies
// against what is now on screen, or walks away; the UI never retries for them.
import { computed, ref } from 'vue'

import type { AdminCaseDetail } from '../../../composables/useAdminCases'

const props = defineProps<{
  detail: AdminCaseDetail
  /** Scopes the session actually holds; the server still decides. */
  scopes: string[]
  leaseSecondsLeft?: number | null
  conflict?: boolean
  busy?: boolean
}>()

const emit = defineEmits<{
  (event: 'decide', body: Record<string, unknown>): void
  (event: 'build-change-set', itemIds: string[]): void
  (event: 'apply-change-set'): void
  (event: 'verify-change-set'): void
  (event: 'rollback-change-set'): void
  (event: 'reload'): void
}>()

// The bounded vocabulary. Free-text reasons are how "vì sai" becomes a ruling.
const DECISION_REASONS = [
  { code: 'source_confirms_change', label: 'Nguồn xác nhận cần sửa' },
  { code: 'source_confirms_current', label: 'Nguồn xác nhận giữ nguyên' },
  { code: 'insufficient_evidence', label: 'Chưa đủ chứng cứ' },
  { code: 'out_of_scope', label: 'Ngoài phạm vi sửa' },
  { code: 'unable_to_verify', label: 'Không kiểm chứng được' },
] as const

const PROMISE_LABEL: Record<string, string> = {
  on_track: 'Đúng hạn',
  at_risk: 'Sắp trễ hạn',
  breached: 'Đã trễ hạn',
  recovery: 'Đang khắc phục sự cố',
}

const PUBLICATION_LABEL: Record<string, string> = {
  not_required: 'Không cần đăng',
  pending: 'Chờ đăng',
  applied: 'Đã ghi, chờ kiểm chứng',
  verified: 'Đã kiểm chứng trên trang',
  rolled_back: 'Đã hoàn tác',
}

const decideItemId = ref('')
const decideOutcome = ref('corrected')
const decideReason = ref<typeof DECISION_REASONS[number]['code']>('source_confirms_change')

const holds = (scope: string) => props.scopes.includes('*') || props.scopes.includes(scope)
// Visibility follows the scope, authorization stays with the server: a crafted
// click without the scope still gets the backend's 403.
const canDecide = computed(() => holds('correction.decide'))
const canPublish = computed(() => holds('publication.apply'))
const canVerify = computed(() => holds('publication.verify'))

const leaseLabel = computed(() => {
  if (props.leaseSecondsLeft == null) return null
  if (props.leaseSecondsLeft <= 0) return 'Phiên giữ việc đã hết — nhận lại trước khi thao tác.'
  const minutes = Math.floor(props.leaseSecondsLeft / 60)
  return `Đang giữ việc — còn ${minutes} phút ${props.leaseSecondsLeft % 60} giây.`
})
</script>

<template>
  <section class="case-workbench" aria-labelledby="workbench-heading">
    <h2 id="workbench-heading">Hồ sơ {{ detail.case_id.slice(0, 8) }}…</h2>

    <div v-if="conflict" class="wb-conflict" role="alert" data-role="revision-conflict">
      <p>
        Hồ sơ đã thay đổi từ khi bạn mở. Bên dưới là bản mới nhất — xem lại rồi
        thao tác lại nếu vẫn đúng ý.
      </p>
      <button type="button" @click="emit('reload')">Tải lại hồ sơ</button>
    </div>

    <p v-if="leaseLabel" class="wb-lease" aria-live="polite" data-role="lease-state">
      {{ leaseLabel }}
    </p>

    <dl class="wb-facts">
      <div><dt>Giai đoạn</dt><dd>{{ detail.phase }}</dd></div>
      <div><dt>Lời hứa</dt><dd data-role="promise-health">{{ PROMISE_LABEL[detail.promise_health] ?? detail.promise_health }}</dd></div>
      <div><dt>Bản ghi số</dt><dd data-role="case-revision">{{ detail.current_revision }}</dd></div>
    </dl>

    <section aria-labelledby="wb-items-heading">
      <h3 id="wb-items-heading">Nội dung được báo</h3>
      <ul class="wb-items">
        <li v-for="item in detail.items" :key="item.item_id" :data-risk="item.risk_class">
          <p class="wb-item-field">{{ item.field_path }} — {{ item.entity_id }}</p>
          <p class="wb-item-meta">
            Mức rủi ro {{ item.risk_class }} · Chứng cứ {{ item.evidence_level }} ·
            <span data-role="publication-state">{{ PUBLICATION_LABEL[item.publication_state] ?? item.publication_state }}</span>
          </p>
          <!-- Before/after values are private; the parent supplies them only
               once a step-up clearance is live. -->
          <slot name="diff" :item="item" />
        </li>
      </ul>
    </section>

    <form
      v-if="canDecide"
      class="wb-decide"
      data-role="decision-form"
      @submit.prevent="emit('decide', {
        item_id: decideItemId, outcome_code: decideOutcome, reason_code: decideReason,
      })"
    >
      <h3>Ra quyết định</h3>
      <label>Mục
        <select v-model="decideItemId" required>
          <option v-for="item in detail.items" :key="item.item_id" :value="item.item_id">
            {{ item.field_path }}
          </option>
        </select>
      </label>
      <label>Kết luận
        <select v-model="decideOutcome">
          <option value="corrected">Sửa theo báo cáo</option>
          <option value="confirmed_current">Giữ nguyên hiện tại</option>
          <option value="insufficient_evidence">Chưa đủ chứng cứ</option>
          <option value="out_of_scope">Ngoài phạm vi</option>
          <option value="unable_to_verify">Không kiểm chứng được</option>
        </select>
      </label>
      <label>Lý do
        <select v-model="decideReason">
          <option v-for="reason in DECISION_REASONS" :key="reason.code" :value="reason.code">
            {{ reason.label }}
          </option>
        </select>
      </label>
      <button type="submit" :disabled="busy || !decideItemId">Ghi quyết định</button>
    </form>

    <div class="wb-publication">
      <button v-if="canDecide" type="button" data-role="build" :disabled="busy"
              @click="emit('build-change-set', detail.items.map(item => item.item_id))">
        Tạo gói thay đổi
      </button>
      <button v-if="canPublish" type="button" data-role="apply" :disabled="busy"
              @click="emit('apply-change-set')">
        Đăng thay đổi
      </button>
      <button v-if="canVerify" type="button" data-role="verify" :disabled="busy"
              @click="emit('verify-change-set')">
        Kiểm chứng trang công khai
      </button>
      <button v-if="canPublish" type="button" data-role="rollback" :disabled="busy"
              @click="emit('rollback-change-set')">
        Hoàn tác thay đổi
      </button>
    </div>
  </section>
</template>

<style scoped>
.case-workbench {
  display: grid;
  gap: 0.9rem;
  min-inline-size: 0;
}
.wb-conflict {
  border: 1px solid var(--color-danger, #b91c1c);
  border-radius: 8px;
  padding: 0.6rem 0.8rem;
  display: grid;
  gap: 0.4rem;
}
.wb-conflict p,
.wb-lease {
  margin: 0;
}
.wb-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1.2rem;
  margin: 0;
}
.wb-facts dt {
  font-size: 0.75rem;
  color: var(--text-muted, #78716c);
}
.wb-facts dd {
  margin: 0;
}
.wb-items {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.6rem;
}
.wb-items li {
  border: 1px solid var(--border-soft, rgba(120, 113, 108, 0.3));
  border-radius: 8px;
  padding: 0.55rem 0.75rem;
}
.wb-item-field {
  margin: 0;
  font-weight: 600;
}
.wb-item-meta {
  margin: 0.15rem 0 0;
  font-size: 0.8rem;
  color: var(--text-muted, #78716c);
}
.wb-decide {
  display: grid;
  gap: 0.5rem;
}
.wb-decide label {
  display: grid;
  gap: 0.2rem;
}
.wb-publication {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>

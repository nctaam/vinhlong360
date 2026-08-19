// The workbench, held to its discipline.
//
// No generic resolve button, revisions on every command, a 409 that reloads
// and stops, states that read in words rather than colour, and a step-up door
// in front of anything a person actually wrote.

import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

import AssistedCorrectionForm from '../components/admin/cases/AssistedCorrectionForm.vue'
import CaseQueue from '../components/admin/cases/CaseQueue.vue'
import CaseWorkbench from '../components/admin/cases/CaseWorkbench.vue'
import ChangeSetDiff from '../components/admin/cases/ChangeSetDiff.vue'
import EvidencePanel from '../components/admin/cases/EvidencePanel.vue'
import {
  RevisionConflictError,
  useAdminCases,
  type AdminCaseDetail,
} from '../composables/useAdminCases'

const DETAIL: AdminCaseDetail = {
  case_id: 'c1a2b3c4-0000-0000-0000-000000000000',
  phase: 'decision',
  activity: 'active',
  disposition_family: 'undetermined',
  current_revision: 4,
  promise_health: 'at_risk',
  items: [{
    item_id: 'i-1', entity_id: 'p-quan-com', field_path: 'attributes.phone',
    risk_class: 'R1', evidence_level: 'E3', publication_state: 'pending',
  }],
}

const ALL_SCOPES = ['service.operator', 'correction.decide',
                    'publication.apply', 'publication.verify']

function workbench(props: Record<string, unknown> = {}) {
  return mount(CaseWorkbench, {
    props: { detail: DETAIL, scopes: ALL_SCOPES, ...props },
  })
}

describe('the composable', () => {
  it('sends the revision the operator was looking at on claim', async () => {
    const calls: Array<{ url: string, options: Record<string, any> }> = []
    const fetcher = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      calls.push({ url, options })
      return {}
    })
    const api = useAdminCases(fetcher as any)

    await api.claim('w-1', 7)

    expect(calls[0]!.options.body).toMatchObject({ expected_revision: 7 })
  })

  it('answers a 409 by reloading the case and stopping, never retrying', async () => {
    const seen: string[] = []
    const fetcher = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      seen.push(`${options.method ?? 'GET'} ${url}`)
      if (options.method === 'POST') {
        throw Object.assign(new Error('conflict'), { statusCode: 409 })
      }
      return DETAIL
    })
    const api = useAdminCases(fetcher as any)
    await api.openCase(DETAIL.case_id)

    await expect(api.decide({ item_id: 'i-1' })).rejects.toBeInstanceOf(RevisionConflictError)

    // Exactly one POST — the blind retry that would apply an action to an
    // unread case is the thing this design forbids.
    expect(seen.filter(entry => entry.startsWith('POST'))).toHaveLength(1)
    expect(seen.filter(entry => entry.startsWith('GET'))).toHaveLength(2)
  })

  it('drops the step-up secret even when the revoke call fails', async () => {
    const fetcher = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (options.method === 'DELETE') throw new Error('network')
      return { access: 'S'.repeat(43) }
    })
    const api = useAdminCases(fetcher as any)
    await api.stepUp('case-1')
    expect(api.stepUpSecret.value).not.toBe('')

    await expect(api.dropStepUp('case-1')).rejects.toThrow()

    expect(api.stepUpSecret.value).toBe('')
  })
})

describe('the workbench', () => {
  it('offers no generic resolve or dismiss anywhere', () => {
    const html = workbench().html()

    for (const generic of ['Đã xử lý', 'Bỏ qua', 'resolve', 'dismiss']) {
      expect(html).not.toContain(generic)
    }
  })

  it('shows a revision conflict as the reloaded truth plus a human decision', async () => {
    const mounted = workbench({ conflict: true })

    const banner = mounted.get('[data-role="revision-conflict"]')
    expect(banner.attributes('role')).toBe('alert')
    expect(banner.text()).toContain('thao tác lại')
    await banner.get('button').trigger('click')
    expect(mounted.emitted('reload')).toHaveLength(1)
  })

  it('speaks promise health and lease state in words, not colour', () => {
    const mounted = workbench({ leaseSecondsLeft: 125 })

    expect(mounted.get('[data-role="promise-health"]').text()).toBe('Sắp trễ hạn')
    const lease = mounted.get('[data-role="lease-state"]')
    expect(lease.text()).toContain('còn 2 phút 5 giây')
    expect(lease.attributes('aria-live')).toBe('polite')
  })

  it('says plainly when the lease has run out', () => {
    expect(workbench({ leaseSecondsLeft: 0 }).get('[data-role="lease-state"]').text())
      .toContain('đã hết')
  })

  it('decides only through the bounded vocabulary', () => {
    const html = workbench().get('[data-role="decision-form"]').html()

    expect(html).toContain('source_confirms_change')
    // No free-text reason: "vì sai" is not a ruling anyone can review.
    expect(html).not.toContain('<textarea')
  })

  it('hides what the scope cannot do while the server still decides', () => {
    const operator = workbench({ scopes: ['service.operator'] })

    expect(operator.find('[data-role="decision-form"]').exists()).toBe(false)
    expect(operator.find('[data-role="apply"]').exists()).toBe(false)

    const publisher = workbench({ scopes: ['publication.apply'] })
    expect(publisher.find('[data-role="apply"]').exists()).toBe(true)
    expect(publisher.find('[data-role="verify"]').exists()).toBe(false)
  })
})

describe('the queue', () => {
  it('labels risk in words so a monochrome screen reads the same', () => {
    const queue = mount(CaseQueue, {
      props: {
        items: [{ work_item_id: 'w-1', case_id: 'c-1', kind: 'decide',
                  risk_class: 'R3', status: 'ready', revision: 1 }],
      },
    })

    expect(queue.text()).toContain('Mức rủi ro R3')
    expect(queue.text()).toContain('Chưa ai nhận')
  })
})

describe('the diff', () => {
  it('names both sides in text and prefixes them like a patch', () => {
    const diff = mount(ChangeSetDiff, {
      props: { fieldPath: 'attributes.phone', before: '0270 111 2222', after: '0270 333 4444' },
    })

    expect(diff.get('[data-role="diff-before"]').text()).toContain('− 0270 111 2222')
    expect(diff.get('[data-role="diff-after"]').text()).toContain('+ 0270 333 4444')
    expect(diff.text()).toContain('Trước (−)')
    expect(diff.text()).toContain('Sau (+)')
  })
})

describe('the evidence door', () => {
  it('asks for a step-up before anything private is shown', () => {
    const panel = mount(EvidencePanel, {
      props: { caseId: 'c-1', stepUpSecret: '' },
      slots: { default: '<p data-role="private">nội dung riêng tư</p>' },
    })

    expect(panel.find('[data-role="private"]').exists()).toBe(false)
    expect(panel.get('[data-role="step-up-prompt"]').text()).toContain('15 phút')
  })

  it('shows the clearance state and a way to lock it again', async () => {
    const panel = mount(EvidencePanel, {
      props: { caseId: 'c-1', stepUpSecret: 'S'.repeat(43),
               stepUpExpiresAt: '2026-08-19T09:15:00+07:00' },
      slots: { default: '<p data-role="private">nội dung riêng tư</p>' },
    })

    expect(panel.find('[data-role="private"]').exists()).toBe(true)
    expect(panel.get('[data-role="clearance-state"]').text()).toContain('tự khoá')
    await panel.get('[data-role="drop-step-up"]').trigger('click')
    expect(panel.emitted('drop-step-up')).toHaveLength(1)
  })
})

describe('the assisted form', () => {
  it('submits nothing until every consent box is real', async () => {
    const form = mount(AssistedCorrectionForm, {
      props: { privacyNoticeRevision: 'privacy-2026-07' },
    })
    await form.get('[data-role="notice-consent"] input').setValue(true)
    await form.get('form').trigger('submit')
    expect(form.emitted('submit')).toBeUndefined()

    await form.get('[data-role="read-back"] input').setValue(true)
    await form.get('[data-role="reporter-confirmed"] input').setValue(true)
    await form.get('form').trigger('submit')

    const [body] = form.emitted('submit')![0] as [Record<string, any>]
    expect(body.privacy_notice_revision).toBe('privacy-2026-07')
    expect(body.items[0].read_back_confirmed).toBe(true)
  })

  it('offers nowhere to paste a recording or a transcript', () => {
    const html = mount(AssistedCorrectionForm, {
      props: { privacyNoticeRevision: 'privacy-2026-07' },
    }).html()

    for (const field of ['recording', 'transcript', 'ghi âm']) {
      expect(html.toLowerCase()).not.toContain(field)
    }
  })
})

describe('the reports page handover', () => {
  const page = readFileSync(resolve(__dirname, '..', 'pages', 'admin', 'bao-cao.vue'), 'utf8')

  it('keeps correction rows read-only and routes them to the workbench', () => {
    expect(page).toContain('isCorrectionRow(r)')
    expect(page).toContain('to="/admin/yeu-cau"')
  })

  it('keeps resolve and dismiss for moderation rows only', () => {
    // The buttons still exist — behind the branch that excludes corrections.
    expect(page).toContain("infoAction(r, 'resolved')")
    expect(page).toContain('v-else-if="(r.status || \'open\') === \'open\'"')
  })
})

describe('the queue grammar', () => {
  it('reads promise health and owner in words on every row', () => {
    const queue = mount(CaseQueue, {
      props: {
        items: [{
          work_item_id: 'w-1', case_id: 'c-1', kind: 'decide',
          risk_class: 'R2', status: 'claimed', revision: 3,
          promise_health: 'breached', owner_ref: 'user:7',
        }],
      },
    })

    const text = queue.text()
    // queue → promise health → owner → next action, all spelled out.
    expect(text).toContain('Đã trễ hạn')
    expect(text).toContain('Người giữ: user:7')
    expect(text).toContain('Cần quyết định')
  })

  it('reads on-track and unowned rows honestly too', () => {
    const queue = mount(CaseQueue, {
      props: {
        items: [{
          work_item_id: 'w-2', case_id: 'c-2', kind: 'publication',
          risk_class: 'R1', status: 'ready', revision: 1,
          promise_health: 'on_track', owner_ref: null,
        }],
      },
    })

    expect(queue.text()).toContain('Đúng hạn')
    expect(queue.text()).toContain('Chưa ai nhận')
  })
})

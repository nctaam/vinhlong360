import { describe, expect, it } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import * as plannerOptimization from '../composables/useItineraryOptimization'
import PlannerOptimizationPreview from '../components/planner/PlannerOptimizationPreview.vue'

interface DraftStop {
  id: string
  name: string
  coords: [number, number] | null
}

const initialStops: DraftStop[] = [
  { id: 'start', name: 'Bến đò', coords: [10, 106] },
  { id: 'middle', name: 'Làng nghề', coords: [10.1, 106.1] },
  { id: 'end', name: 'Vườn cây', coords: [10.2, 106.2] },
]

const candidateStops = [initialStops[0]!, initialStops[2]!, initialStops[1]!]

describe('planner optimizer preview transaction', () => {
  it('renders before/after stop order and waits for an explicit decision', async () => {
    const wrapper = await mountSuspended(PlannerOptimizationPreview, {
      props: {
        before: initialStops,
        after: candidateStops,
        changes: [
          { id: 'middle', from: 1, to: 2 },
          { id: 'end', from: 2, to: 1 },
        ],
        tradeoffs: ['Giữ nguyên điểm đầu và điểm cuối.'],
      },
    })

    expect(wrapper.get('[data-preview-before]').text()).toContain('Làng nghề')
    expect(wrapper.get('[data-preview-after]').text()).toContain('Vườn cây')
    expect(wrapper.get('[data-preview-tradeoffs]').text()).toContain('điểm đầu')
    expect(wrapper.emitted('confirm')).toBeUndefined()
    expect(wrapper.emitted('cancel')).toBeUndefined()

    await wrapper.get('[data-preview-cancel]').trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
    await wrapper.get('[data-preview-confirm]').trigger('click')
    expect(wrapper.emitted('confirm')).toHaveLength(1)
    wrapper.unmount()
  })

  it('does not mutate current stops before optimizer confirmation', async () => {
    const createPreview = (plannerOptimization as Record<string, unknown>)
      .createPlannerOptimizationPreview as undefined | ((before: DraftStop[], after: DraftStop[]) => Promise<unknown>)

    expect(createPreview).toEqual(expect.any(Function))
    if (!createPreview) return

    const currentStops = initialStops.slice()
    const preview = await createPreview(currentStops, candidateStops)

    expect((preview as { after: DraftStop[] }).after.map(stop => stop.id)).toEqual([
      'start',
      'end',
      'middle',
    ])
    expect(currentStops).toEqual(initialStops)
  })

  it('keeps the exact current array and revision on cancel', async () => {
    const createPreview = (plannerOptimization as Record<string, unknown>)
      .createPlannerOptimizationPreview as undefined | ((before: DraftStop[], after: DraftStop[]) => Promise<{
        cancel: () => DraftStop[]
      }>)

    expect(createPreview).toEqual(expect.any(Function))
    if (!createPreview) return

    const currentStops = initialStops.slice()
    const currentReference = currentStops
    const preview = await createPreview(currentStops, candidateStops)

    expect(preview.cancel()).toEqual(initialStops)
    expect(preview.cancel()).toBe(currentReference)
    expect(currentStops).toEqual(initialStops)
  })

  it('returns a confirmed candidate only after explicit confirmation', async () => {
    const createPreview = (plannerOptimization as Record<string, unknown>)
      .createPlannerOptimizationPreview as undefined | ((before: DraftStop[], after: DraftStop[]) => Promise<{
        confirm: () => DraftStop[]
        changes: Array<{ id: string; from: number; to: number }>
      }>)

    expect(createPreview).toEqual(expect.any(Function))
    if (!createPreview) return

    const preview = await createPreview(initialStops, candidateStops)
    expect(preview.changes.map(({ id, from, to }) => ({ id, from, to }))).toEqual([
      { id: 'middle', from: 1, to: 2 },
      { id: 'end', from: 2, to: 1 },
    ])
    expect(preview.confirm().map(stop => stop.id)).toEqual(['start', 'end', 'middle'])
  })
})

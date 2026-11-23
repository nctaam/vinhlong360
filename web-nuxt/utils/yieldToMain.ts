/**
 * Cooperatively yields control back to the browser event loop so input/rendering
 * stays responsive during large client-side batches.
 */
export function yieldToMain(): Promise<void> {
  const sched = (globalThis as { scheduler?: { yield?: () => Promise<void> } }).scheduler
  if (sched && typeof sched.yield === 'function') {
    return sched.yield()
  }
  return new Promise<void>(resolve => setTimeout(resolve, 0))
}

/**
 * Returns true while an IME composition session is active on a keydown event.
 * Pairs event.isComposing with keyCode === 229 (VK_PROCESSKEY) to cover
 * Safari's out-of-order compositionend/keydown bug (WebKit 165004).
 */
export function isImeComposing(event: Pick<KeyboardEvent, 'isComposing' | 'keyCode'>): boolean {
  return Boolean(event.isComposing || event.keyCode === 229)
}

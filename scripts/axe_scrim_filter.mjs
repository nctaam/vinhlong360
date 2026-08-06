/**
 * Điều kiện bỏ qua false positive color-contrast của axe trên `.spread-scrim`.
 *
 * Tách khỏi `axe_scan.mjs` vì file đó mở đầu bằng shebang — vite dời shebang
 * xuống sau các import khi transform, nên import nó từ vitest là lỗi parse.
 *
 * Hàm ở đây phải THUẦN: nó vừa được test ở Node, vừa được `.toString()` rồi
 * serialize vào page context qua CDP. Một bản logic cho cả hai nơi — đừng tham
 * chiếu biến ngoài, đừng dùng API chỉ có ở Node.
 */

export const SCRIM_SELECTORS = ['.spread-kicker', '.spread-title', '.spread-sub', '#spread-title']

/**
 * Scrim còn đủ tối để nuôi chữ trắng hay không.
 *
 * Trả `true` → vi phạm color-contrast trên chữ trong scrim là false positive
 * (axe không thấy nền ở `z-index:-1` nên quy về nền trang: đo được bgColor
 * `#fdfcf9`, tỉ lệ 1.02, trong khi nền thật là `rgba(8,9,12,.84)`).
 *
 * Trả `false` → scrim đã bị gỡ/làm nhạt/ẩn, nền tối không còn, nên vi phạm là
 * THẬT và phải nổi lên cổng R30.6. Đây là điểm khác giữa hàm này và một
 * allowlist chết: nó tự kiểm chính điều kiện đã khiến nó hợp lệ.
 *
 * @param {{display?: string, visibility?: string, opacity?: string, backgroundImage?: string} | null} cs
 */
export function scrimShieldsText(cs) {
  if (!cs) return false
  if (cs.display === 'none' || cs.visibility === 'hidden') return false
  if (Number(cs.opacity) < 0.95) return false
  // Alpha ở điểm dừng đầu của gradient phải còn đủ tối để nuôi chữ trắng.
  const head = /rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([\d.]+)\s*\)/.exec(cs.backgroundImage || '')
  return !!head && Number(head[1]) >= 0.8
}

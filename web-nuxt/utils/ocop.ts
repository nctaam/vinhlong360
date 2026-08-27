// Rút hạng sao OCOP từ entity — MỘT nơi duy nhất.
//
// Dữ liệu ghi hạng sao ở BỐN kiểu khoá khác nhau (nợ chuẩn hoá, ROADMAP §31.5):
// `ocop_star` (81 sản phẩm) · `ocop_stars` · `ocop_rating` · `ocop` (văn xuôi tự
// do). Trang /ocop trước đây chỉ đọc `parseInt(attributes.ocop)`, mà `ocop` là
// câu chữ chứ không phải số — nên `parseInt('OCOP 3 sao')` = NaN → 0. Hậu quả đo
// được trên trang đang chạy: sổ vinh danh hiện 3 sản phẩm thay vì 77, dải "Bậc 5
// sao" KHÔNG render, triện son khai ★4 trong khi dữ liệu có 5 sản phẩm 5 sao.
//
// Chuẩn hoá DỮ LIỆU (gộp 4 khoá về 1) là task riêng cần backup B1 + chỉ đạo chủ
// dự án. Ở đây chỉ sửa BÊN ĐỌC cho chịu được cả bốn kiểu — additive-first (B2),
// không đụng một hàng dữ liệu nào.

export interface OcopEntityLike {
  summary?: string | null
  description?: string | null
  attributes?: Record<string, any> | null | undefined
}

const NUMERIC_KEYS = ['ocop_star', 'ocop_stars', 'ocop_rating'] as const

// NEO ĐẦU CHUỖI có chủ đích. Nới ra thành "tìm N sao ở bất kỳ đâu" sẽ tự phong
// 5 sao cho `dua-sap-cau-ke`, vì `ocop` của nó là
//   "VICOSAP: 4 SP OCOP 5 sao quốc gia + 7 SP OCOP 4 sao"
// — đó là DANH MỤC SẢN PHẨM CỦA MỘT CÔNG TY KHÁC, không phải chứng nhận của trái
// dừa. Neo đầu bắt được 10/11 chuỗi có hạng ("OCOP 3 sao", "4 sao",
// "OCOP 4 sao (QĐ 114/QĐ-UBND, 15/1/2020)"…) và bỏ sót đúng 1 ca lành
// ("Cam sành Khánh Nhân, Thuận Loan — OCOP 3 sao"). Bỏ sót thì sản phẩm hiện là
// "có chứng nhận, chưa rõ hạng" — thiệt thòi nhưng THẬT; bắt nhầm thì trang khai
// khống một hạng quốc gia.
const SELF_TIER = /^\s*(?:ocop\s*)?([1-5])\s*sao\b/i

// §1.7 — hạng "mới được đề nghị" KHÔNG phải hạng đã đạt.
const PROPOSAL = /đề xuất|đề nghị|chờ\s+(?:công nhận|đánh giá|xét)|đang\s+(?:xét|đề nghị)|dự kiến/i
const AWARDED = /đạt|được công nhận|đã công nhận|chứng nhận|cấp quốc gia/i
const CLAIM_WINDOW = 40

function attrs(e: OcopEntityLike | null | undefined): Record<string, any> {
  return (e && e.attributes) || {}
}

/** Hạng sao GHI TRONG DỮ LIỆU, chưa qua bộ lọc §1.7. 0 = không rút được hạng. */
export function ocopClaimedStars(e: OcopEntityLike | null | undefined): number {
  const a = attrs(e)
  for (const key of NUMERIC_KEYS) {
    const raw = a[key]
    if (typeof raw === 'number' && Number.isFinite(raw)) return Math.trunc(raw)
    // Chuỗi thuần số ("4") vẫn là con số người ta định ghi.
    if (typeof raw === 'string' && /^\s*[1-5]\s*$/.test(raw)) return parseInt(raw, 10)
  }
  const text = a.ocop
  if (typeof text === 'string') {
    const m = SELF_TIER.exec(text)
    if (m) return parseInt(m[1]!, 10)
  }
  return 0
}

/**
 * Hạng ghi trong dữ liệu có phải hạng ĐÃ ĐẠT không, hay mới chỉ được đề nghị?
 *
 * Luật HAI CHIỀU, không phải một. Luật một chiều ("văn xuôi có chữ đề xuất thì
 * hạ hạng") đánh oan ngay ca thật đầu tiên gặp phải:
 *
 *   khoai-lang-say-binh-tan  ocop_star=5  "…được ĐỀ XUẤT lên Trung ương đánh giá
 *                                          5 sao OCOP…"        → 5 là CHƯA đạt
 *   khoai-lang-say-dong-phat ocop_star=4  "…ĐẠT OCOP 4 sao và được đề xuất công
 *                                          nhận 5 sao."        → 4 CÓ THẬT
 *
 * Cả hai đều chứa "đề xuất" trong cửa sổ ±40 quanh hạng của mình. Cái phân biệt
 * chúng là ca thứ hai có chữ ĐẠT ngay trước hạng. Nên: chỉ hạ khi cửa sổ có lời
 * đề nghị mà KHÔNG có lời xác nhận. Cùng lớp bài học với cửa sổ ±40 của
 * `_has_stale_geography` bên backend — chuỗi trần giết oan cách viết đúng chuẩn.
 */
export function ocopStarProvisional(e: OcopEntityLike | null | undefined): boolean {
  const claimed = ocopClaimedStars(e)
  if (claimed <= 0) return false
  const prose = `${e?.summary || ''} ${e?.description || ''}`
  if (!prose.trim()) return false

  const needle = new RegExp(`${claimed}\\s*sao`, 'gi')
  let sawProposal = false
  let sawAwarded = false
  let m: RegExpExecArray | null
  while ((m = needle.exec(prose)) !== null) {
    const window = prose.slice(
      Math.max(0, m.index - CLAIM_WINDOW),
      m.index + m[0].length + CLAIM_WINDOW,
    )
    if (PROPOSAL.test(window)) sawProposal = true
    if (AWARDED.test(window)) sawAwarded = true
  }
  // Xét TOÀN VĂN, không xét từng lần nhắc. Văn xuôi của một entity tự mâu thuẫn
  // với chính nó là chuyện thật, không phải giả định: `khoai-lang-say-binh-tan`
  // nói "được đề xuất lên Trung ương đánh giá 5 sao" HAI lần rồi kết bằng câu
  // trần "Sản phẩm OCOP 5 sao." Luật xét-từng-lần để đúng câu trần đó lật ngược
  // cả phán quyết và trang lại khai 5 sao. Cùng họ với bẫy sáu-ô §5c: một sự
  // thật nằm ở nhiều ô, các ô nói ngược nhau.
  //
  // Khi mâu thuẫn thì lời ĐỀ NGHỊ thắng lời khẳng định trần — nó cụ thể hơn, và
  // §1.7 buộc nghiêng về phía KHÔNG khai khống. Chỉ lời xác nhận TƯỜNG MINH
  // ("đạt N sao", "cấp quốc gia") mới lật lại được.
  return sawProposal && !sawAwarded
}

/** Hạng DÙNG ĐƯỢC để xếp bậc và trưng ra. 0 = có chứng nhận nhưng chưa rõ hạng. */
export function ocopStars(e: OcopEntityLike | null | undefined): number {
  return ocopStarProvisional(e) ? 0 : ocopClaimedStars(e)
}

/** Có dấu hiệu OCOP nào không — kể cả khi không rút được hạng. */
export function isOcopCertified(e: OcopEntityLike | null | undefined): boolean {
  const a = attrs(e)
  if (NUMERIC_KEYS.some(k => a[k] !== undefined && a[k] !== null && a[k] !== '')) return true
  return !!(a.ocop || a.ocop_certified)
}

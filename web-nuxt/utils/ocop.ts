// Rút hạng sao OCOP từ entity — MỘT nơi duy nhất.
//
// Dữ liệu ghi hạng sao ở BỐN kiểu khoá khác nhau (nợ chuẩn hoá, ROADMAP §31.5):
// `ocop_star` (81 sản phẩm) · `ocop_stars` · `ocop_rating` · `ocop` (văn xuôi tự
// do). Trang /ocop trước đây chỉ đọc `parseInt(attributes.ocop)`, mà `ocop` là
// câu chữ chứ không phải số — nên `parseInt('OCOP 3 sao')` = NaN → 0. Hậu quả đo
// được trên trang đang chạy: sổ vinh danh hiện 3 sản phẩm thay vì 77, dải "Bậc 5
// sao" KHÔNG render, triện son khai hạng 4 trong khi dữ liệu có 5 sản phẩm
// 5 sao.
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

// Chương trình OCOP chỉ công nhận 3, 4 và 5 sao. KHÔNG có "OCOP 1 sao" hay
// "OCOP 2 sao" — chúng không tồn tại, nên ô số mang 1 hoặc 2 không phải hạng.
const MIN_GRADE = 3

function attrs(e: OcopEntityLike | null | undefined): Record<string, any> {
  return (e && e.attributes) || {}
}

/** Hạng sao GHI TRONG DỮ LIỆU, chưa qua bộ lọc §1.7. 0 = không rút được hạng. */
/** Hạng từ BA KHOÁ SỐ. Tách ra để luật "ô số là rác chép nhầm cột" soi được
 *  riêng phần số, giống `_tu_khoa_so` bên bản Python. */
function numericKeyTier(a: Record<string, any>): number {
  for (const key of NUMERIC_KEYS) {
    const raw = a[key]
    if (typeof raw === 'number' && Number.isFinite(raw)) return Math.trunc(raw)
    // Chuỗi thuần số ("4") vẫn là con số người ta định ghi.
    if (typeof raw === 'string' && /^\s*[1-5]\s*$/.test(raw)) return parseInt(raw, 10)
  }
  return 0
}

/** Hạng từ Ô `ocop` (văn xuôi tự do), tách riêng như `_tu_o_ocop` bên Python. */
function proseFieldTier(a: Record<string, any>): number {
  const text = a.ocop
  // Số nguyên trong ô `ocop` là RÕ NGHĨA, khác hẳn văn xuôi — nhận thẳng. Bản
  // Python (`agent/ocop.py`) nhận ca này; hai bản sinh đôi phải khớp nhau.
  if (typeof text === 'number' && Number.isFinite(text)) return Math.trunc(text)
  if (typeof text === 'string') {
    const m = SELF_TIER.exec(text)
    if (m) return parseInt(m[1]!, 10)
  }
  return 0
}

export function ocopClaimedStars(e: OcopEntityLike | null | undefined): number {
  const a = attrs(e)
  return numericKeyTier(a) || proseFieldTier(a)
}

/** Văn xuôi có XÁC NHẬN hạng này cho CHÍNH entity không? Cùng cửa sổ ±40 với §1.7. */
function proseAwardsTier(e: OcopEntityLike | null | undefined, tier: number): boolean {
  const prose = `${e?.summary || ''} ${e?.description || ''}`
  const needle = new RegExp(`${tier}\\s*sao`, 'gi')
  let m: RegExpExecArray | null
  while ((m = needle.exec(prose)) !== null) {
    const window = prose.slice(Math.max(0, m.index - CLAIM_WINDOW), m.index + m[0].length + CLAIM_WINDOW)
    if (AWARDED.test(window)) return true
  }
  return false
}

/**
 * Con số trong ô OCOP là RÁC CHÉP NHẦM CỘT, không phải một chứng nhận.
 *
 * Đo trên `web/data.json` 2026-08-30: 13 cơ sở lưu trú mang `ocop_star`, và CẢ
 * 13 có `ocop_star` bằng đúng `star_rating` của chính nó (1=1, 2=2, 4=4, 5=5),
 * `ocop_certified` rỗng. Đó là vân tay của một lượt nhập chép nhầm cột
 * hạng-sao-khách-sạn sang ô OCOP. Hậu quả trên trang: một khách sạn hiện
 * «Sản phẩm OCOP 1 sao — Chương trình Mỗi xã Một sản phẩm». Khai khống một
 * chứng nhận NHÀ NƯỚC là đúng thứ CLAUDE.md §1.7 cấm.
 *
 * HAI LUẬT, mỗi luật tự đứng được:
 *  (A) Hạng dưới 3 — OCOP không có bậc đó. Bắt 12 entity (11 khách sạn +
 *      `khu-du-lich-truong-an`). Toàn kho KHÔNG có sản phẩm nào mang hạng 1|2,
 *      nên luật này không đụng một sản phẩm thật nào.
 *  (B) Số chỉ chép lại `star_rating` VÀ văn xuôi không xác nhận hạng đó. Bắt nốt
 *      `homestay-sokfram` (5=5; văn xuôi chỉ nói nó BÀY BÁN sản phẩm OCOP 3–5
 *      sao của địa phương — cùng bẫy "danh mục của người khác" mà
 *      `dua-sap-cau-ke` đã dạy).
 *
 * VÌ SAO (B) phải có vế văn xuôi: `somo-farm-cuu-long` cũng 4=4 nhưng ghi rõ
 * "Đạt chứng nhận OCOP 4 sao năm 2023 cho sản phẩm du lịch sinh thái" — OCOP
 * nhóm 6 (dịch vụ du lịch) là CÓ THẬT. Thiếu vế đó là bóp mất một chứng nhận
 * đúng. Đã đối chiếu từng ca trong cả 13.
 *
 * KHÔNG đụng `ocop_star: 9|0|true` — chúng giữ hành vi cũ (không rút được hạng
 * nhưng vẫn tính là có dấu hiệu): đó là ý định ghi OCOP kèm lỗi gõ, khác hẳn
 * việc chép nhầm nguyên một cột khác.
 */
export function ocopNumberIsColumnBleed(e: OcopEntityLike | null | undefined): boolean {
  const a = attrs(e)
  const n = numericKeyTier(a)
  if (n <= 0) return false
  if (n < MIN_GRADE) return true
  const lodgingStars = a.star_rating
  if (lodgingStars === null || lodgingStars === undefined || lodgingStars === '') return false
  const parsed = parseInt(String(lodgingStars).trim(), 10)
  if (!Number.isFinite(parsed) || parsed !== n) return false
  return !proseAwardsTier(e, n)
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
  return proseProposesTier(e, ocopClaimedStars(e))
}

/** Cùng luật, nhưng xét một hạng CHO TRƯỚC — cần vì `ocopStars` có thể đang xét
 *  hạng lấy từ ô văn xuôi sau khi loại ô số rác. */
function proseProposesTier(e: OcopEntityLike | null | undefined, claimed: number): boolean {
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

/** Hạng DÙNG ĐƯỢC để xếp bậc và trưng ra. 0 = có chứng nhận nhưng chưa rõ hạng.
 *
 * KẸP về thang 1..5 ở ĐÂY, không phải ở nơi hiển thị. Bản đầu chỉ kẹp trong
 * `ocopBadgeLabel` nên `ocop_star: 9` vẫn ra tier 9 cho mọi nơi gọi khác — và
 * bộ ca dùng chung với bản Python (`tests/fixtures/ocop-twin-cases.json`) bắt
 * được ngay: Python trả 0, TS trả 9.
 */
export function ocopStars(e: OcopEntityLike | null | undefined): number {
  // Ô số là rác chép nhầm cột → bỏ nó, chỉ còn ô văn xuôi được nói.
  const n = ocopNumberIsColumnBleed(e) ? proseFieldTier(attrs(e)) : ocopClaimedStars(e)
  if (n <= 0) return 0
  if (proseProposesTier(e, n)) return 0
  return n >= 1 && n <= 5 ? n : 0
}

/** Có dấu hiệu OCOP nào không — kể cả khi không rút được hạng. */
export function isOcopCertified(e: OcopEntityLike | null | undefined): boolean {
  const a = attrs(e)
  const hasNumber = NUMERIC_KEYS.some(k => a[k] !== undefined && a[k] !== null && a[k] !== '')
  // Ô số rác chép nhầm cột KHÔNG phải dấu hiệu OCOP — nếu tính, 12 khách sạn vẫn
  // đeo huy hiệu «OCOP» trơn, vẫn lọt bộ lọc và sổ vinh danh.
  if (hasNumber && !ocopNumberIsColumnBleed(e)) return true
  return !!(a.ocop || a.ocop_certified)
}

/**
 * Nhãn hiển thị cho huy hiệu OCOP — «OCOP 5 sao» · «OCOP» · '' (không có).
 *
 * TUYỆT ĐỐI không in `attributes.ocop` thô ra giao diện. Trường đó là văn xuôi
 * tự do, và ít nhất một entity mang cả danh mục sản phẩm của công ty KHÁC:
 *   dua-sap-cau-ke → "VICOSAP: 4 SP OCOP 5 sao quốc gia + 7 SP OCOP 4 sao"
 * In thô ra thì trang gán chứng nhận của người khác cho trái dừa — đo được
 * 2026-08-27: huy hiệu rộng 468px, và chuỗi đó còn lọt vào JSON-LD `brand.name`
 * cho Google đọc. Một entity khác mang số quyết định:
 *   "OCOP 4 sao (QĐ 114/QĐ-UBND, 15/1/2020)"
 */
export function ocopBadgeLabel(e: OcopEntityLike | null | undefined): string {
  if (!isOcopCertified(e)) return ''
  const tier = ocopStars(e)
  return tier > 0 ? `OCOP ${tier} sao` : 'OCOP'
}

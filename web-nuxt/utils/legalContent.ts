// B5 — canonical default content for the legal pages (privacy, terms).
// Stored as { title, updated_date, seo_title, seo_description, intro, sections }
// where intro/section bodies are markdown-lite (rendered via utils/mdLite).
// The CMS stores an override under `legal.privacy` / `legal.terms`; the page
// merges override-over-default so it renders identically until edited, and an
// admin clearing the override reverts to this (legally-reviewed) default.

import privacyPolicy from '#privacy-policy'

export interface LegalSection {
  heading: string
  body: string
}
export interface CookieInventoryItem {
  name: string
  runtimeRole: 'issued' | 'accepted-legacy'
  owner: string
  purpose: string
  expiry: string
  sameSite: 'Strict' | 'Lax' | 'None'
  secure: boolean | 'production-only'
  httpOnly: boolean
  consentControl: string
  retention: string
  deletion: {
    path: string
    sameSite: 'Strict' | 'Lax' | 'None'
    secure: boolean | 'production-only'
    httpOnly: boolean
    mechanism?: string
  }
  deprecation?: string
  expiryDecision?: string
}
export interface LegalChange {
  version: string
  date: string
  summary: string
}
export interface LegalMetadata {
  policyVersion: string
  updatedDate: string
  owner: string
  contact: string
  cookieInventory: CookieInventoryItem[]
  changeHistory: LegalChange[]
}
export interface LegalDoc {
  title: string
  updated_date: string
  seo_title: string
  seo_description: string
  intro: string
  sections: LegalSection[]
  policyVersion: string
  updatedDate: string
  owner: string
  contact: string
  cookieInventory: CookieInventoryItem[]
  changeHistory: LegalChange[]
}

export const decisionRequired = {
  sla_24h_48h: 'Quy trình 24/48 giờ là mục tiêu đang chờ DPO/luật sư phê duyệt, không phải cam kết dịch vụ.',
  residency: 'Nơi lưu trữ dữ liệu cần được xác minh theo hạ tầng thực tế trước khi công bố.',
  processors_subprocessors: 'Danh sách bên xử lý/bên xử lý phụ cần được phê duyệt và công bố theo hợp đồng hiện hành.',
  public_indexing: 'Phạm vi lập chỉ mục công khai cần quyết định riêng; không mặc định nội dung là public-indexed.',
} as const

const LEGAL_OWNER = 'Chủ quản trị vinhlong360'
const LEGAL_CONTACT = '/lien-he (mục “Dữ liệu cá nhân & pháp lý”)'
const COOKIE_INVENTORY: CookieInventoryItem[] = [
  { name: 'vl360_token', runtimeRole: 'issued', owner: 'vinhlong360', purpose: 'Duy trì phiên đăng nhập OTP.', expiry: '30 ngày (SESSION_EXPIRE_DAYS)', sameSite: 'Lax', secure: 'production-only', httpOnly: true, consentControl: 'Cookie cần thiết; được tạo khi đăng nhập và không dùng cho quảng cáo.', retention: 'Xoá khi đăng xuất hoặc hết hạn phiên.', deletion: { path: '/', sameSite: 'Lax', secure: 'production-only', httpOnly: true } },
  { name: 'token', runtimeRole: 'accepted-legacy', owner: 'vinhlong360', purpose: 'Tên cookie phiên cũ vẫn được đọc và xoá để không giữ phiên cũ sau khi đăng xuất.', expiry: 'Không phát hành mới; nếu còn trên trình duyệt thì tuân theo hạn phiên cũ.', sameSite: 'Lax', secure: 'production-only', httpOnly: true, consentControl: 'Tương thích bắt buộc cho phiên cũ; không dùng cho quảng cáo.', retention: 'Xoá khi đăng xuất; không được phát hành bởi phiên bản hiện tại.', deletion: { path: '/', sameSite: 'Lax', secure: 'production-only', httpOnly: true }, deprecation: 'Alias tương thích cũ; client mới chỉ nhận vl360_token.', expiryDecision: 'Chưa có ngày gỡ bỏ trong runtime; chỉ gỡ đọc/xoá sau quyết định của chủ hệ thống.' },
  { name: 'session_token', runtimeRole: 'accepted-legacy', owner: 'vinhlong360', purpose: 'Tên cookie phiên cũ vẫn được đọc và xoá để không giữ phiên cũ sau khi đăng xuất.', expiry: 'Không phát hành mới; nếu còn trên trình duyệt thì tuân theo hạn phiên cũ.', sameSite: 'Lax', secure: 'production-only', httpOnly: true, consentControl: 'Tương thích bắt buộc cho phiên cũ; không dùng cho quảng cáo.', retention: 'Xoá khi đăng xuất; không được phát hành bởi phiên bản hiện tại.', deletion: { path: '/', sameSite: 'Lax', secure: 'production-only', httpOnly: true }, deprecation: 'Alias tương thích cũ; client mới chỉ nhận vl360_token.', expiryDecision: 'Chưa có ngày gỡ bỏ trong runtime; chỉ gỡ đọc/xoá sau quyết định của chủ hệ thống.' },
  { name: 'vl360_trusted', runtimeRole: 'issued', owner: 'vinhlong360', purpose: 'Ghi nhớ thiết bị đã vượt qua thử thách 2FA.', expiry: '90 ngày', sameSite: 'Lax', secure: 'production-only', httpOnly: true, consentControl: 'Cookie cần thiết, chỉ tạo khi người dùng chọn ghi nhớ thiết bị.', retention: 'Xoá khi hết hạn hoặc người dùng xoá thiết bị tin cậy.', deletion: { path: '/', sameSite: 'Lax', secure: 'production-only', httpOnly: true, mechanism: 'Không có phản hồi xoá cookie riêng; xoá thiết bị sẽ thu hồi bản ghi máy chủ, cookie còn lại tự hết hạn.' } },
  { name: 'vl360_chat_owner', runtimeRole: 'issued', owner: 'vinhlong360', purpose: 'Liên kết phiên khách ẩn danh với lịch sử trò chuyện.', expiry: '365 ngày', sameSite: 'Lax', secure: 'production-only', httpOnly: true, consentControl: 'Cookie cần thiết cho chat ẩn danh; không dùng cho quảng cáo.', retention: 'Xoá khi hết hạn hoặc khi người dùng xoá cookie.', deletion: { path: '/', sameSite: 'Lax', secure: 'production-only', httpOnly: true, mechanism: 'Không có phản hồi xoá cookie riêng; người dùng có thể xoá cookie trong trình duyệt.' } },
  { name: 'vl360_case_access', runtimeRole: 'issued', owner: 'vinhlong360', purpose: 'Cấp quyền truy cập tạm thời vào hồ sơ yêu cầu sửa thông tin.', expiry: '15 phút', sameSite: 'Lax', secure: 'production-only', httpOnly: true, consentControl: 'Cookie cần thiết khi đổi biên nhận hồ sơ; không dùng cho quảng cáo.', retention: 'Tự hết hạn sau 15 phút hoặc bị thu hồi.', deletion: { path: '/api/cases', sameSite: 'Lax', secure: 'production-only', httpOnly: true } },
  { name: 'vl360_case_csrf', runtimeRole: 'issued', owner: 'vinhlong360', purpose: 'Double-submit token chống giả mạo thao tác trên hồ sơ yêu cầu sửa thông tin.', expiry: '15 phút', sameSite: 'Lax', secure: 'production-only', httpOnly: false, consentControl: 'Cookie cần thiết cho bảo vệ biểu mẫu; không dùng cho quảng cáo.', retention: 'Tự hết hạn cùng phiên truy cập hồ sơ hoặc bị xoá khi thu hồi.', deletion: { path: '/api/cases', sameSite: 'Lax', secure: 'production-only', httpOnly: false } },
]
const CHANGE_HISTORY: LegalChange[] = [
  { version: '2026.09', date: '02/09/2026', summary: 'Bổ sung danh mục cookie, đầu mối liên hệ và các mục cần phê duyệt trước khi công bố.' },
  { version: '2026.07', date: '29/07/2026', summary: 'Làm rõ thời hạn lưu trữ và quyền yêu cầu xoá dữ liệu.' },
]

const LEGAL_METADATA: LegalMetadata = {
  policyVersion: '2026.09',
  updatedDate: '02/09/2026',
  owner: LEGAL_OWNER,
  contact: LEGAL_CONTACT,
  cookieInventory: COOKIE_INVENTORY,
  changeHistory: CHANGE_HISTORY,
}

export const policyVersion = LEGAL_METADATA.policyVersion
export const updatedDate = LEGAL_METADATA.updatedDate
export const owner = LEGAL_METADATA.owner
export const contact = LEGAL_METADATA.contact
export const cookieInventory = LEGAL_METADATA.cookieInventory
export const changeHistory = LEGAL_METADATA.changeHistory

export const LEGAL_PRIVACY: LegalDoc = {
  title: 'Chính sách bảo mật',
  updated_date: LEGAL_METADATA.updatedDate,
  seo_title: 'Chính sách bảo mật — vinhlong360',
  seo_description: 'Chính sách bảo mật dữ liệu cá nhân của vinhlong360.vn theo Luật Bảo vệ dữ liệu cá nhân Việt Nam.',
  intro: 'vinhlong360.vn ("chúng tôi") tôn trọng quyền riêng tư của bạn và tuân thủ Luật Bảo vệ dữ liệu cá nhân (Luật 91/2025/QH15) cùng Nghị định 356/2025/NĐ-CP của Việt Nam.',
  ...LEGAL_METADATA,
  sections: [
    {
      heading: '1. Dữ liệu chúng tôi thu thập',
      body: '- **Số điện thoại** — để xác thực đăng nhập bằng OTP.\n- **Tên hiển thị, ảnh đại diện** (tuỳ chọn) — để hiển thị trong cộng đồng.\n- **Nội dung bạn đăng** — bài viết, đánh giá, bình luận, ảnh.\n- **Dữ liệu sử dụng** — truy vấn tìm kiếm/hỏi đáp để cải thiện dịch vụ (ẩn danh khi có thể).',
    },
    {
      heading: '2. Mục đích sử dụng',
      body: 'Xác thực tài khoản, hiển thị nội dung cộng đồng, kiểm duyệt, cải thiện chất lượng tìm kiếm và gợi ý du lịch. Chúng tôi **không bán** dữ liệu cá nhân của bạn.',
    },
    {
      heading: '3. Lưu trữ & bảo mật',
      body: `Dữ liệu được lưu trên hạ tầng có kiểm soát truy cập. Mã OTP được băm (hash), không lưu dạng thô. Chúng tôi giữ dữ liệu trong thời gian cần thiết cho mục đích nêu trên hoặc theo yêu cầu pháp luật.

**Với yêu cầu sửa thông tin**, thời hạn là cụ thể chứ không chung chung:
- **Số điện thoại bạn để lại**: xoá sau **90 ngày** kể từ khi hồ sơ được khép lại.
- **Nội dung riêng tư bạn gửi kèm** (ảnh, tài liệu, giá trị bạn báo): xoá sau **365 ngày**.
- **Liên kết thống kê vận hành**: gỡ danh tính sau **730 ngày**; phần còn lại là số liệu ẩn danh.

Bạn có thể rút lại đồng ý bất cứ lúc nào mà không cần chờ hết thời hạn — xem mục 4.`,
    },
    {
      heading: '4. Quyền của bạn',
      body: `- **Truy cập / chỉnh sửa** thông tin tài khoản — phản hồi trong vòng 10 ngày.\n- **Rút lại đồng ý** — trong vòng 15 ngày.\n- **Xoá tài khoản & dữ liệu** — chậm nhất ${privacyPolicy.accountErasureDeadlineDays} ngày kể từ khi yêu cầu xoá tài khoản. Bạn có thể tự xoá trong phần tài khoản, hoặc gửi yêu cầu qua trang [Liên hệ](/lien-he).`,
    },
    {
      heading: '5. Sự cố dữ liệu',
      body: 'Khi xảy ra rò rỉ dữ liệu cá nhân, chúng tôi thông báo cho cơ quan có thẩm quyền trong vòng 72 giờ và thông báo cho người dùng bị ảnh hưởng theo quy định.',
    },
    {
      heading: '6. Liên hệ',
      body: 'Mọi yêu cầu về dữ liệu cá nhân, vui lòng liên hệ qua trang [Liên hệ](/lien-he).',
    },
  ],
}

export const LEGAL_TERMS: LegalDoc = {
  title: 'Điều khoản sử dụng',
  updated_date: LEGAL_METADATA.updatedDate,
  seo_title: 'Điều khoản sử dụng — vinhlong360',
  seo_description: 'Điều khoản sử dụng nền tảng vinhlong360.vn: tài khoản, nội dung người dùng, báo cáo & gỡ nội dung.',
  intro: 'Khi sử dụng vinhlong360.vn, bạn đồng ý với các điều khoản dưới đây.',
  ...LEGAL_METADATA,
  sections: [
    {
      heading: '1. Tài khoản',
      body: 'Bạn đăng nhập bằng số điện thoại qua mã OTP. Bạn chịu trách nhiệm về hoạt động dưới tài khoản của mình và phải xác thực số điện thoại trước khi đăng nội dung.',
    },
    {
      heading: '2. Nội dung người dùng',
      body: '- Bạn giữ quyền với nội dung mình đăng, nhưng cấp cho chúng tôi quyền hiển thị nội dung đó trên nền tảng.\n- Không đăng nội dung vi phạm pháp luật, sai sự thật, xúc phạm, spam, hoặc xâm phạm bản quyền/quyền riêng tư của người khác.\n- Chúng tôi có quyền gỡ nội dung vi phạm và khoá tài khoản tái phạm.',
    },
    {
      heading: '3. Báo cáo & gỡ nội dung',
      body: `Bạn có thể **báo cáo** nội dung vi phạm bằng nút Báo cáo. Thời gian xử lý phụ thuộc vào mức độ, bằng chứng và nguồn lực tại thời điểm tiếp nhận. Mọi mốc 24/48 giờ là **decisionRequired** — mục tiêu dự kiến đang chờ DPO/luật sư phê duyệt, không phải cam kết dịch vụ.`,
    },
    {
      heading: '4. Nội dung từ nguồn bên thứ ba',
      body: 'Một số thông tin được tổng hợp từ nguồn công khai, có **trích dẫn nguồn và liên kết gốc**. Bản quyền thuộc về tác giả/đơn vị gốc.',
    },
    {
      heading: '5. Miễn trừ trách nhiệm',
      body: 'Thông tin du lịch/đặc sản mang tính tham khảo; giá, giờ mở cửa, mùa vụ có thể thay đổi. Vui lòng kiểm chứng trước khi sử dụng.',
    },
    {
      heading: '6. Liên hệ',
      body: 'Thắc mắc về điều khoản: xem trang [Liên hệ](/lien-he). Xem thêm [Chính sách bảo mật](/chinh-sach-bao-mat).',
    },
  ],
}

export const ABOUT_PAGE: LegalDoc = {
  title: 'Về vinhlong360',
  seo_title: 'Về chúng tôi — vinhlong360',
  seo_description: 'vinhlong360.vn là nền tảng giới thiệu du lịch, đặc sản OCOP và cộng đồng cho tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025) — tổng hợp từ nguồn công khai, có trích dẫn.',
  intro: 'vinhlong360.vn là một dự án độc lập, phi lợi nhuận-định-hướng, do một nhóm nhỏ thực hiện nhằm **giới thiệu** du lịch, đặc sản và đời sống cộng đồng của tỉnh Vĩnh Long hợp nhất — bao gồm 3 khu vực Vĩnh Long, Bến Tre và Trà Vinh (trước 7-2025). Chúng tôi tổng hợp, sắp xếp lại và liên kết tới các nguồn thông tin công khai để người dân và du khách dễ khám phá vùng đất này.',
  ...LEGAL_METADATA,
  // About content has its own reviewed publication date, independent of the
  // privacy/terms release metadata shared for ownership and inventory fields.
  updatedDate: '20/06/2026',
  updated_date: '20/06/2026',
  sections: [
    {
      heading: '1. Sứ mệnh',
      body: 'Giúp mọi người **khám phá tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025) theo cách của người bản địa** — từ điểm đến, lễ hội, lưu trú đến đặc sản theo mùa và sản phẩm OCOP.\n\nChúng tôi muốn thông tin về vùng đất này trở nên dễ tìm, dễ hiểu và đáng tin cậy, đồng thời tôn vinh giá trị văn hoá, ẩm thực và sản vật địa phương.',
    },
    {
      heading: '2. Phạm vi: ba vùng đất',
      body: 'Nội dung tập trung vào **tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025)** gồm:\n- 🍊 **Khu vực Vĩnh Long (trung tâm)** — sông nước, miệt vườn, làng nghề.\n- 🥥 **Khu vực Bến Tre (cũ)** — xứ dừa, cù lao, đặc sản dừa.\n- 🛕 **Khu vực Trà Vinh (cũ)** — văn hoá Khmer, chùa cổ, ẩm thực giao thoa.\n\nMỗi vùng có bản sắc riêng, và chúng tôi cố gắng phản ánh điều đó một cách tôn trọng.',
    },
    {
      heading: '3. Chỉ giới thiệu — không đặt hàng, không thanh toán',
      body: 'vinhlong360.vn là **kênh giới thiệu thông tin**, không phải sàn thương mại điện tử.\n- Chúng tôi **không nhận đặt hàng, đặt phòng (booking) hay thanh toán** trên trang.\n- Chúng tôi **không thu hoa hồng** trên bất kỳ giao dịch nào của bạn với cơ sở.\n- Khi bạn quan tâm một sản phẩm hay dịch vụ, chúng tôi chỉ cung cấp **thông tin liên hệ** (điện thoại, Zalo) để bạn trao đổi trực tiếp với cơ sở.\n\nMọi giao dịch, giá cả và cam kết là **giữa bạn và cơ sở cung cấp**; chúng tôi không phải một bên trong giao dịch đó.',
    },
    {
      heading: '4. Nguồn dữ liệu & tính độc lập',
      body: 'Phần lớn thông tin được **tổng hợp từ các nguồn công khai** (cổng thông tin địa phương, báo chí, tài liệu mở) và đóng góp của cộng đồng.\n- Chúng tôi **trích dẫn nguồn và dẫn liên kết gốc**, không đăng lại nguyên văn các bài báo.\n- Chúng tôi **không sao chép, lưu trữ lại (re-host) nội dung hay hình ảnh có bản quyền**; bản quyền thuộc về tác giả/đơn vị gốc.\n- Thông tin **mùa vụ, giá, giờ mở cửa và địa điểm chỉ mang tính tham khảo** — vui lòng xác nhận với cơ sở hoặc địa phương trước khi sử dụng.\n\nDự án **độc lập về biên tập**; việc một cơ sở được giới thiệu nổi bật (nếu có) sẽ được ghi rõ ràng và không làm thay đổi thông tin khách quan.',
    },
    {
      heading: '5. Cộng đồng & kiểm duyệt',
      body: 'Người dùng có thể đóng góp bài viết, đánh giá, bình luận và hình ảnh.\n- Nội dung do cộng đồng đăng được **kiểm duyệt** nhằm hạn chế sai lệch, spam và vi phạm.\n- Bạn có thể **báo cáo** nội dung không phù hợp bằng nút Báo cáo; chúng tôi xem xét và xử lý các khiếu nại hợp lệ.\n- Vui lòng đóng góp thông tin trung thực và tôn trọng cộng đồng.',
    },
    {
      heading: '6. Bảo mật & pháp lý',
      body: 'Chúng tôi tôn trọng quyền riêng tư của bạn và tuân thủ **quy định pháp luật Việt Nam về bảo vệ dữ liệu cá nhân và nội dung trực tuyến**.\n\nChi tiết về dữ liệu chúng tôi thu thập và quyền của bạn, xem [Chính sách bảo mật](/chinh-sach-bao-mat) và [Điều khoản sử dụng](/dieu-khoan-su-dung).',
    },
    {
      heading: '7. Liên hệ & hợp tác',
      body: 'Bạn là cơ sở muốn được giới thiệu, cập nhật thông tin, hay đề xuất hợp tác quảng bá? Chúng tôi rất mong nhận được phản hồi.\n\nLiên hệ qua trang [Liên hệ](/lien-he) hoặc gửi đề xuất hợp tác để chúng tôi cùng quảng bá vùng đất này tốt hơn.',
    },
  ],
}

/** Merge an admin override (possibly empty/partial) over a default doc. */
export function mergeLegalDoc(override: unknown, def: LegalDoc): LegalDoc {
  const isPlainRecord = (value: unknown): value is Record<string, unknown> => {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) return false
    const prototype = Object.getPrototypeOf(value)
    return prototype === Object.prototype || prototype === null
  }
  const o = isPlainRecord(override) ? override : {}
  const own = (key: string) => Object.hasOwn(o, key) ? o[key] : undefined
  const editableText = (value: unknown, fallback: string) => typeof value === 'string' && value.trim() ? value : fallback
  // Claims in legal copy require a reviewed source change; a CMS editor must
  // not be able to turn an unapproved target, deadline or guarantee into a
  // public promise by replacing the intro or an entire section set.
  const normalizeClaimText = (value: string) => value
    .normalize('NFKC')
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .replace(/\p{Cf}/gu, '')
    .replace(/[\u0000-\u001F\u007F]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  const containsUnapprovedClaim = (value: unknown) => {
    if (typeof value !== 'string') return false
    const normalized = normalizeClaimText(value)
    const folded = normalized.normalize('NFD').replace(/\p{M}/gu, '')
    const compact = folded.toLocaleLowerCase('en-US').replace(/[^\p{L}\p{N}/]+/gu, '')
    return /(?:cam\s*kết|đảm\s*bảo|bảo\s*đảm|đã\s*xác\s*minh|được\s*chứng\s*nhận|tuân\s*thủ\s*hoàn\s*toàn|guarantee(?:d)?|within\s*\d+\s*(?:hours?|days?)|(?:trong\s*vòng|không\s*quá|chậm\s*nhất)\s*\d+\s*(?:giờ|ngày)|\b\d+\s*\/\s*\d+\s*(?:giờ|ngày)?)/iu.test(normalized)
      || /(?:camket|dambao|baodam|daxacminh|duocchungnhan|tuanthuhoantoan|guarantee\w*|within\d+(?:hours?|days?)|trongvong\d+(?:gio|ngay)|khongqua\d+(?:gio|ngay)|chamnhat\d+(?:gio|ngay)|\d+\/\d+(?:gio|ngay)?)/i.test(compact)
  }
  const reviewedText = (value: unknown, fallback: string) => containsUnapprovedClaim(value) ? fallback : editableText(value, fallback)
  const overrideIntro = containsUnapprovedClaim(own('intro')) ? def.intro : editableText(own('intro'), def.intro)
  const candidateSections = own('sections')
  const sectionAddsUnapprovedClaim = (section: { heading: string, body: string }, index: number) => {
    if (containsUnapprovedClaim(section.heading)) return true
    const canonicalSection = def.sections[index]
    if (!canonicalSection) return true
    const canonicalBody = canonicalSection.body
    if (section.body === canonicalBody) return false
    // Canonical sections may contain already-reviewed deadlines/disclaimers.
    // When an editor appends copy, inspect only the added material so those
    // existing claims do not make every otherwise-safe body edit unusable.
    if (section.body.includes(canonicalBody)) {
      return containsUnapprovedClaim(section.body.replace(canonicalBody, ''))
    }
    return containsUnapprovedClaim(section.body)
  }
  const editableSections = Array.isArray(candidateSections) && candidateSections.length > 0
    && candidateSections.length === def.sections.length
    && candidateSections.every((section) => isPlainRecord(section)
      && Object.keys(section).every((key) => key === 'heading' || key === 'body')
      && typeof section.heading === 'string' && section.heading.trim().length > 0
      && typeof section.body === 'string' && section.body.trim().length > 0)
    && candidateSections.every((section, index) => {
      const canonicalSection = def.sections[index]
      return canonicalSection !== undefined && section.heading === canonicalSection.heading
    })
    && !candidateSections.some((section, index) => sectionAddsUnapprovedClaim(section, index))
    ? candidateSections.map(section => ({ heading: section.heading, body: section.body }))
    : def.sections
  return {
    title: reviewedText(own('title'), def.title),
    // Release-owned legal metadata cannot be changed through CMS copy edits.
    updated_date: def.updatedDate,
    seo_title: reviewedText(own('seo_title'), def.seo_title),
    seo_description: reviewedText(own('seo_description'), def.seo_description),
    intro: overrideIntro,
    sections: editableSections,
    // Public legal metadata is governed by the release, never by a free-form
    // CMS override. Updating it requires a reviewed/versioned source change.
    policyVersion: def.policyVersion,
    updatedDate: def.updatedDate,
    owner: def.owner,
    contact: def.contact,
    cookieInventory: def.cookieInventory,
    changeHistory: def.changeHistory,
  }
}

// Stable camelCase metadata views keep legal consumers independent from the
// legacy snake_case CMS document shape.
export const privacy = {
  policyVersion: LEGAL_PRIVACY.policyVersion,
  updatedDate: LEGAL_PRIVACY.updatedDate,
  owner: LEGAL_PRIVACY.owner,
  contact: LEGAL_PRIVACY.contact,
  cookieInventory: LEGAL_PRIVACY.cookieInventory,
  changeHistory: LEGAL_PRIVACY.changeHistory,
  decisionRequired,
}

export const terms = {
  policyVersion: LEGAL_TERMS.policyVersion,
  updatedDate: LEGAL_TERMS.updatedDate,
  owner: LEGAL_TERMS.owner,
  contact: LEGAL_TERMS.contact,
  cookieInventory: LEGAL_TERMS.cookieInventory,
  changeHistory: LEGAL_TERMS.changeHistory,
  decisionRequired,
}

/**
 * Merge an admin override over the About page default. The About page shares the
 * exact LegalDoc shape, so this reuses mergeLegalDoc; kept as a named export so
 * the page reads `mergeAboutDoc(get('page.about', {}), ABOUT_PAGE)` clearly.
 */
export function mergeAboutDoc(override: unknown, def: LegalDoc = ABOUT_PAGE): LegalDoc {
  return mergeLegalDoc(override, def)
}

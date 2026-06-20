// B5 — canonical default content for the legal pages (privacy, terms).
// Stored as { title, updated_date, seo_title, seo_description, intro, sections }
// where intro/section bodies are markdown-lite (rendered via utils/mdLite).
// The CMS stores an override under `legal.privacy` / `legal.terms`; the page
// merges override-over-default so it renders identically until edited, and an
// admin clearing the override reverts to this (legally-reviewed) default.

export interface LegalSection {
  heading: string
  body: string
}
export interface LegalDoc {
  title: string
  updated_date: string
  seo_title: string
  seo_description: string
  intro: string
  sections: LegalSection[]
}

export const LEGAL_PRIVACY: LegalDoc = {
  title: 'Chính sách bảo mật',
  updated_date: '13/06/2026',
  seo_title: 'Chính sách bảo mật — vinhlong360',
  seo_description: 'Chính sách bảo mật dữ liệu cá nhân của vinhlong360.vn theo Luật Bảo vệ dữ liệu cá nhân Việt Nam.',
  intro: 'vinhlong360.vn ("chúng tôi") tôn trọng quyền riêng tư của bạn và tuân thủ Luật Bảo vệ dữ liệu cá nhân (Luật 91/2025/QH15) cùng Nghị định 356/2025/NĐ-CP của Việt Nam.',
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
      body: 'Dữ liệu được lưu trên hạ tầng có kiểm soát truy cập. Mã OTP được băm (hash), không lưu dạng thô. Chúng tôi giữ dữ liệu trong thời gian cần thiết cho mục đích nêu trên hoặc theo yêu cầu pháp luật.',
    },
    {
      heading: '4. Quyền của bạn',
      body: '- **Truy cập / chỉnh sửa** thông tin tài khoản — phản hồi trong vòng 10 ngày.\n- **Rút lại đồng ý** — trong vòng 15 ngày.\n- **Xoá tài khoản & dữ liệu** — trong vòng 20 ngày. Bạn có thể tự xoá trong phần tài khoản, hoặc gửi yêu cầu qua trang [Liên hệ](/lien-he).',
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
  updated_date: '13/06/2026',
  seo_title: 'Điều khoản sử dụng — vinhlong360',
  seo_description: 'Điều khoản sử dụng nền tảng vinhlong360.vn: tài khoản, nội dung người dùng, báo cáo & gỡ nội dung.',
  intro: 'Khi sử dụng vinhlong360.vn, bạn đồng ý với các điều khoản dưới đây.',
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
      body: 'Bạn có thể **báo cáo** nội dung vi phạm bằng nút Báo cáo. Chúng tôi xử lý khiếu nại của người dùng trong vòng 48 giờ và yêu cầu gỡ bỏ từ cơ quan có thẩm quyền trong vòng 24 giờ theo Nghị định 147/2024/NĐ-CP.',
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
  updated_date: '20/06/2026',
  seo_title: 'Về chúng tôi — vinhlong360',
  seo_description: 'vinhlong360.vn là nền tảng giới thiệu du lịch, đặc sản OCOP và cộng đồng cho Vĩnh Long, Bến Tre và Trà Vinh — tổng hợp từ nguồn công khai, có trích dẫn.',
  intro: 'vinhlong360.vn là một dự án độc lập, phi lợi nhuận-định-hướng, do một nhóm nhỏ thực hiện nhằm **giới thiệu** du lịch, đặc sản và đời sống cộng đồng của vùng Vĩnh Long mới — bao gồm Vĩnh Long, Bến Tre và Trà Vinh. Chúng tôi tổng hợp, sắp xếp lại và liên kết tới các nguồn thông tin công khai để người dân và du khách dễ khám phá vùng đất này.',
  sections: [
    {
      heading: '1. Sứ mệnh',
      body: 'Giúp mọi người **khám phá Vĩnh Long, Bến Tre, Trà Vinh theo cách của người bản địa** — từ điểm đến, lễ hội, lưu trú đến đặc sản theo mùa và sản phẩm OCOP.\n\nChúng tôi muốn thông tin về vùng đất này trở nên dễ tìm, dễ hiểu và đáng tin cậy, đồng thời tôn vinh giá trị văn hoá, ẩm thực và sản vật địa phương.',
    },
    {
      heading: '2. Phạm vi: ba vùng đất',
      body: 'Nội dung tập trung vào **vùng Vĩnh Long mới** gồm:\n- 🍊 **Vĩnh Long** — sông nước, miệt vườn, làng nghề.\n- 🥥 **Bến Tre** — xứ dừa, cù lao, đặc sản dừa.\n- 🛕 **Trà Vinh** — văn hoá Khmer, chùa cổ, ẩm thực giao thoa.\n\nMỗi vùng có bản sắc riêng, và chúng tôi cố gắng phản ánh điều đó một cách tôn trọng.',
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
  const o = (override && typeof override === 'object') ? override as Partial<LegalDoc> : {}
  return {
    title: o.title || def.title,
    updated_date: o.updated_date || def.updated_date,
    seo_title: o.seo_title || def.seo_title,
    seo_description: o.seo_description || def.seo_description,
    intro: o.intro || def.intro,
    sections: Array.isArray(o.sections) && o.sections.length ? o.sections : def.sections,
  }
}

/**
 * Merge an admin override over the About page default. The About page shares the
 * exact LegalDoc shape, so this reuses mergeLegalDoc; kept as a named export so
 * the page reads `mergeAboutDoc(get('page.about', {}), ABOUT_PAGE)` clearly.
 */
export function mergeAboutDoc(override: unknown, def: LegalDoc = ABOUT_PAGE): LegalDoc {
  return mergeLegalDoc(override, def)
}

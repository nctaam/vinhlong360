"""
vinhlong360 — Seed default site_settings into Postgres.

Run: python agent/seed_site_settings.py
Requires DATABASE_URL env var pointing to Postgres.
Uses INSERT ... ON CONFLICT DO NOTHING — safe to run multiple times.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

DEFAULTS: dict[str, dict] = {
    # ── Branding ──
    "branding.site_name": {
        "value": "vinhlong360",
        "category": "branding", "label": "Tên trang", "input_type": "text",
        "description": "Tên hiển thị trên logo và tiêu đề",
    },
    "branding.tagline": {
        "value": "Khám phá Vĩnh Long, Bến Tre, Trà Vinh theo cách của người bản địa.",
        "category": "branding", "label": "Slogan", "input_type": "textarea",
        "description": "Dòng mô tả ngắn dưới logo ở footer",
    },
    "branding.og_image": {
        "value": "https://vinhlong360.vn/img/og-default.jpg",
        "category": "branding", "label": "Ảnh OG mặc định", "input_type": "url",
        "description": "Ảnh mặc định khi chia sẻ link (1536x1024)",
    },
    "branding.logo_suffix": {
        "value": ".vn",
        "category": "branding", "label": "Hậu tố logo", "input_type": "text",
        "description": "Phần .vn sau logo",
    },

    # ── SEO ──
    "seo.default_title": {
        "value": "vinhlong360 — Du lịch & Sản phẩm địa phương",
        "category": "seo", "label": "Tiêu đề mặc định", "input_type": "text",
        "description": "Title tag mặc định cho trang chủ",
    },
    "seo.default_description": {
        "value": "Cổng du lịch và sản phẩm địa phương Vĩnh Long: trải nghiệm miệt vườn, đặc sản theo mùa, OCOP, làng nghề và lịch trình gợi ý.",
        "category": "seo", "label": "Mô tả mặc định", "input_type": "textarea",
        "description": "Meta description mặc định",
    },
    "seo.theme_color_light": {
        "value": "#9C3D22",
        "category": "seo", "label": "Theme color (sáng)", "input_type": "color",
        "description": "Màu thanh trạng thái trình duyệt (chế độ sáng)",
    },
    "seo.theme_color_dark": {
        "value": "#1a1a1a",
        "category": "seo", "label": "Theme color (tối)", "input_type": "color",
        "description": "Màu thanh trạng thái trình duyệt (chế độ tối)",
    },

    # ── Navigation ──
    "navigation.nav_groups": {
        "value": [
            {"label": "Khám phá", "children": [
                {"to": "/du-lich", "label": "Du lịch & trải nghiệm"},
                {"to": "/luu-tru", "label": "Lưu trú"},
                {"to": "/theo-mua", "label": "Đặc sản theo mùa"},
                {"to": "/ban-do", "label": "Bản đồ"},
                {"to": "/danh-ba", "label": "Danh bạ hành chính"},
                {"to": "/tuyen-duong", "label": "Tuyến đường gợi ý"},
                {"to": "/le-hoi", "label": "Lễ hội truyền thống"},
                {"to": "/su-kien", "label": "Sự kiện"},
            ]},
            {"label": "Đặc sản", "children": [
                {"to": "/san-pham", "label": "Sản phẩm địa phương"},
                {"to": "/ocop", "label": "Sản phẩm OCOP"},
            ]},
            {"label": "Lịch trình", "children": [
                {"to": "/lich-trinh", "label": "Lịch trình gợi ý"},
                {"to": "/tao-lich-trinh", "label": "Tạo lịch trình"},
                {"to": "/lich-trinh", "label": "Đã lưu ❤️"},
            ]},
            {"label": "Cộng đồng", "to": "/cong-dong"},
        ],
        "category": "navigation", "label": "Menu điều hướng", "input_type": "json",
        "description": "Cấu trúc menu chính (mảng JSON gồm label, to, children)",
    },

    # ── Footer ──
    "footer.tagline": {
        "value": "Khám phá Vĩnh Long, Bến Tre, Trà Vinh\ntheo cách của người bản địa.",
        "category": "footer", "label": "Slogan footer", "input_type": "textarea",
        "description": "Dòng mô tả dưới logo footer",
    },
    "footer.columns": {
        "value": [
            # declutter-2 A3b: 7 link -> 4 curated (đồng bộ DEFAULT_FOOTER_COLUMNS FE;
            # DB prod đã seed thì cập nhật qua AdminCP lúc deploy — ghi chú vận hành).
            {"title": "Gợi ý nhanh", "links": [
                {"to": "/du-lich", "label": "Du lịch & trải nghiệm"},
                {"to": "/san-pham", "label": "Sản phẩm địa phương"},
                {"to": "/theo-mua", "label": "Đặc sản theo mùa"},
                {"to": "/le-hoi", "label": "Lễ hội truyền thống"},
            ]},
            {"title": "Công cụ", "links": [
                {"to": "/ban-do", "label": "Bản đồ"},
                {"to": "/lich-trinh", "label": "Lịch trình gợi ý"},
                {"to": "/tao-lich-trinh", "label": "Tạo lịch trình"},
                {"to": "/danh-ba", "label": "Danh bạ hành chính"},
                {"to": "/cong-dong", "label": "Cộng đồng"},
            ]},
            {"title": "3 vùng", "links": [
                {"to": "/khu-vuc/vinh-long", "label": "🍊 Vĩnh Long"},
                {"to": "/khu-vuc/ben-tre", "label": "🥥 Bến Tre"},
                {"to": "/khu-vuc/tra-vinh", "label": "🛕 Trà Vinh"},
            ]},
            {"title": "Dành cho cơ sở", "links": [
                {"to": "/lien-he?ref=claim", "label": "🏷️ Đăng ký quản lý trang"},
                {"to": "/lien-he", "label": "🤝 Hợp tác quảng bá"},
            ]},
        ],
        "category": "footer", "label": "Cột footer", "input_type": "json",
        "description": "Cấu trúc 4 cột footer (mảng JSON gồm title + links)",
    },
    "footer.copyright": {
        "value": "© 2024–2026 vinhlong360",
        "category": "footer", "label": "Copyright", "input_type": "text",
        "description": "Dòng bản quyền cuối trang",
    },
    "footer.disclaimer": {
        "value": "Thông tin mùa vụ, giá & địa điểm mang tính tham khảo — vui lòng xác nhận với địa phương trước khi sử dụng.",
        "category": "footer", "label": "Tuyên bố miễn trừ", "input_type": "textarea",
        "description": "Dòng disclaimer cuối trang",
    },
    "footer.legal_links": {
        "value": [
            {"to": "/chinh-sach-bao-mat", "label": "Bảo mật"},
            {"to": "/dieu-khoan-su-dung", "label": "Điều khoản"},
            {"to": "/lien-he", "label": "Liên hệ"},
            {"to": "/admin", "label": "Admin"},
        ],
        "category": "footer", "label": "Liên kết pháp lý (đáy trang)", "input_type": "json",
        "description": "Hàng liên kết nhỏ ở đáy footer (mảng JSON gồm to + label)",
    },
    # B8: social links (empty = không hiện hàng MXH ở footer).
    "social.links": {
        "value": [],
        "category": "footer", "label": "Mạng xã hội", "input_type": "json",
        "description": 'Liên kết MXH ở footer (mảng JSON gồm icon emoji, label, url). VD: [{"icon":"📘","label":"Facebook","url":"https://facebook.com/..."}]',
    },

    # ── Homepage ──
    "homepage.hero_subtitle": {
        "value": "Tìm điểm đến, món ngon, lễ hội và lịch trình phù hợp cho chuyến đi Vĩnh Long hôm nay.",
        "category": "homepage", "label": "Hero subtitle", "input_type": "textarea",
        "description": "Dòng mô tả dưới thanh tìm kiếm trang chủ",
    },
    "homepage.search_placeholder": {
        "value": "Tìm điểm đến, món ngon, lịch trình…",
        "category": "homepage", "label": "Placeholder tìm kiếm", "input_type": "text",
        "description": "Placeholder cho ô tìm kiếm trang chủ",
    },
    "homepage.hero_pills": {
        "value": [
            {"emoji": "📍", "label": "Gần tôi", "to": "/ban-do?near=1"},
            {"emoji": "🍲", "label": "Ăn gì hôm nay", "to": "/kham-pha/am-thuc"},
            {"emoji": "🗓️", "label": "Đi 2N1Đ", "to": "/lich-trinh"},
            {"emoji": "🌿", "label": "Miệt vườn", "to": "/du-lich"},
            {"emoji": "🗺️", "label": "Bản đồ", "to": "/ban-do"},
            {"emoji": "🎁", "label": "Đặc sản làm quà", "to": "/ocop"},
        ],
        "category": "homepage", "label": "Quick pills", "input_type": "json",
        "description": "Các nút nhanh dưới hero (mảng JSON gồm emoji, label, to)",
    },
    "homepage.quick_links": {
        "value": [
            {"emoji": "🍊", "label": "Trái cây", "to": "/kham-pha/trai-cay"},
            {"emoji": "🏡", "label": "Homestay", "to": "/kham-pha/homestay"},
            {"emoji": "🛶", "label": "Sông nước", "to": "/kham-pha/song-nuoc"},
            {"emoji": "🧁", "label": "Đặc sản", "to": "/san-pham"},
            {"emoji": "🎭", "label": "Lễ hội", "to": "/le-hoi"},
            {"emoji": "🗺️", "label": "Bản đồ", "to": "/ban-do"},
            {"emoji": "📋", "label": "Lịch trình", "to": "/lich-trinh"},
            {"emoji": "⭐", "label": "OCOP", "to": "/ocop"},
        ],
        "category": "homepage", "label": "Quick links", "input_type": "json",
        "description": "Các liên kết nhanh giữa trang chủ (mảng JSON)",
    },
    "homepage.chatbot_cta_title": {
        "value": "Chưa biết đi đâu?",
        "category": "homepage", "label": "CTA chatbot tiêu đề", "input_type": "text",
        "description": "Tiêu đề khối kêu gọi dùng chatbot",
    },
    "homepage.chatbot_cta_text": {
        "value": "Trợ lý AI sẵn sàng gợi ý địa điểm, đặc sản, lịch trình phù hợp với bạn.",
        "category": "homepage", "label": "CTA chatbot nội dung", "input_type": "textarea",
        "description": "Nội dung mô tả chatbot",
    },
    # A7: admin override cho tagline mùa (backend public_api đọc khi build homepage).
    # Object {"1".."12": "text"}; để trống = dùng mặc định trong code.
    "homepage.seasonal_taglines": {
        "value": {},
        "category": "homepage", "label": "Tagline theo tháng", "input_type": "json",
        "description": 'Ghi đè dòng tagline mùa trên trang chủ. VD: {"6": "Mùa trái cây..."}',
    },

    # ── Contact ──
    "contact.email": {
        "value": "lienhe@vinhlong360.vn",
        "category": "contact", "label": "Email liên hệ", "input_type": "text",
        "description": "Email chính hiển thị trên trang liên hệ",
    },
    "contact.zalo": {
        "value": "vinhlong360",
        "category": "contact", "label": "Zalo", "input_type": "text",
        "description": "Tên Zalo OA hoặc số điện thoại",
    },
    "contact.claim_email": {
        "value": "lienhe@vinhlong360.vn",
        "category": "contact", "label": "Email claim", "input_type": "text",
        "description": "Email nhận yêu cầu xác nhận quyền quản lý",
    },

    # ── Announcements ──
    "announcements.enabled": {
        "value": True,
        "category": "announcements", "label": "Hiện banner", "input_type": "toggle",
        "description": "Bật/tắt banner thông báo trên đầu trang",
    },
    "announcements.icon": {
        "value": "🚧",
        "category": "announcements", "label": "Icon", "input_type": "text",
        "description": "Emoji/icon đầu thông báo",
    },
    "announcements.text": {
        "value": "Trang đang trong giai đoạn xây dựng.",
        "category": "announcements", "label": "Nội dung chính", "input_type": "text",
        "description": "Dòng chữ đậm trong banner",
    },
    "announcements.subtext": {
        "value": "Một số tính năng có thể chưa hoàn thiện hoặc thay đổi. Cảm ơn bạn đã ghé thăm!",
        "category": "announcements", "label": "Nội dung phụ", "input_type": "textarea",
        "description": "Dòng mô tả phụ trong banner",
    },

    # ── Chat widget ──
    "chat.title": {
        "value": "Hỏi về Vĩnh Long",
        "category": "chat", "label": "Tiêu đề chat", "input_type": "text",
        "description": "Tiêu đề hiển thị trên cửa sổ chat",
    },
    "chat.placeholder": {
        "value": "Hỏi gì đó về Vĩnh Long…",
        "category": "chat", "label": "Placeholder chat", "input_type": "text",
        "description": "Placeholder cho ô nhập tin nhắn chat",
    },
    # B6: chat/AI config (frontend reads with inline fallback; empty = dùng mặc định).
    "chat.disclaimer": {
        "value": "Nội dung do AI tạo, có thể chưa chính xác — vui lòng kiểm chứng.",
        "category": "chat", "label": "Dòng minh bạch AI (chat)", "input_type": "text",
        "description": "Dòng nhỏ dưới ô chat nhắc nội dung do AI tạo. Để trống = ẩn.",
    },
    "chat.suggestions_by_route": {
        "value": {},
        "category": "chat", "label": "Gợi ý câu hỏi theo trang", "input_type": "json",
        "description": 'JSON {"/du-lich": ["..."], "default": ["..."]} — câu hỏi gợi ý theo route. Để trống {} = dùng bộ mặc định.',
    },
    "ai.disclaimer_text": {
        "value": "Gợi ý do AI tạo — mang tính tham khảo.",
        "category": "ai", "label": "Dòng minh bạch AI (khối gợi ý)", "input_type": "text",
        "description": "Hiển thị dưới các khối gợi ý AI (mẹo, thời điểm, tìm kiếm). Để trống = ẩn.",
    },

    # ── Theme ──
    "theme.primary_color": {
        "value": "",
        "category": "theme", "label": "Màu chính (primary)", "input_type": "color",
        "description": "Ghi đè CSS --primary (để trống = dùng mặc định)",
    },
    "theme.accent_color": {
        "value": "",
        "category": "theme", "label": "Màu nhấn (accent)", "input_type": "color",
        "description": "Ghi đè CSS --accent (để trống = dùng mặc định)",
    },
    "theme.secondary_color": {
        "value": "",
        "category": "theme", "label": "Màu phụ (secondary)", "input_type": "color",
        "description": "Ghi đè CSS --secondary (để trống = dùng mặc định)",
    },
    # B8: theme depth (validated client-side; để trống = dùng mặc định).
    "theme.radius": {
        "value": "",
        "category": "theme", "label": "Độ bo góc", "input_type": "text",
        "description": "Độ bo góc giao diện, vd 14px / 8px / 1rem (để trống = mặc định)",
    },
    "theme.font_scale": {
        "value": "",
        "category": "theme", "label": "Tỉ lệ cỡ chữ", "input_type": "text",
        "description": "Hệ số cỡ chữ toàn trang 0.8–1.3, vd 1.05 (để trống = 1.0)",
    },

    # ── Features (A4) ──
    # {flagKey: bool}. Empty = all flags use their registry default (true).
    # Defaults live in web-nuxt/utils/featureFlags.ts; edited via toggle grid.
    "features.flags": {
        "value": {},
        "category": "features", "label": "Cờ tính năng", "input_type": "json",
        "description": "Bật/tắt khối nội dung (sửa qua /admin/cai-dat/tinh-nang)",
    },

    # ── Page content (A2) ──
    # One key per page; value = {field: override}. Empty by default — the
    # canonical defaults live in web-nuxt/utils/pageManifest.ts. The frontend
    # falls back to those when a field is absent/empty, so the page renders
    # identically until an admin overrides something. (upsert is UPDATE-only,
    # so the key must be seeded for the admin editor to save into it.)
    "page.du_lich": {
        "value": {},
        "category": "page", "label": "Trang: Du lịch", "input_type": "json",
        "description": "Hero & SEO trang Du lịch (sửa qua /admin/cai-dat/trang)",
    },
    "page.ocop": {"value": {}, "category": "page", "label": "Trang: OCOP", "input_type": "json", "description": "Hero & SEO trang OCOP"},
    "page.san_pham": {"value": {}, "category": "page", "label": "Trang: Đặc sản", "input_type": "json", "description": "Hero & SEO trang Đặc sản"},
    "page.luu_tru": {"value": {}, "category": "page", "label": "Trang: Lưu trú", "input_type": "json", "description": "Hero & SEO trang Lưu trú"},
    "page.le_hoi": {"value": {}, "category": "page", "label": "Trang: Lễ hội", "input_type": "json", "description": "Hero & SEO trang Lễ hội"},
    "page.su_kien": {"value": {}, "category": "page", "label": "Trang: Sự kiện", "input_type": "json", "description": "Hero & SEO trang Sự kiện"},
    "page.theo_mua": {"value": {}, "category": "page", "label": "Trang: Theo mùa", "input_type": "json", "description": "Hero & SEO trang Theo mùa (để trống = tự điền tháng)"},
    "page.danh_ba": {"value": {}, "category": "page", "label": "Trang: Danh bạ", "input_type": "json", "description": "Hero & SEO trang Danh bạ hành chính"},
    "page.tuyen_duong": {"value": {}, "category": "page", "label": "Trang: Tuyến đường", "input_type": "json", "description": "Hero & SEO trang Tuyến đường gợi ý"},
    "page.cong_dong": {"value": {}, "category": "page", "label": "Trang: Cộng đồng", "input_type": "json", "description": "Tiêu đề & SEO trang Cộng đồng"},
    "page.tim_kiem": {"value": {}, "category": "page", "label": "Trang: Tìm kiếm", "input_type": "json", "description": "Hero & SEO trang Tìm kiếm (SEO động theo từ khoá)"},
    "page.lien_he": {"value": {}, "category": "page", "label": "Trang: Liên hệ", "input_type": "json", "description": "Hero & SEO trang Liên hệ"},
    # B2: route data for /tuyen-duong. Empty = use defaults in web-nuxt/utils/routesContent.ts
    # (admin editor pre-fills from those). Edited as JSON (nested stops[] per route).
    "tuyen_duong.routes": {"value": [], "category": "page", "label": "Tuyến đường (dữ liệu)", "input_type": "json", "description": "Danh sách tuyến đường gợi ý (JSON; mỗi tuyến có stops[] lồng nhau). Sửa qua /admin/cai-dat/tuyen-duong"},

    # ── Legal (B5) ──
    # {title, updated_date, seo_title, seo_description, intro, sections:[{heading,body}]}.
    # Empty = use the legally-reviewed defaults in web-nuxt/utils/legalContent.ts.
    # Bodies are markdown-lite (rendered XSS-safe via utils/mdLite).
    "legal.privacy": {"value": {}, "category": "legal", "label": "Chính sách bảo mật", "input_type": "json", "description": "Nội dung trang /chinh-sach-bao-mat (sửa qua /admin/cai-dat/phap-ly)"},
    "legal.terms": {"value": {}, "category": "legal", "label": "Điều khoản sử dụng", "input_type": "json", "description": "Nội dung trang /dieu-khoan-su-dung (sửa qua /admin/cai-dat/phap-ly)"},

    # ── Onboarding (B7) ──
    # {emoji,title,intro,features:[{icon,title,desc}],cta_*}. Empty = defaults in
    # web-nuxt/utils/onboardingContent.ts. Gated by features.flags.onboarding.
    "onboarding": {"value": {}, "category": "onboarding", "label": "Bảng chào mừng", "input_type": "json", "description": "Nội dung onboarding khách lần đầu (sửa qua /admin/cai-dat/chao-mung)"},

    # ── Categories ──
    "categories.type_overrides": {
        "value": {},
        "category": "categories", "label": "Ghi đè loại entity", "input_type": "json",
        "description": "JSON object ghi đè emoji/label cho từng entity type",
    },
    "categories.area_overrides": {
        "value": {},
        "category": "categories", "label": "Ghi đè khu vực", "input_type": "json",
        "description": "JSON object ghi đè emoji/label cho từng area",
    },
    # B4: metadata maps (merged in useConstants via site-overrides plugin).
    "metadata.office_kind": {
        "value": {},
        "category": "categories", "label": "Ghi đè loại cơ quan (danh bạ)", "input_type": "json",
        "description": 'Ghi đè emoji/label loại cơ quan công vụ. VD: {"ubnd": {"label": "UBND phường"}}',
    },
    "metadata.interests": {
        "value": {},
        "category": "categories", "label": "Ghi đè chủ đề khám phá", "input_type": "json",
        "description": 'Ghi đè/thêm chủ đề /kham-pha. VD: {"am-thuc": {"label": "Ẩm thực miền Tây"}}. Thêm mới cần đủ emoji, label, description, types[].',
    },
}

if __name__ == "__main__":
    from site_settings import seed_defaults
    count = seed_defaults(DEFAULTS)
    print(f"Seeded {count} settings (skipped existing).")
    total = len(DEFAULTS)
    print(f"Total defined: {total}")

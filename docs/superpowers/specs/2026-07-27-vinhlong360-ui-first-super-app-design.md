# vinhlong360 UI-first Super App Design

> STATUS: draft-for-review - snapshot 2026-07-27.

> Nền tảng thị giác, kết quả rà soát dấu hiệu giao diện do AI tạo hàng loạt và đặc tả bốn pilot đã được mở rộng trong `2026-07-27-vinhlong360-professional-ui-research-design.md`. Khi có khác biệt, tài liệu chuyên sâu này được ưu tiên cho định hướng thị giác, token, shell và pilot P1.

## 1. Mục tiêu

Nâng cấp và hoàn thiện giao diện toàn bộ vinhlong360 trước khi triển khai các năng lực UX/super app nâng cao. UI mới phải có bản sắc riêng, nhất quán trên toàn hệ thống, hỗ trợ cả người địa phương và khách du lịch, đồng thời giữ nguyên hành vi, route, API, SEO policy và quyền truy cập hiện tại.

Chiến lược được chốt:

- Một ứng dụng, một tài khoản, một bản đồ và một Local Life Graph.
- Không tách mode người địa phương/khách du lịch ở giai đoạn UI-first.
- Homepage và navigation có thể thích ứng theo context, nhưng không thay đổi cấu trúc điều hướng cốt lõi.
- Hoàn thiện UI trước; personalization, intent router, Authority Portal, Partner Portal và AI orchestration triển khai sau.
- Không thêm marketplace, thanh toán hoặc booking engine trong wave UI-first.

## 2. Bối cảnh hiện tại

Baseline code hiện hành:

- Frontend chính: Nuxt 4/Vue 3 trong `web-nuxt/`.
- 68 page template: 36 trang public/private và 32 trang AdminCP.
- 12 layout family đã được kiểm kê.
- 10 template có segment động hoặc catch-all.
- Backend FastAPI hiện có các miền auth, public API, plans, saved, visits, social, notifications, achievements, admin và SEO.
- Admin backend có các scope `content.editor`, `moderation.manager`, `ops.deploy`, `settings.admin`, `security.admin`.

Không thay đổi thư mục legacy `web/`, API contract hoặc launch indexing policy trong phạm vi này.

## 3. Visual direction

Visual direction mặc định cho wave UI-first là **Mekong Editorial Atlas + Civic Utility**:

- Editorial và giàu hình ảnh ở các trang khám phá, địa điểm, đặc sản và hành trình.
- Rõ ràng, đáng tin và có mật độ cao vừa phải ở danh bạ, dịch vụ và AdminCP.
- Lấy cảm hứng từ bản đồ, dòng sông, địa bàn và chất liệu địa phương ở mức trừu tượng; không dùng motif dân gian trực tiếp hoặc sáo mòn.
- Typography có character nhưng phải hỗ trợ đầy đủ tiếng Việt, nội dung dài và số liệu.
- Ảnh thật, nguồn ảnh và nội dung địa phương được ưu tiên hơn minh họa stock hoặc copy giả.
- Một signature module cho mỗi layout family; không dùng cùng công thức hero/card/grid cho mọi trang.

Các giá trị màu, font cụ thể sẽ được chốt trong foundation pass sau khi kiểm tra contrast và font rendering tiếng Việt.

## 4. Nguyên tắc UI-first

### 4.1 UI-first không phải UI-only

Trước mỗi layout vẫn phải khóa UX skeleton tối thiểu:

- Mục tiêu chính của route.
- Primary action.
- Thứ tự thông tin.
- Navigation context.
- Guest/auth/private/admin state.
- Loading, empty, error, stale và forbidden state.
- Mobile composition.

Không triển khai đầy đủ personalization, intent routing hoặc AI orchestration trong wave này.

### 4.2 Giữ behavior hiện tại

- Giữ route hiện tại và deep link.
- Giữ API và dữ liệu hiện tại.
- Giữ auth/session behavior.
- Giữ noindex/canonical/crawl policy.
- Giữ các hành động gọi điện, Zalo, chỉ đường, lưu, theo dõi, báo sai và chia sẻ.
- Không để UI hiển thị tính năng chưa có backend như đã hoạt động.

### 4.3 Chống giao diện đại trà

- Không lạm dụng card bo tròn, pill, badge, glass hoặc gradient.
- Không dùng một layout hero → ba card → stats → CTA cho mọi page.
- Không tạo số liệu, testimonial, lượt xem hoặc social proof giả.
- Không dùng màu tím/xanh hoặc font mặc định nếu không có lý do thương hiệu.
- Không thêm animation chỉ để trang trông “sống động”.
- Không để component mới xuất hiện nếu component hiện có đủ khả năng.

## 5. Foundation system

Foundation sử dụng kiến trúc ba lớp:

```text
Primitive tokens
        ↓
Semantic tokens
        ↓
Component tokens
```

Phạm vi foundation:

- Color roles: brand, primary, secondary, accent, surface, text, border, success, warning, error.
- Light, dark, high-contrast và forced-colors.
- Typography scale cho display, body, label, data và admin chrome.
- Font fallback có metric tương thích với tiếng Việt.
- Spacing 4px base, rhythm nhất quán.
- Radius, border, shadow và elevation theo semantic role.
- Motion 150-300ms, tôn trọng `prefers-reduced-motion`.
- Focus ring bằng `outline`, không phụ thuộc shadow.
- Container, grid và content measure theo layout family.

Mọi component chỉ tiêu thụ semantic/component token; không đặt màu, spacing hoặc radius ngẫu nhiên trong page.

## 6. Adaptive Experience Shell

### 6.1 Desktop shell

- Brand.
- Universal search.
- Context/location control.
- Trang chủ, Khám phá, Gần bạn, Cộng đồng, Lịch trình.
- Notification bell.
- User menu.
- Contextual action rail.

Danh bạ, sự kiện, OCOP, đặc sản và lưu trú nằm trong nhóm khám phá/ngữ cảnh, không chiếm chỗ navigation chính.

### 6.2 Mobile shell

Bottom navigation:

1. Trang chủ.
2. Khám phá.
3. Gần bạn.
4. Cộng đồng.
5. Cá nhân.

Search mở toàn màn hình; lịch trình, đã lưu, thông báo và cài đặt nằm trong workspace cá nhân nhưng vẫn có contextual action từ các trang khác.

### 6.3 Admin shell

AdminCP giữ layout riêng, với navigation theo scope:

- Control Center.
- Local Life Operations.
- Content & Entity Graph.
- Trust & Moderation.
- Authorities & Partners (future surface).
- AI & Search.
- Data Quality.
- Users & Security.
- Settings & Design System.

Frontend guard phải khớp backend scope; moderator không bị chặn khỏi các surface moderation hợp lệ và không thấy các menu ngoài quyền.

## 7. Homepage UI-first

Homepage là composition hữu hạn, không phải feed vô hạn:

```text
Context bar
        ↓
Thông tin cần biết ngay
        ↓
Gần bạn
        ↓
Sự kiện và tiện ích
        ↓
Cộng đồng có nguồn rõ
        ↓
Khám phá theo sở thích
        ↓
AI/search entry point (UI shell trước, orchestration sau)
```

Quy tắc:

- Module không có dữ liệu thì biến mất hoặc thu gọn.
- Cảnh báo chính thức không bị nội dung cộng đồng đẩy xuống.
- Mỗi vùng có giới hạn item và diversity budget.
- Có `Vì sao bạn thấy nội dung này`, đổi khu vực, tắt vị trí và reset đề xuất ở UI.
- UI chỉ mô phỏng context bằng dữ liệu hiện tại; ranking nâng cao triển khai sau.

## 8. Layout family và thứ tự triển khai

### P0 — Foundation và shell

- Tokens và typography.
- Public header/footer.
- Mobile navigation.
- Universal search shell.
- Auth modal.
- Notification/user menu.
- Admin shell.
- Modal, toast, confirm, focus và error boundary.

### P1 — Pilot surfaces

Triển khai và kiểm chứng bốn route:

- `/` — homepage.
- `/du-lich` — catalog.
- `/dia-diem/[id]` — entity detail.
- `/admin` — operations dashboard.

P1 phải xác nhận visual direction, typography, density, component anatomy, responsive behavior, dark mode và state system.

### P2 — Public discovery

- Catalog: `/dia-diem`, `/san-pham`, `/ocop`, `/luu-tru`, `/le-hoi`, `/su-kien`, `/theo-mua`.
- Map/directory: `/ban-do`, `/danh-ba`, `/xa-phuong/[id]`.
- Region/interest: `/khu-vuc/[area]`, `/kham-pha/[interest]`.
- Editorial/trust: `/gioi-thieu`, `/huong-dan`, `/lien-he`, legal pages.

### P3 — Journey và community

- `/tim-kiem`.
- `/lich-trinh`, `/tao-lich-trinh` và shared plan.
- `/cong-dong`, `/bai-viet/[id]`, `/nguoi-dung/[id]`, `/bang-xep-hang`.
- Report, gallery, map popup, save/share/add-to-plan states.

### P4 — Personal workspace

- `/tai-khoan`.
- `/cai-dat` và 9 tab.
- `/da-luu`.
- `/thong-bao`.

### P5 — AdminCP hoàn thiện

- Dashboard/AI/stats/audit.
- Entities và 9 kind views.
- Moderation, reports, users.
- Data quality, media, image review, self-learning review.
- Settings hub và 12 page CMS contexts.

## 9. UX skeleton bắt buộc cho mỗi page spec

Mỗi page trước khi triển khai UI phải có:

- Route.
- Access và RBAC scope.
- SEO policy.
- Layout family.
- Primary goal.
- Primary action.
- Data/API hiện tại.
- Guest/auth variants.
- Loading/empty/error/stale/forbidden.
- Mobile composition.
- Dark/high-contrast behavior.
- Reusable components.
- Analytics event cho primary action.

## 10. QA và acceptance gates

### Visual

- Screenshot desktop 1440px.
- Tablet khoảng 1024px.
- Mobile 390px.
- Light/dark/high-contrast.
- Không có layout shift bất ngờ.
- Không có component lặp sai family.

### Accessibility

- Keyboard navigation.
- Visible focus.
- Screen-reader landmark.
- Contrast đạt chuẩn.
- Text zoom 200%.
- Vietnamese diacritics không va dòng.
- Reduced motion.

### Technical

- `typecheck` và tests hiện có không regress.
- Giữ route/API/SEO policy.
- Không phát sinh console error.
- Ảnh/font có budget.
- Loading/error state không chặn toàn app.
- Không thay đổi quyền truy cập ngoài spec.

### Product

- Người dùng hiểu mục tiêu page trong viewport đầu.
- Primary action nhìn thấy và có trạng thái rõ.
- Gọi/Zalo/chỉ đường/lưu hoạt động trên các surface liên quan.
- “Vì sao bạn thấy nội dung này” và privacy controls có UI đầy đủ.
- Admin task không bị biến thành dashboard trang trí.

## 11. Out of scope cho wave UI-first

- Marketplace, booking và thanh toán.
- Authority/Partner Portal production behavior.
- Ranking/personalization engine đầy đủ.
- Intent router và AI action orchestration production.
- Thay đổi schema backend lớn.
- Tách microservices.
- Xóa route hiện tại.

Các surface tương lai có thể được mô tả bằng placeholder/state disabled, nhưng không được giả vờ là tính năng đã hoạt động.

## 12. Deliverables

- UI direction board và visual principles.
- Token specification.
- Component inventory và state matrix.
- Adaptive Experience Shell specification.
- 4 pilot page specs.
- 12 layout family specs.
- Route-to-family mapping cho 68 template.
- Figma library hoặc equivalent component reference.
- Code component contract cho Nuxt/Vue.
- Visual QA checklist và screenshot baseline.
- Roadmap UX/super app sau khi UI hoàn tất.

## 13. Decision gates

1. Duyệt visual direction và foundation.
2. Duyệt shell và bốn pilot.
3. Duyệt layout family trước khi mở rộng 68 page.
4. Duyệt visual QA baseline.
5. Sau khi UI ổn định mới triển khai personalization, Local Life Graph runtime, portals và AI orchestration.

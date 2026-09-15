# docs/ — Bản đồ Tài liệu & Chỉ mục Kỹ thuật Hệ thống Vĩnh Long 360

Authority: config/release-authority.json

> **STATUS: active (2026-09-15) — nguồn định hướng tài liệu duy nhất.**  
> Đồng bộ hóa toàn diện sau đợt tổng thanh lọc tài liệu và kiểm toán mã nguồn tháng 09/2026 (Milestone 2).  
> **Quy tắc hiệu lực:** Khi có bất kỳ mâu thuẫn nào giữa các tài liệu trong kho lưu trữ:  
> 1. `CLAUDE.md` là **Hiến pháp tối cao** (định vị 1 dòng, quyết định đã chốt §1, bất biến B1–B8 §2).  
> 2. `docs/README.md` là **Bản đồ chỉ mục định hướng duy nhất**.  
> 3. Các tài liệu chuyên môn bắt buộc phải có header `> STATUS: active`. Mọi tài liệu không có nhãn active hoặc nằm trong danh mục đã thanh lọc (purged) đều không có giá trị thi hành.

---

## Bắt đầu từ đâu? (Quick Navigation)

| Bạn muốn làm gì? | Tài liệu chỉ đạo bắt buộc |
|---|---|
| **Hiểu Hiến pháp, Bất biến & Luật chơi** | [`../CLAUDE.md`](../CLAUDE.md) *(Định vị tỉnh mới, 8 bất biến B1–B8, điều kiện dừng)* |
| **Nắm bắt Kiến trúc & Các quyết định chốt (ADR)** | [`architecture-decisions.md`](architecture-decisions.md) *(ADR 1–6: DB-as-SoT, Nuxt SSR, Postgres UGC, Ảnh AI)* |
| **Quy chuẩn Thiết kế, Anti-Slop & Bảng màu Tam Vùng** | [`../web-nuxt/DESIGN.md`](../web-nuxt/DESIGN.md) + [`design-rulebook.md`](design-rulebook.md) |
| **Bộ tiêu chuẩn kỹ thuật có chế tài ("có răng")** | [`standards/00-INDEX.md`](standards/00-INDEX.md) *(Bảng tổng 38 rules: Hard, Ratchet, Soft)* |
| **Hợp đồng dữ liệu Backend ↔ Frontend** | [`api-contract.md`](api-contract.md) *(18 entity types, Auth, Admin, Terroir RFC 7807)* |
| **Tra cứu danh mục 124 xã/phường chuẩn** | [`don-vi-hanh-chinh-vinh-long.md`](don-vi-hanh-chinh-vinh-long.md) *(35 phường + 89 xã, 0 cấp huyện)* |
| **Đối chiếu ngày âm–dương 67 lễ hội** | [`2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md`](2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md) |
| **Lộ trình kỹ thuật dài hạn & Sổ theo dõi nợ** | [`ROADMAP.md`](ROADMAP.md) *(Sổ track tiến độ dài hạn & Backlog)* |
| **Hồ sơ Quyết định thẩm quyền phát hành** | [`decisions/README.md`](decisions/README.md) *(QD-01 đến QD-06 & Owner Signoff)* |
| **Cài đặt môi trường lập trình local** | [`developer-setup.md`](developer-setup.md) *(FastAPI, Nuxt, Docker Postgres, biến `HAS_*`)* |
| **Triển khai VPS & Vận hành Production** | [`deployment-guide.md`](deployment-guide.md) + [`runbooks/`](runbooks/) |
| **Bảo mật hạ tầng & Rà soát OWASP Top 10** | [`security-hardening.md`](security-hardening.md) + [`security/owasp-review-2026-08-05.md`](security/owasp-review-2026-08-05.md) |
| **Quy trình ứng phó sự cố khẩn cấp** | [`incident-runbook.md`](incident-runbook.md) + [`runbooks/`](runbooks/) |
| **Báo cáo kiểm toán dữ liệu & Đồ thị tri thức** | [`reports/2026-09-12-comprehensive-data-audit-report.md`](reports/2026-09-12-comprehensive-data-audit-report.md) |
| **Biên tập nội dung di sản & Chống AI-Slop** | [`content-creation-guide.md`](content-creation-guide.md) + [`toi-uu-chong-ai-va-google-spam-playbook.md`](toi-uu-chong-ai-va-google-spam-playbook.md) |
| **Tra cứu thổ nhưỡng & Dữ liệu văn hóa địa chí** | [`research/corpus-van-hoa-du-lich-vl-2026-06.md`](research/corpus-van-hoa-du-lich-vl-2026-06.md) |
| **Chạy nhiều phiên làm việc song song** | [`parallel-session-guide.md`](parallel-session-guide.md) *(Kỷ luật cô lập worktree)* |

---

## Bản Đồ Tài Liệu Hoạt Động (Active Technical Documentation Map)

### 1. Kiến Trúc, ADRs & Quy Chuẩn Nền Tảng

Nhóm tài liệu định hình toàn bộ khung pháp lý kỹ thuật, cấu trúc phân tầng và nguyên lý bất biến của hệ sinh thái:

- **[`../CLAUDE.md`](../CLAUDE.md)**: Hiến pháp dự án. Định nghĩa bối cảnh 1 dòng (tỉnh Vĩnh Long mới sáp nhập 3 tỉnh cũ, 124 xã/phường, 0 cấp huyện), 7 quyết định chốt không đổi (§1), 8 bất biến B1–B8 (§2), danh mục lệnh hay dùng (§3) và điều kiện dừng (§4).
- **[`../PROJECT.md`](../PROJECT.md)**: Tổng quan kiến trúc kho mã nguồn, phân định ranh giới giữa các module (`agent/`, `web-nuxt/`, `scripts/`, `docs/`) và quy ước làm việc.
- **[`architecture-decisions.md`](architecture-decisions.md)**: Hồ sơ Quyết định Kiến trúc (Architecture Decision Records — ADR):
  - *ADR-1:* SQLite `vinhlong360.db` làm cơ sở dữ liệu nền tảng Single Source of Truth (SSOT), ở chế độ read-only bit-for-bit.
  - *ADR-2:* Kiến trúc đơn giao diện Nuxt 3 (SSR + Nitro) kiêm API server nội bộ, triệt tiêu phân mảnh kiến trúc.
  - *ADR-3:* PostgreSQL dành riêng cho dữ liệu người dùng (UGC) và lưu trữ trạng thái có thể ghi.
  - *ADR-4:* 100% hình ảnh do AI tự tạo theo prompt bản địa, nghiêm cấm cào hoặc hotlink ảnh bên thứ ba.
  - *ADR-5:* Định vị địa lý hành chính 2 cấp (1 tỉnh -> 124 xã/phường).
  - *ADR-6:* Quản trị phân tầng kiểm soát chất lượng (Hard / Ratchet / Soft) và quy chế ngoại lệ có thẩm quyền.
- **[`ROADMAP.md`](ROADMAP.md)**: Sổ theo dõi tiến độ dài hạn và backlog kỹ thuật. Ghi nhận các giai đoạn thi công đã hoàn tất và các hạng mục theo dõi nợ kỹ thuật.
- **[`api-contract.md`](api-contract.md)**: Hợp đồng giao tiếp dữ liệu giữa backend FastAPI (`agent/`) và frontend Nuxt (`web-nuxt/`): đặc tả 18 entity types, phân trang chuẩn, định dạng lỗi RFC 7807, cơ chế xác thực `/auth/*`, quản trị `/admin/*` và cổng dữ liệu mở `/api/v1/terroir/*`.
- **[`don-vi-hanh-chinh-vinh-long.md`](don-vi-hanh-chinh-vinh-long.md)**: Bảng tra cứu mã định danh và tên gọi chính thức của 124 xã/phường mới (35 phường + 89 xã) thuộc tỉnh Vĩnh Long sáp nhập.
- **[`2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md`](2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md)**: Ma trận đối chiếu 6 trường ngày tháng (lịch âm, lịch dương, ngày hội cố định/di động) cho 67 sự kiện và lễ hội truyền thống.
- **[`implementation-specs.md`](implementation-specs.md)**: Đặc tả kỹ thuật chi tiết phục vụ triển khai tính năng frontend và backend.
- **[`../TEST_INFRA.md`](../TEST_INFRA.md)**: Cẩm nang hạ tầng kiểm thử toàn diện, quy định temp-root ngắn cho Windows (`C:\vlt`) và phối hợp kiểm thử liên tầng.
- **[`../TEST_READY.md`](../TEST_READY.md)**: Bộ tiêu chuẩn nghiệm thu kiểm thử tự động trước khi triển khai sản xuất.

### 2. Thiết Kế, Mỹ Thuật Biên Tập & Chuẩn Tiếp Cận

- **[`../web-nuxt/DESIGN.md`](../web-nuxt/DESIGN.md)**: Hiến pháp Thiết Kế Master — Quy định phong cách biên tập di sản sông nước Mekong:
  - Cặp phông chữ ấn loát Lora (tiêu đề/dẫn chuyện) và Be Vietnam Pro (giao diện/thân văn).
  - Hệ thống Token Thổ nhưỡng Tam Vùng: Phù sa sông Tiền (Riverside Amber), Đất sét Mang Thít (Heritage Terracotta), Dừa Bến Tre (Canopy Palm Green).
  - Nhịp thở Fibonacci (8 · 13 · 21 · 34 · 55 · 89) và Liquid Glass bán trong suốt.
  - Đồng bộ hóa 1:1 với dự án Google Stitch MCP (`14916181929760067680`).
- **[`design-rulebook.md`](design-rulebook.md)**: Quy tắc chi tiết về cấu trúc lưới bất đối xứng, khoảng cách vi phân và độ tương phản WCAG 2.2 AAA (>= 7:1 tiêu đề, >= 4.5:1 thân văn), touch target >= 44x44px.
- **[`design-guidelines-apple-google-figma.md`](design-guidelines-apple-google-figma.md)**: Tài liệu đối chuẩn quy chuẩn quốc tế (Apple Human Interface Guidelines, Google Material Design 3, Figma Design Tokens).
- **[`travel-platform-ux-research.md`](travel-platform-ux-research.md)**: Nghiên cứu đối chuẩn 5 nền tảng văn hóa du lịch hàng đầu thế giới (Rijksmuseum, National Geographic, Visit Oslo, Monocle).

### 3. Tiêu Chuẩn Kỹ Thuật "Có Răng" & Cổng Chất Lượng (`standards/`)

Bộ quy tắc kiểm soát tự động thi hành tại pre-commit hook và CI pipeline (`python scripts/checks/run_hard.py --all`):

- **[`standards/00-INDEX.md`](standards/00-INDEX.md)**: Bảng tổng hợp 38 quy tắc phân tầng kiểm soát:
  - **Tầng Hard (Chặn tuyệt đối — 0 vi phạm):** Cấm framework CSS utility tiện dụng (Tailwind), cấm emoji thô vô tội vạ, cấm claim khống kiểm chứng thực địa `verifiedAt`, cấm import phụ thuộc vòng tròn, cấm phá vỡ tính toàn vẹn bit-for-bit của cơ sở dữ liệu.
  - **Tầng Ratchet (Khóa trần nợ kỹ thuật):** Nợ token màu, nợ định dạng, số lỗi kiểm thử chỉ được phép giảm, không bao giờ được tăng.
  - **Tầng Soft (Khuyến nghị kiến trúc):** Hướng dẫn tối ưu hóa kèm cơ chế ghi nhật ký ngoại lệ có ký duyệt.
- **Tiêu chuẩn chuyên môn từng chiều:**
  - [`standards/10-data.md`](standards/10-data.md): Tiêu chuẩn toàn vẹn dữ liệu, kiểm tra schema, WGS84 GPS và SHA-256 hash.
  - [`standards/20-backend.md`](standards/20-backend.md): Tiêu chuẩn backend FastAPI, Pydantic v2, SQLAlchemy và xử lý lỗi RFC 7807.
  - [`standards/30-frontend.md`](standards/30-frontend.md): Tiêu chuẩn Nuxt 3, Vue 3 Composition API, TypeScript strict, payload < 200KB.
  - [`standards/40-ui-design.md`](standards/40-ui-design.md): Tiêu chuẩn mỹ thuật Anti-Slop, hệ thống token Tam Vùng, tiếp cận WCAG 2.2 AAA.
  - [`standards/50-content.md`](standards/50-content.md): Tiêu chuẩn nội dung biên tập, chống bịa đặt, E-E-A-T và trích nguồn minh bạch.
  - [`standards/60-docs.md`](standards/60-docs.md): Tiêu chuẩn tài liệu hệ thống, bắt buộc header `> STATUS: active`, cấm tài liệu rác mồ côi.
  - [`standards/70-ops.md`](standards/70-ops.md): Tiêu chuẩn vận hành, an toàn máy chủ, sao lưu dữ liệu, giám sát và log audit.
- **Báo cáo kiểm soát & Nhật ký ngoại lệ:**
  - [`standards/90-exceptions-log.md`](standards/90-exceptions-log.md): Nhật ký các ngoại lệ kỹ thuật đã được chủ dự án phê duyệt và danh sách SKIP-log chính thức.
  - [`standards/95-ra-soat-cong.md`](standards/95-ra-soat-cong.md): Báo cáo đánh giá tính xác thực của 28 cổng nghiệm thu dự án.
  - [`standards/FE-LEAD-PHASE-0-AUDIT.md`](standards/FE-LEAD-PHASE-0-AUDIT.md): Báo cáo chuẩn hóa giao diện frontend và lộ trình triệt tiêu nợ hiển thị.
- **Tệp cấu hình máy đọc (Machine-readable configs):**
  - `standards/baseline.json`: Ngưỡng baseline kiểm thử và nợ kỹ thuật.
  - `standards/bundle-budget.json`: Ngân sách kích thước bundle JavaScript/CSS (<200KB Brotli).
  - `standards/coverage-thresholds.json`: Ngưỡng độ bao phủ kiểm thử tối thiểu.
  - `standards/scorecard-history.jsonl`: Lịch sử chấm điểm scorecard qua từng đợt kiểm toán.
  - `standards/whitelist-tinh-cu.txt`: Danh sách trắng các từ ngữ địa danh lịch sử được phép xuất hiện.

### 4. Hồ Sơ Quyết Định Phát Hành & Thẩm Quyền Quản Trị (`decisions/`)

Hệ thống hồ sơ quyết định độc lập, có thẩm quyền xác thực trước khi mở cổng release pilot (theo `config/release-authority.json`):

- **[`decisions/README.md`](decisions/README.md)**: Quy chế quản trị quyết định và kỷ luật chữ ký người (máy tuyệt đối không tự ký thay người).
- **[`decisions/QD-01-chu-so-huu-dich-vu.md`](decisions/QD-01-chu-so-huu-dich-vu.md)**: Quyết định chỉ định Chủ sở hữu dịch vụ (`service_owner`).
- **[`decisions/QD-02-phap-ly-dpo.md`](decisions/QD-02-phap-ly-dpo.md)**: Quyết định về khung pháp lý và bảo vệ dữ liệu cá nhân (`legal` / DPO).
- **[`decisions/QD-03-idempotency-nha-cung-cap.md`](decisions/QD-03-idempotency-nha-cung-cap.md)**: Quyết định về tính bất biến khi tích hợp SMS / OTP bên thứ ba (`provider`).
- **[`decisions/QD-04-noi-luu-tru-du-lieu.md`](decisions/QD-04-noi-luu-tru-du-lieu.md)**: Quyết định về địa điểm lưu trữ dữ liệu tại Việt Nam (`residency`, Nghị định 13/2023/NĐ-CP).
- **[`decisions/QD-05-lap-chi-muc-cong-khai.md`](decisions/QD-05-lap-chi-muc-cong-khai.md)**: Quyết định về chính sách lập chỉ mục tìm kiếm công khai (`public_indexing`).
- **[`decisions/QD-06-chu-so-huu-staging-phat-hanh.md`](decisions/QD-06-chu-so-huu-staging-phat-hanh.md)**: Quyết định về thẩm quyền phê duyệt môi trường staging và release (`release_owner`).
- **[`decisions/OWNER-SIGNOFF-PACKET-2026-09-12.md`](decisions/OWNER-SIGNOFF-PACKET-2026-09-12.md)**: Gói trình ký bảo thủ và hồ sơ tổng hợp phê duyệt closed pilot.

### 5. Vận Hành, Bảo Mật & Ứng Phó Sự Cố (`runbooks/` & `security/`)

- **[`deployment-guide.md`](deployment-guide.md)**: Cẩm nang hướng dẫn đóng gói tarball, systemd service, reverse proxy Nginx, SSL Certbot và triển khai lên máy chủ VPS production (`66.42.57.202`).
- **[`developer-setup.md`](developer-setup.md)**: Hướng dẫn thiết lập môi trường phát triển local (FastAPI, Nuxt 3, Docker Postgres, kích hoạt cờ môi trường `HAS_*`).
- **[`security-hardening.md`](security-hardening.md)**: Kế hoạch gia cố bảo mật máy chủ, cấu hình SSH key, tường lửa UFW, cô lập quyền và chính sách xoay vòng khóa.
- **[`security/owasp-review-2026-08-05.md`](security/owasp-review-2026-08-05.md)**: Báo cáo rà soát an ninh toàn diện theo chuẩn OWASP Top 10 (2021) trên mã nguồn thực tế kèm đường dẫn `path:line` chi tiết.
- **[`incident-runbook.md`](incident-runbook.md)**: Quy trình phản ứng sự cố an ninh và rò rỉ dữ liệu cá nhân (lưu ý bẫy xoay vòng `TOTP_ENC_KEY`).
- **[`parallel-session-guide.md`](parallel-session-guide.md)**: Quy trình phối hợp an toàn khi chạy nhiều session agent song song (kỷ luật cô lập git worktree, chống xung đột commit).
- **Kịch bản vận hành chi tiết trong [`runbooks/`](runbooks/):**
  - [`runbooks/db-khong-len.md`](runbooks/db-khong-len.md): Khắc phục sự cố SQLite/Postgres không khởi động hoặc bị khóa (database lock).
  - [`runbooks/deploy-hong.md`](runbooks/deploy-hong.md): Khắc phục lỗi trong quá trình build hoặc deploy VPS thất bại.
  - [`runbooks/het-dia.md`](runbooks/het-dia.md): Quy trình giải phóng và xử lý khẩn cấp khi máy chủ cạn kiệt dung lượng đĩa.
  - [`runbooks/launch-safety-rollback.md`](runbooks/launch-safety-rollback.md): Quy trình khôi phục an toàn (rollback) về phiên bản ổn định gần nhất.
  - [`runbooks/personal-data-erasure.md`](runbooks/personal-data-erasure.md): Quy trình xóa vĩnh viễn dữ liệu cá nhân theo yêu cầu (tuân thủ Nghị định 13/2023/NĐ-CP & GDPR Art. 17).
  - [`runbooks/entity-published-status-migration.md`](runbooks/entity-published-status-migration.md): Quy trình di chuyển và đồng bộ trạng thái xuất bản của thực thể (cần chủ dự án duyệt riêng từng lần).
  - [`runbooks/proof-first-pilot-acceptance.md`](runbooks/proof-first-pilot-acceptance.md): Quy trình nghiệm thu closed pilot dựa trên bằng chứng kỹ thuật thực chứng.
  - [`runbooks/correction-case-cutover.md`](runbooks/correction-case-cutover.md): Kịch bản chuyển đổi hệ thống (cutover) cho môi trường pilot.
  - [`runbooks/correction-case-incident.md`](runbooks/correction-case-incident.md): Quy trình phản ứng và xử lý sự cố phát sinh trong thời gian thử nghiệm pilot.
  - [`runbooks/correction-case-pilot.md`](runbooks/correction-case-pilot.md): Cẩm nang tổng thể điều hành và vận hành chương trình pilot.

### 6. Nghiên Cứu Địa Chí, Thổ Nhưỡng & Biên Tập Nội Dung (`research/`)

- **[`research/corpus-van-hoa-du-lich-vl-2026-06.md`](research/corpus-van-hoa-du-lich-vl-2026-06.md)**: Chỉ mục tổng hợp tư liệu văn hóa, lịch sử và địa danh sông nước Cửu Long.  
  *Điều kiện ràng buộc nghiêm ngặt:* Tài liệu có trạng thái `STATUS: active có giới hạn`, cấm tuyệt đối 4 điều: không dùng khung 3 tỉnh cũ, không dùng cấp huyện cũ, không dùng khuyến nghị bán tour/vé, và không dùng khung định vị cũ.
- **16 tệp dữ liệu đối chứng địa chí, tọa độ và di tích trong `research/`:**
  - `research/nghien_cuu_12_chieu_ban_do_diem_tuyen.geojson`: Bản đồ điểm tuyến du lịch văn hóa dạng GeoJSON.
  - `research/danh_muc_chuyen_sau_dia_diem_le_hoi_van_hoa_vl_tv_bt.csv`: Danh mục tra cứu di tích và lễ hội.
  - Các bộ khảo sát 12 chiều & 6 tầng tài nguyên: `nghien_cuu_12_chieu_catalog_62_tai_nguyen.csv`, `nghien_cuu_12_chieu_canh_tranh_dbscl.csv`, `nghien_cuu_12_chieu_ma_tran_san_pham.csv`, `nghien_cuu_12_chieu_phan_khuc_khach.csv`, `nghien_cuu_12_chieu_rui_ro_bao_ton_moi_truong.csv`, `nghien_cuu_12_chieu_kpi_du_lieu_can_thu_thap.csv`, `nghien_cuu_12_chieu_thu_muc_nguon_mo_rong.csv`, `nghien_cuu_6_tang_danh_gia_tai_nguyen.csv`, `nghien_cuu_6_tang_diem_den_toa_do.csv`, `nghien_cuu_6_tang_ma_tran_tuyen_khong_gian.csv`, `nghien_cuu_6_tang_thu_muc_nguon.csv`.
  - Bộ dữ liệu truyền thông địa phương: `baovinhlong_du_lich_evidence_matrix_2025_2026.csv`, `baovinhlong_du_lich_urls_2025_2026.csv`, `thvl_du_lich_urls.csv`.
- **[`content-creation-guide.md`](content-creation-guide.md)**: Cẩm nang hướng dẫn biên soạn nội dung di sản, tiêu chuẩn nhập liệu điểm đến và quy tắc hình ảnh AI-only.
- **[`toi-uu-chong-ai-va-google-spam-playbook.md`](toi-uu-chong-ai-va-google-spam-playbook.md)**: Sổ tay tối ưu hóa chất lượng bài viết, triệt tiêu văn phong sáo rỗng AI, xây dựng độ tin cậy thực địa theo chuẩn E-E-A-T.
- **[`b2g-pitch.md`](b2g-pitch.md)**: Hồ sơ mẫu đề xuất hợp tác công - tư (B2G) với các cơ quan quản lý nhà nước (tôn chỉ văn hóa, phi thương mại hóa, bảo tồn số).
- **Cấu hình cá nhân hóa Claude Desktop (`claude-desktop/`):**
  - [`claude-desktop/about-me.md`](claude-desktop/about-me.md): Nguyên tắc làm việc và định vị của chuyên gia phát triển.
  - [`claude-desktop/anti-ai-writing-style.md`](claude-desktop/anti-ai-writing-style.md): Quy chuẩn hành văn tự nhiên, bài trừ lối viết sáo rỗng AI.
  - [`claude-desktop/my-company.md`](claude-desktop/my-company.md): Sứ mệnh và tôn chỉ văn hóa của nền tảng Vĩnh Long 360.

### 7. Báo Cáo Kiểm Toán Dữ Liệu & Đồ Thị Tri Thức (`reports/`)

Các công trình nghiên cứu và báo cáo kiểm chứng dữ liệu thực nghiệm chuyên sâu tháng 09/2026:

- **[`reports/2026-09-12-comprehensive-data-audit-report.md`](reports/2026-09-12-comprehensive-data-audit-report.md)**: Báo cáo kiểm toán toàn diện 1.747 thực thể, 12.061 quan hệ và 33 tuyến lộ trình trong cơ sở dữ liệu `vinhlong360.db`.
- **[`reports/2026-09-13-factual-data-accuracy-audit.md`](reports/2026-09-13-factual-data-accuracy-audit.md)**: Báo cáo kiểm toán tính xác thực của thông tin lịch sử, nhân vật, tọa độ GPS và tem sao chứng nhận OCOP.
- **[`reports/2026-09-13-notebooklm-deep-enrichment-report.md`](reports/2026-09-13-notebooklm-deep-enrichment-report.md)**: Báo cáo 12 chương khai phóng tri thức từ 988 nguồn tư liệu Google NotebookLM và xây dựng ma trận thị giác thổ nhưỡng.
- **[`reports/2026-09-13-notebooklm-knowledge-sources-expansion.md`](reports/2026-09-13-notebooklm-knowledge-sources-expansion.md)**: Danh mục mở rộng kho nguồn tri thức thẩm quyền cao qua Bộ lọc 3 Lớp.

### 8. Hồ Sơ Kế Hoạch & Bằng Chứng Thi Công Lịch Sử (`superpowers/`)

Thư mục `superpowers/` lưu giữ các hồ sơ thi công, kế hoạch sprint và bằng chứng nghiệm thu kỹ thuật đã hoàn thành:
- `superpowers/plans/`: Kế hoạch thi công chi tiết của các đợt phát triển, tái cấu trúc và tối ưu hóa hệ thống.
- `superpowers/results/`: Bằng chứng nghiệm thu kỹ thuật thực tế (Launch safety, trust boundary, data erasure, pilot evidence).
- `superpowers/specs/`: Đặc tả kiến trúc các tính năng hiện hành (Anti-Slop design constitution, Sub-agent architecture, Open API).
- `superpowers/qa/`: Báo cáo QA và ảnh chụp màn hình kiểm thử giao diện qua các đợt phát hành.

---

## Tuyên Bố Danh Mục Đã Thanh Lọc (Purged Categories Declaration)

Trong đợt tổng thanh lọc tài liệu tháng 09/2026 (Milestone 2), toàn bộ **86 tệp tài liệu lỗi thời, rác kỹ thuật và mâu thuẫn chính sách** đã bị **XÓA BỎ TRIỆT ĐỂ** khỏi hệ sinh thái để bảo vệ tính nhất quán của Hiến pháp `CLAUDE.md`. Tuyệt đối **KHÔNG khôi phục, KHÔNG trích dẫn, và KHÔNG làm theo** các danh mục sau:

### 1. Ghi chú bàn giao cũ & tệp phiên làm việc (Obsolete Handovers & Session Notes) — 10 tệp
- **Căn cứ thanh lọc:** Tài liệu bàn giao phiên giữa các agent phải nằm trong thư mục `.agents/`, tuyệt đối không lưu trữ trong `docs/` gây ô nhiễm chỉ mục và phân mảnh ngữ cảnh.
- **Danh sách tệp đã xóa:** `docs/HANDOFF.md`, `docs/HANDOFF-BRANCHES.md`, `docs/HANDOFF-CLAUDE-CODE-DESKTOP-2026-09-03.md`, `docs/HANDOFF-CLAUDE-CODE-DESKTOP-2026-09-03-KET-QUA.md`, `docs/2026-08-31-ban-giao-tiep-tuc.md`, `docs/superpowers/handoffs/` (4 tệp: `2026-08-18-claude-code-desktop-correction-case-pilot.md`, `2026-09-08-frontend-lead-moc-170-handover-to-codex.md`, `2026-09-12-antigravity-full-project-handoff.md`, `2026-09-14-stitch-homepage-editorial-field-guide.md`), `docs/superpowers/plans/2026-09-12-antigravity-full-project-handoff.md`.

### 2. Đề xuất Đặt phòng, Bán tour & Thương mại hóa (Booking & Commercialization Proposals) — 18 tệp
- **Căn cứ thanh lọc:** Vi phạm nghiêm trọng Quyết định chốt `CLAUDE.md` §1.4 ("CHỈ GIỚI THIỆU — KHÔNG đặt hàng/booking/thanh toán on-site, KHÔNG hoa hồng booking, KHÔNG bán tour/vé"). Nền tảng là cổng thông tin văn hóa phi lợi nhuận, không phải sàn thương mại điện tử.
- **Danh sách tệp đã xóa:** `docs/superpowers/specs/redesign-concepts/07-tourism-lodging.md` (chứa 9 cơ chế đặt phòng OTA), các tài liệu phân tích booking cũ trong `archive/` (`product-architecture-gap-analysis-2026-06-29.md` với 285 lỗi booking, `codex-feature-research-prompt.md`).

### 3. Khái niệm 3 Tỉnh Tách Rời & Tàn Dư Cấp Huyện (3-Province Concepts & Old District Models) — 18 tệp
- **Căn cứ thanh lọc:** Vi phạm Quyết định chốt `CLAUDE.md` §0 & §1.6 ("ĐỊNH VỊ: Vĩnh Long (tỉnh MỚI: sáp nhập 3 tỉnh cũ, hành chính 2 cấp: 1 tỉnh → 124 xã/phường, KHÔNG còn cấp huyện)").
- **Danh sách tệp đã xóa:** Toàn bộ 17 concept ý tưởng `docs/superpowers/specs/redesign-concepts/00-16`, `docs/superpowers/specs/2026-07-05-public-pages-cinematic-redesign.md` (chứa 16 lỗi "màu 3 tỉnh"), `docs/superpowers/specs/2026-07-10-mientay-rephrase-edits.json` (tàn dư huyện cũ), các báo cáo nghiên cứu 3 tỉnh thời kỳ đầu.

### 4. Toàn bộ Kho Lưu Trữ Lịch Sử Lỗi Thời (`docs/archive/`) — 33 tệp
- **Căn cứ thanh lọc:** 33 tệp trong `docs/archive/` (blueprints, codex prompts, báo cáo cũ từ 06–07/2026) chứa hàng trăm mâu thuẫn với Hiến pháp hiện hành. Đã được thay thế hoàn toàn bởi các bộ chuẩn `standards/` và báo cáo `reports/`.
- **Danh sách tệp đã xóa:** Xóa sổ toàn bộ thư mục `docs/archive/` (33 tệp bao gồm `docs/archive/README.md`).

### 5. Bản Nháp Mồ Côi & Báo Cáo Thử Nghiệm Superseded (Orphan Drafts & Superseded Reports) — 17 tệp
- **Căn cứ thanh lọc:** 5 bản nháp nội dung trong `docs/drafts/` bỏ quên từ tháng 08/2026 chưa từng được nạp vào cơ sở dữ liệu; các báo cáo audit cũ đã bị thay thế bởi báo cáo tháng 09/2026; các file fork lạc đề.
- **Danh sách tệp đã xóa:** Toàn bộ 6 tệp trong `docs/drafts/` (`2026-08-07-*.md`, `lo-10-entity-mau.md`, `doi-chieu-ma-hanh-chinh.md`), `docs/audit-toan-du-an-2026-08.md`, `docs/2026-08-05-fix-report-egress-address-policy.md`, `docs/2026-08-21-danh-gia-toan-du-an.md`, `docs/2026-08-22-cau-hoi-cho-luat-su.md`, `docs/2026-08-27-ban-do-module-de-xuat.md`, `docs/2026-08-29-chien-dich-tra-no-scorecard-backend.md`, `docs/2026-08-30-ho-so-cho-chu-du-an-quyet.md`, `docs/ONBOARDING-GAPS.md`, `docs/QUYET-DINH-DANG-CHO.md`, `docs/entity-content-model.md`, `docs/superpowers/specs/2026-07-13-dongthap360-fork-design.md`, `docs/superpowers/specs/2026-07-27-vinhlong360-ui-first-super-app-design.md`.

### 6. Tệp Dữ Liệu Dump CSV & SQL Lạc Chỗ (Misplaced Raw Data Dumps) — 6 tệp
- **Căn cứ thanh lọc:** Thư mục `docs/` chỉ dành cho tài liệu kỹ thuật, kiến trúc và vận hành. Các bản dump dữ liệu cào web nặng hàng Megabyte gây ô nhiễm kho tài liệu đã được dọn sạch.
- **Danh sách tệp đã xóa:** `docs/data-verification-claims.csv`, `docs/data-verification-web-log.csv`, `docs/data-verification-matrix.csv`, `docs/data-verification-sources.csv`, `docs/data-verification-fixes.sql`, `docs/2026-08-30-entity-can-khao-sat.csv`.

---

## Chính Sách & Kỷ Luật Quản Trị Tài Liệu (Documentation Governance)

1. **Header Trạng Thái Bắt Buộc:** Mọi tài liệu kỹ thuật trong `docs/` bắt buộc phải có header ở đầu tệp:
   ```markdown
   > STATUS: active
   ```
   *(hoặc `> STATUS: active có giới hạn` đối với tư liệu tham khảo có điều kiện cấm, hoặc `> STATUS: superseded-by <đường_dẫn>`)*. Mọi tài liệu thiếu header này bị coi là tài liệu mồ côi và sẽ bị tự động gắn cờ vi phạm tại cổng kiểm tra `python scripts/checks/run_hard.py --all`.
2. **Kỷ Luật Vùng Lưu Trữ (.agents/ vs docs/):** Báo cáo phiên, ghi chú bàn giao (handoff), kế hoạch tạm thời của các AI agent BẮT BUỘC ghi vào thư mục riêng trong `.agents/`. Tuyệt đối không tạo file handoff trong `docs/`.
3. **Bảo Vệ Tính Toàn Vẹn & Bất Biến:** Mọi cập nhật tài liệu phải giữ vững 100% các quyết định đã chốt (§1) và 8 bất biến B1–B8 (§2) của `CLAUDE.md`.

# Báo Cáo Mở Rộng Kho Tri Thức Thẩm Quyền Cao Cho NotebookLM (72 Nguồn Tier 1 & Tier 2)

> STATUS: active (2026-09-18) — Danh mục mở rộng nguồn tri thức thẩm quyền cao cho NotebookLM.
> **Ngày lập:** 13/09/2026 (Cập nhật 18/09/2026)  
> **Mục tiêu:** Mở rộng và làm sâu sắc kho tri thức số cho hệ thống 3 Sổ tay Google NotebookLM của dự án Vĩnh Long 360, phục vụ công tác đối chứng thực địa, làm giàu E-E-A-T, tối ưu hóa AEO/GEO Semantic Graph và chống ảo giác thông tin (anti-hallucination).  
> **Bộ lọc thẩm quyền:** Tuân thủ tuyệt đối **Bộ lọc 3 Lớp (3-Tier Authority Filter)** — 100% nguồn thuộc Tier 1 (Cơ quan Nhà nước, Cổng TTĐT cấp Bộ/Tỉnh) và Tier 2 (Viện nghiên cứu, Trường đại học, Cơ quan Báo chí chính thống). Tuyệt đối **0%** blog tự do, mạng xã hội, tổng hợp thương mại.

---

## 1. Tổng Quan Hiện Trạng & Kết Quả Đạt Được

Hệ thống NotebookLM của dự án hiện vận hành trên 3 Sổ tay chuyên đề:
1. **Sổ tay 1: `v-nh-long-v-nh-long-b-n-tre-tr`** ("Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)") — Tập trung vào Lịch sử, Khảo cổ học, Danh nhân văn hóa, Di tích kiến trúc và Tôn giáo tín ngưỡng.
2. **Sổ tay 2: `mekong-360-t-p-2`** ("Mekong 360 - Tập 2") — Tập trung vào Làng nghề truyền thống, Ẩm thực Nam Bộ & Khmer, Lễ hội dân gian & Duyên hải, Du lịch sinh thái miệt vườn & Mô hình cộng đồng thuận thiên.
3. **Sổ tay 3: `ch-nh-s-ch-ph-p-lu-t-v-n-b-n-q`** ("Chính sách & Pháp luật (Văn bản, Quy định & Đề án)") — Tập trung vào Quy hoạch phát triển tỉnh thời kỳ 2021–2030, Đề án Di sản Đương đại Mang Thít, Bộ Tiêu chí Du lịch Xanh và các Nghị quyết hành chính.

### Thống Kê Phân Bố 72 Nguồn Tri Thức Đã Chuẩn Hóa:
- **Tổng số nguồn thẩm quyền:** **72 nguồn** (lưu trữ đầy đủ tại `outputs/notebooklm_curated_knowledge_sources.json` và đồng bộ `outputs/newly_added_sources.json`).
- **Phân bổ theo Cấp thẩm quyền (Authority Tier):**
  * **Tier 1 (Thẩm quyền Nhà nước - Highest Authority, Weight 1.0):** **45 nguồn (62.5%)**
    - Cổng TTĐT Chính phủ (`chinhphu.vn`, `vanban.chinhphu.vn`)
    - Cục Di sản Văn hóa - Bộ VHTTDL (`dsvh.gov.vn`)
    - Cục Du lịch Quốc gia Việt Nam (`vietnamtourism.gov.vn`, `nongthon.vietnamtourism.gov.vn`, `dantoc.vietnamtourism.gov.vn`)
    - Cổng TTĐT và các Sở ngành tỉnh Vĩnh Long, Bến Tre, Trà Vinh (`vinhlong.gov.vn`, `bentre.gov.vn`, `travinh.gov.vn`, `svhttdl.vinhlong.gov.vn`, `dulichbentre.gov.vn`, `skhcn.travinh.gov.vn`, `socongthuong.bentre.gov.vn`...)
    - Bảo tàng tỉnh Vĩnh Long (`baotangvinhlong.vn`) & Cổng Du lịch Thông minh Vĩnh Long (`vinhlongtourist.vn`)
  * **Tier 2 (Học thuật & Báo chí Chính thống, Weight 0.9–0.95):** **27 nguồn (37.5%)**
    - Viện Hàn lâm KHXH Việt Nam (`vass.gov.vn`)
    - Trường Đại học Cần Thơ (`ctu.edu.vn`)
    - Báo Nhân Dân (`nhandan.vn`)
    - Đài Phát thanh và Truyền hình Vĩnh Long (`thvl.vn` - 10 ký sự/phim tài liệu chuyên đề)
    - Báo Vĩnh Long (`baovinhlong.com.vn` - 13 bài khảo sát thực địa chuyên sâu)
    - Báo Đồng Khởi (`baodongkhoi.vn`)
  * **Nguồn vi phạm / Banned:** **0 nguồn (0.0%)**
- **Phân bổ theo Sổ tay NotebookLM:**
  * **Sổ tay 1 (`v-nh-long-v-nh-long-b-n-tre-tr`):** **19 nguồn**
  * **Sổ tay 2 (`mekong-360-t-p-2`):** **50 nguồn**
  * **Sổ tay 3 (`ch-nh-s-ch-ph-p-lu-t-v-n-b-n-q`):** **3 nguồn**
- **Phân bổ theo Chủ đề Văn hóa & Thổ nhưỡng:**
  * Làng nghề truyền thống & Kỹ nghệ thủ công (`TRADITIONAL_CRAFT`): **16 nguồn**
  * Sinh thái sông nước, Cù lao & OCOP (`MEKONG_ECOLOGY_OCOP`): **14 nguồn**
  * Văn hóa & Tín ngưỡng Khmer Nam Bộ (`KHMER_CULTURE`): **11 nguồn**
  * Lễ hội dân gian, Nghi lễ biển & Kỳ Yên (`FESTIVALS_RITUALS`): **9 nguồn**
  * Khảo cổ, Di tích & Kiến trúc (`ARCHAEOLOGY_HERITAGE`): **9 nguồn**
  * Nhân vật lịch sử & Danh nhân văn hóa (`HISTORICAL_FIGURE`): **5 nguồn**
  * Ẩm thực bản địa chuyên sâu (`TERROIR_CUISINE_OCOP`): **4 nguồn**
  * Quy hoạch, Chính sách & Du lịch xanh (`ADMIN_PLANNING`): **4 nguồn**

---

## 2. Các Khoảng Trống Dữ Liệu Lớn Đã Được Khắc Phục Triệt Để

Trước đợt mở rộng này, cơ sở dữ liệu và sổ tay tri thức còn tồn tại các "khoảng mờ" (blind spots). Đợt bổ sung này giải quyết triệt để 5 nhóm vấn đề:

### 2.1. Lễ hội Văn hóa Khmer & Di sản Mới Công Nhận
- **Đại lễ Ok Om Bok Trà Vinh (SRC-TIER2-TV-037 & SRC-TIER1-TV-020):** Bổ sung nghi thức Đút om-bok đêm Rằm tháng 10 tại Ao Bà Om, Lôi Protip (thả hoa đăng) và Lễ hội đua ghe Ngo trên sông Long Bình từ tư liệu Báo Nhân Dân và Cục Di sản Văn hóa.
- **Lễ hội Đom Lơng Néak Tà (SRC-TIER1-TV-039):** Bổ sung văn bản công nhận Di sản Văn hóa Phi vật thể Quốc gia mới nhất năm 2024 của Bộ VHTTDL cho tín ngưỡng thờ thần bảo hộ phum sóc của người Khmer Trà Vinh.
- **Chôl Chnăm Thmây & Sêne Đôlta (SRC-TIER1-TV-038 & SRC-TIER2-TV-021):** Định hình chu kỳ lễ hội theo lịch trăng và nghi thức đắp núi cát, tắm Phật tại các phum sóc.
- **Sân khấu Kịch hát Dù Kê & Kịch múa Rô-băm (SRC-TIER1-TV-055 & SRC-TIER2-TV-019):** Cung cấp lịch sử hình thành nghệ thuật Dù Kê từ thập niên 1920 tại Trà Vinh và kịch múa cung đình Rô-băm.

### 2.2. Tín Ngưỡng Vùng Biển Duyên Hải & Lễ Hội Nghinh Ông
- **Lễ hội Cúng Biển Mỹ Long (SRC-TIER2-TV-040):** Tư liệu ký sự THVL về nghi lễ cúng Thần Biển ngày 11-12 tháng 5 âm lịch tại Cầu Ngang.
- **Lễ hội Nghinh Ông Bình Thắng (SRC-TIER1-BT-041):** Hồ sơ di sản quốc gia của Sở VHTTDL Bến Tre về tục rước Cá Ông ngày 16-17 tháng 6 âm lịch tại Bình Đại.
- **Lễ hội Nghinh Ông Lăng Cồn Tàu (SRC-TIER2-TV-042):** Khảo sát tục thờ cá voi cổ truyền tại thị xã Duyên Hải ngày 10-11 tháng 3 âm lịch.

### 2.3. Hệ Thống Đình Làng Nam Bộ & Lễ Hội Kỳ Yên
- **Đình Phú Lễ (SRC-TIER1-BT-044):** Hồ sơ khoa học ngôi đình gỗ lim 10 gian lớn nhất Ba Tri và lệ Kỳ Yên xuân - thu gắn với hát bội và làng nghề nấu rượu nếp Phú Lễ.
- **Chuỗi Lễ Kỳ Yên - Hạ Điền - Thượng Điền Vĩnh Long (SRC-TIER2-VL-045):** Khảo sát thực địa chuỗi nghi thức tại Đình Tân Hoa, Đình Tân Ngãi, Đình Tân Giai và Đình Long Thanh (phường 5 TP Vĩnh Long).
- **Lễ hội Lăng Ông Trà Ôn (SRC-TIER2-VL-047):** Di sản văn hóa phi vật thể quốc gia tôn vinh Thống chế Điều bát Nguyễn Văn Tồn vào mùng 3-4 tháng Giêng, kết tinh tình đoàn kết Kinh - Khmer.
- **Lễ Vu Lan Thắng Hội Chùa Ông Bổn Cầu Kè (SRC-TIER2-TV-043):** Hồ sơ di sản phi vật thể quốc gia về lễ hội Vu Lan độc đáo giao thoa văn hóa Việt - Hoa - Khmer từ ngày 25-28 tháng 7 âm lịch.

### 2.4. Làng Nghề Thủ Công & Ẩm Thực Bản Địa (Terroir)
- **Làng nghề bánh tráng & chằm nón Cù Lao Mây (SRC-TIER1-VL-051 & SRC-TIER2-VL-052):** Kỹ nghệ tráng bánh phơi sương xã Lục Sĩ Thành và quy trình chuốt 16 vành tre chằm nón lá xã Phú Thành.
- **Làng nghề Rượu Xuân Thạnh (SRC-TIER1-TV-053):** Quy chuẩn nhãn hiệu chứng nhận và bí quyết men 14 vị thuốc Bắc của danh tửu 60 độ lửa Châu Thành.
- **Làng nghề Rượu nếp Phú Lễ (SRC-TIER1-BT-054):** Tiêu chuẩn men 36 vị thuốc Nam - Bắc và quy trình ủ chum sành hạ thổ 100 ngày.
- **Bún nước lèo Trà Vinh & Cháo ám (SRC-TIER2-TV-056):** Tỷ lệ gia vị mắm bò hóc, ngải bún và cá lóc đồng theo chuẩn truyền hình ẩm thực.
- **Làng nghề dệt chiếu Cà Hôn & Tàu hủ ky Mỹ Hòa (SRC-TIER2-VL-069 & SRC-TIER2-VL-057):** Kỹ thuật dệt lác hoa văn chữ Thọ và 4 chủng loại tàu hủ ky làng nghề trăm năm Bình Minh.

### 2.5. Du Lịch Sinh Thái Thuận Thiên & Bảo Tồn Ven Biển
- **Mô hình Thuận thiên Cồn Chim (SRC-TIER1-TV-048):** Báo cáo của Cục Du lịch Quốc gia về mô hình du lịch nông nghiệp 6 tháng lúa sạch - 6 tháng tôm tự nhiên, không rác thải nhựa.
- **Mô hình Du lịch Tự thân Cồn Hô (SRC-TIER2-TV-049):** Khảo sát ốc đảo sinh thái sông Cổ Chiên không điện lưới, bảo lưu không gian văn hóa đèn măng-sông miệt vườn.
- **Khu Bảo tồn Đất ngập nước Thạnh Phú (SRC-TIER1-BT-050):** Quy hoạch bảo tồn 2.584 ha rừng mắm, đước và bãi đẻ rùa biển Đồi mồi.

---

## 3. Danh Mục Chi Tiết 70 Nguồn Tri Thức Chuẩn Hóa

### Sổ Tay 1: Vĩnh Long (`v-nh-long-v-nh-long-b-n-tre-tr`) — 17 Nguồn
1. **SRC-TIER1-VL-001** [Tier 1]: *Hồ sơ Di tích Lịch sử - Văn hóa Văn Thánh Miếu Vĩnh Long và Tụy Văn Lâu* — Cục Di sản Văn hóa (`dsvh.gov.vn`).
2. **SRC-TIER1-VL-002** [Tier 1]: *Quyết định xếp hạng Di tích Kiến trúc nghệ thuật Chùa Tiên Châu* — Sở VHTTDL Vĩnh Long (`vinhlong.gov.vn`).
3. **SRC-TIER1-VL-003** [Tier 1]: *Di tích Lịch sử Văn hóa Thất Phủ Miếu (Chùa Ông Vĩnh Long)* — Cổng TTĐT tỉnh Vĩnh Long (`vinhlong.gov.vn`).
4. **SRC-TIER1-VL-004** [Tier 2]: *Thân thế, sự nghiệp và di sản khẩn hoang Nam Bộ của Thoại Ngọc Hầu* — Viện Lịch sử Quân sự (`vass.gov.vn`).
5. **SRC-TIER2-VL-005** [Tier 2]: *Khảo cứu thân thế, sự nghiệp và bi kịch lịch sử của Tiến sĩ Phan Thanh Giản* — Viện Hàn lâm KHXH Việt Nam (`vass.gov.vn`).
6. **SRC-TIER1-VL-006** [Tier 1]: *Khu lưu niệm Giáo sư, Viện sĩ Trần Đại Nghĩa* — Cổng TTĐT huyện Tam Bình (`tambinh.vinhlong.gov.vn`).
7. **SRC-TIER1-VL-007** [Tier 1]: *Khu tưởng niệm Cố Thủ tướng Chính phủ Võ Văn Kiệt* — Sở VHTTDL tỉnh Vĩnh Long (`vinhlong.gov.vn`).
8. **SRC-TIER2-VL-008** [Tier 2]: *Nghệ thuật Đờn ca tài tử Vĩnh Long: Từ Kinh lịch Quờn đến Di sản thế giới* — Trường Đại học Cần Thơ (`ctu.edu.vn`).
9. **SRC-TIER1-BT-009** [Tier 1]: *Hồ sơ Di tích Quốc gia Đặc biệt Di tích Đồng Khởi Bến Tre* — Cục Di sản Văn hóa (`dsvh.gov.vn`).
10. **SRC-TIER1-BT-010** [Tier 1]: *Hồ sơ Di tích Quốc gia Đặc biệt Mộ và Khu lưu niệm danh nhân Nguyễn Đình Chiểu* — Cục Di sản Văn hóa (`dsvh.gov.vn`).
11. **SRC-TIER1-BT-011** [Tier 1]: *Khu Di tích Kiến trúc và Tín ngưỡng Đạo Dừa Cồn Phụng* — Sở VHTTDL tỉnh Bến Tre (`bentre.gov.vn`).
12. **SRC-TIER1-VL-012** [Tier 1]: *Quy hoạch tỉnh Vĩnh Long thời kỳ 2021-2030 (QĐ 1759/QĐ-TTg)* — Báo Chính phủ (`xaydungchinhsach.chinhphu.vn`).
13. **SRC-TIER1-BT-044** [Tier 1]: *Hồ sơ Di tích Quốc gia Đình Phú Lễ và Lễ hội Kỳ Yên truyền thống Ba Tri* — Cục Di sản Văn hóa (`dsvh.gov.vn`).
14. **SRC-TIER2-VL-045** [Tier 2]: *Rộn ràng Lễ hội Hạ Điền – Kỳ Yên tại các di tích đình làng Nam Bộ tỉnh Vĩnh Long* — Báo Vĩnh Long (`baovinhlong.com.vn`).
15. **SRC-TIER2-VL-046** [Tier 2]: *Lễ Xuân Đinh - Nét đẹp văn hóa khuyến học tại Văn Thánh Miếu* — Báo Vĩnh Long (`baovinhlong.com.vn`).
16. **SRC-TIER2-VL-047** [Tier 2]: *Tổ chức Lễ hội Lăng Ông Thống chế Điều bát Nguyễn Văn Tồn tại Trà Ôn* — Báo Vĩnh Long (`baovinhlong.com.vn`).
17. **SRC-TIER2-VL-062** [Tier 2]: *Đôi điều suy nghĩ về bảo tồn và phát huy nghệ thuật Đờn ca tài tử ở Vĩnh Long* — Báo Vĩnh Long (`baovinhlong.com.vn`).
18. **SRC-TIER1-VL-071** [Tier 1]: *Cổng Thông tin Điện tử Bảo tàng tỉnh Vĩnh Long - Cơ sở dữ liệu hiện vật & Di sản văn hóa* — Bảo tàng tỉnh Vĩnh Long (`baotangvinhlong.vn`).
19. **SRC-TIER1-VL-072** [Tier 1]: *Cổng Thông tin Du lịch Thông minh Vĩnh Long - Trung tâm Thông tin Xúc tiến Du lịch* — Sở VHTTDL tỉnh Vĩnh Long (`vinhlongtourist.vn`).

---

### Sổ Tay 2: Mekong 360 - Tập 2 (`mekong-360-t-p-2`) — 50 Nguồn
18. **SRC-TIER1-TV-013** [Tier 1]: *Hồ sơ Di tích Lịch sử - Kiến trúc Nghệ thuật Chùa Âng (Wat Angkorajaborey)* — Cục Di sản Văn hóa.
19. **SRC-TIER1-TV-014** [Tier 1]: *Danh lam Thắng cảnh Quần thể Ao Bà Om và Di sản Cây cổ thụ trăm tuổi* — Sở VHTTDL tỉnh Trà Vinh.
20. **SRC-TIER1-TV-015** [Tier 1]: *Kiến trúc và điêu khắc Phật giáo Nam tông Chùa Hang (Wat Kompong Chrây)* — Sở VHTTDL Trà Vinh.
21. **SRC-TIER1-TV-016** [Tier 1]: *Hồ sơ Di tích Quốc gia Chùa Ông Mẹt (Wat Bodhisàlaraja)* — Cục Di sản Văn hóa.
22. **SRC-TIER1-TV-017** [Tier 1]: *Di tích Nghệ thuật Chùa Cò (Wat Phnô Đôn) và Vườn chim tự nhiên Đại An* — Cổng TTĐT tỉnh Trà Vinh.
23. **SRC-TIER1-TV-018** [Tier 1]: *Di sản Văn hóa Phi vật thể Quốc gia: Nghệ thuật Chầm-riêng Chà-pây* — Cục Di sản Văn hóa.
24. **SRC-TIER2-TV-019** [Tier 2]: *Nghệ thuật Sân khấu Kịch múa Cổ điển Rô-băm của cộng đồng Khmer Trà Vinh* — Tạp chí Văn hóa Nghệ thuật.
25. **SRC-TIER1-TV-020** [Tier 1]: *Lễ hội Cúng Trăng Ok Om Bok và Hội đua ghe Ngo truyền thống Trà Vinh* — Cục Di sản Văn hóa.
26. **SRC-TIER2-TV-021** [Tier 2]: *Phân tích chu kỳ văn hóa tín ngưỡng qua hai đại lễ Chôl Chnăm Thmây và Sêne Đôlta* — Trường Đại học Cần Thơ.
27. **SRC-TIER2-TV-022** [Tier 2]: *Văn hóa ẩm thực dân gian Khmer Trà Vinh: Kỹ thuật nấu Bún nước lèo và Chù dẳn* — Trường Đại học Cần Thơ.
28. **SRC-TIER1-TV-023** [Tier 1]: *Làng nghề truyền thống Bánh tét Trà Cuôn* — Sở Công Thương tỉnh Trà Vinh.
29. **SRC-TIER1-TV-024** [Tier 1]: *Sản phẩm OCOP 5 sao Mật hoa dừa Sokfarm Trà Vinh* — Cổng TTĐT tỉnh Trà Vinh.
30. **SRC-TIER1-VL-025** [Tier 1]: *Đề án Di sản Đương đại Mang Thít (QĐ 1293/QĐ-UBND)* — Cổng TTĐT tỉnh Vĩnh Long.
31. **SRC-TIER2-VL-026** [Tier 2]: *Kỹ thuật nung gốm đỏ truyền thống Vĩnh Long: Thổ nhưỡng đất sét phù sa và lửa trấu* — Viện Địa lý Tài nguyên.
32. **SRC-TIER1-VL-027** [Tier 1]: *Làng nghề Tàu hủ ky Mỹ Hòa (Thị xã Bình Minh) - Di sản phi vật thể quốc gia* — Sở VHTTDL tỉnh Vĩnh Long.
33. **SRC-TIER1-VL-028** [Tier 1]: *Nghề dệt chiếu Cà Hôn (Trà Côn, Trà Ôn) - Kỹ nghệ dệt lác thủ công* — Cổng TTĐT huyện Trà Ôn.
34. **SRC-TIER1-VL-029** [Tier 1]: *Làng nghề Bánh tráng nem Cù lao Mây (Lục Sĩ Thành, Trà Ôn)* — Cổng TTĐT huyện Trà Ôn.
35. **SRC-TIER1-VL-030** [Tier 1]: *Vùng chuyên canh Khoai lang tím Nhật Bình Tân - Chỉ dẫn địa lý* — Sở Nông nghiệp & PTNT Vĩnh Long.
36. **SRC-TIER1-BT-031** [Tier 1]: *Làng nghề Kẹo dừa Mỏ Cày xứ dừa Bến Tre* — Sở Công Thương tỉnh Bến Tre.
37. **SRC-TIER1-BT-032** [Tier 1]: *Di sản Phi vật thể Quốc gia: Bánh tráng Mỹ Lồng và Bánh phồng Sơn Đốc* — Cục Di sản Văn hóa.
38. **SRC-TIER1-BT-033** [Tier 1]: *Vương quốc Cây giống và Hoa kiểng Cái Mơn - Chợ Lách* — Sở Nông nghiệp & PTNT Bến Tre.
39. **SRC-TIER2-BT-034** [Tier 2]: *Ẩm thực miệt vườn Cồn Phú Đa (Chợ Lách): Sinh thái ốc gạo và Bánh xèo ốc gạo* — Trường Đại học Cần Thơ.
40. **SRC-TIER1-BT-035** [Tier 1]: *Vùng nuôi nghêu, sò huyết và tôm quảng canh sinh thái Thạnh Phú - Bình Đại* — Chi cục Thủy sản Bến Tre.
41. **SRC-TIER1-TV-036** [Tier 1]: *Quần thể Vườn Dừa sáp đặc sản Cầu Kè* — Sở Nông nghiệp & PTNT Trà Vinh.
42. **SRC-TIER2-TV-037** [Tier 2]: *Đặc sắc Đêm hội Ok Om Bok của đồng bào Khmer tại Trà Vinh* — Báo Nhân Dân.
43. **SRC-TIER1-TV-038** [Tier 1]: *Bảo tồn và phát huy bản sắc văn hóa Khmer tỉnh Trà Vinh* — Cục Du lịch Quốc gia Việt Nam.
44. **SRC-TIER1-TV-039** [Tier 1]: *Quyết định đưa Lễ hội Đom Lơng Néak Tà vào Danh mục Di sản văn hóa phi vật thể quốc gia* — Cục Di sản Văn hóa.
45. **SRC-TIER2-TV-040** [Tier 2]: *Làng ven biển Mỹ Long và Lễ hội Cúng Biển (Ký sự THVL Tập 1)* — Đài PT-TH Vĩnh Long.
46. **SRC-TIER1-BT-041** [Tier 1]: *Lễ hội Nghinh Ông Bình Thắng huyện Bình Đại - Di sản văn hóa phi vật thể quốc gia* — Sở VHTTDL Bến Tre.
47. **SRC-TIER2-TV-042** [Tier 2]: *Trường Long Hòa và Duyên Hải: Điểm tựa tâm linh nghề biển từ Lễ hội Nghinh Ông Lăng Cồn Tàu* — Báo Vĩnh Long.
48. **SRC-TIER2-TV-043** [Tier 2]: *Vu Lan Thắng hội Cầu Kè - Di sản văn hóa phi vật thể giao thoa Việt - Hoa - Khmer* — Báo Vĩnh Long.
49. **SRC-TIER1-TV-048** [Tier 1]: *Cồn Chim Trà Vinh - Điểm sáng du lịch sinh thái nông nghiệp thuận thiên* — Cục Du lịch Quốc gia.
50. **SRC-TIER2-TV-049** [Tier 2]: *Cồn Hô - Ốc đảo xanh sông Cổ Chiên và mô hình du lịch tự thân độc đáo* — Báo Vĩnh Long.
51. **SRC-TIER1-BT-050** [Tier 1]: *Bảo tồn đa dạng sinh học Khu bảo tồn thiên nhiên đất ngập nước Thạnh Phú* — Sở TN&MT Bến Tre.
52. **SRC-TIER1-VL-051** [Tier 1]: *Bảo tồn và phát triển Làng nghề truyền thống Bánh tráng Cù lao Mây xã Lục Sĩ Thành* — UBND tỉnh Vĩnh Long.
53. **SRC-TIER2-VL-052** [Tier 2]: *Nét duyên nghề chằm nón lá truyền thống giữa dòng sông Hậu tại Cù lao Mây* — Đài PT-TH Vĩnh Long.
54. **SRC-TIER1-TV-053** [Tier 1]: *Xây dựng và bảo hộ nhãn hiệu chứng nhận Rượu Xuân Thạnh Trà Vinh* — Sở KH&CN Trà Vinh.
55. **SRC-TIER1-BT-054** [Tier 1]: *Phát triển chuỗi giá trị Làng nghề Rượu truyền thống Phú Lễ huyện Ba Tri* — Sở Công Thương Bến Tre.
56. **SRC-TIER1-TV-055** [Tier 1]: *Di sản Văn hóa Phi vật thể Quốc gia: Nghệ thuật Sân khấu Dù Kê Khmer Trà Vinh* — Cục Di sản Văn hóa.
57. **SRC-TIER2-TV-056** [Tier 2]: *Bếp Việt THVL: Bún nước lèo Trà Vinh và Cháo ám* — Đài PT-TH Vĩnh Long.
58. **SRC-TIER2-VL-057** [Tier 2]: *Làng nghề tàu hủ ky Mỹ Hòa: Trăm năm giữ lửa lò than bên bờ sông Cái Vồn* — Báo Vĩnh Long.
59. **SRC-TIER2-VL-058** [Tier 2]: *Phát triển sản phẩm du lịch đặc thù từ Làng nghề Gạch gốm đỏ Mang Thít* — Báo Vĩnh Long.
60. **SRC-TIER2-BT-063** [Tier 2]: *Làng hoa Chợ Lách tất bật chuẩn bị cho thị trường hoa kiểng Tết Bính Ngọ* — Đài PT-TH Vĩnh Long.
61. **SRC-TIER2-BT-064** [Tier 2]: *Giữ gìn hương vị trăm năm Làng nghề Bánh phồng Sơn Đốc và Bánh tráng Mỹ Lồng* — Báo Đồng Khởi.
62. **SRC-TIER1-VL-065** [Tier 1]: *Trà Ôn Vĩnh Long: Điểm sáng phát triển du lịch sinh thái miệt vườn sông nước* — Cục Du lịch Quốc gia.
63. **SRC-TIER1-TV-066** [Tier 1]: *Xã An Phú Tân Trà Vinh phát huy tiềm năng kinh tế vườn gắn với du lịch sinh thái* — Cục Du lịch Quốc gia.
64. **SRC-TIER2-BT-067** [Tier 2]: *Kẹo dừa Bến Tre - Thương hiệu Bà Hai Tỏ và hành trình bảo vệ thương hiệu Việt* — Đài PT-TH Vĩnh Long.
65. **SRC-TIER2-BT-068** [Tier 2]: *Tinh hoa bếp Việt: Củ hũ dừa Bến Tre - Món ngon thanh đạm miền sông nước* — Đài PT-TH Vĩnh Long.
66. **SRC-TIER2-VL-069** [Tier 2]: *Nghề dệt chiếu Cà Hôn và hành trình bảo tồn kỹ nghệ dệt lác thủ công* — Báo Vĩnh Long.
67. **SRC-TIER2-TV-070** [Tier 2]: *Bảo tàng Dừa Sáp Trà Vinh - Không gian văn hóa kết nối cộng đồng* — Đài PT-TH Vĩnh Long.

---

### Sổ Tay 3: Chính Sách & Pháp Luật (`ch-nh-s-ch-ph-p-lu-t-v-n-b-n-q`) — 3 Nguồn
68. **SRC-TIER1-VL-059** [Tier 1]: *Đề án Bảo tồn và Phát huy giá trị Di sản Đương đại Mang Thít thời kỳ 2021-2030 (QĐ 1293/QĐ-UBND)* — UBND tỉnh Vĩnh Long.
69. **SRC-TIER1-VL-060** [Tier 1]: *Phê duyệt Quy hoạch tỉnh Vĩnh Long thời kỳ 2021-2030, tầm nhìn đến năm 2050 (QĐ 1759/QĐ-TTg)* — Cổng TTĐT Chính phủ (`vanban.chinhphu.vn`).
70. **SRC-TIER1-VN-061** [Tier 1]: *Bộ Tiêu chí Du lịch Xanh áp dụng cho các cơ sở lưu trú và điểm du lịch vùng ĐBSCL* — Cục Du lịch Quốc gia Việt Nam (`vietnamtourism.gov.vn`).

---

## 4. Giá Trị Khai Thác & Hướng Dẫn Nạp Nguồn Số

### 4.1. Khai Thác Trong Dự Án (Grounding & Anti-Hallucination)
- Toàn bộ 70 nguồn được biên soạn với `summary_digest` giàu dữ liệu thực chứng (ngày âm lịch, số quyết định pháp lý, tọa độ địa bàn xã/phường, quy trình thủ công của nghệ nhân, tỷ lệ nguyên liệu, sự kiện lịch sử).
- Khi LLM thực hiện các truy vấn AEO/GEO về Vĩnh Long, các trích dẫn này đóng vai trò mỏ neo chân lý (Truth Anchors), ngăn chặn hoàn toàn việc sinh văn bản AI chung chung hoặc hallucination ngày lễ hội.

### 4.2. Hướng Dẫn Đồng Bộ Vào NotebookLM (Ingestion Protocol)
Khi browser session của MCP NotebookLM đã sẵn sàng xác thực (`get_health` trả về kết nối trực tiếp):
1. Có thể sử dụng công cụ MCP `call_mcp_tool(notebooklm:add_source)` theo từng dòng từ `outputs/notebooklm_curated_knowledge_sources.json`:
   * Với các URL cổng TTĐT truy cập trực tiếp: truyền `type="url"`, `content=source.url`, `title=source.title`, `notebook_id=source.target_notebook`.
   * Với các tài liệu nội bộ hoặc tài liệu PDF/văn bản lưu trữ: truyền `type="text"`, `content=source.summary_digest`, `title=source.title`, `notebook_id=source.target_notebook`.
2. Hạn ngạch tài khoản miễn phí: Tối đa 50 nguồn/sổ tay. Phân bổ hiện tại: Sổ tay 1 (17 nguồn), Sổ tay 2 (50 nguồn), Sổ tay 3 (3 nguồn) hoàn toàn vừa vặn trong ngưỡng giới hạn.

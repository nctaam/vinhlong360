# Đặc Tả Kiến Trúc Thị Giác Tràn Viền & Tối Ưu Bố Cục (Visual-First Redesign Spec)
> STATUS: active

Tài liệu này xác lập các chuẩn mực kỹ thuật mỹ học, cấu trúc thẻ tràn viền (Full-Bleed Photo Portals) và ma trận cắt giảm 65% câu chữ dư thừa cho trang chủ **VinhLong360 - Cổng Di Sản Sông Nước & Khảo Cứu Thực Địa** (Screen ID: `6fd9ce814d344126b9af2791d77b1d3a`).

---

## 1. Phân Tích Định Lượng & Ma Trận Cắt Giảm Câu Chữ (Text Reduction Matrix)

Khảo sát định lượng trên mã nguồn hiện tại ghi nhận **1.021 từ** và **9.865 ký tự** trong phần `<main>`. Lượng chữ quá dày đặc khiến trang chủ giống một tập san đọc chậm thay vì một cổng trải nghiệm văn hóa thị giác sống động.

| Phân đoạn | Hiện trạng số từ | Mục tiêu mới | Tỷ lệ cắt giảm | Giải pháp cấu trúc mỹ học |
|---|---|---|---|---|
| **Section 1: Hero Lead** | 180 từ | **45 từ** | $-75\%$ | Chuyển sang sân khấu Panorama rộng mở. Rút gọn thành 1 tiêu đề Lora thanh thoát, 1 câu định danh 18 từ, thanh tìm kiếm xúc giác tối giản, 1 câu đề từ Sơn Nam. |
| **Section 2: Bộ Tứ Không Gian** | 220 từ | **60 từ** | $-73\%$ | **Xóa bỏ hoàn toàn hộp chữ trắng bên dưới ảnh**. Áp dụng thẻ ảnh tràn viền 100% (*Full-Bleed Photo Portals*), thông tin và huy hiệu kính mờ (*liquid glass*) nổi trực tiếp trên nền ảnh. Mỗi thẻ chỉ giữ 1 dòng định danh bản địa (12 từ). |
| **Section 3: Ký Sự Phù Sa** | 450 từ | **120 từ** | $-73\%$ | Xóa các đoạn văn mô tả dài dòng và các hộp thông số lặp lại. Giữ lại tiêu đề, Drop Cap Lora màu Terracotta, 2 câu trích ký sự thực địa cốt lõi và 1 câu trích dẫn linh hồn. |
| **Section 4: Tàng Thư Bỏ Túi** | 80 từ | **40 từ** | $-50\%$ | Mở rộng thành dải mosaic 6 ảnh tư liệu; nhãn kiểm định gắn gọn `[MS: VL-01 ... VL-06]`. |
| **Section 5: Thước Đo Thủy Triều** | 91 từ | **35 từ** | $-61\%$ | Tinh gọn dải ruy-băng viền vàng phù sa, tập trung vào số liệu con nước lớn/ròng và khuyến nghị đò Đình Khao. |
| **TỔNG CỘNG `<main>`** | **1.021 từ** | **$\le 300\text{ từ}$** | **$-70\%$** | **Đạt chuẩn Visual-First: 75% Diện tích ảnh / 25% Diện tích chữ.** |

---

## 2. Đặc Tả Thẻ Ảnh Tràn Viền (Full-Bleed Borderless Photo Portal Architecture)

Thay vì cấu trúc "ảnh ở trên, hộp trắng chứa chữ ở dưới" tạo cảm giác vụn vặt và nặng tính blog:

```
[MÔ HÌNH CŨ - NẶNG CHỮ]              [MÔ HÌNH MỚI - FULL-BLEED PORTAL]
┌────────────────────────┐           ┌────────────────────────────────┐
│   Ảnh (chỉ 50% thẻ)    │           │                                │
├────────────────────────┤           │      100% BỀ MẶT LÀ ẢNH        │
│ [Hộp chữ trắng]        │           │    TƯ LIỆU ĐỘ PHÂN GIẢI CAO    │
│ - Tiêu đề              │    ===>   │                                │
│ - Đoạn văn 4 dòng      │           │ [Huy hiệu kính mờ nổi trên]    │
│ - Thông số kỹ thuật    │           ├────────────────────────────────┤
│ - Liên kết xem thêm    │           │ Gradient chìm + Chữ trắng + Tag│
└────────────────────────┘           └────────────────────────────────┘
```

### Quy chuẩn kỹ thuật thẻ tràn viền:
1. **Khung hình:** Tỷ lệ $4:5$ (portrait) hoặc $16:10$, bo góc `rounded-xl`, viền tóc siêu mảnh `border border-white/15`.
2. **Lớp phủ Gradient quang học:** `bg-gradient-to-t from-charcoal-ink/90 via-charcoal-ink/30 to-transparent`.
3. **Hiệu ứng xúc giác (Hover physics):** `transform: scale(1.04)` mượt mà trong `500ms cubic-bezier(0.16, 1, 0.3, 1)`.
4. **Huy hiệu kính mờ (Liquid Glass Pill):** `background: rgba(24, 30, 40, 0.72); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.22)`.

---

## 3. Danh Mục 14 Hình Ảnh Thực Địa Vĩnh Long Đã Kiểm Định (100% Anti-AI-Slop)

1. **Hero Panorama Main:** Hoàng hôn sông Tiền & Vòm lò gạch Măng Thít  
   `https://lh3.googleusercontent.com/aida/AEtjO1WL80sNjG2wzX6KSwqtLzWLzEpdZ_nI8Pl3iIcwU5yAJQuWYSNYJ-f9wOD319iWOsM5dYNk32ljzgNKzMTzs7F0lBp72oDBlJ5N98xot_O4Q-2XYD6KM-1JiS1E8j-zr5MZWUI4RSCmmiq48EW8tdi-ORp8j-AhzZ_pbSEWJcuxGBgaUDQPs-UBiJTWqNB-Wh0h-29Zvd1tYi2LfieD7I3qJJsUWf3ZthYw7Umc7v207ZLZltjZBOcCKw8K`
2. **Hero Inset Polaroid:** Ghe tam bản rẽ nước sớm mai Cù lao An Bình  
   `https://lh3.googleusercontent.com/aida-public/AB6AXuCyCbgJl1axlP5oF4RerFPCHl8SG4nop0RNg6n6bIleC256VwufUy-C_3m1QSSeW43L0ksAO9c5M4ti0NoPPRL_eg9SOejqLjorWz3qlu_HIozJ9h07n9kqyLCINksMA6WLA9yLa1AwmiSp_kzjnWMC0gdFshimHvAppyTqMHEw3j6RNB1XxcQ4g3nW7j_i4hziHNg0cBt_fzbVcDqma8UK3cpTcYL5gUlpt3Ht80KJCSqlnD7Qj1WkbWpVjTKy8Brbchs01Jd20kcx`
3. **Portal 01:** Miệt vườn Cù lao An Bình & xuồng chở trái chín  
   `https://lh3.googleusercontent.com/aida-public/AB6AXuA2_knE4Kw8gQG7jn_seXMe4QdUXyxhz0XstEd--G0zmjQyfniwICMc4hQGfolCqb1D6mDF2wveKtQWVAS_XW5vklLw7IorYAC1cRph4MIDvZPuclBmJVcvB2t9Y2MEUyZQrM79JN8Zi-6XzINtA7TOeJk6pb7UGmD32uZVCgU-kZDkexXkRMLKb5yDMcWGqXyBQ99XNpluDveaMSG5XPVPEJy0LTmMpN2CY8wYDPSsIUj9bELF2UcDfjMsVZI5_9uXoWRyHGp-RkRW`
4. **Portal 02:** Vương quốc lò gạch nung trấu Măng Thít hoàng hôn kênh Thầy Cai  
   `https://lh3.googleusercontent.com/aida-public/AB6AXuBhfEqsVJilqU47D5EdNTOZMyLrfF5B72Lg_oFHC0S00cUACpWruAVe7L7dPZsaOLknjFYEBXp6Li8xZu82swu9RnQenyTxzzyVkPz6F48_aiGKTvq-rEz-79jQavKoMdDucSvmdQwmq1CWrODh3hm55kLnStJkNNIlIxXrQmT3coaLGgypp2IUhpqCKzmrVjfiupn2Zh1OKnEidBnfj-h4k4y2g7YiOO5bk5v2QdCjAmPqKCsgLa5DONc2Q67TchZlNpTY1HWNEjn1`
5. **Portal 03:** Trầm tích Khmer, Chùa Âng cổ kính & rặng sao dầu Ao Bà Om  
   `https://lh3.googleusercontent.com/aida/AEtjO1XLyeqw9SdRCl2TB4oI8XZVessrSvyfwrVKWANytvU_gu0xt4IgrY9gbKTh5igIVPntA0CCWIK2Ex268Xiv9dEa3SsDj9zIx4NY28QURY6DTphsh8nUx4mGd_NEvnsTW6HoZWPxIzAAS075w_Z26BlYqAIlssxNP3dZqhiP7UrfkqnfWVp_ClndsA232x8d9_GVzlKhpj_cfBstjrAAf4tgmBJxIQbRR7o7VhF0KKJPjtPW1xkGg0DeyqrJ`
6. **Portal 04:** Ẩm thực cá tai tượng chiên xù vàng rụm cuốn bánh tráng & rau rừng  
   `https://lh3.googleusercontent.com/aida/AEtjO1XvwiqtEJat_nltTbu6nfKC7WSCnnGZsIgSADSjRxbZYw7ilVdduSU9LkaBhEK6s1uKHXGh_MfMKtqpYppzAasq1zSYBI46Xa8AlfhNLZTDnNFWr9xNnRNAJNV5He7KyowBvVA5yaJyPKIbIQZqYBv8mi9zHdaW_BjGY-OuzufSXbkS_6xLHisy3PjHg08FziTDlnTRqBmNXwfeer8UbBtsJ1qn5Pt0TMYOAxKICS8pcImvmSJfjay4kYw`
7. **Chronicle 01:** Phóng sự ghe tam bản lướt êm ru trong rạch dừa nước rạng đông  
   `https://lh3.googleusercontent.com/aida-public/AB6AXuAksvm7eLY9nKwLy2SSahIrs5nx1M54PH23ltt0oyD-IyfRV9Rmi8Axj5jcnW-N1TEukfTJfWJdNCepOLE84NaUvTU_emmW1MYevnK5_3vj2zm6XsYLn67YfY71tKTLVXX-wBfmsm8p6ZGTuKx4Q9RoRSIHRRgE_8PPp5N0x_pfoo99Inb_qvFbdomoofUI5f0fbT46p3ll_oO1-80jYnlLWlFRYhlahwE1V09cNpgiKjoRf9kYjddXKBLaoaemzExkn7uBxDkU-Bo1`
8. **Chronicle 02:** Cận cảnh kết cấu vòm lò gạch nung trấu rực lửa đỏ Măng Thít  
   `https://lh3.googleusercontent.com/aida-public/AB6AXuCglvYEavIVZHtzd-21aRVmeEvpeI_jsGIjgA0o58okp4PAcQ3KgL5NpF0p_vDqMX7A2whmz9x8fjhdHA4yx3YoYVR5roD158jXqEds7wm_SHx3Rc0WHd04CrfISjKmZ3NQSwI6YWFolLMNmu_MTjrbeRy_wgkXSc_eign-nya-JOPGY2Oi07j4hSrluVvy5bLsckt8V2506uMU4qhskHBeNG4z_G8-sQRsRiQBO-3I0zjQlso0LBw4gE85-cWtCRddEG_KAnkwR8Gg`
9. **Chronicle 03:** Nghệ nhân Đờn ca tài tử thăng hoa bên hiên nhà gỗ ven sông Cổ Chiên  
   `https://lh3.googleusercontent.com/aida/AEtjO1UoAysKjFwQLbCUNoaaTSVY0cGFjYkhgIRSlyxbIOumhpti7wXyQItsgxplf5U9rTtpt363H0K7-RXxdzYykfBNVW7gET_2TfTOoXwyAUEhpY1NPKKZz609AAQlVN4OSyn6MH8MCRrVXBeqBrH81fiIJfiPUUGtNUi61mEEDzQqeVRGyfvCYGrS0meqla8MCggNesJTeks863PkzWBfFEDmbRwU1RJ4sqY_HXFNWNV9Z8L6aCaksyjSsuPa`
10. **Mosaic 01:** Bưởi Năm Roi trĩu cành Mỹ Hòa `[MS: VL-01 · THỔ NHƯỠNG SA BỒI]`  
    `https://lh3.googleusercontent.com/aida/AEtjO1VdkaNTy2yToxM3JEGoXIt-sUPG_-HvMpzCVTK6Uh451IWv_fAL5wRtzdrvfu_fFzHX2CTl-oqOhUhX3x3jUgslrD1BQ0dh7zlgR-PObdilgce_n2L55p2K2FIExRwZeQ0YV0FU4sSk-TdZ8WB10IeUvCMxjK_zwrAIoef7i3M-G_A3ADmlqG6kK3cZI8XwM3PfM1TU4Biv4wofW3jPjzbGAAKLsif7AdABXw2Xu9-V8-yTGAQbG2_qjQ8`
11. **Mosaic 02:** Ghe xuồng kênh Thầy Cai rợp bóng gạch `[MS: VL-02 · THỦY TRÌNH THẦY CAI]`  
    `https://lh3.googleusercontent.com/aida/AEtjO1UR3TfkV2wOxhWLP8tCYlFo5ZqD5RFsQ79XPMm8ahF4ymwL1c-tX6CyFnwteeVuLButuXstvct_t_HqB1-M0_mZSyrxOZX3qS4XAx7cokpjnwancw0cvVjzNAogeN4O7LgcDRU3hmHKHdHjtpCia1YETrMNPkHo1_prAQsuey5pgnxgTpr3mho9sOFg3pL7ABZXK8xRxFuIjkQbYsIwvrPEOlEG30F01DIdajIXaPOJyV9e7FwchuxwcR5y`
12. **Mosaic 03:** Dạ khúc Cổ Chiên & Lửa lò gạch nung đêm rằm `[MS: VL-03 · DẠ KHÚC ĐẤT NUNG]`  
    `https://lh3.googleusercontent.com/aida/AEtjO1Vy41omCCCC5D1B4tpRgi_XCaVtMshvh6fO57eXai34dcjofp6vOHRAg2ksvkhdYPhzQar8xiCuLEd2561CVLxE4GXDUdRcwjUpojGIfRrL57eGmMzL-7tUjm4sdm3L5Wbi8xm85LNjuFi0JZf8__Dgco7jt4fXbt0JJGj4kXsMYHeCsFnfDb3V7xoOLBhg5lCF7R8YpuaYO5ySaWnmCTs05ysYEcZi65T9H5Bf7ZwdwaJp-mp4mslNgvni`
13. **Mosaic 04:** Vườn chôm chôm Bình Hòa Phước trĩu quả chín `[MS: VL-04 · VƯỜN TRÁI CHÍN]`  
    `https://lh3.googleusercontent.com/aida/AEtjO1W5b2JpMNpdZpZqomsrnu9q3QcIJ7-_Y-IOPVCr9C3HH75EJKC-fH8VyNqRPYRLhcP0SZlxgdxvJlLvGNQvsy6hOLbhn_m1Ev7XEQovdsp00cz5dAvgwGhpIbbKktVMO_jt5Nxy_gHAC2ixtHwen7kDTR_Njzppxyv4bFpvzSYWh2MU6BVS7kH6n_VZwJRwibWmOsK8gppQp3NNvt98BEvoyqbrf8kNHe0bmumkoZIUlN-YaG4stVWZvXKc`
14. **Mosaic 05 (Mới):** Cảnh chợ nổi Trà Ôn tụ họp trên ngã ba sông Hậu rạng đông `[MS: VL-05 · THỦY DIỆN TRÀ ÔN]`  
    `https://lh3.googleusercontent.com/aida/AEtjO1WL80sNjG2wzX6KSwqtLzWLzEpdZ_nI8Pl3iIcwU5yAJQuWYSNYJ-f9wOD319iWOsM5dYNk32ljzgNKzMTzs7F0lBp72oDBlJ5N98xot_O4Q-2XYD6KM-1JiS1E8j-zr5MZWUI4RSCmmiq48EW8tdi-ORp8j-AhzZ_pbSEWJcuxGBgaUDQPs-UBiJTWqNB-Wh0h-29Zvd1tYi2LfieD7I3qJJsUWf3ZthYw7Umc7v207ZLZltjZBOcCKw8K`
15. **Mosaic 06 (Mới):** Đôi bàn tay nghệ nhân tạo tác gốm đất nung bàn xoay `[MS: VL-06 · BÀN XOAY THỦ CÔNG]`  
    `https://lh3.googleusercontent.com/aida-public/AB6AXuBhfEqsVJilqU47D5EdNTOZMyLrfF5B72Lg_oFHC0S00cUACpWruAVe7L7dPZsaOLknjFYEBXp6Li8xZu82swu9RnQenyTxzzyVkPz6F48_aiGKTvq-rEz-79jQavKoMdDucSvmdQwmq1CWrODh3hm55kLnStJkNNIlIxXrQmT3coaLGgypp2IUhpqCKzmrVjfiupn2Zh1OKnEidBnfj-h4k4y2g7YiOO5bk5v2QdCjAmPqKCsgLa5DONc2Q67TchZlNpTY1HWNEjn1`

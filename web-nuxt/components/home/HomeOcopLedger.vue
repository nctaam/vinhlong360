<template>
  <!-- ĐIỂM DỪNG THỊ GIÁC 3. Kênh tri giác của nó là VIỀN DÀY, cố ý không giẫm lên
       hai điểm dừng kia: hero giữ kênh "khối tối", tin chính đặc sản giữ kênh
       "mảng màu". Ba kênh khác nhau thì nheo mắt vẫn đọc ra ba chỗ dừng; ba khối
       cùng kênh thì chúng triệt tiêu nhau (đo được ở vòng thẩm định có mắt).

       Đây là trạng thái E-LITE: khung + định nghĩa + lối vào. KHÔNG liệt kê sản
       phẩm 5 sao. E-full (sổ vinh danh có tên) cần chủ dự án duyệt danh sách ID
       trước — dữ liệu tự nó KHÔNG chốt được: trong 5 hàng mang ocop_star=5 có 2
       hàng cùng một thương hiệu (Vicosap) và 1 hàng mới chỉ "được đề xuất" lên
       Trung ương. Bốc bừa lên sổ vàng là khai khống §1.7.

       data-home-section="ocop-ledger" nằm NGOÀI allowlist 5 tên mà hai test thứ
       tự mục lọc theo, nên chèn vào khe giữa không phải sửa test nào. -->
  <section
    class="home-ocop"
    data-home-section="ocop-ledger"
    data-home-ocop-ledger
    aria-labelledby="home-ocop-title"
  >
    <div class="home-ocop__frame">
      <p class="home-ocop__dept">Chứng nhận quốc gia · Mỗi xã một sản phẩm</p>
      <h2 id="home-ocop-title" class="home-ocop__title">Sổ vàng OCOP</h2>

      <ul class="home-ocop__tiers">
        <li v-for="tier in TIERS" :key="tier.stars" class="home-ocop__tier">
          <span class="home-ocop__stars" :aria-label="`Hạng ${tier.stars} sao`">
            <IconLine v-for="n in tier.stars" :key="n" name="star" aria-hidden="true" />
          </span>
          <span class="home-ocop__tier-label">{{ tier.stars }} sao</span>
        </li>
      </ul>

      <p class="home-ocop__dek">
        Mỗi ngôi sao là một vòng thẩm định đã qua — không phải nhãn tự phong.
      </p>

      <NuxtLink to="/ocop" class="home-ocop__cta" data-home-ocop-cta>
        Xem sổ vàng <span class="home-ocop__arrow" aria-hidden="true">→</span>
      </NuxtLink>
    </div>
  </section>
</template>

<script setup lang="ts">
// KHÔNG có prop dữ liệu, và đó là chủ ý — mục này không thể render sai vì nó
// không phụ thuộc payload nào.
//
// Từng cân nhắc in số đếm theo hạng ("5 sao: 4 sản phẩm"). Bỏ, vì con số ấy chỉ
// đúng nếu trang chủ và trang /ocop rút hạng sao BẰNG CÙNG MỘT LUẬT — mà luật
// đang sống ở TypeScript (~/utils/ocop.ts) còn payload trang chủ dựng ở Python.
// Viết bản Python thứ hai là tự tạo ra hai bản của cùng một luật, đúng cái bẫy
// vừa phải gỡ ở C2. Con số ở lại /ocop, nơi nó được tính đúng một lần.
//
// Ba bậc là ĐỊNH NGHĨA của chương trình OCOP, không phải số liệu của dự án, nên
// không có gì để lệch. Cố ý không mô tả cấp nào chấm hạng nào: quy định đó vừa
// đổi theo cải cách hành chính 2 cấp (§1.6) và không được nói bừa.
const TIERS = [{ stars: 3 }, { stars: 4 }, { stars: 5 }] as const
</script>

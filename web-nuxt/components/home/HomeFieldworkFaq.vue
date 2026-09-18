<template>
  <section class="home-fieldwork-faq" aria-labelledby="fieldwork-faq-title" data-home-section="fieldwork-faq">
    <div class="fieldwork-faq__inner">
      <header class="fieldwork-faq__header">
        <div class="fieldwork-faq__tagline">
          <span class="fieldwork-faq__badge">
            <IconLine name="info" aria-hidden="true" />
            CHỈ DẪN THỰC ĐỊA
          </span>
          <span class="fieldwork-faq__count">4 chỉ dẫn then chốt</span>
        </div>
        <h2 id="fieldwork-faq-title" class="fieldwork-faq__title">
          Lữ khách cần biết trước khi <em class="editorial-italic-accent" aria-hidden="true">khởi hành</em>
        </h2>
        <p class="fieldwork-faq__subtitle">
          Giải đáp những câu hỏi cốt lõi về mùa vụ con nước, lộ trình di chuyển và chi phí trải nghiệm tại xứ sở miệt vườn Vĩnh Long.
        </p>
      </header>

      <div class="fieldwork-faq__accordion" role="region" aria-label="Danh sách câu hỏi thường gặp">
        <details
          v-for="(item, index) in faqItems"
          :key="item.q"
          class="fieldwork-faq__item"
          :open="index === 0"
        >
          <summary class="fieldwork-faq__summary">
            <span class="fieldwork-faq__question-text">{{ item.q }}</span>
            <span class="fieldwork-faq__icon" aria-hidden="true">
              <IconLine name="chevron-down" />
            </span>
          </summary>
          <div class="fieldwork-faq__answer">
            <p>{{ item.a }}</p>
            <div v-if="item.tips" class="fieldwork-faq__tips">
              <strong class="fieldwork-faq__tips-label">Mẹo bản địa:</strong>
              <span>{{ item.tips }}</span>
            </div>
          </div>
        </details>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
interface FaqEntry {
  q: string
  a: string
  tips?: string
}

const faqItems: FaqEntry[] = [
  {
    q: 'Thời điểm nào trong năm đến Vĩnh Long trải nghiệm mùa vụ đẹp nhất?',
    a: 'Vĩnh Long có 3 thời điểm đẹp nhất: Mùa trái cây trĩu cành từ tháng 5 đến tháng 8 (chôm chôm, sầu riêng Ri6, nhãn xuồng cù lao An Bình); Mùa con nước dâng từ tháng 8 đến tháng 10 ngắm sóng nước Cổ Chiên và thưởng thức cá linh tươi; Mùa hoa kiểng và làng nghề gốm đỏ Mang Thít vào vụ rực lửa từ tháng 11 đến Tết.',
    tips: 'Nên đi xuồng ba lá vào buổi sớm (6h30 – 8h30) khi nước dâng cao và nắng còn dịu mát.',
  },
  {
    q: 'Cách di chuyển từ TP.HCM và Cần Thơ về trung tâm Vĩnh Long?',
    a: 'Từ TP.HCM, bạn di chuyển theo cao tốc Trung Lương – Mỹ Thuận chỉ mất khoảng 1.5 – 2 giờ ô tô. Từ Cần Thơ, bạn chỉ mất 30–40 phút qua cầu Cần Thơ theo Quốc lộ 1A (khoảng 30 km). Nếu từ Bến Tre sang, bến phà Đình Khao hoạt động liên tục 24/7 nối đôi bờ sông Cổ Chiên.',
    tips: 'Phà Đình Khao có làn ưu tiên cho xe máy và ô tô con, mỗi chuyến chỉ mất 12–15 phút sang sông.',
  },
  {
    q: 'Nên chọn homestay sinh thái ven sông hay khách sạn trung tâm?',
    a: 'Nếu bạn yêu thích thiên nhiên và nhịp sống miệt vườn, hãy chọn các homestay đạt giải thưởng ASEAN trên cù lao An Bình (như Út Trinh, Ba Lình) để thưởng thức bữa tối bên rặng bần và chèo xuồng ban mai. Nếu cần tiện nghi đô thị và làm việc, các khách sạn ven sông Cổ Chiên ở bờ thành phố là lựa chọn thuận tiện.',
    tips: 'Homestay An Bình nên đặt trước 2–3 ngày vào dịp cuối tuần để chủ nhà chuẩn bị nguyên liệu chợ sớm tươi ngon.',
  },
  {
    q: 'Chi phí dự kiến cho chuyến lữ hành 2 ngày 1 đêm khoảng bao nhiêu?',
    a: 'Mức chi phí phổ biến chỉ từ 900.000đ đến 1.500.000đ mỗi người. Ngân sách này đã bao gồm lưu trú homestay (kèm điểm tâm), các bữa ăn đặc sản cá tai tượng chiên xù, xuồng chèo tham quan mương vườn và vé vào cổng các điểm di sản văn hóa.',
    tips: 'Các điểm di tích văn hóa như Văn Thánh Miếu, Bảo tàng tỉnh và Chùa Khmer Sanghamangala hoàn toàn miễn phí vé vào cổng.',
  },
]
</script>

<style scoped>
.home-fieldwork-faq{padding:var(--space-8) 0;border-top:1px dashed color-mix(in srgb,var(--color-border) 60%,transparent)}
.fieldwork-faq__inner{max-width:var(--container-max,1120px);margin:0 auto;padding:0 var(--space-4)}
.fieldwork-faq__header{margin-bottom:var(--space-6)}
.fieldwork-faq__tagline{display:flex;align-items:center;gap:var(--space-3);margin-bottom:var(--space-2)}
.fieldwork-faq__badge{display:inline-flex;align-items:center;gap:6px;font-size:var(--text-xs);font-weight:var(--weight-bold);letter-spacing:.08em;color:var(--mangthit-600)}
.fieldwork-faq__count{font-size:11px;font-family:var(--font-mono,monospace);padding:2px 8px;border-radius:var(--radius-pill,999px);border:1px solid color-mix(in srgb,var(--color-border) 80%,transparent);color:var(--color-text-muted)}
.fieldwork-faq__title{font-family:var(--font-serif,'Lora',Georgia,serif);font-size:clamp(1.5rem,2.5vw,2rem);font-weight:400;line-height:1.25;color:var(--color-text);margin:0 0 var(--space-2)}
.fieldwork-faq__subtitle{font-size:var(--text-sm);color:var(--color-text-muted);max-width:640px;margin:0;line-height:1.6}
.fieldwork-faq__accordion{display:flex;flex-direction:column;gap:var(--space-3)}
.fieldwork-faq__item{border-radius:var(--radius-surface,20px);background:color-mix(in srgb,var(--color-surface) 70%,transparent);border:1px solid color-mix(in srgb,var(--color-border) 60%,transparent);overflow:hidden;transition:border-color .2s ease,background-color .2s ease,box-shadow .2s ease}
.fieldwork-faq__item:hover{border-color:color-mix(in srgb,var(--mangthit-600) 40%,transparent);background:var(--color-surface)}
.fieldwork-faq__item[open]{border-color:color-mix(in srgb,var(--mangthit-600) 60%,transparent);box-shadow:0 8px 24px rgba(var(--black-rgb),.04)}
.fieldwork-faq__summary{display:flex;align-items:center;justify-content:space-between;gap:var(--space-3);padding:var(--space-4) var(--space-5);font-size:var(--text-base);font-weight:500;color:var(--color-text);cursor:pointer;list-style:none;min-height:44px;user-select:none;border-radius:var(--radius-surface,20px);transition:background-color .2s ease,transform .15s ease}
.fieldwork-faq__summary:active{transform:scale(.995)}
.fieldwork-faq__summary:focus-visible{outline:2px solid var(--color-focus);outline-offset:-2px}
.fieldwork-faq__question-text{flex:1;line-height:1.4}
.fieldwork-faq__icon{flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:var(--radius-pill,999px);background:color-mix(in srgb,var(--color-border) 40%,transparent);color:var(--color-text-muted);transition:transform .25s cubic-bezier(.16,1,.3,1),background-color .2s ease,color .2s ease}
.fieldwork-faq__item[open] .fieldwork-faq__icon{transform:rotate(180deg);background:var(--mangthit-600);color:rgb(var(--white-rgb))}
.fieldwork-faq__answer{padding:0 var(--space-5) var(--space-5);font-size:var(--text-sm);color:var(--color-text-muted);line-height:1.65;border-top:1px dashed color-mix(in srgb,var(--color-border) 40%,transparent);margin-top:var(--space-1);padding-top:var(--space-3)}
.fieldwork-faq__answer p{margin:0 0 var(--space-2)}
.fieldwork-faq__tips{display:flex;align-items:flex-start;gap:var(--space-2);padding:var(--space-2) var(--space-3);border-radius:var(--radius-control,12px);background:color-mix(in srgb,var(--mangthit-600) 8%,transparent);color:var(--color-text);font-size:var(--text-xs);line-height:1.5}
.fieldwork-faq__tips-label{color:var(--mangthit-600);white-space:nowrap}
@media (prefers-reduced-motion:reduce){.fieldwork-faq__item,.fieldwork-faq__icon{transition:none}}
</style>

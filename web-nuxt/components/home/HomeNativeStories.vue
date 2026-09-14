<template>
  <section class="home-native-stories" data-home-section="native-stories" aria-labelledby="home-stories-title">
    <div class="home-native-stories__header">
      <span class="home-native-stories__eyebrow">Ký sự thổ nhưỡng · Hồn cốt phù sa</span>
      <h2 id="home-stories-title">Bản địa kể chuyện</h2>
      <p class="home-native-stories__lead">
        Những câu chuyện chân thực từ nếp sống mộc mạc, nơi dòng sông hiền hòa ôm ấp những phận người và giá trị di sản.
      </p>
    </div>
    <div class="home-native-stories__grid">
      <!-- Story 1: Left Lead Feature -->
      <NuxtLink to="/kham-pha" class="home-story-card home-story-card--primary">
        <img
          src="/img/spread/cu-lao-an-binh.webp"
          alt="Làng du lịch cộng đồng cù lao An Bình"
          class="home-story-card__img"
          width="800"
          height="500"
          loading="lazy"
          decoding="async"
          @error="onImgError"
        >
        <span class="home-story-card__scrim" />
        <div class="home-story-card__content">
          <blockquote class="home-story-card__quote">
            <p class="home-story-card__quote-text">“Phù sa Cổ Chiên nuôi lớn những rặng bần, rặng dừa và bồi đắp tâm hồn hào sảng của đất cù lao qua bao thế hệ.”</p>
            <cite class="home-story-card__cite">Ký sự Điền dã · Ban biên tập VinhLong360</cite>
          </blockquote>
          <h3>Nhịp chèo trên rạch An Bình</h3>
          <p>Xuôi dòng rạch nhỏ dưới bóng bần cổ thụ, nương theo nhịp con nước lớn ròng rẽ lối vào những vườn chôm chôm, sầu riêng chín rộ.</p>
        </div>
      </NuxtLink>

      <!-- Story 2 & 3: Right Stack -->
      <div class="home-native-stories__side">
        <NuxtLink to="/kham-pha" class="home-story-card home-story-card--secondary">
          <img
            src="/img/spread/song-nuoc.webp"
            alt="Vườn dừa nước & phù sa Cổ Chiên"
            class="home-story-card__img"
            width="500"
            height="300"
            loading="lazy"
            decoding="async"
            @error="onImgError"
          >
          <span class="home-story-card__scrim" />
          <div class="home-story-card__content">
            <h3>Trăm năm giữ lửa Măng Thít</h3>
            <p>Khói lam bảng lảng trên dòng kênh Thầy Cai, nơi những lò gạch gốm đỏ nung trấu gìn giữ kỹ nghệ tạo tác của bao đời nghệ nhân.</p>
          </div>
        </NuxtLink>

        <div class="home-story-callout">
          <div class="home-story-callout__badge">
            <IconLine name="bulb" />
          </div>
          <h4>Tàng thư khảo cứu điền dã</h4>
          <p>Ghi chép thực địa về phong thổ, con nước, nếp sống bến bờ và truyền thống ẩm thực Vĩnh Long xưa và nay.</p>
          <NuxtLink to="/kham-pha" class="home-story-callout__action">
            Xem tuyển tập <IconLine name="arrow-right" />
          </NuxtLink>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
function onImgError(e: Event) {
  const img = e.target as HTMLImageElement
  if (img && !img.dataset.fallbackApplied) {
    img.dataset.fallbackApplied = 'true'
    img.src = '/img/spread/cu-lao-an-binh.webp'
  }
}
</script>

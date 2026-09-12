<template>
  <section class="home-native-stories" data-home-section="native-stories" aria-labelledby="home-stories-title">
    <div class="home-native-stories__header">
      <span class="home-native-stories__eyebrow">The Soul of the Mekong</span>
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
          <h3>Hơi thở miền sông nước</h3>
          <p>Cùng xuôi dòng kênh rạch chằng chịt, lắng nghe tiếng chèo khua nước và khám phá nếp nhà dung dị của người dân miệt vườn.</p>
        </div>
      </NuxtLink>

      <!-- Story 2 & 3: Right Stack -->
      <div class="home-native-stories__side">
        <NuxtLink to="/kham-pha" class="home-story-card home-story-card--secondary">
          <img
            src="/img/spread/song-nuoc.webp"
            alt="Vườn dừa sinh thái Cầu Kè"
            class="home-story-card__img"
            width="500"
            height="300"
            loading="lazy"
            decoding="async"
            @error="onImgError"
          >
          <span class="home-story-card__scrim" />
          <div class="home-story-card__content">
            <h3>Bóng dừa vươn cao</h3>
            <p>Dưới tán lá xanh mát, cuộc sống trôi qua tĩnh lặng, êm đềm như một khúc ca dao.</p>
          </div>
        </NuxtLink>

        <div class="home-story-callout">
          <div class="home-story-callout__badge">
            <IconLine name="bulb" />
          </div>
          <h4>Khám phá thêm giai thoại</h4>
          <p>Đọc những câu chuyện chưa từng được kể về đất và người Vĩnh Long.</p>
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

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
          src="https://lh3.googleusercontent.com/aida/AP1WRLsRbAhYwqPsipNYG1T05OrVkOcggAUC6GAQh8LXbOfSkhDMUCB-T4xDPhs4wE48MuY1kbOLW9nKI7FS_Shv0YH2EzTa_UXO1LfNzGWdTEA1VradAleoN0c9_F4Pnjqrd2-fjWNILpT1un-8pGFmlP8TQMjyznDk4vyXMVLAngkNlUPkLqBcnRUM4xCBp5BS-1hvmcUxa2LqnzRIefvVNe6u7t5UJX7CJamguTR02ORNjvNhADyhdCzLLHWt"
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
            src="https://lh3.googleusercontent.com/aida/AP1WRLvjxEggHbzRxMfDnyGneoufLmZNRImHa_OzMS4fWKufGg9HdaImjDdriGjbcGqVUj5MLGzr-hs-a3yNguX_VI-V-5HrEu8c1IOfZ9rIL7g7l-urXCtSdRLa8fgqkQDRTTya-l20dpTWCunqV7hV7x-ZeugX60gX9f_OFWb2dQ9tAdUEU17W_ZfUzlVo045WgKgtXWfxwcAX3diTyfVTPs4IuJz_qZtwQrAHi-lsX7Cbuva1S4XxhtLCCw-p"
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

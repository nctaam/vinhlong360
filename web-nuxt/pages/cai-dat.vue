<template>
  <section class="page settings-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cài đặt' }]" />

    <div v-if="!isLoggedIn" class="settings-guest card">
      <p class="dateline-eyebrow">QUẦY TIẾP TÂN</p>
      <h1>Cài đặt</h1>
      <p>Bạn cần đăng nhập để chỉnh sửa hồ sơ.</p>
      <button type="button" class="btn btn-primary" @click="openAuth()">Đăng nhập</button>
    </div>

    <template v-else>
    <p class="dateline-eyebrow">QUẦY TIẾP TÂN</p>
    <h1 class="settings-title">Cài đặt</h1>
    <p class="settings-dek">Nơi giữ chìa khoá cho hồ sơ của bạn — đổi mật khẩu, bật bảo mật hai lớp, hoặc chọn ai được xem những gì bạn chia sẻ.</p>

    <div class="settings-overview" aria-label="Tổng quan tài khoản">
      <div class="settings-overview-item">
        <span class="so-label">Hồ sơ</span>
        <strong>{{ settingsProfileCompletion }}%</strong>
        <div class="so-bar" aria-hidden="true"><span :style="{ width: settingsProfileCompletion + '%' }"></span></div>
      </div>
      <div class="settings-overview-item">
        <span class="so-label">Bảo mật</span>
        <strong>{{ hasPassword ? 'Đã có mật khẩu' : 'Cần đặt mật khẩu' }}</strong>
        <NuxtLink to="#bao-mat" class="so-link" @click.prevent="setTab('bao-mat')">Kiểm tra</NuxtLink>
      </div>
      <div class="settings-overview-item">
        <span class="so-label">Phiên đăng nhập</span>
        <strong>{{ sessionsSummary }}</strong>
        <NuxtLink to="#bao-mat" class="so-link" @click.prevent="setTab('bao-mat')">Quản lý</NuxtLink>
      </div>
      <div class="settings-overview-item">
        <span class="so-label">Thông báo</span>
        <strong>{{ notifSummary }}</strong>
        <NuxtLink to="#thong-bao" class="so-link" @click.prevent="setTab('thong-bao')">Tùy chỉnh</NuxtLink>
      </div>
      <div class="settings-overview-item">
        <span class="so-label">Quyền riêng tư</span>
        <strong>{{ privacySummary }}</strong>
        <NuxtLink to="#rieng-tu" class="so-link" @click.prevent="setTab('rieng-tu')">Xem</NuxtLink>
      </div>
    </div>
    <div class="settings-hash-anchors" aria-hidden="true">
      <span v-for="t in TABS" :id="t.key" :key="`anchor-${t.key}`"></span>
    </div>

    <!-- Tab navigation -->
    <nav class="settings-tabs" role="tablist" aria-label="Cài đặt" aria-orientation="horizontal" @keydown="onTabKeydown">
      <button
        v-for="t in TABS" :key="t.key" type="button" role="tab"
        :id="`tab-${t.key}`"
        class="settings-tab" :class="{ active: activeTab === t.key }"
        :aria-selected="activeTab === t.key"
        :aria-controls="`panel-${t.key}`"
        :tabindex="activeTab === t.key ? 0 : -1"
        @click="setTab(t.key)"
      >
        <span class="settings-tab-icon" aria-hidden="true">{{ t.icon }}</span>
        {{ t.label }}
      </button>
    </nav>

    <!-- Tab: Hồ sơ -->
    <div v-show="activeTab === 'ho-so'" id="panel-ho-so" class="settings-card card sediment-head" role="tabpanel" aria-labelledby="tab-ho-so" :hidden="activeTab !== 'ho-so'" :tabindex="activeTab === 'ho-so' ? 0 : -1">
      <h2>Hồ sơ cá nhân</h2>
      <form class="settings-form" @submit.prevent="save">
        <div class="sf-avatar-section">
          <button type="button" class="sf-avatar-preview" aria-label="Thay đổi ảnh đại diện" @click="($refs.avatarInput as HTMLInputElement)?.click()">
            <img v-if="(avatarPreview || user?.avatar_url) && !avatarBroken" :src="avatarPreview || user?.avatar_url!" alt="Avatar" class="sf-avatar-img" width="96" height="96" loading="lazy" decoding="async" @error="avatarBroken = true" />
            <AvatarPlaceholder v-if="avatarBroken || (!avatarPreview && !user?.avatar_url)" :initial="user?.display_name?.[0]?.toUpperCase()" />
            <span class="sf-avatar-overlay">&#128247;</span>
          </button>
          <div class="sf-avatar-info">
            <span class="sf-label">Ảnh đại diện</span>
            <span class="sf-hint">JPEG, PNG hoặc WebP. Tối đa 12MB.</span>
            <button type="button" class="btn btn-ghost btn-sm" :disabled="uploadingAvatar" @click="($refs.avatarInput as HTMLInputElement)?.click()">
              {{ uploadingAvatar ? 'Đang tải...' : 'Đổi ảnh' }}
            </button>
          </div>
          <input ref="avatarInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="onAvatarChange" />
        </div>

        <div class="sf-cover-section">
          <button type="button" class="sf-cover-preview" aria-label="Thay đổi ảnh bìa" @click="($refs.coverInput as HTMLInputElement)?.click()">
            <img v-if="coverPreview || user?.cover_url" :src="coverPreview || user?.cover_url!" alt="Ảnh bìa" class="sf-cover-img" width="640" height="160" loading="lazy" decoding="async" @error="(e: Event) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
            <div v-else class="sf-cover-placeholder">
              <span>Thêm ảnh bìa</span>
            </div>
            <span class="sf-avatar-overlay">&#128247;</span>
          </button>
          <div class="sf-avatar-info">
            <span class="sf-label">Ảnh bìa</span>
            <span class="sf-hint">Ảnh ngang, tỉ lệ 3:1. Tối đa 12MB.</span>
            <button type="button" class="btn btn-ghost btn-sm" :disabled="uploadingCover" @click="($refs.coverInput as HTMLInputElement)?.click()">
              {{ uploadingCover ? 'Đang tải...' : 'Đổi ảnh bìa' }}
            </button>
          </div>
          <input ref="coverInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="onCoverChange" />
        </div>

        <div class="sf-field sf-readonly-group">
          <span class="sf-label">Số điện thoại <span class="sf-hint">— không thể thay đổi</span></span>
          <input type="tel" class="sf-input sf-readonly" :value="user?.phone" readonly tabindex="0" />
        </div>

        <div class="sf-field sf-readonly-group">
          <span class="sf-label">Username <span class="sf-hint">— không thể thay đổi</span></span>
          <div class="sf-username-row">
            <span class="sf-username-prefix">vinhlong360.vn/nguoi-dung/</span>
            <input type="text" class="sf-input sf-username-input sf-readonly" :value="user?.username || user?.id || '—'" readonly tabindex="0" />
          </div>
        </div>

        <label class="sf-field">
          <span class="sf-label">Họ và tên</span>
          <input
            v-model="fullName"
            type="text"
            class="sf-input"
            maxlength="100"
            placeholder="Họ và tên thật"
          />
        </label>

        <label class="sf-field">
          <span class="sf-label">Tên hiển thị</span>
          <input
            v-model="displayName"
            type="text"
            class="sf-input"
            enterkeyhint="done"
            maxlength="50"
            required
            :aria-invalid="!!nameError"
            placeholder="Tên bạn muốn hiển thị"
          />
          <span v-if="nameError" class="sf-error" role="alert">{{ nameError }}</span>
        </label>

        <label class="sf-field">
          <span class="sf-label">Giới thiệu <span class="sf-hint">({{ bio.length }}/300)</span></span>
          <textarea
            v-model="bio"
            class="sf-input sf-textarea"
            maxlength="300"
            rows="4"
            placeholder="Đôi dòng về bạn (không bắt buộc)"
          ></textarea>
        </label>

        <label class="sf-field">
          <span class="sf-label">Email</span>
          <input
            v-model="email"
            type="email"
            class="sf-input"
            maxlength="200"
            placeholder="email@example.com"
            autocomplete="email"
          />
        </label>

        <label class="sf-field">
          <span class="sf-label">Thông tin liên hệ <span class="sf-hint">— Zalo, Facebook, v.v.</span></span>
          <textarea
            v-model="contactInfo"
            class="sf-input sf-textarea"
            maxlength="500"
            rows="2"
            placeholder="Zalo: 0901234567, Facebook: facebook.com/ten-cua-ban"
          ></textarea>
        </label>

        <div class="sf-actions">
          <button type="submit" class="btn btn-primary" :disabled="saving" :aria-busy="saving">
            <span v-if="saving" class="spinner spinner-sm" aria-hidden="true"></span>
            {{ saving ? 'Đang lưu…' : 'Lưu thay đổi' }}
          </button>
          <NuxtLink v-if="user" :to="userPath(user.username || user.id)" class="btn btn-ghost">Xem hồ sơ</NuxtLink>
        </div>
      </form>
    </div>

    <!-- Tab: Bảo mật -->
    <div v-if="activeTab === 'bao-mat'" id="panel-bao-mat" role="tabpanel" aria-labelledby="tab-bao-mat">
      <div class="settings-card card sediment-head">
        <h2>Mật khẩu</h2>
        <p v-if="hasPasswordKnown && !hasPassword" class="sf-hint">Bạn chưa đặt mật khẩu. Đặt mật khẩu để đăng nhập nhanh hơn.</p>
        <form class="settings-form" @submit.prevent="savePassword">
          <label v-if="hasPassword" class="sf-field">
            <span class="sf-label">Mật khẩu hiện tại</span>
            <input v-model="currentPw" type="password" class="sf-input" autocomplete="current-password" required />
          </label>
          <label class="sf-field">
            <span class="sf-label">{{ hasPassword ? 'Mật khẩu mới' : 'Đặt mật khẩu' }}</span>
            <input v-model="newPw" type="password" class="sf-input" minlength="6" autocomplete="new-password" required />
            <div v-if="newPw" class="pw-strength" aria-live="polite">
              <div class="pw-bar">
                <span v-for="i in 4" :key="i" :class="['pw-segment', { filled: i <= pwStrength.score }]" :style="i <= pwStrength.score ? { background: pwStrength.color } : {}"></span>
              </div>
              <span class="pw-label" :style="{ color: pwStrength.color }">{{ pwStrength.label }}</span>
            </div>
          </label>
          <label class="sf-field">
            <span class="sf-label">Xác nhận mật khẩu</span>
            <input v-model="confirmPw" type="password" class="sf-input" minlength="6" autocomplete="new-password" required />
            <span v-if="confirmPw && confirmPw !== newPw" class="sf-error" role="alert">Mật khẩu xác nhận không khớp</span>
          </label>
          <div class="sf-actions">
            <button type="submit" class="btn btn-primary" :disabled="savingPw">
              {{ savingPw ? 'Đang lưu...' : (hasPassword ? 'Đổi mật khẩu' : 'Đặt mật khẩu') }}
            </button>
          </div>
        </form>
      </div>

      <div class="settings-card card sediment-head">
        <h2>Xác thực 2 bước (2FA)</h2>
        <div v-if="twoFALoading" class="sf-loading" role="status" aria-label="Đang tải trạng thái 2FA"><div class="spinner spinner-sm"></div> Đang tải...</div>
        <template v-else-if="recoveryCodes.length">
          <p class="sf-hint">Lưu các mã khôi phục này ở nơi an toàn — mỗi mã dùng một lần khi mất thiết bị.</p>
          <ul class="recovery-list"><li v-for="c in recoveryCodes" :key="c"><code>{{ c }}</code></li></ul>
          <div class="rc-actions">
            <button type="button" class="btn btn-secondary btn-sm" @click="copyRecoveryCodes">Sao chép</button>
            <button type="button" class="btn btn-secondary btn-sm" @click="downloadRecoveryCodes">Tải xuống</button>
            <button type="button" class="btn btn-ghost btn-sm" @click="recoveryCodes = []">Đã lưu, đóng</button>
          </div>
        </template>
        <template v-else-if="twoFA.enabled">
          <p class="sf-hint">✅ Đã bật. Còn {{ twoFA.recovery_remaining }} mã khôi phục.</p>
          <label class="sf-field">
            <span class="sf-label">Nhập mã để tắt 2FA</span>
            <input v-model="disableCode" type="text" inputmode="numeric" class="sf-input" placeholder="Mã 6 số hoặc mã khôi phục" />
          </label>
          <button type="button" class="btn btn-danger-text btn-sm" :disabled="securityBusy" @click="withBusy(() => disable2FA())">Tắt xác thực 2 bước</button>
        </template>
        <template v-else-if="setupData">
          <p class="sf-hint">Quét mã QR bằng Google Authenticator / Authy, rồi nhập mã 6 số.</p>
          <img :src="setupData.qr" alt="QR 2FA" class="qr-img" width="180" height="180" />
          <p class="sf-hint">Hoặc nhập khoá thủ công: <code>{{ setupData.secret }}</code></p>
          <label class="sf-field">
            <span class="sf-label">Mã xác nhận</span>
            <input v-model="setupCode" type="text" inputmode="numeric" maxlength="6" class="sf-input" />
          </label>
          <button type="button" class="btn btn-primary btn-sm" :disabled="securityBusy" @click="withBusy(() => confirm2FASetup())">Xác nhận &amp; bật</button>
        </template>
        <template v-else>
          <p class="sf-hint">Thêm một lớp bảo vệ: yêu cầu mã từ ứng dụng xác thực khi đăng nhập.</p>
          <button type="button" class="btn btn-primary btn-sm" :disabled="securityBusy" @click="withBusy(() => begin2FASetup())">Bật xác thực 2 bước</button>
        </template>
      </div>

      <div class="settings-card card sediment-head">
        <h2>Phiên đăng nhập</h2>
        <div v-if="sessionsLoading" class="sf-loading" role="status" aria-label="Đang tải phiên"><div class="spinner spinner-sm"></div> Đang tải...</div>
        <div v-else-if="sessions.length" class="sessions-list">
          <div v-for="s in sessions" :key="s.id" :class="['session-item', { current: s.is_current }]">
            <div class="session-info">
              <span class="session-ua">{{ shortUA(s.user_agent) }}</span>
              <span class="sf-hint">{{ s.ip_address }} &middot; {{ timeAgo(s.created_at) }}</span>
            </div>
            <span v-if="s.is_current" class="session-badge">Hiện tại</span>
            <button v-else type="button" class="btn btn-ghost btn-sm btn-danger-text" :disabled="securityBusy" @click="withBusy(() => revokeSession(s.id))">Thu hồi</button>
          </div>
        </div>
        <p v-else class="sf-hint">Không có phiên nào.</p>
        <p v-if="hiddenSystemSessions" class="sf-hint session-system-note">
          Đã ẩn {{ hiddenSystemSessions }} phiên hệ thống để danh sách chỉ còn các phiên người dùng cần quản lý.
        </p>
      </div>

      <div v-if="twoFA.enabled" class="settings-card card sediment-head">
        <h2>Thiết bị tin cậy</h2>
        <div v-if="trustedDevices.length" class="sessions-list">
          <div v-for="d in trustedDevices" :key="d.id" class="session-item">
            <div class="session-info">
              <span class="session-ua">{{ d.device_name || 'Thiết bị' }}</span>
              <span class="sf-hint">{{ d.ip }} &middot; {{ timeAgo(d.last_used_at) }}</span>
            </div>
            <button type="button" class="btn btn-ghost btn-sm btn-danger-text" :disabled="securityBusy" @click="withBusy(() => removeTrustedDevice(d.id))">Xoá</button>
          </div>
        </div>
        <p v-else class="sf-hint">Chưa có thiết bị tin cậy nào.</p>
      </div>

      <div class="settings-card card sediment-head">
        <h2>Lịch sử đăng nhập</h2>
        <div v-if="loginHistoryLoading" class="sf-loading" role="status" aria-label="Đang tải lịch sử"><div class="spinner spinner-sm"></div> Đang tải...</div>
        <div v-else-if="loginHistory.length" class="sessions-list">
          <div v-for="h in loginHistory" :key="h.id" :class="['session-item', { 'login-fail': !h.success }]">
            <div class="session-info">
              <span class="session-ua">{{ h.method === 'otp' ? 'OTP' : 'Mật khẩu' }} — {{ h.success ? 'Thành công' : 'Thất bại' }}</span>
              <span class="sf-hint">{{ h.ip }} &middot; {{ timeAgo(h.created_at) }}</span>
            </div>
            <span :class="h.success ? 'login-ok' : 'login-bad'">{{ h.success ? '✓' : '✗' }}</span>
          </div>
        </div>
        <p v-else class="sf-hint">Chưa có lịch sử.</p>
      </div>
    </div>

    <!-- Tab: Thông báo -->
    <div v-if="activeTab === 'thong-bao'" id="panel-thong-bao" class="settings-card card sediment-head" role="tabpanel" aria-labelledby="tab-thong-bao">
      <h2>Tùy chọn thông báo</h2>
      <p class="sf-hint sf-hint-spaced">Chọn loại thông báo bạn muốn nhận.</p>
      <div v-if="notifPrefsLoading" class="sf-loading" role="status" aria-label="Đang tải tùy chọn"><div class="spinner spinner-sm"></div> Đang tải...</div>
      <div v-else class="notif-prefs">
        <label v-for="np in NOTIF_TYPES" :key="np.key" class="notif-pref-item">
          <div class="notif-pref-info">
            <span class="notif-pref-icon" aria-hidden="true">{{ np.icon }}</span>
            <div>
              <strong>{{ np.label }}</strong>
              <span class="sf-hint">{{ np.desc }}</span>
            </div>
          </div>
          <input type="checkbox" :checked="notifPrefs[np.pref]" class="toggle" @change="toggleNotifPref(np.pref)" />
        </label>
      </div>
    </div>

    <!-- Tab: Giao diện -->
    <div v-if="activeTab === 'giao-dien'" id="panel-giao-dien" class="settings-card card sediment-head" role="tabpanel" aria-labelledby="tab-giao-dien">
      <h2>Giao diện</h2>
      <div class="sf-field">
        <span class="sf-label">Chế độ màu</span>
        <div class="theme-options">
          <button type="button" :class="['theme-btn', { active: colorMode === 'light' }]" @click="setColorMode('light')">
            <span class="theme-icon">☀️</span> Sáng
          </button>
          <button type="button" :class="['theme-btn', { active: colorMode === 'dark' }]" @click="setColorMode('dark')">
            <span class="theme-icon">🌙</span> Tối
          </button>
          <button type="button" :class="['theme-btn', { active: colorMode === 'system' }]" @click="setColorMode('system')">
            <span class="theme-icon">💻</span> Hệ thống
          </button>
        </div>
        <span class="sf-hint">Chế độ "Hệ thống" tự động theo cài đặt thiết bị của bạn.</span>
      </div>
    </div>

    <!-- Tab: Quyền riêng tư -->
    <div v-if="activeTab === 'rieng-tu'" id="panel-rieng-tu" class="settings-card card sediment-head" role="tabpanel" aria-labelledby="tab-rieng-tu">
      <h2>Quyền riêng tư</h2>
      <div v-if="privacyLoading" class="sf-loading" role="status" aria-label="Đang tải cài đặt"><div class="spinner spinner-sm"></div> Đang tải...</div>
      <div v-else class="settings-form">
        <div class="sf-field">
          <span class="sf-label">Ai xem được hồ sơ?</span>
          <span class="sf-hint">Kiểm soát ai có thể xem bài viết, hoạt động và danh sách yêu thích.</span>
          <div class="theme-options">
            <button type="button" :class="['theme-btn', { active: privacy.profile_visibility === 'public' }]" @click="setPrivacy('profile_visibility', 'public')">
              Công khai
            </button>
            <button type="button" :class="['theme-btn', { active: privacy.profile_visibility === 'followers' }]" @click="setPrivacy('profile_visibility', 'followers')">
              Người theo dõi
            </button>
            <button type="button" :class="['theme-btn', { active: privacy.profile_visibility === 'private' }]" @click="setPrivacy('profile_visibility', 'private')">
              Riêng tư
            </button>
          </div>
        </div>
        <label class="notif-pref-item">
          <div class="notif-pref-info">
            <span class="notif-pref-icon">📊</span>
            <div>
              <strong>Hiển thị hoạt động</strong>
              <span class="sf-hint">Cho người khác xem bạn đã thích, bình luận gì gần đây.</span>
            </div>
          </div>
          <input type="checkbox" class="toggle" :checked="privacy.show_activity" @change="setPrivacy('show_activity', !privacy.show_activity)" />
        </label>
        <label class="notif-pref-item">
          <div class="notif-pref-info">
            <span class="notif-pref-icon">💾</span>
            <div>
              <strong>Hiển thị danh sách đã lưu</strong>
              <span class="sf-hint">Cho người khác xem địa điểm bạn đã lưu.</span>
            </div>
          </div>
          <input type="checkbox" class="toggle" :checked="privacy.show_saved" @change="setPrivacy('show_saved', !privacy.show_saved)" />
        </label>
      </div>
    </div>

    <!-- Tab: Người chặn -->
    <div v-if="activeTab === 'chan'" id="panel-chan" class="settings-card card sediment-head" role="tabpanel" aria-labelledby="tab-chan">
      <h2>Người bị chặn</h2>
      <div v-if="blockedLoading" class="sf-hint">Đang tải...</div>
      <div v-else-if="blockedUsers.length" class="sessions-list">
        <div v-for="b in blockedUsers" :key="b.id" class="session-item">
          <div class="session-info">
            <NuxtLink :to="userPath(b.username || b.id)" class="session-ua">{{ b.display_name || 'Người dùng' }}</NuxtLink>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" :disabled="securityBusy" @click="withBusy(() => unblockUser(b.id, b.display_name))">Bỏ chặn</button>
        </div>
      </div>
      <p v-else class="sf-hint">Bạn chưa chặn ai.</p>
    </div>

    <!-- Tab: Người tắt tiếng -->
    <div v-if="activeTab === 'tat-tieng'" id="panel-tat-tieng" class="settings-card card sediment-head" role="tabpanel" aria-labelledby="tab-tat-tieng">
      <h2>Người bị tắt tiếng</h2>
      <p class="sf-hint sf-hint-spaced">Bài viết và bình luận của người bị tắt tiếng sẽ ẩn khỏi bảng tin của bạn, nhưng họ vẫn có thể xem nội dung của bạn.</p>
      <div v-if="mutedLoading" class="sf-loading" role="status"><div class="spinner spinner-sm"></div> Đang tải...</div>
      <div v-else-if="mutedUsers.length" class="sessions-list">
        <div v-for="m in mutedUsers" :key="m.id" class="session-item">
          <div class="session-info">
            <NuxtLink :to="userPath(m.username || m.id)" class="session-ua">{{ m.display_name || 'Người dùng' }}</NuxtLink>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" :disabled="securityBusy" @click="withBusy(() => unmuteUser(m.id, m.display_name))">Bỏ tắt tiếng</button>
        </div>
      </div>
      <p v-else class="sf-hint">Bạn chưa tắt tiếng ai.</p>
    </div>

    <!-- Tab: Dữ liệu & pháp lý -->
    <div v-if="activeTab === 'du-lieu'" id="panel-du-lieu" class="settings-card card sediment-head" role="tabpanel" aria-labelledby="tab-du-lieu">
      <h2>Dữ liệu & pháp lý</h2>

      <div class="dl-section">
        <h3>Xuất dữ liệu</h3>
        <p class="sf-hint">Tải toàn bộ dữ liệu tài khoản (hồ sơ, bài viết, bình luận, lưu, theo dõi) dưới dạng JSON.</p>
        <button type="button" class="btn btn-secondary" :disabled="exportLoading" @click="exportData">
          {{ exportLoading ? 'Đang tạo...' : '📥 Tải dữ liệu' }}
        </button>
      </div>

      <div class="dl-section">
        <h3>Lịch sử đồng ý</h3>
        <p class="sf-hint">Các sự kiện đồng ý điều khoản và chính sách bảo mật.</p>
        <div v-if="consentHistory.length" class="dl-consent-list">
          <div v-for="(c, i) in consentHistory" :key="i" class="dl-consent-item">
            <span class="dl-consent-ver">v{{ c.consent_version || '1.0' }}</span>
            <span class="dl-consent-time">{{ new Date(c.consent_at).toLocaleDateString('vi-VN', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span>
          </div>
        </div>
        <p v-else-if="consentLoaded" class="sf-hint">Chưa có dữ liệu đồng ý.</p>
        <button v-if="!consentLoaded" type="button" class="btn btn-ghost btn-sm" @click="loadConsent">Xem lịch sử</button>
      </div>
    </div>

    <!-- Tab: Nguy hiểm -->
    <div v-if="activeTab === 'nguy-hiem'" id="panel-nguy-hiem" class="settings-card card settings-danger sediment-head" role="tabpanel" aria-labelledby="tab-nguy-hiem">
      <h2>Vùng nguy hiểm</h2>
      <div class="danger-actions">
        <div class="danger-item">
          <div>
            <strong>Vô hiệu hóa tài khoản</strong>
            <p class="sf-hint">Tạm khóa — đăng nhập lại bằng OTP để kích hoạt.</p>
          </div>
          <button type="button" class="btn btn-ghost btn-danger-text" @click="deactivate">Vô hiệu hóa</button>
        </div>
        <div class="danger-item">
          <div>
            <strong>Xóa tài khoản</strong>
            <p class="sf-hint">Xóa vĩnh viễn tài khoản và toàn bộ dữ liệu.</p>
          </div>
          <button type="button" class="btn btn-ghost btn-danger-text" @click="deleteAccount">Xóa tài khoản</button>
        </div>
      </div>
    </div>
    </template>
  </section>
</template>

<script setup lang="ts">
const { user, isLoggedIn, authHeaders, fetchMe, handleSessionExpired } = useAuth()
const { openAuth } = useAuthModal()
const { show: showToast } = useToast()
const colorModeState = useColorMode()
const colorMode = computed(() => colorModeState.preference)
watch(isLoggedIn, (v) => { if (!v) navigateTo('/') })
function setColorMode(mode: 'light' | 'dark' | 'system') {
  colorModeState.preference = mode
}
useHead({
  title: 'Cài đặt',
  meta: [{ name: 'robots', content: 'noindex,nofollow' }],
  link: [{ rel: 'canonical', href: canonicalUrl('/cai-dat') }],
})

const TABS = [
  { key: 'ho-so', label: 'Hồ sơ', icon: '\u{1F464}' },
  { key: 'bao-mat', label: 'Bảo mật', icon: '\u{1F512}' },
  { key: 'thong-bao', label: 'Thông báo', icon: '🔔' },
  { key: 'giao-dien', label: 'Giao diện', icon: '🎨' },
  { key: 'rieng-tu', label: 'Riêng tư', icon: '🔒' },
  { key: 'chan', label: 'Chặn', icon: '\u{1F6AB}' },
  { key: 'tat-tieng', label: 'Tắt tiếng', icon: '\u{1F507}' },
  { key: 'du-lieu', label: 'Dữ liệu', icon: '📋' },
  { key: 'nguy-hiem', label: 'Nguy hiểm', icon: '⚠️' },
] as const
type TabKey = typeof TABS[number]['key']

const validKeys = new Set(TABS.map(t => t.key))
const activeTab = ref<TabKey>('ho-so')

const tabLoaded = reactive(new Set<TabKey>())
async function setTab(key: TabKey): Promise<boolean> {
  if (activeTab.value === key) return true
  if (activeTab.value === 'ho-so' && isDirty.value) {
    const ok = await confirm('Bạn có thay đổi hồ sơ chưa lưu. Rời tab bây giờ sẽ giữ dữ liệu trên màn hình nhưng chưa cập nhật lên hệ thống.', {
      title: 'Rời tab Hồ sơ?',
      confirmText: 'Rời tab',
    })
    if (!ok) return false
  }
  activeTab.value = key
  if (import.meta.client) window.history.replaceState(null, '', `#${key}`)
  lazyLoadTab(key)
  return true
}
async function onTabKeydown(e: KeyboardEvent) {
  const keys = ['ArrowRight', 'ArrowLeft', 'Home', 'End']
  if (!keys.includes(e.key)) return
  e.preventDefault()
  const current = TABS.findIndex(t => t.key === activeTab.value)
  const nextIndex = e.key === 'Home'
    ? 0
    : e.key === 'End'
      ? TABS.length - 1
      : e.key === 'ArrowRight'
        ? (current + 1) % TABS.length
        : (current - 1 + TABS.length) % TABS.length
  const nextKey = TABS[nextIndex]!.key
  const changed = await setTab(nextKey)
  if (changed) nextTick(() => document.getElementById(`tab-${nextKey}`)?.focus())
}
function lazyLoadTab(key: TabKey) {
  if (tabLoaded.has(key)) return
  tabLoaded.add(key)
  if (key === 'bao-mat') { loadSessions(); loadLoginHistory(); load2FAStatus(); loadTrustedDevices() }
  else if (key === 'rieng-tu') loadPrivacy()
  else if (key === 'chan') loadBlocked()
  else if (key === 'tat-tieng') loadMutedUsers()
  else if (key === 'thong-bao') loadNotifPrefs()
}

const displayName = ref(user.value?.display_name || '')
const fullName = ref(user.value?.full_name || '')
const bio = ref('')
const email = ref(user.value?.email || '')
const contactInfo = ref(user.value?.contact_info || '')
const savedName = ref(displayName.value)
const savedFullName = ref(fullName.value)
const savedBio = ref('')
const savedEmail = ref(email.value)
const savedContactInfo = ref(contactInfo.value)
const saving = ref(false)
// Guard security-tab action buttons against double-submit while an async op runs.
const securityBusy = ref(false)
async function withBusy(fn: () => unknown) { if (securityBusy.value) return; securityBusy.value = true; try { await fn() } finally { securityBusy.value = false } }
const nameError = ref('')

const uploadingAvatar = ref(false)
const avatarPreview = ref('')
const avatarBroken = ref(false)

const ALLOWED_IMG = ['image/jpeg', 'image/png', 'image/webp']
const MAX_IMG_SIZE = 12 * 1024 * 1024

async function onAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!ALLOWED_IMG.includes(file.type)) { showToast('Chỉ hỗ trợ JPEG, PNG hoặc WebP', 'error'); return }
  if (file.size > MAX_IMG_SIZE) { showToast('Ảnh quá lớn (tối đa 12MB)', 'error'); return }
  if (avatarPreview.value?.startsWith('blob:')) URL.revokeObjectURL(avatarPreview.value)
  avatarPreview.value = URL.createObjectURL(file)
  avatarBroken.value = false
  uploadingAvatar.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await $fetch<{ avatar_url: string }>('/auth/avatar', {
      method: 'POST',
      headers: authHeaders(),
      body: form,
    })
    if (res.avatar_url) {
      await fetchMe()
      showToast('Đã cập nhật ảnh đại diện', 'success')
    }
  } catch (err: unknown) {
    avatarPreview.value = ''
    if (getStatusCode(err) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(err, 'Không thể tải ảnh lên'), 'error')
  } finally {
    uploadingAvatar.value = false
  }
}

// Prefill bio from the public profile (User type doesn't carry bio).
onMounted(async () => {
  const hash = window.location.hash.slice(1) as TabKey
  if (hash && validKeys.has(hash)) {
    activeTab.value = hash
  }
  lazyLoadTab(activeTab.value)
  if (!user.value) return
  // Pre-fetch notif prefs + privacy so the overview cards can show a summary
  // immediately instead of only once those tabs are clicked.
  lazyLoadTab('thong-bao')
  lazyLoadTab('rieng-tu')
  try {
    const res = await $fetch<Record<string, any>>(`/api/users/${user.value.id}`, { headers: authHeaders() })
    const u = res?.user ?? res
    if (u?.bio) { bio.value = u.bio; savedBio.value = u.bio }
    if (!displayName.value && u?.display_name) { displayName.value = u.display_name; savedName.value = u.display_name }
    if (u?.full_name) { fullName.value = u.full_name; savedFullName.value = u.full_name }
    if (u?.email) { email.value = u.email; savedEmail.value = u.email }
    if (u?.contact_info) { contactInfo.value = u.contact_info; savedContactInfo.value = u.contact_info }
  } catch { /* prefill is best-effort */ }
})

const currentPw = ref('')
const newPw = ref('')
const confirmPw = ref('')
const savingPw = ref(false)

const COMMON_PASSWORDS = new Set([
  '123456', 'password', '12345678', 'qwerty', 'abc123', 'monkey', 'master',
  '111111', '123123', 'letmein', 'dragon', 'baseball', 'iloveyou', 'trustno1',
  'sunshine', 'princess', 'football', 'shadow', 'superman', 'michael',
])

const pwStrength = computed(() => {
  const pw = newPw.value
  if (!pw) return { score: 0, label: '', color: '' }
  if (COMMON_PASSWORDS.has(pw.toLowerCase())) return { score: 1, label: 'Rất yếu', color: 'var(--error)' }
  let score = 0
  if (pw.length >= 8) score++
  if (pw.length >= 12) score++
  if (pw.length >= 16) score++
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++
  if (/\d/.test(pw)) score++
  if (/[^a-zA-Z0-9]/.test(pw)) score++
  const level = score <= 2 ? 1 : score <= 3 ? 2 : score <= 4 ? 3 : 4
  const labels = ['', 'Yếu', 'Trung bình', 'Mạnh', 'Rất mạnh']
  const colors = ['', 'var(--error)', 'var(--warning)', 'var(--success)', 'var(--primary)']
  return { score: level, label: labels[level], color: colors[level] }
})
const hasPassword = computed(() => user.value?.has_password === true)
const hasPasswordKnown = computed(() => typeof user.value?.has_password === 'boolean')
const settingsProfileCompletion = computed(() => {
  const checks = [
    Boolean(displayName.value || fullName.value),
    Boolean(user.value?.avatar_url),
    Boolean(user.value?.cover_url),
    Boolean(bio.value.trim()),
    Boolean(email.value.trim() || contactInfo.value.trim()),
  ]
  return Math.round((checks.filter(Boolean).length / checks.length) * 100)
})

async function savePassword() {
  if (hasPassword.value && !currentPw.value) {
    showToast('Vui lòng nhập mật khẩu hiện tại', 'error')
    return
  }
  if (!newPw.value || newPw.value.length < 6) {
    showToast('Mật khẩu mới phải từ 6 ký tự trở lên', 'error')
    return
  }
  if (newPw.value !== confirmPw.value) {
    showToast('Mật khẩu xác nhận không khớp', 'error')
    return
  }
  savingPw.value = true
  try {
    const body: Record<string, string> = { password: newPw.value }
    if (currentPw.value) body.current_password = currentPw.value
    await $fetch('/auth/set-password', { method: 'POST', headers: authHeaders(), body })
    showToast('Đã cập nhật mật khẩu', 'success')
    currentPw.value = ''
    newPw.value = ''
    confirmPw.value = ''
    await fetchMe()
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(e, 'Không thể đổi mật khẩu'), 'error')
  } finally { savingPw.value = false }
}

const sessions = ref<any[]>([])
const sessionsLoading = ref(true)
const hiddenSystemSessions = ref(0)

async function loadSessions() {
  sessionsLoading.value = true
  try {
    const res = await $fetch<{ sessions: any[]; hidden_internal_count?: number }>('/auth/sessions', { headers: authHeaders() })
    const visible = []
    let hidden = Number(res.hidden_internal_count || 0)
    for (const session of res.sessions || []) {
      if (!session.is_current && isInternalUA(session.user_agent)) hidden += 1
      else visible.push(session)
    }
    sessions.value = visible
    hiddenSystemSessions.value = hidden
  } catch { /* ignore */ }
  sessionsLoading.value = false
}

function isInternalUA(ua: string): boolean {
  return /(python|urllib|httpx|aiohttp|curl|wget|healthcheck|uptime|node|undici|node-fetch)/i.test(ua || '')
}

function shortUA(ua: string): string {
  if (!ua) return 'Không rõ'
  if (isInternalUA(ua)) return 'Phiên hệ thống'
  if (ua.includes('Mobile')) return 'Di động'
  if (ua.includes('Windows')) return 'Windows'
  if (ua.includes('Mac')) return 'macOS'
  if (ua.includes('Linux')) return 'Linux'
  return ua.slice(0, 30)
}

const sessionsSummary = computed(() => {
  if (!tabLoaded.has('bao-mat')) return 'Chưa kiểm tra'
  if (sessionsLoading.value) return 'Đang kiểm tra'
  const suffix = hiddenSystemSessions.value ? ` · ẩn ${hiddenSystemSessions.value} phiên hệ thống` : ''
  return `${sessions.value.length} phiên${suffix}`
})

async function revokeSession(id: string) {
  try {
    await $fetch(`/auth/sessions/${id}`, { method: 'DELETE', headers: authHeaders() })
    sessions.value = sessions.value.filter(s => s.id !== id)
    showToast('Đã thu hồi phiên', 'success')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể thu hồi phiên', 'error')
  }
}

const uploadingCover = ref(false)
const coverPreview = ref('')

async function onCoverChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!ALLOWED_IMG.includes(file.type)) { showToast('Chỉ hỗ trợ JPEG, PNG hoặc WebP', 'error'); return }
  if (file.size > MAX_IMG_SIZE) { showToast('Ảnh quá lớn (tối đa 12MB)', 'error'); return }
  if (coverPreview.value?.startsWith('blob:')) URL.revokeObjectURL(coverPreview.value)
  coverPreview.value = URL.createObjectURL(file)
  uploadingCover.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await $fetch<{ cover_url: string }>('/auth/cover', {
      method: 'POST',
      headers: authHeaders(),
      body: form,
    })
    if (res.cover_url) {
      await fetchMe()
      showToast('Đã cập nhật ảnh bìa', 'success')
    }
  } catch (err: unknown) {
    coverPreview.value = ''
    if (getStatusCode(err) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(err, 'Không thể tải ảnh bìa lên'), 'error')
  } finally {
    uploadingCover.value = false
  }
}

const loginHistory = ref<any[]>([])
const loginHistoryLoading = ref(true)

async function loadLoginHistory() {
  loginHistoryLoading.value = true
  try {
    const res = await $fetch<{ history: any[] }>('/auth/login-history', { headers: authHeaders() })
    loginHistory.value = res.history || []
  } catch { /* ignore */ }
  loginHistoryLoading.value = false
}

// ── 2FA ──
const twoFA = ref<{ enabled: boolean; recovery_remaining: number }>({ enabled: false, recovery_remaining: 0 })
const twoFALoading = ref(true)
const setupData = ref<{ secret: string; otpauth_uri: string; qr: string } | null>(null)
const setupCode = ref('')
const recoveryCodes = ref<string[]>([])
const disableCode = ref('')
const trustedDevices = ref<any[]>([])

async function load2FAStatus() {
  twoFALoading.value = true
  try {
    twoFA.value = await $fetch('/auth/2fa/status', { headers: authHeaders() })
  } catch { /* ignore */ }
  twoFALoading.value = false
}
async function begin2FASetup() {
  try { setupData.value = await $fetch('/auth/2fa/setup', { method: 'POST', headers: authHeaders() }) }
  catch (e: unknown) { if (getStatusCode(e) === 401) { handleSessionExpired(); return } showToast(extractErrorMessage(e, 'Không thể bắt đầu thiết lập'), 'error') }
}
async function confirm2FASetup() {
  try {
    const res = await $fetch<{ recovery_codes: string[] }>('/auth/2fa/verify-setup', { method: 'POST', headers: authHeaders(), body: { code: setupCode.value } })
    recoveryCodes.value = res.recovery_codes || []
    setupData.value = null
    setupCode.value = ''
    showToast('Đã bật xác thực 2 bước', 'success')
    await load2FAStatus()
  } catch (e: unknown) { if (getStatusCode(e) === 401) { handleSessionExpired(); return } showToast(extractErrorMessage(e, 'Mã không đúng'), 'error') }
}
async function disable2FA() {
  try {
    await $fetch('/auth/2fa/disable', { method: 'POST', headers: authHeaders(), body: { code: disableCode.value } })
    disableCode.value = ''
    recoveryCodes.value = []
    showToast('Đã tắt xác thực 2 bước', 'success')
    await load2FAStatus()
    await loadTrustedDevices()
  } catch (e: unknown) { if (getStatusCode(e) === 401) { handleSessionExpired(); return } showToast(extractErrorMessage(e, 'Mã không đúng'), 'error') }
}
async function loadTrustedDevices() {
  try {
    const r = await $fetch<{ devices: any[] }>('/auth/trusted-devices', { headers: authHeaders() })
    trustedDevices.value = r.devices || []
  } catch { /* ignore */ }
}
async function removeTrustedDevice(id: string) {
  try {
    await $fetch(`/auth/trusted-devices/${encodeURIComponent(id)}`, { method: 'DELETE', headers: authHeaders() })
    trustedDevices.value = trustedDevices.value.filter(d => d.id !== id)
    showToast('Đã xoá thiết bị', 'success')
  } catch (e: unknown) { if (getStatusCode(e) === 401) { handleSessionExpired(); return } showToast('Không thể xoá thiết bị', 'error') }
}
function copyRecoveryCodes() {
  navigator.clipboard.writeText(recoveryCodes.value.join('\n')).then(() => showToast('Đã sao chép mã khôi phục', 'success')).catch(() => showToast('Không thể sao chép', 'error'))
}
function downloadRecoveryCodes() {
  const blob = new Blob([recoveryCodes.value.join('\n')], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'vinhlong360-recovery-codes.txt'
  a.click()
  URL.revokeObjectURL(url)
}

const privacy = ref({ profile_visibility: 'public', show_activity: true, show_saved: true })
const privacyLoading = ref(true)

async function loadPrivacy() {
  privacyLoading.value = true
  try {
    const res = await $fetch<Record<string, any>>('/auth/privacy', { headers: authHeaders() })
    privacy.value = { profile_visibility: res.profile_visibility || 'public', show_activity: res.show_activity !== false, show_saved: res.show_saved !== false }
  } catch { /* ignore */ }
  privacyLoading.value = false
}

const privacySummary = computed(() => {
  if (!tabLoaded.has('rieng-tu')) return 'Chưa kiểm tra'
  const labels: Record<string, string> = { public: 'Công khai', followers: 'Người theo dõi', private: 'Riêng tư' }
  return labels[privacy.value.profile_visibility] || 'Công khai'
})

async function setPrivacy(key: string, value: any) {
  const prev = { ...privacy.value }
  ;(privacy.value as any)[key] = value
  try {
    await $fetch('/auth/privacy', { method: 'PUT', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: { [key]: value } })
    showToast('Đã cập nhật quyền riêng tư', 'success')
  } catch (e: unknown) {
    privacy.value = prev
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể cập nhật', 'error')
  }
}

const blockedUsers = ref<any[]>([])
const blockedLoading = ref(true)

async function loadBlocked() {
  blockedLoading.value = true
  try {
    const res = await $fetch<{ blocked: any[] }>('/api/blocked-users', { headers: authHeaders() })
    blockedUsers.value = res.blocked || []
  } catch { /* ignore */ }
  blockedLoading.value = false
}

async function unblockUser(id: string, name: string) {
  try {
    await $fetch(`/api/notifications/block/${id}`, { method: 'POST', headers: authHeaders() })
    blockedUsers.value = blockedUsers.value.filter(u => u.id !== id)
    showToast(`${name || 'Người dùng'} đã được bỏ chặn`, 'success')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể bỏ chặn', 'error')
  }
}

const mutedUsers = ref<any[]>([])
const mutedLoading = ref(true)

async function loadMutedUsers() {
  mutedLoading.value = true
  try {
    const res = await $fetch<{ muted: any[] }>('/api/muted-users', { headers: authHeaders() })
    mutedUsers.value = res.muted || []
  } catch { /* ignore */ }
  mutedLoading.value = false
}

async function unmuteUser(id: string, name: string) {
  try {
    await $fetch(`/api/mute/${encodeURIComponent(id)}`, { method: 'POST', headers: authHeaders() })
    mutedUsers.value = mutedUsers.value.filter(u => u.id !== id)
    showToast(`Đã bỏ tắt tiếng ${name || 'người dùng'}`, 'success')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể bỏ tắt tiếng', 'error')
  }
}

const NOTIF_TYPES = [
  { key: 'like', pref: 'pref_like', icon: '❤️', label: 'Lượt thích', desc: 'Khi ai đó thích bài viết của bạn' },
  { key: 'comment', pref: 'pref_comment', icon: '💬', label: 'Bình luận', desc: 'Khi ai đó bình luận bài viết của bạn' },
  { key: 'follow', pref: 'pref_follow', icon: '👤', label: 'Theo dõi', desc: 'Khi ai đó theo dõi bạn' },
  { key: 'mention', pref: 'pref_mention', icon: '📣', label: 'Nhắc đến', desc: 'Khi ai đó nhắc đến bạn' },
  { key: 'system', pref: 'pref_system', icon: '🔔', label: 'Hệ thống', desc: 'Thông báo từ hệ thống và quản trị' },
] as const

const notifPrefs = ref<Record<string, boolean>>({ pref_like: true, pref_comment: true, pref_follow: true, pref_mention: true, pref_system: true })
const notifPrefsLoading = ref(true)

async function loadNotifPrefs() {
  notifPrefsLoading.value = true
  try {
    const res = await $fetch<Record<string, boolean>>('/api/notification-preferences', { headers: authHeaders() })
    Object.assign(notifPrefs.value, res)
  } catch { /* defaults stay */ }
  notifPrefsLoading.value = false
}

const notifSummary = computed(() => {
  if (!tabLoaded.has('thong-bao')) return 'Chưa kiểm tra'
  const on = Object.values(notifPrefs.value).filter(v => v === true).length
  const total = Object.keys(notifPrefs.value).length || 5
  return `${on}/${total} loại bật`
})

async function toggleNotifPref(prefKey: string) {
  const prev = notifPrefs.value[prefKey] ?? false
  notifPrefs.value[prefKey] = !prev
  try {
    await $fetch('/api/notification-preferences', { method: 'PUT', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: { [prefKey]: !prev } })
    showToast('Đã lưu tùy chọn thông báo', 'success')
  } catch (e: unknown) {
    notifPrefs.value[prefKey] = prev
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể cập nhật tùy chọn', 'error')
  }
}

const { confirmDialog: confirm } = useConfirm()

// ── Data & legal ──
const exportLoading = ref(false)
const consentHistory = ref<any[]>([])
const consentLoaded = ref(false)

async function exportData() {
  exportLoading.value = true
  try {
    const data = await $fetch<Record<string, any>>('/auth/export-data', { headers: authHeaders() })
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vinhlong360-data-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
    showToast('Đã tải dữ liệu', 'success')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(e, 'Không thể xuất dữ liệu'), 'error')
  } finally {
    exportLoading.value = false
  }
}

async function loadConsent() {
  try {
    const data = await $fetch<{ history: any[] }>('/auth/consent-history', { headers: authHeaders() })
    consentHistory.value = data.history || []
    consentLoaded.value = true
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(e, 'Không thể tải lịch sử'), 'error')
    consentLoaded.value = true
  }
}

async function deactivate() {
  const ok = await confirm('Tài khoản sẽ bị khóa tạm thời. Đăng nhập lại bằng OTP để kích hoạt.', { title: 'Vô hiệu hóa tài khoản?', confirmText: 'Vô hiệu hóa', danger: true })
  if (!ok) return
  try {
    await $fetch('/auth/deactivate', { method: 'POST', headers: authHeaders() })
    await fetchMe()
    showToast('Tài khoản đã bị vô hiệu hóa', 'success')
    navigateTo('/')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(e, 'Lỗi'), 'error')
  }
}

async function deleteAccount() {
  const ok = await confirm('Toàn bộ dữ liệu sẽ bị xóa và không thể khôi phục.', { title: 'Xóa tài khoản vĩnh viễn?', confirmText: 'Xóa tài khoản', danger: true })
  if (!ok) return
  try {
    await $fetch('/auth/account', { method: 'DELETE', headers: authHeaders() })
    await fetchMe()
    showToast('Đã xóa tài khoản', 'success')
    navigateTo('/')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(e, 'Lỗi'), 'error')
  }
}

const { timeAgo } = useTimeAgo()

async function save() {
  nameError.value = ''
  const name = displayName.value.trim()
  if (name.length < 2) {
    nameError.value = 'Tên hiển thị phải từ 2 ký tự trở lên'
    return
  }
  saving.value = true
  try {
    const body: Record<string, any> = {
      display_name: name,
      full_name: fullName.value.trim() || null,
      bio: bio.value.trim(),
      email: email.value.trim() || null,
      contact_info: contactInfo.value.trim() || null,
    }
    await $fetch('/auth/profile', {
      method: 'PUT',
      headers: authHeaders(),
      body,
    })
    await fetchMe()
    savedName.value = displayName.value
    savedFullName.value = fullName.value
    savedBio.value = bio.value
    savedEmail.value = email.value
    savedContactInfo.value = contactInfo.value
    showToast('Đã lưu hồ sơ', 'success')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast(extractErrorMessage(e, 'Không thể lưu hồ sơ'), 'error')
  } finally {
    saving.value = false
  }
}

const isDirty = computed(() => displayName.value !== savedName.value || bio.value !== savedBio.value || fullName.value !== savedFullName.value || email.value !== savedEmail.value || contactInfo.value !== savedContactInfo.value)
function onBeforeUnload(e: BeforeUnloadEvent) {
  if (isDirty.value) e.preventDefault()
}
function onPopState() {
  const hash = window.location.hash.slice(1) as TabKey
  if (hash && TABS.some(t => t.key === hash)) {
    activeTab.value = hash
    lazyLoadTab(hash)
  }
}
function syncHashTabSoon() {
  onPopState()
  nextTick(onPopState)
  window.setTimeout(onPopState, 250)
}
onMounted(() => {
  if (import.meta.client) {
    window.addEventListener('beforeunload', onBeforeUnload)
    window.addEventListener('popstate', onPopState)
    window.addEventListener('hashchange', onPopState)
    syncHashTabSoon()
  }
})
onUnmounted(() => {
  if (import.meta.client) {
    window.removeEventListener('beforeunload', onBeforeUnload)
    window.removeEventListener('popstate', onPopState)
    window.removeEventListener('hashchange', onPopState)
  }
  if (avatarPreview.value?.startsWith('blob:')) URL.revokeObjectURL(avatarPreview.value)
  if (coverPreview.value?.startsWith('blob:')) URL.revokeObjectURL(coverPreview.value)
})
</script>

<style scoped>
.settings-page { max-width: 920px; margin: 0 auto; }

/* Local page masthead eyebrow — small-caps dateline + hairline tick, matches
   the site's area/ward eyebrow pattern but scoped here (not promoted global). */
.dateline-eyebrow {
  display: flex; align-items: center; gap: .4rem; margin: 0 0 .35rem;
  font-family: var(--font-sans); font-size: .78rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .06em; color: var(--ink-700);
}
.dateline-eyebrow::before { content: ""; width: 14px; height: 1.5px; background: var(--primary); flex-shrink: 0; }

.settings-title { font-family: var(--font-editorial); font-weight: 600; font-size: 1.6rem; margin: 0 0 .4rem; }
.settings-dek { color: var(--ink-700); font-size: .92rem; max-width: 56ch; margin: 0 0 var(--space-5); line-height: var(--leading-relaxed); }
.settings-overview {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--space-3); margin-bottom: var(--space-5);
}
.settings-overview-item {
  min-height: 112px; padding: 1rem; border: 1px solid var(--line);
  border-radius: var(--radius-lg); background: var(--card);
  display: flex; flex-direction: column; gap: .45rem;
}
.so-label { color: var(--ink-700); font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.settings-overview-item strong { font-size: 1rem; line-height: 1.25; }
.so-link { margin-top: auto; color: var(--accent); font-weight: 700; font-size: .82rem; text-decoration: none; }
.so-bar { height: 7px; border-radius: var(--radius-full); background: var(--bg-alt); overflow: hidden; }
.so-bar span { display: block; height: 100%; border-radius: inherit; background: var(--accent); transition: width .3s var(--ease-out); }
.settings-hash-anchors { position: relative; height: 0; overflow: hidden; }
.settings-hash-anchors span { position: absolute; top: -96px; width: 1px; height: 1px; }
.settings-card, .settings-guest { padding: 1.5rem; }
.settings-guest h1 { margin: 0 0 1.25rem; font-family: var(--font-editorial); font-weight: 600; font-size: 1.5rem; }
.settings-guest p { color: var(--ink-700); margin-bottom: 1rem; }

/* ── Tabs ── */
.settings-tabs {
  display: flex; gap: var(--space-2); margin-bottom: var(--space-5);
  border-bottom: 1px solid var(--line); padding-bottom: 0;
  overflow-x: auto; -webkit-overflow-scrolling: touch;
}
.settings-tab {
  display: inline-flex; align-items: center; gap: 6px;
  padding: .6rem 1rem; border: none; background: none;
  font-size: .88rem; font-weight: 500; color: var(--muted);
  cursor: pointer; white-space: nowrap; position: relative;
  border-bottom: 2px solid transparent; margin-bottom: -1px;
  transition: color .2s, border-color .2s;
}
.settings-tab:hover { color: var(--ink); }
.settings-tab.active { color: var(--accent, var(--primary)); border-bottom-color: var(--accent, var(--primary)); font-weight: 600; }
.settings-tab.active .settings-tab-icon { transform: scale(1.15); }
.settings-tab:focus-visible { outline: 2px solid var(--accent, var(--primary)); outline-offset: -2px; border-radius: 4px; }
.settings-tab-icon { font-size: 1rem; transition: transform .25s var(--ease-spring-gentle, cubic-bezier(.2,1,.4,1)); }
.settings-form { display: flex; flex-direction: column; gap: 1.25rem; }
.sf-field { display: flex; flex-direction: column; gap: .4rem; }
.sf-label { font-weight: 600; font-size: .95rem; }
.sf-hint { font-weight: 400; color: var(--ink-700); font-size: .85rem; }
.sf-input {
  width: 100%; padding: .65rem .8rem; border: 1px solid var(--border-input);
  border-radius: var(--radius-md); background: var(--bg); color: var(--ink-900);
  font: inherit; transition: border-color .25s var(--ease-out), box-shadow .25s var(--ease-out), background .25s var(--ease-out);
}
.sf-input:hover:not(:focus) { border-color: var(--ink-700); }
.sf-input:focus-visible { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(var(--accent-rgb, 33,150,83), .15); background: var(--card); }
.sf-textarea { resize: vertical; min-height: 90px; }
.sf-error { color: var(--danger); font-size: .85rem; }
.pw-strength { display: flex; align-items: center; gap: var(--space-2); margin-top: var(--space-1); }
.pw-bar { display: flex; gap: 3px; flex: 1; max-width: 160px; }
.pw-segment { height: 4px; flex: 1; border-radius: 2px; background: var(--line); transition: background .2s; }
.pw-label { font-size: .75rem; font-weight: 500; min-width: 80px; }
.sf-success { color: var(--accent); font-size: .85rem; }
.sf-loading { display: flex; align-items: center; gap: var(--space-2); color: var(--ink-700); font-size: .85rem; padding: var(--space-4) 0; }
.sf-hint-spaced { margin-bottom: var(--space-4); }
.sf-username-row { display: flex; align-items: center; gap: 0; border: 1px solid var(--border-input); border-radius: var(--radius-md); overflow: hidden; }
.sf-username-prefix { padding: .65rem .6rem; background: var(--bg-warm); color: var(--ink-700); font-size: .85rem; white-space: nowrap; border-right: 1px solid var(--border-input); flex-shrink: 0; }
.sf-username-input { border: none !important; border-radius: 0 !important; flex: 1; min-width: 0; }
.sf-readonly { opacity: .6; cursor: not-allowed; background: var(--bg-warm); }
.sf-readonly-group { margin-bottom: var(--space-1); }
.sf-actions { display: flex; gap: .75rem; align-items: center; }
.sf-avatar-section { display: flex; align-items: center; gap: 1rem; }
.sf-avatar-preview {
  width: 80px; height: 80px; border-radius: 50%; overflow: hidden; cursor: pointer;
  position: relative; flex-shrink: 0; border: 2px solid var(--border-input);
  padding: 0; background: none; font: inherit; text-align: left;
}
.sf-avatar-preview:hover .sf-avatar-overlay { opacity: 1; }
.sf-avatar-img { width: 100%; height: 100%; object-fit: cover; }
.sf-avatar-overlay {
  position: absolute; inset: 0; background: rgba(0,0,0,.45); color: var(--text-on-dark, #fff);
  display: flex; align-items: center; justify-content: center; font-size: 1.5rem;
  opacity: 0; transition: opacity .2s;
}
.sf-avatar-info { display: flex; flex-direction: column; gap: .25rem; }
.sf-avatar-info .sf-hint { font-size: .8rem; }
.btn-sm { padding: .3rem .7rem; font-size: .85rem; }
.settings-card h2 { margin: 0 0 1rem; font-size: 1.2rem; padding-bottom: var(--space-3); border-bottom: 1px solid var(--line); }
.settings-card + .settings-card { margin-top: 1.25rem; }
.sessions-list { display: flex; flex-direction: column; gap: .5rem; }
.session-item { display: flex; align-items: center; gap: .75rem; padding: .6rem .8rem; border: 1px solid var(--border-input); border-radius: var(--radius-md); }
.session-item.current { border-color: var(--accent); background: color-mix(in oklab, var(--accent) 5%, transparent); }
.session-info { flex: 1; display: flex; flex-direction: column; gap: .15rem; }
.session-ua { font-weight: 600; font-size: .9rem; }
.session-badge { font-size: .75rem; font-weight: 600; color: var(--accent); background: color-mix(in oklab, var(--accent) 12%, transparent); padding: .15rem .5rem; border-radius: var(--radius-full); }
.session-system-note { margin: .75rem 0 0; padding: .65rem .75rem; border-radius: var(--radius-md); background: var(--bg-alt); }
.recovery-list { list-style: none; padding: 0; display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-1); margin: var(--space-2) 0; }
.recovery-list code { font-size: var(--text-sm); letter-spacing: 0.05em; }
.rc-actions { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.qr-img { display: block; margin: var(--space-2) 0; border-radius: var(--radius-sm); background: #fff; padding: var(--space-2); }
.settings-danger { border-color: rgba(192,57,43,.2); border-left: 3px solid var(--error); }
.danger-actions { display: flex; flex-direction: column; gap: .75rem; }
.danger-item { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.danger-item p { margin: 0; }
.btn-danger-text { color: var(--danger) !important; }
.blocked-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: .5rem; }
.notif-prefs { display: flex; flex-direction: column; gap: .5rem; }
.notif-pref-item { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: .75rem .8rem; border: 1px solid var(--border-input); border-radius: var(--radius-md); cursor: pointer; transition: background .2s; }
.notif-pref-item:hover { background: var(--bg-warm); }
.notif-pref-info { display: flex; align-items: center; gap: .75rem; }
.notif-pref-icon { font-size: 1.25rem; flex-shrink: 0; }
.notif-pref-info strong { display: block; font-size: .9rem; }
.notif-pref-info .sf-hint { display: block; margin-top: .1rem; }
.toggle { appearance: none; width: 40px; height: 22px; background: var(--muted); border-radius: 11px; position: relative; cursor: pointer; transition: background .25s var(--ease-out, ease); flex-shrink: 0; min-height: 44px; padding: 11px 0; box-sizing: content-box; }
.toggle::after { content: ''; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; background: var(--white, #fff); border-radius: 50%; transition: transform .3s var(--ease-spring-gentle, cubic-bezier(.2,1,.4,1)); box-shadow: 0 1px 3px rgba(0,0,0,.15); }
.toggle:checked { background: var(--accent, var(--primary)); }
.toggle:checked::after { transform: translateX(18px); }
.toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.toggle:active::after { width: 22px; }

/* ── Cover photo ── */
.sf-cover-section { display: flex; align-items: flex-start; gap: 1rem; overflow: hidden; }
.sf-cover-preview {
  width: 200px; height: 68px; border-radius: var(--radius-md); overflow: hidden; cursor: pointer;
  position: relative; flex-shrink: 0; border: 2px solid var(--border-input);
  padding: 0; background: none; font: inherit; text-align: left;
}
.sf-cover-preview:hover .sf-avatar-overlay { opacity: 1; }
.sf-cover-img { width: 100%; height: 100%; object-fit: cover; }
.sf-cover-placeholder {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  background: var(--bg-warm); color: var(--ink-700); font-size: .85rem;
}
/* ── Data & legal ── */
.dl-section { margin-bottom: 1.25rem; }
.dl-section h3 { font-size: 1rem; margin: 0 0 .3rem; }
.dl-consent-list { display: flex; flex-direction: column; gap: .35rem; margin-top: .5rem; }
.dl-consent-item { display: flex; gap: .75rem; align-items: center; padding: .4rem .6rem; border: 1px solid var(--border-input); border-radius: var(--radius-md); }
.dl-consent-ver { font-weight: 600; font-size: .85rem; }
.dl-consent-time { font-size: .82rem; color: var(--ink-700); }

.login-fail { border-color: rgba(192,57,43,.3) !important; }
.login-ok { color: var(--accent); font-weight: 600; font-size: 1.1rem; }
.login-bad { color: var(--danger); font-weight: 600; font-size: 1.1rem; }

/* ── Theme toggle ── */
.theme-options { display: flex; gap: .5rem; flex-wrap: wrap; }
.theme-btn {
  display: flex; align-items: center; gap: .4rem; padding: .6rem 1rem;
  border: 2px solid var(--border-input); border-radius: var(--radius-md);
  background: var(--bg); color: var(--ink-700); cursor: pointer; font-size: .9rem;
  transition: border-color .2s, background .2s;
}
.theme-btn:hover { border-color: var(--ink-500); }
.theme-btn.active { border-color: var(--accent, var(--primary)); background: color-mix(in oklab, var(--accent, var(--primary)) 8%, transparent); color: var(--ink); font-weight: 600; }
.theme-icon { font-size: 1.1rem; }

/* ── Dark mode ── */
.dark .sf-input { background: var(--bg-alt); border-color: var(--line); color: var(--ink); }
.dark .session-item { border-color: var(--line); background: var(--bg-alt); }
.dark .session-item.current { border-color: var(--accent); background: color-mix(in oklab, var(--accent) 8%, var(--bg-alt)); }
.dark .settings-danger { border-color: rgba(192,57,43,.3); }
.dark .sf-avatar-preview { border-color: var(--line); }
.dark .sf-username-row { border-color: var(--line); }
.dark .sf-username-prefix { background: var(--bg-alt); border-color: var(--line); }
.dark .notif-pref-item { border-color: var(--line); }
.dark .notif-pref-item:hover { background: var(--bg-alt); }
.dark .sf-readonly { background: var(--bg); }
.dark .settings-overview-item { background: var(--bg-alt); border-color: var(--line); }
.dark .so-bar { background: var(--bg); }

/* ── Mobile ── */
@media (max-width: 600px) {
  .settings-page { padding: var(--space-4) var(--space-3); }
  .settings-overview { grid-template-columns: 1fr; }
  .settings-card, .settings-guest { padding: var(--space-4); }
  .sf-avatar-section { flex-direction: column; align-items: flex-start; }
  .danger-item { flex-direction: column; align-items: flex-start; gap: .5rem; }
  .settings-tabs { gap: 0; }
  .settings-tab { padding: .5rem .65rem; font-size: .8rem; }
  .sf-input { font-size: 16px; }
  .sf-username-prefix { font-size: .75rem; padding: .65rem .4rem; }
}
@media (prefers-reduced-motion: reduce) {
  .settings-tab, .settings-tab-icon, .sf-input, .toggle, .toggle::after,
  .notif-pref-item, .theme-btn { transition: none; }
}
</style>

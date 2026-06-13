/* ============================================================
   vinhlong360 — Frontend Authentication (OTP SMS)
   ============================================================ */

(function () {
  const API = window.location.origin;
  const TOKEN_KEY = "vl360_token";
  const USER_KEY = "vl360_user";

  let currentUser = null;

  // ── Init ──

  function init() {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (saved) {
      fetchMe().catch(() => logout());
    } else {
      renderAuthArea();
    }
  }

  // ── API helpers ──

  function authHeaders() {
    const token = localStorage.getItem(TOKEN_KEY);
    return token ? { Authorization: "Bearer " + token } : {};
  }

  async function fetchMe() {
    const res = await fetch(API + "/auth/me", { headers: authHeaders() });
    if (!res.ok) throw new Error("Not authenticated");
    const data = await res.json();
    currentUser = data.user;
    localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
    renderAuthArea();
    return currentUser;
  }

  async function requestOTP(phone) {
    const res = await fetch(API + "/auth/request-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone }),
    });
    return res.json();
  }

  async function verifyOTP(phone, code) {
    const res = await fetch(API + "/auth/verify-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone, code }),
    });
    return { ok: res.ok, data: await res.json() };
  }

  // ── UI: Auth area in topbar ──

  function renderAuthArea() {
    const area = document.getElementById("authArea");
    if (!area) return;

    if (currentUser) {
      const initials = (currentUser.display_name || "U").slice(0, 2).toUpperCase();
      area.innerHTML =
        '<div class="auth-user dropdown" id="userDropdown">' +
          '<div class="avatar">' + initials + "</div>" +
          '<span class="auth-user-name">' + escHtml(currentUser.display_name || "") + "</span>" +
          '<div class="dropdown-menu" id="userMenu">' +
            '<button class="dropdown-item" onclick="window._vl360Auth.editProfile()">Hồ sơ</button>' +
            '<div class="dropdown-divider"></div>' +
            '<button class="dropdown-item danger" onclick="window._vl360Auth.logout()">Đăng xuất</button>' +
          "</div>" +
        "</div>";
      var dd = document.getElementById("userDropdown");
      dd.addEventListener("click", function (e) {
        e.stopPropagation();
        document.getElementById("userMenu").classList.toggle("show");
      });
    } else {
      area.innerHTML =
        '<button class="auth-btn" onclick="showAuthModal()">Đăng nhập</button>';
    }
  }

  // ── UI: Auth modal ──

  window.showAuthModal = function () {
    var overlay = document.getElementById("authModal");
    overlay.classList.add("show");
    renderPhoneStep();
  };

  window.hideAuthModal = function () {
    document.getElementById("authModal").classList.remove("show");
  };

  function renderPhoneStep() {
    var body = document.getElementById("authModalBody");
    body.innerHTML =
      '<div class="otp-step">' +
        "<h3>Nhập số điện thoại</h3>" +
        "<p>Chúng tôi sẽ gửi mã OTP qua SMS để xác minh</p>" +
        '<div class="form-group">' +
          '<input class="input" id="authPhone" type="tel" placeholder="0912 345 678" autocomplete="tel" />' +
          '<p class="form-error" id="authPhoneErr" style="display:none"></p>' +
        "</div>" +
        '<button class="btn btn-primary" style="width:100%" id="authPhoneBtn" onclick="window._vl360Auth.submitPhone()">Gửi mã OTP</button>' +
      "</div>";
    document.getElementById("authPhone").focus();
    document.getElementById("authPhone").addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); window._vl360Auth.submitPhone(); }
    });
  }

  function renderOTPStep(phone, devCode) {
    var body = document.getElementById("authModalBody");
    var devHint = devCode ? '<p style="color:var(--accent-dark);font-size:.8rem">DEV: ' + devCode + "</p>" : "";
    body.innerHTML =
      '<div class="otp-step">' +
        "<h3>Nhập mã OTP</h3>" +
        '<p>Đã gửi mã đến <strong>' + maskPhone(phone) + "</strong></p>" +
        devHint +
        '<div class="otp-input" id="otpInputRow"></div>' +
        '<p class="form-error" id="authOTPErr" style="display:none"></p>' +
        '<div class="otp-timer">' +
          '<span id="otpTimerText">Gửi lại sau <span id="otpCountdown">60</span>s</span>' +
          '<button class="otp-resend" id="otpResendBtn" style="display:none" onclick="window._vl360Auth.resendOTP()">Gửi lại mã</button>' +
        "</div>" +
        '<button class="btn btn-primary" style="width:100%;margin-top:8px" id="authOTPBtn" onclick="window._vl360Auth.submitOTP()">Xác nhận</button>' +
      "</div>";

    var row = document.getElementById("otpInputRow");
    for (var i = 0; i < 6; i++) {
      var inp = document.createElement("input");
      inp.type = "text";
      inp.inputMode = "numeric";
      inp.maxLength = 1;
      inp.autocomplete = "one-time-code";
      inp.dataset.idx = i;
      row.appendChild(inp);
    }

    var inputs = row.querySelectorAll("input");
    inputs.forEach(function (inp, idx) {
      inp.addEventListener("input", function () {
        if (this.value && idx < 5) inputs[idx + 1].focus();
      });
      inp.addEventListener("keydown", function (e) {
        if (e.key === "Backspace" && !this.value && idx > 0) inputs[idx - 1].focus();
        if (e.key === "Enter") window._vl360Auth.submitOTP();
      });
      inp.addEventListener("paste", function (e) {
        var text = (e.clipboardData || window.clipboardData).getData("text").replace(/\D/g, "");
        if (text.length >= 6) {
          e.preventDefault();
          for (var j = 0; j < 6; j++) inputs[j].value = text[j] || "";
          inputs[5].focus();
        }
      });
    });
    inputs[0].focus();

    startCountdown(60);
  }

  // ── Countdown ──

  var countdownTimer = null;
  function startCountdown(sec) {
    clearInterval(countdownTimer);
    var el = document.getElementById("otpCountdown");
    var timerText = document.getElementById("otpTimerText");
    var resendBtn = document.getElementById("otpResendBtn");
    if (!el) return;
    var remaining = sec;
    el.textContent = remaining;
    countdownTimer = setInterval(function () {
      remaining--;
      el.textContent = remaining;
      if (remaining <= 0) {
        clearInterval(countdownTimer);
        if (timerText) timerText.style.display = "none";
        if (resendBtn) resendBtn.style.display = "inline";
      }
    }, 1000);
  }

  // ── Actions ──

  var _pendingPhone = "";

  window._vl360Auth = {
    submitPhone: async function () {
      var phone = document.getElementById("authPhone").value.trim().replace(/\s+/g, "");
      var err = document.getElementById("authPhoneErr");
      var btn = document.getElementById("authPhoneBtn");
      if (!/^(0|\+84)(3|5|7|8|9)\d{8}$/.test(phone)) {
        err.textContent = "Số điện thoại VN không hợp lệ";
        err.style.display = "block";
        return;
      }
      err.style.display = "none";
      btn.disabled = true;
      btn.textContent = "Đang gửi…";
      try {
        var res = await requestOTP(phone);
        if (res.success) {
          _pendingPhone = phone;
          renderOTPStep(phone, res.dev_code);
        } else {
          err.textContent = res.detail || res.message || "Lỗi gửi OTP";
          err.style.display = "block";
        }
      } catch (e) {
        err.textContent = "Lỗi kết nối. Thử lại sau.";
        err.style.display = "block";
      }
      btn.disabled = false;
      btn.textContent = "Gửi mã OTP";
    },

    submitOTP: async function () {
      var inputs = document.querySelectorAll("#otpInputRow input");
      var code = "";
      inputs.forEach(function (inp) { code += inp.value; });
      var err = document.getElementById("authOTPErr");
      var btn = document.getElementById("authOTPBtn");
      if (code.length < 6) {
        err.textContent = "Vui lòng nhập đủ 6 số";
        err.style.display = "block";
        return;
      }
      err.style.display = "none";
      btn.disabled = true;
      btn.textContent = "Đang xác minh…";
      try {
        var res = await verifyOTP(_pendingPhone, code);
        if (res.ok && res.data.success) {
          localStorage.setItem(TOKEN_KEY, res.data.token);
          currentUser = res.data.user;
          localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
          hideAuthModal();
          renderAuthArea();
          showToast("Đăng nhập thành công!", "success");
        } else {
          err.textContent = res.data.detail || "OTP không đúng";
          err.style.display = "block";
        }
      } catch (e) {
        err.textContent = "Lỗi kết nối";
        err.style.display = "block";
      }
      btn.disabled = false;
      btn.textContent = "Xác nhận";
    },

    resendOTP: async function () {
      var btn = document.getElementById("otpResendBtn");
      btn.disabled = true;
      try {
        var res = await requestOTP(_pendingPhone);
        if (res.dev_code) {
          showToast("DEV: Mã mới " + res.dev_code, "warning");
        } else {
          showToast("Đã gửi lại mã OTP", "success");
        }
        btn.style.display = "none";
        document.getElementById("otpTimerText").style.display = "";
        startCountdown(60);
      } catch (e) {
        showToast("Lỗi gửi lại OTP", "error");
      }
      btn.disabled = false;
    },

    logout: async function () {
      try {
        await fetch(API + "/auth/logout", { method: "POST", headers: authHeaders() });
      } catch (_) {}
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      currentUser = null;
      renderAuthArea();
      showToast("Đã đăng xuất", "success");
    },

    editProfile: function () {
      showToast("Tính năng hồ sơ sẽ có trong Phase 1", "warning");
    },

    getUser: function () { return currentUser; },
    getToken: function () { return localStorage.getItem(TOKEN_KEY); },
    authHeaders: authHeaders,
  };

  // ── Helpers ──

  function maskPhone(phone) {
    if (phone.length < 7) return phone;
    return phone.slice(0, 3) + "****" + phone.slice(-3);
  }

  function escHtml(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  // ── Toast ──

  window.showToast = function (msg, type) {
    var container = document.getElementById("toastContainer");
    if (!container) return;
    var t = document.createElement("div");
    t.className = "toast" + (type ? " " + type : "");
    t.textContent = msg;
    container.appendChild(t);
    setTimeout(function () { t.remove(); }, 3500);
  };

  // ── Close dropdown on outside click ──

  document.addEventListener("click", function () {
    var menu = document.getElementById("userMenu");
    if (menu) menu.classList.remove("show");
  });

  // ── Boot ──

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

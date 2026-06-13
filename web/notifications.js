/* ============================================================
   vinhlong360 — Notifications + Community Frontend
   Bell icon, dropdown, follow, report, block
   ============================================================ */

(function () {
  const API = window.location.origin;
  let notifications = [];
  let unreadCount = 0;
  let pollTimer = null;

  function authHeaders() {
    return window._vl360Auth ? window._vl360Auth.authHeaders() : {};
  }

  function getUser() {
    return window._vl360Auth ? window._vl360Auth.getUser() : null;
  }

  // ── Notifications API ──

  async function fetchNotifications() {
    if (!getUser()) return;
    try {
      const res = await fetch(API + "/api/notifications?limit=20", {
        headers: authHeaders(),
      });
      if (!res.ok) return;
      const data = await res.json();
      notifications = data.notifications || [];
      unreadCount = data.unread_count || 0;
      renderBell();
    } catch (e) { /* silent */ }
  }

  async function markAllRead() {
    if (!getUser()) return;
    try {
      await fetch(API + "/api/notifications/read-all", {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
      });
      unreadCount = 0;
      notifications.forEach(function (n) { n.is_read = true; });
      renderBell();
    } catch (e) { /* silent */ }
  }

  // ── Follow API ──

  async function toggleFollow(targetType, targetId) {
    if (!getUser()) { window.showAuthModal && window.showAuthModal(); return; }
    try {
      const res = await fetch(API + "/api/follow/" + targetType + "/" + targetId, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
      });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) { return null; }
  }

  async function getFollowerCount(targetType, targetId) {
    try {
      const res = await fetch(API + "/api/followers/count/" + targetType + "/" + targetId);
      if (!res.ok) return 0;
      const data = await res.json();
      return data.count || 0;
    } catch (e) { return 0; }
  }

  // ── Report API ──

  async function submitReport(targetType, targetId, reason) {
    if (!getUser()) { window.showAuthModal && window.showAuthModal(); return; }
    try {
      const res = await fetch(API + "/api/report", {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ target_type: targetType, target_id: targetId, reason: reason }),
      });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message || "Đã gửi báo cáo", "success");
      } else {
        showToast(data.detail || "Lỗi", "error");
      }
    } catch (e) {
      showToast("Lỗi kết nối", "error");
    }
  }

  // ── Block API ──

  async function toggleBlock(userId) {
    if (!getUser()) return null;
    try {
      const res = await fetch(API + "/api/block/" + userId, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
      });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) { return null; }
  }

  // ── UI: Bell icon ──

  function renderBell() {
    var area = document.getElementById("authArea");
    if (!area || !getUser()) return;

    var bell = document.getElementById("notifBell");
    if (!bell) {
      bell = document.createElement("div");
      bell.className = "notif-bell";
      bell.id = "notifBell";
      bell.innerHTML = '<button class="btn btn-icon btn-ghost" title="Thông báo" style="font-size:1.2rem;position:relative">🔔</button>';
      area.insertBefore(bell, area.firstChild);

      bell.addEventListener("click", function (e) {
        e.stopPropagation();
        var dd = document.getElementById("notifDropdown");
        if (dd) {
          dd.classList.toggle("show");
          if (dd.classList.contains("show") && unreadCount > 0) {
            markAllRead();
          }
        } else {
          renderNotifDropdown();
          if (unreadCount > 0) markAllRead();
        }
      });
    }

    var btn = bell.querySelector("button");
    var badge = bell.querySelector(".notif-count");
    if (unreadCount > 0) {
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "notif-count";
        btn.appendChild(badge);
      }
      badge.textContent = unreadCount > 9 ? "9+" : unreadCount;
    } else if (badge) {
      badge.remove();
    }
  }

  function renderNotifDropdown() {
    var existing = document.getElementById("notifDropdown");
    if (existing) existing.remove();

    var dd = document.createElement("div");
    dd.className = "dropdown-menu notif-dropdown show";
    dd.id = "notifDropdown";
    dd.style.cssText = "position:absolute;right:0;top:100%;width:320px;max-height:400px;overflow-y:auto;z-index:1000;padding:8px 0";

    if (notifications.length === 0) {
      dd.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted)">Chưa có thông báo</div>';
    } else {
      var html = '<div style="padding:8px 14px;font-weight:700;font-size:.85rem;border-bottom:1px solid var(--border)">Thông báo</div>';
      notifications.forEach(function (n) {
        var readClass = n.is_read ? "" : " style=\"background:var(--bg-light)\"";
        var href = _notifLink(n);
        html +=
          '<a class="dropdown-item notif-item"' + readClass +
          (href ? ' href="' + href + '"' : '') +
          ' style="display:block;padding:10px 14px;white-space:normal;line-height:1.35;text-decoration:none;color:inherit">' +
          '<span class="notif-icon">' + _notifIcon(n.type) + '</span> ' +
          '<span>' + escHtml(n.title) + '</span>' +
          (n.body ? '<br><small style="color:var(--muted)">' + escHtml(n.body).slice(0, 80) + '</small>' : '') +
          '<br><small style="color:var(--muted)">' + timeAgo(n.created_at) + '</small>' +
          '</a>';
      });
      dd.innerHTML = html;
    }

    var bell = document.getElementById("notifBell");
    if (bell) {
      bell.style.position = "relative";
      bell.appendChild(dd);
    }

    document.addEventListener("click", function handler(e) {
      if (!dd.contains(e.target) && e.target.id !== "notifBell") {
        dd.classList.remove("show");
        document.removeEventListener("click", handler);
      }
    });
  }

  function _notifIcon(type) {
    var icons = { like: "❤️", comment: "💬", follow: "👤", system: "📢" };
    return icons[type] || "🔔";
  }

  function _notifLink(n) {
    if (n.ref_type === "post") return "#/bai-viet/" + n.ref_id;
    if (n.ref_type === "user") return "#/nguoi-dung/" + n.ref_id;
    return "";
  }

  // ── UI: Follow button ──

  function renderFollowButton(containerId, targetType, targetId, initialFollowing) {
    var container = document.getElementById(containerId);
    if (!container) return;

    var following = !!initialFollowing;
    var btn = document.createElement("button");
    btn.className = following ? "btn btn-outline btn-sm" : "btn btn-primary btn-sm";
    btn.textContent = following ? "Đang theo dõi" : "Theo dõi";

    btn.addEventListener("click", async function () {
      btn.disabled = true;
      var result = await toggleFollow(targetType, targetId);
      if (result !== null) {
        following = result.following;
        btn.className = following ? "btn btn-outline btn-sm" : "btn btn-primary btn-sm";
        btn.textContent = following ? "Đang theo dõi" : "Theo dõi";
      }
      btn.disabled = false;
    });

    container.innerHTML = "";
    container.appendChild(btn);
  }

  // ── UI: Report modal ──

  function showReportModal(targetType, targetId) {
    if (!getUser()) { window.showAuthModal && window.showAuthModal(); return; }

    var existing = document.getElementById("reportModal");
    if (existing) existing.remove();

    var overlay = document.createElement("div");
    overlay.className = "modal-overlay show";
    overlay.id = "reportModal";

    overlay.innerHTML =
      '<div class="modal" style="max-width:420px">' +
        '<div class="modal-head">' +
          '<h2>Báo cáo nội dung</h2>' +
          '<button class="modal-close" id="reportClose">✕</button>' +
        '</div>' +
        '<div class="modal-body">' +
          '<p style="margin-bottom:12px;color:var(--muted)">Chọn lý do báo cáo:</p>' +
          '<div id="reportReasons" style="display:flex;flex-direction:column;gap:8px">' +
            _reportOption("Nội dung spam hoặc quảng cáo") +
            _reportOption("Thông tin sai lệch") +
            _reportOption("Nội dung không phù hợp") +
            _reportOption("Vi phạm bản quyền") +
          '</div>' +
          '<div style="margin-top:12px">' +
            '<textarea class="textarea" id="reportCustom" placeholder="Lý do khác (tùy chọn)..." rows="2" style="width:100%"></textarea>' +
          '</div>' +
          '<button class="btn btn-primary" style="width:100%;margin-top:12px" id="reportSubmitBtn">Gửi báo cáo</button>' +
        '</div>' +
      '</div>';

    document.body.appendChild(overlay);

    var selectedReason = "";

    overlay.querySelectorAll(".report-reason-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        overlay.querySelectorAll(".report-reason-btn").forEach(function (b) { b.classList.remove("selected"); });
        btn.classList.add("selected");
        selectedReason = btn.dataset.reason;
      });
    });

    document.getElementById("reportClose").addEventListener("click", function () {
      overlay.remove();
    });

    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) overlay.remove();
    });

    document.getElementById("reportSubmitBtn").addEventListener("click", async function () {
      var custom = document.getElementById("reportCustom").value.trim();
      var reason = selectedReason || custom;
      if (!reason || reason.length < 5) {
        showToast("Vui lòng chọn hoặc nhập lý do (ít nhất 5 ký tự)", "warning");
        return;
      }
      this.disabled = true;
      this.textContent = "Đang gửi...";
      await submitReport(targetType, targetId, reason);
      overlay.remove();
    });
  }

  function _reportOption(text) {
    return '<button class="btn btn-outline btn-sm report-reason-btn" data-reason="' +
      escHtml(text) + '" style="text-align:left;justify-content:flex-start">' +
      text + '</button>';
  }

  // ── Polling ──

  function startPolling() {
    stopPolling();
    fetchNotifications();
    pollTimer = setInterval(fetchNotifications, 30000);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  // ── Helpers ──

  function escHtml(s) {
    var div = document.createElement("div");
    div.textContent = s || "";
    return div.innerHTML;
  }

  function timeAgo(dateStr) {
    if (!dateStr) return "";
    var now = Date.now();
    var then = new Date(dateStr).getTime();
    var diff = Math.floor((now - then) / 1000);
    if (diff < 60) return "Vừa xong";
    if (diff < 3600) return Math.floor(diff / 60) + " phút trước";
    if (diff < 86400) return Math.floor(diff / 3600) + " giờ trước";
    if (diff < 604800) return Math.floor(diff / 86400) + " ngày trước";
    return new Date(dateStr).toLocaleDateString("vi-VN");
  }

  function showToast(msg, type) {
    var container = document.getElementById("toastContainer");
    if (!container) return;
    var t = document.createElement("div");
    t.className = "toast" + (type ? " toast-" + type : "");
    t.textContent = msg;
    container.appendChild(t);
    requestAnimationFrame(function () { t.classList.add("show"); });
    setTimeout(function () {
      t.classList.remove("show");
      setTimeout(function () { t.remove(); }, 300);
    }, 3500);
  }

  // ── Init: start polling when logged in ──

  function init() {
    if (getUser()) {
      startPolling();
    }
    var origLogout = window._vl360Auth && window._vl360Auth.logout;
    if (window._vl360Auth) {
      var _origLogout = window._vl360Auth.logout;
      window._vl360Auth.logout = function () {
        stopPolling();
        var bell = document.getElementById("notifBell");
        if (bell) bell.remove();
        var dd = document.getElementById("notifDropdown");
        if (dd) dd.remove();
        if (_origLogout) _origLogout();
      };
    }
  }

  // Wait for auth to be ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { setTimeout(init, 500); });
  } else {
    setTimeout(init, 500);
  }

  // Re-init on login (check periodically for auth state change)
  var _lastAuthState = false;
  setInterval(function () {
    var loggedIn = !!getUser();
    if (loggedIn && !_lastAuthState) {
      startPolling();
    } else if (!loggedIn && _lastAuthState) {
      stopPolling();
    }
    _lastAuthState = loggedIn;
  }, 2000);

  // ── Expose ──

  window._vl360Notif = {
    fetchNotifications: fetchNotifications,
    renderFollowButton: renderFollowButton,
    showReportModal: showReportModal,
    toggleFollow: toggleFollow,
    toggleBlock: toggleBlock,
    getFollowerCount: getFollowerCount,
    startPolling: startPolling,
    stopPolling: stopPolling,
  };
})();

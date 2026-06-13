/* ============================================================
   vinhlong360 — Feed & Community Page
   Renders community feed, entity feed, post detail, user profile
   ============================================================ */

(function () {
  const API = window.location.origin;

  // ── Community Feed Page ──
  async function renderFeedPage(container, params) {
    params = params || {};
    var page = 1;
    var loading = false;
    var hasMore = true;

    container.innerHTML =
      '<div class="page">' +
        '<div class="page-head">' +
          '<h1>Cộng đồng vinhlong360</h1>' +
          '<p>Chia sẻ trải nghiệm du lịch, đánh giá địa điểm, giới thiệu nông sản và kết nối cộng đồng bản địa</p>' +
        '</div>' +
        '<div class="feed-layout">' +
          '<div class="feed-main">' +
            '<div id="createPostArea"></div>' +
            '<div class="feed-filters" id="feedFilters"></div>' +
            '<div id="feedPosts"></div>' +
            '<div id="feedLoader" class="empty" style="display:none"><div class="spinner" style="margin:0 auto"></div></div>' +
            '<div id="feedEnd" class="empty" style="display:none">Đã xem hết bài viết</div>' +
          '</div>' +
          '<aside class="feed-sidebar" id="feedSidebar"></aside>' +
        '</div>' +
      '</div>';

    // Create post form (if logged in)
    var auth = window._vl360Auth;
    if (auth && auth.getUser()) {
      await loadEntitiesAndRenderCreatePost();
    }

    renderFeedFilters(params);
    await loadFeed(params);
    renderSidebar();

    // Infinite scroll
    window._feedScrollHandler = function () {
      if (loading || !hasMore) return;
      if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 400) {
        page++;
        loadFeed(params);
      }
    };
    window.addEventListener("scroll", window._feedScrollHandler);

    async function loadFeed(filters) {
      loading = true;
      document.getElementById("feedLoader").style.display = "block";

      var qs = "?page=" + page + "&limit=15";
      if (filters.post_type) qs += "&post_type=" + filters.post_type;
      if (filters.entity_type) qs += "&entity_type=" + filters.entity_type;
      if (filters.area) qs += "&area=" + filters.area;

      var headers = {};
      if (auth && auth.getToken()) headers = auth.authHeaders();

      try {
        var res = await fetch(API + "/api/feed" + qs, { headers: headers });
        var data = await res.json();
        var postsEl = document.getElementById("feedPosts");

        if (data.posts && data.posts.length) {
          data.posts.forEach(function (post) {
            postsEl.insertAdjacentHTML("beforeend",
              window._vl360Social.renderPostCard(post));
          });
        }

        hasMore = data.has_more;
        if (!hasMore) {
          document.getElementById("feedEnd").style.display = "block";
        }
      } catch (e) {
        if (page === 1) {
          document.getElementById("feedPosts").innerHTML =
            '<p class="empty">Chưa có bài viết nào. Hãy là người đầu tiên chia sẻ!</p>';
        }
      }

      document.getElementById("feedLoader").style.display = "none";
      loading = false;
    }
  }

  function renderFeedFilters(currentFilters) {
    var el = document.getElementById("feedFilters");
    if (!el) return;

    var types = [
      { key: "", label: "Tất cả" },
      { key: "share", label: "Chia sẻ" },
      { key: "review", label: "Đánh giá" },
      { key: "recommend", label: "Giới thiệu" },
      { key: "question", label: "Hỏi đáp" },
    ];

    var entityTypes = [
      { key: "", label: "Mọi loại" },
      { key: "attraction", label: "🏛️ Du lịch" },
      { key: "product", label: "🎁 Sản phẩm" },
      { key: "dish", label: "🍜 Ẩm thực" },
      { key: "experience", label: "🎋 Trải nghiệm" },
      { key: "craft", label: "🏺 Làng nghề" },
    ];

    var html = '<div class="chip-row" style="margin-bottom:8px">';
    types.forEach(function (t) {
      var active = (currentFilters.post_type || "") === t.key ? " active" : "";
      html += '<button class="chip' + active + '" onclick="window._vl360Feed.filterByType(\'' + t.key + '\')">' + t.label + '</button>';
    });
    html += '</div><div class="chip-row">';
    entityTypes.forEach(function (t) {
      var active = (currentFilters.entity_type || "") === t.key ? " active" : "";
      html += '<button class="chip' + active + '" onclick="window._vl360Feed.filterByEntity(\'' + t.key + '\')">' + t.label + '</button>';
    });
    html += '</div>';

    el.innerHTML = html;
  }

  async function loadEntitiesAndRenderCreatePost() {
    try {
      var res = await fetch(API + "/api/feed?limit=1");
      // Fetch entities for the create post dropdown
      // Use the store if available
      var entities = [];
      if (window.store && window.store.entities) {
        entities = window.store.entities.filter(function (e) {
          return e.type !== "place";
        }).slice(0, 200);
      }
      window._vl360Social.renderCreatePost("createPostArea", entities);
    } catch (e) {}
  }

  function renderSidebar() {
    var el = document.getElementById("feedSidebar");
    if (!el) return;

    el.innerHTML =
      '<div class="sidebar-card">' +
        '<h3>Về cộng đồng</h3>' +
        '<p>Nơi chia sẻ trải nghiệm du lịch, đánh giá địa điểm, giới thiệu nông sản và kết nối cộng đồng Vĩnh Long — Trà Vinh — Bến Tre.</p>' +
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">' +
          '<span class="tag tag-primary">Du lịch</span>' +
          '<span class="tag tag-accent">Nông sản</span>' +
          '<span class="tag tag-secondary">Cộng đồng</span>' +
          '<span class="tag tag-tertiary">Ẩm thực</span>' +
        '</div>' +
      '</div>' +
      '<div class="sidebar-card">' +
        '<h3>Hướng dẫn</h3>' +
        '<ul class="sidebar-list">' +
          '<li>📝 <strong>Chia sẻ</strong> — câu chuyện, kinh nghiệm du lịch</li>' +
          '<li>⭐ <strong>Đánh giá</strong> — chấm điểm địa điểm, sản phẩm</li>' +
          '<li>🎁 <strong>Giới thiệu</strong> — nông sản, sản phẩm OCOP</li>' +
          '<li>❓ <strong>Hỏi đáp</strong> — hỏi cộng đồng về du lịch</li>' +
        '</ul>' +
      '</div>';
  }

  // ── Entity Feed Page ──
  async function renderEntityFeed(container, entityId) {
    container.innerHTML = '<div class="page"><div class="spinner" style="margin:40px auto"></div></div>';

    var headers = {};
    var auth = window._vl360Auth;
    if (auth && auth.getToken()) headers = auth.authHeaders();

    try {
      var res = await fetch(API + "/api/entities/" + entityId + "/feed", { headers: headers });
      var data = await res.json();
      var entity = data.entity;
      var rating = data.rating;
      var eInfo = window._vl360Social.ENTITY_TYPE_MAP[entity.type] || { icon: "📍", label: "" };

      var html = '<div class="page">';
      html += '<a class="back" href="#/cong-dong">← Cộng đồng</a>';
      html += '<div class="entity-feed-header">';
      html += '<span style="font-size:2rem">' + eInfo.icon + '</span>';
      html += '<div>';
      html += '<h1>' + esc(entity.name) + '</h1>';
      html += '<span class="tag tag-muted">' + eInfo.label + '</span>';
      if (rating.count > 0) {
        html += ' ' + window._vl360Social.renderStars(Math.round(rating.avg)) +
          ' <strong>' + rating.avg + '</strong> (' + rating.count + ' đánh giá)';
      }
      html += '</div></div>';

      if (entity.summary) {
        html += '<p style="color:var(--muted);margin:0 0 16px">' + esc(entity.summary) + '</p>';
      }

      // Follow entity + Write review CTA
      html += '<div style="margin-bottom:16px;display:flex;gap:8px;align-items:center">';
      html += '<span id="followBtnEntity"></span>';
      if (auth && auth.getUser()) {
        html += '<button class="btn btn-accent" onclick="window._vl360Feed.showCreateReview(\'' + entityId + '\')">⭐ Viết đánh giá</button>';
      }
      html += '</div>';

      html += '<div id="entityFeedPosts">';
      if (data.posts && data.posts.length) {
        data.posts.forEach(function (post) {
          html += window._vl360Social.renderPostCard(post);
        });
      } else {
        html += '<p class="empty">Chưa có bài viết. Hãy là người đầu tiên đánh giá!</p>';
      }
      html += '</div></div>';

      container.innerHTML = html;

      if (window._vl360Notif && document.getElementById("followBtnEntity")) {
        window._vl360Notif.renderFollowButton("followBtnEntity", "entity", entityId, false);
      }
    } catch (e) {
      container.innerHTML = '<div class="page"><p class="empty">Không tải được dữ liệu</p></div>';
    }
  }

  // ── Post Detail Page ──
  async function renderPostDetail(container, postId) {
    container.innerHTML = '<div class="page"><div class="spinner" style="margin:40px auto"></div></div>';

    var headers = {};
    var auth = window._vl360Auth;
    if (auth && auth.getToken()) headers = auth.authHeaders();

    try {
      var res = await fetch(API + "/api/posts/" + postId, { headers: headers });
      if (!res.ok) {
        container.innerHTML = '<div class="page"><p class="empty">Bài viết không tồn tại</p></div>';
        return;
      }
      var data = await res.json();

      var cRes = await fetch(API + "/api/posts/" + postId + "/comments");
      var cData = await cRes.json();

      var html = '<div class="page">';
      html += '<a class="back" href="#/cong-dong">← Cộng đồng</a>';
      html += window._vl360Social.renderPostCard(data.post);
      html += window._vl360Social.renderCommentSection
        ? renderCommentSectionStandalone(cData.comments, postId)
        : '';
      html += '</div>';

      container.innerHTML = html;
    } catch (e) {
      container.innerHTML = '<div class="page"><p class="empty">Lỗi tải bài viết</p></div>';
    }
  }

  function renderCommentSectionStandalone(comments, postId) {
    var html = '<div class="comment-section">';
    html += '<h4 class="comment-title">Bình luận</h4>';
    if (comments && comments.length) {
      comments.forEach(function (c) {
        html += '<div class="comment-item">' +
          '<div class="avatar avatar-sm">' + initials(c.author.display_name) + '</div>' +
          '<div>' +
            '<strong>' + esc(c.author.display_name) + '</strong> ' +
            '<span class="comment-time">' + timeAgo(c.created_at) + '</span>' +
            '<p class="comment-text">' + esc(c.content) + '</p>' +
          '</div></div>';
        if (c.replies) {
          c.replies.forEach(function (r) {
            html += '<div class="comment-reply"><div class="comment-item">' +
              '<div class="avatar avatar-sm">' + initials(r.author.display_name) + '</div>' +
              '<div><strong>' + esc(r.author.display_name) + '</strong> ' +
              '<span class="comment-time">' + timeAgo(r.created_at) + '</span>' +
              '<p class="comment-text">' + esc(r.content) + '</p></div></div></div>';
          });
        }
      });
    } else {
      html += '<p class="empty" style="padding:12px 0">Chưa có bình luận</p>';
    }
    html += '<div class="comment-form">' +
      '<input class="input" id="commentInput_' + postId + '" placeholder="Viết bình luận..." />' +
      '<button class="btn btn-sm btn-primary" onclick="window._vl360Social.submitComment(\'' + postId + '\')">Gửi</button>' +
    '</div></div>';
    return html;
  }

  // ── User Profile Page ──
  async function renderUserProfile(container, userId) {
    container.innerHTML = '<div class="page"><div class="spinner" style="margin:40px auto"></div></div>';
    try {
      var res = await fetch(API + "/api/users/" + userId);
      var data = await res.json();
      var u = data.user;

      var postsRes = await fetch(API + "/api/users/" + userId + "/posts");
      var postsData = await postsRes.json();

      var html = '<div class="page">';
      html += '<a class="back" href="#/cong-dong">← Cộng đồng</a>';
      html += '<div class="profile-header">';
      html += '<div class="avatar avatar-xl">' + initials(u.display_name) + '</div>';
      html += '<div>';
      html += '<h1>' + esc(u.display_name) + '</h1>';
      if (u.bio) html += '<p style="color:var(--muted)">' + esc(u.bio) + '</p>';
      html += '<div class="profile-stats">';
      html += '<span><strong>' + u.stats.posts + '</strong> bài viết</span>';
      html += '<span><strong>' + u.stats.reviews + '</strong> đánh giá</span>';
      html += '</div>';
      var me = window._vl360Auth && window._vl360Auth.getUser();
      if (me && String(me.id) !== String(userId)) {
        html += '<div id="followBtnUser" style="margin-top:8px"></div>';
      }
      html += '</div></div>';

      html += '<h2 style="margin-top:24px">Bài viết</h2>';
      html += '<div id="userPosts">';
      if (postsData.posts && postsData.posts.length) {
        postsData.posts.forEach(function (p) {
          html += window._vl360Social.renderPostCard(p);
        });
      } else {
        html += '<p class="empty">Chưa có bài viết</p>';
      }
      html += '</div></div>';

      container.innerHTML = html;

      if (window._vl360Notif && document.getElementById("followBtnUser")) {
        window._vl360Notif.renderFollowButton("followBtnUser", "user", userId, false);
      }
    } catch (e) {
      container.innerHTML = '<div class="page"><p class="empty">Không tìm thấy người dùng</p></div>';
    }
  }

  // ── Exposed API ──
  var _currentFilters = {};

  window._vl360Feed = {
    renderFeedPage: renderFeedPage,
    renderEntityFeed: renderEntityFeed,
    renderPostDetail: renderPostDetail,
    renderUserProfile: renderUserProfile,

    filterByType: function (type) {
      _currentFilters.post_type = type || undefined;
      var app = document.getElementById("app");
      if (app) renderFeedPage(app, _currentFilters);
    },
    filterByEntity: function (type) {
      _currentFilters.entity_type = type || undefined;
      var app = document.getElementById("app");
      if (app) renderFeedPage(app, _currentFilters);
    },

    showCreateReview: function (entityId) {
      window.location.hash = "#/cong-dong";
      setTimeout(function () {
        var sel = document.getElementById("createPostEntity");
        if (sel) sel.value = entityId;
        var chips = document.querySelectorAll(".post-type-chip");
        chips.forEach(function (c) {
          c.classList.toggle("active", c.dataset.type === "review");
        });
        window._vl360Social.selectPostType(
          document.querySelector('.post-type-chip[data-type="review"]'));
      }, 300);
    },

    refresh: function () {
      var app = document.getElementById("app");
      if (app && window.location.hash.startsWith("#/cong-dong")) {
        renderFeedPage(app, _currentFilters);
      }
    },
  };

  // ── Util ──
  function initials(name) {
    if (!name) return "?";
    return name.split(" ").map(function (w) { return w[0]; }).join("").slice(0, 2).toUpperCase();
  }
  function esc(s) {
    if (!s) return "";
    var d = document.createElement("div"); d.textContent = s; return d.innerHTML;
  }
  function timeAgo(dateStr) {
    if (!dateStr) return "";
    var d = new Date(dateStr); var now = new Date(); var diff = (now - d) / 1000;
    if (diff < 60) return "Vừa xong";
    if (diff < 3600) return Math.floor(diff / 60) + " phút trước";
    if (diff < 86400) return Math.floor(diff / 3600) + " giờ trước";
    if (diff < 604800) return Math.floor(diff / 86400) + " ngày trước";
    return d.toLocaleDateString("vi-VN");
  }
})();

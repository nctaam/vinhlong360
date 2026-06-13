/* ============================================================
   vinhlong360 — Social Components
   PostCard, ReviewCard, CommentSection, StarRating, CreatePost
   ============================================================ */

(function () {
  const API = window.location.origin;

  // ── Entity type labels & icons ──
  const ENTITY_TYPE_MAP = {
    experience: { label: "Trải nghiệm", icon: "🎋" },
    product: { label: "Sản phẩm", icon: "🎁" },
    attraction: { label: "Điểm du lịch", icon: "🏛️" },
    dish: { label: "Ẩm thực", icon: "🍜" },
    craft: { label: "Làng nghề", icon: "🏺" },
    accommodation: { label: "Lưu trú", icon: "🏠" },
    place: { label: "Địa điểm", icon: "📍" },
    org: { label: "Tổ chức", icon: "🏢" },
  };

  const POST_TYPE_MAP = {
    review: { label: "Đánh giá", color: "var(--accent)" },
    share: { label: "Chia sẻ", color: "var(--secondary)" },
    recommend: { label: "Giới thiệu", color: "var(--primary)" },
    question: { label: "Hỏi đáp", color: "var(--tertiary)" },
  };

  // ── Star Rating (display) ──
  function renderStars(rating, size) {
    size = size || "inline";
    var cls = size === "inline" ? "star-rating-inline" : "star-rating readonly";
    var html = '<span class="' + cls + '">';
    for (var i = 1; i <= 5; i++) {
      html += '<span class="star' + (i <= rating ? " active" : "") + '">★</span>';
    }
    html += "</span>";
    return html;
  }

  // ── Star Rating (picker) ──
  function renderStarPicker(containerId, onChange) {
    var el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = '<div class="star-rating" id="' + containerId + 'Picker"></div>';
    var picker = document.getElementById(containerId + "Picker");
    var value = 0;
    for (var i = 1; i <= 5; i++) {
      var star = document.createElement("span");
      star.className = "star";
      star.textContent = "★";
      star.dataset.val = i;
      star.addEventListener("click", function () {
        value = parseInt(this.dataset.val);
        picker.querySelectorAll(".star").forEach(function (s) {
          s.classList.toggle("active", parseInt(s.dataset.val) <= value);
        });
        if (onChange) onChange(value);
      });
      picker.appendChild(star);
    }
    return function () { return value; };
  }

  // ── PostCard ──
  function renderPostCard(post) {
    var entity = post.entity;
    var typeInfo = POST_TYPE_MAP[post.post_type] || POST_TYPE_MAP.share;
    var entityInfo = entity ? (ENTITY_TYPE_MAP[entity.type] || { label: "", icon: "📍" }) : null;

    var html = '<article class="post-card" data-id="' + post.id + '">';

    // Header: author + entity tag
    html += '<div class="post-header">';
    html += '<div class="avatar">' + initials(post.author.display_name) + "</div>";
    html += "<div>";
    html += '<strong class="post-author">' + esc(post.author.display_name) + "</strong>";
    html += '<span class="post-meta">';
    html += '<span class="tag" style="border:1px solid ' + typeInfo.color + ';color:' + typeInfo.color + '">' + typeInfo.label + "</span>";
    html += " · " + timeAgo(post.created_at);
    html += "</span>";
    html += "</div></div>";

    // Entity link
    if (entity && entity.name) {
      html += '<a class="post-entity-link" href="#/chi-tiet/' + entity.id + '">';
      html += entityInfo.icon + " " + esc(entity.name);
      html += '<span class="tag-muted">' + entityInfo.label + "</span>";
      html += "</a>";
    }

    // Rating (review)
    if (post.post_type === "review" && post.rating) {
      html += '<div class="post-rating">' + renderStars(post.rating) + "</div>";
    }

    // Content
    html += '<div class="post-content">' + formatContent(post.content) + "</div>";

    // Images
    if (post.images && post.images.length) {
      html += '<div class="post-images">';
      post.images.forEach(function (img) {
        html += '<img src="' + esc(img) + '" loading="lazy" alt="Ảnh bài viết" />';
      });
      html += "</div>";
    }

    // Actions
    html += '<div class="post-actions">';
    html += '<button class="post-action' + (post.is_liked ? " active" : "") + '" onclick="window._vl360Social.toggleLike(\'' + post.id + '\', this)">❤️ ' + (post.like_count || "") + "</button>";
    html += '<button class="post-action" onclick="window._vl360Social.showComments(\'' + post.id + '\')">💬 ' + (post.comment_count || "") + "</button>";
    html += '<button class="post-action' + (post.is_bookmarked ? " active" : "") + '" onclick="window._vl360Social.toggleBookmark(\'' + post.id + '\', this)">🔖</button>';
    html += '<button class="post-action" onclick="window._vl360Notif && window._vl360Notif.showReportModal(\'post\', \'' + post.id + '\')" title="Báo cáo">⚑</button>';
    html += "</div>";

    html += "</article>";
    return html;
  }

  // ── Create Post Form ──
  function renderCreatePost(containerId, entities, preselectedEntity) {
    var el = document.getElementById(containerId);
    if (!el) return;

    var html = '<div class="create-post">';
    html += '<div class="create-post-header">';
    html += "<h3>Chia sẻ với cộng đồng</h3>";
    html += "</div>";

    // Post type selector
    html += '<div class="chip-row" style="margin-bottom:12px">';
    Object.keys(POST_TYPE_MAP).forEach(function (type) {
      var info = POST_TYPE_MAP[type];
      var active = type === "share" ? " active" : "";
      html += '<button class="chip post-type-chip' + active + '" data-type="' + type + '" onclick="window._vl360Social.selectPostType(this)">' + info.label + "</button>";
    });
    html += "</div>";

    // Entity selector
    html += '<div class="form-group">';
    html += '<label class="form-label">Gắn địa điểm / sản phẩm</label>';
    html += '<select class="select" id="createPostEntity">';
    html += '<option value="">— Không gắn —</option>';
    if (entities && entities.length) {
      entities.forEach(function (e) {
        var info = ENTITY_TYPE_MAP[e.type] || { icon: "📍" };
        var selected = preselectedEntity === e.id ? " selected" : "";
        html += '<option value="' + e.id + '"' + selected + ">" + info.icon + " " + esc(e.name) + "</option>";
      });
    }
    html += "</select></div>";

    // Rating (hidden by default, shown for review type)
    html += '<div class="form-group" id="createPostRatingGroup" style="display:none">';
    html += '<label class="form-label">Đánh giá</label>';
    html += '<div id="createPostRating"></div>';
    html += "</div>";

    // Content
    html += '<div class="form-group">';
    html += '<textarea class="textarea" id="createPostContent" placeholder="Bạn có trải nghiệm gì muốn chia sẻ?" rows="4"></textarea>';
    html += "</div>";

    // Image upload
    html += '<div class="form-group">';
    html += '<div class="img-upload" id="createPostUpload" onclick="document.getElementById(\'createPostFile\').click()">';
    html += "📷 Thêm ảnh (tối đa 4 ảnh, 5MB/ảnh)";
    html += "</div>";
    html += '<input type="file" id="createPostFile" accept="image/*" multiple style="display:none" onchange="window._vl360Social.handleImageUpload(this)" />';
    html += '<div class="img-preview-row" id="createPostPreviews"></div>';
    html += "</div>";

    // Submit
    html += '<button class="btn btn-primary" style="width:100%" id="createPostBtn" onclick="window._vl360Social.submitPost()">Đăng bài</button>';
    html += "</div>";

    el.innerHTML = html;

    // Init star picker for review
    window._createPostRatingGetter = renderStarPicker("createPostRating", function () {});
  }

  // ── Comment Section ──
  function renderCommentSection(comments, postId) {
    var html = '<div class="comment-section">';
    html += '<h4 class="comment-title">Bình luận</h4>';

    if (comments && comments.length) {
      comments.forEach(function (c) {
        html += renderComment(c, postId);
        if (c.replies) {
          c.replies.forEach(function (r) {
            html += '<div class="comment-reply">' + renderComment(r, postId) + "</div>";
          });
        }
      });
    } else {
      html += '<p class="empty" style="padding:12px 0">Chưa có bình luận</p>';
    }

    // Add comment form
    html += '<div class="comment-form">';
    html += '<input class="input" id="commentInput_' + postId + '" placeholder="Viết bình luận..." />';
    html += '<button class="btn btn-sm btn-primary" onclick="window._vl360Social.submitComment(\'' + postId + '\')">Gửi</button>';
    html += "</div>";

    html += "</div>";
    return html;
  }

  function renderComment(c, postId) {
    return '<div class="comment-item">' +
      '<div class="avatar avatar-sm">' + initials(c.author.display_name) + "</div>" +
      "<div>" +
        '<strong>' + esc(c.author.display_name) + "</strong> " +
        '<span class="comment-time">' + timeAgo(c.created_at) + "</span>" +
        '<p class="comment-text">' + esc(c.content) + "</p>" +
      "</div>" +
    "</div>";
  }

  // ── Actions (exposed globally) ──

  var _uploadedImages = [];
  var _selectedPostType = "share";

  window._vl360Social = {
    selectPostType: function (btn) {
      document.querySelectorAll(".post-type-chip").forEach(function (c) { c.classList.remove("active"); });
      btn.classList.add("active");
      _selectedPostType = btn.dataset.type;
      var ratingGroup = document.getElementById("createPostRatingGroup");
      if (ratingGroup) {
        ratingGroup.style.display = _selectedPostType === "review" ? "block" : "none";
      }
    },

    handleImageUpload: async function (input) {
      var files = Array.from(input.files).slice(0, 4 - _uploadedImages.length);
      var previews = document.getElementById("createPostPreviews");
      var auth = window._vl360Auth;
      if (!auth || !auth.getToken()) {
        showToast("Đăng nhập để tải ảnh", "error");
        return;
      }

      for (var i = 0; i < files.length; i++) {
        var fd = new FormData();
        fd.append("file", files[i]);
        try {
          var res = await fetch(API + "/api/upload/image", {
            method: "POST",
            headers: auth.authHeaders(),
            body: fd,
          });
          var data = await res.json();
          if (data.url) {
            _uploadedImages.push(data.url);
            var item = document.createElement("div");
            item.className = "img-preview-item";
            item.innerHTML = '<img src="' + data.url + '" />' +
              '<button class="remove" data-url="' + data.url + '" onclick="window._vl360Social.removeImage(this)">✕</button>';
            previews.appendChild(item);
          }
        } catch (e) {
          showToast("Lỗi tải ảnh", "error");
        }
      }
      input.value = "";
    },

    removeImage: function (btn) {
      var url = btn.dataset.url;
      _uploadedImages = _uploadedImages.filter(function (u) { return u !== url; });
      btn.parentElement.remove();
    },

    submitPost: async function () {
      var auth = window._vl360Auth;
      if (!auth || !auth.getToken()) {
        showAuthModal();
        return;
      }
      var content = document.getElementById("createPostContent").value.trim();
      if (content.length < 10) {
        showToast("Nội dung cần ít nhất 10 ký tự", "error");
        return;
      }

      var entityId = document.getElementById("createPostEntity").value || null;
      var rating = null;
      if (_selectedPostType === "review" && window._createPostRatingGetter) {
        rating = window._createPostRatingGetter();
        if (!rating) {
          showToast("Vui lòng chọn số sao đánh giá", "error");
          return;
        }
      }

      if (_selectedPostType === "review" && !entityId) {
        showToast("Đánh giá phải gắn địa điểm hoặc sản phẩm", "error");
        return;
      }

      var btn = document.getElementById("createPostBtn");
      btn.disabled = true;
      btn.textContent = "Đang đăng...";

      try {
        var res = await fetch(API + "/api/posts", {
          method: "POST",
          headers: Object.assign({ "Content-Type": "application/json" }, auth.authHeaders()),
          body: JSON.stringify({
            content: content,
            entity_id: entityId,
            post_type: _selectedPostType,
            rating: rating,
            images: _uploadedImages,
          }),
        });
        var data = await res.json();
        if (res.ok && data.post) {
          showToast("Đăng bài thành công!", "success");
          document.getElementById("createPostContent").value = "";
          _uploadedImages = [];
          document.getElementById("createPostPreviews").innerHTML = "";
          if (window._vl360Feed && window._vl360Feed.refresh) {
            window._vl360Feed.refresh();
          }
        } else {
          showToast(data.detail || "Lỗi đăng bài", "error");
        }
      } catch (e) {
        showToast("Lỗi kết nối", "error");
      }
      btn.disabled = false;
      btn.textContent = "Đăng bài";
    },

    toggleLike: async function (postId, btn) {
      var auth = window._vl360Auth;
      if (!auth || !auth.getToken()) { showAuthModal(); return; }
      try {
        var res = await fetch(API + "/api/posts/" + postId + "/like", {
          method: "POST",
          headers: auth.authHeaders(),
        });
        var data = await res.json();
        btn.classList.toggle("active", data.liked);
        btn.innerHTML = "❤️ " + (data.like_count || "");
      } catch (e) {}
    },

    toggleBookmark: async function (postId, btn) {
      var auth = window._vl360Auth;
      if (!auth || !auth.getToken()) { showAuthModal(); return; }
      try {
        var res = await fetch(API + "/api/posts/" + postId + "/bookmark", {
          method: "POST",
          headers: auth.authHeaders(),
        });
        var data = await res.json();
        btn.classList.toggle("active", data.bookmarked);
        showToast(data.bookmarked ? "Đã lưu" : "Đã bỏ lưu", "success");
      } catch (e) {}
    },

    showComments: async function (postId) {
      try {
        var res = await fetch(API + "/api/posts/" + postId + "/comments");
        var data = await res.json();
        var card = document.querySelector('.post-card[data-id="' + postId + '"]');
        if (!card) return;
        var existing = card.querySelector(".comment-section");
        if (existing) { existing.remove(); return; }
        card.insertAdjacentHTML("beforeend", renderCommentSection(data.comments, postId));
      } catch (e) {}
    },

    submitComment: async function (postId) {
      var auth = window._vl360Auth;
      if (!auth || !auth.getToken()) { showAuthModal(); return; }
      var input = document.getElementById("commentInput_" + postId);
      if (!input || !input.value.trim()) return;
      try {
        var res = await fetch(API + "/api/posts/" + postId + "/comments", {
          method: "POST",
          headers: Object.assign({ "Content-Type": "application/json" }, auth.authHeaders()),
          body: JSON.stringify({ content: input.value.trim() }),
        });
        if (res.ok) {
          input.value = "";
          window._vl360Social.showComments(postId);
          window._vl360Social.showComments(postId);
        }
      } catch (e) {}
    },

    renderPostCard: renderPostCard,
    renderCreatePost: renderCreatePost,
    renderStars: renderStars,
    ENTITY_TYPE_MAP: ENTITY_TYPE_MAP,
    POST_TYPE_MAP: POST_TYPE_MAP,
  };

  // ── Util ──
  function initials(name) {
    if (!name) return "?";
    return name.split(" ").map(function (w) { return w[0]; }).join("").slice(0, 2).toUpperCase();
  }

  function esc(s) {
    if (!s) return "";
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function formatContent(text) {
    if (!text) return "";
    return esc(text).replace(/\n/g, "<br>");
  }

  function timeAgo(dateStr) {
    if (!dateStr) return "";
    var d = new Date(dateStr);
    var now = new Date();
    var diff = (now - d) / 1000;
    if (diff < 60) return "Vừa xong";
    if (diff < 3600) return Math.floor(diff / 60) + " phút trước";
    if (diff < 86400) return Math.floor(diff / 3600) + " giờ trước";
    if (diff < 604800) return Math.floor(diff / 86400) + " ngày trước";
    return d.toLocaleDateString("vi-VN");
  }
})();

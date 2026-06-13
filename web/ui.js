/*
 * vinhlong360 — UI (router hash + các view). Đọc dữ liệu QUA window.Store.
 * Mô hình 2 cấp: tỉnh → xã/phường. Khu vực (VL/BT/TV) chỉ là nhóm tham chiếu.
 */
(function () {
  const S = window.Store;
  const CURRENT_MONTH = new Date().getMonth() + 1;

  /* ===================== helpers ===================== */
  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function cardBadges(e, sel) {
    const out = [];
    if (sel && S.relevanceScore(e, sel) === 4) out.push('<span class="badge peak">🔥 Đang rộ</span>');
    if (!e.season || S.isYearRound(e.season)) out.push('<span class="badge year">Quanh năm</span>');
    else out.push('<span class="badge season">' + S.seasonText(e.season) + "</span>");
    if (e.attributes && e.attributes.ocop) out.push('<span class="badge ocop">⭐ ' + e.attributes.ocop + "</span>");
    return out.join("");
  }

  function cardHTML(e, sel) {
    const t = S.TYPE_META[e.type] || { emoji: "•", label: e.type, cat: "place" };
    const place = S.byId(e.placeId);
    const pName = place ? place.name : "";
    const shortName = place ? place.name.replace(/^(Xã |Phường )/, "") : "";
    const needsLegacy = place && place.legacyArea && !shortName.includes(place.legacyArea) && !place.legacyArea.includes(shortName);
    const legacy = needsLegacy ? ' <span class="legacy-note">' + place.legacyArea + " (cũ)</span>" : "";
    return (
      '<a class="card cat-' + t.cat + '" href="#/e/' + e.id + '">' +
      '<div class="cover cat-' + t.cat + '"><span>' + t.emoji + "</span></div>" +
      '<div class="card-b">' +
      '<span class="card-type">' + t.label + "</span>" +
      "<h3>" + e.name + "</h3>" +
      '<p class="summary">' + (e.summary || "") + "</p>" +
      '<p class="place">' + pName + legacy + "</p>" +
      '<div class="badges">' + cardBadges(e, sel) + "</div>" +
      "</div></a>"
    );
  }

  function grid(list, sel) { return '<div class="grid">' + list.map((e) => cardHTML(e, sel)).join("") + "</div>"; }

  function section(title, link, body) {
    return (
      '<section class="block"><div class="section-head"><h2>' + title + "</h2>" +
      (link ? '<a class="see-all" href="' + link + '">Xem tất cả →</a>' : "") +
      "</div>" + body + "</section>"
    );
  }

  function itinCard(it) {
    const am = S.AREA_META[it.area] || { emoji: "📍", name: it.area };
    return (
      '<a class="card cat-itinerary" href="#/lich-trinh/' + it.id + '">' +
      '<div class="cover cat-itinerary"><span>🗺️</span></div>' +
      '<div class="card-b">' +
      '<span class="card-type">' + am.emoji + " " + am.name + " · " + it.duration + "</span>" +
      "<h3>" + it.title + "</h3>" +
      '<p class="summary">' + it.summary + "</p>" +
      '<p class="place">' + it.stops.length + " điểm dừng</p>" +
      "</div></a>"
    );
  }

  function areaCard(areaKey) {
    const am = S.AREA_META[areaKey];
    const count = S.query({ area: areaKey }).length;
    const ps = S.placeStats(areaKey);
    return (
      '<a class="region-card" href="#/khu-vuc/' + areaKey + '">' +
      '<span class="rc-emoji">' + am.emoji + "</span>" +
      "<h3>Khu vực " + am.name + "</h3><p>" + am.blurb + "</p>" +
      '<span class="rc-count">' + ps.phuong + " phường · " + ps.xa + " xã · " + count + " mục →</span></a>"
    );
  }

  function monthStrip(season) {
    if (!season) return "";
    let cells = "";
    for (let m = 1; m <= 12; m++) {
      const on = season.months.includes(m);
      const peak = (season.peak || []).includes(m);
      cells += '<span class="ms-cell' + (on ? " on" : "") + (peak ? " peak" : "") + '">' + m + "</span>";
    }
    return '<div class="month-strip">' + cells + "</div>";
  }

  function fact(k, v) { return v ? '<div class="fact"><span class="k">' + k + '</span><span class="v">' + v + "</span></div>" : ""; }

  function placeOptions(selected) {
    const list = S.placesWithContent();
    const byA = {};
    list.forEach((p) => { (byA[p.area] = byA[p.area] || []).push(p); });
    let h = '<option value="all"' + (selected === "all" ? " selected" : "") + ">Tất cả xã/phường</option>";
    Object.keys(S.AREA_META).forEach((a) => {
      const ps = byA[a];
      if (!ps || !ps.length) return;
      h += '<optgroup label="KV ' + S.areaName(a) + '">';
      ps.sort((a, b) => a.name.localeCompare(b.name, "vi"));
      ps.forEach((p) => {
        h += '<option value="' + p.id + '"' + (selected === p.id ? " selected" : "") + ">" + p.name + "</option>";
      });
      h += "</optgroup>";
    });
    return h;
  }

  function hubOf(type) {
    if (["experience", "attraction", "accommodation", "craft_village", "dish"].includes(type)) return "du-lich";
    if (type === "product") return "san-pham";
    return "";
  }

  /* ===================== views ===================== */
  function renderHome() {
    const st = S.stats();
    const season = S.seasonalNow(String(CURRENT_MONTH));
    const exp = S.featured(["experience"], 6);
    const prod = S.featured(["product"], 6);
    const its = S.itineraries.slice(0, 4);
    const areas = Object.keys(S.AREA_META);

    return (
      '<section class="hero"><div class="hero-inner">' +
      "<h1>Khám phá Vĩnh Long<br>theo cách của người bản địa</h1>" +
      "<p>Trải nghiệm miệt vườn, đặc sản theo mùa, làng nghề và lịch trình gợi ý — tất cả trong một bản đồ.</p>" +
      '<form id="heroSearchForm" class="hero-search"><input type="search" placeholder="Tìm: chôm chôm, kẹo dừa, cù lao An Bình…"><button type="submit">Tìm</button></form>' +
      '<div class="hero-stats"><span>' + st.total + " điểm dữ liệu</span><span>" + st.phuong + " phường · " + st.xa + " xã</span><span>" + st.itineraries + " lịch trình</span></div>" +
      "</div></section>" +
      '<section class="weather-bar" id="weatherBar"><div class="weather-inner">⏳ Đang tải thời tiết...</div></section>' +
      (season.length ? section("🔥 Đang vào mùa tháng " + CURRENT_MONTH, "#/san-pham", grid(season, String(CURRENT_MONTH))) : "") +
      section("🌾 Trải nghiệm nổi bật", "#/du-lich", grid(exp)) +
      section("🍊 Đặc sản &amp; OCOP", "#/san-pham", grid(prod)) +
      section("🗺️ Lịch trình gợi ý", "#/lich-trinh", '<div class="grid itin">' + its.map(itinCard).join("") + "</div>") +
      section("📍 Khám phá theo khu vực", null, '<div class="region-grid">' + areas.map(areaCard).join("") + "</div>")
    );
  }

  // Catalog (Du lịch / Sản phẩm) — có bộ lọc tương tác.
  const CATALOG_CFG = {
    tourism: { title: "Du lịch", intro: "Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực khắp Vĩnh Long.", types: S.TOURISM_TYPES, typeChips: true, ocop: false, season: "all" },
    products: { title: "Sản phẩm địa phương", intro: "Đặc sản &amp; sản phẩm OCOP theo mùa — biết mùa nào ngon, mua ở đâu, ai sản xuất.", types: S.PRODUCT_TYPES, typeChips: false, ocop: true, season: String(CURRENT_MONTH) },
  };
  const catState = {};

  function typeChips(kind, st, cfg) {
    const list = [{ v: "all", t: "Tất cả" }].concat(cfg.types.map((t) => ({ v: t, t: S.TYPE_META[t].emoji + " " + S.TYPE_META[t].label })));
    return list.map((c) => '<button class="chip' + (c.v === st.type ? " active" : "") + '" data-type="' + c.v + '">' + c.t + "</button>").join("");
  }
  function seasonChips(st) {
    const list = [{ v: "all", t: "Tất cả mùa" }];
    for (let m = 1; m <= 12; m++) list.push({ v: String(m), t: "T" + m });
    list.push({ v: "flood", t: "🌊 Mùa nước nổi" });
    return list.map((c) => '<button class="chip season' + (c.v === st.season ? " active" : "") + '" data-season="' + c.v + '">' + c.t + "</button>").join("");
  }
  function ocopChip(st) { return '<button class="chip' + (st.ocop ? " active" : "") + '" data-ocop="1">⭐ Chỉ sản phẩm OCOP</button>'; }

  function renderCatalog(kind) {
    const cfg = CATALOG_CFG[kind];
    catState[kind] = { q: "", place: "all", type: "all", season: cfg.season, ocop: false };
    const st = catState[kind];
    return (
      '<section class="page"><div class="page-head"><h1>' + cfg.title + "</h1><p>" + cfg.intro + "</p></div>" +
      '<div class="controls">' +
      '<div class="search-row"><input type="search" id="catSearch" placeholder="Tìm trong ' + cfg.title.toLowerCase() + '…"><select id="catPlace">' + placeOptions("all") + "</select></div>" +
      (cfg.typeChips ? '<p class="control-label">Loại</p><div class="chip-row" id="catTypeChips">' + typeChips(kind, st, cfg) + "</div>" : "") +
      '<p class="control-label">Theo mùa</p><div class="chip-row" id="catSeasonChips">' + seasonChips(st) + "</div>" +
      (cfg.ocop ? '<div class="chip-row" id="catOcopChips" style="margin-top:8px">' + ocopChip(st) + "</div>" : "") +
      "</div>" +
      '<p class="result-meta" id="catMeta"></p><div id="catResults"></div></section>'
    );
  }

  function seasonCtx(sel) {
    if (sel === "all") return "";
    if (sel === "flood") return " · mùa nước nổi";
    return " · ưu tiên đang vào mùa T" + sel;
  }

  function updateCatalog(kind) {
    const cfg = CATALOG_CFG[kind], st = catState[kind];
    let list = S.query({
      types: st.type === "all" ? cfg.types : [st.type],
      placeId: st.place !== "all" ? st.place : null,
      season: st.season !== "all" ? st.season : null,
      q: st.q || null,
    });
    if (cfg.ocop && st.ocop) list = list.filter((e) => e.attributes && e.attributes.ocop);

    const results = document.getElementById("catResults");
    const meta = document.getElementById("catMeta");
    if (results) results.innerHTML = list.length ? grid(list, st.season) : '<p class="empty">Không có mục nào khớp bộ lọc. Thử bỏ bớt điều kiện.</p>';
    if (meta) meta.textContent = "Hiển thị " + list.length + " mục" + seasonCtx(st.season);
    const sc = document.getElementById("catSeasonChips"); if (sc) sc.innerHTML = seasonChips(st);
    const tc = document.getElementById("catTypeChips"); if (tc) tc.innerHTML = typeChips(kind, st, cfg);
    const oc = document.getElementById("catOcopChips"); if (oc) oc.innerHTML = ocopChip(st);
  }

  function bindCatalog(kind) {
    const st = catState[kind];
    const search = document.getElementById("catSearch");
    if (search) search.addEventListener("input", (e) => { st.q = e.target.value; updateCatalog(kind); });
    const place = document.getElementById("catPlace");
    if (place) place.addEventListener("change", (e) => { st.place = e.target.value; updateCatalog(kind); });
    const controls = document.querySelector(".page .controls");
    if (controls) controls.addEventListener("click", (e) => {
      const s = e.target.closest("[data-season]"); if (s) { st.season = s.dataset.season; updateCatalog(kind); return; }
      const t = e.target.closest("[data-type]"); if (t) { st.type = t.dataset.type; updateCatalog(kind); return; }
      const o = e.target.closest("[data-ocop]"); if (o) { st.ocop = !st.ocop; updateCatalog(kind); return; }
    });
    updateCatalog(kind);
  }

  function renderItineraries() {
    return (
      '<section class="page"><div class="page-head"><h1>Lịch trình gợi ý</h1><p>Những hành trình mẫu kết nối trải nghiệm, điểm tham quan và đặc sản theo từng khu vực. Bấm vào để xem từng điểm dừng.</p></div>' +
      '<div class="grid itin">' + S.itineraries.map(itinCard).join("") + "</div></section>"
    );
  }

  function renderItinerary(id) {
    const it = S.itinerary(id);
    if (!it) return notFound();
    const am = S.AREA_META[it.area] || { emoji: "📍", name: it.area };
    const steps = it.stops.map((s) => {
      const e = S.byId(s.id);
      if (!e) return "";
      const t = S.TYPE_META[e.type];
      return (
        '<li class="step"><div class="step-time">' + s.time + "</div>" +
        '<a class="step-card cat-' + t.cat + '" href="#/e/' + e.id + '">' +
        '<span class="step-emoji">' + t.emoji + "</span><div>" +
        '<span class="card-type">' + t.label + "</span><h3>" + e.name + "</h3>" +
        '<p class="summary">' + (e.summary || "") + "</p>" +
        (s.note ? '<p class="step-note">' + s.note + "</p>" : "") +
        "</div></a></li>"
      );
    }).join("");
    return (
      '<article class="page itinerary"><a class="back" href="#/lich-trinh">← Lịch trình</a>' +
      '<div class="page-head"><h1>' + it.title + "</h1><p>" + am.emoji + " KV " + am.name + " · " + it.duration + " · " + it.stops.length + " điểm dừng</p><p>" + it.summary + "</p></div>" +
      '<ol class="timeline">' + steps + "</ol></article>"
    );
  }

  function renderArea(areaKey) {
    const am = S.AREA_META[areaKey];
    if (!am) return notFound();

    // Danh sách xã/phường trong khu vực
    const ps = S.placesByArea(areaKey);
    const phuong = ps.filter((p) => p.level === "phuong").sort((a, b) => a.name.localeCompare(b.name, "vi"));
    const xa = ps.filter((p) => p.level === "xa").sort((a, b) => a.name.localeCompare(b.name, "vi"));

    function placeChip(p) {
      const contentCount = S.query({ placeId: p.id }).length;
      const label = p.name + (contentCount ? " (" + contentCount + ")" : "");
      return '<span class="chip place-chip' + (contentCount ? " has-content" : "") + '" title="' + p.legacyArea + ' (cũ)">' + label + "</span>";
    }

    let placeList = '<div class="place-list">';
    if (phuong.length) placeList += '<h3>Phường (' + phuong.length + ')</h3><div class="chip-row place-chips">' + phuong.map(placeChip).join("") + "</div>";
    if (xa.length) placeList += '<h3>Xã (' + xa.length + ')</h3><div class="chip-row place-chips">' + xa.map(placeChip).join("") + "</div>";
    placeList += "</div>";

    // Nội dung theo loại
    const groups = [
      ["experience", "🌾 Trải nghiệm"], ["attraction", "🛕 Tham quan"], ["accommodation", "🏡 Lưu trú"],
      ["craft_village", "🏺 Làng nghề"], ["product", "🍊 Đặc sản &amp; OCOP"], ["dish", "🍲 Ẩm thực"],
    ];
    let blocks = "";
    groups.forEach(([type, label]) => {
      const list = S.query({ types: [type], area: areaKey });
      if (list.length) blocks += section(label, null, grid(list));
    });
    const its = S.itineraries.filter((i) => i.area === areaKey);
    const itBlock = its.length ? section("🗺️ Lịch trình ở KV " + am.name, "#/lich-trinh", '<div class="grid itin">' + its.map(itinCard).join("") + "</div>") : "";

    return (
      '<section class="page"><div class="region-head"><span class="rc-emoji">' + am.emoji + "</span><div><h1>Khu vực " + am.name + "</h1><p>" + am.blurb + "</p></div></div>" +
      placeList + "</section>" +
      itBlock + blocks
    );
  }

  function renderDetail(id) {
    const e = S.byId(id);
    if (!e) return notFound();
    const t = S.TYPE_META[e.type] || { emoji: "•", label: e.type, cat: "place" };
    const a = e.attributes || {};
    const place = S.placeOf(id);
    const area = S.areaOf(id);
    const rels = S.related(id);
    const near = S.sameArea(id, 6);
    const conf = Math.round((e.confidence || 0) * 100);
    const src = e.source ? (e.source.url ? '<a href="' + e.source.url + '" target="_blank" rel="noopener">' + e.source.title + "</a>" : e.source.title) : "—";

    let seasonV = e.season ? S.seasonText(e.season) : "Quanh năm";
    if (e.season && e.season.peak && e.season.peak.length && !S.isYearRound(e.season)) seasonV += " · rộ " + S.monthRanges(e.season.peak);

    const areaLabel = area ? S.areaName(area) : "";
    const placeLabel = place ? place.name : "";
    const legacyLabel = place && place.legacyArea ? place.legacyArea + " (cũ)" : "";

    const relHtml = rels.length
      ? '<div class="rel-block"><h2>Liên quan</h2><ul class="rel-list">' +
        rels.map((r) => '<li><span class="rel-label">' + r.label + '</span><a href="#/e/' + r.other + '">' + S.byId(r.other).name + "</a></li>").join("") +
        "</ul></div>"
      : "";
    const nearHtml = near.length
      ? '<div class="rel-block"><h2>Khám phá thêm ở ' + (place ? place.name : "gần đây") + "</h2>" + grid(near) + "</div>"
      : "";
    const seasonBlock = e.season
      ? '<div class="rel-block"><h2>Mùa vụ</h2>' + monthStrip(e.season) +
        '<p class="ms-legend"><span class="ms-cell on"></span> có &nbsp;&nbsp; <span class="ms-cell on peak"></span> rộ</p></div>'
      : "";

    var imgHtml = "";
    if (e.images && e.images.length) {
      imgHtml = '<div class="detail-gallery">' +
        e.images.map(function(url, i) {
          return '<img src="' + escapeHtml(url) + '" alt="' + escapeHtml(e.name) + ' ' + (i+1) + '" class="detail-img" loading="lazy">';
        }).join("") + '</div>';
    }

    return (
      '<article class="detail">' + imgHtml + '<header class="detail-cover cat-' + t.cat + '"><div class="dc-inner">' +
      '<a class="back" href="#/' + (hubOf(e.type) || "") + '">← ' + t.label + "</a>" +
      '<span class="dc-emoji">' + t.emoji + "</span>" +
      '<span class="dc-type">' + t.label + "</span><h1>" + e.name + "</h1>" +
      '<p class="dc-place">📍 ' + placeLabel + (legacyLabel ? " · " + legacyLabel : "") + (areaLabel ? " · KV " + areaLabel : "") + "</p>" +
      "</div></header>" +
      '<div class="detail-body"><main class="detail-main">' +
      '<p class="lead">' + (e.summary || "") + "</p>" +
      seasonBlock + relHtml + nearHtml +
      '</main><aside class="detail-aside"><h2>Thông tin nhanh</h2>' +
      fact("Loại", t.label) +
      fact("Xã/Phường", placeLabel) +
      fact("Khu vực", areaLabel) +
      fact("Tham khảo", legacyLabel) +
      fact("Mùa vụ", seasonV) +
      fact("Chứng nhận", a.ocop ? "OCOP " + a.ocop : "") +
      fact("Giá tham khảo", a.gia) +
      fact("Thời lượng", a.thoiluong) +
      fact("Thời điểm", a.thoidiem) +
      '<div class="prov"><div class="prov-row">Độ tin cậy dữ liệu: <b>' + conf + "%</b>" +
      '<div class="confidence-bar"><i style="width:' + conf + '%"></i></div></div>' +
      '<div class="prov-row">Nguồn: ' + src + "</div><div class=\"prov-row\">Cập nhật: " + (e.updatedAt || "—") + "</div></div>" +
      "</aside></div></article>"
    );
  }

  function renderMap() {
    return (
      '<section class="page"><div class="page-head"><h1>Bản đồ Vĩnh Long</h1>' +
      '<p>Khám phá tất cả điểm đến, đặc sản và trải nghiệm trên bản đồ tương tác. Lọc theo loại hoặc khu vực, tìm kiếm nhanh.</p></div>' +
      '<div id="mapContainer"></div>' +
      '</section>'
    );
  }

  function initMap() {
    if (window.VL_Map && window.VL_Map.initMap) {
      window.VL_Map.initMap("mapContainer");
    } else {
      /* Fallback: basic map if map.js not loaded */
      var el = document.getElementById("mapContainer");
      if (!el || typeof L === "undefined") return;
      var map = L.map(el).setView([10.00, 106.15], 9);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 17,
      }).addTo(map);
    }
  }

  function renderSearch(q) {
    const results = S.search(q);
    return (
      '<section class="page"><div class="page-head"><h1>Kết quả tìm kiếm</h1><p>Từ khóa: "' + escapeHtml(q) + '" — ' + results.length + " kết quả</p></div>" +
      (results.length ? grid(results) : '<p class="empty">Không tìm thấy. Thử từ khóa khác như "dừa", "cam", "làng nghề".</p>') +
      "</section>"
    );
  }

  function notFound() {
    return '<section class="page"><div class="page-head"><h1>Không tìm thấy</h1><p>Mục bạn tìm không tồn tại. <a class="see-all" href="#/">← Về trang chủ</a></p></div></section>';
  }

  /* ===================== router ===================== */
  function parseHash() {
    let h = location.hash.replace(/^#/, "");
    if (!h || h === "/") return { name: "home" };
    const [path, qs] = h.split("?");
    const parts = path.split("/").filter(Boolean);
    const params = new URLSearchParams(qs || "");
    switch (parts[0]) {
      case "du-lich": return { name: "tourism" };
      case "san-pham": return { name: "products" };
      case "lich-trinh": return parts[1] ? { name: "itinerary", id: decodeURIComponent(parts[1]) } : { name: "itineraries" };
      case "ban-do": return { name: "map" };
      case "khu-vuc": return { name: "area", area: decodeURIComponent(parts[1] || "") };
      case "vung": return { name: "area", area: decodeURIComponent(parts[1] || "") };
      case "e": return { name: "detail", id: decodeURIComponent(parts[1] || "") };
      case "tim": return { name: "search", q: params.get("q") || "" };
      case "cong-dong": return { name: "community" };
      case "bai-viet": return { name: "post-detail", id: decodeURIComponent(parts[1] || "") };
      case "nguoi-dung": return { name: "user-profile", id: decodeURIComponent(parts[1] || "") };
      case "danh-gia": return { name: "entity-feed", id: decodeURIComponent(parts[1] || "") };
      case "chi-tiet": return { name: "detail", id: decodeURIComponent(parts[1] || "") };
      default: return { name: "home" };
    }
  }

  function setActiveNav(name) {
    const map = { home: "/", tourism: "du-lich", products: "san-pham", itineraries: "lich-trinh", itinerary: "lich-trinh", map: "ban-do", community: "cong-dong" };
    const cur = map[name];
    document.querySelectorAll(".main-nav a").forEach((a) => a.classList.toggle("active", a.getAttribute("data-nav") === cur));
  }

  function route() {
    const r = parseHash();
    const app = document.getElementById("app");
    let html = "";
    if (r.name === "home") html = renderHome();
    else if (r.name === "tourism") html = renderCatalog("tourism");
    else if (r.name === "products") html = renderCatalog("products");
    else if (r.name === "itineraries") html = renderItineraries();
    else if (r.name === "itinerary") html = renderItinerary(r.id);
    else if (r.name === "map") html = renderMap();
    else if (r.name === "area") html = renderArea(r.area);
    else if (r.name === "detail") html = renderDetail(r.id);
    else if (r.name === "search") html = renderSearch(r.q);
    else if (r.name === "community" || r.name === "post-detail" || r.name === "user-profile" || r.name === "entity-feed") {
      // MXH routes — handled by feed.js (async rendering)
      app.innerHTML = "";
      window.scrollTo(0, 0);
      setActiveNav(r.name);
      if (window._feedScrollHandler) window.removeEventListener("scroll", window._feedScrollHandler);
      if (r.name === "community") window._vl360Feed.renderFeedPage(app, {});
      else if (r.name === "post-detail") window._vl360Feed.renderPostDetail(app, r.id);
      else if (r.name === "user-profile") window._vl360Feed.renderUserProfile(app, r.id);
      else if (r.name === "entity-feed") window._vl360Feed.renderEntityFeed(app, r.id);
      return;
    }
    app.innerHTML = html;
    if (r.name === "home") setTimeout(loadWeather, 100);
    window.scrollTo(0, 0);
    setActiveNav(r.name);
    if (r.name === "map") initMap();
    if (r.name === "tourism") bindCatalog("tourism");
    if (r.name === "products") bindCatalog("products");
  }

  /* ===================== init ===================== */
  document.addEventListener("submit", (e) => {
    if (e.target.id === "globalSearchForm" || e.target.id === "heroSearchForm") {
      e.preventDefault();
      const input = e.target.querySelector('input[type="search"]');
      const v = (input ? input.value : "").trim();
      location.hash = v ? "#/tim?q=" + encodeURIComponent(v) : "#/";
    }
  });
  // Weather widget
  function loadWeather() {
    var bar = document.getElementById("weatherBar");
    if (!bar) return;
    fetch("http://localhost:8360/weather/all")
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (!data.areas) { bar.style.display = "none"; return; }
        var html = '<div class="weather-inner">';
        data.areas.forEach(function(w) {
          html += '<div class="weather-card">' +
            '<span class="wc-area">' + escapeHtml(w.area_name) + '</span>' +
            '<span class="wc-temp">' + w.temp_c + '°C</span>' +
            '<span class="wc-desc">' + escapeHtml(w.description) + '</span>' +
            '</div>';
        });
        html += '</div>';
        bar.innerHTML = html;
      })
      .catch(function() { if (bar) bar.style.display = "none"; });
  }

  window.addEventListener("hashchange", route);
  route();
})();

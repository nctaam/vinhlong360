/*
 * vinhlong360 — Interactive Map (Leaflet + MarkerCluster).
 *
 * Reads data via window.Store. Provides:
 *   initMap(containerId)      — render full interactive map
 *   showEntityOnMap(entityId) — fly to entity & open popup
 *   showRoute(entityIds)      — draw polyline for itinerary
 *
 * Loaded as a regular <script> tag; no build step needed.
 * CDN deps: Leaflet 1.9.4 (already in index.html), MarkerCluster (injected).
 */
(function () {
  "use strict";

  /* Lazy reference: resolved on first use so load order with data.js/store.js is flexible. */
  var S = null;
  function ensureStore() {
    if (!S) S = window.Store;
    return S;
  }

  /* ===================== constants ===================== */

  var TYPE_COLORS = {
    attraction:    "#2563eb",  /* blue */
    experience:    "#2563eb",  /* blue — grouped with attraction */
    nature:        "#16a34a",  /* green */
    product:       "#ea580c",  /* orange */
    dish:          "#dc2626",  /* red */
    craft_village: "#9333ea",  /* purple */
    event:         "#ca8a04",  /* gold */
    history:       "#92400e",  /* brown */
    accommodation: "#0891b2",  /* cyan */
    organization:  "#6b7280",  /* gray */
  };

  var TYPE_LABELS = {
    attraction:    "Tham quan",
    experience:    "Trải nghiệm",
    nature:        "Thiên nhiên",
    product:       "Đặc sản",
    dish:          "Ẩm thực",
    craft_village: "Làng nghề",
    event:         "Sự kiện",
    history:       "Lịch sử",
    accommodation: "Lưu trú",
    organization:  "Tổ chức",
  };

  /* Area center fallbacks (used when a place has no coords) */
  var AREA_CENTERS = {
    "vinh-long": [10.2539, 105.9722],
    "ben-tre":   [10.2433, 106.3756],
    "tra-vinh":  [9.9347,  106.3454],
  };

  /* Fallback coordinates for places without coords, keyed by placeId.
   * These are approximate positions within each ward/commune. */
  var PLACE_FALLBACKS = {
    /* Vinh Long */
    "p-long-chau":      [10.2539, 105.9722],
    "p-thanh-duc":      [10.2480, 105.9650],
    "p-phuoc-hau":      [10.2560, 105.9800],
    "p-tan-hanh":       [10.2650, 105.9580],
    "p-tan-ngai":       [10.2700, 105.9550],
    "p-binh-minh":      [10.0780, 105.8530],
    "p-cai-von":        [10.0600, 105.8560],
    "p-dong-thanh":     [10.0650, 105.8400],
    "xa-cai-nhum":      [10.1400, 106.0100],
    "xa-tan-long-hoi":  [10.1500, 106.0000],
    "xa-nhon-phu":      [10.1300, 106.0300],
    "xa-binh-phuoc":    [10.1350, 106.0200],
    "xa-an-binh":       [10.2200, 106.0000],
    "xa-long-ho":       [10.1950, 105.9900],
    "xa-phu-quoi":      [10.2050, 106.0050],
    "xa-quoi-thien":    [10.0800, 106.0800],
    "xa-trung-thanh":   [10.0500, 106.0900],
    "xa-trung-ngai":    [10.0600, 106.0700],
    "xa-quoi-an":       [10.0700, 106.1000],
    "xa-trung-hiep":    [10.0550, 106.0600],
    "xa-hieu-phung":    [10.0450, 106.0500],
    "xa-hieu-thanh":    [10.0400, 106.0400],
    "xa-luc-si-thanh":  [10.0350, 106.0700],
    "xa-tra-on":        [9.9700, 105.9300],
    "xa-tra-con":       [10.0600, 105.9500],
    "xa-vinh-xuan":     [9.9600, 105.9500],
    "xa-hoa-binh":      [10.0800, 105.9600],
    "xa-hoa-hiep":      [10.0900, 105.9400],
    "xa-tam-binh":      [10.0700, 105.9700],
    "xa-ngai-tu":       [10.0600, 105.9800],
    "xa-song-phu":      [10.0500, 105.9500],
    "xa-cai-ngang":     [10.0450, 105.9600],
    "xa-tan-quoi":      [10.1800, 105.9500],
    "xa-tan-luoc":      [10.1700, 105.9400],
    "xa-my-thuan":      [10.1900, 105.9300],
    /* Ben Tre */
    "p-ben-tre":        [10.2400, 106.3800],
    "p-an-hoi":         [10.2350, 106.3750],
    "p-phu-khuong":     [10.2450, 106.3700],
    "p-son-dong":       [10.2500, 106.3850],
    "p-phu-tan":        [10.2300, 106.3900],
    "xa-phu-tuc":       [10.2700, 106.4100],
    "xa-giao-long":     [10.2600, 106.4000],
    "xa-tien-thuy":     [10.2550, 106.4200],
    "xa-tan-phu":       [10.3100, 106.4200],
    "xa-phu-phung":     [10.2500, 106.1700],
    "xa-cho-lach":      [10.2400, 106.1600],
    "xa-vinh-thanh":    [10.2300, 106.1500],
    "xa-hung-khanh-trung": [10.2200, 106.1800],
    "xa-phuoc-my-trung":   [10.1400, 106.3900],
    "xa-tan-thanh-binh":   [10.1500, 106.3800],
    "xa-nhuan-phu-tan":    [10.1300, 106.4000],
    "xa-dong-khoi":     [10.1100, 106.3500],
    "xa-mo-cay":        [10.1000, 106.3700],
    "xa-thanh-thoi":    [10.0900, 106.3600],
    "xa-an-dinh":       [10.1050, 106.3800],
    "xa-huong-my":      [10.0850, 106.3500],
    "xa-dai-dien":      [9.9700, 106.4300],
    "xa-quoi-dien":     [9.9600, 106.4200],
    "xa-thanh-phu":     [9.9500, 106.4400],
    "xa-an-qui":        [9.9400, 106.4500],
    "xa-thanh-hai":     [9.9200, 106.4600],
    "xa-thanh-phong":   [9.9100, 106.4700],
    "xa-tan-thuy":      [10.1500, 106.5000],
    "xa-bao-thanh":     [10.1400, 106.5100],
    "xa-ba-tri":        [10.0400, 106.5800],
    "xa-tan-xuan":      [10.0300, 106.5700],
    "xa-giong-trom":    [10.1600, 106.4400],
    "xa-hung-nhuong":   [10.1700, 106.4300],
    "xa-tan-hao":       [10.1500, 106.4500],
    "xa-phuoc-long":    [10.1400, 106.4600],
    "xa-luong-phu":     [10.1800, 106.4200],
    "xa-chau-hoa":      [10.1900, 106.4100],
    "xa-luong-hoa":     [10.2000, 106.4000],
    /* Tra Vinh */
    "p-tra-vinh":       [9.9350, 106.3450],
    "p-long-duc":       [9.9200, 106.3300],
    "p-nguyet-hoa":     [9.9400, 106.3500],
    "p-hoa-thuan":      [9.9300, 106.3400],
    "p-duyen-hai":      [9.6300, 106.4900],
    "p-truong-long-hoa":[9.6400, 106.5000],
    "xa-long-huu":      [9.6200, 106.4800],
    "xa-cang-long":     [9.9800, 106.2100],
    "xa-an-truong":     [9.9700, 106.2000],
    "xa-tan-an":        [9.9900, 106.2200],
    "xa-nhi-long":      [9.9600, 106.2300],
    "xa-binh-phu":      [9.9500, 106.2400],
    "xa-chau-thanh":    [9.9400, 106.2800],
    "xa-song-loc":      [9.9300, 106.2900],
    "xa-hung-my":       [9.9200, 106.2700],
    "xa-cau-ke":        [9.8700, 106.1200],
    "xa-phong-thanh":   [9.8800, 106.1300],
    "xa-an-phu-tan":    [9.8600, 106.1100],
    "xa-tam-ngai":      [9.8500, 106.1000],
    "xa-tieu-can":      [9.8100, 106.2600],
    "xa-tan-hoa":       [9.8200, 106.2700],
    "xa-hung-hoa":      [9.8000, 106.2500],
    "xa-tap-ngai":      [9.7900, 106.2400],
    "xa-cau-ngang":     [9.7800, 106.3500],
    "xa-my-long":       [9.7700, 106.3600],
    "xa-vinh-kim":      [9.7600, 106.3700],
    "xa-nhi-truong":    [9.7500, 106.3800],
    "xa-hiep-my":       [9.7400, 106.3400],
    "xa-tra-cu":        [9.6800, 106.1500],
    "xa-dai-an":        [9.6700, 106.1600],
    "xa-luu-nghiep-anh":[9.6600, 106.1700],
    "xa-ham-giang":     [9.6500, 106.1400],
    "xa-long-hiep":     [9.6900, 106.1300],
    "xa-tap-son":       [9.7000, 106.1200],
  };

  /* ===================== state ===================== */

  var map = null;
  var markerClusterGroup = null;
  var markerLookup = {};       /* entityId -> L.Marker */
  var entityCoords = {};       /* entityId -> [lat, lon] */
  var routeLayer = null;
  var allEntityMarkers = [];   /* { marker, entity, coords } */
  var filterState = {
    types: {},  /* type -> boolean (true = visible) */
    area: "all",
    searchQuery: "",
  };

  /* ===================== CSS injection ===================== */

  function injectCSS() {
    if (document.getElementById("vl360-map-css")) return;
    var style = document.createElement("style");
    style.id = "vl360-map-css";
    style.textContent = [
      /* MarkerCluster overrides */
      ".marker-cluster-small { background-color: rgba(37,99,235,0.25); }",
      ".marker-cluster-small div { background-color: rgba(37,99,235,0.6); }",
      ".marker-cluster-medium { background-color: rgba(234,88,12,0.25); }",
      ".marker-cluster-medium div { background-color: rgba(234,88,12,0.6); }",
      ".marker-cluster-large { background-color: rgba(220,38,38,0.25); }",
      ".marker-cluster-large div { background-color: rgba(220,38,38,0.6); }",

      /* Map controls panel */
      ".vl-map-controls { padding: 12px 0; display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-start; }",
      ".vl-map-filter-group { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }",
      ".vl-map-filter-group label { font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 999px; border: 1px solid #d1d5db; background: #fff; transition: all 0.15s; user-select: none; white-space: nowrap; }",
      ".vl-map-filter-group label:hover { border-color: #9ca3af; }",
      ".vl-map-filter-group label.active { border-color: currentColor; font-weight: 600; }",
      ".vl-map-filter-group label input { display: none; }",
      ".vl-map-filter-group label .type-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }",
      ".vl-map-filter-group select { font-size: 0.85rem; padding: 5px 10px; border-radius: 999px; border: 1px solid #d1d5db; background: #fff; cursor: pointer; }",
      ".vl-map-search { position: relative; flex: 1; min-width: 180px; max-width: 320px; }",
      ".vl-map-search input { width: 100%; font-size: 0.85rem; padding: 6px 12px; border-radius: 999px; border: 1px solid #d1d5db; outline: none; box-sizing: border-box; }",
      ".vl-map-search input:focus { border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37,99,235,0.15); }",
      ".vl-map-search-results { position: absolute; top: 100%; left: 0; right: 0; background: #fff; border: 1px solid #d1d5db; border-radius: 8px; max-height: 200px; overflow-y: auto; z-index: 1000; margin-top: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); display: none; }",
      ".vl-map-search-results.open { display: block; }",
      ".vl-map-search-results button { display: block; width: 100%; text-align: left; padding: 8px 12px; border: none; background: none; cursor: pointer; font-size: 0.85rem; }",
      ".vl-map-search-results button:hover { background: #f3f4f6; }",
      ".vl-map-search-results button .sr-type { font-size: 0.75rem; color: #6b7280; margin-left: 6px; }",

      /* Legend */
      ".vl-map-legend { display: flex; flex-wrap: wrap; gap: 14px; padding: 8px 0; font-size: 0.82rem; color: #4b5563; }",
      ".vl-map-legend-item { display: flex; align-items: center; gap: 5px; }",
      ".vl-map-legend-item i { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }",

      /* Popup */
      ".vl-map-popup { min-width: 180px; max-width: 260px; }",
      ".vl-map-popup h4 { margin: 0 0 4px; font-size: 0.95rem; line-height: 1.3; }",
      ".vl-map-popup .popup-badge { display: inline-block; font-size: 0.72rem; padding: 1px 7px; border-radius: 999px; color: #fff; margin-bottom: 6px; }",
      ".vl-map-popup p { margin: 0 0 6px; font-size: 0.82rem; color: #374151; line-height: 1.4; }",
      ".vl-map-popup .popup-link { font-size: 0.82rem; color: #2563eb; text-decoration: none; font-weight: 500; }",
      ".vl-map-popup .popup-link:hover { text-decoration: underline; }",

      /* Route */
      ".vl-route-label { background: transparent; border: none; font-size: 0.75rem; font-weight: 700; color: #1e40af; white-space: nowrap; text-shadow: 0 0 3px #fff, 0 0 3px #fff; }",

      /* Responsive container */
      ".vl-map-wrap { width: 100%; }",
      ".vl-map-wrap #mapContainer { height: 500px; }",
      "@media (max-width: 640px) {",
      "  .vl-map-wrap #mapContainer { height: 300px; }",
      "  .vl-map-controls { gap: 6px; }",
      "  .vl-map-search { min-width: 140px; max-width: none; flex-basis: 100%; }",
      "}",
    ].join("\n");
    document.head.appendChild(style);
  }

  /* ===================== CDN loading ===================== */

  function loadMarkerCluster(cb) {
    if (window.L && L.MarkerClusterGroup) { cb(); return; }

    var cssHref = "https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css";
    var cssDefaultHref = "https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css";
    var jsHref = "https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js";

    function loadCSS(href) {
      if (document.querySelector('link[href="' + href + '"]')) return;
      var link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      link.crossOrigin = "";
      document.head.appendChild(link);
    }

    loadCSS(cssHref);
    loadCSS(cssDefaultHref);

    if (document.querySelector('script[src="' + jsHref + '"]')) {
      /* Script tag exists but may still be loading */
      var check = setInterval(function () {
        if (L.MarkerClusterGroup) { clearInterval(check); cb(); }
      }, 50);
      return;
    }

    var script = document.createElement("script");
    script.src = jsHref;
    script.crossOrigin = "";
    script.onload = cb;
    script.onerror = function () { console.warn("MarkerCluster CDN failed; markers will not cluster."); cb(); };
    document.head.appendChild(script);
  }

  /* ===================== coordinate helpers ===================== */

  /** Resolve coordinates for a place by id. Returns [lat, lon] or null. */
  function placeCoords(placeId) {
    if (!placeId) return null;
    var place = S.byId(placeId);
    if (place && place.coords) return place.coords;
    if (PLACE_FALLBACKS[placeId]) return PLACE_FALLBACKS[placeId];

    /* Derive from area center */
    if (place && place.area && AREA_CENTERS[place.area]) {
      return AREA_CENTERS[place.area];
    }
    return null;
  }

  /** Get coords for an entity. Prefers the entity's OWN precise coordinates;
   *  falls back to place-center + deterministic jitter only when absent. */
  function entityPosition(entity) {
    /* Precise GPS pin if the entity carries its own coordinates. */
    if (entity.coords && entity.coords.length === 2 &&
        typeof entity.coords[0] === "number" && typeof entity.coords[1] === "number") {
      return [entity.coords[0], entity.coords[1]];
    }
    var coords = placeCoords(entity.placeId);
    if (!coords) {
      /* No placeId at all: use generic center */
      coords = AREA_CENTERS["vinh-long"];
    }
    /* Add deterministic jitter based on entity id hash */
    var hash = simpleHash(entity.id);
    var jitterLat = ((hash % 200) - 100) / 10000;  /* +/- 0.01 */
    var jitterLon = (((hash >> 8) % 200) - 100) / 10000;
    return [coords[0] + jitterLat, coords[1] + jitterLon];
  }

  function simpleHash(str) {
    var h = 0;
    for (var i = 0; i < str.length; i++) {
      h = ((h << 5) - h + str.charCodeAt(i)) | 0;
    }
    return Math.abs(h);
  }

  /** Determine area for an entity (for area filtering). */
  function entityArea(entity) {
    return S.areaOf(entity.id) || null;
  }

  /* ===================== marker creation ===================== */

  function createMarkerIcon(type) {
    var color = TYPE_COLORS[type] || "#6b7280";
    return L.divIcon({
      className: "vl-entity-marker",
      html: '<div style="' +
        "width:14px;height:14px;border-radius:50%;" +
        "background:" + color + ";" +
        "border:2px solid #fff;" +
        "box-shadow:0 1px 4px rgba(0,0,0,0.3);" +
        '"></div>',
      iconSize: [14, 14],
      iconAnchor: [7, 7],
      popupAnchor: [0, -10],
    });
  }

  function createPopupContent(entity) {
    var color = TYPE_COLORS[entity.type] || "#6b7280";
    var label = TYPE_LABELS[entity.type] || entity.type;
    var summary = entity.summary || "";
    if (summary.length > 100) summary = summary.substring(0, 100) + "...";

    var place = S.byId(entity.placeId);
    var placeLine = place ? '<p style="font-size:0.78rem;color:#6b7280;margin:0 0 4px;">📍 ' + escapeHtml(place.alias || place.name) + "</p>" : "";

    return '<div class="vl-map-popup">' +
      '<h4>' + escapeHtml(entity.name) + "</h4>" +
      '<span class="popup-badge" style="background:' + color + '">' + escapeHtml(label) + "</span>" +
      placeLine +
      "<p>" + escapeHtml(summary) + "</p>" +
      '<a class="popup-link" href="#/e/' + entity.id + '">Xem chi tiết →</a>' +
      "</div>";
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  /* ===================== filter logic ===================== */

  function shouldShowEntity(entry) {
    var entity = entry.entity;

    /* Type filter */
    if (filterState.types[entity.type] === false) return false;

    /* Area filter */
    if (filterState.area !== "all") {
      var area = entityArea(entity);
      if (area !== filterState.area) return false;
    }

    return true;
  }

  function applyFilters() {
    if (!markerClusterGroup) return;
    markerClusterGroup.clearLayers();
    allEntityMarkers.forEach(function (entry) {
      if (shouldShowEntity(entry)) {
        markerClusterGroup.addLayer(entry.marker);
      }
    });
  }

  /* ===================== controls rendering ===================== */

  function renderControls(container) {
    var controls = document.createElement("div");
    controls.className = "vl-map-controls";

    /* -- Type filter checkboxes -- */
    var typeGroup = document.createElement("div");
    typeGroup.className = "vl-map-filter-group";

    /* Collect types actually present in entities */
    var presentTypes = {};
    var cardTypes = S.CARD_TYPES || ["experience", "product", "dish", "craft_village", "attraction", "accommodation"];
    cardTypes.forEach(function (t) { presentTypes[t] = true; });

    Object.keys(presentTypes).forEach(function (type) {
      filterState.types[type] = true;
      var lbl = document.createElement("label");
      lbl.className = "active";
      var cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = true;
      cb.dataset.type = type;
      var dot = document.createElement("span");
      dot.className = "type-dot";
      dot.style.background = TYPE_COLORS[type] || "#6b7280";
      lbl.appendChild(cb);
      lbl.appendChild(dot);
      lbl.appendChild(document.createTextNode(" " + (TYPE_LABELS[type] || type)));

      cb.addEventListener("change", function () {
        filterState.types[type] = cb.checked;
        lbl.className = cb.checked ? "active" : "";
        applyFilters();
      });

      typeGroup.appendChild(lbl);
    });

    controls.appendChild(typeGroup);

    /* -- Area filter dropdown -- */
    var areaGroup = document.createElement("div");
    areaGroup.className = "vl-map-filter-group";
    var areaSelect = document.createElement("select");
    var areas = [
      { v: "all", t: "Tất cả khu vực" },
      { v: "vinh-long", t: "🍊 Vĩnh Long" },
      { v: "ben-tre", t: "🥥 Bến Tre" },
      { v: "tra-vinh", t: "🛕 Trà Vinh" },
    ];
    areas.forEach(function (a) {
      var opt = document.createElement("option");
      opt.value = a.v;
      opt.textContent = a.t;
      areaSelect.appendChild(opt);
    });
    areaSelect.addEventListener("change", function () {
      filterState.area = areaSelect.value;
      applyFilters();
      if (filterState.area !== "all" && AREA_CENTERS[filterState.area]) {
        map.flyTo(AREA_CENTERS[filterState.area], 11, { duration: 0.8 });
      } else {
        map.flyTo([10.00, 106.15], 9, { duration: 0.8 });
      }
    });
    areaGroup.appendChild(areaSelect);
    controls.appendChild(areaGroup);

    /* -- Search box -- */
    var searchWrap = document.createElement("div");
    searchWrap.className = "vl-map-search";
    var searchInput = document.createElement("input");
    searchInput.type = "search";
    searchInput.placeholder = "Tìm địa điểm...";
    searchInput.setAttribute("aria-label", "Tìm địa điểm trên bản đồ");

    var searchResults = document.createElement("div");
    searchResults.className = "vl-map-search-results";

    searchInput.addEventListener("input", function () {
      var q = searchInput.value.trim().toLowerCase();
      if (q.length < 2) { searchResults.className = "vl-map-search-results"; return; }

      var matches = S.search(q).slice(0, 8);
      if (!matches.length) { searchResults.className = "vl-map-search-results"; return; }

      searchResults.innerHTML = "";
      matches.forEach(function (entity) {
        var btn = document.createElement("button");
        btn.type = "button";
        var typeLbl = TYPE_LABELS[entity.type] || entity.type;
        btn.innerHTML = escapeHtml(entity.name) + '<span class="sr-type">' + escapeHtml(typeLbl) + "</span>";
        btn.addEventListener("click", function () {
          searchResults.className = "vl-map-search-results";
          searchInput.value = entity.name;
          showEntityOnMap(entity.id);
        });
        searchResults.appendChild(btn);
      });
      searchResults.className = "vl-map-search-results open";
    });

    /* Close search results on outside click */
    document.addEventListener("click", function (e) {
      if (!searchWrap.contains(e.target)) {
        searchResults.className = "vl-map-search-results";
      }
    });

    searchWrap.appendChild(searchInput);
    searchWrap.appendChild(searchResults);
    controls.appendChild(searchWrap);

    container.appendChild(controls);
  }

  function renderLegend(container) {
    var legend = document.createElement("div");
    legend.className = "vl-map-legend";

    var types = S.CARD_TYPES || ["experience", "product", "dish", "craft_village", "attraction", "accommodation"];
    types.forEach(function (type) {
      var item = document.createElement("span");
      item.className = "vl-map-legend-item";
      var dot = document.createElement("i");
      dot.style.background = TYPE_COLORS[type] || "#6b7280";
      item.appendChild(dot);
      item.appendChild(document.createTextNode(" " + (TYPE_LABELS[type] || type)));
      legend.appendChild(item);
    });

    container.appendChild(legend);
  }

  /* ===================== public API ===================== */

  /**
   * Initialize the interactive map inside the given container element.
   * @param {string} containerId — ID of the DOM element to hold the map
   */
  function initMap(containerId) {
    ensureStore();
    if (!S) { console.warn("Store not available. Cannot initialize map."); return; }
    if (typeof L === "undefined") {
      console.warn("Leaflet not loaded. Cannot initialize map.");
      return;
    }

    injectCSS();

    var container = document.getElementById(containerId);
    if (!container) {
      console.warn("Map container #" + containerId + " not found.");
      return;
    }

    /* Wrap the container with controls, map element, and legend */
    var wrap = document.createElement("div");
    wrap.className = "vl-map-wrap";

    /* Insert wrap before container, then move container into it */
    container.parentNode.insertBefore(wrap, container);

    /* Controls above the map */
    renderControls(wrap);

    /* Map element */
    wrap.appendChild(container);

    /* Legend below the map */
    renderLegend(wrap);

    loadMarkerCluster(function () {
      buildMap(container);
    });
  }

  function buildMap(el) {
    /* Tear down previous map if any */
    if (map) {
      map.remove();
      map = null;
    }

    map = L.map(el, {
      zoomControl: false,
      scrollWheelZoom: true,
      tap: true,           /* touch support */
      touchZoom: true,
      dragging: true,
    }).setView([10.00, 106.15], 9);

    /* Zoom control — top-right for mobile friendliness */
    L.control.zoom({ position: "topright" }).addTo(map);

    /* Scale bar */
    L.control.scale({ imperial: false, position: "bottomleft" }).addTo(map);

    /* OpenStreetMap tile layer */
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18,
    }).addTo(map);

    /* Initialize marker cluster group */
    if (L.MarkerClusterGroup) {
      markerClusterGroup = new L.MarkerClusterGroup({
        maxClusterRadius: 45,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        disableClusteringAtZoom: 15,
      });
    } else {
      /* Fallback: plain layer group */
      markerClusterGroup = L.layerGroup();
    }

    /* Build entity markers */
    allEntityMarkers = [];
    markerLookup = {};
    entityCoords = {};

    var cardTypes = S.CARD_TYPES || ["experience", "product", "dish", "craft_village", "attraction", "accommodation"];
    var entities = S.entities.filter(function (e) {
      return cardTypes.indexOf(e.type) !== -1;
    });

    entities.forEach(function (entity) {
      var pos = entityPosition(entity);
      entityCoords[entity.id] = pos;

      var marker = L.marker(pos, {
        icon: createMarkerIcon(entity.type),
        title: entity.name,
        riseOnHover: true,
      });

      marker.bindPopup(createPopupContent(entity), {
        maxWidth: 280,
        className: "vl-popup-wrapper",
      });

      markerLookup[entity.id] = marker;
      allEntityMarkers.push({
        marker: marker,
        entity: entity,
        coords: pos,
      });
    });

    /* Initialize all type filters as true */
    cardTypes.forEach(function (t) {
      if (filterState.types[t] === undefined) filterState.types[t] = true;
    });

    /* Apply initial filter (shows all) */
    applyFilters();
    map.addLayer(markerClusterGroup);

    /* Fix map sizing after container becomes visible */
    setTimeout(function () { map.invalidateSize(); }, 200);
  }

  /**
   * Fly to an entity on the map and open its popup.
   * @param {string} entityId
   */
  function showEntityOnMap(entityId) {
    if (!map) return;

    var marker = markerLookup[entityId];
    if (!marker) return;

    var coords = entityCoords[entityId];
    if (!coords) return;

    /* Make sure the entity's type filter is on */
    var entity = S.byId(entityId);
    if (entity && filterState.types[entity.type] === false) {
      filterState.types[entity.type] = true;
      applyFilters();
      /* Update the checkbox UI */
      var cb = document.querySelector('.vl-map-filter-group input[data-type="' + entity.type + '"]');
      if (cb) {
        cb.checked = true;
        cb.parentElement.className = "active";
      }
    }

    /* Ensure marker is visible in cluster */
    if (markerClusterGroup.hasLayer && !markerClusterGroup.hasLayer(marker)) {
      markerClusterGroup.addLayer(marker);
    }

    map.flyTo(coords, 14, { duration: 1.0 });

    setTimeout(function () {
      /* Spiderfy cluster if needed */
      if (markerClusterGroup.zoomToShowLayer) {
        markerClusterGroup.zoomToShowLayer(marker, function () {
          marker.openPopup();
        });
      } else {
        marker.openPopup();
      }
    }, 1100);
  }

  /**
   * Draw a polyline route connecting the given entity IDs.
   * Useful for visualizing itinerary stops on the map.
   * @param {string[]} entityIds — ordered list of entity IDs
   */
  function showRoute(entityIds) {
    if (!map) return;

    /* Remove previous route */
    clearRoute();

    if (!entityIds || entityIds.length < 2) return;

    var latlngs = [];
    var validIds = [];

    entityIds.forEach(function (id) {
      var coords = entityCoords[id];
      if (!coords) {
        /* Try to compute coords even if not in markerLookup */
        var entity = S.byId(id);
        if (entity) {
          coords = entityPosition(entity);
          entityCoords[id] = coords;
        }
      }
      if (coords) {
        latlngs.push(coords);
        validIds.push(id);
      }
    });

    if (latlngs.length < 2) return;

    routeLayer = L.layerGroup().addTo(map);

    /* Polyline */
    var polyline = L.polyline(latlngs, {
      color: "#1e40af",
      weight: 3,
      opacity: 0.7,
      dashArray: "8, 6",
      lineCap: "round",
    });
    routeLayer.addLayer(polyline);

    /* Number labels at each stop */
    validIds.forEach(function (id, idx) {
      var coords = entityCoords[id];
      var entity = S.byId(id);
      var labelText = (idx + 1) + ". " + (entity ? entity.name : id);
      var label = L.marker(coords, {
        icon: L.divIcon({
          className: "vl-route-label",
          html: '<span style="' +
            "background:#1e40af;color:#fff;padding:2px 7px;border-radius:10px;" +
            "font-size:0.72rem;white-space:nowrap;display:inline-block;" +
            "box-shadow:0 1px 3px rgba(0,0,0,0.2);" +
            '">' + escapeHtml(labelText) + "</span>",
          iconSize: null,
          iconAnchor: [0, -12],
        }),
        interactive: false,
      });
      routeLayer.addLayer(label);
    });

    /* Fit bounds to show entire route */
    map.fitBounds(polyline.getBounds().pad(0.15), { maxZoom: 13, duration: 0.8 });
  }

  /**
   * Remove the currently displayed route.
   */
  function clearRoute() {
    if (routeLayer && map) {
      map.removeLayer(routeLayer);
      routeLayer = null;
    }
  }

  /**
   * Get the Leaflet map instance (for advanced external use).
   * @returns {L.Map|null}
   */
  function getMap() {
    return map;
  }

  /* ===================== expose on window ===================== */

  window.VL_Map = {
    initMap: initMap,
    showEntityOnMap: showEntityOnMap,
    showRoute: showRoute,
    clearRoute: clearRoute,
    getMap: getMap,
  };

  /* Also expose standalone functions for convenience */
  window.initInteractiveMap = initMap;
  window.showEntityOnMap = showEntityOnMap;
  window.showRoute = showRoute;

})();

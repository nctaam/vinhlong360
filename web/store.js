/*
 * vinhlong360 — STORE (lớp truy vấn dữ liệu, KHÔNG đụng DOM).
 *
 * Hybrid: fetch từ /api/* (dynamic) → fallback về window.VL_DATA (static/offline).
 * Mô hình 2 cấp: tỉnh → 124 xã/phường. Các "khu vực" (vinh-long, ben-tre,
 * tra-vinh) là nhóm tham chiếu theo tỉnh cũ, không phải đơn vị hành chính.
 */
(function () {
  var entities = [];
  var relationships = [];
  var itineraries = [];
  var byId = {};
  var ALL_MONTHS = [1,2,3,4,5,6,7,8,9,10,11,12];
  var _ready = false;
  var _readyCallbacks = [];

  var API_BASE = window.VL_API || '';

  function _initData(data) {
    entities = data.entities || [];
    relationships = data.relationships || [];
    itineraries = data.itineraries || [];
    byId = {};
    entities.forEach(function(e) { byId[e.id] = e; });
    _ready = true;
    _readyCallbacks.forEach(function(cb) { try { cb(); } catch(e) {} });
    _readyCallbacks = [];
  }

  function _fetchAPI() {
    return Promise.all([
      fetch(API_BASE + '/api/entities?limit=2000').then(function(r) { return r.ok ? r.json() : Promise.reject(); }),
      fetch(API_BASE + '/api/places').then(function(r) { return r.ok ? r.json() : Promise.reject(); }),
      fetch(API_BASE + '/api/itineraries').then(function(r) { return r.ok ? r.json() : Promise.reject(); }),
    ]).then(function(results) {
      var ents = (results[0].entities || results[0] || []);
      var places = results[1] || [];
      // Merge places into entities (places have type=place but only id,name,area,level from the places endpoint)
      var placeIds = {};
      places.forEach(function(p) { p.type = 'place'; placeIds[p.id] = true; });
      var allEntities = ents.filter(function(e) { return !placeIds[e.id]; }).concat(places);
      return {
        entities: allEntities,
        relationships: [],  // relationships are fetched per-entity in detail view
        itineraries: results[2] || [],
      };
    });
  }

  // Try API first, fallback to static data.js
  if (window.VL_DATA) {
    // Static data available — use immediately, then try API upgrade
    _initData(window.VL_DATA);
    _fetchAPI().then(function(data) {
      if (data.entities.length > 0) {
        // Keep static relationships since API doesn't return bulk relationships
        data.relationships = relationships;
        _initData(data);
        if (window._onStoreRefresh) window._onStoreRefresh();
      }
    }).catch(function() { /* static data already loaded, ignore */ });
  } else {
    // No static data — must wait for API
    _fetchAPI().then(_initData).catch(function() {
      console.warn('vinhlong360: No data source available');
      _initData({ entities: [], relationships: [], itineraries: [] });
    });
  }

  var TYPE_META = {
    experience: { emoji: "🌾", label: "Trải nghiệm", cat: "experience" },
    product: { emoji: "🍊", label: "Đặc sản & OCOP", cat: "product" },
    dish: { emoji: "🍲", label: "Ẩm thực", cat: "dish" },
    craft_village: { emoji: "🏺", label: "Làng nghề", cat: "craft" },
    attraction: { emoji: "🛕", label: "Tham quan", cat: "attraction" },
    accommodation: { emoji: "🏡", label: "Lưu trú", cat: "accommodation" },
    organization: { emoji: "🏢", label: "Cơ sở / HTX", cat: "org" },
    place: { emoji: "📍", label: "Xã/Phường", cat: "place" },
  };

  var AREA_META = {
    "vinh-long": { name: "Vĩnh Long", emoji: "🍊", blurb: "Miệt vườn cam sành, khoai lang, bưởi Năm Roi và làng gốm Mang Thít." },
    "ben-tre": { name: "Bến Tre", emoji: "🥥", blurb: "Xứ dừa: kẹo dừa, mật hoa dừa, bưởi da xanh và những rẫy dừa bạt ngàn." },
    "tra-vinh": { name: "Trà Vinh", emoji: "🛕", blurb: "Văn hóa Khmer: ao Bà Om, chùa cổ, dừa sáp Cầu Kè và bún nước lèo." },
  };

  var CARD_TYPES = ["experience", "product", "dish", "craft_village", "attraction", "accommodation"];
  var TOURISM_TYPES = ["experience", "attraction", "accommodation", "craft_village", "dish"];
  var PRODUCT_TYPES = ["product"];

  var REL_FWD = { hosts: "Tổ chức", offered_by: "Đặt qua", made_by: "Sản xuất bởi", produced_in: "Sản xuất tại", supplies_to: "Cung ứng cho", near: "Gần" };
  var REL_BWD = { hosts: "Diễn ra tại", offered_by: "Cung cấp", made_by: "Sản phẩm", produced_in: "Đặc sản", supplies_to: "Nguồn cung", near: "Gần" };

  var FLOOD = [8, 9, 10, 11];

  /* ----------------- season helpers ----------------- */
  function isYearRound(season) { return season && season.months && season.months.length >= 11; }

  function monthRanges(months) {
    var s = [];
    months.forEach(function(m) { if (s.indexOf(m) === -1) s.push(m); });
    s.sort(function(a, b) { return a - b; });
    var out = [];
    var start = s[0], prev = s[0];
    for (var i = 1; i < s.length; i++) {
      if (s[i] === prev + 1) prev = s[i];
      else { out.push([start, prev]); start = s[i]; prev = s[i]; }
    }
    out.push([start, prev]);
    return out.map(function(p) { return p[0] === p[1] ? "T" + p[0] : "T" + p[0] + "–" + p[1]; }).join(", ");
  }

  function seasonText(season) {
    if (!season || !season.months) return "Quanh năm";
    if (isYearRound(season)) return "Quanh năm";
    return monthRanges(season.months);
  }

  function expandSeason(sel) {
    if (sel === "all" || sel == null) return null;
    if (sel === "flood") return FLOOD;
    return [parseInt(sel, 10)];
  }

  function inSeason(e, sel) {
    var m = expandSeason(sel);
    if (!m) return true;
    if (!e.season || !e.season.months) return true;
    return e.season.months.some(function(x) { return m.indexOf(x) >= 0; });
  }

  function relevanceScore(e, sel) {
    var m = expandSeason(sel);
    if (!m) return e.confidence || 0;
    if (!e.season || !e.season.months) return 1;
    if (!e.season.months.some(function(x) { return m.indexOf(x) >= 0; })) return -1;
    if (isYearRound(e.season)) return 2;
    return (e.season.peak || []).some(function(x) { return m.indexOf(x) >= 0; }) ? 4 : 3;
  }

  /* ----------------- place helpers ----------------- */
  function placesAll() { return entities.filter(function(e) { return e.type === "place" && e.parentId; }); }
  function placeOf(id) { var e = byId[id]; return e && e.placeId ? byId[e.placeId] : null; }
  function areaOf(id) { var p = placeOf(id); return p ? p.area : (byId[id] && byId[id].area) || null; }
  function placeName(id) { var p = byId[id]; return p ? (p.alias || p.name) : id; }
  function areaName(area) { var m = AREA_META[area]; return m ? m.name : area; }

  function placesWithContent() {
    var used = {};
    entities.forEach(function(e) { if (e.placeId) used[e.placeId] = true; });
    return placesAll().filter(function(p) { return used[p.id]; });
  }

  function placesByArea(area) {
    return placesAll().filter(function(p) { return p.area === area; });
  }

  function placeStats(area) {
    var ps = placesByArea(area);
    var phuong = ps.filter(function(p) { return p.level === "phuong"; }).length;
    var xa = ps.filter(function(p) { return p.level === "xa"; }).length;
    return { total: ps.length, phuong: phuong, xa: xa };
  }

  function placesWithCoords() {
    return placesAll().filter(function(p) { return p.coords; });
  }

  function entitiesAt(placeId) {
    return entities.filter(function(e) { return e.placeId === placeId && CARD_TYPES.indexOf(e.type) >= 0; });
  }

  /* ----------------- queries ----------------- */
  function cards() { return entities.filter(function(e) { return CARD_TYPES.indexOf(e.type) >= 0; }); }

  function query(opts) {
    opts = opts || {};
    var types = opts.types || CARD_TYPES;
    var list = entities.filter(function(e) { return types.indexOf(e.type) >= 0; });
    if (opts.area) list = list.filter(function(e) { return areaOf(e.id) === opts.area; });
    if (opts.placeId) list = list.filter(function(e) { return e.placeId === opts.placeId; });
    if (opts.season) list = list.filter(function(e) { return inSeason(e, opts.season); });
    if (opts.q) {
      var q = opts.q.toLowerCase();
      list = list.filter(function(e) {
        var place = byId[e.placeId];
        var searchable = e.name + " " + (e.summary || "") + " " + (place ? (place.alias || "") + " " + (place.legacyArea || "") : "");
        return searchable.toLowerCase().indexOf(q) >= 0;
      });
    }
    var sel = opts.season;
    list.sort(function(a, b) {
      return relevanceScore(b, sel) - relevanceScore(a, sel) ||
        (b.confidence || 0) - (a.confidence || 0) ||
        a.name.localeCompare(b.name, "vi");
    });
    return list;
  }

  function related(id) {
    var out = [];
    relationships.forEach(function(r) {
      if (r.from === id && byId[r.to]) out.push({ label: REL_FWD[r.type] || r.type, type: r.type, other: r.to });
      else if (r.to === id && byId[r.from]) out.push({ label: REL_BWD[r.type] || r.type, type: r.type, other: r.from });
    });
    return out;
  }

  function sameArea(id, limit) {
    var e = byId[id];
    if (!e) return [];
    return cards()
      .filter(function(x) { return x.id !== id && x.placeId === e.placeId; })
      .sort(function(a, b) { return (b.confidence || 0) - (a.confidence || 0); })
      .slice(0, limit || 6);
  }

  function seasonalNow(month) {
    return query({ types: ["product", "experience"], season: month })
      .filter(function(e) { return relevanceScore(e, month) >= 3; })
      .slice(0, 8);
  }

  function featured(types, limit) {
    return query({ types: types }).sort(function(a, b) { return (b.confidence || 0) - (a.confidence || 0); }).slice(0, limit || 6);
  }

  function searchFn(q) {
    if (!q) return [];
    return query({ q: q, types: CARD_TYPES });
  }

  function stats() {
    var by = {};
    cards().forEach(function(e) { by[e.type] = (by[e.type] || 0) + 1; });
    var allPlaces = placesAll();
    return {
      total: cards().length,
      byType: by,
      places: allPlaces.length,
      phuong: allPlaces.filter(function(p) { return p.level === "phuong"; }).length,
      xa: allPlaces.filter(function(p) { return p.level === "xa"; }).length,
      itineraries: itineraries.length,
    };
  }

  window.Store = {
    get entities() { return entities; },
    get relationships() { return relationships; },
    get itineraries() { return itineraries; },
    ALL_MONTHS: ALL_MONTHS,
    TYPE_META: TYPE_META, AREA_META: AREA_META,
    CARD_TYPES: CARD_TYPES, TOURISM_TYPES: TOURISM_TYPES, PRODUCT_TYPES: PRODUCT_TYPES,
    byId: function(id) { return byId[id]; },
    query: query, related: related,
    placeOf: placeOf, areaOf: areaOf, placeName: placeName, areaName: areaName,
    places: placesAll, placesWithContent: placesWithContent, placesWithCoords: placesWithCoords,
    placesByArea: placesByArea, placeStats: placeStats, entitiesAt: entitiesAt,
    sameArea: sameArea, seasonalNow: seasonalNow, featured: featured,
    search: searchFn, stats: stats,
    isYearRound: isYearRound, monthRanges: monthRanges, seasonText: seasonText, relevanceScore: relevanceScore,
    itinerary: function(id) { return itineraries.find(function(i) { return i.id === id; }); },
    onReady: function(cb) { if (_ready) cb(); else _readyCallbacks.push(cb); },
    isReady: function() { return _ready; },
  };
})();

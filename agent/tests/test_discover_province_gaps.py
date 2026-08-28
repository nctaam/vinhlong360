"""
Characterization test cho các hàm chưa phủ của discover_province.py.

Đặc tả HÀNH VI HIỆN TẠI của pipeline khám phá toàn tỉnh:
  _slug / _district_regions / _build_stream_prompt / _parse_stream_items /
  _filter_stream_items / discover_stream / _collect_streams / _dedup_candidates /
  _geocode_candidates / _persist_to_db / run_discovery / _next_topic /
  run_next_rotation.

Nguyên tắc an toàn:
  - KHÔNG chạm DB thật: đường ghi dùng fixture isolated_sqlite_db (SQLite trong
    tmp_path) và monkeypatch `database.db` — _persist_to_db đọc `db` bằng
    `from database import db` lúc GỌI nên phải vá đúng module `database`.
  - KHÔNG mạng, KHÔNG LLM thật: _client / geo.geocode / kb_curation đều được
    monkeypatch trong phạm vi từng test.
  - Cursor xoay vòng trỏ vào file tạm, không đụng agent/data/discovery_cursor.json.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database
import discover_province


# ── _slug ──────────────────────────────────────────────────────────────


def test_slug_bo_dau_va_thay_khoang_trang_bang_gach():
    assert discover_province._slug("Chùa Âng (Trà Vinh)") == "chua-ang-tra-vinh"


def test_slug_chu_d_gach_ngang_thanh_d_thuong():
    # NFD không tách được "đ" nên module phải replace tay — khoá hành vi đó.
    assert discover_province._slug("Đình Tân Hoà!!!") == "dinh-tan-hoa"


def test_slug_cat_toi_da_60_ky_tu():
    slug = discover_province._slug("Khu du lịch sinh thái " * 5)
    assert len(slug) <= 60
    assert slug.startswith("khu-du-lich-sinh-thai")


def test_slug_chuoi_rong_tra_rong():
    assert discover_province._slug("") == ""


# ── _district_regions ─────────────────────────────────────────────────


def test_district_regions_gom_theo_cap_legacyarea_area(monkeypatch):
    data = {
        "entities": [
            {"id": "p1", "type": "place", "legacyArea": "Huyện Long Hồ", "area": "vinh-long"},
            # trùng cặp (legacyArea, area) → chỉ tính 1 lần
            {"id": "p2", "type": "place", "legacyArea": "Huyện Long Hồ", "area": "vinh-long"},
            {"id": "p3", "type": "place", "legacyArea": "Huyện Mỏ Cày", "area": "ben-tre"},
            # place thiếu legacyArea → bỏ qua
            {"id": "p4", "type": "place", "area": "tra-vinh"},
            # không phải place → bỏ qua dù có đủ field
            {"id": "e1", "type": "attraction", "legacyArea": "X", "area": "vinh-long"},
        ]
    }
    monkeypatch.setattr(discover_province, "load_json", lambda _p: data)

    out = discover_province._district_regions()

    assert out == [
        {"label": "Huyện Long Hồ (tỉnh Vĩnh Long mới)", "area": "vinh-long"},
        {"label": "Huyện Mỏ Cày (tỉnh Vĩnh Long mới)", "area": "ben-tre"},
    ]


def test_district_regions_loi_doc_kb_thi_ve_3_vung_mac_dinh(monkeypatch):
    def boom(_p):
        raise OSError("khong doc duoc data.json")

    monkeypatch.setattr(discover_province, "load_json", boom)
    assert discover_province._district_regions() is discover_province.REGIONS


def test_district_regions_kb_khong_co_place_thi_ve_mac_dinh(monkeypatch):
    monkeypatch.setattr(discover_province, "load_json",
                        lambda _p: {"entities": [{"id": "x", "type": "dish"}]})
    assert discover_province._district_regions() is discover_province.REGIONS


# ── _build_stream_prompt ──────────────────────────────────────────────

_REGION_BT = {"label": "Bến Tre (cũ)", "area": "ben-tre"}


def test_prompt_dia_diem_hoi_xa_phuong_huyen():
    p = discover_province._build_stream_prompt(_REGION_BT, "di tích lịch sử", "history")
    assert "xã/phường + huyện" in p
    assert "Bến Tre (cũ)" in p
    assert "di tích lịch sử" in p
    assert "CÓ THẬT" in p
    assert '"name":"..."' in p
    assert "Tối đa 15 mục" in p


def test_prompt_san_pham_hoi_vung_trong_thay_vi_dia_chi():
    p = discover_province._build_stream_prompt(_REGION_BT, "sản phẩm OCOP", "product")
    assert "vùng trồng/sản xuất (xã/huyện)" in p
    assert "xã/phường + huyện" not in p


# ── _parse_stream_items ───────────────────────────────────────────────

_REGION_VL = {"label": "Vĩnh Long (cũ)", "area": "vinh-long"}


def test_parse_mang_json_tran():
    text = '[{"name":"Chùa Âng","location":"TP","summary":"x"}]'
    items = discover_province._parse_stream_items(text, _REGION_VL, "history")
    assert items == [{"name": "Chùa Âng", "location": "TP", "summary": "x"}]


def test_parse_boc_duoc_khoi_code_fence():
    text = '```json\n[{"name":"Cồn Phụng"}]\n```'
    assert discover_province._parse_stream_items(text, _REGION_VL, "nature") == [
        {"name": "Cồn Phụng"}
    ]


def test_parse_lay_mang_giua_van_xuoi():
    text = 'Đây là kết quả: [{"name":"Cầu Mỹ Thuận"}] — hết.'
    assert discover_province._parse_stream_items(text, _REGION_VL, "attraction") == [
        {"name": "Cầu Mỹ Thuận"}
    ]


def test_parse_json_hong_tra_mang_rong():
    assert discover_province._parse_stream_items("[{name: hong]", _REGION_VL, "history") == []


def test_parse_khong_co_mang_tra_mang_rong():
    assert discover_province._parse_stream_items("không có gì cả", _REGION_VL, "history") == []


# ── _filter_stream_items ──────────────────────────────────────────────


def test_filter_gan_type_va_area_cho_muc_hop_le():
    items = [{"name": "Chùa Vĩnh Tràng Vĩnh Long", "location": "Phường 1", "summary": " mô tả "}]
    out = discover_province._filter_stream_items(items, _REGION_VL, "history")
    assert out == [{
        "name": "Chùa Vĩnh Tràng Vĩnh Long", "location": "Phường 1",
        "summary": "mô tả", "type": "history", "area": "vinh-long",
    }]


def test_filter_loai_muc_khong_phai_dict_va_ten_qua_ngan():
    items = ["chuoi tho", {"name": "Abc", "location": "Phường 2"}]
    assert discover_province._filter_stream_items(items, _REGION_VL, "history") == []


def test_filter_chan_keyword_ngoai_tinh_trong_ten():
    items = [{"name": "Chợ nổi Cái Bè", "location": "Vĩnh Long"}]
    assert discover_province._filter_stream_items(items, _REGION_VL, "attraction") == []


def test_filter_chan_can_tho_chi_khi_nam_trong_dia_chi():
    items = [
        # "Cần Thơ" trong TÊN nhưng địa chỉ thuộc tỉnh → vẫn giữ (OUTSIDE_LOC chỉ soi loc)
        {"name": "Cầu Cần Thơ (bờ Bình Minh)", "location": "Bình Minh, Vĩnh Long"},
        # "Cần Thơ" trong ĐỊA CHỈ → chặn
        {"name": "Homestay Bến Sông", "location": "Cái Răng, Cần Thơ"},
    ]
    out = discover_province._filter_stream_items(items, _REGION_VL, "accommodation")
    assert [x["name"] for x in out] == ["Cầu Cần Thơ (bờ Bình Minh)"]


def test_filter_thieu_summary_thanh_chuoi_rong():
    items = [{"name": "Cồn Thới Sơn Nhỏ", "location": "Xã A"}]
    out = discover_province._filter_stream_items(items, _REGION_VL, "nature")
    assert out[0]["summary"] == ""


# ── discover_stream (LLM đã mock) ─────────────────────────────────────


def _fake_llm_client(content):
    def create(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_discover_stream_parse_va_loc_ket_qua_llm(monkeypatch):
    payload = json.dumps([
        {"name": "Cồn Phụng Bến Tre", "location": "Xã Tân Thạch", "summary": "cồn du lịch"},
        {"name": "Bến Ninh Kiều", "location": "Cần Thơ", "summary": "ngoài tỉnh"},
    ], ensure_ascii=False)
    monkeypatch.setattr(discover_province, "_client", lambda: _fake_llm_client(payload))

    out = discover_province.discover_stream(_REGION_BT, "điểm du lịch", "attraction", "cx/test")

    assert out == [{
        "name": "Cồn Phụng Bến Tre", "location": "Xã Tân Thạch",
        "summary": "cồn du lịch", "type": "attraction", "area": "ben-tre",
    }]


def test_discover_stream_loi_llm_tra_ve_error_marker(monkeypatch):
    def create(**kwargs):
        raise RuntimeError("mất mạng")

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(discover_province, "_client", lambda: client)

    out = discover_province.discover_stream(_REGION_VL, "điểm du lịch", "attraction", "cx/test")

    assert len(out) == 1
    assert out[0]["_error"].startswith("vinh-long/attraction:")
    assert "mất mạng" in out[0]["_error"]


# ── _collect_streams ──────────────────────────────────────────────────


def test_collect_streams_gom_ket_qua_va_dem_loi(monkeypatch):
    def fake_stream(region, category, etype, model):
        if etype == "err":
            return [{"_error": "vinh-long/err: hong"},
                    {"name": "Vẫn giữ", "type": "attraction", "area": "vinh-long"}]
        return [{"name": "Mục A", "type": "history", "area": "vinh-long"}]

    monkeypatch.setattr(discover_province, "discover_stream", fake_stream)
    streams = [(_REGION_VL, "cat1", "err"), (_REGION_VL, "cat2", "ok")]

    found, errors = discover_province._collect_streams(streams, workers=2, model="cx/test")

    assert errors == 1
    assert sorted(x["name"] for x in found) == ["Mục A", "Vẫn giữ"]


# ── _dedup_candidates ─────────────────────────────────────────────────


def test_dedup_trung_ten_trung_kb_va_near_dup_deu_bi_loai(monkeypatch):
    calls = []

    def fake_near_dup(name, etype, entities):
        calls.append((name, list(entities)))
        return "kb-cu" if name == "Điểm trùng KB" else None

    monkeypatch.setattr(discover_province.kb_curation, "find_near_duplicate", fake_near_dup)

    found = [
        {"name": "Nhà xưa Cai Cường", "type": "attraction"},
        {"name": "NHÀ XƯA CAI CƯỜNG", "type": "attraction"},   # trùng tên đã chuẩn hoá
        {"name": "Chùa Hạnh Phúc", "type": "history"},          # slug đã có trong KB
        {"name": "Điểm trùng KB", "type": "attraction"},        # near-dup vs KB
        {"name": "Điểm hoàn toàn mới", "type": "nature"},
    ]
    data = {"entities": [{"id": "kb-cu", "name": "Cũ", "type": "attraction"}]}

    unique = discover_province._dedup_candidates(found, {"chua-hanh-phuc"}, data)

    assert [c["name"] for c in unique] == ["Nhà xưa Cai Cường", "Điểm hoàn toàn mới"]
    assert unique[0]["id"] == "nha-xua-cai-cuong"
    assert unique[1]["id"] == "diem-hoan-toan-moi"
    # near-dup chỉ được hỏi cho ứng viên qua được 2 cổng rẻ (3 lần, không phải 5)
    assert [c[0] for c in calls] == ["Nhà xưa Cai Cường", "Điểm trùng KB", "Điểm hoàn toàn mới"]
    # cổng near-dup phải thấy CẢ ứng viên vừa nhận trong đợt (pseudo-entity)
    last_entities = calls[-1][1]
    assert {"id": "nha-xua-cai-cuong", "name": "Nhà xưa Cai Cường",
            "type": "attraction"} in last_entities


# ── _geocode_candidates ───────────────────────────────────────────────


def test_geocode_dia_diem_theo_ten_san_pham_theo_vung_trong(monkeypatch):
    asked = []

    def fake_geocode(q, region=None):
        asked.append((q, region))
        return None if q == "Chợ Lách" else [10.2, 106.3]

    monkeypatch.setattr(discover_province.geo, "geocode", fake_geocode)
    unique = [
        {"name": "Chùa Âng", "type": "history", "location": "Phường 8"},
        {"name": "Sầu riêng Chợ Lách", "type": "product", "location": "Chợ Lách"},
        {"name": "Cam sành ngon", "type": "product", "location": ""},
    ]

    geocoded = discover_province._geocode_candidates(unique)

    assert asked == [
        ("Chùa Âng", "Phường 8"),          # địa điểm: theo TÊN
        ("Chợ Lách", "Chợ Lách"),          # sản phẩm: theo VÙNG TRỒNG
        ("Cam sành ngon", "Vĩnh Long"),    # sản phẩm thiếu location: fallback tên
    ]
    assert geocoded == 2
    assert unique[0]["coords"] == [10.2, 106.3]
    assert "coords" not in unique[1]
    assert unique[2]["coords"] == [10.2, 106.3]


# ── _persist_to_db (đường GHI — chỉ SQLite tạm) ──────────────────────


def test_persist_to_db_ghi_entity_co_trong_data(monkeypatch, isolated_sqlite_db):
    monkeypatch.setattr(database, "db", isolated_sqlite_db)
    ent = {
        "id": "diem-moi-thu-nghiem", "type": "attraction", "name": "Điểm mới thử nghiệm",
        "summary": "tóm tắt", "status": "provisional", "verified": False,
        "attributes": {}, "images": [], "coords": [10.25, 106.10],
        "source": {"title": "agent discovery", "method": "llm+nominatim"},
    }
    data = {"entities": [ent]}
    unique = [
        {"id": "diem-moi-thu-nghiem", "name": "Điểm mới thử nghiệm"},
        {"id": "khong-co-trong-data", "name": "Bị bỏ qua"},  # không có entity khớp → không ghi
    ]

    discover_province._persist_to_db(unique, data)

    row = isolated_sqlite_db.get_entity("diem-moi-thu-nghiem")
    assert row["name"] == "Điểm mới thử nghiệm"
    assert row["type"] == "attraction"
    # alias "coords" phải thành cột coordinates khi round-trip
    assert row["coordinates"] == [10.25, 106.10]
    assert isolated_sqlite_db.get_entity("khong-co-trong-data") is None


def test_persist_to_db_nuot_loi_db_khong_lan_ra_ngoai(monkeypatch):
    class _BoomDB:
        def upsert_entity(self, entity):
            raise RuntimeError("db hong")

    monkeypatch.setattr(database, "db", _BoomDB())
    data = {"entities": [{"id": "x", "type": "attraction", "name": "X"}]}

    # không được ném exception — chỉ ghi log warning
    assert discover_province._persist_to_db([{"id": "x"}], data) is None


# ── run_discovery (mock trọn) ─────────────────────────────────────────


def _wire_dry_run(monkeypatch):
    """Nối toàn bộ collaborator của run_discovery vào fake offline."""
    kb = {"entities": [
        {"id": "xa-tan-thach", "name": "Tân Thạch", "type": "place", "area": "ben-tre"},
    ]}
    monkeypatch.setattr(discover_province, "load_json", lambda _p: kb)

    def fake_stream(region, category, etype, model):
        if etype == "attraction":
            return [{"name": "Cồn Phụng Bến Tre", "location": "Xã Tân Thạch",
                     "summary": "s", "type": "attraction", "area": region["area"]}]
        if etype == "history":
            return [{"_error": f"{region['area']}/history: hong"}]
        return []

    monkeypatch.setattr(discover_province, "discover_stream", fake_stream)
    monkeypatch.setattr(discover_province.kb_curation, "find_near_duplicate",
                        lambda n, t, ents: None)
    monkeypatch.setattr(discover_province.geo, "geocode",
                        lambda q, region=None: [10.2, 106.3])


def test_run_discovery_dry_run_tra_summary_va_sample(monkeypatch):
    _wire_dry_run(monkeypatch)

    s = discover_province.run_discovery(
        ["tourism"], [_REGION_BT], workers=2, model="cx/test", apply=False)

    assert s["topics"] == ["tourism"]
    assert s["raw"] == 1
    assert s["errors"] == 1
    assert s["new"] == 1
    assert s["geocoded"] == 1
    assert s["added"] == 0
    assert isinstance(s["seconds"], int)
    assert s["sample"] == [{"name": "Cồn Phụng Bến Tre", "type": "attraction",
                            "coords": [10.2, 106.3]}]


def test_run_discovery_topic_rong_tra_error_truoc_khi_doc_kb(monkeypatch):
    def boom(_p):
        raise AssertionError("khong duoc doc KB khi topic sai")

    monkeypatch.setattr(discover_province, "load_json", boom)
    s = discover_province.run_discovery(["bogus"], [_REGION_VL], 1, "cx/test", False)
    assert s == {"error": "no valid topics", "topics": ["bogus"]}


def test_run_discovery_apply_uy_quyen_cho_apply_discovery(monkeypatch):
    _wire_dry_run(monkeypatch)
    captured = {}

    def fake_apply(unique, data, places, model, label, summary):
        captured.update(unique=unique, label=label, summary=summary)
        return {"marker": "da-ap-dung"}

    monkeypatch.setattr(discover_province, "_apply_discovery", fake_apply)

    out = discover_province.run_discovery(
        ["tourism"], [_REGION_BT], workers=2, model="cx/test", apply=True, label="phien-thu")

    assert out == {"marker": "da-ap-dung"}
    assert captured["label"] == "phien-thu"
    assert [c["name"] for c in captured["unique"]] == ["Cồn Phụng Bến Tre"]
    assert captured["summary"]["new"] == 1
    # nhánh apply KHÔNG kèm sample (chỉ dry-run mới có)
    assert "sample" not in captured["summary"]


# ── _next_topic (cursor xoay vòng) ────────────────────────────────────


def test_next_topic_xoay_vong_tourism_agri_ocop(monkeypatch, tmp_path):
    cursor = tmp_path / "cursor.json"
    monkeypatch.setattr(discover_province, "CURSOR_FILE", cursor)

    assert discover_province._next_topic() == "tourism"
    assert json.loads(cursor.read_text(encoding="utf-8")) == {"idx": 1}
    assert discover_province._next_topic() == "agri"
    assert discover_province._next_topic() == "ocop"
    assert discover_province._next_topic() == "tourism"  # quay lại đầu vòng


def test_next_topic_cursor_hong_thi_ve_dau_vong(monkeypatch, tmp_path):
    cursor = tmp_path / "cursor.json"
    cursor.write_text("khong phai json", encoding="utf-8")
    monkeypatch.setattr(discover_province, "CURSOR_FILE", cursor)

    assert discover_province._next_topic() == "tourism"
    assert json.loads(cursor.read_text(encoding="utf-8")) == {"idx": 1}


def test_next_topic_idx_ngoai_bien_van_modulo(monkeypatch, tmp_path):
    cursor = tmp_path / "cursor.json"
    cursor.write_text(json.dumps({"idx": 7}), encoding="utf-8")
    monkeypatch.setattr(discover_province, "CURSOR_FILE", cursor)

    assert discover_province._next_topic() == "agri"  # 7 % 3 == 1
    assert json.loads(cursor.read_text(encoding="utf-8")) == {"idx": 2}


# ── run_next_rotation ─────────────────────────────────────────────────


def test_run_next_rotation_ghep_topic_vao_summary(monkeypatch):
    captured = {}
    monkeypatch.setattr(discover_province, "_next_topic", lambda: "ocop")

    def fake_run(topics, regions, workers, model, apply, label="manual"):
        captured.update(topics=topics, regions=regions, workers=workers,
                        model=model, apply=apply, label=label)
        return {"raw": 5, "new": 2}

    monkeypatch.setattr(discover_province, "run_discovery", fake_run)

    out = discover_province.run_next_rotation(workers=3, model="cx/custom", apply=False)

    assert out == {"topic": "ocop", "raw": 5, "new": 2}
    assert captured["topics"] == ["ocop"]
    assert captured["regions"] is discover_province.REGIONS
    assert captured["workers"] == 3
    assert captured["model"] == "cx/custom"
    assert captured["apply"] is False
    assert captured["label"] == "ocop"


def test_run_next_rotation_mac_dinh_dung_default_model_va_apply_true(monkeypatch):
    captured = {}
    monkeypatch.setattr(discover_province, "_next_topic", lambda: "tourism")

    def fake_run(topics, regions, workers, model, apply, label="manual"):
        captured.update(model=model, apply=apply)
        return {}

    monkeypatch.setattr(discover_province, "run_discovery", fake_run)

    out = discover_province.run_next_rotation()

    assert out == {"topic": "tourism"}
    assert captured["model"] == discover_province.DEFAULT_MODEL
    assert captured["apply"] is True

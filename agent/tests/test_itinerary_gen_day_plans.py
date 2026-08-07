# -*- coding: utf-8 -*-
"""Phủ các vùng mù còn lại của itinerary_gen: `_build_day_plans` + nhóm helper nhỏ.

Vì sao file này tồn tại: cổng hard-ratchet R20.4 đòi `agent/itinerary_gen.py` ≥ 98%;
đo 2026-08-07 được 95% với 22 dòng trống. Khối lớn nhất (186-216) là `_build_day_plans`
— hàm KHÔNG còn chỗ gọi nào trong sản phẩm (`generate_itinerary` đi đường
`_build_joint_day_plans`), nên chưa test nào chạm tới. Nó vẫn nằm trong module nên ta
KHOÁ HÀNH VI THẬT của nó thay vì xoá (xoá là refactor, không phải việc phủ test).

Các helper còn lại (`_project_placements`, `_finite_coordinates`,
`_candidate_suggested_duration`, `_fixed_anchor_window`, `_build_anchor_items`) đều
thuần hoặc gần thuần nên phủ trực tiếp bằng input thật — không mock, không chạm DB.
"""
from __future__ import annotations

import re
import sys
import unicodedata

import pytest

import itinerary_gen as ig
from itinerary_schedule import SchedulePlacement, ScheduleResult


# ─────────────────────────── helper dựng dữ liệu ───────────────────────────
# Cùng khuôn với `_day_item` của test_cov_itinerary_gen.py: entity tối thiểu mà
# `_candidate_schedule_stop` chấp nhận (toạ độ hữu hạn) kèm `score`/`area`.
# Vĩ độ cách nhau ~0.02° (~2km) để bộ lập lịch còn khả thi trong khung 08:00-18:00.

def _item(eid: str, lat: float, etype: str = "attraction", area: str = "vinh-long") -> dict:
    return {
        "entity": {
            "id": eid,
            "name": eid.upper(),
            "type": etype,
            "coordinates": [lat, 106.0],
            "summary": "x" * 60,
        },
        "score": 1.0,
        "area": area,
    }


def _item_khong_toa_do(eid: str) -> dict:
    return {
        "entity": {"id": eid, "name": eid.upper(), "type": "attraction", "summary": ""},
        "score": 1.0,
        "area": "vinh-long",
    }


# ═══════════════════════════ _build_day_plans ═══════════════════════════


def test_build_day_plans_cat_selected_theo_lat_lien_tuc():
    """Mỗi ngày lấy đúng một lát `stops_per_day` liên tiếp của `selected`.

    Đây là hợp đồng phân bổ duy nhất của hàm — `idx` chạy tuyến tính, không xáo trộn,
    không chọn lại. Ai đổi sang "chọn thông minh" phải làm đỏ test này trước.
    """
    selected = [_item("a", 10.00), _item("b", 10.02), _item("c", 10.04), _item("d", 10.06)]

    day_plans = ig._build_day_plans(
        days=2,
        stops_per_day=2,
        selected=selected,
        meal_candidates=[],
        month=6,
        meal_anchors=[],
        rest_anchors=[],
    )

    assert [plan["day"] for plan in day_plans] == [1, 2]
    assert {s["entity"]["id"] for s in day_plans[0]["stops"]} == {"a", "b"}
    assert {s["entity"]["id"] for s in day_plans[1]["stops"]} == {"c", "d"}


def test_build_day_plans_khong_lo_time_min_ra_payload():
    """`time_min` là biến nội bộ của bộ lập lịch, KHÔNG được rò vào payload trả về."""
    day_plans = ig._build_day_plans(
        days=1,
        stops_per_day=2,
        selected=[_item("a", 10.00), _item("b", 10.02)],
        meal_candidates=[],
        month=6,
        meal_anchors=[],
        rest_anchors=[],
    )

    stops = day_plans[0]["stops"]
    assert stops, "phải có stop thì phép lọc khoá mới có nghĩa"
    for stop in stops:
        assert "time_min" not in stop
        assert ":" in stop["time"]
    # `schedule` (chẩn đoán) đi kèm nguyên vẹn, không bị lọc
    assert day_plans[0]["schedule"]["solver"]


def test_build_day_plans_area_focus_tinh_theo_tung_ngay():
    """area_focus = `_day_area` của LÁT entity ngày đó, không phải của cả chuyến."""
    selected = [
        _item("a", 10.00, area="vinh-long"),
        _item("b", 10.02, area="vinh-long"),
        _item("c", 10.04, area="ben-tre"),
        _item("d", 10.06, area="ben-tre"),
    ]

    day_plans = ig._build_day_plans(
        days=2, stops_per_day=2, selected=selected, meal_candidates=[],
        month=6, meal_anchors=[], rest_anchors=[],
    )

    assert [plan["area_focus"] for plan in day_plans] == ["vinh-long", "ben-tre"]


def test_build_day_plans_khong_lap_lai_mon_an_giua_cac_ngay():
    """`used_entity_ids` tích luỹ QUA CÁC NGÀY, kể cả id của stop `is_meal`.

    Đó là lý do tồn tại của hai lệnh `update` trong vòng lặp. `selected` đã nằm sẵn
    trong `used_entity_ids` từ đầu, nên chỉ nhánh `if stop.get("is_meal")` mới đưa
    được `mon-1` vào tập loại trừ của ngày 2. Bỏ nhánh đó đi thì cùng một món sẽ lặp
    lại mỗi ngày mà không test nào kêu.
    """
    selected = [_item("a", 10.00), _item("b", 10.02), _item("c", 10.04), _item("d", 10.06)]
    meal_candidates = [
        _item("mon-1", 10.01, etype="dish"),
        _item("mon-2", 10.05, etype="dish"),
    ]

    day_plans = ig._build_day_plans(
        days=2,
        stops_per_day=2,
        selected=selected,
        meal_candidates=meal_candidates,
        month=6,
        meal_anchors=["11:30"],
        rest_anchors=[],
    )

    meals_per_day = [
        [s["entity"]["id"] for s in plan["stops"] if s.get("is_meal")]
        for plan in day_plans
    ]
    assert meals_per_day == [["mon-1"], ["mon-2"]], meals_per_day


def test_build_day_plans_zero_ngay_tra_ve_rong():
    assert ig._build_day_plans(
        days=0, stops_per_day=4, selected=[_item("a", 10.0)], meal_candidates=[],
        month=None, meal_anchors=[], rest_anchors=[],
    ) == []


def test_build_day_plans_thieu_entity_thi_ngay_thua_van_duoc_tao():
    """QUAN SÁT (không phải mong muốn): selected ngắn hơn `days * stops_per_day` thì
    các ngày thừa vẫn được thêm vào với `stops: []` và `area_focus: ""` — hàm KHÔNG
    cắt bớt ngày. Khoá hành vi thật; nếu coi đây là lỗi thì phải sửa qua task riêng.
    """
    day_plans = ig._build_day_plans(
        days=3,
        stops_per_day=2,
        selected=[_item("a", 10.00), _item("b", 10.02)],
        meal_candidates=[],
        month=6,
        meal_anchors=[],
        rest_anchors=[],
    )

    assert len(day_plans) == 3
    assert day_plans[1]["stops"] == [] and day_plans[2]["stops"] == []
    assert day_plans[1]["area_focus"] == ""
    # ngày rỗng rơi về đường legacy của _build_day_schedule
    assert day_plans[1]["schedule"]["solver"] == "legacy-fixed-order"


# ═══════════════════════════ _project_placements ═══════════════════════════


def _schedule_result(
    ordered_ids: tuple[str, ...], placement_ids: tuple[str, ...]
) -> ScheduleResult:
    """ScheduleResult thật (không stub) để giữ đúng hợp đồng thuộc tính."""
    return ScheduleResult(
        ordered_ids=ordered_ids,
        placements=tuple(
            SchedulePlacement(
                stop_id=stop_id,
                arrival_minute=480.0,
                start_visit_minute=480.0,
                finish_visit_minute=540.0,
            )
            for stop_id in placement_ids
        ),
        skipped=(),
        total_travel_minutes=0.0,
        waiting_minutes=0.0,
        overtime_minutes=0.0,
        minimum_slack_minutes=0.0,
        geometric_distance_km=0.0,
        backtrack_ratio=0.0,
        solver="test",
        matrix_source="test",
        warnings=(),
    )


@pytest.mark.parametrize(
    "ordered_ids, placement_ids, ly_do",
    [
        (("a", "khong-co-item"), ("a", "khong-co-item"), "id không có trong items_by_id"),
        (("a", "b"), ("a",), "id không có placement tương ứng"),
    ],
)
def test_project_placements_bo_qua_id_khong_ghep_duoc(ordered_ids, placement_ids, ly_do):
    """Guard `item is None or placement is None` — bỏ qua thay vì nổ KeyError.

    Lịch và pool candidate là hai nguồn khác nhau; lệch nhau thì người dùng mất một
    stop chứ không được nhận HTTP 500.
    """
    items_by_id = {"a": _item("a", 10.00)}

    stops = ig._project_placements(
        _schedule_result(ordered_ids, placement_ids), items_by_id, month=6
    )

    assert [s["entity"]["id"] for s in stops] == ["a"], ly_do


def test_project_placements_gan_nhan_rest_cho_anchor_nghi():
    """Anchor `rest` phải ra `is_rest` + REST_NOTE, đè lên note sinh từ entity."""
    rest_item = {
        **_item("nghi-1", 10.00),
        "_anchor_kind": "rest",
    }

    stops = ig._project_placements(
        _schedule_result(("nghi-1",), ("nghi-1",)), {"nghi-1": rest_item}, month=6
    )

    assert stops[0]["is_rest"] is True
    assert stops[0]["note"] == ig.REST_NOTE
    assert stops[0]["time"] == "08:00"


# ═══════════════════════════ _finite_coordinates ═══════════════════════════


@pytest.mark.parametrize(
    "raw, mong_doi",
    [
        ({"lat": 10.25, "lng": 106.0}, (10.25, 106.0)),
        ({"latitude": 10.25, "longitude": 106.0}, (10.25, 106.0)),
        ({"lat": 10.25, "lon": 106.0}, (10.25, 106.0)),
        # lat/lng thắng latitude/longitude khi có cả hai
        ({"lat": 1.0, "lng": 2.0, "latitude": 9.0, "longitude": 9.0}, (1.0, 2.0)),
    ],
)
def test_finite_coordinates_chap_nhan_dict_nhieu_kieu_khoa(raw, mong_doi):
    """Toạ độ từ DB có thể là dict với 3 bộ tên khoá khác nhau — nhánh dict phải
    quy hết về tuple (lat, lng)."""
    assert ig._finite_coordinates(raw) == mong_doi


@pytest.mark.parametrize(
    "raw",
    [
        {"lat": 10.0},                    # thiếu lng → tuple có None
        {},                               # dict rỗng
        ["10.0", 106.0],                  # chuỗi không phải số
        [float("nan"), 106.0],            # không hữu hạn
        [10.0, float("inf")],
        [True, 106.0],                    # bool KHÔNG được coi là toạ độ
        [10.0, False],
        [10.0],                           # thiếu phần tử
        "10,106",                         # không phải list/tuple/dict
        None,
    ],
)
def test_finite_coordinates_tra_none_khi_khong_dung_toa_do(raw):
    assert ig._finite_coordinates(raw) is None


# ═══════════════════════ _candidate_suggested_duration ═══════════════════════


@pytest.mark.parametrize(
    "entity, mong_doi",
    [
        ({"suggested_duration": "2 giờ"}, "2 giờ"),
        ({"duration": "45 phút"}, "45 phút"),
        ({"attributes": {"suggested_duration": "nửa ngày"}}, "nửa ngày"),
        ({"attributes": {"duration": "1-2 giờ"}}, "1-2 giờ"),
        # suggested_duration được duyệt trước duration
        ({"suggested_duration": "A", "duration": "B"}, "A"),
    ],
)
def test_candidate_suggested_duration_doc_du_bon_cho(entity, mong_doi):
    assert ig._candidate_suggested_duration({"entity": entity}) == mong_doi


@pytest.mark.parametrize(
    "entity",
    [
        {},
        {"suggested_duration": 90},        # số nguyên KHÔNG phải free-text
        {"suggested_duration": None},
        {"attributes": None},
    ],
)
def test_candidate_suggested_duration_chi_nhan_chuoi(entity):
    assert ig._candidate_suggested_duration({"entity": entity}) is None


# ═══════════════════════════ _fixed_anchor_window ═══════════════════════════


def test_fixed_anchor_window_moc_hop_le():
    window = ig._fixed_anchor_window("12:00", 60)
    assert (window.start_minute, window.end_minute) == (720, 780)


def test_fixed_anchor_window_cat_khoang_trang():
    assert ig._fixed_anchor_window("  12:00  ", 60) == ig._fixed_anchor_window("12:00", 60)


@pytest.mark.parametrize("anchor", [None, 720, ["12:00"], b"12:00"])
def test_fixed_anchor_window_khong_phai_chuoi_tra_none(anchor):
    """`meal_anchors` đến từ payload người dùng nên phải chịu được kiểu rác."""
    assert ig._fixed_anchor_window(anchor, 60) is None


@pytest.mark.parametrize("anchor", ["", "trua", "25:00", "12:60", "12h00-13h00"])
def test_fixed_anchor_window_chuoi_khong_parse_duoc_tra_none(anchor):
    assert ig._fixed_anchor_window(anchor, 60) is None


def test_fixed_anchor_window_tran_qua_nua_dem_tra_none():
    """`TimeWindow` chặn end > 1440, nên mốc sát nửa đêm + visit_minutes bị loại.

    23:30 + 60 phút = 24:30 → ValueError → None (chứ không phải wrap sang hôm sau).
    23:00 + 60 = đúng 24:00 vẫn hợp lệ — biên là 1440 inclusive.
    """
    assert ig._fixed_anchor_window("23:30", 60) is None
    assert ig._fixed_anchor_window("23:00", 60).end_minute == 1440


# ═══════════════════════════ _build_anchor_items ═══════════════════════════


def test_build_anchor_items_bao_thieu_toa_do_cho_moc_nghi():
    """Mốc nghỉ được đặt tại toạ độ của một điểm trên tuyến; ngày không có điểm nào
    có toạ độ thì KHÔNG bịa toạ độ mà báo `rest-anchor-unavailable`."""
    items, warnings = ig._build_anchor_items(
        [_item_khong_toa_do("x")], [], [], ["14:00"], day_number=1, used_entity_ids=set()
    )

    assert items == []
    assert warnings == ["rest-anchor-unavailable"]


def test_build_anchor_items_moc_nghi_hop_le_bam_vao_toa_do_tuyen():
    """Đối chứng của test trên: có toạ độ thì mốc nghỉ được sinh, id gắn day_number."""
    items, warnings = ig._build_anchor_items(
        [_item("a", 10.00), _item("b", 10.02)], [], [], ["14:00"],
        day_number=3, used_entity_ids=set(),
    )

    assert warnings == []
    assert [i["entity"]["id"] for i in items] == ["rest-anchor-3-0"]
    assert items[0]["_anchor_kind"] == "rest"
    assert items[0]["entity"]["coordinates"] == (10.00, 106.0)


def test_build_anchor_items_moc_nghi_hong_bao_invalid_anchor():
    items, warnings = ig._build_anchor_items(
        [_item("a", 10.00)], [], [], ["khong-phai-gio"],
        day_number=1, used_entity_ids=set(),
    )

    assert items == []
    assert warnings == ["invalid-anchor"]


# ═══════════════ chứng minh nhánh ValueError của _candidate_fee_value là chết ═══════════════


def test_regex_gia_luon_parse_duoc_thanh_float():
    """Nhánh `except ValueError` trong `_candidate_fee_value` (dòng 238-239) KHÔNG
    thể chạm tới bằng input thật — test này là bằng chứng, không phải mẹo coverage.

    `re.search(r"\\d+(?:[.,]\\d+)?")` chỉ trả về chuỗi gồm ký tự Unicode category Nd
    (có thể kèm 1 dấu . hoặc ,). `float()` chấp nhận MỌI ký tự Nd, kể cả trộn nhiều
    hệ chữ số. Quét toàn bộ 760 ký tự Nd để khoá kết luận đó: nếu Python/Unicode sau
    này đổi luật, test đỏ và nhánh kia mới đáng phủ.
    """
    pattern = re.compile(r"\d+(?:[.,]\d+)?")
    nd_chars = [
        chr(code)
        for code in range(sys.maxunicode + 1)
        if unicodedata.category(chr(code)) == "Nd"
    ]
    assert len(nd_chars) > 500, "kỳ vọng Unicode có hàng trăm ký tự Nd"

    for char in nd_chars:
        match = pattern.search(char)
        assert match is not None, f"\\d không bắt được Nd {ord(char):#x}"
        float(match.group(0).replace(",", "."))  # không được ném ValueError

    # trộn hệ chữ số + dấu thập phân cũng vẫn parse được
    assert ig._candidate_fee_value({"entity": {"fee_value": "٣3,٤"}}) == pytest.approx(33.4)

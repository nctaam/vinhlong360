# -*- coding: utf-8 -*-
"""Phủ `_candidate_fee_value` và `_build_day_plans` của itinerary_gen.

R20.4 đòi module này ≥ 98%; đo 2026-08-07 được 93.8% với 30 dòng trống, phần lớn
nằm ở hai hàm dưới đây. `_candidate_fee_value` là hàm THUẦN nhiều nhánh (3 nguồn
giá, bool, số, chuỗi, chuỗi hỏng) nên phủ nó rẻ và không cần dựng dữ liệu nặng.
"""
from __future__ import annotations

import math

import pytest

from itinerary_gen import _candidate_fee_value


def _item(**entity) -> dict:
    return {"entity": entity}


@pytest.mark.parametrize(
    "entity, mong_doi",
    [
        ({"fee_value": 50000}, 50000.0),
        ({"attributes": {"admission_fee": 20000}}, 20000.0),
        ({"attributes": {"gia": 15000}}, 15000.0),
        # fee_value thắng attributes khi cả hai cùng có
        ({"fee_value": 1000, "attributes": {"admission_fee": 9000}}, 1000.0),
        ({"fee_value": 0}, 0.0),
    ],
)
def test_lay_gia_tu_ba_nguon_theo_thu_tu_uu_tien(entity, mong_doi):
    assert _candidate_fee_value(_item(**entity)) == mong_doi


@pytest.mark.parametrize(
    "entity",
    [
        {},                                   # không có nguồn nào
        {"fee_value": True},                  # bool KHÔNG được coi là số
        {"fee_value": False},
        {"fee_value": -1},                    # giá âm
        {"fee_value": float("nan")},          # không hữu hạn
        {"fee_value": float("inf")},
        {"fee_value": []},                    # kiểu lạ, không phải str/số
        {"fee_value": "miễn phí"},            # chuỗi không có chữ số
    ],
)
def test_gia_khong_hop_le_tra_none(entity):
    assert _candidate_fee_value(_item(**entity)) is None


@pytest.mark.parametrize(
    "raw, mong_doi",
    [
        ("50000", 50000.0),
        ("50.000đ", 50.0),        # regex bắt cụm số đầu tiên
        ("giá 25,5 nghìn", 25.5),  # dấu phẩy thành dấu chấm
        ("từ 10000 đến 20000", 10000.0),
    ],
)
def test_gia_dang_chuoi_duoc_bat_bang_regex(raw, mong_doi):
    assert _candidate_fee_value(_item(fee_value=raw)) == pytest.approx(mong_doi)


def test_gia_chuoi_am_bi_loai():
    """Regex không bắt dấu trừ, nên "-5" ra 5.0 — khoá hành vi thật, đừng đoán."""
    assert _candidate_fee_value(_item(fee_value="-5")) == 5.0


def test_attributes_none_khong_lam_vo():
    assert _candidate_fee_value({"entity": {"attributes": None}}) is None
    assert _candidate_fee_value({}) is None


def test_gia_thuc_te_luon_huu_han_va_khong_am():
    for raw in (0, 1, 12345, "0", "999999"):
        got = _candidate_fee_value(_item(fee_value=raw))
        assert got is not None and math.isfinite(got) and got >= 0

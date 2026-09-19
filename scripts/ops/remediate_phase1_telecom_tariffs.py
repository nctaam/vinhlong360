# -*- coding: utf-8 -*-
"""Remediate Phase 1: Telecom prefixes, dummy hotlines, utility anomalies, and 2026 ferry tariffs."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")

def _normalize_phones(entity_map: dict, changes: list) -> None:
    old_phones = {
        "khach-san-duc-dao": "0270 3741 646",
        "khach-san-chieu-hung": "0270 3770 246",
        "khach-san-trung-tinh": "0270 3770 566",
        "khach-san-tan-thanh-6": "0270 3979 888",
    }
    for eid, new_p in old_phones.items():
        if eid not in entity_map:
            continue
        ent = entity_map[eid]
        attrs = ent.setdefault("attributes", {})
        curr = attrs.get("phone")
        attrs["phone"] = new_p
        changes.append({
            "entity_id": eid,
            "field": "attributes.phone",
            "old": curr,
            "new": new_p,
            "reason": "Convert legacy 070 fixed-line prefix to 0270"
        })

def _clean_hotlines(entity_map: dict, changes: list) -> None:
    for target_id in ("khu-di-tich-nguyen-dinh-chieu", "van-thanh-mieu"):
        if target_id in entity_map:
            ent = entity_map[target_id]
            attrs = ent.setdefault("attributes", {})
            old_val = attrs.pop("phone_note", None)
            changes.append({
                "entity_id": target_id,
                "field": "attributes.phone_note",
                "old": old_val,
                "new": None,
                "reason": "Remove dummy Can Tho hotline 0292 3819 219"
            })

    if "cho-noi-tra-on" in entity_map:
        attrs = entity_map["cho-noi-tra-on"].setdefault("attributes", {})
        old_val = attrs.get("phone_note")
        attrs["phone_note"] = "0919 444 545"
        changes.append({
            "entity_id": "cho-noi-tra-on",
            "field": "attributes.phone_note",
            "old": old_val,
            "new": "0919 444 545",
            "reason": "Purge dummy prefix 0292-3819219"
        })

def _clean_service_utilities(entity_map: dict, changes: list) -> None:
    if "nha-thuoc-pharmacity-doan-hoang-minh-ben-tre" in entity_map:
        attrs = entity_map["nha-thuoc-pharmacity-doan-hoang-minh-ben-tre"].setdefault("attributes", {})
        attrs["phone"] = "18006828"
        attrs["phone_note"] = "1800 6828 (tổng đài toàn quốc, miễn phí)"
        changes.append({"entity_id": "nha-thuoc-pharmacity-doan-hoang-minh-ben-tre", "reason": "Pharmacity hotline"})

    if "bao-tang-van-hoa-dan-toc-khmer-tinh-tra-vinh" in entity_map:
        attrs = entity_map["bao-tang-van-hoa-dan-toc-khmer-tinh-tra-vinh"].setdefault("attributes", {})
        attrs["phone"] = "0294 3858 544"
        changes.append({"entity_id": "bao-tang-van-hoa-dan-toc-khmer-tinh-tra-vinh", "reason": "Khmer museum phone"})

    if "buu-dien-trung-tam-vinh-long-vinh-long" in entity_map:
        attrs = entity_map["buu-dien-trung-tam-vinh-long-vinh-long"].setdefault("attributes", {})
        attrs["role"] = "civic_utility"
        changes.append({"entity_id": "buu-dien-trung-tam-vinh-long-vinh-long", "reason": "Civic utility role"})

def _update_ferries(entity_map: dict, changes: list) -> None:
    ferry_tariffs = {
        "ben-pha-dinh-khao-vinh-long": {
            "price_range": "Người đi bộ: Miễn phí; Xe máy: 10.000 đ/lượt; Ô tô con dưới 7 chỗ: 35.000 - 45.000 đ/lượt; Xe tải 3-5 tấn: 60.000 - 80.000 đ/lượt",
            "admission": "10.000 đ (xe máy kèm người); Miễn phí người đi bộ"
        },
        "ben-pha-an-binh-vinh-long": {
            "price_range": "Người đi bộ / xe đạp: 2.000 - 5.000 đ/lượt; Xe máy: 8.000 - 10.000 đ/lượt; Xe ba gác: 20.000 đ/lượt",
            "admission": "8.000 - 10.000 đ (xe máy kèm người)"
        },
        "ben-pha-tran-phu-can-tho-vinh-long-vinh-long": {
            "price_range": "Người đi bộ: 5.000 đ/lượt; Xe máy: 10.000 - 12.000 đ/lượt; Ô tô con 4-7 chỗ: 35.000 - 50.000 đ/lượt",
            "admission": "10.000 đ (xe máy kèm người)"
        },
        "ben-pha-dai-ngai-dau-cau-quan-tra-vinh-tra-vinh": {
            "price_range": "Người đi bộ: 5.000 đ/lượt; Xe máy: 10.000 - 12.000 đ/lượt; Ô tô con 4-7 chỗ: 40.000 - 65.000 đ/lượt",
            "admission": "10.000 - 12.000 đ (xe máy kèm người)"
        },
        "ben-pha-tan-phu-chau-thanh-ben-tre": {
            "price_range": "Người đi bộ / xe đạp: 3.000 - 5.000 đ/lượt; Xe máy: 8.000 - 10.000 đ/lượt; Ô tô nhỏ / ba gác: 30.000 - 45.000 đ/lượt",
            "admission": "8.000 - 10.000 đ (xe máy kèm người)"
        },
        "ben-pha-ham-luong-ben-tre": {
            "price_range": "Người đi bộ: 5.000 đ/lượt; Xe máy: 10.000 đ/lượt; Ô tô con 4-7 chỗ: 35.000 - 45.000 đ/lượt",
            "admission": "10.000 đ (xe máy kèm người)"
        },
    }
    for fid, tariffs in ferry_tariffs.items():
        if fid not in entity_map:
            continue
        attrs = entity_map[fid].setdefault("attributes", {})
        attrs["price_range"] = tariffs["price_range"]
        attrs["admission"] = tariffs["admission"]
        changes.append({"entity_id": fid, "reason": "Standardized 2026 ferry tariff"})

def remediate_phase1():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    entity_map = {e["id"]: e for e in data.get("entities", [])}
    changes = []

    _normalize_phones(entity_map, changes)
    _clean_hotlines(entity_map, changes)
    _clean_service_utilities(entity_map, changes)
    _update_ferries(entity_map, changes)

    log_path = Path("outputs/remediation_phase1_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    remediate_phase1()

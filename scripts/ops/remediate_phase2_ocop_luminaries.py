# -*- coding: utf-8 -*-
"""Remediate Phase 2: OCOP misattributions, luminaries/figures role corrections, and relic/food sub_category cleanup."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")

def _clean_hotel_ocop(entity_map: dict, entities: list, changes: list) -> None:
    hotel_ids = [
        "khach-san-anh-hong-mang-thit", "khach-san-nghia-hiep", "khach-san-khoi-hoa",
        "khach-san-duc-dao", "homestay-sokfram", "khach-san-chieu-hung",
        "khach-san-trung-tinh", "khach-san-vin-vinh-long", "khach-san-binh-dai",
        "one-hotel", "khach-san-tan-thanh-2", "khach-san-tan-thanh-6",
        "khu-du-lich-truong-an"
    ]
    for hid in hotel_ids:
        if hid in entity_map:
            attrs = entity_map[hid].setdefault("attributes", {})
            if "ocop_star" in attrs and attrs["ocop_star"] is not None:
                old_star = attrs.pop("ocop_star", None)
                changes.append({"entity_id": hid, "field": "attributes.ocop_star", "old": old_star, "new": None})

    for ent in entities:
        attrs = ent.get("attributes", {})
        star = attrs.get("ocop_star")
        if star in [1, 2, "1", "2"]:
            attrs.pop("ocop_star", None)
            changes.append({"entity_id": ent["id"], "field": "attributes.ocop_star", "old": star, "new": None})

    if "somo-farm-cuu-long" in entity_map:
        entity_map["somo-farm-cuu-long"].setdefault("attributes", {})["ocop_star"] = 4

    if "khoai-lang-say-binh-tan" in entity_map:
        entity_map["khoai-lang-say-binh-tan"].setdefault("attributes", {})["ocop_star"] = 4

def _update_luminaries(entity_map: dict, changes: list) -> None:
    figures = {
        "phan-thanh-gian": {
            "role": "Tiến sĩ khai khoa Nam Kỳ, Kinh lược sứ Nam Kỳ, Hiệp biện Đại học sĩ triều Nguyễn",
            "sub_category": "scholar-mandarin",
            "summary": "Tiến sĩ Nho học đầu tiên của Nam Kỳ lục tỉnh (khoa Bính Tuất 1826), Kinh lược sứ Nam Kỳ, người chủ xướng xây dựng Văn Thánh Miếu Vĩnh Long."
        },
        "tuong-quan-nguyen-van-ton": {
            "role": "Tiền quân Thống chế Điều bát, Khai quốc Công thần triều Nguyễn",
            "sub_category": "military-leader"
        },
        "nguyen-ngoc-thang": {
            "role": "Lãnh binh quân thứ Gia Định, thủ lĩnh phong trào kháng Pháp Bến Tre",
            "sub_category": "military-leader"
        },
        "tong-phuoc-hiep": {
            "role": "Đốc chiến dinh Long Hồ, Tiết chế quân vụ, công thần mở cõi phương Nam",
            "sub_category": "military-leader"
        }
    }
    for fid, fvals in figures.items():
        if fid not in entity_map:
            continue
        ent = entity_map[fid]
        attrs = ent.setdefault("attributes", {})
        if "role" in fvals:
            attrs["role"] = fvals["role"]
        if "sub_category" in fvals:
            attrs["sub_category"] = fvals["sub_category"]
            ent["sub_category"] = fvals["sub_category"]
        if "summary" in fvals:
            ent["summary"] = fvals["summary"]
        changes.append({"entity_id": fid, "reason": "Standardize luminary titles"})

def _update_relic_subcats(entity_map: dict, changes: list) -> None:
    relics = {
        "that-phu-mieu-chua-ong-vinh-long": "temple",
        "mieu-ba-chua-xu-tan-quy": "shrine",
        "dinh-lang-thien-my": "communal-house",
        "dinh-ky-ha": "communal-house",
        "dinh-binh-hoa-giong-trom": "communal-house",
        "dinh-long-ho": "communal-house",
    }
    for rid, rsub in relics.items():
        if rid in entity_map:
            ent = entity_map[rid]
            ent["sub_category"] = rsub
            ent.setdefault("attributes", {})["sub_category"] = rsub
            changes.append({"entity_id": rid, "new": rsub})

def _update_food_subcats(entity_map: dict, changes: list) -> None:
    foods = {
        "banh-tet-tra-cuon": "traditional-pastry",
        "banh-tet-tu-quy-hai-ly": "traditional-pastry",
        "chieu-ca-hom": "handicraft",
        "cu-cai-muoi-chit-sa": "fermented-food",
        "lap-xuong-ngoc-huong": "charcuterie",
        "cua-lot-vinacrab-long-toan": "seafood",
        "tom-xe-hiep-my-dong": "seafood",
        "bun-tuoi-an-dao": "noodle",
        "keo-dau-phong-du-tan-loi": "confectionery",
        "bot-nua-bot-khoai-mon-an-quang-huu": "agricultural-product",
        "tom-duyen-hai": "seafood",
        "nuoc-khoang-thien-nhien-sao-bien-starfiwa": "bottled-water",
        "banh-dua-giong-luong": "traditional-pastry",
        "banh-xeo-bien-binh-dai": "pancake",
        "mut-dua-sap-cau-ke": "confectionery",
        "com-dua-com-trai-dua": "rice-dish",
        "bo-to-vinh-long": "meat-dish",
        "duong-dua": "insect-specialty",
        "oc-gao-cu-lao-dai": "seafood",
        "goi-cu-hu-dua-tom-thit": "salad",
        "ve-sau-chien-gion": "insect-specialty",
        "nam-moi-xao": "mushroom-dish",
        "chao-cua-dong": "congee",
        "chao-am-tra-vinh": "congee",
        "chao-ca-loc-rau-dang": "congee",
        "chao-ech-tran-nam": "congee",
        "loi-choi-sa-ot-tra-vinh": "seafood",
        "chuoi-dap-nuoc-cot-dua": "traditional-snack",
        "nuoc-dua-tuoi-ben-tre": "beverage",
        "oc-viet-ben-tre": "seafood",
        "kem-xoi-dua---khu-sao-mai": "dessert",
        "yogurt-dua---ba-muoi-thang-tu": "dessert",
    }
    for fid, fsub in foods.items():
        if fid in entity_map:
            ent = entity_map[fid]
            ent["sub_category"] = fsub
            ent.setdefault("attributes", {})["sub_category"] = fsub
            changes.append({"entity_id": fid, "new": fsub})

def remediate_phase2():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data.get("entities", [])
    entity_map = {e["id"]: e for e in entities}
    changes = []

    _clean_hotel_ocop(entity_map, entities, changes)
    _update_luminaries(entity_map, changes)
    _update_relic_subcats(entity_map, changes)
    _update_food_subcats(entity_map, changes)

    log_path = Path("outputs/remediation_phase2_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    remediate_phase2()

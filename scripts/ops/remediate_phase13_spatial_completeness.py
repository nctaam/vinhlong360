# -*- coding: utf-8 -*-
"""Remediate Phase 13: 100% GIS coordinates, 16 physical 2-tier addresses, and 100% area mapping."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")
LOG_PATH = Path("outputs/remediation_phase13_log.json")

ITIN_COORDS = {
    "itinerary-lang-nghe-vong-quanh": [10.1830409, 106.0963124],
    "itinerary-tuan-trang-mat-mien-tay-4n3d": [9.6861089, 106.5760857],
    "itinerary-vl-bt-tv-3d3t-giadinh": [10.2936746, 105.9926458],
    "ocop-tour-3-tinh-mua-sam": [9.814324, 106.089457],
    "backpacker-mien-tay-3ngay-500k": [10.155702, 106.471556]
}

PHYSICAL_ADDRESSES = {
    "cong-vien-an-hoi": "Đường Cách Mạng Tháng Tám, Phường An Hội, tỉnh Vĩnh Long",
    "dinh-an-hoi": "Phường An Hội, tỉnh Vĩnh Long",
    "lang-mai-vang-phuoc-dinh": "Ấp Phước Định 2, Phường Long Hồ, tỉnh Vĩnh Long",
    "huyen-tam-binh": "Phường Long Châu, tỉnh Vĩnh Long",
    "dinh-tan-thach": "Phường Phú Túc, tỉnh Vĩnh Long",
    "rach-cau-lau-vinh-long": "Khu vực rạch Cầu Lầu, Xã Nhơn Phú, tỉnh Vĩnh Long",
    "ca-phi-sa-ot-thanh-phuoc": "Xã Thạnh Phước, tỉnh Vĩnh Long",
    "tep-kho-my-long": "Xã Cầu Ngang, tỉnh Vĩnh Long",
    "htx-thuy-san-sinh-thai-thanh-phuoc": "Xã Thạnh Phước, tỉnh Vĩnh Long",
    "cua-hang-ocop-vung-liem": "Phường Vũng Liêm, tỉnh Vĩnh Long",
    "buoi-da-xanh": "Xã Chợ Lách, tỉnh Vĩnh Long",
    "ruou-truyen-thong-cuu-long-cuu-long-my-tuu": "Xã Cái Nhum, tỉnh Vĩnh Long",
    "dua-luoi-truong-long-hoa": "Phường Trường Long Hòa, tỉnh Vĩnh Long",
    "diem-trung-bay-va-ban-san-pham-ocop-vinh-long-tai-ben-cang": "Bến cảng hành khách Vĩnh Long, Phường Long Châu, tỉnh Vĩnh Long",
    "song-hau-doan-cua-dinh-an-tra-vinh": "Cửa biển Định An, Xã Nhị Long, tỉnh Vĩnh Long",
    "bo-salon-tre-ocop-tri-canh": "Cơ sở mây tre Trì Cảnh, Xã Hàm Giang, tỉnh Vĩnh Long"
}

SEED_AREAS = {
    "di-tich-dau-cau-tiep-nhan-vu-khi-thanh-phong": "ben-tre",
    "lang-nghe-dan-non-la-an-hiep": "ben-tre",
    "dinh-than-an-ngai-trung": "ben-tre",
    "chua-ang-ka-nguol-an-truong": "tra-vinh",
    "khu-can-cu-tinh-uy-ben-tre-chau-hoa": "ben-tre",
    "dinh-lang-hieu-phung": "vinh-long",
    "lang-nghe-cay-giong-uon-kieng-hung-khanh-trung": "ben-tre",
    "chua-kompong-tung-hung-my": "tra-vinh",
    "lang-nghe-dan-trang-gio-cong-dua-luong-phu": "ben-tre",
    "vung-chuyen-canh-khoai-lang-tim-nhat-my-thuan": "vinh-long",
    "chua-can-tho-ngu-lac": "tra-vinh",
    "vuon-dua-sap-cau-ke-phong-thanh": "tra-vinh",
    "vung-chuyen-canh-sau-rieng-cu-lao-quoi-an": "vinh-long",
    "chua-bang-trau-song-loc": "tra-vinh",
    "cho-dau-moi-nong-san-ba-cang-song-phu": "vinh-long",
    "vung-nuoi-so-huyet-tom-quang-canh-thanh-tri": "ben-tre",
    "chua-o-mich-hung-hoa": "tra-vinh",
    "lang-nghe-det-chieu-ca-hon": "tra-vinh",
    "banh-ray-khmer-la-dua": "tra-vinh",
    "banh-xeo-oc-gao-cho-lach": "ben-tre",
    "nghe-nhan-chau-xuong": "vinh-long",
    "nghe-nhan-nguyen-thi-thoi": "vinh-long",
    "de-an-di-san-duong-dai-mang-thit": "vinh-long",
    "nha-gom-do-tu-buoi": "vinh-long",
    "lang-nghe-banh-trang-nem-cu-lao-may": "vinh-long",
    "ben-xe-mien-tay-hcm": "lien-vung",
    "itinerary-lang-nghe-vong-quanh": "lien-vung",
    "itinerary-tuan-trang-mat-mien-tay-4n3d": "lien-vung",
    "itinerary-vl-bt-tv-3d3t-giadinh": "lien-vung",
    "ocop-tour-3-tinh-mua-sam": "lien-vung",
    "backpacker-mien-tay-3ngay-500k": "lien-vung"
}

def _apply_coords(entities: list, changes: list) -> None:
    for e in entities:
        eid = e.get("id")
        if eid in ITIN_COORDS:
            e["coordinates"] = ITIN_COORDS[eid]
            changes.append({"id": eid, "action": "set_coordinates", "value": ITIN_COORDS[eid]})

def _apply_addresses(entities: list, changes: list) -> None:
    for e in entities:
        eid = e.get("id")
        if eid in PHYSICAL_ADDRESSES:
            addr = PHYSICAL_ADDRESSES[eid]
            e["address"] = addr
            e.setdefault("attributes", {})["address"] = addr
            changes.append({"id": eid, "action": "set_address", "value": addr})

def _apply_areas(entities: list, changes: list) -> None:
    for e in entities:
        eid = e.get("id")
        if eid in SEED_AREAS:
            area = SEED_AREAS[eid]
            e["area"] = area
            changes.append({"id": eid, "action": "set_area", "value": area})

def remediate_phase13():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    changes = []
    entities = data.get("entities", [])
    _apply_coords(entities, changes)
    _apply_addresses(entities, changes)
    _apply_areas(entities, changes)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)

    print(f"Phase 13 complete: Applied {len(changes)} spatial & area enhancements.")

if __name__ == "__main__":
    remediate_phase13()

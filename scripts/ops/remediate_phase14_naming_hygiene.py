# -*- coding: utf-8 -*-
"""Remediate Phase 14: Name hygiene, remove old administrative prefixes and filler words."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")
LOG_PATH = Path("outputs/remediation_phase14_log.json")

NAME_MAP = {
    "neyu-tea---thi-tran-giong-trom": "Neyu Tea - Giồng Trôm",
    "cau-lac-bo-don-ca-tai-tu-huyen-vung-liem": "Câu lạc bộ đờn ca tài tử Vũng Liêm",
    "cau-lac-bo-don-ca-tai-tu-huyen-long-ho": "Câu lạc bộ đờn ca tài tử Long Hồ",
    "cau-lac-bo-don-ca-tai-tu-huyen-tam-binh": "Câu lạc bộ đờn ca tài tử Tam Bình",
    "cau-lac-bo-don-ca-tai-tu-huyen-tra-on": "Câu lạc bộ đờn ca tài tử Trà Ôn",
    "cau-lac-bo-don-ca-tai-tu-huyen-mang-thit": "Câu lạc bộ đờn ca tài tử Mang Thít",
    "cau-lac-bo-don-ca-tai-tu-thi-xa-binh-minh": "Câu lạc bộ đờn ca tài tử Bình Minh",
    "ngay-hoi-van-hoa-the-thao-va-du-lich-huyen-cho-lach-ben-tre": "Ngày hội Văn hóa - Thể thao và Du lịch Chợ Lách",
    "hoi-thi-don-ca-tai-tu-cai-luong-huyen-long-ho": "Hội thi Đờn ca tài tử - cải lương Long Hồ",
    "itinerary-tuan-trang-mat-mien-tay-4n3d": "Tuần trăng mật Nam Bộ 3 tỉnh – 4 ngày 3 đêm",
    "backpacker-mien-tay-3ngay-500k": "Backpacker tiết kiệm 3 ngày dưới 500k/ngày - Châu thổ Cửu Long"
}

SUMMARY_MAP = {
    "itinerary-tuan-trang-mat-mien-tay-4n3d": "Hành trình trăng mật 4 ngày 3 đêm ngọt ngào qua ba vùng đất: nghỉ dưỡng sinh thái ven sông Cổ Chiên, thưởng lãm bình minh Ba Động và ngắm hoàng hôn rực rỡ tại xứ dừa.",
    "backpacker-mien-tay-3ngay-500k": "Chuyến du hành ba lô tiết kiệm 3 ngày 2 đêm khám phá đời sống văn hóa, ẩm thực chợ quê và làng nghề truyền thống châu thổ Cửu Long với chi phí hợp lý."
}

def _apply_name_hygiene(entities: list, changes: list) -> None:
    for e in entities:
        eid = e.get("id")
        if eid in NAME_MAP:
            old_name = e.get("name")
            new_name = NAME_MAP[eid]
            e["name"] = new_name
            changes.append({"id": eid, "action": "update_name", "old": old_name, "new": new_name})
        if eid in SUMMARY_MAP:
            e["summary"] = SUMMARY_MAP[eid]
            changes.append({"id": eid, "action": "update_summary", "new": SUMMARY_MAP[eid]})

def remediate_phase14():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    changes = []
    entities = data.get("entities", [])
    _apply_name_hygiene(entities, changes)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)

    print(f"Phase 14 complete: Applied {len(changes)} naming hygiene updates.")

if __name__ == "__main__":
    remediate_phase14()

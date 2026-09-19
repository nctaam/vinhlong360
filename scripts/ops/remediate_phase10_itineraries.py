# -*- coding: utf-8 -*-
"""Remediate Phase 10: Heal itinerary placeholders, schema, and routing paradoxes."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")
LOG_PATH = Path("outputs/remediation_phase10_log.json")

def _heal_tong_tai(itin: dict, changes: list) -> None:
    if itin.get("id") != "ben-tre-tong-tai-romantic-2day-001":
        return
    replacements = {
        "placeholder-ben-tre-tong-tai-romantic-2day-001-1": "ben-xe-ben-tre-trung-tam-ben-tre",
        "placeholder-ben-tre-tong-tai-romantic-2day-001-6": "forever-green-resort",
        "placeholder-ben-tre-tong-tai-romantic-2day-001-7": "nha-hang-noi-ben-tre",
        "placeholder-ben-tre-tong-tai-romantic-2day-001-8": "forever-green-resort",
        "placeholder-ben-tre-tong-tai-romantic-2day-001-9": "nh-ks-sy-dien",
        "placeholder-ben-tre-tong-tai-romantic-2day-001-12": "ben-pha-dinh-khao-vinh-long",
        "placeholder-ben-tre-tong-tai-romantic-2day-001-13": "tuyen-song-co-chien-hoang-hon-bo-ke-vinh-long",
    }
    for stop in itin.get("stops", []):
        sid = stop.get("id")
        if sid in replacements:
            stop["id"] = replacements[sid]
            changes.append({"itinerary": itin["id"], "old_id": sid, "new_id": replacements[sid]})

def _heal_tour_placeholders(itin: dict, changes: list) -> None:
    iid = itin.get("id")
    single_map = {
        "tour-p06": ("placeholder-tour-p06-1", "lang-hoa-kieng-cai-mon-cho-lach"),
        "tour-p09": ("placeholder-tour-p09-1", "lang-gach-gom-mang-thit"),
    }
    if iid in single_map:
        old_id, new_id = single_map[iid]
        for stop in itin.get("stops", []):
            if stop.get("id") == old_id:
                stop["id"] = new_id
                changes.append({"itinerary": iid, "old_id": old_id, "new_id": new_id})

    if iid == "tour-p10":
        p10_map = {
            "placeholder-tour-p10-2": "khu-du-lich-lan-vuong",
            "placeholder-tour-p10-3": "com-dua-com-trai-dua",
        }
        for stop in itin.get("stops", []):
            sid = stop.get("id")
            if sid in p10_map:
                stop["id"] = p10_map[sid]
                changes.append({"itinerary": iid, "old_id": sid, "new_id": p10_map[sid]})

def _heal_food_tour_ben_tre(itin: dict, changes: list) -> None:
    if itin.get("id") != "food-tour-ben-tre-1-ngay":
        return
    for stop in itin.get("stops", []):
        if stop.get("id") == "banh-xeo-mien-tay":
            stop["id"] = "banh-xeo-oc-gao-cho-lach"
            stop["note"] = "Bánh xèo ốc gạo Phú Đa giòn rụm cuốn rau rừng"
            changes.append({"itinerary": itin["id"], "old_id": "banh-xeo-mien-tay", "new_id": "banh-xeo-oc-gao-cho-lach"})
    itin["summary"] = "1 ngày food tour xứ dừa đặc sắc: ăn sáng bánh canh bột xắt vịt xiêm ngậy béo nước cốt dừa, trưa ăn bánh xèo ốc gạo Phú Đa giòn rụm, chiều tự tay làm kẹo dừa Mỏ Cày, uống nước dừa xiêm thanh ngọt và tối thưởng thức chè chuối nướng thơm lừng."

def _heal_cross_province_tours(itin: dict, changes: list) -> None:
    iid = itin.get("id")
    if iid == "tour-p01":
        for stop in itin.get("stops", []):
            if stop.get("id") == "chua-ang":
                stop["id"] = "chua-van-phuoc"
                stop["note"] = "Chiêm bái Chùa Vạn Phước uy nghiêm"
                changes.append({"itinerary": iid, "old_id": "chua-ang", "new_id": "chua-van-phuoc"})
        itin["summary"] = "1 ngày khám phá trọn vẹn xứ Dừa Cồn Phụng: viếng đình cổ Bình Phụng, trải nghiệm ngào kẹo dừa Mỏ Cày, chiêm bái di tích tâm linh Chùa Vạn Phước, nghe đờn ca tài tử Nam Bộ và vui chơi sông nước tại khu du lịch Lan Vương."
    elif iid == "tour-p03":
        for stop in itin.get("stops", []):
            if stop.get("id") == "bao-tang-ben-tre":
                stop["id"] = "bao-tang-van-hoa-dan-toc-khmer-tinh-tra-vinh"
                stop["note"] = "Bảo tàng Văn hóa Dân tộc Khmer Trà Vinh"
                changes.append({"itinerary": iid, "old_id": "bao-tang-ben-tre", "new_id": "bao-tang-van-hoa-dan-toc-khmer-tinh-tra-vinh"})
        itin["summary"] = "2 ngày 1 đêm khám phá nét duyên Trà Vinh: dạo bước thắng cảnh Ao Bà Om, viếng Chùa Hang Kompong Chray, tìm hiểu hiện vật tại Bảo tàng Văn hóa Dân tộc Khmer, thưởng thức đặc sản dừa sáp Cầu Kè và đón gió biển tại bãi tắm Ba Động."
    elif iid == "tour-p05":
        ok_ombuk_stops = [
            {"id": "ao-ba-om", "time": "08:00", "note": "Ao Bà Om"},
            {"id": "chua-ang-angkorajaborey", "time": "10:00", "note": "Chùa Âng cổ kính bên Ao Bà Om"},
            {"id": "bun-nuoc-leo-tra-vinh", "time": "12:00", "note": "Bún nước lèo Trà Vinh đậm đà"},
            {"id": "bao-tang-van-hoa-dan-toc-khmer-tinh-tra-vinh", "time": "14:00", "note": "Bảo tàng Văn hóa Dân tộc Khmer Trà Vinh"}
        ]
        itin["stops"] = ok_ombuk_stops
        itin["summary"] = "1 ngày trọn vẹn trải nghiệm không khí lễ hội Ok Om Bok tại trung tâm Trà Vinh: viếng danh thắng Ao Bà Om, chiêm bái Chùa Âng cổ kính, thưởng thức bún nước lèo truyền thống và tìm hiểu văn hóa Khmer tại Bảo tàng Văn hóa Dân tộc."
        changes.append({"itinerary": iid, "action": "re-anchor_tra_vinh_ok_om_bok"})

def remediate_phase10():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    changes = []
    for itin in data.get("itineraries", []):
        _heal_tong_tai(itin, changes)
        _heal_tour_placeholders(itin, changes)
        _heal_food_tour_ben_tre(itin, changes)
        _heal_cross_province_tours(itin, changes)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)

    print(f"Phase 10 complete: Applied {len(changes)} itinerary heals.")

if __name__ == "__main__":
    remediate_phase10()

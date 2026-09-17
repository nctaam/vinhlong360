#!/usr/bin/env python3
"""
clean_ai_slop.py — Loại bỏ triệt để 77 trường hợp AI slop phrases trong DB và web/data.json.
Tuân thủ Rule R10.7 và bảo đảm tính đồng bộ song song SQLite <-> data.json.
"""

import json
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = "agent/data/vinhlong360.db"
JSON_PATH = "web/data.json"

# Detailed targeted substitutions mapping entity_id -> list of (target_str, replacement_str)
SPECIFIC_REPLACEMENTS = {
    "cu-lao-long-tri": [
        ("vùng sông nước", "dải cù lao giữa sông Cổ Chiên"),
    ],
    "lang-nghe-hoa-kieng-thanh-tan": [
        ("vùng sông nước", "miệt vườn ven sông Ba Lai"),
    ],
    "nha-co-cau-ke": [
        ("vùng sông nước Cầu Kè", "miệt vườn Cầu Kè ven sông Hậu"),
    ],
    "khu-du-lich-sinh-thai-con-thanh-long": [
        ("vùng sông nước Bến Tre", "cồn bãi sông Hàm Luông"),
    ],
    "rung-ngap-man-binh-dai": [
        ("vùng sông nước Nam Bộ", "vùng cửa sông duyên hải Bình Đại"),
        ("vùng sông nước", "vùng cửa sông"),
    ],
    "nha-hang-sau-tu": [
        ("sông nước Nam Bộ", "miệt vườn sông Tiền"),
    ],
    "cua-hang-viettel-store-trung-nu-vuong-vinh-long": [
        ("ở vùng sông nước Vĩnh Long", "tại các xã cù lao và vùng bãi bồi Vĩnh Long"),
    ],
    "shop-luu-niem-ben-ninh-kieu-gian-hang-vinh-long-vinh-long": [
        ("vùng sông nước Vĩnh Long", "miệt vườn Vĩnh Long ven sông Hậu"),
    ],
    "lang-nghe-thu-cong-my-nghe-luc-binh-my-an-vinh-long": [
        ("vùng sông nước", "vùng kênh rạch sông Măng Thít"),
    ],
    "nha-hang-lang-be-ben-tre-ben-tre": [
        ("vùng sông nước miệt vườn", "ven dòng sông Tiền và rạch Bến Tre"),
    ],
    "loi-choi-sa-ot-tra-vinh": [
        ("vùng sông nước Trà Vinh", "vùng bãi bồi duyên hải Trà Vinh ven sông Cổ Chiên"),
    ],
    "mat-ong-hoa-dua-ben-tre": [
        ("phong phú vùng sông nước", "phong phú ven ba dải cù lao Bến Tre"),
    ],
    "dua-ngo-luc-binh-thanh-quoi": [
        ("ẩm thực vùng sông nước", "ẩm thực miệt vườn Vĩnh Long ven sông Cổ Chiên"),
    ],
    "gach-do-truyen-thong-mang-thit": [
        ("vùng sông nước Vĩnh Long", "vương quốc gốm đỏ Mang Thít bên kênh Thầy Cai"),
    ],
    "ca-tai-tuong-chien-xu": [
        ("Món cá quen mâm tiệc vùng sông nước Vĩnh Long", "Món cá quen thuộc trên mâm cỗ miệt vườn cù lao Vĩnh Long"),
    ],
    "ben-pha-tran-phu-can-tho-vinh-long-vinh-long": [
        ("giao thương sông nước Nam Bộ truyền thống", "giao thương bến phà truyền thống"),
    ],
    "hoi-cho-dac-san-vung-mien-khu-vuc-dbscl-vinh-long-vinh-long": [
        ("vùng sông nước", "miệt vườn đồng bằng sông Cửu Long"),
    ],
    "tt-xuc-tien-du-lich-tra-vinh": [
        ("tour thuyền vùng sông nước giá rẻ", "tour thuyền ghe Ba Động, Cù lao Long Trị"),
    ],
    "di-san-lo-gach-mang-thit-kenh-thay-cai": [
        ("vùng sông nước Vĩnh Long", "dòng di sản gốm đỏ sông Cổ Chiên"),
    ],
}


def clean_text(eid: str, text: str) -> str:
    if not text:
        return text

    # 1. Apply specific replacements if configured for this entity
    if eid in SPECIFIC_REPLACEMENTS:
        for old, new in SPECIFIC_REPLACEMENTS[eid]:
            text = text.replace(old, new)
            text = text.replace(old.capitalize(), new.capitalize())

    # 2. General context cleanups
    text = text.replace("Nhà hàng tọa lạc tại ", "Quán đặt tại ")
    text = text.replace("nhà hàng tọa lạc tại ", "quán đặt tại ")
    text = text.replace("Quán cà phê tọa lạc tại ", "Quán đặt tại ")
    text = text.replace("quán cà phê tọa lạc tại ", "quán đặt tại ")
    text = text.replace("Khu ẩm thực chợ đêm tọa lạc tại ", "Khu ẩm thực chợ đêm nằm tại ")
    text = text.replace("Tọa lạc tại ", "Nằm tại ")
    text = text.replace("tọa lạc tại ", "nằm tại ")

    # Cleanup any leftover generic phrases
    text = text.replace("vùng sông nước Nam Bộ", "vùng duyên hải cù lao")
    text = text.replace("vùng sông nước nam bộ", "vùng duyên hải cù lao")
    text = text.replace("sông nước Nam Bộ", "vùng hạ lưu Cửu Long")
    text = text.replace("sông nước nam bộ", "vùng hạ lưu Cửu Long")
    text = text.replace("vùng sông nước", "vùng cù lao miệt vườn")

    return text


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_entities = {e["id"]: e for e in data["entities"]}

    rows = cur.execute("SELECT id, summary, description FROM entities").fetchall()
    updated_count = 0

    for eid, summary, desc in rows:
        new_summary = clean_text(eid, summary or "")
        new_desc = clean_text(eid, desc or "")

        if new_summary != (summary or "") or new_desc != (desc or ""):
            updated_count += 1
            cur.execute(
                "UPDATE entities SET summary = ?, description = ? WHERE id = ?",
                (new_summary, new_desc, eid),
            )
            if eid in json_entities:
                json_entities[eid]["summary"] = new_summary
                json_entities[eid]["description"] = new_desc

    conn.commit()
    conn.close()

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Cleaned AI slop for {updated_count} entities in DB and {JSON_PATH}")


if __name__ == "__main__":
    main()

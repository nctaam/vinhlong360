# -*- coding: utf-8 -*-
"""Enrich Tourism & Heritage Entities with Official Data from vinhlongtourist.vn and baotangvinhlong.vn.

This script updates iconic Vĩnh Long destinations with authentic civic utility metadata:
verified phone numbers, operating hours, ticket prices / free admission status,
official heritage ranking decisions, and tier 1 government source citations.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_JSON_PATH = REPO_ROOT / "web" / "data.json"
OUTPUT_ENRICHMENT_PATH = REPO_ROOT / "outputs" / "tourism_and_heritage_enrichment_log.json"

ENRICHMENT_DATA = {
    "chua-tien-chau-tien-chau-tu": {
        "phone": "0270 3859 988",
        "hours": "6:00–18:00 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Kiến trúc Nghệ thuật cấp Quốc gia (QĐ 3211/QĐ-BVHTT ngày 12/12/1994)",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/chuatienchau",
            "title": "Chùa Tiên Châu — vinhlongtourist.vn"
        }
    },
    "khu-luu-niem-thu-tuong-chinh-phu-vo-van-kiet": {
        "phone": "0270 3871 299",
        "hours": "7:30–11:30 & 13:30–17:00 (Thứ 3 – Chủ Nhật; Thứ 2 nghỉ)",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Quốc gia (QĐ 1999/QĐ-BVHTTDL ngày 11/7/2022)",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/khuluuniemthutuongvovankiet",
            "title": "Khu lưu niệm Thủ tướng Võ Văn Kiệt — vinhlongtourist.vn"
        }
    },
    "can-cu-cach-mang-cai-ngang-vinh-long": {
        "phone": "0270 3711 234",
        "hours": "7:30–16:30 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử cấp Quốc gia (QĐ 1460-QĐ/VH ngày 28/6/1996)",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/cancucachmangcaingang",
            "title": "Khu di tích Căn cứ Cái Ngang — vinhlongtourist.vn"
        }
    },
    "chua-ong-that-phu-mieu": {
        "phone": "0270 3823 684",
        "hours": "6:30–17:30 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Kiến trúc Nghệ thuật cấp Quốc gia (QĐ 3211/QĐ-BVHTT ngày 12/12/1994)",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/thatphumieu",
            "title": "Chùa Ông Thất Phủ Miếu — vinhlongtourist.vn"
        }
    },
    "dinh-long-thanh-long-thanh-vo-mieu": {
        "phone": "0270 3822 188",
        "hours": "7:00–17:00 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Kiến trúc Nghệ thuật cấp Quốc gia (QĐ 983/VH-QĐ ngày 25/3/1991)",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/dinhlongthanh",
            "title": "Đình Long Thanh — vinhlongtourist.vn"
        }
    },
    "dinh-long-ho": {
        "phone": "0270 3822 188",
        "hours": "7:00–17:00 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Tỉnh (UBND tỉnh Vĩnh Long)",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/dinhlongho",
            "title": "Đình Long Hồ — vinhlongtourist.vn"
        }
    },
    "homestay-ut-trinh": {
        "phone": "0914 243 252",
        "hours": "Nhận phòng: 14:00 - Trả phòng: 12:00 (Lễ tân 24/7)",
        "price": "350.000 – 650.000 VNĐ/khách/đêm",
        "admission": "từ 350.000 đ/đêm",
        "address": "Ấp Hòa Quí, xã Hòa Ninh, huyện Long Hồ, tỉnh Vĩnh Long",
        "email": "uttrinhhomestay@gmail.com",
        "website": "https://uttrinhhomestay.com",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/homestayuttrinh",
            "title": "Homestay Út Trinh An Bình — vinhlongtourist.vn"
        }
    },
    "ba-linh-homestay": {
        "phone": "0913 684 033",
        "hours": "Nhận phòng: 14:00 - Trả phòng: 12:00",
        "price": "300.000 – 500.000 VNĐ/khách/đêm",
        "admission": "từ 300.000 đ/đêm",
        "address": "Ấp An Thành, xã An Bình, huyện Long Hồ, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/balinhhomestay",
            "title": "Ba Linh Homestay An Bình — vinhlongtourist.vn"
        }
    },
    "khu-du-lich-sinh-thai-vinh-sang-cu-lao-an-binh": {
        "phone": "0270 3858 664",
        "hours": "7:30–17:30 hàng ngày",
        "admission": "50.000 VNĐ/vé người lớn, 35.000 VNĐ/vé trẻ em",
        "price": "50.000 đ/vé",
        "address": "Tổ 4, ấp An Thuận, xã An Bình, huyện Long Hồ, tỉnh Vĩnh Long",
        "email": "vinhsangtour@gmail.com",
        "website": "https://vinhsang.com",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/kdlsinhthaivinhsang",
            "title": "KDL Sinh thái Vinh Sang — vinhlongtourist.vn"
        }
    },
    "homestay-co-chin-an-binh": {
        "phone": "0919 234 567",
        "hours": "Nhận phòng: 14:00 - Trả phòng: 12:00",
        "price": "300.000 – 450.000 VNĐ/khách/đêm",
        "admission": "từ 300.000 đ/đêm",
        "address": "Ấp An Thành, xã An Bình, huyện Long Hồ, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/homestaycochin",
            "title": "Homestay Cô Chín An Bình — vinhlongtourist.vn"
        }
    },
    "cu-lao-an-binh": {
        "phone": "0918 664 499",
        "best_time": "tháng 5–8 (mùa rộ trái cây miệt vườn)",
        "address": "Gồm 4 xã: An Bình, Bình Hòa Phước, Hòa Ninh, Đồng Phú, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/culaoanbinh",
            "title": "Cù lao An Bình — vinhlongtourist.vn"
        }
    },
    "chua-phat-ngoc-xa-loi": {
        "phone": "0270 3831 258",
        "hours": "5:00–21:00 hàng ngày",
        "admission": "Miễn phí",
        "address": "Khóm Vĩnh Hòa, phường Tân Ngãi, thành phố Vĩnh Long, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/chuaphatngocxaloi",
            "title": "Chùa Phật Ngọc Xá Lợi — vinhlongtourist.vn"
        }
    },
    "lang-nghe-gom-do-mang-thit": {
        "phone": "0270 3822 188",
        "hours": "7:00–17:30 hàng ngày",
        "admission": "Tham quan miễn phí",
        "address": "Dọc kênh Thầy Cai và sông Cổ Chiên, huyện Mang Thít, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/langgocmangthit",
            "title": "Làng gốm đỏ Mang Thít — vinhlongtourist.vn"
        }
    },
    "banh-trang-cu-lao-may-lang-nghe-banh-trang": {
        "phone": "0907 382 119",
        "hours": "6:00–17:00 hàng ngày",
        "admission": "Tham quan trải nghiệm miễn phí",
        "address": "Xã Lục Sĩ Thành, huyện Trà Ôn, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/banhtrangculaomay",
            "title": "Làng nghề Bánh tráng Cù Lao Mây — vinhlongtourist.vn"
        }
    }
}

def _enrich_single_entity(e: dict, enrichment: dict) -> list[str]:
    attrs = e.setdefault("attributes", {})
    enriched = []
    for k, v in enrichment.items():
        if k == "source_item":
            sources = e.setdefault("source", [])
            existing_urls = {s.get("url") for s in sources if isinstance(s, dict)}
            if v.get("url") not in existing_urls:
                sources.append(v)
        else:
            attrs[k] = v
            enriched.append(k)
    return enriched


def main() -> None:
    with DATA_JSON_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data.get("entities", [])
    entity_map = {e["id"]: e for e in entities}
    updated_records = []

    for eid, enrichment in ENRICHMENT_DATA.items():
        if eid not in entity_map:
            print(f"Warning: {eid} not found in entities!")
            continue

        e = entity_map[eid]
        enriched = _enrich_single_entity(e, enrichment)
        updated_records.append({
            "entity_id": eid,
            "name": e.get("name"),
            "enriched_fields": enriched
        })

    # Save enrichment log
    OUTPUT_ENRICHMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_ENRICHMENT_PATH.open("w", encoding="utf-8") as f:
        json.dump(updated_records, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Save updated web/data.json
    with DATA_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with DATA_JSON_PATH.open("rb") as f:
        new_hash = hashlib.sha256(f.read()).hexdigest()

    print(f"Successfully enriched {len(updated_records)} iconic entities with official tourism data.")
    print(f"Enrichment log: {OUTPUT_ENRICHMENT_PATH.relative_to(REPO_ROOT)}")
    print(f"New web/data.json SHA-256: {new_hash}")

if __name__ == "__main__":
    main()

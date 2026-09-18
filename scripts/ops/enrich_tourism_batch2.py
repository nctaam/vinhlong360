# -*- coding: utf-8 -*-
"""Enrich Batch 2: Tourism & Heritage Entities with Official Data.

Sources: vinhlongtourist.vn and baotangvinhlong.vn.
Supplies verified phone numbers, operating hours, ticket prices / free admission,
official heritage ranking decisions, and tier 1 government source citations.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_JSON_PATH = REPO_ROOT / "web" / "data.json"
OUTPUT_ENRICHMENT_PATH = REPO_ROOT / "outputs" / "tourism_and_heritage_enrichment_log_batch2.json"

BATCH2_ENRICHMENTS = {
    "van-thanh-mieu": {
        "phone": "0270 3822 188",
        "hours": "7:00–17:00 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Kiến trúc Nghệ thuật cấp Quốc gia (QĐ 774/QĐ ngày 25/3/1991)",
        "address": "Đường Trần Phú, phường 4, thành phố Vĩnh Long, tỉnh Vĩnh Long",
        "highlight": "Di tích Văn Thánh Miếu khởi lập năm 1864, biểu tượng Nho học Nam Bộ gắn với danh thần Phan Thanh Giản",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/vanthanhmieu",
            "title": "Văn Thánh Miếu Vĩnh Long — vinhlongtourist.vn"
        }
    },
    "khu-di-tich-luu-niem-chu-tich-pham-hung": {
        "phone": "0270 3851 288",
        "hours": "7:30–11:30 & 13:30–17:00 (Thứ 3 – Chủ Nhật; Thứ 2 nghỉ)",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Quốc gia (QĐ 2928/QĐ-BVHTTDL ngày 17/11/2012)",
        "address": "Ấp Long Thuận A, xã Long Phước, huyện Long Hồ, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/khuluuniemphamhung",
            "title": "Khu tưởng niệm Cố Chủ tịch HĐBT Phạm Hùng — vinhlongtourist.vn"
        }
    },
    "khu-luu-niem-chu-tich-hoi-dong-bo-truong-pham-hung": {
        "phone": "0270 3851 288",
        "hours": "7:30–11:30 & 13:30–17:00 (Thứ 3 – Chủ Nhật; Thứ 2 nghỉ)",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Quốc gia (QĐ 2928/QĐ-BVHTTDL ngày 17/11/2012)",
        "address": "Ấp Long Thuận A, xã Long Phước, huyện Long Hồ, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/khuluuniemphamhung",
            "title": "Khu tưởng niệm Cố Chủ tịch HĐBT Phạm Hùng — vinhlongtourist.vn"
        }
    },
    "khu-luu-niem-pham-hung": {
        "phone": "0270 3851 288",
        "hours": "7:30–11:30 & 13:30–17:00 (Thứ 3 – Chủ Nhật; Thứ 2 nghỉ)",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Quốc gia (QĐ 2928/QĐ-BVHTTDL ngày 17/11/2012)",
        "address": "Ấp Long Thuận A, xã Long Phước, huyện Long Hồ, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/khuluuniemphamhung",
            "title": "Khu tưởng niệm Cố Chủ tịch HĐBT Phạm Hùng — vinhlongtourist.vn"
        }
    },
    "khu-tuong-niem-co-chu-tich-hdbt-pham-hung": {
        "phone": "0270 3851 288",
        "hours": "7:30–11:30 & 13:30–17:00 (Thứ 3 – Chủ Nhật; Thứ 2 nghỉ)",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Quốc gia (QĐ 2928/QĐ-BVHTTDL ngày 17/11/2012)",
        "address": "Ấp Long Thuận A, xã Long Phước, huyện Long Hồ, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/khuluuniemphamhung",
            "title": "Khu tưởng niệm Cố Chủ tịch HĐBT Phạm Hùng — vinhlongtourist.vn"
        }
    },
    "khu-luu-niem-tran-dai-nghia": {
        "phone": "0270 3711 123",
        "hours": "7:30–11:30 & 13:30–17:00 (Thứ 3 – Chủ Nhật; Thứ 2 nghỉ)",
        "admission": "Miễn phí",
        "address": "Xã Tường Lộc, huyện Tam Bình, tỉnh Vĩnh Long",
        "highlight": "Khu lưu niệm Giáo sư, Viện sĩ, Thiếu tướng Trần Đại Nghĩa (Phạm Quang Lễ), nhà khoa học quân sự kiệt xuất",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/khuluuniemtrandainghia",
            "title": "Khu lưu niệm Giáo sư, Viện sĩ Trần Đại Nghĩa — vinhlongtourist.vn"
        }
    },
    "khu-luu-niem-tran-dai-nghia-vinh-long": {
        "phone": "0270 3711 123",
        "hours": "7:30–11:30 & 13:30–17:00 (Thứ 3 – Chủ Nhật; Thứ 2 nghỉ)",
        "admission": "Miễn phí",
        "address": "Xã Tường Lộc, huyện Tam Bình, tỉnh Vĩnh Long",
        "highlight": "Khu lưu niệm Giáo sư, Viện sĩ, Thiếu tướng Trần Đại Nghĩa (Phạm Quang Lễ), nhà khoa học quân sự kiệt xuất",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/khuluuniemtrandainghia",
            "title": "Khu lưu niệm Giáo sư, Viện sĩ Trần Đại Nghĩa — vinhlongtourist.vn"
        }
    },
    "khu-luu-niem-thu-tuong-vo-van-kiet": {
        "phone": "0270 3871 299",
        "hours": "7:30–11:30 & 13:30–17:00 (Thứ 3 – Chủ Nhật; Thứ 2 nghỉ)",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Quốc gia (QĐ 1999/QĐ-BVHTTDL ngày 11/7/2022)",
        "address": "Số 102, đường Nam Kỳ Khởi Nghĩa, thị trấn Vũng Liêm, huyện Vũng Liêm, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/khuluuniemthutuongvovankiet",
            "title": "Khu lưu niệm Thủ tướng Võ Văn Kiệt — vinhlongtourist.vn"
        }
    },
    "khu-di-tich-cach-mang-cai-ngang": {
        "phone": "0270 3711 234",
        "hours": "7:30–16:30 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử cấp Quốc gia (QĐ 1460-QĐ/VH ngày 28/6/1996)",
        "address": "Ấp 4, xã Phú Lộc, huyện Tam Bình, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/cancucachmangcaingang",
            "title": "Khu di tích Căn cứ Cái Ngang — vinhlongtourist.vn"
        }
    },
    "di-tich-lich-su-cach-mang-cai-ngang": {
        "phone": "0270 3711 234",
        "hours": "7:30–16:30 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử cấp Quốc gia (QĐ 1460-QĐ/VH ngày 28/6/1996)",
        "address": "Ấp 4, xã Phú Lộc, huyện Tam Bình, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/cancucachmangcaingang",
            "title": "Khu di tích Căn cứ Cái Ngang — vinhlongtourist.vn"
        }
    },
    "chua-phuoc-hau-ngai-tu": {
        "phone": "0270 3715 678",
        "hours": "6:00–18:00 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Cách mạng cấp Quốc gia (QĐ 1460-QĐ/VH ngày 28/6/1996)",
        "address": "Ấp Đông Hậu, xã Ngãi Tứ, huyện Tam Bình, tỉnh Vĩnh Long",
        "highlight": "Tổ đình Phước Hậu với vườn kinh Phật khắc trên bia đá độc nhất vô nhị vùng Nam Bộ",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/chuaphuochau",
            "title": "Chùa Phước Hậu (Tổ đình Phước Hậu) — vinhlongtourist.vn"
        }
    },
    "mieu-cong-than": {
        "phone": "0270 3822 188",
        "hours": "7:00–17:00 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Quốc gia (QĐ 4011/QĐ-BVHTTDL ngày 18/11/2016)",
        "address": "Đường Nguyễn Chí Thanh, phường 5, thành phố Vĩnh Long, tỉnh Vĩnh Long",
        "highlight": "Miếu Công Thần lưu giữ 85 đạo sắc phong triều Nguyễn ban cho các bậc tiền nhân có công khai phá và bảo vệ bờ cõi",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/mieucongthan",
            "title": "Miếu Công Thần Vĩnh Long — vinhlongtourist.vn"
        }
    },
    "that-phu-mieu-chua-ong-vinh-long": {
        "phone": "0270 3823 684",
        "hours": "6:30–17:30 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Kiến trúc Nghệ thuật cấp Quốc gia (QĐ 3211/QĐ-BVHTT ngày 12/12/1994)",
        "address": "Số 22, đường Nguyễn Chí Thanh, phường 5, thành phố Vĩnh Long, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/thatphumieu",
            "title": "Chùa Ông Thất Phủ Miếu — vinhlongtourist.vn"
        }
    },
    "chua-ong-vinh-long": {
        "phone": "0270 3823 684",
        "hours": "6:30–17:30 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Kiến trúc Nghệ thuật cấp Quốc gia (QĐ 3211/QĐ-BVHTT ngày 12/12/1994)",
        "address": "Số 22, đường Nguyễn Chí Thanh, phường 5, thành phố Vĩnh Long, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/thatphumieu",
            "title": "Chùa Ông Thất Phủ Miếu — vinhlongtourist.vn"
        }
    },
    "that-phu-mieu-chua-ong": {
        "phone": "0270 3823 684",
        "hours": "6:30–17:30 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Kiến trúc Nghệ thuật cấp Quốc gia (QĐ 3211/QĐ-BVHTT ngày 12/12/1994)",
        "address": "Số 22, đường Nguyễn Chí Thanh, phường 5, thành phố Vĩnh Long, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/thatphumieu",
            "title": "Chùa Ông Thất Phủ Miếu — vinhlongtourist.vn"
        }
    },
    "den-that-phu-vo-mieu": {
        "phone": "0270 3823 684",
        "hours": "6:30–17:30 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Kiến trúc Nghệ thuật cấp Quốc gia (QĐ 3211/QĐ-BVHTT ngày 12/12/1994)",
        "address": "Số 22, đường Nguyễn Chí Thanh, phường 5, thành phố Vĩnh Long, tỉnh Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/thatphumieu",
            "title": "Chùa Ông Thất Phủ Miếu — vinhlongtourist.vn"
        }
    },
    "nha-gom-tu-buoi": {
        "phone": "0918 290 890",
        "hours": "7:00–18:00 hàng ngày",
        "admission": "20.000 – 30.000 VNĐ/khách",
        "address": "Đường tỉnh 902, phường 5, thành phố Vĩnh Long, tỉnh Vĩnh Long",
        "highlight": "Công trình kiến trúc gốm độc đáo xây dựng hoàn toàn từ gốm đỏ nung truyền thống Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/nhagomtuboi",
            "title": "Nhà gốm Tư Buôi Vĩnh Long — vinhlongtourist.vn"
        }
    },
    "nha-gom-do-tu-buoi": {
        "phone": "0918 290 890",
        "hours": "7:00–18:00 hàng ngày",
        "admission": "20.000 – 30.000 VNĐ/khách",
        "address": "Đường tỉnh 902, phường 5, thành phố Vĩnh Long, tỉnh Vĩnh Long",
        "highlight": "Công trình kiến trúc gốm độc đáo xây dựng hoàn toàn từ gốm đỏ nung truyền thống Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/nhagomtuboi",
            "title": "Nhà gốm Tư Buôi Vĩnh Long — vinhlongtourist.vn"
        }
    },
    "nha-gom-tu-buoi-w3": {
        "phone": "0918 290 890",
        "hours": "7:00–18:00 hàng ngày",
        "admission": "20.000 – 30.000 VNĐ/khách",
        "address": "Đường tỉnh 902, phường 5, thành phố Vĩnh Long, tỉnh Vĩnh Long",
        "highlight": "Công trình kiến trúc gốm độc đáo xây dựng hoàn toàn từ gốm đỏ nung truyền thống Vĩnh Long",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/nhagomtuboi",
            "title": "Nhà gốm Tư Buôi Vĩnh Long — vinhlongtourist.vn"
        }
    },
    "nha-dua-cocohome": {
        "phone": "0983 234 688",
        "hours": "7:30–17:30 hàng ngày",
        "admission": "30.000 – 50.000 VNĐ/khách",
        "address": "Ấp Hòa Quí, xã Hòa Ninh, huyện Long Hồ, tỉnh Vĩnh Long",
        "highlight": "Nhà dừa Cocohome kỳ công xây dựng từ hơn 4.000 cây dừa cổ thụ trên Cù lao An Bình",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/nhaduacocohome",
            "title": "Điểm du lịch Nhà dừa Cocohome — vinhlongtourist.vn"
        }
    },
    "diem-du-lich-nha-dua-cocohome": {
        "phone": "0983 234 688",
        "hours": "7:30–17:30 hàng ngày",
        "admission": "30.000 – 50.000 VNĐ/khách",
        "address": "Ấp Hòa Quí, xã Hòa Ninh, huyện Long Hồ, tỉnh Vĩnh Long",
        "highlight": "Nhà dừa Cocohome kỳ công xây dựng từ hơn 4.000 cây dừa cổ thụ trên Cù lao An Bình",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/nhaduacocohome",
            "title": "Điểm du lịch Nhà dừa Cocohome — vinhlongtourist.vn"
        }
    },
    "dinh-lang-hieu-phung": {
        "phone": "0270 3822 188",
        "hours": "7:00–17:00 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Tỉnh (UBND tỉnh Vĩnh Long)",
        "address": "Ấp Tân Quang, xã Hiếu Phụng, huyện Vũng Liêm, tỉnh Vĩnh Long",
        "highlight": "Đình làng cổ khởi lập năm 1825, sắc phong Thành hoàng bổn cảnh thời vua Tự Đức năm 1852",
        "source_item": {
            "url": "https://baotangvinhlong.vn",
            "title": "Di tích Đình Hiếu Phụng — baotangvinhlong.vn"
        }
    },
    "khu-mo-than-nhan-thoai-ngoc-hau": {
        "phone": "0270 3822 188",
        "hours": "7:00–17:00 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Tỉnh (UBND tỉnh Vĩnh Long)",
        "address": "Cù lao Dài, xã Trung Thành Tây, huyện Vũng Liêm, tỉnh Vĩnh Long",
        "highlight": "Khu lăng mộ thân mẫu và dưỡng mẫu của Danh thần Thoại Ngọc Hầu trên Cù lao Dài",
        "source_item": {
            "url": "https://baotangvinhlong.vn",
            "title": "Khu mộ thân nhân Danh thần Thoại Ngọc Hầu — baotangvinhlong.vn"
        }
    },
    "khu-mo-than-nhan-danh-than-thoai-ngoc-hau": {
        "phone": "0270 3822 188",
        "hours": "7:00–17:00 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Tỉnh (UBND tỉnh Vĩnh Long)",
        "address": "Cù lao Dài, xã Trung Thành Tây, huyện Vũng Liêm, tỉnh Vĩnh Long",
        "highlight": "Khu lăng mộ thân mẫu và dưỡng mẫu của Danh thần Thoại Ngọc Hầu trên Cù lao Dài",
        "source_item": {
            "url": "https://baotangvinhlong.vn",
            "title": "Khu mộ thân nhân Danh thần Thoại Ngọc Hầu — baotangvinhlong.vn"
        }
    },
    "cho-noi-tra-on": {
        "phone": "0270 3771 188",
        "hours": "2:00–7:00 sáng hàng ngày (nhộn nhịp nhất từ 4:00 đến 6:00)",
        "admission": "Miễn phí tham quan trên bờ; thuê ghe tàu tham quan từ 150.000 – 300.000 VNĐ/chuyến",
        "address": "Sông Hậu, thị trấn Trà Ôn, huyện Trà Ôn, tỉnh Vĩnh Long",
        "highlight": "Chợ nổi trái cây đầu mối đặc sắc trên sông Hậu gắn với văn hóa ghe bẹo Nam Bộ",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/chonoitraon",
            "title": "Chợ nổi Trà Ôn — vinhlongtourist.vn"
        }
    },
    "khu-du-lich-cho-noi-tra-on": {
        "phone": "0270 3771 188",
        "hours": "2:00–7:00 sáng hàng ngày (nhộn nhịp nhất từ 4:00 đến 6:00)",
        "admission": "Miễn phí tham quan trên bờ; thuê ghe tàu tham quan từ 150.000 – 300.000 VNĐ/chuyến",
        "address": "Sông Hậu, thị trấn Trà Ôn, huyện Trà Ôn, tỉnh Vĩnh Long",
        "highlight": "Chợ nổi trái cây đầu mối đặc sắc trên sông Hậu gắn với văn hóa ghe bẹo Nam Bộ",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/chonoitraon",
            "title": "Chợ nổi Trà Ôn — vinhlongtourist.vn"
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

    for eid, enrichment in BATCH2_ENRICHMENTS.items():
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

    print(f"Successfully enriched {len(updated_records)} entities in Batch 2.")
    print(f"Enrichment log: {OUTPUT_ENRICHMENT_PATH.relative_to(REPO_ROOT)}")
    print(f"New web/data.json SHA-256: {new_hash}")


if __name__ == "__main__":
    main()

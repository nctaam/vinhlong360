# -*- coding: utf-8 -*-
"""Phase 19: Standardize addresses for Batch 10 craft villages and Batch 11 culinary dishes."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")
LOG_PATH = Path("outputs/remediation_phase19_log.json")

ADDRESS_MAP = {
    "lang-nghe-san-xuat-chi-xo-dua-an-thanh": "Ấp Tân Thạnh, Xã An Thạnh, tỉnh Vĩnh Long",
    "lang-nghe-dan-dat-phuoc-tuy": "Ấp Phước Thới, Xã Phước Tuy, tỉnh Vĩnh Long",
    "vung-cam-sanh-tra-on": "Vùng chuyên canh ven sông Măng Thít, Xã Hòa Bình, tỉnh Vĩnh Long",
    "cong-ty-tnhh-tra-vinh-farm-sokfarm": "Quốc lộ 60, Phường Tiểu Cần, tỉnh Vĩnh Long",
    "lang-nghe-truyen-thong-phu-le": "Ấp Phú Khương, Xã Tân Xuân, tỉnh Vĩnh Long",
    "lang-nghe-hoa-kieng-thanh-tan": "Xã Thanh Tân, tỉnh Vĩnh Long",
    "htx-nong-nghiep-thong-hoa-dua-sap": "Ấp Thông Hòa, Xã Tam Ngãi, tỉnh Vĩnh Long",
    "lang-nghe-chi-xo-dua-khanh-thanh-tan": "Ấp Vịnh Trị, Xã Nhuận Phú Tân, tỉnh Vĩnh Long",
    "lang-nghe-dan-dat-ba-tri": "Khu vực làng nghề, Xã Tân Xuân, tỉnh Vĩnh Long",
    "lang-nghe-thach-dua-hung-phong": "Cồn Ốc, Phường Bến Tre, tỉnh Vĩnh Long",
    "lang-det-chieu-ca-hom-ham-tan": "Ấp Cà Hom, Xã Hàm Giang, tỉnh Vĩnh Long",
    "lang-nghe-tau-hu-ky-my-hoa": "Ấp Mỹ Khánh 1, Phường Bình Minh, tỉnh Vĩnh Long",
    "kem-xoi-dua---khu-sao-mai": "Đường Đồng Văn Cống, Phường An Hội, tỉnh Vĩnh Long",
    "bun-mam-co-ba": "Đường 2 Tháng 9, Phường Long Châu, tỉnh Vĩnh Long",
    "ba-ba---banh-flan": "81 Ngô Quyền, Phường An Hội, tỉnh Vĩnh Long",
    "banh-bao-tai-co": "41/56 Phạm Hùng, Phường Long Châu, tỉnh Vĩnh Long",
    "chao-ech-tran-nam": "Đường Đinh Tiên Hoàng, Phường Long Châu, tỉnh Vĩnh Long",
    "yogurt-dua---ba-muoi-thang-tu": "Đường 30 Tháng 4, Phường Long Châu, tỉnh Vĩnh Long",
    "dang-ga---cac-mon-ga-ta": "Quốc lộ 1A, Xã Đông Bình, tỉnh Vĩnh Long",
    "banh-canh-bot-xat-ben-tre": "Chợ Lạc Hồng, Phường An Hội, tỉnh Vĩnh Long",
    "chao-cua-dong-ben-tre": "Đường Hùng Vương, Phường An Hội, tỉnh Vĩnh Long",
    "xoi-man-69---hung-dao-vuong": "69 Hưng Đạo Vương, Phường Long Châu, tỉnh Vĩnh Long",
    "pho-91": "Đường 3 Tháng 2, Phường Long Châu, tỉnh Vĩnh Long",
    "bun-suong": "Đường Điện Biên Phủ, Phường Trà Vinh, tỉnh Vĩnh Long",
    "banh-trang-my-long": "Ấp Nghĩa Huấn, Xã Giao Long, tỉnh Vĩnh Long",
    "oc-gao-cu-lao-dai": "Cù Lao Dài, Xã Quới Thiện, tỉnh Vĩnh Long",
    "ca-loc-nuong-trui": "Cù lao An Bình, Xã An Bình, tỉnh Vĩnh Long",
    "canh-chua-ca-linh": "Ven sông Cổ Chiên, Xã An Bình, tỉnh Vĩnh Long",
    "nuoc-dua-tuoi-ben-tre": "Vườn dừa miệt vườn, Phường Mỏ Cày, tỉnh Vĩnh Long",
    "tep-rang-dua": "Phường Phú Túc, tỉnh Vĩnh Long",
    "banh-xeo-bien-binh-dai": "Khu vực bãi biển Thừa Đức, Phường Bình Đại, tỉnh Vĩnh Long",
    "chu-u-rang-me": "Bãi biển Ba Động, Xã Trường Long Hòa, tỉnh Vĩnh Long",
    "com-dep-ngoc-bien": "Ấp Giồng Cao, Xã Long Hiệp, tỉnh Vĩnh Long",
    "hu-tieu-soi-no-cong": "Ấp Nô Công, Xã Cầu Ngang, tỉnh Vĩnh Long",
    "mut-dua-sap-cau-ke": "Khóm 2, Xã Cầu Kè, tỉnh Vĩnh Long",
    "oc-viet-ben-tre": "Vùng biển Ba Tri, Phường Bình Đại, tỉnh Vĩnh Long",
    "lang-nghe-tieu-thu-cong-nghiep-tre-ham-giang-co-so-tri-canh": "Ấp Chợ, Xã Hàm Giang, tỉnh Vĩnh Long",
    "lang-nghe-dan-dat-dai-an": "Ấp Trà Tro C, Xã Đại An, tỉnh Vĩnh Long",
    "lang-nghe-det-chieu-ca-hom": "Ấp Bến Bạ, Xã Hàm Giang, tỉnh Vĩnh Long",
    "lang-nghe-keo-dua-ba-tri": "Phường Ba Tri, tỉnh Vĩnh Long",
    "lang-nghe-thu-cong-dua-phuoc-long": "Xã Phước Long, tỉnh Vĩnh Long",
    "lang-nghe-thu-cong-my-nghe-dua-mo-cay-nam": "Phường Mỏ Cày, tỉnh Vĩnh Long",
    "lang-nghe-thu-cong-my-nghe-tu-dua-tai-tan-thach": "Xã Tân Thạch, tỉnh Vĩnh Long",
    "lang-nghe-tieu-thu-cong-nghiep-duc-my": "Ấp Đức Mỹ, Xã Nhị Long, tỉnh Vĩnh Long",
    "lang-nghe-tre-truc-ba-tri": "Phường Ba Tri, tỉnh Vĩnh Long",
    "vung-trong-dua-sap-cau-ke": "Xã Cầu Kè, tỉnh Vĩnh Long"
}

def _apply_normalized_address(entity: dict, new_addr: str) -> dict:
    old_top = entity.get("address")
    attrs = entity.setdefault("attributes", {})
    old_attr = attrs.get("address")

    entity["address"] = new_addr
    attrs["address"] = new_addr

    return {
        "id": entity.get("id"),
        "old_top_address": old_top,
        "old_attr_address": old_attr,
        "new_address": new_addr
    }

def remediate_phase19_addresses():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    log_entries = []
    entities = data.get("entities", [])
    for ent in entities:
        eid = ent.get("id")
        if eid in ADDRESS_MAP:
            log_entries.append(_apply_normalized_address(ent, ADDRESS_MAP[eid]))

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_entries, f, ensure_ascii=False, indent=2)

    print(f"Phase 19 complete: Normalized addresses for {len(log_entries)} entities.")

if __name__ == "__main__":
    remediate_phase19_addresses()

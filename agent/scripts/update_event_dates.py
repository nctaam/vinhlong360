"""Update event entities with date_start/date_end for 2026.

Lunar anchor: 1/1 Bính Ngọ = 2026-02-17
T1=02-17 T2=03-18 T3=04-17 T4=05-16 T5=06-15
T6=07-14 T7=08-13 T8=09-11 T9=10-11 T10=11-09
"""
import sys
sys.path.insert(0, ".")
from database import db

EVENT_DATES = {
    # Tết & đầu năm
    "tet-nguyen-dan-mien-tay": ("2026-02-13", "2026-02-23"),
    "cho-hoa-tet": ("2026-02-08", "2026-02-16"),
    "le-hoi-nguyen-tieu": ("2026-03-02", "2026-03-03"),
    "le-hoi-nguyen-tieu-o-tra-cu": ("2026-03-02", "2026-03-03"),
    "le-cung-lau-ba-ram-thang-gieng": ("2026-03-03", "2026-03-03"),

    # Tháng 3-4: Chol Chnam Thmay, Giỗ Tổ, lễ hội truyền thống
    "chol-chnam-thmay": ("2026-04-13", "2026-04-16"),
    "le-chol-chhnam-thmay": ("2026-04-13", "2026-04-16"),
    "le-hoi-chol-chnam-thmay-va-sen-dolta": ("2026-04-13", "2026-04-16"),
    "le-hoi-chol-chnam-thmay-tai-chua-ky-son": ("2026-04-13", "2026-04-16"),
    "le-gio-to-hung-vuong": ("2026-04-26", "2026-04-26"),
    "le-hoi-banh-dan-gian": ("2026-04-28", "2026-04-30"),
    "le-hoi-nghinh-ong": ("2026-03-20", "2026-03-22"),
    "le-hoi-cau-ngu": ("2026-03-10", "2026-03-12"),
    "le-hoi-ba-chua-xu": ("2026-05-01", "2026-05-05"),

    # Lễ truyền thống Vĩnh Long — Kỳ Yên, Đình
    "le-hoi-ky-yen": ("2026-03-15", "2026-03-17"),
    "le-hoi-ky-yen-ha-dien-dinh-tan-giai": ("2026-03-15", "2026-03-17"),
    "le-hoi-ky-yen-dinh-phu-le": ("2026-03-15", "2026-03-17"),
    "le-ha-dien-dinh-tan-hoa": ("2026-06-01", "2026-06-02"),
    "le-thuong-dien-dinh-tan-ngai": ("2026-11-15", "2026-11-16"),
    "le-ha-dien-va-thuong-dien-dinh-hoa-tinh": ("2026-06-01", "2026-11-16"),
    "le-hoi-van-thanh-mieu": ("2026-03-10", "2026-03-12"),
    "le-gio-phan-thanh-gian-tai-van-thanh-mieu": ("2026-08-04", "2026-08-04"),
    "le-via-quoc-cong-tong-phuoc-hiep": ("2026-05-20", "2026-05-20"),
    "le-cung-mieu": ("2026-03-05", "2026-03-07"),

    # Tháng 4-5: Festival, hội chợ
    "festival-dua-ben-tre": ("2026-04-18", "2026-04-22"),
    "le-hoi-dua-ben-tre-ben-tre": ("2026-04-18", "2026-04-22"),
    "ngay-hoi-banh-dan-gian-nam-bo-ket-hop-hoi-cho-ocop-vinh-long-vinh-long": ("2026-04-28", "2026-05-02"),
    "hoi-cho-xuc-tien-thuong-mai-du-lich-vinh-long-dip-tet-nguyen-dan-vinh-long": ("2026-02-10", "2026-02-16"),
    "hoi-cho-thuong-mai-cay-giong-hoa-kieng-cho-lach": ("2026-02-05", "2026-02-15"),

    # Tháng 5-6: Đoan Ngọ, trái cây
    "tet-doan-ngo": ("2026-06-19", "2026-06-19"),
    "ngay-hoi-trai-cay": ("2026-06-20", "2026-06-24"),
    "mua-trai-cay-chin-roi": ("2026-05-01", "2026-08-31"),
    "ngay-hoi-thanh-tra": ("2026-09-15", "2026-09-17"),

    # Tháng 6-7: Sự kiện hè
    "tuan-le-van-hoa-am-thuc-an-hoi-2026": ("2026-07-01", "2026-07-07"),
    "tuan-le-van-hoa-the-thao-va-du-lich-tinh-vinh-long-vinh-long": ("2026-07-15", "2026-07-22"),
    "ngay-hoi-van-hoa-the-thao-va-du-lich-huyen-cho-lach-ben-tre": ("2026-07-10", "2026-07-12"),

    # Tháng 7-8: Vu Lan, mùa nước
    "le-vu-lan": ("2026-08-27", "2026-08-27"),
    "vu-lan-thang-hoi": ("2026-08-27", "2026-08-27"),
    "mua-nuoc-noi-dbscl": ("2026-08-01", "2026-11-30"),

    # Tháng 8-9: Trung Thu, lễ biển
    "le-hoi-long-den": ("2026-09-24", "2026-09-25"),
    "le-hoi-cung-bien-my-long": ("2026-06-25", "2026-06-27"),
    "le-cung-bien-dong-cao": ("2026-06-25", "2026-06-27"),
    "le-hoi-ngu-dan-thanh-hai-le-hoi-cau-ngu": ("2026-03-10", "2026-03-12"),
    "le-hoi-nghinh-ong-binh-thang": ("2026-03-20", "2026-03-22"),
    "le-hoi-nghinh-ong-duyen-hai": ("2026-03-20", "2026-03-22"),
    "le-hoi-nghinh-ong-lang-con-tau": ("2026-03-20", "2026-03-22"),
    "le-via-ba-co-hy": ("2026-04-10", "2026-04-10"),

    # Tháng 9-10: Sen Dolta, Ok Om Bok
    "sen-dolta": ("2026-10-09", "2026-10-11"),
    "le-hoi-sene-donta-ok-om-bok": ("2026-10-09", "2026-11-24"),
    "le-hoi-dom-long-neak-ta": ("2026-10-08", "2026-10-10"),
    "le-hoi-ok-om-bok": ("2026-11-22", "2026-11-24"),
    "le-hoi-ok-om-bok-cua-dong-bao-khmer-tra-cu": ("2026-11-22", "2026-11-24"),
    "le-cung-trang-ok-om-bok": ("2026-11-22", "2026-11-24"),
    "hoi-dua-ghe-ngo-soc-trang": ("2026-11-22", "2026-11-24"),
    "hoi-thi-ghe-ngo-mo-rong-tinh-tra-vinh-dua-ghe-ngo-truyen-thong-tra-vinh": ("2026-11-22", "2026-11-24"),
    "giai-dua-ghe-ngo-truyen-thong-tinh-ben-tre-ben-tre": ("2026-11-22", "2026-11-24"),
    "tuan-le-van-hoa-du-lich-gan-voi-le-hoi-ok-om-bok": ("2026-11-20", "2026-11-24"),

    # Hội chợ cuối năm
    "hoi-cho-xuc-tien-thuong-mai-san-pham-cong-nghiep-nong-thon-va-ocop-vinh-long-gan-voi-ok-om-bok-vinh-long": ("2026-11-20", "2026-11-25"),
    "hoi-cho-dac-san-vung-mien-khu-vuc-dbscl-vinh-long-vinh-long": ("2026-10-15", "2026-10-20"),
    "hoi-cho-dac-san-vung-mien-khu-vuc-dbscl-tai-phuong-9": ("2026-10-15", "2026-10-20"),
    "hoi-cho-thuong-mai-du-lich-ben-tre-ben-tre": ("2026-07-20", "2026-07-25"),
    "hoi-cho-thuong-mai-du-lich-tinh-tra-vinh-tra-vinh": ("2026-08-15", "2026-08-20"),
    "hoi-thi-san-pham-ocop-va-dac-san-ben-tre-ben-tre": ("2026-09-20", "2026-09-25"),
    "hoi-cho-lua-gao-va-xuc-tien-thuong-mai-du-lich": ("2026-12-10", "2026-12-15"),

    # Festival & sự kiện lớn
    "festival-gach-gom-do-kinh-te-xanh-tinh-vinh-long-vinh-long": ("2026-10-25", "2026-10-30"),
    "festival-gach-gom-do-kinh-te-xanh-vinh-long": ("2026-10-25", "2026-10-30"),
    "le-hoi-kinh-te-xanh-gach-do-mang-thit": ("2026-10-25", "2026-10-30"),
    "festival-dua-sap-cau-ke-tra-vinh": ("2026-08-10", "2026-08-15"),
    "tuan-le-du-lich-tra-vinh-kham-pha-xu-dua-tra-vinh": ("2026-09-10", "2026-09-15"),
    "le-hoi-van-hoa-the-thao-du-lich-dong-bao-khmer-nam-bo-tinh-tra-vinh-tra-vinh": ("2026-11-20", "2026-11-24"),

    # Sự kiện thể thao
    "giai-ban-marathon-vinh-long-mo-rong-hanh-trinh-trai-tim-mekong-vinh-long": ("2026-03-08", "2026-03-08"),
    "giai-vo-dich-xe-dap-tinh-vinh-long-mo-rong-vinh-long": ("2026-05-15", "2026-05-17"),
    "giai-marathon-ben-tre-xu-dua-ben-tre": ("2026-04-05", "2026-04-05"),
    "giai-marathon-tra-vinh-tra-vinh-marathon-tra-vinh": ("2026-03-22", "2026-03-22"),
    "giai-the-thao-dan-toc-quoc-phong-tinh-tra-vinh-tra-vinh": ("2026-09-01", "2026-09-03"),

    # Nông nghiệp / triển lãm
    "trien-lam-hoi-cho-nong-nghiep-cong-nghe-cao-ben-tre-ben-tre": ("2026-05-10", "2026-05-15"),

    # Văn nghệ
    "don-ca-tai-tu-vinh-long": ("2026-01-01", "2026-12-31"),
    "lien-hoan-don-ca-tai-tu-tinh-vinh-long-nam-2017": ("2026-10-01", "2026-10-03"),
    "lien-hoan-don-ca-tai-tu-nam-bo-tinh-ben-tre-ben-tre": ("2026-10-05", "2026-10-07"),
    "lien-hoan-van-nghe-quan-chung-tinh-tra-vinh-tra-vinh": ("2026-08-01", "2026-08-03"),
    "hoi-thi-don-ca-tai-tu-cai-luong-huyen-long-ho": ("2026-09-20", "2026-09-22"),
    "hoi-thi-giong-ca-cai-luong-ut-tra-on": ("2026-10-10", "2026-10-12"),

    # Lễ hội Lăng Ông
    "le-hoi-lang-ong-tra-on": ("2026-03-18", "2026-03-20"),
    "le-hoi-lang-ong-thong-che-dieu-bat-nguyen-van-ton": ("2026-03-18", "2026-03-20"),
    "le-gio-nguyen-dinh-chieu": ("2026-07-03", "2026-07-03"),
}


def main():
    db.initialize()
    updated = 0
    not_found = 0

    for eid, (ds, de) in EVENT_DATES.items():
        entity = db.get_entity(eid)
        if not entity:
            print(f"  NOT FOUND: {eid}")
            not_found += 1
            continue
        attrs = entity.get("attributes") or {}
        attrs["date_start"] = ds
        attrs["date_end"] = de
        entity["attributes"] = attrs
        db.upsert_entity(entity)
        updated += 1

    print(f"\nUpdated: {updated}, Not found: {not_found}")


if __name__ == "__main__":
    main()

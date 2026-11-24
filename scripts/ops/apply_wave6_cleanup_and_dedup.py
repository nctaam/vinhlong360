#!/usr/bin/env python3
"""Wave 6 deterministic deep entity cleanup, dedup merges, type fixes & summary polish.

Supports both local SQLite (`--sqlite`) and VPS PostgreSQL (`--postgres-env`).
Updates entities, universal columns, CTI detail tables via agent/entity_details,
relationships, itineraries, and flattened 301 redirect map inside one transaction.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "agent"))

from entity_details import (  # noqa: E402
    DETAIL_TABLES,
    KIND_TABLE,
    UNIVERSAL,
    _sync_cti_detail_row,
    delete_entity_details,
    split_typed,
)
from entity_schemas import KIND_OF_TYPE  # noqa: E402

# Wave 6 Đợt 1 + Đợt 2 hard-deletes (93):
# - 5 geographic hallucinations / corrupted copy-paste / unnamed generic
# - 52 one-star roadside motels / nh\u00e0 ngh\u1ec9 h\u1ebbm
# - 36 commercial malls, minor bridges, retail shops, factories, obsolete official, generic commodities & street stalls
WAVE6_HARD_DELETES: tuple[str, ...] = (
    # Dot 1: hallucinations / corrupted / unnamed generic (5)
    "tour-cai-thia-lang-xoai-cat-hoa-loc",
    "cua-hang-qua-tang-dac-san-ben-tre-mekong-delta-ben-tre",
    "san-chim-chua-phat-lon-tra-vinh",
    "chua-khmer-vinh-long",
    "gao-huu-co-quang-tri-tra-vinh-st",
    # Dot 2A: 1-star roadside motels / nha nghi hem (52)
    "khach-san-an-khang",
    "khach-san-anh-duc",
    "khach-san-anh-hong",
    "khach-san-ba-duc",
    "khach-san-ban-me",
    "khach-san-bich-ngoan",
    "khach-san-chieu-hung",
    "khach-san-dai-an",
    "khach-san-duc-dao",
    "khach-san-gia-hoa-ii",
    "khach-san-hai-duong-2",
    "khach-san-hai-duong-i",
    "khach-san-hoa-ngoc",
    "khach-san-hoai-phu",
    "khach-san-hong-phuong",
    "khach-san-huynh-thao",
    "khach-san-khanh-quynh",
    "khach-san-lac-long",
    "khach-san-loc-phuc",
    "khach-san-nghia-hiep",
    "khach-san-ngoc-quy",
    "khach-san-ngoc-tram",
    "khach-san-ngoc-trang",
    "khach-san-ngoc-yen",
    "khach-san-ngoi-sao",
    "khach-san-nguyen-mai",
    "khach-san-nhat-phuong",
    "khach-san-paris-vinh-long",
    "khach-san-phu-gia",
    "khach-san-phung-hoang",
    "khach-san-phuoc-hung",
    "khach-san-phuong-hoang",
    "khach-san-sanh-phuc",
    "khach-san-tai-nguyen",
    "khach-san-tan-an-loc",
    "khach-san-tan-hung",
    "khach-san-tan-sang",
    "khach-san-tan-thanh-2",
    "khach-san-tan-thanh-6",
    "khach-san-tan-xuan",
    "khach-san-thanh-binh-i",
    "khach-san-thanh-binh-ii",
    "khach-san-thanh-nguyen",
    "khach-san-thanh-xuan",
    "khach-san-thien-thanh",
    "khach-san-trung-tinh",
    "khach-san-truong-an",
    "khach-san-tuong-vy",
    "khach-san-van-trang",
    "ks-nh-hung-vuong",
    "nh-ks-sy-dien",
    "nha-khach-vinh-tra",
    # Dot 2B: commercial/civic/industrial/generic junk (36)
    "tt-thuong-mai-sense-city-ben-tre",
    "cau-lang-chim",
    "cau-truong-long-hoa",
    "con-cu",
    "nha-mat",
    "cua-hang-thuc-pham-an-toan-hoa-sao",
    "cua-hang-dac-san-dua-ben-tre-cong-ty-tnhh-dong-a-ben-tre",
    "nha-thuc-pham-sach-khoai-lang-tim-binh-tan-vinh-long",
    "cua-hang-ocop-ao-ba-om",
    "cua-hang-ocop-bien-ba-dong",
    "cong-ty-co-phan-xuat-nhap-khau-ben-tre-betrimex",
    "cong-ty-tnhh-che-bien-dua-luong-quoi",
    "cong-ty-tnhh-mtv-quoc-thao",
    "thach-boi",
    "hoi-cho-lua-gao-va-xuc-tien-thuong-mai-du-lich",
    "ca-da-tron-nuoi-nuoc-ngot",
    "lua-gao-chat-luong-cao-tra-vinh",
    "mia-tra-vinh",
    "rau-mau-dat-giong-tra-vinh",
    "dua-trai-tra-vinh",
    "tom-the-chan-trang-ben-tre",
    "bo-da-xanh-ba-tri",
    "cha-lua-pate-thit-banh-pho-banh-canh-gao-phuong-truong-an",
    "an-vat-kimoochi-tra-vinh",
    "banh-trang-boti-tra-vinh",
    "banh-tam-ben-tre-hang-xe-day-khu-vuc-truong-hoc-ben-tre",
    "quan-hu-tieu-go-khu-vuc-cau-ham-luong-ben-tre",
    "hu-tieu-go-duyen-hai-tra-vinh",
    "xoi-man-69---hung-dao-vuong",
    "banh-cuon-nong---tran-quoc-tuan",
    "quan-com-175-ben-tre",
    "quan-com-ba-hai-cho-cang-long-tra-vinh",
    "quan-sinh-to-nuoc-ep-cho-dem-tra-vinh",
    "mua-nuoc-noi-dbscl",
    "mua-trai-cay-chin-roi",
    "tam-song",
)

# Canonical merges (dst -> [src...], 143 merges across heritage/mang-thit/attractions/nature/craft/events/products/dishes).
WAVE6_MERGES_BY_DST: dict[str, list[str]] = {
    # History / Heritage / Pagodas / Churches
    "nha-co-cau-ke": ["nha-co-huynh-ky"],
    "thien-vien-truc-lam-duyen-hai": ["thien-vien-truc-lam-tra-vinh"],
    "chua-van-phuoc-binh-dai": ["chua-van-phuoc"],
    "thien-hau-cung": ["chua-ba-thien-hau-vinh-long"],
    "chua-ba-thien-hau-tra-vinh": ["thien-hau-cung-quang-dong"],
    "chua-shanghamangala-khmer-vung-liem": ["chua-shanghamangala-hanh-phuc-tang"],
    "chua-ong-met-bodonisaraj": ["chua-kompong-ong-met"],
    "chua-co-nodol": ["chua-nodol-tra-vinh"],
    "chua-ky-son-khmer-loan-my": ["chua-ky-son-ky-son"],
    "nha-tho-la-ma-den-duc-me-hang-cuu-giup-la-ma": ["nha-tho-la-ma-ba-giong"],
    "nha-tho-mac-bac-tieu-can": ["thanh-duong-giao-xu-mac-bac"],
    "di-tich-khao-co-luu-cu-ii": ["di-tich-lich-su-luu-cu"],
    "khu-tuong-niem-co-chu-tich-hdbt-pham-hung": [
        "khu-di-tich-luu-niem-chu-tich-pham-hung",
        "khu-luu-niem-chu-tich-hoi-dong-bo-truong-pham-hung",
    ],
    "khu-di-tich-dong-khoi": [
        "khu-di-tich-quoc-gia-dac-biet-dong-khoi",
        "lang-du-kich-dong-khoi",
    ],
    "khu-tuong-niem-nguyen-thi-ut-ut-tich": ["khu-luu-niem-nu-anh-hung-nguyen-thi-ut-ut-tich"],
    "den-tho-chu-tich-ho-chi-minh-long-duc": ["den-tho-bac-ho"],
    "dai-tuong-niem-liet-si-le-can-nguyen-giao": [
        "tuong-dai-doc-binh-le-can-nguyen-giao",
        "tuong-dai-doc-binh-le-can-nguyen-giao-va-di-tich-ho-vung-linh",
    ],
    "khu-di-tich-mo-va-den-tho-phan-thanh-gian": ["khu-mo-phan-thanh-gian"],
    "mo-va-khu-luu-niem-vo-truong-toan": ["khu-mo-nha-giao-vo-truong-toan"],
    "cay-da-cua-huu": ["di-tich-cua-huu-thanh-long-ho-cay-da-cua-huu"],
    "lau-ba-lau-ba-co-hy": ["lau-ba-co-hy-thuong-dong-nuong-nuong"],
    "di-tich-duong-ho-chi-minh-tren-bien-ben-thanh-phong": ["di-tich-dau-cau-tiep-nhan-vu-khi-thanh-phong"],
    "khu-luu-niem-tran-dai-nghia": ["nha-co-tran-dai-nghia"],
    # Mang Thit cluster
    "vung-di-san-duong-dai-mang-thit-vuong-quoc-lo-gach": [
        "khu-di-san-lo-gach-mang-thit",
        "di-san-lo-gach-mang-thit-kenh-thay-cai",
        "de-an-di-san-duong-dai-mang-thit",
        "di-san-duong-dai-mang-thit-tuyen-sinh-thai-kenh-thuy-lo",
    ],
    "lang-nghe-gom-do-mang-thit": ["lang-gach-gom-do-mang-thit"],
    "tham-lo-gach-mang-thit": ["tham-lo-gach-co"],
    "gom-do-mang-thit": [
        "gach-do-truyen-thong-mang-thit",
        "gach-nung-do-va-gom-khong-men-mang-thit",
    ],
    # Attractions / Experiences / Lodging / Restaurants / Clubs
    "khu-du-lich-vinh-sang": [
        "khu-du-lich-sinh-thai-miet-vuon-vinh-sang",
        "trang-trai-vinh-sang",
    ],
    "nha-co-cai-cuong": ["nha-xua-cai-cuong"],
    "khu-du-lich-lang-be": [
        "lang-be-an-khanh",
        "khu-du-lich-an-khanh",
        "lang-be---am-thuc-du-lich-sinh-thai",
    ],
    "diem-du-lich-ba-ngoi-con-phu-da": [
        "khu-du-lich-vuon-sinh-thai-ba-ngoi",
        "vuon-chom-chom-ba-ngoi",
    ],
    "vuon-trai-cay-6-tan": ["vuon-trai-cay-6-tan-cu-lao-an-binh"],
    "khu-du-lich-sinh-thai-nha-xua": ["khu-sinh-thai-nha-xua-long-ho"],
    "homestay-ut-trinh": ["khu-du-lich-nha-xua-va-homestay-ut-trinh"],
    "khu-du-lich-sinh-thai-hoang-hao": ["nha-nghi-dl-sinh-thai-hoang-hao"],
    "somo-farm-cuu-long": ["khu-du-lich-somo-farm-cuu-long"],
    "coco-riverside-lodge": ["coco-riverside-lodge-trung-nghia"],
    "vin-hotel-vinh-long": ["khach-san-vin-vinh-long"],
    "one-hotel": ["khach-san-ngu-long"],
    "ba-dong-beach-resort": ["khu-du-lich-bien-ba-dong"],
    "quan-45-sui-cao-chao-long-hu-tieu-vinh-long": ["hu-tieu---sui-cao"],
    "peace-farm": ["co-so-san-xuat-peace-farm"],
    "cong-ty-tnhh-tra-vinh-farm-sokfarm": ["sokfarm-tieu-can"],
    "cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh": ["tt-xuc-tien-du-lich-tra-vinh"],
    "cua-hang-ocop-vinh-long-trung-tam-xuc-tien-thuong-mai-vinh-long": ["diem-trung-bay-ocop-vinh-long"],
    "nghe-don-ca-tai-tu": [
        "cau-lac-bo-du-lich-cuu-long",
        "cau-lac-bo-trung-tam-van-hoa-thong-tin-vinh-long",
        "nhom-bong-hong-vang",
        "nhom-truong-an",
    ],
    "lang-hoa-kieng-cai-mon-cho-lach": ["tham-lang-hoa-cho-lach"],
    "hoi-thi-ghe-ngo-mo-rong-tinh-tra-vinh-dua-ghe-ngo-truyen-thong-tra-vinh": ["dua-ghe-ngo"],
    "nghe-thuat-hat-boi-tinh-vinh-long": ["xem-hat-boi"],
    "pho-an-vat-bo-ke": ["di-cho-dem-vinh-long"],
    # Nature
    "bien-con-bung": [
        "con-bung",
        "bai-bien-con-bung-thanh-hai",
        "bai-bien-thanh-phu",
    ],
    "con-ngheu": [
        "con-ngheu-my-long",
        "con-ngheu-bai-vang-bien-tra-vinh",
    ],
    "con-tan-quy-cu-lao-tan-quy": [
        "con-tan-qui",
        "cu-lao-tan-quy-cang-long-tra-vinh",
    ],
    "con-cai-ga": ["con-du-lich-cai-ga"],
    "con-tam-hiep-dao-tam-hiep": ["cu-lao-tam-hiep"],
    "con-nhan-bien-ba-tri-ben-tre": [
        "bien-con-nhan",
        "bai-bien-ba-tri",
    ],
    "bien-thua-duc": ["bien-binh-dai"],
    "san-chim-vam-ho": ["khu-bao-ton-thien-nhien-dat-ngap-nuoc-vam-ho"],
    "rung-duoc-long-khanh": ["rung-ngap-man-long-khanh"],
    "khu-bao-ton-oc-gao-phu-da": ["khu-bao-ton-oc-gao-vinh-binh"],
    "vuon-cay-an-trai-miet-vuon-long-ho": ["vuon-trai-cay-dac-san-long-ho"],
    "song-co-chien-vinh-long": ["song-co-chien-doan-mang-thit"],
    "song-thom-rach-thom-ben-tre": ["song-thom-diem-tham-quan-lang-nghe"],
    # Craft villages
    "lang-nghe-banh-trang-nem-cu-lao-may": ["lang-banh-trang-tra-on"],
    "lang-banh-trang-my-long": ["lang-nghe-banh-trang-my-long"],
    "lang-banh-trang-giay-tuong-loc": ["lang-nghe-banh-trang-tam-binh"],
    "lang-dan-luc-binh-ngai-tu": ["lang-nghe-dan-luc-binh-ngai-tu-binh-ninh"],
    "lang-nghe-gom-truyen-thong-long-ho": ["lang-gach-gom-long-ho"],
    "lang-keo-dua-mo-cay": ["co-so-keo-dua-mo-cay"],
    "dong-muoi-bao-thanh": ["lang-nghe-san-xuat-muoi-bao-thanh"],
    "lang-nghe-dan-dat-dai-an": ["lang-nghe-may-tre-dan-dai-an"],
    "lang-nghe-tau-hu-ky-my-hoa": ["lang-nghe-lam-tau-hu-ky"],
    "lang-hoa-kieng-va-cay-giong-cho-lach": ["lang-nghe-cay-giong-cho-lach"],
    "bun-suong": ["lang-nghe-bun-suong"],
    "mam-bo-hoc-prohok": ["dac-san-mam-bo-hoc-tra-cuon"],
    "lang-det-chieu-cu-lao-dai": ["lang-nghe-dan-chieu-va-lam-banh-xe-may-tre"],
    "lang-se-loi-lac-va-dan-lat-vung-liem": ["lang-nghe-trong-lac-trung-thanh-dong"],
    "lang-nghe-nau-ruou-phu-le": ["lang-nghe-truyen-thong-phu-le"],
    # Events
    "le-via-ba-co-hy": ["le-cung-lau-ba-ram-thang-gieng"],
    "le-hoi-cau-ngu": ["le-hoi-nghinh-ong-duyen-hai"],
    "le-chol-chhnam-thmay": ["le-hoi-chol-chnam-thmay-tai-chua-ky-son"],
    # Products & Dishes
    "keo-dua-sap-vicosap": ["vicosap-keo-dua-sap-ocop-5-sao"],
    "tau-hu-ky-my-hoa": [
        "tau-hu-ky-cai-von",
        "tau-hu-ky-my-hoa-binh-minh",
        "tau-hu-ky-my-hoa-dong-goi",
    ],
    "banh-trang-nem-cu-lao-may": ["banh-trang-nem-cu-lao-luc-si"],
    "bot-nua-tra-cu": ["bot-nua-bot-khoai-mon-an-quang-huu"],
    "bun-tuoi-sau-thanh": ["bun-tuoi-va-hu-tieu-sau-thanh"],
    "banh-phong-khoai-lang-nhat-ngoc": ["banh-nhat-ngoc"],
    "chom-chom-an-binh": ["chom-chom-binh-hoa-phuoc-rambutan"],
    "chom-chom-cai-mon": ["chom-chom-cho-lach"],
    "chom-chom-con-tan-quy": ["chom-chom-cau-ke"],
    "ruou-truyen-thong-cuu-long-cuu-long-my-tuu": ["cuu-long-my-tuu-ruou-ocop-mang-thit"],
    "cua-bien-thanh-phu": [
        "cua-bien-va-ngheu-thanh-phu",
        "ngheu-so-cua-bien-thanh-phu",
    ],
    "ngheu-thanh-hai": ["hop-tac-xa-thuy-san-thanh-loi-ngheu-thanh-hai-ocop"],
    "mat-ong-rung-ban-nguyen-van-bao": ["mat-ong-rung-ban-my-long-nam"],
    "muoi-ba-tri": ["muoi-bao-thanh"],
    "chao-dua-thuan-duyen-tam-binh": ["san-pham-chao-dua-chao-chanh-day-thuan-duyen-ocop-4-sao"],
    "nuoc-cot-dua-va-san-pham-dua-ocop-beinco": ["san-pham-dua-ocop-beinco"],
    "sau-rieng-cap-dong-chanh-thu": ["sau-rieng-cap-dong-cho-lach"],
    "sau-rieng-ri6": ["sau-rieng-ri-6-long-ho"],
    "thanh-tra-binh-minh": ["thanh-tra"],
    "tra-gung-mat-ong-nguyen-chat-gingo": ["tra-gung-mat-ong-dong-binh"],
    "tranh-dua-cocohand": [
        "tranh-dua-hop-kieng-cocohand",
        "tranh-dua-op-nia-tre-cocohand",
    ],
    "keo-dua-ben-tre": ["keo-dua-thu-cong-ben-tre"],
    "buoi-nam-roi-binh-minh": ["buoi-nam-roi-my-hoa"],
    "buoi-da-xanh": ["buoi-da-xanh-giong-trom"],
    "dua-xiem-xanh": ["dua-xiem-xanh-giong-trom"],
    "xoai-tu-quy": ["xoai-tu-quy-va-cua-bien-thanh-phong-ocop"],
    "kho-ca-bien-thanh-phu": [
        "ca-kho-dac-san-thanh-phong-ocop",
        "kho-ca-bong-lau-ca-du-do-ca-bong-cat-mot-nang-thanh-phong",
    ],
    "tom-duyen-hai": [
        "tom-su-nuoc-lo-tra-vinh",
        "tom-su-sinh-thai-tra-vinh",
    ],
    "nhan-ido-an-binh": ["nhan-an-binh-tam-binh"],
    "oc-gao-phu-da": [
        "oc-gao-vinh-binh",
        "oc-gao-con-phu-da",
        "oc-gao-con-phu-da-hap-sa",
    ],
    "com-dua-com-trai-dua": ["com-hap-trai-dua"],
    "banh-xeo-mien-tay": ["banh-xeo-cu-lao"],
    "banh-canh-bot-xat-ben-tre": ["banh-canh-ben-tre"],
    "khoai-lang-mam-song-cuon-la-cach": ["mam-song-khoai-lang"],
    "bun-nuoc-leo-tra-vinh": ["bun-nuoc-leo-vinh-long"],
}

# Mistyped entities (10).
WAVE6_TYPE_FIXES: dict[str, str] = {
    "banh-bao-tai-co": "restaurant",
    "banh-flan-14": "restaurant",
    "banh-xeo-long-binh-2": "restaurant",
    "com-ga-bong-viet": "restaurant",
    "com-ga-xoi-mo-5-vi-ben-tre": "restaurant",
    "lau-ca-linh-bong-dien-dien": "dish",
    "lau-mam-ben-tre": "dish",
    "lau-mam-mien-tay": "dish",
    "hu-tieu-soi-no-cong": "craft_village",
    "cho-ben-tre": "attraction",
}

WAVE6_ATTR_PATCHES: dict[str, dict[str, Any]] = {
    "hu-tieu-soi-no-cong": {
        "specialty": "Hủ tiếu sợi Nô Công",
    },
}

WAVE6_NAME_FIXES: dict[str, str] = {
    "nha-co-cau-ke": "Nhà cổ Cầu Kè (Nhà cổ Huỳnh Kỳ)",
    "nam-khanh": "Điểm du lịch sinh thái Năm Khanh",
    "nghe-thuat-hat-boi-tinh-vinh-long": "Nghệ thuật Hát bội Vĩnh Long",
    "festival-gach-gom-do-kinh-te-xanh-tinh-vinh-long-vinh-long": "Festival Gạch Gốm Đỏ – Kinh tế Xanh Vĩnh Long",
}

WAVE6_SUMMARY_FIXES: dict[str, str] = {
    "bai-boi-rung-ngap-man-ba-tri-ben-tre": (
        "Hệ sinh thái bãi bồi và rừng ngập mặn ven cửa biển Tân Thủy – Ba Tri, "
        "nơi hội tụ phù sa sông Hàm Luông và biển Đông, tạo sinh cảnh cho nghêu, sò, "
        "cua biển và chim nước trú ngụ."
    ),
    "nha-co-cau-ke": (
        "Ngôi nhà cổ khởi dựng năm 1924 tại Cầu Kè, giao thoa tinh tế giữa kiến trúc "
        "Pháp cổ điển và nếp nhà gỗ truyền thống Nam Bộ với nhiều chi tiết chạm trổ tinh xảo."
    ),
}


def _non_empty(val: Any) -> bool:
    return bool(val.strip()) if isinstance(val, str) else bool(val)


def _parse_attrs(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _load_dotenv(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _open_conn(args: argparse.Namespace) -> tuple[Any, Any, bool]:
    if args.sqlite is not None:
        conn = sqlite3.connect(str(args.sqlite))
        conn.row_factory = sqlite3.Row
        return conn, conn.cursor(), False
    _load_dotenv(REPO_ROOT / ".env")
    _load_dotenv(Path("/opt/vinhlong360/.env"))
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn.startswith(("postgres://", "postgresql://")):
        raise SystemExit("DATABASE_URL not configured for --postgres-env")
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore

    conn = psycopg2.connect(dsn)
    return conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor), True


def _load_snapshot(
    cur: Any, is_pg: bool
) -> tuple[dict[str, dict[str, Any]], list[tuple[str, str, str]], list[dict[str, Any]]]:
    cols = (
        'id, type, name, summary, "placeId", address, phone, website, hours, '
        'price_range, sub_category, best_time, highlight, attributes'
        if is_pg
        else "id, type, name, summary, placeId, address, phone, website, hours, "
        "price_range, sub_category, best_time, highlight, attributes"
    )
    cur.execute(f"SELECT {cols} FROM entities")
    entities = {d["id"]: d for row in cur.fetchall() for d in [{**dict(row), "attrs": _parse_attrs(row["attributes"])}]}
    cur.execute("SELECT from_id, to_id, type FROM relationships")
    rels = [(r["from_id"], r["to_id"], r["type"]) for r in cur.fetchall()]
    cur.execute("SELECT id, title, stops FROM itineraries")
    return entities, rels, [dict(r) for r in cur.fetchall()]


def _ward_index(entities: dict[str, dict[str, Any]]) -> tuple[set[str], dict[str, set[str]], set[str]]:
    places = {eid for eid, r in entities.items() if r["type"] == "place" and eid != "vinh-long"}
    members: dict[str, set[str]] = defaultdict(set)
    for eid, r in entities.items():
        if r["type"] != "place" and r.get("placeId") in places:
            members[r["placeId"]].add(eid)
    return places, members, {w for w, s in members.items() if s}


def _build_raw_merge_pairs(entities: dict[str, dict[str, Any]], hard_set: set[str]) -> list[tuple[str, str]]:
    all_ids = set(entities)
    return [
        (src, dst)
        for dst, srcs in WAVE6_MERGES_BY_DST.items()
        if dst in all_ids and dst not in hard_set
        for src in srcs
        if src in all_ids and src != dst and src not in hard_set and entities[src]["type"] != "place"
    ]


def _needs_ward_rescue(
    sw: str | None,
    dst: str,
    dw: str | None,
    covered_wards: set[str],
    sim: dict[str, set[str]],
    all_srcs: set[str],
) -> tuple[bool, bool]:
    if sw not in covered_wards or (sim[sw] - all_srcs):
        return False, False
    conflict = dw in covered_wards and len(sim[dw] - all_srcs - {dst}) == 0
    return True, conflict


def _compute_merges(
    entities: dict[str, dict[str, Any]],
    ward_members: dict[str, set[str]],
    covered_wards: set[str],
    hard_set: set[str],
) -> tuple[dict[str, str], dict[str, str], list[dict[str, str]]]:
    sim = {w: set(m) - hard_set for w, m in ward_members.items()}
    merge_map: dict[str, str] = {}
    transfers: dict[str, str] = {}
    exempted: list[dict[str, str]] = []

    raw_pairs = _build_raw_merge_pairs(entities, hard_set)
    all_srcs = {s for s, _ in raw_pairs}
    for src, dst in raw_pairs:
        sw = entities[src].get("placeId")
        dw = transfers.get(dst, entities[dst].get("placeId"))
        rescue, conflict = _needs_ward_rescue(sw, dst, dw, covered_wards, sim, all_srcs)
        if rescue and conflict:
            exempted.append({"id": src, "ward": str(sw), "reason": "merge_would_create_white_zone"})
            continue
        if rescue and sw is not None:
            sim.get(dw or "", set()).discard(dst)
            sim.setdefault(sw, set()).add(dst)
            transfers[dst] = sw
        merge_map[src] = dst
        sim.get(sw or "", set()).discard(src)

    exempted.extend({"id": w, "ward": w, "reason": "ward_became_empty"} for w in covered_wards if len(sim[w]) == 0)
    return merge_map, transfers, exempted


def _apply_merge_utilities(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], merge_map: dict[str, str]
) -> None:
    for src, dst in sorted(merge_map.items()):
        for field in ("phone", "website", "hours"):
            cur_val = entities[dst]["attrs"].get(field) or entities[dst].get(field)
            src_val = entities[src]["attrs"].get(field) or entities[src].get(field)
            if not _non_empty(cur_val) and _non_empty(src_val):
                cleaned = str(src_val).strip()
                entities[dst]["attrs"][field] = cleaned
                entities[dst][field] = cleaned
                up = updates.setdefault(dst, {})
                up[field] = cleaned
                up["save_attrs"] = True


def _apply_scalar_map(
    entities: dict[str, dict[str, Any]],
    updates: dict[str, dict[str, Any]],
    removed: set[str],
    field: str,
    mapping: dict[str, str],
    *,
    sync_cti: bool = False,
) -> None:
    for eid, new_val in mapping.items():
        if eid in entities and eid not in removed and entities[eid][field] != new_val:
            entities[eid][field] = new_val
            up = updates.setdefault(eid, {})
            up[field] = new_val
            if sync_cti:
                up["sync_cti"] = True


def _apply_type_name_summary_fixes(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], removed: set[str]
) -> None:
    _apply_scalar_map(entities, updates, removed, "type", WAVE6_TYPE_FIXES, sync_cti=True)
    for eid, patch in WAVE6_ATTR_PATCHES.items():
        if eid in entities and eid not in removed:
            entities[eid]["attrs"].update(patch)
            updates.setdefault(eid, {}).update({"save_attrs": True, "sync_cti": True})
    _apply_scalar_map(entities, updates, removed, "name", WAVE6_NAME_FIXES)
    _apply_scalar_map(entities, updates, removed, "summary", WAVE6_SUMMARY_FIXES)


def _validate_cti_updates(entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]]) -> None:
    for eid, up in updates.items():
        if not up.get("sync_cti"):
            continue
        row = entities[eid]
        effective = {c: row[c] for c in UNIVERSAL if _non_empty(row.get(c))}
        effective.update(row["attrs"])
        uni, det, skipped = split_typed(row["type"], effective)
        assert not skipped, f"{eid} has uncoercible attrs after fix: {skipped}"
        up["_uni_cols"] = {k: v for k, v in uni.items() if row.get(k) != v}
        up["_det_row"] = det


def _apply_entity_updates(
    entities: dict[str, dict[str, Any]],
    merge_map: dict[str, str],
    transfers: dict[str, str],
    removed: set[str],
) -> dict[str, dict[str, Any]]:
    updates: dict[str, dict[str, Any]] = {
        dst: {"placeId": pid} for dst, pid in transfers.items() if entities[dst].get("placeId") != pid
    }
    _apply_merge_utilities(entities, updates, merge_map)
    _apply_type_name_summary_fixes(entities, updates, removed)
    _validate_cti_updates(entities, updates)
    return updates


def _rewrite_relationships(
    rels: list[tuple[str, str, str]], merge_map: dict[str, str], surviving_ids: set[str]
) -> list[tuple[str, str, str]]:
    out: set[tuple[str, str, str]] = set()
    for f_id, t_id, rtype in rels:
        nf, nt = merge_map.get(f_id, f_id), merge_map.get(t_id, t_id)
        if nf in surviving_ids and nt in surviving_ids and nf != nt:
            out.add((nf, nt, rtype))
    return sorted(out)


def _remap_stop(stop: Any, merge_map: dict[str, str], surviving_ids: set[str]) -> tuple[str, Any] | None:
    sid = stop.get("id", "") if isinstance(stop, dict) else stop
    mapped = merge_map.get(sid, sid)
    if mapped not in surviving_ids:
        return None
    cur_stop = dict(stop, id=mapped) if isinstance(stop, dict) else mapped
    return mapped, cur_stop


def _rewrite_itineraries(
    itineraries: list[dict[str, Any]], merge_map: dict[str, str], surviving_ids: set[str]
) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    for it in itineraries:
        raw = it.get("stops")
        old_stops = json.loads(raw) if isinstance(raw, str) else list(raw or [])
        new_stops: list[Any] = []
        last_sid: str | None = None
        for stop in old_stops:
            remapped = _remap_stop(stop, merge_map, surviving_ids)
            if remapped is None:
                continue
            mapped, cur_stop = remapped
            if mapped != last_sid:
                last_sid = mapped
                new_stops.append(cur_stop)
        assert new_stops, f"Itinerary {it['id']} became empty after cleanup"
        if json.dumps(old_stops, sort_keys=True) != json.dumps(new_stops, sort_keys=True):
            updates.append({"id": it["id"], "stops": new_stops})
    return updates


def _resolve_chain(src: str, dst: str, combined: dict[str, str]) -> str:
    seen = {src}
    cur = dst
    while cur in combined and cur not in seen:
        seen.add(cur)
        cur = combined[cur]
    return cur


def _merge_redirects(
    redirects_path: Path | None, merge_map: dict[str, str], surviving_ids: set[str]
) -> dict[str, str]:
    existing: dict[str, str] = {}
    if redirects_path and redirects_path.exists():
        existing = json.loads(redirects_path.read_text(encoding="utf-8"))
    combined = {**existing, **merge_map}
    flattened: dict[str, str] = {}
    for src, dst in combined.items():
        cur = _resolve_chain(src, dst, combined)
        if cur != src and cur in surviving_ids and src not in surviving_ids:
            flattened[src] = cur
    for k, v in flattened.items():
        assert k != v and v not in flattened and v in surviving_ids
    return dict(sorted(flattened.items()))


def _build_plan(
    entities: dict[str, dict[str, Any]],
    rels: list[tuple[str, str, str]],
    itineraries: list[dict[str, Any]],
    redirects_path: Path | None,
) -> dict[str, Any]:
    places, ward_members, covered_wards = _ward_index(entities)
    hard_set = {eid for eid in WAVE6_HARD_DELETES if eid in entities and eid not in places}
    merge_map, transfers, exempted = _compute_merges(entities, ward_members, covered_wards, hard_set)
    assert not exempted, f"Exempted guardrails triggered: {exempted}"

    removed = hard_set | set(merge_map)
    surviving_ids = set(entities) - removed
    updates = _apply_entity_updates(entities, merge_map, transfers, removed)
    remapped_rels = _rewrite_relationships(rels, merge_map, surviving_ids)
    itin_updates = _rewrite_itineraries(itineraries, merge_map, surviving_ids)
    redirects = _merge_redirects(redirects_path, merge_map, surviving_ids)

    return {
        "counts": {
            "before_entities": len(entities),
            "after_entities": len(surviving_ids),
            "catalog_before": sum(1 for r in entities.values() if r["type"] != "place"),
            "catalog_after": sum(1 for eid in surviving_ids if entities[eid]["type"] != "place"),
            "merged": len(merge_map),
            "hard_deleted": len(hard_set),
            "type_fixes": sum(1 for u in updates.values() if "type" in u),
            "name_fixes": sum(1 for u in updates.values() if "name" in u),
            "summary_fixes": sum(1 for u in updates.values() if "summary" in u),
            "covered_wards": len(covered_wards),
            "redirects_total": len(redirects),
            "itineraries_updated": len(itin_updates),
            "before_relationships": len(rels),
            "after_relationships": len(remapped_rels),
        },
        "hard_deletes": sorted(hard_set),
        "merge_map": dict(sorted(merge_map.items())),
        "entity_updates": updates,
        "entities_state": entities,
        "remapped_rels": remapped_rels,
        "itinerary_updates": itin_updates,
        "redirects": redirects,
    }


def _sync_changed_cti(conn: Any, is_pg: bool, eid: str, etype: str, det: dict[str, Any]) -> None:
    ph = "%s" if is_pg else "?"
    kind = KIND_OF_TYPE.get(etype)
    table = KIND_TABLE.get(kind or "")
    cur = conn.cursor()
    for stale_table in DETAIL_TABLES:
        if stale_table != table:
            cur.execute(f"DELETE FROM {stale_table} WHERE entity_id = {ph}", [eid])
    _sync_cti_detail_row(conn, is_pg, ph, eid, kind, table, det)


def _write_entity_update(conn: Any, is_pg: bool, eid: str, up: dict[str, Any], row: dict[str, Any]) -> None:
    ph = "%s" if is_pg else "?"
    col_map: dict[str, Any] = {
        c: up[c] for c in ("type", "name", "summary", "placeId", "phone", "website", "hours") if c in up
    }
    col_map.update(up.get("_uni_cols") or {})
    cols = [f'"{k}" = {ph}' for k in col_map]
    vals: list[Any] = list(col_map.values())
    if up.get("save_attrs"):
        cols.append(f"attributes = {ph}")
        if is_pg:
            import psycopg2.extras  # type: ignore

            vals.append(psycopg2.extras.Json(row["attrs"]))
        else:
            vals.append(json.dumps(row["attrs"], ensure_ascii=False))
    if cols:
        conn.cursor().execute(f"UPDATE entities SET {', '.join(cols)} WHERE id = {ph}", [*vals, eid])
    if up.get("sync_cti"):
        _sync_changed_cti(conn, is_pg, eid, row["type"], up.get("_det_row") or {})


def _apply_sqlite(conn: sqlite3.Connection, plan: dict[str, Any]) -> None:
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    removed = sorted(set(plan["merge_map"]) | set(plan["hard_deletes"]))

    for item in plan["itinerary_updates"]:
        cur.execute("UPDATE itineraries SET stops = ? WHERE id = ?", (json.dumps(item["stops"], ensure_ascii=False), item["id"]))
    for eid, up in plan["entity_updates"].items():
        _write_entity_update(conn, False, eid, up, plan["entities_state"][eid])

    cur.execute("DELETE FROM relationships")
    cur.executemany("INSERT OR IGNORE INTO relationships (from_id, to_id, type) VALUES (?, ?, ?)", plan["remapped_rels"])
    if removed:
        for eid in removed:
            delete_entity_details(conn, False, eid)
        ph = ",".join("?" for _ in removed)
        for tbl in ("image_suggestions", "entity_snapshot_generation", "entity_changes"):
            cur.execute(f"DELETE FROM {tbl} WHERE entity_id IN ({ph})", removed)
        cur.execute(f"DELETE FROM reports WHERE target_type = 'entity' AND target_id IN ({ph})", removed)
        cur.execute(f"DELETE FROM entities WHERE id IN ({ph})", removed)

    cur.execute("INSERT INTO entities_fts(entities_fts) VALUES('rebuild')")
    conn.commit()
    conn.execute("VACUUM")


def _remap_pg_refs(cur: Any, merge_map: dict[str, str]) -> None:
    for src, dst in merge_map.items():
        cur.execute("UPDATE posts SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute("UPDATE correction_items SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute("UPDATE follows SET target_id = %s WHERE target_type = 'entity' AND target_id = %s", (dst, src))
        cur.execute("UPDATE featured_entities SET entity_id = %s WHERE entity_id = %s", (dst, src))
        for tbl in ("user_visits", "saved_entities", "event_rsvp"):
            cur.execute(
                f"DELETE FROM {tbl} a WHERE entity_id = %s AND EXISTS "
                f"(SELECT 1 FROM {tbl} b WHERE b.user_id = a.user_id AND b.entity_id = %s)",
                (src, dst),
            )
            cur.execute(f"UPDATE {tbl} SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute(
            "DELETE FROM entity_ratings WHERE entity_id = %s AND EXISTS "
            "(SELECT 1 FROM entity_ratings b WHERE b.entity_id = %s)",
            (src, dst),
        )
        cur.execute("UPDATE entity_ratings SET entity_id = %s WHERE entity_id = %s", (dst, src))


def _apply_postgres(conn: Any, plan: dict[str, Any]) -> None:
    import psycopg2.extras  # type: ignore

    cur = conn.cursor()
    for item in plan["itinerary_updates"]:
        cur.execute("UPDATE itineraries SET stops = %s WHERE id = %s", (psycopg2.extras.Json(item["stops"]), item["id"]))
    for eid, up in plan["entity_updates"].items():
        _write_entity_update(conn, True, eid, up, plan["entities_state"][eid])

    cur.execute("DELETE FROM relationships")
    if plan["remapped_rels"]:
        psycopg2.extras.execute_values(
            cur, "INSERT INTO relationships (from_id, to_id, type) VALUES %s ON CONFLICT DO NOTHING", plan["remapped_rels"], page_size=500
        )

    _remap_pg_refs(cur, plan["merge_map"])
    removed = sorted(set(plan["merge_map"]) | set(plan["hard_deletes"]))
    if removed:
        for tbl in (
            "user_visits", "saved_entities", "event_rsvp", "featured_entities",
            "user_personalization_events", "correction_items", "entity_claims",
            "entity_snapshot_generation", "entity_changes", "entity_ratings", *DETAIL_TABLES,
        ):
            cur.execute(f"DELETE FROM {tbl} WHERE entity_id = ANY(%s)", (removed,))
        cur.execute("DELETE FROM follows WHERE target_type = 'entity' AND target_id = ANY(%s)", (removed,))
        cur.execute("DELETE FROM reports WHERE target_type = 'entity' AND target_id = ANY(%s)", (removed,))
        cur.execute("UPDATE posts SET entity_id = NULL WHERE entity_id = ANY(%s)", (removed,))
        cur.execute("DELETE FROM entities WHERE id = ANY(%s)", (removed,))
    conn.commit()


def _write_report(
    report_out: Path | None,
    plan: dict[str, Any],
    *,
    apply_changes: bool,
    is_pg: bool,
) -> None:
    if report_out is None:
        return
    out = {
        "mode": "apply" if apply_changes else "dry-run",
        "backend": "postgres" if is_pg else "sqlite",
        "counts": plan["counts"],
        "hard_deletes": plan["hard_deletes"],
        "merge_map": plan["merge_map"],
        "type_fixes": {k: v for k, v in WAVE6_TYPE_FIXES.items() if k in plan["entity_updates"]},
        "name_fixes": {k: v for k, v in WAVE6_NAME_FIXES.items() if k in plan["entity_updates"]},
        "summary_fixes": sorted(k for k in WAVE6_SUMMARY_FIXES if k in plan["entity_updates"]),
    }
    report_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src_group = ap.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--sqlite", type=Path)
    src_group.add_argument("--postgres-env", action="store_true")
    mode_group = ap.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true")
    mode_group.add_argument("--apply", action="store_true")
    ap.add_argument("--redirects-file", type=Path)
    ap.add_argument("--report-out", type=Path)
    args = ap.parse_args(argv)
    apply_changes = bool(args.apply)

    conn, cur, is_pg = _open_conn(args)
    try:
        entities, rels, itineraries = _load_snapshot(cur, is_pg=is_pg)
        plan = _build_plan(entities, rels, itineraries, args.redirects_file)
        if apply_changes:
            (_apply_postgres if is_pg else _apply_sqlite)(conn, plan)
        else:
            conn.rollback()
        if args.redirects_file is not None and apply_changes:
            args.redirects_file.write_text(json.dumps(plan["redirects"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _write_report(args.report_out, plan, apply_changes=apply_changes, is_pg=is_pg)
        print(f"[{'APPLIED' if apply_changes else 'DRY-RUN'}][{'postgres' if is_pg else 'sqlite'}] {json.dumps(plan['counts'], ensure_ascii=False)}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

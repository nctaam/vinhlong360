#!/usr/bin/env python3
"""Deterministic 3-phase entity pruning, duplicate merge & 301 redirect builder.

Supports both local SQLite (`--sqlite`) and VPS PostgreSQL (`--postgres-env`).
All deletions, merges, curated attribute sync, itinerary stop remaps,
relationship cleanups, CTI detail syncs, and FTS rebuilds execute transactionally.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "agent"))

try:
    from entity_details import (
        DETAIL_TABLES,
        JSONB_COLUMNS,
        KIND_TABLE,
        UNIVERSAL,
        split_typed,
    )
    from entity_schemas import KIND_OF_TYPE
except ImportError:  # pragma: no cover - standalone fallback
    DETAIL_TABLES = (
        "entity_place_details",
        "entity_food_details",
        "entity_product_details",
        "entity_lodging_details",
        "entity_event_details",
        "entity_experience_details",
        "entity_facility_details",
        "entity_person_details",
        "entity_adminplace_details",
    )
    JSONB_COLUMNS = frozenset({"ingredients", "amenities", "merged_from"})
    UNIVERSAL = [
        "address", "phone", "website", "hours",
        "price_range", "sub_category", "best_time", "highlight",
    ]
    KIND_TABLE = {}
    KIND_OF_TYPE = {}
    split_typed = None  # type: ignore[assignment]

UNIVERSAL_SET: frozenset[str] = frozenset(UNIVERSAL)

# ---------------------------------------------------------------------------
# Guardrails & Canonical Whitelist
# ---------------------------------------------------------------------------

PROTECTED_IDS: frozenset[str] = frozenset(
    {
        "ben-xe-mien-tay-hcm",
        "chua-ang",
        "chua-vam-ray",
        "van-thanh-mieu",
        "cho-noi-tra-on",
        "chua-tien-chau-tien-chau-tu",
        "bun-nuoc-leo-tra-vinh",
        "ca-tai-tuong-chien-xu",
        "banh-canh-bot-xat-ben-tre",
        "ca-loc-nuong-trui",
        "homestay-ut-trinh",
        "homestay-ut-trinh-con-tam-hiep",
        "mekong-riverside-homestay",
        "nha-dua-cocohome",
        "cu-lao-an-binh",
        "de-an-di-san-duong-dai-mang-thit",
        "chua-shanghamangala-khmer-vung-liem",
        "lang-nghe-gom-do-mang-thit",
        "lo-gach-mang-thit",
        "tau-nha-hang-sai-gon-vinh-long",
        "nha-hang-noi-ben-tre",
        "lang-be---am-thuc-du-lich-sinh-thai",
        "forever-green-resort",
        "diamond-stars-ben-tre-hotel",
        "mekong-home",
        "ba-dong-beach-resort",
        "khu-du-lich-sinh-thai-deja-vu-huynh-kha",
        "chua-hang-kompong-chray",
        "ao-ba-om",
        "cheo-xuong-rach-an-binh",
        "dap-xe-miet-vuon",
        "le-chol-chhnam-thmay",
        "sen-dolta",
        "le-hoi-ok-om-bok",
        "lau-tai-co",
    }
)

STATIC_LEGACY_REDIRECTS: dict[str, str] = {
    "van-thanh-mieu-vinh-long": "van-thanh-mieu",
    "lang-gom-mang-thit": "lang-nghe-gom-do-mang-thit",
    "cu-lao-an-binh-long-ho": "cu-lao-an-binh",
}

# ---------------------------------------------------------------------------
# Phase 1: Hard Delete Lists & Rules
# ---------------------------------------------------------------------------

PHASE_1A_IDS: tuple[str, ...] = (
    "prov-1",
    "ben-tre-tong-tai-romantic-2day-001",
)

PHASE_1B_ARCHIVED_EVENTS: tuple[str, ...] = (
    "festival-dua-sap-cau-ke-tra-vinh",
    "giai-ban-marathon-vinh-long-mo-rong-hanh-trinh-trai-tim-mekong-vinh-long",
    "giai-marathon-ben-tre-xu-dua-ben-tre",
    "giai-marathon-tra-vinh-tra-vinh-marathon-tra-vinh",
    "giai-the-thao-dan-toc-quoc-phong-tinh-tra-vinh-tra-vinh",
    "giai-vo-dich-xe-dap-tinh-vinh-long-mo-rong-vinh-long",
    "hoi-cho-thuong-mai-cay-giong-hoa-kieng-cho-lach",
    "hoi-cho-thuong-mai-du-lich-ben-tre-ben-tre",
    "hoi-cho-thuong-mai-du-lich-tinh-tra-vinh-tra-vinh",
    "hoi-cho-xuc-tien-thuong-mai-du-lich-vinh-long-dip-tet-nguyen-dan-vinh-long",
    "lien-hoan-van-nghe-quan-chung-tinh-tra-vinh-tra-vinh",
    "ngay-hoi-banh-dan-gian-nam-bo-ket-hop-hoi-cho-ocop-vinh-long-vinh-long",
    "ngay-hoi-van-hoa-the-thao-va-du-lich-huyen-cho-lach-ben-tre",
    "trien-lam-hoi-cho-nong-nghiep-cong-nghe-cao-ben-tre-ben-tre",
    "tuan-le-van-hoa-am-thuc-an-hoi-2026",
    "tuan-le-van-hoa-the-thao-va-du-lich-tinh-vinh-long-vinh-long",
)

PHASE_1C_FACILITIES: tuple[str, ...] = (
    "cong-an-tp-ben-tre-ben-tre",
    "ben-pha-ham-luong-ben-tre",
    "vinmart-vinmart-vinh-long-vinh-long",
    "wifi-cong-cong-khu-vuc-trung-tam-tp-vinh-long-vinh-long",
    "sieu-thi-coop-mart-vinh-long",
    "sieu-thi-dien-may-cho-lon-vinh-long",
    "sieu-thi-go-ben-tre",
    "sieu-thi-go-tra-vinh",
    "sieu-thi-thuy-tien",
    "co-opmart-ben-tre-ben-tre",
    "co-opmart-vinh-long-vinh-long",
    "sieu-thi-co-opmart-tra-vinh-tra-vinh",
    "sieu-thi-go-big-c-ben-tre-ben-tre",
    "agribank-chi-nhanh-vinh-long-vinh-long",
    "atm-vietcombank-benh-vien-da-khoa-tinh-vinh-long",
    "bidv-chi-nhanh-ben-tre-atm-dai-lo-dong-khoi-ben-tre",
    "bidv-chi-nhanh-vinh-long-vinh-long",
    "vietcombank-chi-nhanh-ben-tre-ben-tre",
    "vietcombank-chi-nhanh-vinh-long-vinh-long",
    "cua-hang-viettel-dinh-tien-hoang-vinh-long",
    "cua-hang-viettel-pham-hung-vinh-long",
    "cua-hang-viettel-store-trung-nu-vuong-vinh-long",
    "diem-giao-dich-vinaphone-nguyen-thi-dinh-ben-tre",
    "diem-giao-dich-vinaphone-vnpt-cach-mang-thang-8-ben-tre",
    "buu-dien-trung-tam-tp-ben-tre-ben-tre",
    "buu-dien-trung-tam-vinh-long-vinh-long",
    "nha-thuoc-fpt-long-chau-108a3-dong-khoi-ben-tre",
    "nha-thuoc-fpt-long-chau-1237-quoc-lo-54-vinh-long",
    "nha-thuoc-fpt-long-chau-77-duong-1-5-vinh-long",
    "nha-thuoc-pharmacity-doan-hoang-minh-ben-tre",
)

PHASE_1D_REGEX = re.compile(
    r"(jollibee|baskin robbins|bingsu|pizza|dimsum|mì cay|kimchi|trà sữa|milktea|"
    r"bún bò huế|phở bắc|bún đậu mắm tôm|tiệc cưới|buffet|quán nhậu|cơm bình dân|"
    r"cơm tấm|bánh mì |the coffee house|monkey tea|cafe de paris|nướng ngói|"
    r"food & beer|beer garden|martini cocktail|mèo ú kitchen|meo u kitchen|"
    r"hot pot 72|the hotpot|yogurt garden|cake & drink|tea & cake|drinks & tea|"
    r"ola tea|neyu tea)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Phase 2 & 3 Rules
# ---------------------------------------------------------------------------

PHASE_2A_MERGES: dict[str, list[str]] = {
    "ao-ba-om": [
        "khu-di-tich-ao-ba-om", "ao-ba-om-ao-vuong",
        "ao-ba-om-ao-vuong-tra-vinh", "khu-van-hoa-du-lich-ao-ba-om",
    ],
    "chua-ang": ["chua-ang-angkorajaborey", "chua-ang-wat-angkor-raig-borei", "chua-ang-angkor-borei"],
    "chua-vam-ray": ["chua-vam-ray-tra-vinh", "chua-vam-ray-chua-phat-nam", "chua-vam-ray-wat-samrong"],
    "chua-hang-kompong-chray": ["chua-hang", "chua-hang-wat-kompong-chray", "chua-hang-cha-lo"],
    "lang-nghe-det-chieu-ca-hom-ben-ba": [
        "lang-nghe-det-chieu-ca-hom", "lang-det-chieu-ca-hom-ham-tan",
        "lang-nghe-det-chieu-ham-tan", "lang-nghe-det-chieu-ca-hon",
    ],
    "lang-nghe-gom-do-mang-thit": ["lang-gach-gom-mang-thit", "lang-nghe-gach-gom-mang-thit-vuong-quoc-do"],
    "nha-gom-tu-buoi": ["nha-gom-tu-buoi-w3", "nha-gom-do-tu-buoi"],
    "nha-tho-cai-mon": ["nha-tho-cai-mon-ben-tre", "nha-tho-cai-mon-cho-lach"],
    "nha-tho-chanh-toa-vinh-long": [
        "nha-tho-chanh-toa-vinh-long-vinh-long",
        "nha-tho-chinh-toa-vinh-long",
        "nha-tho-chinh-toa-vinh-long-nha-tho-chanh-toa",
    ],
    "dinh-tan-hoa": ["dinh-tan-hoa-w3", "dinh-tan-hoa-dinh-cai-doi"],
    "chua-giac-linh": ["chua-giac-linh-tra-vinh", "chua-giac-linh-chua-doi"],
    "chua-tuyen-linh": ["chua-tuyen-linh-ben-tre", "chua-tuyen-linh-mo-cay-bac"],
    "con-oc": ["con-oc-hung-phong", "con-oc-giong-trom-ben-tre"],
    "chua-ong": [
        "chua-ong-vinh-long", "chua-ong-that-phu-mieu",
        "that-phu-mieu-chua-ong", "that-phu-mieu-chua-ong-vinh-long",
    ],
    "dinh-binh-hoa": ["dinh-binh-hoa-ben-tre", "dinh-binh-hoa-giong-trom"],
    "bao-tang-van-hoa-dan-toc-khmer": [
        "bao-tang-van-hoa-dan-toc-khmer-tinh-tra-vinh",
        "bao-tang-van-hoa-dan-toc-khmer-tra-vinh",
    ],
    "bien-con-bung": [
        "khu-du-lich-bien-con-bung", "bien-con-bung-thanh-phu", "bien-con-bung-thanh-phu-ben-tre",
    ],
    "nha-dua-cocohome": ["diem-du-lich-nha-dua-cocohome"],
    "diamond-stars-ben-tre-hotel": ["khach-san-diamond-stars"],
    "vilabasi-hotel": ["vila-basi"],
    "khu-du-lich-sinh-thai-deja-vu-huynh-kha": ["deja-vu-cafe", "deja-huynh-kha-coffee"],
    "nha-hang-phuong-thuy": ["nha-hang-phuong-thuy-1"],
    "nha-hang-nam-son-ben-tre": ["nam-son"],
    "khu-du-lich-somo-farm-cuu-long": ["khu-du-lich-s-mo-farm-cuu-long"],
    "khu-du-lich-vinh-sang": ["khu-du-lich-sinh-thai-vinh-sang-cu-lao-an-binh"],
    "khu-du-lich-truong-huy": ["khu-du-lich-sinh-thai-truong-huy-vinh-long"],
    "du-lich-vuon-chu-7-gat": ["du-lich-vuon-chu-7-gat-vlt"],
    "khach-san-anh-hong": ["khach-san-anh-hong-mang-thit"],
    "nha-hang-lang-chai": ["nha-hang-lang-chai-ben-tre-ben-tre"],
    "banh-canh-bot-xat-ben-tre": ["banh-canh-bot-xat"],
    "banh-canh-ben-co": ["banh-canh-ben-co-tra-vinh"],
    "bun-suong": ["bun-suong-tra-vinh"],
    "chao-cua-dong": ["chao-cua-dong-ben-tre"],
    "loi-choi-sa-ot": ["loi-choi-sa-ot-tra-vinh"],
    "banh-xeo-oc-gao-phu-da": ["banh-xeo-oc-gao-cho-lach"],
    "buoi-da-xanh": ["buoi-da-xanh-ben-tre"],
    "dua-sap-cau-ke": ["dua-sap", "dua-sap-tra-vinh", "dua-sap-sinh-to"],
    "mam-bo-hoc-prohok": ["mam-bo-hoc-tra-vinh"],
    "com-dep-tra-vinh": ["com-dep-khmer"],
    "lo-com-cuu-long-vlt": ["lo-com-cuu-long"],
    "keo-dua-tuyet-phung": ["keo-dua-mo-cay-co-so-tuyet-phung"],
    "chao-dua-thuan-duyen-tam-binh": ["san-pham-ocop-chao-thuan-duyen"],
    "banh-trang-ngot-le-hang": ["banh-trang-ngot-le-hang-htx-banh-trang-cu-lao-may"],
    "tran-dai-nghia": ["tran-dai-nghia-pham-quang-le"],
    "pham-hung": ["pham-hung-pham-van-thien"],
    "khu-luu-niem-nguyen-dinh-chieu": ["khu-di-tich-nguyen-dinh-chieu", "lang-mo-va-khu-tuong-niem-nguyen-dinh-chieu"],
    "khu-luu-niem-tran-dai-nghia": ["khu-luu-niem-tran-dai-nghia-vinh-long"],
    "khu-mo-than-nhan-thoai-ngoc-hau": ["khu-mo-than-nhan-thoai-ngoc-hau-cu-lao-dai"],
    "chua-co-nodol": ["chua-co-chua-nodol-chua-phno-don"],
    "chua-ong-met-bodonisaraj": ["chua-ong-met-botum-vong-sa-som-rong"],
    "chua-o-mich-ratanadiparamkoskeo": ["chua-o-mich-hung-hoa"],
    "phuoc-minh-cung-chua-ong": ["phuoc-minh-cung-chua-ong-tra-vinh"],
    "dinh-phu-le": ["dinh-phu-le-ben-tre"],
    "dinh-tan-giai": ["dinh-tan-giai-vinh-long"],
    "dinh-long-duc": ["dinh-long-duc-tra-vinh"],
    "den-tho-bac-ho": ["den-tho-bac-ho-tra-vinh"],
    "khu-di-tich-dong-khoi": ["khu-di-tich-dong-khoi-ben-tre"],
    "ben-tiep-nhan-vu-khi-con-tau": ["di-tich-lich-su-ben-tiep-nhan-vu-khi-con-tau"],
    "lang-ong-con-tau": ["khu-di-tich-lang-ong-con-tau"],
    "lang-ong-nam-hai-con-bung": ["lang-ong-nam-hai"],
    "lau-ba-lau-ba-co-hy": ["lau-ba-mieu-ba-chua-xu-ba-co-hy"],
    "cu-lao-an-binh": ["cu-lao-an-binh-bao-gom-xa-dong-phu"],
    "cu-lao-dai": ["cu-lao-dai-cu-lao-thanh-binh-quoi-thien"],
    "cu-lao-may": ["cu-lao-may-cu-lao-luc-si-thanh"],
    "con-quy": ["con-quy-song-tien-chau-thanh-ben-tre"],
    "con-phu-da": ["con-phu-da-song-co-chien-cho-lach-ben-tre"],
    "con-ho": ["con-ho-oc-dao-xanh-song-co-chien"],
    "con-chim": ["con-chim-tra-vinh"],
    "san-chim-vam-ho": ["san-chim-vam-ho-ben-tre"],
    "cho-ben-tre": ["cho-ben-tre-cho-trung-tam-ben-tre"],
    "cho-tra-vinh-cho-trung-tam-tra-vinh": ["cho-tra-vinh"],
    "cho-vinh-long": ["cho-vinh-long-cho-trung-tam-vinh-long"],
    "cho-noi-tra-on": ["khu-du-lich-cho-noi-tra-on", "khu-du-lich-cho-noi-tra-on-ap-long-hung"],
    "de-an-di-san-duong-dai-mang-thit": ["di-san-duong-dai-mang-thit"],
    "lau-tai-co": ["quan-lau-tai-co"],
}

PHASE_2B_DELETE: tuple[str, ...] = (
    "long-ho", "huyen-tam-binh", "san-pham-ocop-cau-ngang",
    "san-pham-ocop-thu-cong-my-nghe-tra-cu",
    "san-pham-ocop-vung-liem-cha-lua-thanh-cong-gao-huu-co-tan-dat-mut-dua-la-dua-duc",
    "cong-ty-tnhh-du-lich-sinh-thai-bao-duyen", "du-lich-sinh-thai-bien-thanh-phu",
    "du-lich-sinh-thai-miet-vuon-mo-cay-bac", "trai-nghiem-mua-nuoc-noi",
    "trai-nghiem-cau-ca-cau-tom-song-hau",
)

PHASE_2B_MERGES: dict[str, list[str]] = {
    "chua-ang": ["tham-chua-khmer"],
    "cu-lao-an-binh": ["tham-quan-vuon-trai-cay"],
    "cheo-xuong-rach-an-binh": ["cheo-xuong-ba-la"],
    "dap-xe-miet-vuon": ["dap-xe-cu-lao"],
    "cho-noi-tra-on": ["ngam-binh-minh-co-chien"],
}

PHASE_3A_IDS: tuple[str, ...] = (
    "nha-nghi-phuong-nam", "nha-nghi-quynh-phuc", "nha-nghi-thanh-thao",
    "nha-nghi-nha-co-dai-an", "happy-family-guesthouse", "hotel-phuoc-thinh",
    "oasis-hotel", "ben-tre-farm-stay",
)

PHASE_3B_EXPLICIT: tuple[str, ...] = (
    "caffe-takeaway---tan-ke", "co-dai---sinh-to-giai-khat", "ha-cao-chi-tu-tra-vinh",
    "kafe-home", "khoi---lau-nuong", "khuc-ban-chieu", "lau-bo",
    "ma-van-tai-quan---pham-thai-buong", "pho-lu-hai", "pho-tien",
    "pho-nuong-bien-dong---pham-thai-buong", "quan-chi-yen---trai-cay-dia",
    "quan-vteen---pham-hung", "quan-tan-tan", "quan-pho-91", "pho-91",
    "quan-tuyet---com-ca-ri-ga", "robusta-koi-garden", "sup-khuyet-tat",
    "tau-hu-ngon-lanh", "tau-hu-nong", "ut-ngan-quan---dui-cuu-nuong",
    "xom-nuong-que-nha", "re-tranhcom---2-thang-9", "chau-dong-quan---am-thuc-viet",
    "nha-hang-am-thuc-pho", "nha-hang-huong-sen", "nha-hang-sau-tu",
    "nha-hang-song-thao", "nha-hang-thien-tan", "tiem-ba-khoang",
    "duc-thanh-2---quan-lau-de", "ben-dua-quan---lau-ga-noi", "bun-rieu-cua-thao-my",
    "quan-banh-uot-hai-nen",
)

PHASE_3C_MERGES: dict[str, list[str]] = {
    "le-chol-chhnam-thmay": ["le-hoi-chol-chnam-thmay-va-sen-dolta"],
    "le-hoi-ok-om-bok": [
        "tuan-le-van-hoa-du-lich-gan-voi-le-hoi-ok-om-bok",
        "le-hoi-van-hoa-the-thao-du-lich-dong-bao-khmer-nam-bo-tinh-tra-vinh-tra-vinh",
        "hoi-cho-xuc-tien-thuong-mai-san-pham-cong-nghiep-nong-thon-va-ocop-vinh-long-gan-voi-ok-om-bok-vinh-long",
    ],
}

PHASE_3C_DELETE: tuple[str, ...] = (
    "hoi-thi-don-ca-tai-tu-cai-luong-huyen-long-ho",
    "hoi-cho-dac-san-vung-mien-khu-vuc-dbscl-vinh-long-vinh-long",
    "hoi-thi-san-pham-ocop-va-dac-san-ben-tre-ben-tre",
    "tuan-le-du-lich-tra-vinh-kham-pha-xu-dua-tra-vinh",
    "lien-hoan-don-ca-tai-tu-nam-bo-tinh-ben-tre-ben-tre",
)

PHASE_3D_IDS: tuple[str, ...] = (
    "ca-tra", "ca-tra-tra-vinh", "ca-tra-thuong-pham-vinh-long",
    "nuoc-khoang-thien-nhien-sao-bien-starfiwa", "dua-kho-tra-vinh",
    "dua-sap-cau-ke-dac-san-ben-tre", "khoai-lang-say-gion-mien-tay",
    "cua-hang-ocop-vung-liem", "diem-trung-bay-va-ban-san-pham-ocop-vinh-long-tai-ben-cang",
    "diem-trung-bay-va-gioi-thieu-san-pham-ocop-vinh-long",
    "htx-thuy-san-sinh-thai-thanh-phuoc", "hop-tac-xa-cam-phuong-thuy",
    "hop-tac-xa-dua-sap-cau-ke-tra-vinh",
)


def _norm_nfc(text: str | None) -> str:
    return unicodedata.normalize("NFC", text or "")


def _non_empty(val: Any) -> bool:
    if isinstance(val, str):
        return bool(val.strip())
    return bool(val)


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


def _load_dotenv_into_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _load_curated_map(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {e["id"]: e for e in payload.get("entities", []) if isinstance(e, dict) and e.get("id")}


def _load_snapshot(cur, is_pg: bool) -> tuple[dict[str, dict[str, Any]], list[tuple[str, str, str]], list[dict[str, Any]]]:
    select_sql = (
        'SELECT id, type, name, "placeId", level, "parentId", address, phone, website, hours, attributes, status FROM entities'
        if is_pg
        else "SELECT id, type, name, placeId, level, parentId, address, phone, website, hours, attributes, status FROM entities"
    )
    cur.execute(select_sql)
    entities: dict[str, dict[str, Any]] = {}
    for row in cur.fetchall():
        d = dict(row)
        d["attributes_dict"] = _parse_attrs(d.get("attributes"))
        entities[d["id"]] = d

    cur.execute("SELECT from_id, to_id, type FROM relationships")
    rels = [(r["from_id"], r["to_id"], r["type"]) for r in cur.fetchall()]
    cur.execute("SELECT id, title, stops FROM itineraries")
    return entities, rels, [dict(r) for r in cur.fetchall()]


def _compute_raw_merges(entities: dict[str, dict[str, Any]]) -> dict[str, tuple[str, str]]:
    all_ids = set(entities)
    raw: dict[str, tuple[str, str]] = {}
    for bucket, group in (("2A", PHASE_2A_MERGES), ("2B", PHASE_2B_MERGES), ("3C", PHASE_3C_MERGES)):
        for target, sources in group.items():
            if target not in all_ids:
                continue
            for src in sources:
                eligible = src in all_ids and src != target and src not in PROTECTED_IDS and entities[src]["type"] != "place"
                if eligible:
                    raw[src] = (target, bucket)
    return raw


def _flatten_merges(raw: dict[str, tuple[str, str]], all_ids: set[str]) -> dict[str, tuple[str, str]]:
    flat: dict[str, tuple[str, str]] = {}
    for src, (dst, bucket) in raw.items():
        seen = {src}
        cur_dst = dst
        while cur_dst in raw and cur_dst not in seen:
            seen.add(cur_dst)
            cur_dst = raw[cur_dst][0]
        if cur_dst != src and cur_dst in all_ids:
            flat[src] = (cur_dst, bucket)
    return flat


_STATIC_DELETE_BUCKETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("1A", PHASE_1A_IDS),
    ("1B", PHASE_1B_ARCHIVED_EVENTS),
    ("1C", PHASE_1C_FACILITIES),
    ("2B", PHASE_2B_DELETE),
    ("3A", PHASE_3A_IDS),
    ("3B", PHASE_3B_EXPLICIT),
    ("3C", PHASE_3C_DELETE),
    ("3D", PHASE_3D_IDS),
)


def _dynamic_delete_phase(eid: str, row: dict[str, Any]) -> str | None:
    etype = row["type"]
    if etype == "itinerary":
        return "1E"
    if etype in ("restaurant", "cafe", "dish", "attraction", "experience"):
        if PHASE_1D_REGEX.search(f"{_norm_nfc(row.get('name'))} {eid.replace('-', ' ')}"):
            return "1D"
    if etype == "cafe" and not _non_empty(row.get("phone")) and not _non_empty(row.get("hours")):
        return "3B"
    return None


def _can_delete_entity(eid: str, row: dict[str, Any], merge_map: dict[str, Any], deletes: dict[str, str]) -> bool:
    if eid in PROTECTED_IDS or row["type"] == "place":
        return False
    return eid not in merge_map and eid not in deletes


def _compute_raw_deletes(entities: dict[str, dict[str, Any]], merge_map: dict[str, tuple[str, str]]) -> dict[str, str]:
    deletes: dict[str, str] = {}
    for phase, bucket in _STATIC_DELETE_BUCKETS:
        for eid in bucket:
            row = entities.get(eid)
            if row and _can_delete_entity(eid, row, merge_map, deletes):
                deletes[eid] = phase
    for eid, row in sorted(entities.items()):
        if not _can_delete_entity(eid, row, merge_map, deletes):
            continue
        dyn = _dynamic_delete_phase(eid, row)
        if dyn:
            deletes[eid] = dyn
    return deletes


def _initial_ward_index(
    entities: dict[str, dict[str, Any]],
) -> tuple[set[str], dict[str, set[str]], set[str], dict[str, str]]:
    places = {eid for eid, r in entities.items() if r["type"] == "place" and eid != "vinh-long"}
    ward_members: dict[str, set[str]] = defaultdict(set)
    eff_place: dict[str, str] = {}
    for eid, row in entities.items():
        pid = row.get("placeId")
        if pid:
            eff_place[eid] = pid
        if row["type"] != "place" and pid in places:
            ward_members[pid].add(eid)
    covered = {w for w, members in ward_members.items() if members}
    return places, ward_members, covered, eff_place


def _guard_merges(
    merge_map: dict[str, tuple[str, str]],
    removed_so_far: set[str],
    sim: dict[str, set[str]],
    covered_wards: set[str],
    eff_place: dict[str, str],
) -> tuple[dict[str, str], list[dict[str, str]]]:
    transfers: dict[str, str] = {}
    exempted: list[dict[str, str]] = []
    for src, (dst, bucket) in list(sorted(merge_map.items())):
        sw, dw = eff_place.get(src), eff_place.get(dst)
        if sw in covered_wards and not (sim[sw] - removed_so_far):
            if dw in covered_wards and len(sim[dw] - removed_so_far - {dst}) == 0:
                merge_map.pop(src)
                exempted.append({"id": src, "phase": bucket, "ward": sw, "reason": "merge_source_only_entity_in_ward"})
                continue
            sim.get(dw, set()).discard(dst)
            sim.setdefault(sw, set()).add(dst)
            eff_place[dst] = sw
            transfers[dst] = sw
        sim.get(sw, set()).discard(src)
    return transfers, exempted


def _apply_ward_guards(
    entities: dict[str, dict[str, Any]],
    merge_map: dict[str, tuple[str, str]],
    deletes_by_phase: dict[str, str],
) -> tuple[dict[str, str], list[dict[str, str]], set[str], set[str]]:
    places, ward_members, covered_wards, eff_place = _initial_ward_index(entities)
    sim = {w: set(m) for w, m in ward_members.items()}
    removed = set(deletes_by_phase) | set(merge_map)
    transfers, exempted = _guard_merges(merge_map, removed, sim, covered_wards, eff_place)

    for eid in sorted(list(deletes_by_phase)):
        ward = eff_place.get(eid)
        if ward in covered_wards:
            survivors = [m for m in sim[ward] if m != eid and m not in deletes_by_phase and m not in merge_map]
            if not survivors:
                exempted.append({"id": eid, "phase": deletes_by_phase.pop(eid), "ward": ward, "reason": "hard_delete_would_create_white_zone"})
                continue
        sim.get(ward, set()).discard(eid)
    return transfers, exempted, places, covered_wards


def _collect_utility_updates(
    entities: dict[str, dict[str, Any]], merge_map: dict[str, tuple[str, str]]
) -> dict[str, dict[str, Any]]:
    updates: dict[str, dict[str, Any]] = {}
    for src, (dst, _) in sorted(merge_map.items()):
        cur_up = updates.get(dst, {})
        for field in ("phone", "website", "hours"):
            existing = cur_up.get(field, entities[dst].get(field))
            cand = entities[src].get(field)
            if not _non_empty(existing) and _non_empty(cand):
                cur_up[field] = cand.strip() if isinstance(cand, str) else cand
        if cur_up:
            updates[dst] = cur_up
    return updates


def _sync_curated_addr(
    row: dict[str, Any], attrs: dict[str, Any], curated_e: dict[str, Any], up: dict[str, Any]
) -> bool:
    addr = curated_e.get("address")
    if not _non_empty(addr) or row.get("address") == addr:
        return False
    up["address"] = addr
    attrs["address"] = addr
    return True


def _apply_curated_attrs(
    row: dict[str, Any], attrs: dict[str, Any], curated_e: dict[str, Any] | None
) -> tuple[dict[str, Any], bool]:
    up: dict[str, Any] = {}
    if not curated_e:
        return up, False
    changed = False
    curated_attrs = curated_e.get("attributes")
    if isinstance(curated_attrs, dict):
        for k, v in curated_attrs.items():
            if _non_empty(v) and attrs.get(k) != v:
                attrs[k] = v
                changed = True
                if k in UNIVERSAL_SET:
                    up[k] = v.strip() if isinstance(v, str) else str(v)
        if _non_empty(curated_attrs.get("hours")) and "opening_hours" in attrs:
            attrs.pop("opening_hours", None)
            changed = True
    addr_changed = _sync_curated_addr(row, attrs, curated_e, up)
    return up, (changed or addr_changed)


def _sync_typed_split(row: dict[str, Any], attrs: dict[str, Any], up: dict[str, Any]) -> None:
    if split_typed is None:
        return
    uni, det, _ = split_typed(row["type"], attrs)
    for k, v in uni.items():
        if row.get(k) != v:
            up[k] = v
    if det:
        up["det_upsert"] = det


def _merge_single_entity(
    eid: str,
    row: dict[str, Any],
    transfers: dict[str, str],
    utility_updates: dict[str, dict[str, Any]],
    curated_e: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, bool]:
    attrs = dict(row["attributes_dict"])
    up, attrs_changed = _apply_curated_attrs(row, attrs, curated_e)
    curated_hit = attrs_changed
    if eid in transfers:
        up["placeId"] = transfers[eid]
    for field, val in utility_updates.get(eid, {}).items():
        up[field] = val
        if field == "hours":
            attrs.pop("opening_hours", None)
        attrs[field] = val
        attrs_changed = True
    if attrs_changed:
        _sync_typed_split(row, attrs, up)
        up["attributes"] = attrs
    return (up or None), curated_hit


def _merge_curated_and_utility(
    entities: dict[str, dict[str, Any]],
    surviving_ids: set[str],
    merge_map: dict[str, tuple[str, str]],
    transfers: dict[str, str],
    curated_by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], int]:
    utility_updates = _collect_utility_updates(entities, merge_map)
    entity_updates: dict[str, dict[str, Any]] = {}
    curated_count = 0
    for eid in sorted(surviving_ids):
        up, curated_hit = _merge_single_entity(eid, entities[eid], transfers, utility_updates, curated_by_id.get(eid))
        if up:
            entity_updates[eid] = up
        curated_count += int(curated_hit)
    return entity_updates, utility_updates, curated_count


def _rewrite_relationships(
    rels: list[tuple[str, str, str]],
    rel_remap: dict[str, str],
    surviving_ids: set[str],
) -> list[tuple[str, str, str]]:
    out: set[tuple[str, str, str]] = set()
    for f_id, t_id, rtype in rels:
        nf, nt = rel_remap.get(f_id, f_id), rel_remap.get(t_id, t_id)
        if nf in surviving_ids and nt in surviving_ids and nf != nt:
            out.add((nf, nt, rtype))
    return sorted(out)


def _rewrite_single_stop(stop: Any, stop_remap: dict[str, str], deletes: dict[str, str]) -> tuple[Any, bool, bool]:
    is_dict = isinstance(stop, dict)
    sid = stop.get("id") if is_dict else stop
    mapped = stop_remap.get(sid, sid)
    if mapped in deletes:
        return None, False, True
    if mapped == sid:
        return stop, True, False
    if not is_dict:
        return mapped, True, True
    updated = dict(stop)
    updated["id"] = mapped
    if isinstance(updated.get("note"), str) and sid in updated["note"]:
        updated["note"] = updated["note"].replace(sid, mapped)
    return updated, True, True


def _rewrite_itineraries(
    itineraries: list[dict[str, Any]],
    stop_remap: dict[str, str],
    deletes: dict[str, str],
) -> tuple[list[dict[str, Any]], list[str]]:
    updates: list[dict[str, Any]] = []
    deleted: list[str] = []
    for it in itineraries:
        if it["id"] == "ben-tre-tong-tai-romantic-2day-001":
            deleted.append(it["id"])
            continue
        raw = it.get("stops")
        stops = json.loads(raw) if isinstance(raw, str) else list(raw or [])
        new_stops: list[Any] = []
        last_sid: str | None = None
        changed = False
        for stop in stops:
            rewritten, keep, item_changed = _rewrite_single_stop(stop, stop_remap, deletes)
            changed = changed or item_changed
            if not keep:
                continue
            cur_sid = rewritten.get("id") if isinstance(rewritten, dict) else rewritten
            if last_sid is not None and cur_sid == last_sid:
                changed = True
                continue
            last_sid = cur_sid
            new_stops.append(rewritten)
        if changed:
            updates.append({"id": it["id"], "stops": new_stops})
    return updates, deleted


def _build_redirects(merge_map: dict[str, tuple[str, str]], surviving_ids: set[str]) -> dict[str, str]:
    redirects = {
        src: dst
        for src, (dst, _) in sorted(merge_map.items())
        if dst in surviving_ids and src not in surviving_ids and src != dst
    }
    for alias, dst in STATIC_LEGACY_REDIRECTS.items():
        if dst in surviving_ids and alias not in surviving_ids and alias != dst:
            redirects[alias] = dst
    for k, v in redirects.items():
        assert k != v and v not in redirects and v in surviving_ids, f"Invalid redirect {k} -> {v}"
    return dict(sorted(redirects.items()))


def _summarize_surviving(
    entities: dict[str, dict[str, Any]],
    surviving_ids: set[str],
    transfers: dict[str, str],
    places: set[str],
) -> tuple[dict[str, int], dict[str, int]]:
    final_wards: dict[str, int] = defaultdict(int)
    surviving_by_type: dict[str, int] = defaultdict(int)
    for eid in surviving_ids:
        etype = entities[eid]["type"]
        surviving_by_type[etype] += 1
        if etype != "place":
            pid = transfers.get(eid, entities[eid].get("placeId"))
            if pid in places:
                final_wards[pid] += 1
    return dict(final_wards), dict(sorted(surviving_by_type.items()))


def _count_phases(deletes_by_phase: dict[str, str], merge_map: dict[str, tuple[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for phase in deletes_by_phase.values():
        counts[f"delete_{phase}"] += 1
    for _, bucket in merge_map.values():
        counts[f"merge_{bucket}"] += 1
    return dict(sorted(counts.items()))


def _validate_plan_invariants(
    entities: dict[str, dict[str, Any]],
    removed_ids: set[str],
    covered_wards: set[str],
    final_wards: dict[str, int],
    stop_targets: dict[str, str],
    surviving_ids: set[str],
) -> None:
    for eid in removed_ids:
        assert eid not in PROTECTED_IDS and entities[eid]["type"] != "place"
    for w in covered_wards:
        assert final_wards.get(w, 0) > 0, f"New white-zone ward detected: {w}"
    if "lang-nghe-gom-do-mang-thit" in entities:
        assert "Làng nghề gốm đỏ Mang Thít" in entities["lang-nghe-gom-do-mang-thit"]["name"]
    for v in stop_targets.values():
        assert v in surviving_ids


def _build_plan(
    entities: dict[str, dict[str, Any]],
    rels: list[tuple[str, str, str]],
    itineraries: list[dict[str, Any]],
    curated_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    all_ids = set(entities)
    merge_map = _flatten_merges(_compute_raw_merges(entities), all_ids)
    deletes_by_phase = _compute_raw_deletes(entities, merge_map)
    transfers, exempted, places, covered_wards = _apply_ward_guards(entities, merge_map, deletes_by_phase)

    removed_ids = set(deletes_by_phase) | set(merge_map)
    surviving_ids = all_ids - removed_ids
    final_wards, surviving_by_type = _summarize_surviving(entities, surviving_ids, transfers, places)

    rel_remap = {src: dst for src, (dst, _) in merge_map.items()}
    stop_remap = {**rel_remap, "com-tam-suon-bi-cha": "bun-nuoc-leo-tra-vinh"}
    _validate_plan_invariants(entities, removed_ids, covered_wards, final_wards, stop_remap, surviving_ids)

    entity_updates, utility_updates, curated_count = _merge_curated_and_utility(
        entities, surviving_ids, merge_map, transfers, curated_by_id
    )
    remapped_rels = _rewrite_relationships(rels, rel_remap, surviving_ids)
    itin_updates, deleted_itins = _rewrite_itineraries(itineraries, stop_remap, deletes_by_phase)
    redirects = _build_redirects(merge_map, surviving_ids)

    return {
        "counts": {
            "before_entities": len(all_ids),
            "after_entities": len(surviving_ids),
            "total_removed": len(removed_ids),
            "hard_deleted": len(deletes_by_phase),
            "merged_with_redirect": len(merge_map),
            "redirects_total": len(redirects),
            "curated_entities_synced": curated_count,
            "before_relationships": len(rels),
            "after_relationships": len(remapped_rels),
            "before_itineraries": len(itineraries),
            "after_itineraries": len(itineraries) - len(deleted_itins),
            "covered_wards_before": len(covered_wards),
            "covered_wards_after": sum(1 for w in covered_wards if final_wards.get(w, 0) > 0),
        },
        "phase_breakdown": _count_phases(deletes_by_phase, merge_map),
        "surviving_by_type": surviving_by_type,
        "exempted_for_ward_coverage": exempted,
        "place_id_transfers": transfers,
        "deletes_by_phase": dict(sorted(deletes_by_phase.items())),
        "merge_map": {k: {"target": v[0], "phase": v[1]} for k, v in sorted(merge_map.items())},
        "utility_updates": utility_updates,
        "entity_updates": entity_updates,
        "entities_types": {eid: row["type"] for eid, row in entities.items()},
        "remapped_rels": remapped_rels,
        "itinerary_updates": itin_updates,
        "deleted_itineraries": deleted_itins,
        "redirects": redirects,
    }


def _apply_entity_updates_sqlite(cur: sqlite3.Cursor, plan: dict[str, Any]) -> None:
    update_cols = ("placeId", *UNIVERSAL)
    for eid, up in plan["entity_updates"].items():
        cols: list[str] = []
        vals: list[Any] = []
        for col in update_cols:
            if col in up:
                cols.append(f'"{col}" = ?')
                vals.append(up[col])
        if "attributes" in up:
            cols.append("attributes = ?")
            vals.append(json.dumps(up["attributes"], ensure_ascii=False))
        if cols:
            vals.append(eid)
            cur.execute(f"UPDATE entities SET {', '.join(cols)} WHERE id = ?", vals)


def _apply_sqlite(conn: sqlite3.Connection, plan: dict[str, Any]) -> None:
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    removed = sorted(set(plan["deletes_by_phase"]) | set(plan["merge_map"]))

    for it_id in plan["deleted_itineraries"]:
        cur.execute("DELETE FROM itineraries WHERE id = ?", (it_id,))
    for item in plan["itinerary_updates"]:
        cur.execute("UPDATE itineraries SET stops = ? WHERE id = ?", (json.dumps(item["stops"], ensure_ascii=False), item["id"]))
    _apply_entity_updates_sqlite(cur, plan)

    cur.execute("DELETE FROM relationships")
    cur.executemany("INSERT OR IGNORE INTO relationships (from_id, to_id, type) VALUES (?, ?, ?)", plan["remapped_rels"])

    if removed:
        ph = ",".join("?" for _ in removed)
        for tbl in DETAIL_TABLES:
            cur.execute(f"DELETE FROM {tbl} WHERE entity_id IN ({ph})", removed)
        for tbl in ("image_suggestions", "entity_snapshot_generation", "entity_changes"):
            cur.execute(f"DELETE FROM {tbl} WHERE entity_id IN ({ph})", removed)
        cur.execute(f"DELETE FROM reports WHERE target_type = 'entity' AND target_id IN ({ph})", removed)
        cur.execute(f"DELETE FROM entities WHERE id IN ({ph})", removed)

    cur.execute("INSERT INTO entities_fts(entities_fts) VALUES('rebuild')")
    conn.commit()
    conn.execute("VACUUM")


def _upsert_pg_cti(cur, eid: str, etype: str, det: dict[str, Any]) -> None:
    import psycopg2.extras  # type: ignore

    table = KIND_TABLE.get(KIND_OF_TYPE.get(etype, "") or "")
    if not table or not det:
        return
    cols = list(det.keys())
    vals = [psycopg2.extras.Json(v) if c in JSONB_COLUMNS else v for c, v in det.items()]
    collist = ", ".join(cols)
    ph = ", ".join(["%s"] * len(cols))
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols)
    cur.execute(
        f"INSERT INTO {table} (entity_id, {collist}) VALUES (%s, {ph}) "
        f"ON CONFLICT (entity_id) DO UPDATE SET {updates}",
        [eid, *vals],
    )


def _apply_entity_updates_postgres(cur, plan: dict[str, Any]) -> None:
    import psycopg2.extras  # type: ignore

    update_cols = ("placeId", *UNIVERSAL)
    for eid, up in plan["entity_updates"].items():
        cols: list[str] = []
        vals: list[Any] = []
        for col in update_cols:
            if col in up:
                cols.append(f'"{col}" = %s')
                vals.append(up[col])
        if "attributes" in up:
            cols.append("attributes = %s")
            vals.append(psycopg2.extras.Json(up["attributes"]))
        if cols:
            vals.append(eid)
            cur.execute(f"UPDATE entities SET {', '.join(cols)} WHERE id = %s", vals)
        if "det_upsert" in up:
            _upsert_pg_cti(cur, eid, plan["entities_types"][eid], up["det_upsert"])


def _remap_pg_references(cur, merge_pairs: list[tuple[str, str]]) -> None:
    for src, dst in merge_pairs:
        cur.execute("UPDATE posts SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute("UPDATE correction_items SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute("UPDATE follows SET target_id = %s WHERE target_type = 'entity' AND target_id = %s", (dst, src))
        cur.execute("UPDATE featured_entities SET entity_id = %s WHERE entity_id = %s", (dst, src))
        for tbl in ("user_visits", "saved_entities", "event_rsvp"):
            cur.execute(
                f"DELETE FROM {tbl} a WHERE entity_id = %s "
                f"AND EXISTS (SELECT 1 FROM {tbl} b WHERE b.user_id = a.user_id AND b.entity_id = %s)",
                (src, dst),
            )
            cur.execute(f"UPDATE {tbl} SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute(
            "DELETE FROM entity_ratings WHERE entity_id = %s "
            "AND EXISTS (SELECT 1 FROM entity_ratings b WHERE b.entity_id = %s)",
            (src, dst),
        )
        cur.execute("UPDATE entity_ratings SET entity_id = %s WHERE entity_id = %s", (dst, src))


def _apply_postgres(conn, plan: dict[str, Any]) -> None:
    import psycopg2.extras  # type: ignore

    cur = conn.cursor()
    removed = sorted(set(plan["deletes_by_phase"]) | set(plan["merge_map"]))
    for it_id in plan["deleted_itineraries"]:
        cur.execute("DELETE FROM itineraries WHERE id = %s", (it_id,))
    for item in plan["itinerary_updates"]:
        cur.execute("UPDATE itineraries SET stops = %s WHERE id = %s", (psycopg2.extras.Json(item["stops"]), item["id"]))
    _apply_entity_updates_postgres(cur, plan)

    cur.execute("DELETE FROM relationships")
    if plan["remapped_rels"]:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO relationships (from_id, to_id, type) VALUES %s ON CONFLICT DO NOTHING",
            plan["remapped_rels"],
            page_size=500,
        )

    _remap_pg_references(cur, [(s, info["target"]) for s, info in plan["merge_map"].items()])
    if removed:
        for tbl in (
            "user_visits", "saved_entities", "event_rsvp", "featured_entities",
            "user_personalization_events", "correction_items", "entity_claims",
            "entity_snapshot_generation", "entity_changes",
        ):
            cur.execute(f"DELETE FROM {tbl} WHERE entity_id = ANY(%s)", (removed,))
        cur.execute("DELETE FROM follows WHERE target_type = 'entity' AND target_id = ANY(%s)", (removed,))
        cur.execute("DELETE FROM reports WHERE target_type = 'entity' AND target_id = ANY(%s)", (removed,))
        cur.execute("UPDATE posts SET entity_id = NULL WHERE entity_id = ANY(%s)", (removed,))
        cur.execute("DELETE FROM entities WHERE id = ANY(%s)", (removed,))
    conn.commit()


def _open_connection(args: argparse.Namespace) -> tuple[Any, Any, bool]:
    if args.sqlite is not None:
        conn = sqlite3.connect(str(args.sqlite))
        conn.row_factory = sqlite3.Row
        return conn, conn.cursor(), False
    _load_dotenv_into_env(REPO_ROOT / ".env")
    _load_dotenv_into_env(Path("/opt/vinhlong360/.env"))
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn.startswith(("postgres://", "postgresql://")):
        raise SystemExit("DATABASE_URL not configured for --postgres-env")
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore

    conn = psycopg2.connect(dsn)
    return conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor), True


def _write_outputs(args: argparse.Namespace, plan: dict[str, Any], is_pg: bool, apply_changes: bool) -> None:
    if args.report_out is not None:
        payload = {
            "mode": "apply" if apply_changes else "dry-run",
            "backend": "postgres" if is_pg else "sqlite",
            "counts": plan["counts"],
            "phase_breakdown": plan["phase_breakdown"],
            "surviving_by_type": plan["surviving_by_type"],
            "exempted_for_ward_coverage": plan["exempted_for_ward_coverage"],
            "place_id_transfers": plan["place_id_transfers"],
            "utility_updates": plan["utility_updates"],
            "deleted_itineraries": plan["deleted_itineraries"],
            "itinerary_updates_count": len(plan["itinerary_updates"]),
            "deletes_by_phase": plan["deletes_by_phase"],
            "merge_map": plan["merge_map"],
            "redirects": plan["redirects"],
        }
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.redirects_out is not None and apply_changes:
        args.redirects_out.parent.mkdir(parents=True, exist_ok=True)
        args.redirects_out.write_text(json.dumps(plan["redirects"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _print_summary(plan: dict[str, Any], is_pg: bool, apply_changes: bool) -> None:
    c = plan["counts"]
    print(
        f"[{'APPLIED' if apply_changes else 'DRY-RUN'}][{'postgres' if is_pg else 'sqlite'}] "
        f"entities: {c['before_entities']} -> {c['after_entities']} "
        f"(-{c['total_removed']}: hard_del={c['hard_deleted']}, merged={c['merged_with_redirect']}, "
        f"redirects={c['redirects_total']}, curated_synced={c['curated_entities_synced']}) | "
        f"rels: {c['before_relationships']} -> {c['after_relationships']} | "
        f"itineraries: {c['before_itineraries']} -> {c['after_itineraries']} | "
        f"covered_wards: {c['covered_wards_before']} -> {c['covered_wards_after']}"
    )
    print("Phase breakdown:", json.dumps(plan["phase_breakdown"], ensure_ascii=False))
    if plan["exempted_for_ward_coverage"]:
        print("Exempted:", json.dumps(plan["exempted_for_ward_coverage"], ensure_ascii=False))
    if plan["place_id_transfers"]:
        print("PlaceId transfers:", json.dumps(plan["place_id_transfers"], ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src_group = ap.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--sqlite", type=Path, help="Path to local SQLite DB")
    src_group.add_argument("--postgres-env", action="store_true", help="Connect using DATABASE_URL env var")
    mode_group = ap.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true", help="Simulate and emit report only (default)")
    mode_group.add_argument("--apply", action="store_true", help="Execute mutations inside a transaction")
    ap.add_argument("--sync-curated-from-json", type=Path, help="Sync curated non-empty attributes from JSON")
    ap.add_argument("--report-out", type=Path, help="Optional JSON report path")
    ap.add_argument("--redirects-out", type=Path, help="Optional canonical 301 redirect JSON map path")
    args = ap.parse_args(argv)
    apply_changes = bool(args.apply)

    conn, cur, is_pg = _open_connection(args)
    try:
        entities, rels, itineraries = _load_snapshot(cur, is_pg=is_pg)
        plan = _build_plan(entities, rels, itineraries, _load_curated_map(args.sync_curated_from_json))
        if apply_changes:
            (_apply_postgres if is_pg else _apply_sqlite)(conn, plan)
        else:
            conn.rollback()
        _write_outputs(args, plan, is_pg=is_pg, apply_changes=apply_changes)
        _print_summary(plan, is_pg=is_pg, apply_changes=apply_changes)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

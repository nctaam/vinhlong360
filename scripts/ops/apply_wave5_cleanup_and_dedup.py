#!/usr/bin/env python3
"""Wave 5 deterministic entity cleanup, dedup merges, type fixes & title polish.

Supports both local SQLite (`--sqlite`) and VPS PostgreSQL (`--postgres-env`).
Updates entities, universal columns, CTI detail tables via agent/entity_details,
relationships, itineraries, and 301 redirect map inside one transaction.
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

# Wave 1A + 1B: Geographic hallucinations (5) & legacy admin mis-entities (3).
# Preserves external gateway `ben-xe-mien-tay-hcm` (`placeId='gateway-hcm'`).
WAVE1_HARD_DELETES: tuple[str, ...] = (
    "nha-co-huynh-thuy-le",
    "mam-tom-cha-vinh-long",
    "ca-phe-nha-co-vinh-long-khu-nha-co-huynh-thuy-le-vinh-long",
    "ca-phe-song-tien-ben-ninh-kieu-vinh-long-vinh-long",
    "shop-luu-niem-ben-ninh-kieu-gian-hang-vinh-long-vinh-long",
    "xa-chanh-an",
    "xa-tuong-loc",
    "xa-kim-hoa-diem-du-lich-sinh-thai-song-nuoc",
)

# Wave 2A: Commercial chains, civic parks/infra, bus stations, national holidays.
WAVE2_HARD_DELETES: tuple[str, ...] = (
    "ca-phe-highland-vincom-vinh-long-vinh-long",
    "trung-tam-thuong-mai-vincom-vinh-long",
    "cong-vien-phuong-9",
    "cong-vien-an-hoi",
    "cong-vien-my-hoa",
    "cong-vien-giong-trom",
    "cong-vien-29",
    "cong-vien-dan-chu",
    "khu-trung-tam-hanh-chinh-van-hoa-phuong-1-tp-vinh-long",
    "cong-an-tinh-vinh-long-vinh-long",
    "cap-cuu-115-ben-tre-ben-tre",
    "benh-vien-da-khoa-nguyen-dinh-chieu-ben-tre",
    "benh-vien-da-khoa-minh-duc-ben-tre-ben-tre",
    "benh-vien-da-khoa-xuyen-a-vinh-long-vinh-long",
    "benh-vien-da-khoa-tinh-vinh-long-vinh-long",
    "tram-xe-buyt-noi-tinh-ben-xe-ben-tre-diem-dau-cac-tuyen-buyt-ben-tre",
    "diem-xe-buyt-phuong-trang-vinh-long-can-tho-tuyen-lien-tinh-vinh-long",
    "ben-xe-ben-tre-trung-tam-ben-tre",
    "ben-xe-tra-vinh-ben-xe-trung-tam-tra-vinh",
    "ben-xe-vinh-long-trung-tam-vinh-long",
    "ben-xe-tra-on-tich-thien-vinh-long",
    "ben-xe-cho-lach-ben-tre",
    "ben-xe-duyen-hai-tx-duyen-hai-tra-vinh",
    "ben-xe-cau-ke-tra-vinh",
    "ben-xe-cau-ngang-tra-vinh",
    "ben-xe-tieu-can-tra-vinh",
    "ben-xe-vung-liem-vinh-long",
    "ben-xe-ba-tri-ben-tre",
    "ben-xe-mo-cay-nam-ben-tre",
    "ben-xe-tra-cu-tra-vinh",
    "tet-doan-ngo",
    "le-vu-lan",
    "le-gio-to-hung-vuong",
    "le-hoi-long-den",
    "le-cung-mieu",
    "festival-dua-ben-tre",
)

WAVE5_HARD_DELETES: tuple[str, ...] = WAVE1_HARD_DELETES + WAVE2_HARD_DELETES
STALE_MERGER_PLACES: tuple[str, ...] = ("xa-cai-ngang", "xa-trung-thanh")

# Canonical merges (dst -> [src...], 60 merges across lodging/heritage/nature/food/events).
WAVE5_MERGES_BY_DST: dict[str, list[str]] = {
    "khu-du-lich-vinh-sang": ["resort-vinh-sang", "vinh-sang-resort", "khach-san-vinh-sang"],
    "saigon-vinh-long-hotel": ["can-tho-hotel-transit"],
    "khach-san-cuu-long": ["cuu-long-hotel"],
    "khach-san-van-trang": ["van-trang-hotel"],
    "khach-san-phuoc-thanh-iv": ["phuoc-thanh-iv-tourist-area"],
    "du-lich-sinh-thai-nam-son": ["khu-du-lich-sinh-thai-nam-son"],
    "khu-du-lich-sinh-thai-deja-vu-huynh-kha": ["khu-du-lich-sinh-thai-huynh-kha"],
    "nha-co-cau-ke": ["ks-nha-co-cau-ke"],
    "khu-du-lich-sinh-thai-sala": ["khu-du-lich-sala"],
    "khu-mo-than-nhan-thoai-ngoc-hau": [
        "khu-mo-than-nhan-danh-than-thoai-ngoc-hau",
        "khu-di-tich-mo-than-mau-va-duong-mau-thoai-ngoc-hau",
    ],
    "di-tich-duong-ho-chi-minh-tren-bien-ben-thanh-phong": [
        "di-tich-duong-ho-chi-minh-tren-bien-thanh-phu",
        "duong-ho-chi-minh-tren-bien-ben-xuat-phat-thanh-phong",
    ],
    "khu-tuong-niem-co-chu-tich-hdbt-pham-hung": ["khu-luu-niem-pham-hung"],
    "khu-luu-niem-nguyen-thi-dinh": ["khu-luu-niem-nu-tuong-nguyen-thi-dinh"],
    "khu-di-tich-can-cu-tinh-uy-tra-vinh": ["khu-can-cu-tinh-uy-tra-vinh"],
    "khu-di-tich-cach-mang-cai-ngang": ["can-cu-cach-mang-cai-ngang-vinh-long"],
    "di-tich-can-cu-khu-uy-sai-gon-gia-dinh": ["can-cu-khu-uy-sai-gon-gia-dinh-tai-tan-phu-tay"],
    "khu-di-tich-mo-va-den-tho-phan-thanh-gian": ["lang-mo-va-dinh-phan-thanh-gian"],
    "den-tho-lanh-binh-nguyen-ngoc-thang": ["den-tho-tuong-quan-nguyen-ngoc-thang"],
    "chua-hoi-tong-ben-tre": ["chua-hoi-ton-co-tu"],
    "tuong-dai-chien-thang-mau-than-vinh-long": ["cong-vien-tuong-dai-chien-thang-mau-than"],
    "khu-bao-ton-thien-nhien-thanh-phu": [
        "khu-bao-ve-canh-quan-thanh-phu-ben-tre",
        "khu-bao-ve-canh-quan-rung-ngap-man-thanh-phu",
    ],
    "bien-ba-dong": ["bai-bien-ba-dong"],
    "con-tan-quy-cu-lao-tan-quy": ["cu-lao-tan-quy-cau-ke"],
    "rung-ngap-man-phong-ho-binh-dai-ben-tre": ["rung-ngap-man-binh-dai"],
    "dong-muoi-bao-thanh": ["canh-dong-muoi-bao-thanh"],
    "lang-nghe-tau-hu-ky-my-hoa": ["lang-tau-hu-ky-my-hoa"],
    "lang-nghe-banh-trang-nem-cu-lao-may": ["banh-trang-cu-lao-may-lang-nghe-banh-trang"],
    "lang-nghe-dan-non-la-tt-long-ho": ["lang-nghe-cham-non-la-long-ho"],
    "lang-nghe-tieu-thu-cong-nghiep-duc-my": ["lang-dan-lat-duc-my-cang-long"],
    "lang-nghe-tieu-thu-cong-nghiep-tre-ham-giang-co-so-tri-canh": [
        "lang-nghe-tieu-thu-cong-nghiep-ham-giang-tre-truc",
    ],
    "gao-sach-tom-lua-thanh-phu-ocop": ["gao-sach-lua-tom-thanh-phu"],
    "bun-nuoc-leo-huong-tra-tra-vinh": ["bun-nuoc-leo-huong-tra---pham-ngu-lao"],
    "hu-tieu-xi-quach-a-linh-tra-vinh": ["hu-tieu-xi-quach-a-linh---le-loi"],
    "bun-nuoc-leo-hem-ly-thuong-kiet": ["bun-nuoc-leo---ly-thuong-kiet"],
    "nha-hang-noi-ben-tre": ["nha-hang-noi-ttc-ben-tre-ben-tre"],
    "nghe-don-ca-tai-tu": [
        "don-ca-tai-tu-nam-bo",
        "don-ca-tai-tu-nam-bo-tai-vinh-long",
        "don-ca-tai-tu-o-vinh-long",
        "cau-lac-bo-don-ca-tai-tu-huyen-vung-liem",
        "cau-lac-bo-don-ca-tai-tu-huyen-long-ho",
        "cau-lac-bo-don-ca-tai-tu-huyen-tam-binh",
        "cau-lac-bo-don-ca-tai-tu-huyen-tra-on",
        "cau-lac-bo-don-ca-tai-tu-huyen-mang-thit",
        "cau-lac-bo-don-ca-tai-tu-thi-xa-binh-minh",
        "cau-lac-bo-don-ca-tai-tu-tinh-vinh-long",
        "cau-lac-bo-don-ca-tai-tu-truong-xay-dung-mien-tay",
        "clb-don-ca-tai-tu-tt-van-hoa-thong-tin-vinh-long",
        "clb-don-ca-tai-tu-du-lich-cuu-long",
        "nhom-don-ca-tai-tu-bong-hong-vang",
        "nhom-don-ca-tai-tu-truong-an",
    ],
    "bun-nuoc-leo-tra-vinh": [
        "bun-nuoc-leo-tieu-can",
        "bun-nuoc-leo-tra-cu",
        "bun-nuoc-leo-cang-long",
    ],
    "tet-nguyen-dan-mien-tay": ["cho-hoa-tet"],
    "le-hoi-ky-yen-dinh-phu-le": ["le-hoi-ky-yen"],
}

# Wave 2B: Mistyped entities (15).
WAVE5_TYPE_FIXES: dict[str, str] = {
    "hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre": "restaurant",
    "lang-nghe-tau-hu-ky-my-hoa": "craft_village",
    "banh-tet-tra-cuon-co-huong": "product",
    "cho-cau-ke": "attraction",
    "cho-dai-an": "attraction",
    "kem-xoi-dua---khu-sao-mai": "restaurant",
    "bun-mam-co-ba": "restaurant",
    "ba-ba---banh-flan": "restaurant",
    "yogurt-dua---ba-muoi-thang-tu": "restaurant",
    "dang-ga---cac-mon-ga-ta": "restaurant",
    "xoi-man-69---hung-dao-vuong": "restaurant",
    "co-diem---banh-canh-vit-bot-xat": "restaurant",
    "banh-cuon-nong---tran-quoc-tuan": "restaurant",
    "bun-bo-co-tam-cho-ben-tre-ben-tre": "restaurant",
    "nem-nuong-thanh-binh-ben-tre": "restaurant",
}

# Ensure switched craft_village passes schema required field & CTI int coercion cleanly.
WAVE5_ATTR_PATCHES: dict[str, dict[str, Any]] = {
    "lang-nghe-tau-hu-ky-my-hoa": {
        "households": 40,
        "specialty": "Tàu hủ ky Mỹ Hòa",
    },
}

# Wave 2C: Standardize 13 legacy pre-merger admin titles + 2 typography/hedging titles.
WAVE5_NAME_FIXES: dict[str, str] = {
    "cua-hang-ocop-tinh-ben-tre-trung-tam-xuc-tien-dau-tu-ho-tro-doanh-nghiep-ben-tre": (
        "Cửa hàng OCOP Bến Tre (Trung tâm Xúc tiến Đầu tư & Hỗ trợ Doanh nghiệp)"
    ),
    "lang-keo-dua-phuong-7-ben-tre": "Làng Kẹo Dừa Bến Tre",
    "chao-long-ba-nam-cho-phuong-4-ben-tre": "Cháo lòng Bà Năm (Chợ Phú Khương)",
    "nha-hang-thien-huong-tp-tra-vinh-tra-vinh": "Nhà hàng Thiên Hương (Trà Vinh)",
    "mieu-ba-chua-xu-my-hoa-ben-tre": "Miếu Bà Chúa Xứ Mỹ Hóa",
    "che-khuc-bach-khu-dem-vinh-long-cho-dem-phuong-1-vinh-long": "Chè Khúc Bạch – Khu ẩm thực đêm Long Châu",
    "ca-phe-cay-bang-phuong-4-tra-vinh": "Cà phê Cây Bàng (Long Đức)",
    "quan-hu-tieu-nguoi-hoa-khu-phuong-1-tra-vinh": "Quán hủ tiếu người Hoa (Trà Vinh)",
    "chua-quan-am-phuong-8": "Chùa Quan Âm Tân Hạnh",
    "ben-tau-du-lich-tp-ben-tre-ben-tre": "Bến tàu Du lịch Bến Tre",
    "hoi-thi-ghe-ngo-mo-rong-tinh-tra-vinh-dua-ghe-ngo-truyen-thong-tra-vinh": (
        "Hội thi Đua Ghe Ngo truyền thống Trà Vinh"
    ),
    "giai-dua-ghe-ngo-truyen-thong-tinh-ben-tre-ben-tre": "Giải Đua Ghe Ngo truyền thống Bến Tre",
    "bao-tang-tong-hop-tinh-tra-vinh": "Bảo tàng Tổng hợp Trà Vinh",
    "khu-luu-niem-tran-dai-nghia": "Khu lưu niệm Trần Đại Nghĩa",
    "lang-hoa-kieng-cai-mon-cho-lach": "Làng Hoa Kiểng Cái Mơn – Chợ Lách",
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
        'id, type, name, "placeId", address, phone, website, hours, '
        'price_range, sub_category, best_time, highlight, attributes'
        if is_pg
        else "id, type, name, placeId, address, phone, website, hours, "
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
        for dst, srcs in WAVE5_MERGES_BY_DST.items()
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


def _apply_type_and_name_fixes(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], removed: set[str]
) -> None:
    for eid, new_type in WAVE5_TYPE_FIXES.items():
        if eid in entities and eid not in removed and entities[eid]["type"] != new_type:
            entities[eid]["type"] = new_type
            updates.setdefault(eid, {}).update({"type": new_type, "sync_cti": True})
    for eid, patch in WAVE5_ATTR_PATCHES.items():
        if eid in entities and eid not in removed:
            entities[eid]["attrs"].update(patch)
            updates.setdefault(eid, {}).update({"save_attrs": True, "sync_cti": True})
    for eid, new_name in WAVE5_NAME_FIXES.items():
        if eid in entities and eid not in removed and entities[eid]["name"] != new_name:
            updates.setdefault(eid, {})["name"] = new_name


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
    _apply_type_and_name_fixes(entities, updates, removed)
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


def _remap_stop(stop: Any, merge_map: dict[str, str], surviving_ids: set[str], it_id: str) -> tuple[str, Any]:
    sid = stop.get("id", "") if isinstance(stop, dict) else stop
    mapped = merge_map.get(sid, sid)
    assert mapped in surviving_ids, f"Itinerary {it_id} broken stop {mapped}"
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
            mapped, cur_stop = _remap_stop(stop, merge_map, surviving_ids, it["id"])
            if mapped != last_sid:
                last_sid = mapped
                new_stops.append(cur_stop)
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
    stale_places = {eid for eid in STALE_MERGER_PLACES if eid in entities and not ward_members.get(eid)}
    hard_set = {eid for eid in WAVE5_HARD_DELETES if eid in entities and eid not in places} | stale_places
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
    col_map: dict[str, Any] = {c: up[c] for c in ("type", "name", "placeId", "phone", "website", "hours") if c in up}
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
        if args.report_out is not None:
            out = {
                "mode": "apply" if apply_changes else "dry-run",
                "backend": "postgres" if is_pg else "sqlite",
                "counts": plan["counts"],
                "hard_deletes": plan["hard_deletes"],
                "merge_map": plan["merge_map"],
                "type_fixes": {k: v for k, v in WAVE5_TYPE_FIXES.items() if k in plan["entity_updates"]},
                "name_fixes": {k: v for k, v in WAVE5_NAME_FIXES.items() if k in plan["entity_updates"]},
            }
            args.report_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[{'APPLIED' if apply_changes else 'DRY-RUN'}][{'postgres' if is_pg else 'sqlite'}] {json.dumps(plan['counts'], ensure_ascii=False)}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

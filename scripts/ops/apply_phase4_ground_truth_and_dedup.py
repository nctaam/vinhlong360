#!/usr/bin/env python3
"""Phase 4 atomic data remediation: Wave-2 dedup, Phase-B GT patches, 2-tier addresses & itinerary repair.

Supports both local SQLite (`--sqlite`) and VPS PostgreSQL (`--postgres-env`).
All functions stay small and modular (cyclomatic complexity <= 10 for R20.8).
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

try:
    from entity_details import (
        DETAIL_TABLES,
        JSONB_COLUMNS,
        KIND_TABLE,
        UNIVERSAL,
        norm_value,
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
    norm_value = lambda v: v.strip() if isinstance(v, str) else v  # noqa: E731

DEFAULT_GT_PATH = REPO_ROOT / "outputs" / "ground-truth-9router-verification-2026-10-21.json"
DEFAULT_LEDGER_PATH = REPO_ROOT / "outputs" / "data_remediation_ledger.json"

WAVE2_MERGES: dict[str, list[str]] = {
    "bao-tang-ben-tre": ["bao-tang-tinh-ben-tre"],
    "bao-tang-vinh-long": ["bao-tang-tinh-vinh-long"],
    "khu-du-lich-sinh-thai-sala": ["du-lich-sinh-thai-sala"],
    "khu-di-tich-cach-mang-cai-ngang": ["di-tich-lich-su-cach-mang-cai-ngang"],
    "chua-tuyen-linh": ["chua-tuyen-linh-mo-cay-nam"],
    "cu-lao-dai": ["cu-lao-dai-vung-liem"],
    "cu-lao-may": ["cu-lao-may-tra-on"],
    "con-thanh-long": ["khu-du-lich-sinh-thai-con-thanh-long", "con-thanh-long-mo-cay-nam"],
    "khu-du-lich-truong-huy": ["khu-du-lich-truong-huy-long-ho"],
    "san-chim-vam-ho": ["san-chim-vam-ho-ba-tri"],
    "bun-mam-vinh-long": ["bun-mam-mien-tay"],
    "ruou-phu-le": ["ruou-phu-le-ba-tri"],
    "buoi-da-xanh": ["buoi-da-xanh-cho-lach"],
    "khu-luu-niem-thu-tuong-vo-van-kiet": ["khu-luu-niem-thu-tuong-chinh-phu-vo-van-kiet"],
    "mo-va-khu-luu-niem-vo-truong-toan": ["mo-va-khu-luu-niem-nha-giao-vo-truong-toan"],
    "banh-xeo-oc-gao-phu-da": ["banh-xeo-oc-gao-con-phu-da"],
    "tuong-quan-nguyen-van-ton": ["nguyen-van-ton-thach-duong"],
    "cong-vien-29": ["cong-vien-29-tan-quoi"],
    "lang-ong-tien-quan-thong-che-dieu-bat": ["lang-ong-lang-ong-che-nguyen-van-ton"],
}

EXPLICIT_CONTENT_FIXES: dict[str, dict[str, str]] = {
    "khu-du-lich-sinh-thai-sala": {
        "summary": (
            "Khu du lịch sinh thái rộng 20 ha tại xã Mỹ Thạnh Trung, tổng đầu tư hơn 40 tỷ đồng, "
            "cách phường Long Châu khoảng 25 km, nổi bật với hai phân khu Sala Farm và Sala Amazing."
        ),
    },
    "com-chay-au-lac-vinh-long": {
        "summary": (
            "Quán cơm chay Âu Lạc bình dân trên đường Trần Văn Ơn, phường Long Châu, "
            "phục vụ thực đơn chay Nam Bộ thanh đạm vào buổi sáng và trưa."
        ),
    },
    "kenh-tra-on-vinh-long": {
        "summary": (
            "Kênh Trà Ôn dài 35 km nối sông Hậu với vùng nội địa Trà Ôn, nơi hình thành chợ nổi Trà Ôn "
            "họp sớm bên sông lúc bình minh."
        ),
    },
}

PLACEHOLDER_ITIN_REPLACEMENTS: dict[str, list[dict[str, str]]] = {
    "tour-p06": [
        {"id": "cho-hoa-tet", "time": "08:00", "note": "Tham quan chợ hoa Tết rực rỡ sắc xuân bên dòng sông Cổ Chiên"},
        {"id": "lang-hoa-kieng-cai-mon-cho-lach", "time": "09:30", "note": "Khám phá làng hoa kiểng Cái Mơn – Chợ Lách mùa hoa nở rộ"},
        {"id": "lang-ong-tien-quan-thong-che-dieu-bat", "time": "13:00", "note": "Viếng Lăng Ông Tiền quân Thống chế Điều bát đầu xuân"},
        {"id": "cu-lao-an-binh", "time": "15:00", "note": "Dạo vườn cây ăn trái và trải nghiệm sông nước cù lao An Bình"},
    ],
    "tour-p09": [
        {"id": "lo-gach-mang-thit", "time": "06:30", "note": "Săn ảnh bình minh và ánh nắng xiên trên vòm lò gạch gốm đỏ Mang Thít"},
        {"id": "ao-ba-om", "time": "10:30", "note": "Chụp ảnh hàng cổ thụ trăm năm và mặt hồ Ao Bà Om thanh tĩnh"},
        {"id": "bien-ba-dong", "time": "16:00", "note": "Ghi lại khoảnh khắc biển Ba Động và cánh đồng điện gió lúc chiều tà"},
    ],
}

PLACEHOLDER_STOP_REMAP: dict[str, dict[str, str]] = {
    "placeholder-tour-p10-2": {
        "id": "co-so-keo-dua-thanh-long-ben-tre",
        "time": "10:00",
        "note": "Workshop trải nghiệm làm kẹo dừa thủ công cùng nghệ nhân địa phương",
    },
    "placeholder-tour-p10-3": {
        "id": "nha-hang-noi-ben-tre",
        "time": "12:00",
        "note": "Thưởng thức bữa trưa ẩm thực bản địa trên nhà hàng nổi sông Bến Tre",
    },
}


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


def _load_dotenv(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
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


def _load_snapshot(cur, is_pg: bool) -> tuple[dict[str, dict[str, Any]], list[tuple[str, str, str]], list[dict[str, Any]]]:
    cols = (
        'id, type, name, summary, "placeId", address, phone, website, hours, '
        'price_range, sub_category, best_time, highlight, attributes'
        if is_pg
        else "id, type, name, summary, placeId, address, phone, website, hours, price_range, sub_category, best_time, highlight, attributes"
    )
    cur.execute(f"SELECT {cols} FROM entities")
    entities = {}
    for row in cur.fetchall():
        d = dict(row)
        d["attrs"] = _parse_attrs(d.get("attributes"))
        entities[d["id"]] = d
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
    covered = {w for w, s in members.items() if s}
    return places, members, covered


def _compute_wave2_merges(
    entities: dict[str, dict[str, Any]],
    ward_members: dict[str, set[str]],
    covered_wards: set[str],
) -> tuple[dict[str, str], dict[str, str], list[dict[str, str]]]:
    all_ids = set(entities)
    sim = {w: set(m) for w, m in ward_members.items()}
    merge_map: dict[str, str] = {}
    transfers: dict[str, str] = {}
    exempted: list[dict[str, str]] = []

    raw_pairs = [
        (src, dst)
        for dst, srcs in WAVE2_MERGES.items()
        if dst in all_ids
        for src in srcs
        if src in all_ids and src != dst and entities[src]["type"] != "place"
    ]
    all_srcs = {s for s, _ in raw_pairs}
    for src, dst in raw_pairs:
        sw, dw = entities[src].get("placeId"), transfers.get(dst, entities[dst].get("placeId"))
        if sw in covered_wards and not (sim[sw] - all_srcs):
            if dw in covered_wards and len(sim[dw] - all_srcs - {dst}) == 0:
                exempted.append({"id": src, "ward": sw, "reason": "wave2_merge_would_create_white_zone"})
                continue
            sim.get(dw, set()).discard(dst)
            sim.setdefault(sw, set()).add(dst)
            transfers[dst] = sw
        merge_map[src] = dst
        sim.get(sw, set()).discard(src)
    return merge_map, transfers, exempted


def _set_entity_field(row: dict[str, Any], up: dict[str, Any], field: str, val: Any, is_attr: bool = True) -> None:
    cleaned = val.strip() if isinstance(val, str) else val
    if not _non_empty(cleaned):
        return
    if row.get(field) != cleaned:
        row[field] = cleaned
        up[field] = cleaned
    if is_attr and row["attrs"].get(field) != cleaned:
        row["attrs"][field] = cleaned
        up["_attrs_dirty"] = True
    if field == "hours" and "opening_hours" in row["attrs"]:
        row["attrs"].pop("opening_hours", None)
        up["_attrs_dirty"] = True


def _apply_ledger_addresses(entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], ledger_path: Path) -> int:
    if not ledger_path.exists():
        return 0
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    count = 0
    for rem in ledger.get("remediations", []):
        if rem.get("error_code") not in ("ERR_OLD_ADMIN_DISTRICT", "ERR_OLD_PROVINCE_REF"):
            continue
        eid = rem.get("entity_id")
        val = rem.get("proposed_value")
        if eid in entities and _non_empty(val):
            up = updates.setdefault(eid, {})
            _set_entity_field(entities[eid], up, "address", val, is_attr=True)
            count += 1
    return count


def _ward_occupancy(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], places: set[str]
) -> tuple[dict[str, set[str]], dict[str, str]]:
    sim_wards: dict[str, set[str]] = defaultdict(set)
    cur_pid: dict[str, str] = {}
    for eid, r in entities.items():
        if r["type"] == "place":
            continue
        pid = updates.get(eid, {}).get("placeId", r.get("placeId"))
        if pid:
            cur_pid[eid] = pid
        if pid in places:
            sim_wards[pid].add(eid)
    return sim_wards, cur_pid


def _try_move_place(
    eid: str,
    target_pid: str,
    entities: dict[str, dict[str, Any]],
    updates: dict[str, dict[str, Any]],
    sim_wards: dict[str, set[str]],
    cur_pid: dict[str, str],
    covered_wards: set[str],
    reason: str,
) -> tuple[bool, dict[str, str] | None]:
    old_pid = cur_pid.get(eid)
    if old_pid == target_pid:
        return False, None
    if old_pid in covered_wards and len(sim_wards[old_pid]) <= 1:
        return False, {"id": eid, "ward": old_pid, "target": target_pid, "reason": reason}
    if old_pid:
        sim_wards[old_pid].discard(eid)
    sim_wards[target_pid].add(eid)
    cur_pid[eid] = target_pid
    _set_entity_field(entities[eid], updates.setdefault(eid, {}), "placeId", target_pid, is_attr=False)
    return True, None


def _apply_one_dossier(
    eid: str,
    entities: dict[str, dict[str, Any]],
    updates: dict[str, dict[str, Any]],
    truth: dict[str, Any],
    sim_wards: dict[str, set[str]],
    cur_pid: dict[str, str],
    places: set[str],
    covered_wards: set[str],
) -> dict[str, str] | None:
    row = entities[eid]
    up = updates.setdefault(eid, {})
    if _non_empty(truth.get("summary")):
        _set_entity_field(row, up, "summary", truth["summary"], is_attr=False)
    for field in ("address", "phone", "hours"):
        if _non_empty(truth.get(field)):
            _set_entity_field(row, up, field, truth[field], is_attr=True)
    target_pid = truth.get("placeId")
    if not (_non_empty(target_pid) and target_pid in entities):
        return None
    if eid in cur_pid and target_pid in places:
        _, skipped = _try_move_place(
            eid, target_pid, entities, updates, sim_wards, cur_pid, covered_wards, "dossier_would_create_white_zone"
        )
        return skipped
    _set_entity_field(row, up, "placeId", target_pid, is_attr=False)
    return None


def _apply_dossiers_and_self_ids(
    entities: dict[str, dict[str, Any]],
    updates: dict[str, dict[str, Any]],
    merge_map: dict[str, str],
    gt: dict[str, Any],
    places: set[str],
    covered_wards: set[str],
) -> tuple[int, int, list[dict[str, str]]]:
    sim_wards, cur_pid = _ward_occupancy(entities, updates, places)
    d_count = 0
    exempted: list[dict[str, str]] = []
    for item in gt.get("verifiedDossiers", []):
        eid = merge_map.get(item.get("entityId", ""), item.get("entityId", ""))
        if eid in entities:
            skipped = _apply_one_dossier(
                eid, entities, updates, item.get("verifiedGroundTruth") or {}, sim_wards, cur_pid, places, covered_wards
            )
            if skipped:
                exempted.append(skipped)
            d_count += 1

    s_count = 0
    for item in gt.get("placeSelfIdFixes", []):
        eid, vid = item.get("entityId"), item.get("verifiedPlaceId")
        if eid in entities and vid == eid and entities[eid].get("placeId") != vid:
            _set_entity_field(entities[eid], updates.setdefault(eid, {}), "placeId", vid, is_attr=False)
            s_count += 1
    return d_count, s_count, exempted


def _apply_rural_place_fixes(
    entities: dict[str, dict[str, Any]],
    updates: dict[str, dict[str, Any]],
    gt: dict[str, Any],
    places: set[str],
    covered_wards: set[str],
) -> tuple[int, list[dict[str, str]]]:
    sim_wards, cur_pid = _ward_occupancy(entities, updates, places)
    applied = 0
    exempted: list[dict[str, str]] = []
    for corr in gt.get("ruralPlaceIdCorrections", []):
        eid, vpid = corr.get("entityId"), corr.get("verifiedPlaceId")
        if eid not in cur_pid or vpid not in places:
            continue
        moved, skipped = _try_move_place(
            eid, vpid, entities, updates, sim_wards, cur_pid, covered_wards, "rural_fix_would_create_white_zone"
        )
        if skipped:
            exempted.append(skipped)
        elif moved:
            applied += 1
    return applied, exempted


def _apply_types_and_summaries(
    entities: dict[str, dict[str, Any]],
    updates: dict[str, dict[str, Any]],
    gt: dict[str, Any],
) -> tuple[int, int]:
    t_count = 0
    for item in gt.get("mistypedEntities", []):
        eid, vtype = item.get("entityId"), item.get("verifiedType")
        if eid in entities and _non_empty(vtype) and entities[eid]["type"] != vtype:
            up = updates.setdefault(eid, {})
            up["type"] = vtype
            up["_old_type"] = entities[eid]["type"]
            entities[eid]["type"] = vtype
            t_count += 1

    sm_count = 0
    for item in gt.get("truncatedSummaryFixes", []):
        eid, vs = item.get("entityId"), item.get("verifiedSummary")
        if eid in entities and _non_empty(vs):
            _set_entity_field(entities[eid], updates.setdefault(eid, {}), "summary", vs, is_attr=False)
            sm_count += 1

    for eid, patch in EXPLICIT_CONTENT_FIXES.items():
        if eid not in entities:
            continue
        up = updates.setdefault(eid, {})
        if _non_empty(patch.get("summary")):
            _set_entity_field(entities[eid], up, "summary", patch["summary"], is_attr=False)
            sm_count += 1
        if _non_empty(patch.get("address")):
            _set_entity_field(entities[eid], up, "address", patch["address"], is_attr=True)
    return t_count, sm_count


def _inherit_merge_utilities(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], merge_map: dict[str, str]
) -> None:
    for src, dst in sorted(merge_map.items()):
        up = updates.setdefault(dst, {})
        for field in ("phone", "website", "hours"):
            existing = up.get(field, entities[dst].get(field))
            cand = entities[src].get(field)
            if not _non_empty(existing) and _non_empty(cand):
                _set_entity_field(entities[dst], up, field, cand, is_attr=True)


def _rewrite_relationships(
    rels: list[tuple[str, str, str]], merge_map: dict[str, str], surviving_ids: set[str]
) -> list[tuple[str, str, str]]:
    out: set[tuple[str, str, str]] = set()
    for f_id, t_id, rtype in rels:
        nf, nt = merge_map.get(f_id, f_id), merge_map.get(t_id, t_id)
        if nf in surviving_ids and nt in surviving_ids and nf != nt:
            out.add((nf, nt, rtype))
    return sorted(out)


def _map_itinerary_stop(stop: Any, merge_map: dict[str, str]) -> list[Any]:
    if not isinstance(stop, dict):
        return [merge_map.get(stop, stop)]
    sid = stop.get("id", "")
    if sid in PLACEHOLDER_STOP_REMAP:
        return [dict(PLACEHOLDER_STOP_REMAP[sid])]
    mapped = merge_map.get(sid, sid)
    if mapped == sid:
        return [stop]
    updated = dict(stop)
    updated["id"] = mapped
    if isinstance(updated.get("note"), str) and sid in updated["note"]:
        updated["note"] = updated["note"].replace(sid, mapped)
    return [updated]


def _dedup_stops(it_id: str, old_stops: list[Any], merge_map: dict[str, str], surviving_ids: set[str]) -> list[Any]:
    new_stops: list[Any] = []
    last_sid: str | None = None
    for stop in old_stops:
        for item in _map_itinerary_stop(stop, merge_map):
            cur_sid = item.get("id") if isinstance(item, dict) else item
            assert cur_sid in surviving_ids, f"Itinerary {it_id} broken stop {cur_sid}"
            if cur_sid != last_sid:
                last_sid = cur_sid
                new_stops.append(item)
    return new_stops


def _rewrite_itineraries(
    itineraries: list[dict[str, Any]], merge_map: dict[str, str], surviving_ids: set[str]
) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    for it in itineraries:
        if it["id"] in PLACEHOLDER_ITIN_REPLACEMENTS:
            stops = [dict(s) for s in PLACEHOLDER_ITIN_REPLACEMENTS[it["id"]]]
            assert all(s["id"] in surviving_ids for s in stops)
            updates.append({"id": it["id"], "stops": stops})
            continue
        raw = it.get("stops")
        old_stops = json.loads(raw) if isinstance(raw, str) else list(raw or [])
        new_stops = _dedup_stops(it["id"], old_stops, merge_map, surviving_ids)
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


def _sync_update_attrs(entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    final_updates: dict[str, dict[str, Any]] = {}
    for eid, up in updates.items():
        clean = {k: v for k, v in up.items() if k not in ("_attrs_dirty", "_old_type")}
        row = entities[eid]
        if up.get("_attrs_dirty"):
            clean["attributes"] = row["attrs"]
        if "type" in up or up.get("_attrs_dirty"):
            uni, det, _ = split_typed(row["type"], row["attrs"])
            for k, v in uni.items():
                if row.get(k) != v:
                    clean[k] = v
            if det:
                clean["_det_upsert"] = det
            if "_old_type" in up:
                clean["_old_type"] = up["_old_type"]
            clean["_new_type"] = row["type"]
        if clean:
            final_updates[eid] = clean
    return final_updates


def _build_plan(
    entities: dict[str, dict[str, Any]],
    rels: list[tuple[str, str, str]],
    itineraries: list[dict[str, Any]],
    gt: dict[str, Any],
    ledger_path: Path,
    redirects_path: Path | None,
) -> dict[str, Any]:
    places, ward_members, covered_wards = _ward_index(entities)
    merge_map, transfers, merge_exempt = _compute_wave2_merges(entities, ward_members, covered_wards)
    surviving = {eid: row for eid, row in entities.items() if eid not in merge_map}
    surviving_ids = set(surviving)

    updates: dict[str, dict[str, Any]] = {
        dst: {"placeId": pid} for dst, pid in transfers.items() if entities[dst].get("placeId") != pid
    }
    _inherit_merge_utilities(entities, updates, merge_map)
    ledger_count = _apply_ledger_addresses(surviving, updates, ledger_path)
    dossier_count, self_count, dossier_exempt = _apply_dossiers_and_self_ids(
        surviving, updates, merge_map, gt, places, covered_wards
    )
    rural_count, rural_exempt = _apply_rural_place_fixes(surviving, updates, gt, places, covered_wards)
    type_count, summary_count = _apply_types_and_summaries(surviving, updates, gt)
    final_updates = _sync_update_attrs(surviving, updates)

    remapped_rels = _rewrite_relationships(rels, merge_map, surviving_ids)
    itin_updates = _rewrite_itineraries(itineraries, merge_map, surviving_ids)
    redirects = _merge_redirects(redirects_path, merge_map, surviving_ids)

    return {
        "counts": {
            "before_entities": len(entities),
            "after_entities": len(surviving_ids),
            "wave2_merged": len(merge_map),
            "redirects_total": len(redirects),
            "ledger_addresses_applied": ledger_count,
            "dossiers_applied": dossier_count,
            "rural_place_fixes_applied": rural_count,
            "mistyped_entities_fixed": type_count,
            "summaries_fixed": summary_count,
            "place_self_ids_fixed": self_count,
            "itineraries_updated": len(itin_updates),
            "before_relationships": len(rels),
            "after_relationships": len(remapped_rels),
        },
        "merge_map": dict(sorted(merge_map.items())),
        "exempted": merge_exempt + dossier_exempt + rural_exempt,
        "entity_updates": final_updates,
        "remapped_rels": remapped_rels,
        "itinerary_updates": itin_updates,
        "redirects": redirects,
    }


def _apply_sqlite(conn: sqlite3.Connection, plan: dict[str, Any]) -> None:
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    removed = sorted(plan["merge_map"])

    for item in plan["itinerary_updates"]:
        cur.execute("UPDATE itineraries SET stops = ? WHERE id = ?", (json.dumps(item["stops"], ensure_ascii=False), item["id"]))

    update_cols = ("type", "summary", "placeId", *UNIVERSAL)
    for eid, up in plan["entity_updates"].items():
        cols, vals = [], []
        for col in update_cols:
            if col in up:
                cols.append(f'"{col}" = ?')
                vals.append(up[col])
        if "attributes" in up:
            cols.append("attributes = ?")
            vals.append(json.dumps(up["attributes"], ensure_ascii=False))
        if cols:
            cur.execute(f"UPDATE entities SET {', '.join(cols)} WHERE id = ?", [*vals, eid])

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


def _upsert_pg_cti(cur, eid: str, old_type: str | None, new_type: str | None, det: dict[str, Any]) -> None:
    import psycopg2.extras  # type: ignore

    new_tbl = KIND_TABLE.get(KIND_OF_TYPE.get(new_type or "", "") or "")
    old_tbl = KIND_TABLE.get(KIND_OF_TYPE.get(old_type or "", "") or "")
    if old_tbl and old_tbl != new_tbl:
        cur.execute(f"DELETE FROM {old_tbl} WHERE entity_id = %s", (eid,))
    if not new_tbl or not det:
        return
    cols = list(det.keys())
    vals = [psycopg2.extras.Json(v) if c in JSONB_COLUMNS else v for c, v in det.items()]
    collist = ", ".join(cols)
    phs = ", ".join(["%s"] * len(cols))
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols)
    cur.execute(
        f"INSERT INTO {new_tbl} (entity_id, {collist}) VALUES (%s, {phs}) ON CONFLICT (entity_id) DO UPDATE SET {updates}",
        [eid, *vals],
    )


def _remap_pg_refs(cur, merge_map: dict[str, str]) -> None:
    for src, dst in merge_map.items():
        cur.execute("UPDATE posts SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute("UPDATE correction_items SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute("UPDATE follows SET target_id = %s WHERE target_type = 'entity' AND target_id = %s", (dst, src))
        cur.execute("UPDATE featured_entities SET entity_id = %s WHERE entity_id = %s", (dst, src))
        for tbl in ("user_visits", "saved_entities", "event_rsvp"):
            cur.execute(f"DELETE FROM {tbl} a WHERE entity_id = %s AND EXISTS (SELECT 1 FROM {tbl} b WHERE b.user_id = a.user_id AND b.entity_id = %s)", (src, dst))
            cur.execute(f"UPDATE {tbl} SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute("DELETE FROM entity_ratings WHERE entity_id = %s AND EXISTS (SELECT 1 FROM entity_ratings b WHERE b.entity_id = %s)", (src, dst))
        cur.execute("UPDATE entity_ratings SET entity_id = %s WHERE entity_id = %s", (dst, src))


def _apply_pg_entity_updates(cur, entity_updates: dict[str, dict[str, Any]]) -> None:
    import psycopg2.extras  # type: ignore

    update_cols = ("type", "summary", "placeId", *UNIVERSAL)
    for eid, up in entity_updates.items():
        cols = [f'"{col}" = %s' for col in update_cols if col in up]
        vals: list[Any] = [up[col] for col in update_cols if col in up]
        if "attributes" in up:
            cols.append("attributes = %s")
            vals.append(psycopg2.extras.Json(up["attributes"]))
        if cols:
            cur.execute(f"UPDATE entities SET {', '.join(cols)} WHERE id = %s", [*vals, eid])
        if "_det_upsert" in up or "_old_type" in up:
            _upsert_pg_cti(cur, eid, up.get("_old_type"), up.get("_new_type"), up.get("_det_upsert") or {})


def _apply_postgres(conn, plan: dict[str, Any]) -> None:
    import psycopg2.extras  # type: ignore

    cur = conn.cursor()
    for item in plan["itinerary_updates"]:
        cur.execute("UPDATE itineraries SET stops = %s WHERE id = %s", (psycopg2.extras.Json(item["stops"]), item["id"]))
    _apply_pg_entity_updates(cur, plan["entity_updates"])

    cur.execute("DELETE FROM relationships")
    if plan["remapped_rels"]:
        psycopg2.extras.execute_values(cur, "INSERT INTO relationships (from_id, to_id, type) VALUES %s ON CONFLICT DO NOTHING", plan["remapped_rels"], page_size=500)

    _remap_pg_refs(cur, plan["merge_map"])
    removed = sorted(plan["merge_map"])
    if removed:
        for tbl in ("user_visits", "saved_entities", "event_rsvp", "featured_entities", "user_personalization_events", "correction_items", "entity_claims", "entity_snapshot_generation", "entity_changes"):
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
    ap.add_argument("--gt-file", type=Path, default=DEFAULT_GT_PATH)
    ap.add_argument("--ledger-file", type=Path, default=DEFAULT_LEDGER_PATH)
    ap.add_argument("--redirects-file", type=Path)
    ap.add_argument("--report-out", type=Path)
    args = ap.parse_args(argv)
    apply_changes = bool(args.apply)

    conn, cur, is_pg = _open_conn(args)
    try:
        entities, rels, itineraries = _load_snapshot(cur, is_pg=is_pg)
        gt = json.loads(args.gt_file.read_text(encoding="utf-8"))
        plan = _build_plan(entities, rels, itineraries, gt, args.ledger_file, args.redirects_file)
        if apply_changes:
            (_apply_postgres if is_pg else _apply_sqlite)(conn, plan)
        else:
            conn.rollback()
        if args.redirects_file is not None and apply_changes:
            args.redirects_file.write_text(json.dumps(plan["redirects"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.report_out is not None:
            out = {"mode": "apply" if apply_changes else "dry-run", "backend": "postgres" if is_pg else "sqlite", "counts": plan["counts"], "merge_map": plan["merge_map"], "exempted": plan["exempted"]}
            args.report_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[{'APPLIED' if apply_changes else 'DRY-RUN'}][{'postgres' if is_pg else 'sqlite'}] {json.dumps(plan['counts'], ensure_ascii=False)}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

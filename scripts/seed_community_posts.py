"""
seed_community_posts.py — Tạo bài viết cộng đồng từ dữ liệu nghiên cứu GPT 5.5.

Sinh ~25 bài viết editorial chất lượng cao từ 3 nguồn:
  1. 12 tuyến sản phẩm → bài "recommend" (gợi ý lịch trình)
  2. 12 rủi ro bảo tồn → bài "share" (du lịch có trách nhiệm), gom nhóm
  3. 10 phân khúc khách → bài "share" (hướng dẫn theo đối tượng)

Kèm khoảng cách/thời gian di chuyển từ ma trận không gian.

Chạy:
    python scripts/seed_community_posts.py                    # xem trước (dry-run)
    python scripts/seed_community_posts.py --llm              # LLM rewrite nội dung
    python scripts/seed_community_posts.py --apply            # ghi vào Postgres
    python scripts/seed_community_posts.py --export seed.json # xuất JSON
"""

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_env_path = REPO_ROOT / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as _ef:
        for _line in _ef:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

DB_SQLITE = REPO_ROOT / "agent" / "data" / "vinhlong360.db"

CSV_PRODUCTS = REPO_ROOT / "nghien_cuu_12_chieu_ma_tran_san_pham.csv"
CSV_RISKS = REPO_ROOT / "nghien_cuu_12_chieu_rui_ro_bao_ton_moi_truong.csv"
CSV_SEGMENTS = REPO_ROOT / "nghien_cuu_12_chieu_phan_khuc_khach.csv"
CSV_SPATIAL = REPO_ROOT / "nghien_cuu_6_tang_ma_tran_tuyen_khong_gian.csv"

EDITORIAL_USER = {
    "phone": "0900000001",
    "display_name": "VinhLong360",
    "bio": "Đội ngũ biên tập vinhlong360.vn — khám phá Vĩnh Long, Bến Tre, Trà Vinh",
    "role": "admin",
}

SEGMENT_LABELS = {}


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_sqlite_entities() -> list[dict]:
    if not DB_SQLITE.exists():
        return []
    conn = sqlite3.connect(str(DB_SQLITE))
    rows = conn.execute("SELECT id, name, type FROM entities").fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "type": r[2]} for r in rows]


def _normalize(s: str) -> str:
    s = s.lower().strip()
    for prefix in ("khu ", "làng ", "lễ hội ", "điểm du lịch ",
                    "chùa ", "đình ", "cù lao ", "cồn ", "bảo tàng "):
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s


def fuzzy_match(name: str, entities: list[dict], threshold: float = 0.55) -> dict | None:
    raw = name.lower().strip()
    norm = _normalize(name)
    if len(norm) < 3:
        return None
    best_score = 0.0
    best_ent = None
    for ent in entities:
        ent_raw = ent["name"].lower().strip()
        ent_norm = _normalize(ent["name"])
        score_raw = SequenceMatcher(None, raw, ent_raw).ratio()
        score_norm = SequenceMatcher(None, norm, ent_norm).ratio()
        score = max(score_raw, score_norm)
        if len(raw) >= 4 and len(ent_raw) >= 4 and (ent_raw in raw or raw in ent_raw):
            score = max(score, 0.85)
        if len(norm) >= 5 and len(ent_norm) >= 5 and (ent_norm in norm or norm in ent_norm):
            score = max(score, 0.78)
        if score > best_score:
            best_score = score
            best_ent = ent
    return best_ent if best_score >= threshold else None


def build_spatial_map(rows: list[dict]) -> dict[str, dict]:
    result = {}
    for r in rows:
        key = f"{r['from_key']}→{r['to_key']}"
        result[key] = r
        rkey = f"{r['to_key']}→{r['from_key']}"
        if rkey not in result:
            result[rkey] = {**r, "from": r["to"], "to": r["from"]}
    return result


def build_segment_label_map(segments: list[dict]):
    for s in segments:
        SEGMENT_LABELS[s["segment_id"]] = s["segment"]


# ── Post generators ────────────────────────────────────────────────────────────

def gen_route_posts(products: list[dict], spatial: dict, entities: list[dict]) -> list[dict]:
    posts = []
    for p in products:
        pid = p["product_id"]
        name = p["product"]
        itinerary = p["itinerary"]
        geo = p["geography"]
        note = p["note"]
        readiness = p["readiness"]
        seg_ids = [s.strip() for s in p.get("segments", "").split(";") if s.strip()]
        seg_names = [SEGMENT_LABELS.get(s, s) for s in seg_ids]

        content_parts = [f"🗺️ {name}\n"]
        content_parts.append(f"Lộ trình: {itinerary}")
        content_parts.append(f"Vùng: {geo}")

        if readiness == "Market-ready":
            content_parts.append("✅ Tuyến đã sẵn sàng, có thể đi ngay!")
        elif readiness == "Seasonal":
            content_parts.append("📅 Tuyến theo mùa — xem lịch lễ hội trước khi đi")
        elif readiness == "Pilot":
            content_parts.append("🆕 Tuyến đang phát triển — phù hợp người thích khám phá")
        elif readiness == "Strategic":
            content_parts.append("💡 Tuyến chiến lược liên vùng — trải nghiệm đa dạng nhất")

        if seg_names:
            content_parts.append(f"\nPhù hợp: {', '.join(seg_names)}")

        if note:
            content_parts.append(f"\n💬 {note}")

        content = "\n".join(content_parts)

        entity = None
        candidates = []
        for part in itinerary.split(" - "):
            for sub in part.split("/"):
                sub = sub.strip()
                if sub and len(sub) >= 3:
                    candidates.append(sub)
        for cand in candidates:
            entity = fuzzy_match(cand, entities)
            if entity:
                break

        posts.append({
            "content": content,
            "post_type": "recommend",
            "entity_id": entity["id"] if entity else None,
            "entity_name": entity["name"] if entity else None,
            "rating": None,
            "category": "route",
            "source_id": pid,
        })

    return posts


def gen_responsible_posts(risks: list[dict], entities: list[dict]) -> list[dict]:
    groups = {
        "festival": {
            "title": "Tham gia lễ hội có trách nhiệm",
            "risk_ids": ["R01", "R02", "R09"],
            "intro": "Lễ hội ở miền Tây không chỉ để vui — đó là không gian thiêng của cộng đồng. Một vài lưu ý giúp bạn tận hưởng mà không làm mất đi ý nghĩa:",
        },
        "water_safety": {
            "title": "An toàn đường sông — điều cần biết",
            "risk_ids": ["R03"],
            "intro": "Du lịch sông nước là linh hồn của vùng này, nhưng đừng quên an toàn:",
        },
        "heritage": {
            "title": "Bảo vệ di sản và sinh thái khi du lịch",
            "risk_ids": ["R04", "R06", "R07"],
            "intro": "Lò gạch cổ Mang Thít, đàn cò ở Chùa Hang, miệt vườn An Bình... đều rất mong manh. Hãy là du khách có trách nhiệm:",
        },
        "community": {
            "title": "Du lịch bền vững — cộng đồng là trung tâm",
            "risk_ids": ["R05", "R10", "R11", "R12"],
            "intro": "Du lịch chỉ bền vững khi cộng đồng địa phương được hưởng lợi thật sự. Đây là những điều bạn nên biết:",
        },
    }

    risk_map = {r["risk_id"]: r for r in risks}
    posts = []

    for gkey, group in groups.items():
        content_parts = [f"🌿 {group['title']}\n", group["intro"], ""]

        for rid in group["risk_ids"]:
            r = risk_map.get(rid)
            if not r:
                continue
            scope = r.get("scope", "").strip()
            mitigation = r.get("mitigation", "").strip()
            risk_name = r.get("risk", "").strip()

            if scope and mitigation:
                content_parts.append(f"⚠️ {risk_name} ({scope})")
                content_parts.append(f"→ {mitigation}")
                content_parts.append("")

        content = "\n".join(content_parts).strip()

        scope_places = []
        for rid in group["risk_ids"]:
            r = risk_map.get(rid)
            if r:
                scope_places.extend([s.strip() for s in r.get("scope", "").split(",") if s.strip()])

        entity = None
        for sp in scope_places:
            entity = fuzzy_match(sp, entities)
            if entity:
                break

        posts.append({
            "content": content,
            "post_type": "share",
            "entity_id": entity["id"] if entity else None,
            "entity_name": entity["name"] if entity else None,
            "rating": None,
            "category": "responsible",
            "source_id": gkey,
        })

    return posts


def gen_segment_posts(segments: list[dict], entities: list[dict]) -> list[dict]:
    posts = []
    for seg in segments:
        sid = seg["segment_id"]
        name = seg["segment"]
        profile = seg["profile"]
        motivation = seg["motivation"]
        best_assets = seg["best_assets"]
        trip_length = seg["trip_length"]
        needs = seg["needs"]

        content_parts = [f"👥 Hướng dẫn cho: {name}\n"]
        content_parts.append(f"Đối tượng: {profile}")
        content_parts.append(f"Mong muốn: {motivation}")
        content_parts.append(f"\n📍 Điểm đến gợi ý: {best_assets}")
        content_parts.append(f"⏱️ Thời gian: {trip_length}")
        content_parts.append(f"\n📝 Cần lưu ý: {needs}")

        content = "\n".join(content_parts)

        first_asset = best_assets.split(",")[0].strip() if best_assets else ""
        entity = fuzzy_match(first_asset, entities) if first_asset else None

        posts.append({
            "content": content,
            "post_type": "share",
            "entity_id": entity["id"] if entity else None,
            "entity_name": entity["name"] if entity else None,
            "rating": None,
            "category": "segment",
            "source_id": sid,
        })

    return posts


# ── Postgres operations ────────────────────────────────────────────────────────

def get_pg_connection():
    import os
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return None
    try:
        import psycopg2
        return psycopg2.connect(url)
    except ImportError:
        print("[ERROR] psycopg2 chưa cài. Chạy: pip install psycopg2-binary", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR] Không kết nối được Postgres: {e}", file=sys.stderr)
        return None


def ensure_editorial_user(conn) -> str:
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE phone = %s", (EDITORIAL_USER["phone"],))
    row = cur.fetchone()
    if row:
        return str(row[0])

    user_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO users (id, phone, display_name, bio, role, password_hash)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (user_id, EDITORIAL_USER["phone"], EDITORIAL_USER["display_name"],
         EDITORIAL_USER["bio"], EDITORIAL_USER["role"], "seed_account_no_login"),
    )
    conn.commit()
    return user_id


def alter_post_type_constraint(conn):
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE posts DROP CONSTRAINT IF EXISTS posts_post_type_check")
        cur.execute("""ALTER TABLE posts ADD CONSTRAINT posts_post_type_check
                       CHECK (post_type IN ('share', 'review', 'recommend', 'question'))""")
        conn.commit()
    except Exception:
        conn.rollback()


def insert_posts(conn, user_id: str, posts: list[dict]):
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    inserted = 0

    for i, post in enumerate(posts):
        post_id = str(uuid.uuid4())
        created = now - timedelta(hours=len(posts) - i)

        cur.execute(
            """INSERT INTO posts (id, user_id, entity_id, content, images, post_type, rating,
                                  moderation_status, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'approved', %s, %s)""",
            (post_id, user_id, post.get("entity_id"), post["content"],
             json.dumps([]), post["post_type"], post.get("rating"),
             created, created),
        )
        inserted += 1

    conn.commit()
    return inserted


# ── LLM rewrite ────────────────────────────────────────────────────────────────

LLM_SYSTEM = """Bạn là biên tập viên nội dung du lịch cho vinhlong360.vn — MXH du lịch cộng đồng Vĩnh Long, Bến Tre, Trà Vinh.

Nhiệm vụ: viết lại bài viết cộng đồng từ bản nháp thô (template) thành bài viết tự nhiên, hấp dẫn, đọc như người thật chia sẻ.

Quy tắc:
- Giữ nguyên tất cả thông tin thực tế (tên điểm, khoảng cách, tips, phân khúc)
- Giọng văn ấm áp, thân thiện, như người địa phương chia sẻ với bạn bè
- Không dùng từ sáo rỗng (tuyệt vời, không thể bỏ lỡ, thiên đường)
- Giữ emoji tiêu đề nhưng hạn chế emoji trong thân bài
- Độ dài 150-400 từ, chia đoạn rõ ràng
- KHÔNG thêm thông tin bịa đặt, KHÔNG thêm giá cả/số điện thoại
- Trả về đúng 1 bài viết đã viết lại, không giải thích thêm"""


def _llm_rewrite_batch(posts: list[dict], batch_size: int = 5) -> list[dict]:
    from openai import OpenAI

    client = OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", ""),
        api_key=os.environ.get("LLM_API_KEY", ""),
        timeout=120,
    )
    model = os.environ.get("LLM_MODEL", "cx/gpt-5.5")

    rewritten = []
    total = len(posts)

    for i in range(0, total, batch_size):
        batch = posts[i : i + batch_size]
        batch_prompts = []
        for p in batch:
            cat = p.get("category", "")
            if cat == "route":
                hint = "Bài gợi ý lịch trình du lịch"
            elif cat == "responsible":
                hint = "Bài chia sẻ về du lịch có trách nhiệm"
            else:
                hint = "Bài hướng dẫn du lịch cho nhóm đối tượng cụ thể"
            batch_prompts.append(f"[{hint}]\n{p['content']}")

        prompt = "Viết lại từng bài viết dưới đây. Phân cách bài bằng dòng ---\n\n" + "\n\n---\n\n".join(batch_prompts)

        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": LLM_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=4000,
            )
            text = resp.choices[0].message.content.strip()
            parts = re.split(r"\n-{3,}\n", text)

            for j, p in enumerate(batch):
                new_content = parts[j].strip() if j < len(parts) else p["content"]
                rewritten.append({**p, "content": new_content})
        except Exception as e:
            print(f"  [LLM ERROR] batch {i//batch_size + 1}: {e}", file=sys.stderr)
            rewritten.extend(batch)

        done = min(i + batch_size, total)
        print(f"  [llm] {done}/{total} rewritten")

    return rewritten


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed community posts from research data")
    parser.add_argument("--apply", action="store_true", help="Ghi vào Postgres (cần DATABASE_URL)")
    parser.add_argument("--llm", action="store_true", help="Dùng LLM viết lại nội dung tự nhiên hơn")
    parser.add_argument("--export", type=str, help="Xuất ra JSON file (VD: seed.json)")
    args = parser.parse_args()

    products = read_csv(CSV_PRODUCTS)
    risks = read_csv(CSV_RISKS)
    segments = read_csv(CSV_SEGMENTS)
    spatial_rows = read_csv(CSV_SPATIAL)
    spatial = build_spatial_map(spatial_rows)

    build_segment_label_map(segments)
    entities = load_sqlite_entities()

    print(f"[csv] {len(products)} products, {len(risks)} risks, {len(segments)} segments")
    print(f"[csv] {len(spatial_rows)} spatial routes")
    print(f"[db]  {len(entities)} entities loaded from SQLite")

    all_posts = []

    route_posts = gen_route_posts(products, spatial, entities)
    all_posts.extend(route_posts)
    print(f"\n[gen] {len(route_posts)} route posts (recommend)")

    resp_posts = gen_responsible_posts(risks, entities)
    all_posts.extend(resp_posts)
    print(f"[gen] {len(resp_posts)} responsible travel posts (share)")

    seg_posts = gen_segment_posts(segments, entities)
    all_posts.extend(seg_posts)
    print(f"[gen] {len(seg_posts)} segment guide posts (share)")

    if args.llm:
        print(f"\n[llm] Rewriting {len(all_posts)} posts with LLM...")
        all_posts = _llm_rewrite_batch(all_posts, batch_size=6)

    print(f"\n{'='*60}")
    print(f"  TỔNG: {len(all_posts)} bài viết")
    print(f"{'='*60}")

    linked = sum(1 for p in all_posts if p.get("entity_id"))
    print(f"  Liên kết entity: {linked}/{len(all_posts)}")

    for i, post in enumerate(all_posts):
        cat = post.get("category", "?")
        etype = post["post_type"]
        eid = post.get("entity_id") or "(none)"
        ename = post.get("entity_name") or ""
        preview = post["content"][:80].replace("\n", " ")
        print(f"\n  [{i+1}] [{cat}/{etype}] entity={eid}")
        if ename:
            print(f"       entity_name: {ename}")
        print(f"       {preview}...")

    if args.export:
        export_data = []
        for p in all_posts:
            export_data.append({
                "content": p["content"],
                "post_type": p["post_type"],
                "entity_id": p.get("entity_id"),
                "rating": p.get("rating"),
                "category": p.get("category"),
                "source_id": p.get("source_id"),
            })
        out_path = Path(args.export)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        print(f"\n[export] {len(export_data)} posts -> {out_path}")
        return

    if not args.apply:
        print(f"\n[dry-run] Chạy --apply để ghi vào Postgres (cần DATABASE_URL)")
        print(f"          Hoặc --export seed.json để xuất JSON")
        return

    conn = get_pg_connection()
    if not conn:
        print("[ERROR] Không có DATABASE_URL hoặc không kết nối được Postgres", file=sys.stderr)
        sys.exit(1)

    alter_post_type_constraint(conn)
    user_id = ensure_editorial_user(conn)
    print(f"\n[pg] Editorial user: {user_id}")

    inserted = insert_posts(conn, user_id, all_posts)
    conn.close()
    print(f"[pg] Inserted {inserted} posts (moderation_status=approved)")


if __name__ == "__main__":
    main()

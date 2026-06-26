"""
vinhlong360 — Auto-Learn Engine.

Agent TỰ ĐỘNG tìm kiếm, học hỏi và mở rộng knowledge base về Vĩnh Long
từ nhiều nguồn chính thống trên internet.

Vòng lặp học:
  1. LLM phân tích knowledge base hiện có → tìm lỗ hổng kiến thức
  2. Sinh truy vấn tìm kiếm (DuckDuckGo)
  3. Fetch + trích xuất thông tin có cấu trúc
  4. Loại trùng lắp, đánh giá chất lượng
  5. Thêm vào knowledge base
  6. Lặp lại

Chạy:
  python agent/auto_learn.py                    # 1 vòng học (mặc định 5 topic)
  python agent/auto_learn.py --topics 10        # 10 topic
  python agent/auto_learn.py --category history  # chỉ học lịch sử
  python agent/auto_learn.py --continuous       # chạy liên tục (mỗi 30 phút)
"""

import json
import logging
import os
import re
import sys
import time
import hashlib
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import httpx
from dotenv import load_dotenv
from openai import OpenAI
from ddgs import DDGS

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
)
MODEL = os.environ.get("LLM_MODEL", "cx/gpt-5.4")
MODEL_MINI = os.environ.get("LLM_MODEL_MINI", "cx/gpt-5.4-mini")

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
LEARN_DIR = Path(__file__).resolve().parent / "learned"
LEARN_DIR.mkdir(exist_ok=True)
LOG_FILE = LEARN_DIR / "_learn_log.jsonl"

# ── Entity types mở rộng ──

ENTITY_TYPES = {
    "attraction": "Điểm tham quan, di tích, công trình",
    "experience": "Trải nghiệm du lịch, hoạt động",
    "product": "Đặc sản, sản phẩm OCOP, nông sản",
    "dish": "Ẩm thực, món ăn đặc trưng",
    "craft_village": "Làng nghề truyền thống",
    "accommodation": "Lưu trú, homestay, khách sạn",
    "person": "Nhân vật lịch sử, danh nhân, nghệ nhân",
    "event": "Sự kiện, lễ hội, festival",
    "history": "Sự kiện lịch sử, di sản văn hóa",
    "nature": "Thiên nhiên, sinh thái, sông rạch",
    "economy": "Kinh tế, nông nghiệp, thủy sản",
}

# ── Danh mục chủ đề để học ──

CATEGORIES = {
    "tourism": {
        "label": "Du lịch",
        "seed_queries": [
            "điểm du lịch Vĩnh Long mới nhất",
            "homestay cù lao An Bình Vĩnh Long",
            "du lịch sinh thái Bến Tre",
            "du lịch Trà Vinh chùa Khmer",
            "khu du lịch mới Vĩnh Long 2025 2026",
        ],
    },
    "history": {
        "label": "Lịch sử",
        "seed_queries": [
            "lịch sử tỉnh Vĩnh Long",
            "di tích lịch sử Vĩnh Long",
            "danh nhân Vĩnh Long lịch sử",
            "chiến khu Bến Tre Trà Vinh lịch sử",
            "Thoại Ngọc Hầu Vĩnh Long",
            "Phan Thanh Giản Vĩnh Long",
            "lịch sử hình thành tỉnh Vĩnh Long",
        ],
    },
    "culture": {
        "label": "Văn hóa",
        "seed_queries": [
            "văn hóa Khmer Trà Vinh",
            "đờn ca tài tử Vĩnh Long",
            "lễ hội Ok Om Bok Trà Vinh",
            "lễ hội truyền thống miền Tây Nam Bộ Vĩnh Long",
            "nghệ thuật dân gian Vĩnh Long Bến Tre",
            "chùa cổ Vĩnh Long Trà Vinh",
        ],
    },
    "food": {
        "label": "Ẩm thực",
        "seed_queries": [
            "đặc sản Vĩnh Long ăn gì",
            "món ăn ngon Bến Tre",
            "ẩm thực Trà Vinh bún nước lèo",
            "quán ăn ngon Vĩnh Long",
            "đặc sản miền Tây sông nước",
        ],
    },
    "nature": {
        "label": "Thiên nhiên",
        "seed_queries": [
            "sông rạch Vĩnh Long cù lao",
            "hệ sinh thái miệt vườn Vĩnh Long",
            "rừng dừa Bến Tre",
            "biển Ba Động Trà Vinh",
            "chim cò Vĩnh Long khu bảo tồn",
        ],
    },
    "economy": {
        "label": "Kinh tế",
        "seed_queries": [
            "nông sản Vĩnh Long xuất khẩu",
            "OCOP Vĩnh Long 2025 2026",
            "thủy sản Bến Tre Trà Vinh",
            "sản phẩm dừa Bến Tre xuất khẩu",
            "cam sành Vĩnh Long thị trường",
        ],
    },
    "people": {
        "label": "Nhân vật",
        "seed_queries": [
            "danh nhân Vĩnh Long nổi tiếng",
            "nhân vật lịch sử Bến Tre",
            "nghệ nhân Trà Vinh Vĩnh Long",
            "người nổi tiếng quê Vĩnh Long",
            "Nguyễn Thông Vĩnh Long",
        ],
    },
    "news": {
        "label": "Tin tức",
        "seed_queries": [
            "tin tức Vĩnh Long mới nhất",
            "sự kiện Vĩnh Long 2026",
            "dự án du lịch Vĩnh Long",
            "sáp nhập tỉnh Vĩnh Long Bến Tre Trà Vinh",
        ],
    },
}

# ── Place mapping ──

PLACE_KEYWORDS = {
    "an bình": "xa-an-binh", "cù lao an bình": "xa-an-binh",
    "long hồ": "xa-long-ho", "nhơn phú": "xa-nhon-phu", "mang thít": "xa-nhon-phu",
    "trà ôn": "xa-tra-on", "lục sĩ thành": "xa-luc-si-thanh",
    "tam bình": "xa-tam-binh", "vũng liêm": "xa-trung-thanh",
    "bình minh": "p-binh-minh", "bình tân": "xa-tan-quoi",
    "tp vĩnh long": "p-long-chau", "thành phố vĩnh long": "p-long-chau",
    "vĩnh long": "p-long-chau",
    "thanh đức": "p-thanh-duc", "long châu": "p-long-chau",
    "phước hậu": "p-phuoc-hau", "tân hạnh": "p-tan-hanh",
    "cái vồn": "p-cai-von", "mỏ cày": "xa-mo-cay",
    "chợ lách": "xa-cho-lach", "bến tre": "p-ben-tre",
    "tp bến tre": "p-ben-tre", "thành phố bến tre": "p-ben-tre",
    "trà vinh": "p-tra-vinh", "tp trà vinh": "p-tra-vinh",
    "cầu kè": "xa-cau-ke", "duyên hải": "p-duyen-hai",
    "trà cú": "xa-tra-cu", "long đức": "p-long-duc",
    "tiểu cần": "xa-tieu-can", "càng long": "xa-cang-long",
    "cầu ngang": "xa-cau-ngang", "châu thành": "xa-chau-thanh",
    "ba tri": "xa-ba-tri", "giồng trôm": "xa-giong-trom",
    "bình đại": "xa-binh-dai", "thạnh phú": "xa-thanh-phu",
}


def guess_place_id(text: str) -> str | None:
    if not text:
        return None
    t = text.lower()
    for key, pid in sorted(PLACE_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if key in t:
            return pid
    return None


def make_slug(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", name.lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    s = s.replace("đ", "d").replace("Đ", "d")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:60]


def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


# ── Load existing knowledge ──

def load_knowledge() -> dict:
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {e["id"]: e for e in data.get("entities", [])}


def existing_names() -> set:
    kb = load_knowledge()
    return {e.get("name", "").lower() for e in kb.values()}


# ── Web search ──

def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Tìm kiếm DuckDuckGo, trả về list {title, url, body}."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="vn-vi", max_results=max_results))
        return results
    except Exception as e:
        logger.warning("Search error: %s", e)
        return []


def fetch_url(url: str) -> str | None:
    """Fetch và clean HTML → text."""
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True,
                         headers={"User-Agent": "vinhlong360-learner/1.0"})
        if resp.status_code != 200:
            return None
        text = resp.text
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.S)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:6000]
    except Exception:
        logger.debug("Failed to fetch URL: %s", url)
        return None


# ── LLM extraction ──

def analyze_gaps(known_names: set, category: str = None) -> list[str]:
    """LLM phân tích lỗ hổng kiến thức, sinh truy vấn tìm kiếm mới."""
    cat_info = ""
    if category and category in CATEGORIES:
        cat_info = f"\nTập trung vào danh mục: {CATEGORIES[category]['label']}"

    sample = sorted(list(known_names))[:50]

    prompt = f"""Bạn là chuyên gia về tỉnh Vĩnh Long (mới, bao gồm cả Bến Tre và Trà Vinh).

Knowledge base hiện có {len(known_names)} thực thể, ví dụ:
{', '.join(sample[:30])}
{cat_info}

Hãy nghĩ ra 5 truy vấn tìm kiếm tiếng Việt để TÌM THÊM thông tin mà knowledge base CHƯA CÓ.
Ưu tiên: thông tin chính thống, cụ thể, có giá trị cho du khách hoặc người tìm hiểu.

Trả về JSON array gồm 5 string, mỗi string là 1 truy vấn tìm kiếm.
Chỉ trả JSON, không text khác."""

    try:
        response = client.chat.completions.create(
            model=MODEL_MINI,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        return json.loads(content)
    except Exception as e:
        logger.warning("Gap analysis error: %s", e)
        return []


def extract_entities_from_text(text: str, source_url: str, query: str) -> list[dict]:
    """Dùng LLM trích xuất entities từ nội dung web page."""
    prompt = f"""Từ nội dung web page dưới đây, trích xuất các THỰC THỂ NẰM TRONG tỉnh Vĩnh Long, Bến Tre, hoặc Trà Vinh.

Query gốc: {query}
URL: {source_url}

Nội dung:
{text[:4000]}

Trích xuất thành JSON array. Mỗi item:
{{
  "name": "Tên thực thể (tiếng Việt, đầy đủ dấu)",
  "type": "attraction|experience|product|dish|craft_village|accommodation|person|event|history|nature|economy",
  "summary": "Mô tả 1-2 câu tiếng Việt, nêu rõ ở đâu thuộc VL/BT/TV",
  "location": "Địa điểm cụ thể (xã/phường/huyện, tỉnh) nếu biết, null nếu không",
  "confidence": 0.5-0.9 (đánh giá mức tin cậy thông tin)
}}

Quy tắc NGHIÊM NGẶT:
- CHỈ trích xuất thực thể CỤ THỂ nằm trong Vĩnh Long, Bến Tre, hoặc Trà Vinh
- LOẠI BỎ thực thể ở tỉnh khác (Cần Thơ, Tiền Giang, Đồng Tháp, Hậu Giang, An Giang, Sóc Trăng, HCMC...)
- LOẠI BỎ khái niệm chung: tên tỉnh/huyện/sông/vùng miền (vd: "Vĩnh Long", "sông Hậu", "ĐBSCL")
- LOẠI BỎ văn bản pháp luật: nghị quyết, chỉ thị, quyết định, thông tư
- LOẠI BỎ thương hiệu toàn quốc: Vincom, FLC, Vietcombank...
- Tên phải bằng tiếng Việt, có dấu đầy đủ. KHÔNG dùng tên tiếng Anh
- Nếu không chắc thực thể thuộc VL/BT/TV → KHÔNG trích xuất
- Nếu không có thực thể nào phù hợp, trả về []

Chỉ trả JSON array, không text khác."""

    try:
        response = client.chat.completions.create(
            model=MODEL_MINI,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        items = json.loads(content)
        if not isinstance(items, list):
            return []
        return items
    except Exception as e:
        logger.warning("Extract error: %s", e)
        return []


def to_entity(raw: dict, source_url: str) -> dict:
    """Chuyển raw extracted item → entity format chuẩn."""
    name = raw.get("name", "")
    slug = make_slug(name)
    entity_type = raw.get("type", "attraction")
    if entity_type not in ENTITY_TYPES:
        entity_type = "attraction"
    place_id = guess_place_id(raw.get("location", "") or name)

    entity = {
        "id": slug,
        "type": entity_type,
        "name": name,
        "placeId": place_id,
        "summary": raw.get("summary", ""),
        "season": None,
        "attributes": {},
        "source": {"title": source_url.split("/")[2] if "/" in source_url else source_url, "url": source_url},
        "confidence": min(0.9, max(0.3, raw.get("confidence", 0.6))),
        "updatedAt": datetime.now().strftime("%Y-%m-%d"),
    }

    # Geocode via OSM (precise map coords — NOT from the LLM, which hallucinates).
    try:
        import geocode as _geo
        coords = _geo.geocode(name, region=raw.get("location") or "Vĩnh Long")
        if coords:
            entity["coords"] = coords
    except Exception:
        logger.debug("Geocode unavailable for entity: %s", name)

    return entity


# ── Noise filters ──

# Địa danh NGOÀI Vĩnh Long mới — loại bỏ
OUTSIDE_KEYWORDS = [
    "cần thơ", "ninh kiều", "tiền giang", "cái bè", "mỹ tho",
    "đồng tháp", "an giang", "sóc trăng", "hậu giang", "kiên giang",
    "bạc liêu", "cà mau", "long an", "hồ chí minh", "sài gòn",
    "hà nội", "đà nẵng", "huế", "nha trang", "đà lạt", "phú quốc",
    "vũng tàu", "bình dương", "đồng nai", "tây ninh", "bình phước",
]

# Tên quá chung — không phải entity cụ thể
TOO_GENERIC = [
    "vĩnh long", "bến tre", "trà vinh", "long hồ",
    "tỉnh vĩnh long", "tỉnh bến tre", "tỉnh trà vinh",
    "huyện tam bình", "huyện mang thít", "huyện vũng liêm",
    "sông tiền", "sông hậu", "sông cổ chiên", "sông mê kông",
    "đồng bằng sông cửu long", "miền tây", "nam bộ",
    "du lịch", "ẩm thực", "văn hóa", "lịch sử",
]

# Pattern cho văn bản pháp luật / hành chính
LEGAL_PATTERNS = [
    r"nghị quyết", r"chỉ thị", r"quyết định", r"thông tư",
    r"luật\s", r"số\s+\d+", r"NQ-", r"CT/TW", r"QĐ-",
    r"UBND", r"HĐND", r"vincom", r"plaza",
]

# Từ tiếng Anh phổ biến → dấu hiệu tên English
ENGLISH_MARKERS = [
    "hotel", "resort", "homestay", "hostel", "market", "floating",
    "temple", "pier", "park", "eco", "island", "beach", "village",
    "museum", "tower", "bridge", "center", "centre", "plaza",
    "garden", "farm", "river", "cruise", "tour", "airport",
]


def _has_vietnamese_diacritics(text: str) -> bool:
    return bool(re.search(r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]", text.lower()))


def _is_english_name(name: str) -> bool:
    """Kiểm tra tên tiếng Anh. Cẩn thận không bắt nhầm tên Việt/Khmer."""
    has_vn = _has_vietnamese_diacritics(name)
    name_lower = name.lower()
    # Nếu chứa từ English phổ biến VÀ không có dấu tiếng Việt → English
    for marker in ENGLISH_MARKERS:
        if marker in name_lower:
            return not has_vn
    # Toàn bộ ASCII, >= 3 từ, không dấu → English
    alpha_chars = re.sub(r"[^a-zA-ZÀ-ỹ]", "", name)
    if not alpha_chars or len(alpha_chars) < 6:
        return False
    if has_vn:
        return False
    return len(name.split()) >= 3


def _normalize(s: str) -> str:
    """Chuẩn hóa text để so sánh tương đồng."""
    import unicodedata
    s = unicodedata.normalize("NFD", s.lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    s = s.replace("đ", "d")
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def is_near_duplicate(name: str, known_names: set) -> str | None:
    """Kiểm tra trùng gần (fuzzy match). Trả về tên trùng nếu có."""
    norm = _normalize(name)
    if len(norm) < 4:
        return None
    for existing in known_names:
        enorm = _normalize(existing)
        if not enorm:
            continue
        # Exact normalized match
        if norm == enorm:
            return existing
        # One contains the other (> 80% length)
        if len(norm) > 6 and len(enorm) > 6:
            if norm in enorm or enorm in norm:
                shorter = min(len(norm), len(enorm))
                longer = max(len(norm), len(enorm))
                if shorter / longer > 0.6:
                    return existing
    return None


def filter_entity(raw: dict, known_names: set) -> tuple[bool, str]:
    """
    Kiểm tra 1 entity có nên giữ không.
    Returns: (keep: bool, reason: str)
    """
    name = raw.get("name", "").strip()
    name_lower = name.lower()
    location = (raw.get("location") or "").lower()

    # 1. Tên quá ngắn
    if len(name) < 4:
        return False, "tên quá ngắn"

    # 2. Tên tiếng Anh
    if _is_english_name(name):
        return False, "tên tiếng Anh"

    # 3. Quá chung chung
    if name_lower in TOO_GENERIC:
        return False, "quá chung"
    for g in TOO_GENERIC:
        if name_lower == g or (len(name_lower) < 15 and name_lower.startswith(g)):
            return False, f"quá chung ({g})"

    # 4. Ngoài Vĩnh Long
    for kw in OUTSIDE_KEYWORDS:
        if kw in location and "vĩnh long" not in location and "bến tre" not in location and "trà vinh" not in location:
            return False, f"ngoài VL ({kw})"
        if kw in name_lower and not any(vl in name_lower for vl in ["vĩnh long", "bến tre", "trà vinh"]):
            return False, f"ngoài VL ({kw})"

    # 5. Văn bản pháp luật / thương mại
    for pat in LEGAL_PATTERNS:
        if re.search(pat, name_lower):
            return False, f"văn bản/thương mại ({pat.strip()})"

    # 6. Trùng gần
    dup = is_near_duplicate(name, known_names)
    if dup:
        return False, f"trùng gần: {dup}"

    # 7. Tên bắt đầu bằng chữ thường (không phải danh từ riêng)
    if name[0].islower() and raw.get("type") not in ("nature", "economy"):
        return False, "không phải danh từ riêng"

    # 8. Summary quá ngắn hoặc rỗng (thông tin ít giá trị)
    summary = raw.get("summary", "")
    if len(summary) < 10:
        return False, "thiếu mô tả"

    return True, "ok"


# ── Main learn loop ──

def learn_from_query(query: str, known: set) -> list[dict]:
    """Tìm kiếm 1 query, trích xuất entities mới."""
    logger.info("Searching: \"%s\"", query)
    results = web_search(query, max_results=3)
    if not results:
        logger.info("No results for query: %s", query)
        return []

    new_entities = []
    for r in results:
        url = r.get("href") or r.get("url", "")
        if not url:
            continue

        # Fetch page content
        text = fetch_url(url)
        if not text or len(text) < 200:
            continue

        # Extract entities
        raw_items = extract_entities_from_text(text, url, query)
        for raw in raw_items:
            name = raw.get("name", "").strip()
            if not name or len(name) < 3:
                continue
            if name.lower() in known:
                continue

            # ── Noise filter ──
            keep, reason = filter_entity(raw, known)
            if not keep:
                logger.debug("Filtered [%s] %s", reason, name)
                continue

            entity = to_entity(raw, url)
            if entity["id"] and entity["id"] not in {e["id"] for e in new_entities}:
                new_entities.append(entity)
                known.add(name.lower())
                logger.info("Found [%s] %s", entity['type'], name)

    return new_entities


def learn_round(category: str = None, num_topics: int = 5) -> list[dict]:
    """1 vòng học: tìm gaps → search → extract → deduplicate."""
    logger.info("Auto-Learn Round started at %s", datetime.now().strftime('%Y-%m-%d %H:%M'))

    known = existing_names()
    logger.info("Knowledge base: %d entities", len(known))

    # Chọn queries
    queries = []
    if category and category in CATEGORIES:
        cat = CATEGORIES[category]
        logger.info("Category: %s", cat['label'])
        queries = cat["seed_queries"][:num_topics]
    else:
        # LLM phân tích gaps + lấy từ seed
        logger.info("Analyzing knowledge gaps...")
        gap_queries = analyze_gaps(known, category)
        if gap_queries:
            queries = gap_queries[:num_topics]
            logger.info("LLM suggested %d new queries", len(queries))
        else:
            # Fallback: random seed queries
            import random
            all_seeds = []
            for cat in CATEGORIES.values():
                all_seeds.extend(cat["seed_queries"])
            random.shuffle(all_seeds)
            queries = all_seeds[:num_topics]

    logger.info("Will search %d topics", len(queries))

    all_new = []
    for q in queries:
        entities = learn_from_query(q, known)
        all_new.extend(entities)
        time.sleep(2)  # Rate limiting

    # Deduplicate by ID
    seen_ids = set()
    unique = []
    for e in all_new:
        if e["id"] not in seen_ids:
            seen_ids.add(e["id"])
            unique.append(e)

    logger.info("Round complete — new entities: %d", len(unique))

    if unique:
        # Group by type
        by_type = {}
        for e in unique:
            by_type.setdefault(e["type"], []).append(e)
        for t, items in sorted(by_type.items()):
            label = ENTITY_TYPES.get(t, t)
            logger.info("[%s] %s: %d", t, label, len(items))
            for e in items:
                place = e.get("placeId", "?")
                logger.debug("  - %s -> %s (conf: %s)", e['name'], place, e['confidence'])

        # Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = LEARN_DIR / f"learned_{timestamp}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(unique, f, ensure_ascii=False, indent=2)
        logger.info("Saved: %s", out_file)

        # Log
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "queries": queries,
            "found": len(unique),
            "types": {t: len(items) for t, items in by_type.items()},
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return unique


def apply_learned(entities: list[dict]):
    """GĐ3.7: thêm entities đã học vào DB (nguồn sự thật), không còn append data.json.

    DB là SoT; chat/`/api` đọc DB. Sau khi thêm, reload knowledge để chat thấy ngay.
    """
    from database import db  # lazy import

    added = []
    for e in entities:
        if not db.get_entity(e["id"]):
            db.upsert_entity(e)
            added.append(e)

    if added:
        logger.info("Added %d entities to DB", len(added))
        try:
            import knowledge
            knowledge.reload()
        except Exception:
            logger.debug("Could not reload knowledge after adding entities")
    else:
        logger.info("No new entities to add (all duplicates)")
    return added


def continuous_learn(interval_minutes: int = 30):
    """Chạy liên tục, học theo vòng xoay danh mục."""
    categories = list(CATEGORIES.keys())
    i = 0
    while True:
        cat = categories[i % len(categories)]
        logger.info("Round %d — Category: %s", i + 1, CATEGORIES[cat]['label'])

        entities = learn_round(category=cat, num_topics=3)
        if entities:
            apply_learned(entities)

        i += 1
        logger.info("Sleeping %d minutes...", interval_minutes)
        time.sleep(interval_minutes * 60)


# ── CLI ──

def main():
    import argparse
    parser = argparse.ArgumentParser(description="vinhlong360 Auto-Learn")
    parser.add_argument("--category", "-c", choices=list(CATEGORIES.keys()),
                        help="Học theo danh mục cụ thể")
    parser.add_argument("--topics", "-t", type=int, default=5,
                        help="Số topic mỗi vòng (mặc định 5)")
    parser.add_argument("--apply", "-a", action="store_true",
                        help="Tự động thêm vào data.json")
    parser.add_argument("--continuous", action="store_true",
                        help="Chạy liên tục")
    parser.add_argument("--interval", type=int, default=30,
                        help="Khoảng cách giữa các vòng (phút, mặc định 30)")
    args = parser.parse_args()

    if args.continuous:
        continuous_learn(args.interval)
    else:
        entities = learn_round(category=args.category, num_topics=args.topics)
        if entities and args.apply:
            apply_learned(entities)
        elif entities:
            print("\n  Dùng --apply để thêm vào data.json")


if __name__ == "__main__":
    main()

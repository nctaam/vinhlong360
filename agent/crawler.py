"""
vinhlong360 — Web Crawler.

Đọc dữ liệu từ vinhlongtourist.vn, dùng LLM trích xuất thông tin
có cấu trúc, rồi đề xuất entity mới cho knowledge base.

Chạy:
  python agent/crawler.py                    # crawl tất cả
  python agent/crawler.py /vi/vinhsang       # crawl 1 trang cụ thể
"""

import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
    timeout=30,
)
MODEL_MINI = os.environ.get("LLM_MODEL_MINI", "cx/gpt-5.4-mini")

BASE_URL = "https://vinhlongtourist.vn"
OUTPUT_DIR = Path(__file__).resolve().parent / "crawled"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Mapping địa chỉ → placeId ──

PLACE_MAPPING = {
    "an bình": "xa-an-binh",
    "cù lao an bình": "xa-an-binh",
    "long hồ": "xa-long-ho",
    "nhơn phú": "xa-nhon-phu",
    "mang thít": "xa-nhon-phu",
    "trà ôn": "xa-tra-on",
    "lục sĩ thành": "xa-luc-si-thanh",
    "lục sỹ thành": "xa-luc-si-thanh",
    "tam bình": "xa-tam-binh",
    "vũng liêm": "xa-trung-thanh",
    "bình minh": "p-binh-minh",
    "bình tân": "xa-tan-quoi",
    "tp vĩnh long": "p-long-chau",
    "thành phố vĩnh long": "p-long-chau",
    "thanh đức": "p-thanh-duc",
    "long châu": "p-long-chau",
    "phước hậu": "p-phuoc-hau",
    "tân hạnh": "p-tan-hanh",
    "tân ngãi": "p-tan-ngai",
    "cái vồn": "p-cai-von",
    "mỏ cày": "xa-mo-cay",
    "chợ lách": "xa-cho-lach",
    "bến tre": "p-ben-tre",
    "trà vinh": "p-tra-vinh",
    "cầu kè": "xa-cau-ke",
    "duyên hải": "p-duyen-hai",
}


def guess_place_id(address: str) -> str | None:
    """Đoán placeId từ địa chỉ text."""
    if not address:
        return None
    addr_lower = address.lower()
    for key, pid in PLACE_MAPPING.items():
        if key in addr_lower:
            return pid
    return None


def guess_entity_type(raw_type: str) -> str:
    """Map loại từ LLM về entity type chuẩn."""
    raw = raw_type.lower()
    if any(k in raw for k in ["tham quan", "du lịch", "khu du lịch", "điểm", "attraction", "bảo tàng", "chùa", "đình", "di tích"]):
        return "attraction"
    if any(k in raw for k in ["homestay", "lưu trú", "khách sạn", "nhà nghỉ", "accommodation"]):
        return "accommodation"
    if any(k in raw for k in ["trải nghiệm", "experience", "tour"]):
        return "experience"
    if any(k in raw for k in ["làng nghề", "craft"]):
        return "craft_village"
    if any(k in raw for k in ["sản phẩm", "đặc sản", "product"]):
        return "product"
    if any(k in raw for k in ["ẩm thực", "món ăn", "dish"]):
        return "dish"
    return "attraction"


def make_slug(name: str) -> str:
    """Tạo slug từ tên tiếng Việt."""
    import unicodedata
    s = unicodedata.normalize("NFD", name.lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    s = s.replace("đ", "d").replace("Đ", "d")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:60]


# ── Fetch & extract ──

def fetch_page(path: str) -> str:
    """Fetch HTML từ vinhlongtourist.vn, trả về text content."""
    url = BASE_URL + path
    print(f"  Fetching: {url}")
    resp = httpx.get(url, timeout=30, follow_redirects=True,
                     headers={"User-Agent": "vinhlong360-crawler/1.0"})
    resp.raise_for_status()
    # Loại bỏ HTML tags cơ bản
    text = resp.text
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Giới hạn độ dài
    return text[:8000]


def extract_with_llm(page_text: str, url: str) -> dict | None:
    """Dùng LLM mini trích xuất thông tin có cấu trúc.

    B6 compliance: chỉ trích xuất tiêu đề + loại + địa chỉ + thông tin liên hệ.
    summary giới hạn 200 ký tự, KHÔNG sao chép nguyên văn nội dung gốc.
    """
    prompt = f"""Trích xuất thông tin du lịch từ nội dung trang web sau thành JSON.
QUAN TRỌNG: Chỉ trích xuất dữ kiện (tên, loại, địa chỉ, SĐT, giờ, giá).
KHÔNG sao chép nguyên văn nội dung. Summary phải tự viết lại, tối đa 200 ký tự.

URL: {BASE_URL}{url}

Nội dung:
{page_text}

Trả về JSON duy nhất (không markdown, không giải thích) với cấu trúc:
{{
  "name": "Tên địa điểm/dịch vụ",
  "type": "attraction|accommodation|experience|craft_village|product|dish",
  "address": "Địa chỉ đầy đủ (xã, huyện, tỉnh)",
  "summary": "Mô tả ngắn tự viết lại, tối đa 200 ký tự (tiếng Việt)",
  "services": ["dịch vụ 1", "dịch vụ 2"],
  "price": "Giá tham khảo nếu có, null nếu không",
  "hours": "Giờ mở cửa nếu có, null nếu không",
  "phone": "SĐT nếu có, null nếu không",
  "source_url": "{BASE_URL}{url}"
}}

Chỉ trả JSON, không có text khác."""

    response = client.chat.completions.create(
        model=MODEL_MINI,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    content = response.choices[0].message.content.strip()
    # Parse JSON (loại bỏ markdown nếu có)
    content = re.sub(r"^```json\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print(f"  ⚠ Không parse được JSON từ LLM: {content[:200]}")
        return None


def to_entity(extracted: dict, url: str) -> dict:
    """Chuyển dữ liệu trích xuất thành entity format chuẩn."""
    name = extracted.get("name", "Unknown")
    entity_type = guess_entity_type(extracted.get("type", "attraction"))
    place_id = guess_place_id(extracted.get("address", ""))
    slug = make_slug(name)

    attrs = {}
    if extracted.get("price"):
        attrs["gia"] = extracted["price"]
    if extracted.get("hours"):
        attrs["gio_mo_cua"] = extracted["hours"]
    if extracted.get("phone"):
        attrs["sdt"] = extracted["phone"]
    if extracted.get("services"):
        attrs["dich_vu"] = ", ".join(extracted["services"][:5])

    # B6: truncate summary to 200 chars, never store full article text
    summary = (extracted.get("summary", "") or "")[:200]

    return {
        "id": slug,
        "type": entity_type,
        "name": name,
        "placeId": place_id,
        "summary": summary,
        "season": None,
        "attributes": attrs,
        "source": {
            "title": "vinhlongtourist.vn",
            "url": extracted.get("source_url", BASE_URL + url),
        },
        "confidence": 0.85,
        "updatedAt": time.strftime("%Y-%m-%d"),
        "_crawled_from": url,
        "_address_raw": extracted.get("address", ""),
    }


# ── Crawl danh sách ──

def fetch_place_list() -> list[dict]:
    """Lấy danh sách địa điểm từ /vi/places."""
    text = fetch_page("/vi/places")
    prompt = f"""Từ nội dung trang web, trích xuất danh sách các địa điểm du lịch.

Nội dung:
{text}

Trả về JSON array (không markdown):
[{{"name": "Tên", "url": "/vi/slug"}}]

Chỉ trả JSON array, không text khác."""

    response = client.chat.completions.create(
        model=MODEL_MINI,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    content = response.choices[0].message.content.strip()
    content = re.sub(r"^```json\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print(f"  ⚠ Không parse được danh sách: {content[:300]}")
        return []


def crawl_one(url_path: str) -> dict | None:
    """Crawl 1 trang chi tiết, trả về entity."""
    try:
        text = fetch_page(url_path)
        extracted = extract_with_llm(text, url_path)
        if not extracted:
            return None
        entity = to_entity(extracted, url_path)
        # Lưu file riêng
        out_file = OUTPUT_DIR / f"{entity['id']}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(entity, f, ensure_ascii=False, indent=2)
        print(f"  ✓ {entity['name']} → {entity['type']} → {entity.get('placeId', '?')}")
        return entity
    except Exception as e:
        print(f"  ✗ Lỗi crawl {url_path}: {e}")
        return None


def crawl_all():
    """Crawl toàn bộ vinhlongtourist.vn/vi/places."""
    print("═══ Crawl vinhlongtourist.vn ═══\n")
    print("Bước 1: Lấy danh sách địa điểm...")
    place_list = fetch_place_list()
    print(f"  Tìm thấy {len(place_list)} địa điểm\n")

    print("Bước 2: Crawl từng trang chi tiết...")
    entities = []
    for i, item in enumerate(place_list):
        url = item.get("url", "")
        if not url:
            continue
        print(f"\n[{i+1}/{len(place_list)}] {item.get('name', url)}")
        entity = crawl_one(url)
        if entity:
            entities.append(entity)
        time.sleep(1)  # Rate limiting

    # Lưu tổng hợp
    all_file = OUTPUT_DIR / "_all_crawled.json"
    with open(all_file, "w", encoding="utf-8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)

    print("\n═══ Hoàn tất ═══")
    print(f"Crawled: {len(entities)}/{len(place_list)} địa điểm")
    print(f"Output: {OUTPUT_DIR}")

    # Thống kê
    no_place = [e for e in entities if not e.get("placeId")]
    if no_place:
        print(f"\n⚠ {len(no_place)} entity chưa map được placeId:")
        for e in no_place:
            print(f"  - {e['name']}: \"{e.get('_address_raw', '')}\"")

    return entities


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        entity = crawl_one(path)
        if entity:
            print(json.dumps(entity, ensure_ascii=False, indent=2))
    else:
        crawl_all()

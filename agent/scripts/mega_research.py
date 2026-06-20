#!/usr/bin/env python3
"""MEGA Research v3 — Accuracy-First, Rate-Limit-Aware, Full Coverage.

12 Phase:
  1  Corpus Expansion       — 150+ web searches, fetch+index sources
  2  Administrative Geography — 26 huyện/TX/TP, web-verified ward lists
  3  OCOP Catalog           — discover + deep-research per product
  4  Heritage & History     — timelines + di tích + web sources
  5  Ecology & Nature       — hệ sinh thái + species + web
  6  Gastronomy             — ẩm thực + web research per dish
  7  Craft Villages         — làng nghề + web research
  8  Festivals & Events     — lễ hội + web verified
  9  Entity Enrichment      — ALL remaining entities + web context
  10 PlaceId & Coordinates  — xã/phường mapping + coords
  11 Cross-Analysis         — journeys, personas, relationships
  12 Adversarial Verify     — independent fact-check sampled claims

Usage:
  python -u agent/scripts/mega_research.py --phase 1 --workers 6
  python -u agent/scripts/mega_research.py --all
  python -u agent/scripts/mega_research.py --stats
  python -u agent/scripts/mega_research.py --phase 1 --dry
"""
from __future__ import annotations
import argparse, json, os, re, sys, time, threading, random, warnings
warnings.filterwarnings("ignore", message=".*renamed.*ddgs.*")
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections import Counter

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research"
DATA_JSON = PROJECT_DIR / "web" / "data.json"

sys.path.insert(0, str(AGENT_DIR))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
try:
    import requests as _req
except ImportError:
    _req = None
try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        DDGS = None

DEFAULT_MODEL = os.environ.get("LLM_MODEL") or "cx/gpt-5.5"
_lock = threading.Lock()
_search_lock = threading.Lock()
_last_search_time = 0.0
SEARCH_COOLDOWN = 1.5  # seconds between web searches to avoid rate-limit

# ─── System prompts ─────────────────────────────────────────────────────────

SYS_ACCURACY = """Bạn là nhà nghiên cứu về miền Tây Nam Bộ Việt Nam (Vĩnh Long, Bến Tre, Trà Vinh).

NGUYÊN TẮC BẮT BUỘC:
1. CHỈ nêu thông tin có trong [NGUỒN WEB] hoặc kiến thức chắc chắn 100%.
2. KHÔNG BAO GIỜ bịa, đoán, hallucinate. Không biết → ghi null hoặc "chưa xác minh".
3. MỌI fact kèm confidence (0.0–1.0):
   0.9–1.0 = có URL xác nhận rõ ràng
   0.7–0.89 = kiến thức phổ biến, phù hợp ngữ cảnh
   0.5–0.69 = suy luận hợp lý, chưa xác minh
   < 0.5 = KHÔNG đưa vào, ghi null
4. Ghi source URL cho mỗi fact quan trọng.
5. JSON hợp lệ, tiếng Việt chính xác, không markdown."""

SYS_VERIFY = """Bạn là fact-checker nghiêm khắc. Kiểm chứng TỪNG claim.

Mỗi claim:
1. Tìm trong nguồn web xem có xác nhận không
2. Kiểm tra nhất quán logic
3. Verdict: CONFIRMED (≥1 nguồn) / PLAUSIBLE (hợp lý, thiếu nguồn) / UNVERIFIED / REFUTED
4. Mặc định = UNVERIFIED nếu không có bằng chứng

JSON hợp lệ."""


# ─── Utilities ───────────────────────────────────────────────────────────────

def _cfg_io():
    os.environ["PYTHONUNBUFFERED"] = "1"
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", line_buffering=True)

def utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")

def log(msg: str):
    print(f"[{ts()}] {msg}", flush=True)

def compact(t: Any, n: int = 8000) -> str:
    return re.sub(r"\s+", " ", str(t or "")).strip()[:n]

def parse_json(text: str) -> Any:
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.MULTILINE).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return None

def append_jsonl(path: Path, rec: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
    return out

def load_entities() -> list[dict]:
    if not DATA_JSON.exists():
        return []
    with open(DATA_JSON, "r", encoding="utf-8") as f:
        d = json.load(f)
    return d.get("entities", d) if isinstance(d, dict) else d

def save_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── LLM Client ─────────────────────────────────────────────────────────────

class LLM:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.key = os.environ.get("LLM_API_KEY", "")
        self.base = os.environ.get("LLM_BASE_URL", "")
        self._lk = threading.Lock()
        self.calls = self.pt = self.ct = self.errs = 0

    @property
    def ok(self) -> bool:
        return bool(self.key and self.base and OpenAI)

    def _add(self, c=0, p=0, t=0, e=0):
        with self._lk:
            self.calls += c; self.pt += p; self.ct += t; self.errs += e

    def ask(self, sys: str, user: str, temp: float = 0.15,
            max_tok: int = 4000, timeout: int = 300, retries: int = 3) -> str | None:
        if not self.ok:
            return None
        for i in range(retries + 1):
            try:
                c = OpenAI(api_key=self.key, base_url=self.base)
                stream = c.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
                    temperature=temp, max_tokens=max_tok, timeout=timeout,
                    stream=True)
                chunks = []
                p_tok = c_tok = 0
                for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        chunks.append(delta.content)
                    u = getattr(chunk, "usage", None)
                    if u:
                        p_tok = int(getattr(u, "prompt_tokens", 0) or 0)
                        c_tok = int(getattr(u, "completion_tokens", 0) or 0)
                if not c_tok and chunks:
                    c_tok = len("".join(chunks)) // 4
                self._add(c=1, p=p_tok, t=c_tok)
                return "".join(chunks) or ""
            except Exception as ex:
                self._add(e=1)
                ex_str = str(ex)
                if "502" in ex_str or "524" in ex_str or "429" in ex_str:
                    w = 60 * (i + 1)
                elif "500" in ex_str or "503" in ex_str:
                    w = 30 * (i + 1)
                else:
                    w = 10 * (i + 1)
                if i < retries:
                    log(f"  retry {i+1}/{retries}: {type(ex).__name__} — wait {w}s")
                    time.sleep(w)
                else:
                    log(f"  LLM ERROR: {ex}")
        return None

    def ask_json(self, sys: str, user: str, **kw) -> Any:
        r = self.ask(sys=sys, user=user, **kw)
        return parse_json(r) if r else None

    def info(self) -> dict:
        return {"model": self.model, "calls": self.calls,
                "prompt_tokens": self.pt, "completion_tokens": self.ct, "errors": self.errs}


# ─── Web Search & Fetch ─────────────────────────────────────────────────────

def _rate_limit():
    global _last_search_time
    with _search_lock:
        now = time.time()
        wait = SEARCH_COOLDOWN - (now - _last_search_time)
        if wait > 0:
            time.sleep(wait)
        _last_search_time = time.time()

def fetch_url(url: str, timeout: int = 15) -> str:
    if not _req or not url.startswith("http"):
        return ""
    try:
        r = _req.get(url.strip(), headers={"User-Agent": "vinhlong360-research/3"},
                     timeout=timeout, allow_redirects=True)
        if r.status_code >= 400:
            return ""
        t = r.text or ""
        t = re.sub(r"<script[^>]*>.*?</script>", " ", t, flags=re.DOTALL | re.I)
        t = re.sub(r"<style[^>]*>.*?</style>", " ", t, flags=re.DOTALL | re.I)
        t = re.sub(r"<[^>]+>", " ", t)
        t = re.sub(r"&\w+;", " ", t)
        return compact(t, 15000)
    except Exception:
        return ""

def web_search(query: str, n: int = 10) -> list[dict]:
    if not DDGS:
        return []
    _rate_limit()
    out = []
    try:
        with DDGS() as d:
            for item in d.text(query, max_results=n):
                if not isinstance(item, dict):
                    continue
                url = item.get("href") or item.get("url") or ""
                if url.startswith("http"):
                    out.append({"title": str(item.get("title", "")), "url": url,
                                "snippet": compact(item.get("body") or item.get("snippet"), 500)})
    except Exception as ex:
        log(f"  search error: {ex}")
    return out[:n]

def web_research(queries: list[str], max_per: int = 8, max_fetch: int = 12) -> tuple[list[dict], str]:
    """Search multiple queries, fetch unique URLs, build context string.
    If first query returns nothing, tries simplified (no quotes) version."""
    all_r, seen = [], set()
    for q in queries:
        results = web_search(q, n=max_per)
        if not results and '"' in q:
            results = web_search(q.replace('"', ''), n=max_per)
        for r in results:
            if r["url"] not in seen:
                seen.add(r["url"])
                all_r.append(r)
    for r in all_r[:max_fetch]:
        r["text"] = fetch_url(r["url"], timeout=12)
    good = [r for r in all_r if r.get("text") and len(r["text"]) > 200]
    ctx = "\n\n---SOURCE---\n\n".join(
        f"[URL: {r['url']}]\n[Title: {r['title']}]\n{r['text'][:2500]}"
        for r in good[:10]
    )
    return good, ctx[:12000]

def src_list(web_results: list[dict]) -> list[dict]:
    return [{"url": r["url"], "title": r.get("title", ""),
             "len": len(r.get("text", ""))} for r in web_results]

PROVINCE = {"vinh-long": "Vĩnh Long", "ben-tre": "Bến Tre", "tra-vinh": "Trà Vinh"}


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: CORPUS EXPANSION (web-only, no LLM)
# ═══════════════════════════════════════════════════════════════════════════════

QUERIES = {
    "vinh-long": [
        "du lịch Vĩnh Long 2026", "ẩm thực Vĩnh Long đặc sản", "di tích lịch sử Vĩnh Long danh sách",
        "làng nghề Vĩnh Long gạch gốm", "OCOP Vĩnh Long 2025 2026 sản phẩm",
        "lễ hội Vĩnh Long 2026", "cù lao An Bình du lịch", "Mang Thít lò gạch gốm",
        "sinh thái Vĩnh Long sông Tiền", "homestay Vĩnh Long farmstay",
        "đình chùa cổ Vĩnh Long", "nhân vật lịch sử Vĩnh Long",
        "nông nghiệp Vĩnh Long trái cây đặc sản", "chợ nổi Vĩnh Long",
        "đờn ca tài tử Vĩnh Long", "quy hoạch du lịch Vĩnh Long",
        "Long Hồ Vĩnh Long du lịch", "Trà Ôn Vĩnh Long", "Vũng Liêm Vĩnh Long",
        "Tam Bình Vĩnh Long", "Bình Tân Vĩnh Long", "Bình Minh Vĩnh Long",
        "site:vinhlong.gov.vn du lịch", "site:baovinhlong.com.vn du lịch",
        "Vĩnh Long miệt vườn sông nước", "khách sạn nhà nghỉ Vĩnh Long",
        "chùa Tiên Châu Vĩnh Long", "Văn Thánh Miếu Vĩnh Long",
        "cù lao Mây Vĩnh Long", "tết miền Tây Vĩnh Long",
    ],
    "ben-tre": [
        "du lịch Bến Tre 2026", "ẩm thực Bến Tre xứ dừa đặc sản", "di tích lịch sử Bến Tre",
        "làng nghề Bến Tre kẹo dừa", "OCOP Bến Tre 2025 2026 sản phẩm",
        "lễ hội Bến Tre 2026 dừa", "cồn Phụng Bến Tre Đạo Dừa",
        "sinh thái Bến Tre rừng ngập mặn", "homestay Bến Tre sông nước",
        "Nguyễn Đình Chiểu Bến Tre di tích", "dừa Bến Tre chuỗi giá trị",
        "Chợ Lách Bến Tre cây giống hoa kiểng", "Ba Tri Bến Tre biển",
        "Giồng Trôm Bến Tre", "Mỏ Cày Bến Tre đặc sản", "Bình Đại Bến Tre",
        "Thạnh Phú Bến Tre rừng ngập mặn", "cacao Bến Tre", "Châu Thành Bến Tre",
        "site:bentre.gov.vn du lịch", "site:baodongkhoi.vn du lịch",
        "rừng dừa Bến Tre du lịch sinh thái", "sông Hàm Luông du lịch",
        "cồn Quy cồn Phụng cồn Ốc", "kẹo dừa Bến Tre làng nghề",
        "Đồng Khởi Bến Tre lịch sử", "bánh tráng Mỹ Lồng Bến Tre",
        "bánh phồng Sơn Đốc Bến Tre", "mắm Bến Tre đặc sản",
    ],
    "tra-vinh": [
        "du lịch Trà Vinh 2026", "ẩm thực Trà Vinh bún nước lèo", "di tích lịch sử Trà Vinh",
        "làng nghề Trà Vinh", "OCOP Trà Vinh 2025 2026 sản phẩm",
        "lễ hội Trà Vinh Ok Om Bok 2026", "chùa Khmer Trà Vinh danh sách",
        "Ao Bà Om Trà Vinh di tích", "biển Ba Động Trà Vinh du lịch",
        "văn hóa Khmer Trà Vinh phong tục", "nhạc ngũ âm Trà Vinh",
        "sân khấu Rô Băm Dù Kê Khmer", "đua ghe ngo Trà Vinh",
        "Cầu Kè Trà Vinh dừa sáp", "Duyên Hải Trà Vinh điện gió",
        "Càng Long Trà Vinh", "Trà Cú Trà Vinh", "Tiểu Cần Trà Vinh",
        "Cầu Ngang Trà Vinh", "dừa sáp Trà Vinh Cầu Kè đặc sản",
        "site:travinh.gov.vn du lịch", "site:baotravinh.vn du lịch",
        "chùa Âng Trà Vinh kiến trúc Khmer", "Trà Vinh điểm đến Khmer",
        "chùa Vàm Ray Trà Vinh", "thiền viện Trúc Lâm Trà Vinh",
        "bún suông Trà Vinh", "bánh canh Bến Có Trà Vinh",
    ],
    "lien-vung": [
        "du lịch ĐBSCL 2026 xu hướng", "liên kết du lịch miền Tây",
        "UNESCO đờn ca tài tử nam bộ", "di sản phi vật thể ĐBSCL",
        "OCOP miền Tây 2025 2026 xếp hạng", "du lịch cộng đồng ĐBSCL mô hình",
        "homestay farmstay miền Tây thành công", "biến đổi khí hậu ĐBSCL",
        "mekong delta tourism 2026 vietnam", "sustainable tourism mekong vietnam",
        "tuyến du lịch liên tỉnh miền Tây Vĩnh Long Bến Tre Trà Vinh",
        "festival mekong delta 2026",
    ],
    "academic": [
        "nghiên cứu du lịch ĐBSCL tạp chí khoa học",
        "luận văn du lịch cộng đồng Vĩnh Long Bến Tre Trà Vinh",
        "hệ sinh thái sông Mekong nghiên cứu", "văn hóa Khmer Nam Bộ nghiên cứu",
        "ẩm thực miền Tây nhân học", "làng nghề ĐBSCL bảo tồn phát triển",
        "phát triển bền vững du lịch ĐBSCL",
    ],
    "government": [
        "site:vinhlong.gov.vn quy hoạch du lịch", "site:bentre.gov.vn phát triển du lịch",
        "site:travinh.gov.vn du lịch quy hoạch",
        "Sở Văn hóa Thể thao Du lịch Vĩnh Long", "Sở Du lịch Bến Tre",
        "Sở Văn hóa Trà Vinh kế hoạch", "tổng cục du lịch ĐBSCL thống kê",
    ],
    "heritage": [
        "danh sách di tích quốc gia Vĩnh Long", "danh sách di tích quốc gia Bến Tre",
        "danh sách di tích quốc gia Trà Vinh", "di sản phi vật thể Nam Bộ",
        "bảo tàng Vĩnh Long", "bảo tàng Bến Tre Đồng Khởi", "bảo tàng Trà Vinh Khmer",
        "di tích cách mạng miền Tây ĐBSCL",
    ],
    "ecology": [
        "đa dạng sinh học ĐBSCL", "rừng ngập mặn Bến Tre Trà Vinh diện tích",
        "sân chim miền Tây danh sách", "cá đồng miền Tây mùa nước nổi",
        "xâm nhập mặn ĐBSCL 2025 2026", "động vật quý hiếm ĐBSCL",
        "vườn trái cây miền Tây Vĩnh Long Bến Tre",
    ],
}


def phase1(llm: LLM, workers: int = 6, dry: bool = False):
    """Corpus Expansion — 150+ web searches, fetch+index sources (no LLM)"""
    log("═══ PHASE 1: CORPUS EXPANSION ═══")
    d = OUTPUT_DIR / "corpus"
    f = d / "corpus.jsonl"
    d.mkdir(parents=True, exist_ok=True)

    seen = {r.get("url") for r in read_jsonl(f)}
    old = AGENT_DIR / "data" / "research_deep" / "corpus" / "full_corpus.jsonl"
    for r in read_jsonl(old):
        seen.add(r.get("url"))
    log(f"  {len(seen)} URLs already known")

    tasks = [(cat, q) for cat, qs in QUERIES.items() for q in qs]
    log(f"  {len(tasks)} queries across {len(QUERIES)} categories")

    if dry:
        for cat in QUERIES:
            log(f"    {cat}: {len(QUERIES[cat])} queries")
        return

    count = 0

    def do(item):
        nonlocal count
        cat, q = item
        results = web_search(q, n=10)
        n = 0
        for r in results:
            if r["url"] in seen:
                continue
            seen.add(r["url"])
            txt = fetch_url(r["url"], timeout=15)
            if not txt or len(txt) < 300:
                continue
            append_jsonl(f, {
                "url": r["url"], "title": r.get("title", ""),
                "snippet": r.get("snippet", ""), "text": txt,
                "text_length": len(txt), "category": cat,
                "query": q, "fetched_at": utc(),
            })
            n += 1
            with _lock:
                count += 1
        return n

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(do, t): t for t in tasks}
        for i, fut in enumerate(as_completed(futs)):
            t = futs[fut]
            try:
                n = fut.result()
                if n:
                    log(f"  [{i+1}/{len(tasks)}] '{t[1][:50]}' → +{n}")
            except Exception as ex:
                log(f"  [{i+1}] ERR: {ex}")

    log(f"  PHASE 1 DONE: +{count} new, {len(read_jsonl(f))} total")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: ADMINISTRATIVE GEOGRAPHY
# ═══════════════════════════════════════════════════════════════════════════════

DISTRICTS = {
    "vinh-long": [
        "Thành phố Vĩnh Long", "Thị xã Bình Minh", "Huyện Long Hồ", "Huyện Mang Thít",
        "Huyện Vũng Liêm", "Huyện Tam Bình", "Huyện Bình Tân", "Huyện Trà Ôn",
    ],
    "ben-tre": [
        "Thành phố Bến Tre", "Huyện Châu Thành", "Huyện Chợ Lách", "Huyện Mỏ Cày Bắc",
        "Huyện Mỏ Cày Nam", "Huyện Giồng Trôm", "Huyện Bình Đại",
        "Huyện Ba Tri", "Huyện Thạnh Phú",
    ],
    "tra-vinh": [
        "Thành phố Trà Vinh", "Thị xã Duyên Hải", "Huyện Càng Long", "Huyện Cầu Kè",
        "Huyện Tiểu Cần", "Huyện Châu Thành", "Huyện Trà Cú",
        "Huyện Duyên Hải", "Huyện Cầu Ngang",
    ],
}


def phase2(llm: LLM, workers: int = 4, dry: bool = False):
    """Administrative Geography — 26 huyện/TX/TP, web-verified"""
    log("═══ PHASE 2: ADMINISTRATIVE GEOGRAPHY ═══")
    f = OUTPUT_DIR / "geography" / "districts.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}

    tasks = []
    for area, dists in DISTRICTS.items():
        prov = PROVINCE[area]
        for d in dists:
            k = f"{area}|{d}"
            if k not in done:
                tasks.append((area, prov, d, k))

    log(f"  {len(tasks)} districts to research (done: {len(done)})")
    if dry or not tasks:
        return

    def do(item):
        area, prov, dist, k = item
        wr, ctx = web_research([
            f'"{dist}" "{prov}" danh sách xã phường thị trấn',
            f'"{dist}" {prov} hành chính dân số diện tích',
            f'"{dist}" {prov} du lịch đặc sản điểm đến',
        ], max_per=5)
        if not ctx:
            log(f"  ⚠ {dist}: no web sources")
            return
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""Nghiên cứu "{dist}" thuộc {prov}.

[NGUỒN WEB]:
{ctx}

JSON:
{{
  "district": "{dist}", "province": "{prov}",
  "type": "huyen|thi_xa|thanh_pho",
  "wards": [{{"name": "...", "level": "xa|phuong|thi_tran", "confidence": 0.9}}],
  "area_km2": {{"value": null, "confidence": 0.0, "source": null}},
  "population": {{"value": null, "year": null, "confidence": 0.0}},
  "key_features": [{{"fact": "...", "confidence": 0.9, "source": "URL"}}],
  "tourism": [{{"name": "...", "confidence": 0.9}}],
  "specialties": [{{"name": "...", "confidence": 0.9}}],
  "overall_confidence": 0.0
}}

Liệt kê TẤT CẢ xã/phường. Không biết đầy đủ → confidence thấp.""",
            temp=0.1, max_tok=6000)
        if r:
            r["key"] = k; r["area"] = area
            r["sources"] = src_list(wr); r["n_sources"] = len(wr)
            r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ {dist}: {len(r.get('wards',[]))} wards, conf={r.get('overall_confidence','?')}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do, t) for t in tasks]):
            try:
                fut.result()
            except Exception as ex:
                log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: OCOP
# ═══════════════════════════════════════════════════════════════════════════════

def phase3(llm: LLM, workers: int = 4, dry: bool = False):
    """OCOP Catalog — discover + deep-research per product"""
    log("═══ PHASE 3: OCOP CATALOG ═══")
    disc_f = OUTPUT_DIR / "ocop" / "discovery.jsonl"
    prod_f = OUTPUT_DIR / "ocop" / "products.jsonl"
    done_d = {r.get("area") for r in read_jsonl(disc_f)}
    done_p = {r.get("key") for r in read_jsonl(prod_f)}

    if dry:
        log("  [DRY] 3 provinces × discovery + per-product deep research")
        return

    for area, prov in PROVINCE.items():
        if area in done_d:
            log(f"  {prov}: already discovered")
            continue
        log(f"  Discovering OCOP {prov}...")
        wr, ctx = web_research([
            f"danh sách sản phẩm OCOP {prov} 2024 2025 2026",
            f"sản phẩm OCOP {prov} 3 sao 4 sao 5 sao",
            f"OCOP {prov} chủ thể sản phẩm danh mục",
            f'"{prov}" OCOP công nhận',
        ], max_per=10)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""Liệt kê sản phẩm OCOP được công nhận tại {prov}.
[NGUỒN WEB]: {ctx}
JSON:
{{
  "province": "{prov}",
  "products": [
    {{"name": "tên chính xác", "stars": 3,
      "category": "thực phẩm|đồ uống|thảo dược|thủ công|du lịch",
      "producer": "chủ thể (nếu có)", "district": "huyện (nếu có)",
      "confidence": 0.9, "source_url": "URL"}}
  ],
  "total_note": "ghi chú tổng số nếu nguồn đề cập"
}}
CHỈ liệt kê sản phẩm có trong nguồn web.""", temp=0.1, max_tok=8000)
        if r:
            r["area"] = area; r["sources"] = src_list(wr); r["ts"] = utc()
            append_jsonl(disc_f, r)
            prods = r.get("products", [])
            log(f"  ✓ {prov}: {len(prods)} OCOP products found")

            for p in prods:
                pk = f"{area}|{p.get('name','')}"
                if pk in done_p or not p.get("name"):
                    continue
                pn = p["name"]
                pr, pc = web_research([f'"{pn}" {prov} OCOP', f'"{pn}" đặc sản'], max_per=5)
                det = llm.ask_json(sys=SYS_ACCURACY, user=f"""Sản phẩm OCOP: "{pn}" ({p.get('stars',3)} sao) — {prov}
[NGUỒN WEB]: {pc[:5000]}
JSON (null cho thông tin không có):
{{
  "name": "{pn}",
  "description": "100-200 từ từ nguồn",
  "origin": {{"text": null, "confidence": 0.0, "source": null}},
  "process": {{"text": null, "confidence": 0.0}},
  "materials": ["nguyên liệu"],
  "taste": null,
  "price": {{"text": null, "confidence": 0.0}},
  "where_buy": [],
  "overall_confidence": 0.0
}}""", temp=0.1, max_tok=3000)
                if det:
                    det["key"] = pk; det["area"] = area; det["stars"] = p.get("stars", 3)
                    det["sources"] = src_list(pr); det["ts"] = utc()
                    append_jsonl(prod_f, det)
                    done_p.add(pk)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASES 4–8: Entity-centric research (generic engine)
# ═══════════════════════════════════════════════════════════════════════════════

def _entity_research(llm: LLM, types: list[str], label: str,
                     subdir: str, fname: str,
                     q_fn, prompt_fn,
                     workers: int = 4, dry: bool = False,
                     topics: list[tuple] | None = None):
    """Generic: web-search → LLM analyze per entity."""
    log(f"═══ {label} ═══")
    out = OUTPUT_DIR / subdir
    ef = out / fname
    done = {r.get("entity_id") for r in read_jsonl(ef)}

    ents = [e for e in load_entities() if e.get("type") in types and e["id"] not in done]
    log(f"  {len(ents)} entities to research (done: {len(done)})")
    if dry:
        return

    if topics:
        tf = out / "topics.jsonl"
        td = {r.get("key") for r in read_jsonl(tf)}
        for tk, tq, tp in topics:
            if tk in td:
                continue
            log(f"  Topic: {tk}...")
            wr, ctx = web_research(tq, max_per=8)
            if not ctx:
                continue
            r = llm.ask_json(sys=SYS_ACCURACY, user=tp.replace("{web_context}", ctx),
                             temp=0.1, max_tok=6000)
            if r:
                r["key"] = tk; r["sources"] = src_list(wr); r["ts"] = utc()
                append_jsonl(tf, r)

    def do(e):
        if e["id"] in done:
            return
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        qs = q_fn(e["name"], prov, e)
        wr, ctx = web_research(qs, max_per=5)
        if not ctx:
            ctx = "(Không tìm thấy nguồn web — confidence thấp)"
        pr = prompt_fn(e["name"], prov, e, ctx)
        r = llm.ask_json(sys=SYS_ACCURACY, user=pr, temp=0.15, max_tok=4000)
        if r:
            r["entity_id"] = e["id"]; r["entity_name"] = e["name"]
            r["entity_type"] = e.get("type", ""); r["area"] = e.get("area", "")
            r["sources"] = src_list(wr); r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(ef, r)
            done.add(e["id"])
            log(f"  ✓ {e['name']} [{len(wr)} src, conf={r.get('overall_confidence','?')}]")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(do, e) for e in ents]
        for i, fut in enumerate(as_completed(futs)):
            try:
                fut.result()
                if (i+1) % 20 == 0:
                    log(f"  {i+1}/{len(ents)}")
            except Exception as ex:
                log(f"  ERR: {ex}")


def phase4(llm: LLM, workers: int = 4, dry: bool = False):
    """Heritage & History — timelines + di tích + web sources"""
    tl = []
    for a, p in PROVINCE.items():
        tl.append((
            f"timeline_{a}",
            [f"lịch sử {p} từ thời khai hoang", f"sự kiện lịch sử {p}",
             f"di tích quốc gia {p} danh sách đầy đủ"],
            f"""Timeline lịch sử {p}. [NGUỒN WEB]: {{web_context}}
JSON:
{{"province":"{p}","timeline":[{{"period":"...","events":[{{"event":"...","confidence":0.9,"source":"URL"}}]}}],
"heritage_sites":[{{"name":"...","year":null,"level":"quốc_gia|tỉnh","confidence":0.9,"source":"URL"}}],
"overall_confidence":0.0}}"""
        ))
    _entity_research(llm, ["history"], "PHASE 4: HERITAGE & HISTORY",
        "heritage", "sites.jsonl",
        q_fn=lambda n, p, e: [f'"{n}" {p}', f'"{n}" di tích lịch sử', f'"{n}" kiến trúc'],
        prompt_fn=lambda n, p, e, c: f""""{n}" ({p}). Summary: {e.get('summary','')[:400]}
[NGUỒN WEB]: {c}
JSON:
{{"name":"{n}","heritage_type":"đình|chùa|miếu|di_tích|bảo_tàng|khác",
"level":{{"value":null,"confidence":0.0,"source":null}},
"year":{{"value":null,"confidence":0.0}},
"history":{{"text":"100-200 từ","confidence":0.0}},
"architecture":{{"text":null,"confidence":0.0}},
"significance":"ý nghĩa",
"events":[{{"name":"...","date":"...","confidence":0.0}}],
"visitor":{{"hours":null,"fee":null,"duration_min":null,"best_time":null}},
"overall_confidence":0.0}}
Không bịa. Không có → null.""",
        workers=workers, dry=dry, topics=tl)


def phase5(llm: LLM, workers: int = 4, dry: bool = False):
    """Ecology & Nature — hệ sinh thái + species + web"""
    topics = [
        ("wetlands", ["hệ sinh thái đất ngập nước ĐBSCL", "wetland Mekong Delta"],
         """Hệ sinh thái đất ngập nước 3 tỉnh VL-BT-TV. [NGUỒN WEB]: {{web_context}}
JSON:{{"topic":"wetlands","overview":{{"text":"...","confidence":0.0}},
"habitats":[{{"name":"...","location":"...","ha":null,"confidence":0.0,"source":null}}],
"species":[{{"name":"...","status":"...","confidence":0.0}}],
"threats":["..."],"overall_confidence":0.0}}"""),
        ("mangroves", ["rừng ngập mặn Bến Tre Trà Vinh bảo tồn", "mangrove Ben Tre Tra Vinh"],
         """Rừng ngập mặn BT-TV. [NGUỒN WEB]: {{web_context}}
JSON:{{"topic":"mangroves","areas":[{{"name":"...","province":"...","ha":null,"confidence":0.0,"source":null}}],
"biodiversity":["..."],"ecotourism":[{{"activity":"...","confidence":0.0}}],"overall_confidence":0.0}}"""),
        ("birds", ["sân chim Vĩnh Long Bến Tre Trà Vinh", "bird sanctuary Mekong Delta"],
         """Sân chim 3 tỉnh. [NGUỒN WEB]: {{web_context}}
JSON:{{"topic":"birds","sites":[{{"name":"...","location":"...","species_count":null,
"notable":["..."],"best_months":"...","confidence":0.0,"source":null}}],"overall_confidence":0.0}}"""),
        ("fruit_calendar", ["trái cây miền Tây theo tháng mùa", "seasonal fruit Mekong Delta"],
         """Lịch trái cây theo tháng. [NGUỒN WEB]: {{web_context}}
JSON:{{"topic":"fruit_calendar","fruits":[{{"name":"...","peak_months":"...","province":"...","confidence":0.0}}],
"overall_confidence":0.0}}"""),
        ("climate", ["biến đổi khí hậu xâm nhập mặn ĐBSCL 2025 2026", "climate change Mekong Delta"],
         """Tác động BĐKH lên 3 tỉnh. [NGUỒN WEB]: {{web_context}}
JSON:{{"topic":"climate","sea_level":{{"data":null,"confidence":0.0}},
"saltwater":{{"areas":["..."],"confidence":0.0}},
"tourism_impact":{{"text":"...","confidence":0.0}},"overall_confidence":0.0}}"""),
    ]
    _entity_research(llm, ["nature"], "PHASE 5: ECOLOGY",
        "ecology", "nature.jsonl",
        q_fn=lambda n, p, e: [f'"{n}" {p} sinh thái', f'"{n}" du lịch'],
        prompt_fn=lambda n, p, e, c: f""""{n}" ({p}). Summary: {e.get('summary','')[:300]}
[NGUỒN WEB]: {c}
JSON:
{{"name":"{n}","ecosystem_type":null,
"biodiversity":{{"species":["..."],"confidence":0.0}},
"seasonal":[{{"months":"...","what":"...","confidence":0.0}}],
"visitor":{{"best_months":null,"duration":null,"fee":null}},
"overall_confidence":0.0}}""",
        workers=workers, dry=dry, topics=topics)


def phase6(llm: LLM, workers: int = 4, dry: bool = False):
    """Gastronomy — ẩm thực + web research per dish"""
    _entity_research(llm, ["dish", "drink"], "PHASE 6: GASTRONOMY",
        "gastronomy", "dishes.jsonl",
        q_fn=lambda n, p, e: [f'"{n}" {p} đặc sản', f'"{n}" công thức nguyên liệu',
                               f'"{n}" ẩm thực miền Tây'],
        prompt_fn=lambda n, p, e, c: f"""Ẩm thực: "{n}" ({p}). Summary: {e.get('summary','')[:300]}
[NGUỒN WEB]: {c}
JSON:
{{"name":"{n}","category":"món_mặn|món_ngọt|bánh|nước|gia_vị|mắm|khô|khác",
"origin":{{"text":null,"confidence":0.0,"source":null}},
"ethnic":"Việt|Khmer|Hoa|pha_trộn|chưa_rõ",
"ingredients":[{{"name":"...","role":"...","confidence":0.0}}],
"preparation":{{"text":null,"confidence":0.0}},
"taste":{{"primary":null,"texture":null,"aroma":null}},
"where_eat":[{{"place":"...","confidence":0.0,"source":null}}],
"price":null,
"cultural_context":null,
"overall_confidence":0.0}}
KHÔNG bịa nguyên liệu. Không có → null.""",
        workers=workers, dry=dry)


def phase7(llm: LLM, workers: int = 4, dry: bool = False):
    """Craft Villages — làng nghề + web research"""
    _entity_research(llm, ["craft_village"], "PHASE 7: CRAFT VILLAGES",
        "craft_villages", "villages.jsonl",
        q_fn=lambda n, p, e: [f'"{n}" {p} làng nghề', f'"{n}" nghề truyền thống',
                               f'"{n}" du lịch trải nghiệm'],
        prompt_fn=lambda n, p, e, c: f"""Làng nghề: "{n}" ({p}). Summary: {e.get('summary','')[:300]}
[NGUỒN WEB]: {c}
JSON:
{{"name":"{n}","craft_type":null,
"history":{{"text":null,"confidence":0.0,"source":null}},
"process":[{{"step":"...","tourist_try":null,"confidence":0.0}}],
"products":[{{"name":"...","price":null,"confidence":0.0}}],
"artisans":{{"households":null,"notable":[],"confidence":0.0}},
"tourism":{{"activities":["..."],"duration":null,"cost":null,"confidence":0.0}},
"overall_confidence":0.0}}""",
        workers=workers, dry=dry)


def phase8(llm: LLM, workers: int = 4, dry: bool = False):
    """Festivals & Events — lễ hội + web verified"""
    topics = []
    for a, p in PROVINCE.items():
        topics.append((
            f"fest_{a}",
            [f"lễ hội {p} 2026 danh sách", f"sự kiện văn hóa {p} 2026",
             f"lễ hội truyền thống {p}"],
            f"""TẤT CẢ lễ hội tại {p}. [NGUỒN WEB]: {{web_context}}
JSON:
{{"province":"{p}","events":[
  {{"name":"...","type":"le_hoi|hoi_cho|ton_giao|the_thao|am_thuc",
    "timing":{{"lunar":null,"solar":"...","days":null}},
    "location":"...","district":"...","description":"...",
    "confidence":0.9,"source":"URL"}}
],"overall_confidence":0.0}}"""
        ))
    _entity_research(llm, ["event"], "PHASE 8: FESTIVALS",
        "festivals", "events.jsonl",
        q_fn=lambda n, p, e: [f'"{n}" {p} lễ hội', f'"{n}" 2026'],
        prompt_fn=lambda n, p, e, c: f""""{n}" ({p}). Summary: {e.get('summary','')[:300]}
[NGUỒN WEB]: {c}
JSON:
{{"name":"{n}","description":{{"text":null,"confidence":0.0}},
"origin":{{"text":null,"confidence":0.0,"source":null}},
"timing":{{"lunar":null,"solar":null,"confidence":0.0}},
"rituals":[{{"name":"...","desc":"...","confidence":0.0}}],
"activities":["..."],
"scale":"địa_phương|tỉnh|vùng|quốc_gia",
"tips":["..."],
"overall_confidence":0.0}}""",
        workers=workers, dry=dry, topics=topics)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 9: ENTITY ENRICHMENT (all remaining)
# ═══════════════════════════════════════════════════════════════════════════════

TYPE_SEARCH = {
    "place": lambda n, p: [f'"{n}" {p} du lịch', f'"{n}" địa điểm'],
    "attraction": lambda n, p: [f'"{n}" {p} tham quan', f'"{n}" đánh giá'],
    "accommodation": lambda n, p: [f'"{n}" {p} khách sạn homestay', f'"{n}" đánh giá giá phòng'],
    "product": lambda n, p: [f'"{n}" {p} sản phẩm đặc sản', f'"{n}" mua ở đâu'],
    "person": lambda n, p: [f'"{n}" {p} nhân vật', f'"{n}" tiểu sử'],
    "organization": lambda n, p: [f'"{n}" {p}', f'"{n}" hoạt động'],
    "experience": lambda n, p: [f'"{n}" {p} trải nghiệm du lịch', f'"{n}" tour'],
}


def phase9(llm: LLM, workers: int = 4, dry: bool = False):
    """Entity Enrichment — ALL remaining entities + web context"""
    log("═══ PHASE 9: ENTITY ENRICHMENT ═══")
    ef = OUTPUT_DIR / "enrichment" / "enrichment.jsonl"
    done = set()
    for sd in ["heritage", "ecology", "gastronomy", "craft_villages", "festivals"]:
        for ff in (OUTPUT_DIR / sd).glob("*.jsonl"):
            for r in read_jsonl(ff):
                if r.get("entity_id"):
                    done.add(r["entity_id"])
    old = AGENT_DIR / "data" / "enrichment"
    if old.exists():
        for ff in old.glob("*.jsonl"):
            for r in read_jsonl(ff):
                done.add(r.get("entity_id"))
    for r in read_jsonl(ef):
        done.add(r.get("entity_id"))

    ents = [e for e in load_entities() if e["id"] not in done]
    log(f"  {len(ents)} remaining (done: {len(done)})")
    if dry:
        for t, c in Counter(e.get("type") for e in ents).most_common():
            log(f"    {t}: {c}")
        return

    def do(e):
        if e["id"] in done:
            return
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        tp = e.get("type", "")
        q_fn = TYPE_SEARCH.get(tp, lambda n, p: [f'"{n}" {p}'])
        wr, ctx = web_research(q_fn(e["name"], prov), max_per=5)
        if not ctx:
            ctx = "(Không có nguồn web)"
        r = llm.ask_json(sys=SYS_ACCURACY, user=f""""{e['name']}" (loại: {tp}, vùng: {prov})
Summary: {e.get('summary','')[:400]}
[NGUỒN WEB]: {ctx}
JSON:
{{"description":{{"text":"100-200 từ","confidence":0.0}},
"tips":[{{"tip":"...","confidence":0.0}}],
"best_time":null,"tags":["..."],"seo_keywords":["..."],
"emotional_hook":null,
"highlights":[{{"text":"...","confidence":0.0,"source":null}}],
"price":null,"hours":null,"contact":null,
"overall_confidence":0.0}}""", temp=0.15, max_tok=3000)
        if r:
            rec = {"entity_id": e["id"], "entity_name": e["name"],
                   "entity_type": tp, "area": e.get("area", ""),
                   "enrichment": r, "sources": src_list(wr),
                   "n_sources": len(wr), "ts": utc(), "model": llm.model}
            append_jsonl(ef, rec)
            done.add(e["id"])

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(do, e) for e in ents]
        for i, fut in enumerate(as_completed(futs)):
            try:
                fut.result()
                if (i+1) % 50 == 0:
                    log(f"  {i+1}/{len(ents)}")
            except Exception as ex:
                log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 10: PLACEID & COORDS
# ═══════════════════════════════════════════════════════════════════════════════

def phase10(llm: LLM, workers: int = 4, dry: bool = False):
    """PlaceId & Coordinates — xã/phường mapping + coords"""
    log("═══ PHASE 10: PLACEID & COORDS ═══")
    gf = OUTPUT_DIR / "geo_mapping" / "placeid.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(gf)}

    ents = [e for e in load_entities() if not e.get("placeId") and e["id"] not in done]
    log(f"  {len(ents)} need placeId (done: {len(done)})")
    if dry:
        return

    geo = read_jsonl(OUTPUT_DIR / "geography" / "districts.jsonl")
    wards = []
    for d in geo:
        for w in d.get("wards", []):
            wn = w.get("name", "") if isinstance(w, dict) else str(w)
            wards.append({"name": wn, "district": d.get("district", ""), "area": d.get("area", "")})
    ward_str = json.dumps([w["name"] for w in wards[:200]], ensure_ascii=False)[:3000]

    def do(e):
        if e["id"] in done:
            return
        prov = PROVINCE.get(e.get("area", ""), "")
        wr, ctx = web_research([f'"{e["name"]}" {prov} địa chỉ xã phường'], max_per=3)
        r = llm.ask_json(
            sys="Chuyên gia địa lý hành chính miền Tây. CHỈ gán xã/phường nếu CHẮC CHẮN.",
            user=f""""{e['name']}" (loại: {e.get('type')}, vùng: {e.get('area')})
Summary: {e.get('summary','')[:300]}
Web: {ctx[:3000]}
Xã/phường: {ward_str}
JSON:
{{"placeId":"slug hoặc null","ward":null,"district":null,
"reasoning":"...","confidence":0.0,"source":null,
"coords":{{"lat":null,"lng":null,"confidence":0.0}}}}
CHỈ gán nếu confidence >= 0.7.""", temp=0.1, max_tok=1500)
        if r:
            r["entity_id"] = e["id"]; r["entity_name"] = e["name"]; r["ts"] = utc()
            append_jsonl(gf, r)
            done.add(e["id"])

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, fut in enumerate(as_completed([pool.submit(do, e) for e in ents])):
            try:
                fut.result()
                if (i+1) % 50 == 0:
                    log(f"  {i+1}/{len(ents)}")
            except Exception as ex:
                log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 11: CROSS-ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

THEMES = [
    ("heritage_trail", "Con đường di sản"), ("food_odyssey", "Hành trình ẩm thực"),
    ("coconut_kingdom", "Vương quốc dừa Bến Tre"), ("khmer_culture", "Khám phá văn hóa Khmer"),
    ("river_life", "Đời sống sông nước"), ("craft_discovery", "Khám phá làng nghề"),
    ("nature_immersion", "Hòa mình thiên nhiên"), ("family_fun", "Gia đình vui miền Tây"),
    ("budget_trip", "Phượt tiết kiệm dưới 500k/ngày"), ("photography", "Nhiếp ảnh miền Tây"),
]


def phase11(llm: LLM, workers: int = 4, dry: bool = False):
    """Cross-Analysis — journeys, personas, relationships"""
    log("═══ PHASE 11: CROSS-ANALYSIS ═══")
    cd = OUTPUT_DIR / "cross"
    jf = cd / "journeys.jsonl"
    pf = cd / "personas.jsonl"
    rf = cd / "relationships.jsonl"

    ents = load_entities()
    if dry:
        log(f"  [DRY] journeys + personas + relationships for {len(ents)} entities")
        return

    dj = {r.get("key") for r in read_jsonl(jf)}
    sample = [{"id": e["id"], "name": e["name"], "type": e.get("type"),
               "area": e.get("area"), "s": (e.get("summary") or "")[:60]}
              for e in ents if e.get("area")][:50]
    sample_s = json.dumps(sample, ensure_ascii=False)[:5000]

    for tk, tn in THEMES:
        if tk in dj:
            continue
        log(f"  Journey: {tn}...")
        r = llm.ask_json(sys="Thiết kế trải nghiệm du lịch. Chỉ dùng entity trong danh sách.",
            user=f"""Hành trình "{tn}" xuyên VL-BT-TV.
Entities: {sample_s}
JSON:
{{"theme":"{tk}","title":"{tn}","tagline":"dưới 15 từ",
"duration_days":3,"budget":"khoảng/người","best_months":"...",
"itinerary":[{{"day":1,"title":"...","province":"...","stops":[
  {{"entity_id":"ID","entity_name":"tên","time":"08:00","activity":"...","tips":"..."}}
]}}],
"packing":["..."],"insider_tips":["..."]}}
CHỈ dùng entity_id có trong danh sách.""", temp=0.25, max_tok=5000)
        if r:
            r["key"] = tk; r["ts"] = utc()
            append_jsonl(jf, r)

    if not read_jsonl(pf):
        log("  Personas...")
        wr, ctx = web_research(["du khách miền Tây ĐBSCL thống kê", "khách du lịch Vĩnh Long Bến Tre Trà Vinh"],
                               max_per=5)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""8 visitor personas cho VL+BT+TV.
[NGUỒN WEB]: {ctx[:4000]}
JSON:
{{"personas":[{{"id":"...","name":"...","age":"25-35","origin":"TP.HCM",
"style":"phượt|gia_đình|sang|văn_hóa|ẩm_thực|eco",
"budget_day":"200-500k","duration":"2-3 ngày",
"motivations":["..."],"pain_points":["..."],
"ideal_types":["attraction","dish"],"confidence":0.0}}],
"overall_confidence":0.0}}""", temp=0.2, max_tok=5000)
        if r:
            r["sources"] = src_list(wr); r["ts"] = utc()
            append_jsonl(pf, r)

    dr = {r.get("key") for r in read_jsonl(rf)}
    for area in PROVINCE:
        rk = f"rels_{area}"
        if rk in dr:
            continue
        log(f"  Relationships: {area}...")
        ae = [{"id": e["id"], "name": e["name"], "type": e.get("type"),
               "s": (e.get("summary") or "")[:50]}
              for e in ents if e.get("area") == area][:50]
        r = llm.ask_json(sys="Phân tích quan hệ entity du lịch. CHỈ quan hệ chắc chắn.",
            user=f"""Quan hệ giữa entities ở {area}:
{json.dumps(ae, ensure_ascii=False)[:5000]}
JSON:
{{"relationships":[{{"from":"id1","to":"id2",
"type":"near|related_to|part_of|produced_in|associated_with",
"reason":"...","confidence":0.0}}]}}
CHỈ confidence >= 0.7.""", temp=0.15, max_tok=5000)
        if r:
            r["key"] = rk; r["area"] = area; r["ts"] = utc()
            append_jsonl(rf, r)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 12: ADVERSARIAL VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def phase12(llm: LLM, workers: int = 4, dry: bool = False):
    """Adversarial Verify — independent fact-check sampled claims"""
    log("═══ PHASE 12: ADVERSARIAL VERIFICATION ═══")
    vf = OUTPUT_DIR / "verify" / "verdicts.jsonl"
    done = {r.get("key") for r in read_jsonl(vf)}

    claims = []
    for sd in ["heritage", "ecology", "gastronomy", "craft_villages", "festivals",
               "ocop", "geography", "enrichment"]:
        d = OUTPUT_DIR / sd
        if not d.exists():
            continue
        for ff in d.glob("*.jsonl"):
            for rec in read_jsonl(ff):
                eid = rec.get("entity_id") or rec.get("key") or ""
                def _ex(obj, pfx=""):
                    if isinstance(obj, dict):
                        txt = obj.get("text") or obj.get("description") or obj.get("value")
                        conf = obj.get("confidence", 0)
                        if txt and isinstance(txt, str) and len(txt) > 20 and conf and conf >= 0.7:
                            ck = f"{eid}|{pfx}|{txt[:50]}"
                            if ck not in done:
                                claims.append({"key": ck, "eid": eid, "text": txt[:500],
                                               "conf": conf, "phase": sd})
                        for k, v in obj.items():
                            _ex(v, f"{pfx}.{k}")
                    elif isinstance(obj, list):
                        for i, it in enumerate(obj):
                            _ex(it, f"{pfx}[{i}]")
                _ex(rec)

    log(f"  {len(claims)} high-confidence claims (done: {len(done)})")
    if dry or not claims:
        return

    random.seed(42)
    if len(claims) > 500:
        claims = random.sample(claims, 500)
        log(f"  Sampled 500")

    def do(c):
        if c["key"] in done:
            return
        wr, ctx = web_research([c["text"][:100]], max_per=5)
        r = llm.ask_json(sys=SYS_VERIFY, user=f"""Claim: {c['text']}
Stated confidence: {c['conf']}  Phase: {c['phase']}
[NGUỒN WEB ĐỘC LẬP]: {ctx[:5000]}
JSON:
{{"verdict":"CONFIRMED|PLAUSIBLE|UNVERIFIED|REFUTED",
"evidence":"...","source":null,"adjusted_confidence":0.0,"notes":""}}""",
            temp=0.1, max_tok=1500)
        if r:
            r["key"] = c["key"]; r["eid"] = c["eid"]
            r["claim"] = c["text"][:200]; r["phase"] = c["phase"]
            r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(vf, r)
            done.add(c["key"])

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, fut in enumerate(as_completed([pool.submit(do, c) for c in claims])):
            try:
                fut.result()
                if (i+1) % 50 == 0:
                    log(f"  {i+1}/{len(claims)}")
            except Exception as ex:
                log(f"  ERR: {ex}")

    vs = read_jsonl(vf)
    ct = Counter(v.get("verdict") for v in vs)
    log(f"  SUMMARY: {dict(ct)}")
    total = len(vs)
    if total:
        ok = ct.get("CONFIRMED", 0) + ct.get("PLAUSIBLE", 0)
        log(f"  Accuracy: {ok}/{total} = {ok/total*100:.1f}%")


# ═══════════════════════════════════════════════════════════════════════════════
# STATS & MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def show_stats():
    log("═══ MEGA RESEARCH v3 — STATS ═══")
    items = [
        ("1  Corpus", "corpus/corpus.jsonl"),
        ("2  Geography", "geography/districts.jsonl"),
        ("3  OCOP Discovery", "ocop/discovery.jsonl"),
        ("3  OCOP Products", "ocop/products.jsonl"),
        ("4  Heritage", "heritage/sites.jsonl"),
        ("4  Heritage Topics", "heritage/topics.jsonl"),
        ("5  Ecology", "ecology/nature.jsonl"),
        ("5  Ecology Topics", "ecology/topics.jsonl"),
        ("6  Gastronomy", "gastronomy/dishes.jsonl"),
        ("7  Craft Villages", "craft_villages/villages.jsonl"),
        ("8  Festivals", "festivals/events.jsonl"),
        ("8  Festival Topics", "festivals/topics.jsonl"),
        ("9  Enrichment", "enrichment/enrichment.jsonl"),
        ("10 PlaceId", "geo_mapping/placeid.jsonl"),
        ("11 Journeys", "cross/journeys.jsonl"),
        ("11 Personas", "cross/personas.jsonl"),
        ("11 Relationships", "cross/relationships.jsonl"),
        ("12 Verification", "verify/verdicts.jsonl"),
    ]
    tr = ts_ = 0
    for lbl, rel in items:
        p = OUTPUT_DIR / rel
        if p.exists():
            recs = read_jsonl(p)
            sz = p.stat().st_size
            tr += len(recs); ts_ += sz
            confs = [r.get("overall_confidence") for r in recs if r.get("overall_confidence") is not None]
            cs = f"  avg_conf={sum(confs)/len(confs):.2f}" if confs else ""
            log(f"  {lbl:25s} {len(recs):>5} records  {sz/1024:>8.1f} KB{cs}")
        else:
            log(f"  {lbl:25s}     — not started")

    vf = OUTPUT_DIR / "verify" / "verdicts.jsonl"
    if vf.exists():
        vs = read_jsonl(vf)
        ct = Counter(v.get("verdict") for v in vs)
        total = len(vs)
        ok = ct.get("CONFIRMED", 0) + ct.get("PLAUSIBLE", 0)
        log(f"\n  Verification: {dict(ct)}")
        if total:
            log(f"  Accuracy: {ok}/{total} = {ok/total*100:.1f}%")

    log(f"\n  {'TOTAL':25s} {tr:>5} records  {ts_/1024:>8.1f} KB")


PHASES = {
    1: phase1, 2: phase2, 3: phase3, 4: phase4, 5: phase5,
    6: phase6, 7: phase7, 8: phase8, 9: phase9, 10: phase10,
    11: phase11, 12: phase12,
}


def main():
    _cfg_io()
    ap = argparse.ArgumentParser(description="Mega Research v3")
    ap.add_argument("--phase", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()

    if a.stats:
        show_stats(); return

    if not a.phase and not a.all:
        ap.print_help()
        print("\n12 Phases:")
        for i in range(1, 13):
            fn = PHASES[i]
            print(f"  {i:2d}: {fn.__doc__ or fn.__name__}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    llm = LLM()
    if not llm.ok:
        log("ERROR: LLM not configured (LLM_API_KEY + LLM_BASE_URL)")
        return

    t0 = time.time()
    log(f"Model: {llm.model}  Workers: {a.workers}  Output: {OUTPUT_DIR}")

    for p in (range(1, 13) if a.all else [a.phase]):
        if p in PHASES:
            PHASES[p](llm, workers=a.workers, dry=a.dry)
            log(f"  LLM: {llm.info()}")

    el = time.time() - t0
    log(f"\n═══ DONE ({el/3600:.1f}h) ═══")
    log(f"  LLM: {llm.info()}")
    show_stats()


if __name__ == "__main__":
    main()

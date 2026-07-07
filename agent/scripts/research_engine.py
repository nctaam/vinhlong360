#!/usr/bin/env python3
"""ULTRA-Depth Parallel Research Engine for vinhlong360.

Architecture (~7,000-8,000 calls, ~20h):
  Pha 0:  Fetch ALL 259 sources → indexed corpus
  Pha 1:  15 dimensions × 10 layers per sub-topic — PARALLEL themes + sub-topics
          L1 Survey → L2 Extract → L3 Multi-Perspective → L4 Adversarial (5 skeptics)
          → L5 Academic → L6 Gap-Until-Dry (5 rounds) → L7 Contradiction
          → L8 Temporal → L9 Counter-Narrative → L10 Synthesis
  Pha 1b: Cross-pollination — themes feed back into each other
  Pha 2:  62 assets × 7 angles + adversarial + synthesis — PARALLEL assets
  Pha 3:  ALL 105 dimension pairs (parallel) + calendar + products + counter

Usage:
  python -u agent/scripts/research_engine.py --full --workers 8 --concurrent 4
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
SOURCES_CSV = PROJECT_DIR / "nghien_cuu_12_chieu_thu_muc_nguon_mo_rong.csv"
ASSETS_CSV = PROJECT_DIR / "nghien_cuu_12_chieu_catalog_62_tai_nguyen.csv"
OUTPUT_DIR = AGENT_DIR / "data" / "research_deep"

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
    import requests as req_lib
except ImportError:
    req_lib = None

DEFAULT_MODEL = os.environ.get("LLM_MODEL") or "cx/gpt-5.5"
_write_lock = threading.Lock()


def configure_io():
    os.environ["PYTHONUNBUFFERED"] = "1"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def compact(text: Any, limit: int = 8000) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]


def is_http_url(url: Any) -> bool:
    if not isinstance(url, str) or not url.strip():
        return False
    p = urlparse(url.strip())
    return p.scheme in {"http", "https"} and bool(p.netloc)


def parse_llm_json(text: str) -> Any:
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


def append_jsonl(path: Path, record: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with _write_lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
    return records


def get_done_layers(result_file: Path) -> set[str]:
    done = set()
    for rec in read_jsonl(result_file):
        st = rec.get("sub_topic", "")
        layer = rec.get("layer", rec.get("pass", ""))
        if st and layer:
            done.add(f"{st}|{layer}")
    return done


def tprint(msg: str):
    """Thread-safe print with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ─── Global Rate Limiter (token bucket) ──────────────────────────────────────


class RateLimiter:
    """Thread-safe token bucket — limits requests/sec across all threads."""
    def __init__(self, rps: float = 2.0):
        self._lock = threading.Lock()
        self._tokens = rps
        self._max = rps
        self._last = time.monotonic()
        self._rps = rps
        self._global_pause_until = 0.0

    def set_rps(self, rps: float):
        with self._lock:
            self._rps = rps
            self._max = rps

    def global_pause(self, seconds: float):
        with self._lock:
            until = time.monotonic() + seconds
            if until > self._global_pause_until:
                self._global_pause_until = until

    def acquire(self):
        while True:
            with self._lock:
                now = time.monotonic()
                if now < self._global_pause_until:
                    wait = self._global_pause_until - now
                    self._lock.release()
                    time.sleep(wait)
                    self._lock.acquire()
                    now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(self._max, self._tokens + elapsed * self._rps)
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            time.sleep(0.1 + random.uniform(0, 0.1))


_rate_limiter = RateLimiter(rps=2.0)


# ─── LLM Client (thread-safe, rate-limited, exponential backoff) ─────────────


class LLMClient:
    def __init__(self, model: str = DEFAULT_MODEL, rps: float = 2.0):
        self.model = model
        self.api_key = os.environ.get("LLM_API_KEY", "")
        self.base_url = os.environ.get("LLM_BASE_URL", "")
        self._lock = threading.Lock()
        self._client = None
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.errors = 0
        self.retries_total = 0
        self.rate_limit_hits = 0
        self.auth_errors = 0
        _rate_limiter.set_rps(rps)

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.base_url and OpenAI)

    def _get_client(self):
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def _reset_client(self):
        self._client = None

    def _inc(self, calls=0, pt=0, ct=0, err=0, retry=0, rl=0, auth=0):
        with self._lock:
            self.calls += calls
            self.prompt_tokens += pt
            self.completion_tokens += ct
            self.errors += err
            self.retries_total += retry
            self.rate_limit_hits += rl
            self.auth_errors += auth

    def _is_rate_limit(self, exc: Exception) -> bool:
        s = str(exc).lower()
        return "429" in s or "rate" in s or "too many" in s or "quota" in s

    def _is_auth_error(self, exc: Exception) -> bool:
        s = str(exc).lower()
        return "401" in s or "unauthorized" in s or "invalid" in s and "key" in s

    def complete(self, *, system: str, user: str, temperature: float = 0.15,
                 max_tokens: int = 4000, timeout: int = 300, retries: int = 5) -> str | None:
        if not self.available:
            return None

        for attempt in range(retries + 1):
            _rate_limiter.acquire()
            try:
                client = self._get_client()
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=temperature, max_tokens=max_tokens, timeout=timeout,
                )
                usage = getattr(resp, "usage", None)
                pt = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
                ct = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
                self._inc(calls=1, pt=pt, ct=ct)
                return resp.choices[0].message.content or ""
            except Exception as exc:
                is_rl = self._is_rate_limit(exc)
                is_auth = self._is_auth_error(exc)
                self._inc(err=1, rl=int(is_rl), auth=int(is_auth))

                if attempt < retries:
                    if is_rl:
                        base = min(30 * (2 ** attempt), 300)
                        jitter = random.uniform(0, base * 0.3)
                        wait = base + jitter
                        _rate_limiter.global_pause(wait * 0.5)
                        tprint(f"  [429 RATE-LIMIT {attempt+1}/{retries}] backoff {wait:.0f}s — {str(exc)[:80]}")
                    elif is_auth:
                        wait = 60 * (attempt + 1)
                        self._reset_client()
                        _rate_limiter.global_pause(wait * 0.8)
                        tprint(f"  [401 AUTH {attempt+1}/{retries}] pause {wait:.0f}s, reset client — {str(exc)[:80]}")
                    else:
                        base = 5 * (2 ** attempt)
                        jitter = random.uniform(0, base * 0.5)
                        wait = base + jitter
                        tprint(f"  [RETRY {attempt+1}/{retries}] {str(exc)[:80]} — {wait:.0f}s")

                    self._inc(retry=1)
                    time.sleep(wait)
                else:
                    tprint(f"  [LLM FAIL after {retries} retries] {str(exc)[:100]}")
        return None

    def complete_json(self, *, system: str, user: str, **kwargs) -> Any:
        raw = self.complete(system=system, user=user, **kwargs)
        return parse_llm_json(raw) if raw else None

    def stats(self) -> dict:
        return {"model": self.model, "calls": self.calls, "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens, "errors": self.errors,
                "retries": self.retries_total, "rate_limit_hits": self.rate_limit_hits,
                "auth_errors": self.auth_errors}


# ─── Web Fetch ────────────────────────────────────────────────────────────────


def fetch_url(url: str, timeout: int = 15) -> str:
    if not is_http_url(url) or req_lib is None:
        return ""
    try:
        r = req_lib.get(url.strip(), headers={"User-Agent": "vinhlong360-research/1.0"},
                        timeout=timeout, allow_redirects=True)
        if r.status_code >= 400:
            return ""
        text = re.sub(r"<script[^>]*>.*?</script>", " ", r.text or "", flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&\w+;", " ", text)
        return compact(text, 12000)
    except Exception:
        return ""


def search_web(query: str, max_results: int = 8) -> list[dict[str, str]]:
    try:
        from ddgs import DDGS
    except ImportError:
        return []
    results = []
    try:
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                if not isinstance(item, dict):
                    continue
                url = item.get("href") or item.get("url") or ""
                if not is_http_url(url):
                    continue
                results.append({"title": str(item.get("title") or ""), "url": url,
                                "snippet": compact(item.get("body") or item.get("snippet"), 500)})
    except Exception:
        pass
    return results[:max_results]


def web_search_and_fetch(queries: list[str], max_per_query: int = 5) -> list[dict]:
    all_results, seen = [], set()
    for q in queries:
        for r in search_web(q, max_results=max_per_query):
            if r["url"] not in seen:
                seen.add(r["url"])
                r["text"] = fetch_url(r["url"], timeout=12)[:3000]
                if r["text"]:
                    all_results.append(r)
    return all_results


def build_web_context(results: list[dict], max_chars: int = 15000) -> str:
    parts, total = [], 0
    for r in results:
        if not r.get("text"):
            continue
        s = f"[{r['url']}] {r['title']}\n{r['text'][:1500]}"
        if total + len(s) > max_chars:
            break
        parts.append(s)
        total += len(s)
    return "\n\n---\n\n".join(parts)


# ─── Data / Corpus ────────────────────────────────────────────────────────────


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        return [dict(row) for row in csv.DictReader(f)]


def build_corpus(workers: int = 8):
    tprint("PHA 0: BUILD CORPUS")
    corpus_dir = OUTPUT_DIR / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    corpus_file = corpus_dir / "full_corpus.jsonl"

    sources = load_csv(SOURCES_CSV)
    tprint(f"  {len(sources)} sources in CSV")
    already = {rec.get("source_id") for rec in read_jsonl(corpus_file)}
    to_fetch = [s for s in sources if s.get("source_id") not in already]
    tprint(f"  Already: {len(already)}, to fetch: {len(to_fetch)}")
    if not to_fetch:
        return read_jsonl(corpus_file)

    def fetch_one(src):
        sid, url = src.get("source_id", ""), src.get("url", "").strip()
        text, status = "", "skipped"
        if url.startswith("C:/") or url.startswith("C:\\"):
            lp = Path(url.replace("/", os.sep))
            if lp.exists():
                try:
                    text, status = compact(lp.read_text(encoding="utf-8-sig"), 12000), "local_read"
                except Exception:
                    status = "local_error"
            else:
                status = "local_not_found"
        elif is_http_url(url):
            text = fetch_url(url, timeout=20)
            status = "fetched" if text else "fetch_failed"
        else:
            status = "no_url"
        rec = {**{k: src.get(k, "") for k in ["source_id", "url", "title", "geography", "layer", "layer_name", "reliability", "note"]},
               "fetch_status": status, "text_length": len(text), "text": text, "fetched_at": utc_now()}
        tprint(f"  [{'✓' if text else '✗'}] {sid}: {src.get('title','')[:50]}... ({status})")
        return rec

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(fetch_one, s) for s in to_fetch]):
            try:
                append_jsonl(corpus_file, fut.result())
            except Exception as e:
                tprint(f"  [ERR] {e}")

    all_rec = read_jsonl(corpus_file)
    ok = sum(1 for r in all_rec if r.get("text_length", 0) > 100)
    tprint(f"  Corpus: {ok}/{len(all_rec)} with text")

    idx = {"total": len(all_rec), "ok": ok, "by_geo": {}, "by_layer": {}, "at": utc_now()}
    for r in all_rec:
        for g in r.get("geography", "").split(";"):
            g = g.strip()
            if g:
                idx["by_geo"].setdefault(g, []).append(r["source_id"])
        idx["by_layer"].setdefault(r.get("layer", "?"), []).append(r["source_id"])
    with open(corpus_dir / "corpus_index.json", "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    return all_rec


def corpus_filter(corpus, geos=None, keywords=None):
    seen, out = set(), []
    if geos:
        for r in corpus:
            rg = r.get("geography", "").lower()
            if any(g.lower() in rg for g in geos) and r["source_id"] not in seen:
                seen.add(r["source_id"])
                out.append(r)
    if keywords:
        for r in corpus:
            if r["source_id"] in seen:
                continue
            s = " ".join([r.get("title", ""), r.get("note", ""), r.get("text", "")[:3000]]).lower()
            if any(k.lower() in s for k in keywords):
                seen.add(r["source_id"])
                out.append(r)
    out.sort(key=lambda r: -int(r.get("reliability", "0") or "0"))
    return out


def build_corpus_context(entries, max_chars=15000):
    parts, total = [], 0
    for r in entries:
        t = r.get("text", "")
        if not t or len(t) < 50:
            continue
        s = f"[{r.get('source_id','')}] {r.get('title','')}\n{t[:2000]}"
        if total + len(s) > max_chars:
            break
        parts.append(s)
        total += len(s)
    return "\n\n---\n\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# PHA 1 ULTRA: 15 dimensions × 10 layers — PARALLEL themes + sub-topics
# ═══════════════════════════════════════════════════════════════════════════════

THEMES = [
    {"id": "T01", "name": "Văn hóa bản địa", "keywords": ["miệt vườn","Khmer","xứ dừa","Kinh-Khmer-Hoa","tín ngưỡng","sông nước","cồn","nhà vườn"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Bản sắc miệt vườn Vĩnh Long","Văn hóa Khmer Trà Vinh","Xứ Dừa Bến Tre","Giao thoa Kinh-Khmer-Hoa","Tín ngưỡng đình/chùa/lăng/miếu","Văn hóa sông nước/cồn/nhà vườn/làng nghề"]},
    {"id": "T02", "name": "Lưu trú", "keywords": ["homestay","farmstay","ecolodge","lưu trú","khách sạn","nhà nghỉ","An Bình"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Homestay cù lao An Bình","Farmstay và ecolodge","Lưu trú đô thị 3 tỉnh","Ven biển Ba Động/Bình Đại","Heritage/craft/coconut/Khmer stay concepts","Chất lượng, review, khả năng đón quốc tế"]},
    {"id": "T03", "name": "Ẩm thực", "keywords": ["ẩm thực","bánh","bún nước lèo","dừa sáp","kẹo dừa","food","nấu ăn","chợ","đặc sản","trái cây"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["VL: bánh tét Trà Cuôn, cá sông, trái cây","TV: bún nước lèo, dừa sáp, Khmer, bánh dân gian","BT: dừa, kẹo, bánh phồng, tôm/cá, món dừa","Food tour / cooking class / chợ quê","Sản phẩm du lịch ẩm thực vs cộng đồng"]},
    {"id": "T04", "name": "Danh nhân", "keywords": ["Phan Thanh Giản","Nguyễn Thông","Phạm Hùng","Nguyễn Văn Tồn","Nguyễn Đình Chiểu","Nguyễn Thị Định","Trương Vĩnh Ký","Đồng Khởi","danh nhân","nghệ nhân"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["VL: Phan Thanh Giản, Nguyễn Thông, Phạm Hùng, Văn Thánh Miếu","TV: danh nhân Khmer, sư sãi, nghệ nhân Rô-băm/ngũ âm","BT: Nguyễn Đình Chiểu, Nguyễn Thị Định, Trương Vĩnh Ký, Đồng Khởi","Kể chuyện danh nhân trong tour du lịch"]},
    {"id": "T05", "name": "Nghệ thuật truyền thống", "keywords": ["đờn ca tài tử","hát bội","nhạc ngũ âm","Rô-băm","Dù kê","múa","diễn xướng","dân ca","hò"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Đờn ca tài tử UNESCO","Hát bội Vĩnh Long","Nhạc ngũ âm Khmer","Rô-băm và Dù kê","Múa/diễn xướng/dân ca/hò/lý","Mini show/workshop/gặp nghệ nhân"]},
    {"id": "T06", "name": "Làng nghề", "keywords": ["gốm","Mang Thít","hoa kiểng","Chợ Lách","dừa","bánh","đan lát","dệt chiếu","làng nghề","workshop"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Gốm đỏ Mang Thít","Hoa kiểng Chợ Lách","Nghề dừa Bến Tre","Dừa sáp Cầu Kè","Bánh dân gian","Đan lát/dệt chiếu/thủ công dừa","Workshop/lưu niệm/chuỗi giá trị"]},
    {"id": "T07", "name": "Nghi lễ - tín ngưỡng", "keywords": ["Ok Om Bok","Kathina","Nguyên Tiêu","Vu lan","Kỳ Yên","Lăng Ông","Nghinh Ông","lễ hội","đình","chùa","sắc phong"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Ok Om Bok/Kathina/Nguyên Tiêu/Vu lan","Kỳ Yên/Lăng Ông/Hạ Điền","Thành hoàng/tiền hiền/hậu hiền","Ngư dân/Nghinh Ông","Quy tắc ứng xử du khách tại lễ hội"]},
    {"id": "T08", "name": "Cộng đồng", "keywords": ["nhà vườn","nông dân","nghệ nhân","sư sãi","cộng đồng","phụ nữ","thanh niên","hợp tác xã","chi hội"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Nhà vườn/nông dân/nghệ nhân/sư sãi/du lịch cộng đồng","Phụ nữ BT/Đồng Khởi","Người trẻ bảo tồn","Chi hội/HTX/tổ cộng đồng du lịch"]},
    {"id": "T09", "name": "Truyền thông", "keywords": ["thương hiệu","storytelling","truyền thông","quảng bá","keyword","content","nội dung"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Thương hiệu từng vùng","Hệ thống nhân vật kể chuyện","Bộ từ khóa văn hóa du lịch","Nội dung web/app/social"]},
    {"id": "T10", "name": "Sản phẩm du lịch", "keywords": ["tour","tuyến","học đường","food tour","craft tour","festival","homestay tour","cultural night"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Tour học đường di sản-nghề-Khmer","Food tour 3 vùng","Craft tour gốm/dừa/hoa","Festival tour theo mùa","Homestay tour 2N1Đ/3N2Đ","Cultural night — mini show/workshop/dinner"]},
    {"id": "T11", "name": "Địa danh học", "keywords": ["địa danh","tên gọi","từ nguyên","Khmer cổ","Nôm","sông","rạch","cồn","cù lao","phum sóc"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Địa danh gốc Khmer ở Trà Vinh","Địa danh Nôm/Hán-Việt ở Vĩnh Long","Địa danh sông nước Bến Tre","Câu chuyện đằng sau tên gọi — kết nối du lịch"]},
    {"id": "T12", "name": "Chuỗi giá trị", "keywords": ["chuỗi giá trị","value chain","thu nhập","doanh thu","vé","phí","lợi ích","phân phối","đào tạo"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Phân phối thu nhập du lịch cộng đồng","Chi phí vận hành tour/homestay/workshop","Vai trò OTA/lữ hành trong chuỗi giá trị","Đào tạo nhân lực — gap nhu cầu vs thực tế"]},
    {"id": "T13", "name": "Tiểu sinh thái", "keywords": ["sinh thái","sông","nước ngọt","nước mặn","rừng","cò","chim","cá","dừa nước","phù sa","sạt lở","xâm nhập mặn"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Hệ sinh thái cù lao/cồn — sông Tiền, sông Hậu","Rừng ngập mặn/dừa nước ven biển BT-TV","Sân chim/cò — Bạc Liêu, Cù Lao Dung","Xâm nhập mặn, sạt lở — rủi ro du lịch","Vi khí hậu theo mùa — ảnh hưởng trải nghiệm"]},
    {"id": "T14", "name": "Bản đồ giác quan", "keywords": ["mùi","hương","vị","âm thanh","cảm giác","trải nghiệm","giác quan","thị giác"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Âm thanh vùng: sóng, đờn ca tài tử, ngũ âm, ghe","Mùi hương: lò gạch, hoa Chợ Lách, dừa, phù sa","Vị: bún nước lèo, bánh tét, kẹo dừa, trái cây mùa","Cảm giác: gió sông, nắng miệt vườn, mưa rào, đêm cồn","Thiết kế trải nghiệm đa giác quan cho du lịch"]},
    {"id": "T15", "name": "Mạng lưới con người", "keywords": ["nghệ nhân","sư sãi","chủ nhà vườn","hướng dẫn viên","chi hội","phụ nữ","thanh niên","elder"], "geos": ["Vĩnh Long","Trà Vinh","Bến Tre"],
     "sub_topics": ["Ai là ai: nghệ nhân, sư sãi, chủ nhà vườn, ban quý tế","Mạng lưới Chi hội du lịch — vai trò kết nối","Phụ nữ và thanh niên trong du lịch cộng đồng","Người giữ lửa: cá nhân then chốt cho bảo tồn"]},
]

# ─── 10 Layer Functions ──────────────────────────────────────────────────────


def _L1(llm, st, tname, ctx):
    sys = f"""Nhà nghiên cứu văn hóa-du lịch VL/TV/BT. Phân tích corpus về "{tname}" → sub-topic "{st}".
Trả về JSON: {{"sub_topic":"{st}","layer":"L1_survey","findings":["1-3 câu mỗi mục"],"claims":[{{"claim":"...","source_id":"...","confidence":0.0-1.0}}],"entities_mentioned":["..."],"gaps":["..."],"summary":"200-400 từ"}}"""
    return llm.complete_json(system=sys, user=f"CORPUS:\n{ctx}", max_tokens=4000)


def _L2(llm, st, prev, ctx):
    sys = f"""Trích xuất CẤU TRÚC từ L1 về "{st}": số liệu, nhân vật, timeline, địa danh, từ nguyên.
Trả về JSON: {{"sub_topic":"{st}","layer":"L2_extract","specific_facts":[{{"fact":"...","source_id":"...","confidence":0.0-1.0}}],"key_people":[{{"name":"...","role":"...","context":"..."}}],"timeline":[{{"date":"...","event":"..."}}],"places":[{{"name":"...","type":"..."}}],"numbers":[{{"metric":"...","value":"...","source_id":"..."}}],"etymology":[{{"name":"...","origin":"...","meaning":"..."}}]}}"""
    p = json.dumps(prev, ensure_ascii=False)[:8000] if prev else "{}"
    return llm.complete_json(system=sys, user=f"L1:\n{p}\n\nCORPUS:\n{ctx[:10000]}", max_tokens=5000)


def _L3(llm, st, prev_all, ctx):
    sys = f"""4 góc nhìn về "{st}": (1)Học thuật (2)Cộng đồng (3)Du khách (4)Nhà điều hành.
Trả về JSON: {{"sub_topic":"{st}","layer":"L3_perspectives","academic":{{"insights":["..."],"concerns":["..."]}},"community":{{"insights":["..."],"concerns":["..."]}},"tourist":{{"insights":["..."],"concerns":["..."]}},"operator":{{"insights":["..."],"concerns":["..."]}},"consensus":["..."],"tensions":["..."]}}"""
    return llm.complete_json(system=sys, user=f"PREV:\n{prev_all[:8000]}\n\nCORPUS:\n{ctx[:8000]}", max_tokens=4000)


def _L4(llm, st, claims, ctx, n_skeptics=5):
    """5 independent skeptics. 3/5 refute = kill."""
    if not claims:
        return {"sub_topic": st, "layer": "L4_adversarial", "verdicts": [], "note": "no claims"}
    claims_text = json.dumps(claims[:40], ensure_ascii=False)
    personas = [
        "Nhà sử học KHẮT KHE — kiểm niên đại, tên riêng, số liệu.",
        "Nhà dân tộc học PHẢN BIỆN — tìm suy luận quá mức, thiếu ngữ cảnh.",
        "Chuyên gia du lịch THỰC TẾ — kiểm tính khả thi, hallucination.",
        "Nhà ngôn ngữ học — kiểm tên gọi, từ nguyên, dịch sai Khmer/Nôm.",
        "Nhà môi trường — kiểm dữ liệu sinh thái, khí hậu, rủi ro tự nhiên.",
    ]

    def skeptic(i):
        sys = f"""{personas[i % len(personas)]}
Mặc định refuted=true nếu không chắc. Chỉ confirmed khi có bằng chứng RÕ trong corpus.
Trả về JSON: {{"skeptic_id":{i},"verdicts":[{{"claim_index":0,"refuted":true,"reason":"..."}}]}}"""
        return llm.complete_json(system=sys, user=f"CLAIMS:\n{claims_text}\n\nCORPUS:\n{ctx[:8000]}", max_tokens=3000)

    results = []
    with ThreadPoolExecutor(max_workers=min(3, n_skeptics)) as pool:
        for f in as_completed([pool.submit(skeptic, i) for i in range(n_skeptics)]):
            try:
                r = f.result()
                if r:
                    results.append(r)
            except Exception:
                pass

    votes = {}
    for r in results:
        for v in r.get("verdicts", []):
            idx = v.get("claim_index", -1)
            if idx not in votes:
                votes[idx] = {"ref": 0, "conf": 0, "reasons": []}
            if v.get("refuted"):
                votes[idx]["ref"] += 1
            else:
                votes[idx]["conf"] += 1
            votes[idx]["reasons"].append(v.get("reason", "")[:100])

    verdicts = []
    for idx, v in sorted(votes.items()):
        ct = claims[idx].get("claim", "") if idx < len(claims) else "?"
        killed = v["ref"] >= 3  # 3/5 majority
        verdicts.append({"claim_index": idx, "claim": ct[:200], "refuted": v["ref"], "confirmed": v["conf"],
                         "killed": killed, "reasons": v["reasons"][:3]})

    return {"sub_topic": st, "layer": "L4_adversarial", "total_claims": len(claims),
            "skeptics": len(results), "verdicts": verdicts,
            "killed": sum(1 for v in verdicts if v["killed"]),
            "survived": sum(1 for v in verdicts if not v["killed"])}


def _L5(llm, st, prev_all):
    queries = [f'"{st}" nghiên cứu khoa học site:tapchicongthuong.vn OR site:vjol.info',
               f'"{st}" luận văn Vĩnh Long Trà Vinh Bến Tre',
               f'"{st}" cultural heritage Mekong Delta research']
    web = web_search_and_fetch(queries, max_per_query=4)
    wctx = build_web_context(web, 10000)
    if not wctx:
        return {"sub_topic": st, "layer": "L5_academic", "new_findings": [], "note": "no academic sources"}
    sys = f"""Nguồn HỌC THUẬT mới về "{st}". Trích: phát hiện mới, số liệu, phương pháp.
Trả về JSON: {{"sub_topic":"{st}","layer":"L5_academic","new_findings":["..."],"confirmed":["..."],"new_data":[{{"metric":"...","value":"...","source":"..."}}],"academic_sources":[{{"url":"...","title":"...","relevance":"high/medium/low"}}]}}"""
    return llm.complete_json(system=sys, user=f"PREV:\n{prev_all[:5000]}\n\nACADEMIC:\n{wctx}", max_tokens=4000)


def _L6(llm, st, tname, prev_all, max_rounds=5):
    """Loop until dry — max 5 rounds, stop after 2 consecutive dry."""
    results, dry = [], 0
    for rnd in range(1, max_rounds + 1):
        if dry >= 2:
            break
        gap = llm.complete_json(
            system=f"""Gaps còn lại về "{st}"? Trả về JSON: {{"search_queries":["câu tìm kiếm cụ thể"],"remaining_gaps":["..."]}}""",
            user=f"ALL:\n{prev_all[:12000]}", max_tokens=1500)
        if not gap or not gap.get("search_queries"):
            dry += 1
            continue
        qs = [f"{q} {tname} Vĩnh Long Trà Vinh Bến Tre" for q in gap["search_queries"][:4]]
        web = web_search_and_fetch(qs, 4)
        wctx = build_web_context(web, 10000)
        if not wctx:
            dry += 1
            continue
        sys = f"""Thông tin MỚI về "{st}" — chỉ ghi những gì CHƯA CÓ.
Trả về JSON: {{"sub_topic":"{st}","layer":"L6_gap_r{rnd}","new_findings":["..."],"new_sources":[{{"url":"...","title":"..."}}],"remaining_gaps":["..."]}}"""
        r = llm.complete_json(system=sys, user=f"PREV:\n{prev_all[:5000]}\n\nWEB:\n{wctx}", max_tokens=3000)
        if r and r.get("new_findings"):
            dry = 0
            results.append(r)
            prev_all += f"\nL6r{rnd}: {json.dumps(r['new_findings'], ensure_ascii=False)[:2000]}"
        else:
            dry += 1
    return results


def _L7(llm, st, prev_all):
    sys = f"""Mâu thuẫn và giải quyết về "{st}": (1)Tìm contradictions (2)Resolution (3)Trust assessment.
Trả về JSON: {{"sub_topic":"{st}","layer":"L7_contradictions","contradictions":[{{"claim_a":"...","claim_b":"...","resolution":"...","trust":"a/b/neither"}}],"unresolved":["..."],"final_confidence":{{"overall":0.0,"justification":"..."}}}}"""
    return llm.complete_json(system=sys, user=f"ALL:\n{prev_all[:15000]}", max_tokens=4000)


def _L8(llm, st, prev_all):
    sys = f"""Phân tích TEMPORAL chuyên sâu về "{st}":
- Dòng thời gian chi tiết (quá khứ → hiện tại → xu hướng)
- Mùa vụ/chu kỳ lễ hội
- Thông tin nào có thể ĐÃ LỖI THỜI
- Dự báo thay đổi 3-5 năm tới
Trả về JSON: {{"sub_topic":"{st}","layer":"L8_temporal","timeline_detailed":[{{"period":"...","event":"...","significance":"..."}}],"seasonal_patterns":[{{"month":"...","activity":"..."}}],"possibly_outdated":[{{"claim":"...","risk":"..."}}],"future_projections":[{{"trend":"...","impact":"...","confidence":0.0}}]}}"""
    return llm.complete_json(system=sys, user=f"ALL:\n{prev_all[:12000]}", max_tokens=4000)


def _L9(llm, st, prev_all):
    sys = f"""COUNTER-NARRATIVE về "{st}" — bạn là PHẢN BIỆN VIÊN:
1. Narrative chính → góc nhìn ngược
2. Giả định chưa kiểm chứng
3. Ai bị thiệt/bị bỏ sót
4. Mặt trái/rủi ro không ai nói
5. Nếu điều ngược lại mới đúng thì sao?
Trả về JSON: {{"sub_topic":"{st}","layer":"L9_counter","mainstream":[{{"narrative":"...","counter":"...","evidence":"...","validity":"strong/moderate/weak"}}],"blind_spots":["..."],"who_loses":["..."],"hidden_risks":["..."]}}"""
    return llm.complete_json(system=sys, user=f"ALL:\n{prev_all[:12000]}", max_tokens=4000)


def _L10(llm, st, tname, prev_all):
    sys = f"""TỔNG HỢP CUỐI CÙNG về "{st}" (chủ đề {tname}). Đã qua 9 layers phân tích.
Chỉ giữ claims SURVIVED adversarial verify. Tích hợp counter-narrative và temporal.

Trả về JSON: {{"sub_topic":"{st}","layer":"L10_synthesis","theme":"{tname}",
  "executive_summary":"300-500 từ",
  "verified_facts":[{{"fact":"...","confidence":0.0-1.0,"sources":["..."]}}],
  "key_entities":[{{"name":"...","type":"person/place/event/concept","significance":"..."}}],
  "sensory_profile":{{"sounds":["..."],"smells":["..."],"tastes":["..."],"textures":["..."],"sights":["..."]}},
  "temporal_status":"current/partially_outdated/needs_field_check",
  "counter_perspectives":["..."],
  "tourism_potential":{{"readiness":"high/medium/low","products":["..."],"barriers":["..."]}},
  "remaining_unknowns":["..."],
  "overall_confidence":0.0}}"""
    return llm.complete_json(system=sys, user=f"ALL 9 LAYERS:\n{prev_all[:18000]}", max_tokens=5000)


# ─── Parallel Sub-topic Pipeline ─────────────────────────────────────────────


def process_subtopic(llm, theme, sub_topic, corpus_ctx, result_file, done):
    """Run all 10 layers for one sub-topic. Called from thread pool."""
    tid, tname = theme["id"], theme["name"]
    tag = f"{tid}/{sub_topic[:30]}"
    prev_all = ""

    # Load existing data for this sub-topic (for resume chain)
    for rec in read_jsonl(result_file):
        if rec.get("sub_topic") == sub_topic:
            prev_all += json.dumps(rec, ensure_ascii=False)[:2500] + "\n"

    def save(r):
        if r:
            r["theme_id"] = tid
            r["timestamp"] = utc_now()
            append_jsonl(result_file, r)
            nonlocal prev_all
            prev_all += json.dumps(r, ensure_ascii=False)[:2500] + "\n"

    layers = [
        ("L1_survey",    lambda: _L1(llm, sub_topic, tname, corpus_ctx)),
        ("L2_extract",   lambda: _L2(llm, sub_topic, None, corpus_ctx)),  # prev loaded from prev_all
        ("L3_perspectives", lambda: _L3(llm, sub_topic, prev_all, corpus_ctx)),
        ("L4_adversarial", None),  # special handling
        ("L5_academic",  lambda: _L5(llm, sub_topic, prev_all)),
        ("L6_gap_r1",    None),  # special handling
        ("L7_contradictions", lambda: _L7(llm, sub_topic, prev_all)),
        ("L8_temporal",  lambda: _L8(llm, sub_topic, prev_all)),
        ("L9_counter",   lambda: _L9(llm, sub_topic, prev_all)),
        ("L10_synthesis", lambda: _L10(llm, sub_topic, tname, prev_all)),
    ]

    for layer_name, fn in layers:
        if f"{sub_topic}|{layer_name}" in done:
            tprint(f"    {tag} {layer_name} SKIP")
            continue

        tprint(f"    {tag} {layer_name}...")

        if layer_name == "L2_extract":
            # Find L1 result for chain
            l1 = None
            for rec in read_jsonl(result_file):
                if rec.get("sub_topic") == sub_topic and rec.get("layer") == "L1_survey":
                    l1 = rec
                    break
            r = _L2(llm, sub_topic, l1, corpus_ctx)
            save(r)

        elif layer_name == "L4_adversarial":
            claims = []
            for rec in read_jsonl(result_file):
                if rec.get("sub_topic") == sub_topic:
                    claims.extend(rec.get("claims", []))
                    for sf in rec.get("specific_facts", []):
                        claims.append({"claim": sf.get("fact", ""), "source_id": sf.get("source_id", ""), "confidence": sf.get("confidence", 0.5)})
            r = _L4(llm, sub_topic, claims, corpus_ctx, n_skeptics=5)
            save(r)
            if r:
                tprint(f"    {tag} L4 → {r.get('survived',0)} survived, {r.get('killed',0)} killed")

        elif layer_name == "L6_gap_r1":
            gap_results = _L6(llm, sub_topic, tname, prev_all, max_rounds=5)
            for gr in gap_results:
                save(gr)
            tprint(f"    {tag} L6 → {len(gap_results)} productive rounds")

        else:
            r = fn()
            save(r)

    tprint(f"  ✓ {tag} — 10 layers done")


def run_thematic_ultra(corpus, llm, concurrent_themes=3, concurrent_subs=2):
    """Pha 1 ULTRA: parallel themes × parallel sub-topics × 10 layers."""
    tprint("=" * 70)
    tprint(f"PHA 1 ULTRA: 15 themes × 10 layers — {concurrent_themes} themes || {concurrent_subs} subs")
    tprint("=" * 70)

    theme_dir = OUTPUT_DIR / "thematic"
    theme_dir.mkdir(parents=True, exist_ok=True)
    c0 = llm.calls

    def process_theme(theme):
        tid, tname = theme["id"], theme["name"]
        subs = theme["sub_topics"]
        safe = re.sub(r"[^\w]", "_", tname)
        out_dir = theme_dir / f"{tid}_{safe}"
        out_dir.mkdir(parents=True, exist_ok=True)
        result_file = out_dir / "research.jsonl"

        tc = corpus_filter(corpus, geos=theme["geos"], keywords=theme["keywords"])
        tprint(f"\n--- {tid}: {tname} ({len(subs)} subs × 10 layers, corpus={len(tc)}) ---")
        ctx = build_corpus_context(tc, max_chars=15000)
        done = get_done_layers(result_file)

        with ThreadPoolExecutor(max_workers=concurrent_subs) as pool:
            futs = [pool.submit(process_subtopic, llm, theme, st, ctx, result_file, done) for st in subs]
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception as e:
                    tprint(f"  [ERR] {tid}: {e}")

        tprint(f"  ✓✓ {tid} COMPLETE")

    with ThreadPoolExecutor(max_workers=concurrent_themes) as pool:
        futs = [pool.submit(process_theme, t) for t in THEMES]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:
                tprint(f"  [THEME ERR] {e}")

    tprint(f"PHA 1 DONE — {llm.calls - c0} calls")


# ─── Pha 1b: Cross-pollination ───────────────────────────────────────────────


def run_cross_pollination(llm):
    """After all themes done, each theme gets insights from ALL other themes."""
    tprint("=" * 70)
    tprint("PHA 1b: CROSS-POLLINATION — themes feed each other")
    tprint("=" * 70)

    theme_dir = OUTPUT_DIR / "thematic"
    if not theme_dir.exists():
        return

    # Collect all L10 syntheses
    all_synth = {}
    for td in theme_dir.iterdir():
        if not td.is_dir():
            continue
        tid = td.name.split("_")[0]
        for rec in read_jsonl(td / "research.jsonl"):
            if rec.get("layer") == "L10_synthesis":
                all_synth.setdefault(tid, []).append(rec)

    if len(all_synth) < 2:
        tprint("  Not enough themes. Skipping.")
        return

    def pollinate_theme(theme):
        tid = theme["id"]
        tname = theme["name"]
        safe = re.sub(r"[^\w]", "_", tname)
        result_file = theme_dir / f"{tid}_{safe}" / "cross_pollination.jsonl"

        if result_file.exists() and len(read_jsonl(result_file)) > 0:
            tprint(f"  {tid} cross-pollination SKIP (already done)")
            return

        # Gather syntheses from OTHER themes
        other_ctx = ""
        for other_tid, synths in all_synth.items():
            if other_tid == tid:
                continue
            for s in synths[:2]:
                other_ctx += f"\n[{other_tid}] {s.get('sub_topic','')}: {s.get('executive_summary','')[:400]}\n"

        if not other_ctx:
            return

        # Own syntheses
        own_ctx = ""
        for s in all_synth.get(tid, []):
            own_ctx += f"\n{s.get('sub_topic','')}: {s.get('executive_summary','')[:300]}\n"

        sys = f"""Bạn đã nghiên cứu "{tname}". Bây giờ xem kết quả 14 chiều KHÁC.
Tìm: (1)Liên hệ mới giữa {tname} và các chiều khác (2)Insights bổ sung (3)Mâu thuẫn liên chiều.

Trả về JSON: {{"theme":"{tname}","layer":"cross_pollination",
  "new_connections":[{{"from_theme":"...","to_theme":"...","insight":"..."}}],
  "enrichments":[{{"sub_topic":"...","new_insight":"...","triggered_by":"..."}}],
  "cross_contradictions":[{{"theme_a":"...","theme_b":"...","contradiction":"..."}}]}}"""

        r = llm.complete_json(system=sys, user=f"OWN ({tname}):\n{own_ctx[:5000]}\n\nOTHER THEMES:\n{other_ctx[:15000]}", max_tokens=4000)
        if r:
            r["timestamp"] = utc_now()
            append_jsonl(result_file, r)
            tprint(f"  ✓ {tid} cross-pollinated: {len(r.get('new_connections',[]))} connections")

    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(pollinate_theme, t) for t in THEMES]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:
                tprint(f"  [ERR] {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHA 2: Asset Research — PARALLEL
# ═══════════════════════════════════════════════════════════════════════════════


ASSET_ANGLES = [
    ("history", "Lịch sử hình thành, niên đại, sự kiện, nhân vật"),
    ("architecture", "Kiến trúc, cảnh quan, quy mô, bảo tồn"),
    ("culture", "Văn hóa, phi vật thể, lễ hội, nghệ thuật"),
    ("tourism", "Trải nghiệm, thời gian, mùa, hạ tầng, giá"),
    ("community", "Cộng đồng, nghệ nhân, kinh tế, chia sẻ lợi ích"),
    ("sensory", "Giác quan: âm thanh, mùi, vị, xúc giác, thị giác"),
    ("etymology", "Tên gọi, địa danh học, truyền thuyết"),
]


def process_asset(llm, asset, corpus, thematic_findings):
    aid, aname = asset.get("asset_id", ""), asset.get("name", "")
    province, category = asset.get("province", ""), asset.get("category", "")

    a_dir = OUTPUT_DIR / "assets" / aid
    a_dir.mkdir(parents=True, exist_ok=True)
    rf = a_dir / "research.jsonl"
    done = {r.get("angle") or r.get("pass") or r.get("layer") for r in read_jsonl(rf)}

    geo_f = [province] if province != "Liên vùng" else ["Vĩnh Long", "Trà Vinh", "Bến Tre"]
    cat_w = [w.strip() for w in category.replace("-", " ").replace("/", " ").split() if len(w.strip()) > 2]
    ac = corpus_filter(corpus, geos=geo_f, keywords=[aname] + cat_w)
    ctx = build_corpus_context(ac[:30], max_chars=12000)

    # Thematic context
    tctx = ""
    for tid, findings in thematic_findings.items():
        for f in findings:
            if aname.lower() in json.dumps(f, ensure_ascii=False).lower():
                tctx += f"\n[{tid}] {json.dumps(f.get('executive_summary', f.get('summary', f.get('findings', ''))), ensure_ascii=False)[:300]}"
                if len(tctx) > 3000:
                    break

    ameta = json.dumps(asset, ensure_ascii=False)

    for ang_id, ang_desc in ASSET_ANGLES:
        if ang_id in done:
            continue
        tprint(f"  {aid} → {ang_id}")
        sys = f"""Phân tích "{aname}" ({province}) — GÓC: {ang_desc}. Metadata: {ameta}
Trả về JSON: {{"asset_id":"{aid}","angle":"{ang_id}","findings":["..."],"specific_facts":[{{"fact":"...","source_id":"...","confidence":0.0-1.0}}],"gaps":["..."],"connections":["..."]}}"""
        r = llm.complete_json(system=sys, user=f"CORPUS:\n{ctx[:12000]}\nTHEMATIC:\n{tctx[:3000]}", max_tokens=4000)
        if r:
            r["timestamp"] = utc_now()
            append_jsonl(rf, r)

    if "adversarial_verify" not in done:
        tprint(f"  {aid} → adversarial (5 skeptics)")
        claims = []
        for f in read_jsonl(rf):
            for sf in f.get("specific_facts", []):
                claims.append(sf)
            for fi in f.get("findings", []):
                if isinstance(fi, str):
                    claims.append({"fact": fi, "confidence": 0.7})
        r = _L4(llm, aname, claims[:40], ctx, n_skeptics=5)
        if r:
            r["pass"] = "adversarial_verify"
            r["asset_id"] = aid
            r["timestamp"] = utc_now()
            append_jsonl(rf, r)

    if "synthesis" not in done:
        tprint(f"  {aid} → synthesis")
        all_d = json.dumps(read_jsonl(rf), ensure_ascii=False)[:20000]
        sys = f"""Tổng hợp "{aname}" — chỉ giữ claims survived. Loại killed.
Trả về JSON: {{"asset_id":"{aid}","pass":"synthesis","name":"{aname}","summary":"150-300 từ","description":"500-1000 từ",
  "key_facts":[{{"fact":"...","confidence":0.0-1.0,"source":"..."}}],
  "sensory_profile":{{"sounds":["..."],"smells":["..."],"tastes":["..."],"textures":["..."],"sights":["..."]}},
  "etymology":"nguồn gốc tên gọi","connections":[{{"target":"...","type":"...","description":"..."}}],
  "best_season":"...","suggested_duration":"...","visitor_tips":["..."],
  "remaining_gaps":["..."],"overall_confidence":0.0}}"""
        r = llm.complete_json(system=sys, user=f"DATA:\n{all_d}", max_tokens=5000)
        if r:
            r["timestamp"] = utc_now()
            append_jsonl(rf, r)

    tprint(f"  ✓ {aid} done")


def run_asset_ultra(corpus, llm, concurrent=4):
    tprint("=" * 70)
    tprint(f"PHA 2 ULTRA: 62 assets × 7 angles + adversarial + synthesis — {concurrent} parallel")
    tprint("=" * 70)

    assets = load_csv(ASSETS_CSV)
    (OUTPUT_DIR / "assets").mkdir(parents=True, exist_ok=True)

    # Load thematic
    tf = {}
    td = OUTPUT_DIR / "thematic"
    if td.exists():
        for p in td.glob("*/research.jsonl"):
            tid = p.parent.name.split("_")[0]
            tf[tid] = read_jsonl(p)

    with ThreadPoolExecutor(max_workers=concurrent) as pool:
        futs = [pool.submit(process_asset, llm, a, corpus, tf) for a in assets]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:
                tprint(f"  [ASSET ERR] {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHA 3: Cross-link ULTRA — ALL 105 pairs + calendar + products + counter
# ═══════════════════════════════════════════════════════════════════════════════


def run_crosslink_ultra(corpus, llm, concurrent=6):
    tprint("=" * 70)
    tprint("PHA 3 ULTRA: 105 cross-pairs + calendar + products + counter")
    tprint("=" * 70)

    cd = OUTPUT_DIR / "crosslink"
    cd.mkdir(parents=True, exist_ok=True)

    # Load all data
    synths, theme_summ = [], []
    ad = OUTPUT_DIR / "assets"
    if ad.exists():
        for f in ad.glob("*/research.jsonl"):
            for r in read_jsonl(f):
                if r.get("pass") == "synthesis":
                    synths.append(r)
    td = OUTPUT_DIR / "thematic"
    if td.exists():
        for f in td.glob("*/research.jsonl"):
            for r in read_jsonl(f):
                if r.get("layer") in ("L1_survey", "L10_synthesis"):
                    theme_summ.append(r)

    all_ctx = json.dumps({"assets": synths[:25], "themes": theme_summ[:20]}, ensure_ascii=False)[:25000]

    # 3.1 Relationships
    if not (cd / "relationships.json").exists():
        tprint("  → 3.1 Relationships")
        r = llm.complete_json(system='Xác định quan hệ thực thể VL/TV/BT. JSON: {"relationships":[{"from":"...","to":"...","type":"...","strength":1-5,"description":"..."}],"clusters":[{"name":"...","members":["..."],"theme":"..."}],"hub_nodes":["..."]}', user=all_ctx, max_tokens=5000)
        if r:
            with open(cd / "relationships.json", "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=2)

    # 3.2 Calendar
    if not (cd / "festival_calendar.json").exists():
        tprint("  → 3.2 Calendar + temporal")
        r = llm.complete_json(system='Lịch lễ hội 12 tháng VL/TV/BT + temporal. JSON: {"calendar":[{"month":1,"lunar_date":"...","name":"...","location":"...","province":"...","confirmed":true,"peak_crowd":"low/medium/high","weather":"..."}],"seasonal_patterns":{"peak":"...","shoulder":"...","low":"..."},"year_round":["..."]}', user=all_ctx, max_tokens=5000)
        if r:
            with open(cd / "festival_calendar.json", "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=2)

    # 3.3 Products
    if not (cd / "products.json").exists():
        tprint("  → 3.3 Products")
        r = llm.complete_json(system='Sản phẩm du lịch từ nghiên cứu. JSON: {"products":[{"name":"...","type":"tour/workshop/event","route":["..."],"duration":"...","season":"...","segments":["..."],"highlights":["..."],"sensory":"...","story_hook":"...","readiness":"market-ready|pilot|development","value_chain":["..."]}]}', user=all_ctx, max_tokens=5000)
        if r:
            with open(cd / "products.json", "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=2)

    # 3.4 ALL 105 cross-dimension pairs — PARALLEL
    pairs_file = cd / "cross_dimension_pairs.jsonl"
    done_pairs = set()
    if pairs_file.exists():
        for r in read_jsonl(pairs_file):
            done_pairs.add(f"{r.get('dim_a','')}×{r.get('dim_b','')}")

    all_pairs = []
    for i, t1 in enumerate(THEMES):
        for t2 in THEMES[i+1:]:
            if f"{t1['id']}×{t2['id']}" not in done_pairs:
                all_pairs.append((t1["id"], t1["name"], t2["id"], t2["name"]))

    if all_pairs:
        tprint(f"  → 3.4 Cross-pairs: {len(all_pairs)} remaining (of 105)")

        def analyze_pair(p):
            d1, n1, d2, n2 = p
            sys = f"""Liên hệ "{n1}" × "{n2}". JSON: {{"dim_a":"{d1}","dim_b":"{d2}","connections":["..."],"synergies":["..."],"tensions":["..."],"insights":["..."]}}"""
            r = llm.complete_json(system=sys, user=all_ctx[:12000], max_tokens=2000)
            if r:
                r["timestamp"] = utc_now()
                append_jsonl(pairs_file, r)

        with ThreadPoolExecutor(max_workers=concurrent) as pool:
            futs = [pool.submit(analyze_pair, p) for p in all_pairs]
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception:
                    pass

    # 3.5 Master counter-narrative
    if not (cd / "counter_narratives.json").exists():
        tprint("  → 3.5 Master counter-narrative")
        r = llm.complete_json(
            system='PHẢN BIỆN VIÊN. Toàn bộ nghiên cứu VL/TV/BT. JSON: {"mainstream":[{"narrative":"...","counter":"...","evidence":"..."}],"assumptions":["..."],"missing_voices":["..."],"source_biases":["..."],"risks_overlooked":["..."]}',
            user=all_ctx, max_tokens=4000)
        if r:
            with open(cd / "counter_narratives.json", "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=2)

    # 3.6 Confidence matrix
    tprint("  → 3.6 Confidence matrix")
    rows = []
    if ad.exists():
        for f in ad.glob("*/research.jsonl"):
            for r in read_jsonl(f):
                if r.get("pass") == "synthesis":
                    rows.append({"asset_id": r.get("asset_id", ""), "name": r.get("name", ""),
                                 "confidence": r.get("overall_confidence", 0), "gaps": len(r.get("remaining_gaps", []))})
    if rows:
        with open(cd / "confidence_matrix.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["asset_id", "name", "confidence", "gaps"])
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: -r["confidence"]))

    tprint("  ✓ PHA 3 DONE")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    configure_io()
    ap = argparse.ArgumentParser(description="ULTRA-Depth Parallel Research Engine")
    ap.add_argument("--phase", type=int, choices=[0, 1, 2, 3])
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--concurrent", type=int, default=3, help="Parallel themes/assets (lower = fewer rate limits)")
    ap.add_argument("--rps", type=float, default=1.5, help="Max LLM requests/sec (token bucket)")
    ap.add_argument("--model", type=str, default=DEFAULT_MODEL)
    args = ap.parse_args()

    if not args.full and args.phase is None:
        ap.print_help()
        return

    phases = [args.phase] if args.phase is not None else [0, 1, 2, 3]

    tprint("ULTRA Research Engine v3.1 (rate-limited)")
    tprint(f"Model: {args.model} | Workers: {args.workers} | Concurrent: {args.concurrent} | RPS: {args.rps}")
    tprint("Depth: 15 dims × 10 layers + 5 skeptics + gap-5-rounds + cross-pollination + 105 pairs")
    tprint(f"Phases: {phases} | Output: {OUTPUT_DIR}")

    llm = LLMClient(model=args.model, rps=args.rps)
    if not llm.available:
        tprint("[WARN] LLM not available — set LLM_API_KEY and LLM_BASE_URL")

    corpus = []
    start = time.time()

    if 0 in phases:
        corpus = build_corpus(workers=args.workers)
    if any(p in phases for p in [1, 2, 3]):
        cf = OUTPUT_DIR / "corpus" / "full_corpus.jsonl"
        if not corpus and cf.exists():
            corpus = read_jsonl(cf)
            tprint(f"Loaded corpus: {len(corpus)} sources")
    if 1 in phases:
        run_thematic_ultra(corpus, llm, concurrent_themes=args.concurrent, concurrent_subs=max(2, args.concurrent // 2))
        run_cross_pollination(llm)
    if 2 in phases:
        run_asset_ultra(corpus, llm, concurrent=args.concurrent)
    if 3 in phases:
        run_crosslink_ultra(corpus, llm, concurrent=min(6, args.concurrent))

    elapsed = time.time() - start
    tprint(f"{'=' * 70}")
    tprint(f"COMPLETE — {elapsed:.0f}s ({elapsed/3600:.1f}h) — {json.dumps(llm.stats())}")

    with open(OUTPUT_DIR / "llm_usage.json", "w", encoding="utf-8") as f:
        json.dump({"run_at": utc_now(), "elapsed_s": round(elapsed), "elapsed_h": round(elapsed/3600, 1),
                    "phases": phases, **llm.stats()}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

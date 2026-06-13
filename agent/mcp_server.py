"""
vinhlong360 — MCP Server (Model Context Protocol).

Expose the vinhlong360 Knowledge Agent as an MCP server so that any
MCP-compatible client (Claude Desktop, Claude Code, Cursor, etc.) can
use the 13 AI tools, 3 resources, and 2 prompts.

Usage
-----
    python agent/mcp_server.py

Claude Desktop configuration (claude_desktop_config.json)
---------------------------------------------------------
    {
      "mcpServers": {
        "vinhlong360": {
          "command": "python",
          "args": ["C:/Code/vinhlong360/agent/mcp_server.py"]
        }
      }
    }

Claude Code configuration (.claude/settings.json)
--------------------------------------------------
    {
      "mcpServers": {
        "vinhlong360": {
          "command": "python",
          "args": ["C:/Code/vinhlong360/agent/mcp_server.py"],
          "type": "stdio"
        }
      }
    }
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── sys.path setup ──
# Ensure the agent/ directory is importable so that knowledge, itinerary_gen,
# etc. can be resolved without requiring the caller to set PYTHONPATH.
AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Load .env (for optional modules that may need env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except ImportError:
    pass

# ── Core imports ──
import knowledge
from tools import SYSTEM_PROMPT

# ── Optional module imports (mirror server.py pattern) ──
try:
    from itinerary_gen import generate_itinerary as _generate_itinerary
    HAS_ITINERARY_GEN = True
except ImportError:
    HAS_ITINERARY_GEN = False

try:
    from realtime import get_weather as _get_weather, get_upcoming_events as _get_upcoming_events
    HAS_REALTIME = True
except ImportError:
    HAS_REALTIME = False

try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

try:
    from openai import OpenAI
    _llm_client = None

    def _get_llm_client() -> OpenAI | None:
        global _llm_client
        if _llm_client is None:
            api_key = os.environ.get("LLM_API_KEY")
            base_url = os.environ.get("LLM_BASE_URL")
            if api_key and base_url:
                _llm_client = OpenAI(api_key=api_key, base_url=base_url)
        return _llm_client
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

    def _get_llm_client():
        return None

# ── MCP Server ──
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "vinhlong360",
    instructions=(
        "vinhlong360 Knowledge Agent — AI tourism assistant for Vinh Long province (Vietnam). "
        "327 entities, 2070 relationships, covering attractions, cuisine, craft villages, "
        "history, nature, economy, accommodation, and travel itineraries across "
        "Vinh Long, Ben Tre, and Tra Vinh."
    ),
)


# ── Helper: ensure knowledge data is loaded ──

def _ensure_knowledge():
    """Load knowledge base data if not already loaded."""
    knowledge._ensure()


# ── Helper: web search (DuckDuckGo) ──

def _web_search(query: str, max_results: int = 5) -> list[dict]:
    if not HAS_DDGS:
        return []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="vn-vi", max_results=max_results))
        return [
            {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            for r in results
        ]
    except Exception:
        return []


# ── Helper: generate follow-up suggestions via LLM ──

def _generate_followups(context: str) -> list[str]:
    import re as _re
    client = _get_llm_client()
    if not client:
        return []
    try:
        model = os.environ.get("LLM_MODEL_MINI", "cx/gpt-5.4-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": (
                    f"Dua vao ngu canh sau, goi y 3 cau hoi tiep theo ngan gon (< 40 ky tu) "
                    f"ma du khach co the muon hoi.\n\nNgu canh: {context}\n\n"
                    f"Tra ve JSON array gom 3 string. Chi tra JSON, khong text khac."
                ),
            }],
            temperature=0.7,
        )
        content = response.choices[0].message.content.strip()
        content = _re.sub(r"^```json\s*", "", content)
        content = _re.sub(r"\s*```$", "", content)
        return json.loads(content)[:3]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════
#  TOOLS (13 tools matching the OpenAI function-calling definitions)
# ═══════════════════════════════════════════════════════════════════════

@mcp.tool(
    name="search",
    description=(
        "Tim kiem trai nghiem, dac san, diem tham quan, lang nghe, am thuc, "
        "luu tru o Vinh Long (bao gom ca Ben Tre va Tra Vinh). "
        "Co the loc theo loai, khu vuc, thang, tu khoa, OCOP."
    ),
)
def search(
    q: Optional[str] = None,
    entity_type: Optional[str] = None,
    area: Optional[str] = None,
    month: Optional[int] = None,
    ocop_only: bool = False,
    limit: int = 10,
) -> str:
    """Search for experiences, specialties, attractions, craft villages, cuisine,
    accommodations in Vinh Long province (including Ben Tre and Tra Vinh).

    Args:
        q: Search keyword (e.g. 'dua', 'cam sanh', 'chua Khmer')
        entity_type: Type filter — experience, product, dish, craft_village,
            attraction, accommodation, person, event, history, nature, economy
        area: Area filter — vinh-long, ben-tre, tra-vinh
        month: Month (1-12) for seasonal filtering
        ocop_only: Only return OCOP-certified products
        limit: Maximum results (default 10)
    """
    _ensure_knowledge()
    result = knowledge.search_entities(
        q=q,
        entity_type=entity_type,
        area=area,
        month=month,
        ocop_only=ocop_only,
        limit=limit,
    )
    return json.dumps([{
        "id": e["id"],
        "type": e["type"],
        "name": e["name"],
        "summary": e.get("summary", ""),
        "place": (knowledge.get_place(e["id"]) or {}).get("name", ""),
        "season": knowledge.season_text(e),
        "confidence": e.get("confidence", 0),
    } for e in result], ensure_ascii=False)


@mcp.tool(
    name="entity_detail",
    description=(
        "Xem thong tin chi tiet cua mot thuc the (dac san, trai nghiem, diem tham quan...) "
        "theo ID. Bao gom mua vu, gia, nguon goc, do tin cay, va cac thuc the lien quan."
    ),
)
def entity_detail(entity_id: str) -> str:
    """View detailed information about an entity by its ID.

    Args:
        entity_id: Entity ID (e.g. 'cam-sanh-tam-binh', 'ao-ba-om')
    """
    _ensure_knowledge()
    detail = knowledge.entity_detail(entity_id)
    if not detail:
        return json.dumps({"error": f"Khong tim thay: {entity_id}"}, ensure_ascii=False)
    return json.dumps(detail, ensure_ascii=False, default=str)


@mcp.tool(
    name="seasonal_now",
    description="Xem san pham va trai nghiem dang vao mua (peak season) trong thang chi dinh.",
)
def seasonal_now(month: int) -> str:
    """View products and experiences currently in peak season.

    Args:
        month: Month to check (1-12)
    """
    _ensure_knowledge()
    result = knowledge.seasonal_now(month)
    return json.dumps([{
        "id": e["id"],
        "type": e["type"],
        "name": e["name"],
        "summary": e.get("summary", ""),
    } for e in result], ensure_ascii=False)


@mcp.tool(
    name="list_itineraries",
    description="Xem danh sach lich trinh goi y. Co the loc theo khu vuc.",
)
def list_itineraries(area: Optional[str] = None) -> str:
    """List suggested itineraries, optionally filtered by area.

    Args:
        area: Optional area filter — vinh-long, ben-tre, tra-vinh
    """
    _ensure_knowledge()
    result = knowledge.list_itineraries(area)
    return json.dumps([{
        "id": it["id"],
        "title": it["title"],
        "area": it.get("area"),
        "duration": it.get("duration"),
        "summary": it.get("summary", ""),
        "stops": len(it.get("stops", [])),
    } for it in result], ensure_ascii=False)


@mcp.tool(
    name="itinerary_detail",
    description="Xem chi tiet mot lich trinh goi y, bao gom cac diem dung va thong tin tung diem.",
)
def itinerary_detail(itinerary_id: str) -> str:
    """View details of a suggested itinerary including all stops.

    Args:
        itinerary_id: Itinerary ID (e.g. 'mot-ngay-cu-lao-an-binh')
    """
    _ensure_knowledge()
    it = knowledge.get_itinerary(itinerary_id)
    if not it:
        return json.dumps({"error": f"Khong tim thay: {itinerary_id}"}, ensure_ascii=False)
    stops_detail = []
    for s in it.get("stops", []):
        e = knowledge.get_entity(s["id"])
        stops_detail.append({
            "time": s["time"],
            "id": s["id"],
            "name": e["name"] if e else s["id"],
            "summary": e.get("summary", "") if e else "",
            "note": s.get("note", ""),
        })
    return json.dumps({**it, "stops": stops_detail}, ensure_ascii=False)


@mcp.tool(
    name="places_in_area",
    description="Danh sach cac xa/phuong trong mot khu vuc, kem so luong noi dung.",
)
def places_in_area(area: str) -> str:
    """List communes/wards in an area with content counts.

    Args:
        area: Area — vinh-long, ben-tre, tra-vinh
    """
    _ensure_knowledge()
    ps = knowledge.places(area)
    content_counts: dict[str, int] = {}
    for e in knowledge._entities.values():
        pid = e.get("placeId")
        if pid and e["type"] in knowledge.CARD_TYPES:
            content_counts[pid] = content_counts.get(pid, 0) + 1
    return json.dumps([{
        "id": p["id"],
        "name": p["name"],
        "level": p.get("level"),
        "legacyArea": p.get("legacyArea", ""),
        "content_count": content_counts.get(p["id"], 0),
    } for p in ps], ensure_ascii=False)


@mcp.tool(
    name="stats",
    description="Thong ke tong quan ve he thong: so luong thuc the theo loai, so xa/phuong, so lich trinh.",
)
def stats() -> str:
    """Get overall knowledge base statistics."""
    _ensure_knowledge()
    return json.dumps(knowledge.stats(), ensure_ascii=False)


@mcp.tool(
    name="compare_areas",
    description=(
        "So sanh 2 khu vuc (Vinh Long, Ben Tre, Tra Vinh) theo nhieu tieu chi: "
        "so luong diem tham quan, dac san, am thuc, lang nghe. "
        "Dung khi nguoi dung hoi 'Ben Tre hay Tra Vinh thu vi hon?', 'So sanh 3 khu vuc'."
    ),
)
def compare_areas(area_1: str, area_2: str) -> str:
    """Compare two areas across multiple criteria.

    Args:
        area_1: First area — vinh-long, ben-tre, tra-vinh
        area_2: Second area — vinh-long, ben-tre, tra-vinh
    """
    _ensure_knowledge()
    result = knowledge.compare_areas(area_1, area_2)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool(
    name="nearby_entities",
    description=(
        "Tim cac thuc the gan mot dia diem (cung xa/phuong hoac xa/phuong lan can). "
        "Dung khi nguoi dung hoi 'Gan do co gi?', 'Quanh khu vuc X co gi?'."
    ),
)
def nearby_entities(entity_id: str, limit: int = 8) -> str:
    """Find entities near a given location (same or neighboring commune/ward).

    Args:
        entity_id: Entity ID to use as center (e.g. 'chua-vam-ray')
        limit: Maximum results (default 8)
    """
    _ensure_knowledge()
    result = knowledge.nearby_entities(entity_id, limit)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool(
    name="web_search",
    description=(
        "Tim kiem tren internet khi knowledge base khong co thong tin. "
        "Dung cho cau hoi ve: tin tuc moi, su kien sap toi, thong tin chua co trong he thong. "
        "CHI dung sau khi da search knowledge base truoc."
    ),
)
def web_search(query: str) -> str:
    """Search the internet when the knowledge base lacks information.

    Args:
        query: Search query (Vietnamese, should include 'Vinh Long' or 'Ben Tre' or 'Tra Vinh')
    """
    results = _web_search(query)
    if not results:
        return json.dumps({"results": [], "note": "Khong tim thay ket qua"}, ensure_ascii=False)
    return json.dumps({"results": results}, ensure_ascii=False)


@mcp.tool(
    name="suggest_followups",
    description=(
        "Goi y 3 cau hoi tiep theo cho nguoi dung, lien quan den cau tra loi vua dua. "
        "Goi SAU KHI da tra loi xong cau hoi chinh."
    ),
)
def suggest_followups(context: str) -> str:
    """Suggest 3 follow-up questions related to the conversation context.

    Args:
        context: Brief summary of the conversation context (topic, area, info type)
    """
    suggestions = _generate_followups(context)
    return json.dumps({"suggestions": suggestions}, ensure_ascii=False)


@mcp.tool(
    name="generate_itinerary",
    description=(
        "Tao lich trinh du lich tuy chinh dua tren so thich, so ngay, khu vuc, thang di va ngan sach. "
        "Tra ve lich trinh chi tiet voi thoi gian, diem dung, ghi chu an uong, meo du lich. "
        "Dung khi du khach hoi 'goi y lich trinh', 'di dau N ngay', 'len ke hoach du lich'."
    ),
)
def generate_itinerary(
    days: int = 1,
    interests: Optional[list[str]] = None,
    areas: Optional[list[str]] = None,
    month: Optional[int] = None,
    budget: str = "trung_binh",
) -> str:
    """Generate a custom travel itinerary.

    Args:
        days: Number of days (1-5, default 1)
        interests: Interests list — am_thuc, lich_su, thien_nhien, van_hoa, mua_sam, tham_quan
        areas: Preferred areas — vinh-long, ben-tre, tra-vinh (default all 3)
        month: Travel month (1-12, default current month)
        budget: Budget level — thap (budget), trung_binh (moderate), cao (luxury)
    """
    _ensure_knowledge()
    if not HAS_ITINERARY_GEN:
        return json.dumps({"error": "Itinerary generator module not available"}, ensure_ascii=False)
    result = _generate_itinerary(
        days=days,
        interests=interests,
        areas=areas,
        month=month,
        budget=budget,
    )
    return json.dumps(result, ensure_ascii=False)


@mcp.tool(
    name="weather",
    description=(
        "Xem thoi tiet hien tai va su kien sap toi o khu vuc. "
        "Gom nhiet do, mo ta, goi y hoat dong phu hop thoi tiet, "
        "va cac le hoi/su kien trong 14 ngay toi."
    ),
)
def weather(area: Optional[str] = None) -> str:
    """Get current weather and upcoming events for an area.

    Args:
        area: Area — vinh-long, ben-tre, tra-vinh (default vinh-long)
    """
    if not HAS_REALTIME:
        return json.dumps({"error": "Weather API not available"}, ensure_ascii=False)
    area = area or "vinh-long"
    weather_data = _get_weather(area)
    events = _get_upcoming_events(days_ahead=14, area=area)
    return json.dumps({"weather": weather_data, "events": events}, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════════════
#  RESOURCES (3 resources for knowledge base data access)
# ═══════════════════════════════════════════════════════════════════════

@mcp.resource(
    "vinhlong360://entities",
    name="entities",
    description=(
        "Danh sach tat ca cac thuc the trong knowledge base "
        "(id, name, type). 327 entities covering attractions, cuisine, "
        "craft villages, history, nature, economy, accommodation."
    ),
    mime_type="application/json",
)
def resource_entities() -> str:
    """List all entities in the knowledge base (id, name, type)."""
    _ensure_knowledge()
    entities = []
    for e in knowledge._entities.values():
        if e["type"] in knowledge.CARD_TYPES:
            entities.append({
                "id": e["id"],
                "name": e["name"],
                "type": e["type"],
                "summary": e.get("summary", "")[:100],
            })
    entities.sort(key=lambda x: x["name"])
    return json.dumps(entities, ensure_ascii=False)


@mcp.resource(
    "vinhlong360://entity/{entity_id}",
    name="entity_detail",
    description="Chi tiet mot thuc the theo ID — bao gom place, area, related entities, season, confidence.",
    mime_type="application/json",
)
def resource_entity_detail(entity_id: str) -> str:
    """Get detailed information about a single entity by ID."""
    _ensure_knowledge()
    detail = knowledge.entity_detail(entity_id)
    if not detail:
        return json.dumps({"error": f"Entity not found: {entity_id}"}, ensure_ascii=False)
    return json.dumps(detail, ensure_ascii=False, default=str)


@mcp.resource(
    "vinhlong360://stats",
    name="stats",
    description=(
        "Thong ke knowledge base: so luong thuc the theo loai, "
        "so xa/phuong, so lich trinh, phan bo theo khu vuc."
    ),
    mime_type="application/json",
)
def resource_stats() -> str:
    """Get knowledge base statistics."""
    _ensure_knowledge()
    base_stats = knowledge.stats()
    base_stats["areas"] = {
        "vinh-long": knowledge.AREA_META.get("vinh-long", {}),
        "ben-tre": knowledge.AREA_META.get("ben-tre", {}),
        "tra-vinh": knowledge.AREA_META.get("tra-vinh", {}),
    }
    base_stats["relationships"] = len(knowledge._relationships) if knowledge._relationships else 0
    return json.dumps(base_stats, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════
#  PROMPTS (2 prompts for common tourism tasks)
# ═══════════════════════════════════════════════════════════════════════

@mcp.prompt(
    name="travel-advisor",
    description=(
        "System prompt cho hoi dap du lich Vinh Long. "
        "Bien LLM thanh huong dan vien du lich AI chuyen gia ve tinh Vinh Long "
        "(bao gom Ben Tre va Tra Vinh)."
    ),
)
def prompt_travel_advisor() -> list[dict]:
    """System prompt that turns an LLM into a Vinh Long tourism advisor."""
    current_month = datetime.now().month
    return [
        {
            "role": "user",
            "content": (
                f"{SYSTEM_PROMPT}\n\n"
                f"Hom nay: {datetime.now().strftime('%d/%m/%Y')}. "
                f"Thang hien tai: {current_month}.\n\n"
                f"Hay tra loi cau hoi cua du khach."
            ),
        }
    ]


@mcp.prompt(
    name="itinerary-planner",
    description=(
        "Prompt de tao lich trinh du lich tuy chinh. "
        "Truyen vao so ngay, so thich, khu vuc de nhan lich trinh chi tiet."
    ),
)
def prompt_itinerary_planner(
    days: str = "2",
    interests: str = "am_thuc, tham_quan",
    areas: str = "vinh-long, ben-tre",
) -> list[dict]:
    """Prompt for creating a custom travel itinerary.

    Args:
        days: Number of travel days (e.g. "2")
        interests: Comma-separated interests (am_thuc, lich_su, thien_nhien, van_hoa, mua_sam, tham_quan)
        areas: Comma-separated areas (vinh-long, ben-tre, tra-vinh)
    """
    current_month = datetime.now().month
    return [
        {
            "role": "user",
            "content": (
                f"{SYSTEM_PROMPT}\n\n"
                f"Hay tao lich trinh du lich chi tiet voi cac thong tin sau:\n"
                f"- So ngay: {days}\n"
                f"- So thich: {interests}\n"
                f"- Khu vuc: {areas}\n"
                f"- Thang di: {current_month}\n\n"
                f"Su dung tool `generate_itinerary` de tao lich trinh, "
                f"ket hop voi `seasonal_now` de uu tien dac san/trai nghiem dang mua. "
                f"Trinh bay theo timeline (gio -> diem den -> ghi chu), de theo doi."
            ),
        }
    ]


# ═══════════════════════════════════════════════════════════════════════
#  CONFIG HELPER
# ═══════════════════════════════════════════════════════════════════════

def get_mcp_config() -> dict:
    """Return the Claude Desktop / Claude Code config snippet for this MCP server.

    Usage:
        python -c "from agent.mcp_server import get_mcp_config; import json; print(json.dumps(get_mcp_config(), indent=2))"
    """
    script_path = str(Path(__file__).resolve()).replace("\\", "/")
    return {
        "mcpServers": {
            "vinhlong360": {
                "command": "python",
                "args": [script_path],
            }
        }
    }


# ═══════════════════════════════════════════════════════════════════════
#  MAIN — run as stdio MCP server
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Pre-load knowledge data so first tool call is fast
    try:
        _ensure_knowledge()
        entity_count = len(knowledge._entities)
        rel_count = len(knowledge._relationships) if knowledge._relationships else 0
    except Exception as e:
        print(f"Warning: Could not pre-load knowledge data: {e}", file=sys.stderr)
        entity_count = 0
        rel_count = 0

    print(
        f"vinhlong360 MCP Server starting — "
        f"{entity_count} entities, {rel_count} relationships, 13 tools",
        file=sys.stderr,
    )
    print(
        f"Config snippet:\n{json.dumps(get_mcp_config(), indent=2)}",
        file=sys.stderr,
    )

    mcp.run(transport="stdio")

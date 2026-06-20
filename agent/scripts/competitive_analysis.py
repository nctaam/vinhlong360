#!/usr/bin/env python3
"""Deep Competitive Analysis Engine — GPT-5.5 multi-layer competitor research.

5 layers of analysis across 3 dimensions:
  Dimension 1: Direct competitors (vinhlongtourist.vn, bentre.gov.vn/du-lich, travinh.gov.vn/du-lich)
  Dimension 2: Category competitors (mytour, traveloka, klook for Mekong Delta)
  Dimension 3: Content gap analysis (what keywords/topics nobody covers)

Each dimension runs through:
  L1: Feature/content audit
  L2: SEO keyword gap analysis
  L3: UX/UI comparison
  L4: Content quality scoring
  L5: Actionable recommendations

Output: agent/data/competitive/ — detailed JSON reports.
"""
from __future__ import annotations
import json, os, sys, time, threading, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "competitive"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(AGENT_DIR))
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

from openai import OpenAI

LLM_BASE = os.environ.get("LLM_BASE_URL", "")
LLM_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "cx/gpt-5.5")

client = OpenAI(base_url=LLM_BASE, api_key=LLM_KEY)
_lock = threading.Lock()
RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")


def tprint(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def llm_call(prompt, system="", retries=2, max_tokens=4000):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    for attempt in range(retries + 1):
        try:
            r = client.chat.completions.create(
                model=LLM_MODEL, messages=msgs,
                temperature=0.5, max_tokens=max_tokens
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
            else:
                raise


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return None


SYSTEM = """Bạn là chuyên gia phân tích thị trường du lịch số Việt Nam. Hiểu sâu SEO, UX, content
marketing, hành vi du khách Việt tìm thông tin du lịch miền Tây. Phân tích dựa trên kiến thức
thực tế về các website du lịch Việt Nam. Trả lời bằng TIẾNG VIỆT, cụ thể, có số liệu ước lượng."""


ANALYSES = [
    {
        "id": "direct_competitors",
        "title": "Đối thủ trực tiếp — Phân tích sâu",
        "competitors": [
            "vinhlongtourist.vn (Sở Du lịch Vĩnh Long)",
            "dulichbentre.com.vn (Du lịch Bến Tre)",
            "travinh.gov.vn/du-lich (Cổng TTĐT Trà Vinh)",
            "vinhlong.gov.vn (Cổng TTĐT Vĩnh Long)",
        ],
        "layers": [
            {
                "name": "L1_feature_audit",
                "prompt": """Phân tích chi tiết tính năng/nội dung của các website đối thủ trực tiếp:
{competitors}

So sánh với vinhlong360.vn (MXH du lịch cộng đồng, 1816 entity, 3 vùng VL+BT+TV).

Trả về JSON:
{{
  "competitors": [
    {{
      "name": "tên website",
      "url": "URL",
      "features": ["tính năng 1", "tính năng 2"],
      "content_types": ["loại nội dung 1", "loại 2"],
      "strengths": ["điểm mạnh 1", "điểm 2"],
      "weaknesses": ["điểm yếu 1", "điểm 2"],
      "update_frequency": "tần suất cập nhật ước tính",
      "target_audience": "đối tượng mục tiêu",
      "monetization": "mô hình kiếm tiền"
    }}
  ],
  "vinhlong360_advantages": ["lợi thế 1", "lợi thế 2", "lợi thế 3"],
  "vinhlong360_gaps": ["thiếu sót 1", "thiếu sót 2"]
}}"""
            },
            {
                "name": "L2_seo_keyword_gap",
                "prompt": """Phân tích keyword gap giữa vinhlong360.vn và đối thủ:
{competitors}

Trả về JSON:
{{
  "keywords_competitors_rank": [
    {{"keyword": "từ khóa", "search_volume_est": "cao/trung/thấp", "competitor": "ai đang rank", "difficulty": "dễ/vừa/khó", "our_opportunity": "mô tả cơ hội"}}
  ],
  "untapped_keywords": [
    {{"keyword": "từ khóa chưa ai target", "volume_est": "ước lượng", "content_needed": "loại content cần tạo"}}
  ],
  "local_seo_gaps": ["thiếu sót local SEO 1", "thiếu 2"],
  "geo_keywords": ["từ khóa GEO (AI search) 1", "kw2", "kw3"],
  "quick_wins": ["keyword dễ rank nhất 1", "kw2", "kw3"]
}}"""
            },
            {
                "name": "L3_ux_comparison",
                "prompt": """So sánh UX/UI giữa vinhlong360.vn và đối thủ:
{competitors}

vinhlong360 đang dùng: Nuxt SSR, Apple HIG design, glassmorphism, spring animations,
44px touch targets, dark mode, PWA-ready, mobile-first responsive.

Trả về JSON:
{{
  "ux_scores": [
    {{
      "competitor": "tên",
      "mobile_friendliness": "1-10 + nhận xét",
      "load_speed_est": "nhanh/trung/chậm + lý do",
      "navigation": "1-10 + nhận xét",
      "search_ux": "1-10 + nhận xét",
      "visual_design": "1-10 + nhận xét",
      "accessibility": "1-10 + nhận xét"
    }}
  ],
  "vinhlong360_ux_advantages": ["lợi thế UX 1", "lợi thế 2"],
  "vinhlong360_ux_improvements": ["cải tiến cần thiết 1", "cải tiến 2"],
  "industry_ux_trends": ["xu hướng UX du lịch 2025 mà ta nên theo 1", "xu hướng 2"]
}}"""
            },
            {
                "name": "L4_content_quality",
                "prompt": """Đánh giá chất lượng content giữa vinhlong360.vn và đối thủ:
{competitors}

Trả về JSON:
{{
  "content_comparison": [
    {{
      "competitor": "tên",
      "content_depth": "1-10 + nhận xét",
      "local_expertise": "1-10 — mức am hiểu địa phương",
      "freshness": "1-10 — độ mới/cập nhật",
      "multimedia": "1-10 — ảnh/video chất lượng",
      "user_generated": "có/không — có UGC không",
      "storytelling": "1-10 — kể chuyện hấp dẫn"
    }}
  ],
  "content_gaps_to_fill": [
    {{"topic": "chủ đề", "why": "tại sao quan trọng", "format": "định dạng nội dung gợi ý", "priority": "cao/trung/thấp"}}
  ],
  "unique_content_angles": ["góc nhìn/content unique mà chỉ vinhlong360 có thể làm 1", "2", "3"]
}}"""
            },
            {
                "name": "L5_strategy_recommendations",
                "prompt": """Dựa trên phân tích tổng hợp đối thủ {competitors}, đưa ra chiến lược
cho vinhlong360.vn (MXH du lịch cộng đồng, 1 dev, ngân sách <1M VND/tháng).

Trả về JSON:
{{
  "positioning_statement": "Định vị thương hiệu 1-2 câu",
  "differentiation_strategy": "Chiến lược khác biệt hóa chi tiết",
  "content_strategy": {{
    "pillar_content": ["content trụ cột 1", "2", "3"],
    "cluster_topics": ["cụm chủ đề 1", "2", "3", "4", "5"],
    "content_calendar_priorities": ["ưu tiên tháng này 1", "2", "3"]
  }},
  "seo_strategy": {{
    "quick_wins": ["hành động SEO ngay 1", "2", "3"],
    "medium_term": ["3-6 tháng 1", "2"],
    "long_term": ["6-12 tháng 1", "2"]
  }},
  "growth_tactics": [
    {{"tactic": "chiến thuật tăng trưởng", "effort": "thấp/vừa/cao", "impact": "thấp/vừa/cao", "timeline": "thời gian"}}
  ],
  "moat_building": ["rào cản cạnh tranh dài hạn 1", "2", "3"]
}}"""
            },
        ]
    },
    {
        "id": "category_competitors",
        "title": "Đối thủ danh mục — OTA & Aggregator",
        "competitors": [
            "mytour.vn (OTA nội địa, có Mekong Delta content)",
            "klook.com/vi (OTA quốc tế, trải nghiệm miền Tây)",
            "traveloka.com/vi (OTA, khách sạn + vé)",
            "review.vn (Review du lịch Việt)",
        ],
        "layers": [
            {
                "name": "L1_mekong_content_audit",
                "prompt": """Phân tích nội dung về miền Tây (đặc biệt Vĩnh Long, Bến Tre, Trà Vinh)
trên các OTA/aggregator:
{competitors}

Trả về JSON:
{{
  "mekong_coverage": [
    {{
      "platform": "tên",
      "vl_content_count": "ước lượng số listing/bài về VL",
      "bt_content_count": "BT",
      "tv_content_count": "TV",
      "content_quality": "1-10",
      "local_depth": "1-10 — am hiểu bản địa",
      "missing_topics": ["chủ đề về miền Tây họ thiếu 1", "2"]
    }}
  ],
  "aggregator_vs_community": {{
    "what_otas_do_better": ["1", "2"],
    "what_community_does_better": ["1", "2"],
    "coexistence_strategy": "Chiến lược chung sống — vinhlong360 bổ trợ OTA thế nào"
  }}
}}"""
            },
            {
                "name": "L2_keyword_opportunity",
                "prompt": """Phân tích từ khóa mà OTA/aggregator KHÔNG phủ tốt cho vùng VL+BT+TV:
{competitors}

Trả về JSON:
{{
  "ota_weak_keywords": [
    {{"keyword": "từ khóa", "why_weak": "tại sao OTA yếu ở keyword này", "our_angle": "vinhlong360 phủ thế nào"}}
  ],
  "local_knowledge_keywords": ["từ khóa đòi hỏi hiểu biết bản địa 1", "2", "3", "4", "5"],
  "long_tail_goldmine": ["cụm từ dài có intent cao 1", "2", "3", "4", "5"],
  "voice_search_queries": ["câu hỏi thoại 1", "2", "3"],
  "seasonal_keywords": {{
    "tet": ["kw Tết 1", "2"],
    "summer": ["kw hè 1", "2"],
    "year_round": ["kw quanh năm 1", "2"]
  }}
}}"""
            },
        ]
    },
    {
        "id": "content_gap_deep",
        "title": "Content Gap Analysis — Ngách trống",
        "competitors": ["Tất cả website du lịch miền Tây hiện có"],
        "layers": [
            {
                "name": "L1_underserved_topics",
                "prompt": """Xác định các chủ đề du lịch miền Tây (VL+BT+TV) mà KHÔNG có website nào
phủ tốt. Đặc biệt focus:
- Danh bạ hành chính (số ĐT, địa chỉ xã/phường) — ngách trống nhất
- Văn hóa Khmer Trà Vinh
- OCOP / sản phẩm bản địa
- Làng nghề truyền thống
- Lịch lễ hội âm lịch
- Mùa trái cây
- Đường sông / cù lao

Trả về JSON:
{{
  "severely_underserved": [
    {{"topic": "chủ đề", "current_coverage": "ai đang phủ + mức độ", "search_demand": "cao/trung/thấp", "content_plan": "vinhlong360 nên làm gì", "priority": 1-10}}
  ],
  "moderately_underserved": [
    {{"topic": "", "gap_description": "", "opportunity": ""}}
  ],
  "emerging_topics": [
    {{"topic": "xu hướng du lịch mới", "why_emerging": "lý do", "first_mover_advantage": "lợi thế người đi đầu"}}
  ],
  "content_moat_opportunities": ["nội dung rào cản cạnh tranh 1", "2", "3"]
}}"""
            },
            {
                "name": "L2_user_intent_map",
                "prompt": """Map user intent (ý định tìm kiếm) cho du khách muốn đến VL+BT+TV:

Trả về JSON:
{{
  "informational_intents": [
    {{"query_pattern": "mẫu câu hỏi", "volume": "cao/trung/thấp", "best_content_type": "loại content", "example_title": "tiêu đề bài mẫu"}}
  ],
  "navigational_intents": [
    {{"query_pattern": "", "target": "người dùng muốn tìm gì", "how_to_capture": ""}}
  ],
  "transactional_intents": [
    {{"query_pattern": "", "action_wanted": "hành động mong muốn", "how_to_serve": "vinhlong360 phục vụ thế nào (chỉ giới thiệu, không booking)"}}
  ],
  "micro_moments": [
    {{"moment": "I-want-to-go/know/do/buy", "context": "bối cảnh cụ thể", "content_needed": "nội dung cần có"}}
  ]
}}"""
            },
            {
                "name": "L3_social_content_analysis",
                "prompt": """Phân tích content du lịch miền Tây trên mạng xã hội (TikTok, Facebook,
YouTube, Zalo) — nội dung nào viral, du khách chia sẻ gì, hashtag nào hot.

Trả về JSON:
{{
  "viral_content_patterns": [
    {{"platform": "tên MXH", "content_type": "loại nội dung viral", "why_viral": "tại sao", "applicable_to_vinhlong360": "áp dụng thế nào"}}
  ],
  "popular_hashtags": {{
    "tiktok": ["#tag1", "#tag2"],
    "facebook": ["#tag1", "#tag2"],
    "youtube": ["keyword1", "keyword2"]
  }},
  "influencer_landscape": {{
    "micro_influencers": "nhận xét về micro-influencer du lịch miền Tây",
    "collab_opportunities": ["cơ hội hợp tác 1", "2"]
  }},
  "ugc_content_gaps": ["nội dung UGC mà chưa ai khai thác 1", "2", "3"],
  "cross_platform_strategy": "Chiến lược content xuyên nền tảng cho vinhlong360"
}}"""
            },
        ]
    },
]


def run_analysis_layer(analysis_id, layer, competitors_str):
    prompt = layer["prompt"].replace("{competitors}", competitors_str)
    try:
        raw = llm_call(prompt, SYSTEM, max_tokens=4000)
        data = parse_json(raw)
        if data:
            tprint(f"  ✓ {analysis_id}/{layer['name']}")
            return {"layer": layer["name"], "data": data}
        tprint(f"  ✗ {analysis_id}/{layer['name']} — parse fail")
    except Exception as e:
        tprint(f"  ✗ {analysis_id}/{layer['name']} — {e}")
    return None


def main():
    tprint("=== Deep Competitive Analysis Engine ===")
    tprint(f"Model: {LLM_MODEL}")
    tprint(f"Dimensions: {len(ANALYSES)}")

    all_results = {}

    for analysis in ANALYSES:
        aid = analysis["id"]
        tprint(f"\n--- {analysis['title']} ({len(analysis['layers'])} layers) ---")
        competitors_str = "\n".join(f"  - {c}" for c in analysis["competitors"])

        layers_result = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            futs = {pool.submit(run_analysis_layer, aid, l, competitors_str): l for l in analysis["layers"]}
            for f in as_completed(futs):
                r = f.result()
                if r:
                    layers_result.append(r)

        all_results[aid] = {
            "title": analysis["title"],
            "competitors": analysis["competitors"],
            "layers": sorted(layers_result, key=lambda x: x["layer"]),
        }

    out = OUTPUT_DIR / f"competitive_{RUN_TS}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    tprint(f"\n=== DONE ===")
    for aid, res in all_results.items():
        tprint(f"  {aid}: {len(res['layers'])} layers completed")
    tprint(f"Output: {out}")


if __name__ == "__main__":
    main()

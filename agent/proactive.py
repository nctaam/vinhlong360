"""
vinhlong360 — Proactive Agent Engine.

Tham khảo: Booking.com Smart Messenger, Google CC Agent (2026).

Agent KHÔNG CHỈ phản hồi — mà CHỦ ĐỘNG gợi ý:
  1. Seasonal alerts — "Mùa chôm chôm bắt đầu!"
  2. Weather-aware — "Trời mưa → gợi ý trong nhà"
  3. Time-of-day — "Buổi sáng → chợ nổi, buổi chiều → vườn trái cây"
  4. User-context — "Bạn đã xem Bến Tre → gợi ý thêm"
  5. Trending — "Nhiều người đang hỏi về lễ hội..."
  6. Follow-up — "Bạn hỏi về A → bạn có muốn biết thêm B?"

Output: danh sách proactive suggestions inject vào responses.
"""

import json
import time
from datetime import datetime
from pathlib import Path

import knowledge

# ══════════════════════════════════════════════════
#  SEASONAL CALENDAR — Lịch mùa vụ Vĩnh Long
# ══════════════════════════════════════════════════

SEASONAL_EVENTS = {
    1: [
        {"type": "festival", "text": "🎆 Tết Nguyên Đán — chợ hoa, bánh tét, đua ghe"},
        {"type": "fruit", "text": "🍈 Mùa bưởi Năm Roi chín rộ"},
    ],
    2: [
        {"type": "festival", "text": "🏮 Lễ hội Chùa Bà (rằm tháng Giêng)"},
        {"type": "fruit", "text": "🥭 Bắt đầu mùa xoài cát Hòa Lộc"},
    ],
    3: [
        {"type": "festival", "text": "🛕 Lễ Chôl Chnăm Thmây (Tết Khmer) — chùa Trà Vinh"},
        {"type": "fruit", "text": "🍊 Mùa cam sành Tam Bình"},
    ],
    4: [
        {"type": "event", "text": "🎭 Mùa đờn ca tài tử — hòa nhạc sông nước"},
        {"type": "fruit", "text": "🍈 Mùa sầu riêng bắt đầu"},
    ],
    5: [
        {"type": "nature", "text": "🌾 Mùa nước nổi bắt đầu — cảnh quan đẹp nhất"},
        {"type": "fruit", "text": "🫐 Mùa chôm chôm An Bình rộ"},
    ],
    6: [
        {"type": "fruit", "text": "🫐 Mùa chôm chôm & măng cụt chín rộ"},
        {"type": "experience", "text": "🚣 Mùa mưa — chèo xuồng rạch An Bình tuyệt đẹp"},
    ],
    7: [
        {"type": "nature", "text": "🌊 Mùa nước nổi — lũ về, cá linh nhiều"},
        {"type": "fruit", "text": "🍊 Mùa cam sành vụ 2"},
    ],
    8: [
        {"type": "festival", "text": "🏁 Lễ hội đua ghe Ngo — Trà Vinh"},
        {"type": "nature", "text": "🐟 Mùa cá linh — đặc sản mùa nước nổi"},
    ],
    9: [
        {"type": "festival", "text": "🌕 Tết Trung Thu — lồng đèn truyền thống"},
        {"type": "fruit", "text": "🥥 Mùa dừa sáp Cầu Kè"},
    ],
    10: [
        {"type": "festival", "text": "🛕 Lễ Ok Om Bok (cúng trăng Khmer) — Trà Vinh"},
        {"type": "nature", "text": "🌿 Mùa nước rút — hoa súng nở rộ"},
    ],
    11: [
        {"type": "event", "text": "🎪 Festival trái cây miền Tây"},
        {"type": "fruit", "text": "🍊 Mùa quýt đường"},
    ],
    12: [
        {"type": "fruit", "text": "🍈 Mùa bưởi da xanh Bến Tre"},
        {"type": "event", "text": "🎄 Mùa du lịch cao điểm — nên đặt trước"},
    ],
}

# ══════════════════════════════════════════════════
#  TIME-OF-DAY SUGGESTIONS
# ══════════════════════════════════════════════════

TIME_SUGGESTIONS = {
    "early_morning": {  # 5-8h
        "text": "🌅 Buổi sáng sớm",
        "activities": [
            "Chợ nổi Cái Bè (5h-8h)",
            "Ngắm bình minh sông Cổ Chiên",
            "Tập thể dục ven sông",
        ],
    },
    "morning": {  # 8-11h
        "text": "☀️ Buổi sáng",
        "activities": [
            "Tham quan vườn trái cây",
            "Đạp xe miệt vườn",
            "Tham quan di tích lịch sử",
        ],
    },
    "noon": {  # 11-14h
        "text": "🍜 Giờ trưa",
        "activities": [
            "Thưởng thức ẩm thực địa phương",
            "Nghỉ ngơi tại homestay",
            "Mua đặc sản OCOP",
        ],
    },
    "afternoon": {  # 14-17h
        "text": "🌤 Buổi chiều",
        "activities": [
            "Chèo xuồng rạch",
            "Làm bánh dân gian",
            "Tham quan làng nghề",
        ],
    },
    "evening": {  # 17-21h
        "text": "🌙 Buổi tối",
        "activities": [
            "Đờn ca tài tử trên sông",
            "Dạo phố đêm",
            "Ngắm hoàng hôn sông Tiền",
        ],
    },
}


def get_time_period() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 8:
        return "early_morning"
    elif 8 <= hour < 11:
        return "morning"
    elif 11 <= hour < 14:
        return "noon"
    elif 14 <= hour < 17:
        return "afternoon"
    else:
        return "evening"


# ══════════════════════════════════════════════════
#  PROACTIVE SUGGESTION ENGINE
# ══════════════════════════════════════════════════

def get_seasonal_suggestions(month: int = None) -> list[dict]:
    """Lấy gợi ý theo mùa."""
    if not month:
        month = datetime.now().month
    return SEASONAL_EVENTS.get(month, [])


def get_time_suggestions() -> dict:
    """Lấy gợi ý theo thời gian trong ngày."""
    period = get_time_period()
    return TIME_SUGGESTIONS.get(period, TIME_SUGGESTIONS["morning"])


def get_trending_entities(limit: int = 5) -> list[dict]:
    """Lấy entities đang được hỏi nhiều."""
    try:
        analytics_path = Path(__file__).resolve().parent / "data" / "analytics.json"
        if not analytics_path.exists():
            return []

        data = json.loads(analytics_path.read_text(encoding="utf-8"))
        hits = data.get("entity_hits", {})
        sorted_hits = sorted(hits.items(), key=lambda x: x[1], reverse=True)

        trending = []
        for eid, count in sorted_hits[:limit]:
            e = knowledge.get_entity(eid)
            if e:
                trending.append({
                    "id": eid,
                    "name": e["name"],
                    "type": e["type"],
                    "hit_count": count,
                })
        return trending
    except Exception:
        return []


def get_proactive_context(user_preferences: dict = None, month: int = None) -> str:
    """
    Tạo proactive context để inject vào system prompt.
    Giúp agent chủ động gợi ý thay vì chỉ trả lời.
    """
    parts = []

    # 1. Seasonal
    seasonal = get_seasonal_suggestions(month)
    if seasonal:
        season_text = "; ".join(s["text"] for s in seasonal)
        parts.append(f"[Mùa này]: {season_text}")

    # 2. Time of day
    time_info = get_time_suggestions()
    parts.append(f"[{time_info['text']}]: Gợi ý — {', '.join(time_info['activities'][:2])}")

    # 3. Trending
    trending = get_trending_entities(3)
    if trending:
        trending_text = ", ".join(f"{t['name']} ({t['hit_count']} lượt)" for t in trending)
        parts.append(f"[Đang hot]: {trending_text}")

    return "\n".join(parts)


def generate_welcome_message(user_preferences: dict = None) -> dict:
    """
    Tạo welcome message cá nhân hóa.
    Dùng cho lần đầu user mở chat hoặc quay lại.
    """
    month = datetime.now().month
    time_info = get_time_suggestions()
    seasonal = get_seasonal_suggestions(month)

    # Build personalized greeting
    greeting = "Xin chào! 👋 Tôi là hướng dẫn viên AI của vinhlong360.vn"

    # Add seasonal highlight
    if seasonal:
        greeting += f"\n\n📅 Tháng này: {seasonal[0]['text']}"

    # Add time-aware suggestion
    greeting += f"\n\n{time_info['text']}: {time_info['activities'][0]}"

    # Personalized if returning user
    if user_preferences:
        interests = user_preferences.get("interests", [])
        if interests:
            greeting += f"\n\n💡 Dựa trên sở thích của bạn ({', '.join(interests[:2])}), tôi có vài gợi ý mới!"

    suggestions = [
        f"Tháng {month} nên đi đâu?",
        "Đặc sản OCOP nổi bật?",
        "Lập lịch trình 2 ngày",
    ]

    return {
        "greeting": greeting,
        "suggestions": suggestions,
    }


def get_followup_suggestions(
    query: str,
    answer_topics: list[str],
    entities_mentioned: list[str],
    area: str = None,
) -> list[str]:
    """
    Tạo gợi ý follow-up thông minh dựa trên context.
    Thay vì random, dựa trên:
      - Entities vừa thảo luận → nearby + related
      - Khu vực → gợi ý khu vực khác
      - Chủ đề → mở rộng hoặc đào sâu
    """
    suggestions = []

    # 1. Nearby exploration
    if entities_mentioned:
        last_entity = entities_mentioned[-1]
        e = knowledge.get_entity(last_entity)
        if e:
            suggestions.append(f"Gần {e['name']} có gì thú vị?")

    # 2. Cross-area suggestion
    all_areas = {"vinh-long", "ben-tre", "tra-vinh"}
    if area:
        other_areas = all_areas - {area}
        area_names = {"vinh-long": "Vĩnh Long", "ben-tre": "Bến Tre", "tra-vinh": "Trà Vinh"}
        for other in list(other_areas)[:1]:
            suggestions.append(f"Còn ở {area_names.get(other, other)} thì sao?")

    # 3. Topic deepening
    q_lower = query.lower()
    if "ẩm thực" in q_lower or "ăn" in q_lower:
        suggestions.append("Quán ăn nào được đánh giá cao nhất?")
    elif "lịch sử" in q_lower:
        suggestions.append("Nhân vật lịch sử nổi tiếng nhất vùng?")
    elif "chùa" in q_lower or "khmer" in q_lower:
        suggestions.append("Lễ hội Khmer sắp tới là khi nào?")
    elif "lịch trình" in q_lower:
        suggestions.append("Nên đặt homestay ở đâu?")

    # Ensure 3 suggestions
    defaults = [
        f"Tháng {datetime.now().month} nên trải nghiệm gì?",
        "So sánh 3 khu vực",
        "Sản phẩm OCOP nổi bật",
    ]
    while len(suggestions) < 3:
        for d in defaults:
            if d not in suggestions:
                suggestions.append(d)
                break
        else:
            break

    return suggestions[:3]

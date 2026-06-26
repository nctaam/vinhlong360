"""
vinhlong360 — Real-time Data APIs.

Cung cấp dữ liệu thời gian thực:
  1. Weather — Thời tiết hiện tại từ OpenWeatherMap (free tier)
  2. Events — Lịch sự kiện từ local calendar + online sources
  3. Suggestions — Gợi ý theo thời tiết

Cache: mỗi API response cache 30 phút để tránh rate limit.
Fallback: nếu API không khả dụng, dùng seasonal data có sẵn.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

# ── Config ──

WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_CACHE_TTL = 1800  # 30 minutes

# Coordinates for 3 areas
AREA_COORDS = {
    "vinh-long": {"lat": 10.2537, "lon": 105.9722, "name": "Vĩnh Long"},
    "ben-tre":   {"lat": 10.2415, "lon": 106.3759, "name": "Bến Tre"},
    "tra-vinh":  {"lat": 9.9347,  "lon": 106.3455, "name": "Trà Vinh"},
}


# ══════════════════════════════════════════════════
#  WEATHER API
# ══════════════════════════════════════════════════

_weather_cache: dict = {}
_weather_lock = Lock()


def get_weather(area: str = "vinh-long") -> dict | None:
    """
    Lấy thời tiết hiện tại cho 1 area.

    Returns: {
        area, temp_c, feels_like_c, humidity, description,
        wind_speed_ms, icon, rain_mm, suggestion
    }
    """
    global _weather_cache

    # Check cache
    with _weather_lock:
        cached = _weather_cache.get(area)
        if cached and time.time() - cached["_ts"] < WEATHER_CACHE_TTL:
            return cached

    if not WEATHER_API_KEY:
        return _fallback_weather(area)

    coords = AREA_COORDS.get(area, AREA_COORDS["vinh-long"])

    try:
        import httpx
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": coords["lat"],
            "lon": coords["lon"],
            "appid": WEATHER_API_KEY,
            "units": "metric",
            "lang": "vi",
        }
        resp = httpx.get(url, params=params, timeout=10)
        data = resp.json()

        if resp.status_code != 200:
            return _fallback_weather(area)

        result = {
            "area": area,
            "area_name": coords["name"],
            "temp_c": round(data["main"]["temp"], 1),
            "feels_like_c": round(data["main"]["feels_like"], 1),
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"] if data.get("weather") else "",
            "icon": data["weather"][0]["icon"] if data.get("weather") else "",
            "wind_speed_ms": round(data.get("wind", {}).get("speed", 0), 1),
            "rain_mm": data.get("rain", {}).get("1h", 0),
            "suggestion": _weather_suggestion(data),
            "_ts": time.time(),
        }

        with _weather_lock:
            _weather_cache[area] = result

        return result

    except Exception:
        logger.warning("Weather API failed for area %s, using fallback", area, exc_info=True)
        return _fallback_weather(area)


def get_all_weather() -> list[dict]:
    """Lấy thời tiết cho cả 3 khu vực."""
    return [get_weather(area) for area in AREA_COORDS]


def _weather_suggestion(data: dict) -> str:
    """Gợi ý hoạt động dựa trên thời tiết."""
    temp = data.get("main", {}).get("temp", 30)
    weather_id = data.get("weather", [{}])[0].get("id", 800) if data.get("weather") else 800
    rain = data.get("rain", {}).get("1h", 0)

    if rain > 5 or (200 <= weather_id <= 531):
        return "🌧 Trời mưa — nên tham quan trong nhà: bảo tàng, chùa, làm bánh dân gian, thưởng thức ẩm thực"
    if temp > 35:
        return "🔥 Trời rất nóng — nên đi sáng sớm hoặc chiều mát, mang theo nước, chọn hoạt động có bóng mát"
    if temp > 30:
        return "☀️ Trời nắng nóng — nên đội nón, uống nhiều nước, tham quan vườn trái cây có bóng mát"
    if temp < 25:
        return "🌤 Thời tiết mát mẻ — lý tưởng cho đạp xe, đi bộ, tham quan ngoài trời"

    return "🌤 Thời tiết tốt — phù hợp mọi hoạt động ngoài trời"


def _fallback_weather(area: str) -> dict:
    """Thời tiết mặc định khi API không khả dụng."""
    month = datetime.now().month
    # Mùa mưa: 5-11, mùa khô: 12-4
    is_rainy = 5 <= month <= 11
    coords = AREA_COORDS.get(area, AREA_COORDS["vinh-long"])

    return {
        "area": area,
        "area_name": coords["name"],
        "temp_c": 28 if is_rainy else 32,
        "feels_like_c": 32 if is_rainy else 36,
        "humidity": 80 if is_rainy else 65,
        "description": "mưa rào" if is_rainy else "nắng nóng",
        "icon": "10d" if is_rainy else "01d",
        "wind_speed_ms": 3.0,
        "rain_mm": 5 if is_rainy else 0,
        "suggestion": "🌧 Mùa mưa — nên mang áo mưa, chọn hoạt động trong nhà buổi chiều" if is_rainy
                      else "☀️ Mùa khô — thời tiết đẹp, phù hợp tham quan ngoài trời",
        "fallback": True,
        "_ts": time.time(),
    }


# ══════════════════════════════════════════════════
#  EVENT CALENDAR
# ══════════════════════════════════════════════════

# Local event database (extends proactive.py's SEASONAL_EVENTS with exact dates)
UPCOMING_EVENTS = [
    # Format: (month, day_start, day_end, title, area, type)
    (1, 1, 7, "Tết Nguyên Đán", "all", "festival"),
    (1, 15, 15, "Rằm tháng Giêng (Lễ Chùa Bà)", "vinh-long", "festival"),
    (2, 14, 14, "Valentine — Đờn ca tài tử cho đôi", "vinh-long", "event"),
    (3, 14, 16, "Chôl Chnăm Thmây (Tết Khmer)", "tra-vinh", "festival"),
    (4, 30, 30, "Ngày Giải Phóng — Di tích lịch sử", "all", "festival"),
    (5, 1, 5, "Tuần lễ Du lịch miệt vườn", "vinh-long", "event"),
    (5, 19, 19, "Ngày sinh Chủ tịch Hồ Chí Minh", "all", "history"),
    (6, 1, 1, "Ngày Quốc tế Thiếu nhi — Vườn trái cây", "all", "event"),
    (7, 15, 15, "Lễ Vu Lan — Chùa chiền", "all", "festival"),
    (8, 20, 22, "Lễ hội đua ghe Ngo", "tra-vinh", "festival"),
    (9, 2, 2, "Quốc Khánh — Di tích lịch sử", "all", "history"),
    (9, 15, 15, "Tết Trung Thu — Lồng đèn", "all", "festival"),
    (10, 13, 15, "Ok Om Bok (Cúng Trăng Khmer)", "tra-vinh", "festival"),
    (10, 20, 22, "Lễ hội Dừa Bến Tre", "ben-tre", "festival"),
    (11, 15, 20, "Festival trái cây miền Tây", "vinh-long", "event"),
    (11, 20, 20, "Ngày Nhà giáo — Văn hóa giáo dục", "all", "history"),
    (12, 24, 25, "Giáng sinh — Nhà thờ cổ", "all", "event"),
    (12, 30, 31, "Countdown — Du lịch cuối năm", "all", "event"),
]


def get_upcoming_events(days_ahead: int = 30, area: str = None) -> list[dict]:
    """
    Lấy sự kiện sắp tới trong N ngày tới.

    Returns: [{title, date_start, date_end, area, type, days_until}]
    """
    now = datetime.now()
    current_month = now.month
    current_day = now.day
    results = []

    for month, day_start, day_end, title, evt_area, evt_type in UPCOMING_EVENTS:
        if area and evt_area != "all" and evt_area != area:
            continue

        # Calculate days until event (simple within-year logic)
        if month > current_month or (month == current_month and day_start >= current_day):
            days_until = (month - current_month) * 30 + (day_start - current_day)
        elif month < current_month:
            days_until = (12 - current_month + month) * 30 + (day_start - current_day)
        else:
            days_until = day_start - current_day

        if 0 <= days_until <= days_ahead:
            results.append({
                "title": title,
                "date_start": f"{day_start}/{month}",
                "date_end": f"{day_end}/{month}" if day_end != day_start else None,
                "area": evt_area,
                "type": evt_type,
                "days_until": days_until,
            })

    results.sort(key=lambda x: x["days_until"])
    return results


# ══════════════════════════════════════════════════
#  REALTIME CONTEXT FOR AGENT
# ══════════════════════════════════════════════════

def get_realtime_context(area: str = "vinh-long") -> str:
    """
    Build realtime context string for injection into agent prompt.
    Combines weather + events.
    """
    parts = []

    # Weather
    weather = get_weather(area)
    if weather:
        fb = " (dự đoán)" if weather.get("fallback") else ""
        parts.append(
            f"[Thời tiết {weather['area_name']}{fb}]: "
            f"{weather['description']}, {weather['temp_c']}°C, "
            f"ẩm {weather['humidity']}%. {weather['suggestion']}"
        )

    # Upcoming events
    events = get_upcoming_events(days_ahead=14, area=area)
    if events:
        evt_lines = []
        for e in events[:3]:
            prefix = f"trong {e['days_until']} ngày" if e["days_until"] > 0 else "HÔM NAY"
            evt_lines.append(f"{e['title']} ({prefix})")
        parts.append(f"[Sự kiện sắp tới]: {'; '.join(evt_lines)}")

    return "\n".join(parts)


# ══════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    print("=== Real-time Data ===\n")

    for area in AREA_COORDS:
        w = get_weather(area)
        print(f"Weather {area}: {w['temp_c']}°C, {w['description']}")
        print(f"  Suggestion: {w['suggestion']}")
        print()

    print("Upcoming events (14 days):")
    for e in get_upcoming_events(14):
        print(f"  {e['date_start']} — {e['title']} ({e['area']})")
    print()

    print("Context for agent:")
    print(get_realtime_context("vinh-long"))

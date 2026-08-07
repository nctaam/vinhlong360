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
import math
import os
import time
from datetime import datetime, timedelta, timezone

_VN_TZ = timezone(timedelta(hours=7))
from pathlib import Path
from threading import Lock
from urllib.parse import urlencode

from pinned_http import (
    BlockedAddressError,
    EgressPolicy,
    PeerMismatchError,
    PinnedHTTPClient,
    RedirectPolicyError,
)

logger = logging.getLogger(__name__)

# ── Config ──

WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_CACHE_TTL = 1800  # 30 minutes
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
WEATHER_ORIGIN = "https://api.openweathermap.org"
WEATHER_USER_AGENT = "vinhlong360-weather/1.0"

_WEATHER_EGRESS_POLICY = EgressPolicy(
    max_encoded_bytes=64 * 1024,
    max_decoded_bytes=256 * 1024,
    accepted_encodings=("gzip", "identity"),
    inactivity_timeout_seconds=10.0,
    total_timeout_seconds=10.0,
    max_redirects=2,
    allowed_origins=(WEATHER_ORIGIN,),
)
_PINNED_HTTP = PinnedHTTPClient()

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
        params = {
            "lat": coords["lat"],
            "lon": coords["lon"],
            "appid": WEATHER_API_KEY,
            "units": "metric",
            "lang": "vi",
        }
        resp = _PINNED_HTTP.get(
            f"{WEATHER_URL}?{urlencode(params)}",
            user_agent=WEATHER_USER_AGENT,
            policy=_WEATHER_EGRESS_POLICY,
            audit_context="realtime_weather",
        )

        if resp.status_code != 200:
            return _fallback_weather(area)
        data = json.loads(resp.content)

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

    except (BlockedAddressError, PeerMismatchError, RedirectPolicyError):
        return _fallback_weather(area)
    except Exception as exc:
        logger.warning(
            "Weather API failed for area %s, using fallback (%s)",
            area,
            type(exc).__name__,
        )
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
    month = datetime.now(_VN_TZ).month
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
#  BIÊN GIỚI LLM — dự phòng KHÔNG được đi tiếp như số đo
# ══════════════════════════════════════════════════
#
# `_fallback_weather()` ngay bên trên trả về payload có ĐỦ MỌI FIELD mà nhánh đo
# thật (:110-122) có: `temp_c`, `humidity`, `description`, `icon`. Nhưng đó là HẰNG
# SỐ THEO THÁNG, giống hệt nhau cho mọi khu vực, không phải quan trắc. Đưa nguyên
# dict đó cho LLM là nó phát biểu "Vĩnh Long hôm nay 28°C, mưa rào" trong khi hệ
# thống chưa hề có số đo nào — vi phạm CLAUDE.md §1.7 (không khai khống).
#
# Dấu hiệu phân biệt DUY NHẤT là key `fallback` (:182). Nhánh đo thật **vắng mặt**
# key này chứ không đặt `fallback: False`. Hệ quả bắt buộc:
#   - kiểm tra theo hướng TRUTHY. `payload.get("fallback") is True` sẽ để lọt mọi
#     giá trị truthy khác; `payload.get("fallback") != False` sẽ coi luôn nhánh đo
#     thật (get → None) là dự phòng và làm câm hết số đo thật.
#
# Cùng vấn đề này ở frontend đã xử lý tại `web-nuxt/composables/useWeather.ts`
# (`classifyWeather`): khi `fallback` truthy thì MỌI trường số bị đưa về `null` —
# giao diện không còn gì để lỡ tay render. Backend giữ đúng nguyên tắc đó: LLM
# không nhận được con số nào để lỡ miệng đọc ra, chỉ nhận một câu tiếng Việt nói
# rõ là chưa có số đo. Chỉ dán nhãn mà vẫn kèm số là không đủ — mô hình (cũng như
# người lướt nhanh) sẽ giữ lại con số và bỏ rơi phần chú thích.
#
# QUAN TRỌNG: hàng rào này chỉ đặt ở ĐƯỜNG VÀO LLM. Đường HTTP `GET /weather`
# (server.py) vẫn trả nguyên payload kèm `fallback: true`, vì frontend cần đúng
# key đó để tự phân loại.

LLM_WEATHER_NO_MEASUREMENT_NOTICE = (
    "KHÔNG CÓ SỐ ĐO THỜI TIẾT. Hệ thống không lấy được quan trắc cho khu vực này, "
    "nên phần dữ liệu thời tiết ở đây đã bị lược sạch, không còn con số nào. "
    "TUYỆT ĐỐI KHÔNG nêu nhiệt độ, độ ẩm, sức gió hay lượng mưa, và KHÔNG khẳng định "
    "trời đang mưa hay đang nắng. Nếu người dùng hỏi thời tiết, hãy nói thẳng rằng "
    "hiện chưa có số liệu quan trắc và mời họ xem dự báo chính thức."
)


def weather_has_measurement(payload: object) -> bool:
    """True chỉ khi `payload` là số đo THẬT từ upstream.

    Ba điều kiện, theo đúng thứ tự của `classifyWeather` ở frontend:
      1. phải là dict;
      2. `fallback` phải FALSY — kiểm tra truthy, xem ghi chú khối trên;
      3. `temp_c` phải là số hữu hạn thật sự (chuỗi "28" KHÔNG tính, `nan`/`inf`
         KHÔNG tính, `True` cũng KHÔNG tính dù `bool` là con của `int`).
    """
    if not isinstance(payload, dict):
        return False
    if payload.get("fallback"):
        return False
    temp = payload.get("temp_c")
    if isinstance(temp, bool) or not isinstance(temp, (int, float)):
        return False
    return math.isfinite(temp)


def weather_for_llm(payload: object) -> dict:
    """Chuẩn hoá payload thời tiết TRƯỚC khi đưa vào bất kỳ ngữ cảnh LLM nào.

    - Có số đo thật → trả nguyên payload (không sao chép, không sửa tại chỗ; dict
      này có thể chính là bản đang nằm trong `_weather_cache` và được `GET /weather`
      trả cho frontend).
    - Dự phòng theo mùa, hoặc không lấy được gì (None / lỗi / circuit breaker mở)
      → trả dict KHÔNG CÓ CON SỐ NÀO, mở đầu bằng câu cảnh báo tiếng Việt.

    Hai nhánh "dự phòng" và "mất kết nối" cố ý dùng chung một hình dạng: với LLM,
    cả hai đều là "không có số đo", và một hình dạng duy nhất thì không thể đọc nhầm.
    """
    if weather_has_measurement(payload):
        return payload  # type: ignore[return-value]
    return {
        # `canh_bao` đứng đầu để là thứ đầu tiên LLM đọc trong JSON (json.dumps giữ
        # thứ tự chèn), và đặt tên tiếng Việt để không bị đọc như metadata kỹ thuật.
        "canh_bao": LLM_WEATHER_NO_MEASUREMENT_NOTICE,
        "co_so_do": False,
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
    now = datetime.now(_VN_TZ)
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
    #
    # Chuỗi này được tiêm THẲNG vào system prompt (server.py `_gather_context_pieces`),
    # nên nó là đường ngắn nhất để một hằng số theo mùa trở thành lời khẳng định của
    # chatbot. Bản cũ vẫn in đủ "mưa rào, 28°C, ẩm 80%" và chỉ gắn hậu tố " (dự đoán)"
    # — một chi tiết hai chữ nằm trong ngoặc, đúng loại chú thích mà mô hình lược đi
    # đầu tiên khi tóm tắt lại cho người dùng. Nay: không có số đo thì KHÔNG có số nào
    # trong prompt, chỉ còn câu cấm bằng tiếng Việt.
    weather = get_weather(area)
    if weather_has_measurement(weather):
        parts.append(
            f"[Thời tiết {weather['area_name']}]: "
            f"{weather['description']}, {weather['temp_c']}°C, "
            f"ẩm {weather['humidity']}%. {weather['suggestion']}"
        )
    else:
        parts.append(f"[Thời tiết]: {LLM_WEATHER_NO_MEASUREMENT_NOTICE}")

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

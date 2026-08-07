"""Thời tiết DỰ PHÒNG không được đi tiếp vào LLM như thể là số đo thật.

Bối cảnh (CLAUDE.md §1.7 — không khai khống):

`realtime._fallback_weather()` (realtime.py:163-184) trả về một payload có ĐỦ MỌI
FIELD mà nhánh đo thật có — `temp_c: 28`, `humidity: 80`, `description: "mưa rào"`,
`icon: "10d"` — nhưng đó là HẰNG SỐ THEO THÁNG, không phải quan trắc. Nó được trả về
khi thiếu `WEATHER_API_KEY` (:86-87), khi upstream != 200 (:106-107), hoặc khi có bất
kỳ exception nào (:129-137). Dấu hiệu phân biệt DUY NHẤT là key `fallback` (:182):
nhánh đo thật (:110-122) **vắng mặt** key này chứ không đặt `fallback: False`.
⇒ chỉ được kiểm tra theo hướng TRUTHY. `is True` sẽ lọt giá trị truthy khác;
`!= False` sẽ coi cả nhánh đo thật là dự phòng.

Frontend đã xử lý đúng vấn đề này ở `web-nuxt/composables/useWeather.ts`
(`classifyWeather`): khi `fallback` truthy thì MỌI trường số bị đưa về `null`, giao
diện không còn gì để lỡ tay render. Các test dưới đây đòi backend nhất quán với
frontend ở BA biên giới LLM — tool `weather` của chat, ngữ cảnh tiêm thẳng vào system
prompt, và tool `weather` của MCP server — đồng thời khoá hợp đồng NGƯỢC lại: đường
HTTP `GET /weather` vẫn phải giao nguyên `fallback: true` cho frontend.
"""

from __future__ import annotations

import copy
import json

import pytest

import realtime

try:  # noqa: SIM105
    # Import cấp module CHỈ để khai báo quan hệ: file này có phủ `mcp_server`.
    # Các test bên dưới vẫn dùng `pytest.importorskip` để tự bỏ qua khi thiếu phụ
    # thuộc MCP — đây không thay thế cho nó. Lý do phải viết thêm: cổng R20.7 ghép
    # test với module bằng TÊN FILE hoặc bằng AST import, mà `importorskip` là lời
    # gọi lúc chạy nên AST không nhìn thấy; thiếu dòng này thì mcp_server bị tính
    # là "sửa mà không có test" dù test đã có thật.
    import mcp_server  # noqa: F401
except Exception:  # pragma: no cover - môi trường không có phụ thuộc MCP
    mcp_server = None  # type: ignore[assignment]


# Payload nhánh ĐO THẬT (realtime.py:110-122) — chú ý: KHÔNG có key `fallback`.
MEASURED = {
    "area": "vinh-long",
    "area_name": "Vĩnh Long",
    "temp_c": 30.6,
    "feels_like_c": 34.4,
    "humidity": 78,
    "description": "mưa nhẹ",
    "icon": "10d",
    "wind_speed_ms": 2.3,
    "rain_mm": 1.2,
    "suggestion": "Trời mưa — nên tham quan trong nhà",
    "_ts": 1_770_000_000.0,
}


@pytest.fixture
def fallback_payload() -> dict:
    """Payload dự phòng THẬT do realtime sinh ra (khác nhau theo mùa) — không bịa lại."""
    return realtime._fallback_weather("vinh-long")


def _has_digit(text: str) -> bool:
    return any(ch.isdigit() for ch in text)


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


# ── Câu cảnh báo: phải là chữ tiếng Việt, không phải cờ kỹ thuật ──────────────

def test_notice_is_plain_vietnamese_prose_not_a_technical_flag():
    notice = realtime.LLM_WEATHER_NO_MEASUREMENT_NOTICE
    assert "KHÔNG CÓ SỐ ĐO" in notice, "LLM phải đọc được lệnh cấm bằng tiếng Việt, không phải suy từ cờ"
    assert len(notice) > 80, "một câu quá ngắn dễ bị mô hình lướt qua"
    assert "fallback" not in notice.lower(), "không được để LLM tự dịch thuật ngữ kỹ thuật"


def test_notice_carries_no_number_of_its_own():
    """Chính câu cảnh báo phải sạch số — nếu không, mọi assert 'không còn chữ số' vô nghĩa."""
    assert not _has_digit(realtime.LLM_WEATHER_NO_MEASUREMENT_NOTICE)


# ── weather_has_measurement: nhận diện theo hướng TRUTHY ─────────────────────

def test_measured_payload_has_no_fallback_key_and_counts_as_measurement():
    assert "fallback" not in MEASURED
    assert realtime.weather_has_measurement(MEASURED) is True


@pytest.mark.parametrize("flag", [True, 1, "yes", ["x"], 0.5])
def test_any_truthy_fallback_flag_blocks_measurement(flag):
    """`is True` sẽ để lọt 1/"yes"/[...] — chốt lại bằng parametrize."""
    payload = {**MEASURED, "fallback": flag}
    assert realtime.weather_has_measurement(payload) is False


@pytest.mark.parametrize("flag", [False, 0, "", None])
def test_falsy_fallback_flag_is_still_a_measurement(flag):
    assert realtime.weather_has_measurement({**MEASURED, "fallback": flag}) is True


@pytest.mark.parametrize("payload", [None, {}, [], "28", {"temp_c": "28"}, {"temp_c": float("nan")}])
def test_shapes_without_a_real_number_are_not_measurements(payload):
    """Nhất quán với frontend `finiteNumber`: chuỗi "28" KHÔNG phải số đo."""
    assert realtime.weather_has_measurement(payload) is False


def test_real_fallback_payload_is_not_a_measurement(fallback_payload):
    assert realtime.weather_has_measurement(fallback_payload) is False


# ── weather_for_llm: lược sạch số ở chế độ dự phòng ─────────────────────────

def test_fallback_payload_reaches_llm_with_warning_and_zero_numbers(fallback_payload):
    safe = realtime.weather_for_llm(fallback_payload)
    text = _dump(safe)

    assert realtime.LLM_WEATHER_NO_MEASUREMENT_NOTICE in text
    assert not _has_digit(text), f"còn con số bịa lọt sang LLM: {text}"
    for fabricated in ("28", "32", "80", "65", "mưa rào", "nắng nóng", "10d", "01d"):
        assert fabricated not in text


def test_warning_is_the_first_key_the_llm_meets(fallback_payload):
    """json.dumps giữ thứ tự chèn — cảnh báo phải đứng trước mọi thứ khác."""
    safe = realtime.weather_for_llm(fallback_payload)
    assert next(iter(safe)) == "canh_bao"


@pytest.mark.parametrize("missing", [None, {}, {"temp_c": None}])
def test_no_data_at_all_gets_the_same_warning(missing):
    """Circuit breaker mở / lỗi realtime → cũng là 'không có số đo', không phải im lặng."""
    assert realtime.LLM_WEATHER_NO_MEASUREMENT_NOTICE in _dump(realtime.weather_for_llm(missing))


def test_measured_payload_passes_through_untouched():
    safe = realtime.weather_for_llm(MEASURED)
    assert safe == MEASURED
    assert realtime.LLM_WEATHER_NO_MEASUREMENT_NOTICE not in _dump(safe)


def test_sanitiser_never_mutates_its_input(fallback_payload):
    """GET /weather trả về chính dict trong `_weather_cache`; sửa tại chỗ = phá frontend."""
    before = copy.deepcopy(fallback_payload)
    realtime.weather_for_llm(fallback_payload)
    realtime.weather_for_llm(MEASURED)
    assert fallback_payload == before
    assert MEASURED["temp_c"] == 30.6


# ── Biên giới 1: ngữ cảnh tiêm thẳng vào system prompt ───────────────────────

def test_realtime_context_states_there_is_no_measurement(monkeypatch, fallback_payload):
    monkeypatch.setattr(realtime, "get_weather", lambda area="vinh-long": fallback_payload)
    monkeypatch.setattr(realtime, "get_upcoming_events", lambda **kwargs: [])

    ctx = realtime.get_realtime_context("vinh-long")

    assert realtime.LLM_WEATHER_NO_MEASUREMENT_NOTICE in ctx
    assert "°C" not in ctx
    assert not _has_digit(ctx), f"số bịa vẫn nằm trong system prompt: {ctx}"


def test_realtime_context_keeps_real_measurement(monkeypatch):
    monkeypatch.setattr(realtime, "get_weather", lambda area="vinh-long": dict(MEASURED))
    monkeypatch.setattr(realtime, "get_upcoming_events", lambda **kwargs: [])

    ctx = realtime.get_realtime_context("vinh-long")

    assert "30.6°C" in ctx
    assert "78%" in ctx
    assert realtime.LLM_WEATHER_NO_MEASUREMENT_NOTICE not in ctx


# ── Biên giới 2: tool `weather` của chat (agent/server.py) ───────────────────

@pytest.fixture
def server_module(monkeypatch):
    import server

    monkeypatch.setattr(server, "HAS_REALTIME", True)
    # Circuit breaker là singleton dùng chung cả suite — tắt nhánh đó để test
    # xác định. Việc _tool_weather PHẢI đi qua weather_breaker đã có test riêng
    # (agent/tests/test_resilience.py::test_weather_tool_uses_circuit_breaker).
    monkeypatch.setattr(server, "HAS_CIRCUIT_BREAKER", False)
    monkeypatch.setattr(server, "get_upcoming_events", lambda **kwargs: [])
    return server


def test_chat_weather_tool_warns_llm_when_data_is_fallback(server_module, monkeypatch, fallback_payload):
    monkeypatch.setattr(server_module, "get_weather", lambda area: fallback_payload)

    raw = server_module._tool_weather({"area": "vinh-long"})
    payload = json.loads(raw)

    assert realtime.LLM_WEATHER_NO_MEASUREMENT_NOTICE in raw
    assert not _has_digit(_dump(payload["weather"])), f"số bịa lọt vào tool result: {raw}"


def test_chat_weather_tool_warns_llm_when_call_fails(server_module, monkeypatch):
    def boom(area):
        raise RuntimeError("upstream down")

    monkeypatch.setattr(server_module, "get_weather", boom)

    raw = server_module._tool_weather({"area": "vinh-long"})

    assert realtime.LLM_WEATHER_NO_MEASUREMENT_NOTICE in raw


def test_chat_weather_tool_still_delivers_real_measurements(server_module, monkeypatch):
    monkeypatch.setattr(server_module, "get_weather", lambda area: dict(MEASURED))

    raw = server_module._tool_weather({"area": "vinh-long"})
    payload = json.loads(raw)

    assert payload["weather"]["temp_c"] == 30.6
    assert payload["weather"]["humidity"] == 78
    assert realtime.LLM_WEATHER_NO_MEASUREMENT_NOTICE not in raw


# ── Biên giới 3: tool `weather` của MCP server ───────────────────────────────

def test_mcp_weather_tool_warns_on_fallback(monkeypatch, fallback_payload):
    mcp_server = pytest.importorskip("mcp_server")

    monkeypatch.setattr(mcp_server, "HAS_REALTIME", True)
    monkeypatch.setattr(mcp_server, "_get_weather", lambda area: fallback_payload)
    monkeypatch.setattr(mcp_server, "_get_upcoming_events", lambda **kwargs: [])

    raw = mcp_server.weather("vinh-long")
    payload = json.loads(raw)

    assert realtime.LLM_WEATHER_NO_MEASUREMENT_NOTICE in raw
    assert not _has_digit(_dump(payload["weather"]))


def test_mcp_weather_tool_still_delivers_real_measurements(monkeypatch):
    mcp_server = pytest.importorskip("mcp_server")

    monkeypatch.setattr(mcp_server, "HAS_REALTIME", True)
    monkeypatch.setattr(mcp_server, "_get_weather", lambda area: dict(MEASURED))
    monkeypatch.setattr(mcp_server, "_get_upcoming_events", lambda **kwargs: [])

    payload = json.loads(mcp_server.weather("vinh-long"))

    assert payload["weather"]["temp_c"] == 30.6


# ── Hợp đồng ngược: frontend vẫn phải thấy `fallback: true` nguyên vẹn ───────

def test_http_payload_for_frontend_keeps_the_fallback_flag_and_its_fields(monkeypatch):
    """useWeather.ts phân loại bằng chính key này — không được sạch hoá ở tầng get_weather."""
    monkeypatch.setattr(realtime, "WEATHER_API_KEY", "")
    realtime._weather_cache.clear()
    try:
        payload = realtime.get_weather("vinh-long")
    finally:
        realtime._weather_cache.clear()

    assert payload["fallback"] is True
    assert isinstance(payload["temp_c"], (int, float))

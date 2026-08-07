"""Cổng lắng nghe tham số hoá được — mà mặc định KHÔNG đổi hành vi prod.

Nền tảng sẽ được nhân bản (dongthap360, cantho360…). Port ghim cứng trong
``uvicorn.run(...)`` chặn việc chạy hai bản trên cùng một máy. Bộ test này khoá
ba tính chất:

1. Không set env => y hệt trước (agent 8360, bot gateway 8361) — nginx.conf và
   ops/systemd/* vẫn ghim hai số này.
2. Set env => tiến trình đi theo, và HAI tiến trình đọc HAI biến riêng.
3. Giá trị rác => dừng ngay, nói rõ biến nào sai; KHÔNG âm thầm rơi về mặc định
   (hai bản clone cùng rơi về 8360 sẽ giành cổng của nhau).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from runtime_ports import MAX_PORT, MIN_PORT, PortConfigError, resolve_port

ROOT = Path(__file__).resolve().parent.parent

CANONICAL = [("AGENT_PORT", 8360), ("BOT_GATEWAY_PORT", 8361)]


# ── resolve_port: nhánh mặc định ───────────────────────────────────────────


@pytest.mark.parametrize(("env_name", "default"), CANONICAL)
def test_khong_set_env_thi_giu_nguyen_cong_hien_hanh(monkeypatch, env_name, default):
    monkeypatch.delenv(env_name, raising=False)

    assert resolve_port(env_name, default) == default


@pytest.mark.parametrize("raw", ["", "   ", "\t"])
def test_env_rong_tinh_la_khong_dat(monkeypatch, raw):
    """docker-compose/systemd hay truyền biến rỗng — đó là "không cấu hình", không phải lỗi."""
    monkeypatch.setenv("AGENT_PORT", raw)

    assert resolve_port("AGENT_PORT", 8360) == 8360


# ── resolve_port: nhánh có env ─────────────────────────────────────────────


@pytest.mark.parametrize(("raw", "expected"), [("9360", 9360), (" 9360 ", 9360), ("80", 80), ("65535", 65535)])
def test_env_hop_le_thang_gia_tri_mac_dinh(monkeypatch, raw, expected):
    monkeypatch.setenv("AGENT_PORT", raw)

    assert resolve_port("AGENT_PORT", 8360) == expected


def test_hai_bien_doc_lap_voi_nhau(monkeypatch):
    monkeypatch.setenv("AGENT_PORT", "9360")
    monkeypatch.delenv("BOT_GATEWAY_PORT", raising=False)

    assert resolve_port("AGENT_PORT", 8360) == 9360
    assert resolve_port("BOT_GATEWAY_PORT", 8361) == 8361


# ── resolve_port: nhánh env rác ────────────────────────────────────────────


@pytest.mark.parametrize("raw", ["abc", "8360.5", "80 80", "0x1f", "eight-thousand"])
def test_gia_tri_khong_phai_so_bao_ro_ten_bien_va_gia_tri(monkeypatch, raw):
    monkeypatch.setenv("AGENT_PORT", raw)

    with pytest.raises(PortConfigError) as exc:
        resolve_port("AGENT_PORT", 8360)

    message = str(exc.value)
    assert "AGENT_PORT" in message, "thông báo phải nói rõ biến nào sai"
    assert raw in message, "thông báo phải in lại giá trị sai để người sửa thấy ngay"
    assert "invalid literal for int()" not in message, "không để lộ lỗi int() trần — vô nghĩa với người vận hành"


@pytest.mark.parametrize("raw", ["0", "-1", "65536", "70000"])
def test_cong_ngoai_khoang_bi_tu_choi(monkeypatch, raw):
    monkeypatch.setenv("BOT_GATEWAY_PORT", raw)

    with pytest.raises(PortConfigError) as exc:
        resolve_port("BOT_GATEWAY_PORT", 8361)

    message = str(exc.value)
    assert "BOT_GATEWAY_PORT" in message
    assert f"{MIN_PORT}-{MAX_PORT}" in message


def test_gia_tri_rac_khong_am_tham_roi_ve_mac_dinh(monkeypatch):
    """Rơi về mặc định = hai bản clone cùng giành 8360; lỗi lộ ra ở tầng khác, khó truy."""
    monkeypatch.setenv("AGENT_PORT", "khong-phai-so")

    with pytest.raises(PortConfigError):
        resolve_port("AGENT_PORT", 8360)


def test_loi_van_la_valueerror(monkeypatch):
    """Code bắt ValueError sẵn có không bị lọt lỗi mới."""
    monkeypatch.setenv("AGENT_PORT", "abc")

    with pytest.raises(ValueError):
        resolve_port("AGENT_PORT", 8360)


# ── Entrypoint thật: import module trong tiến trình con ────────────────────


def _import_entrypoint(module: str, expr: str, **env_overrides: str) -> subprocess.CompletedProcess:
    """Import module entrypoint trong tiến trình con (env sạch, không rò sang test khác).

    Đặt biến = "" thay vì xoá: load_dotenv (override=False) sẽ bỏ qua khoá đã có
    trong env, nên .env của máy dev không lọt vào và test luôn xác định.
    """
    env = {**os.environ, **env_overrides}
    code = f"import sys; sys.path.insert(0, 'agent'); import {module} as m; print('PORT=%s' % ({expr}))"
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
        check=False,
    )


def _clean_env(**overrides: str) -> dict[str, str]:
    env = {name: "" for name, _ in CANONICAL}
    env.update(overrides)
    return env


def test_bot_gateway_khong_set_env_van_la_8361():
    result = _import_entrypoint("bot_gateway", "m.BOT_GATEWAY_PORT", **_clean_env())

    assert result.returncode == 0, result.stderr
    assert "PORT=8361" in result.stdout


def test_bot_gateway_theo_env_rieng_cua_no():
    result = _import_entrypoint(
        "bot_gateway", "m.BOT_GATEWAY_PORT", **_clean_env(BOT_GATEWAY_PORT="9361", AGENT_PORT="9360")
    )

    assert result.returncode == 0, result.stderr
    assert "PORT=9361" in result.stdout


def test_doi_agent_port_khong_keo_bot_gateway_nhay_cong():
    result = _import_entrypoint("bot_gateway", "m.BOT_GATEWAY_PORT", **_clean_env(AGENT_PORT="9360"))

    assert result.returncode == 0, result.stderr
    assert "PORT=8361" in result.stdout, "AGENT_PORT không được điều khiển cổng của bot gateway"


@pytest.mark.parametrize(
    ("module", "expr", "env_name"),
    [
        ("server", "m.AGENT_PORT", "AGENT_PORT"),
        ("bot_gateway", "m.BOT_GATEWAY_PORT", "BOT_GATEWAY_PORT"),
    ],
)
def test_entrypoint_dung_ngay_khi_env_rac(module, expr, env_name):
    """Fail nhanh + nói rõ, thay vì bind nhầm cổng rồi để nginx proxy vào chỗ trống.

    Lỗi ném ở dòng đọc env (ngay sau load_dotenv) nên tiến trình chết TRƯỚC các
    import nặng — rẻ và không đụng DB.
    """
    result = _import_entrypoint(module, expr, **_clean_env(**{env_name: "nam-muoi"}))

    assert result.returncode != 0, "env rác mà vẫn khởi động được là bind sai cổng trong im lặng"
    assert env_name in result.stderr
    assert "nam-muoi" in result.stderr
    assert "invalid literal for int()" not in result.stderr


def test_bot_gateway_dung_bien_port_rieng():
    """`bot_gateway` phải đọc BOT_GATEWAY_PORT, không dùng chung AGENT_PORT.

    Import THẬT (không qua tiến trình con) để R20.7 thấy được cặp
    module↔test: gate quét AST tìm import, nên test chạy subprocess tuy đúng về
    hành vi nhưng không chứng minh được quan hệ này.

    Hai tiến trình dùng chung một biến cổng là bẫy im lặng: bản clone đổi cổng
    agent sẽ vô tình kéo bot gateway nhảy theo rồi đụng cổng nhau.
    """
    import bot_gateway

    assert bot_gateway.BOT_GATEWAY_PORT == 8361
    assert not hasattr(bot_gateway, "AGENT_PORT"), (
        "bot_gateway không được đọc AGENT_PORT — hai tiến trình phải có biến riêng"
    )


def test_server_dung_bien_port_rieng():
    """`server` phải đọc AGENT_PORT, và KHÔNG đọc BOT_GATEWAY_PORT.

    Cùng lý do với test bot_gateway ở trên: import THẬT để R20.7 thấy cặp
    module↔test. Đây là cặp đối xứng — hai tiến trình mỗi cái một biến, không
    cái nào được chạm biến của cái kia.
    """
    import server

    assert server.AGENT_PORT == 8361 - 1
    assert not hasattr(server, "BOT_GATEWAY_PORT"), (
        "server không được đọc BOT_GATEWAY_PORT — hai tiến trình phải có biến riêng"
    )

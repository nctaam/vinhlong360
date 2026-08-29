"""Ranh giới của gói `agent/itineraries/` — gom cơ học, KHÔNG shim (2026-08-29).

Khác 5 lát chương trình module: đây là gom-về-một-mái 5 module vốn đã miền-đơn,
và CHỦ ĐÍCH không để lại shim (bài học §47: gương động sinh cả lớp nhầm lẫn
getsource/monkeypatch). Bộ này khoá đúng các chỗ có thể trôi: đường cũ phải
CHẾT hẳn, consumer phải trỏ cùng-object với nhà mới, gói không import ngược.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chat import api as chat_api  # noqa: E402
import mcp_server  # noqa: E402
import public_api  # noqa: E402
from itineraries import (  # noqa: E402
    itinerary_gen,
    itinerary_multiday,  # noqa: F401  (import được = gói đủ; test cuối kiểm danh sách)
    itinerary_optimizer,
    itinerary_schedule,
    itinerary_selection,  # noqa: F401
)

GOI = Path(itinerary_gen.__file__).resolve().parent


def test_duong_cu_da_chet_khong_con_shim():
    """`import itinerary_gen` phẳng phải nổ — không shim, không file rơi rớt."""
    for ten in ("itinerary_gen", "itinerary_multiday", "itinerary_optimizer",
                "itinerary_schedule", "itinerary_selection"):
        assert ten not in sys.modules or sys.modules[ten].__name__.startswith(
            "itineraries."
        ), f"{ten} còn bản phẳng trong sys.modules"
        try:
            importlib.import_module(ten)
        except ModuleNotFoundError:
            continue
        raise AssertionError(f"đường phẳng `import {ten}` vẫn sống — còn file cũ/shim")


def test_consumer_tro_cung_object_voi_nha_moi():
    assert chat_api.generate_itinerary is itinerary_gen.generate_itinerary
    assert public_api.optimize_stop_order is itinerary_optimizer.optimize_stop_order
    assert public_api.parse_opening_hours is itinerary_schedule.parse_opening_hours
    # mcp_server import trong hàm (lazy) — kiểm nó resolve về đúng nhà mới.
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "from itineraries.itinerary_gen import" in src


def test_KHONG_import_nguoc():
    XAU = ("server", "admin", "chat", "community", "identity", "llmops",
           "entities", "public_api", "mcp_server")
    bad = []
    for f in GOI.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                bad += [f"{f.name}:{a.name}" for a in n.names
                        if a.name.split(".")[0] in XAU]
            elif isinstance(n, ast.ImportFrom) and n.module:
                if n.module.split(".")[0] in XAU:
                    bad.append(f"{f.name}:{n.module}")
    assert not bad, f"itineraries/ import xấu: {bad}"


def test_du_nam_module_trong_goi():
    co = {f.stem for f in GOI.glob("itinerary_*.py")}
    assert co == {"itinerary_gen", "itinerary_multiday", "itinerary_optimizer",
                  "itinerary_schedule", "itinerary_selection"}

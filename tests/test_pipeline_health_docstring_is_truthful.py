"""Docstring không được khẳng định module đang được dùng nếu không nơi nào dùng nó.

pipeline_health.py từng mở đầu bằng "Used by /health endpoint and monitoring".
Không handler /health nào gọi tới nó; tham chiếu duy nhất là một file test. Nhãn
sai kiểu này khiến người đọc (và cả một đợt audit) tin rằng hệ thống có giám sát
pipeline trong khi thực tế không có.

Test đi hai chiều nên không cản trở việc nối module vào /health sau này: nếu có
handler thật sự gọi, docstring được phép khẳng định.
"""
import re
from pathlib import Path

AGENT = Path(__file__).resolve().parent.parent / "agent"

CLAIM_RE = re.compile(r"used by\s+/health|used by\s+the\s+/health", re.I)


def _module_docstring(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.match(r'\s*"""(.*?)"""', text, re.S)
    return match.group(1) if match else ""


def _is_called_by_production_code(symbol: str) -> bool:
    for path in AGENT.rglob("*.py"):
        if "tests" in path.parts or path.name == "pipeline_health.py":
            continue
        if symbol in path.read_text(encoding="utf-8", errors="replace"):
            return True
    return False


def test_pipeline_health_does_not_claim_a_wiring_it_does_not_have():
    docstring = _module_docstring(AGENT / "pipeline_health.py")
    claims_health_wiring = bool(CLAIM_RE.search(docstring))

    if claims_health_wiring:
        assert _is_called_by_production_code("pipeline_health"), (
            "docstring khẳng định module phục vụ /health nhưng không file production nào "
            "tham chiếu tới nó — hoặc nối vào thật, hoặc sửa docstring cho đúng"
        )


def test_pipeline_health_docstring_records_its_actual_state():
    docstring = _module_docstring(AGENT / "pipeline_health.py")
    assert "CHƯA được nối" in docstring or _is_called_by_production_code("pipeline_health"), (
        "module chưa được nối vào endpoint nào thì docstring phải nói rõ điều đó"
    )

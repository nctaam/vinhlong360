import importlib.util
import json
from pathlib import Path
import shutil
import re


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "generate_llms_txt.py"
SPEC = importlib.util.spec_from_file_location("generate_llms_txt", SCRIPT_PATH)
assert SPEC and SPEC.loader
generate_llms_txt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_llms_txt)


def test_llms_generator_emits_only_current_vinh_long_children(monkeypatch):
    data_path = Path(__file__).parents[1] / "web" / "data.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    raw_places = [entity for entity in data["entities"] if entity.get("type") == "place"]
    assert len(raw_places) == 125

    output_dir = Path(__file__).parent / "_llms_test_output"
    output_dir.mkdir(exist_ok=True)
    llms_path = output_dir / "llms.txt"
    llms_full_path = output_dir / "llms-full.txt"
    monkeypatch.setattr(generate_llms_txt, "DATA_JSON_PATH", data_path)
    monkeypatch.setattr(generate_llms_txt, "LLMS_TXT_PATH", llms_path)
    monkeypatch.setattr(generate_llms_txt, "LLMS_FULL_TXT_PATH", llms_full_path)

    try:
        generate_llms_txt.main()

        full_text = llms_full_path.read_text(encoding="utf-8")
        ward_section = full_text.split("## 4. Danh Mục 124 Xã/Phường Thuộc Tỉnh Vĩnh Long", 1)[1]
        ward_lines = [line for line in ward_section.splitlines() if line.startswith("- **[")]

        assert len(ward_lines) == 124
        assert not any("(`vinh-long`)" in line for line in ward_lines)

        current_children = [
            entity
            for entity in raw_places
            if entity.get("parentId") == "vinh-long"
            and entity.get("level") in {"xa", "phuong"}
        ]
        assert len(current_children) == 124
        assert sum(entity.get("level") == "phuong" for entity in current_children) == 35
        assert sum(entity.get("level") == "xa" for entity in current_children) == 89
        rendered_ids = {
            match.group(1)
            for line in ward_lines
            if (match := re.search(r"`([^`]+)`", line))
        }
        assert rendered_ids == {entity["id"] for entity in current_children}
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)

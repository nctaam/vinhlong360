"""Prompt sinh ảnh phải mô tả đúng vật thể và đúng đơn vị hành chính hiện hành.

Hai lỗi thật phát hiện khi chạy dry-run:
  1. "Bún nước lèo chợ Ba Tri" mang type 'attraction' nên nhận prompt
     "heritage site, architectural photography" → ảnh kiến trúc cho một tô bún.
  2. Prompt gắn "Ben Tre province" / "Tra Vinh province", trong khi từ 7/2025 chỉ
     còn một tỉnh Vĩnh Long (CLAUDE.md §1.6).
Mỗi ảnh là một lần gọi API mất tiền, nên sai prompt là sai không hoàn lại.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

gen_entity_images = pytest.importorskip("gen_entity_images")


def _prompt(**entity):
    return gen_entity_images.build_prompt(entity)


class TestPromptMatchesSubject:
    @pytest.mark.parametrize("name", [
        "Bún nước lèo chợ Ba Tri",
        "Hủ tiếu Sa Đéc Chú Tư (gần chợ Phú Hưng)",
        "Bánh xèo ốc gạo Phú Đa",
        "Cơm tấm Cầu Kè",
    ])
    def test_food_named_entity_never_gets_architecture_prompt(self, name):
        prompt = _prompt(id="x", name=name, type="attraction", area="ben-tre")

        assert "architectural photography" not in prompt
        assert "heritage site" not in prompt
        assert "food photography" in prompt.lower()

    def test_real_heritage_site_keeps_architecture_prompt(self):
        prompt = _prompt(id="x", name="Chùa Ông Mẹt", type="attraction", area="tra-vinh")

        assert "heritage site" in prompt

    def test_eatery_named_entity_gets_venue_prompt(self):
        prompt = _prompt(id="x", name="Quán ăn Cô Diễm", type="attraction", area="vinh-long")

        assert "architectural photography" not in prompt


class TestPromptUsesCurrentProvince:
    @pytest.mark.parametrize("area", ["vinh-long", "ben-tre", "tra-vinh"])
    def test_never_names_a_dissolved_province(self, area):
        prompt = _prompt(id="x", name="Làng gốm", type="craft_village", area=area)

        assert "Ben Tre province" not in prompt
        assert "Tra Vinh province" not in prompt
        assert "Vinh Long province" in prompt

    def test_keeps_local_area_as_a_place_name_not_a_province(self):
        prompt = _prompt(id="x", name="Cồn Bửng", type="nature", area="ben-tre")

        assert "Ben Tre" in prompt, "vẫn giữ địa danh để ảnh mang đặc trưng bản địa"
        assert "Ben Tre province" not in prompt


class TestImagePathFormat:
    def test_generated_file_and_db_path_use_the_same_webp_extension(self):
        rel = gen_entity_images.entity_image_relpath("cong-vien-an-hoi")

        assert rel == "/img/entities/cong-vien-an-hoi.webp"
        assert gen_entity_images.entity_image_file("cong-vien-an-hoi").name == "cong-vien-an-hoi.webp"

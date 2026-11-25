"""Unit tests for the province configuration layer across backend and check gates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
import database  # noqa: E402
import province_config  # noqa: E402
import realtime  # noqa: E402
import seed_site_settings  # noqa: E402
import seo  # noqa: E402
from scripts.checks.check_content_voice import VoiceCheck, build_checks as build_voice_checks  # noqa: E402
from scripts.checks.check_data_schema import DataSchemaCheck  # noqa: E402
from scripts.checks.check_tinh_cu import TinhCuCheck  # noqa: E402

DONG_THAP_EXAMPLE = ROOT / "config" / "province.dongthap.example.json"


def test_vinhlong_default_config_matches_runtime_contracts(monkeypatch):
    cfg = province_config.load_province_config()
    assert cfg.slug == "vinhlong360"
    assert cfg.site_url == "https://vinhlong360.vn"
    assert cfg.ingest_bbox_tuple == (9.2, 10.65, 105.6, 106.95)
    assert cfg.schema_bbox == {"lat": (9.0, 10.6), "lng": (105.6, 107.1)}
    assert [area.slug for area in cfg.areas] == ["vinh-long", "ben-tre", "tra-vinh"]

    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("ESMS_BRANDNAME", raising=False)
    default_settings = config.Settings(_env_file=None)
    assert default_settings.ESMS_BRANDNAME == "VinhLong360"
    assert "https://vinhlong360.vn" in default_settings.cors_origins_list
    assert set(realtime.AREA_COORDS) == {"vinh-long", "ben-tre", "tra-vinh"}
    assert seo.SITE == "https://vinhlong360.vn"
    assert seo.AREA_NAMES == {
        "vinh-long": "Vĩnh Long",
        "ben-tre": "Bến Tre",
        "tra-vinh": "Trà Vinh",
    }
    assert seed_site_settings.DEFAULTS["branding.site_name"]["value"] == "vinhlong360"
    assert seed_site_settings.DEFAULTS["contact.email"]["value"] == "lienhe@vinhlong360.vn"
    assert seed_site_settings.DEFAULTS["footer.columns"]["value"][2]["links"] == [
        {"to": "/khu-vuc/vinh-long", "label": "Vĩnh Long"},
        {"to": "/khu-vuc/ben-tre", "label": "Bến Tre"},
        {"to": "/khu-vuc/tra-vinh", "label": "Trà Vinh"},
    ]


def test_dongthap_example_supports_two_regions_and_env_override(monkeypatch):
    dt = province_config.load_province_config(DONG_THAP_EXAMPLE)
    assert dt.slug == "dongthap360"
    assert [area.slug for area in dt.areas] == ["dong-thap", "tien-giang"]
    assert dt.ingest_bbox_tuple == (10.05, 11.05, 105.15, 106.9)
    assert "Cái Bè" not in dt.out_of_province_patterns
    assert "Mang Thít" in dt.out_of_province_patterns

    monkeypatch.delenv("REGION_BBOX", raising=False)
    monkeypatch.setenv("PROVINCE_CONFIG_PATH", str(DONG_THAP_EXAMPLE))
    assert database.region_bbox() == (10.05, 11.05, 105.15, 106.9)

    # Explicit REGION_BBOX still takes precedence over PROVINCE_CONFIG_PATH.
    monkeypatch.setenv("REGION_BBOX", "9.0,11.5,105.0,107.0")
    monkeypatch.setattr(database, "_REGION_BBOX_CACHE", None)
    assert database.region_bbox() == (9.0, 11.5, 105.0, 107.0)


def test_invalid_province_config_fails_closed(tmp_path):
    bad_path = tmp_path / "province.config.json"
    payload = json.loads(DONG_THAP_EXAMPLE.read_text(encoding="utf-8"))
    payload["identity"]["siteUrl"] = "http://insecure.example.com"
    bad_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(province_config.ProvinceConfigError, match="https://"):
        province_config.load_province_config(bad_path)

    payload["identity"]["siteUrl"] = "https://dongthap360.vn"
    payload["bounds"]["ingestBbox"]["lat"] = [11.0, 10.0]
    bad_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(province_config.ProvinceConfigError, match="inverted"):
        province_config.load_province_config(bad_path)


def test_checks_honor_cloned_province_config(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "web-nuxt" / "composables").mkdir(parents=True)
    (tmp_path / "web-nuxt" / "pages").mkdir(parents=True)

    (tmp_path / "config" / "province.config.json").write_text(
        DONG_THAP_EXAMPLE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "web-nuxt" / "composables" / "useConstants.ts").write_text(
        "export const TYPE_META = {\n  place: { label: 'Xã/Phường' }\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "web" / "data.json").write_text(
        json.dumps(
            {
                "entities": [
                    {
                        "id": "tram-chim",
                        "type": "place",
                        "name": "Tràm Chim",
                        "summary": "Thắng cảnh vùng Cái Bè và Tháp Mười.",
                        "coordinates": {"lat": 10.72, "lng": 105.52},
                    }
                ],
                "itineraries": [],
            }
        ),
        encoding="utf-8",
    )

    schema_res = DataSchemaCheck(root=tmp_path).run()
    assert schema_res["count"] == 0

    voice_checks = {c.name: c for c in build_voice_checks(root=tmp_path) if isinstance(c, VoiceCheck)}
    assert voice_checks["out_of_province"].run()["count"] == 0

    (tmp_path / "web-nuxt" / "pages" / "bad.vue").write_text(
        "<template><p>Vùng " + "tỉnh Tiền Giang" + " cũ</p></template>\n",
        encoding="utf-8",
    )
    assert TinhCuCheck(root=tmp_path).run()["count"] == 1

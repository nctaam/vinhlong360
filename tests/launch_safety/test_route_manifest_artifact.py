import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "config" / "launch-indexing-policy.json"


def test_route_manifest_contains_exact_reviewed_schema_and_inventory():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert set(manifest) == {
        "schema_version",
        "revision",
        "canonical_origin",
        "unknown_policy",
        "normalization",
        "exact_routes",
        "sensitive_prefixes",
        "backend_ingress_exceptions",
        "dynamic_templates",
    }
    assert manifest["schema_version"] == 1
    assert type(manifest["schema_version"]) is int
    assert manifest["revision"] == "launch-indexing-policy-v1"
    assert manifest["canonical_origin"] == "https://vinhlong360.vn"
    assert manifest["unknown_policy"] == "noindex-follow-public"
    assert manifest["normalization"] == {
        "percent_decode": "utf8-once",
        "encoded_separator_policy": "reject",
        "dot_segment_policy": "reject",
        "repeated_slash_policy": "redirect-canonical",
        "trailing_slash_policy": "redirect-except-root",
        "query_policy": "noindex-except-sitemap-batch",
    }

    expected_exact_routes = [
        {"path": "/", "classification": "indexable-public", "sitemap": True},
        {"path": "/du-lich", "classification": "indexable-public", "sitemap": True},
        {"path": "/dia-diem", "classification": "indexable-public", "sitemap": True},
        {"path": "/san-pham", "classification": "indexable-public", "sitemap": True},
        {"path": "/ocop", "classification": "indexable-public", "sitemap": True},
        {"path": "/luu-tru", "classification": "indexable-public", "sitemap": True},
        {"path": "/le-hoi", "classification": "indexable-public", "sitemap": True},
        {"path": "/su-kien", "classification": "indexable-public", "sitemap": True},
        {"path": "/theo-mua", "classification": "indexable-public", "sitemap": True},
        {"path": "/ban-do", "classification": "indexable-public", "sitemap": True},
        {"path": "/tuyen-duong", "classification": "indexable-public", "sitemap": True},
        {"path": "/danh-ba", "classification": "indexable-public", "sitemap": True},
        {"path": "/gioi-thieu", "classification": "indexable-public", "sitemap": True},
        {"path": "/huong-dan", "classification": "indexable-public", "sitemap": True},
        {
            "path": "/huong-dan-thanh-vien",
            "classification": "indexable-public",
            "sitemap": True,
        },
        {"path": "/lien-he", "classification": "indexable-public", "sitemap": True},
        {
            "path": "/chinh-sach-bao-mat",
            "classification": "indexable-public",
            "sitemap": True,
        },
        {
            "path": "/dieu-khoan-su-dung",
            "classification": "indexable-public",
            "sitemap": True,
        },
        {
            "path": "/kham-pha/am-thuc",
            "classification": "indexable-public",
            "sitemap": True,
        },
        {
            "path": "/kham-pha/thien-nhien",
            "classification": "indexable-public",
            "sitemap": True,
        },
        {
            "path": "/kham-pha/van-hoa",
            "classification": "indexable-public",
            "sitemap": True,
        },
        {
            "path": "/kham-pha/lang-nghe",
            "classification": "indexable-public",
            "sitemap": True,
        },
        {
            "path": "/kham-pha/mua-sam",
            "classification": "indexable-public",
            "sitemap": True,
        },
        {
            "path": "/khu-vuc/vinh-long",
            "classification": "indexable-public",
            "sitemap": True,
        },
        {
            "path": "/khu-vuc/ben-tre",
            "classification": "indexable-public",
            "sitemap": True,
        },
        {
            "path": "/khu-vuc/tra-vinh",
            "classification": "indexable-public",
            "sitemap": True,
        },
        {
            "path": "/tim-kiem",
            "classification": "noindex-follow-public",
            "sitemap": False,
        },
        {
            "path": "/lich-trinh",
            "classification": "noindex-follow-public",
            "sitemap": False,
        },
        {
            "path": "/tao-lich-trinh",
            "classification": "noindex-follow-public",
            "sitemap": False,
        },
        {
            "path": "/cong-dong",
            "classification": "noindex-follow-public",
            "sitemap": False,
        },
        {
            "path": "/bang-xep-hang",
            "classification": "noindex-follow-public",
            "sitemap": False,
        },
    ]
    assert manifest["exact_routes"] == expected_exact_routes
    assert all(type(route["sitemap"]) is bool for route in manifest["exact_routes"])
    exact_paths = [route["path"] for route in manifest["exact_routes"]]
    assert len(exact_paths) == len(set(exact_paths))

    expected_sensitive_prefixes = [
        {"prefix": prefix, "classification": "crawl-blocked-sensitive"}
        for prefix in (
            "/_internal",
            "/admin",
            "/admin-api",
            "/analytics",
            "/api",
            "/auth",
            "/chat",
            "/events",
            "/feedback",
            "/freshness",
            "/health",
            "/reload",
            "/recommend",
            "/seo",
            "/system",
            "/weather",
            "/webhook",
            "/welcome",
            "/cai-dat",
            "/tai-khoan",
            "/da-luu",
            "/thong-bao",
        )
    ]
    assert manifest["sensitive_prefixes"] == expected_sensitive_prefixes
    sensitive_paths = [item["prefix"] for item in manifest["sensitive_prefixes"]]
    assert len(sensitive_paths) == len(set(sensitive_paths))
    assert {
        "/_internal",
        "/admin",
        "/analytics",
        "/api",
        "/system",
        "/webhook",
        "/welcome",
    } <= set(sensitive_paths)

    assert manifest["backend_ingress_exceptions"] == []

    expected_dynamic_templates = [
        {
            "template": "/dia-diem/{entity_id}",
            "authority": "backend-entity",
            "sitemap": "backend",
        },
        {
            "template": "/xa-phuong/{ward_id}",
            "authority": "backend-ward",
            "sitemap": "backend",
        },
        {
            "template": "/bai-viet/{id}",
            "authority": "fixed-noindex",
            "sitemap": False,
        },
        {
            "template": "/nguoi-dung/{id}",
            "authority": "fixed-noindex",
            "sitemap": False,
        },
        {
            "template": "/lich-trinh/{id}",
            "authority": "fixed-noindex",
            "sitemap": False,
        },
        {
            "template": "/lich-trinh-chia-se/{id}",
            "authority": "fixed-noindex",
            "sitemap": False,
        },
    ]
    assert manifest["dynamic_templates"] == expected_dynamic_templates
    assert [type(item["sitemap"]) for item in manifest["dynamic_templates"]] == [
        str,
        str,
        bool,
        bool,
        bool,
        bool,
    ]
    template_paths = [item["template"] for item in manifest["dynamic_templates"]]
    assert len(template_paths) == len(set(template_paths))

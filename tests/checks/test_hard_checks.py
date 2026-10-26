# -*- coding: utf-8 -*-
"""Test 4 module HARD (SP01 T3) — fixture vi-phạm bị bắt / sạch pass / neg-context pass."""
import json
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_api_contract import ApiContractCheck  # noqa: E402
from checks.check_banned_claims import build_checks as banned_checks  # noqa: E402
from checks.check_data_schema import DataSchemaCheck, DataStoreHashGuard  # noqa: E402
from checks.check_secrets import SecretsCheck  # noqa: E402
from checks.check_entity_image_renderers import EntityImageRendererCheck  # noqa: E402


def _mk(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_entity_image_renderer_check_runs_full_scan_for_relevant_staged_registry(tmp_path):
    _mk(tmp_path, "web-nuxt/config/entity-image-renderers.json", '{"schema_version": 1, "renderers": []}\n')
    _mk(tmp_path, "web-nuxt/pages/new.vue", '<NuxtImg :src="entity.images[0]" />\n')
    result = EntityImageRendererCheck(root=tmp_path).run(files=["web-nuxt/config/entity-image-renderers.json"])
    assert result["level"] == "hard"
    assert result["rule"] == "R20.10"
    assert any(item["code"] == "UNREGISTERED_ENTITY_IMAGE_RENDERER" for item in result["violations"])


def test_entity_image_renderer_check_ignores_irrelevant_staged_files(tmp_path):
    result = EntityImageRendererCheck(root=tmp_path).run(files=["docs/README.md"])
    assert result["count"] == 0


# ---------- secrets ----------

def test_secrets_catches_hardcoded_key(tmp_path):
    _mk(tmp_path, "agent/x.py", 'API_KEY = "sk-abcdefghijklmnop1234"\n')
    r = SecretsCheck(root=tmp_path).run()
    assert r["count"] == 1 and r["level"] == "hard"


def test_secrets_env_staged_blocked(tmp_path):
    r = SecretsCheck(root=tmp_path).run(files=[".env"])
    assert r["count"] == 1 and ".env" in r["violations"][0]["file"]


def test_secrets_allows_env_read_and_example(tmp_path):
    _mk(tmp_path, "agent/x.py", 'API_KEY = os.environ.get("IMAGE_API_KEY", "")\n')
    _mk(tmp_path, ".env.example", 'ADMIN_API_KEY="your_key_here_example_1234567890"\n')
    assert SecretsCheck(root=tmp_path).run()["count"] == 0


# Hồi quy 2026-08-05: hai đường lách đã đo được của R70.1.

@pytest.mark.parametrize("name", [".env.production", ".env.local", ".env.prod", "deploy/.env.staging"])
def test_secrets_blocks_every_env_variant(tmp_path, name):
    """Chỉ chặn đúng `.env` là hụt — biến thể mới là nơi chứa secret PROD.

    `.env.production` vừa thoát chặn tuyệt đối, vừa rớt khỏi bộ lọc đuôi file,
    nên trước bản vá nó không được quét lấy một dòng.
    """
    _mk(tmp_path, name, "LLM_API_KEY=sk-live-XXXXXXXXXXXXXXXXXXXX\n")
    result = SecretsCheck(root=tmp_path).run(files=[name])
    assert result["count"] == 1, f"{name} lọt cổng R70.1"


@pytest.mark.parametrize("name", [".env.example", ".env.sample", ".env.template", ".env.dist"])
def test_secrets_still_allows_env_templates(tmp_path, name):
    _mk(tmp_path, name, "LLM_API_KEY=your_key_here\n")
    assert SecretsCheck(root=tmp_path).run(files=[name])["count"] == 0


def test_secrets_catches_key_wrapped_in_html_tag(tmp_path):
    """Thẻ HTML không phải placeholder: `<div>` từng miễn trừ cả dòng."""
    _mk(tmp_path, "web-nuxt/leak.vue",
        '<div>API_KEY = "sk-live-AAAAAAAAAAAAAAAAAAAAAAAA"</div>\n')
    result = SecretsCheck(root=tmp_path).run(files=["web-nuxt/leak.vue"])
    assert result["count"] == 1, "secret bọc trong thẻ HTML vẫn lọt"


@pytest.mark.parametrize("line", [
    'API_KEY = "<YOUR_API_KEY_HERE>"\n',
    'token: "<REPLACE_ME>"\n',
])
def test_secrets_still_allows_uppercase_placeholders(tmp_path, line):
    _mk(tmp_path, "agent/doc.py", line)
    assert SecretsCheck(root=tmp_path).run(files=["agent/doc.py"])["count"] == 0


# ---------- banned claims ----------

def test_banned_claims_catches_verify_claim_and_image_source(tmp_path):
    _mk(tmp_path, "web-nuxt/pages/x.vue", "<p>1.532 điểm đến đã xác minh</p>\n")
    _mk(tmp_path, "docs/guide.md", "Lấy ảnh từ Pexels cho đẹp\n")
    _mk(tmp_path, "web-nuxt/composables/useConstants.ts", "export const TYPE_META = {\n}\n")
    results = [c.run() for c in banned_checks(root=tmp_path)]
    by_rule = {r["rule"]: r["count"] for r in results}
    assert by_rule["R40.3"] == 1 and by_rule["R10.6"] == 1


def test_banned_claims_neg_context_and_archive_pass(tmp_path):
    _mk(tmp_path, "docs/a.md", "CẤM claim đã xác minh khi verifiedAt = 0\n")
    _mk(tmp_path, "docs/archive/old.md", "ảnh Wikimedia rất đẹp\n")
    results = [c.run() for c in banned_checks(root=tmp_path)]
    assert all(r["count"] == 0 for r in results)


def _image_source_policy_result(
    tmp_path: Path, entity: dict, files: list[str] | None = None
) -> dict:
    _mk(
        tmp_path,
        "web/data.json",
        json.dumps(
            {"entities": [entity], "relationships": [], "itineraries": []},
            ensure_ascii=False,
        ),
    )
    return next(
        result
        for result in (check.run(files=files) for check in banned_checks(root=tmp_path))
        if result["rule"] == "R10.6"
    )


def test_image_source_policy_allows_attributed_press_photo(tmp_path):
    result = _image_source_policy_result(tmp_path, {
        "id": "bao-chi-hop-le",
        "images": ["/img/entities/bao-chi-hop-le.webp"],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Nguyễn Văn A",
            "image_source": "Báo Vĩnh Long",
            "image_license": "CC BY 4.0",
            "image_source_url": "https://baovinhlong.com.vn/images/bao-chi-hop-le.webp",
        },
    })

    assert result["count"] == 0


def test_image_source_policy_rejects_generic_urls_and_copyright_text(tmp_path):
    result = _image_source_policy_result(tmp_path, {
        "id": "bao-chi-generic-evidence",
        "images": ["/img/entities/bao-chi-generic-evidence.webp"],
        "source": [{"url": "https://baovinhlong.com.vn/articles/story"}],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Nguyễn Văn A",
            "image_source": "Báo Vĩnh Long",
            "image_license": "Copyright Publisher",
            "source_citations": [
                {"url": "https://baovinhlong.com.vn/articles/citation"}
            ],
        },
    })

    assert result["count"] == 1
    message = result["violations"][0]["msg"]
    assert "image_license" in message
    assert "URL nguồn" in message


def test_image_source_policy_rejects_placeholder_source_url(tmp_path):
    result = _image_source_policy_result(tmp_path, {
        "id": "bao-chi-placeholder-url",
        "images": ["/img/entities/bao-chi-placeholder-url.webp"],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Nguyễn Văn A",
            "image_source": "Báo Vĩnh Long",
            "image_license": "Được phép sử dụng khi ghi nguồn",
            "image_source_url": "https://example.test/source",
        },
    })

    assert result["count"] == 1
    assert "placeholder" in result["violations"][0]["msg"]


@pytest.mark.parametrize("host", ["127.0.0.2", "[::1]", "10.25.0.8"])
def test_image_source_policy_rejects_non_public_ip_source_url(tmp_path, host):
    result = _image_source_policy_result(tmp_path, {
        "id": "bao-chi-private-ip-url",
        "images": ["/img/entities/bao-chi-private-ip-url.webp"],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Nguyễn Văn A",
            "image_source": "Báo Vĩnh Long",
            "image_license": "Được phép sử dụng khi ghi nguồn",
            "image_source_url": f"https://{host}/source",
        },
    })

    assert result["count"] == 1
    assert "placeholder" in result["violations"][0]["msg"]


@pytest.mark.parametrize(
    "url",
    [
        "https://intranet/source",
        "https://rights.corp/source",
        "https://2130706433/source",
        "https://[::1/source",
    ],
)
def test_image_source_policy_fails_closed_for_non_public_or_malformed_urls(
    tmp_path, url
):
    result = _image_source_policy_result(tmp_path, {
        "id": "bao-chi-non-public-url",
        "images": ["/img/entities/bao-chi-non-public-url.webp"],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Nguyễn Văn A",
            "image_source": "Báo Vĩnh Long",
            "image_license": "CC BY 4.0",
            "image_source_url": url,
        },
    })

    assert result["count"] == 1
    assert "URL nguồn" in result["violations"][0]["msg"]


def test_local_source_url_fails_closed(tmp_path):
    result = _image_source_policy_result(tmp_path, {
        "id": "local-source",
        "images": ["/img/entities/local-source.webp"],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Author",
            "image_source": "Publisher",
            "image_license": "CC BY 4.0",
            "image_source_url": "https://printer.local/image.webp",
        },
    })
    assert result["count"] == 1
    assert "URL nguồn" in result["violations"][0]["msg"]


@pytest.mark.parametrize(
    "host",
    ["foo.example.test", "foo.example.com", "foo.example.net", "foo.example.org", "foo.localhost", "foo.localdomain"],
)
def test_image_source_policy_rejects_placeholder_subdomains(tmp_path, host):
    result = _image_source_policy_result(tmp_path, {
        "id": f"bao-chi-{host.replace('.', '-')}",
        "images": ["/img/entities/placeholder-subdomain.webp"],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Nguyễn Văn A",
            "image_source": "Báo Vĩnh Long",
            "image_license": "Được phép sử dụng khi ghi nguồn",
            "image_source_url": f"https://{host}/source",
        },
    })

    assert result["count"] == 1
    assert "placeholder" in result["violations"][0]["msg"]


def test_image_source_policy_rejects_malformed_source_url(tmp_path):
    result = _image_source_policy_result(tmp_path, {
        "id": "bao-chi-malformed-url",
        "images": ["/img/entities/bao-chi-malformed-url.webp"],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Nguyễn Văn A",
            "image_source": "Báo Vĩnh Long",
            "image_license": "Được phép sử dụng khi ghi nguồn",
            "image_source_url": "https://",
        },
    })

    assert result["count"] == 1
    assert "URL nguồn" in result["violations"][0]["msg"]


def test_image_source_policy_rejects_generic_placeholder_article_url(tmp_path):
    result = _image_source_policy_result(tmp_path, {
        "id": "bao-chi-generic-placeholder-url",
        "images": ["/img/entities/bao-chi-generic-placeholder-url.webp"],
        "source": [{"url": "https://news.example/article"}],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Nguyễn Văn A",
            "image_source": "Báo Vĩnh Long",
            "image_license": "Được phép sử dụng khi ghi nguồn",
        },
    })

    assert result["count"] == 1
    assert "placeholder" in result["violations"][0]["msg"]


def test_image_source_policy_blocks_unlisted_press_photo_without_source_url(tmp_path):
    result = _image_source_policy_result(tmp_path, {
        "id": "bao-chi-chua-co-url",
        "images": ["/img/entities/bao-chi-chua-co-url.webp"],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Nguyễn Văn A",
            "image_source": "Báo Vĩnh Long",
            "image_license": "Được phép sử dụng khi ghi nguồn",
        },
    })

    assert result["count"] == 1
    assert "URL nguồn" in result["violations"][0]["msg"]


def test_image_source_policy_allows_exact_legacy_url_debt_id(tmp_path):
    _mk(tmp_path, "docs/standards/r10.6-image-url-debt.txt", "bao-chi-no-url-cu\n")
    result = _image_source_policy_result(tmp_path, {
        "id": "bao-chi-no-url-cu",
        "images": ["/img/entities/bao-chi-no-url-cu.webp"],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Nguyễn Văn A",
            "image_source": "Báo Vĩnh Long",
            "image_license": "CC BY 4.0",
        },
    })

    assert result["count"] == 0


def test_image_source_policy_rechecks_data_when_url_debt_file_is_staged(tmp_path):
    result = _image_source_policy_result(
        tmp_path,
        {
            "id": "bao-chi-no-url-moi",
            "images": ["/img/entities/bao-chi-no-url-moi.webp"],
            "attributes": {
                "image_type": "documentary",
                "is_verified_photo": True,
                "image_author": "Nguyễn Văn A",
                "image_source": "Báo Vĩnh Long",
                "image_license": "Được phép sử dụng khi ghi nguồn",
            },
        },
        files=["docs/standards/r10.6-image-url-debt.txt"],
    )

    assert result["count"] == 1
    assert "URL nguồn" in result["violations"][0]["msg"]


def test_image_source_policy_blocks_press_photo_without_attribution(tmp_path):
    result = _image_source_policy_result(tmp_path, {
        "id": "bao-chi-thieu-ghi-nguon",
        "images": ["/img/entities/bao-chi-thieu-ghi-nguon.webp"],
        "source": [],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
        },
    })

    assert result["count"] == 1
    message = result["violations"][0]["msg"]
    assert "image_author" in message
    assert "image_source" in message
    assert "image_license" in message
    assert "URL nguồn" in message


def test_image_source_policy_rejects_ai_image_marked_as_verified_photo(tmp_path):
    result = _image_source_policy_result(tmp_path, {
        "id": "anh-ai-ghi-sai-loai",
        "images": ["/img/entities/anh-ai-ghi-sai-loai.webp"],
        "attributes": {
            "image_type": "ai-generated",
            "is_verified_photo": True,
        },
    })

    assert result["count"] == 1
    assert "AI-generated" in result["violations"][0]["msg"]


def test_current_image_source_policy_revokes_batch_21_legacy_compatibility():
    result = next(
        check.run()
        for check in banned_checks(root=ROOT)
        if check.rule == "R10.6"
    )

    assert result["count"] == 40
    assert any("prov-1" in violation["msg"] for violation in result["violations"])


def test_banned_tailwind_in_web_nuxt(tmp_path):
    _mk(tmp_path, "web-nuxt/package.json", '{"dependencies": {"tailwindcss": "^3"}}\n')
    results = {r["rule"]: r["count"] for r in (c.run() for c in banned_checks(root=tmp_path))}
    assert results["R30.1"] == 1


# ---------- data schema ----------

TYPE_META_TS = """export const TYPE_META = {
  dish: { emoji: 'x', icon: 'bowl', label: 'Món', cat: 'food' },
  place: { emoji: 'x', icon: 'pin', label: 'Nơi', cat: 'place' },
}
"""


def _mk_data(tmp_path, entities):
    _mk(tmp_path, "web-nuxt/composables/useConstants.ts", TYPE_META_TS)
    _mk(tmp_path, "web/data.json", json.dumps({"entities": entities, "relationships": [], "itineraries": []}, ensure_ascii=False))


def test_data_schema_pass_clean(tmp_path):
    _mk_data(tmp_path, [{"id": "a", "type": "dish", "name": "A", "summary": "s", "coordinates": {"lat": 10.0, "lng": 106.0}}])
    assert DataSchemaCheck(root=tmp_path).run()["count"] == 0


def test_data_schema_catches_dup_badtype_missing_bbox(tmp_path):
    _mk_data(tmp_path, [
        {"id": "a", "type": "dish", "name": "A", "summary": "s"},
        {"id": "a", "type": "hotel", "name": "", "summary": "s", "coordinates": {"lat": 21.0, "lng": 105.8}},
    ])
    r = DataSchemaCheck(root=tmp_path).run()
    msgs = " | ".join(v["msg"] for v in r["violations"])
    assert "id trùng" in msgs and "ngoài enum" in msgs and "thiếu trường" in msgs and "ngoài bbox" in msgs


def test_data_schema_skips_when_not_staged(tmp_path):
    _mk_data(tmp_path, [{"id": "a", "type": "hotel", "name": "A", "summary": "s"}])
    assert DataSchemaCheck(root=tmp_path).run(files=["agent/x.py"])["count"] == 0


def test_data_store_hash_all_ignores_untracked_runtime_db(tmp_path):
    _mk(tmp_path, "agent/data/vinhlong360.db", "mutable local runtime state")

    result = DataStoreHashGuard(root=tmp_path).run()

    assert result["count"] == 0


def test_data_store_hash_checks_db_when_explicitly_requested(tmp_path):
    db_rel = "agent/data/vinhlong360.db"
    _mk(tmp_path, db_rel, "unexpected database bytes")

    result = DataStoreHashGuard(root=tmp_path).run(files=[db_rel])

    assert result["count"] == 1
    assert result["violations"][0]["file"] == db_rel


# ---------- R10.3b per-type required (SP2 T3) ----------

def test_typed_required_catches_missing_person_role(tmp_path):
    from checks.check_data_schema import DataTypedRequiredCheck

    _mk_data(tmp_path, [
        {"id": "p1", "type": "person", "name": "A", "summary": "s", "attributes": {}},
        {"id": "p2", "type": "person", "name": "B", "summary": "s", "attributes": {"role": "nghệ nhân"}},
        {"id": "d1", "type": "dish", "name": "C", "summary": "s", "attributes": {}},
    ])
    r = DataTypedRequiredCheck(root=tmp_path).run()
    assert r["level"] == "hard-ratchet" and r["rule"] == "R10.3b"
    assert r["count"] == 1 and "p1" in r["violations"][0]["msg"]


def test_typed_required_skips_when_not_staged(tmp_path):
    from checks.check_data_schema import DataTypedRequiredCheck

    _mk_data(tmp_path, [{"id": "p1", "type": "person", "name": "A", "summary": "s", "attributes": {}}])
    assert DataTypedRequiredCheck(root=tmp_path).run(files=["agent/x.py"])["count"] == 0


# ---------- R10.8 RICH-source (SP2 T3) ----------

RICH_TEXT = "chữ " * 140  # ≥130 từ → entity indexable


def test_rich_source_catches_rich_entity_without_source(tmp_path):
    from checks.check_data_schema import DataRichSourceCheck

    _mk_data(tmp_path, [
        {"id": "rich-0src", "type": "dish", "name": "A", "status": "published", "verified": True,
         "summary": "s", "description": RICH_TEXT, "source": []},
        {"id": "rich-ok", "type": "dish", "name": "B", "status": "published", "verified": True,
         "summary": "s", "description": RICH_TEXT,
         "source": [{"url": "https://baovinhlong.com.vn/bai-viet"}]},
        {"id": "thin-0src", "type": "dish", "name": "C", "status": "published", "verified": True,
         "summary": "s", "description": "ngắn", "source": []},
        {"id": "private-rich", "type": "dish", "name": "D", "status": "private", "verified": True,
         "summary": "s", "description": RICH_TEXT, "source": []},
        {"id": "ai-100", "type": "dish", "name": "E", "status": "published", "verified": True,
         "summary": "chữ " * 100, "images": ["/img/ai.webp"], "source": []},
    ])
    r = DataRichSourceCheck(root=tmp_path).run()
    assert r["level"] == "hard-ratchet" and r["rule"] == "R10.8"
    assert r["count"] == 1 and "rich-0src" in r["violations"][0]["msg"]
    assert r["violations"][0]["code"] == "external-source-missing"


def test_rich_source_rejects_self_and_title_only_sources(tmp_path):
    from checks.check_data_schema import DataRichSourceCheck

    _mk_data(tmp_path, [
        {"id": "rich-self", "type": "dish", "name": "A", "status": "published", "verified": True,
         "summary": "s", "description": RICH_TEXT,
         "source": [{"url": "https://vinhlong360.vn/dia-diem/a"}]},
        {"id": "rich-title", "type": "dish", "name": "B", "status": "published", "verified": True,
         "summary": "s", "description": RICH_TEXT,
         "source": [{"title": "Manual review"}]},
    ])

    result = DataRichSourceCheck(root=tmp_path).run()

    assert result["count"] == 2
    assert [violation["code"] for violation in result["violations"]] == [
        "external-source-missing",
        "external-source-missing",
    ]


def test_rich_source_reports_structured_policy_artifact_load_failure(
    tmp_path,
    monkeypatch,
):
    from checks.check_data_schema import DataRichSourceCheck

    monkeypatch.syspath_prepend(str(ROOT / "agent"))
    import launch_evidence

    def fail_to_load_evidence():
        raise RuntimeError("sensitive artifact path")

    monkeypatch.setattr(
        launch_evidence,
        "current_policy_evidence",
        fail_to_load_evidence,
    )
    _mk_data(tmp_path, [])

    result = DataRichSourceCheck(root=tmp_path).run()

    assert result["count"] == 1
    violation = result["violations"][0]
    assert violation["code"] == "index-policy-artifact-load-failed"
    assert "RuntimeError" in violation["msg"]
    assert "sensitive artifact path" not in violation["msg"]


def test_rich_source_checks_policy_artifacts_without_data_json_staged(
    tmp_path,
    monkeypatch,
):
    from checks.check_data_schema import DataRichSourceCheck

    monkeypatch.syspath_prepend(str(ROOT / "agent"))
    import launch_evidence

    def fail_to_load_evidence():
        raise RuntimeError("sensitive artifact path")

    monkeypatch.setattr(
        launch_evidence,
        "current_policy_evidence",
        fail_to_load_evidence,
    )

    result = DataRichSourceCheck(root=tmp_path).run(
        files=["agent/launch_evidence.py"]
    )

    assert result["count"] == 1
    violation = result["violations"][0]
    assert violation["code"] == "index-policy-artifact-load-failed"
    assert "RuntimeError" in violation["msg"]
    assert "sensitive artifact path" not in violation["msg"]


def test_rich_source_uses_the_central_index_policy_not_seo():
    from checks.check_data_schema import DataRichSourceCheck

    source = inspect.getsource(DataRichSourceCheck.check_entities)
    assert "from index_policy import decide_entity" in source
    assert "from launch_evidence import current_policy_evidence" in source
    assert "from source_policy import has_external_source_url" in source
    assert "from seo" not in source


def test_rich_source_skips_when_not_staged(tmp_path):
    from checks.check_data_schema import DataRichSourceCheck

    _mk_data(tmp_path, [{"id": "r", "type": "dish", "name": "A", "summary": "s",
                         "description": RICH_TEXT, "source": []}])
    assert DataRichSourceCheck(root=tmp_path).run(files=["agent/x.py"])["count"] == 0


# ---------- api contract ----------

def _git(root, *args):
    subprocess.run(["git", *args], cwd=str(root), check=True, capture_output=True)


def _mk_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    _mk(tmp_path, "agent/server.py", "x = 1\n")
    _mk(tmp_path, "docs/api-contract.md", "# contract\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def test_api_contract_blocks_route_change_without_contract(tmp_path):
    repo = _mk_repo(tmp_path)
    _mk(repo, "agent/server.py", 'x = 1\n@router.get("/new")\ndef new(): ...\n')
    _git(repo, "add", "agent/server.py")
    r = ApiContractCheck(root=repo).run(files=["agent/server.py"])
    assert r["count"] == 1


def test_api_contract_passes_with_contract_staged(tmp_path):
    repo = _mk_repo(tmp_path)
    _mk(repo, "agent/server.py", 'x = 1\n@router.get("/new")\ndef new(): ...\n')
    _mk(repo, "docs/api-contract.md", "# contract\n/new\n")
    _git(repo, "add", "-A")
    r = ApiContractCheck(root=repo).run(files=["agent/server.py", "docs/api-contract.md"])
    assert r["count"] == 0


def test_api_contract_passes_non_route_change(tmp_path):
    repo = _mk_repo(tmp_path)
    _mk(repo, "agent/server.py", "x = 2\n")
    _git(repo, "add", "agent/server.py")
    assert ApiContractCheck(root=repo).run(files=["agent/server.py"])["count"] == 0


def test_api_contract_survives_vietnamese_diff(tmp_path):
    """Windows cp1252: diff UTF-8 tiếng Việt từng làm stdout=None → crash hook."""
    repo = _mk_repo(tmp_path)
    _mk(repo, "agent/server.py", 'x = 1\n# Trường học — bến phà Đình Khao, chợ nổi Trà Ôn ọp ẹp\n@router.get("/moi")\ndef moi(): ...\n')
    _git(repo, "add", "agent/server.py")
    r = ApiContractCheck(root=repo).run(files=["agent/server.py"])
    assert r["count"] == 1  # route mới thiếu contract vẫn bị bắt, không crash


def test_net_route_changes_ignores_moved_route():
    """Extract-method dời decorator: cùng route ở CẢ +/- → net rỗng (hết false-positive)."""
    from checks.check_api_contract import _route_changes
    diff = ('-@router.get("/homepage",\n'
            '+@router.get("/homepage",\n'
            '-@router.get("/entities/{id}/gallery",\n'
            '+@router.get("/entities/{id}/gallery",\n')
    added, removed = _route_changes(diff)
    assert added == set() and removed == set()


def test_net_route_changes_flags_real_add_and_method_change():
    from checks.check_api_contract import _route_changes
    added, removed = _route_changes('+@router.post("/new")\n')
    assert added == {"POST /new"} and removed == set()

    # đổi method cùng path = đổi hợp đồng → bắt cả 2 chiều, và phân biệt được
    # chiều nào là thêm, chiều nào là xoá để đối chiếu nội dung hợp đồng.
    added, removed = _route_changes('-@router.get("/x")\n+@router.post("/x")\n')
    assert added == {"POST /x"} and removed == {"GET /x"}


def test_r207_ghep_goi_python_bang_ten_thu_muc():
    """`agent/chat/__init__.py` co stem `__init__` — khong test nao mang ten do.

    Khong sua thi MOI GOI Python deu truot R20.7 du da co test day du: cai gia
    la hoac phai SKIP cong, hoac phai de mot file `test___init__.py` vo nghia.
    Phat hien khi boc `agent/chat/` (2026-08-27); `agent/cases/` cung dinh.
    """
    from checks.check_test_pairing import CHECKS as pairing

    chk = pairing[0]
    assert chk._module_name("agent/chat/__init__.py") == "chat"
    assert chk._module_name("agent/cases/__init__.py") == "cases"
    assert chk._module_name("agent/server.py") == "server"
    # va ghep duoc voi test dat ten theo goi
    assert chk._filename_pairs("chat", "agent/tests/test_chat_smoke.py")
    assert not chk._filename_pairs("chat", "agent/tests/test_server_models.py")

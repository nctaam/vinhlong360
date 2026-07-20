# -*- coding: utf-8 -*-
"""TDD contract for the repository-wide entity image renderer guard."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_entity_image_renderers import (  # noqa: E402
    EntityImageRendererCheck,
    Finding,
    group_validated_registry_entries,
    scan_entity_image_renderers,
)


def _mk(tmp_path: Path, rel: str, text: str) -> Path:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _codes(findings: list[Finding]) -> set[str]:
    return {finding.code for finding in findings}


def _entry(**overrides: str) -> dict[str, str]:
    value = {
        "file": "pages/registered.vue",
        "surface": "synthetic",
        "access_path": "entity.images",
        "source_class": "ai-generated",
        "descriptor_producer": "describeEntityImages",
        "presentation": "short",
        "accessibility": "aria-describedby-full-copy",
        "test_file": "tests/registered.test.ts",
    }
    value.update(overrides)
    return value


def test_registry_file_is_required_and_has_strict_top_level_schema(tmp_path: Path):
    result = EntityImageRendererCheck(root=tmp_path).run()
    assert result["count"] == 1
    assert result["violations"][0]["code"] == "MISSING_ENTITY_IMAGE_REGISTRY"

    registry = tmp_path / "web-nuxt" / "config" / "entity-image-renderers.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"schema_version": 2, "renderers": [], "extra": True}), encoding="utf-8")
    result = EntityImageRendererCheck(root=tmp_path).run()
    assert "INVALID_ENTITY_IMAGE_REGISTRY" in {item["code"] for item in result["violations"]}


def test_unregistered_raw_entity_image_access_fails(tmp_path: Path):
    _mk(tmp_path, "pages/new.vue", '<NuxtImg :src="entity.images[0]" />')
    findings = scan_entity_image_renderers(tmp_path, registry=[])
    assert "UNREGISTERED_ENTITY_IMAGE_RENDERER" in _codes(findings)
    assert "RAW_DESCRIPTOR_BYPASS" in _codes(findings)


def test_registration_does_not_exempt_a_raw_renderer(tmp_path: Path):
    _mk(tmp_path, "pages/registered.vue", '<NuxtImg :src="entity.images[0]" />')
    findings = scan_entity_image_renderers(tmp_path, [_entry()])
    assert _codes(findings) >= {
        "RAW_DESCRIPTOR_BYPASS",
        "MISSING_DESCRIPTOR_PRODUCER",
        "MISSING_DISCLOSURE_PRESENTATION",
        "MISSING_ACCESSIBLE_ASSOCIATION",
    }


@pytest.mark.parametrize(
    "source",
    [
        '<NuxtImg :src="entity[\'images\'][0]" />',
        '<script setup>const { images } = entity</script><NuxtImg :src="images[0]" />',
        '<script setup>const pics = entity.images</script><NuxtImg :src="pics?.[0]" />',
        '<div :style="{ backgroundImage: `url(${entity?.images?.[0]})` }" />',
        '<script setup>const pics = entity.value?.[\'images\']; const one = pics?.[0]</script><img :src="one" />',
        '<script setup>const { images: renamed } = entity.value</script><img :src="renamed?.[0]" />',
    ],
)
def test_adversarial_raw_access_forms_cannot_bypass_the_guard(tmp_path: Path, source: str):
    _mk(tmp_path, "pages/adversarial.vue", source)
    codes = _codes(scan_entity_image_renderers(tmp_path, registry=[]))
    assert "UNREGISTERED_ENTITY_IMAGE_RENDERER" in codes
    assert "RAW_DESCRIPTOR_BYPASS" in codes


@pytest.mark.parametrize(
    "source",
    [
        '<img :src="entity.image" />',
        '<NuxtImg :src="item.image_url" />',
        '<Gallery :images="saved.images" />',
        '<ImageLightbox :images="event.images" />',
        '<div :style="{ background: `url(${item.image_urls?.[0]})` }" />',
        '<div style="background-image: url(entity.images[0])" />',
        '<script setup>navigator.share({ image: item.image })</script>',
        '<script setup>const ogImage = item.image; useSeoMeta({ ogImage })</script>',
        '<script setup>const ld = { image: item.images?.[0] }</script>',
    ],
)
def test_all_image_sink_families_are_guarded(tmp_path: Path, source: str):
    _mk(tmp_path, "pages/sinks.vue", source)
    findings = scan_entity_image_renderers(tmp_path, registry=[])
    assert "UNREGISTERED_ENTITY_IMAGE_RENDERER" in _codes(findings)
    assert "RAW_DESCRIPTOR_BYPASS" in _codes(findings)


def test_fixed_point_aliases_distinguish_descriptor_arrays(tmp_path: Path):
    _mk(
        tmp_path,
        "components/aliases.vue",
        """
<script setup lang="ts">
const descriptors = describeEntityImages(entity)
const canonical = descriptors.value
const raw = entity.images
const firstRaw = raw?.[0]
</script>
<img :src="canonical[0].url" />
<img :src="firstRaw" />
<ImageDisclosure :descriptor="canonical[0]" presentation="short" />
""",
    )
    findings = scan_entity_image_renderers(tmp_path, registry=[])
    assert "RAW_DESCRIPTOR_BYPASS" in _codes(findings)
    assert not any(f.code == "RAW_DESCRIPTOR_BYPASS" and "canonical" in f.message for f in findings)


def test_surface_local_short_presentation_requires_linked_full_copy(tmp_path: Path):
    _mk(
        tmp_path,
        "components/surface.vue",
        """
<ImageDisclosure id="one" :descriptor="descriptor" presentation="short" />
<img :src="descriptor.url" aria-describedby="other" />
""",
    )
    findings = scan_entity_image_renderers(
        tmp_path,
        [_entry(file="components/surface.vue", descriptor_producer="descriptor", test_file="tests/surface.test.ts")],
    )
    assert "MISSING_ACCESSIBLE_ASSOCIATION" in _codes(findings)


def test_registered_wrapper_requires_one_hop_delegation_proof(tmp_path: Path):
    _mk(tmp_path, "components/wrapper.vue", "<template><section /></template>")
    findings = scan_entity_image_renderers(
        tmp_path,
        [_entry(file="components/wrapper.vue", surface="wrapper", descriptor_producer="EntityCard", test_file="tests/wrapper.test.ts")],
    )
    assert "MISSING_DELEGATION_PROOF" in _codes(findings)

    _mk(tmp_path, "components/wrapper.vue", "<template><EntityCard :entity=\"entity\" /></template>")
    assert "MISSING_DELEGATION_PROOF" not in _codes(
        scan_entity_image_renderers(
            tmp_path,
            [_entry(file="components/wrapper.vue", surface="wrapper", descriptor_producer="EntityCard", test_file="tests/wrapper.test.ts")],
        )
    )


def test_metadata_proof_requires_full_disclosure_in_exact_consumers(tmp_path: Path):
    _mk(
        tmp_path,
        "pages/metadata.vue",
        """
<script setup lang="ts">
const descriptor = describeEntityImages(entity)[0]
useSeoMeta({ ogImage: buildImageMeta(descriptor).ogImage })
const ld = { image: descriptorToImageObject(descriptor) }
</script>
""",
    )
    findings = scan_entity_image_renderers(
        tmp_path,
        [_entry(file="pages/metadata.vue", surface="metadata", access_path="metadata.image", descriptor_producer="buildImageMeta", presentation="full", accessibility="visible-full-copy", test_file="tests/metadata.test.ts")],
    )
    assert "MISSING_METADATA_DISCLOSURE" in _codes(findings)

    _mk(
        tmp_path,
        "pages/metadata.vue",
        """
<script setup lang="ts">
const descriptor = describeEntityImages(entity)[0]
const meta = buildImageMeta(descriptor)
useSeoMeta({ ogImage: meta.ogImage, ogImageAlt: `${descriptor.alt} — ${descriptor.full_disclosure}`, twitterImageAlt: descriptor.full_disclosure })
const ld = { image: { url: descriptor.url, description: descriptor.full_disclosure } }
</script>
""",
    )
    assert "MISSING_METADATA_DISCLOSURE" not in _codes(
        scan_entity_image_renderers(
            tmp_path,
            [_entry(file="pages/metadata.vue", surface="metadata", access_path="metadata.image", descriptor_producer="buildImageMeta", presentation="full", accessibility="visible-full-copy", test_file="tests/metadata.test.ts")],
        )
    )


def test_map_invariant_scopes_popup_and_every_sethtml_call(tmp_path: Path):
    _mk(
        tmp_path,
        "pages/ban-do.vue",
        """
<template><div class="decorative" /></template>
<script setup>
function popupHTML(name) {
  return `<div data-entity-image-policy="no-image-invariant">${name}</div>`
}
map.on('click', () => popup.setHTML(popupHTML(name)))
</script>
<style>.decorative { background-image: url('/img/map.png'); }</style>
""",
    )
    registry = [_entry(file="pages/ban-do.vue", surface="map-popup", access_path="popup", source_class="none", descriptor_producer="no-image-invariant", presentation="none", accessibility="no-image-invariant", test_file="tests/map.test.ts")]
    assert "BROKEN_NO_IMAGE_INVARIANT" not in _codes(scan_entity_image_renderers(tmp_path, registry))

    _mk(tmp_path, "pages/ban-do.vue", "<script>function popupHTML(){return '<img src=\"x\">'}; popup.setHTML(popupHTML())</script>")
    assert "BROKEN_NO_IMAGE_INVARIANT" in _codes(scan_entity_image_renderers(tmp_path, registry))


@pytest.mark.parametrize(
    "bad",
    [
        _entry(extra="x"),
        {key: value for key, value in _entry().items() if key != "test_file"},
        _entry(file="../pages/evil.vue"),
        _entry(file="C:\\pages\\evil.vue"),
        _entry(file="/pages/evil.vue"),
        _entry(file="components-not-a-root/pages/evil.vue"),
        _entry(source_class="invalid"),
        _entry(presentation="none"),
        _entry(accessibility="no-image-invariant"),
    ],
)
def test_registry_rejects_strict_schema_paths_enums_and_combinations(tmp_path: Path, bad: dict[str, str]):
    _mk(tmp_path, "pages/registered.vue", "<template />")
    _mk(tmp_path, "tests/registered.test.ts", "test('registered', () => {})")
    findings = group_validated_registry_entries(tmp_path, [bad])
    assert any(item.code == "INVALID_ENTITY_IMAGE_REGISTRY" for item in findings)


def test_registry_rejects_duplicates_and_stale_source_or_test(tmp_path: Path):
    duplicate = _entry()
    findings = group_validated_registry_entries(tmp_path, [duplicate, dict(duplicate)])
    assert any(item.code == "DUPLICATE_ENTITY_IMAGE_RENDERER" for item in findings)

    stale = _entry(file="pages/missing.vue", test_file="tests/missing.test.ts")
    findings = group_validated_registry_entries(tmp_path, [stale])
    assert {item.code for item in findings} >= {"MISSING_RENDERER_SOURCE", "MISSING_RENDERER_TEST"}


def test_data_url_preview_is_not_a_generic_exemption(tmp_path: Path):
    _mk(tmp_path, "pages/upload.vue", '<img :src="entity.image" /> <!-- data:image/jpeg;base64 -->')
    assert "RAW_DESCRIPTOR_BYPASS" in _codes(scan_entity_image_renderers(tmp_path, registry=[]))


def test_staged_relevant_change_runs_full_registry_scan(tmp_path: Path):
    _mk(tmp_path, "web-nuxt/config/entity-image-renderers.json", '{"schema_version": 1, "renderers": []}')
    _mk(tmp_path, "web-nuxt/pages/new.vue", '<img :src="entity.images[0]" />')
    result = EntityImageRendererCheck(root=tmp_path).run(files=["web-nuxt/config/entity-image-renderers.json"])
    assert result["count"] > 0
    assert any(item["code"] == "UNREGISTERED_ENTITY_IMAGE_RENDERER" for item in result["violations"])


def test_repository_wide_scan_catches_layout_raw_renderer(tmp_path: Path):
    _mk(tmp_path, "layouts/default.vue", '<template><NuxtImg :src="entity.images[0]" /></template>')
    codes = _codes(scan_entity_image_renderers(tmp_path, registry=[]))
    assert {"UNREGISTERED_ENTITY_IMAGE_RENDERER", "RAW_DESCRIPTOR_BYPASS"} <= codes


@pytest.mark.parametrize(
    "source_file",
    ["layouts/default.vue", "plugins/images.client.ts", "server/api/images.ts", "app/gallery.vue", "error.vue"],
)
def test_registry_accepts_repository_wide_frontend_source_paths(tmp_path: Path, source_file: str):
    _mk(tmp_path, source_file, "export default {}")
    _mk(tmp_path, "tests/source.test.ts", "test('source', () => {})")
    findings = group_validated_registry_entries(
        tmp_path,
        [_entry(file=source_file, test_file="tests/source.test.ts")],
    )
    assert "INVALID_ENTITY_IMAGE_REGISTRY" not in _codes(findings)


def test_registration_cannot_cover_cross_root_generic_thumbnail_sink(tmp_path: Path):
    _mk(tmp_path, "pages/registered.vue", '<template><Card :thumbnail="post.images[0]" /></template>')
    findings = scan_entity_image_renderers(tmp_path, [_entry()])
    assert {"UNREGISTERED_ENTITY_IMAGE_RENDERER", "RAW_DESCRIPTOR_BYPASS"} <= _codes(findings)


def test_singular_props_image_is_not_a_raw_access_exemption(tmp_path: Path):
    _mk(tmp_path, "pages/props.vue", '<template><NuxtImg :src="props.image" /></template>')
    codes = _codes(scan_entity_image_renderers(tmp_path, registry=[]))
    assert {"UNREGISTERED_ENTITY_IMAGE_RENDERER", "RAW_DESCRIPTOR_BYPASS"} <= codes


def test_presentation_and_accessibility_are_scoped_to_source_row(tmp_path: Path):
    _mk(
        tmp_path,
        "pages/scoped.vue",
        """
<template>
  <section data-image-surface="cards" data-source-class="ai-generated">
    <NuxtImg :src="ai.url" aria-describedby="ai-copy" />
    <ImageDisclosure id="ai-copy" :descriptor="ai" presentation="short" />
  </section>
  <section data-image-surface="cards" data-source-class="placeholder">
    <NuxtImg :src="placeholder.url" aria-describedby="placeholder-copy" />
  </section>
</template>
<script setup>
const ai = describeEntityImages(entity)[0]
const placeholder = describeEntityPlaceholder(entity)
</script>
""",
    )
    registry = [
        _entry(file="pages/scoped.vue", surface="cards", source_class="ai-generated", test_file="tests/scoped.test.ts"),
        _entry(file="pages/scoped.vue", surface="cards", source_class="placeholder", descriptor_producer="describeEntityPlaceholder", test_file="tests/scoped.test.ts"),
    ]
    codes = _codes(scan_entity_image_renderers(tmp_path, registry))
    assert "MISSING_DISCLOSURE_PRESENTATION" in codes
    assert "MISSING_ACCESSIBLE_ASSOCIATION" in codes


def test_source_named_disclosure_cannot_exempt_another_source_row(tmp_path: Path):
    _mk(
        tmp_path,
        "pages/sources.vue",
        """
<template>
  <NuxtImg :src="ai.url" aria-describedby="ai-copy" />
  <ImageDisclosure id="ai-copy" :descriptor="ai" presentation="short" />
</template>
<script setup>
const ai = describeEntityImages(entity)[0]
const placeholder = describeEntityPlaceholder(entity)
</script>
""",
    )
    registry = [
        _entry(file="pages/sources.vue", surface="cards", source_class="ai-generated", test_file="tests/sources.test.ts"),
        _entry(file="pages/sources.vue", surface="cards", source_class="placeholder", descriptor_producer="describeEntityPlaceholder", test_file="tests/sources.test.ts"),
    ]
    codes = _codes(scan_entity_image_renderers(tmp_path, registry))
    assert "MISSING_DISCLOSURE_PRESENTATION" in codes
    assert "MISSING_ACCESSIBLE_ASSOCIATION" in codes


def test_post_detail_boundary_requires_postcard_delegation(tmp_path: Path):
    entry = _entry(
        file="pages/bai-viet/[id].vue",
        surface="post-detail-card",
        access_path="post.images",
        source_class="user-uploaded",
        descriptor_producer="PostCard",
        test_file="tests/ugc-image-classification.test.ts",
    )
    _mk(tmp_path, entry["file"], "<template><section /></template><script>const PostCard = 'decoy'</script>")
    assert "MISSING_DELEGATION_PROOF" in _codes(scan_entity_image_renderers(tmp_path, [entry]))

    _mk(tmp_path, entry["file"], '<template><PostCard :post="post" /></template>')
    assert "MISSING_DELEGATION_PROOF" not in _codes(scan_entity_image_renderers(tmp_path, [entry]))

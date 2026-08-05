# -*- coding: utf-8 -*-
"""Test scripts/checks/common.py — nền RegexCheck + ratchet (SP01 T1)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks import common  # noqa: E402


def _mk(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_iter_text_files_prunes_skipped_directories_before_visiting_files(
    tmp_path, monkeypatch
):
    _mk(tmp_path, "web-nuxt/app.ts", "export {}\n")
    ignored = _mk(
        tmp_path,
        "web-nuxt/node_modules/package/ignored.js",
        "const secret = true\n",
    )
    original_is_file = Path.is_file

    def reject_skipped_file(path: Path) -> bool:
        if path == ignored:
            raise AssertionError("iter_text_files descended into node_modules")
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", reject_skipped_file)

    assert common.iter_text_files(
        tmp_path,
        ["*.ts", "*.js"],
        ["web-nuxt"],
        [],
    ) == ["web-nuxt/app.ts"]


def test_iter_text_files_returns_sorted_filtered_repo_relative_paths(tmp_path):
    _mk(tmp_path, "web-nuxt/z.vue", "<template />\n")
    _mk(tmp_path, "web-nuxt/a.ts", "export {}\n")
    _mk(tmp_path, "web-nuxt/generated/skip.ts", "export {}\n")
    _mk(tmp_path, "web-nuxt/readme.md", "ignored\n")

    assert common.iter_text_files(
        tmp_path,
        ["*.ts", "*.vue"],
        ["web-nuxt"],
        ["web-nuxt/generated"],
    ) == ["web-nuxt/a.ts", "web-nuxt/z.vue"]


def test_iter_text_files_excludes_only_exact_paths_and_descendants(tmp_path):
    _mk(tmp_path, "web-nuxt/generated/skip.ts", "export {}\n")
    _mk(tmp_path, "web-nuxt/generated2/keep.ts", "export {}\n")
    _mk(tmp_path, "web-nuxt/generated-manifest.ts", "export {}\n")

    assert common.iter_text_files(
        tmp_path,
        ["*.ts"],
        ["web-nuxt"],
        ["web-nuxt/generated"],
    ) == [
        "web-nuxt/generated-manifest.ts",
        "web-nuxt/generated2/keep.ts",
    ]


def test_iter_text_files_trims_exclude_separators_before_pruning(
    tmp_path, monkeypatch
):
    ignored = _mk(tmp_path, "web-nuxt/generated/skip.ts", "export {}\n")
    original_is_file = Path.is_file

    def reject_excluded_file(path: Path) -> bool:
        if path == ignored:
            raise AssertionError("iter_text_files descended into an excluded directory")
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", reject_excluded_file)

    assert common.iter_text_files(
        tmp_path,
        ["*.ts"],
        ["web-nuxt"],
        ["web-nuxt\\generated\\"],
    ) == []


def test_regexcheck_catches_pattern_and_reports_line(tmp_path):
    _mk(tmp_path, "docs/a.md", "dòng sạch\nảnh lấy từ Wikimedia nhé\n")
    chk = common.RegexCheck(
        name="banned", level="hard", rule="R50.1",
        patterns=[r"Wikimedia"], globs=["*.md"], roots=["docs"],
        msg="nguồn ảnh cấm", root=tmp_path,
    )
    r = chk.run()
    assert r["count"] == 1
    v = r["violations"][0]
    assert v["file"].endswith("a.md") and v["line"] == 2 and v["rule"] == "R50.1"


def test_regexcheck_neg_context_skips_warning_lines(tmp_path):
    _mk(tmp_path, "docs/a.md", "KHÔNG dùng Wikimedia (nguồn cấm)\n")
    chk = common.RegexCheck(
        name="banned", level="hard", rule="R50.1",
        patterns=[r"Wikimedia"], globs=["*.md"], roots=["docs"], root=tmp_path,
    )
    assert chk.run()["count"] == 0


def test_regexcheck_exclude_paths(tmp_path):
    _mk(tmp_path, "docs/archive/old.md", "Wikimedia\n")
    _mk(tmp_path, "docs/live.md", "Wikimedia\n")
    chk = common.RegexCheck(
        name="banned", level="hard", rule="R50.1",
        patterns=[r"Wikimedia"], globs=["*.md"], roots=["docs"],
        exclude_paths=["docs/archive"], root=tmp_path,
    )
    r = chk.run()
    assert r["count"] == 1 and r["violations"][0]["file"].endswith("live.md")


def test_regexcheck_staged_mode_only_scans_given_files(tmp_path):
    _mk(tmp_path, "docs/a.md", "Wikimedia\n")
    _mk(tmp_path, "docs/b.md", "Wikimedia\n")
    chk = common.RegexCheck(
        name="banned", level="hard", rule="R50.1",
        patterns=[r"Wikimedia"], globs=["*.md"], roots=["docs"], root=tmp_path,
    )
    r = chk.run(files=["docs/a.md"])
    assert r["count"] == 1
    # file ngoài globs/roots bị lọc
    assert chk.run(files=["src/x.py"])["count"] == 0


def test_regexcheck_staged_mode_respects_exclude_path_boundaries(tmp_path):
    _mk(tmp_path, "docs/exact.md", "Wikimedia\n")
    _mk(tmp_path, "docs/standards/skip.md", "Wikimedia\n")
    _mk(tmp_path, "docs/standards-v2/keep.md", "Wikimedia\n")
    chk = common.RegexCheck(
        name="banned", level="hard", rule="R50.1",
        patterns=[r"Wikimedia"], globs=["*.md"], roots=["docs"],
        exclude_paths=["docs/exact.md", "docs\\standards"], root=tmp_path,
    )

    result = chk.run(files=[
        "docs/exact.md",
        "docs/standards/skip.md",
        "docs/standards-v2/keep.md",
    ])

    assert result["count"] == 1
    assert result["violations"][0]["file"] == "docs/standards-v2/keep.md"


def test_ratchet_blocks_increase_allows_equal_and_decrease(tmp_path):
    baseline = {"R10.7": 2}
    res_inc = [{"check": "tinh_cu", "level": "hard-ratchet", "rule": "R10.7", "count": 3, "violations": []}]
    res_eq = [{"check": "tinh_cu", "level": "hard-ratchet", "rule": "R10.7", "count": 2, "violations": []}]
    res_dec = [{"check": "tinh_cu", "level": "hard-ratchet", "rule": "R10.7", "count": 1, "violations": []}]
    blockers, _ = common.ratchet_violations(res_inc, baseline)
    assert len(blockers) == 1 and "R10.7" in blockers[0]
    assert common.ratchet_violations(res_eq, baseline)[0] == []
    blockers, suggestions = common.ratchet_violations(res_dec, baseline)
    assert blockers == [] and len(suggestions) == 1  # đề nghị hạ baseline


def test_ratchet_ignores_plain_hard_and_soft(tmp_path):
    baseline = {}
    res = [
        {"check": "secrets", "level": "hard", "rule": "R70.1", "count": 5, "violations": []},
        {"check": "thin", "level": "soft", "rule": "R50.4", "count": 9, "violations": []},
    ]
    blockers, suggestions = common.ratchet_violations(res, baseline)
    assert blockers == [] and suggestions == []


def test_baseline_io_roundtrip(tmp_path):
    (tmp_path / "docs" / "standards").mkdir(parents=True)
    common.save_baseline({"R10.7": 87, "R30.3": 12}, root=tmp_path)
    b = common.load_baseline(root=tmp_path)
    assert b == {"R10.7": 87, "R30.3": 12}


def test_load_baseline_missing_returns_empty(tmp_path):
    assert common.load_baseline(root=tmp_path) == {}


# --- NEG_DEFAULT: phủ định phải là CHỈ DẪN, không phải văn xuôi ------------
# Hồi quy 2026-08-05: `web-nuxt/pages/huong-dan.vue:459` trả lời người dùng
# "Ảnh chỉ hiển thị khi có nguồn bản quyền hợp lệ (UGC, Pexels, Unsplash)" —
# trái CLAUDE.md §1.5 — nhưng lọt cổng hard R10.6 suốt thời gian dài vì câu
# hỏi phía trước chứa chữ "không" ("Tại sao ... không có ảnh?") và NEG_DEFAULT
# khi đó miễn trừ mọi dòng chứa "không" (re.I trùm cả chữ thường).

REAL_VIOLATIONS = [
    "{ q: 'Tại sao một số nơi không có ảnh?', a: 'nguồn hợp lệ (UGC, Pexels, Unsplash)' }",
    "Ảnh không hiện thì lấy tạm từ Wikimedia",
]

LEGIT_DIRECTIVES = [
    '# KHÔNG dùng Tailwind',
    'không dùng Pexels/Unsplash',
    'TUYỆT ĐỐI không thêm lại claim "đã xác minh/kiểm chứng"',
    'không tự nhận "đã xác minh/kiểm chứng thực địa" khi chưa đi thực tế',
    '**⛔ CHẶN — chờ chủ dự án:** PUBLISH ảnh thật (Wikimedia khớp tên sai ~50%)',
    'CẤM Wikimedia',
    'background: no-repeat url(x)',
]


def test_neg_default_khong_mien_tru_cau_mo_ta_thuong():
    """Chữ "không" trơn trong văn xuôi KHÔNG được miễn trừ cả dòng."""
    for line in REAL_VIOLATIONS:
        assert not common.NEG_DEFAULT.search(line), f"vẫn bị miễn trừ: {line}"


def test_neg_default_van_mien_tru_chi_dan_co_chu_dich():
    """Chỉ dẫn cấm (viết HOA hoặc "không <động từ>") vẫn được miễn trừ."""
    for line in LEGIT_DIRECTIVES:
        assert common.NEG_DEFAULT.search(line), f"chỉ dẫn hợp lệ bị bắt nhầm: {line}"


def test_regex_check_bat_duoc_ca_huong_dan_vue(tmp_path):
    """Cổng R10.6 đi hết đường: từ file thật tới danh sách vi phạm."""
    _mk(tmp_path, "web-nuxt/pages/faq.vue",
        "const faq = [\n"
        "  { q: 'Tại sao chỗ này không có ảnh?', a: 'Ảnh lấy từ Pexels và Unsplash.' },\n"
        "]\n")
    check = common.RegexCheck(
        name="banned_image_sources", level="hard", rule="R10.6",
        patterns=[r"\b(Pexels|Unsplash|Wikimedia)\b"],
        globs=["*.vue"], roots=["web-nuxt"], root=tmp_path,
    )
    result = check.run(None)
    assert result["count"] == 1, result
    assert result["violations"][0]["line"] == 2

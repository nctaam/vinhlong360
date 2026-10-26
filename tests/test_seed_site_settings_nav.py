"""Mọi link trong nav mặc định phải trỏ tới một trang có thật.

`agent/seed_site_settings.py` là nguồn sinh menu/footer khi khởi tạo site. Nó là
danh sách chuỗi viết tay, không ai kiểm — thêm một mục trỏ sai, hoặc đổi tên file
trang mà quên sửa nav, thì link chết nằm im trên mọi trang cho tới khi có người
bấm. Test này nối hai đầu lại: từng `to` trong DEFAULTS phải khớp một file route
trong `web-nuxt/pages/`.

Không dùng route manifest: manifest là thứ được SINH ra, nên nếu nó lệch với thư
mục pages thì test sẽ xanh trong khi link vẫn chết. Đọc thẳng thư mục là nguồn
cuối cùng.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "web-nuxt" / "pages"


def _load_defaults() -> dict:
    """Nạp DEFAULTS mà không import cả package `agent` (kéo theo server nặng)."""
    path = ROOT / "agent" / "seed_site_settings.py"
    spec = importlib.util.spec_from_file_location("_seed_site_settings", path)
    assert spec and spec.loader, f"không nạp được {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["_seed_site_settings"] = module
    spec.loader.exec_module(module)
    return module.DEFAULTS


def _collect_links(node: object, out: list[str]) -> None:
    """Gom mọi giá trị `to` ở bất kỳ độ sâu nào — nav lồng nhiều cấp."""
    if isinstance(node, dict):
        to = node.get("to")
        if isinstance(to, str):
            out.append(to)
        for value in node.values():
            _collect_links(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_links(item, out)


def _route_exists(route: str) -> bool:
    """`/lich-van-nien` → pages/lich-van-nien.vue, hoặc pages/lich-van-nien/index.vue.

    CHỈ khớp trang TĨNH. Cố ý không cho đoạn động (`[id]`, `[...slug]`) đứng ra
    nhận: `pages/` có route catch-all, nên nếu tính cả nó thì mọi đường dẫn — kể
    cả đường bịa — đều "tồn tại" và test thành vô dụng. Chính bài kiểm răng bên
    dưới bắt được điều đó ở bản đầu.

    Hệ quả có chủ ý: nav mà trỏ vào một route động sẽ bị báo. Đúng như vậy — link
    viết tay trong menu phải trỏ một trang cụ thể, không phải một khuôn.
    """
    path = route.split("?", 1)[0].split("#", 1)[0]
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return (PAGES / "index.vue").exists()
    if any(p.startswith("[") for p in parts):
        return False

    def _single_param(entries: list[Path]) -> Path | None:
        """Đoạn động MỘT cấp (`[id]`), KHÔNG phải catch-all (`[...slug]`)."""
        for e in entries:
            if e.name.startswith("[") and not e.name.startswith("[..."):
                return e
        return None

    current = PAGES
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        if last:
            if (current / f"{part}.vue").exists():
                return True
            if (current / part / "index.vue").exists():
                return True
            return _single_param(list(current.glob("*.vue"))) is not None
        if (current / part).is_dir():
            current = current / part
            continue
        nested = _single_param([d for d in current.iterdir() if d.is_dir()])
        if nested is None:
            return False
        current = nested
    return False


def test_moi_link_nav_deu_co_trang_that():
    assert PAGES.is_dir(), f"không thấy thư mục pages tại {PAGES}"

    links: list[str] = []
    _collect_links(_load_defaults(), links)

    internal = sorted({l for l in links if l.startswith("/")})
    # Chốt để test không tự rỗng: nav mặc định không thể chỉ có vài link.
    assert len(internal) >= 10, f"gom được quá ít link ({len(internal)}) — logic gom hỏng?"

    chet = [l for l in internal if not _route_exists(l)]
    assert not chet, "link nav trỏ tới trang không tồn tại: " + ", ".join(chet)


def test_ham_kiem_route_that_su_biet_phan_biet():
    """Nếu `_route_exists` luôn trả True thì test trên vô dụng — chốt lại ở đây."""
    assert _route_exists("/lich-van-nien") is True
    assert _route_exists("/khong-bao-gio-co-trang-nay-2026") is False


def test_seed_defaults_khop_editorial_fallback_khong_ai_slop():
    """Hợp đồng chống trôi lệch nguồn chân lý (Critique #6):
    DEFAULTS trong agent/seed_site_settings.py phải khớp với fallback điền dã
    trên Frontend (ChatWidget.vue, AIBestTime.vue, AISearchAssist.vue, AITravelTips.vue)
    và tuyệt đối không tái xuất hiện cụm từ AI Slop cũ."""
    defaults = _load_defaults()
    chat_disclaimer = defaults["chat.disclaimer"]["value"]
    ai_disclaimer = defaults["ai.disclaimer_text"]["value"]
    assert isinstance(chat_disclaimer, str) and chat_disclaimer
    assert isinstance(ai_disclaimer, str) and ai_disclaimer

    for forbidden in ("do AI tạo", "AI có thể sai", "Trợ lý AI", "✨"):
        assert forbidden not in chat_disclaimer
        assert forbidden not in ai_disclaimer

    chat_vue = (ROOT / "web-nuxt" / "components" / "ChatWidget.vue").read_text(encoding="utf-8")
    assert chat_disclaimer in chat_vue

    for comp_name in ("AIBestTime.vue", "AISearchAssist.vue", "AITravelTips.vue"):
        comp_text = (ROOT / "web-nuxt" / "components" / comp_name).read_text(encoding="utf-8")
        assert ai_disclaimer in comp_text, f"{comp_name} lệch fallback so với seed_site_settings.py"


def test_seed_nav_footer_synchronized_and_emoji_free():
    """Hợp đồng đồng bộ cấu trúc điều hướng & footer giữa seed_site_settings.py và default.vue,
    đồng thời khóa cứng không còn emoji hoặc khẩu hiệu 3 tỉnh cũ (QW-16)."""
    import json
    import re

    defaults = _load_defaults()
    emoji_re = re.compile(r"[\U0001F300-\U0001FAFF☀-➿⭐❤]")

    raw_seed_text = (ROOT / "agent" / "seed_site_settings.py").read_text(encoding="utf-8")
    assert not emoji_re.search(raw_seed_text), (
        "agent/seed_site_settings.py không được chứa ký tự emoji (QW-16)"
    )

    for key in ("branding.tagline", "footer.tagline"):
        val = defaults[key]["value"]
        assert "Bến Tre, Trà Vinh" not in val, f"{key} còn câu khẩu hiệu 3 tỉnh cũ"
        assert "Khám phá tỉnh Vĩnh Long" in val

    assert "Trợ lý AI" not in defaults["homepage.chatbot_cta_text"]["value"]

    nav_groups = defaults["navigation.nav_groups"]["value"]
    nav_json = json.dumps(nav_groups, ensure_ascii=False)
    assert '"/da-luu"' in nav_json and '"Đã lưu"' in nav_json
    assert '"/dia-diem"' in nav_json and '"/bang-xep-hang"' in nav_json

    footer_cols = defaults["footer.columns"]["value"]
    titles = [c["title"] for c in footer_cols]
    assert titles == ["Gợi ý nhanh", "Công cụ", "Khu vực", "Dành cho cơ sở"]

    legal_links = defaults["footer.legal_links"]["value"]
    assert legal_links[0] == {"to": "/gioi-thieu", "label": "Về chúng tôi"}



# -*- coding: utf-8 -*-
"""Rút hạng sao OCOP từ entity — MỘT nơi duy nhất cho backend.

Song sinh với `web-nuxt/utils/ocop.ts`. Hai bản là BẮT BUỘC hôm nay vì backend
dựng JSON-LD, văn bản nạp cho LLM và thẻ chat, còn frontend dựng huy hiệu — mà
API chưa phát ra trường hạng đã chuẩn hoá. Đường thoát đúng là backend chiếu sẵn
một trường hạng để frontend khỏi tự rút; đã ghi ROADMAP.

Sửa luật ở đây thì PHẢI sửa cả bản kia. Hai bộ test soi CÙNG MỘT bộ chuỗi thật
(`agent/tests/test_ocop.py` và `web-nuxt/tests/ocop-stars.test.ts`) nên chúng sẽ
cùng đỏ nếu lệch.
"""
from __future__ import annotations

import re
from typing import Any

_RE_OCOP_SELF_TIER = re.compile(r"^\s*(?:ocop\s*)?([1-5])\s*sao\b", re.IGNORECASE)
_RE_OCOP_PROPOSAL = re.compile(
    r"đề xuất|đề nghị|chờ\s+(?:công nhận|đánh giá|xét)|đang\s+(?:xét|đề nghị)|dự kiến",
    re.IGNORECASE)
_RE_OCOP_AWARDED = re.compile(
    r"đạt|được công nhận|đã công nhận|chứng nhận|cấp quốc gia", re.IGNORECASE)
_OCOP_CLAIM_WINDOW = 40
_OCOP_NUMERIC_KEYS = ("ocop_star", "ocop_stars", "ocop_rating")

# Chương trình OCOP chỉ công nhận 3, 4 và 5 sao. KHÔNG có "OCOP 1 sao" hay
# "OCOP 2 sao" — chúng không tồn tại, nên một ô số mang 1 hoặc 2 không phải hạng.
_OCOP_MIN_GRADE = 3


def _attrs(entity: dict[str, Any]) -> dict[str, Any]:
    """`attributes` đã chuẩn hoá về dict.

    Dữ liệu thật có entity mang `attributes` là LIST (dị dạng) — bản đầu nổ
    AttributeError ở đó. Một test cũ của seo bơm đúng ca ấy và đã bắt được; giữ
    chốt chặn ở tầng thấp nhất thay vì rải ở từng nơi gọi.
    """
    a = entity.get("attributes") or {}
    return a if isinstance(a, dict) else {}


def _tu_khoa_so(attrs: dict[str, Any]) -> int:
    """Hạng từ ba khoá SỐ. `bool` bị loại tường minh: `True` là `1` trong Python
    nên không chặn thì `ocop_star: true` thành "OCOP 1 sao"."""
    for key in _OCOP_NUMERIC_KEYS:
        raw = attrs.get(key)
        if isinstance(raw, bool):
            continue
        if isinstance(raw, (int, float)):
            return int(raw)
        if isinstance(raw, str) and raw.strip().isdigit() and 1 <= int(raw.strip()) <= 5:
            return int(raw.strip())
    return 0


def _tu_o_ocop(attrs: dict[str, Any]) -> int:
    """Hạng từ ô `ocop` — văn xuôi tự do, nên NEO ĐẦU CHUỖI có chủ đích.

    Nới thành "tìm N sao ở bất kỳ đâu" là tự phong 5 sao cho trái dừa bằng danh
    mục sản phẩm của VICOSAP. Số nguyên thì rõ nghĩa nên nhận thẳng (bản TS cũng
    nhận; dữ liệu thật hiện không có ca này nhưng nó là hình dạng hợp lệ).
    """
    text = attrs.get("ocop")
    if isinstance(text, bool):
        return 0
    if isinstance(text, (int, float)):
        return int(text)
    if isinstance(text, str):
        m = _RE_OCOP_SELF_TIER.match(text)
        if m:
            return int(m.group(1))
    return 0


def _claimed_tier(attrs: dict[str, Any]) -> int:
    """Hạng GHI TRONG DỮ LIỆU, chưa qua bộ lọc §1.7. Khoá số thắng văn xuôi."""
    return _tu_khoa_so(attrs) or _tu_o_ocop(attrs)


def _van_xuoi_xac_nhan_hang(entity: dict[str, Any], tier: int) -> bool:
    """Văn xuôi có XÁC NHẬN hạng này cho CHÍNH entity không?

    Dùng lại đúng cửa sổ ±40 ký tự quanh "N sao" của luật §1.7 bên dưới, nên hai
    chỗ không thể nói ngược nhau.
    """
    prose = f"{entity.get('summary') or ''} {entity.get('description') or ''}"
    for m in re.finditer(rf"{tier}\s*sao", prose, re.IGNORECASE):
        window = prose[max(0, m.start() - _OCOP_CLAIM_WINDOW):m.end() + _OCOP_CLAIM_WINDOW]
        if _RE_OCOP_AWARDED.search(window):
            return True
    return False


def _o_so_khong_phai_tin_hieu_ocop(entity: dict[str, Any], attrs: dict[str, Any]) -> bool:
    """Con số trong ô OCOP là RÁC CHÉP NHẦM CỘT, không phải một chứng nhận.

    Đo trên `web/data.json` 2026-08-30 — 13 cơ sở lưu trú mang `ocop_star`, và
    CẢ 13 có `ocop_star` bằng đúng `star_rating` của chính nó (1=1, 2=2, 4=4,
    5=5), `ocop_certified` rỗng. Đó là vân tay của một lượt nhập chép nhầm cột
    hạng-sao-khách-sạn sang ô OCOP. Hậu quả: trang chi tiết in "Sản phẩm OCOP
    1 sao — Chương trình Mỗi xã Một sản phẩm" cho một khách sạn. Khai khống một
    chứng nhận NHÀ NƯỚC là đúng thứ CLAUDE.md §1.7 cấm.

    HAI LUẬT, mỗi luật tự đứng được:

    (A) Hạng dưới 3 — OCOP không có bậc đó. Bắt 12 entity (11 khách sạn +
        `khu-du-lich-truong-an`); trong toàn kho KHÔNG có sản phẩm nào mang
        hạng 1|2, nên luật này không đụng một sản phẩm thật nào.

    (B) Số chỉ chép lại `star_rating` VÀ văn xuôi không xác nhận hạng đó. Bắt
        nốt `homestay-sokfram` (5=5, văn xuôi chỉ nói nó BÀY BÁN sản phẩm OCOP
        3–5 sao của địa phương — cùng bẫy "danh mục của người khác" mà
        `dua-sap-cau-ke` đã dạy).

    VÌ SAO luật (B) phải có vế văn xuôi: `somo-farm-cuu-long` cũng có 4=4 nhưng
    văn xuôi ghi "Đạt chứng nhận OCOP 4 sao năm 2023 cho sản phẩm du lịch sinh
    thái" — OCOP nhóm 6 (dịch vụ du lịch) là CÓ THẬT. Luật (B) thiếu vế đó sẽ
    bóp mất một chứng nhận đúng. Đã đối chiếu từng ca trong cả 13.

    Không đụng `ocop_star: 9` / `0` / `true`: chúng vẫn giữ hành vi cũ (không rút
    được hạng nhưng vẫn tính là có dấu hiệu) vì đó là ý định ghi OCOP kèm lỗi gõ,
    khác hẳn việc chép nhầm nguyên một cột khác.
    """
    n = _tu_khoa_so(attrs)
    if n <= 0:
        return False
    if n < _OCOP_MIN_GRADE:
        return True
    sao_luu_tru = attrs.get("star_rating")
    if sao_luu_tru in (None, ""):
        return False
    try:
        cung_so = int(str(sao_luu_tru).strip()) == n
    except (TypeError, ValueError):
        return False
    return cung_so and not _van_xuoi_xac_nhan_hang(entity, n)


def _co_dau_hieu_ocop(entity: dict[str, Any], attrs: dict[str, Any]) -> bool:
    if (any(attrs.get(k) not in (None, "") for k in _OCOP_NUMERIC_KEYS)
            and not _o_so_khong_phai_tin_hieu_ocop(entity, attrs)):
        return True
    return bool(attrs.get("ocop") or attrs.get("ocop_certified"))


def _ocop_tier_is_provisional(entity: dict[str, Any], tier: int) -> bool:
    """Hạng ghi trong dữ liệu có phải hạng ĐÃ ĐẠT, hay mới chỉ được đề nghị?

    Luật HAI CHIỀU. Luật một chiều ("văn xuôi có chữ đề xuất thì hạ hạng") đánh
    oan ngay ca thật đầu tiên: `khoai-lang-say-dong-phat` ghi "ĐẠT OCOP 4 sao và
    được đề xuất công nhận 5 sao" — hạng 4 của nó CÓ THẬT. Nên chỉ hạ khi cửa sổ
    có lời đề nghị mà KHÔNG có lời xác nhận.

    Xét TOÀN VĂN chứ không từng lần nhắc: `khoai-lang-say-binh-tan` nói "được đề
    xuất lên Trung ương đánh giá 5 sao" hai lần rồi kết bằng câu trần "Sản phẩm
    OCOP 5 sao." Luật xét-từng-lần sẽ để câu trần đó lật ngược cả phán quyết.
    """
    prose = f"{entity.get('summary') or ''} {entity.get('description') or ''}"
    if not prose.strip():
        return False
    saw_proposal = saw_awarded = False
    for m in re.finditer(rf"{tier}\s*sao", prose, re.IGNORECASE):
        window = prose[max(0, m.start() - _OCOP_CLAIM_WINDOW):m.end() + _OCOP_CLAIM_WINDOW]
        if _RE_OCOP_PROPOSAL.search(window):
            saw_proposal = True
        if _RE_OCOP_AWARDED.search(window):
            saw_awarded = True
    return saw_proposal and not saw_awarded


def ocop_display_label(entity: dict[str, Any]) -> str:
    """«OCOP 5 sao» · «OCOP» · '' — KHÔNG BAO GIỜ là văn xuôi thô.

    `attributes.ocop` là chuỗi tự do. Trước bản vá này JSON-LD phát thẳng nó, đo
    được trên trang đang chạy 2026-08-27: `dua-sap-cau-ke` có
        brand.name = "OCOP VICOSAP: 4 SP OCOP 5 sao quốc gia + 7 SP OCOP 4 sao"
    tức khai với máy tìm kiếm rằng thương hiệu của TRÁI DỪA là danh mục chứng
    nhận của một CÔNG TY KHÁC. Một entity khác mang cả số quyết định:
        "OCOP 4 sao (QĐ 114/QĐ-UBND, 15/1/2020)"

    NỢ SONG BẢN — ghi rõ để không ai tưởng là trùng lặp vô ý: luật này còn một
    bản TypeScript ở `web-nuxt/utils/ocop.ts` cho huy hiệu trên giao diện. Hai
    bản là BẮT BUỘC hôm nay vì JSON-LD dựng ở backend còn huy hiệu dựng ở
    frontend, và API chưa phát ra trường hạng đã chuẩn hoá. Đường thoát đúng là
    backend chiếu sẵn một trường hạng để frontend khỏi tự rút — task riêng, đã
    ghi ROADMAP. Sửa luật ở đây thì PHẢI sửa cả bản kia; hai bộ test soi cùng
    một bộ chuỗi thật nên chúng sẽ cùng đỏ nếu lệch.
    """
    attrs = _attrs(entity)
    if _o_so_khong_phai_tin_hieu_ocop(entity, attrs):
        # Ô số là rác chép nhầm cột — bỏ nó, chỉ còn văn xuôi được nói.
        tier = _tu_o_ocop(attrs)
    else:
        tier = _claimed_tier(attrs)
    if tier > 0 and _ocop_tier_is_provisional(entity, tier):
        tier = 0   # §1.7 — hạng mới ĐỀ NGHỊ không phải hạng đã đạt
    if 1 <= tier <= 5:
        return f"OCOP {tier} sao"
    return "OCOP" if _co_dau_hieu_ocop(entity, attrs) else ""


def ocop_tier(entity: dict[str, Any]) -> int:
    r"""Hạng DÙNG ĐƯỢC, 0 = có chứng nhận nhưng chưa rõ hạng (hoặc mới đề nghị).

    Dùng cho bộ lọc "từ N sao trở lên". Bản cũ ở `server.py` rút hạng bằng
    `re.search(r"(\d)")` — bắt CHỮ SỐ ĐẦU TIÊN ở bất kỳ đâu trong chuỗi, nên
    "VICOSAP: 4 SP OCOP 5 sao quốc gia..." cho ra 4, và một chuỗi có năm ban
    hành sẽ cho ra chữ số của năm.
    """
    label = ocop_display_label(entity)
    m = re.match(r"OCOP ([1-5]) sao$", label)
    return int(m.group(1)) if m else 0


def is_ocop_certified(entity: dict[str, Any]) -> bool:
    """Có dấu hiệu OCOP nào không — KỂ CẢ khi không rút được hạng.

    Lọc bằng `attributes.ocop` truthy bỏ sót 73 sản phẩm chỉ mang `ocop_star`
    (đo 2026-08-27). Đó là cùng một lỗi đã vá ở trang /ocop, còn sống trong
    xếp hạng, đếm và bộ lọc tìm kiếm của backend.
    """
    return _co_dau_hieu_ocop(entity, _attrs(entity))

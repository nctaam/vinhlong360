# -*- coding: utf-8 -*-
"""R30.3 màu ngoài tokens (HARD-RATCHET) + R30.2 emoji chức năng (SOFT-RATCHET).

Màu hex/rgb trong .vue = nợ (palette sống ở assets/css/tokens.css + biến --*).
Emoji: string-context (SEO/map/option) hợp lệ tồn tại → soft-ratchet, chặn TĂNG.

Cả hai đếm theo TỪNG MATCH (`count_matches=True`), không theo dòng. Mặc định của
`RegexCheck` ghi một violation cho mỗi DÒNG có khớp, nên với một ratchet thì gộp
3 màu cũ vào chung một dòng là mua được 2 suất cho màu cứng mới ở chỗ khác mà
tổng không đổi. Đo 2026-08-05: R30.3 270 dòng ↔ 307 match, R30.2 623 ↔ 687 —
tức 37 và 64 suất ẩn.
"""
from __future__ import annotations

from pathlib import Path

from .common import RegexCheck

_EMOJI = r"[\U0001F300-\U0001FAFF☀-➿⭐❤]"

# app.vue/error.vue nằm ở gốc web-nuxt nên trước đây ngoài tầm quét. Thêm vào tốn
# 0 vi phạm (đã đo) nhưng bịt chỗ trú cho màu cứng mới.
_ROOTS = [
    "web-nuxt/pages", "web-nuxt/components", "web-nuxt/layouts",
    "web-nuxt/app.vue", "web-nuxt/error.vue",
]

# R30.8 quet CA assets/css vi thang bo goc song chu yeu o do (base.css 32,
# components.css 26, catalog.css 24...). _ROOTS von chi nham vao .vue.
_ROOTS_CSS = _ROOTS + ["web-nuxt/assets/css"]


def build_checks(root: Path | None = None) -> list:
    return [
        RegexCheck(
            name="fe_colors", level="hard-ratchet", rule="R30.3",
            # rgb/rgba LITERAL = nợ; rgba(var(--x-rgb), a) = DÙNG token (idiomatic, như
            # base.css) → KHÔNG phải nợ, lookahead loại. (Trước đây flag nhầm ~620.)
            # Lookahead phải bao luôn khoảng trắng: viết `\(\s*(?!var\()` thì engine
            # backtrack `\s*` về rỗng, lookahead soi đúng ký tự space nên `rgb( var(--x) )`
            # vẫn bị tính là màu cứng. Đếm theo dòng che lỗi này (cùng dòng đã có
            # match khác); bật count_matches mới lộ ra.
            # (?<!&) BAT BUOC: HTML entity dang &#128640; (= emoji ten lua) khop phan
            # "#128640" cua pattern hex-6. Do 2026-08-23: 46/165 khop la entity, KHONG
            # phai mau — no R30.3 bi thoi len dung 46 don vi.
            #
            # LUU Y cho nguoi doc sau: chinh nhung entity do la emoji viet o dang khong
            # dau, nen chung cung THOAT khoi rule emoji R30.2 (pattern _EMOJI chi khop
            # ky tu emoji that). Mo rong R30.2 de bat entity se LAM TANG no 507 -> can
            # nang baseline kem giai trinh (§3.7), nen de chu du an quyet.
            patterns=[r"(?<!&)#[0-9a-fA-F]{6}\b", r"(?<!&)#[0-9a-fA-F]{3}\b(?![0-9a-fA-F])", r"\brgba?\((?!\s*var\()"],
            globs=["*.vue"], roots=_ROOTS,
            exclude_paths=["web-nuxt/node_modules"],
            neg_context=None, count_matches=True,
            msg="màu ngoài tokens — dùng var(--*) từ tokens.css (R30.3)",
            root=root,
        ),
        RegexCheck(
            name="fe_emoji", level="soft-ratchet", rule="R30.2",
            patterns=[_EMOJI],
            globs=["*.vue"], roots=_ROOTS,
            exclude_paths=["web-nuxt/node_modules"],
            neg_context=None, count_matches=True,
            msg="emoji chức năng — dùng IconLine (R30.2); string-context được phép qua baseline",
            root=root,
        ),
        RegexCheck(
            name="fe_radius_scale", level="hard-ratchet", rule="R30.8",
            # Thang bo goc CU (--radius-xs/sm/md/lg/xl) dang duoc thay bang tang MUC DICH
            # (--radius-control/surface/sheet). Chu du an chon "di tiep" 2026-08-24.
            # Ratchet nay giu cho no KHONG TANG: ma moi phai dung tang muc dich.
            # KHONG bat --radius-full (dung chung ca hai thang) va --radius (bi danh
            # ngu nghia, se tro sang --radius-sheet khi di tru xong).
            #
            # Neu mot cho khong map duoc vao control/surface/sheet thi do la TIN HIEU
            # can them mot buoc muc dich, KHONG phai co quay lai thang cu. Thang cu con
            # 5 buoc (4/10/14/20/28), tang muc dich moi co 3 (8/12/20).
            patterns=[r"var\(\s*--radius-(?:xs|sm|md|lg|xl)\s*[),]"],
            globs=["*.vue", "*.css"], roots=_ROOTS_CSS,
            exclude_paths=["web-nuxt/node_modules"],
            neg_context=None, count_matches=True,
            msg="thang bo goc cũ — dùng --radius-control/surface/sheet (R30.8)",
            root=root,
        ),
    ]


CHECKS = build_checks()

# -*- coding: utf-8 -*-
"""R50.2 filler-giọng (SOFT-RATCHET) + R10.9 địa danh ngoài tỉnh (SOFT-RATCHET).

Filler = tell "đọc-như-AI/miền-Tây-generic" theo playbook chống-AI-spam.
Quét cả template FE lẫn web/data.json (raw text — đếm xu hướng, SP6 kéo xuống).
"""
from __future__ import annotations

from pathlib import Path

from .common import RegexCheck

FILLERS = [
    r"miền Tây",
    r"sông nước hữu tình",
    r"thiên đường",
    r"hidden gem",
    r"must[- ]see",
    r"không thể bỏ lỡ",
    r"đắm chìm",
    r"hòa mình vào",
    r"điểm đến lý tưởng",
]
# Địa danh NGOÀI tỉnh Vĩnh Long mới hay bị gán nhầm (Đồng Tháp/Tiền Giang cũ).
# Cái Mơn (Chợ Lách) là TRONG tỉnh — không nằm trong danh sách.
OUT_OF_PROVINCE = [r"Cái Bè", r"Lai Vung", r"Định Yên"]


def build_checks(root: Path | None = None) -> list:
    return [
        RegexCheck(
            name="content_fillers", level="soft-ratchet", rule="R50.2",
            patterns=FILLERS,
            globs=["*.vue", "*.ts", "data.json"],
            roots=["web-nuxt/pages", "web-nuxt/components", "web-nuxt/utils", "web-nuxt/composables", "web"],
            exclude_paths=["web-nuxt/node_modules", "web/media"],
            msg="filler giọng generic — thay bằng đặc-thù Vĩnh Long (R50.2, playbook)",
            root=root,
        ),
        RegexCheck(
            name="out_of_province", level="soft-ratchet", rule="R10.9",
            patterns=OUT_OF_PROVINCE,
            globs=["*.vue", "*.ts", "data.json"],
            roots=["web-nuxt/pages", "web-nuxt/components", "web-nuxt/utils", "web"],
            exclude_paths=["web-nuxt/node_modules", "web/media"],
            msg="địa danh NGOÀI tỉnh (Đồng Tháp/Tiền Giang cũ) — kiểm xuất xứ (R10.9)",
            root=root,
        ),
    ]


CHECKS = build_checks()

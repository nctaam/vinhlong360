"""Khoá bất biến cho `attributes.admin_code` của xã/phường.

Nguồn MÃ: file danh mục "Danh sách phường xã thuộc Tỉnh Vĩnh Long_07_08_2026.xls"
(cột `Mã PX`, `Cấp`, `Phường Xã`; dẫn Nghị quyết 1687/NQ-UBTVQH15 ngày 16/06/2025).
File .xls KHÔNG nằm trong repo, nên bảng dưới đây là bản đóng băng của **cả 124** đơn vị
xã/phường, đối chiếu trong `docs/drafts/doi-chieu-ma-hanh-chinh.md`.

Dùng file làm nguồn MÃ, KHÔNG dùng làm nguồn CẤP. File chỉ dẫn NQ 1687/2025 nên cột
`Cấp` của nó chưa cập nhật đợt 16 xã lên phường; `data.json` mới phản ánh trạng thái
hành chính hiện hành (35 phường + 89 xã). Mã thì lấy được từ file vì mã KHÔNG đổi khi
đơn vị đổi loại hình — chính file tự chứng minh: `Xã Ba Tri` 29110 ghi "Đổi loại hình
từ thị trấn Ba Tri thành xã Ba Tri".

`OFFICIAL_ADMIN_CODES` chép **nguyên văn file danh mục** — cột cấp và cột tên là
những gì file GHI, không phải những gì `data.json` hiển thị. Chỗ dữ liệu dự án khác
file được liệt kê tường minh ở ba hằng số ngoại lệ bên dưới, và mỗi ngoại lệ đều có
một test tự tính lại từ dữ liệu để khoá đúng tập đó (xem §"Vì sao không nới assertion").

Vì sao không nới assertion
--------------------------
Cách dễ dãi là đổi `assert level == official_level` thành `assert level in {...}`.
Làm vậy thì một xã bị đổi cấp nhầm trong tương lai sẽ trôi qua im lặng. Ở đây giữ
nguyên phép so sánh BẰNG cho từng đơn vị, chỉ thay giá trị kỳ vọng bằng
`expected_project_level()`; đồng thời `test_level_divergence_is_exactly_the_upgraded_wards`
tính lại tập lệch TỪ DỮ LIỆU và bắt nó bằng đúng `PHUONG_UPGRADE_IDS`. Thêm một ca
lệch mới → đỏ. Bớt một ca → cũng đỏ. Nhét id bừa vào tập ngoại lệ để dập test → đỏ ở
`test_upgraded_wards_are_xa_in_the_official_file`.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = ROOT / "web" / "data.json"

ADMIN_CODE_RE = re.compile(r"^\d{5}$")
NAME_PREFIX_RE = re.compile(r"^(Phường|Xã|P\.|TT\.|Thị trấn)\s+")

# (entity id, Mã PX, cấp THEO FILE CHÍNH THỨC, tên THEO FILE CHÍNH THỨC)
OFFICIAL_ADMIN_CODES: tuple[tuple[str, str, str, str], ...] = (
    ("p-phu-khuong", "28756", "phuong", "Phường Phú Khương"),
    ("p-an-hoi", "28777", "phuong", "Phường An Hội"),
    ("p-son-dong", "28783", "phuong", "Phường Sơn Đông"),
    ("p-ben-tre", "28789", "phuong", "Phường Bến Tre"),
    ("xa-giao-long", "28807", "xa", "Xã Giao Long"),
    ("p-phu-tuc", "28810", "xa", "Xã Phú Túc"),
    ("xa-tan-phu", "28840", "xa", "Xã Tân Phú"),
    ("p-phu-tan", "28858", "phuong", "Phường Phú Tân"),
    ("p-tien-thuy", "28861", "xa", "Xã Tiên Thủy"),
    ("xa-cho-lach", "28870", "xa", "Xã Chợ Lách"),
    ("xa-phu-phung", "28879", "xa", "Xã Phú Phụng"),
    ("xa-vinh-thanh", "28894", "xa", "Xã Vĩnh Thành"),
    ("xa-hung-khanh-trung", "28901", "xa", "Xã Hưng Khánh Trung"),
    ("p-mo-cay", "28903", "xa", "Xã Mỏ Cày"),
    ("xa-phuoc-my-trung", "28915", "xa", "Xã Phước Mỹ Trung"),
    ("xa-tan-thanh-binh", "28921", "xa", "Xã Tân Thành Bình"),
    ("xa-dong-khoi", "28945", "xa", "Xã Đồng Khởi"),
    ("xa-nhuan-phu-tan", "28948", "xa", "Xã Nhuận Phú Tân"),
    ("xa-an-dinh", "28957", "xa", "Xã An Định"),
    ("xa-thanh-thoi", "28969", "xa", "Xã Thành Thới"),
    ("xa-huong-my", "28981", "xa", "Xã Hương Mỹ"),
    ("xa-giong-trom", "28984", "xa", "Xã Giồng Trôm"),
    ("xa-luong-hoa", "28987", "xa", "Xã Lương Hòa"),
    ("xa-luong-phu", "28993", "xa", "Xã Lương Phú"),
    ("xa-chau-hoa", "28996", "xa", "Xã Châu Hòa"),
    ("xa-phuoc-long", "29020", "xa", "Xã Phước Long"),
    ("xa-tan-hao", "29029", "xa", "Xã Tân Hào"),
    ("xa-hung-nhuong", "29044", "xa", "Xã Hưng Nhượng"),
    ("p-binh-dai", "29050", "xa", "Xã Bình Đại"),
    ("xa-phu-thuan", "29062", "xa", "Xã Phú Thuận"),
    ("xa-loc-thuan", "29077", "xa", "Xã Lộc Thuận"),
    ("xa-chau-hung", "29083", "xa", "Xã Châu Hưng"),
    ("xa-thanh-tri", "29089", "xa", "Xã Thạnh Trị"),
    ("xa-thanh-phuoc", "29104", "xa", "Xã Thạnh Phước"),
    ("xa-thoi-thuan", "29107", "xa", "Xã Thới Thuận"),
    ("p-ba-tri", "29110", "xa", "Xã Ba Tri"),
    ("xa-my-chanh-hoa", "29122", "xa", "Xã Mỹ Chánh Hòa"),
    ("xa-bao-thanh", "29125", "xa", "Xã Bảo Thạnh"),
    ("xa-tan-xuan", "29137", "xa", "Xã Tân Xuân"),
    ("xa-an-ngai-trung", "29143", "xa", "Xã An Ngãi Trung"),
    ("xa-an-hiep", "29158", "xa", "Xã An Hiệp"),
    ("p-tan-thuy", "29167", "xa", "Xã Tân Thủy"),
    ("xa-thanh-phu", "29182", "xa", "Xã Thạnh Phú"),
    ("xa-quoi-dien", "29191", "xa", "Xã Quới Điền"),
    ("xa-dai-dien", "29194", "xa", "Xã Đại Điền"),
    ("xa-thanh-hai", "29221", "xa", "Xã Thạnh Hải"),
    ("xa-an-qui", "29224", "xa", "Xã An Qui"),
    ("xa-thanh-phong", "29227", "xa", "Xã Thạnh Phong"),
    ("p-tra-vinh", "29242", "phuong", "Phường Trà Vinh"),
    ("p-nguyet-hoa", "29254", "phuong", "Phường Nguyệt Hóa"),
    ("p-long-duc", "29263", "phuong", "Phường Long Đức"),
    ("p-cang-long", "29266", "xa", "Xã Càng Long"),
    ("xa-an-truong", "29275", "xa", "Xã An Trường"),
    ("xa-tan-an", "29278", "xa", "Xã Tân An"),
    ("xa-binh-phu", "29287", "xa", "Xã Bình Phú"),
    ("xa-nhi-long", "29302", "xa", "Xã Nhị Long"),
    ("xa-cau-ke", "29308", "xa", "Xã Cầu Kè"),
    ("xa-an-phu-tan", "29317", "xa", "Xã An Phú Tân"),
    ("xa-phong-thanh", "29329", "xa", "Xã Phong Thạnh"),
    ("xa-tam-ngai", "29335", "xa", "Xã Tam Ngãi"),
    ("p-tieu-can", "29341", "xa", "Xã Tiểu Cần"),
    ("p-hung-hoa", "29362", "xa", "Xã Hùng Hòa"),
    ("p-tap-ngai", "29365", "xa", "Xã Tập Ngãi"),
    ("p-tan-hoa", "29371", "xa", "Xã Tân Hòa"),
    ("xa-chau-thanh", "29374", "xa", "Xã Châu Thành"),
    ("xa-song-loc", "29386", "xa", "Xã Song Lộc"),
    ("p-hoa-thuan", "29398", "phuong", "Phường Hòa Thuận"),
    ("xa-hung-my", "29407", "xa", "Xã Hưng Mỹ"),
    ("xa-hoa-minh", "29410", "xa", "Xã Hòa Minh"),
    ("xa-long-hoa", "29413", "xa", "Xã Long Hòa"),
    ("xa-cau-ngang", "29416", "xa", "Xã Cầu Ngang"),
    ("xa-my-long", "29419", "xa", "Xã Mỹ Long"),
    ("xa-vinh-kim", "29431", "xa", "Xã Vinh Kim"),
    ("xa-nhi-truong", "29446", "xa", "Xã Nhị Trường"),
    ("xa-hiep-my", "29455", "xa", "Xã Hiệp Mỹ"),
    ("xa-tra-cu", "29461", "xa", "Xã Trà Cú"),
    ("xa-tap-son", "29467", "xa", "Xã Tập Sơn"),
    ("xa-luu-nghiep-anh", "29476", "xa", "Xã Lưu Nghiệp Anh"),
    ("xa-ham-giang", "29489", "xa", "Xã Hàm Giang"),
    ("xa-dai-an", "29491", "xa", "Xã Đại An"),
    ("xa-don-chau", "29497", "xa", "Xã Đôn Châu"),
    ("xa-long-hiep", "29506", "xa", "Xã Long Hiệp"),
    ("p-duyen-hai", "29512", "phuong", "Phường Duyên Hải"),
    ("xa-long-thanh", "29513", "xa", "Xã Long Thành"),
    ("p-truong-long-hoa", "29516", "phuong", "Phường Trường Long Hòa"),
    ("xa-long-huu", "29518", "xa", "Xã Long Hữu"),
    ("xa-ngu-lac", "29530", "xa", "Xã Ngũ Lạc"),
    ("xa-long-vinh", "29533", "xa", "Xã Long Vĩnh"),
    ("xa-dong-hai", "29536", "xa", "Xã Đông Hải"),
    ("p-long-chau", "29551", "phuong", "Phường Long Châu"),
    ("p-phuoc-hau", "29557", "phuong", "Phường Phước Hậu"),
    ("p-tan-ngai", "29566", "phuong", "Phường Tân Ngãi"),
    ("xa-an-binh", "29584", "xa", "Xã An Bình"),
    ("p-thanh-duc", "29590", "phuong", "Phường Thanh Đức"),
    ("p-tan-hanh", "29593", "phuong", "Phường Tân Hạnh"),
    ("p-long-ho", "29602", "xa", "Xã Long Hồ"),
    ("xa-phu-quoi", "29611", "xa", "Xã Phú Quới"),
    ("xa-nhon-phu", "29623", "xa", "Xã Nhơn Phú"),
    ("xa-binh-phuoc", "29638", "xa", "Xã Bình Phước"),
    ("xa-cai-nhum", "29641", "xa", "Xã Cái Nhum"),
    ("xa-tan-long-hoi", "29653", "xa", "Xã Tân Long Hội"),
    ("p-vung-liem", "29659", "xa", "Xã Trung Thành"),
    ("xa-quoi-an", "29668", "xa", "Xã Quới An"),
    ("xa-quoi-thien", "29677", "xa", "Xã Quới Thiện"),
    ("xa-trung-hiep", "29683", "xa", "Xã Trung Hiệp"),
    ("xa-trung-ngai", "29698", "xa", "Xã Trung Ngãi"),
    ("xa-hieu-phung", "29701", "xa", "Xã Hiếu Phụng"),
    ("xa-hieu-thanh", "29713", "xa", "Xã Hiếu Thành"),
    ("p-tam-binh", "29719", "xa", "Xã Tam Bình"),
    ("xa-hau-loc", "29728", "xa", "Xã Cái Ngang"),
    ("xa-hoa-hiep", "29734", "xa", "Xã Hòa Hiệp"),
    ("xa-song-phu", "29740", "xa", "Xã Song Phú"),
    ("xa-ngai-tu", "29767", "xa", "Xã Ngãi Tứ"),
    ("p-cai-von", "29770", "phuong", "Phường Cái Vồn"),
    ("p-binh-minh", "29771", "phuong", "Phường Bình Minh"),
    ("xa-tan-luoc", "29785", "xa", "Xã Tân Lược"),
    ("xa-my-thuan", "29788", "xa", "Xã Mỹ Thuận"),
    ("p-tan-quoi", "29800", "xa", "Xã Tân Quới"),
    ("p-dong-thanh", "29812", "phuong", "Phường Đông Thành"),
    ("p-tra-on", "29821", "xa", "Xã Trà Ôn"),
    ("xa-hoa-binh", "29830", "xa", "Xã Hòa Bình"),
    ("xa-tra-con", "29836", "xa", "Xã Trà Côn"),
    ("xa-vinh-xuan", "29845", "xa", "Xã Vĩnh Xuân"),
    ("xa-luc-si-thanh", "29857", "xa", "Xã Lục Sĩ Thành"),
)

# --- Ngoại lệ 1: 16 đơn vị dự án ghi `phuong` còn file ghi `Xã` -------------------
# TRẠNG THÁI HÀNH CHÍNH HIỆN HÀNH (chủ dự án chốt 2026-08-07, Ca A §5 của báo cáo
# đối chiếu): 16 đơn vị này ĐANG là phường. `data.json` ghi `level=phuong` là đúng;
# chỗ lệch nằm ở file .xls, vì file chỉ dẫn NQ 1687/2025 và chưa cập nhật đợt nâng
# cấp — nó lạc hậu về CẤP, không phải dữ liệu dự án sai.
#
# Mã hành chính vẫn lấy từ file vì **mã KHÔNG đổi khi đổi loại hình** — chính file
# tự chứng minh: `Xã Ba Tri` 29110 ghi "Đổi loại hình từ thị trấn Ba Tri thành xã
# Ba Tri".
#
# Khi có danh mục mới đã cập nhật cấp, sửa cột cấp trong `OFFICIAL_ADMIN_CODES` và
# thu hằng số này lại trong CÙNG commit (rỗng hết thì `expected_project_level` tự
# khớp thẳng với file).
PHUONG_UPGRADE_IDS: frozenset[str] = frozenset({
    "p-ba-tri",
    "p-binh-dai",
    "p-cang-long",
    "p-hung-hoa",
    "p-long-ho",
    "p-mo-cay",
    "p-phu-tuc",
    "p-tam-binh",
    "p-tan-hoa",
    "p-tan-quoi",
    "p-tan-thuy",
    "p-tap-ngai",
    "p-tien-thuy",
    "p-tieu-can",
    "p-tra-on",
    "p-vung-liem",
})

# --- Ngoại lệ 2: 2 ca đổi tên (Ca B) --------------------------------------------
# Chủ dự án giữ tên đang dùng (giá trị nhận diện/SEO), chỉ mượn mã từ file.
# Xác nhận cùng-một-đơn-vị bằng `attributes.merged_from` khớp cột `Ghi chú`.
# Lưu ý `p-vung-liem` nằm trong CẢ hai ngoại lệ: vừa lệch cấp vừa đổi tên.
RENAMED_KEEPING_PROJECT_NAME: dict[str, str] = {
    "p-vung-liem": "Trung Thành",  # file: "Đổi loại hình, đổi tên từ thị trấn Vũng Liêm…"
    "xa-hau-loc": "Cái Ngang",  # file: "Đổi tên từ xã Hậu Lộc thành xã Cái Ngang…"
}

# --- Ngoại lệ 3: 2 ca khác quy ước đặt dấu (Ca C — chủ dự án CHƯA chốt) ----------
# `Hoà` (kiểu cũ) vs `Hòa` (kiểu file). Cùng một chữ, khác vị trí dấu huyền.
# Không ảnh hưởng mã lẫn slug; ghi ra đây để khỏi bị nhầm là ca đổi tên.
DIACRITIC_VARIANT_IDS: frozenset[str] = frozenset({"p-hung-hoa", "p-tan-hoa"})

# Không còn đơn vị nào chờ quyết. Giữ hằng số để lần sau mở lại ca mới thì có chỗ đặt.
PENDING_DECISION_IDS: frozenset[str] = frozenset()


def expected_project_level(entity_id: str, official_level: str) -> str:
    """Cấp mà `data.json` PHẢI ghi: theo file, trừ 16 ca file còn ghi cấp lạc hậu."""
    return "phuong" if entity_id in PHUONG_UPGRADE_IDS else official_level


def bare_name(name: str) -> str:
    """Bỏ tiền tố `Phường `/`Xã `… để so phần tên riêng, giữ nguyên dấu."""
    return NAME_PREFIX_RE.sub("", unicodedata.normalize("NFC", name)).strip()


@pytest.fixture(scope="module")
def entities() -> list[dict]:
    with DATA_JSON.open(encoding="utf-8") as stream:
        return json.load(stream)["entities"]


@pytest.fixture(scope="module")
def coded_entities(entities: list[dict]) -> list[dict]:
    return [
        entity
        for entity in entities
        if isinstance(entity.get("attributes"), dict)
        and "admin_code" in entity["attributes"]
    ]


def test_frozen_table_is_self_consistent() -> None:
    """Bảng đóng băng phải đúng hình dạng trước khi dùng nó để kiểm dữ liệu."""
    assert len(OFFICIAL_ADMIN_CODES) == 124
    ids = [row[0] for row in OFFICIAL_ADMIN_CODES]
    codes = [row[1] for row in OFFICIAL_ADMIN_CODES]
    assert len(set(ids)) == len(ids), "id trùng trong bảng đóng băng"
    assert len(set(codes)) == len(codes), "Mã PX trùng trong bảng đóng băng"
    assert all(ADMIN_CODE_RE.fullmatch(code) for code in codes)
    assert all(row[2] in {"phuong", "xa"} for row in OFFICIAL_ADMIN_CODES)
    assert not PENDING_DECISION_IDS, "còn ca chờ quyết mà bảng đã đủ 124 dòng"
    # Mọi hằng số ngoại lệ phải trỏ vào đơn vị có thật trong bảng.
    known = set(ids)
    for label, exceptions in (
        ("PHUONG_UPGRADE_IDS", PHUONG_UPGRADE_IDS),
        ("RENAMED_KEEPING_PROJECT_NAME", frozenset(RENAMED_KEEPING_PROJECT_NAME)),
        ("DIACRITIC_VARIANT_IDS", DIACRITIC_VARIANT_IDS),
    ):
        assert exceptions <= known, f"{label} có id lạ: {sorted(exceptions - known)}"


def test_upgraded_wards_are_xa_in_the_official_file() -> None:
    """Chặn mẹo nhét id bừa vào PHUONG_UPGRADE_IDS để dập một test đang đỏ.

    Ngoại lệ chỉ hợp lệ khi file danh mục thật sự ghi `Xã` — nếu file đã ghi
    `Phường` thì đơn vị đó không lệch với file, liệt kê nó ở đây là sai.
    """
    official_level = {row[0]: row[2] for row in OFFICIAL_ADMIN_CODES}
    assert len(PHUONG_UPGRADE_IDS) == 16
    for entity_id in sorted(PHUONG_UPGRADE_IDS):
        assert official_level[entity_id] == "xa", (
            f"{entity_id}: file danh mục ghi cấp {official_level[entity_id]!r}, "
            "không thuộc diện 16 đơn vị file ghi cấp lạc hậu"
        )


def test_admin_code_is_five_digit_string(coded_entities: list[dict]) -> None:
    for entity in coded_entities:
        code = entity["attributes"]["admin_code"]
        assert isinstance(code, str), f"{entity['id']}: admin_code phải là chuỗi, gặp {type(code)}"
        assert ADMIN_CODE_RE.fullmatch(code), f"{entity['id']}: admin_code không đúng 5 chữ số: {code!r}"


def test_admin_code_is_unique(coded_entities: list[dict]) -> None:
    seen: dict[str, str] = {}
    for entity in coded_entities:
        code = entity["attributes"]["admin_code"]
        assert code not in seen, f"admin_code {code} dùng cho cả {seen[code]} và {entity['id']}"
        seen[code] = entity["id"]


def test_admin_code_only_on_ward_level_places(coded_entities: list[dict]) -> None:
    for entity in coded_entities:
        assert entity.get("type") == "place", f"{entity['id']}: admin_code chỉ dành cho type=place"
        assert entity.get("level") in {"phuong", "xa"}, (
            f"{entity['id']}: level={entity.get('level')!r} không phải cấp xã/phường"
        )


def test_every_approved_place_carries_its_official_code(entities: list[dict]) -> None:
    by_id = {entity["id"]: entity for entity in entities}
    for entity_id, code, official_level, official_name in OFFICIAL_ADMIN_CODES:
        entity = by_id.get(entity_id)
        assert entity is not None, f"{entity_id} biến mất khỏi data.json"
        attributes = entity.get("attributes")
        assert isinstance(attributes, dict), f"{entity_id}: thiếu attributes"
        assert attributes.get("admin_code") == code, (
            f"{entity_id}: admin_code={attributes.get('admin_code')!r}, file chính thức ghi {code}"
        )
        # So sánh BẰNG cho từng đơn vị — không nới thành `in {…}`.
        expected = expected_project_level(entity_id, official_level)
        assert entity.get("level") == expected, (
            f"{entity_id} (mã {code}, file ghi {official_name!r} cấp {official_level!r}): "
            f"level={entity.get('level')!r} nhưng kỳ vọng {expected!r}"
        )


def test_level_divergence_is_exactly_the_upgraded_wards(entities: list[dict]) -> None:
    """Khoá tập lệch cấp — tính lại TỪ DỮ LIỆU, không đọc PHUONG_UPGRADE_IDS để suy ra.

    Thêm một ca lệch mới → đỏ (dữ liệu trôi ngoài quyết định của chủ dự án).
    Bớt một ca (một trong 16 đơn vị bị hạ về `xa`) → cũng đỏ, vì lúc đó trạng thái
    hành chính đã đổi và hằng số phải được cập nhật trong CÙNG commit.
    """
    by_id = {entity["id"]: entity for entity in entities}
    diverging = {
        entity_id
        for entity_id, _code, official_level, _official_name in OFFICIAL_ADMIN_CODES
        if by_id[entity_id].get("level") != official_level
    }
    assert diverging == PHUONG_UPGRADE_IDS, (
        "tập lệch cấp giữa data.json và file danh mục đã đổi: "
        f"thừa={sorted(diverging - PHUONG_UPGRADE_IDS)}, "
        f"thiếu={sorted(PHUONG_UPGRADE_IDS - diverging)}"
    )


def test_name_divergence_is_exactly_the_documented_cases(entities: list[dict]) -> None:
    """Khoá tập lệch TÊN RIÊNG (bỏ tiền tố Phường/Xã) — 2 ca đổi tên + 2 ca dấu.

    Nếu một xã bị đổi tên trong data.json mà không ai ghi lại lý do, test này đỏ.
    """
    by_id = {entity["id"]: entity for entity in entities}
    diverging = {
        entity_id
        for entity_id, _code, _official_level, official_name in OFFICIAL_ADMIN_CODES
        if bare_name(by_id[entity_id]["name"]) != bare_name(official_name)
    }
    documented = frozenset(RENAMED_KEEPING_PROJECT_NAME) | DIACRITIC_VARIANT_IDS
    assert diverging == documented, (
        "tập lệch tên riêng đã đổi: "
        f"thừa={sorted(diverging - documented)}, thiếu={sorted(documented - diverging)}"
    )


def test_renamed_places_keep_project_name_and_official_code(entities: list[dict]) -> None:
    """Ca B: giữ `id`/`name` của dự án, mã lấy theo tên MỚI trong file."""
    by_id = {entity["id"]: entity for entity in entities}
    official_name = {row[0]: row[3] for row in OFFICIAL_ADMIN_CODES}
    for entity_id, official_bare in RENAMED_KEEPING_PROJECT_NAME.items():
        entity = by_id[entity_id]
        assert bare_name(official_name[entity_id]) == official_bare
        assert bare_name(entity["name"]) != official_bare, (
            f"{entity_id}: name đã đổi sang tên chính thức {official_bare!r} — "
            "nếu đây là chủ ý thì cập nhật RENAMED_KEEPING_PROJECT_NAME trong cùng commit"
        )


def test_coded_places_are_exactly_the_approved_set(coded_entities: list[dict]) -> None:
    approved = {row[0] for row in OFFICIAL_ADMIN_CODES}
    actual = {entity["id"] for entity in coded_entities}
    extra = actual - approved
    assert not extra, (
        f"place ngoài danh sách duyệt lại có admin_code: {sorted(extra)} — "
        "nếu đây là chủ ý, cập nhật OFFICIAL_ADMIN_CODES trong cùng commit"
    )
    assert actual == approved


def test_pending_decision_places_have_no_code(entities: list[dict]) -> None:
    """Không còn ca chờ quyết; nếu sau này mở lại ca mới thì nó phải KHÔNG có mã."""
    by_id = {entity["id"]: entity for entity in entities}
    for entity_id in sorted(PENDING_DECISION_IDS):
        entity = by_id.get(entity_id)
        assert entity is not None, f"{entity_id} biến mất khỏi data.json"
        attributes = entity.get("attributes") or {}
        assert "admin_code" not in attributes, (
            f"{entity_id} được gắn admin_code khi chưa chốt "
            "(xem docs/drafts/doi-chieu-ma-hanh-chinh.md §5)"
        )


def test_every_ward_level_place_is_accounted_for(entities: list[dict]) -> None:
    """124 xã/phường và cả 124 đều đã có mã. Không được có ca thứ ba.

    `type=place` trong data.json là 125 = 124 xã/phường + `vinh-long` (`level=tinh`).
    Đơn vị cấp tỉnh KHÔNG có `admin_code`: mã tỉnh là `86` (2 chữ số, cột `Mã TP`),
    không phải mã phường-xã 5 chữ số.
    """
    ward_ids = {
        entity["id"]
        for entity in entities
        if entity.get("type") == "place" and entity.get("level") in {"phuong", "xa"}
    }
    approved = {row[0] for row in OFFICIAL_ADMIN_CODES}
    assert len(ward_ids) == 124
    assert ward_ids == approved | PENDING_DECISION_IDS, (
        "có xã/phường không thuộc nhóm đã-gắn-mã lẫn nhóm chờ-quyết: "
        f"{sorted(ward_ids ^ (approved | PENDING_DECISION_IDS))}"
    )


def test_province_place_has_no_ward_code(entities: list[dict]) -> None:
    """Chốt lại con số 125 vs 124 để lần sau không ai đi tìm 'mã còn thiếu'."""
    places = [entity for entity in entities if entity.get("type") == "place"]
    assert len(places) == 125
    province = [entity for entity in places if entity.get("level") == "tinh"]
    assert len(province) == 1 and province[0]["id"] == "vinh-long"
    assert "admin_code" not in (province[0].get("attributes") or {}), (
        "cấp tỉnh không mang mã phường-xã 5 chữ số"
    )

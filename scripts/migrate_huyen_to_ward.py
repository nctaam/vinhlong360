"""Migrate placeId huyện-cũ → xã/phường mới (NQ 1687) — evidence-based, §1.4 an toàn.

3 lớp an toàn:
  (a) bằng chứng: tên xã/phường cũ phải XUẤT HIỆN trong address của entity
  (b) name-match: đích phải khớp 1 trong 124 ward THẬT hiện có
  (c) area-match: area của ward đích == area của entity (chặn map xuyên vùng do lỗi parse)
Không khớp đủ 3 → DETACH (placeId=None, giữ area). KHÔNG đoán.

Usage:  python scripts/migrate_huyen_to_ward.py          # dry-run (mặc định)
        python scripts/migrate_huyen_to_ward.py --apply  # ghi web/data.json (cần B1 backup trước)
"""
import json, re, sys, unicodedata, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "web/data.json"
APPLY = "--apply" in sys.argv

def norm(s):
    # GIỮ DẤU tiếng Việt (NFC + \w unicode) — "Bình Thạnh" ≠ "Bình Thành".
    s = unicodedata.normalize("NFC", (s or "")).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)).strip()

# ── Crosswalk NQ1687: new_ward_name -> [old commune names] (từ toàn văn) ──
CROSSWALK = {
 # Vĩnh Long
 "Thanh Đức": ["Thanh Đức"], "Long Châu": ["Trường An"], "Phước Hậu": ["Phước Hậu"],
 "Tân Hạnh": ["Tân Hạnh"], "Tân Ngãi": ["Tân Hòa", "Tân Hội", "Tân Ngãi"],
 "Bình Minh": ["Thuận An", "Thành Phước"], "Cái Vồn": ["Mỹ Hòa", "Cái Vồn"],
 "Đông Thành": ["Đông Thuận", "Đông Bình", "Đông Thạnh", "Đông Thành"],
 "Cái Nhum": ["An Phước", "Chánh An", "Cái Nhum"], "Tân Long Hội": ["Tân An Hội", "Tân Long", "Tân Long Hội"],
 "Nhơn Phú": ["Mỹ An", "Mỹ Phước", "Nhơn Phú"], "Bình Phước": ["Long Mỹ", "Hòa Tịnh", "Bình Phước"],
 "An Bình": ["Hòa Ninh", "Bình Hòa Phước", "Đồng Phú", "An Bình"],
 "Long Hồ": ["Long Hồ", "Long An", "Long Phước"], "Phú Quới": ["Lộc Hòa", "Hòa Phú", "Thạnh Quới", "Phú Quới"],
 "Quới Thiện": ["Thanh Bình", "Quới Thiện"],
 "Trung Thành": ["Trung Hiếu", "Trung Thành"], "Trung Ngãi": ["Trung Thành Đông", "Trung Nghĩa", "Trung Ngãi"],
 "Quới An": ["Trung Thành Tây", "Tân Quới Trung", "Quới An"], "Trung Hiệp": ["Tân An Luông", "Trung Chánh", "Trung Hiệp"],
 "Hiếu Phụng": ["Hiếu Thuận", "Trung An", "Hiếu Phụng"], "Hiếu Thành": ["Hiếu Nhơn", "Hiếu Nghĩa", "Hiếu Thành"],
 "Lục Sĩ Thành": ["Phú Thành", "Lục Sĩ Thành"],
 "Trà Ôn": ["Tích Thiện"], "Trà Côn": ["Nhơn Bình", "Trà Côn", "Tân Mỹ"],
 "Vĩnh Xuân": ["Hựu Thành", "Thuận Thới", "Vĩnh Xuân"], "Hòa Bình": ["Xuân Hiệp", "Thới Hòa", "Hòa Bình"],
 "Hòa Hiệp": ["Hòa Thạnh", "Hòa Lộc", "Hòa Hiệp"], "Tam Bình": ["Mỹ Thạnh Trung"],
 "Ngãi Tứ": ["Loan Mỹ", "Bình Ninh", "Ngãi Tứ"], "Song Phú": ["Long Phú", "Phú Thịnh", "Song Phú"],
 "Cái Ngang": ["Mỹ Lộc", "Tân Lộc", "Hậu Lộc", "Phú Lộc"],
 "Tân Quới": ["Tân Bình", "Thành Lợi", "Tân Quới"], "Tân Lược": ["Tân Thành", "Tân An Thạnh", "Tân Lược"],
 "Mỹ Thuận": ["Thành Trung", "Nguyễn Văn Thảnh", "Mỹ Thuận"],
 # Trà Vinh
 "Long Hữu": ["Hiệp Thạnh", "Long Hữu"],
 "Càng Long": ["Mỹ Cẩm", "Nhị Long Phú", "Càng Long"], "An Trường": ["An Trường A", "An Trường"],
 "Tân An": ["Huyền Hội", "Tân An"], "Nhị Long": ["Đại Phước", "Đức Mỹ", "Nhị Long"],
 "Bình Phú": ["Đại Phúc", "Phương Thạnh", "Bình Phú"],
 "Trà Vinh": ["Phường 1", "Phường 3", "Phường 9"], "Long Đức": ["Phường 4", "Long Đức"],
 "Nguyệt Hoá": ["Phường 7", "Phường 8", "Nguyệt Hóa"], "Hoà Thuận": ["Phường 5", "Hòa Thuận"],
 "Duyên Hải": ["Long Toàn", "Dân Thành"], "Trường Long Hoà": ["Trường Long Hòa"],
 "Châu Thành": ["Thanh Mỹ", "Đa Lộc", "Mỹ Chánh"], "Song Lộc": ["Lương Hòa A", "Song Lộc"],
 "Hưng Mỹ": ["Hòa Lợi", "Phước Hảo", "Hưng Mỹ"],
 "Cầu Kè": ["Hòa Ân", "Châu Điền", "Cầu Kè"], "Phong Thạnh": ["Ninh Thới", "Phong Phú", "Phong Thạnh"],
 "An Phú Tân": ["Hòa Tân", "An Phú Tân"], "Tam Ngãi": ["Thông Hòa", "Thạnh Phú", "Tam Ngãi"],
 "Tiểu Cần": ["Phú Cần", "Hiếu Trung", "Tiểu Cần"], "Tân Hoà": ["Long Thới", "Tân Hòa", "Cầu Quan"],
 "Hùng Hoà": ["Ngãi Hùng", "Tân Hùng", "Hùng Hòa"], "Tập Ngãi": ["Hiếu Tử", "Tập Ngãi"],
 "Cầu Ngang": ["Thuận Hòa", "Cầu Ngang"], "Mỹ Long": ["Mỹ Long Bắc", "Mỹ Long Nam", "Mỹ Long"],
 "Vinh Kim": ["Kim Hòa", "Vinh Kim"], "Nhị Trường": ["Hiệp Hòa", "Trường Thọ", "Nhị Trường"],
 "Hiệp Mỹ": ["Long Sơn", "Hiệp Mỹ Đông", "Hiệp Mỹ Tây"],
 "Trà Cú": ["Ngãi Xuyên", "Thanh Sơn", "Trà Cú"], "Đại An": ["Định An", "Đại An"],
 "Lưu Nghiệp Anh": ["An Quảng Hữu", "Lưu Nghiệp Anh"], "Hàm Giang": ["Hàm Tân", "Kim Sơn", "Hàm Giang"],
 "Long Hiệp": ["Ngọc Biên", "Tân Hiệp", "Long Hiệp"], "Tập Sơn": ["Tân Sơn", "Phước Hưng", "Tập Sơn"],
 "Long Thành": ["Long Khánh", "Long Thành"], "Đôn Châu": ["Đôn Xuân", "Đôn Châu"],
 "Ngũ Lạc": ["Thạnh Hòa Sơn", "Ngũ Lạc"],
 # Bến Tre
 "Phú Túc": ["Tân Thạch", "Tường Đa", "Phú Túc", "An Khánh"], "Giao Long": ["An Phước", "Quới Sơn", "Giao Long"],  # An Khánh→Phú Túc (chủ dự án xác nhận 2026-06-22; verbatim k59 model cắt sót)
 "Tiên Thủy": ["Thành Triệu", "Quới Thành", "Tiên Thủy"], "Tân Phú": ["Tiên Long", "Phú Đức", "Tân Phú"],
 "Phú Phụng": ["Sơn Định", "Vĩnh Bình", "Phú Phụng"],
 "Phú Khương": ["Phú Hưng", "Nhơn Thạnh", "Phú Khương"], "Bến Tre": ["Bình Phú", "Thanh Tân", "Bến Tre"],
 "Sơn Đông": ["Sơn Đông", "Tam Phước"], "Phú Tân": ["Hữu Định", "Phước Thạnh", "Phú Tân"],
 "An Hội": ["Mỹ Thạnh An", "Phú Nhuận", "Sơn Phú"],  # verbatim NQ k116 (xác minh 2026-06-22)
 "Chợ Lách": ["Hòa Nghĩa", "Chợ Lách"], "Vĩnh Thành": ["Phú Sơn", "Tân Thiềng", "Vĩnh Thành"],
 "Hưng Khánh Trung": ["Vĩnh Hòa", "Hưng Khánh Trung A", "Hưng Khánh Trung B"],
 "Phước Mỹ Trung": ["Phú Mỹ", "Thạnh Ngãi", "Tân Phú Tây", "Phước Mỹ Trung"],
 "Tân Thành Bình": ["Thành An", "Tân Thành Bình"], "Nhuận Phú Tân": ["Khánh Thạnh Tân", "Tân Thanh Tây", "Nhuận Phú Tân"],
 "Đồng Khởi": ["Định Thủy", "Phước Hiệp", "Bình Khánh"], "Mỏ Cày": ["Tân Hội", "Đa Phước Hội", "Mỏ Cày"],
 "Thành Thới": ["An Thới", "Thành Thới A", "Thành Thới B"], "An Định": ["Tân Trung", "Minh Đức", "An Định"],
 "Hương Mỹ": ["Ngãi Đăng", "Cẩm Sơn", "Hương Mỹ"], "Đại Điền": ["Phú Khánh", "Tân Phong", "Thới Thạnh", "Đại Điền"],
 "Quới Điền": ["Mỹ Hưng", "Quới Điền"], "Thạnh Phú": ["Bình Thạnh", "Mỹ An", "Thạnh Phú"],
 "An Qui": ["An Thuận", "An Nhơn", "An Qui"], "Thạnh Hải": ["An Điền", "Thạnh Hải"],
 "Thạnh Phong": ["Giao Thạnh", "Thạnh Phong"], "Tân Thủy": ["An Hòa Tây", "Tân Thủy", "An Thủy"],  # An Thủy→Tân Thủy (chủ dự án xác nhận)
 "Bảo Thạnh": ["Bảo Thuận", "Bảo Thạnh"],
 "Ba Tri": ["An Đức", "Vĩnh An", "An Bình Tây", "Ba Tri"], "Tân Xuân": ["Phú Lễ", "Phước Ngãi", "Tân Xuân"],
 "Mỹ Chánh Hòa": ["Mỹ Nhơn", "Mỹ Chánh Hòa"], "An Ngãi Trung": ["An Phú Trung", "An Ngãi Trung"],
 "An Hiệp": ["Tân Hưng", "An Ngãi Tây", "An Hiệp"], "Hưng Nhượng": ["Hưng Lễ", "Hưng Nhượng"],
 "Giồng Trôm": ["Bình Hòa", "Bình Thành", "Giồng Trôm"], "Tân Hào": ["Tân Lợi Thạnh", "Thạnh Phú Đông", "Tân Hào"],
 "Phước Long": ["Hưng Phong", "Phước Long"], "Lương Phú": ["Thuận Điền", "Lương Phú"],
 "Châu Hòa": ["Châu Bình", "Lương Quới", "Châu Hòa"], "Lương Hòa": ["Phong Nẫm", "Lương Hòa"],
 "Thới Thuận": ["Thừa Đức", "Thới Thuận"], "Thạnh Phước": ["Đại Hòa Lộc", "Thạnh Phước"],
 "Bình Đại": ["Bình Thới", "Bình Thắng", "Bình Đại"], "Thạnh Trị": ["Định Trung", "Phú Long", "Thạnh Trị"],
 "Lộc Thuận": ["Vang Quới Đông", "Vang Quới Tây", "Lộc Thuận"], "Châu Hưng": ["Thới Lai", "Châu Hưng"],
 "Phú Thuận": ["Long Định", "Tam Hiệp", "Phú Thuận"],
}
# old commune (norm, GIỮ DẤU) -> SET các ward mới (set vì 1 tên có thể ở nhiều huyện)
OLD2NEW = collections.defaultdict(set)
for new, olds in CROSSWALK.items():
    for o in olds:
        OLD2NEW[norm(o)].add(new)

# Phường-SỐ cũ phải key theo (thành phố, "phường N") — vì P1 có ở nhiều TP/TX cùng vùng.
NUMBERED = { (norm(c), norm("Phường " + str(n))): w for c, n, w in [
    ("Trà Vinh",1,"Trà Vinh"),("Trà Vinh",3,"Trà Vinh"),("Trà Vinh",9,"Trà Vinh"),
    ("Trà Vinh",4,"Long Đức"),("Trà Vinh",7,"Nguyệt Hoá"),("Trà Vinh",8,"Nguyệt Hoá"),("Trà Vinh",5,"Hoà Thuận"),
    ("Duyên Hải",1,"Duyên Hải"),("Duyên Hải",2,"Trường Long Hoà"),
    ("Bến Tre",7,"Bến Tre"),("Bến Tre",8,"Phú Khương"),("Bến Tre",6,"Sơn Đông"),
    ("Vĩnh Long",5,"Thanh Đức"),("Vĩnh Long",1,"Long Châu"),("Vĩnh Long",9,"Long Châu"),
    ("Vĩnh Long",3,"Phước Hậu"),("Vĩnh Long",4,"Phước Hậu"),("Vĩnh Long",8,"Tân Hạnh"),
]}

# Override theo entity-id cho ca địa-chỉ-gõ-nhầm đã xác minh verbatim NQ (KHÔNG đoán):
# chua-vam-ray ghi "xã Hàm Thuận" (không tồn tại) — thực là Hàm Tân → Hàm Giang (k53).
ENTITY_OVERRIDE = {"chua-vam-ray-wat-samrong": "xa-ham-giang"}

with open(DATA, encoding="utf-8") as f:
    d = json.load(f)
ents = d["entities"]
places = [e for e in ents if e.get("type") == "place"]
place_ids = {p["id"] for p in places}
wards = [p for p in places if p.get("level") in ("xa", "phuong")]
# new ward name(norm) + area -> ward id
ward_idx = {}
for w in wards:
    nm = norm(re.sub(r"^(xã|phường)\s+", "", w.get("name", ""), flags=re.I))
    ward_idx[(nm, w.get("area"))] = w["id"]
ward_by_name = collections.defaultdict(list)
for w in wards:
    ward_by_name[norm(re.sub(r"^(xã|phường)\s+", "", w.get("name",""), flags=re.I))].append(w)

DEFUNCT = re.compile(r"^(huyện|thành phố|thị xã|quận)\b", re.IGNORECASE)
defunct = [p for p in places if not p.get("level") and DEFUNCT.search(p.get("name","") or "")]
defunct_ids = {p["id"] for p in defunct}
mis = [e for e in ents if e.get("type") != "place" and (
        (not e.get("placeId")) or (e.get("placeId") in defunct_ids) or (e["placeId"] not in place_ids))]

def attrs(e):
    a = e.get("attributes") or {}
    if isinstance(a, str):
        try: a = json.loads(a)
        except Exception: a = {}
    return a

COMMUNE = re.compile(r"(?:xã|phường|thị trấn)\s+([A-Za-zÀ-ỹ0-9\s]+?)(?:\s*[,–\-]|\s+và\b|$|\s+huyện|\s+TX\b|\s+thị xã|\s+thành phố|\s+tỉnh)", re.IGNORECASE)
CITY = re.compile(r"(?:thành phố|TP|thị xã|TX)\.?\s+([A-Za-zÀ-ỹ\s]+?)(?:,|$|\s+tỉnh)", re.IGNORECASE)

stats = collections.Counter()
reassign, detach, table = {}, [], []
for e in mis:
    a = attrs(e); addr = " ".join(str(a.get(k,"")) for k in ("address","diaChi","dia_chi")).strip()
    area = e.get("area")
    if e["id"] in ENTITY_OVERRIDE:                # ca verbatim-verified riêng (typo địa chỉ)
        reassign[e["id"]] = ENTITY_OVERRIDE[e["id"]]; stats["override (verbatim NQ)"] += 1
        table.append((e["id"], area, "(override typo)", "→", ENTITY_OVERRIDE[e["id"]], "override"))
        continue
    # Bắt MỌI xã/phường/thị trấn trong địa chỉ (đa-đơn-vị sau merger thường về cùng 1 ward).
    wids = set(); how = None
    for raw in COMMUNE.findall(addr):
        raw = raw.strip(); cn = norm(raw)
        if not cn:
            continue
        if re.fullmatch(r"\d+", raw):          # "phường N" -> cần (thành phố, phường N)
            cm = CITY.search(addr); city = norm(cm.group(1)) if cm else ""
            nk = (city, norm("Phường " + raw))
            if nk in NUMBERED:
                w = ward_idx.get((norm(NUMBERED[nk]), area))
                if w: wids.add(w); how = how or "numbered"
        else:
            names = OLD2NEW.get(cn, set()) | ({raw} if cn in ward_by_name else set())
            for nm in names:
                w = ward_idx.get((norm(re.sub(r"^(xã|phường)\s+", "", nm, flags=re.I)), area))
                if w:
                    wids.add(w); how = how or ("crosswalk" if cn in OLD2NEW else "direct")
    if len(wids) == 1:                          # mọi đơn-vị-cũ hội tụ đúng 1 ward khớp area -> an toàn
        wid = next(iter(wids)); reassign[e["id"]] = wid; stats[how] += 1
        table.append((e["id"], area, addr[:45], "→", wid, how))
    else:                                       # 0 hoặc >1 (nhập nhằng) -> detach, KHÔNG đoán
        detach.append(e["id"]); stats["DETACH (area-level)" + (" [ambiguous]" if len(wids) > 1 else "")] += 1

print(f"=== MIGRATION {'APPLY' if APPLY else 'DRY-RUN'} — {len(mis)} entity gán-sai ===")
for k,c in stats.most_common(): print(f"  {c:>4}  {k}")
print(f"\n  Reassign: {len(reassign)} | Detach: {len(detach)} | Gỡ place defunct: {len(defunct)}")
print("\n  Mẫu reassign (crosswalk/numbered):")
for r in [t for t in table if t[5] in ("crosswalk","numbered")][:18]:
    print(f"    {r[0]} [{r[1]}] '{r[2]}' → {r[4]} ({r[5]})")

if APPLY:
    for e in ents:
        if e["id"] in reassign:
            e["placeId"] = reassign[e["id"]]
            a = e.get("area"); pw = next((w for w in wards if w["id"]==reassign[e["id"]]), None)
            if pw and pw.get("area"): e["area"] = pw["area"]
        elif e["id"] in set(detach):
            e["placeId"] = None
    # gỡ place defunct (đã không còn con)
    d["entities"] = [e for e in ents if e["id"] not in defunct_ids]
    json.dump(d, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  ✅ ĐÃ GHI {DATA} | entity: {len(ents)} → {len(d['entities'])} (gỡ {len(defunct_ids)} defunct)")
else:
    print("\n  (DRY-RUN — chưa ghi gì. Thêm --apply để ghi, NHỚ backup B1 trước.)")

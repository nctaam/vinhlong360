#!/usr/bin/env python3
"""Cập nhật summary cho 123 xã/phường từ kết quả workflow deep-research."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data.json"
WORKFLOW_OUTPUT = Path(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\C--Code-vinhlong360\3ed120b9-9dcf-4fa4-90a5-37a05a43ddcc\tasks\wz1oecol5.output")

sys.stdout.reconfigure(encoding="utf-8")

# Read workflow output
wf = json.load(WORKFLOW_OUTPUT.open("r", encoding="utf-8"))
research = wf["result"]["places"]
print(f"Workflow results: {len(research)} places")

# Read data.json
data = json.load(DATA.open("r", encoding="utf-8-sig"))
by_id = {e["id"]: e for e in data["entities"]}

# Gov.vn data (area km², population, merge notes) - source of truth for numbers
GOV_DATA = {
    "p-thanh-duc": (16.49, 35158, "Phường 5 TP Vĩnh Long và xã Thanh Đức (H. Long Hồ)"),
    "p-long-chau": (12.63, 49480, "Phường 1, Phường 9 và Phường Trường An"),
    "p-phuoc-hau": (15.52, 50839, "Phường 3, Phường 4 và xã Phước Hậu (H. Long Hồ)"),
    "p-tan-hanh": (17.84, 32093, "Phường 8 và xã Tân Hạnh (H. Long Hồ)"),
    "p-tan-ngai": (21.7, 31294, "Phường Tân Ngãi, Tân Hòa và Tân Hội"),
    "p-binh-minh": (23.86, 34193, "Xã Thuận An, một phần P. Thành Phước và P. Cái Vồn"),
    "p-cai-von": (26.52, 36031, "Xã Mỹ Hòa, phần còn lại xã Ngãi Tứ, P. Thành Phước và P. Cái Vồn"),
    "p-dong-thanh": (44.35, 41793, "P. Đông Thuận, xã Đông Bình, Đông Thạnh, Đông Thành"),
    "p-an-hoi": (31.90, 53476, "P. An Hội, xã Mỹ Thạnh An, Phú Nhuận, Sơn Phú"),
    "p-ben-tre": (31.99, 35917, "Phường 7, xã Bình Phú (TP BT), xã Thanh Tân"),
    "p-phu-khuong": (24.97, 47059, "P.8 TP BT, P. Phú Khương, xã Phú Hưng, Nhơn Thạnh"),
    "p-phu-tan": (26.58, 28568, "P. Phú Tân, xã Hữu Định, Phước Thạnh"),
    "p-son-dong": (23.48, 34188, "Phường 6, xã Sơn Đông, Tam Phước"),
    "p-tra-vinh": (15.731, 45397, "Phường 1, 3 và 9"),
    "p-hoa-thuan": (16.51, 25384, "Phường 5 TP TV và xã Hòa Thuận"),
    "p-long-duc": (40.619, 33662, "Phường 4 TP TV và xã Long Đức"),
    "p-nguyet-hoa": (21.139, 37066, "Phường 7, 8 TP TV và xã Nguyệt Hóa"),
    "p-duyen-hai": (69.632, 24356, "P.1 TX Duyên Hải, xã Long Toàn, Dân Thành"),
    "p-truong-long-hoa": (56.494, 16150, "P.2 TX Duyên Hải và xã Trường Long Hòa"),
}

updated = 0
skipped = 0

for r in research:
    eid = r["id"]
    summary = r.get("summary", "").strip()
    source_url = r.get("source_url", "")
    district = r.get("district", "")

    if not summary:
        skipped += 1
        continue

    e = by_id.get(eid)
    if not e:
        print(f"  NOT FOUND: {eid}")
        skipped += 1
        continue

    # Update summary
    old_summary = e.get("summary", "")
    e["summary"] = summary

    # Update source if we have a URL
    if source_url:
        e["source"] = {"title": "Wikipedia / UBND tỉnh", "url": source_url}

    # Update attributes with gov.vn data if available
    gov = GOV_DATA.get(eid)
    if gov:
        area_km2, pop, merge_note = gov
        attrs = e.get("attributes") or {}
        attrs["area_km2"] = area_km2
        attrs["population"] = pop
        attrs["merge_note"] = merge_note
        e["attributes"] = attrs

    updated += 1

print(f"\nUpdated: {updated} summaries")
print(f"Skipped: {skipped}")

# Save
with DATA.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))
print(f"\n✅ Saved: {len(data['entities'])} entities, {len(data['relationships'])} rels")

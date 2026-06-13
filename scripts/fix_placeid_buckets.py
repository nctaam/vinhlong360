"""
Fix dữ liệu: gỡ placeId gán sai do importer dồn cả tỉnh cũ vào 1 xã "thùng chứa".

Bối cảnh (xem điều tra): import_baovinhlong.py / import_deep_crawl.py gán cứng mọi
địa điểm Bến Tre -> xa-an-binh, Trà Vinh -> xa-tra-on (placeholder lúc sáp nhập 3 tỉnh,
chưa có crosswalk xã mới). Hệ quả: "Chợ Bình Đại", "Chợ Ba Tri"... hiện trong trang
Xã An Bình dù thuộc tỉnh khác.

Cách sửa AN TOÀN — KHÔNG bịa vị trí:
- Chỉ xử lý entity trong 3 bucket placeholder (xa-an-binh, xa-tra-on, p-long-chau).
- Chỉ sửa khi CHÍNH TÊN/SUMMARY/ĐỊA CHỈ của entity nêu một địa danh tỉnh KHÁC
  (Bến Tre / Trà Vinh) — bằng chứng nội tại, không suy đoán.
- Hành động: placeId -> None (CHƯA phân loại xã, KHÔNG gán xã mới) + sửa area về
  đúng tỉnh (ben-tre / tra-vinh). Entity vẫn tồn tại, vẫn tìm được; chỉ không còn
  khẳng định sai "thuộc Xã An Bình".
- KHÔNG đụng entity thực sự thuộc bucket (vd Vinh Sang ở cù lao An Bình).

Mặc định DRY-RUN. Thêm --apply để ghi DB. Mọi thay đổi ghi log JSON để rollback.
"""
import argparse
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))
from database import db  # noqa: E402

PLACEHOLDER_BUCKETS = {"xa-an-binh", "xa-tra-on", "p-long-chau"}

# Địa danh đặc trưng từng tỉnh cũ (đơn vị huyện/thị cũ) — dùng làm BẰNG CHỨNG tỉnh.
# Cố tình BỎ token mơ hồ ("châu thành" có ở nhiều tỉnh; "long hồ"/"trà ôn"/"an bình"
# là Vĩnh Long nên không liệt kê ở đây).
PROVINCE_TOKENS = {
    "ben-tre": [
        "ba tri", "bình đại", "binh dai", "chợ lách", "cho lach", "giồng trôm",
        "giong trom", "thạnh phú", "thanh phu", "mỏ cày", "mo cay", "ba vát", "ba vat",
        "châu thành bến tre", "tp bến tre", "thành phố bến tre", "bến tre", "ben tre",
        "an hội", "phú khương", "cồn phụng", "con phung", "cồn quy", "mỏ cày nam",
        "mỏ cày bắc",
    ],
    "tra-vinh": [
        "trà vinh", "tra vinh", "cầu kè", "cau ke", "duyên hải", "duyen hai",
        "càng long", "cang long", "tiểu cần", "tieu can", "cầu ngang", "cau ngang",
        "trà cú", "tra cu", "trường long hòa", "nguyệt hóa", "ao bà om", "ba động",
        "ba dong", "vàm láng",
    ],
}


# Nếu CHÍNH text entity khẳng định nó ở ward bucket -> KHÔNG gỡ (tránh false-positive
# kiểu "Homestay Út Trinh nằm trên cù lao An Bình" lỡ có nhắc tên tỉnh khác).
BUCKET_OWN_TOKENS = {
    "xa-an-binh": ["an bình", "an binh"],
    "xa-tra-on": ["trà ôn", "tra on"],
    "p-long-chau": ["long châu", "long chau"],
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", (s or "").lower())
    return s


def _entity_text(entity: dict) -> str:
    attrs = entity.get("attributes") or {}
    return _norm(" ".join([
        entity.get("name", ""), entity.get("summary", ""),
        str(attrs.get("address", "")), str(attrs.get("dia_chi", "")),
    ]))


def detect_province(entity: dict) -> str | None:
    """Tỉnh được nêu trong CHÍNH text entity (name/summary/address). None nếu không rõ."""
    hay = _entity_text(entity)
    for prov, tokens in PROVINCE_TOKENS.items():
        for t in tokens:
            if t in hay:
                return prov
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Ghi thay đổi vào DB (mặc định chỉ dry-run)")
    args = ap.parse_args()

    db.initialize()
    ents = db.all_entities()
    bucket_area = {b: (db.get_entity(b) or {}).get("area") for b in PLACEHOLDER_BUCKETS}

    changes = []
    for e in ents:
        pid = e.get("placeId")
        if pid not in PLACEHOLDER_BUCKETS:
            continue
        # GUARD: text khẳng định ở chính ward bucket -> giữ nguyên (vd Út Trinh ở An Bình).
        hay = _entity_text(e)
        if any(t in hay for t in BUCKET_OWN_TOKENS.get(pid, [])):
            continue
        prov = detect_province(e)
        if not prov:
            continue
        # Bằng chứng nói tỉnh khác với tỉnh của ward bucket -> placeId sai.
        if prov == bucket_area.get(pid):
            continue  # token cùng tỉnh bucket (vd Vĩnh Long) -> không đủ chắc, bỏ qua
        changes.append({
            "id": e["id"], "name": e.get("name"), "type": e.get("type"),
            "old_placeId": pid, "old_area": e.get("area"),
            "new_placeId": None, "new_area": prov,
        })

    print(f"Tổng entity trong 3 bucket placeholder: "
          f"{sum(1 for e in ents if e.get('placeId') in PLACEHOLDER_BUCKETS)}")
    print(f"Phát hiện gán sai (text nêu tỉnh khác): {len(changes)}\n")
    by_prov = {}
    for c in changes:
        by_prov.setdefault(c["new_area"], 0)
        by_prov[c["new_area"]] += 1
    print("Theo tỉnh đúng:", by_prov)
    print("\nVí dụ (tối đa 25):")
    for c in changes[:25]:
        print(f"  {c['name'][:36]:38} {c['old_placeId']:12} -> placeId=None, area={c['new_area']}")

    log_dir = Path(__file__).resolve().parent.parent / "scratch" / "placeid_fix"
    log_dir.mkdir(parents=True, exist_ok=True)

    if not args.apply:
        log = log_dir / "dryrun_changes.json"
        log.write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[DRY-RUN] Chưa ghi gì. Danh sách đầy đủ: {log}")
        print("Chạy lại với --apply để áp dụng.")
        return

    # APPLY: ghi DB + log để rollback
    applied = 0
    for c in changes:
        e = db.get_entity(c["id"])
        if not e:
            continue
        e["placeId"] = None
        e["area"] = c["new_area"]
        db.upsert_entity(e)
        applied += 1
    log = log_dir / "applied_changes.json"
    log.write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[APPLIED] Đã sửa {applied} entity. Log rollback: {log}")


if __name__ == "__main__":
    main()

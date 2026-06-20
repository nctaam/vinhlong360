"""Add the 'tổng tài' romantic itinerary to data.json and SQLite DB."""
import json
import sys
import io
import sqlite3
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DATA_JSON = os.path.join(os.path.dirname(__file__), "..", "web", "data.json")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "agent", "data", "vinhlong360.db")

ITINERARY_ID = "ben-tre-tong-tai-romantic-2day-001"

CONTENT = """# Bến Tre 2N1Đ – Tổng tài đưa nữ chính về miền Tây

> *"Anh không biết chèo xuồng, nhưng vì em, anh sẽ học."*

## Tổng quan
- **Thời gian:** 2 ngày 1 đêm (cuối tuần)
- **Xuất phát:** Bến xe Miền Tây, TP.HCM
- **Điểm đến:** Bến Tre (TP Bến Tre + Chợ Lách)
- **Phong cách:** Lãng mạn, nghỉ dưỡng, trải nghiệm miệt vườn
- **Ngân sách:** 4,5–8 triệu / 2 người (tuỳ xe riêng hay xe khách)

## Di chuyển
- **Xe riêng:** Thuê xe 7 chỗ, HCMC → Cao tốc TP.HCM–Trung Lương → Mỹ Tho → Cầu Rạch Miễu → Bến Tre (~2,5 giờ, 1,5–2,5 triệu khứ hồi)
- **Xe khách:** Phương Trang tại Bến xe Miền Tây → Bến Tre, 100.000đ/người/lượt, chuyến sớm 6:00–6:30 để tới nơi 9:00
- **Mẹo:** Đặt vé sớm cho chuyến cuối tuần. Khởi hành trước 7:00 tránh kẹt xa lộ

---

## Ngày 1 – Sông nước & xứ dừa (khu vực TP Bến Tre)

**06:30** – Xuất phát từ Bến xe Miền Tây
- Tổng tài lái xe hoặc thuê tài xế riêng. Nữ chính ngủ gục trên vai — cảnh kinh điển mọi drama
- Đi cao tốc TP.HCM–Trung Lương → rẽ Mỹ Tho → cầu Rạch Miễu → Bến Tre

**09:00** – **Cồn Phụng** (cù lao Phụng, xã Tân Thạch – ngay cửa ngõ Bến Tre)
- Đi xuồng ba lá len lỏi kênh rạch rừng dừa nước. Tổng tài chèo xuồng, nữ chính ngồi mũi — khung hình TikTok triệu view
- Tham quan xưởng kẹo dừa truyền thống, uống trà mật ong chanh dừa
- Chụp ảnh cổng dừa, cầu khỉ (tổng tài qua cầu khỉ = content cực hài)
- **Chi phí:** Vé 50.000đ/người + xuồng riêng 150.000đ (30 phút)
- **Thời gian:** ~2 tiếng
- **Mẹo:** Buổi sáng ánh sáng đẹp nhất. Mặc đồ sáng màu, mang kem chống nắng

**11:15** – Lunch tại nhà hàng ven sông TP Bến Tre (cách Cồn Phụng ~5 phút)
- Cá tai tượng chiên xù, lẩu mắm miền Tây, tôm nướng muối ớt
- Nước dừa tươi bổ vỏ tại bàn — tổng tài lần đầu cầm dao chặt dừa
- **Chi phí:** 300.000–500.000đ / 2 người

**12:30** – **Trải nghiệm làm kẹo dừa Mỏ Cày** (cách TP Bến Tre ~1km)
- Tay tổng tài quen ký hợp đồng, giờ nặn kẹo dừa — nữ chính quay video cười ngả nghiêng
- Xem quy trình thủ công từ nạo dừa → nấu → kéo → cắt → gói
- Mua kẹo sầu riêng, ca cao, lá dứa làm quà
- **Chi phí:** Miễn phí tham quan, mua kẹo 100.000–200.000đ
- **Thời gian:** ~1 tiếng

**14:00** – Di chuyển về resort (15km, ~25 phút)

**14:30** – Check-in **Forever Green Resort** (Châu Thành, Bến Tre)
- Resort sinh thái quy mô lớn, khuôn viên xanh mướt với kênh rạch xuyên resort
- Phòng từ 1,2–3 triệu/đêm. Tổng tài book phòng view đẹp nhất
- *Thay thế:* Diamond Stars Ben Tre Hotel (TP Bến Tre, 800k–2tr) nếu thích tiện trung tâm
- **Lưu ý:** Book trước cho cuối tuần, nhất là mùa cao điểm (tháng 6–8, lễ Tết)

**15:30** – Hồ bơi & nghỉ ngơi
- Bơi trong khuôn viên resort giữa vườn dừa
- Nữ chính: "Sao ở đây yên bình quá?" — Tổng tài: "Vì có em"

**18:00** – Dinner
- Tại resort (tiện, không gian đẹp) hoặc ra TP Bến Tre ăn hải sản
- **Chi phí:** 200.000–400.000đ / 2 người

**19:30** – Đi dạo trong khuôn viên resort
- Ánh đèn lung linh giữa kênh rạch và vườn dừa. Gió sông mát
- *"Em biết không, anh chưa bao giờ đi chậm như thế này. Nhưng bên em, anh không muốn vội."*

---

## Ngày 2 – Vườn trái cây & làng hoa (Chợ Lách)

**07:00** – Sáng thức dậy, cà phê phin tại resort
- Không gian yên tĩnh, tiếng chim hót. Tổng tài lần đầu pha cà phê phin chậm rãi thay vì espresso

**08:30** – Di chuyển đến Chợ Lách (10km từ Forever Green, ~20 phút)

**09:00** – **Làng hoa kiểng Cái Mơn** (xã Vĩnh Thành, Chợ Lách)
- Dạo giữa vườn hoa rực rỡ: cúc, hồng, lan, bonsai nghệ thuật
- Tổng tài mua cho nữ chính một chậu hoa nhỏ: "Giống em, nhỏ mà rực rỡ"
- Chụp ảnh giữa luống hoa — filter vintage, góc nghệ
- **Chi phí:** 20.000–50.000đ tham quan
- **Thời gian:** ~1 tiếng

**10:00** – **Vườn trái cây Chợ Lách**
- Chôm chôm Cái Mơn, sầu riêng, măng cụt, nhãn — ăn tại vườn, trái vừa hái
- Tổng tài trèo cây hái trái cho nữ chính (plot twist: lần đầu trèo cây, suýt ngã)
- **Chi phí:** 50.000–100.000đ/người (vào vườn + ăn thoả thích)
- **Thời gian:** ~1,5 tiếng
- **Mùa trái cây tốt nhất:** Tháng 5–8 (chôm chôm, sầu riêng, măng cụt chín rộ)

**11:30** – Lunch tại Chợ Lách
- Bánh xèo miền Tây, gỏi cuốn tôm thịt, canh chua cá lóc
- Nước dừa xiêm cuối cùng trước khi rời xứ dừa
- **Chi phí:** 200.000–350.000đ / 2 người

**13:00** – Về TP.HCM
- Từ Chợ Lách → QL57 → cầu Cổ Chiên/Hàm Luông → cầu Rạch Miễu → Mỹ Tho → Cao tốc → HCMC
- Hoặc: Chợ Lách → phà Đình Khao → Vĩnh Long → Cao tốc (nhanh hơn ~15 phút)
- Trên xe, nữ chính lại ngủ gật. Tổng tài nhẹ nhàng đắp áo khoác
- **Thời gian:** ~2,5–3 tiếng

**~16:00** – Về đến Bến xe Miền Tây / TP.HCM
- *"Lần sau anh đưa em đi Trà Vinh nhé?"*

---

## Tổng chi phí ước tính (2 người)

| Hạng mục | Chi phí |
|----------|---------|
| Xe riêng 7 chỗ khứ hồi | 1.500.000–2.500.000đ |
| *Hoặc xe khách Phương Trang* | *200.000–250.000đ* |
| Resort 1 đêm (Forever Green) | 1.200.000–3.000.000đ |
| Ăn uống (4 bữa chính + snack) | 800.000–1.400.000đ |
| Vé tham quan + trải nghiệm | 300.000–500.000đ |
| Mua quà (kẹo dừa, hoa, trái cây) | 200.000–500.000đ |
| **Tổng (xe riêng + resort cao cấp)** | **~5.000.000–8.000.000đ** |
| **Tổng (xe khách + resort tiết kiệm)** | **~2.700.000–5.000.000đ** |

---

## Lưu ý quan trọng
- **Book resort trước** ít nhất 1 tuần cho cuối tuần
- **Mùa mưa (tháng 6–11):** Mang áo mưa, mưa thường đổ chiều tối, sáng vẫn đẹp
- **Mùa trái cây:** Tháng 5–8 là đỉnh điểm chôm chôm, sầu riêng, măng cụt
- **Nón lá + áo bà ba:** Có thể thuê tại Cồn Phụng để chụp ảnh

## Tips content viral
1. **Xuồng ba lá Cồn Phụng:** Nữ chính mũi xuồng + nón lá, tổng tài chèo phía sau
2. **Vườn dừa:** Filter vintage, góc thấp nhìn lên hàng dừa thẳng tắp
3. **Vườn trái cây:** Tổng tài hái trái + biểu cảm bỡ ngỡ
4. **Cầu khỉ:** Tổng tài suit vest đi cầu khỉ = gap moe cực mạnh
5. **Resort pool:** Golden hour, tông ấm"""

itinerary = {
    "id": ITINERARY_ID,
    "type": "itinerary",
    "name": "Bến Tre 2N1Đ – Tổng tài đưa nữ chính về miền Tây",
    "summary": (
        "Lịch trình 2 ngày 1 đêm cuối tuần theo phong cách drama lãng mạn: "
        "tổng tài dẫn nữ chính khám phá xứ dừa Bến Tre. Chèo xuồng ba lá Cồn Phụng, "
        "thưởng thức kẹo dừa Mỏ Cày, dạo vườn trái cây Chợ Lách, nghỉ resort sinh thái. "
        "Xuất phát từ Bến xe Miền Tây (TP.HCM), tuyến đường tối ưu không quay đầu."
    ),
    "placeId": None,
    "confidence": 1.0,
    "season": None,
    "attributes": {
        "duration": "2 ngày 1 đêm",
        "style": "couple",
        "budget": "4.500.000–8.000.000đ/2 người",
        "difficulty": "dễ",
        "start_point": "ben-xe-mien-tay-hcm",
        "area": "ben-tre",
        "tags": [
            "couple", "romantic", "tổng tài", "weekend",
            "resort", "vườn trái cây", "miền Tây",
        ],
        "content": CONTENT,
    },
    "coordinates": [10.2376579, 106.3758519],
    "area": "ben-tre",
    "source": {"title": "Gợi ý từ vinhlong360", "url": None},
}


def add_to_json():
    with open(DATA_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Remove if already exists (idempotent)
    data["entities"] = [e for e in data["entities"] if e["id"] != ITINERARY_ID]
    data["entities"].append(itinerary)

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[data.json] Added '{ITINERARY_ID}'. Total entities: {len(data['entities'])}")


def add_to_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM entities WHERE id = ?", (ITINERARY_ID,))

    cur.execute(
        """INSERT INTO entities (id, type, name, summary, placeId, confidence, season, attributes, coordinates, area, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            itinerary["id"],
            itinerary["type"],
            itinerary["name"],
            itinerary["summary"],
            itinerary["placeId"],
            itinerary["confidence"],
            itinerary["season"],
            json.dumps(itinerary["attributes"], ensure_ascii=False),
            json.dumps(itinerary["coordinates"]),
            itinerary.get("area", "ben-tre"),
            json.dumps(itinerary["source"], ensure_ascii=False),
        ),
    )

    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM entities WHERE id = ?", (ITINERARY_ID,)).fetchone()[0]
    conn.close()
    print(f"[SQLite] Inserted '{ITINERARY_ID}'. Exists: {count}")


if __name__ == "__main__":
    add_to_json()
    add_to_db()
    print("Done!")

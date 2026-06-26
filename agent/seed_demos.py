"""DEPRECATED: This module is dead code (zero references in codebase).
One-time seed script, no longer needed. See docs/DEAD-CODE-AUDIT.md.

Seed curated high-quality demos vào pool và compile fewshot artifact."""
import json, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

POOL_PATH = os.path.join(os.path.dirname(__file__), "data", "optimizer", "demo_pool.json")

NEW_DEMOS = [
    {
        "intent": "itinerary",
        "query": "Lịch trình 2 ngày khám phá cù lao Vĩnh Long cho gia đình có trẻ em",
        "answer": (
            "**Lịch trình 2 ngày Cù lao An Bình – gia đình có trẻ**\n\n"
            "**Ngày 1 – Cù lao An Bình**\n"
            "- 7:30: Phà Đình Khao (bến TP Vĩnh Long) – 5.000đ, 5 phút\n"
            "- 8:00–11:00: Vườn trái cây (20.000đ/người), thử bưởi Năm Roi tươi\n"
            "- 12:00: Cơm nhà vườn (~80–120k/người)\n"
            "- 14:00: Đò chèo xem dừa nước (~150k/đò 4 người)\n"
            "- 16:00: Homestay có sân vườn an toàn cho trẻ (hỏi trước về ao)\n\n"
            "**Ngày 2 – Chợ Nổi + Gốm**\n"
            "- 5:30: Thuyền thăm Chợ Nổi Trà Ôn (100–200k/thuyền)\n"
            "- 9:00: Làng gốm Mang Thít (miễn phí, tự do)\n"
            "- 12:00: Về TP Vĩnh Long\n\n"
            "**Tips:** Mùa khô tháng 11–4 đi thuận tiện nhất. Homestay nên có phao bơi trẻ em."
        ),
        "score": 9.5,
    },
    {
        "intent": "recommendation",
        "query": "Đặc sản Trà Vinh nên mua về làm quà? Cái nào OCOP? Mua ở đâu?",
        "answer": (
            "**Đặc sản Trà Vinh đáng mua:**\n\n"
            "**OCOP 5 sao:**\n"
            "- Mật hoa dừa & đường hoa dừa Sokfarm – ~150.000đ/chai\n"
            "- Kẹo dừa sáp Vicosap (Cầu Kè) – hiếm, độc đáo\n\n"
            "**OCOP 4 sao:**\n"
            "- Dừa sáp Cầu Kè – ~50.000đ/trái\n"
            "- Bánh tét Trà Cuôn – ~30.000đ/đòn\n"
            "- Gạo hữu cơ Long Hòa–Hòa Minh\n\n"
            "**Mua ở đâu:**\n"
            "- Cửa hàng OCOP Trà Vinh: 40 Phường Trà Vinh, TP Trà Vinh\n"
            "- Cửa hàng OCOP Ao Bà Om: khu di tích Ao Bà Om\n"
            "- Co.opmart Trà Vinh có hầu hết sản phẩm OCOP"
        ),
        "score": 9.5,
    },
    {
        "intent": "recommendation",
        "query": "Chùa Khmer nào đẹp nhất ở Trà Vinh, đường đi thế nào?",
        "answer": (
            "**Top chùa Khmer Trà Vinh:**\n\n"
            "1. **Chùa Âng (Angkor Reach)** – lớn nhất, cổ nhất (thế kỷ 9)\n"
            "   Đường Mậu Thân, TP Trà Vinh | Miễn phí | Cạnh Ao Bà Om\n\n"
            "2. **Chùa Kompong (Ông Mẹt)** – đẹp nhất trung tâm TP\n"
            "   Miễn phí, ghé được khi đi bộ\n\n"
            "3. **Chùa Hang (Wat Kompong Chray)** – huyền bí, có vườn tượng\n"
            "   Châu Thành, cách TP ~10km\n\n"
            "**Đi từ TP.HCM:** Xe khách ~3h đến bến Trà Vinh, rồi xe ôm/thuê xe máy 150k/ngày.\n"
            "**Trang phục:** Kín đáo, bỏ giày khi vào chánh điện."
        ),
        "score": 9.5,
    },
    {
        "intent": "factual",
        "query": "Làng nghề gốm đỏ Mang Thít có gì? Giờ mở cửa, đi như thế nào?",
        "answer": (
            "**Làng gạch gốm đỏ Mang Thít** – di sản công nghiệp độc đáo nhất miền Tây\n\n"
            "Hàng trăm lò gạch hình tháp cổ dọc sông Mang Thít (~40km), cảnh quan đỏ rực\n"
            "đang được xét công nhận Di sản UNESCO.\n\n"
            "**Giờ:** Sáng sớm 6–9h đẹp nhất để chụp ảnh bình minh. Tự do cả ngày.\n"
            "**Phí:** Miễn phí ngoài trời. Vào xưởng hỏi chủ lò.\n"
            "**Địa chỉ:** Dọc QL53, Mang Thít, Vĩnh Long (~25km từ TP Vĩnh Long)\n"
            "**Di chuyển:** Thuê xe máy hoặc đặt tour thuyền sông (~200k/thuyền)\n\n"
            "**Tips:** Tour thuyền trên sông Mang Thít đẹp hơn nhìn từ bờ đường."
        ),
        "score": 9.5,
    },
    {
        "intent": "factual",
        "query": "Bến Tre có gì ngoài dừa và bánh kẹo?",
        "answer": (
            "**Bến Tre không chỉ có dừa:**\n\n"
            "**Thiên nhiên:**\n"
            "- Sân chim Vàm Hồ – hàng nghìn cò, vạc (mùa 9–3)\n"
            "- Rừng đước Long Khánh – kayak rừng ngập mặn\n"
            "- Cồn Phụng – đảo nhỏ di tích Đạo Dừa\n\n"
            "**Lịch sử:**\n"
            "- Khu di tích Đồng Khởi – phong trào 1960\n"
            "- Bảo tàng Bến Tre – khuôn viên 20.000m², Nhà Dừa độc đáo (50k/người, 7h–17h)\n"
            "- Khu lưu niệm Nguyễn Đình Chiểu\n\n"
            "**Làng nghề:**\n"
            "- Làng hoa kiểng Cái Mơn (Chợ Lách) – rực rỡ dịp Tết\n"
            "- Làng nghề đan đát, kẹo dừa – xem thợ làm trực tiếp\n\n"
            "Phù hợp kết hợp sinh thái + lịch sử. Tốt nhất tháng 11–4."
        ),
        "score": 9.5,
    },
    {
        "intent": "seasonal",
        "query": "Tháng mấy đi Vĩnh Long đẹp nhất?",
        "answer": (
            "**Tốt nhất: tháng 11 – tháng 4 (mùa khô)**\n\n"
            "- Ít mưa, kênh rạch trong, di chuyển dễ\n"
            "- Tết (tháng 1–2): Làng hoa Cái Mơn rực rỡ nhất\n\n"
            "**Tháng 5–10 (mùa mưa):** Cảnh xanh mướt hơn nhưng đi lại khó.\n"
            "Tháng 9–10 nước nổi – cánh đồng ngập đặc trưng miền Tây.\n\n"
            "**Sự kiện theo mùa:**\n"
            "- Xem chim Vàm Hồ (BT): tháng 9–3, sáng 5–7h\n"
            "- Hoa Cái Mơn: rực nhất tháng 12–2\n"
            "- Lễ hội Ok Om Bok (TV): tháng 10 âm lịch (~11–12 dương)"
        ),
        "score": 9.5,
    },
    {
        "intent": "comparison",
        "query": "Nên đi Vĩnh Long, Bến Tre hay Trà Vinh trước?",
        "answer": (
            "**Tùy mục đích:**\n\n"
            "**Vĩnh Long cũ** – cù lao + làng nghề gốm\n"
            "Mạnh về: cù lao An Bình, Chợ Nổi Trà Ôn, gốm Mang Thít\n"
            "Ideal: gia đình, nhóm bạn thích thiên nhiên + làng nghề\n\n"
            "**Bến Tre** – dừa + lịch sử + sân chim\n"
            "Mạnh về: Cồn Phụng, Đồng Khởi, Sân chim Vàm Hồ, hoa Cái Mơn\n"
            "Ideal: ghép với VL qua phà Đình Khao (5 phút)\n\n"
            "**Trà Vinh** – chùa Khmer + biển\n"
            "Mạnh về: chùa Khmer (Chùa Âng, Chùa Hang), Biển Ba Động, Ao Bà Om\n"
            "Ideal: văn hóa Khmer độc đáo, ít khách du lịch hơn\n\n"
            "**Gợi ý:** 3 ngày = VL 1 ngày + BT 1 ngày + TV 1 ngày. Cả 3 nằm gần nhau (xe khách ~1h giữa các tỉnh)."
        ),
        "score": 9.5,
    },
]

with open(POOL_PATH, encoding="utf-8") as f:
    pool = json.load(f)

existing_queries = {d["query"] for d in pool}
added = 0
for d in NEW_DEMOS:
    if d["query"] not in existing_queries:
        pool.append(d)
        added += 1

pool.sort(key=lambda d: d.get("score", 0), reverse=True)
pool = pool[:300]

with open(POOL_PATH, "w", encoding="utf-8") as f:
    json.dump(pool, f, ensure_ascii=False, indent=2)
print(f"Pool: {len(pool)} demos (+{added} new)")

import prompt_compiler
result = prompt_compiler.compile()
print(f"Compiled: {result}")

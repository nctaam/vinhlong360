"""
Tool definitions cho Knowledge Agent (OpenAI function calling format).
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Tìm kiếm trải nghiệm, đặc sản, điểm tham quan, làng nghề, ẩm thực, lưu trú trong tỉnh Vĩnh Long hiện hành. Tên Bến Tre/Trà Vinh chỉ được hiểu như địa danh lịch sử trong nội dung.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Từ khóa tìm kiếm (vd: 'dừa', 'cam sành', 'chùa Khmer')"
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": ["experience", "product", "dish", "craft_village", "attraction", "accommodation", "person", "event", "history", "nature", "economy"],
                        "description": "Loại: experience (trải nghiệm), product (đặc sản/OCOP), dish (ẩm thực), craft_village (làng nghề), attraction (tham quan), accommodation (lưu trú), person (nhân vật), event (sự kiện), history (lịch sử), nature (thiên nhiên), economy (kinh tế)"
                    },
                    "area": {
                        "type": "string",
                        "enum": ["vinh-long"],
                        "description": "Phạm vi tỉnh hiện hành: vinh-long"
                    },
                    "month": {
                        "type": "integer",
                        "minimum": 1, "maximum": 12,
                        "description": "Tháng (1-12) để lọc theo mùa vụ"
                    },
                    "ocop_only": {
                        "type": "boolean",
                        "description": "Chỉ lấy sản phẩm đạt chuẩn OCOP"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số kết quả tối đa (mặc định 10)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "entity_detail",
            "description": "Xem thông tin chi tiết của một thực thể (đặc sản, trải nghiệm, điểm tham quan...) theo ID. Bao gồm mùa vụ, giá, nguồn gốc, trạng thái kiểm chứng, và các thực thể liên quan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID của thực thể (vd: 'cam-sanh-tam-binh', 'ao-ba-om')"
                    }
                },
                "required": ["entity_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "seasonal_now",
            "description": "Xem sản phẩm và trải nghiệm đang vào mùa (peak season) trong tháng chỉ định.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "integer",
                        "minimum": 1, "maximum": 12,
                        "description": "Tháng cần xem (1-12)"
                    }
                },
                "required": ["month"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_itineraries",
            "description": "Xem danh sách lịch trình gợi ý. Có thể lọc theo khu vực.",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "enum": ["vinh-long"],
                        "description": "Lọc theo khu vực (tùy chọn)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "itinerary_detail",
            "description": "Xem chi tiết một lịch trình gợi ý, bao gồm các điểm dừng và thông tin từng điểm.",
            "parameters": {
                "type": "object",
                "properties": {
                    "itinerary_id": {
                        "type": "string",
                        "description": "ID lịch trình (vd: 'mot-ngay-cu-lao-an-binh')"
                    }
                },
                "required": ["itinerary_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "places_in_area",
            "description": "Danh sách các xã/phường trong một khu vực, kèm số lượng nội dung.",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "enum": ["vinh-long"],
                        "description": "Khu vực"
                    }
                },
                "required": ["area"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stats",
            "description": "Thống kê tổng quan về hệ thống: số lượng thực thể theo loại, số xã/phường, số lịch trình.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_areas",
            "description": "So sánh hai vùng provenance lịch sử trong dữ liệu Vĩnh Long (chỉ dùng khi cần phân tích tư liệu cũ; không phải bộ chọn tỉnh hiện hành).",
            "parameters": {
                "type": "object",
                "properties": {
                    "area_1": {
                        "type": "string",
                        "enum": ["vinh-long"],
                        "description": "Khu vực 1"
                    },
                    "area_2": {
                        "type": "string",
                        "enum": ["vinh-long", "ben-tre", "tra-vinh"],
                        "description": "Khu vực 2"
                    }
                },
                "required": ["area_1", "area_2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "nearby_entities",
            "description": "Tìm các thực thể gần một địa điểm (cùng xã/phường hoặc xã/phường lân cận). Dùng khi người dùng hỏi 'Gần đó có gì?', 'Quanh khu vực X có gì?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID entity làm tâm (vd: 'chua-vam-ray')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số kết quả tối đa (mặc định 8)"
                    }
                },
                "required": ["entity_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Tìm kiếm trên internet khi knowledge base không có thông tin. Dùng cho câu hỏi về: tin tức mới, sự kiện sắp tới, thông tin chưa có trong hệ thống. CHỈ dùng sau khi đã search knowledge base trước.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Truy vấn tìm kiếm (tiếng Việt, bao gồm 'Vĩnh Long' hoặc 'Bến Tre' hoặc 'Trà Vinh')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_followups",
            "description": "Gợi ý 3 câu hỏi tiếp theo cho người dùng, liên quan đến câu trả lời vừa đưa. Gọi SAU KHI đã trả lời xong câu hỏi chính.",
            "parameters": {
                "type": "object",
                "properties": {
                    "context": {
                        "type": "string",
                        "description": "Tóm tắt ngắn ngữ cảnh cuộc hội thoại (chủ đề, khu vực, loại thông tin)"
                    }
                },
                "required": ["context"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ocop_products",
            "description": "Tìm sản phẩm OCOP theo khu vực và hạng sao. Dùng khi hỏi 'đặc sản mua về làm quà', 'sản phẩm OCOP', 'hàng đạt chuẩn OCOP', 'quà từ BT/TV/VL'. Trả về danh sách sản phẩm kèm hạng sao, địa điểm mua, giá tham khảo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "enum": ["vinh-long"],
                        "description": "Phạm vi tỉnh hiện hành (bỏ trống = toàn tỉnh Vĩnh Long)"
                    },
                    "min_stars": {
                        "type": "integer",
                        "minimum": 3, "maximum": 5,
                        "description": "Hạng sao tối thiểu (3/4/5 sao, mặc định 3)"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["food", "drink", "craft", "all"],
                        "description": "Loại: food (thực phẩm), drink (đồ uống), craft (thủ công mỹ nghệ), all (tất cả)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số kết quả tối đa (mặc định 12)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "accommodation_search",
            "description": "Tìm chỗ lưu trú trong tỉnh Vĩnh Long hiện hành: homestay, nhà vườn, resort, khách sạn. Dùng khi hỏi 'ở đâu', 'homestay', 'chỗ ngủ', 'nhà vườn', 'resort'. Trả về tên, giá, địa chỉ, điện thoại, tiện nghi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "enum": ["vinh-long"],
                        "description": "Khu vực muốn ở"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["homestay", "resort", "hotel", "guesthouse", "all"],
                        "description": "Loại hình lưu trú"
                    },
                    "family_friendly": {
                        "type": "boolean",
                        "description": "Lọc chỗ phù hợp gia đình có trẻ em (sân vườn, an toàn)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số kết quả (mặc định 8)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_itinerary",
            "description": "Tạo lịch trình du lịch tùy chỉnh dựa trên sở thích, số ngày, khu vực, tháng đi và ngân sách. Trả về lịch trình chi tiết với thời gian, điểm dừng, ghi chú ăn uống, mẹo du lịch. Dùng khi du khách hỏi 'gợi ý lịch trình', 'đi đâu N ngày', 'lên kế hoạch du lịch'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "minimum": 1, "maximum": 5,
                        "description": "Số ngày (1-5, mặc định 1)"
                    },
                    "interests": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["am_thuc", "lich_su", "thien_nhien", "van_hoa", "mua_sam", "tham_quan"]
                        },
                        "description": "Sở thích: am_thuc (ẩm thực), lich_su (lịch sử), thien_nhien (thiên nhiên), van_hoa (văn hóa), mua_sam (mua sắm), tham_quan (tổng hợp)"
                    },
                    "areas": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["vinh-long"]
                        },
                        "description": "Phạm vi muốn đi (mặc định toàn tỉnh Vĩnh Long)"
                    },
                    "month": {
                        "type": "integer",
                        "minimum": 1, "maximum": 12,
                        "description": "Tháng đi (1-12, mặc định tháng hiện tại)"
                    },
                    "budget": {
                        "type": "string",
                        "enum": ["thap", "trung_binh", "cao"],
                        "description": "Ngân sách: thap (tiết kiệm), trung_binh (vừa phải), cao (sang trọng)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "weather",
            "description": "Xem thời tiết hiện tại và sự kiện sắp tới ở khu vực. Gồm nhiệt độ, mô tả, gợi ý hoạt động phù hợp thời tiết, và các lễ hội/sự kiện trong 14 ngày tới.",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "enum": ["vinh-long"],
                        "description": "Khu vực cần xem thời tiết"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "community_reviews",
            "description": "Xem đánh giá của cộng đồng (người dùng thật) về một địa điểm, sản phẩm, hay trải nghiệm. Trả về các review mới nhất kèm số sao.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID thực thể cần xem đánh giá (vd: 'gom-mang-thit', 'dua-sap-cau-ke')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số review tối đa (mặc định 5)"
                    }
                },
                "required": ["entity_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trending_posts",
            "description": "Xem bài viết nổi bật (nhiều tương tác) trên cộng đồng vinhlong360. Có thể lọc theo loại entity (du lịch, nông sản, ẩm thực...).",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["experience", "product", "dish", "craft_village", "attraction", "accommodation"],
                        "description": "Lọc theo loại (tùy chọn)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số bài tối đa (mặc định 10)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "directory_lookup",
            "description": "Tra DANH BẠ HÀNH CHÍNH: địa chỉ & số điện thoại cơ quan nhà nước (UBND, công an, trạm y tế, bưu điện…) theo tên cơ quan hoặc tên xã/phường. VD: 'UBND xã An Bình', 'công an phường 1', 'trạm y tế xã Bình Hòa Phước'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Tên cơ quan hoặc tên xã/phường cần tra danh bạ"
                    }
                },
                "required": ["query"]
            }
        }
    },
]

TOOLS_BY_NAME: dict[str, dict] = {
    tool["function"]["name"]: tool for tool in TOOLS
}
TOOL_NAMES: tuple[str, ...] = tuple(TOOLS_BY_NAME.keys())


def get_tools_by_names(names: list[str] | tuple[str, ...] | set[str]) -> list[dict]:
    """Return subset of tool definitions preserving requested order in O(K) time."""
    return [TOOLS_BY_NAME[name] for name in names if name in TOOLS_BY_NAME]


SYSTEM_PROMPT = """Bạn là biên tập viên sổ tay thực địa của vinhlong360.vn — am hiểu sâu về tỉnh Vĩnh Long hiện hành (124 xã/phường).

## Bối cảnh địa lý
Phạm vi hiện hành chỉ có tỉnh Vĩnh Long, vận hành theo mô hình 2 cấp (tỉnh → 124 xã/phường, bỏ cấp huyện) từ 01/07/2025.
- Khi người dùng nói "Vĩnh Long": mặc định là toàn tỉnh hiện hành và toàn bộ 124 xã/phường.
- "Bến Tre", "Trà Vinh" chỉ là địa danh lịch sử/provenance trong dữ liệu và nội dung; không phải lựa chọn tỉnh hiện hành.
- Các tên huyện/tỉnh cũ (Mang Thít, Tam Bình, Mỏ Cày, Cầu Kè...): dùng để tìm nội dung lịch sử, sau đó quy về xã/phường tương ứng trong Vĩnh Long hiện hành.

## Nhiệm vụ
- Giúp du khách và người dùng khám phá MỌI khía cạnh: du lịch, ẩm thực, lịch sử, văn hóa, nhân vật, thiên nhiên, kinh tế.
- Trả lời bằng tiếng Việt, thân thiện, dùng **markdown** (bold, danh sách, heading) để dễ đọc.
- LUÔN dùng tools tra cứu dữ liệu trước khi trả lời — không đoán.
- Nếu knowledge base không đủ, dùng `web_search` tìm thêm, ghi chú nguồn.
- Hỏi địa chỉ/số điện thoại cơ quan nhà nước (UBND/công an/trạm y tế/...) → dùng `directory_lookup` (tra theo tên cơ quan hoặc tên xã/phường).
- Ưu tiên mùa vụ hiện tại (`seasonal_now`); nếu `needs_verification: true` thì ghi chú nhẹ "nên xác nhận trước khi đi".
- Cuối mỗi câu trả lời, dùng `suggest_followups` gợi ý 3 câu hỏi tiếp theo.

## Di chuyển (kiến thức nền — dùng khi không có dữ liệu trong KB)
- **Từ TP.HCM đến Vĩnh Long**: xe khách ~2.5h, xe máy qua phà Mỹ Thuận hoặc cầu Mỹ Thuận (~130km).
- Các tuyến/địa danh Bến Tre cũ và Trà Vinh cũ nếu xuất hiện trong nội dung phải được gọi rõ là địa danh lịch sử thuộc tỉnh Vĩnh Long hiện hành.
- **Phà Đình Khao**: xe máy ~5.000đ, ô tô ~30.000đ, 24/7.
- **Cù lao An Bình**: phà từ bến phà An Bình (TP Vĩnh Long), xe máy ~5.000đ, 5 phút.
- **Cồn Phụng**: thuyền từ bến Bến Tre, ~30.000–50.000đ/người.
- **Chợ Nổi Trà Ôn**: đi thuyền thuê từ bến Trà Ôn, ~100.000–200.000đ/thuyền.
- Di chuyển nội tỉnh: xe ôm/grab, thuê xe máy ~150.000–200.000đ/ngày.
Nếu KB có `booking_note` hay `address` → dùng thông tin đó, bổ sung thêm kiến thức nền khi cần.

## Quy tắc tra cứu
- Đánh giá/review: dùng `community_reviews` để trích dẫn đánh giá thật.
- Xu hướng: dùng `trending_posts` để biết cộng đồng đang quan tâm gì.
- Trích dẫn review: ghi rõ tên và số sao, vd: "Theo đánh giá của Anh Minh (5/5 sao): ..."
- So sánh khu vực: dùng `compare_areas`.
- Lịch trình tùy chỉnh: dùng `generate_itinerary` (ngày, sở thích, khu vực, tháng, ngân sách).
- Lịch trình có sẵn: dùng `list_itineraries` + `itinerary_detail`.
- Gần đây: dùng `nearby_entities` khi hỏi "gần đó có gì?".
- Nhân vật/lịch sử: search entity_type=person hoặc history.

## Chất lượng dữ liệu (KHÔNG hiển thị điểm số cho người dùng)
- `verified: true`: dữ liệu đã kiểm chứng — dùng bình thường, không cần ghi chú.
- `verified: false`: provisional — ghi nhẹ "(chưa kiểm chứng chính thức)" nếu phù hợp ngữ cảnh.
- `needs_verification: true`: thông tin chưa chắc chắn — thêm ghi chú nhẹ nhàng "nên liên hệ xác nhận trước khi đi" hoặc "thông tin tham khảo, có thể thay đổi". KHÔNG bao giờ hiển thị con số "Độ tin cậy: 0.7" hay tương tự.
- `web_search`: ghi rõ "theo nguồn internet" để phân biệt với dữ liệu chính thức vinhlong360.

## Tránh bịa đặt (TUYỆT ĐỐI)
- CHỈ nêu tên, địa chỉ, giá, số liệu có trong kết quả tool. KHÔNG đoán hay bịa.
- Không tự chế tên điểm đến, món ăn, nhân vật, con số ngoài kết quả tra cứu.
- Thà nói "Mình chưa có thông tin xác thực về điểm này" còn hơn đưa thông tin sai.
- Khi dùng web_search vì KB thiếu dữ liệu, PHẢI ghi rõ là nguồn internet.

## Thông tin thực tế (LUÔN đưa vào câu trả lời nếu có)
Khi kết quả tool trả về các field sau, BẮT BUỘC nêu ngay trong câu trả lời:
- `hours`: **Giờ mở cửa: ...**
- `admission_fee`: **Giá vé / phí: ...**
- `best_time`: **Thời điểm lý tưởng: ...**
- `address`: **Địa chỉ: ...**
- `ocop`: gắn nhãn **OCOP [số sao]** bên cạnh tên sản phẩm
- `key_facts`: hiển thị dưới dạng gạch đầu dòng ngắn

Nếu tool không trả về các field này → không suy đoán, ghi "(chưa có thông tin giờ/phí — nên liên hệ trực tiếp trước khi đến)".

## Quy tắc lịch trình (itinerary)
Mỗi điểm PHẢI có: tên → giờ tham quan → giá vé (nếu có) → ghi chú thực tế (ăn gì, mua gì, đi bằng gì).
Đừng chỉ liệt kê tên — hãy cho biết mất bao lâu, giá khoảng bao nhiêu, đặc điểm nổi bật.

## Phong cách
Như người bạn địa phương am hiểu sâu, nhiệt tình — không phải chatbot doanh nghiệp.
Không sử dụng biểu tượng emoji trong câu trả lời; trình bày mạch lạc bằng chữ và danh sách markdown.
Trả lời có cấu trúc, gạch đầu dòng khi liệt kê > 2 mục.
Lịch trình: trình bày theo timeline (giờ → điểm đến → ghi chú), dễ theo dõi."""


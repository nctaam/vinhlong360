"""
Characterization tests cho agent/crawler.py — khoá hành vi HIỆN TẠI của các hàm
chưa phủ: make_slug, guess_entity_type, to_entity, extract_with_llm,
fetch_place_list, crawl_one, crawl_all.

KHÔNG network thật, KHÔNG gọi LLM thật: client OpenAI và fetch_page đều được
monkeypatch. OUTPUT_DIR luôn được trỏ vào tmp_path để không đụng agent/crawled/
thật trong repo (crawl_one/crawl_all ghi file JSON ra đó).

B6 (bất biến): crawler chỉ giữ trích đoạn + link nguồn, không re-host nguyên văn
nội dung cào — các test to_entity/crawl_one khoá hành vi cắt summary 200 ký tự
và lưu source.url.
"""

import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# crawler.py đọc os.environ["LLM_API_KEY"] / ["LLM_BASE_URL"] NGAY LÚC IMPORT
# (tạo OpenAI client — không gọi mạng khi khởi tạo). Đặt giá trị giả TRƯỚC khi
# import để không KeyError trên máy không có .env; setdefault giữ nguyên env thật.
os.environ.setdefault("LLM_API_KEY", "test-key-khong-goi-that")
os.environ.setdefault("LLM_BASE_URL", "http://127.0.0.1:9/v1")

import crawler


# ── Harness giả lập LLM client ──


class _RecordingCompletions:
    """Giả chat.completions: trả content cố định + ghi lại kwargs từng call."""

    def __init__(self, content: str):
        self._content = content
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _fake_llm(monkeypatch, content: str) -> _RecordingCompletions:
    completions = _RecordingCompletions(content)
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(crawler, "client", fake_client)
    return completions


# ── make_slug ──


class TestMakeSlug:
    def test_bo_dau_tieng_viet_va_noi_gach(self):
        assert crawler.make_slug("Chùa Tiên Châu") == "chua-tien-chau"

    def test_chu_d_gach_ngang_thanh_d(self):
        # NFD không tách được "đ" (U+0111 không decompose) — replace thủ công lo vụ này.
        assert crawler.make_slug("Đình Long Thanh") == "dinh-long-thanh"

    def test_ky_tu_dac_biet_gop_thanh_mot_gach_va_strip_bien(self):
        assert crawler.make_slug("Bánh tét Trà Cuôn!  (OCOP 4*)") == "banh-tet-tra-cuon-ocop-4"

    def test_cat_toi_da_60_ky_tu(self):
        assert crawler.make_slug("a" * 70) == "a" * 60

    def test_chuoi_rong_ra_chuoi_rong(self):
        assert crawler.make_slug("") == ""


# ── guess_entity_type ──


class TestGuessEntityType:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Khu du lịch sinh thái", "attraction"),
            ("Homestay ven sông", "accommodation"),
            ("tour chèo xuồng", "experience"),
            ("Làng nghề gạch gốm", "craft_village"),
            ("đặc sản OCOP", "product"),
            ("Ẩm thực địa phương", "dish"),
        ],
    )
    def test_map_keyword_ve_type_chuan(self, raw, expected):
        assert crawler.guess_entity_type(raw) == expected

    def test_khong_khop_keyword_nao_thi_mac_dinh_attraction(self):
        assert crawler.guess_entity_type("abc xyz") == "attraction"

    def test_khong_phan_biet_hoa_thuong(self):
        assert crawler.guess_entity_type("HOMESTAY") == "accommodation"

    def test_nhanh_khop_som_nhat_thang(self):
        # "du lịch" (nhánh 1 - attraction) đứng trước "homestay" (nhánh 2)
        # trong _ENTITY_TYPE_KEYWORDS → attraction thắng dù có chữ homestay.
        assert crawler.guess_entity_type("homestay khu du lịch") == "attraction"


# ── to_entity ──


class TestToEntity:
    def test_nhanh_chinh_du_truong(self):
        long_summary = "Vườn trái cây ven sông, đi xuồng, nghe đờn ca tài tử. " * 10
        extracted = {
            "name": "Homestay Út Trinh",
            "type": "homestay",
            "address": "Cù lao An Bình, tỉnh Vĩnh Long",
            "summary": long_summary,
            "services": ["ăn uống", "xe đạp", "xuồng", "lửa trại", "đờn ca", "câu cá", "spa"],
            "price": "500k/đêm",
            "hours": "7:00-21:00",
            "phone": "0123456789",
            "source_url": "https://vinhlongtourist.vn/vi/ut-trinh",
        }
        entity = crawler.to_entity(extracted, "/vi/ut-trinh")

        assert entity["id"] == "homestay-ut-trinh"
        assert entity["type"] == "accommodation"
        # "cù lao an bình" (key dài nhất, không phải fallback tỉnh) thắng.
        assert entity["placeId"] == "xa-an-binh"
        # B6: summary bị cắt còn đúng 200 ký tự đầu, không giữ nguyên văn dài.
        assert entity["summary"] == long_summary[:200]
        assert len(entity["summary"]) == 200
        assert entity["attributes"] == {
            "gia": "500k/đêm",
            "gio_mo_cua": "7:00-21:00",
            "sdt": "0123456789",
            # dich_vu chỉ join 5 dịch vụ đầu, phân cách ", "
            "dich_vu": "ăn uống, xe đạp, xuồng, lửa trại, đờn ca",
        }
        # B6: luôn giữ link nguồn — source_url từ extracted thắng.
        assert entity["source"] == {
            "title": "vinhlongtourist.vn",
            "url": "https://vinhlongtourist.vn/vi/ut-trinh",
        }
        assert entity["confidence"] == 0.85
        assert entity["season"] is None
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entity["updatedAt"])
        assert entity["_crawled_from"] == "/vi/ut-trinh"
        assert entity["_address_raw"] == "Cù lao An Bình, tỉnh Vĩnh Long"

    def test_dict_rong_ra_gia_tri_mac_dinh(self):
        entity = crawler.to_entity({}, "/vi/x")
        assert entity["id"] == "unknown"
        assert entity["name"] == "Unknown"
        assert entity["type"] == "attraction"
        assert entity["placeId"] is None
        assert entity["summary"] == ""
        assert entity["attributes"] == {}
        # Không có source_url → fallback ghép BASE_URL + url path.
        assert entity["source"]["url"] == crawler.BASE_URL + "/vi/x"

    def test_summary_none_khong_no(self):
        entity = crawler.to_entity({"name": "X", "summary": None}, "/vi/x")
        assert entity["summary"] == ""

    def test_dia_chi_tp_vinh_long_map_ve_long_chau(self):
        entity = crawler.to_entity(
            {"name": "Bảo tàng", "type": "bảo tàng", "address": "Phường 1, TP Vĩnh Long"},
            "/vi/bao-tang",
        )
        assert entity["placeId"] == "p-long-chau"
        assert entity["type"] == "attraction"


# ── extract_with_llm ──


class TestExtractWithLlm:
    def test_parse_json_boc_markdown_fence(self, monkeypatch):
        content = '```json\n{"name": "Chùa Tiên Châu", "type": "chùa"}\n```'
        completions = _fake_llm(monkeypatch, content)

        result = crawler.extract_with_llm("nội dung trang", "/vi/chua-tien-chau")

        assert result == {"name": "Chùa Tiên Châu", "type": "chùa"}
        assert len(completions.calls) == 1
        call = completions.calls[0]
        assert call["model"] == crawler.MODEL_MINI
        assert call["temperature"] == 0.1
        prompt = call["messages"][0]["content"]
        assert "nội dung trang" in prompt
        assert crawler.BASE_URL + "/vi/chua-tien-chau" in prompt
        # B6: prompt phải dặn LLM không sao chép nguyên văn, summary tối đa 200 ký tự.
        assert "KHÔNG sao chép nguyên văn" in prompt
        assert "tối đa 200 ký tự" in prompt

    def test_json_tran_khong_fence_van_parse(self, monkeypatch):
        _fake_llm(monkeypatch, '{"name": "A"}')
        assert crawler.extract_with_llm("t", "/vi/a") == {"name": "A"}

    def test_llm_tra_rac_thi_ve_none(self, monkeypatch):
        _fake_llm(monkeypatch, "xin lỗi, tôi không trích xuất được")
        assert crawler.extract_with_llm("t", "/vi/a") is None


# ── fetch_place_list ──


class TestFetchPlaceList:
    def test_nhanh_chinh_parse_array(self, monkeypatch):
        fetched_paths = []

        def fake_fetch_page(path):
            fetched_paths.append(path)
            return "danh sách các điểm"

        monkeypatch.setattr(crawler, "fetch_page", fake_fetch_page)
        content = '```json\n[{"name": "Chùa Tiên Châu", "url": "/vi/chua-tien-chau"}]\n```'
        completions = _fake_llm(monkeypatch, content)

        result = crawler.fetch_place_list()

        assert result == [{"name": "Chùa Tiên Châu", "url": "/vi/chua-tien-chau"}]
        assert fetched_paths == ["/vi/places"]
        prompt = completions.calls[0]["messages"][0]["content"]
        assert "danh sách các điểm" in prompt

    def test_llm_tra_rac_thi_ve_list_rong(self, monkeypatch):
        monkeypatch.setattr(crawler, "fetch_page", lambda path: "x")
        _fake_llm(monkeypatch, "không phải json")
        assert crawler.fetch_place_list() == []


# ── crawl_one ──


class TestCrawlOne:
    def test_nhanh_chinh_ghi_file_va_tra_entity(self, monkeypatch, tmp_path):
        raw_marker = "NOIDUNG-GOC-DAI-" * 50  # giả nguyên văn bài gốc
        monkeypatch.setattr(crawler, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(crawler, "fetch_page", lambda path: raw_marker)
        monkeypatch.setattr(
            crawler,
            "extract_with_llm",
            lambda text, url: {
                "name": "Điểm Test A",
                "type": "tham quan",
                "address": "xã An Bình",
                "summary": "Tóm tắt ngắn tự viết lại.",
                "source_url": "https://vinhlongtourist.vn/vi/diem-a",
            },
        )

        entity = crawler.crawl_one("/vi/diem-a")

        assert entity is not None
        assert entity["id"] == "diem-test-a"
        out_file = tmp_path / "diem-test-a.json"
        assert out_file.exists()
        saved = json.loads(out_file.read_text(encoding="utf-8"))
        assert saved == entity
        # B6: file lưu chỉ có trích đoạn + link, KHÔNG chứa nguyên văn trang gốc.
        raw_text = out_file.read_text(encoding="utf-8")
        assert "NOIDUNG-GOC-DAI-" not in raw_text
        assert saved["source"]["url"] == "https://vinhlongtourist.vn/vi/diem-a"

    def test_extract_none_thi_tra_none_khong_ghi_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(crawler, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(crawler, "fetch_page", lambda path: "t")
        monkeypatch.setattr(crawler, "extract_with_llm", lambda text, url: None)

        assert crawler.crawl_one("/vi/diem-a") is None
        assert list(tmp_path.iterdir()) == []

    def test_fetch_loi_thi_nuot_exception_tra_none(self, monkeypatch, tmp_path):
        monkeypatch.setattr(crawler, "OUTPUT_DIR", tmp_path)

        def boom(path):
            raise RuntimeError("mạng hỏng")

        monkeypatch.setattr(crawler, "fetch_page", boom)
        assert crawler.crawl_one("/vi/diem-a") is None


# ── crawl_all ──


class TestCrawlAll:
    def test_bo_qua_url_rong_gom_entity_va_ghi_tong_hop(self, monkeypatch, tmp_path):
        entity_a = {"id": "a", "name": "A", "placeId": None, "_address_raw": "đâu đó"}
        place_list = [
            {"name": "A", "url": "/vi/a"},
            {"name": "Rỗng", "url": ""},   # url rỗng → bị bỏ qua
            {"name": "B", "url": "/vi/b"},  # crawl_one trả None → không gom
            {"name": "Thiếu url"},          # không có key url → bị bỏ qua
        ]
        crawled_paths = []

        def fake_crawl_one(url):
            crawled_paths.append(url)
            return entity_a if url == "/vi/a" else None

        monkeypatch.setattr(crawler, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(crawler, "fetch_place_list", lambda: place_list)
        monkeypatch.setattr(crawler, "crawl_one", fake_crawl_one)
        monkeypatch.setattr(crawler.time, "sleep", lambda s: None)

        entities = crawler.crawl_all()

        assert entities == [entity_a]
        assert crawled_paths == ["/vi/a", "/vi/b"]
        all_file = tmp_path / "_all_crawled.json"
        assert all_file.exists()
        assert json.loads(all_file.read_text(encoding="utf-8")) == [entity_a]

    def test_danh_sach_rong_van_ghi_file_tong_hop_rong(self, monkeypatch, tmp_path):
        monkeypatch.setattr(crawler, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(crawler, "fetch_place_list", lambda: [])
        monkeypatch.setattr(crawler.time, "sleep", lambda s: None)

        assert crawler.crawl_all() == []
        assert json.loads((tmp_path / "_all_crawled.json").read_text(encoding="utf-8")) == []

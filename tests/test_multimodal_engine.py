"""Tests for multimodal_engine.py -- Level 7 multimodal processing engine."""

import sys
import os
import json
import struct
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from multimodal_engine import (
    TextAnalyzer,
    ImageAnalyzer,
    AudioProcessor,
    DocumentParser,
    MultimodalPipeline,
    ContentType,
    analyze_text,
    get_capabilities,
    text_analyzer,
    image_analyzer,
    audio_processor,
    video_processor,
    document_parser,
)


# ── Sample data helpers ─────────────────────────────────────────────────────

def _make_png_header(width=100, height=50):
    """Create minimal PNG header bytes."""
    sig = b"\x89PNG\r\n\x1a\n"
    # IHDR chunk: length(13) + "IHDR" + width(4) + height(4) + bit_depth(1) + color_type(1) + ...
    ihdr_data = struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00"
    ihdr_len = struct.pack(">I", 13)
    ihdr = ihdr_len + b"IHDR" + ihdr_data
    return sig + ihdr + b"\x00" * 20  # pad with zeros


def _make_jpeg_header():
    """Create minimal JPEG magic bytes."""
    return b"\xff\xd8\xff\xe0" + b"\x00" * 50


def _make_wav_header(sample_rate=44100, channels=2, bits=16, data_size=1000):
    """Create a valid WAV header."""
    byte_rate = sample_rate * channels * (bits // 8)
    block_align = channels * (bits // 8)
    # RIFF header
    riff = b"RIFF"
    file_size = struct.pack("<I", 36 + data_size)
    wave = b"WAVE"
    # fmt subchunk
    fmt_id = b"fmt "
    fmt_size = struct.pack("<I", 16)
    audio_fmt = struct.pack("<H", 1)  # PCM
    ch = struct.pack("<H", channels)
    sr = struct.pack("<I", sample_rate)
    br = struct.pack("<I", byte_rate)
    ba = struct.pack("<H", block_align)
    bps = struct.pack("<H", bits)
    # data subchunk
    data_id = b"data"
    ds = struct.pack("<I", data_size)
    data_bytes = b"\x00" * data_size

    return riff + file_size + wave + fmt_id + fmt_size + audio_fmt + ch + sr + br + ba + bps + data_id + ds + data_bytes


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestTextAnalyzer(unittest.TestCase):
    """Tests for TextAnalyzer."""

    def setUp(self):
        self.analyzer = TextAnalyzer()

    def test_analyze_returns_all_fields(self):
        result = self.analyzer.analyze("Vinh Long la tinh dep")
        self.assertIn("language", result)
        self.assertIn("keywords", result)
        self.assertIn("sentiment", result)
        self.assertIn("entity_mentions", result)
        self.assertIn("statistics", result)
        self.assertIn("intent", result)

    def test_detect_language_vietnamese(self):
        lang = TextAnalyzer.detect_language("Vĩnh Long là tỉnh đẹp nhất miền Tây")
        self.assertEqual(lang, "vi")

    def test_detect_language_english(self):
        lang = TextAnalyzer.detect_language("Vinh Long is a beautiful province")
        self.assertEqual(lang, "en")

    def test_detect_language_unknown(self):
        lang = TextAnalyzer.detect_language("12345")
        self.assertEqual(lang, "unknown")

    def test_extract_keywords(self):
        keywords = TextAnalyzer.extract_keywords("du lich Vinh Long dep lam, Vinh Long tuyet voi")
        self.assertIsInstance(keywords, list)
        words = {k["word"] for k in keywords}
        self.assertIn("vinh", words)
        self.assertIn("long", words)

    def test_extract_keywords_empty_text(self):
        keywords = TextAnalyzer.extract_keywords("")
        self.assertEqual(keywords, [])

    def test_sentiment_positive(self):
        result = TextAnalyzer.analyze_sentiment("Vinh Long tuyệt vời, rất đẹp và ngon")
        self.assertEqual(result["label"], "positive")
        self.assertGreater(result["positive_count"], 0)

    def test_sentiment_negative(self):
        result = TextAnalyzer.analyze_sentiment("terrible, boring, disappointing experience")
        self.assertEqual(result["label"], "negative")

    def test_sentiment_neutral(self):
        result = TextAnalyzer.analyze_sentiment("information about the province 12345")
        self.assertEqual(result["label"], "neutral")

    def test_intent_classification_search(self):
        result = TextAnalyzer.classify_intent("Tìm kiếm homestay ở đâu?")
        self.assertEqual(result["intent"], "search")

    def test_intent_classification_plan(self):
        result = TextAnalyzer.classify_intent("Lịch trình 2 ngày Vĩnh Long")
        self.assertEqual(result["intent"], "plan")

    def test_intent_classification_general(self):
        result = TextAnalyzer.classify_intent("hello there 12345")
        self.assertEqual(result["intent"], "general")


class TestImageAnalyzer(unittest.TestCase):
    """Tests for ImageAnalyzer."""

    def setUp(self):
        self.analyzer = ImageAnalyzer()

    def test_detect_jpeg(self):
        data = _make_jpeg_header()
        result = self.analyzer.analyze(data, "test.jpg")
        self.assertEqual(result["format"], "jpeg")

    def test_detect_png(self):
        data = _make_png_header(200, 100)
        result = self.analyzer.analyze(data, "test.png")
        self.assertEqual(result["format"], "png")

    def test_detect_png_dimensions(self):
        data = _make_png_header(320, 240)
        result = self.analyzer.analyze(data, "test.png")
        self.assertEqual(result.get("width"), 320)
        self.assertEqual(result.get("height"), 240)

    def test_detect_unknown_format(self):
        data = b"\x00\x01\x02\x03\x04\x05"
        result = self.analyzer.analyze(data, "test.xyz")
        self.assertEqual(result["format"], "unknown")

    def test_file_size_reported(self):
        data = _make_png_header()
        result = self.analyzer.analyze(data)
        self.assertEqual(result["file_size"], len(data))


class TestAudioProcessor(unittest.TestCase):
    """Tests for AudioProcessor."""

    def setUp(self):
        self.processor = AudioProcessor()

    def test_transcribe_returns_stub(self):
        data = b"\x00" * 100
        result = self.processor.transcribe(data)
        self.assertEqual(result["status"], "requires_whisper")
        self.assertFalse(result["available"])

    def test_wav_header_parsing(self):
        data = _make_wav_header(sample_rate=44100, channels=2, bits=16, data_size=88200)
        result = self.processor.analyze_audio(data)
        self.assertEqual(result["format"], "wav")
        self.assertEqual(result["sample_rate"], 44100)
        self.assertEqual(result["channels"], 2)
        self.assertEqual(result["bits_per_sample"], 16)
        self.assertGreater(result["duration_seconds"], 0)

    def test_non_wav_returns_unknown(self):
        data = b"\x00" * 100
        result = self.processor.analyze_audio(data)
        self.assertEqual(result["format"], "unknown")


class TestDocumentParser(unittest.TestCase):
    """Tests for DocumentParser."""

    def setUp(self):
        self.parser = DocumentParser()

    def test_parse_txt(self):
        data = "Hello world\nSecond line".encode("utf-8")
        result = self.parser.parse(data, "test.txt")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["format"], "txt")
        self.assertIn("Hello world", result["text"])
        self.assertEqual(result["line_count"], 2)

    def test_parse_csv(self):
        data = "name,age\nAlice,30\nBob,25".encode("utf-8")
        result = self.parser.parse(data, "test.csv")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["format"], "csv")
        self.assertEqual(result["row_count"], 3)
        self.assertEqual(result["headers"], ["name", "age"])

    def test_parse_json(self):
        obj = {"key": "value", "list": [1, 2, 3]}
        data = json.dumps(obj).encode("utf-8")
        result = self.parser.parse(data, "test.json")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["format"], "json")
        self.assertEqual(result["key_count"], 2)
        self.assertIn("key", result["keys"])

    def test_parse_json_list(self):
        data = json.dumps([1, 2, 3]).encode("utf-8")
        result = self.parser.parse(data, "data.json")
        self.assertEqual(result["item_count"], 3)

    def test_parse_unsupported_format(self):
        data = b"\x00" * 10
        result = self.parser.parse(data, "file.xyz")
        self.assertEqual(result["status"], "unsupported")

    def test_parse_pdf_stub(self):
        data = b"%PDF-1.4 some content"
        result = self.parser.parse(data, "doc.pdf")
        self.assertEqual(result["status"], "requires_library")
        self.assertEqual(result["format"], "pdf")


class TestMultimodalPipeline(unittest.TestCase):
    """Tests for MultimodalPipeline."""

    def setUp(self):
        self.pipeline = MultimodalPipeline(
            text_analyzer, image_analyzer, audio_processor,
            video_processor, document_parser,
        )

    def test_process_single_text_auto_detect(self):
        item = self.pipeline.process_single("Hello world text")
        self.assertEqual(item.content_type, ContentType.TEXT)
        self.assertIsNotNone(item.analysis)
        self.assertIn("language", item.analysis)

    def test_process_single_image(self):
        data = _make_png_header(100, 50)
        item = self.pipeline.process_single(data, content_type="auto", filename="img.png")
        self.assertEqual(item.content_type, ContentType.IMAGE)
        self.assertEqual(item.analysis["format"], "png")

    def test_process_single_document(self):
        data = b"plain text content"
        item = self.pipeline.process_single(data, content_type="auto", filename="readme.txt")
        self.assertEqual(item.content_type, ContentType.DOCUMENT)

    def test_get_capabilities(self):
        caps = get_capabilities()
        self.assertIn("text", caps)
        self.assertIn("image", caps)
        self.assertIn("audio", caps)
        self.assertIn("video", caps)
        self.assertIn("document", caps)
        self.assertEqual(caps["text"]["status"], "fully_functional")


class TestAnalyzeTextConvenience(unittest.TestCase):
    """Tests for analyze_text convenience function."""

    def test_returns_dict(self):
        result = analyze_text("Vinh Long travel guide")
        self.assertIsInstance(result, dict)
        self.assertIn("language", result)
        self.assertIn("keywords", result)
        self.assertIn("sentiment", result)


if __name__ == "__main__":
    unittest.main()

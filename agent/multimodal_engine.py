"""
vinhlong360 — Multimodal Processing Engine.

Xử lý đa phương tiện cho Knowledge Agent:
  - Text analysis: phân tích đầy đủ (ngôn ngữ, từ khóa, sentiment, entities)
  - Image analysis: parse header JPEG/PNG, EXIF GPS cơ bản
  - Audio processing: stub (requires ffmpeg/Whisper)
  - Video processing: stub (requires ffmpeg)
  - Document parsing: .txt, .csv, .json đầy đủ; .pdf/.docx stub

Persistence: agent/data/multimodal/

Thread-safe, chỉ dùng stdlib.
"""

import base64
import csv
import io
import json
import logging
import mimetypes
import re
import struct
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data" / "multimodal"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════
#  1. ContentType enum
# ══════════════════════════════════════════════════

class ContentType(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


# ══════════════════════════════════════════════════
#  2. MediaItem dataclass
# ══════════════════════════════════════════════════

@dataclass
class MediaItem:
    id: str
    content_type: ContentType
    source_path: str | None = None
    raw_data: bytes | None = None
    metadata: dict = field(default_factory=dict)
    extracted_text: str | None = None
    analysis: dict | None = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Serialize to dict, excluding raw_data (binary)."""
        return {
            "id": self.id,
            "content_type": self.content_type.value,
            "source_path": self.source_path,
            "metadata": self.metadata,
            "extracted_text": self.extracted_text,
            "analysis": self.analysis,
            "created_at": self.created_at,
        }


# ══════════════════════════════════════════════════
#  3. TextAnalyzer — FULLY FUNCTIONAL
# ══════════════════════════════════════════════════

# Vietnamese diacritical characters for language detection
_VN_DIACRITICS = set("àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩ"
                     "òóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
                     "ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨ"
                     "ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ")

# ── Sentiment word lists (Vietnamese) ──

_POSITIVE_WORDS_VI = {
    "tốt", "đẹp", "ngon", "tuyệt", "hay", "thích", "yêu", "vui",
    "xuất sắc", "tuyệt vời", "tuyệt đẹp", "thú vị", "hấp dẫn",
    "nổi tiếng", "đặc sắc", "thoải mái", "ấn tượng", "độc đáo",
    "trải nghiệm", "khám phá", "tiện nghi", "sạch sẽ", "thân thiện",
    "rẻ", "giá rẻ", "hợp lý", "chất lượng", "an toàn", "bình yên",
    "dễ thương", "xinh", "mới", "hiện đại", "phong phú", "đa dạng",
    "nên", "recommend", "good", "great", "excellent", "beautiful",
    "amazing", "wonderful", "love", "best", "nice", "perfect",
}

_NEGATIVE_WORDS_VI = {
    "xấu", "tệ", "dở", "chán", "buồn", "ghét", "sợ", "bẩn",
    "đắt", "đông", "ồn", "nóng", "lạnh", "nguy hiểm", "khó chịu",
    "thất vọng", "chậm", "cũ", "hỏng", "tồi", "kém", "không tốt",
    "không ngon", "không đẹp", "bad", "terrible", "poor", "dirty",
    "expensive", "boring", "disappointing", "worst", "ugly", "slow",
}

# ── Tourism intent keywords ──

_INTENT_KEYWORDS = {
    "search": [
        "tìm", "tìm kiếm", "ở đâu", "where", "find", "search",
        "có gì", "chỗ nào", "nơi nào", "địa chỉ", "location",
    ],
    "compare": [
        "so sánh", "khác nhau", "compare", "difference", "vs",
        "hay hơn", "tốt hơn", "nên chọn", "which", "better",
    ],
    "plan": [
        "lịch trình", "kế hoạch", "plan", "itinerary", "schedule",
        "bao lâu", "mấy ngày", "how long", "ngày", "trip",
    ],
    "recommend": [
        "gợi ý", "đề xuất", "recommend", "suggest", "nên đi",
        "nên ăn", "nên thử", "should", "must try", "top",
        "hay nhất", "tốt nhất", "phổ biến", "nổi tiếng",
    ],
}


class TextAnalyzer:
    """Phân tích text đầy đủ: ngôn ngữ, từ khóa, sentiment, entities, intent."""

    def __init__(self):
        self._lock = Lock()
        self._entity_names: list[tuple[str, str]] | None = None  # [(name, id)]
        self._stats = {"calls": 0, "total_words": 0}

    # ── Language detection ──

    @staticmethod
    def detect_language(text: str) -> str:
        """Phát hiện ngôn ngữ: 'vi' hoặc 'en' dựa trên dấu tiếng Việt."""
        vn_count = sum(1 for ch in text if ch in _VN_DIACRITICS)
        alpha_count = sum(1 for ch in text if ch.isalpha())
        if alpha_count == 0:
            return "unknown"
        ratio = vn_count / alpha_count
        # Vietnamese text usually has >5% diacritical chars
        return "vi" if ratio > 0.05 else "en"

    # ── Tokenization ──

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tách từ: split trên khoảng trắng / dấu câu, lowercase."""
        raw = re.split(r"[\s,.\-_/\\;:!?()\"'\[\]{}<>|@#$%^&*+=~`]+", text.lower())
        return [w for w in raw if w and len(w) > 1]

    # ── Keyword extraction (TF-based) ──

    @staticmethod
    def extract_keywords(text: str, top_n: int = 10) -> list[dict]:
        """Trích xuất từ khóa dựa trên tần suất (TF)."""
        tokens = TextAnalyzer.tokenize(text)
        if not tokens:
            return []

        # Vietnamese stop words
        stop_words = {
            "của", "và", "là", "có", "được", "cho", "với", "các",
            "trong", "này", "đã", "từ", "một", "không", "những",
            "theo", "về", "tại", "bị", "do", "sẽ", "để", "khi",
            "nếu", "đến", "như", "cũng", "vì", "hay", "mà", "ra",
            "lên", "vào", "rồi", "rất", "thì", "còn", "nhưng",
            "the", "is", "at", "on", "in", "to", "of", "and",
            "for", "it", "an", "by", "or", "as", "be", "was",
            "are", "this", "that", "with", "from", "but", "not",
        }

        freq: dict[str, int] = {}
        for t in tokens:
            if t not in stop_words and len(t) > 1:
                freq[t] = freq.get(t, 0) + 1

        total = len(tokens)
        ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return [{"word": w, "count": c, "tf": round(c / total, 4)} for w, c in ranked]

    # ── Sentiment analysis ──

    @staticmethod
    def analyze_sentiment(text: str) -> dict:
        """Phân tích sentiment đơn giản bằng word lists."""
        lower = text.lower()
        tokens = set(TextAnalyzer.tokenize(text))

        pos_count = 0
        neg_count = 0
        pos_matches = []
        neg_matches = []

        for word in _POSITIVE_WORDS_VI:
            if word in tokens or word in lower:
                pos_count += 1
                pos_matches.append(word)

        for word in _NEGATIVE_WORDS_VI:
            if word in tokens or word in lower:
                neg_count += 1
                neg_matches.append(word)

        total = pos_count + neg_count
        if total == 0:
            label = "neutral"
            score = 0.0
        elif pos_count > neg_count:
            label = "positive"
            score = round(pos_count / total, 2)
        elif neg_count > pos_count:
            label = "negative"
            score = round(-neg_count / total, 2)
        else:
            label = "mixed"
            score = 0.0

        return {
            "label": label,
            "score": score,
            "positive_matches": pos_matches[:5],
            "negative_matches": neg_matches[:5],
            "positive_count": pos_count,
            "negative_count": neg_count,
        }

    # ── Entity mention detection ──

    def _load_entity_names(self):
        """Lazy-load entity names from knowledge base."""
        if self._entity_names is not None:
            return
        try:
            from . import knowledge
            knowledge._ensure()
            names = []
            for eid, e in knowledge._entities.items():
                name = e.get("name", "")
                if name and len(name) > 2:
                    names.append((name.lower(), eid))
            self._entity_names = names
        except Exception as exc:
            logger.debug("Could not load entity names: %s", exc)
            self._entity_names = []

    def detect_entity_mentions(self, text: str) -> list[dict]:
        """Tìm tên entities từ knowledge base trong text."""
        with self._lock:
            self._load_entity_names()

        lower = text.lower()
        mentions = []
        seen = set()
        for name, eid in self._entity_names:
            if name in lower and eid not in seen:
                # Find approximate position
                pos = lower.find(name)
                mentions.append({
                    "entity_id": eid,
                    "name": name,
                    "position": pos,
                })
                seen.add(eid)

        return sorted(mentions, key=lambda m: m["position"])

    # ── Summary statistics ──

    @staticmethod
    def compute_stats(text: str) -> dict:
        """Thống kê cơ bản: word_count, sentence_count, avg, readability."""
        words = TextAnalyzer.tokenize(text)
        word_count = len(words)

        # Sentence splitting: by ., !, ?, newlines
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if s.strip()]
        sentence_count = max(len(sentences), 1)

        avg_sentence_length = round(word_count / sentence_count, 1)

        # Simple readability: average word length (proxy for complexity)
        avg_word_length = (
            round(sum(len(w) for w in words) / word_count, 1) if word_count else 0
        )
        # Simple score: shorter words + shorter sentences = more readable (0-100)
        readability_score = max(0, min(100, round(
            100 - (avg_word_length - 3) * 10 - (avg_sentence_length - 10) * 2
        )))

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": avg_sentence_length,
            "avg_word_length": avg_word_length,
            "readability_score": readability_score,
            "char_count": len(text),
        }

    # ── Tourism intent classification ──

    @staticmethod
    def classify_intent(text: str) -> dict:
        """Phân loại intent du lịch: search/compare/plan/recommend/general."""
        lower = text.lower()
        scores: dict[str, int] = {}

        for intent, keywords in _INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score > 0:
                scores[intent] = score

        if not scores:
            return {"intent": "general", "confidence": 0.5, "scores": {}}

        best = max(scores, key=scores.get)
        total_hits = sum(scores.values())
        confidence = round(min(scores[best] / max(total_hits, 1) + 0.3, 1.0), 2)

        return {
            "intent": best,
            "confidence": confidence,
            "scores": scores,
        }

    # ── Main analyze ──

    def analyze(self, text: str) -> dict:
        """Phân tích text đầy đủ."""
        with self._lock:
            self._stats["calls"] += 1

        language = self.detect_language(text)
        keywords = self.extract_keywords(text)
        sentiment = self.analyze_sentiment(text)
        entities = self.detect_entity_mentions(text)
        stats = self.compute_stats(text)
        intent = self.classify_intent(text)

        with self._lock:
            self._stats["total_words"] += stats["word_count"]

        return {
            "language": language,
            "keywords": keywords,
            "sentiment": sentiment,
            "entity_mentions": entities,
            "statistics": stats,
            "intent": intent,
        }


# ══════════════════════════════════════════════════
#  4. ImageAnalyzer — BASIC (stdlib only)
# ══════════════════════════════════════════════════

# Magic bytes for image format detection
_IMAGE_MAGIC = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"RIFF": "webp",  # RIFF....WEBP
    b"BM": "bmp",
}


class ImageAnalyzer:
    """Phân tích ảnh cơ bản: format, dimensions, EXIF GPS."""

    def __init__(self):
        self._lock = Lock()
        self._stats = {"calls": 0, "formats": {}}

    @staticmethod
    def _detect_format(data: bytes) -> str:
        """Phát hiện format ảnh từ magic bytes."""
        for magic, fmt in _IMAGE_MAGIC.items():
            if data[:len(magic)] == magic:
                if fmt == "webp" and len(data) > 12:
                    # RIFF....WEBP
                    if data[8:12] == b"WEBP":
                        return "webp"
                    return "unknown"
                return fmt
        return "unknown"

    @staticmethod
    def _parse_png_dimensions(data: bytes) -> tuple[int, int] | None:
        """Đọc width/height từ PNG IHDR chunk."""
        # PNG signature (8 bytes) + IHDR length (4) + "IHDR" (4) + width (4) + height (4)
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        try:
            width = struct.unpack(">I", data[16:20])[0]
            height = struct.unpack(">I", data[20:24])[0]
            return (width, height)
        except struct.error:
            return None

    @staticmethod
    def _parse_jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
        """Đọc width/height từ JPEG SOF marker."""
        if len(data) < 4 or data[:2] != b"\xff\xd8":
            return None
        offset = 2
        while offset < len(data) - 1:
            if data[offset] != 0xFF:
                offset += 1
                continue
            marker = data[offset + 1]
            # SOF markers: 0xC0-0xC3
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                if offset + 9 < len(data):
                    try:
                        height = struct.unpack(">H", data[offset + 5:offset + 7])[0]
                        width = struct.unpack(">H", data[offset + 7:offset + 9])[0]
                        return (width, height)
                    except struct.error:
                        return None
            # Skip to next marker
            if offset + 3 < len(data):
                try:
                    seg_len = struct.unpack(">H", data[offset + 2:offset + 4])[0]
                    offset += 2 + seg_len
                except struct.error:
                    break
            else:
                break
        return None

    @staticmethod
    def _parse_jpeg_exif_gps(data: bytes) -> dict | None:
        """Trích xuất GPS cơ bản từ JPEG EXIF (APP1 marker)."""
        if len(data) < 12 or data[:2] != b"\xff\xd8":
            return None

        # Find APP1 marker (0xFFE1)
        offset = 2
        app1_data = None
        while offset < len(data) - 4:
            if data[offset] != 0xFF:
                offset += 1
                continue
            marker = data[offset + 1]
            try:
                seg_len = struct.unpack(">H", data[offset + 2:offset + 4])[0]
            except struct.error:
                break
            if marker == 0xE1:
                # APP1 found
                end = offset + 2 + seg_len
                if end <= len(data):
                    app1_data = data[offset + 4:end]
                break
            offset += 2 + seg_len

        if not app1_data or len(app1_data) < 14:
            return None

        # Check Exif header
        if app1_data[:6] not in (b"Exif\x00\x00", b"Exif\x00\xff"):
            return None

        tiff_data = app1_data[6:]
        if len(tiff_data) < 8:
            return None

        # Determine byte order
        if tiff_data[:2] == b"MM":
            endian = ">"
        elif tiff_data[:2] == b"II":
            endian = "<"
        else:
            return None

        # Parse IFD0 to find GPS IFD pointer (tag 0x8825)
        try:
            ifd_offset = struct.unpack(endian + "I", tiff_data[4:8])[0]
            if ifd_offset + 2 > len(tiff_data):
                return None
            num_entries = struct.unpack(endian + "H",
                                       tiff_data[ifd_offset:ifd_offset + 2])[0]

            gps_ifd_offset = None
            for i in range(num_entries):
                entry_start = ifd_offset + 2 + i * 12
                if entry_start + 12 > len(tiff_data):
                    break
                tag = struct.unpack(endian + "H",
                                    tiff_data[entry_start:entry_start + 2])[0]
                if tag == 0x8825:  # GPSInfo
                    gps_ifd_offset = struct.unpack(
                        endian + "I",
                        tiff_data[entry_start + 8:entry_start + 12]
                    )[0]
                    break

            if gps_ifd_offset is None:
                return None

            # Parse GPS IFD entries
            if gps_ifd_offset + 2 > len(tiff_data):
                return None
            gps_entries = struct.unpack(
                endian + "H",
                tiff_data[gps_ifd_offset:gps_ifd_offset + 2]
            )[0]

            gps_tags: dict[int, tuple] = {}
            for i in range(gps_entries):
                es = gps_ifd_offset + 2 + i * 12
                if es + 12 > len(tiff_data):
                    break
                g_tag = struct.unpack(endian + "H", tiff_data[es:es + 2])[0]
                g_type = struct.unpack(endian + "H", tiff_data[es + 2:es + 4])[0]
                g_count = struct.unpack(endian + "I", tiff_data[es + 4:es + 8])[0]

                # Rational type (5) = unsigned, (10) = signed
                if g_type in (5, 10) and g_count >= 1:
                    val_offset = struct.unpack(endian + "I",
                                               tiff_data[es + 8:es + 12])[0]
                    rationals = []
                    for j in range(min(g_count, 3)):
                        ro = val_offset + j * 8
                        if ro + 8 > len(tiff_data):
                            break
                        num = struct.unpack(endian + "I",
                                            tiff_data[ro:ro + 4])[0]
                        den = struct.unpack(endian + "I",
                                            tiff_data[ro + 4:ro + 8])[0]
                        rationals.append(num / den if den else 0)
                    gps_tags[g_tag] = tuple(rationals)

                # ASCII type (2)
                elif g_type == 2:
                    if g_count <= 4:
                        val_bytes = tiff_data[es + 8:es + 8 + g_count]
                    else:
                        val_offset = struct.unpack(endian + "I",
                                                   tiff_data[es + 8:es + 12])[0]
                        val_bytes = tiff_data[val_offset:val_offset + g_count]
                    gps_tags[g_tag] = val_bytes.rstrip(b"\x00").decode(
                        "ascii", errors="ignore"
                    )

            # Convert GPS DMS to decimal
            def dms_to_decimal(dms_tuple: tuple, ref: str) -> float | None:
                if len(dms_tuple) < 3:
                    return None
                deg, minutes, sec = dms_tuple
                decimal = deg + minutes / 60 + sec / 3600
                if ref in ("S", "W"):
                    decimal = -decimal
                return round(decimal, 6)

            lat_ref = gps_tags.get(1, "N")  # GPSLatitudeRef
            lat_dms = gps_tags.get(2)       # GPSLatitude
            lon_ref = gps_tags.get(3, "E")  # GPSLongitudeRef
            lon_dms = gps_tags.get(4)       # GPSLongitude

            if lat_dms and lon_dms:
                lat = dms_to_decimal(lat_dms, lat_ref)
                lon = dms_to_decimal(lon_dms, lon_ref)
                if lat is not None and lon is not None:
                    return {"latitude": lat, "longitude": lon}

        except (struct.error, IndexError, ValueError) as exc:
            logger.debug("EXIF GPS parse error: %s", exc)

        return None

    def analyze(self, data: bytes, filename: str = "") -> dict:
        """Phân tích ảnh: format, dimensions, EXIF GPS, file_size."""
        fmt = self._detect_format(data)

        with self._lock:
            self._stats["calls"] += 1
            self._stats["formats"][fmt] = self._stats["formats"].get(fmt, 0) + 1

        result: dict = {
            "format": fmt,
            "file_size": len(data),
            "filename": filename,
        }

        # Dimensions
        dims = None
        if fmt == "jpeg":
            dims = self._parse_jpeg_dimensions(data)
        elif fmt == "png":
            dims = self._parse_png_dimensions(data)

        if dims:
            result["width"], result["height"] = dims

        # EXIF GPS for JPEG
        if fmt == "jpeg":
            gps = self._parse_jpeg_exif_gps(data)
            if gps:
                result["gps"] = gps

        return result

    def analyze_from_path(self, path: str) -> dict:
        """Load file rồi analyze."""
        p = Path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        if not p.is_file():
            return {"error": f"Not a file: {path}"}
        data = p.read_bytes()
        return self.analyze(data, filename=p.name)

    def analyze_content(self, data: bytes, model_fn=None) -> dict:
        """
        Hook cho Vision LLM trong tương lai.

        model_fn(base64_image: str) -> dict nếu có.
        Fallback: chỉ parse header.
        """
        basic = self.analyze(data)
        if model_fn is not None:
            try:
                b64 = base64.b64encode(data).decode("ascii")
                vision_result = model_fn(b64)
                basic["vision_analysis"] = vision_result
            except Exception as exc:
                logger.warning("Vision model call failed: %s", exc)
                basic["vision_analysis"] = {"error": str(exc)}
        else:
            basic["vision_analysis"] = {
                "status": "no_model",
                "note": "Pass model_fn for vision analysis",
            }
        return basic


# ══════════════════════════════════════════════════
#  5. AudioProcessor — STUB with framework
# ══════════════════════════════════════════════════

class AudioProcessor:
    """Xử lý audio: WAV header parsing + stub cho transcription."""

    def __init__(self):
        self._lock = Lock()
        self._stats = {"calls": 0}

    @staticmethod
    def _parse_wav_header(data: bytes) -> dict | None:
        """Parse WAV RIFF header: sample_rate, channels, duration."""
        if len(data) < 44:
            return None
        if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
            return None
        try:
            # fmt sub-chunk
            if data[12:16] != b"fmt ":
                return None
            channels = struct.unpack("<H", data[22:24])[0]
            sample_rate = struct.unpack("<I", data[24:28])[0]
            byte_rate = struct.unpack("<I", data[28:32])[0]
            bits_per_sample = struct.unpack("<H", data[34:36])[0]

            # data sub-chunk — find it (may not be at offset 36)
            offset = 36
            data_size = 0
            while offset + 8 <= len(data):
                chunk_id = data[offset:offset + 4]
                chunk_size = struct.unpack("<I", data[offset + 4:offset + 8])[0]
                if chunk_id == b"data":
                    data_size = chunk_size
                    break
                offset += 8 + chunk_size

            duration = data_size / byte_rate if byte_rate > 0 else 0

            return {
                "format": "wav",
                "channels": channels,
                "sample_rate": sample_rate,
                "bits_per_sample": bits_per_sample,
                "byte_rate": byte_rate,
                "data_size": data_size,
                "duration_seconds": round(duration, 2),
                "file_size": len(data),
            }
        except (struct.error, ZeroDivisionError) as exc:
            logger.debug("WAV parse error: %s", exc)
            return None

    def transcribe(self, data: bytes, format: str = "wav",
                   transcribe_fn=None) -> dict:
        """
        Transcribe audio thành text.

        transcribe_fn(data: bytes, format: str) -> str nếu có (Whisper/etc).
        Mặc định: stub.
        """
        with self._lock:
            self._stats["calls"] += 1

        if transcribe_fn is not None:
            try:
                text = transcribe_fn(data, format)
                return {"status": "ok", "text": text, "format": format}
            except Exception as exc:
                logger.warning("Transcription callback failed: %s", exc)
                return {"status": "error", "error": str(exc)}

        return {
            "status": "requires_whisper",
            "available": False,
            "note": "Pass transcribe_fn callback or install Whisper for transcription",
            "format": format,
            "file_size": len(data),
        }

    def analyze_audio(self, data: bytes) -> dict:
        """Phân tích audio: WAV header parsing."""
        with self._lock:
            self._stats["calls"] += 1

        wav_info = self._parse_wav_header(data)
        if wav_info:
            return wav_info

        return {
            "format": "unknown",
            "file_size": len(data),
            "note": "Only WAV header parsing supported with stdlib",
        }


# ══════════════════════════════════════════════════
#  6. VideoProcessor — STUB with framework
# ══════════════════════════════════════════════════

class VideoProcessor:
    """Xử lý video: stub, cần ffmpeg cho processing thực tế."""

    def __init__(self):
        self._lock = Lock()
        self._stats = {"calls": 0}

    def analyze(self, path: str) -> dict:
        """Phân tích video — stub, requires ffmpeg."""
        with self._lock:
            self._stats["calls"] += 1

        p = Path(path)
        result = {
            "status": "requires_ffmpeg",
            "available": False,
            "note": "Video analysis requires ffmpeg; install it for full support",
        }

        if p.exists() and p.is_file():
            result["filename"] = p.name
            result["file_size"] = p.stat().st_size
            result["extension"] = p.suffix.lower()
        else:
            result["error"] = f"File not found: {path}"

        return result

    def process(self, path: str, extract_frames_fn=None,
                transcribe_fn=None) -> dict:
        """
        Pipeline video: extract frames + transcribe audio.

        extract_frames_fn(path: str) -> list[bytes]  (frame images)
        transcribe_fn(path: str) -> str               (audio transcript)

        Cả hai đều optional; nếu không có → stub.
        """
        with self._lock:
            self._stats["calls"] += 1

        result: dict = {"source": path, "steps": {}}

        # Frame extraction
        if extract_frames_fn is not None:
            try:
                frames = extract_frames_fn(path)
                result["steps"]["frames"] = {
                    "status": "ok",
                    "frame_count": len(frames),
                }
            except Exception as exc:
                result["steps"]["frames"] = {"status": "error", "error": str(exc)}
        else:
            result["steps"]["frames"] = {
                "status": "requires_ffmpeg",
                "available": False,
            }

        # Audio transcription
        if transcribe_fn is not None:
            try:
                transcript = transcribe_fn(path)
                result["steps"]["transcript"] = {
                    "status": "ok",
                    "text": transcript,
                }
            except Exception as exc:
                result["steps"]["transcript"] = {"status": "error", "error": str(exc)}
        else:
            result["steps"]["transcript"] = {
                "status": "requires_whisper",
                "available": False,
            }

        return result


# ══════════════════════════════════════════════════
#  7. DocumentParser — FUNCTIONAL for plain text
# ══════════════════════════════════════════════════

# Vietnamese place names / price / date patterns for tourism extraction
_VN_PLACE_PATTERN = re.compile(
    r"(?:Vĩnh Long|Bến Tre|Trà Vinh|Cần Thơ|ĐBSCL|"
    r"Mỹ Tho|Châu Đốc|Long Xuyên|Hồ Chí Minh|Sài Gòn|"
    r"Phú Quốc|Đà Lạt|Nha Trang|Huế|Hà Nội|Đà Nẵng|"
    r"xã\s+\w+|phường\s+\w+|huyện\s+\w+|thành phố\s+\w+|"
    r"tỉnh\s+\w+|quận\s+\w+)",
    re.IGNORECASE | re.UNICODE,
)

_PRICE_PATTERN = re.compile(
    r"(\d[\d.,]*)\s*(đồng|VND|vnđ|triệu|nghìn|ngàn|k|USD|\$)",
    re.IGNORECASE,
)

_DATE_PATTERN = re.compile(
    r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"ngày\s+\d{1,2}\s*(?:tháng|/)\s*\d{1,2}|"
    r"tháng\s+\d{1,2}\s*(?:năm|/)\s*\d{2,4}|"
    r"\d{1,2}\s+(?:January|February|March|April|May|June|"
    r"July|August|September|October|November|December)\s+\d{4})",
    re.IGNORECASE | re.UNICODE,
)


class DocumentParser:
    """Parse documents: .txt, .csv, .json (đầy đủ); .pdf, .docx (stub)."""

    def __init__(self):
        self._lock = Lock()
        self._stats = {"calls": 0, "formats": {}}

    def parse(self, data: bytes, filename: str) -> dict:
        """Trích xuất text từ document dựa trên extension."""
        with self._lock:
            self._stats["calls"] += 1

        ext = Path(filename).suffix.lower() if filename else ""

        with self._lock:
            self._stats["formats"][ext] = self._stats["formats"].get(ext, 0) + 1

        if ext == ".txt" or ext == "":
            return self._parse_text(data, filename)
        elif ext == ".csv":
            return self._parse_csv(data, filename)
        elif ext == ".json":
            return self._parse_json(data, filename)
        elif ext == ".pdf":
            return {
                "status": "requires_library",
                "format": "pdf",
                "note": "PDF parsing requires PyPDF2 or pdfplumber",
                "file_size": len(data),
                "filename": filename,
            }
        elif ext in (".docx", ".doc"):
            return {
                "status": "requires_library",
                "format": ext.lstrip("."),
                "note": "DOCX parsing requires python-docx",
                "file_size": len(data),
                "filename": filename,
            }
        else:
            return {
                "status": "unsupported",
                "format": ext,
                "file_size": len(data),
                "filename": filename,
            }

    @staticmethod
    def _parse_text(data: bytes, filename: str) -> dict:
        """Parse plain text file."""
        # Try UTF-8 first, fall back to latin-1
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1", errors="replace")

        return {
            "status": "ok",
            "format": "txt",
            "text": text,
            "file_size": len(data),
            "filename": filename,
            "line_count": text.count("\n") + 1,
        }

    @staticmethod
    def _parse_csv(data: bytes, filename: str) -> dict:
        """Parse CSV file."""
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1", errors="replace")

        reader = csv.reader(io.StringIO(text))
        rows = []
        headers = None
        for i, row in enumerate(reader):
            if i == 0:
                headers = row
            rows.append(row)
            if i >= 10000:  # safety limit
                break

        # Combine all cells into text for further analysis
        all_text = "\n".join(", ".join(r) for r in rows)

        return {
            "status": "ok",
            "format": "csv",
            "text": all_text,
            "headers": headers,
            "row_count": len(rows),
            "column_count": len(headers) if headers else 0,
            "file_size": len(data),
            "filename": filename,
        }

    @staticmethod
    def _parse_json(data: bytes, filename: str) -> dict:
        """Parse JSON file."""
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1", errors="replace")

        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            return {
                "status": "error",
                "format": "json",
                "error": f"Invalid JSON: {exc}",
                "file_size": len(data),
                "filename": filename,
            }

        # Stringify for text extraction
        pretty = json.dumps(obj, ensure_ascii=False, indent=2)

        result: dict = {
            "status": "ok",
            "format": "json",
            "text": pretty,
            "file_size": len(data),
            "filename": filename,
        }

        if isinstance(obj, list):
            result["item_count"] = len(obj)
        elif isinstance(obj, dict):
            result["key_count"] = len(obj)
            result["keys"] = list(obj.keys())[:50]

        return result

    @staticmethod
    def extract_tourism_data(text: str) -> dict:
        """Trích xuất thông tin du lịch: địa danh, ngày, giá."""
        places = list({m.group() for m in _VN_PLACE_PATTERN.finditer(text)})

        prices = []
        for m in _PRICE_PATTERN.finditer(text):
            prices.append({
                "value": m.group(1),
                "unit": m.group(2),
                "raw": m.group(),
            })

        dates = list({m.group() for m in _DATE_PATTERN.finditer(text)})

        return {
            "places": sorted(places),
            "prices": prices[:20],
            "dates": sorted(dates),
            "has_tourism_content": len(places) > 0,
        }


# ══════════════════════════════════════════════════
#  8. MultimodalPipeline
# ══════════════════════════════════════════════════

# Extension → ContentType mapping
_EXT_MAP: dict[str, ContentType] = {
    ".txt": ContentType.DOCUMENT, ".csv": ContentType.DOCUMENT,
    ".json": ContentType.DOCUMENT, ".pdf": ContentType.DOCUMENT,
    ".doc": ContentType.DOCUMENT, ".docx": ContentType.DOCUMENT,
    ".jpg": ContentType.IMAGE, ".jpeg": ContentType.IMAGE,
    ".png": ContentType.IMAGE, ".gif": ContentType.IMAGE,
    ".webp": ContentType.IMAGE, ".bmp": ContentType.IMAGE,
    ".wav": ContentType.AUDIO, ".mp3": ContentType.AUDIO,
    ".ogg": ContentType.AUDIO, ".flac": ContentType.AUDIO,
    ".mp4": ContentType.VIDEO, ".avi": ContentType.VIDEO,
    ".mkv": ContentType.VIDEO, ".mov": ContentType.VIDEO,
    ".webm": ContentType.VIDEO,
}

# Magic bytes → ContentType
_MAGIC_MAP: list[tuple[bytes, ContentType]] = [
    (b"\xff\xd8\xff", ContentType.IMAGE),        # JPEG
    (b"\x89PNG\r\n\x1a\n", ContentType.IMAGE),   # PNG
    (b"GIF87a", ContentType.IMAGE),               # GIF
    (b"GIF89a", ContentType.IMAGE),               # GIF
    (b"BM", ContentType.IMAGE),                   # BMP
    (b"%PDF", ContentType.DOCUMENT),              # PDF
    (b"PK\x03\x04", ContentType.DOCUMENT),        # ZIP (DOCX)
]


class MultimodalPipeline:
    """Pipeline xử lý đa phương tiện: auto-detect, route, aggregate."""

    def __init__(self, text_analyzer: "TextAnalyzer",
                 image_analyzer: "ImageAnalyzer",
                 audio_processor: "AudioProcessor",
                 video_processor: "VideoProcessor",
                 document_parser: "DocumentParser"):
        self._text = text_analyzer
        self._image = image_analyzer
        self._audio = audio_processor
        self._video = video_processor
        self._doc = document_parser
        self._lock = Lock()
        self._stats = {"processed": 0, "by_type": {}}

    def _detect_content_type(self, data: bytes | None = None,
                             filename: str = "") -> ContentType:
        """Auto-detect content type từ magic bytes / extension."""
        # Try extension first
        if filename:
            ext = Path(filename).suffix.lower()
            if ext in _EXT_MAP:
                return _EXT_MAP[ext]

        # Try magic bytes
        if data:
            for magic, ct in _MAGIC_MAP:
                if data[:len(magic)] == magic:
                    return ct
            # RIFF check (WAV or WEBP)
            if data[:4] == b"RIFF" and len(data) > 12:
                if data[8:12] == b"WAVE":
                    return ContentType.AUDIO
                if data[8:12] == b"WEBP":
                    return ContentType.IMAGE

        return ContentType.UNKNOWN

    def process_single(self, data, content_type: str = "auto",
                       filename: str = "") -> MediaItem:
        """Xử lý một item đơn lẻ."""
        item_id = uuid.uuid4().hex[:12]

        # Determine data and type
        raw_data: bytes | None = None
        text_data: str | None = None

        if isinstance(data, str):
            text_data = data
            raw_data = data.encode("utf-8")
            if content_type == "auto":
                content_type = "text"
        elif isinstance(data, bytes):
            raw_data = data
        elif isinstance(data, Path):
            if data.exists():
                raw_data = data.read_bytes()
                filename = filename or data.name
            else:
                return MediaItem(
                    id=item_id,
                    content_type=ContentType.UNKNOWN,
                    source_path=str(data),
                    analysis={"error": f"File not found: {data}"},
                )

        # Resolve content type
        if content_type == "auto":
            ct = self._detect_content_type(raw_data, filename)
        else:
            try:
                ct = ContentType(content_type)
            except ValueError:
                ct = ContentType.UNKNOWN

        # Track stats
        with self._lock:
            self._stats["processed"] += 1
            ct_val = ct.value
            self._stats["by_type"][ct_val] = (
                self._stats["by_type"].get(ct_val, 0) + 1
            )

        # Route to appropriate analyzer
        extracted_text = text_data
        analysis = None

        if ct == ContentType.TEXT:
            if text_data is None and raw_data:
                try:
                    text_data = raw_data.decode("utf-8")
                except UnicodeDecodeError:
                    text_data = raw_data.decode("latin-1", errors="replace")
                extracted_text = text_data
            if text_data:
                analysis = self._text.analyze(text_data)

        elif ct == ContentType.IMAGE:
            if raw_data:
                analysis = self._image.analyze(raw_data, filename)

        elif ct == ContentType.AUDIO:
            if raw_data:
                analysis = self._audio.analyze_audio(raw_data)

        elif ct == ContentType.VIDEO:
            source = filename or str(item_id)
            analysis = self._video.analyze(source)

        elif ct == ContentType.DOCUMENT:
            if raw_data:
                doc_result = self._doc.parse(raw_data, filename)
                analysis = doc_result
                if doc_result.get("text"):
                    extracted_text = doc_result["text"]

        else:
            analysis = {"status": "unknown_type", "file_size": len(raw_data) if raw_data else 0}

        item = MediaItem(
            id=item_id,
            content_type=ct,
            source_path=filename or None,
            raw_data=raw_data,
            metadata={"filename": filename, "detected_type": ct.value},
            extracted_text=extracted_text,
            analysis=analysis,
        )

        # Persist result
        self._persist(item)

        return item

    def process(self, items: list[dict]) -> list[MediaItem]:
        """
        Xử lý nhiều items.

        Mỗi item dict chứa:
          - "data": str | bytes | Path  (required)
          - "content_type": str          (optional, default "auto")
          - "filename": str              (optional)
        """
        results = []
        for spec in items:
            data = spec.get("data")
            if data is None:
                # Try loading from path
                path = spec.get("path") or spec.get("source_path")
                if path:
                    data = Path(path)
                else:
                    continue

            ct = spec.get("content_type", "auto")
            fn = spec.get("filename", "")
            results.append(self.process_single(data, ct, fn))

        return results

    def _persist(self, item: MediaItem):
        """Lưu kết quả xử lý vào agent/data/multimodal/."""
        try:
            out_file = DATA_DIR / f"{item.id}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(item.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("Failed to persist MediaItem %s: %s", item.id, exc)


# ══════════════════════════════════════════════════
#  9. Module singletons & convenience functions
# ══════════════════════════════════════════════════

text_analyzer = TextAnalyzer()
image_analyzer = ImageAnalyzer()
audio_processor = AudioProcessor()
video_processor = VideoProcessor()
document_parser = DocumentParser()
multimodal_pipeline = MultimodalPipeline(
    text_analyzer, image_analyzer, audio_processor, video_processor, document_parser,
)


def analyze_text(text: str) -> dict:
    """Quick text analysis."""
    return text_analyzer.analyze(text)


def analyze_file(path: str) -> dict:
    """Analyze any file."""
    p = Path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Not a file: {path}"}

    item = multimodal_pipeline.process_single(p, content_type="auto", filename=p.name)
    return item.to_dict()


def get_capabilities() -> dict:
    """Trả về khả năng: gì đang hoạt động vs stub."""
    return {
        "text": {
            "status": "fully_functional",
            "features": [
                "language_detection", "keyword_extraction",
                "sentiment_analysis", "entity_mention_detection",
                "summary_statistics", "tourism_intent_classification",
            ],
        },
        "image": {
            "status": "basic",
            "features": [
                "format_detection", "dimensions_parsing",
                "jpeg_exif_gps", "file_metadata",
            ],
            "limitations": "No content recognition without vision LLM",
        },
        "audio": {
            "status": "stub",
            "features": ["wav_header_parsing"],
            "limitations": "Transcription requires Whisper or equivalent",
        },
        "video": {
            "status": "stub",
            "features": [],
            "limitations": "Requires ffmpeg for frame extraction and analysis",
        },
        "document": {
            "status": "partial",
            "supported_formats": ["txt", "csv", "json"],
            "stub_formats": ["pdf", "docx"],
            "features": ["text_extraction", "tourism_data_extraction"],
        },
    }


def get_multimodal_report() -> dict:
    """Thống kê xử lý multimodal."""
    return {
        "pipeline": multimodal_pipeline._stats,
        "text_analyzer": text_analyzer._stats,
        "image_analyzer": image_analyzer._stats,
        "audio_processor": audio_processor._stats,
        "video_processor": video_processor._stats,
        "document_parser": document_parser._stats,
        "data_dir": str(DATA_DIR),
        "capabilities": get_capabilities(),
    }

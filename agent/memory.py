"""
vinhlong360 — Dual-Layer Conversation Memory System.

Kiến trúc lấy cảm hứng từ Letta/MemGPT (2026):

  HOT MEMORY (Working Memory):
    - Tin nhắn gần nhất (sliding window)
    - Tóm tắt cuộc hội thoại (compressed context)
    - Preferences đã phát hiện trong phiên

  COLD MEMORY (Long-term):
    - User profile (sở thích, lịch sử, khu vực quan tâm)
    - Semantic memory (facts đã học về user)
    - Episodic memory (các cuộc hội thoại trước)
    - Skill documents (patterns thành công)

Mỗi user có 1 profile persistent qua sessions.
"""

import base64
import json
import hashlib
import logging
import os
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from threading import Lock, RLock

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet as _Fernet
    _HAS_FERNET = True
except ImportError:
    _Fernet = None
    _HAS_FERNET = False

MEMORY_DIR = Path(__file__).resolve().parent / "data" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# ── Encryption helpers for ColdMemory ────────────

_KEY_FILE = MEMORY_DIR / ".key"

_encryption_key: bytes | None = None


def _get_encryption_key() -> bytes:
    """
    Return the Fernet key (or base64 key) for encrypting profile data.
    Priority: MEMORY_ENCRYPTION_KEY env var > .key file > auto-generate.

    The result is cached after the first call to avoid repeated disk I/O.
    """
    global _encryption_key
    if _encryption_key is not None:
        return _encryption_key

    env_key = os.environ.get("MEMORY_ENCRYPTION_KEY")
    if env_key:
        # Fernet keys are url-safe base64 of 32 bytes — accept as-is
        _encryption_key = env_key.encode("utf-8")
        return _encryption_key

    if _KEY_FILE.exists():
        _encryption_key = _KEY_FILE.read_bytes().strip()
        return _encryption_key

    # Auto-generate
    if _HAS_FERNET:
        key = _Fernet.generate_key()
    else:
        # 32 random bytes, base64-encoded (used for obfuscation fallback)
        key = base64.urlsafe_b64encode(os.urandom(32))
    _KEY_FILE.write_bytes(key)
    _encryption_key = key
    return _encryption_key


def _encrypt(plaintext: str) -> str:
    """Encrypt a string. Returns Fernet token or base64-encoded data."""
    key = _get_encryption_key()
    data = plaintext.encode("utf-8")
    if _HAS_FERNET:
        f = _Fernet(key)
        return f.encrypt(data).decode("utf-8")
    else:
        # Base64 obfuscation fallback (XOR with repeated key then b64)
        key_bytes = base64.urlsafe_b64decode(key)
        xored = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))
        return base64.urlsafe_b64encode(xored).decode("utf-8")


def _decrypt(ciphertext: str) -> str:
    """Decrypt a string produced by _encrypt."""
    key = _get_encryption_key()
    if _HAS_FERNET:
        f = _Fernet(key)
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    else:
        key_bytes = base64.urlsafe_b64decode(key)
        xored = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
        data = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(xored))
        return data.decode("utf-8")

# ══════════════════════════════════════════════════
#  HOT MEMORY — Working Memory (per session)
# ══════════════════════════════════════════════════

class HotMemory:
    """
    Working memory cho 1 session.
    Giữ sliding window + compressed summary.
    """

    def __init__(self, session_id: str, max_messages: int = 20, max_summary_len: int = 500):
        self.session_id = session_id
        self.max_messages = max_messages
        self.max_summary_len = max_summary_len
        self.messages: list[dict] = []
        self.summary: str = ""
        self.detected_preferences: dict = {}
        self.entities_discussed: list[str] = []
        self.areas_mentioned: set = set()
        self.created_at = time.time()
        self.last_active = time.time()

    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "ts": time.time(),
        })
        self.last_active = time.time()

        # Extract signals
        if role == "user":
            self._extract_preferences(content)

        # Compress if too long
        if len(self.messages) > self.max_messages * 2:
            self._compress()

    def get_context_messages(self) -> list[dict]:
        """Trả về messages cho LLM context, kèm summary nếu có."""
        result = []
        if self.summary:
            result.append({
                "role": "system",
                "content": f"[Tóm tắt cuộc hội thoại trước đó]: {self.summary}"
            })
        # Return recent messages
        recent = self.messages[-self.max_messages:]
        result.extend([{"role": m["role"], "content": m["content"]} for m in recent])
        return result

    def get_preference_context(self) -> str:
        """Trả về user preferences đã phát hiện."""
        if not self.detected_preferences:
            return ""
        parts = []
        if self.detected_preferences.get("interests"):
            parts.append(f"Sở thích: {', '.join(self.detected_preferences['interests'])}")
        if self.detected_preferences.get("budget"):
            parts.append(f"Ngân sách: {self.detected_preferences['budget']}")
        if self.detected_preferences.get("group_type"):
            parts.append(f"Đi cùng: {self.detected_preferences['group_type']}")
        if self.areas_mentioned:
            parts.append(f"Khu vực quan tâm: {', '.join(self.areas_mentioned)}")
        return " | ".join(parts)

    def _extract_preferences(self, text: str):
        """Phát hiện preferences từ tin nhắn user."""
        text_lower = text.lower()

        # Interests
        interest_keywords = {
            "ẩm thực": ["ăn", "món", "đặc sản", "ẩm thực", "quán", "nhà hàng"],
            "lịch sử": ["lịch sử", "di tích", "bảo tàng", "nhân vật", "chiến tranh"],
            "thiên nhiên": ["thiên nhiên", "sông", "vườn", "cây", "chim", "sinh thái"],
            "văn hóa": ["chùa", "lễ hội", "văn hóa", "khmer", "truyền thống"],
            "mua sắm": ["mua", "đặc sản", "quà", "ocop", "sản phẩm"],
        }
        for interest, keywords in interest_keywords.items():
            if any(kw in text_lower for kw in keywords):
                self.detected_preferences.setdefault("interests", set()).add(interest)

        # Budget
        if any(w in text_lower for w in ["tiết kiệm", "rẻ", "bình dân", "giá rẻ"]):
            self.detected_preferences["budget"] = "thấp"
        elif any(w in text_lower for w in ["sang trọng", "cao cấp", "resort", "luxury"]):
            self.detected_preferences["budget"] = "cao"

        # Group type
        if any(w in text_lower for w in ["gia đình", "con nhỏ", "trẻ em"]):
            self.detected_preferences["group_type"] = "gia đình"
        elif any(w in text_lower for w in ["đôi", "couple", "lãng mạn"]):
            self.detected_preferences["group_type"] = "cặp đôi"
        elif any(w in text_lower for w in ["nhóm", "bạn bè", "group"]):
            self.detected_preferences["group_type"] = "nhóm bạn"

        # Areas
        if "vĩnh long" in text_lower or "vinh long" in text_lower:
            self.areas_mentioned.add("vinh-long")
        if "bến tre" in text_lower or "ben tre" in text_lower:
            self.areas_mentioned.add("ben-tre")
        if "trà vinh" in text_lower or "tra vinh" in text_lower:
            self.areas_mentioned.add("tra-vinh")

    def _compress(self):
        """Nén messages cũ thành summary."""
        old_messages = self.messages[:-self.max_messages]
        if not old_messages:
            return

        # Simple compression: giữ nội dung chính
        user_topics = []
        for m in old_messages:
            if m["role"] == "user":
                user_topics.append(m["content"][:100])

        new_summary = f"Người dùng đã hỏi về: {'; '.join(user_topics[-5:])}"
        if self.summary:
            new_summary = f"{self.summary} | {new_summary}"

        self.summary = new_summary[:self.max_summary_len]
        self.messages = self.messages[-self.max_messages:]


# ══════════════════════════════════════════════════
#  COLD MEMORY — Long-term Persistent Memory
# ══════════════════════════════════════════════════

class UserProfile:
    """Persistent user profile across sessions."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.interests: list[str] = []
        self.preferred_areas: list[str] = []
        self.budget_preference: str = ""
        self.group_type: str = ""
        self.visited_entities: list[dict] = []  # [{id, name, ts}]
        self.favorite_entities: list[str] = []
        self.disliked_entities: list[str] = []
        self.conversation_count: int = 0
        self.total_messages: int = 0
        self.first_seen: str = datetime.now().isoformat()
        self.last_seen: str = datetime.now().isoformat()
        self.feedback_history: list[dict] = []  # [{query, rating, ts}]
        self.semantic_facts: list[str] = []  # Extracted facts about user

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "interests": self.interests,
            "preferred_areas": self.preferred_areas,
            "budget_preference": self.budget_preference,
            "group_type": self.group_type,
            "visited_entities": self.visited_entities[-50:],
            "favorite_entities": self.favorite_entities[-20:],
            "disliked_entities": self.disliked_entities[-20:],
            "conversation_count": self.conversation_count,
            "total_messages": self.total_messages,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "feedback_history": self.feedback_history[-100:],
            "semantic_facts": self.semantic_facts[-30:],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        p = cls(data["user_id"])
        p.interests = data.get("interests", [])
        p.preferred_areas = data.get("preferred_areas", [])
        p.budget_preference = data.get("budget_preference", "")
        p.group_type = data.get("group_type", "")
        p.visited_entities = data.get("visited_entities", [])
        p.favorite_entities = data.get("favorite_entities", [])
        p.disliked_entities = data.get("disliked_entities", [])
        p.conversation_count = data.get("conversation_count", 0)
        p.total_messages = data.get("total_messages", 0)
        p.first_seen = data.get("first_seen", datetime.now().isoformat())
        p.last_seen = data.get("last_seen", datetime.now().isoformat())
        p.feedback_history = data.get("feedback_history", [])
        p.semantic_facts = data.get("semantic_facts", [])
        return p

    def get_personalization_prompt(self) -> str:
        """Tạo prompt bổ sung từ profile để personalize câu trả lời."""
        parts = []
        if self.interests:
            parts.append(f"Sở thích: {', '.join(self.interests)}")
        if self.preferred_areas:
            parts.append(f"Khu vực yêu thích: {', '.join(self.preferred_areas)}")
        if self.budget_preference:
            parts.append(f"Ngân sách: {self.budget_preference}")
        if self.group_type:
            parts.append(f"Loại nhóm: {self.group_type}")
        if self.visited_entities:
            recent = self.visited_entities[-5:]
            parts.append(f"Đã xem gần đây: {', '.join(v['name'] for v in recent)}")
        if self.favorite_entities:
            parts.append(f"Yêu thích: {', '.join(self.favorite_entities[-5:])}")
        if self.semantic_facts:
            parts.append(f"Ghi chú: {'; '.join(self.semantic_facts[-3:])}")

        if not parts:
            return ""
        return "[Hồ sơ người dùng]: " + " | ".join(parts)


class ColdMemory:
    """Persistent memory store — saves/loads user profiles to disk."""

    def __init__(self):
        self._profiles: dict[str, UserProfile] = {}
        self._lock = RLock()  # RLock to allow nested get_profile calls
        self._profiles_file = MEMORY_DIR / "user_profiles.json"
        self._load_all()

    def _load_all(self):
        """Load all profiles from disk (handles encrypted and plain JSON)."""
        try:
            if self._profiles_file.exists():
                raw = self._profiles_file.read_text(encoding="utf-8")
                # Backward-compatible: if file starts with '{', it's plain JSON
                if raw.strip().startswith("{"):
                    data = json.loads(raw)
                else:
                    data = json.loads(_decrypt(raw.strip()))
                for uid, pdata in data.items():
                    self._profiles[uid] = UserProfile.from_dict(pdata)
        except Exception as e:
            logger.warning("Failed to load profiles: %s", e)

    def _save_all(self):
        """Save all profiles to disk (encrypted)."""
        try:
            data = {uid: p.to_dict() for uid, p in self._profiles.items()}
            plaintext = json.dumps(data, ensure_ascii=False, indent=2)
            encrypted = _encrypt(plaintext)
            tmp = self._profiles_file.with_suffix(".tmp")
            tmp.write_text(encrypted, encoding="utf-8")
            tmp.replace(self._profiles_file)
        except Exception as e:
            logger.warning("Failed to save profiles: %s", e)

    def get_profile(self, user_id: str) -> UserProfile:
        with self._lock:
            if user_id not in self._profiles:
                self._profiles[user_id] = UserProfile(user_id)
            return self._profiles[user_id]

    def update_profile_from_session(self, user_id: str, hot: HotMemory):
        """Merge hot memory insights into persistent profile."""
        with self._lock:
            profile = self.get_profile(user_id)
            profile.last_seen = datetime.now().isoformat()
            profile.conversation_count += 1
            profile.total_messages += len(hot.messages)

            # Merge interests
            if hot.detected_preferences.get("interests"):
                for interest in hot.detected_preferences["interests"]:
                    if interest not in profile.interests:
                        profile.interests.append(interest)

            # Merge areas
            for area in hot.areas_mentioned:
                if area not in profile.preferred_areas:
                    profile.preferred_areas.append(area)

            # Budget & group
            if hot.detected_preferences.get("budget"):
                profile.budget_preference = hot.detected_preferences["budget"]
            if hot.detected_preferences.get("group_type"):
                profile.group_type = hot.detected_preferences["group_type"]

            # Merge visited entities
            for eid in hot.entities_discussed:
                if not any(v["id"] == eid for v in profile.visited_entities):
                    profile.visited_entities.append({
                        "id": eid,
                        "name": eid,
                        "ts": datetime.now().isoformat(),
                    })

            self._save_all()

    def record_feedback(self, user_id: str, query: str, rating: int, entity_id: str = None):
        """Ghi nhận feedback (1-5 stars hoặc thumbs up/down 1/0)."""
        with self._lock:
            profile = self.get_profile(user_id)
            profile.feedback_history.append({
                "query": query[:200],
                "rating": rating,
                "entity_id": entity_id,
                "ts": datetime.now().isoformat(),
            })

            # Update favorites/dislikes
            if entity_id:
                if rating >= 4:
                    if entity_id not in profile.favorite_entities:
                        profile.favorite_entities.append(entity_id)
                elif rating <= 2:
                    if entity_id not in profile.disliked_entities:
                        profile.disliked_entities.append(entity_id)

            self._save_all()

    def add_semantic_fact(self, user_id: str, fact: str):
        """Thêm fact đã học về user (ví dụ: 'Thích ăn chay', 'Sợ nước')."""
        with self._lock:
            profile = self.get_profile(user_id)
            if fact not in profile.semantic_facts:
                profile.semantic_facts.append(fact)
                self._save_all()

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_users": len(self._profiles),
                "total_conversations": sum(p.conversation_count for p in self._profiles.values()),
                "total_feedback": sum(len(p.feedback_history) for p in self._profiles.values()),
                "avg_messages_per_user": round(
                    sum(p.total_messages for p in self._profiles.values()) /
                    max(len(self._profiles), 1), 1
                ),
            }


# ══════════════════════════════════════════════════
#  SKILL DOCUMENTS — Agent self-improvement
# ══════════════════════════════════════════════════

class SkillDocumentStore:
    """
    Lưu trữ 'skill documents' — patterns thành công mà agent đã học.
    Ví dụ: khi agent trả lời tốt 1 loại câu hỏi, nó tạo skill doc để dùng lại.
    Tham khảo: nghiên cứu cho thấy skill docs giúp agent nhanh hơn 40%.
    """

    def __init__(self):
        self._skills_file = MEMORY_DIR / "skill_documents.json"
        self._skills: list[dict] = []
        self._lock = Lock()
        self._load()

    def _load(self):
        try:
            if self._skills_file.exists():
                self._skills = json.loads(self._skills_file.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load skill documents: %s", exc)
            self._skills = []

    def _save(self):
        try:
            tmp = self._skills_file.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(self._skills, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            tmp.replace(self._skills_file)
        except Exception as exc:
            logger.warning("Failed to save skill documents: %s", exc)

    def add_skill(self, query_pattern: str, tool_sequence: list[str],
                  success_strategy: str, category: str = "general"):
        """Thêm skill document khi agent giải quyết tốt 1 loại câu hỏi."""
        with self._lock:
            skill = {
                "pattern": query_pattern,
                "tools": tool_sequence,
                "strategy": success_strategy,
                "category": category,
                "created": datetime.now().isoformat(),
                "use_count": 0,
            }
            # Dedup
            existing = [s for s in self._skills if s["pattern"] == query_pattern]
            if not existing:
                self._skills.append(skill)
                self._save()

    def find_relevant_skills(self, query: str, limit: int = 3) -> list[dict]:
        """Tìm skill documents phù hợp với query."""
        import unicodedata
        import re

        def normalize(text):
            s = unicodedata.normalize("NFD", text.lower())
            s = re.sub(r"[̀-ͯ]", "", s)
            return s.replace("đ", "d")

        q_norm = normalize(query)
        scored = []
        for skill in self._skills:
            pattern_norm = normalize(skill["pattern"])
            # Simple keyword overlap
            q_words = set(q_norm.split())
            p_words = set(pattern_norm.split())
            overlap = len(q_words & p_words)
            if overlap > 0:
                scored.append((overlap, skill))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Mark usage
        results = [s for _, s in scored[:limit]]
        for s in results:
            s["use_count"] = s.get("use_count", 0) + 1
        if results:
            with self._lock:
                self._save()

        return results

    def get_skill_prompt(self, query: str) -> str:
        """Tạo prompt bổ sung từ relevant skills."""
        skills = self.find_relevant_skills(query)
        if not skills:
            return ""

        lines = ["[Kinh nghiệm trước đó]:"]
        for s in skills:
            lines.append(f"- Câu hỏi tương tự: '{s['pattern']}'")
            lines.append(f"  Chiến lược: {s['strategy']}")
            lines.append(f"  Tools: {' → '.join(s['tools'])}")
        return "\n".join(lines)

    def stats(self) -> dict:
        return {
            "total_skills": len(self._skills),
            "by_category": self._count_by("category"),
            "most_used": sorted(self._skills, key=lambda s: s.get("use_count", 0), reverse=True)[:5],
        }

    def _count_by(self, key: str) -> dict:
        counts = {}
        for s in self._skills:
            v = s.get(key, "unknown")
            counts[v] = counts.get(v, 0) + 1
        return counts


# ══════════════════════════════════════════════════
# ══════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════

def memory_health_check() -> dict:
    """Quick readiness probe for the memory subsystem."""
    dir_writable = os.access(str(MEMORY_DIR), os.W_OK) if MEMORY_DIR.exists() else False
    return {
        "status": "ok" if dir_writable else "degraded",
        "dir_writable": dir_writable,
        "encryption_available": _HAS_FERNET,
    }


#  MEMORY EXTRACTOR — Automatic fact extraction
# ══════════════════════════════════════════════════

class MemoryExtractor:
    """
    Pattern-based fact and preference extraction from conversations.
    Pure Python — no LLM calls — designed for speed.
    Thread-safe: all methods are stateless pure functions.
    """

    # ── Vietnamese pattern constants ──────────────────

    _FOOD_PATTERNS = re.compile(
        r"(?:thích\s+(?:ăn\s+)?|muốn\s+ăn\s+|ưa\s+chuộng\s+|"
        r"không\s+ăn\s+được\s+|ghét\s+ăn\s+|mê\s+)(.{2,40})",
        re.IGNORECASE,
    )

    _AREA_PATTERNS = re.compile(
        r"(?:muốn\s+đi\s+|quan\s+tâm\s+(?:đến\s+)?|thích\s+vùng\s+|"
        r"muốn\s+(?:tham\s+quan|khám\s+phá)\s+)"
        r"(.+?)(?:\s+với\s+|\s+cùng\s+|\s+vào\s+|\s+trong\s+|\s+để\s+|[.,!?]|$)",
        re.IGNORECASE,
    )

    _ACTIVITY_PATTERNS = re.compile(
        r"(?:thích\s+(?:chụp\s+ảnh|trải\s+nghiệm|tham\s+quan|câu\s+cá|"
        r"đi\s+thuyền|bơi|leo\s+núi|đạp\s+xe|đi\s+bộ|nấu\s+ăn|"
        r"ngắm\s+cảnh|mua\s+sắm|khám\s+phá)|"
        r"muốn\s+(?:tham\s+quan|trải\s+nghiệm|khám\s+phá)\s+)(.{0,40})",
        re.IGNORECASE,
    )

    _BUDGET_KEYWORDS: dict[str, list[str]] = {
        "tiết kiệm": ["tiết kiệm", "rẻ", "bình dân", "giá rẻ", "ít tiền"],
        "sang trọng": ["sang trọng", "cao cấp", "luxury", "resort", "5 sao"],
        "trung bình": ["vừa phải", "trung bình", "tầm trung", "hợp lý"],
    }

    _TRAVEL_STYLE_KEYWORDS: dict[str, list[str]] = {
        "gia đình": ["gia đình", "con nhỏ", "trẻ em", "ba mẹ", "bố mẹ", "cả nhà"],
        "một mình": ["một mình", "solo", "tự đi"],
        "nhóm bạn": ["nhóm bạn", "bạn bè", "group", "hội bạn"],
        "cặp đôi": ["cặp đôi", "couple", "lãng mạn", "hai đứa", "hai người"],
    }

    _KNOWN_AREAS = [
        "vĩnh long", "vinh long", "bến tre", "ben tre", "trà vinh", "tra vinh",
        "cần thơ", "can tho", "đồng tháp", "dong thap", "an giang",
        "sóc trăng", "soc trang", "hậu giang", "hau giang", "kiên giang",
        "kien giang", "bạc liêu", "bac lieu", "cà mau", "ca mau",
        "long an", "tiền giang", "tien giang", "long xuyên", "mỹ tho",
    ]

    # ── Fact-extraction relation patterns ────────────

    _FACT_PATTERNS: list[tuple[re.Pattern, str]] = [
        (re.compile(r"(.{2,30}?)\s+nằm\s+(?:ở|tại)\s+(.{2,40})", re.IGNORECASE), "located_in"),
        (re.compile(r"(.{2,30}?)\s+gần\s+(.{2,40})", re.IGNORECASE), "near"),
        (re.compile(r"(.{2,30}?)\s+nổi\s+tiếng\s+(?:với|về)\s+(.{2,40})", re.IGNORECASE), "famous_for"),
        (re.compile(r"(.{2,30}?)\s+thuộc\s+(.{2,40})", re.IGNORECASE), "belongs_to"),
        (re.compile(r"(.{2,30}?)\s+cách\s+(.{2,40})", re.IGNORECASE), "distance_to"),
        (re.compile(r"(.{2,30}?)\s+là\s+(.{2,60})", re.IGNORECASE), "is_a"),
    ]

    # ── Public API ───────────────────────────────────

    def extract_preferences(self, message: str, reply: str) -> list[dict]:
        """
        Detect user preferences from a conversation turn via pattern matching.

        Returns list of dicts with keys: type, value, confidence.
        Types: "food", "area", "activity", "budget", "travel_style".
        """
        results: list[dict] = []
        combined = f"{message} {reply}"
        combined_lower = combined.lower()

        # Food preferences (from user message only — those are the user's words)
        for m in self._FOOD_PATTERNS.finditer(message):
            value = m.group(1).strip().rstrip(".,!?")
            if len(value) >= 2:
                results.append({"type": "food", "value": value, "confidence": 0.8})

        # Area interests
        for m in self._AREA_PATTERNS.finditer(message):
            value = m.group(1).strip().rstrip(".,!?")
            if len(value) >= 2:
                results.append({"type": "area", "value": value, "confidence": 0.7})

        # Also detect known area names mentioned directly
        msg_lower = message.lower()
        for area in self._KNOWN_AREAS:
            if area in msg_lower:
                results.append({"type": "area", "value": area, "confidence": 0.6})

        # Activity preferences
        for m in self._ACTIVITY_PATTERNS.finditer(message):
            # The pattern captures the activity verb phrase itself in group(0)
            full_match = m.group(0).strip().rstrip(".,!?")
            trailing = m.group(1).strip().rstrip(".,!?") if m.group(1) else ""
            value = full_match if not trailing else full_match
            if len(value) >= 4:
                results.append({"type": "activity", "value": value, "confidence": 0.75})

        # Budget signals
        for budget_level, keywords in self._BUDGET_KEYWORDS.items():
            if any(kw in msg_lower for kw in keywords):
                results.append({"type": "budget", "value": budget_level, "confidence": 0.85})

        # Travel style
        for style, keywords in self._TRAVEL_STYLE_KEYWORDS.items():
            if any(kw in msg_lower for kw in keywords):
                results.append({"type": "travel_style", "value": style, "confidence": 0.85})

        # Deduplicate by (type, value)
        seen: set[tuple[str, str]] = set()
        deduped: list[dict] = []
        for pref in results:
            key = (pref["type"], pref["value"].lower())
            if key not in seen:
                seen.add(key)
                deduped.append(pref)

        return deduped

    def extract_entities_mentioned(
        self, message: str, reply: str, entities: dict
    ) -> list[str]:
        """
        Scan both message and reply for entity names/IDs from the knowledge base.

        Args:
            entities: dict mapping entity_id -> entity dict (must have 'name' key).

        Returns list of matched entity_ids.
        """
        if not entities:
            return []

        combined_lower = f"{message} {reply}".lower()
        found: list[str] = []

        for eid, entity in entities.items():
            name = entity.get("name", "")
            if not name:
                continue
            # Match by entity name (case-insensitive)
            if name.lower() in combined_lower:
                found.append(eid)
                continue
            # Match by entity ID mentioned literally
            if eid.lower() in combined_lower:
                found.append(eid)

        return found

    def extract_facts(self, message: str, reply: str) -> list[dict]:
        """
        Extract structured facts as (subject, relation, object) triples
        from both message and reply text.

        Returns list of dicts with keys: subject, relation, object.
        """
        results: list[dict] = []
        # Process both texts — the reply often contains factual statements
        for text in (message, reply):
            # Split into sentences for cleaner matching
            sentences = re.split(r"[.!?\n;]", text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 5:
                    continue
                for pattern, relation in self._FACT_PATTERNS:
                    for m in pattern.finditer(sentence):
                        subj = m.group(1).strip().rstrip(",")
                        obj = m.group(2).strip().rstrip(",.")
                        if len(subj) >= 2 and len(obj) >= 2:
                            results.append({
                                "subject": subj,
                                "relation": relation,
                                "object": obj,
                            })

        # Deduplicate
        seen: set[tuple[str, str, str]] = set()
        deduped: list[dict] = []
        for fact in results:
            key = (fact["subject"].lower(), fact["relation"], fact["object"].lower())
            if key not in seen:
                seen.add(key)
                deduped.append(fact)

        return deduped

    def on_conversation_turn(
        self,
        session_id: str,
        user_id: str,
        message: str,
        reply: str,
        entities_discussed: list[str],
        cold_memory: "ColdMemory",
    ) -> dict:
        """
        Master hook called after each chat turn.
        Extracts preferences, entities, and facts, then persists to cold memory.

        Returns a summary dict of what was extracted (useful for logging/debug).
        """
        # Lazy-import knowledge entities to avoid circular imports
        try:
            try:
                import knowledge as _knowledge
            except ImportError:
                from agent import knowledge as _knowledge
            _knowledge._ensure()
            knowledge_entities = _knowledge._entities or {}
        except Exception as e:
            logger.debug("Failed to load knowledge entities for memory extraction: %s", e)
            knowledge_entities = {}

        # 1. Extract preferences
        preferences = self.extract_preferences(message, reply)

        # 2. Extract entity mentions
        mentioned_entities = self.extract_entities_mentioned(
            message, reply, knowledge_entities
        )

        # 3. Extract facts
        facts = self.extract_facts(message, reply)

        # ── Persist to ColdMemory ────────────────────

        if user_id:
            with cold_memory._lock:
                profile = cold_memory.get_profile(user_id)

                # Update preferences
                for pref in preferences:
                    ptype = pref["type"]
                    value = pref["value"]

                    if ptype == "food":
                        fact_str = f"Ẩm thực: {value}"
                        if fact_str not in profile.semantic_facts:
                            profile.semantic_facts.append(fact_str)

                    elif ptype == "area":
                        normalized = value.lower().replace(" ", "-")
                        if normalized not in profile.preferred_areas:
                            profile.preferred_areas.append(normalized)

                    elif ptype == "activity":
                        fact_str = f"Hoạt động: {value}"
                        if fact_str not in profile.semantic_facts:
                            profile.semantic_facts.append(fact_str)

                    elif ptype == "budget":
                        profile.budget_preference = value

                    elif ptype == "travel_style":
                        profile.group_type = value

                # Track discussed entities
                all_entities = list(set(entities_discussed + mentioned_entities))
                for eid in all_entities:
                    entity_name = knowledge_entities.get(eid, {}).get("name", eid)
                    if not any(v["id"] == eid for v in profile.visited_entities):
                        profile.visited_entities.append({
                            "id": eid,
                            "name": entity_name,
                            "ts": datetime.now().isoformat(),
                        })

                # Store extracted facts as semantic facts
                for fact in facts:
                    fact_str = f"{fact['subject']} [{fact['relation']}] {fact['object']}"
                    if fact_str not in profile.semantic_facts:
                        profile.semantic_facts.append(fact_str)

                # Trim semantic_facts to keep only latest 50
                if len(profile.semantic_facts) > 50:
                    profile.semantic_facts = profile.semantic_facts[-50:]

                cold_memory._save_all()

        return {
            "preferences": preferences,
            "entities_mentioned": mentioned_entities,
            "facts": facts,
        }


# ══════════════════════════════════════════════════
#  MEMORY MANAGER — Unified interface
# ══════════════════════════════════════════════════

class MemoryManager:
    """
    Quản lý thống nhất cả Hot + Cold memory.
    Server gọi qua đây thay vì trực tiếp.
    """

    def __init__(self):
        self.cold = ColdMemory()
        self.skills = SkillDocumentStore()
        self.extractor = MemoryExtractor()
        self._sessions: dict[str, HotMemory] = {}
        self._lock = Lock()

    def get_session(self, session_id: str) -> HotMemory:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = HotMemory(session_id)
            return self._sessions[session_id]

    def build_context(self, session_id: str, user_id: str, message: str) -> str:
        """
        Xây dựng context bổ sung từ memory system.
        Được inject vào system prompt.
        """
        parts = []

        # 1. User profile (cold memory)
        if user_id:
            profile = self.cold.get_profile(user_id)
            profile_prompt = profile.get_personalization_prompt()
            if profile_prompt:
                parts.append(profile_prompt)

        # 2. Session preferences (hot memory)
        session = self.get_session(session_id)
        pref_ctx = session.get_preference_context()
        if pref_ctx:
            parts.append(f"[Phiên hiện tại]: {pref_ctx}")

        # 3. Relevant skills
        skill_prompt = self.skills.get_skill_prompt(message)
        if skill_prompt:
            parts.append(skill_prompt)

        return "\n".join(parts)

    def on_message(self, session_id: str, role: str, content: str):
        """Ghi nhận tin nhắn mới."""
        session = self.get_session(session_id)
        session.add_message(role, content)

    def on_entity_discussed(self, session_id: str, entity_id: str):
        """Ghi nhận entity được thảo luận."""
        session = self.get_session(session_id)
        if entity_id not in session.entities_discussed:
            session.entities_discussed.append(entity_id)

    def on_session_end(self, session_id: str, user_id: str):
        """Merge session insights vào cold memory."""
        if session_id in self._sessions:
            hot = self._sessions[session_id]
            if user_id:
                self.cold.update_profile_from_session(user_id, hot)

    def on_chat_complete(
        self,
        session_id: str,
        user_id: str,
        message: str,
        reply: str,
        entities: list[str] | None = None,
    ) -> dict:
        """
        Post-turn hook: run MemoryExtractor to extract and persist
        preferences, entity mentions, and facts from the conversation turn.

        Call this after both user message and assistant reply are available.
        Does NOT modify on_message() — this is a separate entry point.

        Returns the extraction summary dict from MemoryExtractor.
        """
        return self.extractor.on_conversation_turn(
            session_id=session_id,
            user_id=user_id,
            message=message,
            reply=reply,
            entities_discussed=entities or [],
            cold_memory=self.cold,
        )

    def on_good_answer(self, query: str, tools_used: list[str], strategy: str, category: str = "general"):
        """Agent learned a successful pattern → save as skill."""
        self.skills.add_skill(query, tools_used, strategy, category)

    def feedback(self, user_id: str, query: str, rating: int, entity_id: str = None):
        """User feedback on a response."""
        self.cold.record_feedback(user_id, query, rating, entity_id)

    def cleanup_stale_sessions(self, max_age_seconds: int = 3600):
        """Dọn sessions cũ."""
        now = time.time()
        with self._lock:
            stale = [
                sid for sid, s in self._sessions.items()
                if now - s.last_active > max_age_seconds
            ]
            for sid in stale:
                del self._sessions[sid]

    def stats(self) -> dict:
        return {
            "active_sessions": len(self._sessions),
            "cold_memory": self.cold.stats(),
            "skills": self.skills.stats(),
        }


# Singleton
memory_manager = MemoryManager()

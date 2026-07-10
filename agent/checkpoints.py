"""
vinhlong360 — Human-in-the-Loop & Conversation Checkpoint Module.

Hai thành phần chính:

  1. CHECKPOINT MANAGER
     Lưu/khôi phục trạng thái cuộc hội thoại:
     - Pause agent giữa chừng, resume đúng chỗ
     - Persistence dưới dạng JSON files
     - Auto-cleanup checkpoints cũ (> 24h)

  2. CONFIRMATION MANAGER
     Xác nhận người dùng trước khi thực hiện hành động:
     - Tạo lịch trình có ngân sách → xin xác nhận
     - Gợi ý "tất cả khu vực" → xin xác nhận
     - Hành động trả > 10 kết quả → xin cắt ngắn
     - Gợi ý phụ thuộc thời tiết → xác nhận dữ liệu thời tiết

Flow:
  Agent quyết định → tạo PendingConfirmation → hiển thị cho user
  → User xác nhận/từ chối → Agent tiếp tục hoặc điều chỉnh

Persistence: agent/data/checkpoints/  (một JSON file mỗi checkpoint)
"""

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

# ── Directories ──

CHECKPOINT_DIR = Path(__file__).resolve().parent / "data" / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

CONFIRMATION_DIR = CHECKPOINT_DIR / "confirmations"
CONFIRMATION_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════
#  1. CONVERSATION CHECKPOINT
# ══════════════════════════════════════════════════

@dataclass
class ConversationCheckpoint:
    """Snapshot of conversation state at a point in time."""

    checkpoint_id: str          # unique ID
    session_id: str             # conversation session
    timestamp: float            # when created (time.time())
    messages: list              # full message history at this point
    tools_used: list            # tools called so far
    agent_state: dict           # current agent state (round_num, pending_tools, etc.)
    metadata: dict = field(default_factory=dict)  # arbitrary metadata

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationCheckpoint":
        return cls(
            checkpoint_id=data["checkpoint_id"],
            session_id=data["session_id"],
            timestamp=data["timestamp"],
            messages=data["messages"],
            tools_used=data["tools_used"],
            agent_state=data["agent_state"],
            metadata=data.get("metadata", {}),
        )


class CheckpointManager:
    """
    Manages conversation checkpoints for pause/resume.

    Persistence: one JSON file per checkpoint under data/checkpoints/.
    Thread-safe via Lock. Atomic writes via .tmp + rename.
    """

    def __init__(self, directory: Path = CHECKPOINT_DIR):
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    # ── Internal helpers ──

    def _path(self, checkpoint_id: str) -> Path:
        """File path for a checkpoint."""
        # Sanitize ID to prevent path traversal
        safe_id = checkpoint_id.replace("/", "_").replace("\\", "_").replace("..", "_")
        return self._dir / f"{safe_id}.json"

    def _atomic_write(self, path: Path, data: dict) -> None:
        """Write JSON atomically: write to .tmp then rename."""
        tmp_path = path.with_suffix(".tmp")
        content = json.dumps(data, ensure_ascii=False, indent=2)
        tmp_path.write_text(content, encoding="utf-8")
        # os.replace is atomic on the same filesystem
        os.replace(str(tmp_path), str(path))

    # ── Public API ──

    def save_checkpoint(
        self,
        session_id: str,
        messages: list,
        tools_used: list,
        agent_state: dict,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Save current conversation state. Returns checkpoint_id.

        Args:
            session_id: conversation session identifier
            messages: full message history (list of dicts)
            tools_used: list of tool names called so far
            agent_state: dict with round_num, pending_tools, etc.
            metadata: arbitrary extra data (optional)

        Returns:
            checkpoint_id (str) that can be used to load/resume later.
        """
        checkpoint_id = f"cp_{uuid.uuid4().hex[:12]}"
        checkpoint = ConversationCheckpoint(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            timestamp=time.time(),
            messages=list(messages),       # defensive copy
            tools_used=list(tools_used),
            agent_state=dict(agent_state),
            metadata=metadata or {},
        )

        with self._lock:
            self._atomic_write(self._path(checkpoint_id), checkpoint.to_dict())

        return checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> Optional[ConversationCheckpoint]:
        """
        Load a specific checkpoint by ID.

        Returns:
            ConversationCheckpoint if found, None otherwise.
        """
        path = self._path(checkpoint_id)
        with self._lock:
            if not path.exists():
                return None
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return ConversationCheckpoint.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                return None

    def list_checkpoints(self, session_id: str) -> list[dict]:
        """
        List all checkpoints for a session (summary only, no full messages).

        Returns list of dicts with: checkpoint_id, session_id, timestamp,
        tools_count, message_count, metadata.
        """
        results = []
        with self._lock:
            for fp in self._dir.glob("cp_*.json"):
                try:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                    if data.get("session_id") != session_id:
                        continue
                    results.append({
                        "checkpoint_id": data["checkpoint_id"],
                        "session_id": data["session_id"],
                        "timestamp": data["timestamp"],
                        "tools_count": len(data.get("tools_used", [])),
                        "message_count": len(data.get("messages", [])),
                        "metadata": data.get("metadata", {}),
                    })
                except (json.JSONDecodeError, KeyError):
                    continue

        # Sort by timestamp descending (newest first)
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results

    def resume_from(self, checkpoint_id: str) -> Optional[tuple[list, dict]]:
        """
        Resume conversation from a checkpoint.

        Returns:
            (messages, agent_state) tuple if found, None if checkpoint not found.
        """
        cp = self.load_checkpoint(checkpoint_id)
        if cp is None:
            return None
        return (cp.messages, cp.agent_state)

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a checkpoint by ID.

        Returns True if deleted, False if not found.
        """
        path = self._path(checkpoint_id)
        with self._lock:
            if path.exists():
                path.unlink()
                return True
        return False

    def cleanup_old(self, max_age_hours: float = 24) -> int:
        """
        Remove checkpoints older than max_age_hours.

        Returns the number of checkpoints removed.
        """
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        with self._lock:
            for fp in list(self._dir.glob("cp_*.json")):
                try:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                    if data.get("timestamp", 0) < cutoff:
                        fp.unlink()
                        removed += 1
                except (json.JSONDecodeError, KeyError, OSError):
                    continue
        return removed


# ══════════════════════════════════════════════════
#  2. CONFIRMATION MANAGER
# ══════════════════════════════════════════════════

CONFIRMATION_EXPIRY_SECONDS = 300  # 5 minutes


@dataclass
class PendingConfirmation:
    """A pending action awaiting user confirmation."""

    confirmation_id: str
    session_id: str
    action_type: str            # "itinerary", "recommendation", "booking_info"
    description: str            # human-readable description
    params: dict                # parameters that would be used
    created_at: float
    status: str = "pending"     # "pending", "confirmed", "rejected", "expired"
    expires_at: float = 0.0     # auto-expire timestamp
    reject_reason: str = ""

    def __post_init__(self):
        if self.expires_at == 0.0:
            self.expires_at = self.created_at + CONFIRMATION_EXPIRY_SECONDS

    @property
    def is_expired(self) -> bool:
        return self.status == "pending" and time.time() > self.expires_at

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_expired"] = self.is_expired
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PendingConfirmation":
        # Drop computed fields
        data.pop("is_expired", None)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ConfirmationManager:
    """
    Manages pending confirmations for human-in-the-loop actions.

    Flow:
      1. Agent reaches a decision point (e.g., generate itinerary)
      2. Creates a PendingConfirmation with the proposed action
      3. Returns a confirmation prompt to the user
      4. User confirms/rejects
      5. Agent proceeds or revises

    Persistence: JSON files under data/checkpoints/confirmations/.
    Thread-safe via Lock. Auto-expires after 5 minutes.
    """

    def __init__(self, directory: Path = CONFIRMATION_DIR):
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    # ── Internal helpers ──

    def _path(self, confirmation_id: str) -> Path:
        safe_id = confirmation_id.replace("/", "_").replace("\\", "_").replace("..", "_")
        return self._dir / f"{safe_id}.json"

    def _atomic_write(self, path: Path, data: dict) -> None:
        tmp_path = path.with_suffix(".tmp")
        content = json.dumps(data, ensure_ascii=False, indent=2)
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(str(tmp_path), str(path))

    def _load(self, confirmation_id: str) -> Optional[PendingConfirmation]:
        path = self._path(confirmation_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return PendingConfirmation.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def _save(self, confirmation: PendingConfirmation) -> None:
        self._atomic_write(self._path(confirmation.confirmation_id), confirmation.to_dict())

    # ── Public API ──

    def create_confirmation(
        self,
        session_id: str,
        action_type: str,
        description: str,
        params: dict,
    ) -> PendingConfirmation:
        """
        Create a new pending confirmation.

        Args:
            session_id: conversation session identifier
            action_type: "itinerary", "recommendation", "booking_info", etc.
            description: human-readable description of what will happen
            params: the parameters that would be used if confirmed

        Returns:
            PendingConfirmation object (status="pending")
        """
        confirmation_id = f"cf_{uuid.uuid4().hex[:12]}"
        now = time.time()
        confirmation = PendingConfirmation(
            confirmation_id=confirmation_id,
            session_id=session_id,
            action_type=action_type,
            description=description,
            params=dict(params),
            created_at=now,
            status="pending",
            expires_at=now + CONFIRMATION_EXPIRY_SECONDS,
        )

        with self._lock:
            self._save(confirmation)

        return confirmation

    def confirm(self, confirmation_id: str) -> Optional[dict]:
        """
        User confirms the action.

        Returns the params to proceed with, or None if not found/expired.
        """
        with self._lock:
            confirmation = self._load(confirmation_id)
            if confirmation is None:
                return None

            # Check expiry
            if confirmation.is_expired:
                confirmation.status = "expired"
                self._save(confirmation)
                return None

            if confirmation.status != "pending":
                # Already processed
                return None

            confirmation.status = "confirmed"
            self._save(confirmation)
            return dict(confirmation.params)

    def reject(self, confirmation_id: str, reason: str = "") -> bool:
        """
        User rejects the action.

        Returns True if successfully rejected, False if not found or already processed.
        """
        with self._lock:
            confirmation = self._load(confirmation_id)
            if confirmation is None:
                return False

            if confirmation.status != "pending":
                return False

            confirmation.status = "rejected"
            confirmation.reject_reason = reason
            self._save(confirmation)
            return True

    def get_pending(self, session_id: str) -> list[PendingConfirmation]:
        """
        Get all pending (non-expired) confirmations for a session.

        Automatically marks expired ones along the way.
        """
        results = []
        with self._lock:
            for fp in self._dir.glob("cf_*.json"):
                try:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                    if data.get("session_id") != session_id:
                        continue
                    confirmation = PendingConfirmation.from_dict(data)

                    # Auto-expire
                    if confirmation.is_expired:
                        confirmation.status = "expired"
                        self._save(confirmation)
                        continue

                    if confirmation.status == "pending":
                        results.append(confirmation)
                except (json.JSONDecodeError, KeyError):
                    continue

        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    def is_confirmed(self, confirmation_id: str) -> bool:
        """Check if a specific confirmation was approved."""
        with self._lock:
            confirmation = self._load(confirmation_id)
            if confirmation is None:
                return False
            return confirmation.status == "confirmed"

    def cleanup_expired(self) -> int:
        """
        Remove expired and old (> 1 hour) processed confirmations.

        Returns the number of confirmations removed.
        """
        cutoff = time.time() - 3600  # 1 hour for processed confirmations
        removed = 0
        with self._lock:
            for fp in list(self._dir.glob("cf_*.json")):
                try:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                    confirmation = PendingConfirmation.from_dict(data)
                    should_remove = False

                    if confirmation.is_expired:
                        should_remove = True
                    elif confirmation.status in ("confirmed", "rejected"):
                        if confirmation.created_at < cutoff:
                            should_remove = True

                    if should_remove:
                        fp.unlink()
                        removed += 1
                except (json.JSONDecodeError, KeyError, OSError):
                    continue
        return removed


# ══════════════════════════════════════════════════
#  3. HELPER FUNCTIONS (for server.py integration)
# ══════════════════════════════════════════════════

# Action types that require confirmation
_CONFIRMATION_RULES = {
    "itinerary": {
        "description": "Tạo lịch trình du lịch",
        "check": lambda params: params.get("budget") is not None and params.get("budget") != "",
    },
    "recommendation": {
        "description": "Gợi ý điểm đến",
        "check": lambda params: (
            # "all" areas means broad scope
            "all" in str(params.get("areas", "")).lower()
            or params.get("area", "").lower() in ("all", "tat_ca", "tất cả")
        ),
    },
    "search_results": {
        "description": "Kết quả tìm kiếm",
        "check": lambda params: params.get("result_count", 0) > 10,
    },
    "weather_dependent": {
        "description": "Gợi ý phụ thuộc thời tiết",
        "check": lambda params: params.get("weather_dependent", False),
    },
}


def needs_confirmation(action_type: str, params: dict) -> bool:
    """
    Check if an action requires human confirmation.

    Rules:
    - Itinerary generation with budget specified: YES
    - Recommendations involving "all" areas: YES
    - Any action with > 10 results: YES (truncation confirmation)
    - Weather-dependent recommendations: YES (confirm weather data is current)

    Args:
        action_type: "itinerary", "recommendation", "search_results", "weather_dependent"
        params: action parameters to evaluate

    Returns:
        True if confirmation is needed.
    """
    rule = _CONFIRMATION_RULES.get(action_type)
    if rule is None:
        return False
    try:
        return rule["check"](params)
    except Exception as exc:
        logger.warning("Confirmation rule %s check failed: %s", action_type, exc)
        return False


def _prompt_lines_itinerary(confirmation: PendingConfirmation) -> list:
    """Build itinerary confirmation lines (verbatim from format_confirmation_prompt)."""
    lines = []
    params = confirmation.params
    days = params.get("days", 1)
    areas = params.get("areas", [])
    budget = params.get("budget", "trung_binh")
    interests = params.get("interests", [])

    budget_map = {
        "thap": "Thấp",
        "trung_binh": "Trung bình",
        "cao": "Cao",
    }
    interest_map = {
        "am_thuc": "Ẩm thực",
        "lich_su": "Lịch sử",
        "thien_nhien": "Thiên nhiên",
        "van_hoa": "Văn hóa",
        "mua_sam": "Mua sắm",
        "tham_quan": "Tham quan",
        "tong_hop": "Tổng hợp",
    }
    area_map = {
        "vinh-long": "Vĩnh Long",
        "ben-tre": "Bến Tre",
        "tra-vinh": "Trà Vinh",
    }

    duration = f"{days} ngày" + (f" {days - 1} đêm" if days > 1 else "")
    area_names = ", ".join(area_map.get(a, a) for a in areas) if areas else "Tất cả khu vực"
    interest_names = ", ".join(interest_map.get(i, i) for i in interests) if interests else "Tổng hợp"
    budget_name = budget_map.get(budget, budget)

    lines.append("Xac nhan lich trinh:")
    lines.append(f"  - {duration}, khu vuc {area_names}")
    lines.append(f"  - Ngan sach: {budget_name}")
    lines.append(f"  - So thich: {interest_names}")
    if params.get("month"):
        lines.append(f"  - Thang di: {params['month']}")
    lines.append("")
    lines.append("Ban muon toi tao lich trinh nay? (Xac nhan / Thay doi)")
    return lines


def _prompt_lines_recommendation(confirmation: PendingConfirmation) -> list:
    """Build recommendation confirmation lines (verbatim from format_confirmation_prompt)."""
    lines = []
    params = confirmation.params
    areas = params.get("areas", params.get("area", ""))
    count = params.get("limit", params.get("result_count", ""))

    lines.append("Xac nhan goi y:")
    lines.append(f"  - {confirmation.description}")
    if areas:
        lines.append(f"  - Khu vuc: {areas}")
    if count:
        lines.append(f"  - So luong: {count} ket qua")
    lines.append("")
    lines.append("Ban muon xem goi y nay? (Xac nhan / Thay doi)")
    return lines


def _prompt_lines_search_results(confirmation: PendingConfirmation) -> list:
    """Build search_results confirmation lines (verbatim from format_confirmation_prompt)."""
    lines = []
    count = confirmation.params.get("result_count", 0)
    lines.append("Xac nhan ket qua tim kiem:")
    lines.append(f"  - Tim thay {count} ket qua")
    lines.append(f"  - {confirmation.description}")
    lines.append("")
    lines.append("Ban muon xem tat ca hay chi 10 ket qua dau? (Tat ca / 10 dau)")
    return lines


def _prompt_lines_weather_dependent(confirmation: PendingConfirmation) -> list:
    """Build weather_dependent confirmation lines (verbatim from format_confirmation_prompt)."""
    lines = []
    lines.append("Xac nhan goi y theo thoi tiet:")
    lines.append(f"  - {confirmation.description}")
    lines.append("  - Du lieu thoi tiet co the khong chinh xac 100%")
    lines.append("")
    lines.append("Ban muon tiep tuc voi goi y nay? (Xac nhan / Bo qua)")
    return lines


def _prompt_lines_generic(confirmation: PendingConfirmation) -> list:
    """Build generic fallback confirmation lines (verbatim from format_confirmation_prompt)."""
    lines = []
    lines.append(f"Xac nhan hanh dong: {confirmation.action_type}")
    lines.append(f"  - {confirmation.description}")
    lines.append("")
    lines.append("Ban muon tiep tuc? (Xac nhan / Huy)")
    return lines


def format_confirmation_prompt(confirmation: PendingConfirmation) -> str:
    """
    Format a PendingConfirmation into a user-facing Vietnamese message.

    Returns a string suitable for displaying in the chat UI.
    """
    if confirmation.action_type == "itinerary":
        lines = _prompt_lines_itinerary(confirmation)
    elif confirmation.action_type == "recommendation":
        lines = _prompt_lines_recommendation(confirmation)
    elif confirmation.action_type == "search_results":
        lines = _prompt_lines_search_results(confirmation)
    elif confirmation.action_type == "weather_dependent":
        lines = _prompt_lines_weather_dependent(confirmation)
    else:
        lines = _prompt_lines_generic(confirmation)

    return "\n".join(lines)


# ══════════════════════════════════════════════════
#  4. MODULE SINGLETONS
# ══════════════════════════════════════════════════

checkpoint_manager = CheckpointManager()
confirmation_manager = ConfirmationManager()


# ══════════════════════════════════════════════════
#  CLI TEST
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    print("=" * 60)
    print("  vinhlong360 — Checkpoint & Confirmation Module Test")
    print("=" * 60)

    # ── Test CheckpointManager ──
    print("\n--- CheckpointManager ---")

    cm = CheckpointManager()
    test_session = f"test_{uuid.uuid4().hex[:8]}"

    # Save checkpoint
    messages = [
        {"role": "user", "content": "Cho toi lich trinh 2 ngay Vinh Long"},
        {"role": "assistant", "content": "Toi se tao lich trinh cho ban..."},
    ]
    tools = ["search", "generate_itinerary"]
    state = {"round_num": 2, "pending_tools": [], "status": "active"}

    cp_id = cm.save_checkpoint(
        session_id=test_session,
        messages=messages,
        tools_used=tools,
        agent_state=state,
        metadata={"query_type": "itinerary"},
    )
    print(f"  [OK] Saved checkpoint: {cp_id}")

    # Load checkpoint
    loaded = cm.load_checkpoint(cp_id)
    assert loaded is not None, "Failed to load checkpoint"
    assert loaded.session_id == test_session
    assert len(loaded.messages) == 2
    assert loaded.tools_used == tools
    assert loaded.agent_state["round_num"] == 2
    print(f"  [OK] Loaded checkpoint: {loaded.checkpoint_id}")
    print(f"       Messages: {len(loaded.messages)}, Tools: {loaded.tools_used}")

    # Save a second checkpoint
    messages.append({"role": "user", "content": "Them mon an dia phuong"})
    tools.append("search")
    state["round_num"] = 3
    cp_id_2 = cm.save_checkpoint(
        session_id=test_session,
        messages=messages,
        tools_used=tools,
        agent_state=state,
    )
    print(f"  [OK] Saved checkpoint 2: {cp_id_2}")

    # List checkpoints
    listing = cm.list_checkpoints(test_session)
    assert len(listing) >= 2, f"Expected >=2 checkpoints, got {len(listing)}"
    print(f"  [OK] Listed {len(listing)} checkpoints for session {test_session}")
    for item in listing:
        print(f"       - {item['checkpoint_id']}: {item['message_count']} msgs, {item['tools_count']} tools")

    # Resume from checkpoint 1 (should have 2 messages)
    result = cm.resume_from(cp_id)
    assert result is not None
    msgs, st = result
    assert len(msgs) == 2, f"Expected 2 messages from cp1, got {len(msgs)}"
    assert st["round_num"] == 2
    print(f"  [OK] Resume from {cp_id}: {len(msgs)} messages, round {st['round_num']}")

    # Delete checkpoint
    assert cm.delete_checkpoint(cp_id) is True
    assert cm.load_checkpoint(cp_id) is None
    print(f"  [OK] Deleted checkpoint {cp_id}")

    # Cleanup
    cm.delete_checkpoint(cp_id_2)

    # ── Test ConfirmationManager ──
    print("\n--- ConfirmationManager ---")

    cfm = ConfirmationManager()

    # Create confirmation — itinerary
    cf = cfm.create_confirmation(
        session_id=test_session,
        action_type="itinerary",
        description="Tao lich trinh 2 ngay 1 dem tai Vinh Long",
        params={
            "days": 2,
            "areas": ["vinh-long"],
            "budget": "trung_binh",
            "interests": ["am_thuc", "thien_nhien"],
        },
    )
    print(f"  [OK] Created confirmation: {cf.confirmation_id} (status={cf.status})")

    # Check pending
    pending = cfm.get_pending(test_session)
    assert len(pending) >= 1
    print(f"  [OK] Pending confirmations: {len(pending)}")

    # Format prompt
    prompt = format_confirmation_prompt(cf)
    print("  [OK] Confirmation prompt:")
    for line in prompt.split("\n"):
        print(f"       {line}")

    # Confirm it
    params = cfm.confirm(cf.confirmation_id)
    assert params is not None
    assert params["days"] == 2
    assert cfm.is_confirmed(cf.confirmation_id) is True
    print(f"  [OK] Confirmed: params={params}")

    # Cannot confirm again
    assert cfm.confirm(cf.confirmation_id) is None
    print("  [OK] Double-confirm correctly rejected")

    # Create another and reject it
    cf2 = cfm.create_confirmation(
        session_id=test_session,
        action_type="recommendation",
        description="Goi y diem den tat ca khu vuc",
        params={"areas": "all", "limit": 20},
    )
    assert cfm.reject(cf2.confirmation_id, reason="Qua nhieu") is True
    assert cfm.is_confirmed(cf2.confirmation_id) is False
    print(f"  [OK] Rejected: {cf2.confirmation_id} (reason: 'Qua nhieu')")

    # ── Test needs_confirmation ──
    print("\n--- needs_confirmation ---")

    assert needs_confirmation("itinerary", {"budget": "cao"}) is True
    assert needs_confirmation("itinerary", {}) is False
    assert needs_confirmation("recommendation", {"areas": "all"}) is True
    assert needs_confirmation("recommendation", {"areas": "vinh-long"}) is False
    assert needs_confirmation("search_results", {"result_count": 15}) is True
    assert needs_confirmation("search_results", {"result_count": 5}) is False
    assert needs_confirmation("weather_dependent", {"weather_dependent": True}) is True
    assert needs_confirmation("unknown_action", {}) is False
    print("  [OK] All needs_confirmation rules passed")

    # ── Test format_confirmation_prompt for all types ──
    print("\n--- format_confirmation_prompt ---")

    for action_type, params in [
        ("itinerary", {"days": 3, "areas": ["vinh-long", "ben-tre"], "budget": "cao", "interests": ["am_thuc"], "month": 12}),
        ("recommendation", {"areas": "tat_ca", "limit": 20, "description": "Top diem den mua he"}),
        ("search_results", {"result_count": 25, "description": "Tim kiem 'chua' trong tat ca khu vuc"}),
        ("weather_dependent", {"weather_dependent": True, "description": "Goi y tham quan ngoai troi hom nay"}),
        ("custom_type", {"foo": "bar", "description": "Something custom"}),
    ]:
        cf_test = cfm.create_confirmation(
            session_id=test_session,
            action_type=action_type,
            description=params.pop("description", f"Test {action_type}"),
            params=params,
        )
        prompt = format_confirmation_prompt(cf_test)
        print(f"  [{action_type}]")
        for line in prompt.split("\n"):
            print(f"    {line}")
        # Cleanup
        cfm.reject(cf_test.confirmation_id)

    # ── Cleanup test confirmations ──
    cfm.cleanup_expired()

    # Final cleanup of test files
    for fp in list(CONFIRMATION_DIR.glob("cf_*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            if data.get("session_id") == test_session:
                fp.unlink()
        except Exception as e:
            logging.debug("Cleanup confirmation file failed: %s", e)
    for fp in list(CHECKPOINT_DIR.glob("cp_*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            if data.get("session_id") == test_session:
                fp.unlink()
        except Exception as e:
            logging.debug("Cleanup checkpoint file failed: %s", e)

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED")
    print("=" * 60)

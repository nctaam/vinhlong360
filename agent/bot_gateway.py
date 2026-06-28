"""
vinhlong360 — Multi-Channel Bot Gateway.

Connects the Knowledge Agent to Telegram and Zalo OA.
All platforms share a single agent engine for consistent answers.

Architecture:
  User (Telegram/Zalo) -> BotGateway -> POST /chat -> Agent -> User

Endpoints (FastAPI app on port 8361):
  GET  /             — gateway status
  POST /webhook/zalo — Zalo OA webhook receiver
  GET  /stats        — session statistics

Telegram uses polling via python-telegram-bot (no webhook needed).

Run:
  python agent/bot_gateway.py

Config (.env):
  TELEGRAM_BOT_TOKEN   — from @BotFather
  ZALO_OA_ID           — Zalo OA application ID
  ZALO_OA_SECRET       — Zalo OA secret key
  AGENT_URL            — agent server (default http://localhost:8360)
"""

import hashlib
import hmac
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Structured logging ──

_bot_logger = logging.getLogger("bot_gateway")
if not _bot_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _bot_logger.addHandler(_handler)
    _bot_logger.setLevel(getattr(logging, os.environ.get("LOG_LEVEL", "INFO")))

# ── Optional dependencies ──

try:
    from telegram import (
        Update,
        InlineKeyboardButton,
        InlineKeyboardMarkup,
    )
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters,
    )
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    logging.getLogger("bot_gateway").warning(
          "python-telegram-bot not installed — Telegram bot disabled. "
          "Install with: pip install python-telegram-bot")

# ── Config ──

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8360")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ZALO_OA_ID = os.environ.get("ZALO_OA_ACCESS_TOKEN", os.environ.get("ZALO_OA_ID", ""))
ZALO_OA_SECRET = os.environ.get("ZALO_OA_SECRET", "")

MAP_URL = os.environ.get("MAP_URL", "https://vinhlong360.vn/map")

# Quản trị qua Telegram: chỉ chat ID trong ADMIN_TELEGRAM_IDS (CSV) mới gọi được lệnh admin.
# Bot gọi /admin/* trên agent bằng X-Admin-Key (server-side). KHÔNG bật vòng lặp LLM nền (§B8).
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
ADMIN_TELEGRAM_IDS = {x.strip() for x in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(",") if x.strip()}


async def _async_sleep(seconds: float):
    """Async sleep helper for retry delays."""
    import asyncio
    await asyncio.sleep(seconds)


# ======================================================================
#  Markdown Converter
# ======================================================================

def convert_markdown(text: str, platform: str) -> str:
    """Convert agent markdown to platform-specific formatting.

    The agent returns standard markdown (##, **, *, `code`, lists).
    Each platform has different formatting support:
      - telegram: MarkdownV2 (bold, italic, code, underline)
      - zalo: plain text only (strip all formatting)

    Args:
        text: Markdown text from agent.
        platform: Target platform ("telegram" or "zalo").

    Returns:
        Formatted text for the target platform.
    """
    if platform == "telegram":
        return _md_to_telegram(text)
    elif platform == "zalo":
        return _md_to_zalo(text)
    return text


def _md_to_telegram(text: str) -> str:
    """Convert markdown to Telegram-friendly format.

    Telegram supports a subset of markdown:
      - *bold* (we convert ** to *)
      - _italic_ (we convert * to _)
      - `code`
      - Headers become bold lines with a marker
    """
    # Headers -> bold with marker
    text = re.sub(r"^###\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)
    text = re.sub(r"^#\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # Bold: **text** -> *text* (Telegram bold)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

    # Italic: single *text* that is NOT already bold
    # After the above conversion, remaining single * pairs are italic
    # Telegram uses _text_ for italic, but mixing with * is tricky.
    # Leave single-star italic as-is since Telegram parse_mode=Markdown
    # treats *text* as bold.  Use _text_ for italic markers only if
    # the source explicitly had single-star italic (not bold).
    # For simplicity, we leave the text as-is after bold conversion
    # since most agent output uses ** for emphasis.

    # Code blocks remain unchanged (`code`)

    # Bullet lists: keep as-is, Telegram renders them fine
    return text.strip()


def _md_to_zalo(text: str) -> str:
    """Convert markdown to Zalo-compatible plain text.

    Zalo supports basic text only, so we strip all markdown formatting
    and convert structural elements to Unicode equivalents.
    """
    # Headers -> plain text with marker
    text = re.sub(r"^###\s+(.+)$", r"--- \1 ---", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+(.+)$", r"--- \1 ---", text, flags=re.MULTILINE)
    text = re.sub(r"^#\s+(.+)$", r"--- \1 ---", text, flags=re.MULTILINE)

    # Bold: strip markers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)

    # Italic: strip markers
    text = re.sub(r"\*(.+?)\*", r"\1", text)

    # Code: strip backticks
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Bullet lists: convert to simple dash
    text = re.sub(r"^\*\s+", "- ", text, flags=re.MULTILINE)

    return text.strip()


# ======================================================================
#  Rate Limiter (per-user, per-platform)
# ======================================================================

class UserRateLimiter:
    """Sliding-window rate limiter keyed by user identifier.

    Default: 10 messages per 60 seconds per user.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, user_key: str) -> bool:
        """Check if the user can send another message.

        Args:
            user_key: Unique user identifier (e.g. "telegram:12345").

        Returns:
            True if within limit, False if rate-limited.
        """
        now = time.time()
        cutoff = now - self.window
        self._requests[user_key] = [
            t for t in self._requests[user_key] if t > cutoff
        ]
        if len(self._requests[user_key]) >= self.max_requests:
            return False
        self._requests[user_key].append(now)
        return True

    def remaining(self, user_key: str) -> int:
        """Return how many requests the user has left in the current window."""
        now = time.time()
        cutoff = now - self.window
        recent = [t for t in self._requests.get(user_key, []) if t > cutoff]
        return max(0, self.max_requests - len(recent))

    def retry_after(self, user_key: str) -> int:
        """Seconds until the user can send again. 0 if not limited."""
        now = time.time()
        cutoff = now - self.window
        recent = [t for t in self._requests.get(user_key, []) if t > cutoff]
        if len(recent) < self.max_requests:
            return 0
        oldest = min(recent)
        return max(1, int(oldest + self.window - now) + 1)


# ======================================================================
#  Session Tracker
# ======================================================================

_sessions: dict[str, dict] = {}
_sessions_lock = Lock()
MAX_HISTORY = 20
MAX_SESSIONS = int(os.environ.get("BOT_MAX_SESSIONS", "5000"))
SESSION_TTL = 24 * 3600  # 24 hours


def _session_key(platform: str, user_id: str) -> str:
    return f"{platform}:{user_id}"


def _get_history(platform: str, user_id: str) -> list[dict]:
    key = _session_key(platform, user_id)
    with _sessions_lock:
        session = _sessions.get(key)
        if not session:
            return []
        session["last_active"] = time.time()
        return session["messages"][-MAX_HISTORY:]


def _add_message(platform: str, user_id: str, role: str, content: str):
    key = _session_key(platform, user_id)
    with _sessions_lock:
        if key not in _sessions:
            _sessions[key] = {"messages": [], "last_active": time.time()}
        session = _sessions[key]
        session["messages"].append({"role": role, "content": content})
        session["last_active"] = time.time()
        if len(session["messages"]) > MAX_HISTORY * 2:
            session["messages"] = session["messages"][-MAX_HISTORY:]


def _cleanup_stale_sessions():
    """Remove sessions inactive for more than SESSION_TTL; enforce MAX_SESSIONS cap."""
    now = time.time()
    with _sessions_lock:
        stale = [k for k, v in _sessions.items() if now - v.get("last_active", 0) > SESSION_TTL]
        for k in stale:
            del _sessions[k]
        if len(_sessions) > MAX_SESSIONS:
            by_age = sorted(_sessions.items(), key=lambda kv: kv[1].get("last_active", 0))
            evict = len(_sessions) - MAX_SESSIONS
            for k, _ in by_age[:evict]:
                del _sessions[k]
            _bot_logger.warning("Session cap reached (%d); evicted %d oldest", MAX_SESSIONS, evict)
    if stale:
        _bot_logger.info("Cleaned up %d stale bot sessions", len(stale))


# ======================================================================
#  BotGateway
# ======================================================================

class BotGateway:
    """Central gateway that connects chat platforms to the Knowledge Agent.

    Usage::

        gw = BotGateway(agent_url="http://localhost:8360")

        # Option A: start Telegram polling
        gw.start_telegram(token="BOT_TOKEN")

        # Option B: register Zalo webhook on a FastAPI app
        gw.start_zalo(oa_id="...", oa_secret="...")

    Attributes:
        agent_url: Base URL of the Knowledge Agent server.
        rate_limiter: Per-user rate limiter (10 msg/min default).
        telegram_app: Telegram Application instance (if started).
    """

    def __init__(self, agent_url: str = "http://localhost:8360"):
        self.agent_url = agent_url.rstrip("/")
        self.rate_limiter = UserRateLimiter(max_requests=10, window_seconds=60)
        self.telegram_app: Optional[object] = None
        self._zalo_oa_id: str = ""
        self._zalo_oa_secret: str = ""

    # ── Agent communication ──

    async def send_to_agent(self, message: str, session_id: str) -> dict:
        """Forward a user message to the Knowledge Agent with retry.

        Args:
            message: The user's text message.
            session_id: Unique session identifier (platform:user_id).

        Returns:
            Dict with keys "reply" (str) and "suggestions" (list[str]).
        """
        history = _get_history(
            session_id.split(":")[0] if ":" in session_id else "unknown",
            session_id.split(":")[-1],
        )
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=90) as http_client:
                    resp = await http_client.post(
                        f"{self.agent_url}/chat",
                        json={
                            "message": message,
                            "session_id": session_id,
                            "history": history,
                        },
                    )
                    if resp.status_code >= 500:
                        _bot_logger.warning("Agent returned %d, attempt %d/%d", resp.status_code, attempt + 1, max_retries + 1)
                        if attempt < max_retries:
                            await _async_sleep(1.5 * (attempt + 1))
                            continue
                        return {
                            "reply": "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau ít phút.",
                            "suggestions": [],
                        }
                    if resp.status_code >= 400:
                        _bot_logger.error("Agent returned %d: %s", resp.status_code, resp.text[:200])
                        return {
                            "reply": "Xin lỗi, yêu cầu không hợp lệ. Vui lòng thử lại.",
                            "suggestions": [],
                        }
                    try:
                        data = resp.json()
                    except (json.JSONDecodeError, ValueError) as je:
                        _bot_logger.error("Agent returned invalid JSON: %s, body=%s", je, resp.text[:200])
                        return {
                            "reply": "Xin lỗi, hệ thống trả lời không hợp lệ. Vui lòng thử lại.",
                            "suggestions": [],
                        }
                    return {
                        "reply": data.get("reply", "Xin lỗi, tôi không trả lời được."),
                        "suggestions": data.get("suggestions", []),
                    }
            except httpx.TimeoutException:
                _bot_logger.warning("Agent timeout, attempt %d/%d, session=%s", attempt + 1, max_retries + 1, session_id)
                if attempt < max_retries:
                    await _async_sleep(2)
                    continue
                return {
                    "reply": "Xin lỗi, hệ thống đang xử lý lâu. Vui lòng thử lại.",
                    "suggestions": [],
                }
            except httpx.ConnectError:
                _bot_logger.error("Cannot connect to agent at %s", self.agent_url)
                return {
                    "reply": "Xin lỗi, không thể kết nối đến hệ thống. Vui lòng thử lại sau.",
                    "suggestions": [],
                }
            except Exception as e:
                _bot_logger.error("Unexpected error sending to agent: %s", e, exc_info=True)
                return {
                    "reply": "Xin lỗi, đã xảy ra lỗi. Vui lòng thử lại sau.",
                    "suggestions": [],
                }
        # Should not reach here, but just in case
        return {"reply": "Xin lỗi, hệ thống đang bận. Vui lòng thử lại sau.", "suggestions": []}

    def format_reply(self, reply: str, platform: str) -> str:
        """Format an agent reply for a specific platform.

        Converts markdown produced by the agent into the markup
        supported by the target platform.

        Args:
            reply: Raw markdown reply from the agent.
            platform: Target platform ("telegram" or "zalo").

        Returns:
            Platform-formatted string.
        """
        return convert_markdown(reply, platform)

    # ── Telegram ──

    def start_telegram(self, token: str):
        """Start the Telegram bot with long-polling.

        This is a blocking call that runs the Telegram polling loop.
        Call it from the main thread or in a dedicated thread.

        Args:
            token: Telegram Bot API token from @BotFather.

        Raises:
            RuntimeError: If python-telegram-bot is not installed.
        """
        if not HAS_TELEGRAM:
            raise RuntimeError(
                "python-telegram-bot is not installed. "
                "Install with: pip install python-telegram-bot"
            )

        app = Application.builder().token(token).build()
        self.telegram_app = app

        # Register handlers
        app.add_handler(CommandHandler("start", self._tg_start))
        app.add_handler(CommandHandler("help", self._tg_help))
        app.add_handler(CommandHandler("map", self._tg_map))
        app.add_handler(CommandHandler("reset", self._tg_reset))
        # ── Lệnh quản trị (gated theo ADMIN_TELEGRAM_IDS) ──
        app.add_handler(CommandHandler("admin", self._tg_admin))
        app.add_handler(CommandHandler("thongke", self._tg_thongke))
        app.add_handler(CommandHandler("choduyet", self._tg_choduyet))
        app.add_handler(CommandHandler("baosai", self._tg_baosai))
        app.add_handler(CommandHandler("reloadkb", self._tg_reloadkb))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._tg_message)
        )
        app.add_handler(CallbackQueryHandler(self._tg_callback))

        _bot_logger.info("Telegram bot polling started")
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,  # Fix conflict with stale getUpdates
            # stop_signals=None: chạy dưới systemd/non-main-thread → PTB không cài signal
            # handler (tránh "set_wakeup_fd only works in main thread"). systemd lo restart/stop.
            stop_signals=None,
        )

    async def _tg_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome = (
            "🌴 *Xin chào!* Tôi là hướng dẫn viên AI của vinhlong360.vn\n\n"
            "Bạn có thể hỏi tôi về:\n"
            "🏛 Điểm tham quan Vĩnh Long, Bến Tre, Trà Vinh\n"
            "🍜 Ẩm thực & đặc sản OCOP\n"
            "🗺 Lịch trình du lịch tự động\n"
            "🎭 Lễ hội & văn hóa Khmer\n"
            "📊 So sánh các khu vực\n\n"
            "Gõ câu hỏi bất kỳ để bắt đầu!\n\n"
            "Lệnh: /help · /map · /reset"
        )
        await update.message.reply_text(
            welcome, parse_mode="Markdown"
        )

    async def _tg_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "🤖 *Các khả năng của tôi:*\n\n"
            "🔍 Tìm kiếm điểm du lịch, ẩm thực, đặc sản OCOP\n"
            "🗺 Lập lịch trình du lịch tự động\n"
            "🌸 Thông tin theo mùa (trái cây, lễ hội)\n"
            "⚖ So sánh các vùng (Vĩnh Long vs Bến Tre...)\n"
            "📍 Tìm địa điểm gần nhau\n"
            "🌐 Tìm kiếm web khi cần\n\n"
            "*Lệnh:*\n"
            "/start — Lời chào\n"
            "/help  — Trợ giúp này\n"
            "/map   — Xem bản đồ\n"
            "/reset — Xóa lịch sử hội thoại\n\n"
            "💬 Gõ bất kỳ câu hỏi nào về Vĩnh Long!"
        )
        await update.message.reply_text(
            help_text, parse_mode="Markdown"
        )

    async def _tg_map(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /map command."""
        await update.message.reply_text(
            f"🗺 Bản đồ du lịch Vĩnh Long:\n{MAP_URL}",
            disable_web_page_preview=False,
        )

    async def _tg_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command."""
        user_id = str(update.effective_user.id)
        key = _session_key("telegram", user_id)
        with _sessions_lock:
            _sessions.pop(key, None)
        await update.message.reply_text(
            "✅ Đã xóa lịch sử hội thoại. Bắt đầu cuộc trò chuyện mới!"
        )

    # ── Quản trị (admin-only) ──────────────────────────────────────────

    def _is_admin(self, update: Update) -> bool:
        uid = str(update.effective_user.id) if update.effective_user else ""
        return bool(ADMIN_TELEGRAM_IDS) and uid in ADMIN_TELEGRAM_IDS

    async def _deny(self, update: Update):
        await update.message.reply_text("⛔ Lệnh quản trị chỉ dành cho admin.")

    async def _admin_api(self, method: str, path: str, **kwargs):
        """Gọi /admin/* (hoặc /reload) trên agent với X-Admin-Key. Trả JSON hoặc ném lỗi."""
        headers = {"X-Admin-Key": ADMIN_API_KEY}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.request(method, f"{self.agent_url}{path}", headers=headers, **kwargs)
            r.raise_for_status()
            return r.json()

    async def _tg_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update):
            return await self._deny(update)
        await update.message.reply_text(
            "🛠 *Quản trị vinhlong360*\n"
            "/thongke — số liệu tri thức (entities/quan hệ/cần xem lại)\n"
            "/choduyet — bài cộng đồng chờ duyệt\n"
            "/baosai — báo cáo sai thông tin gần đây\n"
            "/reloadkb — nạp lại tri thức từ DB",
            parse_mode="Markdown")

    async def _tg_thongke(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update):
            return await self._deny(update)
        try:
            s = await self._admin_api("GET", "/admin/stats")
            await update.message.reply_text(
                f"📊 *Thống kê tri thức*\n"
                f"• Entities: {s.get('total_entities', 0)}\n"
                f"• Địa điểm: {s.get('total_places', 0)}\n"
                f"• Quan hệ: {s.get('total_relationships', 0)}\n"
                f"• Lịch trình: {s.get('total_itineraries', 0)}\n"
                f"• Cần xem lại (conf<0.7): {s.get('low_confidence', 0)}",
                parse_mode="Markdown")
        except Exception as e:  # noqa: BLE001
            await update.message.reply_text(f"⚠️ Lỗi lấy thống kê: {e}")

    async def _tg_choduyet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update):
            return await self._deny(update)
        try:
            m = await self._admin_api("GET", "/admin/moderation/stats")
            await update.message.reply_text(
                f"🧐 *Kiểm duyệt cộng đồng*\n• Chờ duyệt: {m.get('pending', 0)}\n"
                f"Mở /admin/kiem-duyet trên web để xử lý.", parse_mode="Markdown")
        except Exception as e:  # noqa: BLE001
            await update.message.reply_text(f"⚠️ Lỗi (UGC cần Postgres?): {e}")

    async def _tg_baosai(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update):
            return await self._deny(update)
        try:
            data = await self._admin_api("GET", "/admin/info-reports?limit=5")
            reports = data.get("reports", [])
            if not reports:
                return await update.message.reply_text("✅ Không có báo cáo sai thông tin nào.")
            lines = [f"⚠️ *Báo sai gần đây* (tổng {data.get('total', 0)}):"]
            for r in reports:
                lines.append(f"• [{r.get('target_type')}] {r.get('target_id')} — {r.get('reason', '')[:60]}")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:  # noqa: BLE001
            await update.message.reply_text(f"⚠️ Lỗi lấy báo sai: {e}")

    async def _tg_reloadkb(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update):
            return await self._deny(update)
        try:
            await update.message.reply_text("⏳ Đang nạp lại tri thức từ DB…")
            res = await self._admin_api("POST", "/reload")
            await update.message.reply_text(
                f"✅ Đã reload: {res.get('entities', '?')} entities (nguồn: {res.get('source', '?')})")
        except Exception as e:  # noqa: BLE001
            await update.message.reply_text(f"⚠️ Reload lỗi: {e}")

    async def _tg_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages."""
        user_id = str(update.effective_user.id)
        user_key = _session_key("telegram", user_id)
        text = update.message.text

        # Rate limit check
        if not self.rate_limiter.is_allowed(user_key):
            wait = self.rate_limiter.retry_after(user_key)
            await update.message.reply_text(
                f"⏳ Bạn gửi tin nhắn quá nhanh. Vui lòng đợi {wait} giây."
            )
            return

        _bot_logger.info("TG message from %s: %s", update.effective_user.first_name, text[:80])

        # Record user message
        _add_message("telegram", user_id, "user", text)

        # Send to agent
        result = await self.send_to_agent(text, user_key)

        reply = result["reply"]
        suggestions = result["suggestions"]

        # Record assistant reply
        _add_message("telegram", user_id, "assistant", reply)

        # Format for Telegram
        formatted = self.format_reply(reply, "telegram")

        # Build inline keyboard from suggestions
        keyboard = None
        if suggestions:
            buttons = [
                [InlineKeyboardButton(s, callback_data=s[:64])]
                for s in suggestions[:5]
            ]
            keyboard = InlineKeyboardMarkup(buttons)

        # Send reply (split if too long)
        chunks = [formatted[i:i + 4000] for i in range(0, len(formatted), 4000)]
        for i, chunk in enumerate(chunks):
            try:
                await update.message.reply_text(
                    chunk,
                    parse_mode="Markdown",
                    reply_markup=keyboard if i == len(chunks) - 1 else None,
                    disable_web_page_preview=True,
                )
            except Exception as md_err:
                # Fallback: send without markdown if parsing fails
                _bot_logger.debug("Markdown parse failed, sending plain text: %s", md_err)
                await update.message.reply_text(
                    chunk,
                    reply_markup=keyboard if i == len(chunks) - 1 else None,
                    disable_web_page_preview=True,
                )

    async def _tg_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses (suggestion clicks)."""
        query = update.callback_query
        await query.answer()

        # Treat the callback data as a new message
        user_id = str(query.from_user.id)
        user_key = _session_key("telegram", user_id)
        text = query.data

        if not self.rate_limiter.is_allowed(user_key):
            wait = self.rate_limiter.retry_after(user_key)
            await query.message.reply_text(
                f"⏳ Bạn gửi tin nhắn quá nhanh. Vui lòng đợi {wait} giây."
            )
            return

        _bot_logger.info("TG callback from %s: %s", query.from_user.first_name, text[:64])

        _add_message("telegram", user_id, "user", text)
        result = await self.send_to_agent(text, user_key)
        reply = result["reply"]
        suggestions = result["suggestions"]
        _add_message("telegram", user_id, "assistant", reply)

        formatted = self.format_reply(reply, "telegram")

        keyboard = None
        if suggestions:
            buttons = [
                [InlineKeyboardButton(s, callback_data=s[:64])]
                for s in suggestions[:5]
            ]
            keyboard = InlineKeyboardMarkup(buttons)

        chunks = [formatted[i:i + 4000] for i in range(0, len(formatted), 4000)]
        for i, chunk in enumerate(chunks):
            try:
                await query.message.reply_text(
                    chunk,
                    parse_mode="Markdown",
                    reply_markup=keyboard if i == len(chunks) - 1 else None,
                    disable_web_page_preview=True,
                )
            except Exception as md_err:
                _bot_logger.debug("Markdown parse failed in callback, sending plain: %s", md_err)
                await query.message.reply_text(
                    chunk,
                    reply_markup=keyboard if i == len(chunks) - 1 else None,
                    disable_web_page_preview=True,
                )

    # ── Zalo OA ──

    def start_zalo(self, oa_id: str, oa_secret: str):
        """Register Zalo OA credentials for webhook handling.

        The actual webhook endpoint is served by the FastAPI app
        returned from ``create_bot_app()``. This method only stores
        the credentials so that incoming webhooks can be verified
        and replies can be sent.

        Args:
            oa_id: Zalo OA application ID.
            oa_secret: Zalo OA secret for webhook signature verification.
        """
        self._zalo_oa_id = oa_id
        self._zalo_oa_secret = oa_secret
        _bot_logger.info("Zalo OA registered (ID: %s...)", oa_id[:8])

    def verify_zalo_signature(self, raw_body: bytes, signature: str) -> bool:
        """Verify Zalo webhook signature.

        Args:
            raw_body: Raw request body bytes.
            signature: Value of the X-ZEvent-Signature header.

        Returns:
            True if signature is valid or no secret is configured.
        """
        if not self._zalo_oa_secret:
            return True
        expected = "mac=" + hmac.new(
            self._zalo_oa_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    async def handle_zalo_event(self, body: dict) -> dict:
        """Process a Zalo OA webhook event.

        Handles:
          - user_send_text: forward to agent and reply
          - follow: send welcome message

        Args:
            body: Parsed JSON body from the webhook.

        Returns:
            Status dict for the HTTP response.
        """
        event_name = body.get("event_name", "")

        if event_name == "user_send_text":
            message_data = body.get("message", {})
            text = message_data.get("text", "")
            user_id = body.get("sender", {}).get("id", "")

            if not text or not user_id:
                return {"success": True}

            user_key = _session_key("zalo", user_id)

            # Rate limit
            if not self.rate_limiter.is_allowed(user_key):
                wait = self.rate_limiter.retry_after(user_key)
                await self._zalo_send(
                    user_id,
                    f"Ban gui tin nhan qua nhanh. Vui long doi {wait} giay."
                )
                return {"status": "rate_limited"}

            _bot_logger.info("Zalo message from %s: %s", user_id, text[:80])

            _add_message("zalo", user_id, "user", text)
            result = await self.send_to_agent(text, user_key)
            reply = result["reply"]
            suggestions = result["suggestions"]
            _add_message("zalo", user_id, "assistant", reply)

            formatted = self.format_reply(reply, "zalo")

            # Send main reply
            await self._zalo_send(user_id, formatted)

            # Send quick reply buttons for suggestions
            if suggestions:
                await self._zalo_send_with_buttons(user_id, suggestions)

        elif event_name == "follow":
            user_id = body.get("follower", {}).get("id", "")
            if user_id:
                welcome = (
                    "Chao ban! Toi la tro ly AI cua vinhlong360.vn\n\n"
                    "Ban co the hoi toi ve du lich, am thuc, lich su, "
                    "van hoa tinh Vinh Long (bao gom Ben Tre va Tra Vinh).\n\n"
                    "Go cau hoi bat ky de bat dau!"
                )
                await self._zalo_send(user_id, welcome)

        return {"success": True}

    async def _zalo_send(self, user_id: str, text: str):
        """Send a text message via Zalo OA API.

        Args:
            user_id: Zalo user ID to send to.
            text: Message text (max ~2000 chars per chunk).
        """
        url = "https://openapi.zalo.me/v3.0/oa/message/cs"
        headers = {"access_token": self._zalo_oa_id}
        chunks = [text[i:i + 1900] for i in range(0, len(text), 1900)]
        async with httpx.AsyncClient(timeout=30) as client:
            for chunk in chunks:
                for attempt in range(2):
                    try:
                        resp = await client.post(url, headers=headers, json={
                            "recipient": {"user_id": user_id},
                            "message": {"text": chunk},
                        })
                        if resp.status_code >= 500 and attempt == 0:
                            _bot_logger.warning("Zalo API 5xx (%d), retrying", resp.status_code)
                            continue
                        break
                    except Exception as exc:
                        _bot_logger.warning("Zalo send failed (attempt %d): %s", attempt + 1, exc)
                        if attempt == 0:
                            continue
                        break

    async def _zalo_send_with_buttons(self, user_id: str, suggestions: list[str]):
        """Send quick-reply buttons for suggestions via Zalo OA API.

        Uses the Zalo list/buttons template to show suggestion options.

        Args:
            user_id: Zalo user ID.
            suggestions: List of suggestion strings.
        """
        url = "https://openapi.zalo.me/v3.0/oa/message/cs"
        headers = {"access_token": self._zalo_oa_id}
        # Build quick reply elements
        elements = []
        for s in suggestions[:5]:
            elements.append({
                "title": s,
                "subtitle": "",
                "image_url": "",
                "default_action": {
                    "type": "oa.query.show",
                    "payload": s,
                },
            })

        payload = {
            "recipient": {"user_id": user_id},
            "message": {
                "text": "Ban co the hoi them:",
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "list",
                        "elements": elements,
                    },
                },
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                await client.post(url, headers=headers, json=payload)
            except Exception as exc:
                _bot_logger.warning("Zalo send_with_buttons failed: %s", exc)


# ======================================================================
#  FastAPI App Factory
# ======================================================================

# Module-level gateway instance (used by the FastAPI app and CLI)
_gateway: Optional[BotGateway] = None


def _get_gateway() -> BotGateway:
    """Return the module-level BotGateway, creating it if needed."""
    global _gateway
    if _gateway is None:
        _gateway = BotGateway(agent_url=AGENT_URL)
    return _gateway


def create_bot_app() -> FastAPI:
    """Create and return a FastAPI app with Zalo webhook endpoints.

    The returned app can be:
      - Mounted on the main agent server via ``app.mount("/bot", create_bot_app())``
      - Run standalone on port 8361 via ``uvicorn.run(app, port=8361)``

    Returns:
        Configured FastAPI application.
    """
    bot_app = FastAPI(title="vinhlong360 Bot Gateway")
    gw = _get_gateway()

    # Register Zalo if credentials are available
    if ZALO_OA_ID and ZALO_OA_SECRET:
        gw.start_zalo(oa_id=ZALO_OA_ID, oa_secret=ZALO_OA_SECRET)

    @bot_app.get("/")
    async def home():
        """Gateway status page."""
        platforms = []
        if TELEGRAM_TOKEN and HAS_TELEGRAM:
            platforms.append("Telegram")
        if ZALO_OA_ID:
            platforms.append("Zalo OA")
        return {
            "service": "vinhlong360 Bot Gateway",
            "platforms": platforms or ["(chua cau hinh - xem .env)"],
            "agent_url": gw.agent_url,
            "session_count": len(_sessions),
        }

    @bot_app.post("/webhook/zalo")
    async def zalo_webhook(request: Request):
        """Receive and process Zalo OA webhook events.

        Verifies the webhook signature if ZALO_OA_SECRET is configured,
        then delegates to ``BotGateway.handle_zalo_event()``.
        """
        if not ZALO_OA_ID:
            raise HTTPException(503, detail="ZALO_OA_ID not configured")

        # Read raw body for signature verification
        raw_body = await request.body()

        # Verify signature — reject if secret not configured (no unauthenticated webhooks)
        if not ZALO_OA_SECRET:
            _bot_logger.warning("Zalo webhook rejected: ZALO_OA_SECRET not configured")
            raise HTTPException(503, detail="Webhook signature verification not configured")
        signature = request.headers.get("X-ZEvent-Signature", "")
        if not gw.verify_zalo_signature(raw_body, signature):
            _bot_logger.warning("Zalo webhook: invalid signature")
            raise HTTPException(401, detail="Invalid webhook signature")

        try:
            body = json.loads(raw_body)
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(400, detail="Invalid JSON body")
        return await gw.handle_zalo_event(body)

    @bot_app.get("/stats")
    async def gateway_stats():
        """Session statistics by platform."""
        with _sessions_lock:
            by_platform: dict[str, int] = defaultdict(int)
            total_messages = 0
            for key, session in _sessions.items():
                platform = key.split(":")[0]
                by_platform[platform] += 1
                total_messages += len(session.get("messages", []))
            return {
                "total_sessions": len(_sessions),
                "by_platform": dict(by_platform),
                "total_messages": total_messages,
            }

    return bot_app


# ======================================================================
#  CLI Entry Point
# ======================================================================

if __name__ == "__main__":
    import asyncio
    import threading

    import uvicorn

    gw = _get_gateway()

    print("=" * 55)
    print("  vinhlong360 Bot Gateway")
    print("=" * 55)
    print(f"  Agent:    {gw.agent_url}")
    print(f"  Telegram: {'configured' if TELEGRAM_TOKEN and HAS_TELEGRAM else 'disabled (set TELEGRAM_BOT_TOKEN)'}")
    if not HAS_TELEGRAM and TELEGRAM_TOKEN:
        print("            (token set but python-telegram-bot not installed)")
    print(f"  Zalo:     {'configured' if ZALO_OA_ID else 'disabled (set ZALO_OA_ID, ZALO_OA_SECRET)'}")
    _admin_state = (f"{len(ADMIN_TELEGRAM_IDS)} chat ID" if ADMIN_TELEGRAM_IDS
                    else "disabled (set ADMIN_TELEGRAM_IDS=<chat_id,...>)")
    print(f"  Admin TG: {_admin_state}{'' if ADMIN_API_KEY else '  ⚠ thiếu ADMIN_API_KEY'}")
    print(f"  API:      http://localhost:8361")
    print("=" * 55)

    if not any([TELEGRAM_TOKEN and HAS_TELEGRAM, ZALO_OA_ID]):
        print()
        print("  Chua cau hinh platform nao. Dien token vao .env:")
        print("    TELEGRAM_BOT_TOKEN  - lay tu @BotFather")
        print("    ZALO_OA_ID          - lay tu oa.zalo.me")
        print("    ZALO_OA_SECRET      - lay tu oa.zalo.me")
        print()

    # Create FastAPI app (includes Zalo webhook)
    app = create_bot_app()

    # Start session cleanup thread (every hour)
    def _session_cleanup_loop():
        while True:
            time.sleep(3600)
            _cleanup_stale_sessions()

    cleanup_thread = threading.Thread(target=_session_cleanup_loop, daemon=True, name="session-cleanup")
    cleanup_thread.start()

    # Start Telegram in a background thread (polling is blocking)
    if TELEGRAM_TOKEN and HAS_TELEGRAM:
        def _run_telegram():
            try:
                gw.start_telegram(token=TELEGRAM_TOKEN)
            except Exception as e:
                _bot_logger.error("Telegram polling error: %s", e, exc_info=True)

        tg_thread = threading.Thread(target=_run_telegram, daemon=True)
        tg_thread.start()
        print("  [Telegram] Polling started in background thread")

    # Start FastAPI server (Zalo webhook + stats)
    uvicorn.run(app, host="0.0.0.0", port=8361)

"""
vinhlong360 — Task Scheduler.

Chạy các tác vụ nền định kỳ:
  - Auto-learn từ knowledge gaps (mỗi 6h)
  - Relationship discovery (mỗi 24h)
  - Data sync (data.json → data.js) sau mỗi thay đổi
  - Analytics cleanup (mỗi 24h)
  - Cache cleanup (mỗi 1h)

Chạy: python agent/scheduler.py
Hoặc import và gọi start_scheduler() từ server.
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
import threading
import traceback
from datetime import datetime, timedelta, timezone

_VN_TZ = timezone(timedelta(hours=7))
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent

# ── Logging ──
_sched_logger = logging.getLogger("scheduler")
if not _sched_logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _sched_logger.addHandler(_h)
    _sched_logger.setLevel(getattr(logging, os.environ.get("LOG_LEVEL", "INFO")))


# ── Learning cadence (seconds) — override via .env, floor 5 phút ──

def _env_int(name: str, default: int) -> int:
    try:
        v = int(os.environ.get(name, ""))
        return v if v >= 300 else default
    except (ValueError, TypeError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


SCHEDULER_ENABLED = _env_bool("SCHEDULER_ENABLED", True)
SCHEDULER_RUN_STARTUP_TASKS = _env_bool("SCHEDULER_RUN_STARTUP_TASKS", False)
AUTONOMOUS_TASKS_ENABLED = _env_bool("SCHEDULER_ENABLE_AUTONOMOUS_TASKS", False)  # §B8: vòng lặp LLM nền TẮT mặc định (khớp config.py + .env.example)

DISCOVERY_INTERVAL    = _env_int("LEARN_INTERVAL_DISCOVERY", 3600)        # 1h (adaptive 30m–6h)
LEARNING_LOOP_INTERVAL = _env_int("LEARN_INTERVAL_LOOP", 3600)            # 1h
AUTO_LEARN_INTERVAL   = _env_int("LEARN_INTERVAL_AUTOLEARN", 3 * 3600)    # 3h
PROMOTION_INTERVAL    = _env_int("LEARN_INTERVAL_PROMOTION", 6 * 3600)    # 6h

# Adaptive bounds for continuous-discovery
DISCOVERY_MIN_INTERVAL = 1800       # 30 phút khi đang "trúng mỏ"
DISCOVERY_MAX_INTERVAL = 6 * 3600   # 6h khi bão hoà


def _get_task(name: str):
    for t in TASKS:
        if t.name == name:
            return t
    return None


# ══════════════════════════════════════════════════
#  DATA SYNC: data.json → data.js
# ══════════════════════════════════════════════════

def sync_data_json_to_js():
    """Đồng bộ data.json → data.js khi data.json thay đổi."""
    json_path = PROJECT_DIR / "web" / "data.json"
    js_path = PROJECT_DIR / "web" / "data.js"

    if not json_path.exists():
        _sched_logger.warning("data.json not found, skip sync")
        return False

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))

        # Build a plain script because web/index.html loads data.js without type="module".
        places = [e for e in data["entities"] if e["type"] == "place"]
        entities = [e for e in data["entities"] if e["type"] != "place"]
        relationships = data.get("relationships", [])
        itineraries = data.get("itineraries", [])

        js_content = (
            "/* vinhlong360 data - auto-synced from data.json */\n"
            "(function () {\n"
            f"var places = {json.dumps(places, ensure_ascii=False, indent=2)};\n"
            f"var items = {json.dumps(entities, ensure_ascii=False, indent=2)};\n"
            f"var relationships = {json.dumps(relationships, ensure_ascii=False, indent=2)};\n"
            f"var itineraries = {json.dumps(itineraries, ensure_ascii=False, indent=2)};\n"
            "window.VL_DATA = {\n"
            "  entities: places.concat(items),\n"
            "  relationships: relationships,\n"
            "  itineraries: itineraries,\n"
            "  ALL_MONTHS: [1,2,3,4,5,6,7,8,9,10,11,12]\n"
            "};\n"
            "})();\n"
        )
        js_path.write_text(js_content, encoding="utf-8")

        _sched_logger.info("Synced data.json → data.js (%d places, %d entities, %d rels, %d itineraries)", len(places), len(entities), len(relationships), len(itineraries))
        return True
    except Exception as e:
        _sched_logger.error("Data sync error: %s", e)
        return False


# ══════════════════════════════════════════════════
#  SCHEDULED TASKS
# ══════════════════════════════════════════════════

_TASK_TIMEOUT = int(os.environ.get("SCHEDULER_TASK_TIMEOUT", "600"))


_MAX_RETRIES = 2
_RETRY_BACKOFF_BASE = 30


class ScheduledTask:
    def __init__(self, name: str, func, interval_seconds: int, enabled: bool = True,
                 run_immediately: bool = True, timeout: int | None = None):
        self.name = name
        self.func = func
        self.interval = interval_seconds
        self.enabled = enabled
        self.last_run = 0
        self.run_count = 0
        self.last_error = None
        self.timeout = timeout or _TASK_TIMEOUT
        self.next_run_after = 0 if run_immediately else time.time() + interval_seconds
        self._consecutive_failures = 0

    def should_run(self) -> bool:
        if not self.enabled:
            return False
        if time.time() < self.next_run_after:
            return False
        return time.time() - self.last_run >= self.interval

    def run(self):
        try:
            _sched_logger.info("Running task: %s (timeout=%ds)", self.name, self.timeout)
            start = time.time()
            result_holder = [None]
            error_holder = [None]

            def _target():
                try:
                    result_holder[0] = self.func()
                except Exception as exc:
                    error_holder[0] = exc

            worker = threading.Thread(target=_target, daemon=True)
            worker.start()
            worker.join(timeout=self.timeout)

            if worker.is_alive():
                self._consecutive_failures += 1
                self.last_error = f"Task timed out after {self.timeout}s"
                if self._consecutive_failures <= _MAX_RETRIES:
                    backoff = _RETRY_BACKOFF_BASE * (2 ** (self._consecutive_failures - 1))
                    self.next_run_after = time.time() + backoff
                    _sched_logger.warning("Task timed out: %s (%ds), retry in %ds (attempt %d/%d)",
                                          self.name, self.timeout, backoff,
                                          self._consecutive_failures, _MAX_RETRIES + 1)
                else:
                    _sched_logger.error("Task timed out: %s (%ds) — %d consecutive failures",
                                        self.name, self.timeout, self._consecutive_failures)
                return

            if error_holder[0] is not None:
                raise error_holder[0]

            elapsed = round(time.time() - start, 1)
            self.last_run = time.time()
            self.run_count += 1
            self.last_error = None
            self._consecutive_failures = 0
            _sched_logger.info("Task done: %s (%.1fs)", self.name, elapsed)
        except Exception as e:
            self._consecutive_failures += 1
            self.last_error = str(e)
            if self._consecutive_failures <= _MAX_RETRIES:
                backoff = _RETRY_BACKOFF_BASE * (2 ** (self._consecutive_failures - 1))
                self.next_run_after = time.time() + backoff
                _sched_logger.warning("Task failed: %s (attempt %d/%d), retry in %ds — %s",
                                      self.name, self._consecutive_failures, _MAX_RETRIES + 1, backoff, e)
            else:
                _sched_logger.error("Task failed: %s — %d consecutive failures, waiting normal interval — %s\n%s",
                                    self.name, self._consecutive_failures, e, traceback.format_exc())


def task_auto_learn():
    """Chạy LLM auto-learn SAU cổng fitness, chỉ khi có knowledge gaps.

    Trước đây hỏng kép: đọc sai key 'knowledge_gaps' (thực tế gaps nằm ở
    'unanswered') và truyền tham số '--query' mà auto_learn.py không hỗ trợ.
    Nay: kiểm tra gaps qua 'unanswered', chạy '--apply --topics 3' hợp lệ,
    bọc trong guarded_evolve để rollback nếu KB xấu đi.
    """
    try:
        analytics_path = AGENT_DIR / "data" / "analytics.json"
        if not analytics_path.exists():
            return
        data = json.loads(analytics_path.read_text(encoding="utf-8"))
        gaps = data.get("unanswered", []) or []
        if not gaps:
            _sched_logger.info("No knowledge gaps for auto-learn")
            return

        _sched_logger.info("Auto-learn triggered (%d unanswered queries)", len(gaps))

        def _apply():
            result = subprocess.run(
                [sys.executable, str(AGENT_DIR / "auto_learn.py"), "--apply", "--topics", "3"],
                capture_output=True, text=True, timeout=300,
                cwd=str(PROJECT_DIR),
            )
            return {
                "returncode": result.returncode,
                "stderr": result.stderr[:200] if result.returncode else "",
            }

        from self_evolve import guarded_evolve
        summary = guarded_evolve("auto-learn", _apply)
        _sched_logger.info("Auto-learn: decision=%s reason=%s", summary['decision'], summary['reason'])

    except subprocess.TimeoutExpired:
        _sched_logger.error("Auto-learn timeout (300s)")
    except Exception as e:
        _sched_logger.error("Auto-learn error: %s\n%s", e, traceback.format_exc())


def task_relationship_discovery():
    """Chạy relationship discovery SAU cổng fitness (auto-rollback nếu hại KB)."""
    try:
        def _apply():
            result = subprocess.run(
                [sys.executable, str(AGENT_DIR / "relationship_discovery.py"), "--apply"],
                capture_output=True, text=True, timeout=300,
                cwd=str(PROJECT_DIR),
            )
            return {"returncode": result.returncode,
                    "stderr": result.stderr[:200] if result.returncode else ""}

        from self_evolve import guarded_evolve
        summary = guarded_evolve("relationships", _apply)
        _sched_logger.info("Relationship discovery: decision=%s reason=%s", summary['decision'], summary['reason'])
    except subprocess.TimeoutExpired:
        _sched_logger.error("Relationship discovery timeout (300s)")
    except Exception as e:
        _sched_logger.error("Relationship discovery error: %s\n%s", e, traceback.format_exc())


def task_sync_data():
    """Đồng bộ data."""
    sync_data_json_to_js()


def task_cleanup_analytics():
    """Dọn dẹp analytics data cũ."""
    try:
        analytics_path = AGENT_DIR / "data" / "analytics.json"
        if not analytics_path.exists():
            return

        data = json.loads(analytics_path.read_text(encoding="utf-8"))

        # Keep only last 30 days of daily stats
        daily = data.get("daily_stats", {})
        if len(daily) > 30:
            sorted_days = sorted(daily.keys())
            for day in sorted_days[:-30]:
                del daily[day]
            data["daily_stats"] = daily
            analytics_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            _sched_logger.info("Trimmed daily stats to last 30 days")

    except Exception as e:
        _sched_logger.error("Analytics cleanup error: %s", e)


def task_admin_digest():
    """Digest quản lý định kỳ → Telegram admin. MIỄN PHÍ: tính từ DB/file, KHÔNG gọi LLM
    (không vi phạm §B8 — thay cho 'agent tự động' tốn LLM 24/7). No-op nếu chưa cấu hình
    TELEGRAM_BOT_TOKEN + ADMIN_TELEGRAM_IDS."""
    import os
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    admin_ids = [x.strip() for x in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(",") if x.strip()]
    if not token or not admin_ids:
        return  # chưa cấu hình admin Telegram → bỏ qua

    parts = []
    try:
        import knowledge
        s = knowledge.stats()
        parts.append(f"• Nội dung: {s.get('total_content', 0)} · Địa điểm: {s.get('places', 0)} · Lịch trình: {s.get('itineraries', 0)}")
    except Exception as e:
        _sched_logger.error("digest stats error: %s", e)
    # Báo-sai (reports.jsonl) — free, đọc file
    try:
        rf = AGENT_DIR / "data" / "reports.jsonl"
        n = sum(1 for ln in rf.read_text(encoding="utf-8").splitlines() if ln.strip()) if rf.exists() else 0
        if n:
            parts.append(f"• ⚠️ Báo sai: {n} (xem /baosai)")
    except Exception as e:
        _sched_logger.warning("digest reports read error: %s", e)
    # Kiểm duyệt chờ (Postgres-only; bỏ qua nếu lỗi)
    try:
        from database import db
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT COUNT(*) AS c FROM posts WHERE status = {ph}", ("pending",))
            if row and row["c"]:
                parts.append(f"• 🧐 Chờ duyệt: {row['c']}")
    except Exception as e:
        _sched_logger.debug("digest moderation check skipped: %s", e)

    # Cảnh báo ngân sách: nếu agent tự động bật, báo mức dùng LLM/cap (free, không gọi LLM).
    try:
        import autonomous_budget as ab
        if ab.enabled():
            st = ab.status()
            warn = " ⚠️ GẦN CAP!" if st["remaining_today"] <= max(1, st["cap_per_day"] // 5) else ""
            parts.append(f"• 💰 Agent LLM: {st['used_today']}/{st['cap_per_day']} hôm nay{warn}")
    except Exception as e:
        _sched_logger.warning("digest budget status error: %s", e)

    if not parts:
        return
    text = "📊 *vinhlong360 — digest quản lý*\n" + "\n".join(parts)
    try:
        import httpx
        for cid in admin_ids:
            httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                       json={"chat_id": cid, "text": text, "parse_mode": "Markdown"}, timeout=15)
        _sched_logger.info("Admin digest sent to %d chat(s)", len(admin_ids))
    except Exception as e:
        _sched_logger.error("digest send error: %s", e)


def _send_telegram_admins(text: str) -> bool:
    """Gửi 1 tin Telegram tới mọi ADMIN_TELEGRAM_IDS (free, HTTP API)."""
    import os
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    ids = [x.strip() for x in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(",") if x.strip()]
    if not token or not ids:
        return False
    sent = False
    try:
        import httpx
        for cid in ids:
            httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                       json={"chat_id": cid, "text": text, "parse_mode": "Markdown"}, timeout=15)
            sent = True
    except Exception as e:
        _sched_logger.error("telegram send error: %s", e)
    return sent


def task_autonomous_agent():
    """Agent TỰ ĐỘNG gọi LLM — NGOẠI LỆ CÓ-KIỂM-SOÁT của §B8 (chủ dự án duyệt):
    OFF mặc định; mỗi lần chạy tốn TỐI ĐA 1 lần gọi LLM (đã trừ cap cứng/ngày), gửi gợi
    ý quản trị cho admin qua Telegram. Bỏ qua nếu tắt hoặc hết cap (kiểm soát chi phí)."""
    import autonomous_budget as ab
    if not ab.enabled():
        return  # kill-switch: AUTONOMOUS_AGENT_ENABLED=false (mặc định)
    if not ab.try_consume(1):
        _sched_logger.warning("autonomous-agent: hết cap LLM/ngày → bỏ qua (kiểm soát chi phí)")
        return

    ctx = []
    try:
        import knowledge
        s = knowledge.stats()
        ctx.append(f"- Nội dung: {s.get('total_content', 0)}, lịch trình: {s.get('itineraries', 0)}")
    except Exception as e:
        _sched_logger.debug("autonomous-agent context: knowledge stats unavailable: %s", e)
    try:
        from database import db
        ph = db._ph
        with db._conn() as conn:
            lc = db._fetchone(conn, f"SELECT COUNT(*) AS c FROM entities WHERE type != {ph} AND confidence < 0.7", ("place",))
            ctx.append(f"- Cần xem lại (confidence < 0.7): {lc['c'] if lc else 0}")
    except Exception as e:
        _sched_logger.debug("autonomous-agent context: low-confidence count unavailable: %s", e)
    try:
        rf = AGENT_DIR / "data" / "reports.jsonl"
        n = sum(1 for ln in rf.read_text(encoding="utf-8").splitlines() if ln.strip()) if rf.exists() else 0
        ctx.append(f"- Báo cáo sai thông tin: {n}")
    except Exception as e:
        _sched_logger.debug("autonomous-agent context: reports read error: %s", e)
    raw = "\n".join(ctx) or "(không có dữ liệu)"

    try:
        from llm_config import get_client, get_model_mini
        resp = get_client().chat.completions.create(
            model=get_model_mini(), temperature=0.3, max_tokens=400, timeout=20,  # P1-2: tránh treo scheduler
            messages=[
                {"role": "system", "content": "Bạn là trợ lý quản trị vinhlong360. Đề xuất TỐI ĐA 3 việc ưu tiên xử lý, ngắn gọn, tiếng Việt, có thứ tự."},
                {"role": "user", "content": f"Tình hình hiện tại:\n{raw}\n\nĐề xuất việc ưu tiên:"},
            ])
        suggestion = resp.choices[0].message.content
    except Exception as e:
        _sched_logger.error("autonomous-agent LLM error: %s", e)
        return  # LLM lỗi → không gửi (cap đã trừ; lần sau thử lại)

    st = ab.status()
    _send_telegram_admins(f"🤖 *Agent quản trị* (LLM dùng {st['used_today']}/{st['cap_per_day']} hôm nay)\n{suggestion}")
    _sched_logger.info("autonomous-agent: đã gửi gợi ý quản trị")


# ══════════════════════════════════════════════════
#  SCHEDULER ENGINE
# ══════════════════════════════════════════════════

# ── Level 6-7 scheduled tasks ──

# GĐ6/11: task_graph_snapshot (advanced_graph) + task_knowledge_evolution (knowledge_evolution)
# đã gỡ — module bị xoá (dead-weight), task vốn disabled (AUTONOMOUS_TASKS_ENABLED=false).


def task_cache_warmup():
    """Warm semantic cache with popular and seasonal queries."""
    try:
        from semantic_cache import cache_warmer, multi_tier_cache
        month = datetime.now(_VN_TZ).month
        seasonal = cache_warmer.get_seasonal_queries(month)
        _sched_logger.info("Cache warmup: %d seasonal queries for month %d", len(seasonal), month)
    except Exception as e:
        _sched_logger.error("Cache warmup error: %s", e)


def task_agent_evolution():
    """Evaluate dynamic agents — deactivate underperformers."""
    try:
        from dynamic_agents import agent_evolution, agent_factory
        results = agent_evolution.evaluate_agents()
        active = len(agent_factory.get_active_agents())
        _sched_logger.info("Agent evolution: %d active agents, %d evaluated", active, len(results))
    except Exception as e:
        _sched_logger.error("Agent evolution error: %s", e)


def task_optimizer_check():
    """Auto-optimize prompts: propose AND ACTIVATE a variant (champion/challenger).

    Trước đây chỉ propose mà không bao giờ activate → variant chết. Nay: nếu
    variant mới giải quyết deficiency đo được (có rules_applied), kích hoạt nó
    làm challenger. Variant chỉ là prompt addon bổ trợ (vd: "dùng compare_areas
    khi so sánh") nên an toàn; có rollback() nếu chất lượng tụt.
    """
    try:
        from self_optimizer import prompt_optimizer, performance_collector, should_optimize
        if not should_optimize():
            _sched_logger.debug("Optimizer: not enough data yet")
            return
        stats = performance_collector.get_stats()

        # Champion/challenger rollback guard: if the currently-active variant has
        # underperformed its creation baseline, revert before proposing a new one.
        try:
            active = prompt_optimizer.get_current_variant()
            if active.get("id") != "default":
                baseline = active.get("score_at_creation", 0)
                current = stats.get("avg_score", 0)
                if baseline and current and current < baseline - 0.5:
                    prompt_optimizer.rollback()
                    _sched_logger.info(
                        "Optimizer rolled back variant %s (avg_score %.2f < baseline %.2f)",
                        active['id'], current, baseline
                    )
        except Exception as e:
            _sched_logger.warning("Optimizer rollback check failed: %s", e)

        variant = prompt_optimizer.propose_variant(stats)
        if not variant:
            _sched_logger.info("Optimizer: no new variant proposed")
            return
        # Only activate variants that address a measured deficiency.
        if variant.get("rules_applied"):
            activated = prompt_optimizer.activate_variant(variant["id"])
            _sched_logger.info(
                "Optimizer activated variant %s (rules=%s, activated=%s)",
                variant['id'], variant['rules_applied'], activated
            )
        else:
            _sched_logger.info("Optimizer proposed %s (no rules → not activated)", variant['id'])

        # Recompile few-shot demonstrations from the latest high-quality pool.
        try:
            import prompt_compiler
            res = prompt_compiler.compile()
            _sched_logger.info("Few-shot demos compiled: %s", res)
        except Exception as e:
            _sched_logger.debug("Prompt compiler unavailable: %s", e)
    except Exception as e:
        _sched_logger.error("Optimizer error: %s", e)


def task_guardrails_cleanup():
    """Cleanup expired guardrail session budgets."""
    try:
        from guardrails import budget_manager as gb
        gb.cleanup()
        _sched_logger.info("Guardrails budget cleanup done")
    except Exception as e:
        _sched_logger.error("Guardrails cleanup error: %s", e)


def task_learning_loop():
    """Chạy vòng lặp tự học SAU cổng fitness (eval-gated, auto-rollback)."""
    try:
        from self_evolve import guarded_evolve
        from learn_loop import run_full_cycle
        summary = guarded_evolve("learning-loop", lambda: run_full_cycle(dry_run=False))
        _sched_logger.info(
            "Learning loop: decision=%s reason=%s", summary['decision'], summary['reason']
        )
    except Exception as e:
        _sched_logger.error("Learning loop error: %s\n%s", e, traceback.format_exc())


def task_continuous_discovery():
    """Tự học liên tục, đa luồng: mỗi chu kỳ quét 1 chủ đề (xoay vòng du lịch →
    nông sản → OCOP) trên cả 3 vùng song song, geocode qua OSM, thêm provisional.
    Bọc trong guarded_evolve (eval-gated, auto-rollback nếu hại KB).

    NHỊP THÍCH NGHI ("học nhanh nhất có thể" một cách an toàn): vòng nào học
    được nhiều (≥5 entity mới) → rút ngắn chu kỳ kế (tối thiểu 30 phút);
    vòng khô (0 mới = bão hoà hoặc API lỗi) → giãn ra (tối đa 6h). Tránh dồn
    tải 9router vô ích khi không còn gì mới để học.
    """
    try:
        from self_evolve import guarded_evolve
        import discover_province as dp
        summary = guarded_evolve(
            "continuous-discovery",
            lambda: dp.run_next_rotation(workers=4, apply=True),
        )
        _sched_logger.info("Continuous discovery: decision=%s reason=%s", summary['decision'], summary['reason'])

        # Adaptive pacing dựa trên năng suất vòng vừa rồi
        res = summary.get("change_result")
        added = res.get("added", 0) if isinstance(res, dict) else 0
        task = _get_task("continuous-discovery")
        if task:
            if summary.get("decision") == "kept" and added >= 5:
                task.interval = max(DISCOVERY_MIN_INTERVAL, int(task.interval * 0.5))
            elif added == 0:
                task.interval = min(DISCOVERY_MAX_INTERVAL, int(task.interval * 1.5))
            _sched_logger.info(
                "Discovery adaptive: +%d entities → next round in %d min",
                added, round(task.interval / 60)
            )
    except Exception as e:
        _sched_logger.error("Continuous discovery error: %s\n%s", e, traceback.format_exc())


def task_kb_promotion():
    """Tự động thăng hạng entity provisional ĐÃ chứng tỏ hữu ích, SAU cổng fitness.

    Hiện thực mô hình 'eval-gated autonomous': tri thức tự học sống sót qua sử
    dụng thực tế (được truy vấn nhiều) sẽ được promote lên verified — nhưng cả
    lô promote bị rollback nếu làm tụt fitness.
    """
    try:
        from self_evolve import guarded_evolve
        import kb_curation
        summary = guarded_evolve("kb-promotion", lambda: kb_curation.auto_promote_pass(min_hits=3))
        _sched_logger.info("KB promotion: decision=%s reason=%s", summary['decision'], summary['reason'])
    except Exception as e:
        _sched_logger.error("KB promotion error: %s\n%s", e, traceback.format_exc())


def task_notification_cleanup():
    """Prune notifications older than 90 days and read notifications older than 30 days."""
    try:
        import database as db
        if not db._use_pg:
            return
        with db._conn() as conn:
            db._execute(conn, "DELETE FROM notifications WHERE created_at < NOW() - INTERVAL '90 days'", ())
            db._execute(conn, "DELETE FROM notifications WHERE is_read = TRUE AND created_at < NOW() - INTERVAL '30 days'", ())
        _sched_logger.info("Notification cleanup: pruned old notifications")
    except Exception as e:
        _sched_logger.error("Notification cleanup error: %s", e)


def task_session_cleanup():
    """Purge expired user_sessions, otp_sessions, and sessions of deleted users."""
    try:
        import database as db
        if not db._use_pg:
            return
        with db._conn() as conn:
            db._execute(conn, "DELETE FROM user_sessions WHERE expires_at < NOW()", ())
            db._execute(conn, "DELETE FROM otp_sessions WHERE expires_at < NOW()", ())
            db._execute(conn, """
                DELETE FROM user_sessions WHERE user_id IN (
                    SELECT id FROM users WHERE deleted_at IS NOT NULL
                    AND deleted_at < NOW() - INTERVAL '30 days'
                )
            """, ())
            result = db._execute(conn, """
                DELETE FROM users WHERE deleted_at IS NOT NULL
                AND deleted_at < NOW() - INTERVAL '30 days'
            """, ())
            hard_deleted = getattr(result, 'rowcount', 0)
            if hard_deleted and hard_deleted > 0:
                _sched_logger.info("Session cleanup: hard-deleted %d accounts past grace period", hard_deleted)
        _sched_logger.info("Session cleanup: purged expired sessions and OTPs")
    except Exception as e:
        _sched_logger.error("Session cleanup error: %s", e)


def task_moderation_auto_escalation():
    """Auto-approve pending posts older than 48h (solo admin can't review everything)."""
    try:
        import database as db
        if not db._use_pg:
            return
        with db._conn() as conn:
            result = db._execute(conn, """
                UPDATE posts SET moderation_status = 'approved'
                WHERE moderation_status = 'pending'
                AND created_at < NOW() - INTERVAL '48 hours'
            """, ())
            rowcount = getattr(result, 'rowcount', 0)
            if rowcount and rowcount > 0:
                _sched_logger.info("Moderation auto-escalation: approved %d stale pending posts", rowcount)
    except Exception as e:
        _sched_logger.error("Moderation auto-escalation error: %s", e)


def task_ratelimit_gc():
    """Periodic GC for all in-memory rate-limit dicts to prevent memory leaks."""
    try:
        from ratelimit import gc_all
        result = gc_all()
        if result["freed"] > 0:
            _sched_logger.info("Rate-limit GC: freed %d keys (%d→%d)", result["freed"], result["before"], result["after"])
    except Exception as e:
        _sched_logger.error("Rate-limit GC error: %s", e)


TASKS = [
    ScheduledTask("auto-learn",     task_auto_learn,            interval_seconds=AUTO_LEARN_INTERVAL, enabled=AUTONOMOUS_TASKS_ENABLED, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),   # 3h (env)
    ScheduledTask("relationships",  task_relationship_discovery, interval_seconds=12 * 3600, enabled=AUTONOMOUS_TASKS_ENABLED, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),  # 12h
    ScheduledTask("data-sync",      task_sync_data,              interval_seconds=3600),        # 1h
    ScheduledTask("analytics-cleanup", task_cleanup_analytics,   interval_seconds=24 * 3600, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),  # 24h
    # Digest quản lý MIỄN PHÍ (không LLM) — chạy bất kể AUTONOMOUS_TASKS_ENABLED; no-op nếu chưa cấu hình admin TG.
    ScheduledTask("admin-digest",      task_admin_digest,         interval_seconds=24 * 3600, run_immediately=False),  # 24h
    # Agent tự động gọi LLM CÓ CAP (§B8 ngoại lệ kiểm soát) — task tự gate qua AUTONOMOUS_AGENT_ENABLED
    # (off mặc định) + cap cứng/ngày. Đăng ký enabled=True nhưng no-op khi flag off.
    ScheduledTask("autonomous-agent",  task_autonomous_agent,     interval_seconds=24 * 3600, run_immediately=False),  # 24h, capped
    # Level 6-7 tasks
    ScheduledTask("cache-warmup",      task_cache_warmup,         interval_seconds=3600, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),        # 1h
    ScheduledTask("agent-evolution",   task_agent_evolution,      interval_seconds=12 * 3600, enabled=AUTONOMOUS_TASKS_ENABLED, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),  # 12h
    ScheduledTask("optimizer-check",   task_optimizer_check,      interval_seconds=6 * 3600, enabled=AUTONOMOUS_TASKS_ENABLED, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),   # 6h
    ScheduledTask("guardrails-cleanup",task_guardrails_cleanup,   interval_seconds=12 * 3600, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),  # 12h
    ScheduledTask("session-cleanup", task_session_cleanup,       interval_seconds=6 * 3600, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),  # 6h
    ScheduledTask("notification-cleanup", task_notification_cleanup, interval_seconds=24 * 3600, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),  # 24h
    ScheduledTask("ratelimit-gc",  task_ratelimit_gc,          interval_seconds=300),        # 5min
    ScheduledTask("moderation-escalation", task_moderation_auto_escalation, interval_seconds=6 * 3600, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),  # 6h
    ScheduledTask("learning-loop",    task_learning_loop,         interval_seconds=LEARNING_LOOP_INTERVAL, enabled=AUTONOMOUS_TASKS_ENABLED, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),   # 1h (env)
    ScheduledTask("kb-promotion",     task_kb_promotion,          interval_seconds=PROMOTION_INTERVAL, enabled=AUTONOMOUS_TASKS_ENABLED, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),  # 6h (env)
    ScheduledTask("continuous-discovery", task_continuous_discovery, interval_seconds=DISCOVERY_INTERVAL, enabled=AUTONOMOUS_TASKS_ENABLED, run_immediately=SCHEDULER_RUN_STARTUP_TASKS),  # 1h adaptive 30m–6h (env)
]

_scheduler_thread = None
_running = False


def _scheduler_loop():
    global _running
    _sched_logger.info("Background scheduler started")

    while _running:
        for task in TASKS:
            if task.should_run():
                task.run()
        time.sleep(60)  # Check every minute


def start_scheduler():
    """Start the background scheduler (call from server startup)."""
    global _scheduler_thread, _running

    if not SCHEDULER_ENABLED:
        _sched_logger.info("Background scheduler disabled by SCHEDULER_ENABLED")
        return

    if _scheduler_thread and _scheduler_thread.is_alive():
        return

    _running = True
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="scheduler")
    _scheduler_thread.start()
    _sched_logger.info("Background scheduler thread started")


def stop_scheduler():
    global _running
    _running = False
    _sched_logger.info("Scheduler stopped")


def _autonomous_agent_status() -> dict:
    try:
        import autonomous_budget as ab
        return ab.status()
    except Exception as e:
        _sched_logger.debug("autonomous_budget import failed: %s", e)
        return {"enabled": False}


def scheduler_status() -> dict:
    return {
        "running": _running,
        "enabled": SCHEDULER_ENABLED,
        "run_startup_tasks": SCHEDULER_RUN_STARTUP_TASKS,
        "autonomous_tasks_enabled": AUTONOMOUS_TASKS_ENABLED,
        "autonomous_agent": _autonomous_agent_status(),
        "tasks": [
            {
                "name": t.name,
                "enabled": t.enabled,
                "interval_hours": round(t.interval / 3600, 1),
                "last_run": datetime.fromtimestamp(t.last_run).isoformat() if t.last_run else None,
                "next_run_after": datetime.fromtimestamp(t.next_run_after).isoformat() if t.next_run_after else None,
                "run_count": t.run_count,
                "last_error": t.last_error,
            }
            for t in TASKS
        ],
    }


# ── CLI ──

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="vinhlong360 Task Scheduler")
    parser.add_argument("--once", action="store_true", help="Run all tasks once then exit")
    parser.add_argument("--task", type=str, help="Run a specific task once")
    parser.add_argument("--sync", action="store_true", help="Just sync data.json → data.js")
    args = parser.parse_args()

    print("=" * 50)
    print("vinhlong360 — Task Scheduler")
    print("=" * 50)

    if args.sync:
        sync_data_json_to_js()
    elif args.task:
        task_map = {t.name: t for t in TASKS}
        if args.task in task_map:
            task_map[args.task].run()
        else:
            print(f"  Unknown task: {args.task}")
            print(f"  Available: {list(task_map.keys())}")
    elif args.once:
        for task in TASKS:
            task.run()
    else:
        _running = True
        try:
            _scheduler_loop()
        except KeyboardInterrupt:
            print("\n  Scheduler stopped")

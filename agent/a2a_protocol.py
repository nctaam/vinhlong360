"""
vinhlong360 — Google Agent-to-Agent (A2A) Protocol Implementation.

Implements the Google A2A standard for inter-agent communication, enabling
the vinhlong360 Knowledge Agent to participate in multi-agent ecosystems.

Components:
    AgentCard     -> JSON-LD agent descriptor for /.well-known/agent.json
    AgentSkill    -> describes a single capability with I/O schemas
    TaskState     -> lifecycle enum (SUBMITTED -> WORKING -> COMPLETED/FAILED)
    A2ATask       -> a single task with input/output messages
    TaskManager   -> thread-safe task store with FIFO eviction
    A2AServer     -> JSON-RPC 2.0 request router
    A2AClient     -> HTTP client for discovering and calling remote agents

Thread-safe: all mutable state is guarded by threading.Lock.
Pure stdlib: no external dependencies (json, uuid, time, threading, http.client).
"""

from __future__ import annotations

import http.client
import json
import logging
import threading
import time
import urllib.parse
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_TASKS = 1000
_DEFAULT_TIMEOUT = 30  # seconds
_DEFAULT_BASE_URL = "http://localhost:8360"
_AGENT_VERSION = "7.5"

# JSON-RPC 2.0 error codes
_ERR_INVALID_REQUEST = -32600
_ERR_METHOD_NOT_FOUND = -32601
_ERR_INVALID_PARAMS = -32602


# ---------------------------------------------------------------------------
# AgentSkill dataclass
# ---------------------------------------------------------------------------

@dataclass
class AgentSkill:
    """A single skill/capability that the agent can perform."""

    id: str
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    examples: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "examples": self.examples,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentSkill:
        """Deserialize from a plain dict."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            examples=data.get("examples", []),
        )


# ---------------------------------------------------------------------------
# DEFAULT_SKILLS
# ---------------------------------------------------------------------------

_TEXT_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "User query in Vietnamese or English"},
    },
    "required": ["query"],
}

_TEXT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string", "description": "Agent response text"},
        "sources": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Source references",
        },
    },
    "required": ["response"],
}

DEFAULT_SKILLS: list[AgentSkill] = [
    AgentSkill(
        id="tourism-search",
        name="Tourism Search",
        description="Search for tourist attractions, restaurants, accommodations in Vinh Long",
        input_schema=_TEXT_INPUT_SCHEMA,
        output_schema=_TEXT_OUTPUT_SCHEMA,
        examples=[
            {"input": {"query": "Chợ nổi Cái Bè ở đâu?"}, "output": {"response": "Chợ nổi Cái Bè nằm tại..."}},
            {"input": {"query": "Best homestays in Vinh Long"}, "output": {"response": "Top homestays include..."}},
        ],
    ),
    AgentSkill(
        id="itinerary-planning",
        name="Itinerary Planning",
        description="Generate multi-day travel itineraries",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Itinerary request"},
                "days": {"type": "integer", "description": "Number of days", "default": 2},
            },
            "required": ["query"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "itinerary": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "day": {"type": "integer"},
                            "activities": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
            "required": ["response"],
        },
        examples=[
            {"input": {"query": "Lịch trình 2 ngày Vĩnh Long", "days": 2}},
        ],
    ),
    AgentSkill(
        id="area-comparison",
        name="Area Comparison",
        description="Compare different areas/districts for tourism",
        input_schema=_TEXT_INPUT_SCHEMA,
        output_schema=_TEXT_OUTPUT_SCHEMA,
        examples=[
            {"input": {"query": "So sánh Cái Bè và Long Hồ"}},
        ],
    ),
    AgentSkill(
        id="seasonal-guide",
        name="Seasonal Guide",
        description="Seasonal recommendations based on time of year",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "month": {"type": "integer", "description": "Month number (1-12)"},
            },
            "required": ["query"],
        },
        output_schema=_TEXT_OUTPUT_SCHEMA,
        examples=[
            {"input": {"query": "Tháng 12 nên đi đâu ở Vĩnh Long?", "month": 12}},
        ],
    ),
    AgentSkill(
        id="food-guide",
        name="Food Guide",
        description="Local cuisine and specialty food recommendations",
        input_schema=_TEXT_INPUT_SCHEMA,
        output_schema=_TEXT_OUTPUT_SCHEMA,
        examples=[
            {"input": {"query": "Đặc sản Vĩnh Long"}},
            {"input": {"query": "Best banh mi in Vinh Long"}},
        ],
    ),
]


# ---------------------------------------------------------------------------
# AgentCard dataclass
# ---------------------------------------------------------------------------

@dataclass
class AgentCard:
    """Agent descriptor following the Google A2A AgentCard specification.

    Exposes agent metadata for discovery via /.well-known/agent.json.
    """

    name: str = "vinhlong360-knowledge-agent"
    description: str = "Vietnamese tourism Knowledge Agent for Vinh Long province"
    url: str = _DEFAULT_BASE_URL
    version: str = _AGENT_VERSION
    capabilities: list[str] = field(default_factory=lambda: [
        "tourism-search",
        "itinerary-planning",
        "area-comparison",
        "seasonal-recommendations",
        "food-guide",
    ])
    skills: list[AgentSkill] = field(default_factory=lambda: list(DEFAULT_SKILLS))
    input_modes: list[str] = field(default_factory=lambda: ["text"])
    output_modes: list[str] = field(default_factory=lambda: ["text", "markdown"])

    def to_dict(self) -> dict:
        """Serialize to JSON-LD compatible format."""
        return {
            "@context": "https://schema.org",
            "@type": "SoftwareAgent",
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": list(self.capabilities),
            "skills": [s.to_dict() for s in self.skills],
            "inputModes": list(self.input_modes),
            "outputModes": list(self.output_modes),
            "protocol": "a2a",
            "protocolVersion": "0.1",
        }

    def to_well_known(self) -> dict:
        """Format for /.well-known/agent.json endpoint."""
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": list(self.capabilities),
            "skills": [s.to_dict() for s in self.skills],
            "inputModes": list(self.input_modes),
            "outputModes": list(self.output_modes),
            "protocol": "a2a",
            "protocolVersion": "0.1",
            "endpoints": {
                "agentCard": f"{self.url}/.well-known/agent.json",
                "tasksSend": f"{self.url}/a2a",
                "tasksGet": f"{self.url}/a2a",
                "tasksCancel": f"{self.url}/a2a",
            },
        }


# ---------------------------------------------------------------------------
# TaskState enum
# ---------------------------------------------------------------------------

class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


# ---------------------------------------------------------------------------
# A2ATask dataclass
# ---------------------------------------------------------------------------

@dataclass
class A2ATask:
    """A single A2A task with input/output messages and lifecycle state."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    state: TaskState = TaskState.SUBMITTED
    input_message: dict = field(default_factory=dict)
    output_messages: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return {
            "id": self.id,
            "sessionId": self.session_id,
            "state": self.state.value,
            "inputMessage": self.input_message,
            "outputMessages": list(self.output_messages),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> A2ATask:
        """Deserialize from a plain dict."""
        return cls(
            id=data["id"],
            session_id=data.get("sessionId", ""),
            state=TaskState(data["state"]),
            input_message=data.get("inputMessage", {}),
            output_messages=data.get("outputMessages", []),
            created_at=data.get("createdAt", time.time()),
            updated_at=data.get("updatedAt", time.time()),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# TaskManager -- thread-safe task store with FIFO eviction
# ---------------------------------------------------------------------------

class TaskManager:
    """Thread-safe task store with bounded capacity.

    At most ``_MAX_TASKS`` tasks are kept in memory.  When the limit is
    reached, the oldest tasks (by creation time) are evicted first.
    """

    def __init__(self, max_tasks: int = _MAX_TASKS) -> None:
        self._tasks: dict[str, A2ATask] = {}
        self._order: list[str] = []  # insertion order for FIFO eviction
        self._max_tasks = max_tasks
        self._lock = threading.Lock()

    def create_task(
        self,
        input_message: dict,
        session_id: Optional[str] = None,
    ) -> A2ATask:
        """Create a new task from an input message.

        Parameters
        ----------
        input_message : dict
            The message that initiated the task (e.g. {"role": "user", "content": "..."}).
        session_id : str, optional
            Session identifier.  Auto-generated if not provided.

        Returns
        -------
        A2ATask
        """
        now = time.time()
        task = A2ATask(
            session_id=session_id or str(uuid.uuid4()),
            state=TaskState.SUBMITTED,
            input_message=input_message,
            created_at=now,
            updated_at=now,
        )

        with self._lock:
            self._evict_if_full()
            self._tasks[task.id] = task
            self._order.append(task.id)

        logger.debug("TaskManager: created task %s (session=%s)", task.id, task.session_id)
        return task

    def get_task(self, task_id: str) -> Optional[A2ATask]:
        """Return a task by id, or None if not found."""
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        state: TaskState,
        output: Optional[dict] = None,
    ) -> None:
        """Update a task's state and optionally append an output message.

        Raises
        ------
        KeyError
            If task_id is not found.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"Task {task_id} not found")
            task.state = state
            task.updated_at = time.time()
            if output is not None:
                task.output_messages.append(output)

        logger.debug("TaskManager: updated task %s -> %s", task_id, state.value)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.  Returns True if canceled, False if not found or already terminal."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED):
                return False
            task.state = TaskState.CANCELED
            task.updated_at = time.time()

        logger.debug("TaskManager: canceled task %s", task_id)
        return True

    def list_tasks(
        self,
        session_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> list[A2ATask]:
        """List tasks, optionally filtered by session_id and/or state.

        Parameters
        ----------
        session_id : str, optional
            Filter by session.
        state : str, optional
            Filter by state value (e.g. "completed").

        Returns
        -------
        list[A2ATask]
        """
        with self._lock:
            tasks = list(self._tasks.values())

        if session_id is not None:
            tasks = [t for t in tasks if t.session_id == session_id]
        if state is not None:
            tasks = [t for t in tasks if t.state.value == state]

        return tasks

    def cleanup(self, max_age_hours: int = 24) -> int:
        """Remove tasks older than *max_age_hours*.

        Returns
        -------
        int
            Number of tasks removed.
        """
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0

        with self._lock:
            expired_ids = [
                tid for tid, task in self._tasks.items()
                if task.created_at < cutoff
            ]
            for tid in expired_ids:
                del self._tasks[tid]
                removed += 1
            self._order = [tid for tid in self._order if tid in self._tasks]

        if removed:
            logger.info("TaskManager: cleaned up %d expired tasks", removed)
        return removed

    def _evict_if_full(self) -> None:
        """Evict oldest tasks if at capacity (must hold lock)."""
        while len(self._tasks) >= self._max_tasks and self._order:
            oldest_id = self._order.pop(0)
            self._tasks.pop(oldest_id, None)
            logger.debug("TaskManager: evicted task %s (FIFO)", oldest_id)

    def stats(self) -> dict:
        """Return summary statistics."""
        with self._lock:
            by_state: dict[str, int] = {}
            for task in self._tasks.values():
                sv = task.state.value
                by_state[sv] = by_state.get(sv, 0) + 1
            return {
                "total": len(self._tasks),
                "by_state": by_state,
                "max_tasks": self._max_tasks,
            }


# ---------------------------------------------------------------------------
# A2AServer -- JSON-RPC 2.0 request router
# ---------------------------------------------------------------------------

class A2AServer:
    """Route incoming A2A JSON-RPC requests to the appropriate handler.

    Supported methods:
        tasks/send          -> create + execute a task
        tasks/get           -> retrieve task status / result
        tasks/cancel        -> cancel a running task
        tasks/sendSubscribe -> create task with SSE (stub)
    """

    def __init__(
        self,
        card: Optional[AgentCard] = None,
        manager: Optional[TaskManager] = None,
        task_handler: Optional[Any] = None,
    ) -> None:
        self._card = card
        self._manager = manager
        self._task_handler = task_handler  # callable(input_message) -> output_message
        self._lock = threading.Lock()
        self._request_count = 0

    @property
    def card(self) -> AgentCard:
        if self._card is None:
            self._card = agent_card
        return self._card

    @property
    def manager(self) -> TaskManager:
        if self._manager is None:
            self._manager = task_manager
        return self._manager

    def handle_request(self, method: str, path: str, body: dict) -> dict:
        """Route an A2A JSON-RPC request and return a JSON-RPC response.

        Parameters
        ----------
        method : str
            HTTP method (e.g. "POST", "GET").
        path : str
            Request path (e.g. "/a2a", "/.well-known/agent.json").
        body : dict
            Parsed JSON body (for POST requests).

        Returns
        -------
        dict
            JSON-RPC 2.0 response.
        """
        with self._lock:
            self._request_count += 1

        # Well-known agent card endpoint
        if path.rstrip("/") in ("/.well-known/agent.json", "/.well-known/agent"):
            return self.card.to_well_known()

        # JSON-RPC dispatch
        if not isinstance(body, dict):
            return self._error_response(None, _ERR_INVALID_REQUEST, "Invalid request body")

        jsonrpc = body.get("jsonrpc")
        if jsonrpc != "2.0":
            return self._error_response(
                body.get("id"), _ERR_INVALID_REQUEST,
                f"Expected jsonrpc 2.0, got {jsonrpc!r}",
            )

        rpc_method = body.get("method", "")
        rpc_id = body.get("id")
        params = body.get("params", {})

        dispatch = {
            "tasks/send": self._handle_tasks_send,
            "tasks/get": self._handle_tasks_get,
            "tasks/cancel": self._handle_tasks_cancel,
            "tasks/sendSubscribe": self._handle_tasks_send_subscribe,
        }

        handler = dispatch.get(rpc_method)
        if handler is None:
            return self._error_response(
                rpc_id, _ERR_METHOD_NOT_FOUND,
                f"Unknown method: {rpc_method}",
            )

        try:
            result = handler(params)
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": result,
            }
        except ValueError as exc:
            return self._error_response(rpc_id, _ERR_INVALID_PARAMS, str(exc))
        except Exception as exc:
            logger.error("A2AServer: error handling %s: %s", rpc_method, exc, exc_info=True)
            return self._error_response(rpc_id, _ERR_INVALID_REQUEST, str(exc))

    # -- RPC handlers -------------------------------------------------------

    def _handle_tasks_send(self, params: dict) -> dict:
        """Handle tasks/send: create and execute a task."""
        message = params.get("message")
        if not message:
            raise ValueError("Missing 'message' in params")

        session_id = params.get("sessionId")
        task = self.manager.create_task(
            input_message=message,
            session_id=session_id,
        )

        # Execute the task
        self.manager.update_task(task.id, TaskState.WORKING)

        try:
            if self._task_handler is not None:
                output = self._task_handler(message)
                if isinstance(output, str):
                    output = {"role": "agent", "content": output}
            else:
                # Default handler: echo back a stub response
                content = message.get("content", "") if isinstance(message, dict) else str(message)
                output = {
                    "role": "agent",
                    "content": f"[vinhlong360] Received: {content[:200]}",
                }

            self.manager.update_task(task.id, TaskState.COMPLETED, output)
        except Exception as exc:
            logger.error("Task %s execution failed: %s", task.id, exc, exc_info=True)
            error_output = {
                "role": "agent",
                "content": f"Task failed: {exc}",
            }
            self.manager.update_task(task.id, TaskState.FAILED, error_output)

        return self.manager.get_task(task.id).to_dict()

    def _handle_tasks_get(self, params: dict) -> dict:
        """Handle tasks/get: return task status."""
        task_id = params.get("taskId") or params.get("id")
        if not task_id:
            raise ValueError("Missing 'taskId' in params")

        task = self.manager.get_task(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        return task.to_dict()

    def _handle_tasks_cancel(self, params: dict) -> dict:
        """Handle tasks/cancel: cancel a running task."""
        task_id = params.get("taskId") or params.get("id")
        if not task_id:
            raise ValueError("Missing 'taskId' in params")

        canceled = self.manager.cancel_task(task_id)
        if not canceled:
            task = self.manager.get_task(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")
            return task.to_dict()

        return self.manager.get_task(task_id).to_dict()

    def _handle_tasks_send_subscribe(self, params: dict) -> dict:
        """Handle tasks/sendSubscribe: create task with SSE streaming (stub).

        Returns the task with updates inline since true SSE requires
        an HTTP streaming transport layer.
        """
        message = params.get("message")
        if not message:
            raise ValueError("Missing 'message' in params")

        session_id = params.get("sessionId")
        task = self.manager.create_task(
            input_message=message,
            session_id=session_id,
        )

        # Execute synchronously and return final state
        self.manager.update_task(task.id, TaskState.WORKING)

        try:
            if self._task_handler is not None:
                output = self._task_handler(message)
                if isinstance(output, str):
                    output = {"role": "agent", "content": output}
            else:
                content = message.get("content", "") if isinstance(message, dict) else str(message)
                output = {
                    "role": "agent",
                    "content": f"[vinhlong360] Received: {content[:200]}",
                }

            self.manager.update_task(task.id, TaskState.COMPLETED, output)
        except Exception as exc:
            logger.error("Task %s (subscribe) failed: %s", task.id, exc, exc_info=True)
            error_output = {"role": "agent", "content": f"Task failed: {exc}"}
            self.manager.update_task(task.id, TaskState.FAILED, error_output)

        result_task = self.manager.get_task(task.id)
        return {
            "task": result_task.to_dict(),
            "updates": [
                {"state": TaskState.WORKING.value, "timestamp": result_task.created_at},
                {"state": result_task.state.value, "timestamp": result_task.updated_at},
            ],
        }

    # -- Helpers ------------------------------------------------------------

    @staticmethod
    def _error_response(rpc_id: Any, code: int, message: str) -> dict:
        """Build a JSON-RPC 2.0 error response."""
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    def stats(self) -> dict:
        """Return server statistics."""
        with self._lock:
            return {
                "request_count": self._request_count,
                "tasks": self.manager.stats(),
            }


# ---------------------------------------------------------------------------
# A2AClient -- HTTP client for discovering and calling remote agents
# ---------------------------------------------------------------------------

class A2AClient:
    """HTTP client for A2A protocol communication with remote agents.

    Uses http.client from stdlib (no external dependencies).
    All requests have a 30-second timeout by default.
    """

    def __init__(self, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    def discover(self, url: str) -> AgentCard:
        """Discover a remote agent by fetching its /.well-known/agent.json.

        Parameters
        ----------
        url : str
            Base URL of the remote agent (e.g. "http://agent.example.com:8000").

        Returns
        -------
        AgentCard
            Parsed agent card.

        Raises
        ------
        ConnectionError
            If the request fails.
        ValueError
            If the response is not valid JSON.
        """
        parsed = urllib.parse.urlparse(url)
        path = (parsed.path.rstrip("/") or "") + "/.well-known/agent.json"

        data = self._http_get(parsed.hostname, parsed.port, path, parsed.scheme)

        return AgentCard(
            name=data.get("name", "unknown"),
            description=data.get("description", ""),
            url=data.get("url", url),
            version=data.get("version", ""),
            capabilities=data.get("capabilities", []),
            skills=[AgentSkill.from_dict(s) for s in data.get("skills", [])],
            input_modes=data.get("inputModes", ["text"]),
            output_modes=data.get("outputModes", ["text"]),
        )

    def send_task(self, url: str, message: str) -> dict:
        """Send a task to a remote agent via tasks/send.

        Parameters
        ----------
        url : str
            Base URL of the remote agent.
        message : str
            The user message to send.

        Returns
        -------
        dict
            JSON-RPC response (result or error).
        """
        rpc_body = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {
                "message": {
                    "role": "user",
                    "content": message,
                },
            },
            "id": str(uuid.uuid4()),
        }

        parsed = urllib.parse.urlparse(url)
        path = (parsed.path.rstrip("/") or "") + "/a2a"

        return self._http_post(parsed.hostname, parsed.port, path, parsed.scheme, rpc_body)

    def get_task_status(self, url: str, task_id: str) -> dict:
        """Check the status of a task on a remote agent.

        Parameters
        ----------
        url : str
            Base URL of the remote agent.
        task_id : str
            The task ID to check.

        Returns
        -------
        dict
            JSON-RPC response with task state.
        """
        rpc_body = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {
                "taskId": task_id,
            },
            "id": str(uuid.uuid4()),
        }

        parsed = urllib.parse.urlparse(url)
        path = (parsed.path.rstrip("/") or "") + "/a2a"

        return self._http_post(parsed.hostname, parsed.port, path, parsed.scheme, rpc_body)

    # -- HTTP helpers -------------------------------------------------------

    def _get_connection(
        self, host: str, port: Optional[int], scheme: str,
    ) -> http.client.HTTPConnection:
        """Create an HTTP(S) connection."""
        if scheme == "https":
            return http.client.HTTPSConnection(host, port or 443, timeout=self._timeout)
        return http.client.HTTPConnection(host, port or 80, timeout=self._timeout)

    def _http_get(
        self, host: str, port: Optional[int], path: str, scheme: str,
    ) -> dict:
        """Perform an HTTP GET and return parsed JSON."""
        conn = self._get_connection(host, port, scheme)
        try:
            conn.request("GET", path, headers={"Accept": "application/json"})
            resp = conn.getresponse()
            body = resp.read().decode("utf-8")

            if resp.status != 200:
                raise ConnectionError(
                    f"GET {scheme}://{host}:{port}{path} returned {resp.status}: {body[:200]}"
                )

            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON from {path}: {exc}") from exc
        finally:
            conn.close()

    def _http_post(
        self, host: str, port: Optional[int], path: str, scheme: str, body: dict,
    ) -> dict:
        """Perform an HTTP POST with JSON body and return parsed JSON."""
        conn = self._get_connection(host, port, scheme)
        payload = json.dumps(body).encode("utf-8")
        try:
            conn.request(
                "POST", path, body=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            resp = conn.getresponse()
            resp_body = resp.read().decode("utf-8")

            if resp.status not in (200, 201):
                raise ConnectionError(
                    f"POST {scheme}://{host}:{port}{path} returned {resp.status}: {resp_body[:200]}"
                )

            return json.loads(resp_body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON from {path}: {exc}") from exc
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

agent_card = AgentCard()
task_manager = TaskManager()
a2a_server = A2AServer(card=agent_card, manager=task_manager)
a2a_client = A2AClient()


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def get_agent_card() -> dict:
    """Return this agent's card as a dict."""
    return agent_card.to_dict()


def handle_a2a(method: str, path: str, body: dict) -> dict:
    """Route an incoming A2A request through the server.

    Parameters
    ----------
    method : str
        HTTP method.
    path : str
        Request path.
    body : dict
        Parsed JSON body.

    Returns
    -------
    dict
        JSON-RPC response.
    """
    return a2a_server.handle_request(method, path, body)


def get_a2a_status() -> dict:
    """Return A2A subsystem stats for health endpoint."""
    return {
        "a2a_protocol": "enabled",
        "agent": agent_card.name,
        "version": agent_card.version,
        "capabilities": list(agent_card.capabilities),
        "skills_count": len(agent_card.skills),
        "server": a2a_server.stats(),
    }


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("a2a_protocol -- unit tests")
    print("=" * 60)

    # -- AgentSkill ---------------------------------------------------------
    print("\n--- AgentSkill ---")
    skill = DEFAULT_SKILLS[0]
    d = skill.to_dict()
    print(f"  id: {d['id']}, name: {d['name']}")
    skill_rt = AgentSkill.from_dict(d)
    print(f"  round-trip OK: {skill_rt.id == skill.id}")

    # -- AgentCard ----------------------------------------------------------
    print("\n--- AgentCard ---")
    card = AgentCard()
    card_dict = card.to_dict()
    print(f"  @type: {card_dict['@type']}")
    print(f"  name: {card_dict['name']}")
    print(f"  skills: {len(card_dict['skills'])}")
    print(f"  capabilities: {card_dict['capabilities']}")

    wk = card.to_well_known()
    print(f"  well-known endpoints: {sorted(wk['endpoints'].keys())}")

    # -- TaskState ----------------------------------------------------------
    print("\n--- TaskState ---")
    for ts in TaskState:
        print(f"  {ts.name} = {ts.value}")

    # -- A2ATask ------------------------------------------------------------
    print("\n--- A2ATask ---")
    task = A2ATask(
        session_id="sess-1",
        input_message={"role": "user", "content": "Cho toi biet ve Vinh Long"},
    )
    td = task.to_dict()
    print(f"  id: {td['id'][:8]}..., state: {td['state']}")
    task_rt = A2ATask.from_dict(td)
    print(f"  round-trip OK: {task_rt.id == task.id and task_rt.state == task.state}")

    # -- TaskManager --------------------------------------------------------
    print("\n--- TaskManager ---")
    tm = TaskManager(max_tasks=5)
    tasks_created = []
    for i in range(7):
        t = tm.create_task(
            input_message={"role": "user", "content": f"Query {i}"},
            session_id="sess-1" if i < 4 else "sess-2",
        )
        tasks_created.append(t)
    print(f"  created 7, stored: {tm.stats()['total']} (max=5)")

    t0 = tasks_created[-1]
    tm.update_task(t0.id, TaskState.WORKING)
    tm.update_task(t0.id, TaskState.COMPLETED, {"role": "agent", "content": "Done"})
    fetched = tm.get_task(t0.id)
    print(f"  task {t0.id[:8]}... state: {fetched.state.value}, outputs: {len(fetched.output_messages)}")

    sess1_tasks = tm.list_tasks(session_id="sess-1")
    print(f"  session sess-1 tasks: {len(sess1_tasks)}")

    completed = tm.list_tasks(state="completed")
    print(f"  completed tasks: {len(completed)}")

    cancel_ok = tm.cancel_task(tasks_created[-2].id)
    print(f"  cancel active: {cancel_ok}")
    cancel_fail = tm.cancel_task(t0.id)
    print(f"  cancel completed: {cancel_fail}")

    cleaned = tm.cleanup(max_age_hours=0)
    print(f"  cleanup(0h): removed {cleaned}")

    # -- A2AServer ----------------------------------------------------------
    print("\n--- A2AServer ---")
    srv = A2AServer()

    # Well-known endpoint
    wk_resp = srv.handle_request("GET", "/.well-known/agent.json", {})
    print(f"  well-known: {wk_resp.get('name', '?')}")

    # tasks/send
    send_resp = srv.handle_request("POST", "/a2a", {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "message": {"role": "user", "content": "Hello agent"},
        },
        "id": "req-1",
    })
    print(f"  tasks/send result state: {send_resp.get('result', {}).get('state', '?')}")
    task_id = send_resp.get("result", {}).get("id", "")

    # tasks/get
    get_resp = srv.handle_request("POST", "/a2a", {
        "jsonrpc": "2.0",
        "method": "tasks/get",
        "params": {"taskId": task_id},
        "id": "req-2",
    })
    print(f"  tasks/get result state: {get_resp.get('result', {}).get('state', '?')}")

    # tasks/cancel
    cancel_resp = srv.handle_request("POST", "/a2a", {
        "jsonrpc": "2.0",
        "method": "tasks/cancel",
        "params": {"taskId": task_id},
        "id": "req-3",
    })
    print(f"  tasks/cancel (already done): {cancel_resp.get('result', {}).get('state', '?')}")

    # tasks/sendSubscribe
    sub_resp = srv.handle_request("POST", "/a2a", {
        "jsonrpc": "2.0",
        "method": "tasks/sendSubscribe",
        "params": {
            "message": {"role": "user", "content": "Subscribe test"},
        },
        "id": "req-4",
    })
    sub_result = sub_resp.get("result", {})
    print(f"  tasks/sendSubscribe updates: {len(sub_result.get('updates', []))}")

    # Unknown method
    err_resp = srv.handle_request("POST", "/a2a", {
        "jsonrpc": "2.0",
        "method": "tasks/unknown",
        "params": {},
        "id": "req-5",
    })
    print(f"  unknown method error code: {err_resp.get('error', {}).get('code', '?')}")

    # Invalid request (no jsonrpc field)
    bad_resp = srv.handle_request("POST", "/a2a", {"method": "tasks/send"})
    print(f"  invalid request error code: {bad_resp.get('error', {}).get('code', '?')}")

    # Server stats
    stats = srv.stats()
    print(f"  server request_count: {stats['request_count']}")

    # -- Convenience functions ----------------------------------------------
    print("\n--- Convenience functions ---")
    ac = get_agent_card()
    print(f"  get_agent_card name: {ac['name']}")

    a2a_resp = handle_a2a("POST", "/a2a", {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {"message": {"role": "user", "content": "Test"}},
        "id": "conv-1",
    })
    print(f"  handle_a2a result: {a2a_resp.get('result', {}).get('state', '?')}")

    status = get_a2a_status()
    print(f"  get_a2a_status: protocol={status['a2a_protocol']}, skills={status['skills_count']}")

    # -- A2AClient (structure only, no live server) -------------------------
    print("\n--- A2AClient ---")
    client = A2AClient(timeout=10)
    print(f"  timeout: {client._timeout}s")
    print("  (skipping live HTTP tests -- no remote server)")

    print("\n" + "=" * 60)
    print("All a2a_protocol tests completed.")

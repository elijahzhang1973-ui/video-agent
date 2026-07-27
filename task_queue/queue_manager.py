"""JSON-backed download task queue."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse
from uuid import uuid4


TASK_STATUSES = {"pending", "running", "success", "failed"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_platform_validator() -> Callable[[str], tuple[str, str]]:
    detector_path = Path(__file__).resolve().parents[1] / "platform" / "detector.py"
    spec = importlib.util.spec_from_file_location(
        "video_agent_queue_platform_detector",
        detector_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载平台检测模块：{detector_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_platform_url


def _extract_video_id(url: str, platform_name: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]

    if platform_name == "YouTube":
        if (parsed.hostname or "").lower() == "youtu.be":
            return parts[0]
        if parsed.path.rstrip("/") == "/watch":
            return parse_qs(parsed.query)["v"][0]
        return parts[1]

    if platform_name == "X/Twitter":
        return parts[parts.index("status") + 1]

    if platform_name in {"小红书", "Bilibili", "TikTok"}:
        return parts[-1]

    raise ValueError(f"无法提取{platform_name}视频ID")


class QueueManager:
    """Persist and update download tasks in one JSON file."""

    def __init__(
        self,
        queue_path: str | Path,
        validator: Callable[[str], tuple[str, str]] | None = None,
    ) -> None:
        self.queue_path = Path(queue_path).resolve()
        self.validator = validator or _load_platform_validator()
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.queue_path.exists():
            self._write_tasks([])

    def _read_tasks(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self.queue_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"任务队列JSON格式无效：{self.queue_path}") from exc
        if not isinstance(payload, list):
            raise ValueError(f"任务队列必须是JSON数组：{self.queue_path}")
        return payload

    def _write_tasks(self, tasks: list[dict[str, Any]]) -> None:
        temporary_path = self.queue_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(tasks, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self.queue_path)

    def identify_url(self, raw_url: str) -> tuple[str, str, str]:
        """Return normalized URL, platform name, and stable video ID."""
        url, platform_name = self.validator(raw_url)
        video_id = _extract_video_id(url, platform_name)
        if not video_id:
            raise ValueError("无法从URL提取视频ID")
        return url, platform_name, video_id

    def add_task(self, raw_url: str) -> tuple[dict[str, Any], bool]:
        """Add a pending task, returning ``(task, created)``."""
        url, platform_name, video_id = self.identify_url(raw_url)
        tasks = self._read_tasks()

        for task in tasks:
            if (
                task.get("platform") == platform_name
                and task.get("video_id") == video_id
                and task.get("status") in {"pending", "running"}
            ):
                return dict(task), False

        timestamp = _utc_now()
        task: dict[str, Any] = {
            "id": uuid4().hex,
            "url": url,
            "platform": platform_name,
            "video_id": video_id,
            "status": "pending",
            "created_at": timestamp,
            "updated_at": timestamp,
            "retry_count": 0,
            "error": None,
        }
        tasks.append(task)
        self._write_tasks(tasks)
        return dict(task), True

    def list_tasks(self) -> list[dict[str, Any]]:
        """Return all tasks in creation order."""
        return [dict(task) for task in self._read_tasks()]

    def get_next_task(self) -> dict[str, Any] | None:
        """Return the oldest pending task without changing its status."""
        for task in self._read_tasks():
            if task.get("status") == "pending":
                return dict(task)
        return None

    def update_task_status(
        self,
        task_id: str,
        status: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Update one task status and persist any failure reason."""
        if status not in TASK_STATUSES:
            allowed = "、".join(sorted(TASK_STATUSES))
            raise ValueError(f"无效任务状态：{status}；允许状态：{allowed}")

        tasks = self._read_tasks()
        for task in tasks:
            if task.get("id") != task_id:
                continue
            task["status"] = status
            task["updated_at"] = _utc_now()
            task["error"] = error if status == "failed" else None
            if status == "failed":
                task["retry_count"] = int(task.get("retry_count", 0)) + 1
            self._write_tasks(tasks)
            return dict(task)

        raise KeyError(f"未找到任务：{task_id}")

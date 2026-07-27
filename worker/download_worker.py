"""Download pending tasks through the existing downloader."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from assets import AssetRegistry
from task_queue import QueueManager


@dataclass(frozen=True)
class WorkerResult:
    task_id: str
    status: str
    message: str
    asset: dict[str, Any] | None = None


class DownloadWorker:
    """Process pending queue tasks sequentially."""

    def __init__(
        self,
        queue_manager: QueueManager,
        downloader: Any,
        asset_registry: AssetRegistry,
    ) -> None:
        self.queue_manager = queue_manager
        self.downloader = downloader
        self.asset_registry = asset_registry

    def run_next(self) -> WorkerResult | None:
        """Process the next pending task, if any."""
        task = self.queue_manager.get_next_task()
        if task is None:
            return None

        existing = self.asset_registry.find_asset(
            task["video_id"],
            task["platform"],
        )
        if existing is not None:
            self.queue_manager.update_task_status(task["id"], "success")
            return WorkerResult(
                task_id=task["id"],
                status="already_exists",
                message=f"already exists: {existing['file_path']}",
                asset=existing,
            )

        self.queue_manager.update_task_status(task["id"], "running")
        try:
            download_result = self.downloader.download(task["url"])
            asset, _ = self.asset_registry.register_asset(
                platform=task["platform"],
                video_id=task["video_id"],
                title=download_result.title,
                url=task["url"],
                file_path=download_result.video_path,
                metadata_path=download_result.metadata_path,
                status="success",
            )
            self.queue_manager.update_task_status(task["id"], "success")
            return WorkerResult(
                task_id=task["id"],
                status="success",
                message=f"下载完成：{asset['file_path']}",
                asset=asset,
            )
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            self.queue_manager.update_task_status(
                task["id"],
                "failed",
                error=message,
            )
            return WorkerResult(
                task_id=task["id"],
                status="failed",
                message=message,
            )

    def run_until_empty(self) -> list[WorkerResult]:
        """Process pending tasks until the queue has none left."""
        results: list[WorkerResult] = []
        while True:
            result = self.run_next()
            if result is None:
                return results
            results.append(result)

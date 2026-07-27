"""Video collection task entry point for video-agent v0.2.0."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

from assets import AssetRegistry
from browser import PlaywrightBrowser
from downloader import YtDlpDownloader
from task_queue import QueueManager
from utils import read_clipboard_text
from worker import DownloadWorker


PROJECT_ROOT = Path(__file__).resolve().parent
VERSION = "0.2.0"


def _load_platform_detector():
    """Load platform/detector.py without shadowing Python's platform module."""
    detector_path = PROJECT_ROOT / "platform" / "detector.py"
    spec = importlib.util.spec_from_file_location(
        "video_agent_platform_detector",
        detector_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载平台检测模块：{detector_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_platform_detector = _load_platform_detector()


class PlatformEntryDownloader(YtDlpDownloader):
    """Use detector validation while preserving the downloader implementation."""

    @staticmethod
    def validate_youtube_url(url: str) -> str:
        return url.strip()


def load_settings() -> dict:
    config_path = PROJECT_ROOT / "config" / "settings.yaml"
    with config_path.open("r", encoding="utf-8") as stream:
        settings = yaml.safe_load(stream)
    if not isinstance(settings, dict):
        raise ValueError("settings.yaml 格式无效")
    return settings


def runtime_state_paths(settings: dict) -> tuple[Path, Path]:
    """Resolve queue and registry files from the configured runtime directory."""
    raw_runtime_dir = str(settings.get("runtime_dir", "")).strip()
    if not raw_runtime_dir:
        raise ValueError("settings.yaml 缺少 runtime_dir")
    configured_path = Path(raw_runtime_dir)
    runtime_dir = (
        configured_path.resolve()
        if configured_path.is_absolute()
        else (PROJECT_ROOT / configured_path).resolve()
    )
    return runtime_dir / "tasks.json", runtime_dir / "registry.json"


def parse_command(argv: list[str]) -> tuple[str, str | None]:
    """Return command mode and optional URL."""
    if not argv:
        return "interactive", None
    if argv == ["--clipboard"]:
        clipboard_text = read_clipboard_text()
        if not clipboard_text.strip():
            raise ValueError("未检测到剪贴板中的视频URL。")
        return "download", clipboard_text
    if argv == ["--queue"]:
        return "queue", None
    if argv and argv[0] == "--add":
        if len(argv) != 2 or not argv[1].strip():
            raise ValueError("参数错误：请使用 python main.py --add VIDEO_URL")
        return "add", argv[1]
    if len(argv) > 1:
        raise ValueError("参数错误：只接受一个受支持平台的视频URL")
    if argv and argv[0].startswith("-"):
        raise ValueError(f"未知参数：{argv[0]}")
    return "download", argv[0]


def command_line_url(argv: list[str]) -> str | None:
    """Backward-compatible URL argument parser for v0.1.x callers."""
    mode, url = parse_command(argv)
    if mode == "interactive":
        return None
    if mode != "download":
        raise ValueError("该参数不是单URL下载模式")
    return url


def validate_video_url(raw_url: str) -> str:
    """Backward-compatible URL validator returning the normalized URL."""
    url, _ = _platform_detector.validate_platform_url(raw_url)
    return url


def run_direct_download(url_argument: str | None, settings: dict) -> int:
    """Run the existing immediate/interactive download flow."""
    browser = PlaywrightBrowser(settings["browser"], PROJECT_ROOT)
    downloader = PlatformEntryDownloader(settings["download"], PROJECT_ROOT)

    try:
        if url_argument is None:
            browser.start()
            browser.open_youtube()
            print("浏览器已启动。登录状态仅保存在本机 Profile。")
            url_argument = input("请输入视频URL：")
            if url_argument.strip().lower() in {"q", "quit", "exit"}:
                print("已取消。")
                return 0

        url, platform_name = _platform_detector.validate_platform_url(url_argument)
        browser.close()
        print("\n开始下载：")
        print(f"平台：{platform_name}")
        print(f"URL：{url}")

        result = downloader.download(url)
        print("\n下载完成：")
        print(f"标题：{result.title}")
        print(f"文件：{result.video_path}")
        print(f"metadata：{result.metadata_path}")
        print(f"日志：{result.log_path}")
        return 0
    finally:
        browser.close()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        mode, url_argument = parse_command(argv)
        settings = load_settings()

        if mode == "add":
            tasks_path, _ = runtime_state_paths(settings)
            queue_manager = QueueManager(tasks_path)
            task, created = queue_manager.add_task(url_argument or "")
            print("任务已加入队列。" if created else "相同任务已在队列中。")
            print(f"任务ID：{task['id']}")
            print(f"平台：{task['platform']}")
            print(f"视频ID：{task['video_id']}")
            print(f"状态：{task['status']}")
            return 0

        if mode == "queue":
            tasks_path, registry_path = runtime_state_paths(settings)
            queue_manager = QueueManager(tasks_path)
            asset_registry = AssetRegistry(registry_path)
            downloader = PlatformEntryDownloader(settings["download"], PROJECT_ROOT)
            worker = DownloadWorker(queue_manager, downloader, asset_registry)
            results = worker.run_until_empty()
            if not results:
                print("队列中没有pending任务。")
                return 0
            for result in results:
                print(f"{result.task_id} | {result.status} | {result.message}")
            return 1 if any(result.status == "failed" for result in results) else 0

        return run_direct_download(url_argument, settings)
    except KeyboardInterrupt:
        print("\n用户取消。")
        return 130
    except Exception as exc:
        print(f"\n执行失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

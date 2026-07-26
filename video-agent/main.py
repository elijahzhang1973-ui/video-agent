"""Multi-platform URL entry point for video-agent v0.1.3."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

from browser import PlaywrightBrowser
from downloader import YtDlpDownloader
from utils import read_clipboard_text


PROJECT_ROOT = Path(__file__).resolve().parent
VERSION = "0.1.3"


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


def command_line_url(argv: list[str]) -> str | None:
    if len(argv) > 1:
        raise ValueError("参数错误：只接受一个受支持平台的视频URL")
    if argv == ["--clipboard"]:
        clipboard_text = read_clipboard_text()
        if not clipboard_text.strip():
            raise ValueError("未检测到剪贴板中的视频URL。")
        return clipboard_text
    if argv and argv[0].startswith("-"):
        raise ValueError(f"未知参数：{argv[0]}")
    return argv[0] if argv else None


def validate_video_url(raw_url: str) -> str:
    """Backward-compatible URL validator returning the normalized URL."""
    url, _ = _platform_detector.validate_platform_url(raw_url)
    return url


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    settings = load_settings()
    browser = PlaywrightBrowser(settings["browser"], PROJECT_ROOT)
    downloader = PlatformEntryDownloader(settings["download"], PROJECT_ROOT)

    try:
        url_argument = command_line_url(argv)
        if url_argument is None:
            browser.start()
            browser.open_youtube()
            print("浏览器已启动。登录状态仅保存在本机 Profile。")
            url_argument = input("请输入视频URL：")
            if url_argument.strip().lower() in {"q", "quit", "exit"}:
                print("已取消。")
                return 0

        url, platform_name = _platform_detector.validate_platform_url(url_argument)
        # Chromium locks parts of its profile on Windows. Close it before
        # yt-dlp reads the authorized local login state.
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
    except KeyboardInterrupt:
        print("\n用户取消。")
        return 130
    except Exception as exc:
        print(f"\n执行失败: {exc}", file=sys.stderr)
        return 1
    finally:
        browser.close()


if __name__ == "__main__":
    raise SystemExit(main())

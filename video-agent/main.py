"""CLI and interactive entry point for video-agent v0.1.1."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from browser import PlaywrightBrowser
from downloader import YtDlpDownloader


PROJECT_ROOT = Path(__file__).resolve().parent
VERSION = "0.1.1"
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}


def load_settings() -> dict:
    config_path = PROJECT_ROOT / "config" / "settings.yaml"
    with config_path.open("r", encoding="utf-8") as stream:
        settings = yaml.safe_load(stream)
    if not isinstance(settings, dict):
        raise ValueError("settings.yaml 格式无效")
    return settings


def command_line_url(argv: list[str]) -> str | None:
    if len(argv) > 1:
        raise ValueError("参数错误：只接受一个 YouTube 视频 URL")
    return argv[0] if argv else None


def validate_video_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise ValueError("URL不能为空")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("无效URL：请输入以 http:// 或 https:// 开头的完整地址")

    hostname = parsed.hostname.lower()
    if hostname not in YOUTUBE_HOSTS:
        raise ValueError("非YouTube地址：仅支持 youtube.com 或 youtu.be 视频链接")

    path = parsed.path.strip("/")
    is_video_url = False
    if hostname == "youtu.be":
        is_video_url = bool(path)
    elif parsed.path.rstrip("/") == "/watch":
        is_video_url = bool(parse_qs(parsed.query).get("v", [""])[0])
    else:
        first_segment = path.split("/", 1)[0] if path else ""
        is_video_url = first_segment in {"shorts", "live", "embed"} and "/" in path

    if not is_video_url:
        raise ValueError("无效YouTube URL：链接中未找到视频ID")
    return url


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    settings = load_settings()
    browser = PlaywrightBrowser(settings["browser"], PROJECT_ROOT)
    downloader = YtDlpDownloader(settings["download"], PROJECT_ROOT)

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

        url = validate_video_url(url_argument)
        # Chromium locks parts of its profile on Windows. Close it before
        # yt-dlp reads the authorized local login state.
        browser.close()
        print("\n开始下载：")
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

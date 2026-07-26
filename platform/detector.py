"""Detect and validate supported video-platform URLs."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


SUPPORTED_PLATFORM_NAMES = (
    "YouTube",
    "X/Twitter",
    "小红书",
    "Bilibili",
    "TikTok",
)

HOST_TO_PLATFORM = {
    "youtube.com": "YouTube",
    "www.youtube.com": "YouTube",
    "m.youtube.com": "YouTube",
    "music.youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "x.com": "X/Twitter",
    "www.x.com": "X/Twitter",
    "mobile.x.com": "X/Twitter",
    "twitter.com": "X/Twitter",
    "www.twitter.com": "X/Twitter",
    "mobile.twitter.com": "X/Twitter",
    "xiaohongshu.com": "小红书",
    "www.xiaohongshu.com": "小红书",
    "m.xiaohongshu.com": "小红书",
    "xhslink.com": "小红书",
    "www.xhslink.com": "小红书",
    "bilibili.com": "Bilibili",
    "www.bilibili.com": "Bilibili",
    "m.bilibili.com": "Bilibili",
    "b23.tv": "Bilibili",
    "www.b23.tv": "Bilibili",
    "tiktok.com": "TikTok",
    "www.tiktok.com": "TikTok",
    "m.tiktok.com": "TikTok",
    "vm.tiktok.com": "TikTok",
    "vt.tiktok.com": "TikTok",
}


def detect_platform(raw_url: str) -> tuple[str, object]:
    """Return the display platform name and parsed URL."""
    url = raw_url.strip()
    if not url:
        raise ValueError("URL不能为空")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("无效URL：请输入以 http:// 或 https:// 开头的完整地址")

    platform_name = HOST_TO_PLATFORM.get(parsed.hostname.lower())
    if platform_name is None:
        supported = "、".join(SUPPORTED_PLATFORM_NAMES)
        raise ValueError(f"不支持的平台：当前支持 {supported}")
    return platform_name, parsed


def _is_youtube_video(parsed) -> bool:
    hostname = parsed.hostname.lower()
    path = parsed.path.strip("/")
    if hostname == "youtu.be":
        return bool(path)
    if parsed.path.rstrip("/") == "/watch":
        return bool(parse_qs(parsed.query).get("v", [""])[0])
    first_segment = path.split("/", 1)[0] if path else ""
    return first_segment in {"shorts", "live", "embed"} and "/" in path


def _is_x_video(parsed) -> bool:
    parts = [part for part in parsed.path.split("/") if part]
    try:
        status_index = parts.index("status")
    except ValueError:
        return False
    return status_index + 1 < len(parts) and parts[status_index + 1].isdigit()


def _is_xiaohongshu_video(parsed) -> bool:
    hostname = parsed.hostname.lower()
    path = parsed.path.rstrip("/")
    if hostname in {"xhslink.com", "www.xhslink.com"}:
        return bool(path)
    return bool(re.fullmatch(r"/(?:explore|discovery/item)/[A-Za-z0-9]+", path))


def _is_bilibili_video(parsed) -> bool:
    hostname = parsed.hostname.lower()
    path = parsed.path.rstrip("/")
    if hostname in {"b23.tv", "www.b23.tv"}:
        return bool(path)
    return bool(re.fullmatch(r"/video/(?:BV[0-9A-Za-z]+|av\d+)", path))


def _is_tiktok_video(parsed) -> bool:
    hostname = parsed.hostname.lower()
    path = parsed.path.rstrip("/")
    if hostname in {"vm.tiktok.com", "vt.tiktok.com"}:
        return bool(path)
    return bool(re.fullmatch(r"/@[^/]+/video/\d+", path))


PLATFORM_VALIDATORS = {
    "YouTube": _is_youtube_video,
    "X/Twitter": _is_x_video,
    "小红书": _is_xiaohongshu_video,
    "Bilibili": _is_bilibili_video,
    "TikTok": _is_tiktok_video,
}


def validate_platform_url(raw_url: str) -> tuple[str, str]:
    """Return normalized URL and platform name after video-link validation."""
    platform_name, parsed = detect_platform(raw_url)
    if not PLATFORM_VALIDATORS[platform_name](parsed):
        raise ValueError(f"无效{platform_name} URL：链接中未找到视频ID")
    return raw_url.strip(), platform_name

"""YouTube downloads with yt-dlp, MP4 merging, metadata, and logs."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import imageio_ffmpeg
import yt_dlp


@dataclass(frozen=True)
class DownloadResult:
    video_path: Path
    metadata_path: Path
    log_path: Path
    video_id: str
    title: str


class _YtDlpLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def debug(self, message: str) -> None:
        if message.startswith("[debug]"):
            self.logger.debug(message)
        else:
            self.logger.info(message)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str) -> None:
        self.logger.error(message)


class YtDlpDownloader:
    def __init__(self, settings: dict[str, Any], project_root: Path) -> None:
        self.settings = settings
        self.project_root = project_root.resolve()
        self.output_dir = self._project_path(str(settings["output_dir"]))
        self.log_dir = self._project_path(str(settings["log_dir"]))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _project_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        return path.resolve() if path.is_absolute() else (self.project_root / path).resolve()

    @staticmethod
    def validate_youtube_url(url: str) -> str:
        candidate = url.strip()
        parsed = urlparse(candidate)
        hostname = (parsed.hostname or "").lower()
        allowed_hosts = {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
            "youtu.be",
        }
        if parsed.scheme not in {"http", "https"} or hostname not in allowed_hosts:
            raise ValueError("请输入有效的 YouTube 视频 URL")
        return candidate

    def _new_logger(self) -> tuple[logging.Logger, Path]:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        log_path = self.log_dir / f"download-{stamp}.log"
        logger = logging.getLogger(f"video_agent.download.{stamp}")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        return logger, log_path

    @staticmethod
    def _safe_video_id(video_id: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", video_id)
        if not cleaned:
            raise ValueError("yt-dlp 未返回有效的视频 ID")
        return cleaned

    def _base_options(self, logger: logging.Logger) -> dict[str, Any]:
        options: dict[str, Any] = {
            "logger": _YtDlpLogger(logger),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": False,
            "socket_timeout": int(self.settings.get("socket_timeout", 30)),
            "retries": int(self.settings.get("retries", 5)),
            "js_runtimes": {"node": {}},
        }
        cookie_settings = self.settings.get("cookies_from_browser", {})
        if cookie_settings.get("enabled", False):
            browser_name = str(cookie_settings.get("browser", "chrome"))
            raw_profile = str(cookie_settings["profile"])
            profile = Path(
                os.path.expandvars(os.path.expanduser(raw_profile))
            ).resolve()
            if profile == self.project_root or self.project_root in profile.parents:
                raise ValueError("Cookie Profile 不允许位于项目目录中")
            if not profile.exists():
                raise FileNotFoundError(f"浏览器 Profile 不存在: {profile}")
            # yt-dlp reads directly from the local browser profile. It does not
            # create or persist a cookie file in this project.
            options["cookiesfrombrowser"] = (browser_name, str(profile), None, None)
        return options

    def inspect(self, url: str) -> dict[str, Any]:
        """Validate and resolve one public YouTube URL without downloading."""
        validated = self.validate_youtube_url(url)
        logger, _ = self._new_logger()
        options = self._base_options(logger)
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(validated, download=False)
        if info is None:
            raise RuntimeError("yt-dlp 未解析到视频信息")
        return info

    def download(self, url: str) -> DownloadResult:
        validated = self.validate_youtube_url(url)
        logger, log_path = self._new_logger()
        logger.info("开始解析 URL: %s", validated)

        output_template = str(
            self.output_dir / "%(id)s" / "%(title).180B [%(id)s].%(ext)s"
        )

        options = self._base_options(logger)
        options.update(
            {
                "format": str(self.settings.get("format", "bestvideo*+bestaudio/best")),
                "merge_output_format": "mp4",
                "outtmpl": output_template,
                "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
                "overwrites": False,
            }
        )

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(validated, download=True)
            if info is None:
                raise RuntimeError("yt-dlp 下载后未返回视频信息")
            prepared_path = Path(ydl.prepare_filename(info))

        video_id = self._safe_video_id(str(info["id"]))
        video_dir = self.output_dir / video_id
        video_path = prepared_path.with_suffix(".mp4")
        if not video_path.exists() and prepared_path.exists():
            video_path = prepared_path
        if not video_path.exists():
            candidates = sorted(
                video_dir.glob("*"),
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
            candidates = [
                item for item in candidates if item.is_file() and item.name != "metadata.json"
            ]
            if not candidates:
                raise FileNotFoundError("下载完成，但未找到输出视频文件")
            video_path = candidates[0]

        metadata_path = video_dir / "metadata.json"
        metadata = {
            "id": info.get("id"),
            "title": info.get("title"),
            "webpage_url": info.get("webpage_url") or validated,
            "extractor": info.get("extractor"),
            "duration": info.get("duration"),
            "width": info.get("width"),
            "height": info.get("height"),
            "fps": info.get("fps"),
            "vcodec": info.get("vcodec"),
            "acodec": info.get("acodec"),
            "ext": video_path.suffix.lstrip("."),
            "filesize_bytes": video_path.stat().st_size,
            "downloaded_at": datetime.now().astimezone().isoformat(),
            "local_file": video_path.name,
        }
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("视频文件: %s", video_path)
        logger.info("元数据: %s", metadata_path)

        return DownloadResult(
            video_path=video_path,
            metadata_path=metadata_path,
            log_path=log_path,
            video_id=video_id,
            title=str(info.get("title") or video_id),
        )

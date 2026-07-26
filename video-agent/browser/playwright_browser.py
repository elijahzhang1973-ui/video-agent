"""Visible Playwright browser backed by a persistent local profile."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright


class PlaywrightBrowser:
    """Manage a visible persistent Chromium context."""

    def __init__(self, settings: dict[str, Any], project_root: Path) -> None:
        self.settings = settings
        self.project_root = project_root
        self._playwright: Playwright | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def _profile_path(self) -> Path:
        raw_path = str(self.settings["user_data_dir"])
        expanded = os.path.expandvars(os.path.expanduser(raw_path))
        path = Path(expanded)
        if not path.is_absolute():
            raise ValueError(
                "browser.user_data_dir 必须是项目外的本机绝对路径或环境变量路径"
            )

        resolved = path.resolve()
        project = self.project_root.resolve()
        if resolved == project or project in resolved.parents:
            raise ValueError("浏览器 Profile 不允许存放在项目目录中")
        return resolved

    def start(self) -> Page:
        if self.context is not None:
            raise RuntimeError("浏览器已经启动")

        profile_path = self._profile_path()
        profile_path.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()

        try:
            launch_options: dict[str, Any] = {
                "user_data_dir": str(profile_path),
                "headless": bool(self.settings.get("headless", False)),
                "viewport": None,
                "args": ["--start-maximized"],
            }
            channel = self.settings.get("channel")
            if channel:
                launch_options["channel"] = str(channel)

            self.context = self._playwright.chromium.launch_persistent_context(
                **launch_options,
            )
            self.context.set_default_timeout(
                int(self.settings.get("timeout_ms", 30_000))
            )
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            return self.page
        except Exception:
            self._playwright.stop()
            self._playwright = None
            raise

    def open_youtube(self) -> str:
        if self.page is None:
            raise RuntimeError("请先启动浏览器")
        self.page.goto(
            "https://www.youtube.com",
            wait_until="domcontentloaded",
        )
        title = self.page.title()
        print(f"页面标题: {title}")
        return title

    def close(self) -> None:
        if self.context is not None:
            self.context.close()
            self.context = None
            self.page = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self) -> "PlaywrightBrowser":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

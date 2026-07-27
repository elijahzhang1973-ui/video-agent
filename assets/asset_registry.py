"""JSON registry for successfully downloaded video assets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AssetRegistry:
    """Persist downloaded asset locations and support duplicate checks."""

    def __init__(self, registry_path: str | Path) -> None:
        self.registry_path = Path(registry_path).resolve()
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._write_assets([])

    def _read_assets(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"资产登记JSON格式无效：{self.registry_path}"
            ) from exc
        if not isinstance(payload, list):
            raise ValueError(f"资产登记必须是JSON数组：{self.registry_path}")
        return payload

    def _write_assets(self, assets: list[dict[str, Any]]) -> None:
        temporary_path = self.registry_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(assets, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self.registry_path)

    def register_asset(
        self,
        *,
        platform: str,
        video_id: str,
        title: str,
        url: str,
        file_path: str | Path,
        metadata_path: str | Path,
        status: str = "success",
    ) -> tuple[dict[str, Any], bool]:
        """Register one asset, returning ``(asset, created)``."""
        existing = self.find_asset(video_id, platform)
        if existing is not None:
            return existing, False

        asset: dict[str, Any] = {
            "asset_id": uuid4().hex,
            "platform": platform,
            "video_id": video_id,
            "title": title,
            "url": url,
            "file_path": str(Path(file_path).resolve()),
            "metadata_path": str(Path(metadata_path).resolve()),
            "status": status,
            "created_at": _utc_now(),
        }
        assets = self._read_assets()
        assets.append(asset)
        self._write_assets(assets)
        return dict(asset), True

    def find_asset(
        self,
        video_id: str,
        platform: str | None = None,
    ) -> dict[str, Any] | None:
        """Find a successful asset by video ID and optional platform."""
        for asset in self._read_assets():
            if asset.get("video_id") != video_id:
                continue
            if platform is not None and asset.get("platform") != platform:
                continue
            if asset.get("status") == "success":
                return dict(asset)
        return None

    def list_assets(self) -> list[dict[str, Any]]:
        """Return all registered assets."""
        return [dict(asset) for asset in self._read_assets()]

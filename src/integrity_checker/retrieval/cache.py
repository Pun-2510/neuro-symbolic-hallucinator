"""Disk-based JSON cache cho API responses."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class DiskCache:
    """Cache file JSON theo key, có TTL.

    Dùng để giảm tải API khi rerun pipeline.
    """

    def __init__(self, cache_dir: Path, ttl_seconds: int = 86400, enabled: bool = True) -> None:
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        safe = "".join(c if c.isalnum() else "_" for c in key)[:120]
        return self.cache_dir / f"{safe}.json"

    def get(self, key: str) -> dict | None:
        if not self.enabled:
            return None
        path = self._key_to_path(key)
        if not path.exists():
            return None
        if time.time() - path.stat().st_mtime > self.ttl_seconds:
            return None  # expired
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def set(self, key: str, value: dict) -> None:
        if not self.enabled:
            return
        path = self._key_to_path(key)
        path.write_text(json.dumps(value, ensure_ascii=False, default=str), encoding="utf-8")
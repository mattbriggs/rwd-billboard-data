"""Filesystem-backed JSON cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class JsonCacheStore:
    """Simple filesystem cache for provider JSON responses.

    :param root: Cache directory.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path_for_key(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        """Read a cached JSON payload by key."""

        path = self._path_for_key(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def set(self, key: str, payload: dict[str, Any]) -> None:
        """Persist a JSON payload by key."""

        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

"""Cache locale dei soli metadati: domini delle dimensioni.

Non contiene osservazioni. Ogni voce conserva sorgente, data di acquisizione e
scadenza.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

DEFAULT_TTL_SECONDS = 24 * 3600


def default_cache_dir() -> Path:
    env = os.environ.get("OSSERVAPREZZI_CACHE_DIR")
    if env:
        return Path(env)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "osservaprezzi" / "cache"
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "osservaprezzi"


class MetadataCache:
    def __init__(self, directory: Path | None = None, ttl: int = DEFAULT_TTL_SECONDS):
        self.directory = directory or default_cache_dir()
        self.ttl = ttl
        self._data: dict[str, dict[str, Any]] | None = None

    @property
    def path(self) -> Path:
        return self.directory / "metadata.json"

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._data is None:
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._data = {}
        return self._data

    @staticmethod
    def key(collection_id: str, dimension: str, context: dict[str, str]) -> str:
        parts = "&".join(f"{k}={context[k]}" for k in sorted(context))
        return f"{collection_id}|{dimension}|{parts}"

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._load().get(key)
        if not entry:
            return None
        if entry.get("expires_at", 0) < time.time():
            return None
        return entry

    def set(self, key: str, values: list[dict[str, str]], source_url: str, fetched_at: str) -> None:
        data = self._load()
        data[key] = {
            "values": values,
            "source_url": source_url,
            "fetched_at": fetched_at,
            "expires_at": time.time() + self.ttl,
        }

    def flush(self) -> None:
        if self._data is None:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    def clear(self) -> None:
        self._data = {}
        try:
            self.path.unlink()
        except OSError:
            pass

"""SQLite-backed peak cache — drop-in replacement for plyvel/LevelDB."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator


_SCHEMA = """
CREATE TABLE IF NOT EXISTS peak_cache (
    key        TEXT PRIMARY KEY,
    data       BLOB NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class PeakCache:
    """Persistent key→bytes cache stored in a single SQLite file.

    Interface is compatible with the plyvel.DB subset used in this project:
    get/Get, put/Put, iterator, close.
    """

    def __init__(self, path: str | Path, create_if_missing: bool = True) -> None:
        path = Path(path)
        if not create_if_missing and not path.exists():
            raise FileNotFoundError(f'Peak cache not found: {path}')
        self._conn = sqlite3.connect(str(path))
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Read

    def get(self, key: str | bytes, default: bytes | None = None) -> bytes | None:
        if isinstance(key, bytes):
            key = key.decode()
        row = self._conn.execute(
            'SELECT data FROM peak_cache WHERE key = ?', (key,)
        ).fetchone()
        return bytes(row[0]) if row else default

    # plyvel used capitalised .Get()
    Get = get

    # ------------------------------------------------------------------
    # Write

    def put(self, key: str | bytes, value: bytes) -> None:
        if isinstance(key, bytes):
            key = key.decode()
        self._conn.execute(
            'INSERT OR REPLACE INTO peak_cache (key, data) VALUES (?, ?)',
            (key, value)
        )
        self._conn.commit()

    Put = put

    # ------------------------------------------------------------------
    # Iteration

    def iterator(self, include_value: bool = True) -> Iterator[bytes] | Iterator[tuple[bytes, bytes]]:
        """Yield (key_bytes[, value_bytes]) rows ordered by key."""
        if include_value:
            for key, data in self._conn.execute(
                'SELECT key, data FROM peak_cache ORDER BY key'
            ):
                yield key.encode(), bytes(data)
        else:
            for (key,) in self._conn.execute(
                'SELECT key FROM peak_cache ORDER BY key'
            ):
                yield key.encode()

    # ------------------------------------------------------------------
    # Lifecycle

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> PeakCache:
        return self

    def __exit__(self, *_) -> None:
        self.close()

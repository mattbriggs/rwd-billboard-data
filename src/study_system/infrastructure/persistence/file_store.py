"""Low-level file persistence helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def ensure_parent(path: Path) -> None:
    """Ensure that a file's parent directory exists."""

    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any, *, pretty: bool = True) -> None:
    """Write JSON to disk.

    :param path: Output path.
    :param payload: JSON-serializable payload.
    :param pretty: Pretty-print output.
    """

    ensure_parent(path)
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None)
    path.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")


def read_json(path: Path) -> Any:
    """Read JSON from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a list of dictionaries to CSV.

    :param path: Output path.
    :param rows: CSV rows.
    """

    ensure_parent(path)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key in seen:
                continue
            seen.add(key)
            fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

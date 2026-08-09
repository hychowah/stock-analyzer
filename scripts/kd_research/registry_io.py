"""Simple JSON / CSV read-write helpers for the research harness."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def load_json(path: Path | str) -> Any:
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path | str, data: Any, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=indent, default=str) + "\n", encoding="utf-8")


def load_csv(path: Path | str) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path | str, records: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    if fieldnames is None:
        fieldnames = list(records[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow({k: row.get(k) for k in fieldnames})


def append_csv(path: Path | str, records: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        return
    exists = path.exists()
    if fieldnames is None:
        fieldnames = list(records[0].keys())
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        for row in records:
            writer.writerow({k: row.get(k) for k in fieldnames})

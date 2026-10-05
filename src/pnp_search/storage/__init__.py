"""Append-only JSONL records in isolated experiment directories."""

import json
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel


def append_jsonl(path: Path, record: BaseModel | dict[str, Any]) -> None:
    """Append a complete UTF-8 record; callers own a single-writer run directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    value = record.model_dump(mode="json") if isinstance(record, BaseModel) else record
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    """Fail visibly on corrupt records rather than silently dropping failed experiments."""
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)

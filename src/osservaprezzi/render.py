"""Rendering di tabella, JSON e CSV.

JSON e CSV rappresentano gli stessi record, con gli stessi valori nulli: in CSV
un valore assente è una cella vuota, in JSON è `null`.
"""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


def format_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def to_csv(records: Sequence[dict[str, Any]], columns: Sequence[str] | None = None) -> str:
    if not records:
        return ""
    fields = list(columns) if columns else list(records[0].keys())
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow({f: format_scalar(record.get(f)) for f in fields})
    return buffer.getvalue()


def to_table(records: Sequence[dict[str, Any]], columns: Sequence[str] | None = None) -> str:
    if not records:
        return ""
    fields = list(columns) if columns else list(records[0].keys())
    rows = [[format_scalar(r.get(f)) for f in fields] for r in records]
    widths = [
        max(len(fields[i]), *(len(row[i]) for row in rows)) for i in range(len(fields))
    ]
    lines = [
        "  ".join(fields[i].ljust(widths[i]) for i in range(len(fields))).rstrip(),
        "  ".join("-" * widths[i] for i in range(len(fields))),
    ]
    for row in rows:
        lines.append(
            "  ".join(row[i].ljust(widths[i]) for i in range(len(fields))).rstrip()
        )
    return "\n".join(lines) + "\n"


def write(text: str, output: Path | None) -> None:
    """Scrive su file oppure su stdout, che contiene soltanto dati."""
    if not text.endswith("\n"):
        text += "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def jsonl(records: Iterable[dict[str, Any]]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)

"""Archivi on-demand: pianificazione, esecuzione sequenziale, manifest e ripresa."""

from __future__ import annotations

import itertools
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION, __version__
from .client import Client
from .collections import Collection
from .errors import InvalidParameter, NoData, OsservaprezziError
from .render import to_csv

DEFAULT_MAX_REQUESTS = 100
MANIFEST_NAME = "manifest.json"


def normalize_product(text: str) -> str:
    """Normalizzazione documentata per il confronto locale del prodotto."""
    return " ".join(text.split()).casefold()


PRODUCT_MATCH_RULE = (
    "confronto esatto dopo casefold e compattazione degli spazi "
    "(normalize_product)"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass
class Plan:
    collection: str
    filters: dict[str, str]
    expanded: dict[str, list[str]]
    combinations: list[dict[str, str]]
    product: str | None = None

    @property
    def request_count(self) -> int:
        return len(self.combinations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "collection": self.collection,
            "filters": self.filters,
            "expanded": self.expanded,
            "product": self.product,
            "planned_requests": self.request_count,
        }


def build_plan(
    client: Client,
    collection: Collection,
    filters: dict[str, str],
    expand: list[str],
    product: str | None = None,
) -> Plan:
    for name in expand:
        if collection.dimension(name) is None:
            raise InvalidParameter(
                f"dimensione non espandibile per {collection.id}: {name}",
                parameter="all",
                value=name,
                allowed=list(collection.dimension_names),
            )
        if name in filters:
            raise InvalidParameter(
                f"la dimensione {name} è sia filtrata sia espansa",
                parameter="all",
                value=name,
            )

    missing = [
        d for d in collection.dimension_names if d not in filters and d not in expand
    ]
    if missing:
        raise InvalidParameter(
            "filtri mancanti: " + ", ".join(missing),
            parameter="filters",
            missing=missing,
            hint="indica ogni dimensione con un filtro esplicito oppure con --all",
        )

    expanded: dict[str, list[str]] = {}
    for name in expand:
        dimension = collection.dimension(name)
        parents = {p: filters[p] for p in dimension.parents if p in filters}
        options, _ = client.values(collection, name, parents)
        expanded[name] = [o.value for o in options]

    ordered_expand = [d for d in collection.dimension_names if d in expanded]
    combos: list[dict[str, str]] = []
    for values in itertools.product(*(expanded[d] for d in ordered_expand)):
        combo = dict(filters)
        combo.update(dict(zip(ordered_expand, values)))
        combos.append({d: combo[d] for d in collection.dimension_names})

    return Plan(
        collection=collection.id,
        filters=filters,
        expanded=expanded,
        combinations=combos,
        product=product,
    )


@dataclass
class ArchiveResult:
    directory: Path
    status: str
    row_count: int
    completed: int
    failed: int
    manifest: dict[str, Any] = field(default_factory=dict)


def _combo_id(combo: dict[str, str]) -> str:
    return "&".join(f"{k}={combo[k]}" for k in sorted(combo))


def _record_key(record: dict[str, Any], key_fields: tuple[str, ...]) -> tuple:
    return tuple(str(record.get(f)) for f in key_fields)


def _data_path(directory: Path, data_format: str) -> Path:
    return directory / ("data.jsonl" if data_format == "jsonl" else "data.csv")


def _write_data(
    directory: Path,
    data_format: str,
    records: list[dict[str, Any]],
    columns: list[str],
) -> None:
    path = _data_path(directory, data_format)
    if data_format == "jsonl":
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    else:
        text = to_csv(records, columns) if records else ",".join(columns) + "\n"
    path.write_text(text, encoding="utf-8")


def _load_previous(directory: Path, data_format: str) -> list[dict[str, Any]]:
    path = _data_path(directory, data_format)
    if not path.exists():
        return []
    if data_format == "jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    import csv as _csv

    with path.open(encoding="utf-8", newline="") as handle:
        return [
            {k: (v if v != "" else None) for k, v in row.items()}
            for row in _csv.DictReader(handle)
        ]


def run_archive(
    client: Client,
    collection: Collection,
    plan: Plan,
    directory: Path,
    data_format: str = "csv",
    resume: bool = False,
    verbose: bool = False,
) -> ArchiveResult:
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / MANIFEST_NAME

    done: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    seen: set[tuple] = set()

    if resume and manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in previous.get("results", []):
            if entry.get("status") in {"ok", "no_data"}:
                done[entry["id"]] = entry
        for record in _load_previous(directory, data_format):
            key = _record_key(record, collection.natural_key)
            if key not in seen:
                seen.add(key)
                records.append(record)

    columns = (
        list(collection.dimension_names)
        + [c.name for c in collection.derived]
        + [c.name for c in collection.columns]
    ) + [
        "collection",
        "source_url",
        "retrieved_at",
    ]

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tool": f"osservaprezzi/{__version__}",
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "collection": collection.id,
        "filters": plan.filters,
        "expanded": plan.expanded,
        "product_filter": (
            {"value": plan.product, "rule": PRODUCT_MATCH_RULE} if plan.product else None
        ),
        "natural_key": list(collection.natural_key),
        "data_file": _data_path(directory, data_format).name,
        "requests": {
            "planned": plan.request_count,
            "completed": len(done),
            "failed": 0,
        },
        "row_count": len(records),
        "results": list(done.values()),
        "notes": list(collection.notes),
        "source": collection.url,
    }
    _write_manifest(manifest_path, manifest)

    target = normalize_product(plan.product) if plan.product else None
    failed = 0

    for combo in plan.combinations:
        combo_id = _combo_id(combo)
        if combo_id in done:
            continue
        entry: dict[str, Any] = {"id": combo_id, "filters": combo}
        try:
            result = client.get(collection, combo)
            rows = result.records
            if target is not None:
                rows = [
                    r
                    for r in rows
                    if normalize_product(str(r.get("product", ""))) == target
                ]
            added = 0
            for record in rows:
                key = _record_key(record, collection.natural_key)
                if key in seen:
                    continue
                seen.add(key)
                records.append(record)
                added += 1
            entry.update(
                status="ok" if rows else "no_match",
                rows=added,
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
            )
        except NoData as exc:
            entry.update(
                status="no_data",
                rows=0,
                source_url=exc.details.get("source_url"),
                retrieved_at=_now(),
            )
        except OsservaprezziError as exc:
            failed += 1
            entry.update(status="failed", rows=0, error=exc.to_dict())
            if verbose:
                print(f"richiesta fallita: {combo_id}: {exc.message}", file=sys.stderr)

        manifest["results"].append(entry)
        manifest["requests"]["completed"] = sum(
            1 for e in manifest["results"] if e["status"] != "failed"
        )
        manifest["requests"]["failed"] = failed
        manifest["row_count"] = len(records)
        _write_data(directory, data_format, records, columns)
        _write_manifest(manifest_path, manifest)
        if verbose:
            print(
                f"{len(manifest['results'])}/{plan.request_count} {combo_id} "
                f"({entry['status']})",
                file=sys.stderr,
            )

    status = "complete" if failed == 0 else "partial"
    manifest["status"] = status
    manifest["finished_at"] = _now()
    _write_manifest(manifest_path, manifest)

    return ArchiveResult(
        directory=directory,
        status=status,
        row_count=len(records),
        completed=manifest["requests"]["completed"],
        failed=failed,
        manifest=manifest,
    )


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

"""Query salvate in YAML, versione 1 dello schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .collections import get_collection
from .errors import InvalidQuery

SUPPORTED_VERSIONS = (1,)
FORMATS = ("table", "json", "csv")


@dataclass
class SavedQuery:
    version: int
    collection: str
    filters: dict[str, str]
    format: str = "table"
    limit: int | None = None


def load(path: Path) -> SavedQuery:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InvalidQuery(f"file di query non leggibile: {path}", error=str(exc)) from exc
    except yaml.YAMLError as exc:
        raise InvalidQuery(f"YAML non valido: {path}", error=str(exc)) from exc

    if not isinstance(raw, dict):
        raise InvalidQuery("la query deve essere una mappa YAML", path=str(path))

    unknown = set(raw) - {"version", "collection", "filters", "format", "limit"}
    if unknown:
        raise InvalidQuery(
            "chiavi sconosciute nella query: " + ", ".join(sorted(unknown)),
            unknown=sorted(unknown),
        )

    version = raw.get("version")
    if version not in SUPPORTED_VERSIONS:
        raise InvalidQuery(
            f"versione dello schema non supportata: {version}",
            supported=list(SUPPORTED_VERSIONS),
        )

    collection_id = raw.get("collection")
    if not isinstance(collection_id, str):
        raise InvalidQuery("campo `collection` mancante o non testuale")
    collection = get_collection(collection_id)

    filters = raw.get("filters") or {}
    if not isinstance(filters, dict):
        raise InvalidQuery("campo `filters` deve essere una mappa")
    unknown_filters = set(filters) - set(collection.dimension_names)
    if unknown_filters:
        raise InvalidQuery(
            "filtri sconosciuti: " + ", ".join(sorted(unknown_filters)),
            collection=collection.id,
            unknown=sorted(unknown_filters),
            allowed=list(collection.dimension_names),
        )

    fmt = raw.get("format", "table")
    if fmt not in FORMATS:
        raise InvalidQuery(f"formato non supportato: {fmt}", supported=list(FORMATS))

    limit = raw.get("limit")
    if limit is not None and (not isinstance(limit, int) or limit <= 0):
        raise InvalidQuery("`limit` deve essere un intero positivo", value=limit)

    return SavedQuery(
        version=version,
        collection=collection.id,
        filters={k: str(v) for k, v in filters.items()},
        format=fmt,
        limit=limit,
    )


def dump(query: SavedQuery) -> str:
    payload = {
        "version": query.version,
        "collection": query.collection,
        "filters": query.filters,
        "format": query.format,
    }
    if query.limit:
        payload["limit"] = query.limit
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

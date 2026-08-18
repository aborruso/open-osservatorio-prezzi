"""Superficie a riga di comando.

Sequenza di scoperta consigliata, anche per agenti:
`catalog` → `describe <collezione>` → `values <collezione> <dimensione>` → `get`.
`stdout` contiene soltanto i dati richiesti; avvisi, progressi ed errori vanno
su `stderr`.
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import typer

from . import SCHEMA_VERSION, __version__
from . import errors as err
from . import render
from .archive import DEFAULT_MAX_REQUESTS, build_plan, run_archive
from .cache import MetadataCache
from .client import Client
from .collections import COLLECTIONS, Collection, get_collection
from .http import DEFAULT_PAUSE, DEFAULT_RETRIES, DEFAULT_TIMEOUT, Fetcher
from .query import load as load_query

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help=(
        "CLI read-only per i dati pubblici dell'Osservatorio Prezzi. "
        "Scoperta: catalog → describe → values → get."
    ),
)

FILTER_OPTIONS = ("year", "month", "week", "province", "category", "market", "group")


def _fail(error: err.OsservaprezziError, as_json: bool) -> None:
    raise typer.Exit(err.emit(error, as_json))


def handle_errors(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        as_json = bool(kwargs.get("json_output"))
        try:
            return func(*args, **kwargs)
        except err.OsservaprezziError as exc:
            _fail(exc, as_json)

    return wrapper


def _make_client(
    timeout: float, retries: int, pause: float, refresh: bool, verbose: bool
) -> tuple[Client, MetadataCache, Fetcher]:
    cache = MetadataCache()
    fetcher = Fetcher(timeout=timeout, retries=retries, pause=pause, verbose=verbose)
    return Client(fetcher, cache, refresh=refresh), cache, fetcher


def _collect_filters(collection: Collection, provided: dict[str, Any]) -> dict[str, str]:
    """Filtra le opzioni valorizzate e rifiuta quelle estranee alla collezione."""
    filters: dict[str, str] = {}
    unexpected: list[str] = []
    for name in FILTER_OPTIONS:
        value = provided.get(name)
        if value is None:
            continue
        if collection.dimension(name) is None:
            unexpected.append(name)
        else:
            filters[name] = str(value)
    if unexpected:
        raise err.InvalidParameter(
            "opzioni non previste per questa collezione: " + ", ".join(unexpected),
            collection=collection.id,
            unexpected=unexpected,
            allowed=list(collection.dimension_names),
        )
    return filters


PROVENANCE_FIELDS = ("collection", "source_url", "retrieved_at", "defaults_used")


def _emit(
    payload: Any,
    records: list[dict[str, Any]] | None,
    columns: list[str] | None,
    json_output: bool,
    csv_output: bool,
    output: Optional[Path],
    hide_provenance: bool = False,
) -> None:
    if json_output:
        text = render.to_json(payload)
    elif csv_output:
        text = render.to_csv(records or [], columns)
    else:
        # Nelle osservazioni la provenienza è identica su tutte le righe e
        # renderebbe illeggibile la tabella: resta in JSON e CSV. Nei comandi
        # di scoperta, invece, `collection` è un identificatore e va mostrato.
        visible = [
            c
            for c in (columns or [])
            if not (hide_provenance and c in PROVENANCE_FIELDS)
        ]
        text = render.to_table(records or [], visible)
    render.write(text, output)


# -- comandi ---------------------------------------------------------------


@app.command()
@handle_errors
def catalog(
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    csv_output: bool = typer.Option(False, "--csv", help="Output CSV."),
    output: Optional[Path] = typer.Option(None, "--output", help="Scrive su file."),
) -> None:
    """Elenca le collezioni supportate. Passo successivo: `describe <collezione>`."""
    records = [
        {
            "collection": c.id,
            "title": c.title,
            "status": "available",
            "dimensions": ", ".join(c.dimension_names),
        }
        for c in COLLECTIONS.values()
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "collections": [
            {
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "status": "available",
                "url": c.url,
                "dimensions": list(c.dimension_names),
            }
            for c in COLLECTIONS.values()
        ],
        "next_step": "osservaprezzi describe <collezione>",
    }
    _emit(payload, records, list(records[0]), json_output, csv_output, output)


@app.command()
@handle_errors
def describe(
    collection_id: str = typer.Argument(..., metavar="COLLEZIONE"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    csv_output: bool = typer.Option(False, "--csv", help="Output CSV."),
    output: Optional[Path] = typer.Option(None, "--output", help="Scrive su file."),
    refresh: bool = typer.Option(False, "--refresh", help="Ignora la cache dei metadati."),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries"),
    verbose: bool = typer.Option(False, "--verbose", help="Diagnostica su stderr."),
) -> None:
    """Descrive metadati, dimensioni e copertura temporale di una collezione."""
    collection = get_collection(collection_id)
    client, cache, fetcher = _make_client(timeout, retries, 0.0, refresh, verbose)
    try:
        years, meta = client.values(collection, "year")
        payload = {
            "schema_version": SCHEMA_VERSION,
            "collection": collection.id,
            "title": collection.title,
            "description": collection.description,
            "url": collection.url,
            "dimensions": [
                {
                    "name": d.name,
                    "html_parameter": d.html_name,
                    "label": d.label,
                    "depends_on": list(d.parents),
                }
                for d in collection.dimensions
            ],
            "columns": [
                {"name": c.name, "header": c.header, "numeric": c.numeric}
                for c in collection.columns
            ],
            "natural_key": list(collection.natural_key),
            "coverage": {
                "dimension": "year",
                "values": [o.value for o in years],
            },
            "notes": list(collection.notes),
            "provenance": meta,
            "next_step": f"osservaprezzi values {collection.id} <dimensione>",
        }
        records = [
            {
                "dimension": d.name,
                "html_parameter": d.html_name,
                "label": d.label,
                "depends_on": ", ".join(d.parents),
            }
            for d in collection.dimensions
        ]
        cache.flush()
    finally:
        fetcher.close()
    _emit(payload, records, list(records[0]), json_output, csv_output, output)


@app.command()
@handle_errors
def values(
    collection_id: str = typer.Argument(..., metavar="COLLEZIONE"),
    dimension: str = typer.Argument(..., metavar="DIMENSIONE"),
    year: Optional[int] = typer.Option(None, "--year"),
    month: Optional[int] = typer.Option(None, "--month"),
    week: Optional[int] = typer.Option(None, "--week"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    csv_output: bool = typer.Option(False, "--csv", help="Output CSV."),
    output: Optional[Path] = typer.Option(None, "--output", help="Scrive su file."),
    refresh: bool = typer.Option(False, "--refresh", help="Ignora la cache dei metadati."),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries"),
    verbose: bool = typer.Option(False, "--verbose", help="Diagnostica su stderr."),
) -> None:
    """Elenca i valori ammessi per una dimensione.

    I domini dipendenti richiedono i filtri genitori: i mesi dipendono
    dall'anno, le settimane da anno e mese.
    """
    collection = get_collection(collection_id)
    parents = {
        k: str(v)
        for k, v in (("year", year), ("month", month), ("week", week))
        if v is not None
    }
    client, cache, fetcher = _make_client(timeout, retries, 0.0, refresh, verbose)
    try:
        options, meta = client.values(collection, dimension, parents)
        cache.flush()
    finally:
        fetcher.close()

    records = [{"value": o.value, "label": o.label} for o in options]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "collection": collection.id,
        "dimension": dimension,
        "parents": parents,
        "values": records,
        "provenance": meta,
        "next_step": f"osservaprezzi get {collection.id} --{dimension} <valore> ...",
    }
    _emit(payload, records, ["value", "label"], json_output, csv_output, output)


@app.command()
@handle_errors
def get(
    collection_id: str = typer.Argument(..., metavar="COLLEZIONE"),
    year: Optional[int] = typer.Option(None, "--year"),
    month: Optional[int] = typer.Option(None, "--month"),
    week: Optional[int] = typer.Option(None, "--week"),
    province: Optional[str] = typer.Option(None, "--province"),
    category: Optional[str] = typer.Option(None, "--category"),
    market: Optional[str] = typer.Option(None, "--market"),
    group: Optional[str] = typer.Option(None, "--group"),
    latest: bool = typer.Option(
        False, "--latest", help="Usa i valori predefiniti del portale per i filtri mancanti."
    ),
    limit: Optional[int] = typer.Option(None, "--limit", help="Numero massimo di osservazioni."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    csv_output: bool = typer.Option(False, "--csv", help="Output CSV."),
    output: Optional[Path] = typer.Option(None, "--output", help="Scrive su file."),
    refresh: bool = typer.Option(False, "--refresh", help="Ignora la cache dei metadati."),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries"),
    verbose: bool = typer.Option(False, "--verbose", help="Diagnostica su stderr."),
) -> None:
    """Recupera le osservazioni per una combinazione esplicita di filtri."""
    collection = get_collection(collection_id)
    filters = _collect_filters(collection, locals())
    client, cache, fetcher = _make_client(timeout, retries, 0.0, refresh, verbose)
    try:
        defaults_used: list[str] = []
        if latest:
            missing = [d for d in collection.dimension_names if d not in filters]
            if missing:
                proposed = client.latest(collection)
                for name in missing:
                    if name in proposed:
                        filters[name] = proposed[name]
                        defaults_used.append(name)
        result = client.get(collection, filters, limit=limit)
        cache.flush()
    finally:
        fetcher.close()

    # RF-05F: l'uso dei valori predefiniti del portale resta visibile in ogni
    # formato, non soltanto nel JSON.
    origine = ",".join(defaults_used) or None
    for record in result.records:
        record["defaults_used"] = origine

    columns = list(result.records[0])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "collection": result.collection,
        "filters": result.filters,
        "defaults_used": defaults_used,
        "count": len(result.records),
        "complete": limit is None or len(result.records) < limit,
        "source_url": result.source_url,
        "retrieved_at": result.retrieved_at,
        "notes": list(collection.notes),
        "records": result.records,
    }
    _emit(
        payload,
        result.records,
        columns,
        json_output,
        csv_output,
        output,
        hide_provenance=True,
    )


@app.command()
@handle_errors
def run(
    query_file: Path = typer.Argument(..., metavar="QUERY.YAML"),
    output: Optional[Path] = typer.Option(None, "--output", help="Scrive su file."),
    json_output: bool = typer.Option(False, "--json", help="Forza output JSON."),
    csv_output: bool = typer.Option(False, "--csv", help="Forza output CSV."),
    refresh: bool = typer.Option(False, "--refresh"),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Esegue una query salvata in YAML."""
    saved = load_query(query_file)
    collection = get_collection(saved.collection)
    if not json_output and not csv_output:
        json_output = saved.format == "json"
        csv_output = saved.format == "csv"

    client, cache, fetcher = _make_client(timeout, retries, 0.0, refresh, verbose)
    try:
        result = client.get(collection, saved.filters, limit=saved.limit)
        cache.flush()
    finally:
        fetcher.close()

    for record in result.records:
        record["defaults_used"] = None

    columns = list(result.records[0])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "collection": result.collection,
        "filters": result.filters,
        "count": len(result.records),
        "source_url": result.source_url,
        "retrieved_at": result.retrieved_at,
        "notes": list(collection.notes),
        "records": result.records,
    }
    _emit(
        payload,
        result.records,
        columns,
        json_output,
        csv_output,
        output,
        hide_provenance=True,
    )


@app.command()
@handle_errors
def archive(
    collection_id: str = typer.Argument(..., metavar="COLLEZIONE"),
    year: Optional[int] = typer.Option(None, "--year"),
    month: Optional[int] = typer.Option(None, "--month"),
    week: Optional[int] = typer.Option(None, "--week"),
    province: Optional[str] = typer.Option(None, "--province"),
    category: Optional[str] = typer.Option(None, "--category"),
    market: Optional[str] = typer.Option(None, "--market"),
    group: Optional[str] = typer.Option(None, "--group"),
    all_dimensions: list[str] = typer.Option(
        [], "--all", help="Dimensione da espandere su tutti i valori (ripetibile)."
    ),
    product: Optional[str] = typer.Option(
        None, "--product", help="Conserva solo il prodotto indicato (confronto locale)."
    ),
    output: Optional[Path] = typer.Option(None, "--output", help="Directory dell'archivio."),
    data_format: str = typer.Option("csv", "--format", help="csv oppure jsonl."),
    max_requests: int = typer.Option(DEFAULT_MAX_REQUESTS, "--max-requests"),
    pause: float = typer.Option(DEFAULT_PAUSE, "--pause", help="Pausa fra richieste, in secondi."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Mostra il piano senza eseguirlo."),
    resume: bool = typer.Option(False, "--resume", help="Ripete solo le richieste mancanti o fallite."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    refresh: bool = typer.Option(False, "--refresh"),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Crea un archivio espandendo una o più dimensioni, in sequenza."""
    collection = get_collection(collection_id)
    filters = _collect_filters(collection, locals())
    if data_format not in {"csv", "jsonl"}:
        raise err.InvalidParameter(
            f"formato archivio non supportato: {data_format}",
            parameter="format",
            allowed=["csv", "jsonl"],
        )
    if product and collection.id == "consumo" and "category" not in filters:
        raise err.InvalidParameter(
            "il filtro prodotto richiede anche la categoria",
            parameter="product",
            hint=f"osservaprezzi values {collection.id} category",
        )

    client, cache, fetcher = _make_client(timeout, retries, pause, refresh, verbose)
    try:
        plan = build_plan(client, collection, filters, list(all_dimensions), product)
        cache.flush()

        if plan.request_count > max_requests:
            raise err.InvalidParameter(
                f"il piano richiede {plan.request_count} richieste, oltre il limite di {max_requests}",
                parameter="max-requests",
                planned=plan.request_count,
                limit=max_requests,
                hint="riduci le dimensioni espanse oppure alza --max-requests consapevolmente",
            )

        if dry_run:
            payload = {
                "schema_version": SCHEMA_VERSION,
                "plan": plan.to_dict(),
                "max_requests": max_requests,
                "pause_seconds": pause,
                "notes": list(collection.notes),
            }
            if json_output:
                render.write(render.to_json(payload), output=None)
            else:
                render.write(
                    f"richieste previste: {plan.request_count}\n"
                    f"dimensioni espanse: "
                    f"{', '.join(f'{k} ({len(v)})' for k, v in plan.expanded.items()) or 'nessuna'}\n",
                    output=None,
                )
            return

        if output is None:
            raise err.InvalidParameter(
                "indicare la directory dell'archivio con --output", parameter="output"
            )

        result = run_archive(
            client,
            collection,
            plan,
            output,
            data_format=data_format,
            resume=resume,
            verbose=verbose,
        )
    finally:
        fetcher.close()

    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": result.status,
        "directory": str(result.directory),
        "rows": result.row_count,
        "requests": result.manifest["requests"],
        "manifest": str(result.directory / "manifest.json"),
    }
    if json_output:
        render.write(render.to_json(summary), output=None)
    else:
        render.write(
            f"archivio {result.status}: {result.row_count} righe in {result.directory}\n",
            output=None,
        )
    if result.status == "partial":
        raise typer.Exit(err.EXIT_PARTIAL_RESPONSE)


@app.command()
def version(
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Mostra versione del programma e dello schema di output."""
    if json_output:
        render.write(
            render.to_json({"version": __version__, "schema_version": SCHEMA_VERSION}),
            output=None,
        )
    else:
        render.write(f"osservaprezzi {__version__} (schema {SCHEMA_VERSION})", output=None)


@app.command("cache")
def cache_command(
    clear: bool = typer.Option(False, "--clear", help="Svuota la cache dei metadati."),
) -> None:
    """Mostra o svuota la cache locale dei metadati."""
    store = MetadataCache()
    if clear:
        store.clear()
        print(f"cache svuotata: {store.path}", file=sys.stderr)
        return
    render.write(str(store.path), output=None)


def main() -> None:
    app()


if __name__ == "__main__":
    main()

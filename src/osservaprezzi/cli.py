"""Superficie a riga di comando.

Sequenza di scoperta consigliata, anche per agenti:
`catalog` → `describe <collezione>` → `values <collezione> <dimensione>` → `get`.
`stdout` contiene soltanto i dati richiesti; avvisi, progressi ed errori vanno
su `stderr`.
"""

from __future__ import annotations

import functools
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import typer

from . import SCHEMA_VERSION, __version__
from . import errors as err
from . import render
from .archive import (
    DEFAULT_MAX_REQUESTS,
    build_plan,
    run_archive,
    temporal_expansion,
)
from .cache import MetadataCache
from .catalogo import costruisci, risolvi_categoria
from .client import Client
from .collections import COLLECTIONS, Collection, get_collection
from .gate import DEFAULT_LOCK_TIMEOUT
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

# L'help di ogni filtro dichiara a quali collezioni appartiene e da cosa
# dipende: sono le due informazioni che altrimenti si scoprono solo sbagliando.
H_YEAR = "Anno. Tutte le collezioni."
H_MONTH = "Mese, da 1 a 12. Tutte le collezioni. Il dominio dipende da --year."
H_WEEK = (
    "Settimana del mese. Solo ortofrutta-it e ortofrutta-eu. "
    "Il dominio dipende da --year e --month."
)
H_PROVINCE = (
    "Provincia di rilevazione. Solo consumo. Accetta il nome (Roma), il codice "
    "ISTAT (058), quello dell'unità territoriale (258), il NUTS3 (ITI43) o la "
    "sigla (RM)."
)
H_CATEGORY = "Tipologia di prodotto. Solo consumo."
H_MARKET = "Mercato all'ingrosso. Solo ortofrutta-it e ortofrutta-eu."
H_GROUP = "Gruppo merceologico. Solo ortofrutta-it e ortofrutta-eu."
H_AGENT = "Modalità agente: JSON, senza colori e senza interazione."
H_LOCK_TIMEOUT = (
    "Secondi di attesa se un'altra esecuzione sta già interrogando il portale. "
    "0 attende senza limite."
)


def _fail(error: err.OsservaprezziError, as_json: bool) -> None:
    raise typer.Exit(err.emit(error, as_json))


def handle_errors(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if kwargs.pop("agent", False):
            # `--agent` è la scorciatoia per l'uso non interattivo: JSON su
            # dati ed errori, nessun colore, nessun comportamento implicito.
            kwargs["json_output"] = True
            os.environ["NO_COLOR"] = "1"
        as_json = bool(kwargs.get("json_output"))
        try:
            return func(*args, **kwargs)
        except err.OsservaprezziError as exc:
            _fail(exc, as_json)

    return wrapper


def _make_client(
    timeout: float,
    retries: int,
    pause: float,
    refresh: bool,
    verbose: bool,
    lock_timeout: float = DEFAULT_LOCK_TIMEOUT,
) -> tuple[Client, MetadataCache, Fetcher]:
    cache = MetadataCache()
    fetcher = Fetcher(
        timeout=timeout,
        retries=retries,
        pause=pause,
        verbose=verbose,
        lock_timeout=lock_timeout,
    )
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


def _avvisa_espansione_temporale(avviso: dict[str, Any]) -> None:
    """Segnala su stderr che si sta costruendo una serie non comparabile."""
    dimensioni = ", ".join(avviso["dimensions"])
    print(
        f"\nattenzione: stai espandendo la dimensione temporale ({dimensioni}, "
        f"{avviso['periods']} periodi).\n  {avviso['reason']}\n"
        f"  Per l'andamento nel tempo la fonte corretta sono gli indici ISTAT:\n"
        f"    {avviso['use_instead']['command']}\n",
        file=sys.stderr,
    )


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
    agent: bool = typer.Option(False, "--agent", help=H_AGENT),
    csv_output: bool = typer.Option(False, "--csv", help="Output CSV."),
    output: Optional[Path] = typer.Option(None, "--output", help="Scrive su file."),
) -> None:
    """Elenca le collezioni supportate.

    \b
    Esempi:
      osservaprezzi catalog
      osservaprezzi catalog --json

    Passo successivo: osservaprezzi describe <collezione>
    """
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
    agent: bool = typer.Option(False, "--agent", help=H_AGENT),
    csv_output: bool = typer.Option(False, "--csv", help="Output CSV."),
    output: Optional[Path] = typer.Option(None, "--output", help="Scrive su file."),
    refresh: bool = typer.Option(False, "--refresh", help="Ignora la cache dei metadati."),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries"),
    lock_timeout: float = typer.Option(
        DEFAULT_LOCK_TIMEOUT, "--lock-timeout", help=H_LOCK_TIMEOUT
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Diagnostica su stderr."),
) -> None:
    """Descrive metadati, dimensioni e copertura temporale di una collezione.

    \b
    Esempi:
      osservaprezzi describe consumo
      osservaprezzi describe ortofrutta-it --json

    Passo successivo: osservaprezzi values <collezione> <dimensione>
    """
    collection = get_collection(collection_id)
    client, cache, fetcher = _make_client(timeout, retries, 0.0, refresh, verbose, lock_timeout)
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
            "derived_columns": [
                {"name": c.name, "description": c.header} for c in collection.derived
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
    year: Optional[int] = typer.Option(None, "--year", help=H_YEAR),
    month: Optional[int] = typer.Option(None, "--month", help=H_MONTH),
    week: Optional[int] = typer.Option(None, "--week", help=H_WEEK),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    agent: bool = typer.Option(False, "--agent", help=H_AGENT),
    csv_output: bool = typer.Option(False, "--csv", help="Output CSV."),
    output: Optional[Path] = typer.Option(None, "--output", help="Scrive su file."),
    refresh: bool = typer.Option(False, "--refresh", help="Ignora la cache dei metadati."),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries"),
    lock_timeout: float = typer.Option(
        DEFAULT_LOCK_TIMEOUT, "--lock-timeout", help=H_LOCK_TIMEOUT
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Diagnostica su stderr."),
) -> None:
    """Elenca i valori ammessi per una dimensione.

    I domini dipendenti richiedono i filtri genitori: i mesi dipendono
    dall'anno, le settimane da anno e mese.

    \b
    Esempi:
      osservaprezzi values consumo province
      osservaprezzi values consumo month --year 2025
      osservaprezzi values ortofrutta-it week --year 2025 --month 5

    Passo successivo: osservaprezzi get <collezione> <filtri>
    """
    collection = get_collection(collection_id)
    parents = {
        k: str(v)
        for k, v in (("year", year), ("month", month), ("week", week))
        if v is not None
    }
    client, cache, fetcher = _make_client(timeout, retries, 0.0, refresh, verbose, lock_timeout)
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
    year: Optional[int] = typer.Option(None, "--year", help=H_YEAR),
    month: Optional[int] = typer.Option(None, "--month", help=H_MONTH),
    week: Optional[int] = typer.Option(None, "--week", help=H_WEEK),
    province: Optional[str] = typer.Option(None, "--province", help=H_PROVINCE),
    category: Optional[str] = typer.Option(None, "--category", help=H_CATEGORY),
    market: Optional[str] = typer.Option(None, "--market", help=H_MARKET),
    group: Optional[str] = typer.Option(None, "--group", help=H_GROUP),
    latest: bool = typer.Option(
        False, "--latest", help="Usa i valori predefiniti del portale per i filtri mancanti."
    ),
    limit: Optional[int] = typer.Option(None, "--limit", help="Numero massimo di osservazioni."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    agent: bool = typer.Option(False, "--agent", help=H_AGENT),
    csv_output: bool = typer.Option(False, "--csv", help="Output CSV."),
    output: Optional[Path] = typer.Option(None, "--output", help="Scrive su file."),
    refresh: bool = typer.Option(False, "--refresh", help="Ignora la cache dei metadati."),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries"),
    lock_timeout: float = typer.Option(
        DEFAULT_LOCK_TIMEOUT, "--lock-timeout", help=H_LOCK_TIMEOUT
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Diagnostica su stderr."),
) -> None:
    """Recupera le osservazioni per una combinazione esplicita di filtri.

    Tutti i filtri della collezione sono obbligatori: i valori predefiniti del
    portale cambiano nel tempo e vanno richiesti con --latest.

    \b
    Esempi:
      osservaprezzi get consumo --year 2025 --month 5
        --province Roma --category energia
      osservaprezzi get ortofrutta-it --year 2025 --month 5 --week 2
        --market ROMA --group ORTAGGI
      osservaprezzi get ortofrutta-eu --year 2025 --month 5 --week 2
        --market PARIGI --group ORTAGGI --csv
      osservaprezzi get consumo --latest --json

    Uscite: 2 filtro non ammesso, 3 nessun dato, 4 contratto cambiato.
    """
    collection = get_collection(collection_id)
    filters = _collect_filters(collection, locals())
    client, cache, fetcher = _make_client(timeout, retries, 0.0, refresh, verbose, lock_timeout)
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
def find(
    collection_id: str = typer.Argument(..., metavar="COLLEZIONE"),
    text: str = typer.Argument(..., metavar="TESTO"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    agent: bool = typer.Option(False, "--agent", help=H_AGENT),
    csv_output: bool = typer.Option(False, "--csv", help="Output CSV."),
    output: Optional[Path] = typer.Option(None, "--output", help="Scrive su file."),
    refresh: bool = typer.Option(False, "--refresh", help="Ricostruisce il catalogo."),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries"),
    lock_timeout: float = typer.Option(
        DEFAULT_LOCK_TIMEOUT, "--lock-timeout", help=H_LOCK_TIMEOUT
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Diagnostica su stderr."),
) -> None:
    """Cerca un prodotto e dice in quale categoria si trova.

    Il portale non espone il prodotto come filtro, quindi la categoria è
    l'unica cosa che resta da indovinare: questo comando la trova. Il catalogo
    viene costruito una volta interrogando le categorie di una cella di
    riferimento e poi resta in cache.

    \b
    Esempi:
      osservaprezzi find consumo salmone
      osservaprezzi find consumo "pane fresco" --agent
      osservaprezzi find ortofrutta-it pomodori

    I risultati sono osservati, non dichiarati: valgono per il contesto
    indicato in `observed_with` e altrove possono cambiare.
    """
    collection = get_collection(collection_id)
    client, cache, fetcher = _make_client(
        timeout, retries, 0.0, refresh, verbose, lock_timeout
    )
    try:
        catalogo = costruisci(client, collection)
        cache.flush()
    finally:
        fetcher.close()

    trovate = catalogo.cerca(text)
    if not trovate:
        raise err.NoData(
            f"nessun risultato per {text!r}",
            collection=collection.id,
            observed_with=catalogo.context,
            hint=f"il catalogo contiene {len(catalogo.voci)} voci; prova un testo più corto",
        )

    records = [
        {catalogo.field: v.value, catalogo.dimension: v.parent, "label": v.parent_label}
        for v in trovate
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "collection": collection.id,
        "query": text,
        "source": "observed",
        "observed_with": catalogo.context,
        "count": len(records),
        "matches": records,
        "next_step": (
            f"osservaprezzi get {collection.id} "
            f"--{catalogo.dimension} <valore> <altri filtri>"
        ),
    }
    _emit(payload, records, list(records[0]), json_output, csv_output, output)


@app.command()
@handle_errors
def run(
    query_file: Path = typer.Argument(..., metavar="QUERY.YAML"),
    output: Optional[Path] = typer.Option(None, "--output", help="Scrive su file."),
    json_output: bool = typer.Option(False, "--json", help="Forza output JSON."),
    agent: bool = typer.Option(False, "--agent", help=H_AGENT),
    csv_output: bool = typer.Option(False, "--csv", help="Forza output CSV."),
    refresh: bool = typer.Option(False, "--refresh"),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries"),
    lock_timeout: float = typer.Option(
        DEFAULT_LOCK_TIMEOUT, "--lock-timeout", help=H_LOCK_TIMEOUT
    ),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Esegue una query salvata in YAML.

    \b
    Esempi:
      osservaprezzi run query.yaml
      osservaprezzi run query.yaml --csv --output dati.csv

    \b
    Schema del file:
      version: 1
      collection: ortofrutta-it
      filters: {year: 2025, month: 5, week: 2, market: ROMA, group: ORTAGGI}
      format: json
    """
    saved = load_query(query_file)
    collection = get_collection(saved.collection)
    if not json_output and not csv_output:
        json_output = saved.format == "json"
        csv_output = saved.format == "csv"

    client, cache, fetcher = _make_client(timeout, retries, 0.0, refresh, verbose, lock_timeout)
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
    year: Optional[int] = typer.Option(None, "--year", help=H_YEAR),
    month: Optional[int] = typer.Option(None, "--month", help=H_MONTH),
    week: Optional[int] = typer.Option(None, "--week", help=H_WEEK),
    province: Optional[str] = typer.Option(None, "--province", help=H_PROVINCE),
    category: Optional[str] = typer.Option(None, "--category", help=H_CATEGORY),
    market: Optional[str] = typer.Option(None, "--market", help=H_MARKET),
    group: Optional[str] = typer.Option(None, "--group", help=H_GROUP),
    all_dimensions: list[str] = typer.Option(
        [], "--all", help="Dimensione da espandere su tutti i valori (ripetibile)."
    ),
    product: Optional[str] = typer.Option(
        None, "--product", help="Conserva solo il prodotto indicato (confronto locale)."
    ),
    output: Optional[Path] = typer.Option(None, "--output", help="Directory dell'archivio."),
    data_format: str = typer.Option("csv", "--format", help="csv oppure jsonl."),
    max_requests: int = typer.Option(
        DEFAULT_MAX_REQUESTS,
        "--max-requests",
        help=(
            "Limite sulle richieste dell'archivio. Quelle per preparare il piano "
            "(catalogo, domini) non sono contate: il piano le dichiara."
        ),
    ),
    pause: float = typer.Option(DEFAULT_PAUSE, "--pause", help="Pausa fra richieste, in secondi."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Mostra il piano senza eseguirlo."),
    resume: bool = typer.Option(False, "--resume", help="Ripete solo le richieste mancanti o fallite."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    agent: bool = typer.Option(False, "--agent", help=H_AGENT),
    refresh: bool = typer.Option(False, "--refresh"),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries"),
    lock_timeout: float = typer.Option(
        DEFAULT_LOCK_TIMEOUT, "--lock-timeout", help=H_LOCK_TIMEOUT
    ),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Crea un archivio espandendo una o più dimensioni, in sequenza.

    Ogni dimensione non espansa va filtrata: nessuna espansione è implicita.

    \b
    Esempi (piano, esecuzione, ripresa):
      osservaprezzi archive consumo --year 2025 --month 5
        --all province --product "pane fresco" --dry-run
      osservaprezzi archive consumo --year 2025 --month 5
        --all province --product "pane fresco" --output archivio
      osservaprezzi archive ortofrutta-it --year 2025 --month 5 --week 2
        --group ORTAGGI --all market --output archivio --resume

    Produce data.csv (o data.jsonl) e manifest.json. Uscita 6 se resta parziale.
    """
    collection = get_collection(collection_id)
    filters = _collect_filters(collection, locals())
    if data_format not in {"csv", "jsonl"}:
        raise err.InvalidParameter(
            f"formato archivio non supportato: {data_format}",
            parameter="format",
            allowed=["csv", "jsonl"],
        )
    client, cache, fetcher = _make_client(timeout, retries, pause, refresh, verbose, lock_timeout)
    try:
        # Il prodotto non è un filtro del portale e vive dentro una categoria:
        # invece di pretendere che l'utente la conosca, la ricaviamo dal
        # catalogo quando la corrispondenza è una sola. Se è ambigua l'errore
        # elenca le possibilità, che vengono dai dati.
        risolto = product
        catalogo_usato = None
        if product and collection.catalog is not None:
            dimensione = collection.catalog.dimension
            if dimensione not in filters and dimensione not in all_dimensions:
                valore, risolto = risolvi_categoria(client, collection, product)
                filters[dimensione] = valore
                catalogo_usato = {dimensione: valore, "product": risolto}
                if not json_output:
                    print(
                        f"{collection.catalog.label} risolto dal catalogo: "
                        f"{risolto!r} in {dimensione}={valore}",
                        file=sys.stderr,
                    )

        plan = build_plan(client, collection, filters, list(all_dimensions), risolto)
        cache.flush()
        # Catalogo e domini delle dimensioni espanse costano richieste prima
        # ancora dell'archivio, quando non sono in cache: vanno dichiarate.
        preparazione = fetcher.requests_made

        if plan.request_count > max_requests:
            raise err.InvalidParameter(
                f"il piano richiede {plan.request_count} richieste, oltre il limite di {max_requests}",
                parameter="max-requests",
                planned=plan.request_count,
                limit=max_requests,
                hint="riduci le dimensioni espanse oppure alza --max-requests consapevolmente",
            )

        # L'avvertenza va data prima dell'esecuzione, quando può ancora
        # cambiare la decisione, e su stderr per non contaminare i dati.
        avviso = temporal_expansion(collection, plan)
        if avviso and not json_output:
            _avvisa_espansione_temporale(avviso)

        if dry_run:
            payload = {
                "schema_version": SCHEMA_VERSION,
                "plan": plan.to_dict(),
                "max_requests": max_requests,
                "pause_seconds": pause,
                "notes": list(collection.notes),
                "temporal_expansion": avviso,
                "resolved_from_catalog": catalogo_usato,
                "preparation_requests": preparazione,
            }
            if json_output:
                render.write(render.to_json(payload), output=None)
            else:
                render.write(
                    f"richieste previste: {plan.request_count}\n"
                    f"dimensioni espanse: "
                    f"{', '.join(f'{k} ({len(v)})' for k, v in plan.expanded.items()) or 'nessuna'}\n"
                    f"richieste già fatte per preparare il piano: {preparazione}\n",
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
        # Anche chi esegue in modalità agente deve trovare l'avvertenza nel
        # risultato, non solo nel manifest.
        "temporal_expansion": result.manifest.get("temporal_expansion"),
    }
    if json_output:
        render.write(render.to_json(summary), output=None)
    else:
        render.write(
            f"archivio {result.status}: {result.row_count} righe in {result.directory}\n",
            output=None,
        )
        richieste = result.manifest["requests"]
        vuote = richieste["no_data"] + richieste["no_match"]
        if vuote:
            print(
                f"richieste senza righe: {vuote} su {richieste['planned']} "
                f"(no_data {richieste['no_data']}, no_match {richieste['no_match']}), "
                "dettaglio in manifest.json",
                file=sys.stderr,
            )
    if result.status == "partial":
        raise typer.Exit(err.EXIT_PARTIAL_RESPONSE)


@app.command("agent-context")
def agent_context(
    pretty: bool = typer.Option(False, "--pretty", help="Indentazione leggibile."),
    agent: bool = typer.Option(False, "--agent", help=H_AGENT),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Descrive l'intero contratto della CLI in una sola chiamata.

    Pensato per essere il primo comando eseguito da un agente: elenca
    collezioni, dimensioni con le loro dipendenze, comandi, codici di uscita e
    forma degli errori, così non serve dedurre nulla dall'help testuale.

    \b
    Esempi:
      osservaprezzi agent-context
      osservaprezzi agent-context --pretty
    """
    # L'output è già JSON: --json e --agent sono accettati perché un agente
    # non debba sapere che questo comando fa eccezione.
    contesto = {
        "tool": "osservaprezzi",
        "version": __version__,
        "schema_version": SCHEMA_VERSION,
        "summary": (
            "CLI read-only sui dati pubblici dell'Osservatorio Prezzi (MIMIT). "
            "Restituisce soltanto dati pubblicati dal portale."
        ),
        "conventions": {
            "stdout": "solo dati o output richiesto",
            "stderr": "diagnostica, progressi ed errori",
            "errors": "con --json o --agent gli errori sono JSON su stderr",
            "agent_flag": "--agent equivale a --json senza colori né interazione",
            "read_only": True,
            "network": "una richiesta GET per interrogazione, nessun parallelismo",
        },
        "workflow": [
            "osservaprezzi catalog",
            "osservaprezzi describe <collezione>",
            "osservaprezzi values <collezione> <dimensione> [filtri genitori]",
            "osservaprezzi find <collezione> <testo>  # se non sai in quale categoria sta un prodotto",
            "osservaprezzi get <collezione> <tutti i filtri>",
        ],
        "collections": [
            {
                "id": c.id,
                "title": c.title,
                "url": c.url,
                "dimensions": [
                    {
                        "name": d.name,
                        "label": d.label,
                        "depends_on": list(d.parents),
                        "required_in_get": True,
                    }
                    for d in c.dimensions
                ],
                "columns": [c2.name for c2 in c.columns] + [d.name for d in c.derived],
                "natural_key": list(c.natural_key),
                "notes": list(c.notes),
            }
            for c in COLLECTIONS.values()
        ],
        "commands": [
            {
                "name": "catalog",
                "purpose": "elenca le collezioni",
                "example": "osservaprezzi catalog --agent",
            },
            {
                "name": "describe",
                "purpose": "dimensioni, colonne e copertura di una collezione",
                "example": "osservaprezzi describe consumo --agent",
            },
            {
                "name": "values",
                "purpose": "valori ammessi per una dimensione",
                "example": "osservaprezzi values consumo month --year 2025 --agent",
            },
            {
                "name": "find",
                "purpose": (
                    "cerca un prodotto e dice in quale categoria si trova; "
                    "risultati osservati in una cella di riferimento"
                ),
                "example": "osservaprezzi find consumo salmone --agent",
            },
            {
                "name": "get",
                "purpose": "osservazioni per una combinazione esplicita di filtri",
                "example": (
                    "osservaprezzi get consumo --year 2025 --month 5 "
                    "--province Roma --category energia --agent"
                ),
            },
            {
                "name": "run",
                "purpose": "esegue una query YAML salvata",
                "example": "osservaprezzi run query.yaml --agent",
            },
            {
                "name": "archive",
                "purpose": "espande dimensioni e produce dati più manifest",
                "example": (
                    "osservaprezzi archive consumo --year 2025 --month 5 "
                    "--all province --product \"pane fresco\" --dry-run --agent"
                ),
            },
        ],
        "exit_codes": {
            "0": "successo",
            "2": "input non valido: collezione, dimensione, filtro o query",
            "3": "nessun dato per i filtri indicati",
            "4": "contratto cambiato: HTML non riconosciuto",
            "5": "servizio temporaneamente indisponibile",
            "6": "risposta parziale o archivio incompleto",
        },
        "error_shape": {
            "code": "identificatore stabile dell'errore",
            "message": "descrizione in italiano",
            "retryable": "vero se ha senso ritentare",
            "details": "parametri rifiutati, valori ammessi, suggerimento",
        },
        "guarantees": [
            "i valori suggeriti negli errori provengono dal form del portale",
            "un filtro non applicato dal portale è un errore, non un risultato vuoto",
            "ogni record conserva collection, source_url e retrieved_at",
            "gli archivi non partono senza un piano entro --max-requests",
            "il catalogo dei prodotti è osservato in una cella di riferimento, non dichiarato dal portale",
        ],
    }
    render.write(
        render.to_json(contesto) if pretty else json.dumps(contesto, ensure_ascii=False),
        output=None,
    )


@app.command()
def version(
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    agent: bool = typer.Option(False, "--agent", help=H_AGENT),
) -> None:
    """Mostra versione del programma e dello schema di output."""
    if agent:
        json_output = True
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

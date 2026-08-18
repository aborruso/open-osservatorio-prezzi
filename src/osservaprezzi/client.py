"""Adattatore delle collezioni: scoperta dei valori e recupero delle osservazioni.

Le tre collezioni condividono lo stesso protocollo (form GET server-side,
tabella `id-table-results`) e differiscono per URL, dimensioni e schema delle
colonne: la differenza è tutta nella configurazione in `collections.py`, così
un cambiamento di contratto resta circoscritto alla collezione interessata.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cache import MetadataCache
from .collections import Collection, Dimension
from .errors import ContractChanged, InvalidDimension, InvalidParameter, NoData
from .forms import Option, Select, check_echo, parse_document, parse_form
from .http import Fetcher
from .parse import parse_table
from .territori import codici


@dataclass
class Page:
    document: object
    selects: dict[str, Select]
    source_url: str
    retrieved_at: str


@dataclass
class QueryResult:
    collection: str
    filters: dict[str, str]
    records: list[dict[str, object]] = field(default_factory=list)
    source_url: str = ""
    retrieved_at: str = ""


class Client:
    def __init__(
        self,
        fetcher: Fetcher,
        cache: MetadataCache | None = None,
        refresh: bool = False,
    ) -> None:
        self.fetcher = fetcher
        self.cache = cache or MetadataCache()
        self.refresh = refresh

    # -- richieste ---------------------------------------------------------

    def fetch_page(self, collection: Collection, filters: dict[str, str]) -> Page:
        params = {
            collection.dimension(name).html_name: value
            for name, value in filters.items()
        }
        response = self.fetcher.get(collection.url, params or None)
        document = parse_document(response.text)
        selects = parse_form(document)
        return Page(document, selects, response.url, response.retrieved_at)

    def _store_domains(
        self, collection: Collection, filters: dict[str, str], page: Page
    ) -> None:
        """Memorizza i domini osservati nella pagina, per il contesto richiesto.

        Va invocato solo dopo aver verificato che il portale abbia davvero
        applicato i filtri: una pagina che ricade sui valori predefiniti
        descrive un contesto diverso da quello richiesto.
        """
        for dimension in collection.dimensions:
            select = page.selects.get(dimension.html_name)
            if select is None:
                continue
            context = {p: filters[p] for p in dimension.parents if p in filters}
            if len(context) != len(dimension.parents):
                continue
            key = self.cache.key(collection.id, dimension.name, context)
            self.cache.set(
                key,
                [{"value": o.value, "label": o.label} for o in select.options],
                page.source_url,
                page.retrieved_at,
            )

    # -- scoperta ----------------------------------------------------------

    def values(
        self,
        collection: Collection,
        dimension_name: str,
        parent_filters: dict[str, str] | None = None,
    ) -> tuple[list[Option], dict[str, str]]:
        dimension = collection.dimension(dimension_name)
        if dimension is None:
            raise InvalidDimension(
                f"dimensione sconosciuta per {collection.id}: {dimension_name}",
                parameter="dimension",
                value=dimension_name,
                allowed=list(collection.dimension_names),
            )
        parent_filters = parent_filters or {}
        missing = [p for p in dimension.parents if p not in parent_filters]
        if missing:
            raise InvalidParameter(
                f"la dimensione {dimension_name} dipende da {', '.join(dimension.parents)}",
                parameter="parents",
                missing=missing,
            )
        context = {p: parent_filters[p] for p in dimension.parents}

        key = self.cache.key(collection.id, dimension_name, context)
        if not self.refresh:
            entry = self.cache.get(key)
            if entry:
                options = [Option(v["value"], v["label"]) for v in entry["values"]]
                return options, {
                    "source_url": entry["source_url"],
                    "retrieved_at": entry["fetched_at"],
                    "cached": "true",
                }

        page = self.fetch_page(collection, context)
        self._reject_unapplied(collection, context, page)
        self._store_domains(collection, context, page)
        select = page.selects.get(dimension.html_name)
        if select is None:
            raise ContractChanged(
                f"controllo {dimension.html_name} assente nel form",
                collection=collection.id,
                dimension=dimension_name,
            )
        return list(select.options), {
            "source_url": page.source_url,
            "retrieved_at": page.retrieved_at,
            "cached": "false",
        }

    def domains(
        self, collection: Collection, parent_filters: dict[str, str]
    ) -> dict[str, list[Option]]:
        """Domini di tutte le dimensioni nel contesto dei filtri genitori dati."""
        result: dict[str, list[Option]] = {}
        for dimension in collection.dimensions:
            if all(p in parent_filters for p in dimension.parents):
                options, _ = self.values(collection, dimension.name, parent_filters)
                result[dimension.name] = options
        return result

    def latest(self, collection: Collection) -> dict[str, str]:
        """Valori proposti dal portale come predefiniti, usati solo su richiesta."""
        page = self.fetch_page(collection, {})
        self._store_domains(collection, {}, page)
        selected: dict[str, str] = {}
        for dimension in collection.dimensions:
            select = page.selects.get(dimension.html_name)
            if select is None or not select.options:
                continue
            selected[dimension.name] = select.selected or select.options[0].value
        return selected

    # -- recupero ----------------------------------------------------------

    def get(
        self, collection: Collection, filters: dict[str, str], limit: int | None = None
    ) -> QueryResult:
        missing = [d for d in collection.dimension_names if d not in filters]
        if missing:
            raise InvalidParameter(
                "filtri mancanti: " + ", ".join(missing),
                parameter="filters",
                missing=missing,
                hint=f"osservaprezzi values {collection.id} <dimensione>",
            )
        ordered = {name: str(filters[name]) for name in collection.dimension_names}

        page = self.fetch_page(collection, ordered)
        self._reject_unapplied(collection, ordered, page)
        self._store_domains(collection, ordered, page)

        rows = parse_table(page.document, collection)
        if not rows:
            raise NoData(
                "nessuna osservazione per i filtri indicati",
                collection=collection.id,
                filters=ordered,
                source_url=page.source_url,
            )
        if limit is not None:
            rows = rows[:limit]

        derivati = self._derivati(collection, ordered)
        records = [
            {
                **ordered,
                **derivati,
                **row,
                "collection": collection.id,
                "source_url": page.source_url,
                "retrieved_at": page.retrieved_at,
            }
            for row in rows
        ]
        return QueryResult(
            collection=collection.id,
            filters=ordered,
            records=records,
            source_url=page.source_url,
            retrieved_at=page.retrieved_at,
        )

    @staticmethod
    def _derivati(collection: Collection, filters: dict[str, str]) -> dict[str, str | None]:
        """Codici territoriali ricavati dai filtri, quando la collezione li prevede."""
        if not collection.derived:
            return {}
        return codici(filters.get("province", ""))

    # -- validazione -------------------------------------------------------

    def _reject_unapplied(
        self, collection: Collection, filters: dict[str, str], page: Page
    ) -> None:
        """Un filtro non riflesso nel form è un valore non ammesso dal portale."""
        requested = {
            collection.dimension(name).html_name: value
            for name, value in filters.items()
        }
        rejected = check_echo(page.selects, requested)
        if not rejected:
            return

        by_html = {d.html_name: d for d in collection.dimensions}
        details = []
        for item in rejected:
            dimension: Dimension | None = by_html.get(str(item["html_name"]))
            select = page.selects.get(str(item["html_name"]))
            details.append(
                {
                    "dimension": dimension.name if dimension else item["html_name"],
                    "value": item["requested"],
                    "allowed": list(select.values) if select else [],
                }
            )
        names = ", ".join(str(d["dimension"]) for d in details)
        raise InvalidParameter(
            f"valori non ammessi dal portale: {names}",
            collection=collection.id,
            rejected=details,
            source_url=page.source_url,
            hint=f"osservaprezzi values {collection.id} <dimensione>",
        )

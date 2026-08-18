"""Configurazione centralizzata delle collezioni e delle loro sorgenti.

Ogni collezione dichiara: URL della pagina, dimensioni (nome CLI, nome HTML,
dimensioni genitori da cui dipende il dominio), colonne della tabella dei
risultati e chiave naturale usata per la deduplicazione negli archivi.

Gli identificatori CLI sono in inglese e sono l'unica forma usata da comandi,
opzioni, query YAML e output.
"""

from __future__ import annotations

from dataclasses import dataclass, field

BASE_URL = "https://osservaprezzi.mise.gov.it/prezzi/livelli/"


@dataclass(frozen=True)
class Dimension:
    name: str
    html_name: str
    label: str
    parents: tuple[str, ...] = ()


@dataclass(frozen=True)
class Column:
    name: str
    header: str
    numeric: bool = False


@dataclass(frozen=True)
class CatalogSpec:
    """Come costruire il catalogo dei prodotti di una collezione.

    Il portale non espone il prodotto come filtro: per sapere cosa esiste
    bisogna interrogare una cella e leggere le righe. Questa configurazione dice
    quale dimensione percorrere, quale campo indicizzare e in quale contesto
    farlo, così la ricerca resta una funzione sola per tutte le collezioni.
    """

    dimension: str
    field: str
    context: dict[str, str]
    label: str
    label_plural: str


@dataclass(frozen=True)
class Collection:
    id: str
    title: str
    description: str
    path: str
    dimensions: tuple[Dimension, ...]
    columns: tuple[Column, ...]
    natural_key: tuple[str, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)
    # Campi non presenti nella tabella sorgente, aggiunti dalla CLI per rendere
    # i record incrociabili con altre fonti (codici territoriali ISTAT).
    derived: tuple[Column, ...] = field(default_factory=tuple)
    catalog: CatalogSpec | None = None

    @property
    def url(self) -> str:
        return BASE_URL + self.path

    @property
    def dimension_names(self) -> tuple[str, ...]:
        return tuple(d.name for d in self.dimensions)

    def dimension(self, name: str) -> Dimension | None:
        for d in self.dimensions:
            if d.name == name:
                return d
        return None


COMPARABILITY_WARNING = (
    "La stessa descrizione di prodotto può riferirsi a combinazioni differenti di "
    "varietà, marca, confezione e punto vendita tra province o mesi: i valori "
    "raccolti non costituiscono automaticamente una serie storica comparabile."
)

_YEAR = Dimension("year", "ANNO", "Anno")
_MONTH = Dimension("month", "MESE", "Mese", parents=("year",))
_WEEK = Dimension("week", "SETTIMANA", "Settimana", parents=("year", "month"))

_ORTOFRUTTA_DIMENSIONS = (
    _YEAR,
    _MONTH,
    _WEEK,
    Dimension("market", "f[MERCATO]", "Mercato"),
    Dimension("group", "f[GRUPPO]", "Gruppo"),
)

# I due portali ortofrutticoli usano intestazioni scritte in modo diverso
# (`Varietà` nei mercati italiani, `VARIETA` in quelli europei): gli header
# attesi restano quelli effettivamente pubblicati.
_DESCRIPTOR_NAMES = ("species", "variety", "size", "grade", "packaging", "origin", "unit")

_ORTOFRUTTA_IT_DESCRIPTORS = tuple(
    Column(name, header)
    for name, header in zip(
        _DESCRIPTOR_NAMES,
        ("Specie", "Varietà", "Calibro", "Cat.", "Presentazione", "Origine", "U.M."),
    )
)

_ORTOFRUTTA_EU_DESCRIPTORS = tuple(
    Column(name, header)
    for name, header in zip(
        _DESCRIPTOR_NAMES,
        ("SPECIE", "VARIETA", "CALIBRO", "CAT.", "PRESENTAZIONE", "ORIGINE", "U.M."),
    )
)

_ORTOFRUTTA_KEY = (
    "year",
    "month",
    "week",
    "market",
    "group",
    "species",
    "variety",
    "size",
    "grade",
    "packaging",
    "origin",
    "unit",
)

CONSUMO = Collection(
    id="consumo",
    title="Rilevazioni mensili di beni e servizi di largo consumo",
    description=(
        "Quotazioni minime, massime e medie rilevate per provincia, mese e "
        "tipologia di prodotto."
    ),
    path="beni-e-servizi-di-largo-consumo/archivio-rilevazioni-beni-e-servizi-di-largo-consumo",
    dimensions=(
        _YEAR,
        _MONTH,
        Dimension("province", "f[PROVINCIA]", "Provincia"),
        Dimension("category", "f[TIPO_RECORD_MISE]", "Tipologia di prodotto"),
    ),
    columns=(
        Column("product", "Descrizione Prodotto"),
        Column("price_min", "Quotazione Minima", numeric=True),
        Column("price_max", "Quotazione Massima", numeric=True),
        Column("price_avg", "Quotazione Media", numeric=True),
        Column("category_label", "Tipologia di Prodotto"),
    ),
    natural_key=("year", "month", "province", "category", "product"),
    notes=(COMPARABILITY_WARNING,),
    catalog=CatalogSpec(
        dimension="category",
        field="product",
        # Roma rileva il paniere più ampio: come indice di ricerca è il
        # riferimento che lascia fuori meno prodotti.
        context={"province": "Roma"},
        label="prodotto",
        label_plural="prodotti",
    ),
    derived=(
        Column("province_istat", "Codice ISTAT della provincia (storico)"),
        Column("province_uts", "Codice ISTAT dell'unità territoriale sovracomunale"),
        Column("province_nuts3", "Codice NUTS3 2024"),
    ),
)

ORTOFRUTTA_IT = Collection(
    id="ortofrutta-it",
    title="Prodotti ortofrutticoli all'ingrosso nei mercati italiani",
    description=(
        "Prezzo prevalente, minimo e massimo per settimana, mercato e gruppo "
        "merceologico."
    ),
    path="prodotti-ortofrutticoli-all-ingrosso/mercati-italiani",
    dimensions=_ORTOFRUTTA_DIMENSIONS,
    columns=_ORTOFRUTTA_IT_DESCRIPTORS
    + (
        Column("price_prevalent", "Prezzo prev.", numeric=True),
        Column("price_min", "Prezzo Minimo", numeric=True),
        Column("price_max", "Prezzo Massimo", numeric=True),
    ),
    natural_key=_ORTOFRUTTA_KEY,
    catalog=CatalogSpec(
        dimension="group",
        field="species",
        context={"market": "ROMA"},
        label="specie",
        label_plural="specie",
    ),
)

ORTOFRUTTA_EU = Collection(
    id="ortofrutta-eu",
    title="Prodotti ortofrutticoli all'ingrosso nei mercati europei",
    description=(
        "Prezzo unico per settimana, mercato e gruppo merceologico nei mercati "
        "europei rilevati."
    ),
    path="prodotti-ortofrutticoli-all-ingrosso/mercati-europei",
    dimensions=_ORTOFRUTTA_DIMENSIONS,
    columns=_ORTOFRUTTA_EU_DESCRIPTORS + (Column("price", "PREZZO", numeric=True),),
    natural_key=_ORTOFRUTTA_KEY,
    catalog=CatalogSpec(
        dimension="group",
        field="species",
        context={"market": "PARIGI"},
        label="specie",
        label_plural="specie",
    ),
)

COLLECTIONS: dict[str, Collection] = {
    c.id: c for c in (CONSUMO, ORTOFRUTTA_IT, ORTOFRUTTA_EU)
}


def get_collection(collection_id: str) -> Collection:
    from .errors import InvalidCollection

    try:
        return COLLECTIONS[collection_id]
    except KeyError:
        raise InvalidCollection(
            f"collezione sconosciuta: {collection_id}",
            parameter="collection",
            value=collection_id,
            allowed=sorted(COLLECTIONS),
        ) from None

"""Catalogo dei prodotti: l'indice che il portale non pubblica.

Il prodotto non è un filtro del portale, quindi per sapere in quale categoria
si trovi il salmone bisogna interrogare le categorie e guardare le righe. È il
punto in cui, senza aiuto, si tira a indovinare: questo modulo costruisce una
volta quell'indice, lo tiene nella cache dei metadati e lo usa per rispondere a
«dove sta X» e per completare i filtri di un archivio.

L'indice è **osservato**, non dichiarato: i prodotti rilevati cambiano da
provincia a provincia e da mese a mese. Ogni risposta dichiara quindi il
contesto da cui proviene, e trovare un prodotto qui non garantisce che esista
altrove.
"""

from __future__ import annotations

import time
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .collections import Collection
from .errors import InvalidParameter, NoData

if TYPE_CHECKING:  # pragma: no cover
    from .client import Client

TTL_SECONDS = 7 * 24 * 3600


@dataclass(frozen=True)
class Voce:
    value: str
    parent: str
    parent_label: str


@dataclass(frozen=True)
class Catalogo:
    collection: str
    field: str
    dimension: str
    context: dict[str, str]
    voci: tuple[Voce, ...]

    def cerca(self, testo: str) -> list[Voce]:
        """Corrispondenze per sottostringa, ignorando accenti e maiuscole."""
        ago = normalizza(testo)
        if not ago:
            return []
        esatte = [v for v in self.voci if normalizza(v.value) == ago]
        return esatte or [v for v in self.voci if ago in normalizza(v.value)]


def normalizza(testo: str) -> str:
    senza_accenti = unicodedata.normalize("NFKD", testo).encode("ascii", "ignore").decode()
    return " ".join(senza_accenti.split()).casefold()


def _chiave(collection: Collection, contesto: dict[str, str]) -> str:
    parti = "&".join(f"{k}={contesto[k]}" for k in sorted(contesto))
    return f"catalogo|{collection.id}|{parti}"


def costruisci(
    client: "Client", collection: Collection, context: dict[str, str] | None = None
) -> Catalogo:
    """Percorre le categorie di una cella di riferimento e indicizza le righe.

    Costa una richiesta per categoria — sei per `consumo`, cinque per i mercati
    italiani — e il risultato resta in cache per una settimana.
    """
    if collection.catalog is None:
        raise InvalidParameter(
            f"la collezione {collection.id} non ha un catalogo dei prodotti",
            parameter="collection",
            value=collection.id,
        )
    spec = collection.catalog
    richiesto = {**spec.context, **(context or {})}

    # La chiave non include il periodo, che altrimenti andrebbe chiesto al
    # portale prima di poter guardare in cache: il periodo osservato viene
    # conservato insieme alle voci e restituito con esse.
    chiave = _chiave(collection, richiesto)
    if not client.refresh:
        salvato = client.cache.get(chiave)
        if salvato:
            voci = tuple(
                Voce(v["value"], v["parent"], v["parent_label"]) for v in salvato["values"]
            )
            contesto = salvato.get("context", richiesto)
            return Catalogo(collection.id, spec.field, spec.dimension, contesto, voci)

    # Il periodo di riferimento è l'ultimo pubblicato: un catalogo vecchio
    # descriverebbe un paniere che non esiste più.
    contesto = dict(richiesto)
    predefiniti = client.latest(collection)
    for nome in collection.dimension_names:
        if nome not in contesto and nome != spec.dimension:
            contesto[nome] = predefiniti[nome]

    opzioni, _ = client.values(collection, spec.dimension, contesto)
    voci: list[Voce] = []
    visti: set[tuple[str, str]] = set()
    for opzione in opzioni:
        filtri = {**contesto, spec.dimension: opzione.value}
        try:
            risultato = client.get(collection, filtri)
        except NoData:
            continue
        for record in risultato.records:
            valore = str(record.get(spec.field) or "").strip()
            if not valore or (valore, opzione.value) in visti:
                continue
            visti.add((valore, opzione.value))
            voci.append(Voce(valore, opzione.value, opzione.label))

    voci.sort(key=lambda v: (v.parent, normalizza(v.value)))
    client.cache.set(
        chiave,
        [{"value": v.value, "parent": v.parent, "parent_label": v.parent_label} for v in voci],
        f"{collection.url} ({', '.join(f'{k}={v}' for k, v in sorted(contesto.items()))})",
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        extra={"context": contesto},
    )
    client.cache.flush()
    return Catalogo(collection.id, spec.field, spec.dimension, contesto, tuple(voci))


def risolvi_categoria(
    client: "Client", collection: Collection, testo: str
) -> tuple[str, str]:
    """Dal nome di un prodotto alla coppia (categoria, descrizione completa).

    Se la corrispondenza è unica il filtro si completa da solo; se è ambigua
    l'errore elenca le possibilità, che vengono dai dati e non da un'ipotesi.
    """
    catalogo = costruisci(client, collection)
    trovate = catalogo.cerca(testo)
    if not trovate:
        raise InvalidParameter(
            f"nessun {collection.catalog.label} corrisponde a {testo!r}",
            parameter="product",
            value=testo,
            context=catalogo.context,
            hint=f"osservaprezzi find {collection.id} <testo>",
        )
    categorie = {v.parent for v in trovate}
    if len(trovate) > 1 and len(categorie) > 1:
        raise InvalidParameter(
            f"{testo!r} corrisponde a più {collection.catalog.label_plural}, in categorie diverse",
            parameter="product",
            value=testo,
            matches=[{"value": v.value, catalogo.dimension: v.parent} for v in trovate],
            hint=f"indica --{catalogo.dimension} oppure un testo più preciso",
        )
    if len(trovate) > 1:
        raise InvalidParameter(
            f"{testo!r} corrisponde a più {collection.catalog.label_plural}",
            parameter="product",
            value=testo,
            matches=[v.value for v in trovate],
            hint="usa la descrizione completa",
        )
    voce = trovate[0]
    return voce.parent, voce.value

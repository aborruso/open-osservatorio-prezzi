"""Corrispondenza fra le province di rilevazione e i codici territoriali ISTAT.

Il portale identifica le province solo per nome. Per incrociare questi prezzi
con qualsiasi altra fonte territoriale serve un codice: la tabella in
`data/province_istat.csv` lo fornisce, ed è generata dal SITUAS con
`scripts/refresh_province_istat.py`.

Un nome sconosciuto non è un errore: se il portale aggiunge una provincia, i
campi derivati restano vuoti e il dato viene comunque restituito. Preferiamo un
codice mancante e visibile a un dato non consegnato.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

TABELLA = Path(__file__).parent / "data" / "province_istat.csv"


@lru_cache(maxsize=1)
def _tabella() -> dict[str, dict[str, str]]:
    try:
        with TABELLA.open(encoding="utf-8", newline="") as handle:
            return {riga["province"]: riga for riga in csv.DictReader(handle)}
    except OSError:
        return {}


CAMPI = ("province_istat", "province_uts", "province_nuts3")


def codici(provincia: str) -> dict[str, str | None]:
    """Le codifiche territoriali di una provincia, tutte vuote se sconosciuta.

    Sono tre perché servono a cose diverse: `province_istat` è il codice
    provincia storico (058 per Roma), quello usato nella gran parte dei dataset
    ISTAT; `province_uts` è il codice dell'unità territoriale sovracomunale, che
    per le quindici città metropolitane differisce (258 per Roma);
    `province_nuts3` è la codifica europea. Esporne uno solo significherebbe
    rompere in silenzio metà dei join possibili.
    """
    riga = _tabella().get(provincia) or {}
    return {
        "province_istat": riga.get("istat_code") or None,
        "province_uts": riga.get("uts_code") or None,
        "province_nuts3": riga.get("nuts3") or None,
    }


def scheda(provincia: str) -> dict[str, str] | None:
    """Tutti i dati territoriali disponibili per una provincia."""
    riga = _tabella().get(provincia)
    return dict(riga) if riga else None


def province_note() -> list[str]:
    return list(_tabella())

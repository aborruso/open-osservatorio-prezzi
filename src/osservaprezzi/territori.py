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


def risolvi(valore: str) -> str | None:
    """Traduce un identificatore territoriale nel nome usato dal portale.

    Chi arriva da un dataset ISTAT ha in mano un codice, non il nome: accettare
    `082`, `282`, `ITG12` o `PA` al posto di `Palermo` evita di dover costruire
    una tabella di conversione prima di poter interrogare i prezzi. I nomi non
    possono collidere con i codici, quindi non c'è ambiguità da sciogliere.
    """
    testo = valore.strip()
    if not testo:
        return None
    tabella = _tabella()
    if testo in tabella:
        return testo

    confronto = testo.upper()
    numerico = confronto.zfill(3) if confronto.isdigit() else None
    for nome, riga in tabella.items():
        if confronto == riga["nuts3"].upper() or confronto == riga["plate"].upper():
            return nome
        if numerico and numerico in (riga["istat_code"], riga["uts_code"]):
            return nome
        if confronto == riga["istat_name"].upper():
            return nome
    return None


def sembra_un_codice(valore: str) -> bool:
    """Vero per input che non sono nomi di provincia ma identificatori."""
    testo = valore.strip()
    return bool(testo) and (
        testo.isdigit()
        or (len(testo) == 2 and testo.isalpha())
        or (len(testo) == 5 and testo[:2].upper() == "IT" and testo[2:].isalnum())
    )


def scheda(provincia: str) -> dict[str, str] | None:
    """Tutti i dati territoriali disponibili per una provincia."""
    riga = _tabella().get(provincia)
    return dict(riga) if riga else None


def province_note() -> list[str]:
    return list(_tabella())

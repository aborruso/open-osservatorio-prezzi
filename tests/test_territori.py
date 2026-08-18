"""Codici territoriali ISTAT associati alle province di rilevazione."""

from __future__ import annotations

import pytest

from osservaprezzi.collections import CONSUMO, ORTOFRUTTA_IT
from osservaprezzi.territori import codici, province_note, scheda

FILTRI = {"year": "2025", "month": "5", "province": "Roma", "category": "energia"}


def test_ogni_provincia_del_portale_ha_un_codice(client):
    """Se il portale aggiunge una provincia, la tabella va rigenerata.

    Il test confronta l'elenco vivo dei valori ammessi con la tabella
    distribuita: è il modo per accorgersene senza aspettare una segnalazione.
    """
    opzioni, _ = client.values(CONSUMO, "province")
    portale = {o.value for o in opzioni}
    senza_codice = sorted(
        p for p in portale if not any(codici(p).values())
    )
    assert not senza_codice, (
        "province senza corrispondenza ISTAT: rigenera la tabella con "
        f"scripts/refresh_province_istat.py — {senza_codice}"
    )


def test_le_grafie_del_portale_sono_ricondotte_a_quelle_ufficiali():
    """Quattro province hanno sul portale una grafia diversa da quella ISTAT."""
    assert codici("Aosta")["province_istat"] == "007"
    assert codici("Bolzano")["province_nuts3"] == "ITH10"
    assert codici("Forli")["province_istat"] == "040"
    assert codici("Reggio Emilia")["province_nuts3"] == "ITH53"
    assert scheda("Forli")["istat_name"] == "Forlì-Cesena"


def test_le_citta_metropolitane_hanno_due_codici_diversi():
    """Roma è 058 come provincia e 258 come unità territoriale: servono entrambi."""
    roma = codici("Roma")
    assert roma["province_istat"] == "058"
    assert roma["province_uts"] == "258"
    # Dove non c'è città metropolitana le due codifiche coincidono.
    trento = codici("Trento")
    assert trento["province_istat"] == trento["province_uts"] == "022"


def test_una_provincia_sconosciuta_non_fa_fallire_nulla():
    """Un codice mancante è preferibile a un dato non consegnato."""
    assert codici("Atlantide") == {
        "province_istat": None,
        "province_uts": None,
        "province_nuts3": None,
    }
    assert scheda("Atlantide") is None


def test_i_record_portano_i_codici(client):
    result = client.get(CONSUMO, FILTRI)
    record = result.records[0]
    assert record["province_istat"] == "058"
    assert record["province_uts"] == "258"
    assert record["province_nuts3"] == "ITI43"


def test_le_collezioni_ortofrutticole_non_hanno_codici_territoriali(client):
    """I mercati non sono unità amministrative: nessun codice inventato."""
    assert ORTOFRUTTA_IT.derived == ()
    result = client.get(
        ORTOFRUTTA_IT,
        {"year": "2025", "month": "5", "week": "2", "market": "ROMA", "group": "ORTAGGI"},
    )
    assert "province_istat" not in result.records[0]


def test_la_tabella_copre_le_64_province():
    assert len(province_note()) == 64


def test_una_provincia_si_indica_anche_col_codice():
    """Chi arriva da un dataset ISTAT ha il codice, non il nome."""
    from osservaprezzi.territori import risolvi

    for identificatore in ("Palermo", "082", "82", "282", "ITG12", "itg12", "PA"):
        assert risolvi(identificatore) == "Palermo", identificatore
    # Anche la denominazione ufficiale, che sul portale è scritta diversamente.
    assert risolvi("Reggio nell'Emilia") == "Reggio Emilia"
    assert risolvi("Forlì-Cesena") == "Forli"


def test_il_client_accetta_i_codici_nei_filtri(client):
    from osservaprezzi.client import Client

    normalizzati = Client.normalizza(CONSUMO, {**FILTRI, "province": "ITI43"})
    assert normalizzati["province"] == "Roma"
    # Il resto dei filtri non viene toccato.
    assert normalizzati["category"] == FILTRI["category"]


def test_un_codice_inesistente_e_un_errore_esplicito():
    from osservaprezzi.client import Client
    from osservaprezzi.errors import InvalidParameter

    with pytest.raises(InvalidParameter) as info:
        Client.normalizza(CONSUMO, {**FILTRI, "province": "999"})
    assert "999" in info.value.message
    assert "NUTS3" in info.value.details["hint"]


def test_un_nome_sconosciuto_lo_rifiuta_il_portale():
    """Non è un codice: lasciamo che sia il portale a elencare i valori validi."""
    from osservaprezzi.client import Client

    assert Client.normalizza(CONSUMO, {**FILTRI, "province": "Atlantide"})["province"] == "Atlantide"


def test_le_collezioni_senza_province_non_vengono_toccate():
    from osservaprezzi.client import Client

    filtri = {"year": "2025", "month": "5", "week": "2", "market": "ROMA", "group": "ORTAGGI"}
    assert Client.normalizza(ORTOFRUTTA_IT, filtri) == filtri

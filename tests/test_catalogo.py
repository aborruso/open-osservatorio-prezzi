"""Catalogo dei prodotti: la ricerca che dice in quale categoria sta una voce."""

from __future__ import annotations

import httpx
import pytest

from osservaprezzi.catalogo import costruisci, normalizza, risolvi_categoria
from osservaprezzi.collections import CONSUMO
from osservaprezzi.errors import InvalidParameter

from .conftest import make_client, pagina_echo

DOMINI = {
    "year": ["2025"],
    "month": ["5"],
    "province": ["Roma", "Aosta"],
    "category": ["altri_alim", "energia", "ittici"],
}

PANIERE = {
    "altri_alim": ["Pane Fresco Con Farina Di Grano (1000 Gr)", "Latte Fresco Intero (1 L)"],
    "energia": ["Gasolio Per Auto Con Servizio (1 L)", "Gasolio Per Auto Senza Servizio (1 L)"],
    "ittici": ["Salmone Fresco (1000 Gr)"],
}


@pytest.fixture
def client(tmp_path):
    """Un portale finto che riflette i filtri e ha un paniere noto."""

    def handler(request: httpx.Request) -> httpx.Response:
        filtri = {
            d.name: v
            for d in CONSUMO.dimensions
            if (v := dict(request.url.params).get(d.html_name)) is not None
        }
        prodotti = PANIERE.get(filtri.get("category", ""), [])
        righe = [[p, "1", "2", "1.5", "Etichetta"] for p in prodotti]
        return httpx.Response(200, text=pagina_echo(CONSUMO, filtri, DOMINI, righe))

    return make_client(handler, tmp_path)


def test_il_catalogo_indicizza_i_prodotti_per_categoria(client):
    catalogo = costruisci(client, CONSUMO)
    assert catalogo.field == "product"
    assert catalogo.dimension == "category"
    assert len(catalogo.voci) == 5
    # Il contesto di osservazione è dichiarato: quei prodotti valgono lì.
    assert catalogo.context["province"] == "Roma"


def test_la_ricerca_ignora_accenti_e_maiuscole(client):
    catalogo = costruisci(client, CONSUMO)
    assert catalogo.cerca("SALMONE") == catalogo.cerca("salmone")
    assert len(catalogo.cerca("salmone")) == 1


def test_una_corrispondenza_esatta_batte_le_parziali(client):
    catalogo = costruisci(client, CONSUMO)
    trovate = catalogo.cerca("Gasolio Per Auto Con Servizio (1 L)")
    assert [v.value for v in trovate] == ["Gasolio Per Auto Con Servizio (1 L)"]


def test_il_prodotto_univoco_completa_la_categoria(client):
    categoria, descrizione = risolvi_categoria(client, CONSUMO, "salmone")
    assert categoria == "ittici"
    # Restituisce la descrizione canonica, non il testo cercato.
    assert descrizione == "Salmone Fresco (1000 Gr)"


def test_un_testo_ambiguo_dentro_una_categoria(client):
    with pytest.raises(InvalidParameter) as info:
        risolvi_categoria(client, CONSUMO, "gasolio")
    assert "più prodotti" in info.value.message
    assert len(info.value.details["matches"]) == 2


def test_un_testo_ambiguo_fra_categorie(client):
    with pytest.raises(InvalidParameter) as info:
        risolvi_categoria(client, CONSUMO, "fresc")
    assert "categorie diverse" in info.value.message


def test_un_testo_senza_riscontro_suggerisce_la_ricerca(client):
    with pytest.raises(InvalidParameter) as info:
        risolvi_categoria(client, CONSUMO, "monopattino")
    assert "find" in info.value.details["hint"]


def test_il_catalogo_resta_in_cache(client):
    costruisci(client, CONSUMO)
    prima = client.fetcher.requests_made
    costruisci(client, CONSUMO)
    assert client.fetcher.requests_made == prima


def test_una_categoria_senza_dati_non_interrompe_la_costruzione(tmp_path):
    """Se una categoria non ha rilevazioni, il catalogo prosegue con le altre."""

    def handler(request: httpx.Request) -> httpx.Response:
        filtri = {
            d.name: v
            for d in CONSUMO.dimensions
            if (v := dict(request.url.params).get(d.html_name)) is not None
        }
        categoria = filtri.get("category", "")
        prodotti = [] if categoria == "energia" else PANIERE.get(categoria, [])
        righe = [[p, "1", "2", "1.5", "Etichetta"] for p in prodotti]
        return httpx.Response(200, text=pagina_echo(CONSUMO, filtri, DOMINI, righe))

    client = make_client(handler, tmp_path)
    catalogo = costruisci(client, CONSUMO)
    assert {v.parent for v in catalogo.voci} == {"altri_alim", "ittici"}


def test_normalizzazione():
    assert normalizza("  Varietà   MISTA ") == "varieta mista"

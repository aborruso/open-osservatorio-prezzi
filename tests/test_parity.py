"""Parità fra controlli dei form HTML e parametri della CLI.

Ogni controllo visibile e abilitato dei form dati deve avere un parametro CLI
corrispondente; gli unici controlli ammessi senza parametro pubblico sono
quelli tecnici (il pulsante di invio), che l'adattatore non usa nemmeno.
"""

from __future__ import annotations

import pytest

from osservaprezzi.cli import FILTER_OPTIONS
from osservaprezzi.collections import COLLECTIONS
from osservaprezzi.forms import parse_document, parse_form

from .conftest import read_fixture

FIXTURE_BASE = {
    "consumo": "consumo-base",
    "ortofrutta-it": "ortofrutta-it-base",
    "ortofrutta-eu": "ortofrutta-eu-base",
}

CONTROLLI_TECNICI = {"submit"}


@pytest.mark.parametrize("collection_id", sorted(COLLECTIONS))
def test_ogni_select_del_form_ha_un_parametro_cli(collection_id):
    collection = COLLECTIONS[collection_id]
    document = parse_document(read_fixture(FIXTURE_BASE[collection_id]))
    selects = parse_form(document)

    attesi = {d.html_name for d in collection.dimensions}
    assert set(selects) == attesi

    for dimension in collection.dimensions:
        assert dimension.name in FILTER_OPTIONS


@pytest.mark.parametrize("collection_id", sorted(COLLECTIONS))
def test_nessun_altro_controllo_utente_resta_scoperto(collection_id):
    document = parse_document(read_fixture(FIXTURE_BASE[collection_id]))
    form = document.xpath('//form[@id="search-form"]')[0]
    controlli = form.xpath(".//input | .//textarea | .//button")
    for controllo in controlli:
        nome = controllo.get("name") or ""
        assert nome in CONTROLLI_TECNICI, f"controllo non mappato: {nome}"
        assert controllo.get("type") == "submit"


@pytest.mark.parametrize("collection_id", sorted(COLLECTIONS))
def test_i_select_sono_a_scelta_singola_e_abilitati(collection_id):
    document = parse_document(read_fixture(FIXTURE_BASE[collection_id]))
    form = document.xpath('//form[@id="search-form"]')[0]
    for select in form.xpath(".//select"):
        assert select.get("multiple") is None
        assert select.get("disabled") is None

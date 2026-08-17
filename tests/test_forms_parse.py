"""Lettura dei form e della tabella dei risultati."""

from __future__ import annotations

import pytest

from osservaprezzi.collections import CONSUMO, ORTOFRUTTA_EU, ORTOFRUTTA_IT
from osservaprezzi.errors import ContractChanged
from osservaprezzi.forms import check_echo, parse_document, parse_form
from osservaprezzi.parse import parse_table

from .conftest import read_fixture


def test_option_selezionata_con_attributi_in_ordine_qualsiasi():
    html = (
        '<html><body><form id="search-form"><select name="ANNO">'
        "<option  value=\"2024\">2024</option>"
        "<option  selected='selected'  value=\"2025\">2025</option>"
        "</select></form></body></html>"
    )
    selects = parse_form(parse_document(html))
    assert selects["ANNO"].selected == "2025"
    assert selects["ANNO"].values == ("2024", "2025")


def test_echo_riconosce_il_filtro_non_applicato():
    document = parse_document(read_fixture("consumo-invalid"))
    selects = parse_form(document)
    rejected = check_echo(
        selects,
        {
            "ANNO": "2025",
            "MESE": "5",
            "f[PROVINCIA]": "Atlantide",
            "f[TIPO_RECORD_MISE]": "energia",
        },
    )
    assert [r["html_name"] for r in rejected] == ["f[PROVINCIA]"]
    assert rejected[0]["applied"] is None


def test_tabella_consumo():
    rows = parse_table(parse_document(read_fixture("consumo-ok")), CONSUMO)
    assert len(rows) == 6
    assert rows[0]["product"] == "Gasolio Per Auto Con Servizio Alla Pompa (1 L)"
    assert rows[0]["price_min"] == 1.489
    assert rows[0]["category_label"] == "Energetici"


def test_celle_vuote_conservate_come_null():
    rows = parse_table(parse_document(read_fixture("ortofrutta-it-ok")), ORTOFRUTTA_IT)
    assert rows[0]["variety"] is None
    assert rows[0]["unit"] is None
    assert rows[0]["price_prevalent"] == 1.8


def test_tabella_europea_ha_un_solo_prezzo():
    rows = parse_table(parse_document(read_fixture("ortofrutta-eu-ok")), ORTOFRUTTA_EU)
    assert "price" in rows[0]
    assert "price_prevalent" not in rows[0]


def test_tabella_vuota_non_e_un_errore_di_contratto():
    rows = parse_table(parse_document(read_fixture("ortofrutta-it-empty")), ORTOFRUTTA_IT)
    assert rows == []


def test_intestazione_cambiata_e_contratto_cambiato():
    with pytest.raises(ContractChanged):
        parse_table(parse_document(read_fixture("consumo-broken")), CONSUMO)

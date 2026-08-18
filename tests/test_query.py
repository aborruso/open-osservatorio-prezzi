"""Query salvate in YAML."""

from __future__ import annotations

import pytest

from osservaprezzi.collections import ORTOFRUTTA_IT
from osservaprezzi.errors import InvalidCollection, InvalidQuery
from osservaprezzi.query import load

VALIDA = """
version: 1
collection: ortofrutta-it
filters:
  year: 2025
  month: 5
  week: 2
  market: ROMA
  group: ORTAGGI
format: json
"""


def scrivi(tmp_path, testo):
    path = tmp_path / "query.yaml"
    path.write_text(testo, encoding="utf-8")
    return path


def test_query_valida(tmp_path):
    saved = load(scrivi(tmp_path, VALIDA))
    assert saved.collection == "ortofrutta-it"
    assert saved.filters == {
        "year": "2025",
        "month": "5",
        "week": "2",
        "market": "ROMA",
        "group": "ORTAGGI",
    }
    assert saved.format == "json"


def test_versione_non_supportata(tmp_path):
    with pytest.raises(InvalidQuery) as info:
        load(scrivi(tmp_path, VALIDA.replace("version: 1", "version: 2")))
    assert info.value.details["supported"] == [1]


def test_chiave_sconosciuta(tmp_path):
    with pytest.raises(InvalidQuery) as info:
        load(scrivi(tmp_path, VALIDA + "\ncursore: 3\n"))
    assert info.value.details["unknown"] == ["cursore"]


def test_filtro_sconosciuto(tmp_path):
    with pytest.raises(InvalidQuery) as info:
        load(scrivi(tmp_path, VALIDA.replace("  market: ROMA", "  provincia: Roma")))
    assert info.value.details["unknown"] == ["provincia"]
    assert set(info.value.details["allowed"]) == set(ORTOFRUTTA_IT.dimension_names)


def test_collezione_sconosciuta(tmp_path):
    with pytest.raises(InvalidCollection):
        load(scrivi(tmp_path, VALIDA.replace("ortofrutta-it", "carburanti")))


def test_formato_non_supportato(tmp_path):
    with pytest.raises(InvalidQuery):
        load(scrivi(tmp_path, VALIDA.replace("format: json", "format: xlsx")))


def test_limite_non_valido(tmp_path):
    with pytest.raises(InvalidQuery):
        load(scrivi(tmp_path, VALIDA + "\nlimit: 0\n"))


def test_yaml_non_valido(tmp_path):
    with pytest.raises(InvalidQuery):
        load(scrivi(tmp_path, "version: 1\n  filters: ["))

"""Scoperta, validazione e recupero."""

from __future__ import annotations

import httpx
import pytest

from osservaprezzi.collections import CONSUMO, ORTOFRUTTA_IT
from osservaprezzi.errors import (
    InvalidDimension,
    InvalidParameter,
    NoData,
    ServiceUnavailable,
)

from .conftest import make_client, read_fixture

CONSUMO_FILTERS = {
    "year": "2025",
    "month": "5",
    "province": "Roma",
    "category": "energia",
}


def test_get_restituisce_record_con_provenienza(client):
    result = client.get(CONSUMO, CONSUMO_FILTERS)
    assert len(result.records) == 6
    record = result.records[0]
    assert record["collection"] == "consumo"
    assert record["source_url"].startswith("https://osservaprezzi.mise.gov.it/")
    assert record["retrieved_at"].endswith("Z")
    assert record["province"] == "Roma"


def test_limite_applicato(client):
    result = client.get(CONSUMO, CONSUMO_FILTERS, limit=2)
    assert len(result.records) == 2


def test_filtri_mancanti(client):
    with pytest.raises(InvalidParameter) as info:
        client.get(CONSUMO, {"year": "2025"})
    assert info.value.details["missing"] == ["month", "province", "category"]


def test_valore_non_ammesso_distinto_da_assenza_di_dati(client):
    with pytest.raises(InvalidParameter) as info:
        client.get(CONSUMO, {**CONSUMO_FILTERS, "province": "Atlantide"})
    rejected = info.value.details["rejected"][0]
    assert rejected["dimension"] == "province"
    assert "Roma" in rejected["allowed"]


def test_nessun_dato(client):
    with pytest.raises(NoData):
        client.get(
            ORTOFRUTTA_IT,
            {
                "year": "2025",
                "month": "5",
                "week": "2",
                "market": "CATANIA",
                "group": "PRODOTTI SECCHI",
            },
        )


def test_values_richiede_i_genitori(client):
    with pytest.raises(InvalidParameter) as info:
        client.values(ORTOFRUTTA_IT, "week")
    assert info.value.details["missing"] == ["year", "month"]


def test_values_dimensione_sconosciuta(client):
    with pytest.raises(InvalidDimension):
        client.values(CONSUMO, "market")


def test_values_usa_la_cache_alla_seconda_chiamata(client):
    client.values(CONSUMO, "province")
    prima = client.fetcher.requests_made
    _, meta = client.values(CONSUMO, "province")
    assert client.fetcher.requests_made == prima
    assert meta["cached"] == "true"


def test_values_month_passa_i_filtri_genitori(tmp_path):
    visto: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        visto.append(str(request.url))
        return httpx.Response(200, text=read_fixture("consumo-ok"))

    client = make_client(handler, tmp_path)
    client.values(CONSUMO, "month", {"year": "2025"})
    assert "ANNO=2025" in visto[0]


def test_servizio_indisponibile_dopo_i_retry(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="")

    client = make_client(handler, tmp_path)
    client.fetcher.retries = 1
    with pytest.raises(ServiceUnavailable) as info:
        client.get(CONSUMO, CONSUMO_FILTERS)
    assert info.value.retryable is True
    assert info.value.exit_code == 5


def test_pagina_con_filtro_rifiutato_non_popola_la_cache(client):
    with pytest.raises(InvalidParameter):
        client.get(CONSUMO, {**CONSUMO_FILTERS, "province": "Atlantide"})
    assert client.cache._load() == {}

"""Archivi on-demand: piano, limiti, manifest, deduplicazione, ripresa."""

from __future__ import annotations

import json

import httpx
import pytest

from osservaprezzi.archive import build_plan, normalize_product, run_archive
from osservaprezzi.collections import CONSUMO
from osservaprezzi.errors import InvalidParameter

from .conftest import make_client

PROVINCE = ["Alessandria", "Roma", "Torino"]
CATEGORIE = ["altri_alim", "energia"]
DOMINI = {
    "ANNO": ["2025"],
    "MESE": ["5"],
    "f[PROVINCIA]": PROVINCE,
    "f[TIPO_RECORD_MISE]": CATEGORIE,
}

PRODOTTI = {
    "Alessandria": [("Pane Fresco Con Farina Di Grano (1000 Gr)", "3.19")],
    "Roma": [
        ("  pane   fresco con farina di grano (1000 gr) ", "3.50"),
        ("Prosciutto Cotto (1000 Gr)", "18.5"),
    ],
    "Torino": [],
}


def pagina(filters: dict[str, str]) -> str:
    """Pagina di prova con echo dei filtri e tabella coerenti."""
    select_html = []
    for nome, valori in DOMINI.items():
        opzioni = "".join(
            "<option {} value=\"{}\">{}</option>".format(
                "selected='selected'" if filters.get(nome) == v else "", v, v
            )
            for v in valori
        )
        select_html.append(f'<select name="{nome}">{opzioni}</select>')

    intestazioni = "".join(f"<th>{c.header}</th>" for c in CONSUMO.columns)
    righe = "".join(
        f"<tr><td>{descrizione}</td><td>{prezzo}</td><td>{prezzo}</td>"
        f"<td>{prezzo}</td><td>Alimentari</td></tr>"
        for descrizione, prezzo in PRODOTTI.get(filters.get("f[PROVINCIA]", ""), [])
    )
    return (
        '<html><body><form id="search-form">'
        + "".join(select_html)
        + "</form>"
        + f'<table id="id-table-results"><thead><tr>{intestazioni}</tr></thead>'
        + f"<tbody>{righe}</tbody></table></body></html>"
    )


@pytest.fixture
def client(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=pagina(dict(request.url.params)))

    return make_client(handler, tmp_path)


FILTRI = {"year": "2025", "month": "5", "category": "altri_alim"}


def test_piano_espande_solo_le_dimensioni_richieste(client):
    plan = build_plan(client, CONSUMO, FILTRI, ["province"])
    assert plan.request_count == 3
    assert plan.expanded == {"province": PROVINCE}
    assert all(c["category"] == "altri_alim" for c in plan.combinations)


def test_piano_rifiuta_dimensioni_non_coperte(client):
    with pytest.raises(InvalidParameter) as info:
        build_plan(client, CONSUMO, {"year": "2025", "month": "5"}, ["province"])
    assert info.value.details["missing"] == ["category"]


def test_piano_rifiuta_dimensione_filtrata_ed_espansa(client):
    with pytest.raises(InvalidParameter):
        build_plan(client, CONSUMO, {**FILTRI, "province": "Roma"}, ["province"])


def test_espansione_multipla_moltiplica_le_richieste(client):
    plan = build_plan(client, CONSUMO, {"year": "2025", "month": "5"}, ["province", "category"])
    assert plan.request_count == len(PROVINCE) * len(CATEGORIE)


def test_archivio_completo_con_manifest(client, tmp_path):
    plan = build_plan(client, CONSUMO, FILTRI, ["province"])
    result = run_archive(client, CONSUMO, plan, tmp_path / "archivio")
    assert result.status == "complete"
    assert result.row_count == 3

    manifest = json.loads((tmp_path / "archivio" / "manifest.json").read_text("utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["requests"] == {"planned": 3, "completed": 3, "failed": 0}
    assert manifest["natural_key"] == list(CONSUMO.natural_key)
    assert manifest["notes"]
    esiti = {r["filters"]["province"]: r["status"] for r in manifest["results"]}
    assert esiti == {"Alessandria": "ok", "Roma": "ok", "Torino": "no_data"}


def test_filtro_prodotto_locale_con_normalizzazione(client, tmp_path):
    plan = build_plan(
        client,
        CONSUMO,
        FILTRI,
        ["province"],
        product="Pane Fresco Con Farina Di Grano (1000 Gr)",
    )
    result = run_archive(client, CONSUMO, plan, tmp_path / "pane")
    assert result.row_count == 2

    manifest = json.loads((tmp_path / "pane" / "manifest.json").read_text("utf-8"))
    assert manifest["product_filter"]["value"].startswith("Pane Fresco")
    assert "casefold" in manifest["product_filter"]["rule"]
    esiti = {r["filters"]["province"]: r["status"] for r in manifest["results"]}
    assert esiti["Roma"] == "ok"
    assert esiti["Torino"] == "no_data"


def test_deduplicazione_per_chiave_naturale(client, tmp_path):
    plan = build_plan(client, CONSUMO, FILTRI, ["province"])
    plan.combinations.append(dict(plan.combinations[0]))
    result = run_archive(client, CONSUMO, plan, tmp_path / "dup")
    assert result.row_count == 3


def test_ripresa_ripete_solo_le_richieste_fallite(tmp_path):
    stato = {"fallisci": True}

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        if params.get("f[PROVINCIA]") == "Torino" and stato["fallisci"]:
            return httpx.Response(503, text="")
        return httpx.Response(200, text=pagina(params))

    client = make_client(handler, tmp_path)
    client.fetcher.retries = 0
    plan = build_plan(client, CONSUMO, FILTRI, ["province"])
    primo = run_archive(client, CONSUMO, plan, tmp_path / "archivio")
    assert primo.status == "partial"
    assert primo.failed == 1

    stato["fallisci"] = False
    prima_della_ripresa = client.fetcher.requests_made
    secondo = run_archive(client, CONSUMO, plan, tmp_path / "archivio", resume=True)
    assert secondo.status == "complete"
    assert client.fetcher.requests_made - prima_della_ripresa == 1
    assert secondo.row_count == primo.row_count


def test_normalizzazione_prodotto():
    assert normalize_product("  Pane   FRESCO ") == "pane fresco"

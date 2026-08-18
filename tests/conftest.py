"""Fixture di test: nessun accesso di rete, solo HTML sanificato su disco."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from osservaprezzi.cache import MetadataCache
from osservaprezzi.client import Client
from osservaprezzi.http import Fetcher

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    """I test non toccano la rete: niente lock condiviso né cache dell'utente.

    Il gate di serializzazione ha test propri in `test_gate.py`.
    """
    monkeypatch.setenv("OSSERVAPREZZI_NO_LOCK", "1")
    monkeypatch.setenv("OSSERVAPREZZI_CACHE_DIR", str(tmp_path / "cache-utente"))


def read_fixture(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


def _fixture_for(request: httpx.Request) -> str:
    path = request.url.path
    params = request.url.params
    if "beni-e-servizi" in path:
        if params.get("f[PROVINCIA]") == "Atlantide":
            return "consumo-invalid"
        return "consumo-ok" if "ANNO" in params else "consumo-base"
    if "mercati-italiani" in path:
        if params.get("f[MERCATO]") == "CATANIA":
            return "ortofrutta-it-empty"
        return "ortofrutta-it-ok" if "ANNO" in params else "ortofrutta-it-base"
    if "mercati-europei" in path:
        return "ortofrutta-eu-ok" if "ANNO" in params else "ortofrutta-eu-base"
    raise AssertionError(f"URL non previsto nei test: {request.url}")


@pytest.fixture
def transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=read_fixture(_fixture_for(request)))

    return httpx.MockTransport(handler)


@pytest.fixture
def client(transport: httpx.MockTransport, tmp_path: Path) -> Client:
    http_client = httpx.Client(transport=transport)
    fetcher = Fetcher(client=http_client)
    return Client(fetcher, MetadataCache(tmp_path / "cache"))


def make_client(handler, tmp_path: Path) -> Client:
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    return Client(Fetcher(client=http_client), MetadataCache(tmp_path / "cache"))


def pagina_echo(collection, filters: dict[str, str], domini: dict[str, list[str]], righe: list[list[str]]) -> str:
    """HTML sintetico che riflette i filtri richiesti e le righe indicate.

    Serve ai test in cui la risposta deve dipendere dalla domanda: il portale
    riflette sempre i filtri applicati, e senza quell'eco la CLI — a ragione —
    rifiuta la pagina.
    """
    select_html = []
    for dimension in collection.dimensions:
        valori = domini.get(dimension.name, [])
        opzioni = "".join(
            "<option {} value=\"{}\">{}</option>".format(
                "selected='selected'" if filters.get(dimension.name) == v else "", v, v
            )
            for v in valori
        )
        select_html.append(f'<select name="{dimension.html_name}">{opzioni}</select>')

    intestazioni = "".join(f"<th>{c.header}</th>" for c in collection.columns)
    corpo = "".join(
        "<tr>" + "".join(f"<td>{cella}</td>" for cella in riga) + "</tr>" for riga in righe
    )
    return (
        '<html><body><form id="search-form">'
        + "".join(select_html)
        + "</form>"
        + f'<table id="id-table-results"><thead><tr>{intestazioni}</tr></thead>'
        + f"<tbody>{corpo}</tbody></table></body></html>"
    )

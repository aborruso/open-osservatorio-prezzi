"""Fixture di test: nessun accesso di rete, solo HTML sanificato su disco."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from osservaprezzi.cache import MetadataCache
from osservaprezzi.client import Client
from osservaprezzi.http import Fetcher

FIXTURES = Path(__file__).parent / "fixtures"


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

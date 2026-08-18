"""Contratti di output: equivalenza JSON/CSV, purezza di stdout, codici di uscita."""

from __future__ import annotations

import csv
import io
import json

import pytest
from typer.testing import CliRunner

from osservaprezzi import cli as cli_module
from osservaprezzi.cache import MetadataCache
from osservaprezzi.client import Client
from osservaprezzi.http import Fetcher
from osservaprezzi.render import to_csv, to_json

from .conftest import _fixture_for, read_fixture

runner = CliRunner()


@pytest.fixture(autouse=True)
def cli_offline(monkeypatch, tmp_path):
    """La CLI usa il trasporto di prova e una cache temporanea."""
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=read_fixture(_fixture_for(request)))

    def make_client(timeout, retries, pause, refresh, verbose, lock_timeout=0):
        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        fetcher = Fetcher(client=http_client, verbose=verbose)
        cache = MetadataCache(tmp_path / "cache")
        return Client(fetcher, cache, refresh=refresh), cache, fetcher

    monkeypatch.setattr(cli_module, "_make_client", make_client)


GET_CONSUMO = [
    "get",
    "consumo",
    "--year",
    "2025",
    "--month",
    "5",
    "--province",
    "Roma",
    "--category",
    "energia",
]


def test_json_e_csv_rappresentano_gli_stessi_record():
    as_json = runner.invoke(cli_module.app, GET_CONSUMO + ["--json"])
    as_csv = runner.invoke(cli_module.app, GET_CONSUMO + ["--csv"])
    assert as_json.exit_code == 0 and as_csv.exit_code == 0

    records = json.loads(as_json.stdout)["records"]
    righe = list(csv.DictReader(io.StringIO(as_csv.stdout)))
    for record, riga in zip(records, righe):
        record.pop("retrieved_at"), riga.pop("retrieved_at")
    assert len(records) == len(righe)
    for atteso, riga in zip(records, righe):
        for campo, valore in atteso.items():
            if valore is None:
                assert riga[campo] == ""
            elif isinstance(valore, float):
                assert riga[campo] == repr(valore)
            else:
                assert riga[campo] == str(valore)


def test_i_valori_nulli_sopravvivono_nei_due_formati():
    comando = [
        "get",
        "ortofrutta-it",
        "--year",
        "2025",
        "--month",
        "5",
        "--week",
        "2",
        "--market",
        "ROMA",
        "--group",
        "ORTAGGI",
        "--limit",
        "1",
    ]
    as_json = runner.invoke(cli_module.app, comando + ["--json"])
    as_csv = runner.invoke(cli_module.app, comando + ["--csv"])
    record = json.loads(as_json.stdout)["records"][0]
    riga = next(csv.DictReader(io.StringIO(as_csv.stdout)))
    assert record["variety"] is None
    assert riga["variety"] == ""


def test_verbose_non_sporca_stdout():
    result = runner.invoke(cli_module.app, GET_CONSUMO + ["--csv", "--verbose"])
    assert result.exit_code == 0
    assert "GET " not in result.stdout
    assert "GET " in result.stderr


def test_errore_json_su_stderr_e_stdout_vuoto():
    result = runner.invoke(
        cli_module.app,
        ["get", "consumo", "--year", "2025", "--json"],
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    errore = json.loads(result.stderr)
    assert errore["code"] == "invalid_parameter"
    assert errore["retryable"] is False
    assert errore["details"]["missing"] == ["month", "province", "category"]


def test_nessun_dato_ha_codice_dedicato():
    result = runner.invoke(
        cli_module.app,
        [
            "get",
            "ortofrutta-it",
            "--year",
            "2025",
            "--month",
            "5",
            "--week",
            "2",
            "--market",
            "CATANIA",
            "--group",
            "PRODOTTI SECCHI",
            "--json",
        ],
    )
    assert result.exit_code == 3
    assert json.loads(result.stderr)["code"] == "no_data"


def test_collezione_sconosciuta():
    result = runner.invoke(cli_module.app, ["describe", "carburanti", "--json"])
    assert result.exit_code == 2
    assert json.loads(result.stderr)["code"] == "invalid_collection"


def test_query_salvata_equivale_al_comando_get(tmp_path):
    query = tmp_path / "q.yaml"
    query.write_text(
        "version: 1\ncollection: consumo\nfilters:\n"
        "  year: 2025\n  month: 5\n  province: Roma\n  category: energia\n"
        "format: json\n",
        encoding="utf-8",
    )
    da_query = runner.invoke(cli_module.app, ["run", str(query)])
    da_get = runner.invoke(cli_module.app, GET_CONSUMO + ["--json"])
    assert da_query.exit_code == 0
    def senza_istante(payload):
        return [
            {k: v for k, v in r.items() if k != "retrieved_at"}
            for r in json.loads(payload)["records"]
        ]

    assert senza_istante(da_query.stdout) == senza_istante(da_get.stdout)


def test_scrittura_su_file(tmp_path):
    destinazione = tmp_path / "dati.csv"
    result = runner.invoke(
        cli_module.app, GET_CONSUMO + ["--csv", "--output", str(destinazione)]
    )
    assert result.exit_code == 0
    assert result.stdout == ""
    assert destinazione.read_text(encoding="utf-8").startswith("year,month,")


def test_catalog_elenca_le_tre_collezioni():
    result = runner.invoke(cli_module.app, ["catalog", "--json"])
    payload = json.loads(result.stdout)
    assert [c["id"] for c in payload["collections"]] == [
        "consumo",
        "ortofrutta-it",
        "ortofrutta-eu",
    ]
    assert payload["next_step"].startswith("osservaprezzi describe")


def test_version_espone_schema():
    result = runner.invoke(cli_module.app, ["version", "--json"])
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1


def test_ordine_stabile_dei_campi():
    record = {"b": None, "a": 1.5}
    assert to_csv([record]).splitlines()[0] == "b,a"
    assert list(json.loads(to_json([record]))[0]) == ["b", "a"]


ARCHIVIO_CONSUMO = [
    "archive",
    "consumo",
    "--year",
    "2025",
    "--month",
    "5",
    "--category",
    "energia",
    "--all",
    "province",
]


def test_piano_ispezionabile_senza_eseguirlo():
    result = runner.invoke(cli_module.app, ARCHIVIO_CONSUMO + ["--dry-run", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["plan"]["planned_requests"] == 64
    assert payload["plan"]["expanded"]["province"][0] == "Alessandria"
    assert payload["notes"]


def test_limite_di_richieste_blocca_l_avvio():
    result = runner.invoke(
        cli_module.app, ARCHIVIO_CONSUMO + ["--max-requests", "10", "--json"]
    )
    assert result.exit_code == 2
    errore = json.loads(result.stderr)
    assert errore["details"]["planned"] == 64
    assert errore["details"]["limit"] == 10


def test_prodotto_senza_categoria_e_rifiutato():
    result = runner.invoke(
        cli_module.app,
        [
            "archive",
            "consumo",
            "--year",
            "2025",
            "--month",
            "5",
            "--all",
            "province",
            "--all",
            "category",
            "--product",
            "Pane Fresco Con Farina Di Grano (1000 Gr)",
            "--json",
        ],
    )
    assert result.exit_code == 2
    assert json.loads(result.stderr)["details"]["parameter"] == "product"


def test_latest_registra_i_default_nella_provenienza(monkeypatch, tmp_path):
    import httpx

    from osservaprezzi.cache import MetadataCache as Cache
    from osservaprezzi.client import Client as ClientClass

    def handler(request: httpx.Request) -> httpx.Response:
        # Pagina che espone come predefiniti gli stessi filtri che poi riflette.
        return httpx.Response(200, text=read_fixture("consumo-ok"))

    def make_client(timeout, retries, pause, refresh, verbose, lock_timeout=0):
        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        cache = Cache(tmp_path / "latest")
        fetcher = Fetcher(client=http_client, verbose=verbose)
        return ClientClass(fetcher, cache, refresh=refresh), cache, fetcher

    monkeypatch.setattr(cli_module, "_make_client", make_client)
    result = runner.invoke(
        cli_module.app, ["get", "consumo", "--latest", "--csv", "--limit", "1"]
    )
    assert result.exit_code == 0
    riga = next(csv.DictReader(io.StringIO(result.stdout)))
    assert set(riga["defaults_used"].split(",")) == {
        "year",
        "month",
        "province",
        "category",
    }


def test_senza_latest_la_provenienza_non_dichiara_default():
    result = runner.invoke(cli_module.app, GET_CONSUMO + ["--csv", "--limit", "1"])
    riga = next(csv.DictReader(io.StringIO(result.stdout)))
    assert riga["defaults_used"] == ""


def test_archivio_parziale_esce_con_codice_dedicato(tmp_path, monkeypatch):
    import httpx

    from osservaprezzi.cache import MetadataCache as Cache
    from osservaprezzi.client import Client as ClientClass

    def handler(request: httpx.Request) -> httpx.Response:
        if dict(request.url.params).get("f[GRUPPO]") == "ORTAGGI":
            return httpx.Response(503, text="")
        return httpx.Response(200, text=read_fixture(_fixture_for(request)))

    def make_client(timeout, retries, pause, refresh, verbose, lock_timeout=0):
        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        fetcher = Fetcher(client=http_client, retries=0, verbose=verbose)
        return ClientClass(fetcher, Cache(tmp_path / "c"), refresh=refresh), Cache(
            tmp_path / "c"
        ), fetcher

    monkeypatch.setattr(cli_module, "_make_client", make_client)

    destinazione = tmp_path / "archivio"
    result = runner.invoke(
        cli_module.app,
        [
            "archive",
            "ortofrutta-eu",
            "--year",
            "2025",
            "--month",
            "5",
            "--week",
            "2",
            "--market",
            "PARIGI",
            "--all",
            "group",
            "--output",
            str(destinazione),
            "--json",
        ],
    )
    assert result.exit_code == 6
    sommario = json.loads(result.stdout)
    assert sommario["status"] == "partial"
    assert sommario["requests"]["failed"] >= 1
    manifest = json.loads((destinazione / "manifest.json").read_text("utf-8"))
    assert manifest["status"] == "partial"


def test_catalog_in_tabella_mostra_l_identificatore():
    result = runner.invoke(cli_module.app, ["catalog"])
    assert result.stdout.splitlines()[0].startswith("collection")
    assert "ortofrutta-eu" in result.stdout


def test_get_in_tabella_nasconde_la_provenienza():
    result = runner.invoke(cli_module.app, GET_CONSUMO)
    intestazione = result.stdout.splitlines()[0]
    assert "source_url" not in intestazione
    assert intestazione.startswith("year")


@pytest.mark.parametrize("opzioni", [[], ["--agent"], ["--json"], ["--pretty"]])
def test_agent_context_accetta_le_opzioni_degli_altri_comandi(opzioni):
    result = runner.invoke(cli_module.app, ["agent-context", *opzioni])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["tool"] == "osservaprezzi"


def test_agent_context_descrive_il_contratto():
    result = runner.invoke(cli_module.app, ["agent-context"])
    assert result.exit_code == 0
    contesto = json.loads(result.stdout)
    assert [c["id"] for c in contesto["collections"]] == [
        "consumo",
        "ortofrutta-it",
        "ortofrutta-eu",
    ]
    assert set(contesto["exit_codes"]) == {"0", "2", "3", "4", "5", "6"}
    assert contesto["workflow"][0].startswith("osservaprezzi catalog")
    settimana = next(
        d
        for c in contesto["collections"]
        if c["id"] == "ortofrutta-it"
        for d in c["dimensions"]
        if d["name"] == "week"
    )
    assert settimana["depends_on"] == ["year", "month"]


def test_agent_equivale_a_json_sui_dati():
    con_agent = runner.invoke(cli_module.app, GET_CONSUMO + ["--agent"])
    con_json = runner.invoke(cli_module.app, GET_CONSUMO + ["--json"])
    def senza_istante(payload):
        return [
            {k: v for k, v in r.items() if k != "retrieved_at"}
            for r in json.loads(payload)["records"]
        ]

    assert senza_istante(con_agent.stdout) == senza_istante(con_json.stdout)


def test_agent_produce_errori_json():
    result = runner.invoke(cli_module.app, ["get", "consumo", "--year", "2025", "--agent"])
    assert result.exit_code == 2
    assert json.loads(result.stderr)["code"] == "invalid_parameter"


def test_ogni_comando_ha_esempi_nell_help():
    for comando in [
        "catalog",
        "describe",
        "values",
        "get",
        "run",
        "archive",
        "agent-context",
    ]:
        result = runner.invoke(cli_module.app, [comando, "--help"])
        assert "osservaprezzi" in result.stdout, comando
        assert "Esempi" in result.stdout, comando


def _testo_help(result) -> str:
    """Help senza cornici Rich, per verificare le frasi che vanno a capo."""
    return " ".join(result.stdout.replace("│", " ").split())


def test_le_opzioni_filtro_dichiarano_la_collezione():
    result = runner.invoke(cli_module.app, ["get", "--help"])
    testo = _testo_help(result)
    assert "Solo consumo." in testo
    assert "Solo ortofrutta-it e ortofrutta-eu." in testo

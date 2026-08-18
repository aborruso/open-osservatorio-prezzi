"""Serializzazione fra processi: una sola esecuzione alla volta sul portale."""

from __future__ import annotations

import multiprocessing
import time

import pytest

from osservaprezzi.errors import ServiceUnavailable
from osservaprezzi.gate import RequestGate, lock_path


@pytest.fixture(autouse=True)
def cache_isolata(monkeypatch, tmp_path):
    monkeypatch.setenv("OSSERVAPREZZI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("OSSERVAPREZZI_NO_LOCK", raising=False)


def _occupa_lo_slot(cache_dir: str, durata: float, pronto, fine) -> None:
    import os

    os.environ["OSSERVAPREZZI_CACHE_DIR"] = cache_dir
    os.environ.pop("OSSERVAPREZZI_NO_LOCK", None)
    from osservaprezzi.gate import RequestGate as Gate

    with Gate(min_interval=0).slot():
        pronto.set()
        time.sleep(durata)
    fine.set()


def test_una_seconda_esecuzione_attende_la_prima(tmp_path, monkeypatch):
    cache_dir = str(tmp_path / "cache")
    monkeypatch.setenv("OSSERVAPREZZI_CACHE_DIR", cache_dir)

    ctx = multiprocessing.get_context("spawn")
    pronto, fine = ctx.Event(), ctx.Event()
    altro = ctx.Process(target=_occupa_lo_slot, args=(cache_dir, 1.0, pronto, fine))
    altro.start()
    try:
        assert pronto.wait(timeout=10), "il primo processo non ha preso il lock"
        inizio = time.time()
        with RequestGate(min_interval=0).slot():
            atteso = time.time() - inizio
        assert atteso >= 0.5, "la seconda esecuzione non ha atteso la prima"
        assert fine.is_set()
    finally:
        altro.join(timeout=10)


def test_timeout_scaduto_produce_un_errore_esplicito(tmp_path, monkeypatch):
    cache_dir = str(tmp_path / "cache")
    monkeypatch.setenv("OSSERVAPREZZI_CACHE_DIR", cache_dir)

    ctx = multiprocessing.get_context("spawn")
    pronto, fine = ctx.Event(), ctx.Event()
    altro = ctx.Process(target=_occupa_lo_slot, args=(cache_dir, 2.0, pronto, fine))
    altro.start()
    try:
        assert pronto.wait(timeout=10)
        with pytest.raises(ServiceUnavailable) as info:
            with RequestGate(min_interval=0, timeout=0.5).slot():
                pass
        assert info.value.exit_code == 5
        assert info.value.retryable is True
        assert "parallelo" in info.value.message
    finally:
        altro.join(timeout=10)


def test_intervallo_minimo_fra_richieste_consecutive():
    gate = RequestGate(min_interval=0.6)
    with gate.slot():
        pass
    inizio = time.time()
    with gate.slot():
        pass
    assert time.time() - inizio >= 0.5


def test_il_lock_puo_essere_disattivato(monkeypatch):
    monkeypatch.setenv("OSSERVAPREZZI_NO_LOCK", "1")
    gate = RequestGate(min_interval=5)
    inizio = time.time()
    with gate.slot():
        pass
    with gate.slot():
        pass
    assert time.time() - inizio < 0.5
    assert not lock_path().exists()

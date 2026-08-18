"""Serializzazione delle richieste verso il portale.

Il servizio è di una pubblica amministrazione e va trattato come una risorsa
condivisa e fragile: nessuna esecuzione di questa CLI deve poter sommarsi a
un'altra. Il controllo non è per processo ma per macchina e per utente — un
lock su file, come fa `opensdmx` con ISTAT.

Due istanze lanciate in parallelo non producono due flussi di richieste: la
seconda attende che la prima abbia liberato lo slot. Fra una richiesta e la
successiva viene inoltre rispettato un intervallo minimo, misurato da invio a
invio, condiviso fra tutti i processi.
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import portalocker

from .cache import default_cache_dir
from .errors import ServiceUnavailable

MIN_INTERVAL = 1.0
DEFAULT_LOCK_TIMEOUT = 300.0


def state_dir() -> Path:
    directory = default_cache_dir() / "rate_limit"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def lock_path() -> Path:
    return state_dir() / "portale.lock"


def timestamp_path() -> Path:
    return state_dir() / "portale.log"


class RequestGate:
    """Concede un solo slot di richiesta alla volta su tutta la macchina."""

    def __init__(
        self,
        min_interval: float = MIN_INTERVAL,
        timeout: float = DEFAULT_LOCK_TIMEOUT,
        verbose: bool = False,
        enabled: bool = True,
    ) -> None:
        self.min_interval = max(0.0, min_interval)
        self.timeout = timeout
        self.verbose = verbose
        self.enabled = enabled and os.environ.get("OSSERVAPREZZI_NO_LOCK") != "1"

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message, file=sys.stderr)

    @contextmanager
    def slot(self):
        if not self.enabled:
            # Disattivare il lock toglie la serializzazione fra processi, mai
            # il ritmo: l'intervallo minimo continua a valere, altrimenti una
            # variabile d'ambiente basterebbe a scatenare richieste a raffica.
            self._respect_interval()
            self._mark()
            yield
            return

        path = lock_path()
        attesa_iniziata = time.time()
        # Con un timeout portalocker deve poter riprovare: il flag non
        # bloccante gli permette di attendere a intervalli e poi arrendersi.
        # Senza timeout si attende indefinitamente, in modo bloccante.
        if self.timeout > 0:
            flags = portalocker.LOCK_EX | portalocker.LOCK_NB
            timeout = self.timeout
        else:
            flags = portalocker.LOCK_EX
            timeout = None
        try:
            with portalocker.Lock(
                str(path),
                mode="a",
                flags=flags,
                timeout=timeout,
                check_interval=0.25,
            ):
                attesa = time.time() - attesa_iniziata
                if attesa > 1:
                    self._log(
                        f"un'altra esecuzione era in corso: atteso {attesa:.0f}s"
                    )
                self._respect_interval()
                self._mark()
                yield
        except portalocker.exceptions.LockException as exc:
            raise ServiceUnavailable(
                "un'altra esecuzione di osservaprezzi sta già interrogando il "
                "portale; le richieste non vengono eseguite in parallelo",
                lock=str(path),
                waited_seconds=round(time.time() - attesa_iniziata, 1),
                hint="attendi il termine dell'altra esecuzione oppure alza --lock-timeout",
            ) from exc

    def _mark(self) -> None:
        """Registra l'istante di invio, condiviso fra i processi."""
        timestamp_path().write_text(str(time.time()), encoding="utf-8")

    def _respect_interval(self) -> None:
        """Attende il tempo che manca all'intervallo minimo fra due invii."""
        if not self.min_interval:
            return
        path = timestamp_path()
        if not path.exists():
            return
        try:
            ultimo = float(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return
        residuo = self.min_interval - (time.time() - ultimo)
        if residuo > 0:
            self._log(f"intervallo minimo fra richieste: attesa {residuo:.1f}s")
            time.sleep(residuo)

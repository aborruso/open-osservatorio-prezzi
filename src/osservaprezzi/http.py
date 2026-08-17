"""Client HTTP read-only: user-agent identificabile, timeout, retry limitati,
rispetto di Retry-After, pausa configurabile fra richieste, nessun parallelismo."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from . import __version__
from .errors import ContractChanged, PartialResponse, ServiceUnavailable

USER_AGENT = f"osservaprezzi/{__version__} (+CLI read-only per dati pubblici)"

DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 3
DEFAULT_PAUSE = 1.0
MAX_RETRY_AFTER = 30.0


@dataclass
class Response:
    url: str
    text: str
    retrieved_at: str


class Fetcher:
    """Esegue le richieste GET in sequenza, con pausa e retry controllati."""

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        pause: float = 0.0,
        verbose: bool = False,
        client: httpx.Client | None = None,
    ) -> None:
        self.timeout = timeout
        self.retries = max(0, retries)
        self.pause = max(0.0, pause)
        self.verbose = verbose
        self._client = client or httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
        )
        self._requests = 0

    @property
    def requests_made(self) -> int:
        return self._requests

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message, file=sys.stderr)

    def get(self, url: str, params: dict[str, str] | None = None) -> Response:
        if self._requests and self.pause:
            time.sleep(self.pause)

        attempt = 0
        while True:
            attempt += 1
            self._requests += 1
            self._log(f"GET {url} {params or ''} (tentativo {attempt})")
            try:
                response = self._client.get(url, params=params)
            except httpx.RemoteProtocolError as exc:
                raise PartialResponse(
                    "risposta interrotta dal servizio", url=url, error=str(exc)
                ) from exc
            except httpx.TimeoutException as exc:
                if attempt <= self.retries:
                    self._sleep_backoff(attempt)
                    continue
                raise ServiceUnavailable(
                    "timeout della richiesta", url=url, timeout=self.timeout
                ) from exc
            except httpx.TransportError as exc:
                if attempt <= self.retries:
                    self._sleep_backoff(attempt)
                    continue
                raise ServiceUnavailable(
                    "servizio non raggiungibile", url=url, error=str(exc)
                ) from exc

            if response.status_code == 429 or response.status_code >= 500:
                if attempt <= self.retries:
                    self._sleep_backoff(attempt, response.headers.get("Retry-After"))
                    continue
                raise ServiceUnavailable(
                    "servizio temporaneamente indisponibile",
                    url=str(response.url),
                    status=response.status_code,
                )

            if response.status_code >= 400:
                raise ContractChanged(
                    "risposta inattesa dal servizio",
                    url=str(response.url),
                    status=response.status_code,
                )

            return Response(
                url=str(response.url),
                text=response.text,
                retrieved_at=datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"),
            )

    def _sleep_backoff(self, attempt: int, retry_after: str | None = None) -> None:
        delay = min(2.0 ** (attempt - 1), 8.0)
        if retry_after:
            try:
                delay = min(float(retry_after), MAX_RETRY_AFTER)
            except ValueError:
                pass
        self._log(f"nuovo tentativo fra {delay:.1f}s")
        time.sleep(delay)

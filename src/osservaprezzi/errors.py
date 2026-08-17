"""Tassonomia degli errori, codici di uscita e contratto JSON su stderr."""

from __future__ import annotations

import json
import sys
from typing import Any

EXIT_OK = 0
EXIT_INVALID_INPUT = 2
EXIT_NO_DATA = 3
EXIT_CONTRACT_CHANGED = 4
EXIT_SERVICE_UNAVAILABLE = 5
EXIT_PARTIAL_RESPONSE = 6


class OsservaprezziError(Exception):
    """Errore con codice stabile, codice di uscita e dettagli strutturati."""

    code = "error"
    exit_code = EXIT_INVALID_INPUT
    retryable = False

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details = {k: v for k, v in details.items() if v is not None}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details,
        }


class InvalidInput(OsservaprezziError):
    code = "invalid_input"
    exit_code = EXIT_INVALID_INPUT


class InvalidCollection(InvalidInput):
    code = "invalid_collection"


class InvalidDimension(InvalidInput):
    code = "invalid_dimension"


class InvalidParameter(InvalidInput):
    code = "invalid_parameter"


class InvalidQuery(InvalidInput):
    code = "invalid_query"


class NoData(OsservaprezziError):
    code = "no_data"
    exit_code = EXIT_NO_DATA


class ContractChanged(OsservaprezziError):
    code = "contract_changed"
    exit_code = EXIT_CONTRACT_CHANGED


class ServiceUnavailable(OsservaprezziError):
    code = "service_unavailable"
    exit_code = EXIT_SERVICE_UNAVAILABLE
    retryable = True


class PartialResponse(OsservaprezziError):
    code = "partial_response"
    exit_code = EXIT_PARTIAL_RESPONSE
    retryable = True


def emit(error: OsservaprezziError, as_json: bool) -> int:
    """Scrive l'errore su stderr e restituisce il codice di uscita."""
    if as_json:
        print(json.dumps(error.to_dict(), ensure_ascii=False), file=sys.stderr)
    else:
        print(f"errore [{error.code}]: {error.message}", file=sys.stderr)
        for key, value in error.details.items():
            print(f"  {key}: {value}", file=sys.stderr)
    return error.exit_code

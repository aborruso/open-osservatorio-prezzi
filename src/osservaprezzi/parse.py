"""Lettura della tabella dei risultati.

Il server rende l'intera tabella: la paginazione visibile nel portale è
implementata lato client da DataTables e non esiste come contratto HTTP.
"""

from __future__ import annotations

from .collections import Collection
from .errors import ContractChanged

TABLE_ID = "id-table-results"


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _cell(text: str, numeric: bool) -> str | float | None:
    value = " ".join(text.split())
    if not value:
        return None
    if numeric:
        try:
            return float(value)
        except ValueError:
            return value
    return value


def parse_table(document, collection: Collection) -> list[dict[str, object]]:
    """Estrae le righe della tabella verificando l'intestazione attesa."""
    tables = document.xpath(f'//table[@id="{TABLE_ID}"]')
    if not tables:
        raise ContractChanged(
            "tabella dei risultati non trovata nella pagina",
            expected_table_id=TABLE_ID,
            collection=collection.id,
        )
    table = tables[0]

    headers = [_normalize(th.text_content()) for th in table.xpath(".//thead//th")]
    expected = [_normalize(c.header) for c in collection.columns]
    if headers != expected:
        raise ContractChanged(
            "intestazione della tabella diversa da quella attesa",
            collection=collection.id,
            expected=expected,
            found=headers,
        )

    rows: list[dict[str, object]] = []
    for tr in table.xpath(".//tbody/tr"):
        cells = tr.xpath("./td")
        if len(cells) != len(collection.columns):
            raise ContractChanged(
                "numero di celle diverso dal numero di colonne",
                collection=collection.id,
                expected=len(collection.columns),
                found=len(cells),
            )
        rows.append(
            {
                column.name: _cell(cell.text_content(), column.numeric)
                for column, cell in zip(collection.columns, cells)
            }
        )
    return rows

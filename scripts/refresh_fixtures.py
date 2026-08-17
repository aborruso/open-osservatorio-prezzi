"""Riscarica le fixture HTML di test e le ritaglia.

Conserva soltanto il form dei filtri e la tabella dei risultati: il resto della
pagina (menu, script di analytics, footer) non fa parte del contratto letto
dalla CLI e non deve finire nel repository.

Uso:
    uv run python scripts/refresh_fixtures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree, html as lxml_html

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from osservaprezzi.collections import COLLECTIONS  # noqa: E402
from osservaprezzi.http import Fetcher  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"

CASES = {
    "consumo": {
        "base": {},
        "ok": {"year": "2025", "month": "5", "province": "Roma", "category": "energia"},
        "invalid": {
            "year": "2025",
            "month": "5",
            "province": "Atlantide",
            "category": "energia",
        },
    },
    "ortofrutta-it": {
        "base": {},
        "ok": {
            "year": "2025",
            "month": "5",
            "week": "2",
            "market": "ROMA",
            "group": "ORTAGGI",
        },
        "empty": {
            "year": "2025",
            "month": "5",
            "week": "2",
            "market": "CATANIA",
            "group": "PRODOTTI SECCHI",
        },
    },
    "ortofrutta-eu": {
        "base": {},
        "ok": {
            "year": "2025",
            "month": "5",
            "week": "2",
            "market": "PARIGI",
            "group": "ORTAGGI",
        },
    },
}


def trim(text: str) -> str:
    document = lxml_html.fromstring(text)
    parts = []
    for xpath in ('//form[@id="search-form"]', '//table[@id="id-table-results"]'):
        found = document.xpath(xpath)
        if found:
            parts.append(
                etree.tostring(found[0], encoding="unicode", method="html").strip()
            )
    return (
        '<html><head><meta charset="utf-8"></head><body>\n'
        + "\n".join(parts)
        + "\n</body></html>\n"
    )


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    with Fetcher(pause=1.0, verbose=True) as fetcher:
        for collection_id, cases in CASES.items():
            collection = COLLECTIONS[collection_id]
            for case, filters in cases.items():
                params = {
                    collection.dimension(name).html_name: value
                    for name, value in filters.items()
                }
                response = fetcher.get(collection.url, params or None)
                path = FIXTURES / f"{collection_id}-{case}.html"
                path.write_text(trim(response.text), encoding="utf-8")
                print(f"{path.name}: {path.stat().st_size} byte", file=sys.stderr)


if __name__ == "__main__":
    main()

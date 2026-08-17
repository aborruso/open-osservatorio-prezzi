"""Lettura dei form HTML: domini delle dimensioni e verifica dei filtri applicati.

Il portale non valida gli input: un valore fuori dominio produce HTTP 200, una
tabella senza righe e nessuna option selezionata. La lettura dell'echo dei
filtri è quindi l'unico modo per distinguere «nessun dato» da «parametro non
valido».
"""

from __future__ import annotations

from dataclasses import dataclass

from lxml import html as lxml_html

from .errors import ContractChanged

FORM_ID = "search-form"


@dataclass(frozen=True)
class Option:
    value: str
    label: str


@dataclass(frozen=True)
class Select:
    html_name: str
    options: tuple[Option, ...]
    selected: str | None

    @property
    def values(self) -> tuple[str, ...]:
        return tuple(o.value for o in self.options)


def parse_document(text: str):
    return lxml_html.fromstring(text)


def parse_form(document) -> dict[str, Select]:
    """Estrae i select del form dati, indicizzati per nome HTML."""
    forms = document.xpath(f'//form[@id="{FORM_ID}"]')
    if not forms:
        raise ContractChanged(
            "form dei filtri non trovato nella pagina", expected_form_id=FORM_ID
        )

    selects: dict[str, Select] = {}
    for element in forms[0].xpath(".//select"):
        name = element.get("name")
        if not name:
            continue
        options: list[Option] = []
        selected: str | None = None
        for option in element.xpath("./option"):
            value = option.get("value") or ""
            label = " ".join(option.text_content().split())
            options.append(Option(value, label))
            if option.get("selected") is not None:
                selected = value
        selects[name] = Select(name, tuple(options), selected)
    return selects


def check_echo(
    selects: dict[str, Select], requested: dict[str, str]
) -> list[dict[str, object]]:
    """Restituisce i filtri richiesti che il portale non ha applicato."""
    rejected: list[dict[str, object]] = []
    for html_name, value in requested.items():
        select = selects.get(html_name)
        if select is None:
            rejected.append(
                {"html_name": html_name, "requested": value, "applied": None}
            )
        elif select.selected != value:
            rejected.append(
                {
                    "html_name": html_name,
                    "requested": value,
                    "applied": select.selected,
                }
            )
    return rejected

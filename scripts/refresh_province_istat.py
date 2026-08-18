"""Rigenera la tabella di corrispondenza fra province del portale e codici ISTAT.

Le province di rilevazione dell'Osservatorio Prezzi sono indicate per nome, con
grafie che in quattro casi non coincidono con la denominazione ufficiale ISTAT.
Questo script scarica l'elenco corrente delle unità territoriali sovracomunali
dal SITUAS (via `opensituas`, report 64), lo confronta con i nomi esposti dal
portale e scrive `src/osservaprezzi/data/province_istat.csv`.

Uso:
    uv run python scripts/refresh_province_istat.py
"""

from __future__ import annotations

import csv
import io
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from osservaprezzi.cache import MetadataCache  # noqa: E402
from osservaprezzi.client import Client  # noqa: E402
from osservaprezzi.collections import CONSUMO  # noqa: E402
from osservaprezzi.http import Fetcher  # noqa: E402

DESTINAZIONE = (
    Path(__file__).resolve().parents[1] / "src" / "osservaprezzi" / "data" / "province_istat.csv"
)

# Il portale usa il nome del capoluogo o una grafia semplificata; queste sono le
# uniche quattro divergenze dalla denominazione ufficiale, verificate a mano.
ECCEZIONI = {
    "Aosta": "Valle d'Aosta/Vallée d'Aoste",
    "Bolzano": "Bolzano/Bozen",
    "Forli": "Forlì-Cesena",
    "Reggio Emilia": "Reggio nell'Emilia",
}


def normalizza(testo: str) -> str:
    senza_accenti = unicodedata.normalize("NFKD", testo).encode("ascii", "ignore").decode()
    return " ".join(senza_accenti.lower().replace("'", " ").split())


def unita_territoriali() -> dict[str, dict[str, str]]:
    completato = subprocess.run(
        ["opensituas", "-o", "csv", "get", "64"],
        capture_output=True,
        text=True,
        check=True,
    )
    righe = csv.DictReader(io.StringIO(completato.stdout))
    return {normalizza(r["DEN_UTS"]): r for r in righe}


def province_del_portale() -> list[str]:
    with Fetcher() as fetcher:
        client = Client(fetcher, MetadataCache())
        opzioni, _ = client.values(CONSUMO, "province")
    return [o.value for o in opzioni]


def main() -> None:
    istat = unita_territoriali()
    righe = []
    mancanti = []
    for provincia in province_del_portale():
        chiave = normalizza(ECCEZIONI.get(provincia, provincia))
        uts = istat.get(chiave)
        if uts is None:
            mancanti.append(provincia)
            continue
        righe.append(
            {
                "province": provincia,
                # Le 15 città metropolitane hanno un codice UTS (2xx) diverso dal
                # codice provincia storico (0xx): quest'ultimo è quello usato
                # nella gran parte dei dataset ISTAT, quindi vanno conservati
                # entrambi per non rompere i join in modo silenzioso.
                "istat_code": uts["COD_PROV_STORICO"],
                "uts_code": uts["COD_UTS"],
                "nuts3": uts["COD_NUTS3_2024"],
                "istat_name": uts["DEN_UTS"],
                "region": uts["DEN_REG"],
                "area": uts["DEN_RIP"],
                "plate": uts["SIGLA_AUTOMOBILISTICA"],
            }
        )

    DESTINAZIONE.parent.mkdir(parents=True, exist_ok=True)
    with DESTINAZIONE.open("w", encoding="utf-8", newline="") as handle:
        scrittore = csv.DictWriter(handle, fieldnames=list(righe[0]), lineterminator="\n")
        scrittore.writeheader()
        scrittore.writerows(righe)

    print(f"{DESTINAZIONE}: {len(righe)} province", file=sys.stderr)
    if mancanti:
        print(
            "senza corrispondenza, da aggiungere alle eccezioni: "
            + ", ".join(mancanti),
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()

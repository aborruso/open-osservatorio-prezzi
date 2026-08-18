# Riferimento dei comandi

Tutti i comandi accettano `--agent` (JSON, niente colori, niente interazione) e `--json`. I dati vanno su `stdout`, la diagnostica su `stderr`.

## Indice

- [Scoperta](#scoperta)
- [Recupero](#recupero)
- [Query salvate](#query-salvate)
- [Archivi](#archivi)
- [Opzioni comuni](#opzioni-comuni)
- [Ricette](#ricette)

## Scoperta

### `agent-context`

L'intero contratto in una chiamata: collezioni, dimensioni, dipendenze, comandi, codici di uscita, forma degli errori.

```bash
osservaprezzi agent-context           # JSON compatto
osservaprezzi agent-context --pretty  # indentato
```

### `catalog`

```bash
osservaprezzi catalog --agent | jq -r '.collections[] | "\(.id): \(.title)"'
```

### `describe <collezione>`

Dimensioni con dipendenze, colonne prodotte, chiave naturale, copertura temporale, avvertenze.

```bash
osservaprezzi describe ortofrutta-it --agent \
  | jq '{dimensioni: [.dimensions[] | {name, depends_on}], anni: .coverage.values}'
```

### `values <collezione> <dimensione>`

I valori ammessi, letti dal portale. Le dimensioni dipendenti richiedono i genitori.

```bash
osservaprezzi values consumo category --agent
osservaprezzi values consumo province --agent | jq -r '.values[].value'
osservaprezzi values consumo month --year 2026 --agent          # dipende dall'anno
osservaprezzi values ortofrutta-it week --year 2025 --month 5 --agent
osservaprezzi values ortofrutta-eu market --agent
```

I domini cambiano davvero: nel 2026 `consumo` espone sei mesi, i mercati italiani otto; gennaio 2021 ha cinque settimane, maggio 2025 quattro.

## Recupero

### `get <collezione> [filtri]`

```bash
# prezzi al consumo
osservaprezzi get consumo --year 2025 --month 5 --province Roma --category ittici

# mercati italiani
osservaprezzi get ortofrutta-it --year 2025 --month 5 --week 2 \
  --market ROMA --group ORTAGGI

# mercati europei, in CSV su file
osservaprezzi get ortofrutta-eu --year 2025 --month 5 --week 2 \
  --market PARIGI --group ORTAGGI --csv --output parigi.csv
```

Filtri per collezione:

| Collezione | Filtri |
|---|---|
| `consumo` | `--year --month --province --category` |
| `ortofrutta-it` | `--year --month --week --market --group` |
| `ortofrutta-eu` | `--year --month --week --market --group` |

Passare un'opzione estranea alla collezione (per esempio `--market` su `consumo`) è un errore con uscita 2, non viene ignorata.

`--latest` riempie i filtri mancanti con i valori predefiniti del portale e lo registra nel campo `defaults_used` di ogni record: serve per un'esplorazione rapida, non per una query riproducibile, perché quei default cambiano nel tempo.

`--limit <n>` tronca le osservazioni restituite.

### Colonne prodotte

`consumo`: `year, month, province, category, product, price_min, price_max, price_avg, category_label`

`ortofrutta-it`: `year, month, week, market, group, species, variety, size, grade, packaging, origin, unit, price_prevalent, price_min, price_max`

`ortofrutta-eu`: come sopra ma con un solo `price`.

A queste si aggiungono sempre `collection`, `source_url`, `retrieved_at` e `defaults_used`. La vista tabella le nasconde perché identiche su tutte le righe; JSON e CSV le riportano.

## Query salvate

```yaml
# ortaggi-roma.yaml
version: 1
collection: ortofrutta-it
filters:
  year: 2025
  month: 5
  week: 2
  market: ROMA
  group: ORTAGGI
format: csv
limit: 50
```

```bash
osservaprezzi run ortaggi-roma.yaml --output ortaggi.csv
```

`run` rifiuta versioni di schema diverse da 1, chiavi sconosciute e filtri che non appartengono alla collezione. Produce gli stessi record del comando `get` equivalente.

## Archivi

```bash
# 1. il piano, senza toccare i dati
osservaprezzi archive consumo --year 2025 --month 5 --category altri_alim \
  --all province --dry-run --agent

# 2. l'esecuzione
osservaprezzi archive consumo --year 2025 --month 5 --category altri_alim \
  --all province --product "Pane Fresco Con Farina Di Grano (1000 Gr)" \
  --output pane-2025-05

# 3. la ripresa, se si è interrotta
osservaprezzi archive consumo --year 2025 --month 5 --category altri_alim \
  --all province --output pane-2025-05 --resume
```

Opzioni specifiche:

| Opzione | Effetto |
|---|---|
| `--all <dimensione>` | espande su tutti i valori; ripetibile |
| `--product <testo>` | filtro locale a confronto esatto normalizzato |
| `--output <dir>` | directory dell'archivio, obbligatoria per eseguire |
| `--format csv\|jsonl` | formato del file dati |
| `--max-requests <n>` | limite rigido, default 100: il piano che lo supera non parte |
| `--pause <secondi>` | attesa fra richieste, si somma al minimo di sistema |
| `--dry-run` | mostra il piano e termina |
| `--resume` | ripete solo le richieste mancanti o fallite |

Contenuto della directory:

- `data.csv` (o `data.jsonl`) — righe deduplicate per chiave naturale;
- `manifest.json` — query, valori espansi, URL sorgente, istanti, conteggi, esito di ogni richiesta (`ok`, `no_data`, `no_match`, `failed`), chiave usata e avvertenze del portale.

Lo stato del manifest è `running` durante l'esecuzione, poi `complete` o `partial`. Un archivio `partial` fa uscire il comando con codice 6.

Costo tipico: `--all province` su `consumo` sono 64 richieste, circa due minuti e mezzo con la pausa predefinita. `--all market` su `ortofrutta-it` sono 23 richieste.

## Opzioni comuni

| Opzione | Effetto |
|---|---|
| `--agent` | JSON su dati ed errori, nessun colore, nessuna interazione |
| `--json` / `--csv` | formato di output |
| `--output <file>` | scrive su file invece che su `stdout` |
| `--limit <n>` | numero massimo di osservazioni |
| `--refresh` | ignora la cache dei metadati |
| `--timeout <s>` | limite della singola richiesta, default 30 |
| `--retries <n>` | tentativi in caso di errore temporaneo, default 3 |
| `--lock-timeout <s>` | attesa massima del turno, default 300; `0` attende senza limite |
| `--verbose` | diagnostica su `stderr`, incluse le attese del turno |

La cache contiene **solo metadati** (domini delle dimensioni), mai osservazioni. `osservaprezzi cache` ne mostra il percorso, `osservaprezzi cache --clear` la svuota.

## Ricette

**Leggere un errore in JSON** — gli errori sono su `stderr`:

```bash
osservaprezzi get consumo --year 2025 --agent 2>&1 >/dev/null | jq -c '{code, message}'
```

**Elencare i valori ammessi dopo un errore:**

```bash
osservaprezzi get ortofrutta-it --year 2025 --month 5 --week 2 \
  --market MESSINA --group ORTAGGI --agent 2>&1 >/dev/null \
  | jq -r '.details.rejected[].allowed[]'
```

**Dispersione dei prezzi in una provincia:**

```bash
osservaprezzi get consumo --year 2025 --month 5 --province Milano --category altri_alim --agent \
  | jq -r '.records[] | "\(.product): \(.price_min)–\(.price_max) (medio \(.price_avg))"'
```

**Confronto fra province su un prodotto omogeneo** (carburanti, dove il confronto regge):

```bash
for p in Milano Napoli Bologna Palermo; do
  osservaprezzi get consumo --year 2025 --month 5 --province "$p" --category energia --agent \
    | jq -r --arg p "$p" '.records[] | select(.product|test("Benzina Verde Senza")) | "\($p): \(.price_avg)"'
done
```

Il ciclo è sequenziale ed è corretto così: le richieste sono comunque serializzate, e lanciarle in parallelo non le renderebbe più veloci.

**Verificare la copertura di un archivio:**

```bash
jq -r '.results[] | select(.status != "ok") | "\(.filters.province): \(.status)"' pane-2025-05/manifest.json
```

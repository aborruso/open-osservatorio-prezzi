# osservaprezzi

CLI read-only per i dati pubblici dell'[Osservatorio Prezzi](https://osservaprezzi.mise.gov.it/) del Ministero delle Imprese e del Made in Italy.

Recupera, in forma strutturata e riproducibile, tre collezioni:

| Collezione | Contenuto |
|---|---|
| `consumo` | Rilevazioni mensili di beni e servizi di largo consumo |
| `ortofrutta-it` | Prodotti ortofrutticoli all'ingrosso nei mercati italiani |
| `ortofrutta-eu` | Prodotti ortofrutticoli all'ingrosso nei mercati europei |

I dati provengono sempre dal portale: la CLI non genera, non stima e non completa valori mancanti. Ogni record conserva `collection`, `source_url` e `retrieved_at`.

## Installazione

```bash
uv sync
uv run osservaprezzi --help
```

## Sequenza di scoperta

Ogni comando indica il passo successivo, così una persona o un agente può partire senza conoscere gli endpoint.

```bash
osservaprezzi catalog
osservaprezzi describe consumo
osservaprezzi values consumo province
osservaprezzi values consumo month --year 2025
osservaprezzi get consumo --year 2025 --month 5 --province Roma --category energia
```

I domini dipendenti vanno chiesti con i filtri genitori: i mesi dipendono dall'anno, le settimane da anno e mese. Chiedere `values ortofrutta-it week` senza `--year` e `--month` è un errore, non un valore predefinito silenzioso.

## Filtri

| Collezione | Filtri obbligatori |
|---|---|
| `consumo` | `--year --month --province --category` |
| `ortofrutta-it` | `--year --month --week --market --group` |
| `ortofrutta-eu` | `--year --month --week --market --group` |

`get` richiede tutti i filtri della collezione. Per usare i valori predefiniti del portale serve `--latest`: i filtri così ricavati sono elencati nel campo `defaults_used`, presente sia nel JSON sia in ogni record esportato, così un CSV prodotto con i default resta distinguibile da uno con filtri espliciti.

## Output

- predefinito: tabella allineata;
- `--json`: oggetto documentato con `schema_version`, filtri, provenienza e `records`;
- `--csv`: stesse righe e stessi valori nulli del JSON (cella vuota = `null`);
- `--output <file>`: scrive su file.

La vista tabella è pensata per la lettura umana e omette le colonne di provenienza (`collection`, `source_url`, `retrieved_at`, `defaults_used`), identiche su tutte le righe; JSON e CSV le riportano sempre.

`stdout` contiene soltanto i dati. Progressi, avvisi ed errori vanno su `stderr`.

## Query salvate

```yaml
version: 1
collection: ortofrutta-it
filters:
  year: 2025
  month: 5
  week: 2
  market: ROMA
  group: ORTAGGI
format: json
```

```bash
osservaprezzi run query.yaml
```

`run` rifiuta versioni non supportate, chiavi e filtri sconosciuti.

## Archivi on-demand

`archive` espande una o più dimensioni indicate esplicitamente. Le richieste sono sequenziali, con pausa configurabile e un limite rigido.

```bash
osservaprezzi archive consumo \
  --year 2025 --month 5 --category altri_alim \
  --all province \
  --product "Pane Fresco Con Farina Di Grano (1000 Gr)" \
  --output archivio-pane-2025-05
```

Prima dell'esecuzione:

```bash
osservaprezzi archive consumo --year 2025 --month 5 --category altri_alim \
  --all province --dry-run --json
```

L'archivio contiene `data.csv` (oppure `data.jsonl` con `--format jsonl`) e `manifest.json` con schema, query, valori espansi, URL sorgente, istanti di acquisizione, conteggi, esito di ogni richiesta, chiave naturale di deduplicazione e avvertenze del portale. Un'esecuzione interrotta resta `partial` e si riprende con `--resume`: vengono ripetute solo le richieste mancanti o fallite.

Il filtro `--product` non esiste nel portale: viene applicato localmente con confronto esatto dopo casefold e compattazione degli spazi, e la regola è registrata nel manifest. Per `consumo` richiede anche `--category`, perché senza categoria l'espansione costerebbe fino a 384 richieste per un solo periodo.

## Codici di uscita

| Codice | Significato |
|---:|---|
| 0 | Successo |
| 2 | Input non valido (collezione, dimensione, filtro o query) |
| 3 | Nessun dato per i filtri indicati |
| 4 | Contratto cambiato: HTML non riconosciuto |
| 5 | Servizio temporaneamente indisponibile |
| 6 | Risposta parziale o archivio incompleto |

Con `--json` gli errori sono emessi su `stderr` come oggetto con `code`, `message`, `retryable` e `details`, e i valori ammessi suggeriti provengono sempre dal form del portale, mai da somiglianze inventate.

## Note sui dati

Il portale non valida gli input: un valore inesistente produce comunque HTTP 200 e una tabella vuota. La CLI legge i filtri effettivamente applicati nel form della risposta e distingue quindi «parametro non valido» (uscita 2) da «nessun dato» (uscita 3).

Per i beni di largo consumo il portale avverte che la stessa descrizione di prodotto può riferirsi a combinazioni differenti di varietà, marca, confezione e punto vendita tra province o mesi: i valori raccolti non costituiscono automaticamente una serie storica comparabile. L'avvertenza è riportata nell'output e nei manifest.

La licenza dei dati di origine (Istat, Unioncamere, BMTI) non è dichiarata in modo univoco dal portale: citare sempre fonte e URL e verificare le condizioni prima di ridistribuire archivi derivati.

## Sviluppo

```bash
uv run pytest
```

I test funzionano su fixture HTML ridotte e non richiedono rete. Lo script `scripts/refresh_fixtures.py` riscarica e ritaglia le fixture quando serve.

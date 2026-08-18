---
name: osservaprezzi
description: >-
  Recupera i prezzi pubblici dell'Osservatorio Prezzi del MIMIT con la CLI
  `osservaprezzi` — prezzi al consumo mensili per provincia (alimentari,
  carburanti, ittici, ortofrutta, servizi) e quotazioni ortofrutticole
  settimanali all'ingrosso nei mercati italiani ed europei. Usa questa skill
  ogni volta che la richiesta riguarda quanto costa un prodotto in Italia, il
  confronto dei prezzi fra province o mercati, il prezzo di benzina, gasolio,
  pane, pesce, frutta o verdura, la dispersione fra prezzo minimo e massimo, o
  dati dell'Osservatorio Prezzi, Osservaprezzi, Mister Prezzi e MIMIT — anche
  quando l'utente non nomina la CLI e chiede solo «quanto costa X a Y» oppure
  «confronta i prezzi di Z». Usala anche per costruire archivi CSV su tutte le
  province o su tutti i mercati, e quando servono prezzi incrociabili con altre
  fonti territoriali, perché ogni record porta i codici ISTAT e NUTS3 della
  provincia. Non usarla per serie storiche o per l'andamento dell'inflazione,
  che sono indici ISTAT e si prendono via SDMX.
license: MIT
compatibility: Richiede la CLI `osservaprezzi` 0.3.0 o successiva (pacchetto PyPI `openosservaprezzi`) e accesso a osservaprezzi.mise.gov.it
metadata:
  author: aborruso
  version: "1.1"
  repository: https://github.com/aborruso/open-osservatorio-prezzi
allowed-tools: Bash(osservaprezzi:*) Bash(uvx:*) Bash(jq:*) Read
---

# Osservatorio Prezzi

La CLI `osservaprezzi` recupera i **livelli di prezzo in euro** pubblicati dal portale del Ministero delle Imprese e del Made in Italy. Sono dati che non esistono in nessuna API: il portale li espone solo come pagine HTML con menu a tendina, e questa CLI li trasforma in tabelle, JSON e CSV con la provenienza allegata.

## Prima di tutto: la CLI è installata?

```bash
osservaprezzi version
```

Se manca, installala oppure eseguila al volo senza installare:

```bash
uv tool install openosservaprezzi     # installazione stabile
uvx --from openosservaprezzi osservaprezzi version   # esecuzione occasionale
```

## Il comando da cui partire

```bash
osservaprezzi agent-context
```

Restituisce in una sola chiamata l'intero contratto: collezioni, dimensioni con le loro dipendenze, comandi con esempi, codici di uscita, forma degli errori. Leggilo invece di dedurre la sintassi: se il contratto cambia, quel comando cambia con lui, questa skill no.

Aggiungi `--agent` a qualunque comando per ottenere JSON senza colori né interazione, su dati **ed errori**.

## Le tre collezioni

| id | Contenuto | Filtri obbligatori |
|---|---|---|
| `consumo` | prezzi al dettaglio mensili, min/max/medio, 64 province | `--year --month --province --category` |
| `ortofrutta-it` | quotazioni settimanali all'ingrosso, 23 mercati italiani | `--year --month --week --market --group` |
| `ortofrutta-eu` | quotazioni settimanali, 11 mercati europei, prezzo unico | `--year --month --week --market --group` |

Copertura dal 2021. Le categorie di `consumo` sono sei: `altri_alim` (alimentari), `energia` (carburanti), `groc` (cura persona e casa), `ittici`, `orto` (ortofrutta), `servizi`.

## I record di `consumo` sono già incrociabili

Ogni riga porta con sé tre codifiche territoriali che il portale non espone, aggiunte dalla CLI: `province_istat` (codice provincia classico, Roma `058`), `province_uts` (unità territoriale sovracomunale, che per le quindici città metropolitane è diverso — Roma `258`) e `province_nuts3` (`ITI43`).

Funziona anche al contrario: `--province` accetta il codice al posto del nome, quindi `082`, `ITG12`, `PA` e `Palermo` chiedono la stessa provincia. Se l'utente ti dà un codice, passalo direttamente invece di convertirlo a mano.

Servono per unire questi prezzi ad altre fonti — popolazione, redditi, confini, dataflow SDMX — senza costruire a mano una tabella di conversione. Quando riporti un join, usa il codice giusto per la fonte di destinazione: se una provincia grande risulta senza corrispondenza, quasi sempre è perché stai usando l'una al posto dell'altra. Per i mercati ortofrutticoli questi campi non esistono, perché un mercato non è un'unità amministrativa e nessun codice viene inventato.

## Il percorso: scoprire prima di chiedere

Il portale **non valida gli input**: un valore inventato produce HTTP 200 con una tabella vuota, indistinguibile da un'assenza di dati. La CLI se ne accorge rileggendo il form della risposta, ma tu eviti il giro a vuoto chiedendo prima i valori ammessi.

```bash
osservaprezzi catalog --agent                          # cosa c'è
osservaprezzi describe consumo --agent                 # dimensioni e dipendenze
osservaprezzi values consumo province --agent          # valori ammessi
osservaprezzi values consumo month --year 2025 --agent # domini dipendenti
osservaprezzi get consumo --year 2025 --month 5 \
  --province Roma --category ittici --agent            # i dati
```

Tre regole che evitano quasi tutti gli errori:

1. **I domini dipendenti richiedono i genitori.** I mesi dipendono dall'anno, le settimane da anno e mese. `values ortofrutta-it week` senza `--year` e `--month` è un errore, non un default: gennaio 2021 ha cinque settimane, maggio 2025 quattro.
2. **`get` vuole tutti i filtri della collezione.** Non esistono valori impliciti; per usare quelli del portale serve `--latest`, che li dichiara nel campo `defaults_used` di ogni record.
3. **Non inventare codici.** I nomi di province e mercati vanno presi da `values`. Se sbagli, l'errore ti restituisce la lista giusta — ma è una richiesta sprecata verso un servizio pubblico.

## Leggere gli esiti

Gli errori escono su `stderr`, i dati su `stdout`: per parsarli con `jq` serve `2>&1 >/dev/null`.

| Uscita | Codice | Significato e cosa fare |
|---:|---|---|
| 0 | — | dati recuperati |
| 2 | `invalid_parameter` | valore non ammesso; i valori validi sono in `details.rejected[].allowed` |
| 3 | `no_data` | filtri corretti, nessuna rilevazione per quel periodo: **non è un errore da correggere**, è un'informazione |
| 4 | `contract_changed` | il portale ha cambiato struttura: la CLI va aggiornata, non c'è workaround |
| 5 | `service_unavailable` | portale irraggiungibile, oppure un'altra esecuzione ha lo slot |
| 6 | — | archivio rimasto parziale, riprendibile con `--resume` |

La distinzione fra 2 e 3 è il cuore dello strumento: `no_data` significa che quel prodotto non è stato rilevato lì, non che la domanda fosse mal posta. Riportalo come informazione, non come fallimento.

## Archivi: molte province o molti mercati

Per espandere una dimensione su tutti i suoi valori, chiedi **sempre prima il piano**:

```bash
osservaprezzi archive consumo --year 2025 --month 5 --category altri_alim \
  --all province --dry-run --agent
```

Poi esegui, indicando una directory di uscita:

```bash
osservaprezzi archive consumo --year 2025 --month 5 --category altri_alim \
  --all province --product "Pane Fresco Con Farina Di Grano (1000 Gr)" \
  --output pane-2025-05
```

Produce `data.csv` e `manifest.json` con copertura, URL, esiti per singola richiesta e chiave di deduplicazione. Un'esecuzione interrotta si riprende con `--resume`, che ripete solo ciò che manca.

Se la richiesta riguarda un **andamento nel tempo**, non espandere i mesi con `--all month`: quella serie mescolerebbe il rincaro reale con il cambio del paniere campionato. La CLI stessa lo segnala su `stderr` e propone il comando `opensdmx` equivalente; segui quella strada invece di produrre comunque il grafico. Espandere il tempo resta legittimo per altri scopi — verificare in quali mesi un prodotto è stato rilevato, misurare la copertura — purché il risultato non venga presentato come una serie storica.

Nota su `--product`: quel filtro non esiste nel portale, viene applicato localmente con confronto esatto dopo normalizzazione, e per `consumo` richiede anche `--category`. Le province senza corrispondenza finiscono nel manifest come `no_match`: vanno riportate, perché «non rilevato» non è «prezzo zero».

## Una richiesta alla volta

Le richieste sono serializzate su tutta la macchina da un lock su file, con almeno un secondo fra l'una e l'altra. Lanciare più comandi in parallelo non accelera nulla: si alternano. Non tentare di aggirare il vincolo con task concorrenti — il portale è un servizio pubblico senza API, dimensionato per la consultazione umana. Se un comando sembra fermo sta aspettando il turno, e con `--verbose` lo dichiara.

## Interpretare i numeri prima di riportarli

Questa è la parte in cui è facile sbagliare in buona fede, e vale la pena leggerla: **[references/interpretazione.md](references/interpretazione.md)**.

In sintesi, perché nessuno costruisca conclusioni che i dati non reggono:

- Una descrizione come «Pane Fresco Con Farina Di Grano (1000 Gr)» è una **categoria**, non un prodotto: ogni provincia campiona marche, varietà e punti vendita diversi. Le classifiche fra città sugli alimentari e le serie storiche non reggono.
- Regge invece la **dispersione** dentro una singola rilevazione (min, max e medio vengono dallo stesso campione) e il confronto territoriale sui **prodotti omogenei**, carburanti in testa: la benzina verde è identica ovunque.
- Per l'andamento nel tempo la fonte corretta sono gli **indici ISTAT** (NIC fino al dettaglio provinciale, IPCA solo nazionale), che stanno su SDMX e non qui. Se la richiesta riguarda l'inflazione o una serie storica, dillo e indirizza lì invece di forzare questi livelli.

Quando riporti un valore, cita sempre il mese, la provincia o il mercato, e la fonte: ogni record contiene già `source_url` e `retrieved_at`.

## Riferimenti

- **[references/comandi.md](references/comandi.md)** — tutte le opzioni, query YAML riutilizzabili, formati di output, ricette pronte.
- **[references/interpretazione.md](references/interpretazione.md)** — cosa si può concludere da questi dati e cosa no, con i numeri che lo dimostrano.

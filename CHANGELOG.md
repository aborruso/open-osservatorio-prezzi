# Diario delle versioni

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/); le versioni seguono il [versionamento semantico](https://semver.org/lang/it/).

## [0.2.0] — 2026-08-18

### Aggiunto

- Codici territoriali ISTAT in ogni record di `consumo`: `province_istat` (codice provincia storico), `province_uts` (unità territoriale sovracomunale) e `province_nuts3`. Le quindici città metropolitane hanno codice provincia e codice UTS diversi — Roma è `058` e `258` — quindi sono esposti entrambi per non rompere in silenzio i join.
- Tabella di corrispondenza in `src/osservaprezzi/data/province_istat.csv`, generata dal SITUAS ISTAT con `scripts/refresh_province_istat.py`, documentata in `references/README.md`.
- Agent Skill in `skills/osservaprezzi/`, conforme alla specifica agentskills.io.

### Modificato

- `SCHEMA_VERSION` passa a 2: i record di `consumo` hanno tre campi in più. Le altre collezioni restano invariate, perché i mercati non sono unità amministrative e nessun codice viene inventato.
- `describe` espone i campi derivati in `derived_columns`.

## [0.1.0] — 2026-08-18

Prima versione, pubblicata su PyPI come `openosservaprezzi`; il comando installato è `osservaprezzi`.

### Aggiunto

- Tre collezioni: `consumo` (rilevazioni mensili di beni e servizi di largo consumo), `ortofrutta-it` e `ortofrutta-eu` (quotazioni all'ingrosso).
- Percorso di scoperta `catalog` → `describe` → `values` → `get`, con i valori ammessi letti dal portale e i domini dipendenti risolti passando i filtri genitori.
- Output in tabella, JSON e CSV, con provenienza (`collection`, `source_url`, `retrieved_at`) in ogni record e scrittura su file senza sporcare `stdout`.
- Query salvate in YAML ed eseguibili con `run`.
- Archivi on-demand con `archive`: piano preventivo `--dry-run`, limite `--max-requests`, esecuzione sequenziale, `manifest.json`, deduplicazione per chiave naturale, ripresa con `--resume` e filtro locale `--product`.
- Errori distinti per categoria con codici di uscita deterministici (2 input non valido, 3 nessun dato, 4 contratto cambiato, 5 servizio indisponibile, 6 risposta parziale) ed emissione JSON su `stderr`.
- Riconoscimento dei filtri rifiutati dal portale leggendo il form della risposta: un valore inesistente non viene più confuso con un'assenza di dati.
- Aiuto autodescrittivo: esempi eseguibili in ogni comando, opzioni che dichiarano collezione di appartenenza e dipendenze, comando `agent-context` e opzione `--agent`.
- Serializzazione delle richieste su tutta la macchina tramite lock su file, con intervallo minimo condiviso fra processi e `--lock-timeout`.
- Cache locale dei soli metadati, invalidabile con `--refresh`.

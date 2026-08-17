# Piano implementazione prima versione CLI Osservatorio Prezzi

Riferimenti: `PRD.md` (criteri di accettazione 1-10) e `docs/evaluation.md` (decisione GO).
Il piano della fattibilità, concluso, resta in coda a questo documento.

## Evidenze aggiuntive del 2026-08-17 (pre-implementazione)

Verificate con sessione `agent-browser` (traffico tracciato) e replay HTTP:

- L'echo dei filtri funziona su **tutte** le dimensioni delle tre collezioni, `SETTIMANA` inclusa: un valore valido torna `selected`, un valore fuori dominio torna senza alcuna option selezionata.
- Discriminante confermato: `echo assente + 0 righe` = parametro non valido; `echo coerente + 0 righe` = nessun dato (esempio reale: mercati italiani 2025-05, settimana 2, CATANIA, PRODOTTI SECCHI).
- `submit=Applica` non è necessario: stessa risposta e stesso conteggio righe senza il parametro.
- Il dominio dei mesi dipende da anno **e** collezione (consumo 2026 non include agosto; mercati italiani 2026 ne espone 8); il dominio delle settimane dipende da anno e mese (2021-01 → 5 settimane, 2025-05 → 4).
- Nessuna paginazione HTTP: la tabella completa è servita dal server, DataTables pagina lato client. RF-07 non ha nulla da implementare.
- L'endpoint ausiliario `admin-osservaprezzi.mise.gov.it` continua a non risolvere (NXDOMAIN); la pagina funziona lo stesso. Nessuna dipendenza.
- Nessun export XLS/CSV disponibile nelle pagine: unica sorgente è la tabella HTML.

## Fase 0 - Preparazione

- [ ] Inizializzare il repository git e aggiungere `.gitignore` (`tmp/`, `.venv/`, cache) → verifica: `git status` pulito a parte i file sorgente.
- [ ] Creare il progetto con `uv` (`pyproject.toml`, `src/osservaprezzi/`, dipendenze Typer, httpx, lxml, PyYAML) → verifica: `uv run osservaprezzi --version` stampa la versione.
- [ ] Definire la configurazione centralizzata delle sorgenti (URL, dimensioni, nomi HTML, schema tabella per collezione) → verifica: test che le tre collezioni siano registrate con nomi CLI in inglese (`province`, non `provincia`, correggendo l'incoerenza del PRD).

## Fase 1 - Nucleo HTTP, form e parsing

- [ ] `http.py`: client httpx con user-agent `osservaprezzi/<versione>`, timeout, retry limitati con attesa progressiva e rispetto di `Retry-After`, pausa configurabile, nessun parallelismo → verifica: test con transport simulato su timeout, 429 e 5xx.
- [ ] `forms.py`: lettura dei domini di ogni select con lxml (attributi letti per nome, mai per posizione) e lettura dell'echo dei filtri → verifica: fixture con `<option  selected='selected'  value="2025">` interpretata correttamente.
- [ ] `parse.py`: estrazione righe da `#id-table-results`, celle vuote conservate come null, prezzi come decimali con rappresentazione originale preservata → verifica: fixture ortofrutta con `U.M.` vuota e varietà vuota.
- [ ] `errors.py`: tassonomia errori, codici di uscita 2-6, errore JSON su `stderr` con `code`, `message`, `retryable`, `details` → verifica: test su ciascun codice.

## Fase 2 - Scoperta e recupero (adattatore `consumo`)

- [ ] `catalog`: elenco delle tre collezioni con descrizione e stato → verifica: test su output tabellare e JSON.
- [ ] `describe consumo`: metadati, dimensioni, copertura temporale ricavata dai domini → verifica: test su fixture.
- [ ] `values consumo <dimensione>` con filtri genitori passati nella GET (i mesi dipendono dall'anno) → verifica: test che `values month --year 2026` e `--year 2025` restituiscano domini diversi.
- [ ] `get consumo`: tutti i filtri obbligatori, `--latest` esplicito per i default del sito, validazione locale sui domini, verifica dell'echo prima di leggere la tabella → verifica: fixture per risultato valido, valido vuoto e parametro non valido.
- [ ] Renderer tabella, JSON e CSV con stessi record e stessi null, ordine stabile, `stdout` solo dati → verifica: test di equivalenza JSON/CSV e test che `--verbose` non scriva nulla su `stdout`.
- [ ] Cache dei soli metadati con sorgente, data e scadenza; `--refresh` → verifica: test che la cache non contenga osservazioni.

## Fase 3 - Adattatori ortofrutticoli

- [ ] `ortofrutta-it`: cinque dimensioni, schema a dieci colonne con prezzo prevalente, minimo e massimo → verifica: fixture reale e test di schema.
- [ ] `ortofrutta-eu`: cinque dimensioni, schema a nove colonne con prezzo unico → verifica: fixture reale e test di schema.
- [ ] Matrice di parità form HTML → parametro HTTP → parametro CLI per le tre collezioni → verifica: test che fallisce se una select del form non ha un parametro CLI corrispondente.

## Fase 4 - Query salvate e archivi

- [ ] `run <query.yaml>`: schema versione 1, rifiuto di versioni, filtri e valori sconosciuti → verifica: test che query salvata e comando `get` equivalente producano lo stesso insieme di record.
- [ ] `archive`: piano preventivo, `--dry-run --json`, `--max-requests` con limite predefinito 100, esecuzione sequenziale con pausa → verifica: test di pianificazione su fixture, senza rete.
- [ ] `manifest.json` con versione schema, query, valori espansi, URL, istanti, conteggi, richieste riuscite e fallite, chiave di deduplicazione, avvertenza di comparabilità del portale → verifica: test di struttura del manifest.
- [ ] Deduplicazione per chiave naturale e ripresa con `--resume` di stato `partial` → verifica: test di ripresa su manifest parziale simulato.
- [ ] Filtro locale `--product` con normalizzazione documentata (casefold, spazi compattati, trim) registrata nel manifest → verifica: test su descrizioni con maiuscole e spazi differenti.

## Fase 5 - Verifica finale e documentazione

- [ ] Smoke test live read-only, una query per collezione, non automatizzato in parallelo → verifica: tre query reali riuscite.
- [ ] Archivio di accettazione: 64 province, un periodo, una categoria, un prodotto, eseguito una sola volta in sequenza → verifica: `manifest.json` completo, dati deduplicati, conservato come evidenza del criterio 10.
- [ ] `README.md` orientato ad agenti: sequenza scoperta → recupero, codici di uscita, contratto JSON → verifica: rilettura contro il criterio 9 del PRD.
- [ ] Aggiornare `LOG.md`, `docs/evaluation.md` (assenza di paginazione, echo verificato, `submit` non necessario) e la sezione di revisione → verifica: rilettura dei dieci criteri di accettazione uno per uno.

## Domande irrisolte

- Git: inizializzo il repository qui? Il documento cita un commit `edbb3b2` che non esiste in questa directory.
- Polars come indicato in `docs/evaluation.md`, oppure `csv`/`json` della libreria standard? I volumi sono di poche centinaia di righe per query e la deduplicazione è un insieme di tuple.
- Nome del pacchetto e del comando: confermo `osservaprezzi`?
- Licenza dei dati Istat, Unioncamere e BMTI ancora aperta: non blocca la costruzione, blocca la distribuzione di archivi derivati. Il manifest citerà fonte, URL e avvertenza senza dichiarare una licenza.

---

# Piano verifica fattibilità CLI Osservatorio Prezzi

## Fase preparatoria

- [x] Identificare skill e vincoli applicabili.
- [x] Definire perimetro, metodo e risultati attesi.
- [x] Esaminare struttura, README, dipendenze e cronologia recente di `opensdmx`.
- [x] Ricevere conferma del piano aggiornato prima dell'esecuzione.

## Fase PRD

- [x] Assumere un PRD preliminare, da validare e aggiornare dopo la ricognizione tecnica.
- [x] Chiarire obiettivo e confine della prima versione con una domanda alla volta.
- [x] Confrontare 2-3 impostazioni di prodotto e scegliere la CLI unificata orientata ai casi d'uso.
- [x] Presentare progressivamente il design: utenti, casi d'uso, comandi, dati, errori e test.
- [x] Ricevere approvazione del design.
- [x] Scrivere `PRD.md` includendo requisiti verificabili e assunzioni da validare durante la ricognizione.
- [x] Riesaminare il PRD per placeholder, contraddizioni, ambiguità e ampiezza dello scope.
- [x] Sottoporre il PRD scritto alla revisione dell'utente e integrare i requisiti richiesti.

## Fase di ricognizione

- [x] Eseguire il preflight previsto da `printing-press` e caricare la guida runtime di `agent-browser`.
- [x] Esaminare struttura e convenzioni del progetto `opensdmx` come riferimento per CLI orchestrabili da LLM.
- [x] Esplorare le tre sezioni dell’Osservatorio Prezzi con una sessione browser dedicata.
- [x] Registrare e classificare il traffico di rete generato dalle operazioni di consultazione.

## Fase di verifica tecnica

- [x] Individuare endpoint, metodi, parametri, paginazione, formati, dipendenze da sessione e protezioni anti-automazione.
- [x] Costruire per ciascun form la matrice controllo HTML → parametro HTTP → parametro CLI, coprendo ogni controllo utente abilitato.
- [x] Verificare con richieste HTTP non distruttive quali superfici siano riproducibili senza browser residente.
- [x] Valutare archivi on-demand: espansione delle dimensioni, filtro prodotto, cardinalità, chiavi naturali, ripresa e limiti prudenti.
- [x] Valutare stabilità, copertura e rischi distintamente per archivio beni e servizi, mercati italiani e mercati europei.
- [x] Disegnare una superficie CLI minima, coerente e adatta all'uso da parte di LLM, includendo output JSON e diagnostica degli errori.

## Fase conclusiva

- [x] Documentare evidenze, matrice di fattibilità, architettura proposta e raccomandazione in `docs/evaluation.md`.
- [x] Allineare `PRD.md` alle evidenze raccolte e distinguere requisiti confermati da requisiti condizionati.
- [x] Aggiornare `LOG.md` e segnare le attività completate.
- [x] Aggiungere qui una sezione di revisione finale con verifiche svolte, limiti e lavoro residuo.

## Domande irrisolte

- Solo valutazione o anche piccolo prototipo dopo il responso?
- La CLI deve coprire soltanto consultazione ed export?
- Esiste un formato di output preferito oltre a JSON e CSV?

## Revisione

### PRD preliminare

- Controllati placeholder, contraddizioni, ambiguità e ampiezza dello scope.
- Reso esplicito che l'esempio YAML descrive uno schema non ancora eseguibile.
- Precisato il contratto degli errori JSON su `stderr`.
- Documento registrato nel commit locale `edbb3b2`.

### Indagine di fattibilità

- Verificate tre query reali tramite browser e replay `curl` senza cookie.
- Confermata parità completa dei 14 controlli dati osservati.
- Identificato come non affidabile il sottodominio API ausiliario; l'HTML server-side copre valori e risultati.
- Verificato che input non validi falliscono silenziosamente e richiedono validazione preventiva.
- Definito archivio su 64 province con categoria obbligatoria, esecuzione sequenziale e manifest.
- Verdetto: GO con rischio medio per dipendenza dal contratto HTML e licenza dati da chiarire.

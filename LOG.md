# Log

## 2026-10-22

- Versione 0.4.3: chiusi gli ultimi punti della review. Esempi di `archive --help` e `agent-context` con `--product "pane fresco"`; elenco dei codici di provincia identico nei tre documenti; risoluzione della categoria descritta una volta sola nella skill.
- Primo giro della CI rosso su un test già esistente: su GitHub Actions Rich forza i colori e i codici ANSI spezzavano le frasi dell'help. Il test ora li toglie; nessun cambio al pacchetto, quindi nessuna nuova versione.
- Chiusi gli altri punti della review di `v0.4.0...HEAD`: il piano di `archive` dichiara le richieste di preparazione (`preparation_requests`), perché a cache vuota il dry-run interroga il portale per catalogo e domini; documentazione allineata al codice su codici di provincia, `--product` parziale solo senza categoria, catalogo osservato sull'ultimo periodo a Roma.
- Scoperto che la 0.4.1 non è su PyPI (ultima 0.4.0): finora il rilascio non aveva una procedura scritta. Adottata la procedura di opensdmx: `docs/release.md` con la lista di controllo (PyPI e verifica con `uvx` compresi) e CI con `pytest` su GitHub Actions. Versione 0.4.2, prima pubblicata su PyPI dopo la 0.4.0.
- Corretto `archive --product` sull'ortofrutta: confrontava `product` invece di `species`, quindi ogni richiesta finiva `no_match`. Emerso da una review di `v0.4.0...HEAD`; test di regressione in `tests/test_archive.py`. Versione 0.4.1.
- Documentazione: «Quattro regole» in SKILL.md (erano quattro, il testo diceva tre); nel README il catalogo costa una richiesta per categoria più una.
- Verifica dal vivo della CLI (84 richieste, nessun errore) su un confronto ortofrutta 2026 sul 2025. Nota per l'alternativa con gli indici: il server SDMX di ISTAT non ha risposto; l'IPCA Italia da Eurostat sta ora in `prc_hicp_minr` (COICOP 2018, dimensione `coicop18`), mentre `prc_hicp_manr` si ferma a dicembre 2025.

## 2026-08-18

- Aggiunto `find`: cerca un prodotto e dice in quale categoria si trova, risolvendo l'unico punto in cui restava da indovinare. `--product` completa da solo la categoria quando la corrispondenza è unica, come già previsto da RF-20. Catalogo osservato in una cella di riferimento, in cache. Versione 0.4.0.
- `--province` accetta gli identificatori territoriali standard (codice ISTAT, UTS, NUTS3, sigla) oltre al nome del portale: la traduzione sta nel client, quindi vale anche per query salvate e archivi. Versione 0.3.0.
- `archive` avverte quando si espande il tempo su `consumo` e propone il comando `opensdmx` sugli indici ISTAT, con il codice NUTS3 della provincia già risolto; l'avvertenza è anche nel manifest. Nasce da un difetto osservato nei test della skill: un agente aveva prodotto variazioni anno su anno e suggerito `archive` sui mesi per farne una serie storica.
- Aggiunti i codici territoriali ISTAT ai record di `consumo`, ricavati dal SITUAS con `opensituas`: schema di output alla versione 2, pacchetto alla 0.2.0.
- Scoperto che le quindici città metropolitane hanno codice provincia storico e codice UTS diversi (Roma 058 e 258): esposti entrambi, perché un join che perde Roma e Milano non dà errore, dà solo risultati incompleti.
- README: installazione della skill con `npx skills add` (verificata sul repo pubblico) e regola generale per l'uso agentico, cioè leggere `agent-context` e gli `--help` prima di costruire comandi.
- Aggiunta la Agent Skill `skills/osservaprezzi/` conforme alla specifica agentskills.io: SKILL.md più riferimenti su comandi e interpretazione dei dati. Validata con `skills-ref` e provata comando per comando.
- README: aggiunta la sezione sul valore dei dati, con il confronto fra pane (referenze eterogenee) e benzina (prodotto omogeneo) e la tabella delle analisi che reggono.
- Aggiunti al PRD due principi fondativi: l'aiuto come contratto e l'accesso serializzato al servizio pubblico (RF-27…RF-38).
- Aiuto autodescrittivo: esempi in ogni comando, opzioni che dichiarano collezione e dipendenze, comando `agent-context`, opzione `--agent`, `AGENTS.md`.
- Introdotto un lock su file che impedisce esecuzioni parallele sulla stessa macchina, con intervallo minimo condiviso fra processi e `--lock-timeout`.
- Aggiunta licenza MIT e riscritto il README per chi analizza i dati.
- Completata la prima versione: verificati sul campo `run` e `archive`, aggiunti i test di parità, contratto e archivio (57 test verdi).
- Eseguito l'archivio di accettazione su 64 province: 60 righe, nessun duplicato, manifest `complete` conservato in `docs/evidence/`.
- Corretto un difetto della vista tabella: `catalog` nascondeva la colonna `collection`, cioè l'identificatore da usare nei comandi successivi.
- Corretto un difetto della cache: i domini venivano memorizzati anche da pagine con filtri rifiutati.
- Chiusi tre rilievi della revisione: `defaults_used` nella provenienza di ogni record, test dell'uscita 6 per l'archivio parziale, nota sulla vista tabella nel README.
- Allineati `docs/evaluation.md` e `tasks/todo.md` con le evidenze e la revisione dei dieci criteri di accettazione.

## 2026-08-17

- Tracciato il traffico del portale con `agent-browser`: unica GET del documento, nessuna XHR di dati, endpoint ausiliario ancora non risolvibile.
- Verificato che l'echo dei filtri copre tutte le dimensioni e distingue parametro non valido da assenza di dati; `submit=Applica` non è necessario.
- Realizzata la prima versione della CLI `osservaprezzi`: catalog, describe, values, get, run, archive, version, cache.
- Aggiunte fixture HTML ritagliate, script di rigenerazione e 17 test offline verdi.
- Conclusa l'indagine di fattibilità: tre collezioni fattibili via GET HTML, con rischio medio.
- Documentate evidenze, replay HTTP, parità dei form, archivi e raccomandazione in `docs/evaluation.md`.
- Aggiornato il PRD con dimensioni reali, filtri espliciti e vincoli degli archivi.
- Aggiunti al PRD archivi on-demand con espansione delle dimensioni, manifest, deduplicazione e ripresa.
- Esteso il PRD con la parità completa tra controlli dei form HTML e parametri CLI.
- Scritto il PRD preliminare della CLI unificata e read-only.
- Preparato il piano per la verifica di fattibilità della CLI Osservatorio Prezzi.

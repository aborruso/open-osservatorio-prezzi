# Log

## 2026-08-18

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

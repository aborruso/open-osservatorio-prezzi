# Log

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

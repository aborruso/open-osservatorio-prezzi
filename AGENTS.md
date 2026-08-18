# Guida per agenti

`osservaprezzi` è una CLI read-only sui dati pubblici dell'Osservatorio Prezzi (MIMIT). Non scrive nulla sul portale, non richiede credenziali, non usa un browser.

## Primo comando

```bash
osservaprezzi agent-context
```

Restituisce in una sola chiamata l'intero contratto: collezioni, dimensioni con le loro dipendenze, comandi con un esempio ciascuno, codici di uscita, forma degli errori e garanzie. Non dedurre queste informazioni dall'help testuale: chiedile qui.

## Modalità agente

Aggiungi `--agent` a qualsiasi comando: equivale a `--json`, senza colori e senza interazione. Vale per dati ed errori.

```bash
osservaprezzi catalog --agent
osservaprezzi get consumo --year 2025 --month 5 --province Roma --category energia --agent
```

## Regole che evitano gli errori più comuni

1. **Non inventare valori.** Ogni valore ammesso si ottiene da `values`. I suggerimenti negli errori vengono dal form del portale, mai da somiglianze.
2. **I domini dipendenti richiedono i genitori.** I mesi dipendono dall'anno, le settimane da anno e mese: `values ortofrutta-it week --year 2025 --month 5`.
3. **`get` vuole tutti i filtri.** Non esistono default impliciti; per usare quelli del portale serve `--latest`, che li dichiara nel campo `defaults_used`.
4. **Distingui le uscite.** `2` significa che il portale ha rifiutato un valore, `3` che i filtri erano validi ma non c'erano dati. Non sono la stessa cosa.
5. **Leggi gli errori da `stderr`.** `stdout` contiene solo dati: `comando --agent 2>&1 >/dev/null | jq .`
6. **Prima di un archivio, chiedi il piano.** `archive ... --dry-run --agent` dice quante richieste servono, senza eseguirle.

## Nessun parallelismo

Le richieste al portale sono serializzate su tutta la macchina da un lock su file: una sola per volta, con un intervallo minimo condiviso fra processi. Lanciare più istanze in parallelo non accelera nulla — si alternano. Non tentare di aggirare il vincolo con task concorrenti: il traffico complessivo resterebbe lo stesso e serviresti solo a rendere imprevedibili le attese. Se un comando sembra fermo, sta aspettando il suo turno e lo dichiara su `stderr` con `--verbose`.

`--lock-timeout` limita l'attesa: allo scadere il comando esce con `service_unavailable` (uscita 5, `retryable: true`), mai proseguendo in parallelo.

## Interpretazione dei dati

I prezzi sono **livelli** in euro, non indici. Il portale sconsiglia i confronti fra province e fra mesi: sotto la stessa descrizione possono esserci varietà, marche e confezioni diverse. Per le serie storiche la fonte corretta sono gli indici ISTAT (NIC, IPCA), disponibili via SDMX.

Ogni record conserva `collection`, `source_url` e `retrieved_at`: citali quando riporti un valore.

## Sviluppo

```bash
uv sync
uv run pytest
```

I test girano su fixture HTML ritagliate, senza rete. `scripts/refresh_fixtures.py` le rigenera.

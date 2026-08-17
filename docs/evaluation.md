# Valutazione di fattibilità della CLI Osservatorio Prezzi

## Sintesi

La CLI è fattibile per tutte e tre le collezioni analizzate.

Il portale usa form HTML in GET e restituisce tabelle complete renderizzate dal server. Non sono richiesti autenticazione, browser residente, token CSRF o chiamate API per ottenere i dati. Le stesse interrogazioni sono state riprodotte con `curl` e hanno restituito HTTP 200.

Il livello di fattibilità è **alto**, con un rischio operativo **medio** dovuto a tre caratteristiche:

- il contratto dati è HTML e non è documentato come API;
- valori non validi producono pagine HTTP 200 senza errori e senza righe;
- gli endpoint ausiliari usati dal JavaScript per aggiornare mesi e settimane puntano a un sottodominio oggi non risolvibile.

La soluzione raccomandata è una CLI Python ispirata a `opensdmx`, basata su Typer, `httpx`, lxml e output strutturato. La CLI deve considerare i form HTML server-side come sorgente dei metadati e delle osservazioni, senza dipendere dagli endpoint ausiliari.

## Perimetro verificato

| Collezione CLI | Pagina ufficiale | Esito |
|---|---|---|
| `consumo` | [Rilevazioni mensili](https://osservaprezzi.mise.gov.it/prezzi/livelli/beni-e-servizi-di-largo-consumo/archivio-rilevazioni-beni-e-servizi-di-largo-consumo) | Fattibile |
| `ortofrutta-it` | [Mercati italiani](https://osservaprezzi.mise.gov.it/prezzi/livelli/prodotti-ortofrutticoli-all-ingrosso/mercati-italiani) | Fattibile |
| `ortofrutta-eu` | [Mercati europei](https://osservaprezzi.mise.gov.it/prezzi/livelli/prodotti-ortofrutticoli-all-ingrosso/mercati-europei) | Fattibile |

Ricognizione eseguita il 2026-08-17 con sessioni browser anonime, osservazione delle richieste di rete e replay HTTP read-only.

## Risultati dell’ispezione

### Beni e servizi di largo consumo

Il form dati ha metodo GET e quattro controlli utente.

| Etichetta | Nome HTML | Parametro CLI proposto | Valori osservati |
|---|---|---|---|
| Anno | `ANNO` | `--year` | `2021`–`2026` |
| Mese | `MESE` | `--month` | `1`–`12`, dipendenti dall’anno |
| Provincia | `f[PROVINCIA]` | `--province` | 64 province/città di rilevazione |
| Tipologia di prodotto | `f[TIPO_RECORD_MISE]` | `--category` | 6 codici |

Codici di categoria osservati:

| Codice | Etichetta |
|---|---|
| `altri_alim` | Alimentari |
| `energia` | Energetici |
| `groc` | Cura della persona e della casa |
| `ittici` | Ittici |
| `orto` | Ortofrutta |
| `servizi` | Servizi |

Schema della tabella `id-table-results`:

- descrizione prodotto;
- quotazione minima;
- quotazione massima;
- quotazione media;
- tipologia di prodotto.

Query campione: maggio 2025, Roma, energetici. Risultato: HTTP 200 e 6 righe.

### Mercati italiani

Il form dati ha metodo GET e cinque controlli utente.

| Etichetta | Nome HTML | Parametro CLI proposto | Valori osservati |
|---|---|---|---|
| Anno | `ANNO` | `--year` | `2021`–`2026` |
| Mese | `MESE` | `--month` | dipendenti dall’anno |
| Settimana | `SETTIMANA` | `--week` | dipendenti da anno e mese |
| Mercato | `f[MERCATO]` | `--market` | 23 mercati |
| Gruppo | `f[GRUPPO]` | `--group` | 5 gruppi |

Gruppi osservati: `AGRUMI`, `FRUTTA`, `ORTAGGI`, `PRODOTTI ESOTICI`, `PRODOTTI SECCHI`.

Schema della tabella `id-table-results`:

- specie;
- varietà;
- calibro;
- categoria;
- presentazione;
- origine;
- unità di misura;
- prezzo prevalente;
- prezzo minimo;
- prezzo massimo.

Query campione: maggio 2025, settimana 2, Roma, ortaggi. Risultato: HTTP 200 e 35 righe.

### Mercati europei

La struttura del form coincide con quella dei mercati italiani, ma i domini dei valori sono differenti.

| Etichetta | Nome HTML | Parametro CLI proposto | Valori osservati |
|---|---|---|---|
| Anno | `ANNO` | `--year` | `2021`–`2026` |
| Mese | `MESE` | `--month` | dipendenti dall’anno |
| Settimana | `SETTIMANA` | `--week` | dipendenti da anno e mese |
| Mercato | `f[MERCATO]` | `--market` | 11 mercati |
| Gruppo | `f[GRUPPO]` | `--group` | 3 gruppi |

Gruppi osservati: `AGRUMI`, `FRUTTA`, `ORTAGGI`.

Schema della tabella `id-table-results`:

- specie;
- varietà;
- calibro;
- categoria;
- presentazione;
- origine;
- unità di misura;
- prezzo.

Query campione: maggio 2025, settimana 2, Parigi, ortaggi. Risultato: HTTP 200 e 11 righe.

## Traffico e contratto HTTP

### Consultazioni principali

Tutte le consultazioni sono richieste GET sulla pagina della collezione. I valori del form sono serializzati nella query string; il parametro tecnico `submit=Applica` può essere gestito internamente.

Esempi osservati:

```text
...?ANNO=2025&MESE=5&f[PROVINCIA]=Roma&f[TIPO_RECORD_MISE]=energia&submit=Applica

...?ANNO=2025&MESE=5&SETTIMANA=2&f[MERCATO]=ROMA&f[GRUPPO]=ORTAGGI&submit=Applica
```

Tre richieste Fetch con credenziali omesse hanno restituito:

| Collezione | Stato | Content-Type | Dimensione indicativa | Righe |
|---|---:|---|---:|---:|
| `consumo` | 200 | `text/html; charset=utf-8` | 135 kB | 6 |
| `ortofrutta-it` | 200 | `text/html; charset=utf-8` | 149 kB | 35 |
| `ortofrutta-eu` | 200 | `text/html; charset=utf-8` | 131 kB | 11 |

Il replay con `curl`, senza cookie e senza sessione browser, ha restituito gli stessi stati, schemi e conteggi. Nell’ambiente di prova il resolver della shell non risolveva il dominio; il replay è stato completato con `--resolve` usando l’indirizzo A ottenuto dal DNS pubblico. Questo è un limite della sandbox locale, non un requisito del portale.

### Richieste ausiliarie

Il JavaScript incorporato tenta di aggiornare i valori temporali tramite:

```text
https://admin-osservaprezzi.mise.gov.it/upload-dati/open_api.php
```

Operazioni osservate:

| Operazione | Metodo | Parametri |
|---|---|---|
| Mesi disponibili | POST | `who=getMesiFonteFe`, `fonte`, `anno` |
| Settimane disponibili | GET | `who=getSettimaneMesiFonteFe`, `fonte`, `anno`, `mese` |

Codici `fonte` osservati: `1` per consumo, `3` per mercati italiani, `33` per mercati europei.

Il sottodominio ha restituito NXDOMAIN durante la verifica. Le pagine continuano tuttavia a funzionare perché il server principale rende già nei form mesi e settimane coerenti con i parametri GET. Per esempio, `ANNO=2021` ha restituito 12 mesi; gennaio 2021 ha restituito 5 settimane per i mercati italiani e 4 per quelli europei.

Decisione: gli endpoint ausiliari non devono essere una dipendenza della CLI. `values` deve interrogare la pagina HTML passando i filtri genitori e leggere le opzioni renderizzate dal server.

## Parità tra form e CLI

La copertura richiesta dal PRD è raggiungibile al 100% per i form dati.

| Collezione | Controlli dati visibili | Parametri CLI | Copertura |
|---|---:|---:|---:|
| `consumo` | 4 select | 4 | 100% |
| `ortofrutta-it` | 5 select | 5 | 100% |
| `ortofrutta-eu` | 5 select | 5 | 100% |

I tre form contengono inoltre il pulsante `Applica`; non rappresenta una scelta distinta e resta un dettaglio dell’adattatore. Il form globale di ricerca del sito non appartiene alla consultazione dei dati e non rientra nella superficie della CLI.

Tutti i select osservati sono a scelta singola, abilitati e non marcati `required`. La CLI non deve ereditare questa permissività: ogni query `get` deve indicare esplicitamente tutti i filtri, oppure usare un’opzione esplicita come `--latest`. I default del sito cambiano nel tempo e non sono adatti a query riproducibili.

## Validazione ed errori

Il portale non valida gli input in modo utile al chiamante. Due prove con provincia, mercato e settimana inesistenti hanno prodotto:

- HTTP 200;
- zero righe;
- nessun messaggio d’errore;
- controlli visualizzati con valori di default anziché con i valori richiesti.

Questo comportamento rende obbligatoria la seguente sequenza:

```text
leggi valori dal form → valida localmente → costruisci GET → verifica selezioni restituite → analizza tabella
```

Una risposta senza righe non può essere classificata automaticamente come “nessun dato” se i controlli restituiti non coincidono con la query. In quel caso la CLI deve restituire `invalid_parameter` o `contract_changed`.

## Archivi on-demand

### Caso tutte le province, periodo e prodotto

Per `consumo` sono state osservate 64 province/città. Con periodo, categoria e prodotto noti, l’archivio richiede 64 GET sequenziali: una richiesta per provincia.

Il prodotto non è un parametro del form. La CLI deve quindi:

1. richiedere `--category` insieme a `--product`, salvo che una cache di catalogo risolva il prodotto in modo univoco;
2. interrogare ciascuna provincia per il periodo e la categoria;
3. filtrare localmente la descrizione prodotto con confronto esatto normalizzato;
4. registrare province senza corrispondenza e richieste fallite nel manifest;
5. deduplicare con una chiave che includa periodo, provincia, categoria e descrizione prodotto.

Senza categoria nota sarebbero necessarie fino a 384 richieste per un solo periodo, perché le categorie sono sei. L’esecuzione deve quindi rifiutare questo ampliamento implicito e chiedere la categoria o una precedente risoluzione univoca.

### Limiti consigliati

- piano obbligatorio prima dell’esecuzione;
- `--dry-run --json` per agenti LLM;
- richieste sequenziali;
- pausa predefinita prudente tra richieste;
- limite predefinito di 100 richieste, modificabile esplicitamente;
- manifest aggiornato incrementalmente;
- ripresa delle sole combinazioni mancanti;
- nessun parallelismo predefinito.

### Avvertenza semantica

La pagina dei beni di largo consumo avverte che la stessa descrizione può riferirsi a combinazioni differenti di varietà, marca, confezione e punto vendita tra province o mesi. L’archivio può raccogliere i valori, ma non deve presentarli automaticamente come serie comparabili. Il manifest e l’output umano devono conservare questa avvertenza.

## Schema e chiavi naturali

Non sono stati osservati identificatori stabili dei record.

Chiavi naturali proposte:

| Collezione | Componenti della chiave |
|---|---|
| `consumo` | anno, mese, provincia, categoria, descrizione prodotto |
| `ortofrutta-it` | anno, mese, settimana, mercato, gruppo e tutti i sette descrittori merceologici |
| `ortofrutta-eu` | anno, mese, settimana, mercato, gruppo e tutti i sette descrittori merceologici |

I campi vuoti devono essere conservati come null. I prezzi devono essere analizzati come numeri decimali senza perdere la rappresentazione originale. Quando l’unità di misura è vuota, la CLI non deve inventarla nel campo sorgente; può aggiungere un campo derivato soltanto indicando la regola metodologica della pagina.

## Vincoli di accesso e riuso

Il file `robots.txt` non vieta le tre sezioni pubbliche; limita directory tecniche di Joomla come `/administrator/`, `/cache/` e `/components/`.

Le [note legali del portale](https://osservaprezzi.mise.gov.it/strumenti-per-l-utente/note-legali) dichiarano che visualizzazione, download e utilizzo comportano accettazione delle condizioni pubblicate; indicano inoltre CC-BY 3.0 per i testi salvo diversa indicazione e disponibilità libera e gratuita dei documenti scaricabili salvo avviso contrario.

Resta da chiarire prima della distribuzione di archivi a terzi la licenza specifica dei dati provenienti da Istat, Unioncamere e BMTI. La CLI può essere realizzata e usata per consultazione, ma deve citare sempre fonte e URL e non deve attribuire automaticamente ai dati la licenza dei testi del sito.

## Architettura raccomandata

La CLI dovrebbe essere un pacchetto autonomo, non un provider `opensdmx`: le pagine non espongono SDMX e forzarle in quel modello aumenterebbe la complessità.

Pattern da riusare da `opensdmx`:

- Typer per la superficie CLI;
- `httpx` con timeout, user-agent, retry limitati e rate limiting;
- lxml per parsing HTML;
- Polars per output CSV, JSONL e deduplicazione;
- separazione netta tra `stdout` dati e `stderr` diagnostica;
- sequenza `catalog/describe/values/get/run`;
- query YAML riproducibili;
- adattatori indipendenti e testabili con fixture;
- errori brevi senza stack trace per l’uso da agenti.

Componenti minimi:

```text
cli → query/validation → form discovery → collection adapter
    → HTML parser → normalized records → renderer/archive manifest
```

I due adattatori ortofrutticoli possono condividere il protocollo del form, ma devono mantenere schemi di output distinti: l’Italia espone prezzo prevalente, minimo e massimo; l’Europa un solo prezzo.

## Strategia di verifica dell’implementazione

Per ogni collezione:

- fixture HTML del form base, di un risultato valido, di un risultato vuoto e di una struttura incompatibile;
- test di parità controllo HTML → parametro CLI;
- test dei valori dipendenti da anno e mese senza endpoint ausiliari;
- test di preservazione delle celle vuote;
- test di input non valido e rilevamento dei fallback silenziosi;
- smoke test read-only con una singola query;
- test `archive --dry-run` e test di ripresa con fixture, senza eseguire archivi completi sul servizio pubblico.

## Decisione

**GO**, con queste condizioni:

1. usare le pagine GET server-side come unico contratto di runtime;
2. validare ogni parametro contro i form prima del recupero;
3. non dipendere da `admin-osservaprezzi.mise.gov.it`;
4. mantenere adattatori e schemi separati;
5. imporre limiti e sequenzialità agli archivi;
6. conservare provenienza e avvertenze metodologiche;
7. chiarire la licenza dei dati prima di distribuire archivi derivati.

Non è necessario un prototipo browser-based. Il passo successivo sicuro è implementare prima `catalog`, `describe`, `values` e una singola query `get` per `consumo`, quindi riusare il contratto per i due adattatori ortofrutticoli.

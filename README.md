# osservaprezzi

Porta sul tuo computer, in forma analizzabile, i prezzi pubblicati dall'[Osservatorio Prezzi](https://osservaprezzi.mise.gov.it/) del Ministero delle Imprese e del Made in Italy.

Sul portale quei dati si consultano una pagina alla volta, scegliendo mese, provincia e categoria da quattro menu a tendina. Se vuoi confrontare il prezzo del pane in tutta Italia, o seguire le quotazioni degli ortaggi in dieci mercati, ti servono decine di consultazioni manuali e altrettanti copia-incolla. Questo strumento fa quel lavoro al posto tuo e ti restituisce un CSV.

**Cosa NON fa**: non inventa valori, non stima, non completa i buchi. Se un dato non è pubblicato, te lo dice.

## I dati disponibili

| | Cosa contiene | Aggiornamento | Dettaglio |
|---|---|---|---|
| **consumo** | Prezzi al dettaglio di 159 tra beni e servizi: pane, carne, pesce, benzina, ortofrutta, parrucchiere, lavanderia… | mensile | 64 province |
| **ortofrutta-it** | Quotazioni all'ingrosso di frutta e verdura | settimanale | 23 mercati italiani |
| **ortofrutta-eu** | Le stesse quotazioni sui mercati esteri | settimanale | 11 mercati europei |

Si parte dal 2021. Per `consumo` ogni riga riporta prezzo minimo, massimo e medio rilevati nella provincia; per l'ortofrutta specie, varietà, calibro, origine e prezzo.

## Installazione

Il modo più semplice, se hai [uv](https://docs.astral.sh/uv/):

```bash
uv tool install osservaprezzi
```

Per provarlo senza installare nulla:

```bash
uvx osservaprezzi catalog
```

Con pip:

```bash
pip install osservaprezzi
```

Verifica che funzioni:

```bash
osservaprezzi version
```

## I primi tre comandi

### Cosa c'è

```bash
osservaprezzi catalog
```

```
collection     title                                                      status     dimensions
-------------  ---------------------------------------------------------  ---------  --------------------------------
consumo        Rilevazioni mensili di beni e servizi di largo consumo     available  year, month, province, category
ortofrutta-it  Prodotti ortofrutticoli all'ingrosso nei mercati italiani  available  year, month, week, market, group
ortofrutta-eu  Prodotti ortofrutticoli all'ingrosso nei mercati europei   available  year, month, week, market, group
```

Le parole nell'ultima colonna sono i filtri che dovrai indicare. Per `consumo` servono anno, mese, provincia e categoria.

### Quali valori posso usare

Non devi indovinarli: te li elenca lo strumento, chiedendoli al portale.

```bash
osservaprezzi values consumo category
```

```
value       label
----------  -------------------------------
altri_alim  Alimentari
energia     Energetici
groc        Cura della persona e della casa
ittici      Ittici
orto        Ortofrutta
servizi     Servizi
```

Stessa cosa per province, mercati, gruppi:

```bash
osservaprezzi values ortofrutta-eu market
```

```
value       label
----------  ----------
AMBURGO     AMBURGO
BARCELLONA  BARCELLONA
BERLINO     BERLINO
BOLOGNA     BOLOGNA
LIONE       LIONE
MILANO      MILANO
MONACO      MONACO
PARIGI      PARIGI
PERPIGNANO  PERPIGNANO
ROMA        ROMA
STOCCARDA   STOCCARDA
```

Attenzione a mesi e settimane: dipendono dall'anno, quindi vanno chiesti indicandolo.

```bash
osservaprezzi values ortofrutta-it week --year 2021 --month 1
```

Gennaio 2021 ha cinque settimane, maggio 2025 ne ha quattro: è il portale a dirlo.

### I dati

```bash
osservaprezzi get consumo --year 2025 --month 5 --province Roma --category ittici
```

```
year  month  province  category  product                                          price_min  price_max  price_avg
----  -----  --------  --------  -----------------------------------------------  ---------  ---------  ---------
2025  5      Roma      ittici    Alici Fresche Di Pescata (1000 Gr)               5.9        29.9       10.36
2025  5      Roma      ittici    Sgombri Freschi Di Pescata (1000 Gr)             5.99       24.0       10.99
2025  5      Roma      ittici    Merluzzi O Naselli Freschi Di Pescata (1000 Gr)  18.01      29.9       24.99
2025  5      Roma      ittici    Trote Di Allevamento Fresche (1000 Gr)           6.9        16.0       10.5
2025  5      Roma      ittici    Salmone Fresco (1000 Gr)                         12.9       30.92      20.14
2025  5      Roma      ittici    Mitili O Cozze Fresche (1000 Gr)                 4.44       7.01       5.57
2025  5      Roma      ittici    Vongole Fresche (1000 Gr)                        5.99       28.0       21.53
```

I prezzi sono in euro, riferiti alla quantità tra parentesi.

## Portare i dati in Excel, R, Python

Aggiungi `--csv` e `--output`:

```bash
osservaprezzi get consumo --year 2025 --month 5 --province Bologna --category energia \
  --csv --output benzina-bologna.csv
```

Il file contiene anche l'indirizzo esatto della pagina da cui il dato proviene e il momento in cui è stato letto — utile quando dovrai citare la fonte:

```
year,month,province,category,product,price_min,price_max,price_avg,category_label,collection,source_url,retrieved_at
2025,5,Bologna,energia,Gasolio Per Auto Con Servizio Alla Pompa (1 L),1.512,2.142,1.75,Energetici,consumo,https://…
```

Con `--json` ottieni invece una struttura pronta per essere elaborata.

## Il pane in tutta Italia: gli archivi

Qui lo strumento dà il meglio. Vuoi il prezzo di un prodotto in tutte le province? Non serve ripetere 64 comandi:

```bash
osservaprezzi archive consumo \
  --year 2025 --month 5 --category altri_alim \
  --all province \
  --product "Pane Fresco Con Farina Di Grano (1000 Gr)" \
  --output pane-maggio-2025
```

Prima di partire puoi vedere quanto costerà, senza chiedere niente al portale:

```bash
osservaprezzi archive consumo --year 2025 --month 5 --category altri_alim \
  --all province --dry-run
```

```
richieste previste: 64
dimensioni espanse: province (64)
```

Al termine trovi due file:

- **`data.csv`** — i dati, senza duplicati;
- **`manifest.json`** — cosa è stato chiesto, a quale indirizzo, quando, quali province hanno risposto e quali no.

Nell'esempio reale: 64 province interrogate, 60 con quel pane, 4 dove non è stato rilevato. Il prezzo medio andava da 2,42 a 7,04 euro al chilo.

Se l'esecuzione si interrompe, riprende da dove era rimasta:

```bash
osservaprezzi archive … --output pane-maggio-2025 --resume
```

Puoi espandere anche altre dimensioni — tutti i mercati per una settimana, per esempio:

```bash
osservaprezzi archive ortofrutta-it --year 2025 --month 5 --week 2 \
  --group ORTAGGI --all market --output ortaggi-settimana2
```

## Riusare la stessa interrogazione

Salva i filtri in un file e rieseguili quando vuoi:

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
```

```bash
osservaprezzi run ortaggi-roma.yaml --output ortaggi.csv
```

È il modo più semplice per rifare la stessa estrazione il mese prossimo, o per condividerla con un collega.

## Leggere i dati senza sbagliare

Tre avvertenze che vengono dal portale stesso e che conviene prendere sul serio.

**Non sono serie storiche.** Sotto la stessa descrizione — «Pane Fresco Con Farina Di Grano» — possono esserci pani diversi per varietà, marca, confezione e punto vendita, e la composizione cambia da una provincia all'altra e da un mese all'altro. Confrontare Milano con Palermo, o maggio con giugno, porta a conclusioni sbagliate. Per l'andamento nel tempo la fonte corretta sono gli indici dei prezzi al consumo dell'Istat, non questi livelli.

**Le assenze significano «non rilevato».** Se un prodotto non compare per una provincia non vuol dire che lì non si venda: quel mese non è stato rilevato. Negli archivi queste situazioni sono registrate nel manifest, non nascoste.

**Il dettaglio è provinciale, non comunale.** Le province coperte sono 64 delle 107 italiane.

## Un vincolo voluto: una richiesta alla volta

Il portale è un servizio pubblico pensato per la consultazione umana, senza API. Per non sovraccaricarlo, lo strumento esegue **una sola richiesta alla volta su tutto il computer**: se lanci due comandi in parallelo, il secondo aspetta il suo turno invece di aggiungere traffico. Fra una richiesta e l'altra passa almeno un secondo.

Non è una limitazione da aggirare: è il motivo per cui uno strumento del genere può esistere senza creare problemi a chi lo ospita. Se ti servono volumi molto grandi, la strada giusta è chiedere i dati alla fonte.

## Quando qualcosa non va

Lo strumento distingue i casi, invece di restituire silenziosamente una tabella vuota come fa il portale:

| Messaggio | Cosa significa |
|---|---|
| `invalid_parameter` | hai indicato un valore che non esiste; ti vengono elencati quelli ammessi |
| `no_data` | i filtri erano corretti, ma per quel periodo non ci sono rilevazioni |
| `contract_changed` | il portale ha cambiato struttura: lo strumento va aggiornato |
| `service_unavailable` | il portale non risponde, oppure un'altra esecuzione è in corso |

Se sbagli il nome di un mercato te lo dice subito, con la lista giusta:

```bash
osservaprezzi get ortofrutta-it --year 2025 --month 5 --week 2 --market MESSINA --group ORTAGGI
# errore [invalid_parameter]: valori non ammessi dal portale: market
#   valori ammessi: BERGAMO, BOLOGNA, BOLZANO, CAGLIARI, CATANIA, …
```

## Usarlo con un assistente AI

Ogni comando ha `--agent`, che produce output strutturato, e c'è un comando che descrive l'intero strumento in una volta sola:

```bash
osservaprezzi agent-context
```

Se lavori con Claude, Copilot o simili, il file [`AGENTS.md`](AGENTS.md) contiene le istruzioni da dare all'assistente.

## Fonte e licenza

I dati provengono dall'Osservatorio Prezzi del MIMIT, che li elabora a partire da rilevazioni Istat, Unioncamere e BMTI. Cita sempre la fonte e l'indirizzo della pagina: li trovi in ogni riga esportata.

La licenza dei dati non è dichiarata in modo univoco dal portale: prima di ripubblicare archivi derivati, verifica le condizioni con le fonti.

Il codice di questo strumento è rilasciato con licenza MIT (vedi [`LICENSE`](LICENSE)).

## Contribuire

Segnalazioni e proposte sono benvenute. Per lavorare al codice:

```bash
uv sync
uv run pytest
```

I test girano su pagine HTML salvate in locale e non richiedono connessione.

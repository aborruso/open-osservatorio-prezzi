# osservaprezzi

Porta sul tuo computer, in forma analizzabile, i prezzi pubblicati dall'[Osservatorio Prezzi](https://osservaprezzi.mise.gov.it/) del Ministero delle Imprese e del Made in Italy.

Sul portale quei dati si consultano una pagina alla volta, scegliendo mese, provincia e categoria da quattro menu a tendina. Se vuoi confrontare il prezzo del pane in tutta Italia, o seguire le quotazioni degli ortaggi in dieci mercati, ti servono decine di consultazioni manuali e altrettanti copia-incolla. Questo strumento fa quel lavoro al posto tuo e ti restituisce un CSV.

**Cosa NON fa**: non inventa valori, non stima, non completa i buchi. Se un dato non è pubblicato, te lo dice.

Prima di impostare un'analisi leggi [A cosa servono davvero questi dati](#a-cosa-servono-davvero-questi-dati): non tutti i confronti che sembrano possibili lo sono, e la differenza dipende dal prodotto.

## I dati disponibili

| | Cosa contiene | Aggiornamento | Dettaglio |
|---|---|---|---|
| **consumo** | Prezzi al dettaglio di beni e servizi — pane, carne, pesce, benzina, ortofrutta, parrucchiere, lavanderia… — fino a circa 160 voci, con differenze fra province | mensile | 64 province |
| **ortofrutta-it** | Quotazioni all'ingrosso di frutta e verdura | settimanale | 23 mercati italiani |
| **ortofrutta-eu** | Le stesse quotazioni sui mercati esteri | settimanale | 11 mercati europei |

Si parte dal 2021. Per `consumo` ogni riga riporta prezzo minimo, massimo e medio rilevati nella provincia; per l'ortofrutta specie, varietà, calibro, origine e prezzo.

## Installazione

Il modo più semplice, se hai [uv](https://docs.astral.sh/uv/):

```bash
uv tool install openosservaprezzi
```

Il pacchetto si chiama `openosservaprezzi`, il comando che installa è `osservaprezzi`.

Per provarlo senza installare nulla:

```bash
uvx --from openosservaprezzi osservaprezzi catalog
```

Con pip:

```bash
pip install openosservaprezzi
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

### In quale categoria sta quello che cerco?

È l'unica cosa che restava da indovinare: il portale non espone il prodotto come filtro, quindi bisogna sapere che il salmone sta negli «ittici» e il pane negli «alimentari». Ora lo chiedi:

```bash
osservaprezzi find consumo salmone
```

```
product                   category  label
------------------------  --------  ------
Salmone Fresco (1000 Gr)  ittici    Ittici
```

La ricerca ignora accenti e maiuscole e accetta anche pezzi di nome. La prima volta costruisce un indice interrogando le categorie (una decina di secondi), poi risponde dalla cache in un istante.

Un avvertimento che trovi anche nell'output: quell'elenco è **osservato**, non dichiarato. Viene da una provincia di riferimento e da un mese preciso — il campo `observed_with` te lo dice — e altrove il paniere può essere diverso.

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

### I codici ISTAT delle province

Ogni riga di `consumo` porta con sé le codifiche territoriali, così il join con altre fonti — popolazione, redditi, confini geografici, dati SDMX — non richiede una tabella di conversione fatta a mano:

```
province,province_istat,province_uts,province_nuts3
Roma,058,258,ITI43
```

Sono tre perché servono a cose diverse. `province_istat` è il codice provincia classico, quello usato nella gran parte dei dataset ISTAT; `province_uts` è il codice dell'unità territoriale sovracomunale, che **per le quindici città metropolitane è diverso** (Roma 058 e 258, Milano 015 e 215); `province_nuts3` è la codifica europea. Esporne uno solo avrebbe rotto in silenzio i join proprio sulle province più grandi.

La corrispondenza è generata dal SITUAS dell'ISTAT ed è documentata in [`references/README.md`](references/README.md), inclusi i quattro nomi che il portale scrive diversamente (Aosta, Bolzano, Forlì, Reggio Emilia).

### Puoi anche chiedere per codice

Vale in entrambe le direzioni: se parti da un dataset ISTAT hai in mano un codice, non un nome, e `--province` lo accetta così com'è.

```bash
osservaprezzi get consumo --year 2025 --month 5 --province ITG12 --category ittici
osservaprezzi get consumo --year 2025 --month 5 --province 082   --category ittici
osservaprezzi get consumo --year 2025 --month 5 --province PA    --category ittici
```

Tutti e tre chiedono Palermo. Sono ammessi il nome del portale, il codice provincia (con o senza zero iniziale), quello dell'unità territoriale, il NUTS3 e la sigla automobilistica — anche nelle query YAML e negli archivi. Un codice che non corrisponde a nessuna provincia rilevata è un errore esplicito, non una richiesta a vuoto verso il portale.

## Il pane in tutta Italia: gli archivi

Qui lo strumento dà il meglio. Vuoi il prezzo di un prodotto in tutte le province? Non serve ripetere 64 comandi:

```bash
osservaprezzi archive consumo \
  --year 2025 --month 5 \
  --all province \
  --product "pane fresco" \
  --output pane-maggio-2025
```

Non serve più indicare la categoria né la descrizione completa: se il testo corrisponde a un solo prodotto, la CLI lo riconosce e completa il filtro da sola, dicendotelo. Se corrisponde a più prodotti, l'errore li elenca invece di scegliere al posto tuo.

Prima di partire puoi vedere quanto costerà:

```bash
osservaprezzi archive consumo --year 2025 --month 5 \
  --all province --product "pane fresco" --dry-run
```

```
prodotto risolto dal catalogo: 'Pane Fresco Con Farina Di Grano (1000 Gr)' in category=altri_alim
richieste previste: 64
dimensioni espanse: province (64)
```

Il piano in sé non interroga il portale; se però hai usato `--product` e il catalogo non è ancora in cache, viene costruito ora — sono le stesse richieste che farebbe `find`, una per categoria.

Al termine trovi due file:

- **`data.csv`** — i dati, senza duplicati;
- **`manifest.json`** — cosa è stato chiesto, a quale indirizzo, quando, quali province hanno risposto e quali no.

Nell'esempio reale: 64 province interrogate, 60 con quel pane, 4 dove non è stato rilevato. Il prezzo medio andava da 2,42 a 7,04 euro al chilo.

Se l'esecuzione si interrompe, riprende da dove era rimasta:

```bash
osservaprezzi archive … --output pane-maggio-2025 --resume
```

### Se espandi i mesi, lo strumento ti avvisa

Espandere la dimensione temporale è tecnicamente possibile e a volte utile — per sapere in quali mesi un prodotto è stato rilevato, per esempio. Ma è anche il modo più rapido per costruire una serie storica che i dati non sostengono, quindi la CLI te lo dice prima di partire:

```
attenzione: stai espandendo la dimensione temporale (month, 12 periodi).
  Fra un periodo e l'altro cambiano le referenze campionate: una variazione fra
  questi livelli mescola il rincaro reale con il cambio di paniere.
  Per l'andamento nel tempo la fonte corretta sono gli indici ISTAT:
    opensdmx get 167_744_DF_DCSP_NIC1B2015_1 --provider istat --FREQ M
      --REF_AREA ITG12 --DATA_TYPE 39 --MEASURE 4 --E_COICOP_REV_ISTAT 00
```

Il comando suggerito è già pronto, con il codice territoriale della provincia che hai chiesto. Nessun blocco: l'archivio parte lo stesso, e nel `manifest.json` resta scritto sotto `temporal_expansion` che quella serie non è comparabile — così l'avvertenza viaggia insieme ai dati anche se il CSV finisce in altre mani.

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

## A cosa servono davvero questi dati

Vale la pena saperlo prima di impostare un'analisi, perché il valore di questi numeri cambia molto a seconda di cosa si guarda.

### Il limite da cui parte tutto

Una descrizione come «Pane Fresco Con Farina Di Grano (1000 Gr)» non identifica un prodotto: identifica una **categoria**. Dentro ci finiscono pani diversi per varietà, marca, confezione e negozio in cui sono stati rilevati — quella combinazione, nel linguaggio Istat, si chiama *referenza*. Ogni provincia campiona le proprie, e da un mese all'altro il campione può cambiare.

Lo si vede nei dati stessi. Maggio 2025, stessa descrizione, stesso mese:

| | minimo | massimo | medio |
|---|---:|---:|---:|
| Napoli | 2,00 | 2,99 | **2,42** |
| Roma | 2,29 | 4,89 | **3,41** |
| Palermo | 3,50 | 5,00 | **4,42** |
| Milano | 2,99 | 7,00 | **4,97** |
| Bologna | 3,99 | 7,80 | **5,23** |

A Milano il pane più caro costa 2,3 volte il più economico, nella stessa città e nello stesso mese: quella dispersione interna è la prova che sotto l'etichetta ci sono prodotti differenti. Perciò la distanza fra Napoli e Bologna mescola due cose inseparabili — quanto costa il pane e quali pani sono finiti nel campione.

Il portale lo dice esplicitamente: i confronti fra città e fra mesi «possono essere effettuati correttamente solo utilizzando gli indici dei prezzi al consumo».

### Cosa regge comunque

**La dispersione dentro una singola rilevazione.** Minimo, massimo e medio della stessa cella vengono dalla stessa rilevazione: confrontarli fra loro è legittimo. È anche l'informazione più concreta per chi compra — dice quanto conviene guardarsi intorno — e per chi osserva un mercato, perché misura quanto è differenziato.

**I prodotti omogenei.** L'avvertenza morde dove la referenza è variabile; dove il prodotto è sempre lo stesso quasi sparisce. Benzina verde self, maggio 2025:

| | medio |
|---|---:|
| Milano | 1,688 |
| Bologna | 1,692 |
| Napoli | 1,695 |
| Palermo | 1,715 |

Uno scarto dell'1,6% fra la prima e l'ultima, contro il più del doppio che separa le stesse città sul pane. La benzina verde è la benzina verde ovunque: niente varietà, niente marca artigianale, niente pezzatura. Sui carburanti il confronto territoriale regge.

**L'ortofrutta all'ingrosso.** Lì specie, varietà, calibro, categoria, presentazione e origine sono colonne esplicite, non nascoste in una descrizione: sai esattamente cosa stai confrontando, quindi puoi confrontarlo.

### Cosa non regge

Classifiche fra città sugli alimentari e serie storiche di qualsiasi voce. Non è una cautela formale: sono conclusioni che i dati non sostengono. Per l'andamento nel tempo la fonte corretta sono gli indici dei prezzi al consumo dell'Istat, costruiti confrontando ogni prodotto con se stesso e quindi immuni al cambio di composizione. In cambio danno la variazione, non il prezzo in euro. Sono pubblicati via SDMX: il **NIC** arriva fino al dettaglio provinciale (132 aree fra Italia, ripartizioni, regioni e province) ed espone numeri indice e variazioni congiunturali e tendenziali; l'**IPCA**, l'indice armonizzato europeo, è invece solo nazionale.

Sono due strumenti con due mestieri: i **livelli** dicono quanto si paga qui e ora, gli **indici** come si muove nel tempo.

### Perché allora esistono

Questi livelli nascono dalla stessa raccolta che alimenta gli indici dei prezzi al consumo, ma non sono dati grezzi: sono elaborazioni. Per la rilevazione tradizionale e le fonti amministrative il portale pubblica il prezzo minimo e massimo effettivamente rilevati e la media delle quotazioni validate; per i dati degli scanner di cassa il minimo e il massimo fra i prezzi medi mensili di ciascun codice a barre, e una media provinciale ponderata sul peso campionario dei punti vendita. Le singole quotazioni per punto vendita non sono pubbliche. Servono inoltre alla sorveglianza dei prezzi — individuare situazioni anomale, alimentare il lavoro del Garante e delle commissioni di allerta rapida — dove basta un ordine di grandezza pubblico e verificabile.

### In breve

| Analisi | Regge? |
|---|---|
| Dispersione min-max in una provincia e un mese | sì |
| Confronto fra province sui carburanti | sì |
| Ortofrutta all'ingrosso fra mercati | sì, i descrittori sono espliciti |
| Copertura: dove e quando un prodotto è rilevato | sì |
| Classifica delle città sul costo degli alimentari | no |
| Serie storica di un prodotto | no, usa gli indici Istat |

## Altre due cose da sapere

**Le assenze significano «non rilevato».** Se un prodotto non compare per una provincia non vuol dire che lì non si venda: quel mese non è stato rilevato. A Roma i prodotti ittici sono sette, ad Aosta quattro. Negli archivi queste situazioni sono registrate nel manifest, non nascoste.

**Il dettaglio è provinciale, non comunale.** Le province coperte sono 64 delle 107 italiane.

## Un vincolo voluto: una richiesta alla volta

Il portale è un servizio pubblico pensato per la consultazione umana, senza API. Per non sovraccaricarlo, lo strumento lascia passare **una sola richiesta alla volta su tutto il computer**, con almeno un secondo fra l'una e l'altra. Se lanci due comandi in parallelo non raddoppi il traffico: si alternano, e nell'insieme vanno alla velocità di uno solo. Un archivio lungo non ti impedisce quindi di fare nel frattempo una singola interrogazione — aspetterà solo il suo turno.

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

### Regola generale, con qualsiasi assistente

Prima di lasciargli costruire comandi, **chiedigli di leggere l'aiuto della CLI**. È il modo più semplice per evitare che inventi opzioni o valori:

> «Prima di eseguire qualsiasi cosa, lancia `osservaprezzi agent-context` e `osservaprezzi <comando> --help`, poi usa solo le opzioni e i valori che trovi lì.»

`agent-context` restituisce in una sola chiamata collezioni, dimensioni con le loro dipendenze, comandi con esempi, codici di uscita e forma degli errori. Ogni comando ha inoltre esempi eseguibili nel proprio `--help`, e ogni opzione dichiara a quale collezione appartiene. Vale anche quando la CLI verrà aggiornata: l'aiuto cambia con lei, un prompt scritto a mano no.

### La Agent Skill

Nel repository c'è una **[Agent Skill](skills/osservaprezzi/)** conforme alla [specifica agentskills.io](https://agentskills.io/specification.md). Installarla significa che l'assistente sa da solo quando usare questi dati, come interrogarli e — soprattutto — quali confronti reggono e quali no.

```bash
npx skills add aborruso/open-osservatorio-prezzi
```

Aggiungi `-g` per installarla a livello utente invece che nel progetto corrente, e `--list` per vedere cosa contiene senza installare nulla. In alternativa basta copiare la cartella `skills/osservaprezzi/` in `~/.claude/skills/`.

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

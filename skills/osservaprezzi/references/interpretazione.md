# Cosa si può concludere da questi dati

Questi numeri sono facili da leggere e facili da usare male. La differenza non è formale: certe conclusioni i dati le reggono, altre no, e dipende dal prodotto.

## Il limite da cui parte tutto

Una descrizione come «Pane Fresco Con Farina Di Grano (1000 Gr)» non identifica un prodotto: identifica una **categoria**. Dentro ci finiscono pani diversi per varietà, marca, confezione e negozio in cui sono stati rilevati — quella combinazione, nel linguaggio ISTAT, si chiama *referenza*. Ogni provincia campiona le proprie, e da un mese all'altro il campione può cambiare.

Lo si vede nei dati stessi. Maggio 2025, stessa descrizione, stesso mese:

| | minimo | massimo | medio |
|---|---:|---:|---:|
| Napoli | 2,00 | 2,99 | 2,42 |
| Roma | 2,29 | 4,89 | 3,41 |
| Palermo | 3,50 | 5,00 | 4,42 |
| Milano | 2,99 | 7,00 | 4,97 |
| Bologna | 3,99 | 7,80 | 5,23 |

A Milano il pane più caro costa 2,3 volte il più economico, nella stessa città e nello stesso mese: quella dispersione interna è la prova che sotto l'etichetta ci sono prodotti differenti. La distanza fra Napoli e Bologna mescola perciò due cose inseparabili — quanto costa il pane e quali pani sono finiti nel campione.

Il portale lo scrive esplicitamente: i confronti fra città e fra mesi «possono essere effettuati correttamente solo utilizzando gli indici dei prezzi al consumo».

## Cosa regge

**La dispersione dentro una singola rilevazione.** Minimo, massimo e medio della stessa cella vengono dallo stesso campione: confrontarli fra loro è legittimo. È anche l'informazione più concreta per chi compra, perché dice quanto conviene guardarsi intorno, e per chi osserva un mercato, perché ne misura la differenziazione.

**I prodotti omogenei.** L'avvertenza morde dove la referenza è variabile; dove il prodotto è sempre lo stesso quasi sparisce. Benzina verde self, maggio 2025:

| | medio |
|---|---:|
| Milano | 1,688 |
| Bologna | 1,692 |
| Napoli | 1,695 |
| Palermo | 1,715 |

Uno scarto dell'1,6% fra la prima e l'ultima, contro il più del doppio che separa le stesse città sul pane. La benzina verde è la benzina verde ovunque: niente varietà, niente marca artigianale, niente pezzatura. Sui carburanti il confronto territoriale regge, ed è anche il motivo per cui su quel fronte esiste una sorveglianza dedicata.

**L'ortofrutta all'ingrosso.** Specie, varietà, calibro, categoria, presentazione e origine sono colonne esplicite, non nascoste in una descrizione: sai esattamente cosa stai confrontando, quindi puoi confrontarlo.

**La copertura.** Dove e quando un prodotto è stato rilevato è di per sé un'informazione: a Roma i prodotti ittici sono sette, ad Aosta quattro.

## Cosa non regge

Classifiche fra città sugli alimentari e serie storiche di qualsiasi voce. Non è una cautela formale: sono conclusioni che i dati non sostengono.

Se la richiesta riguarda l'inflazione, l'andamento nel tempo o il confronto fra territori su beni non omogenei, la risposta corretta non è produrre comunque una tabella: è dire perché quella domanda ha un'altra fonte, e indicarla.

## L'alternativa corretta: gli indici ISTAT

Gli indici dei prezzi al consumo confrontano **ogni prodotto con se stesso** — stessa referenza, stesso punto vendita — da un periodo al successivo, e solo dopo aggregano. Il cambio di composizione viene neutralizzato per costruzione. In cambio si perde il livello: l'indice dice «+2,3% sul mese», non «4,97 € al chilo».

Sono pubblicati via SDMX sul catalogo ISTAT e si interrogano con la CLI `opensdmx`:

| | Contenuto | Territorio |
|---|---|---|
| **NIC** (`167_744_DF_DCSP_NIC1B2015_1`) | numeri indice, variazioni congiunturali e tendenziali | 132 aree, fino alle province |
| **IPCA** | come sopra, armonizzato UE | solo Italia |
| **Pesi NIC** (`167_743_DF_DCSP_NIC3B2015_3`) | struttura del paniere su base 1.000.000 | solo Italia |

Attenzione a un trade-off che sorprende: in SDMX il dettaglio merceologico e quello territoriale non sono cumulabili. Il dataflow con 715 voci ECOICOP a 5 cifre (fino a «pane fresco») è **solo nazionale**; quello provinciale si ferma a 58 voci a 3 cifre, dove il massimo dettaglio alimentare è «prodotti alimentari». Il pane fresco *a Palermo, in euro* esiste soltanto nei livelli dell'Osservatorio Prezzi.

## La scala completa dei dati

| | Cosa contiene | Pubblico |
|---|---|---|
| Microdati della rilevazione | singola quotazione per prodotto e punto vendita | no |
| **Livelli dell'Osservatorio** | min, max, medio per provincia, mese, descrizione | sì, questa CLI |
| **Indici NIC / IPCA** | numeri indice e variazioni percentuali | sì, via SDMX |
| **Pesi del paniere** | quanto ciascuna voce incide sull'indice | sì, via SDMX |

I livelli non sono dati grezzi: sono elaborazioni. Per la rilevazione tradizionale e le fonti amministrative il portale pubblica il minimo e il massimo effettivamente rilevati e la media delle quotazioni validate; per gli scanner di cassa il minimo e il massimo fra i prezzi medi mensili di ciascun codice a barre, con media provinciale ponderata sul peso campionario dei punti vendita.

## Come riportare un risultato

- Indica sempre **mese, territorio e descrizione completa** del prodotto: senza, il numero non è verificabile.
- Cita la fonte: ogni record contiene `source_url` e `retrieved_at`.
- Se stai confrontando territori, di' esplicitamente se il prodotto è omogeneo (carburanti) o no (alimentari), e nel secondo caso accompagna il confronto con l'avvertenza.
- Distingui l'assenza dal valore nullo: `no_data` e `no_match` significano «non rilevato», mai «prezzo zero» o «prodotto non venduto».
- La licenza dei dati di origine (ISTAT, Unioncamere, BMTI) non è dichiarata in modo univoco dal portale: prima di ridistribuire archivi derivati vanno verificate le condizioni.

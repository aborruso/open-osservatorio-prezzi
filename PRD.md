# CLI per l’Osservatorio Prezzi

## Stato del documento

- Tipo: PRD preliminare
- Data: 2026-08-17
- Stato: fattibilità verificata, pronto per il piano di implementazione
- Nome provvisorio del prodotto: `osservaprezzi`

Questo documento definisce il prodotto desiderato. Le caratteristiche tecniche delle sorgenti, gli endpoint e i nomi effettivi dei filtri saranno confermati mediante ricognizione del portale e analisi non distruttiva del traffico di rete.

## Contesto

Il portale Osservatorio Prezzi presenta dati pubblici attraverso pagine web dedicate a più domini informativi. La consultazione manuale rende difficile integrare questi dati in script, analisi riproducibili e flussi governati da modelli linguistici.

Il prodotto applica lo stesso principio adottato da `opensdmx`: un agente interpreta la richiesta dell’utente e costruisce una query strutturata; la CLI valida la query e recupera i dati effettivamente pubblicati. Il modello linguistico non deve inventare valori, filtri o osservazioni.

## Obiettivo

Creare una CLI read-only, stabile e componibile che permetta a persone, script e agenti LLM di scoprire, interrogare ed esportare i dati di tre sezioni dell’Osservatorio Prezzi:

- archivio delle rilevazioni di beni e servizi di largo consumo;
- prodotti ortofrutticoli all’ingrosso nei mercati italiani;
- prodotti ortofrutticoli all’ingrosso nei mercati europei.

La CLI deve nascondere le differenze tecniche tra API, download e pagine HTML, mantenendo visibili provenienza e significato dei dati.

## Utenti principali

### Agente LLM

Scopre collezioni e filtri, costruisce query valide, recupera risultati strutturati e interpreta errori senza analizzare HTML o pilotare un browser.

### Analista

Esplora periodi e dimensioni disponibili, esporta dati in CSV e salva interrogazioni riproducibili.

### Sviluppatore o pipeline automatizzata

Integra il comando in script e processi schedulati usando output deterministico, codici di uscita documentati e diagnostica separata dai dati.

## Principi di prodotto

- **Dati, non risposte generate:** i valori restituiti provengono sempre dal servizio pubblico.
- **Scoperta prima della query:** la CLI espone filtri e valori effettivamente disponibili.
- **Intenti stabili:** i comandi rappresentano casi d’uso, non endpoint interni del portale.
- **Provenienza verificabile:** ogni risultato conserva sorgente e momento di acquisizione.
- **Automazione prudente:** richieste limitate, retry controllati e nessuna operazione mutativa.
- **Browser non necessario a runtime:** il browser è ammesso nella fase di ricerca, non come trasporto della CLI distribuita.
- **Interfaccia autodescrittiva:** l'aiuto della CLI è parte del prodotto, non documentazione accessoria.
- **Accesso serializzato:** il servizio pubblico è una risorsa condivisa e fragile; nessuna esecuzione può sommarsi a un'altra.
- **Differenze preservate:** dati al consumo e quotazioni all’ingrosso condividono solo i campi realmente equivalenti.

## Principi fondativi

Due caratteristiche non sono funzionalità accessorie ma condizioni di esistenza del prodotto: senza di esse la CLI resta uno script, non uno strumento affidabile né orchestrabile.

### L'aiuto è il contratto

Chi usa questa CLI — una persona, uno script o un modello linguistico — non conosce il portale, non ha letto questo documento e non deve dedurre nulla. L'unica superficie che incontra è l'aiuto dei comandi. Se l'aiuto tace, l'utente indovina; se indovina, sbaglia; e poiché ogni tentativo sbagliato è una richiesta al servizio pubblico, l'ambiguità dell'aiuto si traduce in traffico inutile su un'infrastruttura della pubblica amministrazione.

Per un agente LLM il problema è più netto: un aiuto incompleto non produce un'esitazione ma un'invenzione. Un modello che non trova scritto quali filtri appartengano a quale collezione non chiede, prova; e prova con valori verosimili, che il portale accetta restituendo pagine vuote. Un aiuto autodescrittivo è quindi il principale strumento di prevenzione degli errori, prima ancora della validazione.

Ne discendono requisiti verificabili:

- **RF-27:** ogni comando espone nell'aiuto almeno un esempio eseguibile e completo.
- **RF-28:** ogni opzione dichiara nell'aiuto a quali collezioni si applica e da quali altre opzioni dipende.
- **RF-29:** l'aiuto di ciascun comando indica il passo successivo del percorso di scoperta e i codici di uscita rilevanti.
- **RF-30:** un comando `agent-context` restituisce in una sola chiamata l'intero contratto — collezioni, dimensioni e dipendenze, comandi con esempi, codici di uscita, forma degli errori e garanzie — così che nessun consumatore debba ricavarlo dall'aiuto testuale.
- **RF-31:** un'opzione unica `--agent` attiva insieme output JSON, assenza di colori e assenza di interazione, evitando che l'uso non presidiato dipenda dal ricordarsi più opzioni.
- **RF-32:** i test verificano la presenza degli esempi e delle dichiarazioni di appartenenza nell'aiuto; un aiuto che si svuota fa fallire la suite.

### Il servizio pubblico non si satura

I dati provengono da un portale della pubblica amministrazione, dimensionato per la consultazione umana e privo di API. Uno strumento che rende banale automatizzare le richieste rende altrettanto banale saturarlo: bastano poche esecuzioni concorrenti, o un ciclo distratto in uno script, per trasformare una consultazione legittima in un carico anomalo. La responsabilità di evitarlo è dello strumento, non della disciplina di chi lo usa.

La sequenzialità interna a un archivio non basta, perché non governa ciò che accade fra processi distinti: due esecuzioni lanciate in parallelo — da due terminali, da uno script, da un agente che apre più task — sommano il loro traffico. Il controllo deve quindi essere esterno al singolo processo e valere per l'intera macchina.

Ne discendono requisiti verificabili:

- **RF-33:** una sola richiesta per volta raggiunge il portale dalla stessa macchina; il vincolo è imposto da un lock su file attorno a ogni richiesta, non dalla cooperazione fra processi. Due esecuzioni concorrenti si alternano richiesta per richiesta e non sommano il proprio traffico: la frequenza complessiva resta quella di una sola esecuzione.
- **RF-34:** un'esecuzione che trova lo slot occupato attende il proprio turno anziché fallire, e segnala l'attesa su `stderr`. Il turno è per richiesta e non per esecuzione, così un archivio lungo non impedisce una singola interrogazione di intercalarsi.
- **RF-35:** l'attesa è limitata da `--lock-timeout`, oltre il quale l'esecuzione termina con errore `service_unavailable` e uscita 5, mai proseguendo in parallelo.
- **RF-36:** fra due richieste consecutive è rispettato un intervallo minimo condiviso fra processi, misurato da invio a invio; `--pause` può alzarlo, non abbassarlo sotto il minimo.
- **RF-37:** la terminazione anomala di un processo libera lo slot, perché il lock è mantenuto dal sistema operativo e non da uno stato applicativo.
- **RF-38:** il comportamento è verificato da test che eseguono due processi concorrenti reali.

Il parallelismo non è quindi una funzionalità mancante da aggiungere in futuro: è una funzionalità esclusa per scelta. Chi ha bisogno di volumi maggiori deve chiedere i dati alla fonte, non estrarli più in fretta.

## Perimetro della prima versione

### Incluso

- elenco delle collezioni supportate;
- descrizione di metadati, dimensioni e copertura temporale;
- elenco dei valori ammessi per ciascuna dimensione;
- recupero di osservazioni mediante filtri espliciti;
- disponibilità come parametri CLI di tutti i controlli utente abilitati nei form HTML delle tre sezioni;
- gestione trasparente della paginazione, se presente;
- output tabellare, JSON e CSV;
- scrittura su file senza contaminare `stdout` con messaggi diagnostici;
- salvataggio e riesecuzione di query YAML;
- creazione on-demand di archivi che espandono una o più dimensioni, per esempio tutte le province per un periodo e un prodotto;
- manifest di archivio con query, copertura, richieste eseguite, errori e provenienza;
- cache locale dei soli metadati, invalidabile esplicitamente;
- errori strutturati e codici di uscita deterministici;
- provenienza dei record e conservazione dei campi sorgente rilevanti.

### Escluso

- scrittura o modifica di dati sul portale;
- dashboard e interfacce grafiche;
- grafici e analisi statistiche incorporate;
- previsioni o generazione di valori mancanti;
- crawler continuativo, schedulazione incorporata e database storico gestito dalla CLI;
- aggiramento di CAPTCHA, autenticazione o protezioni anti-automazione;
- browser residente, cookie personali o profili Chrome come dipendenza di runtime.

## Modello concettuale

La CLI espone tre identificatori stabili:

| Identificatore | Contenuto |
|---|---|
| `consumo` | Archivio delle rilevazioni di beni e servizi di largo consumo |
| `ortofrutta-it` | Quotazioni dei mercati ortofrutticoli italiani |
| `ortofrutta-eu` | Quotazioni dei mercati ortofrutticoli europei |

Ogni collezione possiede:

- metadati e copertura temporale;
- dimensioni interrogabili;
- valori ammessi per le dimensioni;
- osservazioni;
- informazioni di provenienza.

Le dimensioni confermate sono:

| Collezione | Dimensioni CLI | Parametri HTML |
|---|---|---|
| `consumo` | `year`, `month`, `province`, `category` | `ANNO`, `MESE`, `f[PROVINCIA]`, `f[TIPO_RECORD_MISE]` |
| `ortofrutta-it` | `year`, `month`, `week`, `market`, `group` | `ANNO`, `MESE`, `SETTIMANA`, `f[MERCATO]`, `f[GRUPPO]` |
| `ortofrutta-eu` | `year`, `month`, `week`, `market`, `group` | `ANNO`, `MESE`, `SETTIMANA`, `f[MERCATO]`, `f[GRUPPO]` |

La CLI traduce le strutture sorgente in nomi coerenti senza perdere i campi originari necessari a interpretare il dato.

## Interfaccia a riga di comando

### Comandi principali

```text
osservaprezzi catalog
osservaprezzi describe <collezione>
osservaprezzi values <collezione> <dimensione>
osservaprezzi get <collezione> [filtri]
osservaprezzi run <query.yaml>
osservaprezzi archive <collezione> [filtri e dimensioni da espandere]
```

### Comportamento comune

- `--json` produce JSON valido e documentato.
- `--csv` produce CSV con intestazione stabile.
- `--output <file>` scrive il risultato nel percorso indicato.
- `--limit <n>` limita il numero di osservazioni restituite.
- `--all <dimensione>` espande la query su tutti i valori disponibili della dimensione indicata ed è ripetibile.
- `--product <testo-o-identificatore>` conserva soltanto il prodotto richiesto; quando il portale non offre questo filtro, la selezione avviene localmente dopo il recupero delle categorie pertinenti.
- `--refresh` ignora la cache dei metadati.
- `--timeout <secondi>` imposta il limite della richiesta.
- `--verbose` invia dettagli diagnostici a `stderr`.

`stdout` contiene esclusivamente dati o output richiesto. Avvisi, progressi ed errori sono inviati a `stderr`.

### Query salvate

Una query YAML contiene almeno:

```yaml
version: 1
collection: ortofrutta-it
filters:
  year: 2025
  month: 5
  week: 2
  market: ROMA
  group: ORTAGGI
format: json
```

`run` deve rifiutare versioni di schema non supportate, filtri sconosciuti e valori non presenti nei form HTML per la combinazione dei filtri genitori.

## Requisiti funzionali

### Scoperta

- **RF-01:** `catalog` elenca tutte e tre le collezioni con descrizione e stato di disponibilità.
- **RF-02:** `describe` restituisce metadati, dimensioni, copertura temporale nota e data dell’ultimo aggiornamento rilevabile.
- **RF-03:** `values` restituisce l’insieme dei valori ammessi per una dimensione, senza richiedere che l’utente conosca codici interni.
- **RF-04:** i comandi di scoperta supportano JSON adatto al consumo programmatico.

### Recupero

- **RF-05:** `get` valida collezione, dimensioni e valori prima del recupero, quando il servizio rende disponibili i relativi metadati.
- **RF-05F:** `get` richiede tutti i filtri della collezione; l’uso dei valori più recenti o dei default del sito richiede un’opzione esplicita e viene registrato nella provenienza.
- **RF-05A:** ogni controllo visibile, abilitato e modificabile dall’utente nei form HTML è rappresentato da un’opzione CLI o da un argomento strutturato equivalente.
- **RF-05B:** la mappatura conserva tipo, valore predefinito, obbligatorietà, valori ammessi, selezione multipla e dipendenze tra controlli osservate nel form.
- **RF-05C:** pulsanti che attivano modalità di consultazione differenti sono rappresentati da opzioni o sottocomandi distinti quando modificano la richiesta o il risultato.
- **RF-05D:** campi nascosti, token CSRF e altri parametri tecnici sono gestiti dall’adattatore e non diventano opzioni pubbliche, salvo che rappresentino una scelta effettiva dell’utente.
- **RF-05E:** nessun controllo utente può essere ignorato silenziosamente; un controllo non riproducibile deve comparire nello stato di capacità della collezione come gap documentato.
- **RF-06:** `get` applica filtri espliciti e non amplia silenziosamente la richiesta.
- **RF-07:** la paginazione è seguita automaticamente fino al completamento o al limite richiesto.
- **RF-08:** una risposta parziale viene segnalata come tale e non presentata come completa.
- **RF-09:** ogni record include `collection`, `retrieved_at` e `source_url`, oppure equivalenti documentati nel metadato di risposta.
- **RF-10:** i campi specifici delle collezioni restano disponibili anche quando non appartengono allo schema comune.

### Riproducibilità

- **RF-11:** una query valida può essere serializzata in YAML e rieseguita con `run`.
- **RF-12:** l’ordine dei campi e dei record è stabile a parità di risposta sorgente.
- **RF-13:** JSON e CSV rappresentano gli stessi record e gli stessi valori nulli.
- **RF-14:** la CLI espone versione del programma e versione dello schema di output.

### Cache

- **RF-15:** nella prima versione la cache contiene soltanto metadati, dimensioni e valori ammessi; non contiene osservazioni.
- **RF-16:** ogni elemento in cache ha sorgente, data di acquisizione e scadenza.
- **RF-17:** `--refresh` forza il recupero dei metadati aggiornati.

### Archivi on-demand

- **RF-18:** `archive` esegue una query su tutti i valori disponibili di una o più dimensioni richieste esplicitamente, senza introdurre una schedulazione permanente.
- **RF-19:** per `consumo` deve essere possibile creare almeno un archivio per tutte le province, un periodo definito e uno specifico prodotto.
- **RF-20:** quando `prodotto` non è un parametro del form sorgente, la CLI richiede anche la categoria, salvo risoluzione univoca da un catalogo già acquisito, e applica localmente un confronto esatto documentato su identificatore o descrizione normalizzata.
- **RF-21:** prima dell’esecuzione la CLI calcola e mostra il numero di richieste previste; `--json` rende disponibile lo stesso piano in forma strutturata.
- **RF-22:** ogni archivio contiene i dati e un `manifest.json` con versione dello schema, query, valori espansi, URL sorgente, istanti di acquisizione, conteggi, richieste riuscite e richieste fallite.
- **RF-23:** le righe sono deduplicate tramite una chiave naturale definita per collezione; la chiave utilizzata è registrata nel manifest.
- **RF-24:** un’esecuzione interrotta mantiene un archivio marcato `partial`; una successiva esecuzione con `--resume` ripete soltanto le richieste mancanti o fallite.
- **RF-25:** `--max-requests <n>` impone un limite rigido e impedisce l’avvio quando il piano lo supera.
- **RF-26:** le richieste dell’archivio sono eseguite in sequenza con una pausa configurabile e senza parallelismo predefinito.

## Requisiti per agenti LLM

- **RA-01:** tutti i comandi informativi e di recupero offrono output JSON.
- **RA-02:** gli identificatori di collezioni, dimensioni e valori sono separati dalle etichette umane.
- **RA-03:** quando è richiesto `--json`, gli errori sono emessi come JSON su `stderr` e includono almeno `code`, `message`, `retryable` e dettagli sui parametri non validi.
- **RA-04:** i suggerimenti per correggere una query derivano dai valori scoperti, non da similarità inventate senza conferma.
- **RA-05:** help e descrizioni dei comandi indicano il passo di scoperta successivo.
- **RA-06:** l’esito di un comando è determinabile tramite codice di uscita senza interpretare testo libero.
- **RA-07:** il piano di un archivio è ispezionabile senza eseguirlo tramite `archive --dry-run --json`.

## Architettura proposta

```text
CLI
 ├─ catalogo e validazione
 ├─ gestione query
 ├─ pianificazione e manifest degli archivi
 ├─ modello normalizzato minimo
 ├─ adattatore consumo
 ├─ adattatore ortofrutta-it
 ├─ adattatore ortofrutta-eu
 └─ renderer table / JSON / CSV
```

Ogni adattatore implementa la stessa interfaccia logica:

- descrivere la collezione;
- elencare i valori di una dimensione;
- recuperare osservazioni;
- tradurre errori e condizioni di risposta parziale.

L’adattatore può usare JSON, CSV, altri download strutturati o parsing HTML. Questa scelta non modifica i comandi pubblici. Un cambiamento incompatibile in un adattatore non deve compromettere le altre collezioni.

## Flusso dei dati

```text
argomenti CLI o YAML
        ↓
validazione sintattica
        ↓
scoperta e validazione dei valori
        ↓
adattatore della collezione
        ↓
risposta sorgente e controllo completezza
        ↓
normalizzazione minima e provenienza
        ↓
JSON, CSV o tabella
```

La risposta sorgente può essere mantenuta nelle fixture di test soltanto dopo sanificazione. Cookie di sessione, token, identificatori personali e intestazioni sensibili non devono essere salvati nel repository.

## Formato degli archivi

Un archivio è una directory esplicita scelta con `--output` e contiene almeno:

```text
<output>/
├── data.csv oppure data.jsonl
└── manifest.json
```

`manifest.json` è scritto fin dall’inizio con stato `running`, aggiornato durante l’esecuzione e chiuso come `complete` o `partial`. Il manifest permette di verificare la copertura e riprendere il lavoro senza trasformare la CLI in un database o in uno scheduler.

Esempio di intenzione:

```text
osservaprezzi archive consumo \
  --year 2025 --month 5 \
  --all provincia \
  --category altri_alim \
  --product "Pane Fresco Con Farina Di Grano (1000 Gr)" \
  --output archivio-pane-2025-05
```

Per `consumo`, un periodo, una categoria e un prodotto su tutte le province generano 64 richieste. L’espansione implicita su tutte le sei categorie non è consentita: produrrebbe fino a 384 richieste per un solo periodo.

L’archivio deve riportare l’avvertenza del portale secondo cui la stessa descrizione può riferirsi a combinazioni differenti di varietà, marca, confezione e punto vendita tra province o mesi; i valori raccolti non devono essere presentati automaticamente come serie comparabili.

## Gestione degli errori

| Categoria | Esempio | Retry automatico | Codice di uscita proposto |
|---|---|---:|---:|
| Input non valido | collezione o filtro sconosciuto | No | 2 |
| Dato assente | periodo senza osservazioni | No | 3 |
| Contratto cambiato | HTML o JSON non riconosciuto | No | 4 |
| Servizio temporaneamente indisponibile | timeout, 429, errore 5xx | Limitato | 5 |
| Risposta parziale | paginazione interrotta | Limitato | 6 |

I retry devono usare attese progressive, rispettare `Retry-After` quando presente e non trasformare un errore persistente in traffico aggressivo.

## Requisiti non funzionali

- **RNF-01:** nessuna dipendenza da browser a runtime.
- **RNF-02:** nessuna credenziale richiesta per dati pubblicamente consultabili.
- **RNF-03:** timeout e numero massimo di retry configurabili.
- **RNF-04:** user-agent identificabile con nome e versione della CLI.
- **RNF-05:** log e fixture privi di segreti, cookie e dati personali.
- **RNF-06:** comportamento compatibile con Linux, macOS e Windows nei limiti delle dipendenze scelte.
- **RNF-07:** il fallimento di una collezione non impedisce l’uso delle altre.
- **RNF-08:** ogni adattatore è testabile senza accesso di rete tramite fixture.

## Verifica della fattibilità

La ricognizione deve essere svolta separatamente per ciascuna collezione e deve:

1. aprire la pagina iniziale in una sessione browser dedicata;
2. eseguire almeno una consultazione reale e read-only;
3. registrare le richieste di rete pertinenti;
4. identificare endpoint, metodo, parametri, paginazione e formato della risposta;
5. inventariare tutti i controlli visibili, abilitati e modificabili dei form, inclusi valori predefiniti, opzioni multiple e dipendenze dinamiche;
6. associare ogni controllo utente al parametro HTTP osservato e al corrispondente parametro CLI;
7. separare le scelte dell’utente dai campi nascosti e dai token tecnici gestiti internamente;
8. verificare se cookie o token siano realmente necessari;
9. riprodurre la richiesta mediante un client HTTP non browser;
10. verificare filtri, casi vuoti, errori e completezza;
11. misurare il numero di richieste necessario per gli archivi sulle dimensioni espandibili e individuare limiti prudenti;
12. definire la chiave naturale per deduplicare i record di ciascuna collezione;
13. classificare stabilità e rischio della superficie osservata.

La registrazione del traffico deve essere sanificata prima di essere conservata. Non sono ammesse tecniche di elusione delle protezioni del servizio.

## Criteri di fattibilità per collezione

Una collezione è:

- **fattibile**, se scoperta e recupero sono riproducibili via HTTP e producono dati strutturati completi;
- **fattibile con rischio**, se richiede parsing HTML stabile o parametri di sessione pubblici rinnovabili senza browser residente;
- **non fattibile per la prima versione**, se richiede browser residente, CAPTCHA, credenziali non disponibili o elusione di protezioni.

La decisione complessiva può essere positiva anche se una collezione resta esclusa, purché `catalog` ne riporti chiaramente lo stato e le altre funzionino in modo indipendente.

## Strategia di test

### Test offline

- parsing delle risposte tramite fixture sanificate;
- normalizzazione e conservazione della provenienza;
- validazione di filtri e query YAML;
- matrice di parità tra controlli dei form HTML, parametri HTTP e parametri CLI;
- valori predefiniti, campi obbligatori, selezioni multiple e dipendenze tra controlli;
- equivalenza tra JSON e CSV;
- contratti degli errori JSON;
- rilevamento di risposta incompleta o struttura cambiata.
- pianificazione `--dry-run`, limite massimo di richieste e assenza di parallelismo predefinito;
- deduplicazione, manifest `complete`/`partial` e ripresa delle richieste mancanti;
- filtro locale del prodotto quando non disponibile nel form sorgente.

### Test live

- smoke test read-only per ogni collezione supportata;
- una query minima valida;
- una query senza risultati;
- un filtro non valido;
- verifica di paginazione o limite, se applicabile;
- confronto tra output live e contratto documentato.

I test live devono avere frequenza moderata e non devono essere eseguiti automaticamente in parallelo contro il servizio pubblico.

## Criteri di accettazione della prima versione

La prima versione è accettabile quando:

1. `catalog` descrive correttamente stato e capacità delle tre collezioni;
2. ogni collezione dichiarata supportata supera i criteri di fattibilità;
3. `describe`, `values` e `get` funzionano per almeno una query reale della collezione;
4. la matrice di parità copre il 100% dei controlli utente abilitati osservati nei form HTML, oppure identifica esplicitamente ogni eccezione bloccante;
5. una query salvata produce lo stesso insieme di record della query CLI equivalente;
6. JSON e CSV superano i rispettivi test di contratto;
7. errori e risposte parziali non vengono confusi con risultati completi;
8. nessuna operazione richiede un browser residente o conserva segreti;
9. la documentazione guida un agente dalla scoperta al recupero senza conoscenza preventiva degli endpoint.
10. un archivio di prova per tutte le province, un periodo e un prodotto produce dati deduplicati e un manifest verificabile senza richieste parallele.

## Rischi e mitigazioni

| Rischio | Impatto | Mitigazione |
|---|---|---|
| Endpoint interni non documentati | Cambiamenti improvvisi | adattatori isolati, test di contratto e messaggi espliciti |
| Dati serviti soltanto tramite HTML | Parser fragile | selettori semantici, fixture e classificazione “fattibile con rischio” |
| Filtri dipendenti da sessione | Automazione instabile | verificare chiamate iniziali e token pubblici; escludere se serve browser residente |
| Paginazione non evidente | Risultati incompleti | test su conteggi, cursori e pagine terminali |
| Schemi differenti | Normalizzazione fuorviante | schema comune minimo e campi specifici preservati |
| Limitazioni o blocchi del servizio | Indisponibilità temporanea | rate limit prudente, retry limitati e cache metadati |
| Espansione di molte combinazioni | Carico eccessivo sul servizio | `--dry-run`, `--max-requests`, esecuzione sequenziale, pausa e ripresa |
| Cambiamenti di dominio o proprietà | URL obsoleti | configurazione centralizzata delle sorgenti e controllo di reachability |

## Dipendenze decisionali

L’implementazione resta subordinata alle seguenti evidenze:

- almeno una superficie HTTP riproducibile per ciascuna collezione candidata;
- termini d’uso e comportamento del servizio compatibili con consultazioni automatizzate moderate;
- possibilità di ricavare valori ammessi e copertura temporale;
- disponibilità di un identificatore stabile per record o di una chiave naturale documentabile;
- comprensione della semantica di prezzo, unità, valuta e periodo per ogni collezione.

Le evidenze e i limiti confermati sono riportati in `docs/evaluation.md`.

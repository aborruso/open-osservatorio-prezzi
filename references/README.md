# Codifiche territoriali

Il portale identifica le province di rilevazione **solo per nome**. Per incrociare questi prezzi con qualsiasi altra fonte territoriale — popolazione, redditi, dati SDMX, confini geografici — serve un codice, e questa cartella documenta quello che la CLI aggiunge in automatico.

## La tabella

Il file distribuito con il pacchetto è [`src/osservaprezzi/data/province_istat.csv`](../src/osservaprezzi/data/province_istat.csv): 64 righe, una per provincia di rilevazione.

| Colonna | Contenuto | Esempio (Roma) |
|---|---|---|
| `province` | nome esattamente come lo scrive il portale | `Roma` |
| `istat_code` | codice provincia ISTAT, cosiddetto storico | `058` |
| `uts_code` | codice dell'unità territoriale sovracomunale | `258` |
| `nuts3` | codifica europea NUTS3 2024 | `ITI43` |
| `istat_name` | denominazione ufficiale ISTAT | `Roma` |
| `region`, `area` | regione e ripartizione geografica | `Lazio`, `Centro` |
| `plate` | sigla automobilistica | `RM` |

Nell'output della CLI finiscono tre campi: `province_istat`, `province_uts`, `province_nuts3`. Gli altri restano qui, per chi voglia un join più ricco.

## Perché due codici numerici e non uno

Le **quindici città metropolitane** hanno un codice di unità territoriale diverso dal codice provincia storico:

| | provincia | UTS |
|---|---:|---:|
| Torino | 001 | 201 |
| Milano | 015 | 215 |
| Genova | 010 | 210 |
| Venezia | 027 | 227 |
| Bologna | 037 | 237 |
| Firenze | 048 | 248 |
| Roma | 058 | 258 |
| Napoli | 063 | 263 |
| Bari | 072 | 272 |
| Reggio Calabria | 080 | 280 |
| Palermo | 082 | 282 |
| Messina | 083 | 283 |
| Catania | 087 | 287 |
| Sassari | 112 | 312 |
| Cagliari | 118 | 318 |

Nelle altre 49 province i due codici coincidono. Esporne uno solo sembrerebbe più pulito, ma romperebbe silenziosamente i join proprio sulle province più grandi: il codice storico è quello usato nella gran parte dei dataset ISTAT (elenco comuni, serie demografiche), il codice UTS è quello della nomenclatura amministrativa attuale. Un join che non trova corrispondenza per Roma e Milano non dà errore: dà semplicemente risultati incompleti, ed è il tipo di bug che si scopre tardi.

## Le quattro grafie che non coincidono

Il portale usa il nome del capoluogo o una grafia semplificata. Quattro province vanno ricondotte a mano alla denominazione ufficiale, e la corrispondenza è dichiarata nello script di rigenerazione:

| Portale | ISTAT |
|---|---|
| `Aosta` | Valle d'Aosta/Vallée d'Aoste |
| `Bolzano` | Bolzano/Bozen |
| `Forli` | Forlì-Cesena |
| `Reggio Emilia` | Reggio nell'Emilia |

Le altre 60 combaciano dopo una normalizzazione che ignora accenti, maiuscole e apostrofi.

## Rigenerare la tabella

La fonte è il **SITUAS** dell'ISTAT (Sistema Informativo Territoriale delle Unità Amministrative e Statistiche), report 64 «Elenco Province/Uts», letto con la CLI [`opensituas`](https://pypi.org/project/opensituas/):

```bash
uv run python scripts/refresh_province_istat.py
```

Lo script confronta l'elenco vivo delle province esposte dal portale con le unità territoriali ISTAT e **fallisce se resta qualcosa senza corrispondenza**, indicando i nomi da aggiungere alle eccezioni. Lo stesso controllo è nei test (`tests/test_territori.py`): se il portale aggiunge una provincia, la suite lo segnala invece di lasciare campi vuoti in silenzio.

Una provincia sconosciuta non blocca comunque il recupero dei prezzi: i tre campi restano vuoti e il dato viene consegnato. Un codice mancante e visibile è preferibile a un dato non consegnato.

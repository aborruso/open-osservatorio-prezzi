# Idee future

## Riportare gli avvisi del portale nei risultati

Sotto la tabella delle rilevazioni mensili (`consumo`) il portale mostra un blocco «AVVISO». Dal 2026 spiega che, per il passaggio a ECOICOP e alla base degli indici 2025=100, nei primi mesi dell'anno si pubblicano solo i dati della rilevazione territoriale ISTAT e di fonte MIMIT, mentre i livelli da scanner data arriveranno più avanti. È la spiegazione del paniere ridotto del 2026: a Roma gli alimentari passano da 45-47 voci a 7, energetici e cura della persona e della casa sono vuoti da gennaio ad agosto (verificato il 2026-10-22).

Oggi la CLI non legge quel blocco, e chi riceve un archivio pieno di `no_data` non sa perché. L'idea è estrarre il testo dell'avviso e riportarlo in `notes` del risultato di `get` e nel manifest di `archive`, insieme a un'impronta del testo (hash) e alla data di acquisizione, così un cambio di avviso si nota.

Da tenere presente:

- l'avviso è testo fisso della pagina e compare anche nelle risposte per i mesi del 2025; dalla sola presenza non si può dedurre che la cella richiesta ne sia toccata, quindi va riportato come contesto, non usato per decidere l'esito;
- se l'avviso sparisce o cambia, il fixture HTML dei test va aggiornato: serve un test che fissi l'estrazione e uno che regga la sua assenza;
- vale la pena controllare se le pagine dell'ortofrutta all'ingrosso hanno avvisi analoghi.

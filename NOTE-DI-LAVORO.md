# Note di lavoro — VISIO Studio

Stato del progetto, decisioni prese e cose ancora da fare.
**Questo file sta nel repository**, quindi si sincronizza con `git pull` ed è
disponibile su qualsiasi computer. Aggiornalo quando cambia qualcosa di
strutturale: è la memoria condivisa del progetto.

Ultimo aggiornamento: 4 novembre 2026 (studio del sole).

---

## 1. Cose da fare, in ordine di urgenza

### Legale — resta solo roba di pannello, non di codice
Fatto il 1 settembre: `privacy.html`, `cookie.html`, dati societari e P.IVA nel
piede di tutte le pagine, riga sull'informativa sotto i due moduli, font portati
in casa. Dettagli e ragionamento nel §7. Restano tre cose fuori dal repository:

- **La notifica dei moduli su Netlify** punta ancora al vecchio indirizzo:
  pannello → Forms → notifications → `info@visiorender.it`.
- **Roma o Aprilia?** La sede legale è ad Aprilia (LT), ma tutto il sito è
  costruito su "Roma": titolo, descrizione, `areaServed`, testi. Nello schema ho
  messo l'indirizzo vero come `address` e Roma+Lazio come `areaServed`, che è la
  lettura onesta (si opera a Roma, la società ha sede ad Aprilia). Se un domani
  si apre una scheda Google Business, l'indirizzo lì dev'essere quello vero,
  altrimenti la verifica salta.
- **I periodi di conservazione** nell'informativa (24 mesi per le richieste che
  non diventano incarico, 10 anni per i documenti contabili) sono una proposta
  ragionevole, non un dato che mi ha dato Matteo: se il commercialista dice
  altro, si cambia quella riga.

### Recensioni — fatte, ma se ne aggiungono altre si fa così
La fascia `#recensioni` (fra i numeri e "chi siamo") contiene **sei recensioni di
clienti veri**, date da Matteo il 31 agosto 2026. Nome puntato (`Marco R.`) per
non esporre il cognome; la seconda riga è il servizio di cui parla la recensione
stessa, ricavato dal testo — non inventarlo.

Le carte sono scritte **due volte** nell'HTML: la copia con `aria-hidden` serve a
far richiudere lo scorrimento senza salti. Se se ne aggiunge una, va aggiunta in
entrambi i gruppi. Su desktop la fascia scorre da sola e si ferma al passaggio
del mouse; dove non c'è il mouse l'animazione è spenta e si scorre col dito
(`@media (hover:none)`), altrimenti il testo scapperebbe mentre lo si legge.

**Non si scrivono recensioni inventate**, nemmeno "di esempio" e nemmeno con nomi
di fantasia credibili: chi legge le prende per vere ed è una pratica commerciale
ingannevole (Codice del consumo, art. 21-23). Servono clienti veri.

Non è stato messo il markup `AggregateRating` nel JSON-LD: Google non ammette i
"self-serving reviews" (recensioni sul proprio conto raccolte da sé) per i rich
snippet delle attività locali, e marcarle porterebbe una penalizzazione invece
che una stellina.

### La journey sfocata — mezzo passo fatto, manca il sorgente grande
**Il problema:** i fotogrammi sono **1152x864** e il canvas li disegna a tutto
schermo fino a 2x (su un portatile retina ~2880x1800). Vengono ingranditi due
volte e mezzo, ed e per questo che scorrendo si vedono molli. Nessuna riga di
codice puo inventare i pixel che mancano.

**Cosa e stato fatto il 31 agosto:** `img/journey-2` sostituisce `img/journey`.
Stessa misura e stessi 145 fotogrammi, ma con una **maschera di contrasto**
(PIL, `UnsharpMask(radius=1.1, percent=95, threshold=2)`, qualita 64,
`optimize`, `progressive`) applicata prima della compressione: il browser
ingrandisce un'immagine gia incisa e il risultato e visibilmente meno molle, a
parita di peso (8,2 MB contro 7,6). E un cerotto, non la cura.

    python3 -c "
    from PIL import Image, ImageFilter; import glob, os
    os.makedirs('img/journey-3', exist_ok=True)
    for f in sorted(glob.glob('img/journey-2/frame-*.jpg')):
        Image.open(f).convert('RGB').filter(ImageFilter.UnsharpMask(1.1,95,2)).save(
            'img/journey-3/'+os.path.basename(f),'JPEG',quality=64,optimize=True,progressive=True)"

**La cura vera:** rifare i fotogrammi da un sorgente piu grande.

- **Prima di generare un video nuovo, cercare l'mp4 originale** (`visio-journey*.mp4`
  sul Mac): se e a 1080p o piu, i fotogrammi attuali sono stati estratti
  rimpicciolendo, e basta ri-estrarli. Costa zero.
- Video nuovo, se serve: **almeno 1920 di larghezza**, meglio 2560, in **16:9**
  (il canvas ritaglia in "cover": un 4:3 viene tagliato e ingrandito ancora di
  piu), movimento di camera lento e continuo.
- **Controllare l'angolo in basso a destra**: i video generati con Gemini
  portano li il rombo della filigrana (e gia successo con `img/esterni`).
- Si estrae a 12 fps in una cartella **nuova** (`img/journey-3`) e si aggiorna la
  regola in `netlify.toml` piu i due riferimenti in `index.html`.
- Meglio **meno fotogrammi ma piu grandi**: 96 a 1920 pesano quanto 145 a 1152.

**Da questa sessione non si possono generare immagini ne video:** l'MCP
`nano-banana` sta sul Mac di Matteo e comunque fa solo immagini. Il video lo
produce lui.

### Dominio visiorender.it — collegato il 25 agosto 2026
Comprato su Aruba l'8 agosto insieme alla casella email. Dominio **attivo**
(`Status: ok`, scadenza 2027-08-08), posta configurata (`MX: mx.visiorender.it`).

**Record impostati** nel pannello Aruba (Dominio → Gestione DNS e Name Server,
che apre `dns-panel.aruba.it`):

| Tipo  | Nome | Valore                    |
|-------|------|---------------------------|
| A     | `@`  | `75.2.60.5` (era 62.149.128.40, parcheggio Aruba) |
| CNAME | `www`| `visiorender.netlify.app` (era visiorender.it)    |

Su Netlify il dominio era già stato aggiunto l'8 agosto (`visiorender.it`
principale, `www` che reindirizza).

**I record MX non sono stati toccati.** Nel pannello Aruba i record `mail` e
`mx` sono protetti (*Nessuna operazione*) e gli MX stanno in una scheda
separata: la posta non rischia nulla modificando A e CNAME.

**Correzione a una nota precedente: Aruba supporta i record ALIAS.** Netlify li
preferisce all'A record (`ALIAS @ → apex-loadbalancer.netlify.com`) perché
seguono automaticamente eventuali cambi di IP. Abbiamo usato l'A record, che è
il ripiego documentato da Netlify e funziona; **se un domani il sito smettesse
di rispondere sul dominio senza motivo apparente, la prima cosa da verificare è
se Netlify ha cambiato quell'IP** — e in quel caso conviene passare ad ALIAS.

**Propagazione completata il 25 agosto 2026.** I nameserver autoritativi Aruba
(`dns.technorail.com`) e i resolver pubblici (8.8.8.8, 1.1.1.1) rispondono
`75.2.60.5`, `www` punta a `visiorender.netlify.app`, gli MX sono intatti. Il
sito risponde in HTTP.

**Il certificato HTTPS: stato bloccato, sbloccato il 26 agosto 2026.**
Per settimane Netlify ha risposto *"We could not provision a Let's Encrypt
certificate"* e il pulsante *Verify DNS configuration* non produceva alcun
effetto, nemmeno con il DNS ormai corretto. Non era un problema di DNS:
verificati e tutti a posto apex, www, assenza di CAA, assenza di DNSSEC,
nameserver, e nessun redirect nostro che intercettasse
`/.well-known/acme-challenge/` (`netlify.toml` non ha regole di redirect).

Era lo **stato interno di Netlify rimasto incastrato** dai tentativi falliti di
quando il dominio puntava ancora ad Aruba. La cura: *Options → Remove domain*
sul dominio primario e poi ri-aggiungerlo con *Add a domain → Add a domain you
already own*. Subito dopo *Verify DNS configuration* ha finalmente risposto
**"DNS verification was successful"**. Il sito non ha mai smesso di rispondere
durante l'operazione, e `www` si ricrea da solo come redirect.

L'emissione vera e propria puo restare indietro ancora un po': Let's Encrypt
limita i tentativi falliti (5 per host all'ora) e ne erano stati accumulati
molti. Se serve rifarlo: premere *Provision certificate* una volta sola e
aspettare, senza insistere, perche ogni tentativo fallito allunga l'attesa.

**Attenzione all'interfaccia di Netlify:** i dialoghi di conferma hanno una
dissolvenza in entrata, e un clic dato troppo presto viene assorbito senza fare
nulla — sembra che il pulsante non funzioni. Aspettare un paio di secondi e
cliccare il pulsante per riferimento, non a coordinate.

Attenzione a una trappola nel diagnosticare: **il resolver di macOS tiene in
cache il vecchio IP Aruba** (`62.149.128.40`, server Microsoft-IIS) molto più a
lungo dei resolver pubblici. Se `curl` mostra ancora la pagina Aruba mentre
`dig` dice `75.2.60.5`, non è un problema di DNS: è la cache locale. Confrontare
sempre `dscacheutil -q host -a name visiorender.it` con `dig @8.8.8.8`, e
provare il sito con `curl --resolve visiorender.it:443:75.2.60.5`.

**Posta: attiva.** Il servizio è provvisionato e l'account amministratore
`postmaster@visiorender.it` esiste con password impostata (pannello Aruba →
Servizi di posta → Caselle di posta). Da lì, con il pulsante *Gestisci caselle*,
si creano e configurano gli indirizzi del dominio: quel passaggio richiede le
credenziali del postmaster, quindi lo fa Matteo.

Parametri per il client: `imaps.aruba.it` 993 SSL in arrivo, `smtps.aruba.it`
465 SSL in uscita, nome utente = **indirizzo email completo** (l'errore più
comune è metterci solo la parte prima della chiocciola). Se il client dà errore
di autenticazione con parametri giusti, verificare che **IMAP sia attivo**: su
Aruba è un servizio aggiuntivo, e senza si ha solo POP3 — inadatto a chi lavora
da più computer, perché i messaggi scaricati spariscono dagli altri dispositivi.


### Listino interno collegato al form preventivi
Richiesta esplicita di Matteo, da sviluppare insieme: un listino **non
pubblico** che permetta di stimare rapidamente un preventivo a partire da ciò
che il cliente indica nel form. Implica probabilmente di arricchire il form
contatti con i campi che alimentano la stima (tipo progetto, numero ambienti,
servizi richiesti). Al pubblico si continua a comunicare "preventivo su misura,
si va a progetto e non a singola vista".

### Madia — da migliorare
Il montaggio fotorealistico funziona (vedi §3) ma è incompleto:

- **Configuratore rimosso**: finiture, maniglia e base pilotavano i tracciati
  SVG e senza quelli lanciavano errori. Per riaverli servono immagini dedicate
  del mobile finito in noce, salvia e antracite (3 generazioni, ~18 crediti),
  da mostrare al click sul canvas. Le regole CSS (`.esp-sw`, `.esp-opt`,
  `.esp-swatches`, `.esp-optrow`) sono rimaste nel foglio di stile, pronte.
- Il **backup della versione vettoriale** con tutte le sue funzioni sta in
  `backup/esploso-madia-svg.html`.

### Pagine cliente vere
La struttura è pronta ma esiste solo l'esempio. Per ogni cliente: creare la
cartella con la sua pagina e generare il codice (vedi §4).

### Titoli disallineati nella gallery render
Le slide 02, 03 e 06 hanno titoli che non corrispondono alle foto: un soggiorno
intitolato "Vialetto d'Ingresso", la villa notturna "Bagno Padronale", la
terrazza "Cabina Armadio". Da sistemare quando si decidono i titoli giusti.

---

## 2. Come si lavora su questo progetto

### Non pubblicare a ogni modifica

**Ogni push su `main` fa partire una ricostruzione su Netlify, e le build del
piano gratuito sono contate.** Accumulare tutte le modifiche di una sessione,
verificarle in locale, e fare **un solo push alla fine**. Committare in locale
quanto si vuole: e il push che costa, non il commit.


- **`git pull` all'inizio di ogni sessione.** Matteo lavora da due computer.
- Si lavora su `index.html` (tutto inline: HTML, CSS, JS). Le pagine separate
  sono `faq.html` e `esempio/index.html`.
- Commit brevi in italiano, push su `origin main`.
- Quando cambia l'elenco dei servizi o l'URL, aggiornare **anche**
  `sitemap.xml`, `llms.txt` e il JSON-LD nel `<head>`.

### Il pannello di anteprima integrato non basta
Questo è il tranello che fa perdere più tempo. Nel Browser pane di Claude Code:

- `requestAnimationFrame` **non gira** e lo scroll con gesture va in timeout;
- gli screenshot vengono renderizzati a scroll ≈ 0 e diventano neri se la
  pagina è scrollata altrove.

Quindi **journey, LiDAR, VR 360, realtà aumentata, timelapse esterni e
montaggio madia lì non si animano.** Non è un bug del sito. Per verificarli
davvero serve un browser vero:

```bash
cd ~/Desktop/visio-studio && python3 -m http.server 4601
open -a "Google Chrome" http://localhost:4601/index.html
```

Il server configurato in `.claude/launch.json` **non funziona su questo Mac**
(permessi macOS sulla cartella Scrivania): il file è stato svuotato apposta.

Per verificare una singola sezione senza browser, il metodo che funziona è
estrarla in una pagina di prova temporanea, simulare il progresso
sovrascrivendo `wrap.getBoundingClientRect` e poi fare lo screenshot.

---

## 3. Sezioni animate allo scroll

Tutte seguono lo stesso schema: un contenitore alto più schermate, un figlio
`position:sticky`, e il progresso calcolato come
`-wrap.getBoundingClientRect().top / (wrap.offsetHeight - innerHeight)`.

| Sezione | Contenitore | Contenuto |
|---|---|---|
| Journey | `#journey` | 145 fotogrammi in `img/journey-2/` |
| LiDAR | `#lidar-section` | nuvola di punti su canvas |
| VR 360 | `#vr-scroll` (450vh) | panorama WebGL |
| Esterni | `#ex-wrap` (430vh) | 60 fotogrammi in `img/esterni-2/` |
| Sito dedicato | `#sd-wrap` | dispositivi + mini-sito |
| Madia | `#esploso-wrap` (620vh) | modello 3D WebGL (`madia-3d.json`) |

**Usare sempre il ciclo `requestAnimationFrame`, non l'evento `scroll`**: è lo
schema della journey, l'unico collaudato su tutti i browser qui.

### Da video a fotogrammi
`ffmpeg` non è installato: si usa quello incluso in Python.

```bash
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
"$FF" -i ~/Desktop/video.mp4 -vf "fps=12" -q:v 3 img/CARTELLA/frame-%04d.jpg
```

12 fps è la densità giusta: 8 secondi danno 96 fotogrammi, circa 4 MB.
**Controllare le bande nere**: i video generati da AI escono spesso 4:3 dentro
un fotogramma 16:9. Se ci sono, verificare che il soggetto stia dentro l'area
utile anche nell'ultimo fotogramma e poi ritagliare **in modo uniforme** tutti i
fotogrammi. Riempire le bande estendendo lo sfondo produce striature: scartato.

### Il tour 360
I panorami generati da AI **non chiudono mai la sfera**: i due bordi non
combaciano. La cucitura si misura confrontando prima e ultima colonna con una
colonna a caso — in un 360 vero il rapporto è ~20×, in uno generato ~1×.

La dissolvenza circolare **non** è la soluzione: crea una banda a doppia
esposizione che si nota subito. Ha funzionato il **raccordo speculare**:
sostituire la coda con una copia specchiata della testa (~27°), ammorbidendo
solo l'innesto. Giuntura misurata: 0,0.

Di conseguenza la rotazione è limitata alla porzione pulita: **da -93° a +115°**
(`sweep = π·1.1556`, offset `+0.192`), che apre sulla vetrata con piscina e
chiude sul camino. FOV 75°, mappatura verticale piena.

**Attenzione al segno dello yaw**: lo shader usa `d.z = -1` e
`lon = atan(d.x, -d.z)`. Una riproiezione scritta a mano in Python con `dz=+f`
dà la **rotazione invertita** e porta a diagnosticare il lato sbagliato.

---

### La madia in 3D (in linea dal 26 agosto 2026, ha sostituito il video)

Il mobile e un modello vero: `modelli/madia.glb` (32 KB, esportato da SimLab,
2,04 x 0,77 x 0,54 m, 15 pezzi, gia con l'asse verticale giusto).
`strumenti/glb-a-json.py` ne estrae la geometria in `madia-3d.json` (21 KB)
applicando le trasformazioni dei nodi e ricentrando il mobile con la base a
Y = 0. Se il modello viene riesportato, rigenerare con:

    python3 strumenti/glb-a-json.py modelli/madia.glb madia-3d.json

Il renderer e **WebGL scritto a mano**, come il tour 360: niente three.js,
niente dipendenze. Vive in `index.html` dentro `#esploso-wrap`; `_test-madia.html`
resta come banco di prova isolato (in `noindex`).

Il montaggio occupa il primo 60% dello scroll della sezione, poi le quattro
finiture si succedono da sole. Barra e tasti **non sono comandi paralleli**:
trascinare la barra o cliccare una finitura sposta lo scroll, cosi posizione
nella pagina, barra e tasto acceso non possono mai discordare.

I 96 fotogrammi in `img/madia/` (4,4 MB) non sono piu usati da nessuna pagina:
si possono togliere dal deploy quando si vuole, restano comunque nella storia
di git. In tutto pesa 45 KB
contro i 4,4 MB dei 96 fotogrammi che sostituisce.

Tre inciampi gia pagati, da non ripetere:

- **`smoothstep(a,b,x)` con `a > b` e comportamento indefinito in GLSL** e su
  questa GPU produce NaN, che si vede come nero pieno. Per invertire una
  rampa scrivere `1.0 - smoothstep(b,a,x)`, mai scambiare i bordi.
- Un uniform impostato a **NaN** annerisce tutto il pezzo senza alcun errore in
  console: gli shader compilano, il programma linka, e sembra un bug di
  rendering. Se una superficie e nera, controllare prima i valori passati con
  `gl.uniform*`.
- Il piano dell'ombra a terra va disegnato con il **culling disattivato**,
  altrimenti sparisce a seconda di come e avvolto il quad.

Il modello **non ha maniglie**: l'opzione gola/pomello del vecchio
configuratore non e ricreabile finche non vengono aggiunti i gruppi
`maniglia-gola` e `maniglia-pomello`. Le tre ante si chiamano tutte
`anta 1` e vengono distinte dalla posizione lungo X.

Le essenze sono texture vere (`img/essenza-rovere.jpg`, `img/essenza-noce.jpg`,
512x512 perche la ripetizione specchiata in WebGL 1 richiede potenze di due).
Il modello non ha coordinate UV: si ricavano nello shader proiettando la
posizione sui tre assi, scegliendo per ogni faccia il verso in cui deve correre
la venatura. Salvia e antracite restano tinte piene: sono laccati, ed e giusto
cosi.

### La sequenza esterni e stata rifatta (26 agosto 2026)

I fotogrammi dei video generati con Gemini portano il **rombo del filigrana in
basso a destra**, a circa il 90% della larghezza e l'83% dell'altezza, sempre
nella stessa posizione. Nella vecchia `img/esterni` c'era in tutti e 120.
Controllate anche `img/journey` e le vecchie `img/madia`: quelle erano pulite.

`img/esterni-2` sostituisce `img/esterni`: **60 fotogrammi invece di 120**,
ritagliati a `1125x720` (il taglio del bordo destro porta via il rombo senza
inventare pixel) e ricompressi a qualita 72. Da **13,8 MB a 5,1 MB, -63%**,
senza perdere nulla di visibile: la sezione e a tutto schermo con ritaglio
"cover", quindi i bordi vengono comunque tagliati dal browser.

**La cartella e nuova apposta.** `netlify.toml` mette cache `immutable` su
queste sequenze: riscrivendo file con lo stesso nome, chi era gia stato sul
sito avrebbe continuato a vedere i vecchi. Se un giorno si rigenera di nuovo,
usare `esterni-3` e aggiornare la regola in `netlify.toml`.

`img/madia` (4,4 MB) e stata rimossa: non serviva piu dal passaggio al 3D.
Entrambe restano nella storia di git se dovessero servire.

**Se arriva un nuovo video generato con l'AI:** controllare sempre l'angolo in
basso a destra prima di spezzarlo in fotogrammi.

### Apertura del sito: cosa NON rifare

Il primo caricamento chiedeva **250 file per 20,5 MB**, perche journey (145
fotogrammi) ed esterni (120) partivano tutti insieme al primo istante. Il
fotogramma iniziale della journey — l'unico che serve subito — finiva in coda
dietro altri 264, e l'apertura restava nera. Peggio: il velo di caricamento
spariva dopo **2,2 secondi fissi** senza aspettare nulla, e nel frattempo la
pagina scorreva sotto, quindi l'utente si ritrovava gia a meta sito.

Ora:

- **Le sequenze lontane si caricano quando servono.** `img/esterni` parte da un
  IntersectionObserver con `rootMargin:'150% 0px'`, circa una schermata e mezza
  prima. Da sola vale 14 MB tolti all'apertura. Se si aggiunge una nuova
  sequenza pesante, differirla allo stesso modo — non lasciarla partire al
  caricamento.
- **La journey carica per priorita:** prima il fotogramma 0, poi uno ogni 12
  (cosi lo scrub e subito scorrevole), poi tutti gli altri, sei alla volta.
  Lo stato e in `window.VISIO_CARICA` (`primo`, `radi`, `radiTot`).
- **Il velo si alza quando `VISIO_CARICA.primo` e vero**, con un minimo di 1,5 s
  (il logo deve finire di disegnarsi) e un tetto di 9 s perche nessuno resti
  intrappolato. In piu c'e un salvagente in CSS (`@keyframes ldSalvagente`) che
  lo toglie a 12 s anche se il JavaScript non parte affatto.
- **Lo scorrimento e bloccato mentre il velo e su** (`overflow:hidden` su html e
  body) e alla chiusura si fa `scrollTo(0,0)`: si riparte sempre dall'inizio.
  Il gesto di scroll non muove la pagina, **spinge le due scritte** che scorrono
  in versi opposti sopra e sotto il logo. Sono solo testo: zero file da
  scaricare.

Misurato: da **20,5 MB a 10,8 MB** al primo caricamento, primo fotogramma a
117 ms invece che in coda.

**Come rimisurare** (in console, dopo un caricamento pulito):

    performance.getEntriesByType('resource').length
    performance.getEntriesByType('resource').reduce((s,e)=>s+(e.transferSize||0),0)/1048576

**Per ispezionare il velo** senza rete lenta: alzare temporaneamente `MIN` *e*
`MAX` nel blocco LOADER — alzare solo `MIN` non basta, chiude comunque `MAX`.

### La pagina preventivo (`preventivo.html`)

Configuratore: il cliente sceglie i servizi e ottiene una **forbice di prezzo**,
mai una cifra secca. Si arriva a `/preventivo` da tre punti:

1. **voce 04 del menu** a panino;
2. il **richiamo in vetro nella sezione contatti** della home, accanto al modulo,
   cosi chi e gia deciso sceglie fra scrivere e configurare;
3. **due link nella FAQ**, dentro le risposte "Quanto costa un render?" e
   "Come faccio ad avere un preventivo?" — che sono i momenti di massimo
   interesse su tutto il sito.

**Le risposte della FAQ sono state riscritte** perche contraddicevano il
listino: dicevano *"non lavoriamo a singola vista ma a progetto"* mentre il
configuratore prezza proprio a vista. Se un domani cambiano i prezzi, ricordarsi
che le cifre compaiono **anche nella FAQ**, sia nel testo visibile sia nello
schema JSON-LD per i motori — sono due copie, vanno cambiate tutte e due.

**Il meccanismo da capire prima di toccarla.** La forbice parte larga e **si
stringe a ogni risposta**: le fasce "non risposto" in `IGNOTO` contengono tutte
le risposte possibili, quindi rispondere puo solo restringere, mai allargare.
Se si aggiunge una nuova domanda, la sua fascia in `IGNOTO` deve contenere tutte
le opzioni, altrimenti il cliente vede il prezzo salire mentre risponde — che e
esattamente l'effetto opposto a quello voluto.

I moltiplicatori sono volutamente contenuti (±10-20%). Si moltiplicano fra loro:
allargandoli si ottengono massimi che nessun cliente riconosce come credibili.
La parte grossa del prezzo la decidono i servizi scelti e il numero di viste.

**I prezzi stanno tutti nel blocco `LISTINO` in cima al file**, insieme a
`SCONTO`, `MINIMO` e `IVA_ESCLUSA`. I prezzi dei servizi sono quelli dati da
Matteo il 26 agosto 2026 (`PREZZI_VERIFICATI = true`). L'IVA esclusa e confermata. Sconto (10%), minimo di progetto (300 €) e IVA esclusa sono stati
confermati il 26 agosto: `APERTI_CONFERMATI = true` e l'avviso giallo è sparito.
Se un domani si rimettono in discussione, rimetterlo a `false` e ricompare. Lo sconto in particolare finisce nero su bianco in pagina: e una promessa
al cliente, non un dettaglio.

**I pacchetti non sono la somma delle voci.** Ognuno porta in dote degli `extra`
compresi (alta risoluzione, formati social, PDF impaginato, giri di revisione,
archivio a fine lavori) che a listino non si comprano: e quello che li rende
convenienti rispetto al configurare a mano, altrimenti sceglierli non darebbe
alcun vantaggio al cliente. Gli extra crescono da Smart (3) a Chiavi in mano (7).

Quando si parte da un pacchetto, `stato.pacchetto` se lo ricorda: gli extra
compaiono nel riepilogo come "compreso" senza prezzo, e finiscono **nella bozza
che ci arriva per email**, marcati *da onorare nel preventivo*. Se si aggiungono
extra nuovi, ricordarsi che sono promesse contrattuali, non decorazione.

Attenzione al **minimo di progetto**: deve restare sotto al pacchetto Smart
(5 viste x 65 = 325), altrimenti la card mostra una cifra e il riepilogo un'altra.
Il minimo viene applicato sia al totale sia alle card dei pacchetti.

Il render di interni ha un **minimo di 5 viste** (`min:5`): scendere sotto quella
soglia con il "meno" toglie del tutto il servizio, invece di bloccarsi.

Altro che c'e dentro: quattro **pacchetti pronti** (Smart per una stanza sola,
Essenziale, Completo, Chiavi in mano) che riempiono il configuratore in un clic; l'elenco **"cosa ci serve da te"** che cambia in base alle scelte; i
**tempi indicativi**; la bozza **salvata in `localStorage`** (si ritrova
tornando); invio via **Netlify Forms** (`name="preventivo"`) con la bozza
completa in un campo nascosto.

### Le URL pubbliche puntano al dominio

Dal 26 agosto 2026 `canonical`, Open Graph, JSON-LD, `sitemap.xml`, `robots.txt`
e `llms.txt` usano `https://visiorender.it` e non piu `visiorender.netlify.app`:
altrimenti Google indicizza il sottodominio Netlify e il dominio vero resta un
doppione. Se si aggiunge una pagina, usarlo anche li.

### Indicizzazione: stato al 26 agosto 2026

**Google non ha ancora nessuna pagina del sito.** Verificato con `site:visiorender.it`
e `site:visiorender.netlify.app`: zero risultati su entrambi. Non e un problema
tecnico — robots.txt e aperto, la sitemap risponde, nessun `noindex`, i canonical
puntano al dominio giusto. Semplicemente **il dominio ha due giorni e nessun sito
al mondo lo linka**, quindi Googlebot non ha mai avuto motivo di passare.

**Il nome e molto conteso, e va saputo:**

- cercando *"visio render"* Google **corregge da solo in "visoid render"** e mostra
  Visoid (piattaforma AI di rendering). Secondo risultato: **visiorealis.it**, uno
  studio italiano di rendering 3D con un nome quasi identico.
- cercando *"visiorender"* attaccato esce **visiorender.com**, un costruttore di
  siti no-code che ha il .com del nostro nome.
- in piu Microsoft Visio occupa tutto il campo semantico di "visio".

Quindi puntare su "visio render" e una battaglia persa in partenza. Le query
realistiche sono **"visio render roma"**, **"rendering architettonico roma"** e
soprattutto **"quanto costa un render"**, dove la pagina preventivo ha argomenti
veri da spendere.

**Cosa manca (richiede l'account Google di Matteo):** proprieta su Search Console
+ invio della sitemap + "richiedi indicizzazione" sulle pagine principali. E il
**profilo Google Business**, che per un'attivita locale a Roma pesa piu del sito.

**IndexNow e attivo:** chiave in `1fa6e4742bf23695b0a06ba0da8115b2.txt` alla radice. Notifica Bing, Yandex e di
riflesso la ricerca di ChatGPT (che usa Bing). Google non lo usa. Per rilanciarlo
dopo aver pubblicato pagine nuove:

    curl "https://api.indexnow.org/indexnow?url=https://visiorender.it/&key=1fa6e4742bf23695b0a06ba0da8115b2"

## 4. Area riservata clienti

Nel menu, sotto le voci numerate, c'è un blocco separato "Accedi al tuo sito":
il cliente digita il codice e viene portato alla sua pagina.

**I codici non sono in chiaro nel sorgente.** Si salva l'impronta SHA-256 del
codice e l'indirizzo cifrato con il codice stesso, così chi legge il sorgente
non ricava l'elenco dei clienti. Per aggiungerne uno:

```bash
python3 strumenti/genera-accesso.py CODICE /cartella-cliente
```

Stampa la riga da incollare nell'elenco `ACCESSI` dentro `index.html`.

**È una porta di cortesia, non una serratura**: chi ha il codice può girarlo, e
chi arriva sull'indirizzo lo apre comunque. Le pagine cliente hanno `noindex`
per non finire su Google. Per una protezione vera serve una password lato
server, quindi il piano Netlify a pagamento.

**Casa Traversa** (novembre 2026) → `/area-ct26`, codice **`traversa26`**. Pagina con
rilievo Polycam navigabile (tre scansioni separate: piano terra, scala, piano camere,
non allineate fra loro), render, piante, preventivo Michelessi da sfogliare e
calcolatore «Componi l'offerta» (B e C si tolgono, F si aggiunge, A-D-E fissi;
le voci stanno nell'array `G` in fondo alla pagina). In `_headers` c'è
`X-Robots-Tag: noindex` su tutta la cartella, perché il PDF ha nomi e prezzi.
I DAE di Polycam si convertono con `strumenti/polycam/converti.py`.
Il modello SketchUp «TRAVERSA DEFINITIVO» (83 MB, sorgenti sul ramo orfano
`traversa-sorgenti`, che non va pubblicato) è in pagina come `area-ct26/3d/progetto.glb`
(18 MB): convertito con OpenSKP, a cui va corretta in locale la classe `EdgeFlagStore`
(array denso → Map, altrimenti chiede 32 GB), poi tolte normali e uv dei materiali senza
texture e passato in `gltf-transform optimize --compress meshopt --texture-compress webp
--texture-size 1024 --simplify-ratio 0.3`. Cloudflare non accetta file oltre 25 MB.
Rilievo allineato al modello: `area-ct26/3d/allineamento.json` (una matrice per
scansione), calcolato con `strumenti/polycam/allinea.py` sui muri in pianta (rotazione
per correlazione, poi ICP 2D; 66-77 % dei muri entro 15 cm). Nel modello il pavimento del
piano terra è a 0,588 m (sotto c'è il terreno) e quello del piano camere a 3,588 m: 3,00 m
fra i pavimenti contro i circa 3,20 m del rilievo. Il rilievo è messo sui pavimenti del modello. Tour 360: `area-ct26/3d/tour.html`, punti di vista
nell'array `PUNTI` (coordinate del modello; il modello è ruotato di 180° rispetto alle
piante del preventivo). Nel modello ci sono scritte 3D di SketchUp («cappotti», «LAV ASC»)
che si vedono nel tour: vanno tolte in SketchUp e il GLB rigenerato.
Piante ante e post operam (6 tavole A3 1:50, `scarica/Casa_Traversa_piante_ante_post.pdf`,
anteprime in `area-ct26/tavole/`): ante dalla sezione del rilievo a 1,20 m, post dalla sezione
del modello (muri riconosciuti come coppie di linee a 5-46 cm che proseguono a 2 m, perché
nel modello i tag sono tutti vuoti), confronto col rilievo riscalato. Strumenti in
`strumenti/polycam/` (orto.html, sezione.mjs, piante.py, tavole.py, fogli.py, pdf.js).
Il modello è circa il 4-5 % più grande del rilievo: segnalato al cliente sulla pagina.
Da fare: render nuovi della cucina (specchio fumé anticato al posto del pannello azzurro).

**Progetto Mario** (23 novembre 2026) → `/area-mr26`, codice **`Mario26`** (i codici
sono senza maiuscole: va bene anche `mario26`). Pagina: copertina sul soggiorno, modello 3D in pagina,
anteprime dall'alto, render «stanza per stanza» (zona giorno, camere e studio, bagni,
casa dall'alto: 18 immagini in `area-mr26/render/`, con il confronto a cursore ante scure/chiare della cucina, colonne che rispettano il formato),
confronto oggi/domani; niente preventivo per ora. In due render dall'alto (studio,
camera) il simbolo di Gemini nell'angolo è stato tolto ritagliando il bordo in basso.
Sorgente: `curigliano daniel.skp` (380 MB, sul Desktop, non nel repo) con più varianti
vecchie, una planimetria 2D importata (il DWG «Rilievo stato attuale») e la variante
definitiva, riconoscibile dalla scritta 3D «definitivo» (un componente con quel nome)
appoggiata accanto. Per trovarla: `strumenti/polycam/skp-radici.mjs` elenca gli oggetti
di primo livello con l'ingombro; la definitiva è il blocco a x −181…−160, z −34…−13.
Esportata con `skp-esporta.mjs file.skp radici.json out.glb -181 -160 -34 -13 definitivo`
(toglie anche la geometria libera del livello principale, che è delle altre varianti),
poi `strip-uv.mjs` **senza togliere le normali** (con le normali da ricalcolare il browser
si bloccava per minuti su un blocco da 300 mila triangoli) e `gltf-transform optimize`
come per Casa Traversa → `area-mr26/3d/progetto.glb`, 18 MB.
**Aggiornato il 24/11/2026 con il nuovo `Documents/mario.skp` (148 MB)**: contiene solo
la variante definitiva (niente copie vecchie né DWG), esportato intero con OpenSKP compresa
la geometria libera del livello principale, che qui sono i **controsoffitti** (circa 120 m²
fra 2,5 e 2,6 m dal pavimento, più una parte a 3 m). La pergola sul terrazzo non c'è più.
Il visore apre il modello tagliato a 2,40 m («Senza soffitto», sotto i controsoffitti);
«Tutto» li mostra.
Rilievo (dal 25/11): una sola scansione, `sr`, cioè la scena Polycam «mario 2» che accorpa le due catture
(le vecchie `sa` e `sb` sono state tolte; i link `?s=sa` e `?s=sb` aprono `sr`). Convertita con
`strumenti/polycam/scena-a-blocchi.mjs` (GLB della scena → formato del visore, già allineata al modello con la matrice
di `allinea-mario.py` e spostata come il progetto nel visore, così passando dall'uno all'altra la casa resta ferma)
+ `riduci-texture.py` (texture 4096 → 2048). Per l'ingombro del progetto va dato `finito.glb`: con il GLB compresso
`getBounds` legge male le posizioni quantizzate. Anteprime in `area-mr26/img/`, catturate dal visore con `?nui`
(che abilita `preserveDrawingBuffer` per leggere il canvas).
**Finiture e lampi (24/11/2026)**: OpenSKP esporta ogni faccia SketchUp con fronte e retro come due triangoli
nello stesso punto (124 mila coppie su 950 mila): a doppia faccia il visore li disegnava insieme e ruotando lampeggiavano.
`strumenti/polycam/finiture-mario.mjs` (sul GLB grezzo, prima di strip-uv e optimize) mette le coppie in primitive a
faccia singola e il visore ora rispetta doubleSided del GLB invece di forzare DoubleSide; nello stesso passo il pavimento
(texture laminato m227, m229) diventa parquet a spina di pesce in rovere a 45° (`spina.py`, piastrella 1,08 m, doghe
9 x 54 cm), pareti e soffitti bianco caldo, il lato di sopra dei controsoffitti (grigio) chiaro, la vetrata azzurra vetro.
Gli indici dei materiali valgono per il mario.skp del 24/11: se il file cambia, rifare l'inventario.
**Pianta arredata PDF**: `orto-mario.html` (vista dall'alto a 200 px/m, taglio 1,20 m) + `sezione-glb.mjs` (sezione
vera del GLB grezzo) + `pianta-mario.py` (muri del gruppo «Gruppo#20» campiti: zone più strette di 65 cm fra le linee;
stanze misurate riempiendole da un punto, con porte e finestre come barriera) + `impagina-mario.py` (reportlab, A2 1:50,
cartiglio, scala grafica) → `area-mr26/scarica/Progetto_Mario_pianta_arredata.pdf`. Su questo PC Smart App Control blocca
le DLL non firmate: niente SciPy né bpy da pip (si usa PIL per la morfologia).
**Tour 360** (24/11): `area-mr26/3d/tour.html` + `3d/tour/` (11 panorami 4096 px, `punti.json`, `visibili.json`), fatti
con `strumenti/polycam/render360-mario.py` in Blender 5.3 portatile (`C:\Users\PC\Tools\blender-5.3.0-windows-x64`,
GPU RTX 5080 con OptiX: circa 2 minuti a panorama a 384 campioni). Parte da `finito.glb` (le finiture senza meshopt, che
Blender non legge). Le facce gemelle a faccia singola diventano trasparenti dal retro (nodo Backfacing); i vetri e le
finestre «Janela» (grigio al 50 %) sono lastre sottili trasparenti. Alcune stanze nel modello non hanno soffitto: lo script
mette un tetto a 3,075 m dove si è dentro casa (muri in tutte le direzioni a 1,90 m) e sopra non c'è niente, allargato di
30 cm; i terrazzi restano aperti. I punti si spostano da soli nel punto libero più vicino; l'ingresso (corridoio stretto)
è escluso. Le porte del modello sono chiuse: i collegamenti fra stanze sono nell'array `PORTE` di `tour.html`.
Luce: sole basso e caldo (22°, azimut 150°), cielo, un disco caldo a soffitto per stanza; `ESPO=-0.6 LUCE=45`.
**Rilievo sovrapposto e piante ante/post** (24/11): scena Polycam unica «mario 2» (le due catture insieme, scaricata in GLB
dal pulsante Download della scena). `triangoli-glb.mjs` → `allinea-mario.py` (solo numpy: muri = linee a 1,20 e 1,90 m,
rotazione per correlazione FFT, poi ICP; risultato rotazione 20,5°, 60 % dei muri entro 15 cm) → vista dall'alto della
scansione con `orto-mario.html?foto&mat4=…&riquadro=…` (stesso riquadro della pianta arredata) → `ante-post-mario.py`
(muri di oggi = strisce non rilevate più strette di 50 cm fra zone rilevate; confronto esistenti/nuovi/da demolire) →
`impagina-ante-post.py` → `area-mr26/scarica/Progetto_Mario_piante_ante_post.pdf` (3 tavole A2 1:50) e anteprime
`img/ante.jpg`, `post.jpg`, `confronto.jpg`. Oggi il pranzo è un terrazzo e cucina + cameretta sono un unico locale. Le
campiture gialle (da demolire) sono indicative: possono essere armadi rilevati come ingombri.
Da fare: render nuovi (il progetto è cambiato), rilievo sovrapposto anche nel visore 3D, piante quotate.

Codice pubblico di esempio: **`visio`** → `/esempio` (Villa Ferrara), suggerito
in chiaro nel menu stesso.

---

## 5. Generazione immagini

MCP `nano-banana` su **imgeditor.co**, chiave nel Portachiavi
(`imgeditor-api-key`). **Chiedere sempre a Matteo quale modello usare e
riportare i crediti residui prima di generare**, anche per i lotti.

- **`nano-banana-pro`**, ~6 crediti a 2K: l'unico da usare. Rispetta i
  riferimenti, regge bene il testo dentro le immagini.
- `nano-banana` senza suffisso **ignora le immagini di riferimento**.
- Non esiste uno strumento per generare video: quelli li produce Matteo.

**Il metodo che funziona**: passare come riferimento i frame della villa
(`img/journey-2/frame-0075.jpg` per i materiali interni, `frame-0145.jpg` per
esterni e luce), e per gli elaborati successivi passare **il precedente** —
è così che schema impianti e planimetria sono risultati coerenti fra loro.

**Il testo è il punto debole**: la planimetria è uscita in inglese e con una
camera duplicata, ed è servito un secondo giro. Un oggetto isolato su fondo
neutro riesce invece molto bene al primo colpo.

Le immagini vanno **sempre ricompresse** prima di pubblicarle: i render
originali del sito pesavano 1,5-2,4 MB l'uno a fronte di 200 KB necessari.
Qualità 85-88, `optimize`, `progressive`.

---

## 8. Accessibilità

Misurata con **axe-core** in Chromium, non a occhio. Prima: 6 tipi di problema in
home (2 critici, 2 gravi), 5 nel configuratore. Adesso: **nessun problema critico
o grave su nessuna pagina**; resta solo `region` (buona pratica, non un requisito
WCAG) sul salta-contenuto e sul tasto WhatsApp, che stanno fuori dai landmark
perché sono elementi flottanti.

Per rimisurare:

    cd <cartella scratch> && npm i axe-core playwright
    # servire il sito su 127.0.0.1:4601 e lanciare axe su ogni pagina
    # ATTENZIONE: forzare `.in` sugli elementi `.rev` e spegnere transizioni e
    # animazioni prima di misurare, altrimenti axe legge i colori a metà
    # dissolvenza e restituisce 170 falsi positivi.

### Cosa è stato sistemato
- **Contrasti**: l'oro `#C9A96E` e i grigi `#888/#999/#AAA` sul chiaro stavano fra
  2,0 e 3,4:1. Ora ci sono due token — `--gold-t #7a5f30` per l'oro come testo su
  fondo chiaro e `--muted-s #7e7e7e` per i grigi su fondo scuro — e `--muted` è
  passato da `#888` a `#6a6a6a`. **Sul fondo scuro l'oro resta quello di sempre**
  (8,85:1): il problema era solo sulle sezioni chiare.
- **Etichette dei moduli**: erano `<label>` sciolte, senza `for`. Chi usa uno
  screen reader sentiva "casella di testo" e basta. Ora tutte collegate.
- **Menu chiuso**: era invisibile ma raggiungibile col tabulatore. Ora ha `inert`
  quando è chiuso, il fuoco entra sulla prima voce quando si apre e torna sul
  tasto quando si chiude. Esc lo chiude.
- **Fuoco da tastiera visibile**: col cursore custom (`cursor:none`) non si vedeva
  proprio dove si era. Ora c'è un contorno dorato su `:focus-visible`.
- **Salta al contenuto** come prima voce di tabulazione, e `<main>` su tutte le
  pagine (le FAQ ne avevano già uno: attenzione a non annidarne due).
- **Livelli dei titoli** nel configuratore: c'erano `h4` dopo `h2`.
- **Cursore finto spento dove non c'è il mouse** (`hover:none`): sul telefono
  restava fermo in un angolo e toglieva la manina ai comandi. Ora non viene
  nemmeno creato, e il suo ciclo `requestAnimationFrame` non parte.

### Cosa resta — le cose che axe non sa misurare
Sono tutte legate al fatto che il sito è molto interattivo, e vanno provate a
mano, con la sola tastiera e con VoiceOver:

1. **Le sezioni si comandano solo con mouse o dito.** Madia (trascinamento), tour
   360°, mirino della realtà aumentata, cursore prima/dopo, comandi delle luci,
   gallery orizzontale: da tastiera non si fa nulla. Servono almeno le frecce per
   ruotare e `Tab`+`Invio` per i comandi.
2. **I `<canvas>` non hanno alternativa testuale.** Chi non vede non sa cosa c'è
   dentro: serve un testo che descriva la scena (`aria-label` o testo dentro il
   canvas).
3. **Il velo di apertura blocca lo scroll fino a 9 secondi** e non è annunciato.
4. **Ordine del fuoco quando si apre il bottom-sheet** dei tre modi di lavorare.
5. **`prefers-reduced-motion`**: rispettato da recensioni, madia e prima/dopo, non
   ancora dalle sezioni legate allo scroll.
6. **Dimensione dei bersagli** sotto i 44x44 px su alcuni comandi piccoli.
7. **Ingrandimento del testo al 200%** da verificare sulle sezioni sticky.

---

## 7. Legale, privacy e font

### Perché non c'è il banner dei cookie
Perché non serve. Il consenso si chiede per i cookie di profilazione e per gli
strumenti di statistica: **questo sito non ne ha nessuno**. Niente Analytics,
niente pixel, niente mappe o video incorporati. L'unico `localStorage` è la
bozza del preventivo, che resta sul dispositivo di chi la compila.

Mettere un banner "per sicurezza" costerebbe conversioni in cambio di niente.
**Se un domani si aggiunge Analytics o un pixel, il banner diventa obbligatorio**
e va aggiunto prima di pubblicare lo strumento, non dopo.

Quello che invece serve, e adesso c'è: informativa privacy (art. 13 GDPR, perché
i moduli raccolgono dati personali), pagina cookie, dati societari e partita IVA
in ogni piede di pagina — per una società con partita IVA è un obbligo di legge,
non un vezzo.

### I font stanno sul nostro dominio
Prima le pagine chiamavano `fonts.googleapis.com`: significa che l'indirizzo IP
di ogni visitatore finiva a Google prima ancora che decidesse di restare. È il
punto su cui in Europa sono arrivate le contestazioni. Ora i file stanno in
`font/` e il foglio di stile è `font/visio.css` — nessuna richiesta a terzi.

Sono solo i sottoinsiemi `latin` e `latin-ext` (cirillico, greco e vietnamita non
servono) e solo i pesi usati davvero: Cormorant Garamond 300/400 e corsivo
300/400, Inter 300/400/500. Se servisse un peso nuovo va aggiunto qui, altrimenti
il browser lo sintetizza e si vede.

Per rigenerarli (serve rete verso Google, una volta sola):

    curl -A "Mozilla/5.0" "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=Inter:wght@300;400;500&display=swap" -o /tmp/gf.css

poi si tengono i blocchi `/* latin */` e `/* latin-ext */`, si scaricano i
`.woff2` in `font/` e si riscrivono le `@font-face` con `url(/font/nome.woff2)`.
`netlify.toml` mette su `/font/*` la cache `immutable`: i nomi non devono
cambiare, o chi è già stato sul sito continuerà a vedere i vecchi.

### Le due pagine
`privacy.html` e `cookie.html` girano sullo stesso guscio scuro delle FAQ, sono
indicizzabili e stanno in `sitemap.xml`. I dati del titolare compaiono in tre
posti — piede delle pagine, informativa, JSON-LD (`legalName`, `vatID`,
`address`): se cambiano, vanno cambiati in tutti e tre.

---

## 6. Decisioni prese, per non rimetterle in discussione

- **Menu a hamburger su tutte le larghezze**, anche desktop. Navbar ridotta a
  logo e hamburger; le voci e la CTA vivono nel menu a schermo intero.
- **Niente voce "Contatti"** nel menu: era ridondante con "Richiedi info".
- **Il modello 3D sorgente non è compreso** nella consegna: il servizio è di
  visualizzazione. Dichiarato nelle FAQ, e coerente con la scheda "Modello 3D
  completo" nella sezione documenti — che prima prometteva erroneamente i file
  OBJ/FBX/nativo ed è stata corretta l'8 agosto. **Se si tocca quella scheda,
  non reintrodurre la promessa dei file sorgente.**
- **Il 360 mantiene FOV 75° e mappatura piena.** Una correzione della curvatura
  a 115° era stata provata e scartata: raddrizzava le linee ma zoomava,
  restringendo il campo visivo.
- **Immagini reali al posto delle illustrazioni** dove possibile: fatto per
  documentazione, realtà aumentata, esterni e madia.

---

## Studio del sole — sezione `#solare` e pagina `/sole/` (4 novembre 2026)

- **In home** la sezione `#solare` (fra esterni e illuminazione) spiega lo studio
  dell'esposizione: orientamento della casa, pannelli solari, ombre sul contesto.
  La demo è un canvas 2D scritto a mano come la madia, niente librerie. I calcoli
  del sole sono quelli astronomici veri per Roma (41,9° N) ma in **ora solare**:
  per questo la riga sotto lo dice esplicitamente. La percentuale "sole sulla falda
  sud" è l'incidenza rispetto al sole perpendicolare, non una resa in kWh: non
  presentarla come produzione dell'impianto.
- **Lo strumento completo** sta in `/sole/` ed è generato da `strumenti/sole-src/`
  (`npm run build:sito`). Parte con un quartiere di esempio e **non contatta
  nessuno finché il visitatore non sceglie "Usa le mappe reali"**: OpenStreetMap
  (mappe, ricerca indirizzi) e Overpass (edifici) ricevono l'IP, quindi è la
  stessa logica dei font ospitati in casa. La scelta resta in `localStorage`
  (`visio-sole-osm`), documentata in privacy (`#sole`) e nella pagina cookie.
- I servizi pubblici di OSM hanno limiti d'uso pensati per traffico leggero. Se lo
  strumento comincia a girare molto, passare a un fornitore (MapTiler, Stadia,
  Geoapify) cambiando gli URL in `src/ground.js`, `src/geo.js`, `src/buildings.js`.

---

## Demo per pizzerie — `/pizza/` (20 novembre 2026, menu vero dal 23 novembre)

Prova reale per un cliente pizzeria (**Il Presidente, Via Milazzo**), **non è un
servizio di VISIO** e non è collegata al sito: niente link, `noindex` (meta e
`X-Robots-Tag` in `_headers`), fuori da sitemap e `llms.txt`.

- **Cosa fa**: il QR sul tavolo apre `visiorender.it/pizza/#tavolo-N`; il cliente
  sceglie una delle 43 pizze del menu (rosse, bianche, speciali), la vede comporsi,
  aggiunge o toglie ingredienti, aggiunge ripieni, fritti, dolci e bevande e invia;
  poi ne segue lo stato. `#cucina` mostra le comande e gli «esauriti», `#gestione`
  la sala, le analisi (pizze mai ordinate, aggiunte più richieste…) e i cartellini
  QR in PDF. `/pizza/` senza hash è l'indice.
- **Una comanda per tavolo**: ogni telefono manda il suo ordine (resta separato
  per il conto e le analisi), ma in cucina gli ordini dello stesso tavolo e nello
  stesso stato diventano una sola scheda con le quantità sommate e tutte le note;
  «Inforna», «Pronto» e «Servito» spostano insieme tutto il tavolo
  (`staff/stato` con `ids`). Un ordine arrivato quando il resto del tavolo è già
  in forno resta una scheda a parte, segnata «Aggiunta».
- **App camerieri** (`#cameriere`, stesso PIN di cucina e gestione): «Da fare» con
  chiamate dei tavoli e comande pronte (suono e vibrazione dopo «Attiva avvisi»,
  solo a pagina aperta: niente notifiche a telefono bloccato), tavoli, coperti,
  conto diviso alla romana o per telefono (ogni telefono ha un id in
  `localStorage`, campo `dev` dell'ordine), «Prendi l'ordine» per il tavolo
  (stessa pagina del cliente, ordine segnato `cameriere`), schermo sempre acceso.
- **Coperti**: impostazione in gestione (`cliente` = chiesti al primo ordine,
  `cameriere`, `no`); stanno nella chiave `tav:N` del Durable Object fino alla
  chiusura del conto. Il prezzo del coperto si cambia nella scheda Menu.
- **Menu modificabile dal titolare** (gestione → Menu): prezzi, pizze nascoste,
  pizze nuove, pizza del giorno, supplementi, coperto. Le modifiche stanno nella
  chiave `menu` del Durable Object sopra `listino.json` (`menuUnito` in
  `worker/pizza.js`); le pagine le leggono da `/api/pizza/menu`.
- **Stima dell'attesa** per il cliente: mediana degli ultimi ordini arrivati a
  «pronto» (12 minuti se non ce ne sono) + 45 secondi per ogni pizza arrivata
  prima e non ancora in forno. È dichiarata come stima.
- **Filtro allergeni** sul telefono («Evita: …»): nasconde pizze e voci che li
  contengono secondo il menu, con l'invito ad avvisare sempre il personale.
- **Riepilogo serale via email**: cron `0 0 * * *` in `wrangler.jsonc` →
  `scheduled` in `worker/index.js` → email via Resend (stessa `RESEND_API_KEY`
  dei moduli; mittente `PIZZA_MAIL_FROM` o `MAIL_FROM`) all'indirizzo scelto in
  gestione → Impostazioni. Ultime 20 ore; niente email se non ci sono ordini.
- **Listino**: tutto in `pizza/listino.json` (preso dal PDF del menu dell'11/11/2026):
  pizze con prezzo e ingredienti, ingredienti per categoria con allergeni, resto del
  menu. Lo leggono **sia la pagina sia il Worker** (`import` in `worker/pizza.js`):
  i prezzi si cambiano solo lì. Regola del prezzo: pizza del menu + supplemento
  delle aggiunte, togliere è gratis; se gli ingredienti coincidono con un'altra
  pizza del menu vale quella. **I supplementi (`supp`) non sono nel menu: sono
  provvisori, da far confermare alla pizzeria.**
- **Da chiarire con la pizzeria** (riportati come stampati): il coperto compare a
  2,50 € e a 2,00 € (in pagina si usa 2,50); allergeni dubbi su Mr. Duplo (5 =
  pesce, mancano le nocciole), Tiramisù (mancano le uova), Dubai chocolate
  (pistacchio). Corretti refusi evidenti (Delizia, lemon curd, Spinelli).
- **Dati**: un Durable Object con SQLite (`worker/pizza.js`, classe `Pizzeria`,
  binding `PIZZERIA` e migrazione `pizza-v1` in `wrangler.jsonc`). Le pagine
  leggono `/api/pizza/stato` ogni 2,5 secondi.
- **PIN del personale**: se nel Worker c'è il segreto `PIZZA_PIN` (Cloudflare →
  visio-studio → Settings → Variables and secrets), cucina e gestione lo chiedono.
  Senza segreto sono aperte a chi conosce l'indirizzo: va bene per la prova, non
  per l'uso vero.
- **Immagini**: basi, creme e 50 ingredienti sono rese procedurali
  (`strumenti/pizza-render.py pizza/img`, circa 6 minuti), non foto. In
  `pizza/index.html` la tabella `VIS` dice quale immagine, quanto grande e su
  quale strato disegnare ogni ingrediente del listino. Font, libreria QR e jsPDF
  stanno in `pizza/` (nessuna richiesta a terzi).
- **Presentazione animata** (`/pizza/presentazione/`, collegata dall'indice della
  demo): 16 schermate che spiegano l'app a una pizzeria, circa 4 minuti, avanzano da
  sole (frecce, tocco, spazio per la pausa, `#N` per aprire la schermata N). È un
  solo file HTML con le schermate vere dell'app in `pizza/presentazione/img/` e la
  pizza disegnata con gli stessi sprite di `pizza/img/`. Si adatta: 1920×1080 in
  orizzontale, 1080×1920 in verticale. Con `?rec` gira su un orologio virtuale
  (`window.__rec.step(ms)`), così si registra un video fotogramma per fotogramma
  con Playwright + ffmpeg senza scatti. Se cambia l'app, rifare le schermate.
  **È generica, senza il nome del cliente** (scelta del 27/11/2026, per poterla
  mostrare ad altre pizzerie): le schermate sono state rifatte con il Worker in
  locale e un `listino.json` modificato solo per l'occasione («La tua pizzeria»,
  senza via; le pizze «Il Presidente» e «La Presidentessa» rinominate «Della casa»
  e «Gorgonzola e noci»; pizza del giorno la Tarantella) e con il fuso del browser
  spostato perché gli orari fossero di sera. La demo vera (`/pizza/`) resta quella
  de Il Presidente, e il QR dell'ultima schermata porta lì.
- **Voce della presentazione**: un mp3 per schermata in `pizza/presentazione/voce/`,
  testi e durate in `voce.json`. Dal 27/11/2026 è una voce da spot fatta con
  **ElevenLabs (Eleven v4 Turbo) tramite Higgsfield**, voce preimpostata «Elena»
  (`ca83ca7f-c186-493d-bd69-0d765fa861b2`), stabilità 0,35: tutte le 16 frasi in una
  sola richiesta, così tono e volume restano uguali (circa 9 crediti Higgsfield per
  2.900 caratteri). L'audio intero si divide in 16 file con
  `strumenti/pizza-voce-dividi.py` (trascrive con faster-whisper e taglia nei
  silenzi; `14=file.mp3` sostituisce una frase rifatta a parte, come è successo per
  «ogni allergene», pronunciato male e rifatto al plurale). Prima c'era Piper con la
  voce «Paola» (`strumenti/pizza-voce.py`, gratis ma piatta): resta come ripiego,
  ma sbaglia «gli»/«glie», «gn», «codice» e «app», e i testi attuali li contengono.
  All'apertura la pagina chiede «Guarda con la voce» o «Senza audio» (i browser non
  fanno partire suoni senza un tocco); con la voce ogni schermata dura almeno quanto
  la sua frase più un secondo. **Sincronia**: le animazioni sono scritte sui tempi
  della prima voce; ogni `<section>` ha un `data-warp="vecchio:nuovo,…"` (ms dalla
  partenza della schermata) che il motore usa per spostare cue e disegni sui tempi
  della voce attuale (calcolato confrontando le parole delle due voci). I pochi
  ritardi solo CSS (binario della schermata 2, schede della 7, tessere della 14,
  elenco della 15) sono stati spostati a mano con la stessa corrispondenza. Se si
  rifà la voce, rifare le ancore allo stesso modo. Dopo aver cambiato un testo
  conviene trascrivere l'audio (faster-whisper) per controllarlo.
- **Per toglierla**: cancellare `pizza/`, `worker/pizza.js`, le righe in
  `worker/index.js` e, in `wrangler.jsonc`, il binding; la migrazione resta e se ne
  aggiunge una con `deleted_classes: ["Pizzeria"]`.

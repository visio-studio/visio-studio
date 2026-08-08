# Note di lavoro — VISIO Studio

Stato del progetto, decisioni prese e cose ancora da fare.
**Questo file sta nel repository**, quindi si sincronizza con `git pull` ed è
disponibile su qualsiasi computer. Aggiornalo quando cambia qualcosa di
strutturale: è la memoria condivisa del progetto.

Ultimo aggiornamento: 8 agosto 2026.

---

## 1. Cose da fare, in ordine di urgenza

### Netlify è fermo — sbloccare dal 13 agosto
I deploy sono **in pausa per crediti esauriti** del piano gratuito (300/mese,
ciclo 14 luglio → 13 agosto). Ogni commit dopo `c98017d` risulta *Skipped —
account credit usage exceeded*. Il tasto *Trigger deploy* è disattivato: non è
un guasto e non è risolvibile via codice.

- **Dal 13 agosto** i crediti si ripristinano, ma i deploy arretrati sono
  *Skipped*, non in coda: **non ripartono da soli**. Serve un nuovo push o un
  *Trigger deploy* manuale.
- Nel frattempo il sito aggiornato è visibile su
  **https://visio-studio.github.io/visio-studio/** (tutto tranne il form
  contatti, che dipende da Netlify Forms).
- I 18 deploy di sviluppo sono costati 270 dei 308 crediti consumati, circa 15
  l'uno. Il traffico ha inciso solo per 38. A regime, con 2-3 pubblicazioni al
  mese, il piano gratuito basta ampiamente.

### Dominio visiorender.it — completare il collegamento
Comprato su Aruba l'8 agosto (11:25) insieme alla casella email. Al momento è
in stato `inactive / dnsHold`: registrato ma non ancora attivo, e infatti non
compare nel pannello Aruba. Di norma si sblocca entro 24 ore.

Su Netlify **è già aggiunto** (`visiorender.it` come dominio principale,
`www.visiorender.it` che reindirizza), in attesa di verifica DNS.

Quando compare nel pannello Aruba, impostare:

| Tipo  | Nome | Valore                    |
|-------|------|---------------------------|
| A     | `@`  | `75.2.60.5`               |
| CNAME | `www`| `visiorender.netlify.app` |

**Non toccare i record MX**: lì vive la posta. Aruba non supporta i record
ALIAS, quindi si usa l'A record (è l'opzione di ripiego indicata da Netlify).

Verificare anche se **IMAP è incluso** nel pacchetto o va attivato a parte: su
Aruba è un servizio aggiuntivo, e senza si ha solo POP3 — inadatto a chi lavora
da più computer. Parametri: `imaps.aruba.it` 993 SSL, `smtps.aruba.it` 465 SSL,
nome utente = indirizzo completo.

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
| Journey | `#journey` | 145 fotogrammi in `img/journey/` |
| LiDAR | `#lidar-section` | nuvola di punti su canvas |
| VR 360 | `#vr-scroll` (450vh) | panorama WebGL |
| Esterni | `#ex-wrap` (430vh) | 120 fotogrammi in `img/esterni/` |
| Sito dedicato | `#sd-wrap` | dispositivi + mini-sito |
| Madia | `#esploso-wrap` (340vh) | 96 fotogrammi in `img/madia/` |

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
(`img/journey/frame-0075.jpg` per i materiali interni, `frame-0145.jpg` per
esterni e luce), e per gli elaborati successivi passare **il precedente** —
è così che schema impianti e planimetria sono risultati coerenti fra loro.

**Il testo è il punto debole**: la planimetria è uscita in inglese e con una
camera duplicata, ed è servito un secondo giro. Un oggetto isolato su fondo
neutro riesce invece molto bene al primo colpo.

Le immagini vanno **sempre ricompresse** prima di pubblicarle: i render
originali del sito pesavano 1,5-2,4 MB l'uno a fronte di 200 KB necessari.
Qualità 85-88, `optimize`, `progressive`.

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

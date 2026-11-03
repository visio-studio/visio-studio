# VISIO · Sole e Ombre

Visore 3D per studi di soleggiamento: cerchi un indirizzo, il programma scarica gli edifici
reali da OpenStreetMap, li estrude in 3D e mostra le ombre per qualsiasi giorno e ora.

## Funzioni

- Ricerca per indirizzo o coordinate (`41.9, 12.49`), raggio 150 / 300 / 500 m
- Edifici reali da OpenStreetMap con altezze da `height` o `building:levels`;
  quelli senza dato hanno un'altezza stimata per tipologia (colore sabbia)
- Mappa OSM al suolo, ombre in tempo reale, cielo e luce che cambiano con l'altezza del sole
- Percorso solare del giorno con le ore, più i solstizi (arancio = 21 giugno, blu = 21 dicembre)
- Data, slider orario, animazione (barra spaziatrice), preset solstizi/equinozio
- Ora locale corretta del luogo cercato, con ora legale
- Dati del sole: altezza, azimut, alba, tramonto, lunghezza dell'ombra di un elemento di 10 m
- **Importa un modello GLB di progetto** (in metri), ruotalo e nascondi l'edificio OSM esistente sul punto
- **Esporta PNG** della vista e **scena GLB** con edifici, terreno, modello e una luce solare
  già orientata: si apre in Blender (e da lì in 3ds Max, SketchUp, ecc.) per usarla come contesto nei render
- Link condivisibile: posizione, data, ora e raggio restano nell'indirizzo della pagina

## Avvio in locale

Serve Node.js 20 o più recente.

```bash
npm install
npm run dev
```

Apri l'indirizzo mostrato nel terminale (di solito http://localhost:5173).

## Pubblicazione su Netlify

Il file `netlify.toml` è già pronto: collega la cartella a un sito Netlify (da Git o con
`npx netlify deploy --prod`), comando di build `npm run build`, cartella `dist`.

## Struttura

| File | Cosa fa |
|---|---|
| `src/main.js` | Scena Three.js, interfaccia, animazione, import/export |
| `src/buildings.js` | Download da Overpass ed estrusione degli edifici |
| `src/ground.js` | Mappa OSM sul terreno |
| `src/sun.js` | Posizione del sole (libreria suncalc) |
| `src/time.js` | Fuso orario del luogo e conversioni ora locale/UTC |
| `src/geo.js` | Proiezione in metri e geocoding Nominatim |

## Dati e limiti d'uso

- Dati © OpenStreetMap contributors (licenza ODbL): l'attribuzione in basso a sinistra va lasciata.
- Overpass, Nominatim e le tile di tile.openstreetmap.org sono servizi gratuiti con limiti
  d'uso pensati per uso leggero. Per un uso intenso o pubblico conviene passare a un fornitore
  (es. MapTiler, Stadia Maps, Geoapify) cambiando gli URL in `ground.js`, `geo.js` e `buildings.js`.
- Tetti piani, terreno piatto, niente alberi: va bene per studi di massima, non per verifiche normative.

## Prossimi passi possibili

Alberi e ostacoli posizionabili, terreno con quote reali (DEM), mappa delle ore di sole
su facciate e superfici, pannelli solari con stima della produzione.

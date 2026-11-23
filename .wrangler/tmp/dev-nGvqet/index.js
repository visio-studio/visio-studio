var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// worker/modulo.js
var MAX_ALLEGATO = 8 * 1024 * 1024;
var MAX_CAMPO = 5e3;
var ORIGINI = /^https:\/\/([a-z0-9-]+\.)?(visiorender\.it|visiorender\.pages\.dev)$/;
var NOMI = { contatti: "Contatti dalla home", preventivo: "Richiesta di preventivo" };
var json = /* @__PURE__ */ __name((dati, stato = 200) => new Response(JSON.stringify(dati), {
  status: stato,
  headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" }
}), "json");
var esc = /* @__PURE__ */ __name((s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]), "esc");
var etichetta = /* @__PURE__ */ __name((k) => k.replace(/[-_]/g, " ").replace(/^./, (c) => c.toUpperCase()), "etichetta");
function base64(buf) {
  const b = new Uint8Array(buf);
  let s = "";
  for (let i = 0; i < b.length; i += 32768) s += String.fromCharCode.apply(null, b.subarray(i, i + 32768));
  return btoa(s);
}
__name(base64, "base64");
async function inviaModulo(request, env) {
  const origine = request.headers.get("Origin") || "";
  if (origine && !ORIGINI.test(origine)) return json({ ok: false, errore: "provenienza non ammessa" }, 403);
  if (!env.RESEND_API_KEY) return json({ ok: false, errore: "invio non configurato" }, 503);
  let dati;
  try {
    dati = await request.formData();
  } catch {
    return json({ ok: false, errore: "modulo non leggibile" }, 400);
  }
  if ((dati.get("bot-field") || "").toString().trim()) return json({ ok: true });
  const modulo = (dati.get("form-name") || "contatti").toString();
  const email = (dati.get("email") || "").toString().trim();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 200) return json({ ok: false, errore: "email non valida" }, 400);
  const righe = [];
  const allegati = [];
  for (const [k, v] of dati.entries()) {
    if (k === "form-name" || k === "bot-field") continue;
    if (typeof v === "object" && v && "arrayBuffer" in v) {
      if (!v.size) continue;
      if (v.size > MAX_ALLEGATO) return json({ ok: false, errore: "allegato oltre 8 MB" }, 413);
      allegati.push({ filename: (v.name || "allegato").slice(0, 120), content: base64(await v.arrayBuffer()) });
      continue;
    }
    const t = v.toString().trim().slice(0, MAX_CAMPO);
    if (t) righe.push([etichetta(k), t]);
  }
  const nome = [dati.get("nome"), dati.get("cognome")].filter(Boolean).join(" ").toString().trim() || email;
  const titolo = `${NOMI[modulo] || "Modulo " + modulo} \xB7 ${nome}`.slice(0, 180);
  const html = `<h2 style="font-family:Arial,sans-serif">${esc(titolo)}</h2>
<table style="font-family:Arial,sans-serif;font-size:14px;border-collapse:collapse">${righe.map(([k, v]) => `<tr><td style="padding:6px 12px 6px 0;color:#666;vertical-align:top">${esc(k)}</td><td style="padding:6px 0;white-space:pre-wrap">${esc(v)}</td></tr>`).join("")}</table>
<p style="font-family:Arial,sans-serif;font-size:12px;color:#888">Inviato dal sito visiorender.it${allegati.length ? " \xB7 allegato: " + esc(allegati[0].filename) : ""}. Rispondi a questa email per scrivere a ${esc(email)}.</p>`;
  const testo2 = righe.map(([k, v]) => `${k}: ${v}`).join("\n");
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from: env.MAIL_FROM || "Sito VISIO <sito@visiorender.it>",
      to: [env.MAIL_TO || "info@visiorender.it"],
      reply_to: email,
      subject: titolo,
      html,
      text: testo2,
      ...allegati.length ? { attachments: allegati } : {}
    })
  });
  if (!r.ok) return json({ ok: false, errore: "invio email non riuscito", stato: r.status }, 502);
  return json({ ok: true });
}
__name(inviaModulo, "inviaModulo");

// worker/pizza.js
import { DurableObject } from "cloudflare:workers";

// pizza/listino.json
var listino_default = {
  _nota: "Listino della demo /pizza/, dal menu de Il Presidente (Via Milazzo, PDF dell'11/11/2026). Lo leggono sia la pagina sia il Worker (worker/pizza.js): i prezzi si cambiano solo qui. 'supp' = supplemento per aggiungere l'ingrediente a una pizza: NON \xE8 nel menu, sono valori provvisori da far confermare alla pizzeria. Allergeni con i numeri del menu.",
  locale: "Il Presidente",
  sede: "Via Milazzo",
  coperto: 2.5,
  allergeni: {
    "1": "Arachidi",
    "2": "Frutta a guscio",
    "3": "Latte",
    "4": "Molluschi",
    "5": "Pesce",
    "6": "Sesamo",
    "7": "Soia",
    "8": "Crostacei",
    "9": "Glutine",
    "10": "Lupini",
    "11": "Senape",
    "12": "Sedano",
    "13": "Solfiti",
    "14": "Uova"
  },
  categorie: [
    { id: "basi", nome: "Basi e creme" },
    { id: "formaggi", nome: "Formaggi" },
    { id: "salumi", nome: "Salumi e carni" },
    { id: "pesce", nome: "Pesce" },
    { id: "verdure", nome: "Verdure" },
    { id: "fritti", nome: "Fritti e croccanti" },
    { id: "finiture", nome: "Per finire" }
  ],
  ingredienti: {
    pomodoro: { nome: "Pomodoro", cat: "basi", supp: 1, all: [] },
    crema_pistacchi: { nome: "Crema di pistacchi", cat: "basi", supp: 2, all: [2] },
    vellutata_zucchine: { nome: "Vellutata di zucchine", cat: "basi", supp: 1.5, all: [] },
    crema_zucca: { nome: "Crema di zucca", cat: "basi", supp: 1.5, all: [] },
    crema_funghi: { nome: "Crema di funghi champignon", cat: "basi", supp: 1.5, all: [] },
    panna: { nome: "Panna", cat: "basi", supp: 1, all: [3] },
    fonduta: { nome: "Fonduta di Parmigiano", cat: "basi", supp: 1.5, all: [3] },
    cornicione_ricotta: { nome: "Cornicione di ricotta", cat: "basi", supp: 2, all: [3] },
    fiordilatte: { nome: "Fior di latte", cat: "formaggi", supp: 1.5, all: [3] },
    bufala: { nome: "Mozzarella di bufala", cat: "formaggi", supp: 2.5, all: [3] },
    stracciatella: { nome: "Stracciatella di bufala", cat: "formaggi", supp: 2.5, all: [3] },
    burrata: { nome: "Burrata al tartufo", cat: "formaggi", supp: 3, all: [3] },
    provola: { nome: "Provola", cat: "formaggi", supp: 1.5, all: [3] },
    gorgonzola: { nome: "Gorgonzola", cat: "formaggi", supp: 1.5, all: [3] },
    pecorino: { nome: "Pecorino romano", cat: "formaggi", supp: 1.5, all: [3] },
    parmigiano: { nome: "Parmigiano", cat: "formaggi", supp: 1.5, all: [3] },
    grana: { nome: "Grana Padano", cat: "formaggi", supp: 1.5, all: [3] },
    ventricina: { nome: "Ventricina piccante", cat: "salumi", supp: 2, all: [] },
    cotto: { nome: "Prosciutto cotto", cat: "salumi", supp: 2, all: [] },
    crudo: { nome: "Prosciutto crudo di Parma", cat: "salumi", supp: 2.5, all: [] },
    salsiccia: { nome: "Salsiccia di Monte San Biagio", cat: "salumi", supp: 2, all: [] },
    wurstel: { nome: "Wurstel", cat: "salumi", supp: 1.5, all: [] },
    mortadella: { nome: "Mortadella", cat: "salumi", supp: 2.5, all: [] },
    lonza: { nome: "Lonza", cat: "salumi", supp: 2.5, all: [] },
    guanciale: { nome: "Guanciale croccante", cat: "salumi", supp: 2, all: [] },
    porchetta: { nome: "Porchetta di Ariccia", cat: "salumi", supp: 2.5, all: [] },
    nduja: { nome: "'Nduja", cat: "salumi", supp: 2, all: [] },
    polpette: { nome: "Polpettine fritte", cat: "salumi", supp: 2.5, all: [9, 14] },
    alici: { nome: "Alici in filetti", cat: "pesce", supp: 2, all: [5] },
    tonno: { nome: "Tonno in filetti", cat: "pesce", supp: 2.5, all: [5] },
    funghi: { nome: "Funghi champignon", cat: "verdure", supp: 1, all: [] },
    porcini: { nome: "Funghi porcini", cat: "verdure", supp: 2.5, all: [] },
    carciofini: { nome: "Carciofini", cat: "verdure", supp: 1.5, all: [13] },
    olive: { nome: "Olive nere", cat: "verdure", supp: 1, all: [] },
    melanzane_fritte: { nome: "Melanzane fritte", cat: "verdure", supp: 1.5, all: [] },
    melanzane_funghetto: { nome: "Melanzane a funghetto", cat: "verdure", supp: 1.5, all: [] },
    zucchine: { nome: "Zucchine", cat: "verdure", supp: 1, all: [] },
    peperoni: { nome: "Peperoni", cat: "verdure", supp: 1.5, all: [] },
    fiori_zucca: { nome: "Fiori di zucca", cat: "verdure", supp: 2, all: [] },
    pachino: { nome: "Pachino rosso", cat: "verdure", supp: 1, all: [] },
    pachino_giallo: { nome: "Pachino giallo", cat: "verdure", supp: 1, all: [] },
    broccoletti: { nome: "Broccoletti", cat: "verdure", supp: 1.5, all: [] },
    patate: { nome: "Patate al forno", cat: "verdure", supp: 1.5, all: [] },
    cipolla_caramellata: { nome: "Cipolla caramellata", cat: "verdure", supp: 1, all: [] },
    rucola: { nome: "Rucola", cat: "verdure", supp: 1, all: [] },
    basilico: { nome: "Basilico", cat: "verdure", supp: 0.5, all: [] },
    patatine: { nome: "Patatine fritte", cat: "fritti", supp: 1.5, all: [] },
    crocchetta: { nome: "Crocchetta di patate", cat: "fritti", supp: 2, all: [3, 9, 14] },
    zucchine_fritte: { nome: "Zucchine fritte", cat: "fritti", supp: 1.5, all: [] },
    cipolla_croccante: { nome: "Cipolla croccante", cat: "fritti", supp: 1, all: [] },
    tarallo: { nome: "Tarallo sbriciolato", cat: "finiture", supp: 1, all: [9] },
    granella_pistacchi: { nome: "Granella di pistacchi", cat: "finiture", supp: 1.5, all: [2] },
    noci: { nome: "Noci", cat: "finiture", supp: 1, all: [2] },
    polvere_olive: { nome: "Polvere di olive nere", cat: "finiture", supp: 1, all: [] },
    pepe: { nome: "Pepe", cat: "finiture", supp: 0, all: [] },
    origano: { nome: "Origano", cat: "finiture", supp: 0, all: [] },
    aglio: { nome: "Aglio", cat: "finiture", supp: 0, all: [] }
  },
  sezioni_pizze: [
    { id: "rosse", nome: "Rosse" },
    { id: "bianche", nome: "Bianche" },
    { id: "speciali", nome: "Speciali" }
  ],
  pizze: [
    { id: "marinara", sez: "rosse", nome: "Marinara", prezzo: 6, desc: "Pomodoro, origano, aglio, olio evo.", all: [9], ing: ["pomodoro", "origano", "aglio"] },
    { id: "margherita", sez: "rosse", nome: "Margherita", prezzo: 7, desc: "Pomodoro, fior di latte, olio evo.", all: [3, 9], ing: ["pomodoro", "fiordilatte"] },
    { id: "diavola", sez: "rosse", nome: "Diavola", prezzo: 8.5, desc: "Pomodoro, fior di latte, ventricina piccante, olio evo.", all: [3, 9], ing: ["pomodoro", "fiordilatte", "ventricina"] },
    { id: "provola_pepe", sez: "rosse", nome: "Provola e pepe", prezzo: 9, desc: "Pomodoro, fior di latte, provola, pepe, olio evo.", all: [3, 9], ing: ["pomodoro", "fiordilatte", "provola", "pepe"] },
    { id: "regina", sez: "rosse", nome: "Regina", prezzo: 9, desc: "Pomodoro, mozzarella di bufala, olio evo.", all: [3, 9], ing: ["pomodoro", "bufala"] },
    { id: "napoletana", sez: "rosse", nome: "Napoletana", prezzo: 8.5, desc: "Pomodoro, fior di latte, alici in filetto, olio evo.", all: [3, 5, 9], ing: ["pomodoro", "fiordilatte", "alici"] },
    { id: "capricciosa", sez: "rosse", nome: "Capricciosa", prezzo: 10, desc: "Pomodoro, fior di latte, funghi champignon, carciofini, prosciutto cotto, olive nere, olio evo.", all: [3, 9, 13], ing: ["pomodoro", "fiordilatte", "funghi", "carciofini", "cotto", "olive"] },
    { id: "margherita_scomposta", sez: "rosse", nome: "Margherita scomposta", prezzo: 8.5, desc: "Pomodoro, stracciatella di bufala, olio evo.", all: [3, 9], ing: ["pomodoro", "stracciatella"] },
    { id: "wurstel", sez: "rosse", nome: "Wurstel", prezzo: 8, desc: "Pomodoro, fior di latte, wurstel, olio evo.", all: [3, 9], ing: ["pomodoro", "fiordilatte", "wurstel"] },
    { id: "peppino", sez: "rosse", nome: "Peppino", prezzo: 9.5, desc: "Pomodoro, fior di latte, pecorino romano, salsiccia di Monte San Biagio, olio evo.", all: [3, 9], ing: ["pomodoro", "fiordilatte", "pecorino", "salsiccia"] },
    { id: "parmigiana", sez: "rosse", nome: "Parmigiana", prezzo: 10, desc: "Pomodoro, fior di latte, provola, melanzane fritte, parmigiano, basilico, olio evo.", all: [3, 9], ing: ["pomodoro", "fiordilatte", "provola", "melanzane_fritte", "parmigiano", "basilico"] },
    { id: "crostino", sez: "bianche", nome: "Crostino", prezzo: 8, desc: "Fior di latte, prosciutto cotto, olio evo.", all: [3, 9], ing: ["fiordilatte", "cotto"] },
    { id: "boscaiola", sez: "bianche", nome: "Boscaiola", prezzo: 9.5, desc: "Fior di latte, funghi champignon, salsiccia di Monte San Biagio, olio evo.", all: [3, 9], ing: ["fiordilatte", "funghi", "salsiccia"] },
    { id: "pomodoro_colori", sez: "bianche", nome: "Pomodoro a colori", prezzo: 9.5, desc: "Fior di latte, pachino giallo, pachino rosso, olio evo.", all: [3, 9], ing: ["fiordilatte", "pachino_giallo", "pachino"] },
    { id: "parmense", sez: "bianche", nome: "Parmense", prezzo: 9, desc: "Fior di latte, prosciutto crudo di Parma, olio evo.", all: [3, 9], ing: ["fiordilatte", "crudo"] },
    { id: "peperoni_salsiccia", sez: "bianche", nome: "Peperoni e salsiccia", prezzo: 9, desc: "Fior di latte, salsiccia di Monte San Biagio, peperoni arrosto, basilico, olio evo.", all: [3, 9], ing: ["fiordilatte", "salsiccia", "peperoni", "basilico"] },
    { id: "fior_alice", sez: "bianche", nome: "Fior d'alice", prezzo: 9.5, desc: "Fior di latte, fiori di zucca, alici in filetti, olio evo.", all: [3, 5, 9], ing: ["fiordilatte", "fiori_zucca", "alici"] },
    { id: "ortolana", sez: "bianche", nome: "Ortolana", prezzo: 9.5, desc: "Fior di latte, melanzane, zucchine e peperoni ripassate in padella, olio evo.", all: [3, 9], ing: ["fiordilatte", "melanzane_funghetto", "zucchine", "peperoni"] },
    { id: "patane", sez: "bianche", nome: "Patan\xE8", prezzo: 9.5, desc: "Fior di latte, salsiccia di Monte San Biagio, patate al forno, olio evo.", all: [3, 9], ing: ["fiordilatte", "salsiccia", "patate"] },
    { id: "quattro_formaggi", sez: "bianche", nome: "Quattro formaggi", prezzo: 9.5, desc: "Fior di latte, gorgonzola, provola, pecorino romano, olio evo.", all: [3, 9], ing: ["fiordilatte", "gorgonzola", "provola", "pecorino"] },
    { id: "wurstel_patate", sez: "bianche", nome: "Wurstel e patate", prezzo: 8.5, desc: "Fior di latte, wurstel, patatine fritte.", all: [3, 9], ing: ["fiordilatte", "wurstel", "patatine"] },
    { id: "provola_pepe_gialla", sez: "bianche", nome: "Provola e pepe gialla", prezzo: 11, desc: "Fior di latte, provola, pachino giallo, alici in filetti, pepe, basilico, olio evo.", all: [3, 5, 9], ing: ["fiordilatte", "provola", "pachino_giallo", "alici", "pepe", "basilico"] },
    { id: "toto", sez: "bianche", nome: "Tot\xF2", prezzo: 11, desc: "Fior di latte, prosciutto crudo, pachino rosso, rucola, Grana Padano, olio evo.", all: [3, 9], ing: ["fiordilatte", "crudo", "pachino", "rucola", "grana"] },
    { id: "campagnola", sez: "bianche", nome: "Campagnola", prezzo: 10, desc: "Fior di latte, broccoletti, salsiccia di Monte San Biagio, olio evo.", all: [3, 9], ing: ["fiordilatte", "broccoletti", "salsiccia"] },
    { id: "primavera", sez: "bianche", nome: "Primavera", prezzo: 8.5, desc: "Fior di latte, pachino, basilico, olio evo.", all: [3, 9], ing: ["fiordilatte", "pachino", "basilico"] },
    { id: "crocche", sez: "speciali", nome: "Crocch\xE8", prezzo: 10.5, desc: "Fior di latte, panna, prosciutto cotto, crocchetta di patate fritta, olio evo.", all: [3, 9, 14], ing: ["fiordilatte", "panna", "cotto", "crocchetta"] },
    { id: "mortade", sez: "speciali", nome: "Mortad\xE8", prezzo: 10.5, desc: "Fior di latte, crema di pistacchi, mortadella, granella di pistacchi, olio evo.", all: [2, 3, 9], ing: ["fiordilatte", "crema_pistacchi", "mortadella", "granella_pistacchi"] },
    { id: "lonza_zucchine", sez: "speciali", nome: "Lonza e zucchine", prezzo: 11, desc: "Fior di latte, lonza, zucchine scapece, stracciatella di bufala, olio evo.", all: [3, 9], ing: ["fiordilatte", "lonza", "zucchine", "stracciatella"] },
    { id: "nerano", sez: "speciali", nome: "Nerano", prezzo: 10, desc: "Fior di latte, vellutata di zucchine, zucchine fritte, fonduta di Parmigiano.", all: [3, 9], ing: ["fiordilatte", "vellutata_zucchine", "zucchine_fritte", "fonduta"] },
    { id: "mortade2", sez: "speciali", nome: "Mortad\xE8 2.0", prezzo: 11, desc: "Fior di latte, mortadella, burrata al tartufo, olio evo.", all: [3, 9], ing: ["fiordilatte", "mortadella", "burrata"] },
    { id: "presidente", sez: "speciali", nome: "Il Presidente", prezzo: 11, desc: "Cornicione di ricotta, fior di latte, pachino rosso, tarallo sbriciolato, olio evo.", all: [3, 9], ing: ["cornicione_ricotta", "fiordilatte", "pachino", "tarallo"] },
    { id: "presidentessa", sez: "speciali", nome: "La Presidentessa", prezzo: 11, desc: "Fior di latte, gorgonzola, noci, guanciale, olio evo.", all: [2, 3, 9], ing: ["fiordilatte", "gorgonzola", "noci", "guanciale"] },
    { id: "zia_margherita", sez: "speciali", nome: "Zia Margherita", prezzo: 10, desc: "Cornicione di ricotta, fior di latte, pomodoro, basilico, olio evo.", all: [3, 9], ing: ["cornicione_ricotta", "fiordilatte", "pomodoro", "basilico"] },
    { id: "paesana", sez: "speciali", nome: "Paesana", prezzo: 10.5, desc: "Fior di latte, pomodoro, polpettine fritte, melanzane a funghetto, olio evo.", all: [3, 9, 14], ing: ["fiordilatte", "pomodoro", "polpette", "melanzane_funghetto"] },
    { id: "zuccona", sez: "speciali", nome: "Zuccona", prezzo: 10, desc: "Crema di zucca, fior di latte, provola, salsiccia di Monte San Biagio, basilico, olio evo.", all: [3, 9], ing: ["crema_zucca", "fiordilatte", "provola", "salsiccia", "basilico"] },
    { id: "margot", sez: "speciali", nome: "Margot", prezzo: 11, desc: "Fior di latte, zucchine fritte, polpette fritte, stracciatella di bufala.", all: [3, 9, 14], ing: ["fiordilatte", "zucchine_fritte", "polpette", "stracciatella"] },
    { id: "tonno_cipolla", sez: "speciali", nome: "Tonno e cipolla", prezzo: 11, desc: "Fior di latte, tonno in filetti, cipolla caramellata, cipolla croccante, polvere di olive nere, olio evo.", all: [3, 5, 9], ing: ["fiordilatte", "tonno", "cipolla_caramellata", "cipolla_croccante", "polvere_olive"] },
    { id: "ariccia", sez: "speciali", nome: "Ariccia", prezzo: 11, desc: "Fior di latte, porchetta di Ariccia, provola, patate al forno.", all: [3, 9], ing: ["fiordilatte", "porchetta", "provola", "patate"] },
    { id: "parmense2", sez: "speciali", nome: "Parmense 2.0", prezzo: 11, desc: "Fior di latte, prosciutto crudo di Parma, rucola, stracciatella di bufala, olio evo.", all: [3, 9], ing: ["fiordilatte", "crudo", "rucola", "stracciatella"] },
    { id: "vulcano", sez: "speciali", nome: "Vulcano", prezzo: 10.5, desc: "Pomodoro, fior di latte, 'nduja, ventricina piccante, basilico, olio evo.", all: [3, 9], ing: ["pomodoro", "fiordilatte", "nduja", "ventricina", "basilico"] },
    { id: "tarantella", sez: "speciali", nome: "Tarantella", prezzo: 11.5, desc: "Fior di latte, funghi porcini, prosciutto crudo di Parma, basilico, olio evo.", all: [3, 9], ing: ["fiordilatte", "porcini", "crudo", "basilico"] },
    { id: "boscaiola2", sez: "speciali", nome: "Boscaiola 2.0", prezzo: 12, desc: "Crema di funghi champignon, fior di latte, funghi porcini, salsiccia di Monte San Biagio, basilico, olio evo.", all: [3, 9], ing: ["crema_funghi", "fiordilatte", "porcini", "salsiccia", "basilico"] },
    { id: "campagnola2", sez: "speciali", nome: "Campagnola 2.0", prezzo: 12, desc: "Fior di latte, guanciale croccante, broccoletti, 'nduja, provola, basilico, olio evo.", all: [3, 9], ing: ["fiordilatte", "guanciale", "broccoletti", "nduja", "provola", "basilico"] }
  ],
  voci: [
    { sez: "Ripieni", id: "calzone", nome: "Calzone al forno", prezzo: 9.5, desc: "Fior di latte, ricotta, salame Napoli, pepe nero, basilico, olio evo.", all: [3, 9] },
    { sez: "Ripieni", id: "pizza_fritta", nome: "Pizza fritta", prezzo: 10, desc: "Fior di latte, ricotta, salame Napoli, pepe nero, olio evo.", all: [3, 9] },
    { sez: "Antipasti", id: "crudo_mozzarella", nome: "Crudo e mozzarella", prezzo: 9.5, desc: "Prosciutto crudo di Parma e mozzarella di bufala.", all: [3] },
    { sez: "Antipasti", id: "bruschetta", nome: "Bruschetta al pomodoro (2 pz)", prezzo: 4, desc: "", all: [9] },
    { sez: "Antipasti", id: "verdure_stagione", nome: "Verdure di stagione", prezzo: 7.5, desc: "", all: [] },
    { sez: "Fritti", id: "crocche_patate", nome: "Crocch\xE8 di patate", prezzo: 2, desc: "Fior di latte, patate rosse, pecorino, Grana Padano, pepe.", all: [3, 9, 14] },
    { sez: "Fritti", id: "suppli", nome: "Suppl\xEC", prezzo: 2, desc: "Riso, pomodoro, fior di latte.", all: [3, 9, 14] },
    { sez: "Fritti", id: "fiori_pastellati", nome: "Fiori di zucca pastellati", prezzo: 3.5, desc: "Mozzarella e alici.", all: [3, 5, 9] },
    { sez: "Fritti", id: "frittatina_classica", nome: "Frittatina classica", prezzo: 3.5, desc: "Bucatini, besciamella, rag\xF9 di manzo e piselli. Servita con crema al parmigiano.", all: [3, 9] },
    { sez: "Fritti", id: "frittatina_carbonara", nome: "Frittatina carbonara", prezzo: 3.5, desc: "Bucatini, besciamella, uova, guanciale, pecorino, pepe. Servita con crema al pecorino e guanciale.", all: [3, 9, 14] },
    { sez: "Fritti", id: "crocchetta_mortadella", nome: "Crocchetta di patate", prezzo: 3.5, desc: "Farcita con mortadella e pesto di pistacchi.", all: [2, 3, 9, 14] },
    { sez: "Fritti", id: "montanara_classica", nome: "Montanara classica (2 pz)", prezzo: 5, desc: "Impasto di pizza fritto con pomodoro, Grana Padano.", all: [3, 9] },
    { sez: "Fritti", id: "montanara_amatriciana", nome: "Montanara amatriciana (2 pz)", prezzo: 6, desc: "Impasto di pizza fritto con pomodoro, guanciale croccante, pecorino, pepe.", all: [3, 9] },
    { sez: "Fritti", id: "fritto_misto", nome: "Fritto misto", prezzo: 12, desc: "1 suppl\xEC, 1 crocchetta di patate, 1 frittatina carbonara, 1 frittatina classica, 1 montanara classica.", all: [3, 9, 14] },
    { sez: "Fritti", id: "patate_fritte", nome: "Patate fritte", prezzo: 5, desc: "", all: [] },
    { sez: "Dolci", id: "don_vito", nome: "Don Vito", prezzo: 7, desc: "Semifreddo alla vaniglia bianca del Madagascar con inserto di lamponi e copertura di cioccolato di Modica.", all: [1, 3, 6] },
    { sez: "Dolci", id: "delizia_limone", nome: "Delizia al limone", prezzo: 7, desc: "Semifreddo al limone di Amalfi con cuore di lemon curd e copertura con glassa al limone.", all: [1, 3] },
    { sez: "Dolci", id: "imperiale", nome: "Imperiale", prezzo: 7, desc: "Semifreddo ai tre cioccolati con crumble al cacao.", all: [1, 3, 6, 7] },
    { sez: "Dolci", id: "mr_duplo", nome: "Mr. Duplo", prezzo: 7, desc: "Semifreddo alla gianduia con cuore Nutella croccante e copertura alla nocciola e granella di nocciole IGP.", all: [1, 3, 5, 6] },
    { sez: "Dolci", id: "tiramisu", nome: "Tiramis\xF9", prezzo: 7, desc: "Mascarpone, tuorli d'uovo, zucchero, Pavesini, caff\xE8, latte, cacao dolce in polvere.", all: [1, 3, 7] },
    { sez: "Dolci", id: "dubai", nome: "Dubai chocolate", prezzo: 7, desc: "Semifreddo al cioccolato, con cuore morbido al variegato dubai chocolate, copertura al cioccolato al latte, base di biscotto al cacao.", all: [3, 9, 10] },
    { sez: "Birre alla spina", id: "raffo", nome: "Raffo Grezza 0,5 l", prezzo: 6, desc: "Italia \xB7 Lager \xB7 4,8% vol.", all: [] },
    { sez: "Birre alla spina", id: "nastro_piccola", nome: "Nastro Azzurro 0,2 l", prezzo: 3.5, desc: "Italia \xB7 Lager \xB7 5,1% vol.", all: [] },
    { sez: "Birre alla spina", id: "nastro_media", nome: "Nastro Azzurro 0,4 l", prezzo: 6, desc: "Italia \xB7 Lager \xB7 5,1% vol.", all: [] },
    { sez: "Birre alla spina", id: "peroni_rossa", nome: "Peroni Gran Riserva Rossa 33 cl", prezzo: 6, desc: "Italia \xB7 Vienna Style \xB7 5,2% vol.", all: [] },
    { sez: "Vini bianchi", id: "pinot_grigio", nome: "Roeno Pinot Grigio Rivoli", prezzo: 18, desc: "Roeno \xB7 13,5% vol. \xB7 100% Pinot grigio", all: [] },
    { sez: "Vini bianchi", id: "ribolla", nome: "Ronco dei Tassi Ribolla Gialla", prezzo: 22, desc: "Ronco dei Tassi \xB7 14% vol. \xB7 100% Ribolla Gialla", all: [] },
    { sez: "Vini bianchi", id: "pecorino_igt", nome: "Spinelli Serranella Pecorino IGT Bio", prezzo: 18, desc: "Cantine Spinelli \xB7 12% vol. \xB7 100% Pecorino", all: [] },
    { sez: "Vini bianchi", id: "vermentino", nome: "Mancini Vermentino di Gallura Saraina", prezzo: 18, desc: "Dalle Vigne \xB7 13% vol. \xB7 100% Vermentino di Gallura", all: [] },
    { sez: "Vini rossi", id: "merlot", nome: "Gaffino Lazio Merlot Tubbo", prezzo: 18, desc: "Gaffino Gabriele \xB7 12,5% vol. \xB7 100% Merlot", all: [] },
    { sez: "Vini rossi", id: "primitivo", nome: "A Mano Primitivo", prezzo: 18, desc: "A Mano \xB7 14% vol. \xB7 100% Primitivo", all: [] },
    { sez: "Vini rossi", id: "valpolicella", nome: "Ca' Rugate Valpolicella Rio Albo", prezzo: 24, desc: "12,5% vol. \xB7 45% Corvina, 40% Corvinone, 15% Rondinella", all: [] },
    { sez: "Vini rossi", id: "bolgheri", nome: "Bolgheri Rosso Zizzolo", prezzo: 22, desc: "Forcelle Az. A. \xB7 13,5% vol. \xB7 60% Merlot, 40% Cabernet Sauvignon", all: [] },
    { sez: "Vini rossi", id: "montepulciano", nome: "Serranella Montepulciano d'Abruzzo Bio", prezzo: 18, desc: "Cantine Spinelli \xB7 13% vol. \xB7 90% Montepulciano, 10% Sangiovese", all: [] },
    { sez: "Bollicine e champagne", id: "champagne", nome: "Louis Constant Champagne Brut Reserve", prezzo: 45, desc: "12% vol. \xB7 40% Pinot Meunier, 30% Pinot Nero, 30% Chardonnay", all: [] },
    { sez: "Bollicine e champagne", id: "valbon", nome: "Valbon Prosecco DOC Treviso Brut", prezzo: 15, desc: "Follador \xB7 11% vol. \xB7 100% Glera", all: [] },
    { sez: "Bollicine e champagne", id: "franciacorta", nome: "Franciacorta Brut", prezzo: 30, desc: "San Cristoforo \xB7 13% vol. \xB7 100% Chardonnay", all: [] },
    { sez: "Al calice", id: "chardonnay_calice", nome: "Pietra Pinta Chardonnay Lazio", prezzo: 5, desc: "100% Chardonnay \xB7 14% vol.", all: [] },
    { sez: "Al calice", id: "shiraz_calice", nome: "Shiraz Pietra Pinta", prezzo: 5, desc: "100% Shiraz \xB7 13,5% vol.", all: [] },
    { sez: "Al calice", id: "prosecco_calice", nome: "Prosecco", prezzo: 5, desc: "", all: [] },
    { sez: "Al calice", id: "aperol", nome: "Aperol Spritz", prezzo: 7, desc: "", all: [] },
    { sez: "Al calice", id: "campari", nome: "Campari Spritz", prezzo: 7, desc: "", all: [] },
    { sez: "Al calice", id: "gin", nome: "Gin tonic / Gin lemon", prezzo: 7, desc: "", all: [] },
    { sez: "Analcolici", id: "electa", nome: "Acqua Electa 0,75 l", prezzo: 2.5, desc: "", all: [] },
    { sez: "Analcolici", id: "ferrarelle", nome: "Acqua Ferrarelle 0,75 l", prezzo: 2.5, desc: "", all: [] },
    { sez: "Analcolici", id: "coca", nome: "Coca-Cola 0,33 l", prezzo: 3.5, desc: "In vetro", all: [] },
    { sez: "Analcolici", id: "coca_zero", nome: "Coca-Cola Zero 0,33 l", prezzo: 3.5, desc: "In vetro", all: [] },
    { sez: "Analcolici", id: "coca_zero_dec", nome: "Coca-Cola Zero Caffeina 0,33 l", prezzo: 3.5, desc: "In vetro", all: [] },
    { sez: "Analcolici", id: "fanta", nome: "Fanta 0,33 l", prezzo: 3.5, desc: "In vetro", all: [] },
    { sez: "Analcolici", id: "sprite", nome: "Sprite 0,33 l", prezzo: 3.5, desc: "In vetro", all: [] },
    { sez: "Amari e caff\xE8", id: "jefferson", nome: "Jefferson", prezzo: 5, desc: "", all: [] },
    { sez: "Amari e caff\xE8", id: "amaro_capo", nome: "Amaro del Capo", prezzo: 4, desc: "", all: [] },
    { sez: "Amari e caff\xE8", id: "fernet", nome: "Fernet Branca", prezzo: 4, desc: "", all: [] },
    { sez: "Amari e caff\xE8", id: "branca_menta", nome: "Branca Menta", prezzo: 4, desc: "", all: [] },
    { sez: "Amari e caff\xE8", id: "jager", nome: "J\xE4germeister", prezzo: 4, desc: "", all: [] },
    { sez: "Amari e caff\xE8", id: "montenegro", nome: "Montenegro", prezzo: 4, desc: "", all: [] },
    { sez: "Amari e caff\xE8", id: "sambuca", nome: "Sambuca", prezzo: 4, desc: "", all: [] },
    { sez: "Amari e caff\xE8", id: "liquorice", nome: "Liquorice", prezzo: 5, desc: "", all: [] },
    { sez: "Amari e caff\xE8", id: "baileys", nome: "Baileys", prezzo: 5, desc: "", all: [] },
    { sez: "Amari e caff\xE8", id: "grappa", nome: "Grappa 903", prezzo: 4, desc: "", all: [] },
    { sez: "Amari e caff\xE8", id: "limoncello", nome: "Limoncello di Capri", prezzo: 4, desc: "", all: [] },
    { sez: "Amari e caff\xE8", id: "caffe", nome: "Caff\xE8", prezzo: 2, desc: "", all: [] }
  ]
};

// worker/pizza.js
var ORIGINI2 = /^https:\/\/([a-z0-9-]+\.)*(visiorender\.it|visiorender\.pages\.dev|workers\.dev)$|^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/;
var STATI = ["nuovo", "forno", "pronto", "servito"];
var MAX_ORDINI = 2e4;
var ORDINE_ING = Object.keys(listino_default.ingredienti);
var SEZIONI = listino_default.sezioni_pizze.map((s) => s.id);
var r2 = /* @__PURE__ */ __name((v) => Math.round(v * 100) / 100, "r2");
var json2 = /* @__PURE__ */ __name((dati, stato = 200) => new Response(JSON.stringify(dati), {
  status: stato,
  headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" }
}), "json");
var errore = /* @__PURE__ */ __name((msg, stato = 400) => json2({ ok: false, errore: msg }, stato), "errore");
var testo = /* @__PURE__ */ __name((v, max) => String(v == null ? "" : v).replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, max), "testo");
var listaIng = /* @__PURE__ */ __name((a) => Array.isArray(a) ? ORDINE_ING.filter((i) => a.includes(i)) : [], "listaIng");
var prezzo = /* @__PURE__ */ __name((v, d) => {
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 && n <= 500 ? r2(n) : d;
}, "prezzo");
var tavoloValido = /* @__PURE__ */ __name((t) => {
  const n = Math.floor(Number(t));
  return n >= 1 && n <= 60 ? n : 0;
}, "tavoloValido");
var eur = /* @__PURE__ */ __name((v) => v.toLocaleString("it-IT", { style: "currency", currency: "EUR" }), "eur");
var escH = /* @__PURE__ */ __name((s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]), "escH");
function breveDa(ING, id) {
  const n = ING[id].nome, w = n.split(" ");
  return w.length > 1 && /^[A-Z]/.test(w[1]) ? n : n.charAt(0).toLowerCase() + n.slice(1);
}
__name(breveDa, "breveDa");
function allergeni(ing) {
  const s = /* @__PURE__ */ new Set([9]);
  ing.forEach((i) => (listino_default.ingredienti[i] ? listino_default.ingredienti[i].all : []).forEach((a) => s.add(a)));
  return [...s].sort((a, b) => a - b);
}
__name(allergeni, "allergeni");
function descrizione(ing) {
  const s = ing.map((i) => breveDa(listino_default.ingredienti, i)).join(", ");
  return s ? s.charAt(0).toUpperCase() + s.slice(1) + ", olio evo." : "";
}
__name(descrizione, "descrizione");
function menuUnito(ov) {
  ov = ov || {};
  const prezzi = ov.prezzi || {}, supp = ov.supp || {}, nascoste = new Set(ov.nascoste || []);
  const ingredienti = {};
  for (const [id, i] of Object.entries(listino_default.ingredienti)) ingredienti[id] = { ...i, supp: prezzo(supp[id], i.supp) };
  const pizze = listino_default.pizze.filter((p) => !nascoste.has(p.id)).map((p) => ({ ...p, prezzo: prezzo(prezzi[p.id], p.prezzo) }));
  for (const p of ov.nuove || []) pizze.push({ ...p, all: allergeni(p.ing), desc: descrizione(p.ing), nuova: true });
  const voci = listino_default.voci.filter((v) => !nascoste.has(v.id)).map((v) => ({ ...v, prezzo: prezzo(prezzi[v.id], v.prezzo) }));
  const ev = ov.evidenza && pizze.some((p) => p.id === ov.evidenza.id) ? { id: ov.evidenza.id, nota: ov.evidenza.nota || "" } : null;
  return { ...listino_default, ingredienti, pizze, voci, coperto: prezzo(ov.coperto, listino_default.coperto), evidenza: ev, nascoste: [...nascoste] };
}
__name(menuUnito, "menuUnito");
function indici(M) {
  return { M, ING: M.ingredienti, PIZZE: M.pizze, PIZ: Object.fromEntries(M.pizze.map((p) => [p.id, p])), VOC: Object.fromEntries(M.voci.map((v) => [v.id, v])) };
}
__name(indici, "indici");
function pulisciMenu(b) {
  const idPizze = new Set(listino_default.pizze.map((p) => p.id)), idVoci = new Set(listino_default.voci.map((v) => v.id));
  const out = { prezzi: {}, supp: {}, nascoste: [], nuove: [], evidenza: null, coperto: null };
  for (const [id, v] of Object.entries(b.prezzi || {})) if ((idPizze.has(id) || idVoci.has(id)) && prezzo(v, null) != null) out.prezzi[id] = prezzo(v, null);
  for (const [id, v] of Object.entries(b.supp || {})) if (listino_default.ingredienti[id] && prezzo(v, null) != null) out.supp[id] = prezzo(v, null);
  out.nascoste = [...new Set((b.nascoste || []).filter((id) => idPizze.has(id) || idVoci.has(id)))];
  for (const p of (Array.isArray(b.nuove) ? b.nuove : []).slice(0, 20)) {
    const nome = testo(p && p.nome, 40), ing = listaIng(p && p.ing), pr = prezzo(p && p.prezzo, null);
    if (!nome || !ing.length || pr == null) continue;
    const id = /^n_[a-z0-9]{4,12}$/.test(p.id) ? p.id : "n_" + crypto.randomUUID().replace(/-/g, "").slice(0, 8);
    out.nuove.push({ id, sez: SEZIONI.includes(p.sez) ? p.sez : "speciali", nome, prezzo: pr, ing });
  }
  if (b.evidenza && b.evidenza.id) out.evidenza = { id: testo(b.evidenza.id, 40), nota: testo(b.evidenza.nota, 140) };
  if (b.coperto != null) out.coperto = prezzo(b.coperto, null);
  return out;
}
__name(pulisciMenu, "pulisciMenu");
function riga(r, X) {
  if (!r || typeof r !== "object") return null;
  const qty = Math.floor(Number(r.qty));
  if (!(qty >= 1 && qty <= 20)) return null;
  if (r.tipo === "voce") {
    const v = X.VOC[r.id];
    return v ? { tipo: "voce", id: v.id, nome: v.nome, sez: v.sez, prezzo: v.prezzo, qty } : null;
  }
  const da = X.PIZ[r.da];
  if (!da) return null;
  const ing = listaIng(r.ing), set = new Set(ing);
  const base = X.PIZZE.find((p) => p.ing.length === set.size && p.ing.every((i) => set.has(i))) || da;
  const add = ing.filter((i) => !base.ing.includes(i)), rem = base.ing.filter((i) => !set.has(i));
  const b = /* @__PURE__ */ __name((id) => breveDa(X.ING, id), "b");
  let nome = base.nome;
  if (add.length > 3) nome += " + " + add.length + " ingredienti";
  else if (add.length) nome += " + " + add.map(b).join(", ");
  if (rem.length > 2) nome += " senza " + rem.length + " ingredienti";
  else if (rem.length) nome += " senza " + rem.map(b).join(", ");
  const pr = r2(base.prezzo + add.reduce((t, i) => t + (X.ING[i].supp || 0), 0));
  return { tipo: "pizza", da: base.id, nome, add, rem, ing, prezzo: pr, qty };
}
__name(riga, "riga");
var pizzeIn = /* @__PURE__ */ __name((o) => (o.righe || []).filter((r) => r.tipo !== "voce").reduce((t, r) => t + (r.qty || 1), 0), "pizzeIn");
var mediana = /* @__PURE__ */ __name((a) => {
  const s = [...a].sort((x, y) => x - y);
  return s.length ? s[Math.floor(s.length / 2)] : 0;
}, "mediana");
var Pizzeria = class extends DurableObject {
  static {
    __name(this, "Pizzeria");
  }
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS ordini (id TEXT PRIMARY KEY, tavolo INTEGER, dati TEXT, rev INTEGER);
      CREATE INDEX IF NOT EXISTS ordini_rev ON ordini(rev);
      CREATE TABLE IF NOT EXISTS chiamate (id TEXT PRIMARY KEY, tavolo INTEGER, dati TEXT, rev INTEGER, aperta INTEGER);
      CREATE INDEX IF NOT EXISTS chiamate_rev ON chiamate(rev);
      CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);`);
  }
  leggi(k, def) {
    const r = this.sql.exec("SELECT v FROM kv WHERE k = ?", k).toArray()[0];
    return r ? JSON.parse(r.v) : def;
  }
  scrivi(k, v) {
    this.sql.exec("INSERT INTO kv (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v", k, JSON.stringify(v));
  }
  togli(k) {
    this.sql.exec("DELETE FROM kv WHERE k = ?", k);
  }
  prossimaRev() {
    const n = this.leggi("rev", 0) + 1;
    this.scrivi("rev", n);
    return n;
  }
  impostazioni() {
    return { coperti: "cliente", email: "", ...this.leggi("impostazioni", {}) };
  }
  menu() {
    return menuUnito(this.leggi("menu", {}));
  }
  config(staff) {
    const imp = this.impostazioni();
    return { tavoli: this.leggi("tavoli", 12), esauriti: this.leggi("esauriti", []), menuRev: this.leggi("menuRev", 0), coperti: imp.coperti, ...staff ? { email: imp.email } : {} };
  }
  sessioni(tavolo) {
    const out = {};
    const righe = tavolo ? this.sql.exec("SELECT k, v FROM kv WHERE k = ?", "tav:" + tavolo).toArray() : this.sql.exec("SELECT k, v FROM kv WHERE k LIKE 'tav:%'").toArray();
    for (const r of righe) out[r.k.slice(4)] = JSON.parse(r.v);
    return out;
  }
  salvaOrdine(o) {
    this.sql.exec("INSERT INTO ordini (id, tavolo, dati, rev) VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET dati = excluded.dati, rev = excluded.rev", o.id, o.tavolo, JSON.stringify(o), this.prossimaRev());
  }
  salvaChiamata(c) {
    this.sql.exec("INSERT INTO chiamate (id, tavolo, dati, rev, aperta) VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET dati = excluded.dati, rev = excluded.rev, aperta = excluded.aperta", c.id, c.tavolo, JSON.stringify(c), this.prossimaRev(), c.gestita ? 0 : 1);
  }
  ordine(id) {
    const r = this.sql.exec("SELECT dati FROM ordini WHERE id = ?", String(id)).toArray()[0];
    return r ? JSON.parse(r.dati) : null;
  }
  recenti(n) {
    return this.sql.exec("SELECT dati FROM ordini ORDER BY rev DESC LIMIT ?", n).toArray().map((r) => JSON.parse(r.dati));
  }
  // Stima per il cliente: tempo tipico della cucina (mediana degli ultimi ordini arrivati a «pronto»)
  // piu' le pizze ancora da infornare arrivate prima, meno il tempo gia' passato.
  attesa(tavolo) {
    const rec = this.recenti(400);
    const aperti = rec.filter((o) => !o.chiuso && (o.stato === "nuovo" || o.stato === "forno"));
    const mie = aperti.filter((o) => o.tavolo === tavolo);
    if (!mie.length) return null;
    const fatti = rec.filter((o) => o.pronto > o.creato).slice(0, 30).map((o) => (o.pronto - o.creato) / 6e4);
    const tipico = Math.min(35, Math.max(6, fatti.length >= 3 ? mediana(fatti) : 12));
    const primo = Math.min(...mie.map((o) => o.creato));
    const davanti = aperti.filter((o) => o.tavolo !== tavolo && o.stato === "nuovo" && o.creato < primo).reduce((t, o) => t + pizzeIn(o), 0);
    let resto = tipico + davanti * 0.75 - (Date.now() - primo) / 6e4;
    if (mie.every((o) => o.stato === "forno")) resto = Math.min(resto, 4);
    resto = Math.max(2, resto);
    return { min: Math.round(resto), max: Math.round(resto * 1.25 + 2), davanti };
  }
  riepilogoDati() {
    const X = indici(this.menu());
    const da = Date.now() - 20 * 36e5;
    const os = this.recenti(3e3).filter((o) => o.creato >= da);
    const byP = /* @__PURE__ */ new Map(), add = /* @__PURE__ */ new Map(), voci = /* @__PURE__ */ new Map(), tav = /* @__PURE__ */ new Set();
    let inc = 0, pz = 0;
    const prep = [];
    for (const o of os) {
      inc += o.totale || 0;
      tav.add(o.tavolo);
      if (o.pronto > o.creato) prep.push((o.pronto - o.creato) / 6e4);
      for (const r of o.righe || []) {
        if (r.tipo === "voce") {
          voci.set(r.nome, (voci.get(r.nome) || 0) + r.qty);
          continue;
        }
        pz += r.qty;
        const n = X.PIZ[r.da] ? X.PIZ[r.da].nome : r.nome;
        byP.set(n, (byP.get(n) || 0) + r.qty);
        (r.add || []).forEach((i) => {
          if (X.ING[i]) add.set(X.ING[i].nome, (add.get(X.ING[i].nome) || 0) + r.qty);
        });
      }
    }
    const top = /* @__PURE__ */ __name((m, k) => [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, k), "top");
    const mai = X.PIZZE.filter((p) => !byP.has(p.nome)).map((p) => p.nome);
    const es = this.leggi("esauriti", []).map((id) => X.ING[id] ? X.ING[id].nome : X.VOC[id] ? X.VOC[id].nome : id);
    return { n: os.length, inc: r2(inc), pz, tavoli: tav.size, prep: prep.length ? Math.round(mediana(prep)) : null, pizze: top(byP, 8), aggiunte: top(add, 5), voci: top(voci, 6), mai, esauriti: es, locale: X.M.locale };
  }
  async inviaRiepilogo(manuale) {
    const imp = this.impostazioni();
    if (!imp.email) return { ok: false, errore: "manca l'indirizzo email" };
    if (!this.env.RESEND_API_KEY) return { ok: false, errore: "invio email non configurato" };
    const R = this.riepilogoDati();
    if (!R.n && !manuale) return { ok: true, saltato: "nessun ordine" };
    const giorno = (/* @__PURE__ */ new Date()).toLocaleDateString("it-IT", { timeZone: "Europe/Rome", weekday: "long", day: "numeric", month: "long" });
    const lista = /* @__PURE__ */ __name((a) => a.length ? "<ul>" + a.map(([k, v]) => `<li>${escH(k)}: <b>${v}</b></li>`).join("") + "</ul>" : "<p>\u2014</p>", "lista");
    const html = `<div style="font-family:Arial,sans-serif;font-size:15px;color:#121A44;max-width:560px">
      <h2 style="margin:0 0 4px">Riepilogo della serata</h2><p style="margin:0 0 16px;color:#566089">${escH(R.locale || "")} \xB7 ${escH(giorno)} (ultime 20 ore)</p>
      <p>Incasso dagli ordini: <b>${eur(R.inc)}</b> (coperti esclusi)<br>Ordini: <b>${R.n}</b> \xB7 Pizze: <b>${R.pz}</b> \xB7 Tavoli serviti: <b>${R.tavoli}</b>${R.prep != null ? `<br>Tempo tipico in cucina: <b>${R.prep} min</b>` : ""}</p>
      <h3>Pizze pi\xF9 ordinate</h3>${lista(R.pizze)}
      <h3>Aggiunte pi\xF9 richieste</h3>${lista(R.aggiunte)}
      <h3>Dal resto del menu</h3>${lista(R.voci)}
      <h3>Mai ordinate stasera</h3><p>${R.mai.length ? escH(R.mai.join(", ")) : "Nessuna: tutte ordinate almeno una volta."}</p>
      <h3>Segnati come esauriti</h3><p>${R.esauriti.length ? escH(R.esauriti.join(", ")) : "Niente."}</p>
      <p style="color:#566089;font-size:13px">Dettagli e grafici nella gestione, scheda Analisi.</p></div>`;
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: "Bearer " + this.env.RESEND_API_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ from: this.env.PIZZA_MAIL_FROM || this.env.MAIL_FROM || "Pizza su Misura <sito@visiorender.it>", to: [imp.email], subject: `Riepilogo serata: ${eur(R.inc)}, ${R.pz} pizze`, html })
    });
    return r.ok ? { ok: true, inviato: imp.email } : { ok: false, errore: "il servizio email ha rifiutato l'invio (" + r.status + ")" };
  }
  async fetch(request) {
    const url = new URL(request.url);
    const via = url.pathname.replace(/^\/+/, "");
    if (via === "interno/riepilogo") return json2(await this.inviaRiepilogo(false));
    if (request.method === "GET" && via === "menu") return json2({ ok: true, menu: this.menu(), menuRev: this.leggi("menuRev", 0) });
    const staff = via.startsWith("staff/") || via === "stato" && !url.searchParams.get("tavolo");
    if (staff && this.env.PIZZA_PIN && request.headers.get("X-Pin") !== this.env.PIZZA_PIN) return errore("PIN richiesto", 401);
    if (request.method === "GET" && via === "stato") {
      const rev = Math.max(0, Math.floor(Number(url.searchParams.get("rev")) || 0));
      const tavolo = tavoloValido(url.searchParams.get("tavolo"));
      const filtro = tavolo ? " AND tavolo = " + tavolo : "";
      const ordini = this.sql.exec(`SELECT dati FROM ordini WHERE rev > ?${filtro} ORDER BY rev LIMIT 3000`, rev).toArray().map((r) => JSON.parse(r.dati));
      const chiamate = this.sql.exec(`SELECT dati FROM chiamate WHERE rev > ?${filtro} ORDER BY rev LIMIT 500`, rev).toArray().map((r) => JSON.parse(r.dati));
      const out = { ok: true, rev: this.leggi("rev", 0), ordini, chiamate, config: this.config(!tavolo), sessioni: this.sessioni(tavolo) };
      if (tavolo) out.attesa = this.attesa(tavolo);
      return json2(out);
    }
    if (request.method !== "POST") return errore("metodo non ammesso", 405);
    const corpo = await request.text();
    if (corpo.length > 65536) return errore("richiesta troppo grande", 413);
    let b;
    try {
      b = JSON.parse(corpo);
    } catch {
      return errore("richiesta non valida");
    }
    if (!b || typeof b !== "object") return errore("richiesta non valida");
    const ora = Date.now();
    if (via === "ordini") {
      const tavolo = tavoloValido(b.tavolo);
      if (!tavolo) return errore("tavolo non valido");
      const X = indici(this.menu());
      const righe = (Array.isArray(b.righe) ? b.righe.slice(0, 40) : []).map((r) => riga(r, X));
      if (!righe.length || righe.some((r) => !r)) return errore("ordine non valido");
      const esauriti = new Set(this.leggi("esauriti", []));
      const finiti = [...new Set(righe.flatMap((r) => r.tipo === "voce" ? esauriti.has(r.id) ? [r.id] : [] : r.ing.filter((i) => esauriti.has(i))))];
      if (finiti.length) return json2({ ok: false, errore: "ingrediente finito", finiti }, 409);
      const n = this.sql.exec("SELECT COUNT(*) AS n FROM ordini").toArray()[0].n;
      if (n >= MAX_ORDINI) return errore("archivio pieno", 507);
      const o = {
        id: crypto.randomUUID().slice(0, 12),
        tavolo,
        righe,
        nota: testo(b.nota, 300),
        dev: testo(b.dev, 12) || null,
        cameriere: b.cameriere === true,
        totale: r2(righe.reduce((t, r) => t + r.prezzo * r.qty, 0)),
        stato: "nuovo",
        creato: ora,
        chiuso: false
      };
      const cop = Math.floor(Number(b.coperti));
      const modo = this.impostazioni().coperti;
      if (cop >= 1 && cop <= 40 && (modo === "cliente" || o.cameriere && modo !== "no") && !this.leggi("tav:" + tavolo, null)) this.scrivi("tav:" + tavolo, { coperti: cop, da: o.cameriere ? "cameriere" : "cliente" });
      this.salvaOrdine(o);
      return json2({ ok: true, id: o.id, totale: o.totale });
    }
    if (via === "chiamate") {
      const tavolo = tavoloValido(b.tavolo);
      const tipo = b.tipo === "conto" ? "conto" : b.tipo === "cameriere" ? "cameriere" : "";
      if (!tavolo || !tipo) return errore("richiesta non valida");
      const gia = this.sql.exec("SELECT dati FROM chiamate WHERE aperta = 1 AND tavolo = ?", tavolo).toArray().map((r) => JSON.parse(r.dati)).find((c2) => c2.tipo === tipo);
      if (gia) return json2({ ok: true, id: gia.id });
      const c = { id: crypto.randomUUID().slice(0, 12), tavolo, tipo, creato: ora, gestita: false };
      this.salvaChiamata(c);
      return json2({ ok: true, id: c.id });
    }
    if (via === "staff/stato") {
      if (!STATI.includes(b.stato)) return errore("stato non valido");
      const ids = (Array.isArray(b.ids) ? b.ids : [b.id]).map(String).slice(0, 60);
      let n = 0;
      for (const id of ids) {
        const o = this.ordine(id);
        if (!o) continue;
        o.stato = b.stato;
        if (b.stato === "forno" || b.stato === "pronto") o[b.stato] = ora;
        if (b.stato === "servito") o.servito = ora;
        this.salvaOrdine(o);
        n++;
      }
      return n ? json2({ ok: true, aggiornati: n }) : errore("ordine non trovato", 404);
    }
    if (via === "staff/chiamata") {
      const r = this.sql.exec("SELECT dati FROM chiamate WHERE id = ?", String(b.id)).toArray()[0];
      if (!r) return errore("chiamata non trovata", 404);
      const c = JSON.parse(r.dati);
      c.gestita = true;
      c.gestitaAlle = ora;
      this.salvaChiamata(c);
      return json2({ ok: true });
    }
    if (via === "staff/coperti") {
      const tavolo = tavoloValido(b.tavolo), n = Math.floor(Number(b.coperti));
      if (!tavolo || !(n >= 0 && n <= 40)) return errore("richiesta non valida");
      if (n) this.scrivi("tav:" + tavolo, { coperti: n, da: "cameriere" });
      else this.togli("tav:" + tavolo);
      this.prossimaRev();
      return json2({ ok: true });
    }
    if (via === "staff/chiudi") {
      const tavolo = tavoloValido(b.tavolo);
      if (!tavolo) return errore("tavolo non valido");
      const sess = this.leggi("tav:" + tavolo, null);
      for (const r of this.sql.exec("SELECT dati FROM ordini WHERE tavolo = ?", tavolo).toArray()) {
        const o = JSON.parse(r.dati);
        if (!o.chiuso) {
          o.chiuso = true;
          o.chiusoAlle = ora;
          if (sess) o.coperti = sess.coperti;
          this.salvaOrdine(o);
        }
      }
      for (const r of this.sql.exec("SELECT dati FROM chiamate WHERE aperta = 1 AND tavolo = ?", tavolo).toArray()) {
        const c = JSON.parse(r.dati);
        c.gestita = true;
        c.gestitaAlle = ora;
        this.salvaChiamata(c);
      }
      this.togli("tav:" + tavolo);
      return json2({ ok: true });
    }
    if (via === "staff/config") {
      if (b.tavoli != null) {
        const n = tavoloValido(b.tavoli);
        if (!n) return errore("numero di tavoli non valido");
        this.scrivi("tavoli", n);
      }
      if (b.esauriti != null) {
        const ok = /* @__PURE__ */ new Set([...ORDINE_ING, ...listino_default.voci.map((v) => v.id)]);
        this.scrivi("esauriti", Array.isArray(b.esauriti) ? [...new Set(b.esauriti.filter((i) => ok.has(i)))].slice(0, 200) : []);
      }
      if (b.coperti != null || b.email != null) {
        const imp = this.impostazioni();
        if (["cliente", "cameriere", "no"].includes(b.coperti)) imp.coperti = b.coperti;
        if (b.email != null) {
          const e = testo(b.email, 120);
          if (e && !/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(e)) return errore("indirizzo email non valido");
          imp.email = e;
        }
        this.scrivi("impostazioni", imp);
      }
      this.prossimaRev();
      return json2({ ok: true, config: this.config(true) });
    }
    if (via === "staff/menu") {
      this.scrivi("menu", pulisciMenu(b));
      this.scrivi("menuRev", this.leggi("menuRev", 0) + 1);
      this.prossimaRev();
      return json2({ ok: true, menu: this.menu() });
    }
    if (via === "staff/riepilogo") return json2(await this.inviaRiepilogo(true));
    return errore("non trovato", 404);
  }
};
var stub = /* @__PURE__ */ __name((env) => env.PIZZERIA.get(env.PIZZERIA.idFromName("demo")), "stub");
async function gestisciPizza(request, env) {
  if (!env.PIZZERIA) return errore("servizio non configurato", 503);
  const url = new URL(request.url);
  const via = url.pathname.slice("/api/pizza".length);
  if (via.startsWith("/interno/")) return errore("non trovato", 404);
  if (request.method === "POST") {
    const origine = request.headers.get("Origin") || "";
    if (!origine || !ORIGINI2.test(origine)) return errore("provenienza non ammessa", 403);
  }
  return stub(env).fetch(new Request("https://pizzeria" + via + url.search, request));
}
__name(gestisciPizza, "gestisciPizza");
async function riepilogoSerale(env) {
  if (!env.PIZZERIA) return;
  await stub(env).fetch("https://pizzeria/interno/riepilogo", { method: "POST" });
}
__name(riepilogoSerale, "riepilogoSerale");

// worker/index.js
var json3 = /* @__PURE__ */ __name((dati, stato) => new Response(JSON.stringify(dati), {
  status: stato,
  headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" }
}), "json");
var worker_default = {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === "/api/modulo") {
      if (request.method !== "POST") return json3({ ok: false, errore: "usa POST" }, 405);
      return inviaModulo(request, env);
    }
    if (pathname.startsWith("/api/pizza/")) return gestisciPizza(request, env);
    if (pathname.startsWith("/api/")) return json3({ ok: false, errore: "non trovato" }, 404);
    return env.ASSETS.fetch(request);
  },
  // cron di wrangler.jsonc: riepilogo serale della demo pizzeria via email (se l'indirizzo e' impostato)
  async scheduled(event, env, ctx) {
    ctx.waitUntil(riepilogoSerale(env));
  }
};

// ../../../tmp/claude-0/-home-user-visio-studio/91ffa7e7-38e9-5fc7-8070-1325995c3469/scratchpad/npmlibs/node_modules/wrangler/templates/middleware/middleware-ensure-req-body-drained.ts
var drainBody = /* @__PURE__ */ __name(async (request, env, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env);
  } finally {
    try {
      if (request.body !== null && !request.bodyUsed) {
        const reader = request.body.getReader();
        while (!(await reader.read()).done) {
        }
      }
    } catch (e) {
      console.error("Failed to drain the unused request body.", e);
    }
  }
}, "drainBody");
var middleware_ensure_req_body_drained_default = drainBody;

// ../../../tmp/claude-0/-home-user-visio-studio/91ffa7e7-38e9-5fc7-8070-1325995c3469/scratchpad/npmlibs/node_modules/wrangler/templates/middleware/middleware-miniflare3-json-error.ts
function reduceError(e) {
  return {
    name: e?.name,
    message: e?.message ?? String(e),
    stack: e?.stack,
    cause: e?.cause === void 0 ? void 0 : reduceError(e.cause)
  };
}
__name(reduceError, "reduceError");
var jsonError = /* @__PURE__ */ __name(async (request, env, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env);
  } catch (e) {
    const error = reduceError(e);
    const body = JSON.stringify(error);
    const headers = {
      "Content-Type": "application/json",
      "MF-Experimental-Error-Stack": "true"
    };
    const encoded = encodeURIComponent(body);
    if (encoded.length <= 8192) {
      headers["MF-Experimental-Error-Stack-Payload"] = encoded;
    }
    return new Response(body, { status: 500, headers });
  }
}, "jsonError");
var middleware_miniflare3_json_error_default = jsonError;

// .wrangler/tmp/bundle-VvLL22/middleware-insertion-facade.js
var __INTERNAL_WRANGLER_MIDDLEWARE__ = [
  middleware_ensure_req_body_drained_default,
  middleware_miniflare3_json_error_default
];
var middleware_insertion_facade_default = worker_default;

// ../../../tmp/claude-0/-home-user-visio-studio/91ffa7e7-38e9-5fc7-8070-1325995c3469/scratchpad/npmlibs/node_modules/wrangler/templates/middleware/common.ts
var __facade_middleware__ = [];
function __facade_register__(...args) {
  __facade_middleware__.push(...args.flat());
}
__name(__facade_register__, "__facade_register__");
function __facade_invokeChain__(request, env, ctx, dispatch, middlewareChain) {
  const [head, ...tail] = middlewareChain;
  const middlewareCtx = {
    dispatch,
    next(newRequest, newEnv) {
      return __facade_invokeChain__(newRequest, newEnv, ctx, dispatch, tail);
    }
  };
  return head(request, env, ctx, middlewareCtx);
}
__name(__facade_invokeChain__, "__facade_invokeChain__");
function __facade_invoke__(request, env, ctx, dispatch, finalMiddleware) {
  return __facade_invokeChain__(request, env, ctx, dispatch, [
    ...__facade_middleware__,
    finalMiddleware
  ]);
}
__name(__facade_invoke__, "__facade_invoke__");

// .wrangler/tmp/bundle-VvLL22/middleware-loader.entry.ts
var __Facade_ScheduledController__ = class ___Facade_ScheduledController__ {
  constructor(scheduledTime, cron, noRetry) {
    this.scheduledTime = scheduledTime;
    this.cron = cron;
    this.#noRetry = noRetry;
  }
  scheduledTime;
  cron;
  static {
    __name(this, "__Facade_ScheduledController__");
  }
  #noRetry;
  noRetry() {
    if (!(this instanceof ___Facade_ScheduledController__)) {
      throw new TypeError("Illegal invocation");
    }
    this.#noRetry();
  }
};
function wrapExportedHandler(worker) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return worker;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  const fetchDispatcher = /* @__PURE__ */ __name(function(request, env, ctx) {
    if (worker.fetch === void 0) {
      throw new Error("Handler does not export a fetch() function.");
    }
    return worker.fetch(request, env, ctx);
  }, "fetchDispatcher");
  return {
    ...worker,
    fetch(request, env, ctx) {
      const dispatcher = /* @__PURE__ */ __name(function(type, init) {
        if (type === "scheduled" && worker.scheduled !== void 0) {
          const controller = new __Facade_ScheduledController__(
            Date.now(),
            init.cron ?? "",
            () => {
            }
          );
          return worker.scheduled(controller, env, ctx);
        }
      }, "dispatcher");
      return __facade_invoke__(request, env, ctx, dispatcher, fetchDispatcher);
    }
  };
}
__name(wrapExportedHandler, "wrapExportedHandler");
function wrapWorkerEntrypoint(klass) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return klass;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  return class extends klass {
    #fetchDispatcher = /* @__PURE__ */ __name((request, env, ctx) => {
      this.env = env;
      this.ctx = ctx;
      if (super.fetch === void 0) {
        throw new Error("Entrypoint class does not define a fetch() function.");
      }
      return super.fetch(request);
    }, "#fetchDispatcher");
    #dispatcher = /* @__PURE__ */ __name((type, init) => {
      if (type === "scheduled" && super.scheduled !== void 0) {
        const controller = new __Facade_ScheduledController__(
          Date.now(),
          init.cron ?? "",
          () => {
          }
        );
        return super.scheduled(controller);
      }
    }, "#dispatcher");
    fetch(request) {
      return __facade_invoke__(
        request,
        this.env,
        this.ctx,
        this.#dispatcher,
        this.#fetchDispatcher
      );
    }
  };
}
__name(wrapWorkerEntrypoint, "wrapWorkerEntrypoint");
var WRAPPED_ENTRY;
if (typeof middleware_insertion_facade_default === "object") {
  WRAPPED_ENTRY = wrapExportedHandler(middleware_insertion_facade_default);
} else if (typeof middleware_insertion_facade_default === "function") {
  WRAPPED_ENTRY = wrapWorkerEntrypoint(middleware_insertion_facade_default);
}
var middleware_loader_entry_default = WRAPPED_ENTRY;
export {
  Pizzeria,
  __INTERNAL_WRANGLER_MIDDLEWARE__,
  middleware_loader_entry_default as default
};
//# sourceMappingURL=index.js.map

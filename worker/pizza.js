/* Demo «Pizza su Misura»: ordini dal tavolo per una pizzeria (pagina /pizza/).
   Un solo Durable Object con SQLite tiene ordini, chiamate al cameriere, coperti dei tavoli,
   modifiche al menu e impostazioni. Le pagine leggono lo stato ogni pochi secondi
   (GET /api/pizza/stato?rev=N restituisce solo gli ordini cambiati dopo la revisione N).
   Le azioni del personale (/api/pizza/staff/*) chiedono il PIN se nel Worker c'e' il
   segreto PIZZA_PIN; senza segreto sono aperte, va bene solo per la prova.
   Il menu di partenza e' pizza/listino.json; il titolare lo modifica dalla gestione
   (prezzi, pizze nascoste o nuove, pizza del giorno, coperto) e le modifiche stanno qui,
   nella chiave 'menu'. Il server ricalcola sempre i prezzi dal menu unito: il cliente non
   li puo' cambiare. Ogni notte (cron in wrangler.jsonc) manda il riepilogo della serata
   via Resend all'indirizzo scelto in gestione. */
import { DurableObject } from 'cloudflare:workers';
import LISTINO from '../pizza/listino.json';

const ORIGINI = /^https:\/\/([a-z0-9-]+\.)*(visiorender\.it|visiorender\.pages\.dev|workers\.dev)$|^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/;
const STATI = ['nuovo', 'forno', 'pronto', 'servito'];
const MAX_ORDINI = 20000;
const ORDINE_ING = Object.keys(LISTINO.ingredienti);
const SEZIONI = LISTINO.sezioni_pizze.map(s => s.id);

const r2 = v => Math.round(v * 100) / 100;
const json = (dati, stato = 200) => new Response(JSON.stringify(dati), {
  status: stato, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }
});
const errore = (msg, stato = 400) => json({ ok: false, errore: msg }, stato);
const testo = (v, max) => String(v == null ? '' : v).replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, max);
const listaIng = a => Array.isArray(a) ? ORDINE_ING.filter(i => a.includes(i)) : [];
const prezzo = (v, d) => { const n = Number(v); return Number.isFinite(n) && n >= 0 && n <= 500 ? r2(n) : d; };
const tavoloValido = t => { const n = Math.floor(Number(t)); return n >= 1 && n <= 60 ? n : 0; };
const eur = v => v.toLocaleString('it-IT', { style: 'currency', currency: 'EUR' });
const escH = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function breveDa(ING, id) { const n = ING[id].nome, w = n.split(' '); return w.length > 1 && /^[A-Z]/.test(w[1]) ? n : n.charAt(0).toLowerCase() + n.slice(1); }
function allergeni(ing) { const s = new Set([9]); ing.forEach(i => (LISTINO.ingredienti[i] ? LISTINO.ingredienti[i].all : []).forEach(a => s.add(a))); return [...s].sort((a, b) => a - b); }
function descrizione(ing) { const s = ing.map(i => breveDa(LISTINO.ingredienti, i)).join(', '); return s ? s.charAt(0).toUpperCase() + s.slice(1) + ', olio evo.' : ''; }

// Menu del listino con le modifiche del titolare sopra.
export function menuUnito(ov) {
  ov = ov || {};
  const prezzi = ov.prezzi || {}, supp = ov.supp || {}, nascoste = new Set(ov.nascoste || []);
  const ingredienti = {};
  for (const [id, i] of Object.entries(LISTINO.ingredienti)) ingredienti[id] = { ...i, supp: prezzo(supp[id], i.supp) };
  const pizze = LISTINO.pizze.filter(p => !nascoste.has(p.id)).map(p => ({ ...p, prezzo: prezzo(prezzi[p.id], p.prezzo) }));
  for (const p of ov.nuove || []) pizze.push({ ...p, all: allergeni(p.ing), desc: descrizione(p.ing), nuova: true });
  const voci = LISTINO.voci.filter(v => !nascoste.has(v.id)).map(v => ({ ...v, prezzo: prezzo(prezzi[v.id], v.prezzo) }));
  const ev = ov.evidenza && pizze.some(p => p.id === ov.evidenza.id) ? { id: ov.evidenza.id, nota: ov.evidenza.nota || '' } : null;
  return { ...LISTINO, ingredienti, pizze, voci, coperto: prezzo(ov.coperto, LISTINO.coperto), evidenza: ev, nascoste: [...nascoste] };
}
function indici(M) {
  return { M, ING: M.ingredienti, PIZZE: M.pizze, PIZ: Object.fromEntries(M.pizze.map(p => [p.id, p])), VOC: Object.fromEntries(M.voci.map(v => [v.id, v])) };
}
// Solo cio' che il titolare puo' davvero cambiare, con valori controllati.
function pulisciMenu(b) {
  const idPizze = new Set(LISTINO.pizze.map(p => p.id)), idVoci = new Set(LISTINO.voci.map(v => v.id));
  const out = { prezzi: {}, supp: {}, nascoste: [], nuove: [], evidenza: null, coperto: null };
  for (const [id, v] of Object.entries(b.prezzi || {})) if ((idPizze.has(id) || idVoci.has(id)) && prezzo(v, null) != null) out.prezzi[id] = prezzo(v, null);
  for (const [id, v] of Object.entries(b.supp || {})) if (LISTINO.ingredienti[id] && prezzo(v, null) != null) out.supp[id] = prezzo(v, null);
  out.nascoste = [...new Set((b.nascoste || []).filter(id => idPizze.has(id) || idVoci.has(id)))];
  for (const p of (Array.isArray(b.nuove) ? b.nuove : []).slice(0, 20)) {
    const nome = testo(p && p.nome, 40), ing = listaIng(p && p.ing), pr = prezzo(p && p.prezzo, null);
    if (!nome || !ing.length || pr == null) continue;
    const id = /^n_[a-z0-9]{4,12}$/.test(p.id) ? p.id : 'n_' + crypto.randomUUID().replace(/-/g, '').slice(0, 8);
    out.nuove.push({ id, sez: SEZIONI.includes(p.sez) ? p.sez : 'speciali', nome, prezzo: pr, ing });
  }
  if (b.evidenza && b.evidenza.id) out.evidenza = { id: testo(b.evidenza.id, 40), nota: testo(b.evidenza.nota, 140) };
  if (b.coperto != null) out.coperto = prezzo(b.coperto, null);
  return out;
}

// Stessa regola della pagina: se gli ingredienti coincidono con una pizza del menu vale quella,
// altrimenti prezzo della pizza di partenza + supplementi delle aggiunte (togliere e' gratis).
function riga(r, X) {
  if (!r || typeof r !== 'object') return null;
  const qty = Math.floor(Number(r.qty));
  if (!(qty >= 1 && qty <= 20)) return null;
  if (r.tipo === 'voce') {
    const v = X.VOC[r.id];
    return v ? { tipo: 'voce', id: v.id, nome: v.nome, sez: v.sez, prezzo: v.prezzo, qty } : null;
  }
  const da = X.PIZ[r.da];
  if (!da) return null;
  const ing = listaIng(r.ing), set = new Set(ing);
  const base = X.PIZZE.find(p => p.ing.length === set.size && p.ing.every(i => set.has(i))) || da;
  const add = ing.filter(i => !base.ing.includes(i)), rem = base.ing.filter(i => !set.has(i));
  const b = id => breveDa(X.ING, id);
  let nome = base.nome;
  if (add.length > 3) nome += ' + ' + add.length + ' ingredienti'; else if (add.length) nome += ' + ' + add.map(b).join(', ');
  if (rem.length > 2) nome += ' senza ' + rem.length + ' ingredienti'; else if (rem.length) nome += ' senza ' + rem.map(b).join(', ');
  const pr = r2(base.prezzo + add.reduce((t, i) => t + (X.ING[i].supp || 0), 0));
  return { tipo: 'pizza', da: base.id, nome, add, rem, ing, prezzo: pr, qty };
}
const pizzeIn = o => (o.righe || []).filter(r => r.tipo !== 'voce').reduce((t, r) => t + (r.qty || 1), 0);
const mediana = a => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : 0; };

export class Pizzeria extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS ordini (id TEXT PRIMARY KEY, tavolo INTEGER, dati TEXT, rev INTEGER);
      CREATE INDEX IF NOT EXISTS ordini_rev ON ordini(rev);
      CREATE TABLE IF NOT EXISTS chiamate (id TEXT PRIMARY KEY, tavolo INTEGER, dati TEXT, rev INTEGER, aperta INTEGER);
      CREATE INDEX IF NOT EXISTS chiamate_rev ON chiamate(rev);
      CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);`);
  }
  leggi(k, def) { const r = this.sql.exec('SELECT v FROM kv WHERE k = ?', k).toArray()[0]; return r ? JSON.parse(r.v) : def; }
  scrivi(k, v) { this.sql.exec('INSERT INTO kv (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v', k, JSON.stringify(v)); }
  togli(k) { this.sql.exec('DELETE FROM kv WHERE k = ?', k); }
  prossimaRev() { const n = this.leggi('rev', 0) + 1; this.scrivi('rev', n); return n; }
  impostazioni() { return { coperti: 'cliente', email: '', ...this.leggi('impostazioni', {}) }; }
  menu() { return menuUnito(this.leggi('menu', {})); }
  config(staff) {
    const imp = this.impostazioni();
    return { tavoli: this.leggi('tavoli', 12), esauriti: this.leggi('esauriti', []), menuRev: this.leggi('menuRev', 0), coperti: imp.coperti, ...(staff ? { email: imp.email } : {}) };
  }
  sessioni(tavolo) {
    const out = {};
    const righe = tavolo ? this.sql.exec('SELECT k, v FROM kv WHERE k = ?', 'tav:' + tavolo).toArray() : this.sql.exec("SELECT k, v FROM kv WHERE k LIKE 'tav:%'").toArray();
    for (const r of righe) out[r.k.slice(4)] = JSON.parse(r.v);
    return out;
  }
  salvaOrdine(o) { this.sql.exec('INSERT INTO ordini (id, tavolo, dati, rev) VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET dati = excluded.dati, rev = excluded.rev', o.id, o.tavolo, JSON.stringify(o), this.prossimaRev()); }
  salvaChiamata(c) { this.sql.exec('INSERT INTO chiamate (id, tavolo, dati, rev, aperta) VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET dati = excluded.dati, rev = excluded.rev, aperta = excluded.aperta', c.id, c.tavolo, JSON.stringify(c), this.prossimaRev(), c.gestita ? 0 : 1); }
  ordine(id) { const r = this.sql.exec('SELECT dati FROM ordini WHERE id = ?', String(id)).toArray()[0]; return r ? JSON.parse(r.dati) : null; }
  recenti(n) { return this.sql.exec('SELECT dati FROM ordini ORDER BY rev DESC LIMIT ?', n).toArray().map(r => JSON.parse(r.dati)); }

  // Stima per il cliente: tempo tipico della cucina (mediana degli ultimi ordini arrivati a «pronto»)
  // piu' le pizze ancora da infornare arrivate prima, meno il tempo gia' passato.
  attesa(tavolo) {
    const rec = this.recenti(400);
    const aperti = rec.filter(o => !o.chiuso && (o.stato === 'nuovo' || o.stato === 'forno'));
    const mie = aperti.filter(o => o.tavolo === tavolo);
    if (!mie.length) return null;
    const fatti = rec.filter(o => o.pronto > o.creato).slice(0, 30).map(o => (o.pronto - o.creato) / 60000);
    const tipico = Math.min(35, Math.max(6, fatti.length >= 3 ? mediana(fatti) : 12));
    const primo = Math.min(...mie.map(o => o.creato));
    const davanti = aperti.filter(o => o.tavolo !== tavolo && o.stato === 'nuovo' && o.creato < primo).reduce((t, o) => t + pizzeIn(o), 0);
    let resto = tipico + davanti * 0.75 - (Date.now() - primo) / 60000;
    if (mie.every(o => o.stato === 'forno')) resto = Math.min(resto, 4);
    resto = Math.max(2, resto);
    return { min: Math.round(resto), max: Math.round(resto * 1.25 + 2), davanti };
  }

  riepilogoDati() {
    const X = indici(this.menu());
    const da = Date.now() - 20 * 3600e3;
    const os = this.recenti(3000).filter(o => o.creato >= da);
    const byP = new Map(), add = new Map(), voci = new Map(), tav = new Set();
    let inc = 0, pz = 0; const prep = [];
    for (const o of os) {
      inc += o.totale || 0; tav.add(o.tavolo);
      if (o.pronto > o.creato) prep.push((o.pronto - o.creato) / 60000);
      for (const r of o.righe || []) {
        if (r.tipo === 'voce') { voci.set(r.nome, (voci.get(r.nome) || 0) + r.qty); continue; }
        pz += r.qty; const n = X.PIZ[r.da] ? X.PIZ[r.da].nome : r.nome; byP.set(n, (byP.get(n) || 0) + r.qty);
        (r.add || []).forEach(i => { if (X.ING[i]) add.set(X.ING[i].nome, (add.get(X.ING[i].nome) || 0) + r.qty); });
      }
    }
    const top = (m, k) => [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, k);
    const mai = X.PIZZE.filter(p => !byP.has(p.nome)).map(p => p.nome);
    const es = this.leggi('esauriti', []).map(id => X.ING[id] ? X.ING[id].nome : X.VOC[id] ? X.VOC[id].nome : id);
    return { n: os.length, inc: r2(inc), pz, tavoli: tav.size, prep: prep.length ? Math.round(mediana(prep)) : null, pizze: top(byP, 8), aggiunte: top(add, 5), voci: top(voci, 6), mai, esauriti: es, locale: X.M.locale };
  }
  async inviaRiepilogo(manuale) {
    const imp = this.impostazioni();
    if (!imp.email) return { ok: false, errore: 'manca l\'indirizzo email' };
    if (!this.env.RESEND_API_KEY) return { ok: false, errore: 'invio email non configurato' };
    const R = this.riepilogoDati();
    if (!R.n && !manuale) return { ok: true, saltato: 'nessun ordine' };
    const giorno = new Date().toLocaleDateString('it-IT', { timeZone: 'Europe/Rome', weekday: 'long', day: 'numeric', month: 'long' });
    const lista = a => a.length ? '<ul>' + a.map(([k, v]) => `<li>${escH(k)}: <b>${v}</b></li>`).join('') + '</ul>' : '<p>—</p>';
    const html = `<div style="font-family:Arial,sans-serif;font-size:15px;color:#121A44;max-width:560px">
      <h2 style="margin:0 0 4px">Riepilogo della serata</h2><p style="margin:0 0 16px;color:#566089">${escH(R.locale || '')} · ${escH(giorno)} (ultime 20 ore)</p>
      <p>Incasso dagli ordini: <b>${eur(R.inc)}</b> (coperti esclusi)<br>Ordini: <b>${R.n}</b> · Pizze: <b>${R.pz}</b> · Tavoli serviti: <b>${R.tavoli}</b>${R.prep != null ? `<br>Tempo tipico in cucina: <b>${R.prep} min</b>` : ''}</p>
      <h3>Pizze più ordinate</h3>${lista(R.pizze)}
      <h3>Aggiunte più richieste</h3>${lista(R.aggiunte)}
      <h3>Dal resto del menu</h3>${lista(R.voci)}
      <h3>Mai ordinate stasera</h3><p>${R.mai.length ? escH(R.mai.join(', ')) : 'Nessuna: tutte ordinate almeno una volta.'}</p>
      <h3>Segnati come esauriti</h3><p>${R.esauriti.length ? escH(R.esauriti.join(', ')) : 'Niente.'}</p>
      <p style="color:#566089;font-size:13px">Dettagli e grafici nella gestione, scheda Analisi.</p></div>`;
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + this.env.RESEND_API_KEY, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: this.env.PIZZA_MAIL_FROM || this.env.MAIL_FROM || 'Pizza su Misura <sito@visiorender.it>', to: [imp.email], subject: `Riepilogo serata: ${eur(R.inc)}, ${R.pz} pizze`, html })
    });
    return r.ok ? { ok: true, inviato: imp.email } : { ok: false, errore: 'il servizio email ha rifiutato l\'invio (' + r.status + ')' };
  }

  async fetch(request) {
    const url = new URL(request.url);
    const via = url.pathname.replace(/^\/+/, '');
    if (via === 'interno/riepilogo') return json(await this.inviaRiepilogo(false));
    if (request.method === 'GET' && via === 'menu') return json({ ok: true, menu: this.menu(), menuRev: this.leggi('menuRev', 0) });
    const staff = via.startsWith('staff/') || (via === 'stato' && !url.searchParams.get('tavolo'));
    if (staff && this.env.PIZZA_PIN && request.headers.get('X-Pin') !== this.env.PIZZA_PIN) return errore('PIN richiesto', 401);

    if (request.method === 'GET' && via === 'stato') {
      const rev = Math.max(0, Math.floor(Number(url.searchParams.get('rev')) || 0));
      const tavolo = tavoloValido(url.searchParams.get('tavolo'));
      const filtro = tavolo ? ' AND tavolo = ' + tavolo : '';
      const ordini = this.sql.exec(`SELECT dati FROM ordini WHERE rev > ?${filtro} ORDER BY rev LIMIT 3000`, rev).toArray().map(r => JSON.parse(r.dati));
      const chiamate = this.sql.exec(`SELECT dati FROM chiamate WHERE rev > ?${filtro} ORDER BY rev LIMIT 500`, rev).toArray().map(r => JSON.parse(r.dati));
      const out = { ok: true, rev: this.leggi('rev', 0), ordini, chiamate, config: this.config(!tavolo), sessioni: this.sessioni(tavolo) };
      if (tavolo) out.attesa = this.attesa(tavolo);
      return json(out);
    }
    if (request.method !== 'POST') return errore('metodo non ammesso', 405);
    const corpo = await request.text();
    if (corpo.length > 65536) return errore('richiesta troppo grande', 413);
    let b; try { b = JSON.parse(corpo); } catch { return errore('richiesta non valida'); }
    if (!b || typeof b !== 'object') return errore('richiesta non valida');
    const ora = Date.now();

    if (via === 'ordini') {
      const tavolo = tavoloValido(b.tavolo);
      if (!tavolo) return errore('tavolo non valido');
      const X = indici(this.menu());
      const righe = (Array.isArray(b.righe) ? b.righe.slice(0, 40) : []).map(r => riga(r, X));
      if (!righe.length || righe.some(r => !r)) return errore('ordine non valido');
      const esauriti = new Set(this.leggi('esauriti', []));
      const finiti = [...new Set(righe.flatMap(r => r.tipo === 'voce' ? (esauriti.has(r.id) ? [r.id] : []) : r.ing.filter(i => esauriti.has(i))))];
      if (finiti.length) return json({ ok: false, errore: 'ingrediente finito', finiti }, 409);
      const n = this.sql.exec('SELECT COUNT(*) AS n FROM ordini').toArray()[0].n;
      if (n >= MAX_ORDINI) return errore('archivio pieno', 507);
      const o = {
        id: crypto.randomUUID().slice(0, 12), tavolo, righe, nota: testo(b.nota, 300), dev: testo(b.dev, 12) || null,
        cameriere: b.cameriere === true, totale: r2(righe.reduce((t, r) => t + r.prezzo * r.qty, 0)), stato: 'nuovo', creato: ora, chiuso: false
      };
      // coperti indicati dal cliente al primo ordine, se la pizzeria li fa indicare cosi'
      const cop = Math.floor(Number(b.coperti));
      const modo = this.impostazioni().coperti;
      if (cop >= 1 && cop <= 40 && (modo === 'cliente' || (o.cameriere && modo !== 'no')) && !this.leggi('tav:' + tavolo, null)) this.scrivi('tav:' + tavolo, { coperti: cop, da: o.cameriere ? 'cameriere' : 'cliente' });
      this.salvaOrdine(o);
      return json({ ok: true, id: o.id, totale: o.totale });
    }
    if (via === 'chiamate') {
      const tavolo = tavoloValido(b.tavolo);
      const tipo = b.tipo === 'conto' ? 'conto' : b.tipo === 'cameriere' ? 'cameriere' : '';
      if (!tavolo || !tipo) return errore('richiesta non valida');
      const gia = this.sql.exec('SELECT dati FROM chiamate WHERE aperta = 1 AND tavolo = ?', tavolo).toArray().map(r => JSON.parse(r.dati)).find(c => c.tipo === tipo);
      if (gia) return json({ ok: true, id: gia.id });
      const c = { id: crypto.randomUUID().slice(0, 12), tavolo, tipo, creato: ora, gestita: false };
      this.salvaChiamata(c);
      return json({ ok: true, id: c.id });
    }
    if (via === 'staff/stato') {
      // la cucina sposta insieme tutti gli ordini della comanda di un tavolo (ids), o uno solo (id)
      if (!STATI.includes(b.stato)) return errore('stato non valido');
      const ids = (Array.isArray(b.ids) ? b.ids : [b.id]).map(String).slice(0, 60);
      let n = 0;
      for (const id of ids) {
        const o = this.ordine(id);
        if (!o) continue;
        o.stato = b.stato;
        if (b.stato === 'forno' || b.stato === 'pronto') o[b.stato] = ora;
        if (b.stato === 'servito') o.servito = ora;
        this.salvaOrdine(o);
        n++;
      }
      return n ? json({ ok: true, aggiornati: n }) : errore('ordine non trovato', 404);
    }
    if (via === 'staff/chiamata') {
      const r = this.sql.exec('SELECT dati FROM chiamate WHERE id = ?', String(b.id)).toArray()[0];
      if (!r) return errore('chiamata non trovata', 404);
      const c = JSON.parse(r.dati); c.gestita = true; c.gestitaAlle = ora;
      this.salvaChiamata(c);
      return json({ ok: true });
    }
    if (via === 'staff/coperti') {
      const tavolo = tavoloValido(b.tavolo), n = Math.floor(Number(b.coperti));
      if (!tavolo || !(n >= 0 && n <= 40)) return errore('richiesta non valida');
      if (n) this.scrivi('tav:' + tavolo, { coperti: n, da: 'cameriere' }); else this.togli('tav:' + tavolo);
      this.prossimaRev();
      return json({ ok: true });
    }
    if (via === 'staff/chiudi') {
      const tavolo = tavoloValido(b.tavolo);
      if (!tavolo) return errore('tavolo non valido');
      const sess = this.leggi('tav:' + tavolo, null);
      for (const r of this.sql.exec('SELECT dati FROM ordini WHERE tavolo = ?', tavolo).toArray()) {
        const o = JSON.parse(r.dati);
        if (!o.chiuso) { o.chiuso = true; o.chiusoAlle = ora; if (sess) o.coperti = sess.coperti; this.salvaOrdine(o); }
      }
      for (const r of this.sql.exec('SELECT dati FROM chiamate WHERE aperta = 1 AND tavolo = ?', tavolo).toArray()) {
        const c = JSON.parse(r.dati); c.gestita = true; c.gestitaAlle = ora; this.salvaChiamata(c);
      }
      this.togli('tav:' + tavolo);
      return json({ ok: true });
    }
    if (via === 'staff/config') {
      if (b.tavoli != null) {
        const n = tavoloValido(b.tavoli);
        if (!n) return errore('numero di tavoli non valido');
        this.scrivi('tavoli', n);
      }
      if (b.esauriti != null) {
        const ok = new Set([...ORDINE_ING, ...LISTINO.voci.map(v => v.id)]);
        this.scrivi('esauriti', Array.isArray(b.esauriti) ? [...new Set(b.esauriti.filter(i => ok.has(i)))].slice(0, 200) : []);
      }
      if (b.coperti != null || b.email != null) {
        const imp = this.impostazioni();
        if (['cliente', 'cameriere', 'no'].includes(b.coperti)) imp.coperti = b.coperti;
        if (b.email != null) { const e = testo(b.email, 120); if (e && !/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(e)) return errore('indirizzo email non valido'); imp.email = e; }
        this.scrivi('impostazioni', imp);
      }
      this.prossimaRev();
      return json({ ok: true, config: this.config(true) });
    }
    if (via === 'staff/menu') {
      this.scrivi('menu', pulisciMenu(b));
      this.scrivi('menuRev', this.leggi('menuRev', 0) + 1);
      this.prossimaRev();
      return json({ ok: true, menu: this.menu() });
    }
    if (via === 'staff/riepilogo') return json(await this.inviaRiepilogo(true));
    return errore('non trovato', 404);
  }
}

const stub = env => env.PIZZERIA.get(env.PIZZERIA.idFromName('demo'));

export async function gestisciPizza(request, env) {
  if (!env.PIZZERIA) return errore('servizio non configurato', 503);
  const url = new URL(request.url);
  const via = url.pathname.slice('/api/pizza'.length);
  if (via.startsWith('/interno/')) return errore('non trovato', 404);
  if (request.method === 'POST') {
    const origine = request.headers.get('Origin') || '';
    if (!origine || !ORIGINI.test(origine)) return errore('provenienza non ammessa', 403);
  }
  return stub(env).fetch(new Request('https://pizzeria' + via + url.search, request));
}

// Chiamato dal cron notturno (worker/index.js → scheduled).
export async function riepilogoSerale(env) {
  if (!env.PIZZERIA) return;
  await stub(env).fetch('https://pizzeria/interno/riepilogo', { method: 'POST' });
}

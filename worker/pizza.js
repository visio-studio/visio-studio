/* Demo «Pizza su Misura»: ordini dal tavolo per una pizzeria (pagina /pizza/).
   Un solo Durable Object con SQLite tiene ordini, chiamate al cameriere e impostazioni.
   Le pagine leggono lo stato ogni pochi secondi (GET /api/pizza/stato?rev=N restituisce
   solo cio' che e' cambiato dopo la revisione N).
   Le azioni del personale (/api/pizza/staff/*) chiedono il PIN se nel Worker c'e' il
   segreto PIZZA_PIN; senza segreto sono aperte, va bene solo per la prova.
   Prezzi, pizze e ingredienti stanno in pizza/listino.json, letto anche dalla pagina:
   il server ricalcola sempre il prezzo da li', il cliente non lo puo' cambiare. */
import { DurableObject } from 'cloudflare:workers';
import LISTINO from '../pizza/listino.json';

const ORIGINI = /^https:\/\/([a-z0-9-]+\.)*(visiorender\.it|visiorender\.pages\.dev|workers\.dev)$|^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/;

const ING = LISTINO.ingredienti;
const ORDINE_ING = Object.keys(ING);
const PIZZE = LISTINO.pizze;
const PIZ = Object.fromEntries(PIZZE.map(p => [p.id, p]));
const VOC = Object.fromEntries(LISTINO.voci.map(v => [v.id, v]));
const STATI = ['nuovo', 'forno', 'pronto', 'servito'];
const MAX_ORDINI = 20000;

const r2 = v => Math.round(v * 100) / 100;
const json = (dati, stato = 200) => new Response(JSON.stringify(dati), {
  status: stato, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }
});
const errore = (msg, stato = 400) => json({ ok: false, errore: msg }, stato);
const testo = (v, max) => String(v == null ? '' : v).replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, max);
const listaIng = a => Array.isArray(a) ? ORDINE_ING.filter(i => a.includes(i)) : [];
function breve(id) { const n = ING[id].nome, w = n.split(' '); return w.length > 1 && /^[A-Z]/.test(w[1]) ? n : n.charAt(0).toLowerCase() + n.slice(1); }

// Stessa regola della pagina: se gli ingredienti coincidono con una pizza del menu vale quella,
// altrimenti prezzo della pizza di partenza + supplementi delle aggiunte (togliere e' gratis).
function riga(r) {
  if (!r || typeof r !== 'object') return null;
  const qty = Math.floor(Number(r.qty));
  if (!(qty >= 1 && qty <= 20)) return null;
  if (r.tipo === 'voce') {
    const v = VOC[r.id];
    return v ? { tipo: 'voce', id: v.id, nome: v.nome, sez: v.sez, prezzo: v.prezzo, qty } : null;
  }
  const da = PIZ[r.da];
  if (!da) return null;
  const ing = listaIng(r.ing), set = new Set(ing);
  const base = PIZZE.find(p => p.ing.length === set.size && p.ing.every(i => set.has(i))) || da;
  const add = ing.filter(i => !base.ing.includes(i)), rem = base.ing.filter(i => !set.has(i));
  let nome = base.nome;
  if (add.length > 3) nome += ' + ' + add.length + ' ingredienti'; else if (add.length) nome += ' + ' + add.map(breve).join(', ');
  if (rem.length > 2) nome += ' senza ' + rem.length + ' ingredienti'; else if (rem.length) nome += ' senza ' + rem.map(breve).join(', ');
  const prezzo = r2(base.prezzo + add.reduce((t, i) => t + (ING[i].supp || 0), 0));
  return { tipo: 'pizza', da: base.id, nome, add, rem, ing, prezzo, qty };
}
const tavoloValido = t => { const n = Math.floor(Number(t)); return n >= 1 && n <= 60 ? n : 0; };

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
  prossimaRev() { const n = this.leggi('rev', 0) + 1; this.scrivi('rev', n); return n; }
  config() { return { tavoli: this.leggi('tavoli', 12), esauriti: this.leggi('esauriti', []) }; }
  salvaOrdine(o) { this.sql.exec('INSERT INTO ordini (id, tavolo, dati, rev) VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET dati = excluded.dati, rev = excluded.rev', o.id, o.tavolo, JSON.stringify(o), this.prossimaRev()); }
  salvaChiamata(c) { this.sql.exec('INSERT INTO chiamate (id, tavolo, dati, rev, aperta) VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET dati = excluded.dati, rev = excluded.rev, aperta = excluded.aperta', c.id, c.tavolo, JSON.stringify(c), this.prossimaRev(), c.gestita ? 0 : 1); }
  ordine(id) { const r = this.sql.exec('SELECT dati FROM ordini WHERE id = ?', String(id)).toArray()[0]; return r ? JSON.parse(r.dati) : null; }

  async fetch(request) {
    const url = new URL(request.url);
    const via = url.pathname.replace(/^\/+/, '');
    const staff = via.startsWith('staff/') || (via === 'stato' && !url.searchParams.get('tavolo'));
    if (staff && this.env.PIZZA_PIN && request.headers.get('X-Pin') !== this.env.PIZZA_PIN) return errore('PIN richiesto', 401);

    if (request.method === 'GET' && via === 'stato') {
      const rev = Math.max(0, Math.floor(Number(url.searchParams.get('rev')) || 0));
      const tavolo = tavoloValido(url.searchParams.get('tavolo'));
      const filtro = tavolo ? ' AND tavolo = ' + tavolo : '';
      const ordini = this.sql.exec(`SELECT dati FROM ordini WHERE rev > ?${filtro} ORDER BY rev LIMIT 3000`, rev).toArray().map(r => JSON.parse(r.dati));
      const chiamate = this.sql.exec(`SELECT dati FROM chiamate WHERE rev > ?${filtro} ORDER BY rev LIMIT 500`, rev).toArray().map(r => JSON.parse(r.dati));
      return json({ ok: true, rev: this.leggi('rev', 0), ordini, chiamate, config: this.config() });
    }
    if (request.method !== 'POST') return errore('metodo non ammesso', 405);
    const corpo = await request.text();
    if (corpo.length > 32768) return errore('richiesta troppo grande', 413);
    let b; try { b = JSON.parse(corpo); } catch { return errore('richiesta non valida'); }
    if (!b || typeof b !== 'object') return errore('richiesta non valida');
    const ora = Date.now();

    if (via === 'ordini') {
      const tavolo = tavoloValido(b.tavolo);
      if (!tavolo) return errore('tavolo non valido');
      const righe = (Array.isArray(b.righe) ? b.righe.slice(0, 40) : []).map(riga);
      if (!righe.length || righe.some(r => !r)) return errore('ordine non valido');
      const esauriti = new Set(this.config().esauriti);
      const finiti = [...new Set(righe.flatMap(r => r.tipo === 'voce' ? (esauriti.has(r.id) ? [r.id] : []) : r.ing.filter(i => esauriti.has(i))))];
      if (finiti.length) return json({ ok: false, errore: 'ingrediente finito', finiti }, 409);
      const n = this.sql.exec('SELECT COUNT(*) AS n FROM ordini').toArray()[0].n;
      if (n >= MAX_ORDINI) return errore('archivio pieno', 507);
      const o = {
        id: crypto.randomUUID().slice(0, 12), tavolo, righe, nota: testo(b.nota, 300),
        totale: r2(righe.reduce((t, r) => t + r.prezzo * r.qty, 0)), stato: 'nuovo', creato: ora, chiuso: false
      };
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
      const o = this.ordine(b.id);
      if (!o) return errore('ordine non trovato', 404);
      if (!STATI.includes(b.stato)) return errore('stato non valido');
      o.stato = b.stato;
      if (b.stato !== 'nuovo' && b.stato !== 'servito') o[b.stato] = ora;
      if (b.stato === 'servito') o.servito = ora;
      this.salvaOrdine(o);
      return json({ ok: true });
    }
    if (via === 'staff/chiamata') {
      const r = this.sql.exec('SELECT dati FROM chiamate WHERE id = ?', String(b.id)).toArray()[0];
      if (!r) return errore('chiamata non trovata', 404);
      const c = JSON.parse(r.dati); c.gestita = true; c.gestitaAlle = ora;
      this.salvaChiamata(c);
      return json({ ok: true });
    }
    if (via === 'staff/chiudi') {
      const tavolo = tavoloValido(b.tavolo);
      if (!tavolo) return errore('tavolo non valido');
      for (const r of this.sql.exec('SELECT dati FROM ordini WHERE tavolo = ?', tavolo).toArray()) {
        const o = JSON.parse(r.dati);
        if (!o.chiuso) { o.chiuso = true; o.chiusoAlle = ora; this.salvaOrdine(o); }
      }
      for (const r of this.sql.exec('SELECT dati FROM chiamate WHERE aperta = 1 AND tavolo = ?', tavolo).toArray()) {
        const c = JSON.parse(r.dati); c.gestita = true; c.gestitaAlle = ora; this.salvaChiamata(c);
      }
      return json({ ok: true });
    }
    if (via === 'staff/config') {
      if (b.tavoli != null) {
        const n = tavoloValido(b.tavoli);
        if (!n) return errore('numero di tavoli non valido');
        this.scrivi('tavoli', n);
      }
      if (b.esauriti != null) this.scrivi('esauriti', Array.isArray(b.esauriti) ? [...new Set(b.esauriti.filter(i => ING[i] || VOC[i]))].slice(0, 200) : []);
      this.prossimaRev();
      return json({ ok: true, config: this.config() });
    }
    return errore('non trovato', 404);
  }
}

export async function gestisciPizza(request, env) {
  if (!env.PIZZERIA) return errore('servizio non configurato', 503);
  if (request.method === 'POST') {
    const origine = request.headers.get('Origin') || '';
    if (!origine || !ORIGINI.test(origine)) return errore('provenienza non ammessa', 403);
  }
  const url = new URL(request.url);
  const via = url.pathname.slice('/api/pizza'.length) + url.search;
  const stub = env.PIZZERIA.get(env.PIZZERIA.idFromName('demo'));
  return stub.fetch(new Request('https://pizzeria' + via, request));
}

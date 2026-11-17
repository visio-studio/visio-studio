/* Worker del sito visiorender.it (Cloudflare Workers con asset statici, vedi wrangler.jsonc).
   Tutte le pagine e i file sono serviti direttamente come asset; il Worker gira solo per /api/*
   (run_worker_first), cioè per l'invio dei moduli. */
import { inviaModulo } from './modulo.js';

const json = (dati, stato) => new Response(JSON.stringify(dati), {
  status: stato, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }
});

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === '/api/modulo') {
      if (request.method !== 'POST') return json({ ok: false, errore: 'usa POST' }, 405);
      return inviaModulo(request, env);
    }
    if (pathname.startsWith('/api/')) return json({ ok: false, errore: 'non trovato' }, 404);
    return env.ASSETS.fetch(request);
  }
};

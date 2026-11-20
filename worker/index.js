/* Worker del sito visiorender.it (Cloudflare Workers con asset statici, vedi wrangler.jsonc).
   Tutte le pagine e i file sono serviti direttamente come asset; il Worker gira solo per /api/*
   (run_worker_first): l'invio dei moduli e la demo per pizzerie (/api/pizza/*, vedi pizza.js). */
import { inviaModulo } from './modulo.js';
import { gestisciPizza, Pizzeria } from './pizza.js';

export { Pizzeria };

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
    if (pathname.startsWith('/api/pizza/')) return gestisciPizza(request, env);
    if (pathname.startsWith('/api/')) return json({ ok: false, errore: 'non trovato' }, 404);
    return env.ASSETS.fetch(request);
  }
};

/* ---------------------------------------------------------------------------
   Invio dei moduli del sito (contatti in home e preventivo.html) per email.

   I due moduli fanno POST multipart su /api/modulo. Questa funzione del
   Worker Cloudflare (chiamata da worker/index.js) controlla i campi, scarta lo spam (campo trappola
   «bot-field» e provenienza) e inoltra la richiesta con Resend
   (https://resend.com) all'indirizzo dello studio, con «Rispondi a» impostato
   sull'email di chi ha scritto e l'eventuale allegato (max 8 MB).

   Variabili del Worker visio-studio (Cloudflare → Workers & Pages → visio-studio → Settings → Variables and secrets):
     RESEND_API_KEY  segreto, chiave dell'account Resend          (obbligatoria)
     MAIL_TO         destinatario     (predefinito info@visiorender.it)
     MAIL_FROM       mittente sul dominio verificato in Resend
                     (predefinito "Sito VISIO <sito@visiorender.it>")
   Senza RESEND_API_KEY risponde 503: la pagina mostra il messaggio d'errore
   con WhatsApp e email, quindi nessuna richiesta va persa in silenzio.
--------------------------------------------------------------------------- */
const MAX_ALLEGATO = 8 * 1024 * 1024;
const MAX_CAMPO = 5000;
const ORIGINI = /^https:\/\/([a-z0-9-]+\.)?(visiorender\.it|visiorender\.pages\.dev)$/;
const NOMI = { contatti: 'Contatti dalla home', preventivo: 'Richiesta di preventivo' };

const json = (dati, stato = 200) => new Response(JSON.stringify(dati), {
  status: stato,
  headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }
});
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const etichetta = k => k.replace(/[-_]/g, ' ').replace(/^./, c => c.toUpperCase());

function base64(buf) {
  const b = new Uint8Array(buf); let s = '';
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
  return btoa(s);
}

export async function inviaModulo(request, env) {
  const origine = request.headers.get('Origin') || '';
  if (origine && !ORIGINI.test(origine)) return json({ ok: false, errore: 'provenienza non ammessa' }, 403);
  if (!env.RESEND_API_KEY) return json({ ok: false, errore: 'invio non configurato' }, 503);

  let dati;
  try { dati = await request.formData(); } catch { return json({ ok: false, errore: 'modulo non leggibile' }, 400); }
  if ((dati.get('bot-field') || '').toString().trim()) return json({ ok: true });   // spam: finge di accettare

  const modulo = (dati.get('form-name') || 'contatti').toString();
  const email = (dati.get('email') || '').toString().trim();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 200) return json({ ok: false, errore: 'email non valida' }, 400);

  const righe = []; const allegati = [];
  for (const [k, v] of dati.entries()) {
    if (k === 'form-name' || k === 'bot-field') continue;
    if (typeof v === 'object' && v && 'arrayBuffer' in v) {
      if (!v.size) continue;
      if (v.size > MAX_ALLEGATO) return json({ ok: false, errore: 'allegato oltre 8 MB' }, 413);
      allegati.push({ filename: (v.name || 'allegato').slice(0, 120), content: base64(await v.arrayBuffer()) });
      continue;
    }
    const t = v.toString().trim().slice(0, MAX_CAMPO);
    if (t) righe.push([etichetta(k), t]);
  }
  const nome = [dati.get('nome'), dati.get('cognome')].filter(Boolean).join(' ').toString().trim() || email;
  const titolo = `${NOMI[modulo] || 'Modulo ' + modulo} · ${nome}`.slice(0, 180);

  const html = `<h2 style="font-family:Arial,sans-serif">${esc(titolo)}</h2>
<table style="font-family:Arial,sans-serif;font-size:14px;border-collapse:collapse">${righe.map(([k, v]) =>
    `<tr><td style="padding:6px 12px 6px 0;color:#666;vertical-align:top">${esc(k)}</td><td style="padding:6px 0;white-space:pre-wrap">${esc(v)}</td></tr>`).join('')}</table>
<p style="font-family:Arial,sans-serif;font-size:12px;color:#888">Inviato dal sito visiorender.it${allegati.length ? ' · allegato: ' + esc(allegati[0].filename) : ''}. Rispondi a questa email per scrivere a ${esc(email)}.</p>`;
  const testo = righe.map(([k, v]) => `${k}: ${v}`).join('\n');

  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: env.MAIL_FROM || 'Sito VISIO <sito@visiorender.it>',
      to: [env.MAIL_TO || 'info@visiorender.it'],
      reply_to: email,
      subject: titolo,
      html, text: testo,
      ...(allegati.length ? { attachments: allegati } : {})
    })
  });
  if (!r.ok) return json({ ok: false, errore: 'invio email non riuscito', stato: r.status }, 502);
  return json({ ok: true });
}



// Gestione dell'ora locale del luogo cercato (non del browser).
import tzlookup from '@photostructure/tz-lookup';

export function zoneFor(lat, lon) {
  try {
    return tzlookup(lat, lon);
  } catch {
    return 'UTC';
  }
}

function partsInZone(date, tz) {
  const f = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  const o = {};
  for (const p of f.formatToParts(date)) o[p.type] = p.value;
  return { y: +o.year, m: +o.month, d: +o.day, h: +o.hour % 24, mi: +o.minute, s: +o.second };
}

// Differenza in minuti fra l'ora locale del fuso e UTC in un dato istante.
export function offsetMinutes(date, tz) {
  const p = partsInZone(date, tz);
  const asUTC = Date.UTC(p.y, p.m - 1, p.d, p.h, p.mi, p.s);
  return Math.round((asUTC - date.getTime()) / 60000);
}

// Converte "giorno + minuti dalla mezzanotte" nel fuso tz in un istante UTC.
export function zonedToUtc(y, m, d, minutes, tz) {
  const guess = Date.UTC(y, m - 1, d, 0, minutes);
  const off = offsetMinutes(new Date(guess), tz);
  let t = guess - off * 60000;
  const off2 = offsetMinutes(new Date(t), tz);
  if (off2 !== off) t = guess - off2 * 60000;
  return new Date(t);
}

export function fmtTime(date, tz) {
  if (!date || isNaN(date)) return '—';
  return new Intl.DateTimeFormat('it-IT', { timeZone: tz, hour: '2-digit', minute: '2-digit' }).format(date);
}

export function todayInZone(tz) {
  const p = partsInZone(new Date(), tz);
  return { y: p.y, m: p.m, d: p.d, minutes: p.h * 60 + p.mi };
}

export const pad = (n) => String(n).padStart(2, '0');
export const minutesToHHMM = (min) => `${pad(Math.floor(min / 60) % 24)}:${pad(Math.floor(min % 60))}`;

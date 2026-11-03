import { getPosition, getTimes } from 'suncalc';

// Posizione del sole: altitudine (rad e gradi, con rifrazione), azimut come bussola
// (0° = Nord, senso orario) e versore verso il sole nella scena (x = est, y = su, z = sud).
// suncalc v2 restituisce già gradi, azimut da Nord in senso orario.
export function sunPosition(date, lat, lon) {
  const p = getPosition(date, lat, lon);
  const altDeg = p.altitude;
  const bearing = ((p.azimuth % 360) + 360) % 360;
  const alt = (altDeg * Math.PI) / 180;
  const b = (bearing * Math.PI) / 180;
  const c = Math.cos(alt);
  return {
    alt,
    altDeg,
    bearing,
    dir: { x: Math.sin(b) * c, y: Math.sin(alt), z: -Math.cos(b) * c },
  };
}

export function sunTimes(date, lat, lon) {
  return getTimes(date, lat, lon);
}

const CARD = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'];
export const cardinal = (deg) => CARD[Math.round(deg / 45) % 8];

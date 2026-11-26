// Display helpers. Times are always shown in the clinic's time zone (B-BKG-07),
// whatever the visitor's computer is set to.
export const CLINIC_TIME_ZONE = 'America/Toronto';

const LOCALES = { fr: 'fr-CA', en: 'en-CA' };
const locale = (language) => LOCALES[language] || 'fr-CA';

export function formatPrice(cents, language) {
  return new Intl.NumberFormat(locale(language), { style: 'currency', currency: 'CAD' }).format(
    cents / 100,
  );
}

export function formatTime(isoString, language) {
  return new Intl.DateTimeFormat(locale(language), {
    hour: 'numeric', // "7 h 00" / "7:00 a.m."
    minute: '2-digit',
    timeZone: CLINIC_TIME_ZONE,
  }).format(new Date(isoString));
}

export function formatDay(isoString, language) {
  return new Intl.DateTimeFormat(locale(language), {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    timeZone: CLINIC_TIME_ZONE,
  }).format(new Date(isoString));
}

/** The clinic's calendar date of an instant, as YYYY-MM-DD. */
export function clinicDateKey(isoString) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: CLINIC_TIME_ZONE }).format(
    new Date(isoString),
  );
}

/** Today in Montréal, as YYYY-MM-DD. */
export function clinicToday(now = new Date()) {
  return clinicDateKey(now.toISOString());
}

/** Add days to a YYYY-MM-DD date (calendar arithmetic, no time zone involved). */
export function addDays(dateKey, days) {
  const [y, m, d] = dateKey.split('-').map(Number);
  const date = new Date(Date.UTC(y, m - 1, d + days));
  return date.toISOString().slice(0, 10);
}

/** Group slots by clinic day, keeping the time order. */
export function groupByDay(slots) {
  const groups = new Map();
  for (const slot of slots) {
    const key = clinicDateKey(slot.start);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(slot);
  }
  return [...groups.entries()];
}

/** Initial evaluation first (required before any treatment), then alphabetical. */
export function sortServices(services, language) {
  const name = (s) => (language === 'fr' ? s.name_fr : s.name_en);
  return [...services].sort(
    (a, b) =>
      Number(b.is_initial_evaluation) - Number(a.is_initial_evaluation) ||
      name(a).localeCompare(name(b), language),
  );
}

/**
 * A clinic date and time ("2026-11-02", "08:00") as an ISO string with Montréal's offset of
 * that day ("2026-11-02T08:00:00-05:00"), as the API expects for time off.
 */
export function clinicIso(dateKey, hhmm) {
  const [y, m, d] = dateKey.split('-').map(Number);
  const [h, mi] = hhmm.split(':').map(Number);
  const offsetAt = (instant) => {
    const name = new Intl.DateTimeFormat('en-US', {
      timeZone: CLINIC_TIME_ZONE,
      timeZoneName: 'longOffset',
    })
      .formatToParts(instant)
      .find((p) => p.type === 'timeZoneName').value; // "GMT-05:00"
    const match = /GMT([+-])(\d{2}):(\d{2})/.exec(name);
    return match ? (match[1] === '-' ? -1 : 1) * (Number(match[2]) * 60 + Number(match[3])) : 0;
  };
  const wall = Date.UTC(y, m - 1, d, h, mi);
  let offset = offsetAt(new Date(wall));
  offset = offsetAt(new Date(wall - offset * 60000)); // again, in case the guess crossed a change
  const sign = offset < 0 ? '-' : '+';
  const abs = Math.abs(offset);
  const pad = (n) => String(n).padStart(2, '0');
  return `${dateKey}T${pad(h)}:${pad(mi)}:00${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
}

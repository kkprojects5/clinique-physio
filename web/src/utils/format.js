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

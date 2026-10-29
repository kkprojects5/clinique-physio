// Display helpers. The API gives each start in Montréal time with its offset
// ("2026-11-02T10:00:00-05:00"), so the clock time is read directly from it:
// it is always the clinic's time, whatever time zone the phone is in (B-BKG-07).
import type { Language } from './i18n';

/** "10:00" from "2026-11-02T10:00:00-05:00". */
export function clockTime(startLocal: string): string {
  return startLocal.slice(11, 16);
}

/** End time, e.g. "10:00" + 30 min -> "10:30". */
export function addMinutes(clock: string, minutes: number): string {
  const [h, m] = clock.split(':').map(Number);
  const total = (h * 60 + m + minutes) % (24 * 60);
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}

/** "lundi 2 novembre" / "Monday, November 2", from the clinic date of the appointment. */
export function dayLabel(startLocal: string, language: Language): string {
  const [y, m, d] = startLocal.slice(0, 10).split('-').map(Number);
  const noonUtc = new Date(Date.UTC(y, m - 1, d, 12)); // same calendar day everywhere
  const text = new Intl.DateTimeFormat(language === 'en' ? 'en-CA' : 'fr-CA', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    timeZone: 'UTC',
  }).format(noonUtc);
  return text.charAt(0).toUpperCase() + text.slice(1);
}

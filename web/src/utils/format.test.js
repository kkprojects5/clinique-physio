import { describe, expect, it } from 'vitest';
import { addDays, clinicToday, formatPrice, formatTime, groupByDay, sortServices } from './format';

describe('formatting in Montréal time (B-BKG-07)', () => {
  it('shows 10:00 local for a Monday after the November DST change', () => {
    // 2026-11-02 10:00 EST = 15:00 UTC
    expect(formatTime('2026-11-02T15:00:00Z', 'en')).toMatch(/10:00/);
  });

  it('shows 10:00 local for a Monday before the change too', () => {
    // 2026-10-26 10:00 EDT = 14:00 UTC
    expect(formatTime('2026-10-26T14:00:00Z', 'en')).toMatch(/10:00/);
  });

  it('uses the clinic date, not the UTC date, for late evening slots', () => {
    // 2026-11-02 20:30 in Montréal is already 2026-11-03 in UTC
    const groups = groupByDay([{ start: '2026-11-03T01:30:00Z' }]);
    expect(groups[0][0]).toBe('2026-11-02');
  });

  it("knows today's date in Montréal even when UTC is already tomorrow", () => {
    expect(clinicToday(new Date('2026-11-03T02:00:00Z'))).toBe('2026-11-02');
  });
});

describe('other helpers', () => {
  it('formats Canadian dollars in each language', () => {
    expect(formatPrice(12000, 'en')).toBe('$120.00');
    expect(formatPrice(12000, 'fr').replace(/\s/g, ' ')).toBe('120,00 $');
  });

  it('adds days across month ends and DST changes', () => {
    expect(addDays('2026-10-30', 6)).toBe('2026-11-05');
    expect(addDays('2026-12-30', 3)).toBe('2027-01-02');
  });

  it('groups slots by day in time order', () => {
    const groups = groupByDay([
      { start: '2026-11-02T13:00:00Z' },
      { start: '2026-11-02T14:00:00Z' },
      { start: '2026-11-03T13:00:00Z' },
    ]);
    expect(groups.map(([day, slots]) => [day, slots.length])).toEqual([
      ['2026-11-02', 2],
      ['2026-11-03', 1],
    ]);
  });
});

describe('service order', () => {
  it('puts the initial evaluation first, then sorts by name in the current language', () => {
    const services = [
      { name_fr: 'Traitement', name_en: 'Treatment', is_initial_evaluation: false },
      {
        name_fr: 'Évaluation initiale',
        name_en: 'Initial evaluation',
        is_initial_evaluation: true,
      },
      { name_fr: 'Réadaptation', name_en: 'Rehabilitation', is_initial_evaluation: false },
    ];
    expect(sortServices(services, 'fr').map((s) => s.name_fr)).toEqual([
      'Évaluation initiale',
      'Réadaptation',
      'Traitement',
    ]);
  });
});

describe('time display', () => {
  it('has no leading zero on the hour', () => {
    expect(formatTime('2026-11-02T12:00:00Z', 'en')).toMatch(/^7:00/);
    expect(formatTime('2026-11-02T12:00:00Z', 'fr')).toMatch(/^7 h 00/);
  });
});

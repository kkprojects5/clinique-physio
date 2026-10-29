import { addMinutes, clockTime, dayLabel } from '../format';
import { keysFor, translate } from '../i18n';

describe('times in Montréal (B-BKG-07)', () => {
  it('reads the clinic time before and after the November DST change', () => {
    expect(clockTime('2026-10-26T10:00:00-04:00')).toBe('10:00');
    expect(clockTime('2026-11-02T10:00:00-05:00')).toBe('10:00');
  });

  it('computes the end time, including past the hour', () => {
    expect(addMinutes('10:00', 30)).toBe('10:30');
    expect(addMinutes('10:45', 45)).toBe('11:30');
  });

  it('labels the clinic day, not the phone day, in each language', () => {
    // 23:30 in Montréal on Nov 2 is already Nov 3 in UTC: the label must still say Nov 2.
    expect(dayLabel('2026-11-02T23:30:00-05:00', 'en')).toMatch(/November 2/);
    expect(dayLabel('2026-11-02T23:30:00-05:00', 'fr')).toMatch(/^Lundi 2 novembre/);
  });
});

describe('texts (NFR-10)', () => {
  it('has every text in both languages', () => {
    expect(keysFor('en')).toEqual(keysFor('fr'));
  });

  it('fills in names', () => {
    expect(translate('fr', 'with', { name: 'Anne Lefebvre' })).toBe('avec Anne Lefebvre');
  });
});

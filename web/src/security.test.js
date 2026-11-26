import { describe, expect, it } from 'vitest';

// Challenge B-C4: React writes text, never HTML. The only way around it would be
// dangerouslySetInnerHTML (or innerHTML); this test fails if one ever appears in the code.
const sources = import.meta.glob(['./**/*.{js,jsx}', '!./**/*.test.{js,jsx}'], {
  query: '?raw',
  import: 'default',
  eager: true,
});

describe('no raw HTML in the website (XSS, challenge B-C4)', () => {
  it('reads every source file', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(20);
  });

  it('never inserts HTML from data', () => {
    const offenders = Object.entries(sources)
      .filter(([, code]) => /dangerouslySetInnerHTML|\.innerHTML\s*=|insertAdjacentHTML/.test(code))
      .map(([file]) => file);
    expect(offenders).toEqual([]);
  });

  it('never keeps a token in browser storage', () => {
    const offenders = Object.entries(sources)
      .filter(([, code]) => /(localStorage|sessionStorage)\.setItem\([^)]*token/i.test(code))
      .map(([file]) => file);
    expect(offenders).toEqual([]);
  });
});

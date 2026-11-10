// Fake API for pages used by a logged-in user: answers by "METHOD /path".
import { vi } from 'vitest';
import { SERVICES, THERAPISTS } from './render';

export const PATIENT = { id: 'u1', email: 'marie@example.com', role: 'patient', language: 'fr' };

/** Fake API by "METHOD /path". Each handler returns [status, body]. */
export function mockRoutes(routes, { loggedIn = true, me = PATIENT } = {}) {
  const calls = [];
  const all = {
    'GET /services': () => [200, SERVICES],
    'GET /therapists': () => [200, THERAPISTS],
    'POST /auth/refresh': () => (loggedIn ? [200, { access_token: 'tok' }] : [401, {}]),
    'GET /me': () => [200, me],
    'POST /auth/logout': () => [200, {}],
    ...routes,
  };
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url, options = {}) => {
      const u = new URL(url);
      const key = `${options.method || 'GET'} ${u.pathname.replace('/api/v1', '')}`;
      const body = options.body ? JSON.parse(options.body) : undefined;
      calls.push({ key, body, headers: options.headers || {}, credentials: options.credentials });
      const handler = all[key];
      const [status, data] = handler ? handler(body, u) : [404, {}];
      return { ok: status < 300, status, json: async () => data };
    }),
  );
  return calls;
}

// All calls to the API go through here, so the address is configured in one place.
export const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export async function apiGet(path, params = {}) {
  const url = new URL(`${API_URL}/api/v1${path}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
  });
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new ApiError(response.status, `API error ${response.status}`);
  return response.json();
}

/** POST JSON. Returns { status, data } so pages can show a message for each answer. */
export async function apiPost(path, body) {
  const response = await fetch(`${API_URL}/api/v1${path}`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  return { status: response.status, data };
}

/**
 * Request with the logged-in user's access token. Sends the refresh cookie too
 * (credentials: 'include') and tells the API which app is calling, for the audit log.
 * Returns { status, data }.
 */
export async function authRequest(path, { method = 'GET', body, token } = {}) {
  const headers = { Accept: 'application/json', 'X-Client-App': 'web' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_URL}/api/v1${path}`, {
    method,
    headers,
    credentials: 'include',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => null);
  return { status: response.status, data };
}

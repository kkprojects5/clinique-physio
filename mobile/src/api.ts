import { API_URL } from './config';

export type ErrorKind = 'offline' | 'unauthorized' | 'forbidden' | 'tooMany' | 'other';

export class ApiError extends Error {
  constructor(
    public kind: ErrorKind,
    public status: number,
  ) {
    super(`API error ${status} (${kind})`);
  }
}

export type MyAppointment = {
  id: string;
  start: string;
  end: string;
  start_local: string; // e.g. "2026-11-02T10:00:00-05:00" (Montréal time)
  status: string;
  service: { id: string; name_fr: string; name_en: string; duration_min: number };
  therapist: { id: string; first_name: string; last_name: string };
};

/** Patients get a token; staff accounts need MFA and must use the desktop app or website. */
export type LoginResult = { kind: 'patient'; accessToken: string } | { kind: 'staff' };

function kindFor(status: number): ErrorKind {
  if (status === 401) return 'unauthorized';
  if (status === 403) return 'forbidden';
  if (status === 429) return 'tooMany';
  return 'other';
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  } catch {
    throw new ApiError('offline', 0);
  }
  if (!response.ok) throw new ApiError(kindFor(response.status), response.status);
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<LoginResult> {
  const body = await request<{ access_token?: string; mfa_required?: boolean }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (body.access_token) return { kind: 'patient', accessToken: body.access_token };
  return { kind: 'staff' };
}

export function myAppointments(token: string): Promise<MyAppointment[]> {
  return request<MyAppointment[]>('/me/appointments', {}, token);
}

import { API_URL } from './config';

export type ErrorKind = 'offline' | 'unauthorized' | 'forbidden' | 'conflict' | 'tooMany' | 'other';

export class ApiError extends Error {
  constructor(
    public kind: ErrorKind,
    public status: number,
  ) {
    super(`API error ${status} (${kind})`);
  }
}

export type Exercise = {
  id: string;
  name_fr: string;
  name_en: string;
  description_fr: string;
  description_en: string;
  instructions_fr: string;
  instructions_en: string;
};

export type ProgramItem = {
  id: string;
  exercise: Exercise;
  sets: number;
  reps: number;
  times_per_week: number;
  done_this_week: number;
  done_today: boolean;
};

export type Program = {
  id: string;
  therapist: { id: string; first_name: string; last_name: string };
  start_date: string;
  end_date: string; // first day after the program
  notes: string | null;
  items: ProgramItem[];
};

export type CheckOff = { id: string; program_item_id: string; done_on: string; pain_level: number | null };

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
  if (status === 409) return 'conflict';
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
        'X-Client-App': 'mobile', // recorded in the audit log
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  } catch {
    throw new ApiError('offline', 0);
  }
  if (!response.ok) throw new ApiError(kindFor(response.status), response.status);
  if (response.status === 204) return undefined as T;
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

/** My program in progress today, or null when there is none. */
export function myProgram(token: string): Promise<Program | null> {
  return request<Program | null>('/me/program', {}, token);
}

/** I did this exercise today, with an optional pain level from 0 to 10. */
export function checkOff(token: string, itemId: string, painLevel: number | null): Promise<CheckOff> {
  return request<CheckOff>(
    `/me/program/items/${itemId}/check-off`,
    { method: 'POST', body: JSON.stringify({ pain_level: painLevel }) },
    token,
  );
}

/** Undo today's check-off (a mistake). */
export function undoCheckOff(token: string, checkOffId: string): Promise<void> {
  return request<void>(`/me/program/check-offs/${checkOffId}`, { method: 'DELETE' }, token);
}

// --- Booking (B-BKG-01) ------------------------------------------------------------------

export type Service = {
  id: string;
  name_fr: string;
  name_en: string;
  duration_min: number;
  price_cents: number;
  deposit_cents: number;
  is_initial_evaluation: boolean;
  therapist_ids: string[];
};

export type Therapist = { id: string; first_name: string; last_name: string };

export type Slot = { therapist_id: string; start: string; end: string; start_local: string };

export type Booking = MyAppointment & { hold_expires_at: string | null; deposit_cents: number };

export type PaymentStart = {
  appointment: Booking;
  client_secret: string; // given to Stripe's payment sheet only; never stored or logged
  publishable_key: string;
  amount_cents: number;
  currency: string;
};

export function services(): Promise<Service[]> {
  return request<Service[]>('/services');
}

export function therapists(): Promise<Therapist[]> {
  return request<Therapist[]>('/therapists');
}

/** Free times of one day (Montréal date "2026-11-24"). No therapist: everyone who gives it. */
export function freeSlots(serviceId: string, therapistId: string | null, day: string): Promise<Slot[]> {
  const query = new URLSearchParams({ service_id: serviceId, date_from: day, date_to: day });
  if (therapistId) query.set('therapist_id', therapistId);
  return request<Slot[]>(`/availability?${query.toString()}`);
}

/** Keep the slot 10 minutes while paying. 409 ('conflict') if it was just taken. */
export function hold(token: string, serviceId: string, slot: Slot): Promise<Booking> {
  return request<Booking>(
    '/appointments/hold',
    {
      method: 'POST',
      body: JSON.stringify({ service_id: serviceId, therapist_id: slot.therapist_id, start: slot.start }),
    },
    token,
  );
}

/** Start (or resume) paying the deposit: gives what Stripe's payment sheet needs. */
export function startPayment(token: string, appointmentId: string): Promise<PaymentStart> {
  return request<PaymentStart>(`/appointments/${appointmentId}/pay`, { method: 'POST' }, token);
}

import { fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import LoginScreen from '../screens/LoginScreen';
import AppointmentsScreen from '../screens/AppointmentsScreen';

type FakeResponse = { status: number; body: unknown };

/** Fake network: each call to fetch gets the next prepared answer. */
function mockFetch(...responses: (FakeResponse | 'offline')[]) {
  const calls: { url: string; init: RequestInit }[] = [];
  globalThis.fetch = jest.fn(async (url: string, init: RequestInit = {}) => {
    calls.push({ url, init });
    const next = responses.shift();
    if (!next || next === 'offline') throw new TypeError('Network request failed');
    return { ok: next.status < 400, status: next.status, json: async () => next.body } as Response;
  }) as unknown as typeof fetch;
  return calls;
}

const APPOINTMENT = {
  id: 'a1',
  start: '2026-11-02T15:00:00Z',
  end: '2026-11-02T15:30:00Z',
  start_local: '2026-11-02T10:00:00-05:00',
  status: 'confirmed',
  service: { id: 's1', name_fr: 'Suivi 30 min', name_en: 'Follow-up 30 min', duration_min: 30 },
  therapist: { id: 't1', first_name: 'Anne', last_name: 'Lefebvre' },
};

describe('login screen', () => {
  async function fill(email = 'patient01@example.com', password = 'secret-password') {
    await fireEvent.changeText(screen.getByLabelText('Courriel'), email);
    await fireEvent.changeText(screen.getByLabelText('Mot de passe'), password);
    await fireEvent.press(screen.getByRole('button', { name: 'Se connecter' }));
  }

  it('asks for both fields before calling the API', async () => {
    const calls = mockFetch();
    await render(<LoginScreen language="fr" onLoggedIn={jest.fn()} />);

    await fill('', '');

    expect(screen.getByText('Entrez votre courriel et votre mot de passe.')).toBeTruthy();
    expect(calls).toHaveLength(0);
  });

  it('logs a patient in with the token from the API', async () => {
    const calls = mockFetch({ status: 200, body: { access_token: 'tok', token_type: 'bearer', expires_in: 600 } });
    const onLoggedIn = jest.fn();
    await render(<LoginScreen language="fr" onLoggedIn={onLoggedIn} />);

    await fill();

    await waitFor(() => expect(onLoggedIn).toHaveBeenCalledWith('tok'));
    expect(calls[0].url).toMatch(/\/api\/v1\/auth\/login$/);
    expect(JSON.parse(String(calls[0].init.body))).toEqual({
      email: 'patient01@example.com',
      password: 'secret-password',
    });
  });

  it('sends staff accounts to the desktop app or website', async () => {
    mockFetch({ status: 200, body: { mfa_required: true, mfa_token: 'ticket' } });
    const onLoggedIn = jest.fn();
    await render(<LoginScreen language="fr" onLoggedIn={onLoggedIn} />);

    await fill('accueil1@clinique.example.com');

    expect(await screen.findByText(/compte du personnel/)).toBeTruthy();
    expect(onLoggedIn).not.toHaveBeenCalled();
  });

  it.each([
    [401, 'Courriel ou mot de passe incorrect.'],
    [429, 'Trop de tentatives. Attendez une minute.'],
  ])('explains an HTTP %i error', async (status, message) => {
    mockFetch({ status, body: {} });
    await render(<LoginScreen language="fr" onLoggedIn={jest.fn()} />);

    await fill();

    expect(await screen.findByText(message)).toBeTruthy();
  });

  it('explains when the phone is offline', async () => {
    mockFetch('offline');
    await render(<LoginScreen language="fr" onLoggedIn={jest.fn()} />);

    await fill();

    expect(await screen.findByText(/Impossible de joindre le serveur/)).toBeTruthy();
  });
});

describe('my appointments screen', () => {
  it('shows each appointment with day, Montréal time, service and therapist', async () => {
    const calls = mockFetch({ status: 200, body: [APPOINTMENT] });
    await render(<AppointmentsScreen language="fr" accessToken="tok" onExpired={jest.fn()} onLogout={jest.fn()} />);

    expect(await screen.findByText('10:00–10:30')).toBeTruthy();
    expect(screen.getByText(/^Lundi 2 novembre/)).toBeTruthy();
    expect(screen.getByText('Suivi 30 min')).toBeTruthy();
    expect(screen.getByText('avec Anne Lefebvre')).toBeTruthy();
    expect(screen.getByText('Confirmé')).toBeTruthy();
    expect(calls[0].url).toMatch(/\/api\/v1\/me\/appointments$/);
    expect((calls[0].init.headers as Record<string, string>).Authorization).toBe('Bearer tok');
  });

  it('uses the English service name in English', async () => {
    mockFetch({ status: 200, body: [APPOINTMENT] });
    await render(<AppointmentsScreen language="en" accessToken="tok" onExpired={jest.fn()} onLogout={jest.fn()} />);

    expect(await screen.findByText('Follow-up 30 min')).toBeTruthy();
    expect(screen.getByText('with Anne Lefebvre')).toBeTruthy();
  });

  it('says so when there is nothing upcoming', async () => {
    mockFetch({ status: 200, body: [] });
    await render(<AppointmentsScreen language="fr" accessToken="tok" onExpired={jest.fn()} onLogout={jest.fn()} />);

    expect(await screen.findByText('Aucun rendez-vous à venir.')).toBeTruthy();
  });

  it('goes back to login when the token has expired', async () => {
    mockFetch({ status: 401, body: {} });
    const onExpired = jest.fn();
    await render(<AppointmentsScreen language="fr" accessToken="old" onExpired={onExpired} onLogout={jest.fn()} />);

    await waitFor(() => expect(onExpired).toHaveBeenCalled());
  });

  it('logs out from the button', async () => {
    mockFetch({ status: 200, body: [] });
    const onLogout = jest.fn();
    await render(<AppointmentsScreen language="fr" accessToken="tok" onExpired={jest.fn()} onLogout={onLogout} />);
    await screen.findByText('Aucun rendez-vous à venir.');

    await fireEvent.press(screen.getByRole('button', { name: 'Se déconnecter' }));

    expect(onLogout).toHaveBeenCalled();
  });
});

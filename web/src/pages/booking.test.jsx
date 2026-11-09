import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderAt, SERVICES, THERAPISTS } from '../test/render';
import { safeNext } from './Login';

// Stripe is replaced: no network, no real card form. We check what our pages do with it.
const stripe = { confirmPayment: vi.fn() };
vi.mock('@stripe/stripe-js', () => ({ loadStripe: vi.fn(async () => ({})) }));
vi.mock('@stripe/react-stripe-js', () => ({
  Elements: ({ children }) => children,
  PaymentElement: () => <div>Formulaire de carte Stripe</div>,
  useStripe: () => stripe,
  useElements: () => ({}),
}));

const START = '2030-03-04T14:00:00Z'; // 9:00 in Montréal
const PATIENT = { id: 'u1', email: 'marie@example.com', role: 'patient', language: 'fr' };
const HELD = {
  id: 'a1',
  status: 'pending_payment',
  start: START,
  end: '2030-03-04T15:00:00Z',
  start_local: '2030-03-04T09:00:00-05:00',
  hold_expires_at: '2030-03-04T13:10:00Z',
  deposit_cents: 3000,
  service: { id: 's-eval', name_fr: 'Évaluation initiale', name_en: 'Initial evaluation' },
  therapist: { id: 't-anne', first_name: 'Anne', last_name: 'Lefebvre' },
};

/** Fake API by "METHOD /path". Each handler returns [status, body]. */
function mockRoutes(routes, { loggedIn = true } = {}) {
  const calls = [];
  const all = {
    'GET /services': () => [200, SERVICES],
    'GET /therapists': () => [200, THERAPISTS],
    'POST /auth/refresh': () => (loggedIn ? [200, { access_token: 'tok' }] : [401, {}]),
    'GET /me': () => [200, PATIENT],
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

const bookPath = `/reserver?service=s-eval&therapist=t-anne&start=${encodeURIComponent(START)}`;

beforeEach(() => {
  stripe.confirmPayment.mockReset();
  localStorage.clear();
  sessionStorage.clear();
});

describe('booking from the availability page (B-BKG-01)', () => {
  it('each free time has a Book link with the chosen time', async () => {
    mockRoutes({
      'GET /availability': () => [200, [{ therapist_id: 't-anne', start: START, end: START }]],
    });
    renderAt('/disponibilites?service=s-eval');

    const link = await screen.findByRole('link', { name: /Réserver .* avec Anne Lefebvre/ });
    const href = new URL(link.getAttribute('href'), 'http://x');
    expect(href.pathname).toBe('/reserver');
    expect(href.searchParams.get('start')).toBe(START);
    expect(href.searchParams.get('therapist')).toBe('t-anne');
  });

  it('asks to log in first, then comes back to the booking', async () => {
    mockRoutes(
      {
        'POST /auth/login': () => [200, { access_token: 'tok', token_type: 'bearer' }],
      },
      { loggedIn: false },
    );
    renderAt(bookPath);

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Adresse courriel'), 'marie@example.com');
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'Une-longue-phrase-42');
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }));

    expect(
      await screen.findByRole('heading', { name: 'Réserver un rendez-vous' }),
    ).toBeInTheDocument();
    expect(screen.getByText('30,00 $')).toBeInTheDocument();
  });

  it('holds the time, shows Stripe’s card form, pays and waits for confirmation', async () => {
    let status = 'pending_payment';
    const calls = mockRoutes({
      'POST /appointments/hold': () => [201, { ...HELD, status: 'held' }],
      'POST /appointments/a1/pay': () => [
        200,
        {
          appointment: HELD,
          payment_id: 'p1',
          client_secret: 'pi_1_secret',
          publishable_key: 'pk_test_x',
          amount_cents: 3000,
          currency: 'cad',
        },
      ],
      'GET /me/appointments': () => [200, [{ ...HELD, status }]],
    });
    stripe.confirmPayment.mockImplementation(async () => {
      status = 'confirmed'; // Stripe's webhook arrives
      return {};
    });
    renderAt(bookPath);

    await userEvent.click(
      await screen.findByRole('button', { name: 'Réserver et payer le dépôt' }),
    );
    expect(await screen.findByText('Formulaire de carte Stripe')).toBeInTheDocument();
    expect(screen.getByText(/réservée jusqu’à 8 h 10/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Payer 30,00/ }));

    expect(
      await screen.findByRole('heading', { name: 'Rendez-vous confirmé' }, { timeout: 4000 }),
    ).toBeInTheDocument();
    expect(stripe.confirmPayment.mock.calls[0][0].redirect).toBe('if_required');
    const hold = calls.find((c) => c.key === 'POST /appointments/hold');
    expect(hold.body).toEqual({ service_id: 's-eval', therapist_id: 't-anne', start: START });
    expect(hold.headers.Authorization).toBe('Bearer tok');
    expect(hold.headers['X-Client-App']).toBe('web');
    expect(hold.credentials).toBe('include'); // the refresh cookie goes with the request
  });

  it('keeps asking until Stripe’s confirmation has arrived', async () => {
    let asked = 0;
    mockRoutes({
      // first answer: still waiting for the webhook; second answer: confirmed
      'GET /me/appointments': () => {
        asked += 1;
        return [200, [{ ...HELD, status: asked < 2 ? 'pending_payment' : 'confirmed' }]];
      },
    });
    renderAt('/reserver/termine?rdv=a1');

    expect(
      await screen.findByRole('heading', { name: 'Paiement en cours de confirmation' }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole('heading', { name: 'Rendez-vous confirmé' }, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  it('never stores the session in browser storage', async () => {
    mockRoutes({});
    renderAt(bookPath);
    await screen.findByRole('heading', { name: 'Réserver un rendez-vous' });

    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it('explains when the time was just taken', async () => {
    mockRoutes({
      'POST /appointments/hold': () => [409, { detail: 'This time is no longer available.' }],
    });
    renderAt(bookPath);

    await userEvent.click(
      await screen.findByRole('button', { name: 'Réserver et payer le dépôt' }),
    );

    expect(await screen.findByRole('alert')).toHaveTextContent('vient d’être prise');
    expect(screen.getByRole('link', { name: 'Choisir une autre heure' })).toBeInTheDocument();
  });

  it('explains that a first treatment needs an evaluation', async () => {
    mockRoutes({
      'POST /appointments/hold': () => [
        409,
        { detail: 'A first treatment needs an initial evaluation before it.' },
      ],
    });
    renderAt(bookPath);

    await userEvent.click(
      await screen.findByRole('button', { name: 'Réserver et payer le dépôt' }),
    );

    expect(await screen.findByRole('alert')).toHaveTextContent('évaluation initiale');
  });

  it('says when online payment is switched off', async () => {
    mockRoutes({
      'POST /appointments/hold': () => [201, HELD],
      'POST /appointments/a1/pay': () => [503, {}],
    });
    renderAt(bookPath);

    await userEvent.click(
      await screen.findByRole('button', { name: 'Réserver et payer le dépôt' }),
    );

    expect(await screen.findByRole('alert')).toHaveTextContent('Appelez la clinique');
  });

  it('shows Stripe’s message when the card is declined', async () => {
    mockRoutes({
      'POST /appointments/hold': () => [201, HELD],
      'POST /appointments/a1/pay': () => [
        200,
        {
          appointment: HELD,
          payment_id: 'p1',
          client_secret: 's',
          publishable_key: 'pk_test_x',
          amount_cents: 3000,
          currency: 'cad',
        },
      ],
    });
    stripe.confirmPayment.mockResolvedValue({ error: { message: 'Votre carte a été refusée.' } });
    renderAt(bookPath);

    await userEvent.click(
      await screen.findByRole('button', { name: 'Réserver et payer le dépôt' }),
    );
    await userEvent.click(await screen.findByRole('button', { name: /Payer/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Votre carte a été refusée.');
  });
});

describe('staff login with the 6-digit code', () => {
  it('asks for the code after the password', async () => {
    const calls = mockRoutes(
      {
        'POST /auth/login': () => [
          200,
          { mfa_required: true, mfa_setup_required: false, mfa_token: 'ticket', expires_in: 300 },
        ],
        'POST /auth/mfa/verify': () => [200, { access_token: 'tok' }],
        'GET /me': () => [200, { ...PATIENT, role: 'therapist' }],
      },
      { loggedIn: false },
    );
    renderAt('/connexion?next=/equipe');

    await userEvent.type(
      await screen.findByLabelText('Adresse courriel'),
      'anne@clinique.example.com',
    );
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'Une-longue-phrase-42');
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }));
    await userEvent.type(await screen.findByLabelText('Code à 6 chiffres'), '123456');
    await userEvent.click(screen.getByRole('button', { name: 'Vérifier' }));

    expect(await screen.findByRole('heading', { name: 'Notre équipe' })).toBeInTheDocument();
    expect(calls.find((c) => c.key === 'POST /auth/mfa/verify').body).toEqual({
      mfa_token: 'ticket',
      code: '123456',
    });
  });

  it('shows a clear message for a wrong password', async () => {
    mockRoutes({ 'POST /auth/login': () => [401, {}] }, { loggedIn: false });
    renderAt('/connexion');

    await userEvent.type(await screen.findByLabelText('Adresse courriel'), 'x@example.com');
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'wrong-password-123');
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('incorrect');
  });

  it('only sends users back to pages of this site', () => {
    expect(safeNext('/reserver?x=1')).toBe('/reserver?x=1');
    expect(safeNext('https://evil.example.com')).toBe('/mes-rendez-vous');
    expect(safeNext('//evil.example.com')).toBe('/mes-rendez-vous');
    expect(safeNext(null)).toBe('/mes-rendez-vous');
  });
});

describe('my appointments (B-BKG-06)', () => {
  const inDays = (days) => new Date(Date.now() + days * 24 * 3600 * 1000).toISOString();

  it('cancels more than 24 hours before and says the deposit is refunded', async () => {
    const appointment = { ...HELD, status: 'confirmed', start: inDays(5) };
    const calls = mockRoutes({
      'GET /me/appointments': () => [200, [appointment]],
      'POST /appointments/a1/cancel': () => [
        200,
        { appointment: { ...appointment, status: 'cancelled_by_patient' }, deposit_refunded: true },
      ],
    });
    renderAt('/mes-rendez-vous');

    expect(await screen.findByText('Confirmé')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Changer l’heure' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Annuler' }));
    expect(screen.getByRole('alert')).toHaveTextContent('votre dépôt sera remboursé');
    await userEvent.click(screen.getByRole('button', { name: 'Oui, annuler' }));

    expect(
      await screen.findByText(/Votre dépôt sera remboursé sur votre carte/),
    ).toBeInTheDocument();
    expect(calls.some((c) => c.key === 'POST /appointments/a1/cancel')).toBe(true);
  });

  it('warns that the deposit is kept less than 24 hours before', async () => {
    mockRoutes({
      'GET /me/appointments': () => [200, [{ ...HELD, status: 'confirmed', start: inDays(0.5) }]],
    });
    renderAt('/mes-rendez-vous');

    await userEvent.click(await screen.findByRole('button', { name: 'Annuler' }));

    expect(screen.getByRole('alert')).toHaveTextContent('conservé comme frais');
    expect(screen.queryByRole('link', { name: 'Changer l’heure' })).not.toBeInTheDocument();
  });

  it('says nothing was cancelled when the refund fails', async () => {
    mockRoutes({
      'GET /me/appointments': () => [200, [{ ...HELD, status: 'confirmed', start: inDays(5) }]],
      'POST /appointments/a1/cancel': () => [502, { detail: 'refund failed' }],
    });
    renderAt('/mes-rendez-vous');

    await userEvent.click(await screen.findByRole('button', { name: 'Annuler' }));
    await userEvent.click(screen.getByRole('button', { name: 'Oui, annuler' }));

    expect(await screen.findByText(/rien n’a été annulé/)).toBeInTheDocument();
  });

  it('reschedules through the availability page', async () => {
    const calls = mockRoutes({
      'POST /appointments/a1/reschedule': () => [200, HELD],
      'GET /me/appointments': () => [200, []],
    });
    renderAt(`${bookPath}&reschedule=a1`);

    await userEvent.click(await screen.findByRole('button', { name: 'Confirmer le changement' }));

    expect(await screen.findByText('Votre rendez-vous a été changé.')).toBeInTheDocument();
    expect(calls.find((c) => c.key === 'POST /appointments/a1/reschedule').body).toEqual({
      start: START,
      therapist_id: 't-anne',
    });
  });
});

describe('registration (B-AUTH-01)', () => {
  it('sends the form with the consents', async () => {
    const calls = mockRoutes({ 'POST /auth/register': () => [202, {}] }, { loggedIn: false });
    renderAt('/inscription');

    await userEvent.type(await screen.findByLabelText('Prénom'), 'Marie');
    await userEvent.type(screen.getByLabelText('Nom'), 'Tremblay');
    await userEvent.type(screen.getByLabelText('Date de naissance'), '1990-05-12');
    await userEvent.type(screen.getByLabelText('Téléphone'), '514-555-0101');
    await userEvent.type(screen.getByLabelText('Adresse courriel'), 'marie@example.com');
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'Une-longue-phrase-42');
    await userEvent.click(screen.getByLabelText(/politique de confidentialité/));
    await userEvent.click(screen.getByRole('button', { name: 'Créer mon compte' }));

    expect(await screen.findByRole('status')).toHaveTextContent('Compte créé');
    const sent = calls.find((c) => c.key === 'POST /auth/register').body;
    expect(sent).toMatchObject({
      first_name: 'Marie',
      accept_privacy_policy: true,
      accept_electronic_comms: false,
      language: 'fr',
    });
    expect(sent).not.toHaveProperty('emergency_contact'); // empty optional field not sent
  });
});

describe('navigation', () => {
  it('shows My appointments and Log out when logged in', async () => {
    mockRoutes({ 'GET /me/appointments': () => [200, []] });
    renderAt('/');

    expect(await screen.findByRole('link', { name: 'Mes rendez-vous' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Déconnexion' }));
    await waitFor(() =>
      expect(screen.getByRole('link', { name: 'Connexion' })).toBeInTheDocument(),
    );
  });
});

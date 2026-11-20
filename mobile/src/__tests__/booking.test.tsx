import { fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import { initPaymentSheet, initStripe, presentPaymentSheet } from '@stripe/stripe-react-native';
import BookScreen from '../screens/BookScreen';
import { clinicToday, money, nextDays } from '../format';

// Stripe's native payment sheet does not exist in tests: a fake answers for it.
jest.mock('@stripe/stripe-react-native', () => ({
  initStripe: jest.fn(async () => undefined),
  initPaymentSheet: jest.fn(async () => ({})),
  presentPaymentSheet: jest.fn(async () => ({})),
}));

const TREATMENT = {
  id: 's1',
  name_fr: 'Traitement de suivi 30 min',
  name_en: 'Follow-up treatment 30 min',
  duration_min: 30,
  price_cents: 8000,
  deposit_cents: 2000,
  is_initial_evaluation: false,
  therapist_ids: ['t-anne', 't-sophie'],
};
const TEAM = [
  { id: 't-anne', first_name: 'Anne', last_name: 'Lefebvre' },
  { id: 't-sophie', first_name: 'Sophie', last_name: 'Nguyen' },
  { id: 't-marc', first_name: 'Marc', last_name: 'Tremblay' }, // does not give this service
];
const TODAY = clinicToday();
const SLOT = {
  therapist_id: 't-anne',
  start: `${TODAY}T15:00:00Z`,
  end: `${TODAY}T15:30:00Z`,
  start_local: `${TODAY}T10:00:00-05:00`,
};
const BOOKING = {
  id: 'a1',
  status: 'held',
  start: SLOT.start,
  end: SLOT.end,
  start_local: SLOT.start_local,
  hold_expires_at: null,
  deposit_cents: 2000,
  service: { id: 's1', name_fr: TREATMENT.name_fr, name_en: TREATMENT.name_en, duration_min: 30 },
  therapist: TEAM[0],
};

type Handler = (url: string, init: RequestInit) => { status: number; body?: unknown };

/** Fake API answering by "METHOD /path" (without the query string). */
function mockApi(extra: Record<string, Handler> = {}) {
  const calls: { key: string; url: string; init: RequestInit }[] = [];
  const routes: Record<string, Handler> = {
    'GET /services': () => ({ status: 200, body: [TREATMENT] }),
    'GET /therapists': () => ({ status: 200, body: TEAM }),
    'GET /availability': () => ({ status: 200, body: [SLOT] }),
    'POST /appointments/hold': () => ({ status: 201, body: BOOKING }),
    'POST /appointments/a1/pay': () => ({
      status: 200,
      body: {
        appointment: BOOKING,
        payment_id: 'pay1',
        client_secret: 'pi_1_secret_test',
        publishable_key: 'pk_test_fake',
        amount_cents: 2000,
        currency: 'cad',
      },
    }),
    'GET /me/appointments': () => ({ status: 200, body: [{ ...BOOKING, status: 'confirmed' }] }),
    ...extra,
  };
  globalThis.fetch = jest.fn(async (url: string, init: RequestInit = {}) => {
    const path = new URL(url).pathname.replace('/api/v1', '');
    const key = `${init.method ?? 'GET'} ${path}`;
    calls.push({ key, url, init });
    const handler = routes[key];
    const { status, body } = handler ? handler(url, init) : { status: 404, body: {} };
    return { ok: status < 400, status, json: async () => body } as Response;
  }) as unknown as typeof fetch;
  return calls;
}

async function show(extra?: Record<string, Handler>) {
  const calls = mockApi(extra);
  const onBooked = jest.fn();
  const onExpired = jest.fn();
  await render(
    <BookScreen language="fr" accessToken="tok" onBooked={onBooked} onExpired={onExpired} pollMs={0} />,
  );
  return { calls, onBooked, onExpired };
}

/** Service, first available, then today's 10:00 slot. */
async function chooseUpToReview() {
  fireEvent.press(await screen.findByText('Traitement de suivi 30 min'));
  fireEvent.press(await screen.findByText('Premier disponible'));
  fireEvent.press(await screen.findByText('10:00 · Anne Lefebvre'));
  await screen.findByText('4. Vérifiez et payez le dépôt');
}

beforeEach(() => jest.clearAllMocks());

describe('booking on the phone (B-BKG-01)', () => {
  it('shows each service with its length, price and deposit', async () => {
    await show();

    expect(await screen.findByText('Traitement de suivi 30 min')).toBeTruthy();
    expect(
      screen.getByText(`30 min · ${money(8000, 'fr')} · dépôt ${money(2000, 'fr')}`),
    ).toBeTruthy();
  });

  it('offers first available and only the therapists who give the service', async () => {
    await show();

    fireEvent.press(await screen.findByText('Traitement de suivi 30 min'));

    expect(await screen.findByText('Premier disponible')).toBeTruthy();
    expect(screen.getByText('Anne Lefebvre')).toBeTruthy();
    expect(screen.getByText('Sophie Nguyen')).toBeTruthy();
    expect(screen.queryByText('Marc Tremblay')).toBeNull();
  });

  it('asks the free times of the chosen day, for the chosen therapist', async () => {
    const { calls } = await show();
    fireEvent.press(await screen.findByText('Traitement de suivi 30 min'));
    fireEvent.press(await screen.findByText('Sophie Nguyen'));
    await screen.findByText('10:00 · Anne Lefebvre');

    const tomorrow = nextDays(TODAY, 2)[1];
    const label = screen.getAllByRole('button').find((b) => b.props.accessibilityState?.selected === false);
    expect(label).toBeTruthy();
    fireEvent.press(label!);

    await waitFor(() => {
      const asked = calls.filter((c) => c.key === 'GET /availability').map((c) => new URL(c.url).searchParams);
      expect(asked[0].get('date_from')).toBe(TODAY);
      expect(asked[0].get('therapist_id')).toBe('t-sophie');
      expect(asked[1].get('date_from')).toBe(tomorrow);
    });
  });

  it('says so when a day has no free time', async () => {
    await show({ 'GET /availability': () => ({ status: 200, body: [] }) });
    fireEvent.press(await screen.findByText('Traitement de suivi 30 min'));
    fireEvent.press(await screen.findByText('Premier disponible'));

    expect(await screen.findByText(/Aucune heure libre ce jour-là/)).toBeTruthy();
  });

  it('holds the slot, pays with the payment sheet and waits for the confirmation', async () => {
    const { calls, onBooked } = await show();
    await chooseUpToReview();

    fireEvent.press(screen.getByText(`Payer ${money(2000, 'fr')} et réserver`));

    expect(await screen.findByText('Rendez-vous confirmé ✓')).toBeTruthy();
    const held = calls.find((c) => c.key === 'POST /appointments/hold')!;
    expect(JSON.parse(held.init.body as string)).toEqual({
      service_id: 's1',
      therapist_id: 't-anne',
      start: SLOT.start,
    });
    expect(initStripe).toHaveBeenCalledWith({ publishableKey: 'pk_test_fake' });
    expect(initPaymentSheet).toHaveBeenCalledWith(
      expect.objectContaining({ paymentIntentClientSecret: 'pi_1_secret_test' }),
    );
    expect(presentPaymentSheet).toHaveBeenCalled();

    fireEvent.press(screen.getByText('Voir mes rendez-vous'));
    expect(onBooked).toHaveBeenCalled();
  });

  it('keeps the hold when the payment is cancelled and lets the patient try again', async () => {
    (presentPaymentSheet as jest.Mock).mockResolvedValueOnce({
      error: { code: 'Canceled', message: 'cancelled' },
    });
    const { calls } = await show();
    await chooseUpToReview();

    fireEvent.press(screen.getByText(`Payer ${money(2000, 'fr')} et réserver`));

    expect(await screen.findByText(/Paiement annulé/)).toBeTruthy();
    fireEvent.press(screen.getByText('Réessayer le paiement'));

    expect(await screen.findByText('Rendez-vous confirmé ✓')).toBeTruthy();
    expect(calls.filter((c) => c.key === 'POST /appointments/hold')).toHaveLength(1); // held once
    expect(calls.filter((c) => c.key === 'POST /appointments/a1/pay')).toHaveLength(2);
  });

  it('goes back to the times when the slot was just taken', async () => {
    await show({ 'POST /appointments/hold': () => ({ status: 409, body: {} }) });
    await chooseUpToReview();

    fireEvent.press(screen.getByText(`Payer ${money(2000, 'fr')} et réserver`));

    expect(await screen.findByText(/Cette heure vient d’être prise/)).toBeTruthy();
    expect(screen.getByText('3. Choisissez le jour et l’heure')).toBeTruthy();
    expect(presentPaymentSheet).not.toHaveBeenCalled();
  });

  it('explains when online payment is switched off', async () => {
    await show({ 'POST /appointments/a1/pay': () => ({ status: 503, body: {} }) });
    await chooseUpToReview();

    fireEvent.press(screen.getByText(`Payer ${money(2000, 'fr')} et réserver`));

    expect(await screen.findByText(/paiement en ligne n’est pas disponible/)).toBeTruthy();
  });

  it('says the confirmation is coming when Stripe is slow', async () => {
    await show({ 'GET /me/appointments': () => ({ status: 200, body: [BOOKING] }) }); // still held
    await chooseUpToReview();

    fireEvent.press(screen.getByText(`Payer ${money(2000, 'fr')} et réserver`));

    expect(await screen.findByText(/La confirmation peut prendre une minute/)).toBeTruthy();
  });

  it('goes back to login when the session expired', async () => {
    const { onExpired } = await show({ 'POST /appointments/hold': () => ({ status: 401, body: {} }) });
    await chooseUpToReview();

    fireEvent.press(screen.getByText(`Payer ${money(2000, 'fr')} et réserver`));

    await waitFor(() => expect(onExpired).toHaveBeenCalled());
  });
});

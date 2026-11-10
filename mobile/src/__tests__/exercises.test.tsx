import { fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import ExercisesScreen from '../screens/ExercisesScreen';
import { dayBefore } from '../format';

type FakeResponse = { status: number; body?: unknown };

/** Fake network: each call to fetch gets the next prepared answer. */
function mockFetch(...responses: FakeResponse[]) {
  const calls: { url: string; init: RequestInit }[] = [];
  globalThis.fetch = jest.fn(async (url: string, init: RequestInit = {}) => {
    calls.push({ url, init });
    const next = responses.shift();
    if (!next) throw new TypeError('Network request failed');
    return {
      ok: next.status < 400,
      status: next.status,
      json: async () => next.body,
    } as Response;
  }) as unknown as typeof fetch;
  return calls;
}

const item = (extra = {}) => ({
  id: 'i1',
  exercise: {
    id: 'e1',
    name_fr: 'Pont fessier',
    name_en: 'Glute bridge',
    description_fr: 'Renforce les fessiers.',
    description_en: 'Strengthens the glutes.',
    instructions_fr: 'Couché sur le dos, soulevez le bassin.',
    instructions_en: 'Lie on your back, lift your hips.',
  },
  sets: 3,
  reps: 12,
  times_per_week: 3,
  done_this_week: 1,
  done_today: false,
  ...extra,
});

const program = (extra = {}) => ({
  id: 'p1',
  therapist: { id: 't1', first_name: 'Anne', last_name: 'Lefebvre' },
  start_date: '2026-11-09',
  end_date: '2026-12-07',
  notes: 'Le matin, sans douleur forte.',
  items: [item()],
  ...extra,
});

async function show(...responses: FakeResponse[]) {
  const calls = mockFetch(...responses);
  const onExpired = jest.fn();
  await render(<ExercisesScreen language="fr" accessToken="tok" onExpired={onExpired} />);
  return { calls, onExpired };
}

describe('exercises screen (B-EXE-03)', () => {
  it('shows my program in progress', async () => {
    const { calls } = await show({ status: 200, body: program() });

    expect(await screen.findByText('Pont fessier')).toBeTruthy();
    expect(screen.getByText('3 séries × 12')).toBeTruthy();
    expect(screen.getByText('Cette semaine : 1 / 3')).toBeTruthy();
    expect(screen.getByText(/Programme de Anne Lefebvre, jusqu’au Dimanche 6 décembre/)).toBeTruthy();
    expect(screen.getByText('Le matin, sans douleur forte.')).toBeTruthy();
    const headers = calls[0].init.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer tok');
    expect(headers['X-Client-App']).toBe('mobile');
  });

  it('says when there is no program', async () => {
    await show({ status: 200, body: null });

    expect(await screen.findByText(/Aucun programme d’exercices en cours/)).toBeTruthy();
  });

  it('shows how to do the exercise on demand', async () => {
    await show({ status: 200, body: program() });

    await fireEvent.press(await screen.findByRole('button', { name: 'Comment faire' }));

    expect(screen.getByText('Couché sur le dos, soulevez le bassin.')).toBeTruthy();
  });

  it('checks off with the pain level, then can undo it today', async () => {
    const { calls } = await show(
      { status: 200, body: program() },
      { status: 201, body: { id: 'log1', program_item_id: 'i1', done_on: '2026-11-09', pain_level: 3 } },
      { status: 200, body: program({ items: [item({ done_today: true, done_this_week: 2 })] }) },
      { status: 204 },
      { status: 200, body: program() },
    );

    await fireEvent.press(await screen.findByRole('button', { name: /J’ai fait cet exercice/ }));
    expect(screen.getByText(/Douleur ressentie/)).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: 'Douleur 3 sur 10' }));

    expect(await screen.findByText('Fait aujourd’hui ✓')).toBeTruthy();
    expect(screen.getByText('Cette semaine : 2 / 3')).toBeTruthy();
    expect(calls[1].url).toMatch(/\/me\/program\/items\/i1\/check-off$/);
    expect(JSON.parse(calls[1].init.body as string)).toEqual({ pain_level: 3 });

    await fireEvent.press(screen.getByRole('button', { name: /Annuler/ }));
    await waitFor(() => expect(calls[3].init.method).toBe('DELETE'));
    expect(calls[3].url).toMatch(/\/me\/program\/check-offs\/log1$/);
    expect(await screen.findByRole('button', { name: /J’ai fait cet exercice/ })).toBeTruthy();
  });

  it('can skip the pain level', async () => {
    const { calls } = await show(
      { status: 200, body: program() },
      { status: 201, body: { id: 'log1', program_item_id: 'i1', done_on: '2026-11-09', pain_level: null } },
      { status: 200, body: program({ items: [item({ done_today: true })] }) },
    );

    await fireEvent.press(await screen.findByRole('button', { name: /J’ai fait cet exercice/ }));
    await fireEvent.press(screen.getByRole('button', { name: 'Passer' }));

    await waitFor(() => expect(calls).toHaveLength(3));
    expect(JSON.parse(calls[1].init.body as string)).toEqual({ pain_level: null });
  });

  it('says when it was already done today', async () => {
    await show(
      { status: 200, body: program() },
      { status: 409, body: { detail: 'Already checked off today.' } },
      { status: 200, body: program({ items: [item({ done_today: true })] }) },
    );

    await fireEvent.press(await screen.findByRole('button', { name: /J’ai fait cet exercice/ }));
    await fireEvent.press(screen.getByRole('button', { name: 'Douleur 0 sur 10' }));

    expect(await screen.findByText('Déjà fait aujourd’hui.')).toBeTruthy();
    expect(screen.getByText('Fait aujourd’hui ✓')).toBeTruthy();
  });

  it('asks to log in again when the session expired', async () => {
    const { onExpired } = await show({ status: 401, body: {} });

    await waitFor(() => expect(onExpired).toHaveBeenCalled());
  });

  it('every pain button is big enough to tap (48 dp)', async () => {
    await show({ status: 200, body: program() });

    await fireEvent.press(await screen.findByRole('button', { name: /J’ai fait cet exercice/ }));

    const button = screen.getByRole('button', { name: 'Douleur 10 sur 10' });
    const style = Array.isArray(button.props.style) ? Object.assign({}, ...button.props.style) : button.props.style;
    expect(style.width).toBeGreaterThanOrEqual(48);
    expect(style.height).toBeGreaterThanOrEqual(48);
  });
});

describe('program dates', () => {
  it('shows the last day of the program', () => {
    expect(dayBefore('2026-12-07')).toBe('2026-12-06');
    expect(dayBefore('2027-01-01')).toBe('2026-12-31');
    expect(dayBefore('2028-03-01')).toBe('2028-02-29');
  });
});

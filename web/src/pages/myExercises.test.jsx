import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { mockRoutes } from '../test/routes';
import { renderAt } from '../test/render';

const BRIDGE = {
  id: 'i1',
  exercise: {
    id: 'e1',
    name_fr: 'Pont fessier',
    name_en: 'Glute bridge',
    description_fr: 'Renforce les fessiers.',
    description_en: 'Strengthens the glutes.',
    instructions_fr: 'Couché sur le dos, soulevez le bassin.',
    instructions_en: 'Lying on your back, lift your hips.',
    image_url: null,
    default_sets: 3,
    default_reps: 10,
  },
  sets: 3,
  reps: 12,
  times_per_week: 5,
  done_total: 4,
  planned_total: 20,
  done_this_week: 2,
  done_today: false,
};
const PROGRAM = {
  id: 'pr1',
  patient_id: 'p1',
  therapist: { id: 't1', first_name: 'Anne', last_name: 'Lefebvre' },
  start_date: '2026-11-09',
  end_date: '2026-12-07',
  weeks: 4,
  notes: 'Faites les exercices le matin.',
  adherence_percent: 20,
  items: [BRIDGE],
};

describe('my exercises on the website (B-EXE-03)', () => {
  it('shows my program with the dose, this week and the therapist', async () => {
    mockRoutes({ 'GET /me/program': () => [200, PROGRAM] });
    renderAt('/mes-exercices');

    expect(await screen.findByRole('heading', { name: 'Pont fessier' })).toBeInTheDocument();
    expect(screen.getByText(/3 séries de 12 répétitions, 5 fois par semaine/)).toBeInTheDocument();
    expect(screen.getByText('Cette semaine : 2 sur 5')).toBeInTheDocument();
    expect(screen.getByText(/Programme de Anne Lefebvre/)).toBeInTheDocument();
    expect(screen.getByText(/20 % du programme/)).toBeInTheDocument();
  });

  it('says so when there is no program', async () => {
    mockRoutes({ 'GET /me/program': () => [200, null] });
    renderAt('/mes-exercices');

    expect(await screen.findByText(/pas de programme d’exercices en cours/)).toBeInTheDocument();
  });

  it('checks off with the pain level, then can undo today', async () => {
    let doneToday = false;
    const calls = mockRoutes({
      'GET /me/program': () => [200, { ...PROGRAM, items: [{ ...BRIDGE, done_today: doneToday }] }],
      'POST /me/program/items/i1/check-off': () => {
        doneToday = true;
        return [201, { id: 'log1', program_item_id: 'i1', done_on: '2026-11-19', pain_level: 3 }];
      },
      'DELETE /me/program/check-offs/log1': () => {
        doneToday = false;
        return [204, null];
      },
    });
    renderAt('/mes-exercices');

    await userEvent.selectOptions(await screen.findByLabelText(/Douleur ressentie/), '3');
    await userEvent.click(screen.getByRole('button', { name: 'C’est fait : Pont fessier' }));

    expect(await screen.findByText(/Fait aujourd’hui/)).toBeInTheDocument();
    const sent = calls.find((c) => c.key === 'POST /me/program/items/i1/check-off');
    expect(sent.body).toEqual({ pain_level: 3 });

    await userEvent.click(screen.getByRole('button', { name: 'Annuler' }));

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'C’est fait : Pont fessier' })).toBeInTheDocument(),
    );
    expect(calls.some((c) => c.key === 'DELETE /me/program/check-offs/log1')).toBe(true);
  });

  it('sends no pain level when the patient prefers not to say', async () => {
    const calls = mockRoutes({
      'GET /me/program': () => [200, PROGRAM],
      'POST /me/program/items/i1/check-off': () => [201, { id: 'log1' }],
    });
    renderAt('/mes-exercices');

    await userEvent.click(await screen.findByRole('button', { name: 'C’est fait : Pont fessier' }));

    await waitFor(() =>
      expect(calls.find((c) => c.key === 'POST /me/program/items/i1/check-off')?.body).toEqual({
        pain_level: null,
      }),
    );
  });

  it('explains when the exercise was already checked off (e.g. on the phone)', async () => {
    mockRoutes({
      'GET /me/program': () => [200, PROGRAM],
      'POST /me/program/items/i1/check-off': () => [409, { detail: 'Already checked off today.' }],
    });
    renderAt('/mes-exercices');

    await userEvent.click(await screen.findByRole('button', { name: 'C’est fait : Pont fessier' }));

    expect(await screen.findByText('Cet exercice est déjà coché aujourd’hui.')).toBeInTheDocument();
  });
});

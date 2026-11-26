import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderAt } from '../test/render';
import { mockRoutes } from '../test/routes';
import { clinicIso } from '../utils/format';

const THERAPIST = { id: 'u9', email: 'anne@clinique.example.com', role: 'therapist' };
const AVAILABILITY = {
  rules: [{ weekday: 1, start_time: '08:00:00', end_time: '12:00:00' }],
  exceptions: [
    {
      id: 'x1',
      starts_at: '2026-12-01T13:00:00Z',
      ends_at: '2026-12-01T22:00:00Z',
      reason: 'formation',
    },
  ],
};

function routes(extra = {}) {
  return mockRoutes(
    {
      'GET /therapist/availability': () => [200, AVAILABILITY],
      'GET /therapist/me': () => [200, { first_name: 'Anne', last_name: 'Lefebvre' }],
      'GET /therapist/patients': () => [200, []],
      ...extra,
    },
    { me: THERAPIST },
  );
}

describe('my hours and time off (B-AVL-02)', () => {
  it('is linked from the workspace and shows the weekly hours and time off', async () => {
    routes();
    renderAt('/espace-therapeute');

    await userEvent.click(await screen.findByRole('link', { name: 'Mes heures et congés' }));

    expect(await screen.findByDisplayValue('12:00')).toBeInTheDocument(); // Monday 08:00-12:00
    expect(screen.getByText(/— formation/)).toBeInTheDocument();
  });

  it('adds hours and saves the whole week', async () => {
    const calls = routes({
      'PUT /therapist/availability': (body) => [
        200,
        {
          ...AVAILABILITY,
          rules: body.rules.map((r) => ({
            ...r,
            start_time: `${r.start_time}:00`,
            end_time: `${r.end_time}:00`,
          })),
        },
      ],
    });
    renderAt('/espace-therapeute/heures');

    await userEvent.click(await screen.findByRole('button', { name: 'Ajouter une plage' }));
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer les heures' }));

    await screen.findByText('Heures enregistrées.');
    expect(calls.find((c) => c.key === 'PUT /therapist/availability').body.rules).toEqual([
      { weekday: 1, start_time: '08:00', end_time: '12:00' },
      { weekday: 1, start_time: '09:00', end_time: '17:00' },
    ]);
  });

  it('adds time off with the clinic time zone and removes it', async () => {
    const calls = routes({
      'POST /therapist/availability/exceptions': (body) => [201, { id: 'x2', ...body }],
      'DELETE /therapist/availability/exceptions/x1': () => [204, null],
    });
    renderAt('/espace-therapeute/heures');

    await userEvent.type(await screen.findByLabelText('Motif (facultatif)'), 'vacances');
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter le congé' }));
    await screen.findByText(/Congé ajouté/);
    await userEvent.click(screen.getAllByRole('button', { name: 'Retirer' }).at(-1));

    const sent = calls.find((c) => c.key === 'POST /therapist/availability/exceptions').body;
    expect(sent.reason).toBe('vacances');
    expect(sent.starts_at).toMatch(/T08:00:00-0[45]:00$/);
    await waitFor(() =>
      expect(calls.some((c) => c.key === 'DELETE /therapist/availability/exceptions/x1')).toBe(
        true,
      ),
    );
  });
});

describe('clinicIso', () => {
  it("uses Montréal's offset of that day, across the DST changes", () => {
    expect(clinicIso('2026-11-02', '08:00')).toBe('2026-11-02T08:00:00-05:00');
    expect(clinicIso('2026-10-30', '08:00')).toBe('2026-10-30T08:00:00-04:00');
    expect(clinicIso('2027-03-15', '09:30')).toBe('2027-03-15T09:30:00-04:00');
  });
});

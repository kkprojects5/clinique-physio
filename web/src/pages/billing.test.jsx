import { afterEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { mockRoutes } from '../test/routes';
import { renderAt } from '../test/render';

const ADMIN = { id: 'u-admin', email: 'admin@clinique.example.com', role: 'admin', language: 'fr' };

const REPORT = {
  week_start: '2026-11-23',
  week_end: '2026-11-29',
  appointments: 5,
  seen: 2,
  no_shows: 1,
  cancelled_by_patient: 1,
  cancelled_by_clinic: 0,
  confirmed: 1,
  no_show_rate: 0.333,
  occupancy: 0.25,
  revenue_cents: 6000,
  deposits_cents: 2000,
  desk_cents: 6000,
  refunds_cents: 2000,
  therapists: [
    {
      therapist_id: 't-anne',
      first_name: 'Anne',
      last_name: 'Lefebvre',
      appointments: 4,
      seen: 2,
      no_shows: 1,
      booked_minutes: 90,
      working_minutes: 240,
      occupancy: 0.375,
    },
  ],
};

const RECEIPT = {
  appointment_id: 'a9',
  start: '2026-11-16T15:00:00Z',
  service_fr: 'Traitement de suivi 30 min',
  service_en: 'Follow-up treatment 30 min',
  therapist: 'Anne Lefebvre',
  paid_cents: 8000,
  receipt_number: 'R-1A2B3C4D',
};

afterEach(() => vi.unstubAllGlobals());

describe('weekly report (B-ADM-02)', () => {
  function reportRoutes() {
    return mockRoutes(
      {
        'GET /admin/services': () => [200, []],
        'GET /admin/reports/weekly': () => [200, REPORT],
      },
      { me: ADMIN },
    );
  }

  it('shows the week’s totals and each therapist', async () => {
    reportRoutes();
    renderAt('/administration');

    await userEvent.click(await screen.findByRole('tab', { name: 'Rapports' }));

    expect(await screen.findByText(/Semaine du 23 nov/)).toBeInTheDocument();
    expect(screen.getByText('Taux d’occupation', { selector: 'dt' }).nextSibling).toHaveTextContent(
      '25 %',
    );
    expect(screen.getByText('Taux d’absence', { selector: 'dt' }).nextSibling).toHaveTextContent(
      '33 %',
    );
    const row = screen.getByRole('rowheader', { name: 'Anne Lefebvre' }).closest('tr');
    expect(within(row).getByText('1,5 h / 4 h')).toBeInTheDocument();
    expect(within(row).getByText('38 %')).toBeInTheDocument();
  });

  it('asks for the previous week', async () => {
    const calls = reportRoutes();
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Rapports' }));
    await screen.findByText(/Semaine du/);

    await userEvent.click(screen.getByRole('button', { name: '◀ Semaine précédente' }));

    await waitFor(() => {
      const weeks = calls
        .filter((c) => c.key === 'GET /admin/reports/weekly')
        .map((c) => new URLSearchParams(c.url).get('week'));
      expect(new Set(weeks).size).toBe(2);
    });
  });
});

describe('receipts for the insurer (B-BKG-10)', () => {
  it('lists past visits and downloads the PDF', async () => {
    const created = vi.fn(() => 'blob:receipt');
    vi.stubGlobal('URL', Object.assign(globalThis.URL, { createObjectURL: created }));
    URL.revokeObjectURL = vi.fn();
    const calls = mockRoutes({
      'GET /me/appointments': () => [200, []],
      'GET /me/receipts': () => [200, [RECEIPT]],
      'GET /appointments/a9/receipt': () => [200, '%PDF'],
    });
    renderAt('/mes-rendez-vous');

    expect(await screen.findByText('Mes reçus')).toBeInTheDocument();
    expect(screen.getByText(/R-1A2B3C4D/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Télécharger le reçu (PDF)' }));

    await waitFor(() => expect(created).toHaveBeenCalled());
    const asked = calls.find((c) => c.key === 'GET /appointments/a9/receipt');
    expect(asked.headers.Accept).toBe('application/pdf');
  });

  it('shows nothing when there is no receipt yet', async () => {
    mockRoutes({
      'GET /me/appointments': () => [200, []],
      'GET /me/receipts': () => [200, []],
    });
    renderAt('/mes-rendez-vous');

    expect(
      await screen.findByText('Aucun rendez-vous à venir.', { exact: false }),
    ).toBeInTheDocument();
    expect(screen.queryByText('Mes reçus')).not.toBeInTheDocument();
  });
});

import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { mockRoutes } from '../test/routes';
import { renderAt } from '../test/render';

const ADMIN = { id: 'u-admin', email: 'admin@clinique.example.com', role: 'admin', language: 'fr' };
const REQUEST = {
  id: 'r1',
  type: 'access',
  details: 'Je veux voir mon dossier.',
  status: 'received',
  requested_at: '2026-11-10T15:00:00Z',
  due_at: '2026-12-10T15:00:00Z',
  completed_at: null,
  outcome: null,
};
const ADMIN_REQUEST = {
  ...REQUEST,
  patient_id: 'p1',
  patient_name: 'Marie Tremblay',
  email: 'marie@example.com',
  overdue: false,
};
const INCIDENT = {
  id: 'i1',
  occurred_at: '2026-11-10T12:00:00Z',
  discovered_at: '2026-11-12T12:00:00Z',
  description: 'Courriel envoyé au mauvais patient.',
  data_categories: 'Nom, date du rendez-vous',
  people_affected: 1,
  risk_level: 'serious',
  measures: 'Courriel supprimé.',
  cai_notified_at: null,
  persons_notified_at: null,
  recorded_by: 'u-admin',
  created_at: '2026-11-12T12:00:00Z',
  updated_at: '2026-11-12T12:00:00Z',
  to_notify: ['cai', 'persons'],
};

function adminRoutes(extra = {}) {
  return mockRoutes(
    {
      'GET /admin/services': () => [200, []],
      'GET /admin/staff': () => [200, []],
      'GET /admin/privacy-requests': () => [200, [ADMIN_REQUEST]],
      'GET /admin/incidents': () => [200, [INCIDENT]],
      ...extra,
    },
    { me: ADMIN },
  );
}

describe('my data (Law 25, B-ADM-04)', () => {
  it('sends a request and shows it with its 30-day deadline', async () => {
    let mine = [];
    const calls = mockRoutes({
      'GET /me/privacy-requests': () => [200, mine],
      'POST /me/privacy-requests': (body) => {
        mine = [{ ...REQUEST, type: body.type, details: body.details }];
        return [201, mine[0]];
      },
    });
    renderAt('/mes-donnees');

    await userEvent.click(await screen.findByLabelText('Corriger un renseignement'));
    await userEvent.type(screen.getByLabelText('Précisions (facultatif)'), 'Mon numéro a changé.');
    await userEvent.click(screen.getByRole('button', { name: 'Envoyer la demande' }));

    expect(await screen.findByText(/Demande envoyée/)).toBeInTheDocument();
    expect(calls.find((c) => c.key === 'POST /me/privacy-requests').body).toEqual({
      type: 'correction',
      details: 'Mon numéro a changé.',
    });
    expect(await screen.findByText(/réponse au plus tard le/)).toBeInTheDocument();
  });

  it('explains what deletion keeps before the patient asks', async () => {
    mockRoutes({ 'GET /me/privacy-requests': () => [200, []] });
    renderAt('/mes-donnees');

    await userEvent.click(await screen.findByLabelText(/Supprimer mon compte/));

    expect(screen.getByText(/dossier de santé est gardé 5 ans/)).toBeInTheDocument();
  });

  it('says when a request of the same type is already open', async () => {
    mockRoutes({
      'GET /me/privacy-requests': () => [200, [REQUEST]],
      'POST /me/privacy-requests': () => [409, {}],
    });
    renderAt('/mes-donnees');

    await userEvent.click(await screen.findByRole('button', { name: 'Envoyer la demande' }));

    expect(await screen.findByText(/déjà une demande de ce type/)).toBeInTheDocument();
  });
});

describe('Law 25 administration (B-ADM-04, B-ADM-05)', () => {
  it('shows late requests in red', async () => {
    adminRoutes({
      'GET /admin/privacy-requests': () => [200, [{ ...ADMIN_REQUEST, overdue: true }]],
    });
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Demandes (Loi 25)' }));

    const item = (await screen.findByText(/Marie Tremblay/)).closest('li');
    expect(item).toHaveClass('panel--alert');
    expect(within(item).getByText(/En retard/)).toBeInTheDocument();
  });

  it('exports and answers an access request', async () => {
    const calls = adminRoutes({
      'GET /admin/privacy-requests/r1/export': () => [200, { profile: { first_name: 'Marie' } }],
      'PATCH /admin/privacy-requests/r1': () => [200, { ...REQUEST, status: 'completed' }],
    });
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Demandes (Loi 25)' }));

    await userEvent.click(await screen.findByRole('button', { name: 'Traiter' }));
    await userEvent.click(screen.getByRole('button', { name: /Préparer l’export/ }));
    expect(await screen.findByLabelText('Renseignements personnels du patient')).toHaveValue(
      JSON.stringify({ profile: { first_name: 'Marie' } }, null, 2),
    );
    await userEvent.type(screen.getByLabelText('Réponse donnée au patient'), 'Export envoyé.');
    await userEvent.click(screen.getByRole('button', { name: 'Répondre (terminée)' }));

    await waitFor(() =>
      expect(calls.find((c) => c.key === 'PATCH /admin/privacy-requests/r1')?.body).toEqual({
        status: 'completed',
        outcome: 'Export envoyé.',
      }),
    );
  });

  it('asks for confirmation before erasing', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const calls = adminRoutes({
      'GET /admin/privacy-requests': () => [200, [{ ...ADMIN_REQUEST, type: 'deletion' }]],
    });
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Demandes (Loi 25)' }));

    await userEvent.click(await screen.findByRole('button', { name: 'Traiter' }));
    await userEvent.click(screen.getByRole('button', { name: 'Effacer et répondre' }));

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('Marie Tremblay'));
    expect(calls.some((c) => c.key === 'POST /admin/privacy-requests/r1/erase')).toBe(false);
    confirm.mockRestore();
  });

  it('shows incidents to notify and records the notification', async () => {
    const calls = adminRoutes({
      'PATCH /admin/incidents/i1': () => [200, { ...INCIDENT, to_notify: ['persons'] }],
    });
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Incidents' }));

    expect(await screen.findByText(/Avis à faire/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Commission avisée aujourd’hui' }));

    await waitFor(() =>
      expect(Object.keys(calls.find((c) => c.key === 'PATCH /admin/incidents/i1').body)).toEqual([
        'cai_notified_at',
      ]),
    );
  });

  it('records a new incident', async () => {
    const calls = adminRoutes({
      'GET /admin/incidents': () => [200, []],
      'POST /admin/incidents': () => [201, INCIDENT],
    });
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Incidents' }));

    await userEvent.click(await screen.findByRole('button', { name: 'Enregistrer un incident' }));
    await userEvent.type(screen.getByLabelText('Date de l’incident'), '2026-11-10');
    await userEvent.type(screen.getByLabelText('Date où la clinique l’a appris'), '2026-11-12');
    await userEvent.type(
      screen.getByLabelText('Ce qui s’est passé'),
      'Courriel au mauvais patient.',
    );
    await userEvent.type(screen.getByLabelText('Renseignements concernés'), 'Nom');
    await userEvent.type(screen.getByLabelText('Mesures prises'), 'Courriel supprimé.');
    await userEvent.selectOptions(screen.getByLabelText('Risque'), 'serious');
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));

    await waitFor(() =>
      expect(calls.find((c) => c.key === 'POST /admin/incidents')?.body).toMatchObject({
        occurred_at: '2026-11-10T12:00:00Z',
        discovered_at: '2026-11-12T12:00:00Z',
        risk_level: 'serious',
        people_affected: null,
      }),
    );
  });
});

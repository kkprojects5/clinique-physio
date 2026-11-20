import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { mockRoutes } from '../test/routes';
import { renderAt } from '../test/render';

const ADMIN = { id: 'u-admin', email: 'admin@clinique.example.com', role: 'admin', language: 'fr' };
const SERVICE = {
  id: 's1',
  name_fr: 'Traitement de suivi 30 min',
  name_en: 'Follow-up treatment 30 min',
  description_fr: null,
  description_en: null,
  duration_min: 30,
  price_cents: 8000,
  deposit_cents: 2000,
  is_initial_evaluation: false,
  is_active: true,
  therapist_ids: ['t-anne'],
};
const ANNE = {
  id: 'u-anne',
  email: 'anne@clinique.example.com',
  role: 'therapist',
  is_active: true,
  mfa_ready: true,
  last_login_at: '2026-11-18T14:00:00Z',
  therapist_id: 't-anne',
  first_name: 'Anne',
  last_name: 'Lefebvre',
  licence_number: 'PT-10001',
  future_appointments: 3,
};
const DESK = {
  ...ANNE,
  id: 'u-desk',
  email: 'accueil1@clinique.example.com',
  role: 'front_desk',
  therapist_id: null,
  first_name: null,
  last_name: null,
  licence_number: null,
  future_appointments: 0,
  mfa_ready: false,
  last_login_at: null,
};
const ENTRY = {
  id: 42,
  created_at: '2026-11-18T15:30:00Z',
  actor_email: 'anne@clinique.example.com',
  actor_role: 'therapist',
  action: 'read',
  resource_type: 'clinical_note',
  resource_id: 'n1',
  patient_id: 'p1',
  patient_name: 'Marie Tremblay',
  ip: '203.0.113.7',
  client_app: 'web',
  unusual: false,
};

function adminRoutes(extra = {}) {
  return mockRoutes(
    {
      'GET /admin/services': () => [200, [SERVICE]],
      'GET /admin/staff': () => [200, [ANNE, DESK]],
      'GET /admin/audit': () => [200, { entries: [ENTRY], next_before_id: null }],
      ...extra,
    },
    { me: ADMIN },
  );
}

describe('administration (B-ADM-01, B-ADM-03)', () => {
  it('is only for administrators', async () => {
    mockRoutes({});
    renderAt('/administration');

    await waitFor(() => expect(screen.queryByText('Administration')).not.toBeInTheDocument());
  });

  it('lists the services with prices and status', async () => {
    adminRoutes();
    renderAt('/administration');

    const row = (await screen.findByText('Traitement de suivi 30 min')).closest('tr');
    expect(within(row).getByText(/80,00/)).toBeInTheDocument();
    expect(within(row).getByText('Actif')).toBeInTheDocument();
  });

  it('creates a service with prices in cents and chosen therapists', async () => {
    const calls = adminRoutes({ 'POST /admin/services': () => [201, SERVICE] });
    renderAt('/administration');

    await userEvent.click(await screen.findByRole('button', { name: 'Nouveau service' }));
    await userEvent.type(screen.getByLabelText('Nom (français)'), 'Rééducation vestibulaire');
    await userEvent.type(screen.getByLabelText('Nom (anglais)'), 'Vestibular rehabilitation');
    await userEvent.selectOptions(screen.getByLabelText('Durée'), '45');
    await userEvent.type(screen.getByLabelText('Prix ($)'), '105,50');
    await userEvent.type(screen.getByLabelText('Dépôt en ligne ($)'), '25');
    await userEvent.click(screen.getByLabelText('Anne Lefebvre'));
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));

    await waitFor(() => expect(calls.some((c) => c.key === 'POST /admin/services')).toBe(true));
    const sent = calls.find((c) => c.key === 'POST /admin/services').body;
    expect(sent).toMatchObject({
      name_fr: 'Rééducation vestibulaire',
      duration_min: 45,
      price_cents: 10550,
      deposit_cents: 2500,
      therapist_ids: ['t-anne'],
    });
  });

  it('refuses a deposit higher than the price before calling the API', async () => {
    const calls = adminRoutes();
    renderAt('/administration');

    await userEvent.click(await screen.findByRole('button', { name: 'Modifier' }));
    const deposit = screen.getByLabelText('Dépôt en ligne ($)');
    await userEvent.clear(deposit);
    await userEvent.type(deposit, '500');
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));

    expect(screen.getByText('Le dépôt ne peut pas dépasser le prix.')).toBeInTheDocument();
    expect(calls.some((c) => c.key === 'PATCH /admin/services/s1')).toBe(false);
  });

  it('deactivates a service', async () => {
    const calls = adminRoutes({
      'PATCH /admin/services/s1': () => [200, { ...SERVICE, is_active: false }],
    });
    renderAt('/administration');

    await userEvent.click(await screen.findByRole('button', { name: 'Désactiver' }));

    await waitFor(() =>
      expect(calls.find((c) => c.key === 'PATCH /admin/services/s1')?.body).toEqual({
        is_active: false,
      }),
    );
  });

  it('creates a therapist account: an invitation, never a password', async () => {
    const calls = adminRoutes({
      'POST /admin/staff': (body) => [201, { ...ANNE, email: body.email, mfa_ready: false }],
    });
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Personnel' }));

    await userEvent.click(
      await screen.findByRole('button', { name: 'Nouveau membre du personnel' }),
    );
    expect(screen.queryByLabelText(/mot de passe/i)).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Adresse courriel'), 'julie.roy@example.com');
    await userEvent.type(screen.getByLabelText('Prénom'), 'Julie');
    await userEvent.type(screen.getByLabelText('Nom'), 'Roy');
    await userEvent.type(screen.getByLabelText('Numéro de permis'), 'PT-99001');
    await userEvent.click(screen.getByRole('button', { name: 'Créer et envoyer l’invitation' }));

    expect(
      await screen.findByText(/Une invitation a été envoyée à julie.roy@example.com/),
    ).toBeInTheDocument();
    expect(calls.find((c) => c.key === 'POST /admin/staff').body).toEqual({
      email: 'julie.roy@example.com',
      role: 'therapist',
      language: 'fr',
      therapist: { first_name: 'Julie', last_name: 'Roy', licence_number: 'PT-99001' },
    });
  });

  it('warns about upcoming appointments before deactivating a therapist', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const calls = adminRoutes();
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Personnel' }));

    const row = (await screen.findByText('Anne Lefebvre')).closest('tr');
    await userEvent.click(within(row).getByRole('button', { name: 'Désactiver' }));

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('3 rendez-vous à venir'));
    expect(calls.some((c) => c.key.startsWith('PATCH /admin/staff'))).toBe(false);
    confirm.mockRestore();
  });

  it('resends the invitation to someone who has not set up their account', async () => {
    const calls = adminRoutes({ 'POST /admin/staff/u-desk/invitation': () => [204, null] });
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Personnel' }));

    await userEvent.click(await screen.findByRole('button', { name: 'Renvoyer l’invitation' }));

    expect(await screen.findByText(/Nouvelle invitation envoyée/)).toBeInTheDocument();
    expect(calls.some((c) => c.key === 'POST /admin/staff/u-desk/invitation')).toBe(true);
  });

  it('highlights unusual access and filters by a clicked patient', async () => {
    const calls = adminRoutes({
      'GET /admin/audit': () => [
        200,
        { entries: [{ ...ENTRY, id: 43, unusual: true }], next_before_id: null },
      ],
    });
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Journal d’audit' }));

    const name = await screen.findByRole('button', { name: 'Marie Tremblay' });
    expect(name.closest('tr')).toHaveClass('row--alert');
    expect(within(name.closest('tr')).getByText('Inhabituel')).toBeInTheDocument();

    await userEvent.click(name);

    expect(await screen.findByText(/Patient : Marie Tremblay/)).toBeInTheDocument();
    await waitFor(() =>
      expect(
        calls.some((c) => c.key === 'GET /admin/audit' && c.url.includes('patient_id=p1')),
      ).toBe(true),
    );
  });

  it('shows the audit log and filters it', async () => {
    const calls = adminRoutes();
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Journal d’audit' }));

    const row = (await screen.findByRole('button', { name: 'Marie Tremblay' })).closest('tr');
    expect(row).not.toHaveClass('row--alert');
    expect(within(row).getByText('Note clinique')).toBeInTheDocument();
    expect(within(row).getByText('Consultation')).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText('Action'), 'access_denied');
    await userEvent.click(screen.getByRole('button', { name: 'Filtrer' }));

    await waitFor(() =>
      expect(
        calls.some((c) => c.key === 'GET /admin/audit' && c.url?.includes('access_denied')),
      ).toBe(true),
    );
  });
});

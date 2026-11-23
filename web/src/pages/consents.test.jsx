import { describe, expect, it } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { mockApi, renderAt } from '../test/render';
import { mockRoutes } from '../test/routes';

const POLICY = {
  type: 'privacy_policy',
  given: true,
  version: '2026-10',
  granted_at: '2026-11-10T15:00:00Z',
  revoked_at: null,
  current_version: '2026-10',
  up_to_date: true,
};
const COMMS = {
  type: 'electronic_comms',
  given: true,
  version: '2026-10',
  granted_at: '2026-11-10T15:00:00Z',
  revoked_at: null,
  current_version: '2026-10',
  up_to_date: true,
};

function consentRoutes(consents, extra = {}) {
  return mockRoutes({
    'GET /me/privacy-requests': () => [200, []],
    'GET /me/consents': () => [200, consents()],
    ...extra,
  });
}

describe('privacy policy page (Law 25)', () => {
  it('is public and linked from the footer of every page', async () => {
    mockApi();
    renderAt('/');

    await userEvent.click(
      within(screen.getByRole('contentinfo')).getByRole('link', {
        name: 'Politique de confidentialité',
      }),
    );

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Politique de confidentialité' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '8. Vos droits' })).toBeInTheDocument();
    expect(screen.getByText(/Commission d’accès à l’information du Québec/)).toBeInTheDocument();
  });

  it('is linked from the consent box at registration', async () => {
    mockApi();
    renderAt('/inscription');

    const link = await screen.findByRole('link', { name: '(lire la politique)' });

    expect(link).toHaveAttribute('href', '/confidentialite');
  });
});

describe('my consents (Law 25)', () => {
  it('shows the accepted version and withdraws electronic messages', async () => {
    let comms = COMMS;
    const calls = consentRoutes(() => [POLICY, comms], {
      'PUT /me/consents/electronic_comms': (body) => {
        comms = { ...COMMS, given: body.given, revoked_at: '2026-11-23T15:00:00Z' };
        return [200, comms];
      },
    });
    renderAt('/mes-donnees');

    expect(await screen.findByText(/Acceptée \(version 2026-10\)/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Retirer mon consentement' }));

    expect(await screen.findByText('Votre choix est enregistré.')).toBeInTheDocument();
    expect(calls.find((c) => c.key === 'PUT /me/consents/electronic_comms').body).toEqual({
      given: false,
    });
    expect(await screen.findByText(/^Retiré le/)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Je veux recevoir les communications' }),
    ).toBeVisible();
  });

  it('asks to accept a new version of the policy', async () => {
    let policy = { ...POLICY, version: '2025-01', up_to_date: false };
    const calls = consentRoutes(() => [policy, { ...COMMS, given: false, granted_at: null }], {
      'POST /me/consents/privacy_policy': () => {
        policy = POLICY;
        return [200, policy];
      },
    });
    renderAt('/mes-donnees');

    await userEvent.click(
      await screen.findByRole('button', { name: 'J’accepte la nouvelle version' }),
    );

    await waitFor(() =>
      expect(calls.some((c) => c.key === 'POST /me/consents/privacy_policy')).toBe(true),
    );
    expect(await screen.findByText(/Acceptée \(version 2026-10\)/)).toBeInTheDocument();
    expect(screen.getByText(/ni rappels ni nouvelles/)).toBeInTheDocument();
  });
});

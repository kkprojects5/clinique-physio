import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderAt } from '../test/render';

/** Fake API for POST requests: 'answer' gives the status for each path. */
function mockPost(answer) {
  const calls = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url, options = {}) => {
      const path = new URL(url).pathname;
      calls.push({ path, body: options.body ? JSON.parse(options.body) : null });
      const status = answer(path, calls.length);
      return { ok: status < 300, status, json: async () => ({}) };
    }),
  );
  return calls;
}

const NEW = 'Une-longue-phrase-secrete-42';

async function fillReset(password = NEW, confirm = password) {
  await userEvent.type(screen.getByLabelText('Nouveau mot de passe'), password);
  await userEvent.type(screen.getByLabelText('Confirmez le mot de passe'), confirm);
  await userEvent.click(screen.getByRole('button', { name: 'Enregistrer le mot de passe' }));
}

describe('forgot password (B-AUTH-03)', () => {
  it('sends the email and shows the same neutral message', async () => {
    const calls = mockPost(() => 202);
    renderAt('/mot-de-passe-oublie');
    await userEvent.type(screen.getByLabelText('Adresse courriel'), 'claire@example.com');
    await userEvent.click(screen.getByRole('button', { name: 'Envoyer le lien' }));

    expect(await screen.findByRole('status')).toHaveTextContent('Si un compte existe');
    expect(calls[0]).toEqual({
      path: '/api/v1/auth/password/forgot',
      body: { email: 'claire@example.com' },
    });
  });

  it('explains when there were too many attempts', async () => {
    mockPost(() => 429);
    renderAt('/mot-de-passe-oublie');
    await userEvent.type(screen.getByLabelText('Adresse courriel'), 'claire@example.com');
    await userEvent.click(screen.getByRole('button', { name: 'Envoyer le lien' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Trop de tentatives');
  });

  it('is linked from the footer of every page', () => {
    mockPost(() => 200);
    renderAt('/nowhere');
    expect(screen.getByRole('link', { name: 'Mot de passe oublié ?' })).toHaveAttribute(
      'href',
      '/mot-de-passe-oublie',
    );
  });
});

describe('reset password (B-AUTH-03)', () => {
  it('sends the token from the link with the new password', async () => {
    const calls = mockPost(() => 200);
    renderAt('/reinitialiser-mot-de-passe?token=abc123');
    await fillReset();

    expect(await screen.findByRole('status')).toHaveTextContent('mot de passe a été modifié');
    expect(calls[0]).toEqual({
      path: '/api/v1/auth/password/reset',
      body: { token: 'abc123', new_password: NEW },
    });
  });

  it('checks length and confirmation before calling the API', async () => {
    const calls = mockPost(() => 200);
    renderAt('/reinitialiser-mot-de-passe?token=abc123');

    await fillReset('court', 'court');
    expect(screen.getByRole('alert')).toHaveTextContent('au moins 12 caractères');
    await userEvent.clear(screen.getByLabelText('Nouveau mot de passe'));
    await userEvent.clear(screen.getByLabelText('Confirmez le mot de passe'));
    await fillReset(NEW, `${NEW}x`);
    expect(screen.getByRole('alert')).toHaveTextContent('pas identiques');
    expect(calls).toHaveLength(0);
  });

  it('offers a new link when the link is used or expired', async () => {
    mockPost(() => 400);
    renderAt('/reinitialiser-mot-de-passe?token=old');
    await fillReset();

    expect(await screen.findByRole('alert')).toHaveTextContent('n’est plus valide');
    expect(screen.getByRole('link', { name: 'Demander un nouveau lien' })).toBeInTheDocument();
  });

  it('shows the password rule refused by the API', async () => {
    mockPost(() => 422);
    renderAt('/reinitialiser-mot-de-passe?token=abc123');
    await fillReset();

    expect(await screen.findByRole('alert')).toHaveTextContent('adresse courriel');
  });

  it('says the link is invalid when there is no token', () => {
    mockPost(() => 200);
    renderAt('/reinitialiser-mot-de-passe');
    expect(screen.getByRole('alert')).toHaveTextContent('n’est plus valide');
    expect(screen.queryByLabelText('Nouveau mot de passe')).not.toBeInTheDocument();
  });
});

describe('email confirmation link (B-AUTH-01)', () => {
  it('confirms the address once', async () => {
    const calls = mockPost(() => 200);
    renderAt('/verify-email?token=tok');

    expect(await screen.findByText(/adresse courriel est confirmée/)).toBeInTheDocument();
    expect(calls).toEqual([{ path: '/api/v1/auth/verify-email', body: { token: 'tok' } }]);
  });

  it('shows an error for an expired link', async () => {
    mockPost(() => 400);
    renderAt('/verify-email?token=tok');
    expect(await screen.findByRole('alert')).toHaveTextContent('pas valide');
  });
});

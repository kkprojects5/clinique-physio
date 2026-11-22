import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { mockRoutes } from '../test/routes';
import { renderAt, THERAPISTS } from '../test/render';

const ADMIN = { id: 'u-admin', email: 'admin@clinique.example.com', role: 'admin', language: 'fr' };
const ANNE = {
  id: 'u-anne',
  email: 'anne@clinique.example.com',
  role: 'therapist',
  is_active: true,
  mfa_ready: true,
  last_login_at: null,
  therapist_id: 't-anne',
  first_name: 'Anne',
  last_name: 'Lefebvre',
  licence_number: 'PT-10001',
  future_appointments: 0,
  photo_url: null,
};

describe('therapist photos (B-AVL-05)', () => {
  it('shows the photo on the team page, or the initials when there is none', async () => {
    const [first, ...others] = THERAPISTS;
    mockRoutes(
      {
        'GET /therapists': () => [
          200,
          [{ ...first, photo_url: '/api/v1/therapists/t-anne/photo?v=1' }, ...others],
        ],
      },
      { loggedIn: false },
    );
    renderAt('/equipe');

    const photo = await screen.findByRole('img', {
      name: `Photo de ${first.first_name} ${first.last_name}`,
    });
    expect(photo.getAttribute('src')).toMatch(/\/api\/v1\/therapists\/t-anne\/photo\?v=1$/);
    const second = others[0];
    expect(screen.getByText(`${second.first_name[0]}${second.last_name[0]}`)).toBeInTheDocument();
  });

  it('lets the administrator upload a photo, sent as the image itself', async () => {
    const calls = mockRoutes(
      {
        'GET /admin/services': () => [200, []],
        'GET /admin/staff': () => [200, [ANNE]],
        'PUT /admin/therapists/t-anne/photo': () => [200, { photo_url: '/x?v=2' }],
      },
      { me: ADMIN },
    );
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Personnel' }));
    const file = new File(['png-bytes'], 'anne.png', { type: 'image/png' });

    await userEvent.upload(await screen.findByLabelText(/Photo de Anne/), file);

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Photo de Anne'));
    const sent = calls.find((c) => c.key === 'PUT /admin/therapists/t-anne/photo');
    expect(sent.headers['Content-Type']).toBe('image/png');
    expect(sent.body).toBe(file);
  });

  it('refuses a file that is not an image before sending it', async () => {
    const calls = mockRoutes(
      {
        'GET /admin/services': () => [200, []],
        'GET /admin/staff': () => [200, [ANNE]],
      },
      { me: ADMIN },
    );
    renderAt('/administration');
    await userEvent.click(await screen.findByRole('tab', { name: 'Personnel' }));
    const file = new File(['<svg/>'], 'anne.svg', { type: 'image/svg+xml' });

    await userEvent.upload(await screen.findByLabelText(/Photo de Anne/), file, {
      applyAccept: false,
    });

    expect(await screen.findByText('Choisissez une image JPEG, PNG ou WebP.')).toBeInTheDocument();
    expect(calls.some((c) => c.key.startsWith('PUT'))).toBe(false);
  });
});

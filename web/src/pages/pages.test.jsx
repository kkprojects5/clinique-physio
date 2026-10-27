import { describe, expect, it } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { mockApi, renderAt } from '../test/render';

describe('layout and language (NFR-10)', () => {
  it('is in French by default', async () => {
    mockApi();
    renderAt('/');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Physiothérapie');
    expect(document.documentElement.lang).toBe('fr');
  });

  it('switches to English and back', async () => {
    mockApi();
    renderAt('/');
    await userEvent.click(screen.getByRole('button', { name: 'Switch to English' }));
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Physiotherapy');
    expect(document.documentElement.lang).toBe('en');
    await userEvent.click(screen.getByRole('button', { name: 'Passer en français' }));
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Physiothérapie');
  });

  it('has a skip link and a labelled main navigation (NFR-09)', () => {
    mockApi();
    renderAt('/');
    expect(screen.getByRole('link', { name: 'Aller au contenu' })).toHaveAttribute('href', '#main');
    expect(screen.getByRole('navigation', { name: 'Navigation principale' })).toBeInTheDocument();
  });

  it('shows a not-found page for unknown addresses', () => {
    mockApi();
    renderAt('/nowhere');
    expect(screen.getByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument();
  });
});

describe('services page (B-AVL-01)', () => {
  it('lists services with price and deposit from the API', async () => {
    mockApi();
    renderAt('/services');
    const card = (await screen.findByRole('heading', { name: 'Évaluation initiale' })).closest(
      'li',
    );
    expect(within(card).getByText('60 min')).toBeInTheDocument();
    expect(within(card).getByText(/120,00/)).toBeInTheDocument();
    expect(within(card).getByText(/30,00/)).toBeInTheDocument();
    expect(within(card).getByText('Requis avant un premier traitement')).toBeInTheDocument();
  });

  it('shows a clear message and a retry button when the API is down', async () => {
    mockApi({ fail: true });
    renderAt('/services');
    expect(await screen.findByRole('alert')).toHaveTextContent('momentanément indisponible');
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument();
  });

  it('displays API text as text, never as HTML (XSS, challenge B-C4)', async () => {
    mockApi({
      services: [
        {
          id: 'x',
          name_fr: '<img src=x onerror=alert(1)>',
          name_en: 'x',
          duration_min: 30,
          price_cents: 1,
          deposit_cents: 0,
          is_initial_evaluation: false,
          therapist_ids: [],
        },
      ],
    });
    renderAt('/services');
    expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeInTheDocument();
    expect(document.querySelector('img[src="x"]')).toBeNull();
  });
});

describe('team page', () => {
  it('shows names, bios in the current language and spoken languages', async () => {
    mockApi();
    renderAt('/equipe');
    expect(await screen.findByRole('heading', { name: 'Anne Lefebvre' })).toBeInTheDocument();
    expect(screen.getByText('Bio FR Anne')).toBeInTheDocument();
    expect(screen.getByText('français, anglais')).toBeInTheDocument();
  });
});

describe('availability page (B-AVL-03)', () => {
  const SLOTS = [
    {
      therapist_id: 't-anne',
      start: '2026-11-02T15:00:00Z',
      end: '2026-11-02T16:00:00Z',
      start_local: '2026-11-02T10:00:00-05:00',
    },
    {
      therapist_id: 't-karim',
      start: '2026-11-03T14:00:00Z',
      end: '2026-11-03T15:00:00Z',
      start_local: '2026-11-03T09:00:00-05:00',
    },
  ];

  it('asks the API for the chosen service and week, and groups slots by day', async () => {
    const calls = mockApi({ slots: SLOTS });
    renderAt('/disponibilites?service=s-eval&week=2026-11-02');

    expect(await screen.findByText('2 plages disponibles')).toBeInTheDocument();
    const request = calls.find((u) => u.pathname.endsWith('/availability'));
    expect(request.searchParams.get('service_id')).toBe('s-eval');
    expect(request.searchParams.get('date_from')).toBe('2026-11-02');
    expect(request.searchParams.get('date_to')).toBe('2026-11-08');
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(2);
    expect(screen.getByText('avec Anne Lefebvre')).toBeInTheDocument();
    expect(screen.getByText(/10:00|10 h 00/)).toBeInTheDocument(); // Montréal time
  });

  it('lets the visitor pick a therapist among those offering the service', async () => {
    const calls = mockApi({ slots: SLOTS.slice(0, 1) });
    renderAt('/disponibilites?service=s-eval&week=2026-11-02');
    await screen.findByText(/plage/);

    await userEvent.selectOptions(screen.getByLabelText('Physiothérapeute'), 't-anne');

    expect(await screen.findByText('1 plage disponible')).toBeInTheDocument();
    const last = calls.filter((u) => u.pathname.endsWith('/availability')).at(-1);
    expect(last.searchParams.get('therapist_id')).toBe('t-anne');
  });

  it('explains when there is nothing available', async () => {
    mockApi({ slots: [] });
    renderAt('/disponibilites?service=s-eval&week=2026-11-02');
    expect(await screen.findByText(/Aucune disponibilité pour cette semaine/)).toBeInTheDocument();
  });

  it('does not call the API before a service is chosen', async () => {
    const calls = mockApi();
    renderAt('/disponibilites');
    await screen.findByRole('option', { name: 'Évaluation initiale' });
    expect(calls.some((u) => u.pathname.endsWith('/availability'))).toBe(false);
    expect(screen.getByLabelText('Physiothérapeute')).toBeDisabled();
  });
});

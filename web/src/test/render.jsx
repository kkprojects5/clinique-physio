// Render a page with the same providers as the real app, and a fake API.
import { render } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import Layout from '../components/Layout';
import App from '../App';

export const SERVICES = [
  {
    id: 's-eval',
    name_fr: 'Évaluation initiale',
    name_en: 'Initial evaluation',
    description_fr: null,
    description_en: null,
    duration_min: 60,
    price_cents: 12000,
    deposit_cents: 3000,
    is_initial_evaluation: true,
    therapist_ids: ['t-anne', 't-karim'],
  },
];
export const THERAPISTS = [
  {
    id: 't-anne',
    first_name: 'Anne',
    last_name: 'Lefebvre',
    specialties: ['sport'],
    languages: ['fr', 'en'],
    bio_fr: 'Bio FR Anne',
    bio_en: 'Bio EN Anne',
    service_ids: ['s-eval'],
  },
  {
    id: 't-karim',
    first_name: 'Karim',
    last_name: 'Haddad',
    specialties: ['shoulder'],
    languages: ['ar'],
    bio_fr: 'Bio FR Karim',
    bio_en: 'Bio EN Karim',
    service_ids: ['s-eval'],
  },
];

/** Fake fetch: answers by path; 'slots' can be a list or a function of the URL. */
export function mockApi({
  services = SERVICES,
  therapists = THERAPISTS,
  slots = [],
  fail = false,
} = {}) {
  const calls = [];
  const fetchMock = vi.fn(async (url) => {
    const u = new URL(url);
    calls.push(u);
    if (fail) return { ok: false, status: 503, json: async () => ({}) };
    const body = u.pathname.endsWith('/services')
      ? services
      : u.pathname.endsWith('/therapists')
        ? therapists
        : typeof slots === 'function'
          ? slots(u)
          : slots;
    return { ok: true, status: 200, json: async () => body };
  });
  vi.stubGlobal('fetch', fetchMock);
  return calls;
}

export function renderAt(path) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

export { Layout, Routes, Route };

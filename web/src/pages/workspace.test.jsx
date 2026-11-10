import { describe, expect, it, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderAt } from '../test/render';
import { mockRoutes } from '../test/routes';

// qrcode draws on a canvas, which the test browser does not have.
vi.mock('qrcode', () => ({
  default: { toDataURL: vi.fn(async () => 'data:image/png;base64,QR') },
}));

const ANNE = { id: 't-anne', first_name: 'Anne', last_name: 'Lefebvre' };
const THERAPIST_USER = { id: 'u9', email: 'anne@clinique.example.com', role: 'therapist' };
const PAST = '2026-11-02T15:00:00Z';
const FUTURE = '2030-01-07T15:00:00Z';
const FILE = {
  id: 'p1',
  first_name: 'Marie',
  last_name: 'Tremblay',
  date_of_birth: '1990-05-12',
  phone: '514-555-0101',
  emergency_contact: 'Luc 514-555-0199',
  history: [
    {
      appointment_id: 'a-past',
      start: PAST,
      start_local: '2026-11-02T10:00:00-05:00',
      status: 'completed',
      service_name_fr: 'Suivi',
      service_name_en: 'Follow-up',
      therapist_id: 't-anne',
      therapist_name: 'Anne Lefebvre',
    },
    {
      appointment_id: 'a-future',
      start: FUTURE,
      start_local: '2030-01-07T10:00:00-05:00',
      status: 'confirmed',
      service_name_fr: 'Suivi',
      service_name_en: 'Follow-up',
      therapist_id: 't-anne',
      therapist_name: 'Anne Lefebvre',
    },
    {
      appointment_id: 'a-other',
      start: PAST,
      start_local: '2026-11-02T10:00:00-05:00',
      status: 'completed',
      service_name_fr: 'Évaluation',
      service_name_en: 'Evaluation',
      therapist_id: 't-sophie',
      therapist_name: 'Sophie Nguyen',
    },
  ],
};
const SOAP = {
  subjective: 'Douleur au genou',
  objective: 'Flexion 110°',
  assessment: 'Tendinopathie',
  plan: 'Exercices',
};
const note = (extra = {}) => ({
  id: 'n1',
  appointment_id: 'a-past',
  patient_id: 'p1',
  author_therapist_id: 't-anne',
  content: SOAP,
  version: 1,
  signed_at: null,
  amends_note_id: null,
  created_at: PAST,
  updated_at: PAST,
  ...extra,
});

function workspace(routes = {}, notes = []) {
  return mockRoutes(
    {
      'GET /therapist/me': () => [200, ANNE],
      'GET /therapist/patients': () => [
        200,
        [
          {
            id: 'p1',
            first_name: 'Marie',
            last_name: 'Tremblay',
            date_of_birth: '1990-05-12',
            last_visit: PAST,
          },
        ],
      ],
      'GET /therapist/patients/p1': () => [200, FILE],
      'GET /therapist/patients/p1/notes': () => [
        200,
        typeof notes === 'function' ? notes() : notes,
      ],
      'GET /therapist/patients/p1/programs': () => [200, []],
      'GET /exercises': () => [
        200,
        [
          {
            id: 'e1',
            name_fr: 'Pont fessier',
            name_en: 'Glute bridge',
            default_sets: 3,
            default_reps: 12,
          },
          {
            id: 'e2',
            name_fr: 'Squat au mur',
            name_en: 'Wall sit',
            default_sets: 3,
            default_reps: 5,
          },
        ],
      ],
      ...routes,
    },
    { me: THERAPIST_USER },
  );
}

describe('first staff login on the website (B-AUTH-04)', () => {
  it('shows the QR code to scan, then opens the workspace', async () => {
    const calls = mockRoutes(
      {
        'POST /auth/login': () => [
          200,
          { mfa_required: true, mfa_setup_required: true, mfa_token: 'ticket', expires_in: 300 },
        ],
        'POST /auth/mfa/setup': () => [200, { secret: 'ABCDEF123456', otpauth_uri: 'otpauth://x' }],
        'POST /auth/mfa/verify': () => [200, { access_token: 'tok' }],
        'GET /therapist/me': () => [200, ANNE],
        'GET /therapist/patients': () => [200, []],
      },
      { loggedIn: false, me: THERAPIST_USER },
    );
    renderAt('/connexion');

    await userEvent.type(
      await screen.findByLabelText('Adresse courriel'),
      'anne@clinique.example.com',
    );
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'Une-longue-phrase-42');
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }));

    expect(await screen.findByRole('img', { name: /Code QR/ })).toHaveAttribute(
      'src',
      'data:image/png;base64,QR',
    );
    expect(screen.getByText('ABCDEF123456')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Code à 6 chiffres'), '654321');
    await userEvent.click(screen.getByRole('button', { name: 'Vérifier' }));

    expect(await screen.findByRole('heading', { name: 'Espace thérapeute' })).toBeInTheDocument();
    expect(calls.find((c) => c.key === 'POST /auth/mfa/setup').body).toEqual({
      mfa_token: 'ticket',
    });
  });
});

describe('therapist workspace (B-CLN-01 to 03)', () => {
  it('lists the patients I treat with a link to their file', async () => {
    workspace();
    renderAt('/espace-therapeute');

    expect(await screen.findByText('Bonjour Anne Lefebvre.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Tremblay, Marie' })).toHaveAttribute(
      'href',
      '/espace-therapeute/patients/p1',
    );
    expect(screen.getByRole('link', { name: 'Espace thérapeute' })).toBeInTheDocument();
  });

  it('offers a note only for my appointments that have taken place', async () => {
    workspace();
    renderAt('/espace-therapeute/patients/p1');

    expect(await screen.findByRole('heading', { name: 'Marie Tremblay' })).toBeInTheDocument();
    expect(screen.getByText('Luc 514-555-0199')).toBeInTheDocument();
    // past + mine: yes; future: no; Sophie's: no
    expect(screen.getAllByRole('button', { name: 'Rédiger la note' })).toHaveLength(1);
  });

  it('writes a draft SOAP note', async () => {
    let notes = [];
    const calls = workspace(
      {
        'POST /therapist/appointments/a-past/notes': (body) => {
          notes = [note({ content: body })];
          return [201, notes[0]];
        },
      },
      () => notes,
    );
    renderAt('/espace-therapeute/patients/p1');

    await userEvent.click(await screen.findByRole('button', { name: 'Rédiger la note' }));
    await userEvent.type(screen.getByLabelText(/Subjectif/), 'Douleur au genou');
    await userEvent.type(screen.getByLabelText(/Plan de traitement/), 'Exercices');
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer le brouillon' }));

    expect(await screen.findByText('Brouillon')).toBeInTheDocument();
    expect(calls.find((c) => c.key === 'POST /therapist/appointments/a-past/notes').body).toEqual({
      subjective: 'Douleur au genou',
      objective: '',
      assessment: '',
      plan: 'Exercices',
    });
    expect(screen.queryByRole('button', { name: 'Rédiger la note' })).not.toBeInTheDocument();
  });

  it('refuses an empty note before calling the API', async () => {
    const calls = workspace();
    renderAt('/espace-therapeute/patients/p1');

    await userEvent.click(await screen.findByRole('button', { name: 'Rédiger la note' }));
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer le brouillon' }));

    expect(screen.getByRole('alert')).toHaveTextContent('au moins une partie');
    expect(calls.some((c) => c.key.startsWith('POST /therapist/appointments'))).toBe(false);
  });

  it('signs a draft after a warning', async () => {
    let current = note();
    const calls = workspace(
      {
        'POST /therapist/notes/n1/sign': () => {
          current = note({ signed_at: '2026-11-09T20:00:00Z' });
          return [200, current];
        },
      },
      () => [current],
    );
    renderAt('/espace-therapeute/patients/p1');

    await userEvent.click(await screen.findByRole('button', { name: 'Signer' }));
    expect(screen.getByRole('alert')).toHaveTextContent('ne pourra plus jamais être modifiée');
    await userEvent.click(screen.getByRole('button', { name: 'Signer définitivement' }));

    expect(await screen.findByText(/Signée le/)).toBeInTheDocument();
    expect(calls.some((c) => c.key === 'POST /therapist/notes/n1/sign')).toBe(true);
    expect(screen.queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument();
  });

  it('edits only my own drafts', async () => {
    workspace({}, [note({ author_therapist_id: 't-sophie' })]);
    renderAt('/espace-therapeute/patients/p1');

    expect(await screen.findByText('Brouillon')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Signer' })).not.toBeInTheDocument();
  });

  it('corrects a signed note with an amendment', async () => {
    const signed = note({ signed_at: '2026-11-03T20:00:00Z' });
    let notes = [signed];
    const calls = workspace(
      {
        'POST /therapist/notes/n1/amendments': (body) => {
          notes = [
            signed,
            note({
              id: 'n2',
              amends_note_id: 'n1',
              content: body,
              signed_at: '2026-11-09T20:00:00Z',
            }),
          ];
          return [201, notes[1]];
        },
      },
      () => notes,
    );
    renderAt('/espace-therapeute/patients/p1');

    await userEvent.click(await screen.findByRole('button', { name: 'Ajouter un amendement' }));
    await userEvent.type(screen.getByLabelText(/Analyse/), 'Tendinopathie confirmée');
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer l’amendement signé' }));

    expect(await screen.findByText(/Amendement du/)).toBeInTheDocument();
    expect(screen.getByText('Tendinopathie confirmée')).toBeInTheDocument();
    expect(screen.getByText('Tendinopathie')).toBeInTheDocument(); // original kept
    expect(calls.find((c) => c.key === 'POST /therapist/notes/n1/amendments').body.assessment).toBe(
      'Tendinopathie confirmée',
    );
  });

  it('says the file is not found for a patient I do not treat', async () => {
    workspace({ 'GET /therapist/patients/p1': () => [404, { detail: 'Not found.' }] });
    renderAt('/espace-therapeute/patients/p1');

    expect(await screen.findByRole('alert')).toHaveTextContent('patients que vous traitez');
  });

  it('keeps patients out of the workspace', async () => {
    mockRoutes({});
    renderAt('/espace-therapeute');

    expect(await screen.findByRole('heading', { level: 1 })).not.toHaveTextContent(
      'Espace thérapeute',
    );
  });
});

describe('exercise programs (B-EXE-02, B-EXE-04)', () => {
  it('gives a program from the library', async () => {
    let programs = [];
    const calls = workspace({
      'GET /therapist/patients/p1/programs': () => [200, programs],
      'POST /therapist/patients/p1/programs': (body) => {
        programs = [
          {
            id: 'pr1',
            start_date: body.start_date,
            end_date: '2026-12-07',
            weeks: body.weeks,
            notes: body.notes,
            adherence_percent: 0,
            items: [
              {
                id: 'i1',
                exercise: { name_fr: 'Pont fessier', name_en: 'Glute bridge' },
                sets: 3,
                reps: 12,
                times_per_week: 5,
                done_total: 0,
                planned_total: 20,
              },
            ],
          },
        ];
        return [201, programs[0]];
      },
    });
    renderAt('/espace-therapeute/patients/p1');

    await userEvent.click(await screen.findByRole('button', { name: 'Nouveau programme' }));
    await userEvent.click(await screen.findByLabelText(/Pont fessier/));
    const times = screen.getByLabelText('Fois par semaine pour Pont fessier');
    await userEvent.clear(times);
    await userEvent.type(times, '5');
    await userEvent.type(screen.getByLabelText(/Conseils pour le patient/), 'Le matin');
    await userEvent.click(screen.getByRole('button', { name: 'Donner le programme' }));

    expect(await screen.findByText('Assiduité : 0 %')).toBeInTheDocument();
    const table = screen.getByRole('table');
    expect(within(table).getByText('0 / 20')).toBeInTheDocument();
    const sent = calls.find((c) => c.key === 'POST /therapist/patients/p1/programs').body;
    expect(sent.items).toEqual([{ exercise_id: 'e1', times_per_week: 5 }]);
    expect(sent.weeks).toBe(4);
    expect(sent.notes).toBe('Le matin');
  });

  it('asks for at least one exercise', async () => {
    const calls = workspace();
    renderAt('/espace-therapeute/patients/p1');

    await userEvent.click(await screen.findByRole('button', { name: 'Nouveau programme' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Donner le programme' }));

    expect(screen.getByRole('alert')).toHaveTextContent('au moins un exercice');
    expect(calls.some((c) => c.key === 'POST /therapist/patients/p1/programs')).toBe(false);
  });
});

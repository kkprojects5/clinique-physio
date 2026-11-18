import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { mockRoutes } from '../test/routes';
import { renderAt } from '../test/render';

const ANSWER = {
  id: 'm1',
  kind: 'answer',
  answer: "Il n'y a pas de stationnement privé.",
  sources: [{ id: 'parking', title: 'Stationnement' }],
};

async function ask(question) {
  await userEvent.click(screen.getByRole('button', { name: /questions/i }));
  await userEvent.type(screen.getByLabelText('Votre question'), question);
  await userEvent.click(screen.getByRole('button', { name: 'Envoyer' }));
}

describe('chatbot', () => {
  it('sends the question in the site language and shows the answer with its source', async () => {
    const calls = mockRoutes({ 'POST /chat/messages': () => [200, ANSWER] }, { loggedIn: false });
    renderAt('/');

    await ask('Où se garer ?');

    expect(await screen.findByText(ANSWER.answer)).toBeInTheDocument();
    expect(screen.getByText(/Source : Stationnement/)).toBeInTheDocument();
    const sent = calls.find((c) => c.key === 'POST /chat/messages');
    expect(sent.body).toEqual({ message: 'Où se garer ?', language: 'fr' });
  });

  it('shows that it gives no medical advice before any question', async () => {
    mockRoutes({}, { loggedIn: false });
    renderAt('/');

    await userEvent.click(screen.getByRole('button', { name: /questions/i }));

    expect(screen.getByText(/Aucun conseil médical/)).toBeInTheDocument();
    expect(screen.getByText(/Urgence : 911/)).toBeInTheDocument();
  });

  it('shows an emergency answer highlighted and without feedback buttons', async () => {
    mockRoutes(
      {
        'POST /chat/messages': () => [
          200,
          { id: 'm2', kind: 'emergency', answer: 'Appelez le 911 maintenant.', sources: [] },
        ],
      },
      { loggedIn: false },
    );
    renderAt('/');

    await ask("J'ai mal à la poitrine");

    const answer = await screen.findByText('Appelez le 911 maintenant.');
    expect(answer.closest('li')).toHaveClass('chat__message--emergency');
    expect(screen.queryByText('Cette réponse vous a aidé ?')).not.toBeInTheDocument();
  });

  it('sends feedback once and thanks the visitor', async () => {
    const calls = mockRoutes(
      { 'POST /chat/messages': () => [200, ANSWER], 'POST /chat/feedback': () => [204, {}] },
      { loggedIn: false },
    );
    renderAt('/');
    await ask('Où se garer ?');

    await userEvent.click(await screen.findByRole('button', { name: 'Oui' }));

    expect(screen.getByText('Merci pour votre avis.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Oui' })).not.toBeInTheDocument();
    const sent = calls.filter((c) => c.key === 'POST /chat/feedback');
    expect(sent).toEqual([expect.objectContaining({ body: { message_id: 'm1', helpful: true } })]);
  });

  it('explains when too many questions are asked', async () => {
    mockRoutes({ 'POST /chat/messages': () => [429, {}] }, { loggedIn: false });
    renderAt('/');

    await ask('Adresse ?');

    expect(await screen.findByText(/Trop de questions/)).toBeInTheDocument();
  });

  it('does not send an empty question', async () => {
    const calls = mockRoutes({}, { loggedIn: false });
    renderAt('/');

    await userEvent.click(screen.getByRole('button', { name: /questions/i }));

    expect(screen.getByRole('button', { name: 'Envoyer' })).toBeDisabled();
    await waitFor(() => expect(calls.some((c) => c.key === 'POST /chat/messages')).toBe(false));
  });
});

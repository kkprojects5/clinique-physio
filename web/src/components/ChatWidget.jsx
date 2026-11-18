import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { apiPost } from '../api/client';

const MAX_LENGTH = 500;

/**
 * Chatbot for practical questions (B-BOT-01 to 05). Answers come only from the clinic's
 * documents; emergencies get 911 / 811 / 9-8-8 only; medical questions are refused by the API.
 * Nothing is kept in the browser: the conversation disappears when the page is closed.
 */
export default function ChatWidget() {
  const { t, i18n } = useTranslation();
  const language = i18n.language === 'en' ? 'en' : 'fr';
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const inputRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: 'end' });
  }, [messages]);

  async function send(event) {
    event.preventDefault();
    const question = text.trim();
    if (!question || sending) return;
    setText('');
    setMessages((list) => [...list, { from: 'me', text: question }]);
    setSending(true);
    try {
      const { status, data } = await apiPost('/chat/messages', { message: question, language });
      const reply =
        status === 200
          ? { from: 'bot', ...data }
          : {
              from: 'bot',
              kind: 'error',
              answer: t(status === 429 ? 'chat.tooMany' : 'chat.error'),
            };
      setMessages((list) => [...list, reply]);
    } catch {
      setMessages((list) => [...list, { from: 'bot', kind: 'error', answer: t('chat.error') }]);
    } finally {
      setSending(false);
    }
  }

  async function rate(message, helpful) {
    setMessages((list) => list.map((m) => (m === message ? { ...m, rated: helpful } : m)));
    await apiPost('/chat/feedback', { message_id: message.id, helpful }).catch(() => {});
  }

  if (!open) {
    return (
      <button type="button" className="chat-toggle" onClick={() => setOpen(true)}>
        {t('chat.open')}
      </button>
    );
  }

  return (
    <section className="chat" aria-labelledby="chat-title">
      <header className="chat__header">
        <h2 id="chat-title">{t('chat.title')}</h2>
        <button
          type="button"
          className="chat__close"
          onClick={() => setOpen(false)}
          aria-label={t('chat.close')}
        >
          ×
        </button>
      </header>
      <p className="chat__notice">{t('chat.notice')}</p>
      <ol className="chat__messages" aria-live="polite">
        {messages.length === 0 && <li className="chat__hint">{t('chat.hint')}</li>}
        {messages.map((m, i) => (
          <li
            key={i}
            className={`chat__message chat__message--${m.from} chat__message--${m.kind || ''}`}
          >
            {m.from === 'bot' && <span className="visually-hidden">{t('chat.botSays')}</span>}
            <p>{m.answer ?? m.text}</p>
            {m.sources?.length > 0 && (
              <p className="chat__sources">
                {t('chat.source')} {m.sources.map((s) => s.title).join(', ')}
              </p>
            )}
            {m.id && m.kind === 'answer' && (
              <Feedback rated={m.rated} onRate={(helpful) => rate(m, helpful)} />
            )}
          </li>
        ))}
        {sending && <li className="chat__hint">{t('chat.thinking')}</li>}
        <li ref={endRef} aria-hidden="true" />
      </ol>
      <form className="chat__form" onSubmit={send}>
        <label htmlFor="chat-input" className="visually-hidden">
          {t('chat.label')}
        </label>
        <input
          id="chat-input"
          ref={inputRef}
          value={text}
          maxLength={MAX_LENGTH}
          autoComplete="off"
          placeholder={t('chat.placeholder')}
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit" className="button" disabled={sending || !text.trim()}>
          {t('chat.send')}
        </button>
      </form>
    </section>
  );
}

function Feedback({ rated, onRate }) {
  const { t } = useTranslation();
  if (rated !== undefined) return <p className="chat__thanks">{t('chat.thanks')}</p>;
  return (
    <p className="chat__feedback">
      {t('chat.helpful')}{' '}
      <button type="button" onClick={() => onRate(true)}>
        {t('chat.yes')}
      </button>{' '}
      <button type="button" onClick={() => onRate(false)}>
        {t('chat.no')}
      </button>
    </p>
  );
}

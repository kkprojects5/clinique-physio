import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { apiPost } from '../api/client';

// Same message whether or not the account exists: the page reveals nothing (B-AUTH-03).
export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [state, setState] = useState('idle'); // idle, sending, sent, tooMany, error

  async function submit(event) {
    event.preventDefault();
    setState('sending');
    try {
      const { status } = await apiPost('/auth/password/forgot', { email });
      setState(status === 202 ? 'sent' : status === 429 ? 'tooMany' : 'error');
    } catch {
      setState('error');
    }
  }

  return (
    <section className="narrow">
      <h1>{t('account.forgot.title')}</h1>
      {state === 'sent' ? (
        <p className="status status--ok" role="status">
          {t('account.forgot.sent')}
        </p>
      ) : (
        <form className="panel form" onSubmit={submit}>
          <p className="hint">{t('account.forgot.intro')}</p>
          <div className="field">
            <label htmlFor="email">{t('account.email')}</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          {state === 'tooMany' && <Problem text={t('account.tooMany')} />}
          {state === 'error' && <Problem text={t('status.error')} />}
          <button type="submit" className="button" disabled={state === 'sending'}>
            {t('account.forgot.submit')}
          </button>
        </form>
      )}
    </section>
  );
}

export function Problem({ text, children }) {
  return (
    <div className="status status--error" role="alert">
      <p>{text}</p>
      {children}
    </div>
  );
}

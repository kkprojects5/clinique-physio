import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiPost } from '../api/client';
import { Problem } from './ForgotPassword';

const MIN_LENGTH = 12;

export default function ResetPassword() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  // Keep the token in memory and take it out of the address bar, so it is not left in the
  // browser history or shown on screen.
  const [token] = useState(() => params.get('token') || '');
  useEffect(() => {
    if (params.has('token')) setParams({}, { replace: true });
  }, [params, setParams]);

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [state, setState] = useState('idle'); // idle, sending, done, invalid, weak, tooMany, error
  const [localError, setLocalError] = useState('');

  const askAgain = (
    <Link to="/mot-de-passe-oublie" className="button button--ghost button--small">
      {t('account.reset.askAgain')}
    </Link>
  );

  if (!token) {
    return (
      <section className="narrow">
        <h1>{t('account.reset.title')}</h1>
        <Problem text={t('account.reset.invalid')}>{askAgain}</Problem>
      </section>
    );
  }

  async function submit(event) {
    event.preventDefault();
    if (password.length < MIN_LENGTH) return setLocalError(t('account.reset.tooShort'));
    if (password !== confirm) return setLocalError(t('account.reset.mismatch'));
    setLocalError('');
    setState('sending');
    try {
      const { status } = await apiPost('/auth/password/reset', { token, new_password: password });
      const states = { 200: 'done', 400: 'invalid', 422: 'weak', 429: 'tooMany' };
      setState(states[status] || 'error');
    } catch {
      setState('error');
    }
  }

  return (
    <section className="narrow">
      <h1>{t('account.reset.title')}</h1>
      {state === 'done' ? (
        <p className="status status--ok" role="status">
          {t('account.reset.done')}
        </p>
      ) : state === 'invalid' ? (
        <Problem text={t('account.reset.invalid')}>{askAgain}</Problem>
      ) : (
        <form className="panel form" onSubmit={submit}>
          <p className="hint">{t('account.reset.rules')}</p>
          <div className="field">
            <label htmlFor="new-password">{t('account.reset.newPassword')}</label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={MIN_LENGTH}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="confirm-password">{t('account.reset.confirm')}</label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </div>
          {localError && <Problem text={localError} />}
          {state === 'weak' && <Problem text={t('account.reset.weak')} />}
          {state === 'tooMany' && <Problem text={t('account.tooMany')} />}
          {state === 'error' && <Problem text={t('status.error')} />}
          <button type="submit" className="button" disabled={state === 'sending'}>
            {t('account.reset.submit')}
          </button>
        </form>
      )}
    </section>
  );
}

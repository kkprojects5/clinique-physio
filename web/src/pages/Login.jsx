import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthContext';
import { Problem } from './ForgotPassword';

/** Only go back to a page of this site (never to another website: open redirect). */
export function safeNext(value) {
  return value && value.startsWith('/') && !value.startsWith('//') ? value : '/mes-rendez-vous';
}

export default function Login() {
  const { t } = useTranslation();
  const { login, verifyCode } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get('next'));

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [mfaToken, setMfaToken] = useState(null);
  const [state, setState] = useState('idle');

  async function submitPassword(event) {
    event.preventDefault();
    setState('sending');
    const { result, mfaToken: ticket } = await login(email, password);
    if (result === 'ok') return navigate(next, { replace: true });
    if (result === 'mfa') {
      setMfaToken(ticket);
      return setState('idle');
    }
    setState(result);
  }

  async function submitCode(event) {
    event.preventDefault();
    setState('sending');
    const result = await verifyCode(mfaToken, code);
    if (result === 'ok') return navigate(next, { replace: true });
    setState(result);
  }

  const problems = {
    invalid: t('login.invalid'),
    unverified: t('login.unverified'),
    tooMany: t('account.tooMany'),
    invalidCode: t('login.invalidCode'),
    mfa_setup: t('login.mfaSetup'),
    error: t('status.error'),
  };

  return (
    <section className="narrow">
      <h1>{t('login.title')}</h1>
      {mfaToken ? (
        <form className="panel form" onSubmit={submitCode}>
          <p className="hint">{t('login.codeIntro')}</p>
          <div className="field">
            <label htmlFor="code">{t('login.code')}</label>
            <input
              id="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            />
          </div>
          {problems[state] && <Problem text={problems[state]} />}
          <button type="submit" className="button" disabled={state === 'sending'}>
            {t('login.verify')}
          </button>
        </form>
      ) : (
        <form className="panel form" onSubmit={submitPassword}>
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
          <div className="field">
            <label htmlFor="password">{t('login.password')}</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {problems[state] && <Problem text={problems[state]} />}
          <button type="submit" className="button" disabled={state === 'sending'}>
            {t('login.submit')}
          </button>
          <p className="hint">
            <Link to="/mot-de-passe-oublie">{t('account.forgot.link')}</Link>
            {' · '}
            <Link to={`/inscription?next=${encodeURIComponent(next)}`}>{t('login.register')}</Link>
          </p>
        </form>
      )}
    </section>
  );
}

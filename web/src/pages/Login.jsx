import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import QRCode from 'qrcode';
import { useAuth } from '../auth/AuthContext';
import { Problem } from './ForgotPassword';

const HOME_BY_ROLE = { patient: '/mes-rendez-vous', therapist: '/espace-therapeute' };

/** Only go back to a page of this site (never to another website: open redirect). */
export function safeNext(value, role = 'patient') {
  if (value && value.startsWith('/') && !value.startsWith('//')) return value;
  return HOME_BY_ROLE[role] || '/';
}

export default function Login() {
  const { t } = useTranslation();
  const { login, verifyCode, setupCode } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const requested = params.get('next');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [mfa, setMfa] = useState(null); // { token, setup }
  const [state, setState] = useState('idle');

  const goOn = (role) => navigate(safeNext(requested, role), { replace: true });

  async function submitPassword(event) {
    event.preventDefault();
    setState('sending');
    const { result, role, mfaToken } = await login(email, password);
    if (result === 'ok') return goOn(role);
    if (result === 'mfa' || result === 'mfa_setup') {
      setMfa({ token: mfaToken, setup: result === 'mfa_setup' });
      return setState('idle');
    }
    setState(result);
  }

  async function submitCode(event) {
    event.preventDefault();
    setState('sending');
    const { result, role } = await verifyCode(mfa.token, code);
    if (result === 'ok') return goOn(role);
    setState(result);
  }

  const problems = {
    invalid: t('login.invalid'),
    unverified: t('login.unverified'),
    tooMany: t('account.tooMany'),
    invalidCode: t('login.invalidCode'),
    error: t('status.error'),
  };

  return (
    <section className="narrow">
      <h1>{t('login.title')}</h1>
      {mfa ? (
        <form className="panel form" onSubmit={submitCode}>
          {mfa.setup ? (
            <SetupCode mfaToken={mfa.token} setupCode={setupCode} />
          ) : (
            <p className="hint">{t('login.codeIntro')}</p>
          )}
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
            <Link
              to={requested ? `/inscription?next=${encodeURIComponent(requested)}` : '/inscription'}
            >
              {t('login.register')}
            </Link>
          </p>
        </form>
      )}
    </section>
  );
}

/** First staff login: show the QR code to scan with an authenticator app (B-AUTH-04). */
function SetupCode({ mfaToken, setupCode }) {
  const { t } = useTranslation();
  const [setup, setSetup] = useState(null);
  const [image, setImage] = useState('');
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    setupCode(mfaToken)
      .then(async (data) => {
        if (!active) return;
        if (!data) return setFailed(true);
        setSetup(data);
        setImage(await QRCode.toDataURL(data.otpauth_uri, { margin: 1, width: 220 }));
      })
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
    };
  }, [mfaToken, setupCode]);

  if (failed) return <Problem text={t('status.error')} />;
  return (
    <div className="setup">
      <p className="hint">{t('login.setupIntro')}</p>
      {image && <img src={image} alt={t('login.qrAlt')} width="220" height="220" />}
      {setup && (
        <p className="hint">
          {t('login.manualKey')} <code className="secret">{setup.secret}</code>
        </p>
      )}
    </div>
  );
}

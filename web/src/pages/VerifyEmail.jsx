import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiPost } from '../api/client';
import { Problem } from './ForgotPassword';

// Opened from the confirmation email sent at registration (B-AUTH-01).
export default function VerifyEmail() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [state, setState] = useState(token ? 'checking' : 'invalid');
  const sent = useRef(false);

  useEffect(() => {
    if (!token || sent.current) return;
    sent.current = true; // send once, even when React runs effects twice in development
    apiPost('/auth/verify-email', { token })
      .then(({ status }) => setState(status === 200 ? 'done' : 'invalid'))
      .catch(() => setState('error'));
  }, [token]);

  return (
    <section className="narrow">
      <h1>{t('account.verify.title')}</h1>
      {state === 'checking' && (
        <p className="status" role="status">
          {t('status.loading')}
        </p>
      )}
      {state === 'done' && (
        <p className="status status--ok" role="status">
          {t('account.verify.done')}
        </p>
      )}
      {state === 'invalid' && <Problem text={t('account.verify.invalid')} />}
      {state === 'error' && <Problem text={t('status.error')} />}
    </section>
  );
}

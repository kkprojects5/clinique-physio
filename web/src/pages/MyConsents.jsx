import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useApiData } from '../auth/useApiData';
import { formatDay } from '../utils/format';
import { Problem } from './ForgotPassword';

// My consents (Law 25): what I agreed to, which version and when. The optional consent to
// electronic messages can be given or withdrawn at any time. The privacy policy cannot be
// withdrawn here (it is needed to have an account): a deletion request closes the account.
export default function MyConsents() {
  const { t, i18n } = useTranslation();
  const { api } = useAuth();
  const consents = useApiData('/me/consents');
  const [state, setState] = useState('idle'); // idle, saving, saved, error
  const lang = i18n.language;

  async function change(path, options) {
    setState('saving');
    const { status } = await api(path, options);
    if (status === 200) {
      setState('saved');
      consents.reload();
    } else setState('error');
  }

  if (consents.failed) return <Problem text={t('consents.loadError')} />;
  if (!consents.data) return null;
  const policy = consents.data.find((c) => c.type === 'privacy_policy');
  const comms = consents.data.find((c) => c.type === 'electronic_comms');
  const since = (c) => (c.granted_at ? formatDay(c.granted_at, lang) : '');

  return (
    <section className="panel" aria-labelledby="consents-title">
      <h2 id="consents-title">{t('consents.title')}</h2>
      <h3>{t('consents.policy')}</h3>
      {policy?.given && policy.up_to_date ? (
        <p>{t('consents.policyGiven', { version: policy.version, date: since(policy) })}</p>
      ) : (
        <>
          <p>{t('consents.policyNew', { version: policy?.current_version })}</p>
          <button
            type="button"
            className="button"
            disabled={state === 'saving'}
            onClick={() => change('/me/consents/privacy_policy', { method: 'POST' })}
          >
            {t('consents.accept')}
          </button>
        </>
      )}
      <p className="hint">
        <Link to="/confidentialite">{t('consents.read')}</Link> · {t('consents.policyHint')}
      </p>
      <h3>{t('consents.comms')}</h3>
      <p>
        {comms?.given
          ? t('consents.commsGiven', { date: since(comms) })
          : comms?.revoked_at
            ? t('consents.commsWithdrawn', { date: formatDay(comms.revoked_at, lang) })
            : t('consents.commsNever')}
      </p>
      <button
        type="button"
        className={comms?.given ? 'button button--ghost' : 'button'}
        disabled={state === 'saving'}
        onClick={() =>
          change('/me/consents/electronic_comms', {
            method: 'PUT',
            body: { given: !comms?.given },
          })
        }
      >
        {comms?.given ? t('consents.withdraw') : t('consents.give')}
      </button>
      <p className="hint">{t('consents.commsHint')}</p>
      {state === 'saved' && (
        <p className="notice" role="status">
          {t('consents.saved')}
        </p>
      )}
      {state === 'error' && <Problem text={t('status.error')} />}
    </section>
  );
}

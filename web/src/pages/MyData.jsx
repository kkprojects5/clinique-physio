import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthContext';
import { useApiData } from '../auth/useApiData';
import { formatDay } from '../utils/format';
import { LoadError, Loading } from '../components/Status';
import { Problem } from './ForgotPassword';

const TYPES = ['access', 'correction', 'deletion'];

// My rights under Law 25 (B-ADM-04): ask to see, correct or delete my information, and follow
// the answer. The clinic answers within 30 days.
export default function MyData() {
  const { t, i18n } = useTranslation();
  const { api } = useAuth();
  const requests = useApiData('/me/privacy-requests');
  const [type, setType] = useState('access');
  const [details, setDetails] = useState('');
  const [state, setState] = useState('idle'); // idle, sending, sent, open, error
  const lang = i18n.language;

  async function send(event) {
    event.preventDefault();
    setState('sending');
    const { status } = await api('/me/privacy-requests', {
      method: 'POST',
      body: { type, details: details.trim() || null },
    });
    if (status === 201) {
      setDetails('');
      setState('sent');
      requests.reload();
    } else setState(status === 409 ? 'open' : 'error');
  }

  if (requests.failed) return <LoadError onRetry={requests.reload} />;
  if (!requests.data) return <Loading />;
  return (
    <section>
      <h1>{t('myData.title')}</h1>
      <p>{t('myData.intro')}</p>
      <form className="panel form" onSubmit={send}>
        <h2>{t('myData.newRequest')}</h2>
        <fieldset className="field">
          <legend>{t('myData.what')}</legend>
          {TYPES.map((value) => (
            <label className="check" key={value}>
              <input
                type="radio"
                name="type"
                value={value}
                checked={type === value}
                onChange={() => setType(value)}
              />{' '}
              {t(`myData.types.${value}`)}
            </label>
          ))}
        </fieldset>
        {type === 'deletion' && <p className="hint">{t('myData.deletionHint')}</p>}
        <div className="field">
          <label htmlFor="details">{t('myData.details')}</label>
          <textarea
            id="details"
            rows={3}
            maxLength={1000}
            value={details}
            onChange={(e) => setDetails(e.target.value)}
          />
        </div>
        <p className="hint">{t('myData.noHealth')}</p>
        {state === 'sent' && (
          <p className="notice" role="status">
            {t('myData.sent')}
          </p>
        )}
        {state === 'open' && <Problem text={t('myData.alreadyOpen')} />}
        {state === 'error' && <Problem text={t('status.error')} />}
        <button type="submit" className="button" disabled={state === 'sending'}>
          {t('myData.send')}
        </button>
      </form>
      <h2>{t('myData.myRequests')}</h2>
      {requests.data.length === 0 ? (
        <p>{t('myData.none')}</p>
      ) : (
        <ul className="request-list">
          {requests.data.map((r) => (
            <li key={r.id} className="panel">
              <p>
                <strong>{t(`myData.types.${r.type}`)}</strong> — {t(`myData.statuses.${r.status}`)}
              </p>
              <p className="hint">
                {t('myData.dates', {
                  asked: formatDay(r.requested_at, lang),
                  due: formatDay(r.due_at, lang),
                })}
              </p>
              {r.outcome && (
                <p>
                  {t('myData.answer')} {r.outcome}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

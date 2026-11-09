import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthContext';
import { formatDay, formatTime } from '../utils/format';
import { LoadError, Loading } from '../components/Status';
import { Problem } from './ForgotPassword';

const DAY_MS = 24 * 60 * 60 * 1000;
const CHANGEABLE = ['held', 'pending_payment', 'confirmed'];

// My upcoming appointments (patients see only their own; the API guarantees it).
export default function MyAppointments() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { api } = useAuth();
  const [params] = useSearchParams();
  const [list, setList] = useState(null);
  const [failed, setFailed] = useState(false);
  const [confirming, setConfirming] = useState(null);
  const [message, setMessage] = useState(
    params.get('changed') ? { ok: true, text: t('mine.changed') } : null,
  );

  const [now] = useState(() => Date.now());

  const load = useCallback(
    () =>
      api('/me/appointments')
        .then(({ status, data }) => {
          if (status === 200) {
            setList(data);
            setFailed(false);
          } else setFailed(true);
        })
        .catch(() => setFailed(true)),
    [api],
  );

  useEffect(() => {
    load();
  }, [load]);

  async function cancel(appointment) {
    const { status, data } = await api(`/appointments/${appointment.id}/cancel`, {
      method: 'POST',
    });
    setConfirming(null);
    if (status === 200) {
      setMessage({
        ok: true,
        text: data.deposit_refunded ? t('mine.cancelledRefund') : t('mine.cancelled'),
      });
      load();
    } else {
      setMessage({
        ok: false,
        text: status === 502 ? t('mine.refundFailed') : t('mine.cannotCancel'),
      });
    }
  }

  if (failed) return <LoadError onRetry={load} />;
  if (!list) return <Loading />;

  const upcoming = list.filter((a) => CHANGEABLE.includes(a.status) || a.status === 'checked_in');
  return (
    <section>
      <h1>{t('mine.title')}</h1>
      {message?.ok && (
        <p className="status status--ok" role="status">
          {message.text}
        </p>
      )}
      {message && !message.ok && <Problem text={message.text} />}
      {upcoming.length === 0 && (
        <p>
          {t('mine.none')} <Link to="/disponibilites">{t('mine.book')}</Link>
        </p>
      )}
      <ul className="cards">
        {upcoming.map((a) => {
          const moreThan24h = new Date(a.start).getTime() - now > DAY_MS;
          const paid = a.status === 'confirmed';
          return (
            <li key={a.id} className="card">
              <h2 className="card__title">
                {formatDay(a.start, lang)}, {formatTime(a.start, lang)}
              </h2>
              <p>
                {lang === 'fr' ? a.service.name_fr : a.service.name_en} — {a.therapist.first_name}{' '}
                {a.therapist.last_name}
              </p>
              <p className={`badge badge--${a.status}`}>{t(`statuses.${a.status}`)}</p>
              {CHANGEABLE.includes(a.status) &&
                (confirming === a.id ? (
                  <div className="status status--error" role="alert">
                    <p>
                      {!paid
                        ? t('mine.confirmUnpaid')
                        : moreThan24h
                          ? t('mine.confirmRefund')
                          : t('mine.confirmFee')}
                    </p>
                    <button type="button" className="button" onClick={() => cancel(a)}>
                      {t('mine.yesCancel')}
                    </button>{' '}
                    <button
                      type="button"
                      className="button button--ghost"
                      onClick={() => setConfirming(null)}
                    >
                      {t('mine.keep')}
                    </button>
                  </div>
                ) : (
                  <div className="actions">
                    {paid && moreThan24h && (
                      <Link
                        className="button button--ghost button--small"
                        to={`/disponibilites?service=${a.service.id}&reschedule=${a.id}`}
                      >
                        {t('mine.reschedule')}
                      </Link>
                    )}
                    <button
                      type="button"
                      className="button button--ghost button--small"
                      onClick={() => setConfirming(a.id)}
                    >
                      {t('mine.cancel')}
                    </button>
                  </div>
                ))}
              {paid && !moreThan24h && <p className="hint">{t('mine.lateHint')}</p>}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

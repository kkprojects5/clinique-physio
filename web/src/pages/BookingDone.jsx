import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthContext';
import { formatDay, formatTime } from '../utils/format';

const EVERY_MS = 2000;
const TRIES = 15; // about 30 seconds

// After paying: Stripe's webhook confirms the appointment within a few seconds. We ask the
// API until it is confirmed, instead of trusting the browser (ADR-007).
export default function BookingDone() {
  const { t, i18n } = useTranslation();
  const { api } = useAuth();
  const [params] = useSearchParams();
  const id = params.get('rdv');
  const [appointment, setAppointment] = useState(null);
  const [gaveUp, setGaveUp] = useState(false);

  useEffect(() => {
    let tries = 0;
    let stopped = false;
    let timer;
    async function check() {
      const { status, data } = await api('/me/appointments');
      if (stopped) return;
      const found = status === 200 ? data.find((a) => a.id === id) : null;
      if (found) setAppointment(found);
      if (found?.status === 'confirmed') return;
      tries += 1;
      if (tries >= TRIES) return setGaveUp(true);
      timer = setTimeout(check, EVERY_MS);
    }
    check().catch(() => setGaveUp(true));
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [api, id]);

  const confirmed = appointment?.status === 'confirmed';
  return (
    <section className="narrow">
      <h1>{confirmed ? t('done.confirmedTitle') : t('done.waitingTitle')}</h1>
      {confirmed ? (
        <p className="status status--ok" role="status">
          {t('done.confirmed', {
            day: formatDay(appointment.start, i18n.language),
            time: formatTime(appointment.start, i18n.language),
            name: `${appointment.therapist.first_name} ${appointment.therapist.last_name}`,
          })}
        </p>
      ) : (
        <p className="status" role="status">
          {gaveUp ? t('done.slow') : t('done.waiting')}
        </p>
      )}
      <Link to="/mes-rendez-vous" className="button button--ghost">
        {t('nav.myAppointments')}
      </Link>
    </section>
  );
}

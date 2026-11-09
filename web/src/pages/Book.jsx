import { useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, useElements, useStripe } from '@stripe/react-stripe-js';
import { useAuth } from '../auth/AuthContext';
import { useServices, useTherapists } from '../api/queries';
import { formatDay, formatPrice, formatTime } from '../utils/format';
import { Loading } from '../components/Status';
import { Problem } from './ForgotPassword';

// Booking (B-BKG-01): summary, hold the time 10 minutes, then pay the deposit with Stripe's
// card form. Card details go from the browser straight to Stripe, never to our API; the
// appointment is confirmed by Stripe's signed webhook (ADR-007).
export default function Book() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { api } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const serviceId = params.get('service');
  const therapistId = params.get('therapist');
  const start = params.get('start');
  const rescheduleId = params.get('reschedule');

  const services = useServices();
  const therapists = useTherapists();
  const [state, setState] = useState('idle');
  const [payment, setPayment] = useState(null);

  const service = services.data?.find((s) => s.id === serviceId);
  const therapist = therapists.data?.find((p) => p.id === therapistId);

  if (!serviceId || !start) return <Problem text={t('book.missing')} />;
  if (services.isPending || therapists.isPending) return <Loading />;
  if (!service) return <Problem text={t('book.missing')} />;

  const problems = {
    taken: t('book.taken'),
    evaluation: t('book.evaluation'),
    late: t('book.late'),
    paymentsOff: t('book.paymentsOff'),
    error: t('status.error'),
  };

  async function reserve() {
    setState('sending');
    try {
      if (rescheduleId) {
        const moved = await api(`/appointments/${rescheduleId}/reschedule`, {
          method: 'POST',
          body: { start, therapist_id: therapistId || null },
        });
        if (moved.status === 200) return navigate('/mes-rendez-vous?changed=1');
        return setState(moved.status === 409 ? refusal(moved.data) : 'error');
      }
      const held = await api('/appointments/hold', {
        method: 'POST',
        body: { service_id: serviceId, therapist_id: therapistId || null, start },
      });
      if (held.status !== 201) return setState(held.status === 409 ? refusal(held.data) : 'error');
      const paid = await api(`/appointments/${held.data.id}/pay`, { method: 'POST' });
      if (paid.status === 200) {
        setPayment(paid.data);
        return setState('paying');
      }
      setState(paid.status === 503 ? 'paymentsOff' : 'error');
    } catch {
      setState('error');
    }
  }

  return (
    <section className="narrow">
      <h1>{rescheduleId ? t('book.rescheduleTitle') : t('book.title')}</h1>
      <dl className="panel summary">
        <dt>{t('book.service')}</dt>
        <dd>{lang === 'fr' ? service.name_fr : service.name_en}</dd>
        <dt>{t('book.when')}</dt>
        <dd>
          {formatDay(start, lang)}, {formatTime(start, lang)}
        </dd>
        <dt>{t('book.with')}</dt>
        <dd>{therapist ? `${therapist.first_name} ${therapist.last_name}` : t('book.first')}</dd>
        {!rescheduleId && (
          <>
            <dt>{t('book.deposit')}</dt>
            <dd>
              {formatPrice(service.deposit_cents, lang)}{' '}
              <span className="hint">
                ({t('book.total', { price: formatPrice(service.price_cents, lang) })})
              </span>
            </dd>
          </>
        )}
      </dl>
      <p className="hint">{t('book.rule')}</p>

      {state === 'paying' && payment ? (
        <PaymentStep payment={payment} />
      ) : (
        <>
          {problems[state] && (
            <Problem text={problems[state]}>
              {state !== 'error' && (
                <Link to="/disponibilites" className="button button--ghost button--small">
                  {t('book.chooseAgain')}
                </Link>
              )}
            </Problem>
          )}
          <button type="button" className="button" onClick={reserve} disabled={state === 'sending'}>
            {rescheduleId ? t('book.confirmChange') : t('book.reserve')}
          </button>
        </>
      )}
    </section>
  );
}

function refusal(data) {
  const detail = data?.detail || '';
  if (detail.includes('initial evaluation')) return 'evaluation';
  if (detail.includes('24 hours')) return 'late';
  return 'taken';
}

function PaymentStep({ payment }) {
  const { t, i18n } = useTranslation();
  // loadStripe must run once per key, not at every render.
  const stripePromise = useMemo(
    () => loadStripe(payment.publishable_key),
    [payment.publishable_key],
  );
  const until = formatTime(payment.appointment.hold_expires_at, i18n.language);
  return (
    <div className="panel form">
      <p className="status" role="status">
        {t('book.heldUntil', { time: until })}
      </p>
      <Elements
        stripe={stripePromise}
        options={{ clientSecret: payment.client_secret, locale: i18n.language }}
      >
        <CardForm payment={payment} />
      </Elements>
      <p className="hint">{t('book.testCard')}</p>
    </div>
  );
}

function CardForm({ payment }) {
  const { t, i18n } = useTranslation();
  const stripe = useStripe();
  const elements = useElements();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const done = `/reserver/termine?rdv=${payment.appointment.id}`;

  async function pay(event) {
    event.preventDefault();
    if (!stripe || !elements) return;
    setBusy(true);
    setMessage('');
    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: `${window.location.origin}${done}` },
      redirect: 'if_required', // cards finish here; some methods need Stripe's page
    });
    if (error) {
      setMessage(error.message || t('status.error'));
      setBusy(false);
      return;
    }
    navigate(done);
  }

  return (
    <form onSubmit={pay} className="form">
      <PaymentElement />
      {message && <Problem text={message} />}
      <button type="submit" className="button" disabled={!stripe || busy}>
        {t('book.pay', { amount: formatPrice(payment.amount_cents, i18n.language) })}
      </button>
    </form>
  );
}

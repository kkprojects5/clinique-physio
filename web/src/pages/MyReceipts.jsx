import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthContext';
import { useApiData } from '../auth/useApiData';
import { saveFile } from '../api/client';
import { formatDay, formatPrice } from '../utils/format';
import { Problem } from './ForgotPassword';

// Receipts of past visits, for the patient's insurer (B-BKG-10). Shown under My appointments.
export default function MyReceipts() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { api } = useAuth();
  const receipts = useApiData('/me/receipts');
  const [problem, setProblem] = useState('');

  if (!receipts.data || receipts.data.length === 0) return null;

  async function download(receipt) {
    setProblem('');
    const { status, data } = await api(`/appointments/${receipt.appointment_id}/receipt`, {
      file: true,
    });
    if (status === 200) saveFile(data, `${receipt.receipt_number}.pdf`);
    else setProblem(t('receipts.failed'));
  }

  return (
    <section aria-labelledby="receipts-title">
      <h2 id="receipts-title">{t('receipts.title')}</h2>
      <p className="hint">{t('receipts.intro')}</p>
      {problem && <Problem text={problem} />}
      <ul className="request-list">
        {receipts.data.map((r) => (
          <li key={r.appointment_id} className="panel receipt">
            <p>
              <strong>{formatDay(r.start, lang)}</strong> —{' '}
              {lang === 'fr' ? r.service_fr : r.service_en}, {r.therapist}
            </p>
            <p>
              {t('receipts.paid', { amount: formatPrice(r.paid_cents, lang) })} · {r.receipt_number}
            </p>
            <button
              type="button"
              className="button button--ghost button--small"
              onClick={() => download(r)}
            >
              {t('receipts.download')}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

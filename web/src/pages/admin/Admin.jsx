import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import ServicesAdmin from './ServicesAdmin';
import StaffAdmin from './StaffAdmin';
import AuditAdmin from './AuditAdmin';
import PrivacyAdmin from './PrivacyAdmin';
import IncidentsAdmin from './IncidentsAdmin';
import ReportsAdmin from './ReportsAdmin';

const TABS = [
  ['services', ServicesAdmin],
  ['staff', StaffAdmin],
  ['audit', AuditAdmin],
  ['privacy', PrivacyAdmin],
  ['incidents', IncidentsAdmin],
  ['reports', ReportsAdmin],
];

/** Clinic administration (B-ADM-01 to 05). The API checks the admin role and MFA. */
export default function Admin() {
  const { t } = useTranslation();
  const [tab, setTab] = useState('services');
  const Current = TABS.find(([key]) => key === tab)[1];
  return (
    <section>
      <h1>{t('admin.title')}</h1>
      <div className="tabs" role="tablist" aria-label={t('admin.title')}>
        {TABS.map(([key]) => (
          <button
            key={key}
            type="button"
            role="tab"
            id={`tab-${key}`}
            aria-selected={tab === key}
            aria-controls="admin-panel"
            className={`tabs__tab${tab === key ? ' tabs__tab--active' : ''}`}
            onClick={() => setTab(key)}
          >
            {t(`admin.tabs.${key}`)}
          </button>
        ))}
      </div>
      <div id="admin-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        <Current />
      </div>
    </section>
  );
}

/** "120,00" or "120.5" (dollars typed by a person) to cents; NaN if not a number. */
export function toCents(text) {
  const value = Number(String(text).replace(',', '.').trim());
  return Number.isFinite(value) && String(text).trim() !== '' ? Math.round(value * 100) : NaN;
}

/** The first error message of an API answer, for display. */
export function apiError(data, fallback) {
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return fallback;
}

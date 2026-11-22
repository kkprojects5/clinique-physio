import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useApiData } from '../../auth/useApiData';
import { addDays, clinicToday, formatPrice } from '../../utils/format';
import { LoadError, Loading } from '../../components/Status';

const hours = (minutes, lang) =>
  new Intl.NumberFormat(lang === 'en' ? 'en-CA' : 'fr-CA', { maximumFractionDigits: 1 }).format(
    minutes / 60,
  );

const percent = (rate, lang) =>
  rate === null || rate === undefined
    ? '—'
    : new Intl.NumberFormat(lang === 'en' ? 'en-CA' : 'fr-CA', {
        style: 'percent',
        maximumFractionDigits: 0,
      }).format(rate);

/** "2026-11-23" to "23 nov." / "Nov 23", read as a calendar date (no time zone shift). */
const shortDay = (key, lang) =>
  new Intl.DateTimeFormat(lang === 'en' ? 'en-CA' : 'fr-CA', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  }).format(new Date(`${key}T00:00:00Z`));

// Weekly report (B-ADM-02): appointments, occupancy, cancellations, no-shows, revenue.
// Counts and totals only: the API never sends patient names here.
export default function ReportsAdmin() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const [week, setWeek] = useState(clinicToday());
  const report = useApiData(`/admin/reports/weekly?week=${week}`);

  if (report.failed) return <LoadError onRetry={report.reload} />;
  const r = report.data;

  return (
    <>
      <p className="hint">{t('admin.reports.intro')}</p>
      <div className="week-nav">
        <button
          type="button"
          className="button button--ghost button--small"
          onClick={() => setWeek(addDays(week, -7))}
        >
          {t('admin.reports.previous')}
        </button>
        <h2 className="week-nav__title">
          {r
            ? t('admin.reports.week', {
                from: shortDay(r.week_start, lang),
                to: shortDay(r.week_end, lang),
              })
            : '…'}
        </h2>
        <button
          type="button"
          className="button button--ghost button--small"
          onClick={() => setWeek(addDays(week, 7))}
        >
          {t('admin.reports.next')}
        </button>
        <button
          type="button"
          className="button button--ghost button--small"
          onClick={() => setWeek(clinicToday())}
        >
          {t('admin.reports.thisWeek')}
        </button>
      </div>
      {!r ? (
        <Loading />
      ) : (
        <>
          <dl className="stats">
            <div className="stat">
              <dt>{t('admin.reports.appointments')}</dt>
              <dd>{r.appointments}</dd>
            </div>
            <div className="stat">
              <dt>{t('admin.reports.occupancy')}</dt>
              <dd>{percent(r.occupancy, lang)}</dd>
            </div>
            <div className="stat">
              <dt>{t('admin.reports.noShowRate')}</dt>
              <dd>{percent(r.no_show_rate, lang)}</dd>
            </div>
            <div className="stat">
              <dt>{t('admin.reports.revenue')}</dt>
              <dd>{formatPrice(r.revenue_cents, lang)}</dd>
            </div>
          </dl>
          <dl className="summary">
            <dt>{t('admin.reports.seen')}</dt>
            <dd>{r.seen}</dd>
            <dt>{t('admin.reports.upcoming')}</dt>
            <dd>{r.confirmed}</dd>
            <dt>{t('admin.reports.noShows')}</dt>
            <dd>{r.no_shows}</dd>
            <dt>{t('admin.reports.cancelledPatient')}</dt>
            <dd>{r.cancelled_by_patient}</dd>
            <dt>{t('admin.reports.cancelledClinic')}</dt>
            <dd>{r.cancelled_by_clinic}</dd>
            <dt>{t('admin.reports.deposits')}</dt>
            <dd>{formatPrice(r.deposits_cents, lang)}</dd>
            <dt>{t('admin.reports.desk')}</dt>
            <dd>{formatPrice(r.desk_cents, lang)}</dd>
            <dt>{t('admin.reports.refunds')}</dt>
            <dd>{formatPrice(r.refunds_cents ? -r.refunds_cents : 0, lang)}</dd>
          </dl>
          <div className="table-wrap">
            <table>
              <caption className="visually-hidden">{t('admin.reports.byTherapist')}</caption>
              <thead>
                <tr>
                  <th scope="col">{t('admin.reports.therapist')}</th>
                  <th scope="col">{t('admin.reports.appointments')}</th>
                  <th scope="col">{t('admin.reports.seen')}</th>
                  <th scope="col">{t('admin.reports.noShows')}</th>
                  <th scope="col">{t('admin.reports.hours')}</th>
                  <th scope="col">{t('admin.reports.occupancy')}</th>
                </tr>
              </thead>
              <tbody>
                {r.therapists.map((row) => (
                  <tr key={row.therapist_id}>
                    <th scope="row">
                      {row.first_name} {row.last_name}
                    </th>
                    <td>{row.appointments}</td>
                    <td>{row.seen}</td>
                    <td>{row.no_shows}</td>
                    <td>
                      {t('admin.reports.hoursValue', {
                        booked: hours(row.booked_minutes, lang),
                        working: hours(row.working_minutes, lang),
                      })}
                    </td>
                    <td>{percent(row.occupancy, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="hint">{t('admin.reports.definitions')}</p>
        </>
      )}
    </>
  );
}

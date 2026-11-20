import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../auth/AuthContext';
import { formatDay, formatTime } from '../../utils/format';
import { LoadError, Loading } from '../../components/Status';

const ACTIONS = [
  '',
  'read',
  'create',
  'update',
  'sign',
  'amend',
  'access_denied',
  'deactivate',
  'activate',
  'invite',
];

// Audit log viewer (B-ADM-03): who opened or changed what, when and from which app.
// Reading it is itself recorded by the API. Entries can never be changed or deleted.
export default function AuditAdmin() {
  const { t, i18n } = useTranslation();
  const { api } = useAuth();
  const [filters, setFilters] = useState({
    date_from: '',
    date_to: '',
    action: '',
    actor: '',
    patient: null, // { id, name } when a patient's name was clicked
  });
  const [applied, setApplied] = useState(filters);
  const [entries, setEntries] = useState(null);
  const [next, setNext] = useState(null);
  const [failed, setFailed] = useState(false);

  /** One page of entries as { entries, next_before_id }, or null if the API refused. */
  const fetchPage = useCallback(
    async (before) => {
      const params = new URLSearchParams();
      if (applied.date_from) params.set('date_from', applied.date_from);
      if (applied.date_to) params.set('date_to', applied.date_to);
      if (applied.action) params.set('action', applied.action);
      if (applied.actor.trim()) params.set('actor_email', applied.actor.trim());
      if (applied.patient) params.set('patient_id', applied.patient.id);
      if (before) params.set('before_id', before);
      const query = params.toString();
      const { status, data } = await api(`/admin/audit${query ? `?${query}` : ''}`);
      return status === 200 ? data : null;
    },
    [api, applied],
  );

  const show = useCallback((page, append) => {
    if (!page) return setFailed(true);
    setFailed(false);
    setEntries((old) => (append ? [...(old || []), ...page.entries] : page.entries));
    setNext(page.next_before_id);
  }, []);

  useEffect(() => {
    let active = true;
    fetchPage(null)
      .then((page) => active && show(page, false))
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
    };
  }, [fetchPage, show]);

  const set = (name, value) => setFilters((f) => ({ ...f, [name]: value }));
  function choosePatient(patient) {
    const next = { ...filters, patient };
    setFilters(next);
    setEntries(null);
    setApplied(next);
  }
  const lang = i18n.language;

  return (
    <>
      <p className="hint">{t('admin.audit.intro')}</p>
      <p className="hint">{t('admin.audit.unusualHint')}</p>
      <form
        className="filters"
        onSubmit={(e) => {
          e.preventDefault();
          setEntries(null);
          setApplied(filters);
        }}
      >
        <div className="field">
          <label htmlFor="audit-from">{t('admin.audit.from')}</label>
          <input
            id="audit-from"
            type="date"
            value={filters.date_from}
            onChange={(e) => set('date_from', e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="audit-to">{t('admin.audit.to')}</label>
          <input
            id="audit-to"
            type="date"
            value={filters.date_to}
            onChange={(e) => set('date_to', e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="audit-action">{t('admin.audit.action')}</label>
          <select
            id="audit-action"
            value={filters.action}
            onChange={(e) => set('action', e.target.value)}
          >
            {ACTIONS.map((a) => (
              <option key={a} value={a}>
                {a ? t(`admin.audit.actions.${a}`) : t('admin.audit.all')}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="audit-actor">{t('admin.audit.actor')}</label>
          <input
            id="audit-actor"
            type="email"
            value={filters.actor}
            onChange={(e) => set('actor', e.target.value)}
          />
        </div>
        <button type="submit" className="button">
          {t('admin.audit.filter')}
        </button>
        {applied.patient && (
          <p className="chip">
            {t('admin.audit.patientFilter', { name: applied.patient.name })}{' '}
            <button
              type="button"
              className="chip__remove"
              aria-label={t('admin.audit.removePatient')}
              onClick={() => choosePatient(null)}
            >
              ×
            </button>
          </p>
        )}
      </form>
      {failed && <LoadError onRetry={() => fetchPage(null).then((page) => show(page, false))} />}
      {!failed && !entries && <Loading />}
      {entries && entries.length === 0 && <p>{t('admin.audit.none')}</p>}
      {entries && entries.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">{t('admin.audit.when')}</th>
                <th scope="col">{t('admin.audit.actor')}</th>
                <th scope="col">{t('admin.audit.action')}</th>
                <th scope="col">{t('admin.audit.what')}</th>
                <th scope="col">{t('admin.audit.patient')}</th>
                <th scope="col">{t('admin.audit.app')}</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} className={e.unusual ? 'row--alert' : ''}>
                  <td>
                    {formatDay(e.created_at, lang)}
                    <div className="nowrap">{formatTime(e.created_at, lang)}</div>
                  </td>
                  <td>
                    {e.actor_email || '—'}
                    {e.actor_role && <div className="hint">{t(`admin.roles.${e.actor_role}`)}</div>}
                  </td>
                  <td>{t(`admin.audit.actions.${e.action}`, { defaultValue: e.action })}</td>
                  <td>
                    {t(`admin.audit.resources.${e.resource_type}`, {
                      defaultValue: e.resource_type,
                    })}
                  </td>
                  <td>
                    {e.patient_name ? (
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => choosePatient({ id: e.patient_id, name: e.patient_name })}
                      >
                        {e.patient_name}
                      </button>
                    ) : (
                      '—'
                    )}
                    {e.unusual && <div className="alert-text">{t('admin.audit.unusual')}</div>}
                  </td>
                  <td>
                    {e.client_app || '—'}
                    {e.ip && <div className="hint">{e.ip}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {next && (
        <button
          type="button"
          className="button button--ghost"
          onClick={() => fetchPage(next).then((page) => show(page, true))}
        >
          {t('admin.audit.older')}
        </button>
      )}
    </>
  );
}

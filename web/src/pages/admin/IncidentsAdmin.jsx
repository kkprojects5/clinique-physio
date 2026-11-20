import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../auth/AuthContext';
import { useApiData } from '../../auth/useApiData';
import { formatDay } from '../../utils/format';
import { LoadError, Loading } from '../../components/Status';
import { Problem } from '../ForgotPassword';
import { apiError } from './Admin';

const EMPTY = {
  occurred_at: '',
  discovered_at: '',
  description: '',
  data_categories: '',
  people_affected: '',
  risk_level: 'low',
  measures: '',
};

/** "2026-11-12" typed in a date field to an ISO time at noon UTC (same day everywhere). */
const toIso = (day) => (day ? `${day}T12:00:00Z` : null);

// Confidentiality incident register (Law 25, B-ADM-05). Entries are never deleted.
export default function IncidentsAdmin() {
  const { t, i18n } = useTranslation();
  const { api } = useAuth();
  const incidents = useApiData('/admin/incidents');
  const [adding, setAdding] = useState(false);
  const [problem, setProblem] = useState('');

  if (incidents.failed) return <LoadError onRetry={incidents.reload} />;
  if (!incidents.data) return <Loading />;
  const lang = i18n.language;

  async function notified(incident, field) {
    setProblem('');
    const today = new Date().toISOString();
    const { status, data } = await api(`/admin/incidents/${incident.id}`, {
      method: 'PATCH',
      body: { [field]: today },
    });
    if (status === 200) incidents.reload();
    else setProblem(apiError(data, t('status.error')));
  }

  return (
    <>
      <p className="hint">{t('admin.incidents.intro')}</p>
      {problem && <Problem text={problem} />}
      {incidents.data.length === 0 && <p>{t('admin.incidents.none')}</p>}
      <ul className="request-list">
        {incidents.data.map((i) => (
          <li key={i.id} className={`panel${i.to_notify.length ? ' panel--alert' : ''}`}>
            <p>
              <strong>{formatDay(i.discovered_at, lang)}</strong> —{' '}
              {t(`admin.incidents.risks.${i.risk_level}`)}
            </p>
            <p>{i.description}</p>
            <dl className="summary">
              <dt>{t('admin.incidents.data')}</dt>
              <dd>{i.data_categories}</dd>
              <dt>{t('admin.incidents.people')}</dt>
              <dd>{i.people_affected ?? '—'}</dd>
              <dt>{t('admin.incidents.measures')}</dt>
              <dd>{i.measures}</dd>
              <dt>{t('admin.incidents.cai')}</dt>
              <dd>{i.cai_notified_at ? formatDay(i.cai_notified_at, lang) : '—'}</dd>
              <dt>{t('admin.incidents.persons')}</dt>
              <dd>{i.persons_notified_at ? formatDay(i.persons_notified_at, lang) : '—'}</dd>
            </dl>
            {i.to_notify.length > 0 && (
              <p className="alert-text">{t('admin.incidents.toNotify')}</p>
            )}
            <div className="actions">
              {i.to_notify.includes('cai') && (
                <button
                  type="button"
                  className="button button--small"
                  onClick={() => notified(i, 'cai_notified_at')}
                >
                  {t('admin.incidents.markCai')}
                </button>
              )}
              {i.to_notify.includes('persons') && (
                <button
                  type="button"
                  className="button button--small"
                  onClick={() => notified(i, 'persons_notified_at')}
                >
                  {t('admin.incidents.markPersons')}
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
      {adding ? (
        <IncidentForm
          onDone={() => {
            setAdding(false);
            incidents.reload();
          }}
          onCancel={() => setAdding(false)}
        />
      ) : (
        <button type="button" className="button" onClick={() => setAdding(true)}>
          {t('admin.incidents.new')}
        </button>
      )}
    </>
  );
}

function IncidentForm({ onDone, onCancel }) {
  const { t } = useTranslation();
  const { api } = useAuth();
  const [form, setForm] = useState(EMPTY);
  const [problem, setProblem] = useState('');
  const set = (name, value) => setForm((f) => ({ ...f, [name]: value }));

  async function save(event) {
    event.preventDefault();
    const body = {
      ...form,
      occurred_at: toIso(form.occurred_at),
      discovered_at: toIso(form.discovered_at),
      people_affected: form.people_affected === '' ? null : Number(form.people_affected),
    };
    const { status, data } = await api('/admin/incidents', { method: 'POST', body });
    if (status === 201) onDone();
    else setProblem(apiError(data, t('status.error')));
  }

  return (
    <form className="panel form" onSubmit={save}>
      <h2>{t('admin.incidents.new')}</h2>
      {['occurred_at', 'discovered_at'].map((name) => (
        <div className="field" key={name}>
          <label htmlFor={`inc-${name}`}>{t(`admin.incidents.${name}`)}</label>
          <input
            id={`inc-${name}`}
            type="date"
            required
            value={form[name]}
            onChange={(e) => set(name, e.target.value)}
          />
        </div>
      ))}
      {['description', 'data_categories', 'measures'].map((name) => (
        <div className="field" key={name}>
          <label htmlFor={`inc-${name}`}>{t(`admin.incidents.${name}`)}</label>
          <textarea
            id={`inc-${name}`}
            required
            rows={name === 'data_categories' ? 1 : 3}
            value={form[name]}
            onChange={(e) => set(name, e.target.value)}
          />
        </div>
      ))}
      <div className="field">
        <label htmlFor="inc-people">{t('admin.incidents.people')}</label>
        <input
          id="inc-people"
          type="number"
          min="0"
          value={form.people_affected}
          onChange={(e) => set('people_affected', e.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="inc-risk">{t('admin.incidents.risk')}</label>
        <select
          id="inc-risk"
          value={form.risk_level}
          onChange={(e) => set('risk_level', e.target.value)}
        >
          <option value="low">{t('admin.incidents.risks.low')}</option>
          <option value="serious">{t('admin.incidents.risks.serious')}</option>
        </select>
      </div>
      {problem && <Problem text={problem} />}
      <div className="actions">
        <button type="submit" className="button">
          {t('admin.save')}
        </button>
        <button type="button" className="button button--ghost" onClick={onCancel}>
          {t('admin.cancel')}
        </button>
      </div>
    </form>
  );
}

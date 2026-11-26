import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../auth/AuthContext';
import { useApiData } from '../../auth/useApiData';
import { clinicIso, clinicToday, formatDay, formatTime } from '../../utils/format';
import { LoadError, Loading } from '../../components/Status';
import { Problem } from '../ForgotPassword';

const DAYS = [1, 2, 3, 4, 5, 6, 7];
const hhmm = (time) => time.slice(0, 5); // "08:00:00" -> "08:00"
const toRows = (rules) =>
  rules.map((r) => ({ weekday: r.weekday, start: hhmm(r.start_time), end: hhmm(r.end_time) }));

// My working hours and time off (B-AVL-02). Patients can book only inside these hours,
// outside time off. Times are the clinic's (Montréal).
export default function MyHours() {
  const { t } = useTranslation();
  const availability = useApiData('/therapist/availability');

  if (availability.failed) return <LoadError onRetry={availability.reload} />;
  if (!availability.data) return <Loading />;
  return (
    <section>
      <p>
        <Link to="/espace-therapeute">← {t('workspace.title')}</Link>
      </p>
      <h1>{t('hours.title')}</h1>
      <p className="hint">{t('hours.intro')}</p>
      <WeeklyHours rules={availability.data.rules} />
      <TimeOff exceptions={availability.data.exceptions} onChanged={availability.reload} />
    </section>
  );
}

function WeeklyHours({ rules }) {
  const { t } = useTranslation();
  const { api } = useAuth();
  // Starts from the saved hours; after a save, shows what the server kept.
  const [rows, setRows] = useState(() => toRows(rules));
  const [state, setState] = useState('idle');

  const change = (index, field, value) =>
    setRows(rows.map((row, i) => (i === index ? { ...row, [field]: value } : row)));

  async function save(event) {
    event.preventDefault();
    setState('saving');
    const body = {
      rules: rows.map((r) => ({
        weekday: Number(r.weekday),
        start_time: r.start,
        end_time: r.end,
      })),
    };
    const { status, data } = await api('/therapist/availability', { method: 'PUT', body });
    if (status === 200) {
      setRows(toRows(data.rules));
      setState('saved');
    } else setState(status === 422 ? 'invalid' : 'error');
  }

  return (
    <form className="panel" onSubmit={save} aria-labelledby="weekly-title">
      <h2 id="weekly-title">{t('hours.weekly')}</h2>
      {rows.length === 0 && <p>{t('hours.noHours')}</p>}
      {rows.map((row, index) => (
        <div className="field-row" key={index}>
          <label>
            {t('hours.day')}{' '}
            <select value={row.weekday} onChange={(e) => change(index, 'weekday', e.target.value)}>
              {DAYS.map((d) => (
                <option key={d} value={d}>
                  {t(`hours.days.${d}`)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('hours.from')}{' '}
            <input
              type="time"
              step="900"
              required
              value={row.start}
              onChange={(e) => change(index, 'start', e.target.value)}
            />
          </label>
          <label>
            {t('hours.to')}{' '}
            <input
              type="time"
              step="900"
              required
              value={row.end}
              onChange={(e) => change(index, 'end', e.target.value)}
            />
          </label>
          <button
            type="button"
            className="button button--ghost button--small"
            onClick={() => setRows(rows.filter((_, i) => i !== index))}
          >
            {t('hours.remove')}
          </button>
        </div>
      ))}
      <p>
        <button
          type="button"
          className="button button--ghost"
          onClick={() => setRows([...rows, { weekday: 1, start: '09:00', end: '17:00' }])}
        >
          {t('hours.addHours')}
        </button>{' '}
        <button type="submit" className="button" disabled={state === 'saving'}>
          {t('hours.save')}
        </button>
      </p>
      {state === 'saved' && (
        <p className="notice" role="status">
          {t('hours.saved')}
        </p>
      )}
      {state === 'invalid' && <Problem text={t('hours.invalid')} />}
      {state === 'error' && <Problem text={t('status.error')} />}
    </form>
  );
}

function TimeOff({ exceptions, onChanged }) {
  const { t, i18n } = useTranslation();
  const { api } = useAuth();
  const today = clinicToday();
  const [form, setForm] = useState({ day: today, start: '08:00', endDay: today, end: '17:00' });
  const [reason, setReason] = useState('');
  const [state, setState] = useState('idle');
  const lang = i18n.language;
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  async function add(event) {
    event.preventDefault();
    setState('saving');
    const { status } = await api('/therapist/availability/exceptions', {
      method: 'POST',
      body: {
        starts_at: clinicIso(form.day, form.start),
        ends_at: clinicIso(form.endDay, form.end),
        reason: reason.trim() || null,
      },
    });
    if (status === 201) {
      setState('added');
      setReason('');
      onChanged();
    } else setState(status === 422 ? 'invalid' : 'error');
  }

  async function remove(id) {
    const { status } = await api(`/therapist/availability/exceptions/${id}`, { method: 'DELETE' });
    setState(status === 204 ? 'removed' : 'error');
    onChanged();
  }

  const when = (iso) => `${formatDay(iso, lang)} ${formatTime(iso, lang)}`;
  return (
    <section className="panel" aria-labelledby="timeoff-title">
      <h2 id="timeoff-title">{t('hours.timeOff')}</h2>
      {exceptions.length === 0 ? (
        <p>{t('hours.noTimeOff')}</p>
      ) : (
        <ul>
          {exceptions.map((e) => (
            <li key={e.id}>
              {when(e.starts_at)} → {when(e.ends_at)}
              {e.reason ? ` — ${e.reason}` : ''}{' '}
              <button
                type="button"
                className="button button--ghost button--small"
                onClick={() => remove(e.id)}
              >
                {t('hours.remove')}
              </button>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={add}>
        <div className="field-row">
          <label>
            {t('hours.fromDay')}{' '}
            <input type="date" required value={form.day} onChange={set('day')} />
          </label>
          <label>
            {t('hours.at')}{' '}
            <input type="time" step="900" required value={form.start} onChange={set('start')} />
          </label>
          <label>
            {t('hours.toDay')}{' '}
            <input type="date" required value={form.endDay} onChange={set('endDay')} />
          </label>
          <label>
            {t('hours.at')}{' '}
            <input type="time" step="900" required value={form.end} onChange={set('end')} />
          </label>
        </div>
        <div className="field">
          <label htmlFor="timeoff-reason">{t('hours.reason')}</label>
          <input
            id="timeoff-reason"
            maxLength={200}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <p className="hint">{t('hours.reasonHint')}</p>
        </div>
        <button type="submit" className="button" disabled={state === 'saving'}>
          {t('hours.addTimeOff')}
        </button>
      </form>
      {state === 'added' && (
        <p className="notice" role="status">
          {t('hours.added')}
        </p>
      )}
      {state === 'invalid' && <Problem text={t('hours.invalidTimeOff')} />}
      {state === 'error' && <Problem text={t('status.error')} />}
    </section>
  );
}

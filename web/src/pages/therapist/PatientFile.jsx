import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../auth/AuthContext';
import { useApiData } from '../../auth/useApiData';
import { clinicToday, formatDay, formatTime } from '../../utils/format';
import { LoadError, Loading } from '../../components/Status';
import { Problem } from '../ForgotPassword';

const SOAP = ['subjective', 'objective', 'assessment', 'plan'];
const NOTE_STATUSES = ['confirmed', 'checked_in', 'completed'];

// A patient's file for a therapist who treats them: history, SOAP notes, exercise programs.
// Every opening of the file and of the notes is recorded in the audit log by the API.
export default function PatientFile() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const me = useApiData('/therapist/me');
  const file = useApiData(`/therapist/patients/${id}`);
  const notes = useApiData(`/therapist/patients/${id}/notes`);
  const [now] = useState(() => Date.now());

  if (file.failed) {
    return <Problem text={t('workspace.notFound')} />;
  }
  if (!file.data || !me.data || !notes.data) return <Loading />;
  const p = file.data;
  const lang = i18n.language;
  const noted = new Set(notes.data.filter((n) => !n.amends_note_id).map((n) => n.appointment_id));

  return (
    <section>
      <p>
        <Link to="/espace-therapeute">← {t('workspace.patients')}</Link>
      </p>
      <h1>
        {p.first_name} {p.last_name}
      </h1>
      <dl className="panel summary">
        <dt>{t('register.date_of_birth')}</dt>
        <dd>{p.date_of_birth}</dd>
        <dt>{t('register.phone')}</dt>
        <dd>{p.phone}</dd>
        <dt>{t('workspace.emergency')}</dt>
        <dd>{p.emergency_contact || '—'}</dd>
      </dl>
      <p className="hint">{t('workspace.audited')}</p>

      <h2>{t('workspace.history')}</h2>
      <ul className="cards">
        {p.history.map((a) => {
          const canWrite =
            a.therapist_id === me.data.id &&
            NOTE_STATUSES.includes(a.status) &&
            new Date(a.start).getTime() <= now &&
            !noted.has(a.appointment_id);
          return (
            <li key={a.appointment_id} className="card">
              <h3 className="card__title">
                {formatDay(a.start, lang)}, {formatTime(a.start, lang)}
              </h3>
              <p>
                {lang === 'fr' ? a.service_name_fr : a.service_name_en} — {a.therapist_name}
              </p>
              <p className={`badge badge--${a.status}`}>{t(`statuses.${a.status}`)}</p>
              {canWrite && <NewNote appointmentId={a.appointment_id} onSaved={notes.reload} />}
            </li>
          );
        })}
      </ul>

      <h2>{t('workspace.notes')}</h2>
      <Notes notes={notes.data} meId={me.data.id} onChanged={notes.reload} />

      <h2>{t('workspace.programs')}</h2>
      <Programs patientId={id} />
    </section>
  );
}

function SoapForm({ initial, submitLabel, onSubmit, onCancel }) {
  const { t } = useTranslation();
  const [content, setContent] = useState(
    initial || { subjective: '', objective: '', assessment: '', plan: '' },
  );
  const [problem, setProblem] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (!SOAP.some((k) => content[k].trim())) return setProblem(t('workspace.emptyNote'));
    setBusy(true);
    const message = await onSubmit(content);
    setBusy(false);
    if (message) setProblem(message);
  }

  return (
    <form className="form soap" onSubmit={submit}>
      {SOAP.map((key) => (
        <div className="field" key={key}>
          <label htmlFor={`soap-${key}`}>{t(`soap.${key}`)}</label>
          <textarea
            id={`soap-${key}`}
            rows={3}
            maxLength={5000}
            value={content[key]}
            onChange={(e) => setContent({ ...content, [key]: e.target.value })}
          />
        </div>
      ))}
      {problem && <Problem text={problem} />}
      <div className="actions">
        <button type="submit" className="button" disabled={busy}>
          {submitLabel}
        </button>
        <button type="button" className="button button--ghost" onClick={onCancel}>
          {t('workspace.cancel')}
        </button>
      </div>
    </form>
  );
}

function NewNote({ appointmentId, onSaved }) {
  const { t } = useTranslation();
  const { api } = useAuth();
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <button type="button" className="button button--small" onClick={() => setOpen(true)}>
        {t('workspace.writeNote')}
      </button>
    );
  }
  return (
    <SoapForm
      submitLabel={t('workspace.saveDraft')}
      onCancel={() => setOpen(false)}
      onSubmit={async (content) => {
        const { status, data } = await api(`/therapist/appointments/${appointmentId}/notes`, {
          method: 'POST',
          body: content,
        });
        if (status === 201) {
          setOpen(false);
          onSaved();
          return '';
        }
        return data?.detail || t('status.error');
      }}
    />
  );
}

function Notes({ notes, meId, onChanged }) {
  const { t } = useTranslation();
  const originals = notes.filter((n) => !n.amends_note_id);
  if (originals.length === 0) return <p>{t('workspace.noNotes')}</p>;
  return (
    <ul className="cards">
      {originals.map((note) => (
        <Note
          key={note.id}
          note={note}
          amendments={notes.filter((n) => n.amends_note_id === note.id)}
          mine={note.author_therapist_id === meId}
          onChanged={onChanged}
        />
      ))}
    </ul>
  );
}

function SoapView({ content }) {
  const { t } = useTranslation();
  return (
    <dl className="soap-view">
      {SOAP.map((key) =>
        content[key] ? (
          <div key={key}>
            <dt>{t(`soap.${key}`)}</dt>
            <dd>{content[key]}</dd>
          </div>
        ) : null,
      )}
    </dl>
  );
}

function Note({ note, amendments, mine, onChanged }) {
  const { t, i18n } = useTranslation();
  const { api } = useAuth();
  const [mode, setMode] = useState('view'); // view, edit, amend, sign
  const [problem, setProblem] = useState('');
  const lang = i18n.language;
  const draft = !note.signed_at;

  async function send(path, method, body) {
    const { status, data } = await api(path, { method, body });
    if (status === 200 || status === 201) {
      setMode('view');
      setProblem('');
      onChanged();
      return '';
    }
    return data?.detail || t('status.error');
  }

  return (
    <li className="card">
      <p className={`badge ${draft ? 'badge--held' : 'badge--confirmed'}`}>
        {draft
          ? t('workspace.draft')
          : t('workspace.signedOn', { day: formatDay(note.signed_at, lang) })}
      </p>
      {mode === 'edit' ? (
        <SoapForm
          initial={note.content}
          submitLabel={t('workspace.saveDraft')}
          onCancel={() => setMode('view')}
          onSubmit={(content) => send(`/therapist/notes/${note.id}`, 'PUT', content)}
        />
      ) : (
        <SoapView content={note.content} />
      )}
      {amendments.map((a) => (
        <div key={a.id} className="amendment">
          <p className="badge badge--confirmed">
            {t('workspace.amendment', { day: formatDay(a.created_at, lang) })}
          </p>
          <SoapView content={a.content} />
        </div>
      ))}
      {mode === 'amend' && (
        <SoapForm
          submitLabel={t('workspace.addAmendment')}
          onCancel={() => setMode('view')}
          onSubmit={(content) => send(`/therapist/notes/${note.id}/amendments`, 'POST', content)}
        />
      )}
      {mode === 'sign' && (
        <div className="status status--error" role="alert">
          <p>{t('workspace.signWarning')}</p>
          <div className="actions">
            <button
              type="button"
              className="button"
              onClick={async () =>
                setProblem(await send(`/therapist/notes/${note.id}/sign`, 'POST'))
              }
            >
              {t('workspace.signNow')}
            </button>
            <button type="button" className="button button--ghost" onClick={() => setMode('view')}>
              {t('workspace.cancel')}
            </button>
          </div>
        </div>
      )}
      {problem && <Problem text={problem} />}
      {mode === 'view' && (
        <div className="actions">
          {draft && mine && (
            <>
              <button
                type="button"
                className="button button--ghost button--small"
                onClick={() => setMode('edit')}
              >
                {t('workspace.edit')}
              </button>
              <button
                type="button"
                className="button button--small"
                onClick={() => setMode('sign')}
              >
                {t('workspace.sign')}
              </button>
            </>
          )}
          {!draft && (
            <button
              type="button"
              className="button button--ghost button--small"
              onClick={() => setMode('amend')}
            >
              {t('workspace.amend')}
            </button>
          )}
        </div>
      )}
    </li>
  );
}

function Programs({ patientId }) {
  const { t, i18n } = useTranslation();
  const programs = useApiData(`/therapist/patients/${patientId}/programs`);
  const [creating, setCreating] = useState(false);
  const lang = i18n.language;

  if (programs.failed) return <LoadError onRetry={programs.reload} />;
  if (!programs.data) return <Loading />;
  return (
    <>
      {programs.data.length === 0 && <p>{t('workspace.noPrograms')}</p>}
      <ul className="cards">
        {programs.data.map((program) => (
          <li key={program.id} className="card">
            <h3 className="card__title">
              {t('workspace.programDates', {
                start: program.start_date,
                end: program.end_date,
                weeks: program.weeks,
              })}
            </h3>
            <p className="badge badge--confirmed">
              {t('workspace.adherence', { percent: program.adherence_percent })}
            </p>
            {program.notes && <p>{program.notes}</p>}
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">{t('workspace.exercise')}</th>
                    <th scope="col">{t('workspace.dose')}</th>
                    <th scope="col">{t('workspace.perWeek')}</th>
                    <th scope="col">{t('workspace.done')}</th>
                  </tr>
                </thead>
                <tbody>
                  {program.items.map((item) => (
                    <tr key={item.id}>
                      <td>{lang === 'fr' ? item.exercise.name_fr : item.exercise.name_en}</td>
                      <td>
                        {item.sets} × {item.reps}
                      </td>
                      <td>{item.times_per_week}</td>
                      <td>
                        {item.done_total} / {item.planned_total}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </li>
        ))}
      </ul>
      {creating ? (
        <NewProgram
          patientId={patientId}
          onCancel={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            programs.reload();
          }}
        />
      ) : (
        <button type="button" className="button" onClick={() => setCreating(true)}>
          {t('workspace.newProgram')}
        </button>
      )}
    </>
  );
}

function NewProgram({ patientId, onCancel, onSaved }) {
  const { t, i18n } = useTranslation();
  const { api } = useAuth();
  const library = useApiData('/exercises');
  const [startDate, setStartDate] = useState(clinicToday());
  const [weeks, setWeeks] = useState(4);
  const [notes, setNotes] = useState('');
  const [chosen, setChosen] = useState({}); // exercise id -> times per week
  const [problem, setProblem] = useState('');
  const lang = i18n.language;

  if (!library.data) return <Loading />;

  async function submit(event) {
    event.preventDefault();
    const items = Object.entries(chosen).map(([exerciseId, times]) => ({
      exercise_id: exerciseId,
      times_per_week: Number(times),
    }));
    if (items.length === 0) return setProblem(t('workspace.chooseExercise'));
    const { status, data } = await api(`/therapist/patients/${patientId}/programs`, {
      method: 'POST',
      body: { start_date: startDate, weeks: Number(weeks), notes, items },
    });
    if (status === 201) return onSaved();
    setProblem(typeof data?.detail === 'string' ? data.detail : t('status.error'));
  }

  const toggle = (id) => {
    const next = { ...chosen };
    if (id in next) delete next[id];
    else next[id] = 3;
    setChosen(next);
  };

  return (
    <form className="panel form" onSubmit={submit}>
      <h3>{t('workspace.newProgram')}</h3>
      <div className="filters">
        <div className="field">
          <label htmlFor="program-start">{t('workspace.startDate')}</label>
          <input
            id="program-start"
            type="date"
            min={clinicToday()}
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="program-weeks">{t('workspace.weeks')}</label>
          <input
            id="program-weeks"
            type="number"
            min={1}
            max={26}
            value={weeks}
            onChange={(e) => setWeeks(e.target.value)}
            required
          />
        </div>
      </div>
      <fieldset className="exercise-picker">
        <legend>{t('workspace.exercises')}</legend>
        {library.data.map((exercise) => {
          const name = lang === 'fr' ? exercise.name_fr : exercise.name_en;
          const selected = exercise.id in chosen;
          return (
            <div key={exercise.id} className="exercise-choice">
              <div className="check">
                <input
                  id={`ex-${exercise.id}`}
                  type="checkbox"
                  checked={selected}
                  onChange={() => toggle(exercise.id)}
                />
                <label htmlFor={`ex-${exercise.id}`}>
                  {name}{' '}
                  <span className="hint">
                    ({exercise.default_sets} × {exercise.default_reps})
                  </span>
                </label>
              </div>
              {selected && (
                <label className="inline">
                  {t('workspace.perWeek')}{' '}
                  <input
                    type="number"
                    min={1}
                    max={14}
                    value={chosen[exercise.id]}
                    aria-label={t('workspace.perWeekFor', { name })}
                    onChange={(e) => setChosen({ ...chosen, [exercise.id]: e.target.value })}
                  />
                </label>
              )}
            </div>
          );
        })}
      </fieldset>
      <div className="field">
        <label htmlFor="program-notes">{t('workspace.adviceForPatient')}</label>
        <textarea
          id="program-notes"
          rows={2}
          maxLength={2000}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>
      {problem && <Problem text={problem} />}
      <div className="actions">
        <button type="submit" className="button">
          {t('workspace.giveProgram')}
        </button>
        <button type="button" className="button button--ghost" onClick={onCancel}>
          {t('workspace.cancel')}
        </button>
      </div>
    </form>
  );
}

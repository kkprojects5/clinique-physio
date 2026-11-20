import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthContext';
import { formatDay } from '../utils/format';
import { LoadError, Loading } from '../components/Status';
import { Problem } from './ForgotPassword';

const PAIN_LEVELS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

// My home exercise program on the website (B-EXE-03), the same as in the mobile app:
// check off each exercise once a day with the pain felt; today's check-off can be undone.
// The therapist sees adherence and pain levels in their workspace.
export default function MyExercises() {
  const { t, i18n } = useTranslation();
  const { api } = useAuth();
  const [program, setProgram] = useState(undefined); // undefined: loading, null: none
  const [failed, setFailed] = useState(false);
  const [todayLogs, setTodayLogs] = useState({}); // item id -> check-off id, to undo it
  const [problem, setProblem] = useState('');

  const fetchProgram = useCallback(async () => {
    const { status, data } = await api('/me/program');
    if (status !== 200) throw new Error(String(status));
    return data;
  }, [api]);

  const show = useCallback((data) => {
    setFailed(false);
    setProgram(data);
  }, []);

  useEffect(() => {
    let active = true;
    fetchProgram()
      .then((data) => active && show(data))
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
    };
  }, [fetchProgram, show]);

  const reload = () => fetchProgram().then(show, () => setFailed(true));

  async function done(item, pain) {
    setProblem('');
    const body = { pain_level: pain === '' ? null : Number(pain) };
    const { status, data } = await api(`/me/program/items/${item.id}/check-off`, {
      method: 'POST',
      body,
    });
    if (status === 201) {
      setTodayLogs((logs) => ({ ...logs, [item.id]: data.id }));
      return reload();
    }
    setProblem(status === 409 ? t('myExercises.alreadyDone') : t('status.error'));
  }

  async function undo(item) {
    setProblem('');
    const { status } = await api(`/me/program/check-offs/${todayLogs[item.id]}`, {
      method: 'DELETE',
    });
    if (status === 204) {
      setTodayLogs((logs) => {
        const next = { ...logs };
        delete next[item.id];
        return next;
      });
      return reload();
    }
    setProblem(t('status.error'));
  }

  if (failed) return <LoadError onRetry={reload} />;
  if (program === undefined) return <Loading />;
  const lang = i18n.language;
  if (program === null) {
    return (
      <section>
        <h1>{t('myExercises.title')}</h1>
        <p>{t('myExercises.none')}</p>
      </section>
    );
  }
  return (
    <section>
      <h1>{t('myExercises.title')}</h1>
      <p className="hint">
        {t('myExercises.by', {
          name: `${program.therapist.first_name} ${program.therapist.last_name}`,
          from: formatDay(program.start_date + 'T12:00:00Z', lang),
          to: formatDay(program.end_date + 'T12:00:00Z', lang),
        })}
      </p>
      {program.notes && <p className="panel">{program.notes}</p>}
      <p>
        <strong>{t('myExercises.adherence', { percent: program.adherence_percent })}</strong>
      </p>
      {problem && <Problem text={problem} />}
      <ul className="exercise-list">
        {program.items.map((item) => (
          <Exercise
            key={item.id}
            item={item}
            lang={lang}
            canUndo={Boolean(todayLogs[item.id])}
            onDone={(pain) => done(item, pain)}
            onUndo={() => undo(item)}
          />
        ))}
      </ul>
    </section>
  );
}

function Exercise({ item, lang, canUndo, onDone, onUndo }) {
  const { t } = useTranslation();
  const [pain, setPain] = useState('');
  const [busy, setBusy] = useState(false);
  const exercise = item.exercise;
  const name = lang === 'en' ? exercise.name_en : exercise.name_fr;
  const run = async (action) => {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
    }
  };
  const painId = `pain-${item.id}`;

  return (
    <li className="panel exercise">
      <h2>{name}</h2>
      <p>
        {t('myExercises.dose', { sets: item.sets, reps: item.reps, times: item.times_per_week })}
      </p>
      <p className="hint">
        {t('myExercises.thisWeek', { done: item.done_this_week, planned: item.times_per_week })}
      </p>
      <p>{lang === 'en' ? exercise.description_en : exercise.description_fr}</p>
      <details>
        <summary>{t('myExercises.instructions')}</summary>
        <p>{lang === 'en' ? exercise.instructions_en : exercise.instructions_fr}</p>
      </details>
      {item.done_today ? (
        <p className="done-today">
          ✓ {t('myExercises.doneToday')}{' '}
          {canUndo && (
            <button
              type="button"
              className="button button--small button--ghost"
              disabled={busy}
              onClick={() => run(onUndo)}
            >
              {t('myExercises.undo')}
            </button>
          )}
        </p>
      ) : (
        <div className="check-off">
          <div className="field">
            <label htmlFor={painId}>{t('myExercises.pain')}</label>
            <select id={painId} value={pain} onChange={(e) => setPain(e.target.value)}>
              <option value="">{t('myExercises.noPain')}</option>
              {PAIN_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="button"
            disabled={busy}
            aria-label={t('myExercises.doneFor', { name })}
            onClick={() => run(() => onDone(pain))}
          >
            {t('myExercises.done')}
          </button>
        </div>
      )}
    </li>
  );
}

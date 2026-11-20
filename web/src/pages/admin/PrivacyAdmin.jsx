import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../auth/AuthContext';
import { useApiData } from '../../auth/useApiData';
import { formatDay } from '../../utils/format';
import { LoadError, Loading } from '../../components/Status';
import { Problem } from '../ForgotPassword';
import { apiError } from './Admin';

const OPEN = ['received', 'in_progress'];

// Patients' privacy requests (Law 25, B-ADM-04): answer within 30 days, late ones in red.
export default function PrivacyAdmin() {
  const { t, i18n } = useTranslation();
  const requests = useApiData('/admin/privacy-requests');
  const [open, setOpen] = useState(null);

  if (requests.failed) return <LoadError onRetry={requests.reload} />;
  if (!requests.data) return <Loading />;
  const lang = i18n.language;
  return (
    <>
      <p className="hint">{t('admin.privacy.intro')}</p>
      {requests.data.length === 0 && <p>{t('admin.privacy.none')}</p>}
      <ul className="request-list">
        {requests.data.map((r) => (
          <li key={r.id} className={`panel${r.overdue ? ' panel--alert' : ''}`}>
            <p>
              <strong>{t(`myData.types.${r.type}`)}</strong> — {r.patient_name}{' '}
              <span className="hint">({r.email})</span>
            </p>
            <p className="hint">
              {t('myData.statuses.' + r.status)} ·{' '}
              {t('admin.privacy.due', { date: formatDay(r.due_at, lang) })}
              {r.overdue && <strong className="alert-text"> · {t('admin.privacy.overdue')}</strong>}
            </p>
            {r.details && <p>« {r.details} »</p>}
            {r.outcome && (
              <p>
                {t('myData.answer')} {r.outcome}
              </p>
            )}
            {OPEN.includes(r.status) &&
              (open === r.id ? (
                <Answer
                  request={r}
                  onDone={() => {
                    setOpen(null);
                    requests.reload();
                  }}
                />
              ) : (
                <button
                  type="button"
                  className="button button--small"
                  onClick={() => setOpen(r.id)}
                >
                  {t('admin.privacy.handle')}
                </button>
              ))}
          </li>
        ))}
      </ul>
    </>
  );
}

function Answer({ request, onDone }) {
  const { t } = useTranslation();
  const { api } = useAuth();
  const [outcome, setOutcome] = useState('');
  const [problem, setProblem] = useState('');
  const [exported, setExported] = useState(null);

  async function act(path, options) {
    setProblem('');
    const { status, data } = await api(path, options);
    if (status === 200) return data;
    setProblem(apiError(data, t('status.error')));
    return null;
  }
  const decide = async (status) => {
    if (
      await act(`/admin/privacy-requests/${request.id}`, {
        method: 'PATCH',
        body: { status, outcome },
      })
    )
      onDone();
  };
  async function erase() {
    if (!window.confirm(t('admin.privacy.confirmErase', { name: request.patient_name }))) return;
    if (await act(`/admin/privacy-requests/${request.id}/erase`, { method: 'POST' })) onDone();
  }
  async function exportData() {
    const data = await act(`/admin/privacy-requests/${request.id}/export`);
    if (data) setExported(JSON.stringify(data, null, 2));
  }

  return (
    <div className="answer">
      {request.type === 'access' && (
        <>
          <button type="button" className="button button--small button--ghost" onClick={exportData}>
            {t('admin.privacy.export')}
          </button>
          {exported && (
            <textarea
              className="export"
              readOnly
              rows={8}
              aria-label={t('admin.privacy.exportLabel')}
              value={exported}
            />
          )}
        </>
      )}
      {request.type === 'deletion' ? (
        <>
          <p className="hint">{t('admin.privacy.eraseHint')}</p>
          <button type="button" className="button button--small" onClick={erase}>
            {t('admin.privacy.erase')}
          </button>
        </>
      ) : (
        <div className="field">
          <label htmlFor={`outcome-${request.id}`}>{t('admin.privacy.outcome')}</label>
          <textarea
            id={`outcome-${request.id}`}
            rows={3}
            maxLength={2000}
            value={outcome}
            onChange={(e) => setOutcome(e.target.value)}
          />
        </div>
      )}
      {problem && <Problem text={problem} />}
      <div className="actions">
        {request.status === 'received' && (
          <button
            type="button"
            className="button button--small button--ghost"
            onClick={() => decide('in_progress')}
          >
            {t('admin.privacy.inProgress')}
          </button>
        )}
        {request.type !== 'deletion' && (
          <button
            type="button"
            className="button button--small"
            onClick={() => decide('completed')}
          >
            {t('admin.privacy.complete')}
          </button>
        )}
        <button
          type="button"
          className="button button--small button--ghost"
          onClick={() => decide('refused')}
        >
          {t('admin.privacy.refuse')}
        </button>
      </div>
    </div>
  );
}

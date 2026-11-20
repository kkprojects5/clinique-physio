import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../auth/AuthContext';
import { useApiData } from '../../auth/useApiData';
import { formatDay } from '../../utils/format';
import { LoadError, Loading } from '../../components/Status';
import { Problem } from '../ForgotPassword';
import { apiError } from './Admin';

// Staff accounts (B-ADM-01). A new member receives an email link to choose their password
// and sets up their 6-digit code at the first login: the administrator never sees a password.
export default function StaffAdmin() {
  const { t, i18n } = useTranslation();
  const { api } = useAuth();
  const staff = useApiData('/admin/staff');
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState('');
  const [problem, setProblem] = useState('');

  if (staff.failed) return <LoadError onRetry={staff.reload} />;
  if (!staff.data) return <Loading />;

  async function setActive(member, active) {
    setMessage('');
    setProblem('');
    if (!active) {
      const question =
        member.future_appointments > 0
          ? t('admin.staff.confirmDeactivateWithAppointments', {
              email: member.email,
              count: member.future_appointments,
            })
          : t('admin.staff.confirmDeactivate', { email: member.email });
      if (!window.confirm(question)) return;
    }
    const { status, data } = await api(`/admin/staff/${member.id}`, {
      method: 'PATCH',
      body: { is_active: active },
    });
    if (status === 200) staff.reload();
    else setProblem(apiError(data, t('status.error')));
  }

  async function invite(member) {
    setMessage('');
    setProblem('');
    const { status, data } = await api(`/admin/staff/${member.id}/invitation`, { method: 'POST' });
    if (status === 204) setMessage(t('admin.staff.invitationSent', { email: member.email }));
    else setProblem(apiError(data, t('status.error')));
  }

  return (
    <>
      <p className="hint">{t('admin.staff.intro')}</p>
      {message && (
        <p className="notice" role="status">
          {message}
        </p>
      )}
      {problem && <Problem text={problem} />}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th scope="col">{t('admin.staff.person')}</th>
              <th scope="col">{t('admin.staff.role')}</th>
              <th scope="col">{t('admin.status')}</th>
              <th scope="col">{t('admin.staff.lastLogin')}</th>
              <th scope="col">{t('admin.staff.future')}</th>
              <th scope="col">
                <span className="visually-hidden">{t('admin.actions')}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {staff.data.map((m) => (
              <tr key={m.id} className={m.is_active ? '' : 'row--inactive'}>
                <td>
                  {m.first_name ? `${m.first_name} ${m.last_name}` : ''}
                  <div className="hint">{m.email}</div>
                </td>
                <td>{t(`admin.roles.${m.role}`)}</td>
                <td>
                  <span className={`badge${m.is_active ? '' : ' badge--muted'}`}>
                    {t(m.is_active ? 'admin.active' : 'admin.inactive')}
                  </span>
                  {m.is_active && !m.mfa_ready && (
                    <div className="hint">{t('admin.staff.notSetUp')}</div>
                  )}
                </td>
                <td>{m.last_login_at ? formatDay(m.last_login_at, i18n.language) : '—'}</td>
                <td>{m.therapist_id ? m.future_appointments : '—'}</td>
                <td className="actions">
                  {m.role !== 'admin' && (
                    <>
                      {m.is_active && !m.mfa_ready && (
                        <button
                          type="button"
                          className="button button--small"
                          onClick={() => invite(m)}
                        >
                          {t('admin.staff.resend')}
                        </button>
                      )}
                      <button
                        type="button"
                        className="button button--small button--ghost"
                        onClick={() => setActive(m, !m.is_active)}
                      >
                        {t(m.is_active ? 'admin.deactivate' : 'admin.activate')}
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {adding ? (
        <StaffForm
          onDone={(email) => {
            setAdding(false);
            setMessage(t('admin.staff.created', { email }));
            staff.reload();
          }}
          onCancel={() => setAdding(false)}
        />
      ) : (
        <button type="button" className="button" onClick={() => setAdding(true)}>
          {t('admin.staff.new')}
        </button>
      )}
    </>
  );
}

function StaffForm({ onDone, onCancel }) {
  const { t } = useTranslation();
  const { api } = useAuth();
  const [form, setForm] = useState({
    email: '',
    role: 'therapist',
    language: 'fr',
    first_name: '',
    last_name: '',
    licence_number: '',
  });
  const [problem, setProblem] = useState('');
  const set = (name, value) => setForm((f) => ({ ...f, [name]: value }));
  const therapist = form.role === 'therapist';

  async function save(event) {
    event.preventDefault();
    const body = { email: form.email.trim(), role: form.role, language: form.language };
    if (therapist) {
      body.therapist = {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        licence_number: form.licence_number.trim(),
      };
    }
    const { status, data } = await api('/admin/staff', { method: 'POST', body });
    if (status === 201) onDone(data.email);
    else setProblem(apiError(data, t('status.error')));
  }

  return (
    <form className="panel form" onSubmit={save}>
      <h2>{t('admin.staff.new')}</h2>
      <div className="field">
        <label htmlFor="staff-email">{t('account.email')}</label>
        <input
          id="staff-email"
          type="email"
          required
          value={form.email}
          onChange={(e) => set('email', e.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="staff-role">{t('admin.staff.role')}</label>
        <select id="staff-role" value={form.role} onChange={(e) => set('role', e.target.value)}>
          <option value="therapist">{t('admin.roles.therapist')}</option>
          <option value="front_desk">{t('admin.roles.front_desk')}</option>
        </select>
      </div>
      <div className="field">
        <label htmlFor="staff-language">{t('admin.staff.language')}</label>
        <select
          id="staff-language"
          value={form.language}
          onChange={(e) => set('language', e.target.value)}
        >
          <option value="fr">Français</option>
          <option value="en">English</option>
        </select>
      </div>
      {therapist &&
        ['first_name', 'last_name', 'licence_number'].map((name) => (
          <div className="field" key={name}>
            <label htmlFor={`staff-${name}`}>{t(`admin.staff.${name}`)}</label>
            <input
              id={`staff-${name}`}
              required
              value={form[name]}
              onChange={(e) => set(name, e.target.value)}
            />
          </div>
        ))}
      <p className="hint">{t('admin.staff.invitationHint')}</p>
      {problem && <Problem text={problem} />}
      <div className="actions">
        <button type="submit" className="button">
          {t('admin.staff.create')}
        </button>
        <button type="button" className="button button--ghost" onClick={onCancel}>
          {t('admin.cancel')}
        </button>
      </div>
    </form>
  );
}

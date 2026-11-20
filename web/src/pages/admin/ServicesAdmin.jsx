import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../auth/AuthContext';
import { useApiData } from '../../auth/useApiData';
import { formatPrice } from '../../utils/format';
import { LoadError, Loading } from '../../components/Status';
import { Problem } from '../ForgotPassword';
import { apiError, toCents } from './Admin';

const EMPTY = {
  name_fr: '',
  name_en: '',
  duration_min: 30,
  price: '',
  deposit: '',
  is_initial_evaluation: false,
  therapist_ids: [],
};

// Services and their prices (B-ADM-01). A service is never deleted: it is deactivated,
// so it disappears from booking while past appointments keep pointing to it.
export default function ServicesAdmin() {
  const { t, i18n } = useTranslation();
  const { api } = useAuth();
  const services = useApiData('/admin/services');
  const staff = useApiData('/admin/staff');
  const [editing, setEditing] = useState(null); // null, 'new' or a service id
  const [problem, setProblem] = useState('');

  if (services.failed || staff.failed) return <LoadError onRetry={services.reload} />;
  if (!services.data || !staff.data) return <Loading />;
  const therapists = staff.data.filter((s) => s.therapist_id && s.is_active);
  const lang = i18n.language;

  async function toggle(service) {
    setProblem('');
    const { status, data } = await api(`/admin/services/${service.id}`, {
      method: 'PATCH',
      body: { is_active: !service.is_active },
    });
    if (status === 200) services.reload();
    else setProblem(apiError(data, t('status.error')));
  }

  return (
    <>
      <p className="hint">{t('admin.services.intro')}</p>
      {problem && <Problem text={problem} />}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th scope="col">{t('admin.services.name')}</th>
              <th scope="col">{t('admin.services.duration')}</th>
              <th scope="col">{t('admin.services.price')}</th>
              <th scope="col">{t('admin.services.deposit')}</th>
              <th scope="col">{t('admin.services.therapists')}</th>
              <th scope="col">{t('admin.status')}</th>
              <th scope="col">
                <span className="visually-hidden">{t('admin.actions')}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {services.data.map((s) => (
              <tr key={s.id} className={s.is_active ? '' : 'row--inactive'}>
                <td>{lang === 'en' ? s.name_en : s.name_fr}</td>
                <td>{s.duration_min} min</td>
                <td>{formatPrice(s.price_cents, lang)}</td>
                <td>{formatPrice(s.deposit_cents, lang)}</td>
                <td>{s.therapist_ids.length}</td>
                <td>
                  <span className={`badge${s.is_active ? '' : ' badge--muted'}`}>
                    {t(s.is_active ? 'admin.active' : 'admin.inactive')}
                  </span>
                </td>
                <td className="actions">
                  <button
                    type="button"
                    className="button button--small"
                    onClick={() => setEditing(s.id)}
                  >
                    {t('admin.edit')}
                  </button>
                  <button
                    type="button"
                    className="button button--small button--ghost"
                    onClick={() => toggle(s)}
                  >
                    {t(s.is_active ? 'admin.deactivate' : 'admin.activate')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editing === null ? (
        <button type="button" className="button" onClick={() => setEditing('new')}>
          {t('admin.services.new')}
        </button>
      ) : (
        <ServiceForm
          key={editing}
          service={services.data.find((s) => s.id === editing)}
          therapists={therapists}
          onDone={() => {
            setEditing(null);
            services.reload();
          }}
          onCancel={() => setEditing(null)}
        />
      )}
    </>
  );
}

function ServiceForm({ service, therapists, onDone, onCancel }) {
  const { t } = useTranslation();
  const { api } = useAuth();
  const [form, setForm] = useState(() =>
    service
      ? {
          ...service,
          price: (service.price_cents / 100).toFixed(2),
          deposit: (service.deposit_cents / 100).toFixed(2),
        }
      : EMPTY,
  );
  const [problem, setProblem] = useState('');
  const set = (name, value) => setForm((f) => ({ ...f, [name]: value }));

  function toggleTherapist(id) {
    set(
      'therapist_ids',
      form.therapist_ids.includes(id)
        ? form.therapist_ids.filter((x) => x !== id)
        : [...form.therapist_ids, id],
    );
  }

  async function save(event) {
    event.preventDefault();
    const price_cents = toCents(form.price);
    const deposit_cents = toCents(form.deposit);
    if (Number.isNaN(price_cents) || Number.isNaN(deposit_cents)) {
      return setProblem(t('admin.services.badMoney'));
    }
    if (deposit_cents > price_cents) return setProblem(t('admin.services.depositTooHigh'));
    const body = {
      name_fr: form.name_fr.trim(),
      name_en: form.name_en.trim(),
      duration_min: Number(form.duration_min),
      price_cents,
      deposit_cents,
      is_initial_evaluation: form.is_initial_evaluation,
      therapist_ids: form.therapist_ids,
    };
    const { status, data } = service
      ? await api(`/admin/services/${service.id}`, { method: 'PATCH', body })
      : await api('/admin/services', { method: 'POST', body });
    if (status === 200 || status === 201) onDone();
    else setProblem(apiError(data, t('status.error')));
  }

  return (
    <form className="panel form" onSubmit={save}>
      <h2>{t(service ? 'admin.services.editTitle' : 'admin.services.new')}</h2>
      {['name_fr', 'name_en'].map((name) => (
        <div className="field" key={name}>
          <label htmlFor={name}>{t(`admin.services.${name}`)}</label>
          <input
            id={name}
            required
            minLength={2}
            maxLength={120}
            value={form[name]}
            onChange={(e) => set(name, e.target.value)}
          />
        </div>
      ))}
      <div className="field">
        <label htmlFor="duration">{t('admin.services.duration')}</label>
        <select
          id="duration"
          value={form.duration_min}
          onChange={(e) => set('duration_min', e.target.value)}
        >
          {[30, 45, 60].map((d) => (
            <option key={d} value={d}>
              {d} min
            </option>
          ))}
        </select>
      </div>
      {['price', 'deposit'].map((name) => (
        <div className="field" key={name}>
          <label htmlFor={name}>{t(`admin.services.${name}Dollars`)}</label>
          <input
            id={name}
            inputMode="decimal"
            required
            value={form[name]}
            onChange={(e) => set(name, e.target.value)}
          />
        </div>
      ))}
      <label className="check">
        <input
          type="checkbox"
          checked={form.is_initial_evaluation}
          onChange={(e) => set('is_initial_evaluation', e.target.checked)}
        />{' '}
        {t('admin.services.initial')}
      </label>
      <fieldset className="field">
        <legend>{t('admin.services.therapists')}</legend>
        {therapists.map((th) => (
          <label className="check" key={th.therapist_id}>
            <input
              type="checkbox"
              checked={form.therapist_ids.includes(th.therapist_id)}
              onChange={() => toggleTherapist(th.therapist_id)}
            />{' '}
            {th.first_name} {th.last_name}
          </label>
        ))}
      </fieldset>
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

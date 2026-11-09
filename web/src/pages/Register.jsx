import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiPost } from '../api/client';
import { clinicToday } from '../utils/format';
import { Problem } from './ForgotPassword';

const EMPTY = {
  first_name: '',
  last_name: '',
  date_of_birth: '',
  phone: '',
  email: '',
  password: '',
  emergency_contact: '',
  accept_privacy_policy: false,
  accept_electronic_comms: false,
};

// Patient registration (B-AUTH-01): only the information the clinic needs (data minimization).
export default function Register() {
  const { t, i18n } = useTranslation();
  const [form, setForm] = useState(EMPTY);
  const [state, setState] = useState('idle');
  const set = (key) => (e) =>
    setForm({ ...form, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  async function submit(event) {
    event.preventDefault();
    if (form.password.length < 12) return setState('tooShort');
    setState('sending');
    try {
      const body = { ...form, language: i18n.language === 'en' ? 'en' : 'fr' };
      if (!body.emergency_contact.trim()) delete body.emergency_contact;
      const { status } = await apiPost('/auth/register', body);
      setState({ 202: 'sent', 422: 'invalid', 429: 'tooMany' }[status] || 'error');
    } catch {
      setState('error');
    }
  }

  if (state === 'sent') {
    return (
      <section className="narrow">
        <h1>{t('register.title')}</h1>
        <p className="status status--ok" role="status">
          {t('register.sent')}
        </p>
      </section>
    );
  }

  const field = (key, type = 'text', extra = {}) => (
    <div className="field">
      <label htmlFor={key}>{t(`register.${key}`)}</label>
      <input id={key} type={type} value={form[key]} onChange={set(key)} {...extra} />
    </div>
  );

  return (
    <section className="narrow">
      <h1>{t('register.title')}</h1>
      <form className="panel form" onSubmit={submit}>
        <p className="hint">{t('register.intro')}</p>
        {field('first_name', 'text', {
          required: true,
          autoComplete: 'given-name',
          maxLength: 100,
        })}
        {field('last_name', 'text', {
          required: true,
          autoComplete: 'family-name',
          maxLength: 100,
        })}
        {field('date_of_birth', 'date', {
          required: true,
          max: clinicToday(),
          autoComplete: 'bday',
        })}
        {field('phone', 'tel', { required: true, autoComplete: 'tel', maxLength: 20 })}
        {field('email', 'email', { required: true, autoComplete: 'email' })}
        {field('password', 'password', {
          required: true,
          minLength: 12,
          maxLength: 128,
          autoComplete: 'new-password',
        })}
        <p className="hint">{t('account.reset.rules')}</p>
        {field('emergency_contact', 'text', { maxLength: 200 })}
        <div className="check">
          <input
            id="accept_privacy_policy"
            type="checkbox"
            required
            checked={form.accept_privacy_policy}
            onChange={set('accept_privacy_policy')}
          />
          <label htmlFor="accept_privacy_policy">{t('register.privacy')}</label>
        </div>
        <div className="check">
          <input
            id="accept_electronic_comms"
            type="checkbox"
            checked={form.accept_electronic_comms}
            onChange={set('accept_electronic_comms')}
          />
          <label htmlFor="accept_electronic_comms">{t('register.comms')}</label>
        </div>
        {state === 'tooShort' && <Problem text={t('account.reset.tooShort')} />}
        {state === 'invalid' && <Problem text={t('register.invalid')} />}
        {state === 'tooMany' && <Problem text={t('account.tooMany')} />}
        {state === 'error' && <Problem text={t('status.error')} />}
        <button type="submit" className="button" disabled={state === 'sending'}>
          {t('register.submit')}
        </button>
        <p className="hint">
          <Link to="/connexion">{t('register.haveAccount')}</Link>
        </p>
      </form>
    </section>
  );
}

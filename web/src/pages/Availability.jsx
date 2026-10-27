import { useId } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useServices, useSlots, useTherapists } from '../api/queries';
import {
  addDays,
  clinicToday,
  formatDay,
  formatTime,
  groupByDay,
  sortServices,
} from '../utils/format';
import { Loading, LoadError } from '../components/Status';

export default function Availability() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const ids = { service: useId(), therapist: useId(), week: useId() };

  // The choices live in the address (?service=...&week=...), so a search can be shared or bookmarked.
  const [params, setParams] = useSearchParams();
  const today = clinicToday();
  const serviceId = params.get('service') || '';
  const therapistId = params.get('therapist') || '';
  const week = params.get('week') || today;

  const services = useServices();
  const therapists = useTherapists();
  const slots = useSlots({ serviceId, therapistId, dateFrom: week, dateTo: addDays(week, 6) });

  const update = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key === 'service') next.delete('therapist'); // previous therapist may not offer this service
    setParams(next, { replace: true });
  };

  const service = services.data?.find((s) => s.id === serviceId);
  const offering = (therapists.data || []).filter((p) => service?.therapist_ids.includes(p.id));
  const nameOf = (id) => {
    const person = therapists.data?.find((p) => p.id === id);
    return person ? `${person.first_name} ${person.last_name}` : '';
  };

  return (
    <>
      <h1>{t('availability.title')}</h1>
      <form className="filters" onSubmit={(event) => event.preventDefault()}>
        <div className="field">
          <label htmlFor={ids.service}>{t('availability.service')}</label>
          <select
            id={ids.service}
            value={serviceId}
            onChange={(e) => update('service', e.target.value)}
          >
            <option value="">{t('availability.choose')}</option>
            {sortServices(services.data || [], lang).map((s) => (
              <option key={s.id} value={s.id}>
                {lang === 'fr' ? s.name_fr : s.name_en}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={ids.therapist}>{t('availability.therapist')}</label>
          <select
            id={ids.therapist}
            value={therapistId}
            onChange={(e) => update('therapist', e.target.value)}
            disabled={!service}
          >
            <option value="">{t('availability.anyTherapist')}</option>
            {offering.map((p) => (
              <option key={p.id} value={p.id}>
                {p.first_name} {p.last_name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={ids.week}>{t('availability.week')}</label>
          <input
            id={ids.week}
            type="date"
            value={week}
            min={today}
            max={addDays(today, 60)}
            onChange={(e) => update('week', e.target.value)}
          />
        </div>
      </form>

      <p className="hint">{t('availability.timezone')}</p>

      {(services.isError || slots.isError) && (
        <LoadError onRetry={() => (services.isError ? services.refetch() : slots.refetch())} />
      )}
      {serviceId && slots.isPending && <Loading />}
      {slots.data && (
        <section aria-live="polite">
          <p className="count">{t('availability.count', { count: slots.data.length })}</p>
          {slots.data.length === 0 && <p>{t('availability.noSlots')}</p>}
          {groupByDay(slots.data).map(([day, daySlots]) => (
            <div key={day} className="day">
              <h2 className="day__title">{formatDay(daySlots[0].start, lang)}</h2>
              <ul className="slots">
                {daySlots.map((slot) => (
                  <li key={`${slot.therapist_id}-${slot.start}`} className="slot">
                    <span className="slot__time">{formatTime(slot.start, lang)}</span>
                    {!therapistId && (
                      <span className="slot__who">
                        {t('availability.with', { name: nameOf(slot.therapist_id) })}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}
    </>
  );
}

import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useServices } from '../api/queries';
import { formatPrice, sortServices } from '../utils/format';
import { Loading, LoadError } from '../components/Status';

export default function Services() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { data, isPending, isError, refetch } = useServices();

  return (
    <>
      <h1>{t('services.title')}</h1>
      {isPending && <Loading />}
      {isError && <LoadError onRetry={refetch} />}
      {data && (
        <ul className="cards">
          {sortServices(data, lang).map((service) => (
            <li key={service.id} className="card">
              <h2 className="card__title">{lang === 'fr' ? service.name_fr : service.name_en}</h2>
              <p className="card__meta">
                {t('services.duration', { minutes: service.duration_min })}
              </p>
              {service.is_initial_evaluation && <p className="tag">{t('services.initial')}</p>}
              <dl className="facts">
                <div>
                  <dt>{t('services.price')}</dt>
                  <dd>{formatPrice(service.price_cents, lang)}</dd>
                </div>
                <div>
                  <dt>{t('services.deposit')}</dt>
                  <dd>{formatPrice(service.deposit_cents, lang)}</dd>
                </div>
              </dl>
              <Link to={`/disponibilites?service=${service.id}`} className="button button--small">
                {t('services.book')}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

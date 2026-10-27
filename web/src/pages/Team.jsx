import { useTranslation } from 'react-i18next';
import { useTherapists } from '../api/queries';
import { Loading, LoadError } from '../components/Status';

export default function Team() {
  const { t, i18n } = useTranslation();
  const { data, isPending, isError, refetch } = useTherapists();

  return (
    <>
      <h1>{t('team.title')}</h1>
      {isPending && <Loading />}
      {isError && <LoadError onRetry={refetch} />}
      {data && (
        <ul className="cards">
          {data.map((person) => (
            <li key={person.id} className="card">
              <h2 className="card__title">
                {person.first_name} {person.last_name}
              </h2>
              <p>{i18n.language === 'fr' ? person.bio_fr : person.bio_en}</p>
              <dl className="facts">
                <div>
                  <dt>{t('team.specialties')}</dt>
                  <dd>{person.specialties.join(', ')}</dd>
                </div>
                <div>
                  <dt>{t('team.languages')}</dt>
                  <dd>{person.languages.map((code) => t(`languageNames.${code}`)).join(', ')}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

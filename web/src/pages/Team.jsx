import { useTranslation } from 'react-i18next';
import { useTherapists } from '../api/queries';
import { API_URL } from '../api/client';
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
              <div className="person">
                <Portrait person={person} />
                <h2 className="card__title">
                  {person.first_name} {person.last_name}
                </h2>
              </div>
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

/** The therapist's photo (B-AVL-05), or their initials when there is none yet. */
export function Portrait({ person, small = false }) {
  const { t } = useTranslation();
  const size = small ? ' portrait--small' : '';
  if (person.photo_url) {
    return (
      <img
        className={`portrait${size}`}
        src={`${API_URL}${person.photo_url}`}
        alt={t('team.photoOf', { name: `${person.first_name} ${person.last_name}` })}
        width={small ? 48 : 96}
        height={small ? 48 : 96}
        loading="lazy"
      />
    );
  }
  const initials = `${person.first_name?.[0] ?? ''}${person.last_name?.[0] ?? ''}`;
  return (
    <span className={`portrait portrait--initials${size}`} aria-hidden="true">
      {initials}
    </span>
  );
}

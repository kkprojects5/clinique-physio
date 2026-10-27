import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function Home() {
  const { t } = useTranslation();
  return (
    <>
      <section className="hero">
        <h1>{t('home.title')}</h1>
        <p className="lead">{t('home.intro')}</p>
        <Link to="/disponibilites" className="button">
          {t('home.cta')}
        </Link>
      </section>
      <section className="panel">
        <h2>{t('home.hoursTitle')}</h2>
        <p>{t('home.hoursText')}</p>
      </section>
    </>
  );
}

import { NavLink, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const NAV = [
  { to: '/', key: 'home', end: true },
  { to: '/services', key: 'services' },
  { to: '/equipe', key: 'team' },
  { to: '/disponibilites', key: 'availability' },
];

export default function Layout() {
  const { t, i18n } = useTranslation();
  const other = i18n.language === 'fr' ? 'en' : 'fr';

  return (
    <>
      <a className="skip-link" href="#main">
        {t('skipToContent')}
      </a>
      <header className="site-header">
        <div className="site-header__inner">
          <NavLink to="/" className="brand">
            <span className="brand__mark" aria-hidden="true">
              P
            </span>
            Clinique Physio Mont-Royal
          </NavLink>
          <nav aria-label={t('nav.label')}>
            <ul className="nav">
              {NAV.map((item) => (
                <li key={item.to}>
                  <NavLink to={item.to} end={item.end} className="nav__link">
                    {t(`nav.${item.key}`)}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <button
            type="button"
            className="language-switch"
            onClick={() => i18n.changeLanguage(other)}
            aria-label={t('language.switchToLabel')}
            lang={other}
          >
            {t('language.switchTo')}
          </button>
        </div>
      </header>
      <main id="main" className="page" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="site-footer">
        <p>{t('footer.address')}</p>
        <p>{t('footer.fictional')}</p>
      </footer>
    </>
  );
}

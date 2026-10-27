import { useTranslation } from 'react-i18next';

export function Loading() {
  const { t } = useTranslation();
  return (
    <p className="status" role="status">
      {t('status.loading')}
    </p>
  );
}

export function LoadError({ onRetry }) {
  const { t } = useTranslation();
  return (
    <div className="status status--error" role="alert">
      <p>{t('status.error')}</p>
      <button type="button" className="button button--ghost" onClick={onRetry}>
        {t('status.retry')}
      </button>
    </div>
  );
}

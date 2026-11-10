import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useApiData } from '../../auth/useApiData';
import { formatDay } from '../../utils/format';
import { LoadError, Loading } from '../../components/Status';

// The patients I treat (care relationship, B-AUTH-05). Nobody else appears here.
export default function Patients() {
  const { t, i18n } = useTranslation();
  const me = useApiData('/therapist/me');
  const patients = useApiData('/therapist/patients');

  if (patients.failed) return <LoadError onRetry={patients.reload} />;
  if (!patients.data) return <Loading />;
  return (
    <section>
      <h1>{t('workspace.title')}</h1>
      {me.data && (
        <p className="hint">
          {t('workspace.hello', { name: `${me.data.first_name} ${me.data.last_name}` })}
        </p>
      )}
      <h2>{t('workspace.patients')}</h2>
      {patients.data.length === 0 ? (
        <p>{t('workspace.noPatients')}</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th scope="col">{t('workspace.name')}</th>
              <th scope="col">{t('register.date_of_birth')}</th>
              <th scope="col">{t('workspace.lastVisit')}</th>
            </tr>
          </thead>
          <tbody>
            {patients.data.map((p) => (
              <tr key={p.id}>
                <td>
                  <Link to={`/espace-therapeute/patients/${p.id}`}>
                    {p.last_name}, {p.first_name}
                  </Link>
                </td>
                <td>{p.date_of_birth}</td>
                <td>{p.last_visit ? formatDay(p.last_visit, i18n.language) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

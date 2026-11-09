import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { Loading } from '../components/Status';

/** Pages for logged-in users only: others go to the login page and come back afterwards. */
export default function RequireAuth({ children, needRole }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <Loading />;
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/connexion?next=${next}`} replace />;
  }
  if (needRole && user.role !== needRole) return <Navigate to="/" replace />;
  return children;
}

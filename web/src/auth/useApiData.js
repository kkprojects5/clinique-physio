import { useCallback, useEffect, useState } from 'react';
import { useAuth } from './AuthContext';

/** Load data as the logged-in user. Returns { data, failed, reload }. */
export function useApiData(path) {
  const { api } = useAuth();
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);

  const reload = useCallback(
    () =>
      api(path)
        .then(({ status, data: body }) => {
          if (status === 200) {
            setData(body);
            setFailed(false);
          } else setFailed(true);
        })
        .catch(() => setFailed(true)),
    [api, path],
  );

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, failed, reload };
}

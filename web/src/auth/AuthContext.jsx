// Who is logged in. The access token lives only in memory (never in localStorage, so a script
// injected into the page cannot steal a long-lived token). After a reload, the session comes
// back through the httpOnly refresh cookie, which JavaScript cannot read (ADR-002).
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { authRequest } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const token = useRef(null);

  const startSession = useCallback(async (accessToken) => {
    token.current = accessToken;
    const me = await authRequest('/me', { token: accessToken });
    if (me.status === 200) {
      setUser(me.data);
      return me.data;
    }
    token.current = null;
    setUser(null);
    return null;
  }, []);

  const refresh = useCallback(async () => {
    try {
      const { status, data } = await authRequest('/auth/refresh', { method: 'POST' });
      if (status === 200 && data?.access_token) return startSession(data.access_token);
    } catch {
      // offline or API asleep: stay logged out
    }
    token.current = null;
    setUser(null);
    return false;
  }, [startSession]);

  // After a reload: try to get the session back from the refresh cookie, once.
  useEffect(() => {
    let active = true;
    authRequest('/auth/refresh', { method: 'POST' })
      .then(({ status, data }) =>
        status === 200 && data?.access_token ? startSession(data.access_token) : false,
      )
      .catch(() => false)
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, [startSession]);

  /** Returns 'ok', 'mfa', 'mfa_setup', 'invalid', 'unverified', 'tooMany' or 'error'. */
  const login = useCallback(
    async (email, password) => {
      try {
        const { status, data } = await authRequest('/auth/login', {
          method: 'POST',
          body: { email, password },
        });
        if (status === 200 && data?.access_token) {
          const me = await startSession(data.access_token);
          return me ? { result: 'ok', role: me.role } : { result: 'error' };
        }
        if (status === 200 && data?.mfa_required) {
          return {
            result: data.mfa_setup_required ? 'mfa_setup' : 'mfa',
            mfaToken: data.mfa_token,
          };
        }
        const byStatus = { 401: 'invalid', 403: 'unverified', 429: 'tooMany' };
        return { result: byStatus[status] || 'error' };
      } catch {
        return { result: 'error' };
      }
    },
    [startSession],
  );

  const verifyCode = useCallback(
    async (mfaToken, code) => {
      try {
        const { status, data } = await authRequest('/auth/mfa/verify', {
          method: 'POST',
          body: { mfa_token: mfaToken, code },
        });
        if (status === 200 && data?.access_token) {
          const me = await startSession(data.access_token);
          return me ? { result: 'ok', role: me.role } : { result: 'error' };
        }
        return { result: { 401: 'invalidCode', 429: 'tooMany' }[status] || 'error' };
      } catch {
        return { result: 'error' };
      }
    },
    [startSession],
  );

  /** First staff login: get the authenticator secret to show as a QR code. */
  const setupCode = useCallback(async (mfaToken) => {
    try {
      const { status, data } = await authRequest('/auth/mfa/setup', {
        method: 'POST',
        body: { mfa_token: mfaToken },
      });
      return status === 200 ? data : null;
    } catch {
      return null;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await authRequest('/auth/logout', { method: 'POST' });
    } finally {
      token.current = null;
      setUser(null);
    }
  }, []);

  /** Call the API as the logged-in user; renews the access token once if it has expired. */
  const api = useCallback(
    async (path, options = {}) => {
      let answer = await authRequest(path, { ...options, token: token.current });
      if (answer.status === 401 && (await refresh())) {
        answer = await authRequest(path, { ...options, token: token.current });
      }
      return answer;
    },
    [refresh],
  );

  const value = useMemo(
    () => ({ user, ready, login, verifyCode, setupCode, logout, api }),
    [user, ready, login, verifyCode, setupCode, logout, api],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

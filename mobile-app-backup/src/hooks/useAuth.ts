import { useState, useCallback } from 'react';
import * as authApi from '../api/auth';
import { useAuthStore } from '../store/authStore';

export function useAuth() {
  const { user, isAuthenticated, isLoading, setUser, logout, loadPersistedAuth } =
    useAuthStore();
  const [loginLoading, setLoginLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = useCallback(
    async (loginName: string, password: string) => {
      setLoginLoading(true);
      setError(null);
      try {
        const response = await authApi.login(loginName, password);
        await setUser(response.user, response.access_token, response.refresh_token);
      } catch (err: unknown) {
        const message =
          (err as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail ?? 'Помилка входу. Перевірте дані.';
        setError(message);
        throw err;
      } finally {
        setLoginLoading(false);
      }
    },
    [setUser],
  );

  return {
    user,
    isAuthenticated,
    isLoading,
    loginLoading,
    error,
    login: handleLogin,
    logout,
    loadPersistedAuth,
  };
}

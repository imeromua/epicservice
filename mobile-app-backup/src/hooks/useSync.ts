import { useState, useCallback } from 'react';
import { useSQLiteContext } from 'expo-sqlite';
import { syncProducts, getLastSyncTime } from '../db/sync';
import { useConnectivity } from '../utils/connectivity';
import { useAuthStore } from '../store/authStore';

export function useSync() {
  const db = useSQLiteContext();
  const { isOnline } = useConnectivity();
  const user = useAuthStore((s) => s.user);
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadLastSync = useCallback(async () => {
    const time = await getLastSyncTime(db);
    setLastSync(time);
  }, [db]);

  const doSync = useCallback(async () => {
    if (!isOnline || !user) return;
    setSyncing(true);
    setError(null);
    try {
      await syncProducts(db, user.id);
      const time = await getLastSyncTime(db);
      setLastSync(time);
    } catch (err: unknown) {
      const message =
        (err as Error)?.message ?? 'Помилка синхронізації';
      setError(message);
    } finally {
      setSyncing(false);
    }
  }, [db, isOnline, user]);

  return {
    syncing,
    lastSync,
    error,
    doSync,
    loadLastSync,
  };
}

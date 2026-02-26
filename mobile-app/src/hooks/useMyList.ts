import { useState, useCallback, useEffect } from 'react';
import { useSQLiteContext } from 'expo-sqlite';
import {
  getLocalListWithProducts,
  addLocalListItem,
  updateLocalListItem,
  deleteLocalListItem,
  clearLocalList,
} from '../db/list';
import * as listApi from '../api/list';
import { useConnectivity } from '../utils/connectivity';
import { useAuthStore } from '../store/authStore';

export interface MyListItem {
  id: number;
  product_id: number;
  quantity: number;
  article: string;
  name: string;
  price: number;
  total: number;
  synced: boolean;
}

export function useMyList() {
  const db = useSQLiteContext();
  const { isOnline } = useConnectivity();
  const user = useAuthStore((s) => s.user);
  const [items, setItems] = useState<MyListItem[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      if (isOnline && user) {
        try {
          const response = await listApi.getList(user.id);
          setItems(
            response.items.map((item, idx) => ({
              id: idx,
              product_id: item.product_id,
              quantity: item.quantity,
              article: item.article,
              name: item.name,
              price: item.price,
              total: item.total,
              synced: true,
            })),
          );
          return;
        } catch {
          // Fall through to local
        }
      }

      const localItems = await getLocalListWithProducts(db);
      setItems(
        localItems.map((item) => ({
          id: item.id,
          product_id: item.product_id,
          quantity: item.quantity,
          article: item.article ?? '',
          name: item.name ?? '',
          price: item.price ?? 0,
          total: (item.price ?? 0) * item.quantity,
          synced: item.synced === 1,
        })),
      );
    } finally {
      setLoading(false);
    }
  }, [db, isOnline, user]);

  const addItem = useCallback(
    async (productId: number, quantity: number) => {
      await addLocalListItem(db, productId, quantity);
      if (isOnline && user) {
        try {
          await listApi.addToList(user.id, productId, quantity);
        } catch {
          // Queued locally
        }
      }
      await refresh();
    },
    [db, isOnline, user, refresh],
  );

  const updateItem = useCallback(
    async (productId: number, quantity: number) => {
      await updateLocalListItem(db, productId, quantity);
      if (isOnline && user) {
        try {
          await listApi.updateListItem(user.id, productId, quantity);
        } catch {
          // Queued locally
        }
      }
      await refresh();
    },
    [db, isOnline, user, refresh],
  );

  const removeItem = useCallback(
    async (productId: number) => {
      await deleteLocalListItem(db, productId);
      if (isOnline && user) {
        try {
          await listApi.deleteFromList(user.id, productId);
        } catch {
          // Queued locally
        }
      }
      await refresh();
    },
    [db, isOnline, user, refresh],
  );

  const clear = useCallback(async () => {
    await clearLocalList(db);
    if (isOnline && user) {
      try {
        await listApi.clearList(user.id);
      } catch {
        // Local clear already done
      }
    }
    await refresh();
  }, [db, isOnline, user, refresh]);

  const saveList = useCallback(async () => {
    if (!isOnline || !user) {
      throw new Error('Збереження доступне тільки онлайн');
    }
    return listApi.saveList(user.id);
  }, [isOnline, user]);

  const totalSum = items.reduce((sum, item) => sum + item.total, 0);
  const totalCount = items.reduce((sum, item) => sum + item.quantity, 0);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    items,
    loading,
    totalSum,
    totalCount,
    refresh,
    addItem,
    updateItem,
    removeItem,
    clear,
    saveList,
  };
}

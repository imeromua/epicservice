import { useState, useCallback, useRef } from 'react';
import { useSQLiteContext } from 'expo-sqlite';
import { searchLocalProducts } from '../db/products';
import { searchProducts as searchApi } from '../api/products';
import { useConnectivity } from '../utils/connectivity';
import { useAuthStore } from '../store/authStore';
import type { LocalProduct, SearchProduct } from '../types';

export interface ProductResult {
  id: number;
  article: string;
  name: string;
  department: number;
  group: string;
  available: string;
  price: number;
  reserved: number;
  months_without_movement: number;
  balance_sum: number;
}

function localToResult(p: LocalProduct): ProductResult {
  return {
    id: p.id,
    article: p.артикул,
    name: p.назва,
    department: p.відділ,
    group: p.група,
    available: p.кількість,
    price: p.ціна,
    reserved: p.відкладено,
    months_without_movement: p.місяці_без_руху,
    balance_sum: p.сума_залишку,
  };
}

function searchToResult(p: SearchProduct): ProductResult {
  return {
    id: p.id,
    article: p.article,
    name: p.name,
    department: p.department,
    group: p.group,
    available: String(p.available),
    price: p.price,
    reserved: p.reserved,
    months_without_movement: p.months_without_movement,
    balance_sum: p.balance_sum,
  };
}

export function useProducts() {
  const db = useSQLiteContext();
  const { isOnline } = useConnectivity();
  const user = useAuthStore((s) => s.user);
  const [products, setProducts] = useState<ProductResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback(
    async (
      query: string,
      department?: number,
      group?: string,
      onlyAvailable?: boolean,
    ) => {
      setLoading(true);
      try {
        // Always try local first
        const localResults = await searchLocalProducts(
          db,
          query,
          department,
          group,
          onlyAvailable,
        );

        if (localResults.length > 0) {
          setProducts(localResults.map(localToResult));
          setTotal(localResults.length);
        }

        // Then try API if online
        if (isOnline && user) {
          try {
            const apiResults = await searchApi({
              query,
              user_id: user.id,
              offset: 0,
              limit: 500,
            });
            setProducts(apiResults.products.map(searchToResult));
            setTotal(apiResults.total);
          } catch {
            // API failed, use local results which are already set
          }
        }
      } finally {
        setLoading(false);
      }
    },
    [db, isOnline, user],
  );

  const debouncedSearch = useCallback(
    (
      query: string,
      department?: number,
      group?: string,
      onlyAvailable?: boolean,
    ) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        search(query, department, group, onlyAvailable);
      }, 300);
    },
    [search],
  );

  return {
    products,
    loading,
    total,
    search,
    debouncedSearch,
  };
}

import type { SQLiteDatabase } from 'expo-sqlite';
import { searchProducts } from '../api/products';
import { upsertProducts } from './products';
import type { LocalProduct } from '../types';

export async function syncProducts(
  db: SQLiteDatabase,
  userId: number,
): Promise<{ synced: number }> {
  let offset = 0;
  const limit = 500;
  let totalSynced = 0;
  let hasMore = true;

  while (hasMore) {
    const response = await searchProducts({
      query: '',
      user_id: userId,
      offset,
      limit,
    });

    const localProducts: LocalProduct[] = response.products.map((p) => ({
      id: p.id,
      артикул: p.article,
      назва: p.name,
      відділ: p.department,
      група: p.group,
      кількість: String(p.available),
      відкладено: p.reserved,
      місяці_без_руху: p.months_without_movement,
      сума_залишку: p.balance_sum,
      ціна: p.price,
      активний: 1,
      synced_at: Math.floor(Date.now() / 1000),
    }));

    if (localProducts.length > 0) {
      await upsertProducts(db, localProducts);
      totalSynced += localProducts.length;
    }

    hasMore = response.has_more;
    offset += limit;
  }

  await db.runAsync(
    "INSERT OR REPLACE INTO sync_meta (key, value) VALUES ('last_sync', ?)",
    Date.now().toString(),
  );

  return { synced: totalSynced };
}

export async function getLastSyncTime(
  db: SQLiteDatabase,
): Promise<number | null> {
  const result = await db.getFirstAsync<{ value: string } | null>(
    "SELECT value FROM sync_meta WHERE key = 'last_sync'",
  );
  return result ? parseInt(result.value, 10) : null;
}

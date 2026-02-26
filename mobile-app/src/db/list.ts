import type { SQLiteDatabase } from 'expo-sqlite';
import type { LocalTempListItem } from '../types';

export async function getLocalList(
  db: SQLiteDatabase,
): Promise<LocalTempListItem[]> {
  return db.getAllAsync<LocalTempListItem>(
    'SELECT * FROM temp_list ORDER BY added_at DESC',
  );
}

export async function addLocalListItem(
  db: SQLiteDatabase,
  productId: number,
  quantity: number,
): Promise<void> {
  const existing = await db.getFirstAsync<LocalTempListItem>(
    'SELECT * FROM temp_list WHERE product_id = ?',
    productId,
  );

  if (existing) {
    await db.runAsync(
      'UPDATE temp_list SET quantity = ?, synced = 0 WHERE product_id = ?',
      quantity,
      productId,
    );
  } else {
    await db.runAsync(
      'INSERT INTO temp_list (product_id, quantity, synced) VALUES (?, ?, 0)',
      productId,
      quantity,
    );
  }
}

export async function updateLocalListItem(
  db: SQLiteDatabase,
  productId: number,
  quantity: number,
): Promise<void> {
  await db.runAsync(
    'UPDATE temp_list SET quantity = ?, synced = 0 WHERE product_id = ?',
    quantity,
    productId,
  );
}

export async function deleteLocalListItem(
  db: SQLiteDatabase,
  productId: number,
): Promise<void> {
  await db.runAsync('DELETE FROM temp_list WHERE product_id = ?', productId);
}

export async function clearLocalList(db: SQLiteDatabase): Promise<void> {
  await db.runAsync('DELETE FROM temp_list');
}

export async function getLocalListWithProducts(db: SQLiteDatabase) {
  return db.getAllAsync<{
    id: number;
    product_id: number;
    quantity: number;
    added_at: number;
    synced: number;
    article: string;
    name: string;
    price: number;
  }>(
    `SELECT tl.*, p.артикул AS article, p.назва AS name, p.ціна AS price
     FROM temp_list tl
     LEFT JOIN products p ON tl.product_id = p.id
     ORDER BY tl.added_at DESC`,
  );
}

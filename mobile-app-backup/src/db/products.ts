import type { SQLiteDatabase } from 'expo-sqlite';
import type { LocalProduct } from '../types';

export async function searchLocalProducts(
  db: SQLiteDatabase,
  query: string,
  department?: number,
  group?: string,
  onlyAvailable?: boolean,
  limit = 500,
  offset = 0,
): Promise<LocalProduct[]> {
  let sql = 'SELECT * FROM products WHERE активний = 1';
  const params: (string | number)[] = [];

  if (query) {
    sql += ' AND (артикул LIKE ? OR назва LIKE ?)';
    const q = `%${query}%`;
    params.push(q, q);
  }

  if (department != null) {
    sql += ' AND відділ = ?';
    params.push(department);
  }

  if (group) {
    sql += ' AND група = ?';
    params.push(group);
  }

  if (onlyAvailable) {
    sql += " AND CAST(кількість AS REAL) > 0";
  }

  sql += ' LIMIT ? OFFSET ?';
  params.push(limit, offset);

  return db.getAllAsync<LocalProduct>(sql, params);
}

export async function getLocalProduct(
  db: SQLiteDatabase,
  articleOrId: string | number,
): Promise<LocalProduct | null> {
  if (typeof articleOrId === 'number') {
    return db.getFirstAsync<LocalProduct>(
      'SELECT * FROM products WHERE id = ?',
      articleOrId,
    );
  }
  return db.getFirstAsync<LocalProduct>(
    'SELECT * FROM products WHERE артикул = ?',
    articleOrId,
  );
}

export async function upsertProducts(
  db: SQLiteDatabase,
  products: LocalProduct[],
): Promise<void> {
  const now = Math.floor(Date.now() / 1000);
  await db.withTransactionAsync(async () => {
    for (const p of products) {
      await db.runAsync(
        `INSERT OR REPLACE INTO products
          (id, артикул, назва, відділ, група, кількість, відкладено, місяці_без_руху, сума_залишку, ціна, активний, synced_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        p.id,
        p.артикул,
        p.назва,
        p.відділ,
        p.група,
        p.кількість,
        p.відкладено,
        p.місяці_без_руху,
        p.сума_залишку,
        p.ціна,
        p.активний,
        now,
      );
    }
  });
}

export async function getProductCount(db: SQLiteDatabase): Promise<number> {
  const result = await db.getFirstAsync<{ count: number }>(
    'SELECT COUNT(*) as count FROM products',
  );
  return result?.count ?? 0;
}

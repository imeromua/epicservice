import type { SQLiteDatabase } from 'expo-sqlite';

export const PRODUCTS_TABLE = `
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY,
  артикул TEXT UNIQUE NOT NULL,
  назва TEXT NOT NULL,
  відділ INTEGER,
  група TEXT,
  кількість TEXT,
  відкладено INTEGER DEFAULT 0,
  місяці_без_руху INTEGER DEFAULT 0,
  сума_залишку REAL DEFAULT 0,
  ціна REAL DEFAULT 0,
  активний INTEGER DEFAULT 1,
  synced_at INTEGER
);
`;

export const TEMP_LIST_TABLE = `
CREATE TABLE IF NOT EXISTS temp_list (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL,
  added_at INTEGER DEFAULT (strftime('%s','now')),
  synced INTEGER DEFAULT 0
);
`;

export const SYNC_META_TABLE = `
CREATE TABLE IF NOT EXISTS sync_meta (
  key TEXT PRIMARY KEY,
  value TEXT
);
`;

export async function createTables(db: SQLiteDatabase): Promise<void> {
  await db.execAsync(PRODUCTS_TABLE);
  await db.execAsync(TEMP_LIST_TABLE);
  await db.execAsync(SYNC_META_TABLE);
}

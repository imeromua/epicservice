import * as SQLite from 'expo-sqlite';

let db: SQLite.SQLiteDatabase | null = null;

export function getDatabase(): SQLite.SQLiteDatabase {
  if (!db) {
    db = SQLite.openDatabaseSync('epicservice.db');
    initDatabase(db);
  }
  return db;
}

function initDatabase(database: SQLite.SQLiteDatabase): void {
  database.execSync(`PRAGMA journal_mode = WAL;`);
  database.execSync(`PRAGMA foreign_keys = ON;`);

  database.execSync(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      login TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      first_name TEXT NOT NULL,
      role TEXT DEFAULT 'user',
      status TEXT DEFAULT 'active',
      created_at TEXT DEFAULT (datetime('now'))
    );
  `);

  database.execSync(`
    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      article TEXT,
      name TEXT,
      department TEXT,
      group_name TEXT,
      quantity TEXT,
      price REAL,
      active INTEGER DEFAULT 1
    );
  `);

  database.execSync(`
    CREATE TABLE IF NOT EXISTS temp_list (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      product_id INTEGER NOT NULL,
      quantity INTEGER DEFAULT 1,
      FOREIGN KEY (user_id) REFERENCES users(id),
      FOREIGN KEY (product_id) REFERENCES products(id)
    );
  `);

  database.execSync(`
    CREATE TABLE IF NOT EXISTS saved_lists (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (user_id) REFERENCES users(id)
    );
  `);

  database.execSync(`
    CREATE TABLE IF NOT EXISTS saved_list_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      list_id INTEGER NOT NULL,
      article TEXT,
      product_name TEXT,
      quantity INTEGER DEFAULT 1,
      FOREIGN KEY (list_id) REFERENCES saved_lists(id) ON DELETE CASCADE
    );
  `);

  // Create indexes for search performance
  database.execSync(`
    CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
  `);
  database.execSync(`
    CREATE INDEX IF NOT EXISTS idx_products_article ON products(article);
  `);
  database.execSync(`
    CREATE INDEX IF NOT EXISTS idx_products_department ON products(department);
  `);
  database.execSync(`
    CREATE INDEX IF NOT EXISTS idx_temp_list_user ON temp_list(user_id);
  `);
  database.execSync(`
    CREATE INDEX IF NOT EXISTS idx_saved_lists_user ON saved_lists(user_id);
  `);
}

export function closeDatabase(): void {
  if (db) {
    db.closeSync();
    db = null;
  }
}

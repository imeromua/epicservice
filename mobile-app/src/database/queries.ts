import { getDatabase } from './database';
import type { CSVProduct } from '../utils/csv';

export interface User {
  id: number;
  login: string;
  password_hash: string;
  first_name: string;
  role: string;
  status: string;
  created_at: string;
}

export interface Product {
  id: number;
  article: string;
  name: string;
  department: string;
  group_name: string;
  quantity: string;
  price: number;
  active: number;
}

export interface TempListItem {
  id: number;
  user_id: number;
  product_id: number;
  quantity: number;
  article: string;
  name: string;
  department: string;
  price: number;
}

export interface SavedList {
  id: number;
  user_id: number;
  name: string;
  created_at: string;
  item_count?: number;
}

export interface SavedListItem {
  id: number;
  list_id: number;
  article: string;
  product_name: string;
  quantity: number;
}

// Users
export function createUser(
  login: string,
  passwordHash: string,
  firstName: string,
  role: string = 'user'
): User {
  const db = getDatabase();
  const result = db.runSync(
    'INSERT INTO users (login, password_hash, first_name, role) VALUES (?, ?, ?, ?)',
    [login, passwordHash, firstName, role]
  );
  return db.getFirstSync<User>(
    'SELECT * FROM users WHERE id = ?',
    [result.lastInsertRowId]
  )!;
}

export function getUserByLogin(login: string): User | null {
  const db = getDatabase();
  return db.getFirstSync<User>(
    'SELECT * FROM users WHERE login = ?',
    [login]
  );
}

// Products
export function searchProducts(
  query: string,
  department?: string
): Product[] {
  const db = getDatabase();
  const searchTerm = `%${query}%`;

  if (department && department !== '') {
    return db.getAllSync<Product>(
      `SELECT * FROM products WHERE active = 1
       AND (LOWER(name) LIKE LOWER(?) OR LOWER(article) LIKE LOWER(?))
       AND department = ?
       ORDER BY name LIMIT 100`,
      [searchTerm, searchTerm, department]
    );
  }

  return db.getAllSync<Product>(
    `SELECT * FROM products WHERE active = 1
     AND (LOWER(name) LIKE LOWER(?) OR LOWER(article) LIKE LOWER(?))
     ORDER BY name LIMIT 100`,
    [searchTerm, searchTerm]
  );
}

export function getAllDepartments(): string[] {
  const db = getDatabase();
  const rows = db.getAllSync<{ department: string }>(
    'SELECT DISTINCT department FROM products WHERE active = 1 AND department IS NOT NULL AND department != "" ORDER BY department'
  );
  return rows.map((r) => r.department);
}

export function importProducts(products: CSVProduct[]): number {
  const db = getDatabase();
  let count = 0;

  db.execSync('BEGIN TRANSACTION');
  try {
    const stmt = db.prepareSync(
      'INSERT INTO products (article, name, department, group_name, quantity, price, active) VALUES (?, ?, ?, ?, ?, ?, 1)'
    );
    for (const p of products) {
      stmt.executeSync([
        p.article,
        p.name,
        p.department,
        p.group_name,
        p.quantity,
        p.price,
      ]);
      count++;
    }
    stmt.finalizeSync();
    db.execSync('COMMIT');
  } catch (error) {
    db.execSync('ROLLBACK');
    throw error;
  }

  return count;
}

export function getProductCount(): number {
  const db = getDatabase();
  const row = db.getFirstSync<{ count: number }>(
    'SELECT COUNT(*) as count FROM products WHERE active = 1'
  );
  return row?.count ?? 0;
}

// Temp list
export function addToList(
  userId: number,
  productId: number,
  quantity: number
): void {
  const db = getDatabase();
  const existing = db.getFirstSync<{ id: number; quantity: number }>(
    'SELECT id, quantity FROM temp_list WHERE user_id = ? AND product_id = ?',
    [userId, productId]
  );

  if (existing) {
    db.runSync(
      'UPDATE temp_list SET quantity = quantity + ? WHERE id = ?',
      [quantity, existing.id]
    );
  } else {
    db.runSync(
      'INSERT INTO temp_list (user_id, product_id, quantity) VALUES (?, ?, ?)',
      [userId, productId, quantity]
    );
  }
}

export function getListItems(userId: number): TempListItem[] {
  const db = getDatabase();
  return db.getAllSync<TempListItem>(
    `SELECT t.id, t.user_id, t.product_id, t.quantity,
            p.article, p.name, p.department, p.price
     FROM temp_list t
     JOIN products p ON t.product_id = p.id
     WHERE t.user_id = ?
     ORDER BY p.department, p.name`,
    [userId]
  );
}

export function updateListQuantity(
  userId: number,
  productId: number,
  quantity: number
): void {
  const db = getDatabase();
  if (quantity <= 0) {
    removeFromList(userId, productId);
    return;
  }
  db.runSync(
    'UPDATE temp_list SET quantity = ? WHERE user_id = ? AND product_id = ?',
    [quantity, userId, productId]
  );
}

export function removeFromList(userId: number, productId: number): void {
  const db = getDatabase();
  db.runSync(
    'DELETE FROM temp_list WHERE user_id = ? AND product_id = ?',
    [userId, productId]
  );
}

export function clearList(userId: number): void {
  const db = getDatabase();
  db.runSync('DELETE FROM temp_list WHERE user_id = ?', [userId]);
}

export function getListCount(userId: number): number {
  const db = getDatabase();
  const row = db.getFirstSync<{ count: number }>(
    'SELECT COUNT(*) as count FROM temp_list WHERE user_id = ?',
    [userId]
  );
  return row?.count ?? 0;
}

// Saved lists
export function saveList(userId: number, name: string): void {
  const db = getDatabase();
  const items = getListItems(userId);
  if (items.length === 0) return;

  db.execSync('BEGIN TRANSACTION');
  try {
    const result = db.runSync(
      'INSERT INTO saved_lists (user_id, name) VALUES (?, ?)',
      [userId, name]
    );
    const listId = result.lastInsertRowId;

    const stmt = db.prepareSync(
      'INSERT INTO saved_list_items (list_id, article, product_name, quantity) VALUES (?, ?, ?, ?)'
    );
    for (const item of items) {
      stmt.executeSync([listId, item.article, item.name, item.quantity]);
    }
    stmt.finalizeSync();

    db.runSync('DELETE FROM temp_list WHERE user_id = ?', [userId]);
    db.execSync('COMMIT');
  } catch (error) {
    db.execSync('ROLLBACK');
    throw error;
  }
}

export function getSavedLists(userId: number): SavedList[] {
  const db = getDatabase();
  return db.getAllSync<SavedList>(
    `SELECT sl.*, COUNT(sli.id) as item_count
     FROM saved_lists sl
     LEFT JOIN saved_list_items sli ON sl.id = sli.list_id
     WHERE sl.user_id = ?
     GROUP BY sl.id
     ORDER BY sl.created_at DESC`,
    [userId]
  );
}

export function getSavedListItems(listId: number): SavedListItem[] {
  const db = getDatabase();
  return db.getAllSync<SavedListItem>(
    'SELECT * FROM saved_list_items WHERE list_id = ? ORDER BY product_name',
    [listId]
  );
}

export function deleteSavedList(listId: number): void {
  const db = getDatabase();
  db.runSync('DELETE FROM saved_list_items WHERE list_id = ?', [listId]);
  db.runSync('DELETE FROM saved_lists WHERE id = ?', [listId]);
}

// Admin
export function clearAllProducts(): void {
  const db = getDatabase();
  db.execSync('DELETE FROM products');
}

export function clearAllData(): void {
  const db = getDatabase();
  db.execSync('DELETE FROM saved_list_items');
  db.execSync('DELETE FROM saved_lists');
  db.execSync('DELETE FROM temp_list');
  db.execSync('DELETE FROM products');
}

export function getUserCount(): number {
  const db = getDatabase();
  const row = db.getFirstSync<{ count: number }>(
    'SELECT COUNT(*) as count FROM users'
  );
  return row?.count ?? 0;
}

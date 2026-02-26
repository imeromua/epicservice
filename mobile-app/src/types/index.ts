export interface User {
  id: number;
  login: string;
  first_name: string;
  username?: string;
  role: 'user' | 'admin' | 'moderator';
  status: 'pending' | 'approved' | 'blocked';
}

export interface AuthResponse {
  success: boolean;
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface Product {
  id: number;
  артикул: string;
  назва: string;
  відділ: number;
  група: string;
  кількість: string;
  відкладено: number;
  місяці_без_руху: number;
  сума_залишку: number;
  ціна: number;
  активний: boolean;
}

export interface SearchProduct {
  id: number;
  article: string;
  name: string;
  price: number;
  available: string;
  department: number;
  group: string;
  months_without_movement: number;
  balance_sum: number;
  reserved: number;
  user_reserved: number;
  user_reserved_sum: number;
  is_different_department: boolean;
  current_list_department: number | null;
}

export interface ListItem {
  product_id: number;
  article: string;
  name: string;
  quantity: number;
  price: number;
  total: number;
}

export interface ListResponse {
  items: ListItem[];
  total: number;
  count: number;
}

export interface SearchRequest {
  query: string;
  user_id: number;
  offset?: number;
  limit?: number;
}

export interface SearchResponse {
  products: SearchProduct[];
  has_more: boolean;
  total: number;
  offset: number;
  limit: number;
}

export interface FilterRequest {
  user_id: number;
  departments?: number[];
  sort_by?: string;
  offset?: number;
  limit?: number;
}

export interface Department {
  department: number;
  count: number;
}

export interface ArchiveFile {
  name: string;
  size: number;
  created_at: string;
}

export interface ProductPhoto {
  id: number;
  file_path: string;
  order: number;
}

export interface PendingPhoto {
  id: number;
  article: string;
  product_name: string;
  file_path: string;
  file_size: number;
  original_size: number;
  uploaded_by: number;
  uploaded_at: string;
}

export interface AdminStats {
  total_users: number;
  active_users: number;
  total_products: number;
  reserved_sum: number;
}

export interface AdminUser {
  id: number;
  username: string;
  first_name: string;
  status: string;
  role: string;
  display_name: string;
}

export interface ImportResult {
  success: boolean;
  report: {
    added: number;
    updated: number;
    deactivated: number;
  };
}

export interface SyncMeta {
  key: string;
  value: string;
}

export interface LocalProduct {
  id: number;
  артикул: string;
  назва: string;
  відділ: number;
  група: string;
  кількість: string;
  відкладено: number;
  місяці_без_руху: number;
  сума_залишку: number;
  ціна: number;
  активний: number;
  synced_at: number | null;
}

export interface LocalTempListItem {
  id: number;
  product_id: number;
  quantity: number;
  added_at: number;
  synced: number;
}

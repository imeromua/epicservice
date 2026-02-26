import client from './client';
import type {
  SearchRequest,
  SearchResponse,
  FilterRequest,
  Department,
} from '../types';

export async function searchProducts(
  params: SearchRequest,
): Promise<SearchResponse> {
  const { data } = await client.post<SearchResponse>('/api/search', params);
  return data;
}

export async function filterProducts(params: FilterRequest) {
  const { data } = await client.post('/api/products/filter', params);
  return data;
}

export async function getDepartments(): Promise<Department[]> {
  const { data } = await client.get<{ departments: Department[] }>(
    '/api/products/departments',
  );
  return data.departments;
}

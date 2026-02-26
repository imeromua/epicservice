import client from './client';
import type { ListResponse } from '../types';

export async function getList(userId: number): Promise<ListResponse> {
  const { data } = await client.get<ListResponse>(`/api/list/${userId}`);
  return data;
}

export async function getListDepartment(userId: number) {
  const { data } = await client.get<{ department: number | null }>(
    `/api/list/department/${userId}`,
  );
  return data.department;
}

export async function addToList(
  userId: number,
  productId: number,
  quantity: number,
) {
  const { data } = await client.post('/api/add', {
    user_id: userId,
    product_id: productId,
    quantity,
  });
  return data;
}

export async function updateListItem(
  userId: number,
  productId: number,
  quantity: number,
) {
  const { data } = await client.post('/api/update', {
    user_id: userId,
    product_id: productId,
    quantity,
  });
  return data;
}

export async function deleteFromList(userId: number, productId: number) {
  const { data } = await client.post('/api/delete', {
    user_id: userId,
    product_id: productId,
  });
  return data;
}

export async function clearList(userId: number) {
  const { data } = await client.post(`/api/clear/${userId}`);
  return data;
}

export async function saveList(userId: number) {
  const { data } = await client.post(`/api/save/${userId}`);
  return data;
}

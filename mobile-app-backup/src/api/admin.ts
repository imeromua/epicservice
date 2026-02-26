import client from './client';
import type { AdminUser } from '../types';

export async function getAdminStatistics(userId: number) {
  const { data } = await client.get('/api/admin/statistics', {
    params: { user_id: userId },
  });
  return data;
}

export async function getActiveUsers(userId: number) {
  const { data } = await client.get('/api/admin/users/active', {
    params: { user_id: userId },
  });
  return data;
}

export async function getAllUsers(
  userId: number,
  params?: { status?: string; role?: string; q?: string; offset?: number; limit?: number },
) {
  const { data } = await client.get<{
    success: boolean;
    total: number;
    users: AdminUser[];
  }>('/api/admin/user-management/users', {
    params: { user_id: userId, ...params },
  });
  return data;
}

export async function approveUser(userId: number, targetUserId: number) {
  const { data } = await client.post('/api/admin/user-management/approve', {
    user_id: userId,
    target_user_id: targetUserId,
  });
  return data;
}

export async function blockUser(
  userId: number,
  targetUserId: number,
  reason: string,
) {
  const { data } = await client.post('/api/admin/user-management/block', {
    user_id: userId,
    target_user_id: targetUserId,
    reason,
  });
  return data;
}

export async function unblockUser(userId: number, targetUserId: number) {
  const { data } = await client.post('/api/admin/user-management/unblock', {
    user_id: userId,
    target_user_id: targetUserId,
  });
  return data;
}

export async function changeUserRole(
  userId: number,
  targetUserId: number,
  role: string,
) {
  const { data } = await client.post('/api/admin/user-management/role', {
    user_id: userId,
    target_user_id: targetUserId,
    role,
  });
  return data;
}

export async function importExcel(userId: number, fileUri: string) {
  const formData = new FormData();
  formData.append('file', {
    uri: fileUri,
    name: 'import.xlsx',
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  } as unknown as Blob);

  const { data } = await client.post('/api/admin/import', formData, {
    params: { user_id: userId, notify_users: false },
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function exportStock(userId: number) {
  const { data } = await client.get('/api/admin/export/stock', {
    params: { user_id: userId },
    responseType: 'blob',
  });
  return data;
}

export async function getAdminArchives(userId: number) {
  const { data } = await client.get('/api/admin/archives', {
    params: { user_id: userId },
  });
  return data;
}

export async function dangerClearDatabase(userId: number) {
  const { data } = await client.post('/api/admin/danger/clear-database', null, {
    params: { user_id: userId },
  });
  return data;
}

export async function dangerDeleteAllPhotos(userId: number) {
  const { data } = await client.post(
    '/api/admin/danger/delete-all-photos',
    null,
    { params: { user_id: userId } },
  );
  return data;
}

export async function dangerResetModeration(userId: number) {
  const { data } = await client.post(
    '/api/admin/danger/reset-moderation',
    null,
    { params: { user_id: userId } },
  );
  return data;
}

export async function dangerFullWipe(userId: number) {
  const { data } = await client.post('/api/admin/danger/full-wipe', null, {
    params: { user_id: userId },
  });
  return data;
}

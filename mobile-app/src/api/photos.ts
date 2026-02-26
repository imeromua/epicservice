import client from './client';
import type { ProductPhoto, PendingPhoto } from '../types';

export async function getProductPhotos(
  article: string,
): Promise<ProductPhoto[]> {
  const { data } = await client.get<{
    success: boolean;
    photos: ProductPhoto[];
  }>(`/api/photos/product/${article}`);
  return data.photos;
}

export async function uploadPhoto(
  article: string,
  userId: number,
  fileUri: string,
) {
  const formData = new FormData();
  formData.append('photo', {
    uri: fileUri,
    name: 'photo.jpg',
    type: 'image/jpeg',
  } as unknown as Blob);
  formData.append('article', article);
  formData.append('user_id', userId.toString());

  const { data } = await client.post('/api/photos/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function getPendingPhotos(
  userId: number,
): Promise<PendingPhoto[]> {
  const { data } = await client.get<{
    success: boolean;
    photos: PendingPhoto[];
  }>('/api/photos/moderation/pending', {
    params: { user_id: userId },
  });
  return data.photos;
}

export async function moderatePhoto(
  photoId: number,
  status: 'approved' | 'rejected',
  userId: number,
  reason?: string,
) {
  const formData = new FormData();
  formData.append('status', status);
  formData.append('user_id', userId.toString());
  if (reason) formData.append('reason', reason);

  const { data } = await client.post(
    `/api/photos/moderation/${photoId}`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return data;
}

import client from './client';
import type { ArchiveFile } from '../types';

export async function getArchives(userId: number): Promise<ArchiveFile[]> {
  const { data } = await client.get<{ files: ArchiveFile[] }>('/api/archives', {
    params: { user_id: userId },
  });
  return data.files;
}

export function getArchiveDownloadUrl(filename: string): string {
  return `/api/archives/download/${filename}`;
}

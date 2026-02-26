import client from './client';
import type { AuthResponse } from '../types';

export async function login(
  loginName: string,
  password: string,
): Promise<AuthResponse> {
  const { data } = await client.post<AuthResponse>('/api/auth/login', {
    login: loginName,
    password,
  });
  return data;
}

export async function getMe() {
  const { data } = await client.get<{ success: boolean; user: AuthResponse['user'] }>(
    '/api/auth/me',
  );
  return data.user;
}

export async function refreshToken(token: string) {
  const { data } = await client.post<{ success: boolean; access_token: string }>(
    '/api/auth/refresh',
    { refresh_token: token },
  );
  return data;
}

import * as Crypto from 'expo-crypto';
import * as SecureStore from 'expo-secure-store';
import { createUser, getUserByLogin, getUserCount } from '../database/queries';

export interface Session {
  userId: number;
  login: string;
  role: string;
  firstName: string;
}

const SESSION_KEY = 'epicservice_session';

export async function hashPassword(password: string): Promise<string> {
  return await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    password
  );
}

export async function verifyPassword(
  password: string,
  hash: string
): Promise<boolean> {
  const passwordHash = await hashPassword(password);
  return passwordHash === hash;
}

export async function saveSession(
  userId: number,
  login: string,
  role: string,
  firstName: string
): Promise<void> {
  const session: Session = { userId, login, role, firstName };
  await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(session));
}

export async function getSession(): Promise<Session | null> {
  try {
    const data = await SecureStore.getItemAsync(SESSION_KEY);
    if (data) {
      return JSON.parse(data) as Session;
    }
  } catch {
    // Session corrupted or unavailable
  }
  return null;
}

export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(SESSION_KEY);
}

export async function register(
  login: string,
  password: string,
  firstName: string
): Promise<Session> {
  const existing = getUserByLogin(login);
  if (existing) {
    throw new Error('USER_EXISTS');
  }

  const passwordHash = await hashPassword(password);
  // First user becomes admin
  const totalUsers = getUserCount();
  const role = totalUsers === 0 ? 'admin' : 'user';
  const user = createUser(login, passwordHash, firstName, role);

  const session: Session = {
    userId: user.id,
    login: user.login,
    role: user.role,
    firstName: user.first_name,
  };
  await saveSession(session.userId, session.login, session.role, session.firstName);
  return session;
}

export async function loginUser(
  login: string,
  password: string
): Promise<Session> {
  const user = getUserByLogin(login);
  if (!user) {
    throw new Error('INVALID_CREDENTIALS');
  }

  if (user.status !== 'active') {
    throw new Error('INVALID_CREDENTIALS');
  }

  const valid = await verifyPassword(password, user.password_hash);
  if (!valid) {
    throw new Error('INVALID_CREDENTIALS');
  }

  const session: Session = {
    userId: user.id,
    login: user.login,
    role: user.role,
    firstName: user.first_name,
  };
  await saveSession(session.userId, session.login, session.role, session.firstName);
  return session;
}

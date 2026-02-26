import * as LocalAuthentication from 'expo-local-authentication';
import * as SecureStore from 'expo-secure-store';
import { uk } from '../i18n/uk';
import type { Session } from './auth';

const BIOMETRIC_ENABLED_KEY = 'epicservice_biometric_enabled';
const BIOMETRIC_SESSION_KEY = 'epicservice_biometric_session';

export async function isBiometricAvailable(): Promise<boolean> {
  try {
    const hasHardware = await LocalAuthentication.hasHardwareAsync();
    if (!hasHardware) return false;
    const isEnrolled = await LocalAuthentication.isEnrolledAsync();
    return isEnrolled;
  } catch {
    return false;
  }
}

export async function authenticateWithBiometric(): Promise<boolean> {
  try {
    const result = await LocalAuthentication.authenticateAsync({
      promptMessage: uk.biometricPrompt,
      cancelLabel: uk.cancel,
      disableDeviceFallback: false,
    });
    return result.success;
  } catch {
    return false;
  }
}

export async function enableBiometric(session: Session): Promise<void> {
  await SecureStore.setItemAsync(BIOMETRIC_ENABLED_KEY, 'true');
  await SecureStore.setItemAsync(
    BIOMETRIC_SESSION_KEY,
    JSON.stringify(session)
  );
}

export async function disableBiometric(): Promise<void> {
  await SecureStore.deleteItemAsync(BIOMETRIC_ENABLED_KEY);
  await SecureStore.deleteItemAsync(BIOMETRIC_SESSION_KEY);
}

export async function isBiometricEnabled(): Promise<boolean> {
  try {
    const value = await SecureStore.getItemAsync(BIOMETRIC_ENABLED_KEY);
    return value === 'true';
  } catch {
    return false;
  }
}

export async function getBiometricSession(): Promise<Session | null> {
  try {
    const data = await SecureStore.getItemAsync(BIOMETRIC_SESSION_KEY);
    if (data) {
      return JSON.parse(data) as Session;
    }
  } catch {
    // Session unavailable
  }
  return null;
}

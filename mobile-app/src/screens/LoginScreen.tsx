import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { colors } from '../theme/colors';
import { uk } from '../i18n/uk';
import { loginUser, register, type Session, saveSession } from '../services/auth';
import {
  isBiometricAvailable,
  authenticateWithBiometric,
  isBiometricEnabled,
  getBiometricSession,
} from '../services/biometric';

interface LoginScreenProps {
  onLogin: (session: Session) => void;
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [isRegister, setIsRegister] = useState(false);
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [biometricAvailable, setBiometricAvailable] = useState(false);
  const [biometricEnabled, setBiometricEnabled] = useState(false);

  useEffect(() => {
    checkBiometric();
  }, []);

  async function checkBiometric() {
    const available = await isBiometricAvailable();
    setBiometricAvailable(available);
    if (available) {
      const enabled = await isBiometricEnabled();
      setBiometricEnabled(enabled);
    }
  }

  async function handleBiometricLogin() {
    try {
      setError('');
      setLoading(true);
      const success = await authenticateWithBiometric();
      if (success) {
        const session = await getBiometricSession();
        if (session) {
          await saveSession(session.userId, session.login, session.role, session.firstName);
          onLogin(session);
          return;
        }
        setError(uk.errorBiometricNotEnabled);
      } else {
        setError(uk.errorBiometricFailed);
      }
    } catch {
      setError(uk.errorBiometricFailed);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    setError('');

    if (!login.trim()) {
      setError(uk.errorLoginRequired);
      return;
    }
    if (login.trim().length < 3) {
      setError(uk.errorLoginTooShort);
      return;
    }
    if (!password) {
      setError(uk.errorPasswordRequired);
      return;
    }
    if (password.length < 4) {
      setError(uk.errorPasswordTooShort);
      return;
    }
    if (isRegister && !firstName.trim()) {
      setError(uk.errorFirstNameRequired);
      return;
    }

    setLoading(true);
    try {
      let session: Session;
      if (isRegister) {
        session = await register(login.trim(), password, firstName.trim());
      } else {
        session = await loginUser(login.trim(), password);
      }
      onLogin(session);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '';
      if (message === 'USER_EXISTS') {
        setError(uk.errorUserExists);
      } else if (message === 'INVALID_CREDENTIALS') {
        setError(uk.errorInvalidCredentials);
      } else {
        setError(uk.errorGeneral);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <StatusBar style="light" />
      <View style={styles.content}>
        <Text style={styles.appName}>{uk.appName}</Text>
        <Text style={styles.title}>
          {isRegister ? uk.registerTitle : uk.loginTitle}
        </Text>

        {isRegister && (
          <TextInput
            style={styles.input}
            placeholder={uk.firstNamePlaceholder}
            placeholderTextColor={colors.textMuted}
            value={firstName}
            onChangeText={setFirstName}
            autoCapitalize="words"
          />
        )}

        <TextInput
          style={styles.input}
          placeholder={uk.loginPlaceholder}
          placeholderTextColor={colors.textMuted}
          value={login}
          onChangeText={setLogin}
          autoCapitalize="none"
          autoCorrect={false}
        />

        <TextInput
          style={styles.input}
          placeholder={uk.passwordPlaceholder}
          placeholderTextColor={colors.textMuted}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleSubmit}
          disabled={loading}
          activeOpacity={0.7}
        >
          {loading ? (
            <ActivityIndicator color={colors.text} />
          ) : (
            <Text style={styles.buttonText}>
              {isRegister ? uk.registerButton : uk.loginButton}
            </Text>
          )}
        </TouchableOpacity>

        {biometricAvailable && biometricEnabled && !isRegister && (
          <TouchableOpacity
            style={styles.biometricButton}
            onPress={handleBiometricLogin}
            disabled={loading}
            activeOpacity={0.7}
          >
            <Text style={styles.biometricIcon}>🔐</Text>
            <Text style={styles.biometricText}>{uk.biometricLogin}</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={styles.switchButton}
          onPress={() => {
            setIsRegister(!isRegister);
            setError('');
          }}
          activeOpacity={0.7}
        >
          <Text style={styles.switchText}>
            {isRegister ? uk.switchToLogin : uk.switchToRegister}
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  appName: {
    color: colors.primary,
    fontSize: 32,
    fontWeight: '800',
    textAlign: 'center',
    marginBottom: 8,
  },
  title: {
    color: colors.textSecondary,
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 32,
  },
  input: {
    backgroundColor: colors.inputBg,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    marginBottom: 14,
  },
  error: {
    color: colors.danger,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 14,
  },
  button: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 16,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: colors.text,
    fontSize: 17,
    fontWeight: '700',
  },
  biometricButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface,
    borderRadius: 12,
    paddingVertical: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.border,
  },
  biometricIcon: {
    fontSize: 20,
    marginRight: 8,
  },
  biometricText: {
    color: colors.textSecondary,
    fontSize: 16,
    fontWeight: '500',
  },
  switchButton: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  switchText: {
    color: colors.primary,
    fontSize: 15,
  },
});

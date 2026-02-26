import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Text, ActivityIndicator } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { getDatabase } from './src/database/database';
import { getSession, clearSession, type Session } from './src/services/auth';
import { LoginScreen } from './src/screens/LoginScreen';
import { AppNavigator } from './src/navigation/AppNavigator';
import { colors } from './src/theme/colors';
import { uk } from './src/i18n/uk';

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [dbReady, setDbReady] = useState(false);

  useEffect(() => {
    initApp();
  }, []);

  async function initApp() {
    try {
      // Initialize database (synchronous, creates tables)
      getDatabase();
      setDbReady(true);

      // Check for existing session
      const existingSession = await getSession();
      if (existingSession) {
        setSession(existingSession);
      }
    } catch (error) {
      console.error('Failed to initialize app:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    await clearSession();
    setSession(null);
  }

  function handleLogin(newSession: Session) {
    setSession(newSession);
  }

  if (loading || !dbReady) {
    return (
      <View style={styles.loadingContainer}>
        <StatusBar style="light" />
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>{uk.loading}</Text>
      </View>
    );
  }

  if (!session) {
    return (
      <SafeAreaProvider>
        <LoginScreen onLogin={handleLogin} />
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <StatusBar style="light" />
        <AppNavigator session={session} onLogout={handleLogout} />
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    color: colors.textSecondary,
    fontSize: 16,
    marginTop: 12,
  },
});

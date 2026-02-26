import { useState } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { TextInput, Button, Text, Surface } from 'react-native-paper';
import { useAuth } from '../../src/hooks/useAuth';

export default function LoginScreen() {
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const { login: handleLogin, loginLoading, error } = useAuth();

  const onSubmit = async () => {
    if (!login.trim() || !password.trim()) return;
    try {
      await handleLogin(login.trim(), password);
    } catch {
      // Error is handled in hook
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.inner}>
        <Surface style={styles.card} elevation={2}>
          <Text variant="headlineMedium" style={styles.title}>
            EpicService
          </Text>
          <Text variant="bodyMedium" style={styles.subtitle}>
            Система управління складом
          </Text>

          <TextInput
            label="Логін"
            value={login}
            onChangeText={setLogin}
            autoCapitalize="none"
            autoCorrect={false}
            style={styles.input}
            mode="outlined"
          />

          <TextInput
            label="Пароль"
            value={password}
            onChangeText={setPassword}
            secureTextEntry={!showPassword}
            right={
              <TextInput.Icon
                icon={showPassword ? 'eye-off' : 'eye'}
                onPress={() => setShowPassword(!showPassword)}
              />
            }
            style={styles.input}
            mode="outlined"
          />

          {error && (
            <Text variant="bodySmall" style={styles.error}>
              {error}
            </Text>
          )}

          <Button
            mode="contained"
            onPress={onSubmit}
            loading={loginLoading}
            disabled={loginLoading || !login.trim() || !password.trim()}
            style={styles.button}
          >
            Увійти
          </Button>
        </Surface>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  inner: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  card: {
    padding: 24,
    borderRadius: 16,
    backgroundColor: '#ffffff',
  },
  title: {
    textAlign: 'center',
    fontWeight: 'bold',
    color: '#1976D2',
    marginBottom: 4,
  },
  subtitle: {
    textAlign: 'center',
    color: '#666',
    marginBottom: 24,
  },
  input: {
    marginBottom: 16,
  },
  error: {
    color: '#D32F2F',
    textAlign: 'center',
    marginBottom: 12,
  },
  button: {
    marginTop: 8,
    paddingVertical: 4,
  },
});

import { useState, useCallback } from 'react';
import { View, StyleSheet, Alert } from 'react-native';
import { Text, Button, Surface, ProgressBar } from 'react-native-paper';
import * as DocumentPicker from 'expo-document-picker';
import { useAdmin } from '../../../src/hooks/useAdmin';

export default function ImportScreen() {
  const { importExcel } = useAdmin();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    added: number;
    updated: number;
    deactivated: number;
  } | null>(null);

  const handlePick = useCallback(async () => {
    const picked = await DocumentPicker.getDocumentAsync({
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      copyToCacheDirectory: true,
    });

    if (picked.canceled || !picked.assets?.[0]) return;

    setLoading(true);
    setResult(null);
    try {
      const data = await importExcel(picked.assets[0].uri);
      if (data.success && data.report) {
        setResult(data.report);
      } else {
        Alert.alert('Помилка', 'Імпорт не вдався');
      }
    } catch {
      Alert.alert('Помилка', 'Не вдалося імпортувати файл');
    } finally {
      setLoading(false);
    }
  }, [importExcel]);

  return (
    <View style={styles.container}>
      <Text variant="headlineSmall" style={styles.title}>
        Імпорт Excel
      </Text>

      <Text variant="bodyMedium" style={styles.description}>
        Оберіть файл .xlsx для імпорту товарів. Існуючі товари буде оновлено,
        нові — додано.
      </Text>

      <Button
        mode="contained"
        icon="file-upload"
        onPress={handlePick}
        loading={loading}
        disabled={loading}
        style={styles.button}
      >
        Обрати файл
      </Button>

      {loading && <ProgressBar indeterminate style={styles.progress} />}

      {result && (
        <Surface style={styles.resultCard} elevation={2}>
          <Text variant="titleMedium" style={styles.resultTitle}>
            Результат імпорту
          </Text>
          <Text variant="bodyMedium">Додано: {result.added}</Text>
          <Text variant="bodyMedium">Оновлено: {result.updated}</Text>
          <Text variant="bodyMedium">
            Деактивовано: {result.deactivated}
          </Text>
        </Surface>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 16,
  },
  title: {
    fontWeight: 'bold',
    marginBottom: 8,
  },
  description: {
    color: '#666',
    marginBottom: 24,
  },
  button: {
    marginBottom: 16,
  },
  progress: {
    marginBottom: 16,
  },
  resultCard: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#ffffff',
  },
  resultTitle: {
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#2E7D32',
  },
});

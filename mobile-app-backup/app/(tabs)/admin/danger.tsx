import { useState, useCallback } from 'react';
import { View, StyleSheet, Alert } from 'react-native';
import { Text, Button, Surface, TextInput, Divider } from 'react-native-paper';
import { ScrollView } from 'react-native';
import { useAdmin } from '../../../src/hooks/useAdmin';

const CONFIRM_TEXT = 'ПІДТВЕРДЖУЮ';

interface DangerAction {
  title: string;
  description: string;
  action: () => Promise<unknown>;
}

export default function DangerScreen() {
  const {
    dangerClearDatabase,
    dangerDeleteAllPhotos,
    dangerResetModeration,
    dangerFullWipe,
  } = useAdmin();
  const [confirmText, setConfirmText] = useState('');
  const [loading, setLoading] = useState<string | null>(null);

  const actions: DangerAction[] = [
    {
      title: 'Очистити базу даних',
      description: 'Видалити всі товари з бази даних',
      action: dangerClearDatabase,
    },
    {
      title: 'Видалити всі фото',
      description: 'Видалити всі завантажені фото товарів',
      action: dangerDeleteAllPhotos,
    },
    {
      title: 'Скинути модерацію',
      description: 'Скинути статус модерації всіх фото',
      action: dangerResetModeration,
    },
    {
      title: 'Повне очищення',
      description: 'Видалити ВСЕ: товари, фото, списки, архіви',
      action: dangerFullWipe,
    },
  ];

  const handleAction = useCallback(
    async (action: DangerAction) => {
      if (confirmText !== CONFIRM_TEXT) {
        Alert.alert('Помилка', `Введіть "${CONFIRM_TEXT}" для підтвердження`);
        return;
      }

      Alert.alert(
        'Останнє підтвердження',
        `Ви впевнені? ${action.description}. Цю дію НЕ МОЖНА скасувати!`,
        [
          { text: 'Скасувати', style: 'cancel' },
          {
            text: 'Виконати',
            style: 'destructive',
            onPress: async () => {
              setLoading(action.title);
              try {
                await action.action();
                Alert.alert('Виконано', action.title);
                setConfirmText('');
              } catch {
                Alert.alert('Помилка', 'Операція не вдалася');
              } finally {
                setLoading(null);
              }
            },
          },
        ],
      );
    },
    [confirmText],
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Surface style={styles.warning} elevation={0}>
        <Text variant="headlineSmall" style={styles.warningTitle}>
          ⚠️ Небезпечна зона
        </Text>
        <Text variant="bodyMedium" style={styles.warningText}>
          Ці дії незворотні. Перед виконанням введіть слово підтвердження.
        </Text>
      </Surface>

      <TextInput
        label={`Введіть "${CONFIRM_TEXT}"`}
        value={confirmText}
        onChangeText={setConfirmText}
        mode="outlined"
        style={styles.confirmInput}
        outlineColor="#D32F2F"
        activeOutlineColor="#D32F2F"
      />

      {actions.map((action, idx) => (
        <View key={action.title}>
          {idx > 0 && <Divider />}
          <Surface style={styles.actionCard} elevation={1}>
            <View style={styles.actionInfo}>
              <Text variant="titleSmall" style={styles.actionTitle}>
                {action.title}
              </Text>
              <Text variant="bodySmall" style={styles.actionDesc}>
                {action.description}
              </Text>
            </View>
            <Button
              mode="contained"
              buttonColor="#D32F2F"
              onPress={() => handleAction(action)}
              loading={loading === action.title}
              disabled={
                loading !== null || confirmText !== CONFIRM_TEXT
              }
              compact
            >
              Виконати
            </Button>
          </Surface>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    padding: 16,
  },
  warning: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#FFEBEE',
    marginBottom: 16,
  },
  warningTitle: {
    color: '#D32F2F',
    fontWeight: 'bold',
    marginBottom: 4,
  },
  warningText: {
    color: '#C62828',
  },
  confirmInput: {
    marginBottom: 16,
  },
  actionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    marginVertical: 4,
    borderRadius: 8,
    backgroundColor: '#ffffff',
  },
  actionInfo: {
    flex: 1,
    marginRight: 12,
  },
  actionTitle: {
    fontWeight: 'bold',
  },
  actionDesc: {
    color: '#666',
    marginTop: 2,
  },
});

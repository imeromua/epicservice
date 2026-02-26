import { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, Surface, Button, ActivityIndicator } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useAdmin } from '../../../src/hooks/useAdmin';
import { formatPrice, formatNumber } from '../../../src/utils/formatters';

export default function AdminDashboard() {
  const router = useRouter();
  const { getStatistics } = useAdmin();
  const [stats, setStats] = useState<Record<string, number> | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStats = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getStatistics();
      setStats(data);
    } catch {
      // Stats unavailable
    } finally {
      setLoading(false);
    }
  }, [getStatistics]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text variant="headlineSmall" style={styles.title}>
        Панель адміністратора
      </Text>

      <View style={styles.cards}>
        <Surface style={styles.card} elevation={2}>
          <Text variant="labelMedium" style={styles.cardLabel}>
            Товарів
          </Text>
          <Text variant="headlineMedium" style={styles.cardValue}>
            {formatNumber(stats?.total_products ?? 0)}
          </Text>
        </Surface>

        <Surface style={styles.card} elevation={2}>
          <Text variant="labelMedium" style={styles.cardLabel}>
            Користувачів
          </Text>
          <Text variant="headlineMedium" style={styles.cardValue}>
            {formatNumber(stats?.total_users ?? 0)}
          </Text>
        </Surface>

        <Surface style={styles.card} elevation={2}>
          <Text variant="labelMedium" style={styles.cardLabel}>
            Активних
          </Text>
          <Text variant="headlineMedium" style={styles.cardValue}>
            {formatNumber(stats?.active_users ?? 0)}
          </Text>
        </Surface>

        <Surface style={styles.card} elevation={2}>
          <Text variant="labelMedium" style={styles.cardLabel}>
            Сума резерву
          </Text>
          <Text variant="titleMedium" style={styles.cardValue}>
            {formatPrice(stats?.reserved_sum ?? 0)}
          </Text>
        </Surface>
      </View>

      <Text variant="titleMedium" style={styles.sectionTitle}>
        Швидкі дії
      </Text>

      <Button
        mode="contained"
        icon="file-import"
        onPress={() => router.push('/(tabs)/admin/import')}
        style={styles.actionButton}
      >
        Імпорт Excel
      </Button>

      <Button
        mode="contained"
        icon="account-group"
        onPress={() => router.push('/(tabs)/admin/users')}
        style={styles.actionButton}
      >
        Користувачі
      </Button>

      <Button
        mode="contained"
        icon="image-multiple"
        onPress={() => router.push('/(tabs)/admin/moderation')}
        style={styles.actionButton}
      >
        Модерація фото
      </Button>

      <Button
        mode="outlined"
        icon="alert"
        onPress={() => router.push('/(tabs)/admin/danger')}
        style={styles.actionButton}
        textColor="#D32F2F"
      >
        Небезпечна зона
      </Button>
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
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontWeight: 'bold',
    marginBottom: 16,
  },
  cards: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 24,
  },
  card: {
    width: '47%',
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#ffffff',
  },
  cardLabel: {
    color: '#666',
    marginBottom: 4,
  },
  cardValue: {
    fontWeight: 'bold',
    color: '#1976D2',
  },
  sectionTitle: {
    fontWeight: 'bold',
    marginBottom: 12,
  },
  actionButton: {
    marginBottom: 12,
  },
});

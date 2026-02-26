import { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, Alert } from 'react-native';
import { Text, Surface, IconButton, ActivityIndicator, Banner } from 'react-native-paper';
import { FlashList } from '@shopify/flash-list';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { getArchives } from '../../src/api/archives';
import { useAuthStore } from '../../src/store/authStore';
import { useConnectivity } from '../../src/utils/connectivity';
import { formatDate } from '../../src/utils/formatters';
import client from '../../src/api/client';
import type { ArchiveFile } from '../../src/types';

export default function ArchivesScreen() {
  const user = useAuthStore((s) => s.user);
  const { isOnline } = useConnectivity();
  const [archives, setArchives] = useState<ArchiveFile[]>([]);
  const [loading, setLoading] = useState(true);

  const loadArchives = useCallback(async () => {
    if (!user || !isOnline) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const files = await getArchives(user.id);
      setArchives(files);
    } catch {
      Alert.alert('Помилка', 'Не вдалося завантажити архіви');
    } finally {
      setLoading(false);
    }
  }, [user, isOnline]);

  useEffect(() => {
    loadArchives();
  }, [loadArchives]);

  const handleDownload = useCallback(
    async (filename: string) => {
      if (!user) return;
      try {
        const baseURL = client.defaults.baseURL ?? '';
        const url = `${baseURL}/api/archives/download/${filename}`;
        const fileUri = `${FileSystem.documentDirectory}${filename}`;
        await FileSystem.downloadAsync(url, fileUri);
        await Sharing.shareAsync(fileUri);
      } catch {
        Alert.alert('Помилка', 'Не вдалося завантажити файл');
      }
    },
    [user],
  );

  const renderItem = useCallback(
    ({ item }: { item: ArchiveFile }) => (
      <Surface style={styles.row} elevation={1}>
        <View style={styles.rowInfo}>
          <Text variant="bodyMedium" numberOfLines={1}>
            {item.name}
          </Text>
          <Text variant="bodySmall" style={styles.date}>
            {formatDate(item.created_at)}
          </Text>
        </View>
        <IconButton
          icon="download"
          onPress={() => handleDownload(item.name)}
          disabled={!isOnline}
        />
        <IconButton
          icon="share-variant"
          onPress={() => handleDownload(item.name)}
          disabled={!isOnline}
        />
      </Surface>
    ),
    [handleDownload, isOnline],
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {!isOnline && (
        <Banner visible icon="wifi-off" actions={[]}>
          Офлайн — архіви недоступні
        </Banner>
      )}

      {archives.length === 0 ? (
        <View style={styles.center}>
          <Text variant="bodyLarge" style={styles.emptyText}>
            Немає збережених списків
          </Text>
        </View>
      ) : (
        <FlashList
          data={archives}
          renderItem={renderItem}
          estimatedItemSize={64}
          keyExtractor={(item) => item.name}
          refreshing={loading}
          onRefresh={loadArchives}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 12,
    marginVertical: 4,
    borderRadius: 8,
    backgroundColor: '#ffffff',
    paddingLeft: 12,
  },
  rowInfo: {
    flex: 1,
  },
  date: {
    color: '#888',
    marginTop: 2,
  },
  emptyText: {
    color: '#666',
  },
});

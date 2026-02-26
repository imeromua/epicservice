import { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, Image, Alert } from 'react-native';
import {
  Text,
  Surface,
  Button,
  TextInput,
  ActivityIndicator,
} from 'react-native-paper';
import { FlashList } from '@shopify/flash-list';
import { useAdmin } from '../../../src/hooks/useAdmin';
import client from '../../../src/api/client';
import type { PendingPhoto } from '../../../src/types';

export default function ModerationScreen() {
  const { getPendingPhotos, moderatePhoto } = useAdmin();
  const [photos, setPhotos] = useState<PendingPhoto[]>([]);
  const [loading, setLoading] = useState(true);
  const [reason, setReason] = useState('');
  const [actioningId, setActioningId] = useState<number | null>(null);

  const loadPhotos = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getPendingPhotos();
      setPhotos(data);
    } catch {
      Alert.alert('Помилка', 'Не вдалося завантажити фото');
    } finally {
      setLoading(false);
    }
  }, [getPendingPhotos]);

  useEffect(() => {
    loadPhotos();
  }, [loadPhotos]);

  const handleModerate = useCallback(
    async (photoId: number, status: 'approved' | 'rejected') => {
      setActioningId(photoId);
      try {
        await moderatePhoto(photoId, status, status === 'rejected' ? reason : undefined);
        setPhotos((prev) => prev.filter((p) => p.id !== photoId));
        setReason('');
      } catch {
        Alert.alert('Помилка', 'Не вдалося обробити фото');
      } finally {
        setActioningId(null);
      }
    },
    [moderatePhoto, reason],
  );

  const renderItem = useCallback(
    ({ item }: { item: PendingPhoto }) => {
      const baseURL = client.defaults.baseURL ?? '';
      return (
        <Surface style={styles.card} elevation={2}>
          <Image
            source={{ uri: `${baseURL}${item.file_path}` }}
            style={styles.image}
            resizeMode="cover"
          />
          <View style={styles.cardInfo}>
            <Text variant="titleSmall">{item.product_name}</Text>
            <Text variant="bodySmall" style={styles.article}>
              Артикул: {item.article}
            </Text>

            <TextInput
              label="Причина відхилення"
              value={reason}
              onChangeText={setReason}
              mode="outlined"
              dense
              style={styles.reasonInput}
            />

            <View style={styles.cardActions}>
              <Button
                mode="contained"
                onPress={() => handleModerate(item.id, 'approved')}
                loading={actioningId === item.id}
                disabled={actioningId !== null}
                style={styles.approveBtn}
                buttonColor="#4CAF50"
              >
                ✓
              </Button>
              <Button
                mode="contained"
                onPress={() => handleModerate(item.id, 'rejected')}
                loading={actioningId === item.id}
                disabled={actioningId !== null}
                style={styles.rejectBtn}
                buttonColor="#F44336"
              >
                ✕
              </Button>
            </View>
          </View>
        </Surface>
      );
    },
    [reason, actioningId, handleModerate],
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
      <Text variant="headlineSmall" style={styles.title}>
        Модерація фото ({photos.length})
      </Text>

      {photos.length === 0 ? (
        <View style={styles.center}>
          <Text variant="bodyLarge" style={styles.emptyText}>
            Немає фото на модерацію
          </Text>
        </View>
      ) : (
        <FlashList
          data={photos}
          renderItem={renderItem}
          estimatedItemSize={300}
          keyExtractor={(item) => String(item.id)}
          refreshing={loading}
          onRefresh={loadPhotos}
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
  title: {
    fontWeight: 'bold',
    padding: 16,
  },
  card: {
    marginHorizontal: 12,
    marginVertical: 6,
    borderRadius: 12,
    backgroundColor: '#ffffff',
    overflow: 'hidden',
  },
  image: {
    width: '100%',
    height: 200,
  },
  cardInfo: {
    padding: 12,
  },
  article: {
    color: '#666',
    marginTop: 2,
  },
  reasonInput: {
    marginTop: 8,
  },
  cardActions: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 8,
  },
  approveBtn: {
    flex: 1,
  },
  rejectBtn: {
    flex: 1,
  },
  emptyText: {
    color: '#666',
  },
});

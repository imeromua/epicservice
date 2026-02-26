import { useState, useCallback } from 'react';
import { View, StyleSheet, Alert } from 'react-native';
import { Text, Surface, Button, IconButton, TextInput, Portal, Modal } from 'react-native-paper';
import { FlashList } from '@shopify/flash-list';
import { useMyList, type MyListItem } from '../../src/hooks/useMyList';
import { useConnectivity } from '../../src/utils/connectivity';
import { formatPrice } from '../../src/utils/formatters';

export default function ListScreen() {
  const { items, loading, totalSum, totalCount, refresh, updateItem, removeItem, clear, saveList } =
    useMyList();
  const { isOnline } = useConnectivity();
  const [editingItem, setEditingItem] = useState<MyListItem | null>(null);
  const [editQuantity, setEditQuantity] = useState('');

  const handleDelete = useCallback(
    (item: MyListItem) => {
      Alert.alert('Видалити?', `${item.name}`, [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Видалити',
          style: 'destructive',
          onPress: () => removeItem(item.product_id),
        },
      ]);
    },
    [removeItem],
  );

  const handleClear = useCallback(() => {
    Alert.alert('Очистити список?', 'Всі товари буде видалено', [
      { text: 'Скасувати', style: 'cancel' },
      { text: 'Очистити', style: 'destructive', onPress: clear },
    ]);
  }, [clear]);

  const handleSave = useCallback(async () => {
    try {
      await saveList();
      Alert.alert('Збережено', 'Список збережено в архів');
    } catch {
      Alert.alert('Помилка', 'Не вдалося зберегти. Перевірте з\'єднання.');
    }
  }, [saveList]);

  const handleEditSave = useCallback(async () => {
    if (!editingItem) return;
    const qty = parseInt(editQuantity, 10);
    if (isNaN(qty) || qty <= 0) return;
    await updateItem(editingItem.product_id, qty);
    setEditingItem(null);
  }, [editingItem, editQuantity, updateItem]);

  const renderItem = useCallback(
    ({ item }: { item: MyListItem }) => (
      <Surface style={styles.row} elevation={1}>
        <View
          style={styles.rowContent}
          onTouchEnd={() => {
            setEditingItem(item);
            setEditQuantity(String(item.quantity));
          }}
        >
          <View style={styles.rowInfo}>
            <Text variant="labelMedium" style={styles.article}>
              {item.article}
            </Text>
            <Text variant="bodyMedium" numberOfLines={1}>
              {item.name}
            </Text>
          </View>
          <View style={styles.rowMeta}>
            <Text variant="bodySmall">
              {item.quantity} шт × {formatPrice(item.price)}
            </Text>
            <Text variant="labelMedium" style={styles.rowTotal}>
              {formatPrice(item.total)}
            </Text>
            {!item.synced && <Text style={styles.pendingIcon}>⏳</Text>}
          </View>
        </View>
        <IconButton
          icon="delete-outline"
          size={20}
          onPress={() => handleDelete(item)}
        />
      </Surface>
    ),
    [handleDelete],
  );

  return (
    <View style={styles.container}>
      {items.length === 0 && !loading ? (
        <View style={styles.empty}>
          <Text variant="bodyLarge" style={styles.emptyText}>
            Список порожній
          </Text>
          <Text variant="bodyMedium" style={styles.emptyHint}>
            Додайте товари з вкладки "Пошук"
          </Text>
        </View>
      ) : (
        <FlashList
          data={items}
          renderItem={renderItem}
          estimatedItemSize={72}
          keyExtractor={(item) => String(item.product_id)}
          refreshing={loading}
          onRefresh={refresh}
        />
      )}

      {items.length > 0 && (
        <Surface style={styles.bottomBar} elevation={4}>
          <View style={styles.summary}>
            <Text variant="bodyMedium">
              Позицій: {items.length} | Кількість: {totalCount}
            </Text>
            <Text variant="titleMedium" style={styles.totalPrice}>
              {formatPrice(totalSum)}
            </Text>
          </View>
          <View style={styles.actions}>
            <Button mode="outlined" onPress={handleClear} style={styles.actionBtn}>
              Очистити
            </Button>
            <Button
              mode="contained"
              onPress={handleSave}
              disabled={!isOnline}
              style={styles.actionBtn}
            >
              Зберегти
            </Button>
          </View>
        </Surface>
      )}

      <Portal>
        <Modal
          visible={editingItem !== null}
          onDismiss={() => setEditingItem(null)}
          contentContainerStyle={styles.modal}
        >
          {editingItem && (
            <Surface style={styles.modalContent} elevation={0}>
              <Text variant="titleMedium">{editingItem.name}</Text>
              <TextInput
                label="Кількість"
                value={editQuantity}
                onChangeText={setEditQuantity}
                keyboardType="numeric"
                mode="outlined"
                style={styles.editInput}
              />
              <Button mode="contained" onPress={handleEditSave}>
                Оновити
              </Button>
            </Surface>
          )}
        </Modal>
      </Portal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  empty: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    color: '#666',
  },
  emptyHint: {
    color: '#999',
    marginTop: 4,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 12,
    marginVertical: 4,
    borderRadius: 8,
    backgroundColor: '#ffffff',
  },
  rowContent: {
    flex: 1,
    flexDirection: 'row',
    padding: 12,
  },
  rowInfo: {
    flex: 1,
  },
  article: {
    color: '#1976D2',
    marginBottom: 2,
  },
  rowMeta: {
    alignItems: 'flex-end',
    marginLeft: 8,
  },
  rowTotal: {
    color: '#2E7D32',
    fontWeight: 'bold',
  },
  pendingIcon: {
    fontSize: 12,
    marginTop: 2,
  },
  bottomBar: {
    padding: 12,
    backgroundColor: '#ffffff',
  },
  summary: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  totalPrice: {
    color: '#2E7D32',
    fontWeight: 'bold',
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
  },
  actionBtn: {
    flex: 1,
  },
  modal: {
    margin: 20,
  },
  modalContent: {
    padding: 20,
    borderRadius: 16,
    backgroundColor: '#ffffff',
  },
  editInput: {
    marginVertical: 16,
  },
});

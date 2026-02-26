import { useState, useCallback, useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import {
  Searchbar,
  Text,
  Chip,
  Modal,
  Portal,
  Surface,
  Button,
  TextInput,
  Banner,
  IconButton,
} from 'react-native-paper';
import { FlashList } from '@shopify/flash-list';
import { useProducts, type ProductResult } from '../../src/hooks/useProducts';
import { useMyList } from '../../src/hooks/useMyList';
import { useSync } from '../../src/hooks/useSync';
import { useConnectivity } from '../../src/utils/connectivity';
import { formatPrice, formatRelativeTime, parseQuantity } from '../../src/utils/formatters';

export default function SearchScreen() {
  const [query, setQuery] = useState('');
  const [selectedDepartment, setSelectedDepartment] = useState<number | undefined>();
  const [onlyAvailable, setOnlyAvailable] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<ProductResult | null>(null);
  const [quantity, setQuantity] = useState('1');
  const { products, loading, debouncedSearch } = useProducts();
  const { addItem } = useMyList();
  const { syncing, lastSync, doSync, loadLastSync } = useSync();
  const { isOnline } = useConnectivity();

  useEffect(() => {
    loadLastSync();
  }, [loadLastSync]);

  useEffect(() => {
    debouncedSearch(query, selectedDepartment, undefined, onlyAvailable);
  }, [query, selectedDepartment, onlyAvailable, debouncedSearch]);

  const handleAddToList = useCallback(async () => {
    if (!selectedProduct) return;
    const qty = parseInt(quantity, 10);
    if (isNaN(qty) || qty <= 0) return;
    await addItem(selectedProduct.id, qty);
    setSelectedProduct(null);
    setQuantity('1');
  }, [selectedProduct, quantity, addItem]);

  const renderItem = useCallback(
    ({ item }: { item: ProductResult }) => (
      <Surface
        style={styles.productRow}
        elevation={1}
        onTouchEnd={() => {
          setSelectedProduct(item);
          setQuantity('1');
        }}
      >
        <View style={styles.productInfo}>
          <Text variant="labelLarge" style={styles.article}>
            {item.article}
          </Text>
          <Text variant="bodyMedium" numberOfLines={2}>
            {item.name}
          </Text>
        </View>
        <View style={styles.productMeta}>
          <Text variant="bodySmall" style={styles.quantity}>
            {parseQuantity(item.available) > 0
              ? item.available
              : '—'}
          </Text>
          <Text variant="labelMedium" style={styles.price}>
            {formatPrice(item.price)}
          </Text>
        </View>
      </Surface>
    ),
    [],
  );

  return (
    <View style={styles.container}>
      {!isOnline && (
        <Banner visible icon="wifi-off" actions={[]}>
          Офлайн режим — дані з локальної бази
        </Banner>
      )}

      <View style={styles.header}>
        <View style={styles.searchRow}>
          <Searchbar
            placeholder="Пошук товарів..."
            value={query}
            onChangeText={setQuery}
            style={styles.searchbar}
          />
          <IconButton
            icon="sync"
            loading={syncing}
            onPress={doSync}
            disabled={!isOnline || syncing}
          />
        </View>

        {lastSync && (
          <Text variant="labelSmall" style={styles.syncLabel}>
            Синхронізовано: {formatRelativeTime(lastSync)}
          </Text>
        )}

        <View style={styles.filters}>
          <Chip
            selected={onlyAvailable}
            onPress={() => setOnlyAvailable(!onlyAvailable)}
            style={styles.chip}
          >
            В наявності
          </Chip>
          {selectedDepartment != null && (
            <Chip
              onClose={() => setSelectedDepartment(undefined)}
              style={styles.chip}
            >
              Відділ {selectedDepartment}
            </Chip>
          )}
        </View>
      </View>

      <FlashList
        data={products}
        renderItem={renderItem}
        estimatedItemSize={80}
        keyExtractor={(item) => String(item.id)}
        refreshing={loading}
        onRefresh={() =>
          debouncedSearch(query, selectedDepartment, undefined, onlyAvailable)
        }
      />

      <Portal>
        <Modal
          visible={selectedProduct !== null}
          onDismiss={() => setSelectedProduct(null)}
          contentContainerStyle={styles.modal}
        >
          {selectedProduct && (
            <Surface style={styles.modalContent} elevation={0}>
              <Text variant="titleMedium" style={styles.modalTitle}>
                {selectedProduct.name}
              </Text>
              <Text variant="bodyMedium">
                Артикул: {selectedProduct.article}
              </Text>
              <Text variant="bodyMedium">
                Відділ: {selectedProduct.department}
              </Text>
              <Text variant="bodyMedium">
                Група: {selectedProduct.group}
              </Text>
              <Text variant="bodyMedium">
                В наявності: {selectedProduct.available}
              </Text>
              <Text variant="bodyMedium">
                Ціна: {formatPrice(selectedProduct.price)}
              </Text>
              <Text variant="bodyMedium">
                Сума залишку: {formatPrice(selectedProduct.balance_sum)}
              </Text>

              <TextInput
                label="Кількість"
                value={quantity}
                onChangeText={setQuantity}
                keyboardType="numeric"
                mode="outlined"
                style={styles.quantityInput}
              />

              <Button
                mode="contained"
                onPress={handleAddToList}
                style={styles.addButton}
              >
                Додати до списку
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
  header: {
    padding: 12,
    backgroundColor: '#ffffff',
  },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  searchbar: {
    flex: 1,
  },
  syncLabel: {
    color: '#888',
    marginTop: 4,
    marginLeft: 4,
  },
  filters: {
    flexDirection: 'row',
    marginTop: 8,
    gap: 8,
  },
  chip: {
    marginRight: 4,
  },
  productRow: {
    flexDirection: 'row',
    padding: 12,
    marginHorizontal: 12,
    marginVertical: 4,
    borderRadius: 8,
    backgroundColor: '#ffffff',
  },
  productInfo: {
    flex: 1,
  },
  article: {
    color: '#1976D2',
    marginBottom: 2,
  },
  productMeta: {
    alignItems: 'flex-end',
    justifyContent: 'center',
    marginLeft: 12,
  },
  quantity: {
    color: '#666',
  },
  price: {
    color: '#2E7D32',
    fontWeight: 'bold',
  },
  modal: {
    margin: 20,
  },
  modalContent: {
    padding: 20,
    borderRadius: 16,
    backgroundColor: '#ffffff',
  },
  modalTitle: {
    fontWeight: 'bold',
    marginBottom: 12,
  },
  quantityInput: {
    marginTop: 16,
    marginBottom: 12,
  },
  addButton: {
    marginTop: 4,
  },
});

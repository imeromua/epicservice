import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Modal,
  Alert,
} from 'react-native';
import { colors } from '../theme/colors';
import { uk } from '../i18n/uk';
import { searchProducts, getAllDepartments, addToList } from '../database/queries';
import type { Product } from '../database/queries';
import { ProductCard } from '../components/ProductCard';

interface SearchScreenProps {
  userId: number;
}

export function SearchScreen({ userId }: SearchScreenProps) {
  const [query, setQuery] = useState('');
  const [department, setDepartment] = useState('');
  const [departments, setDepartments] = useState<string[]>([]);
  const [results, setResults] = useState<Product[]>([]);
  const [showDeptPicker, setShowDeptPicker] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [addQuantity, setAddQuantity] = useState('1');
  const [hasSearched, setHasSearched] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    loadDepartments();
  }, []);

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    if (query.trim().length > 0) {
      debounceRef.current = setTimeout(() => {
        doSearch();
      }, 300);
    } else {
      setResults([]);
      setHasSearched(false);
    }
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, department]);

  function loadDepartments() {
    try {
      const deps = getAllDepartments();
      setDepartments(deps);
    } catch {
      // Departments may not be loaded yet
    }
  }

  function doSearch() {
    try {
      const found = searchProducts(query.trim(), department || undefined);
      setResults(found);
      setHasSearched(true);
    } catch {
      setResults([]);
    }
  }

  function handleAdd(product: Product) {
    setSelectedProduct(product);
    setAddQuantity('1');
  }

  function confirmAdd() {
    if (!selectedProduct) return;
    const qty = parseInt(addQuantity, 10) || 1;
    try {
      addToList(userId, selectedProduct.id, qty);
      Alert.alert(uk.success, uk.productAdded);
    } catch {
      Alert.alert(uk.error, uk.errorGeneral);
    }
    setSelectedProduct(null);
  }

  function renderItem({ item }: { item: Product }) {
    return <ProductCard product={item} onAdd={handleAdd} />;
  }

  return (
    <View style={styles.container}>
      <View style={styles.searchBar}>
        <TextInput
          style={styles.searchInput}
          placeholder={uk.searchPlaceholder}
          placeholderTextColor={colors.textMuted}
          value={query}
          onChangeText={setQuery}
          autoCapitalize="none"
          autoCorrect={false}
        />
        <TouchableOpacity
          style={styles.deptButton}
          onPress={() => setShowDeptPicker(true)}
          activeOpacity={0.7}
        >
          <Text style={styles.deptButtonText} numberOfLines={1}>
            {department || uk.allDepartments}
          </Text>
          <Text style={styles.deptArrow}>▼</Text>
        </TouchableOpacity>
      </View>

      {!hasSearched && results.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>🔍</Text>
          <Text style={styles.emptyText}>{uk.searchEmpty}</Text>
        </View>
      ) : hasSearched && results.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>😕</Text>
          <Text style={styles.emptyText}>{uk.searchNoResults}</Text>
        </View>
      ) : (
        <FlatList
          data={results}
          renderItem={renderItem}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        />
      )}

      {/* Department picker modal */}
      <Modal
        visible={showDeptPicker}
        transparent
        animationType="slide"
        onRequestClose={() => setShowDeptPicker(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setShowDeptPicker(false)}
        >
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>{uk.department}</Text>
            <TouchableOpacity
              style={[
                styles.deptOption,
                !department && styles.deptOptionSelected,
              ]}
              onPress={() => {
                setDepartment('');
                setShowDeptPicker(false);
              }}
            >
              <Text style={styles.deptOptionText}>{uk.allDepartments}</Text>
            </TouchableOpacity>
            <FlatList
              data={departments}
              keyExtractor={(item) => item}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.deptOption,
                    department === item && styles.deptOptionSelected,
                  ]}
                  onPress={() => {
                    setDepartment(item);
                    setShowDeptPicker(false);
                  }}
                >
                  <Text style={styles.deptOptionText}>{item}</Text>
                </TouchableOpacity>
              )}
            />
          </View>
        </TouchableOpacity>
      </Modal>

      {/* Add quantity modal */}
      <Modal
        visible={!!selectedProduct}
        transparent
        animationType="fade"
        onRequestClose={() => setSelectedProduct(null)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setSelectedProduct(null)}
        >
          <View style={styles.quantityModal}>
            <Text style={styles.modalTitle}>{uk.addToList}</Text>
            {selectedProduct && (
              <Text style={styles.selectedProductName} numberOfLines={2}>
                {selectedProduct.name}
              </Text>
            )}
            <Text style={styles.quantityLabel}>{uk.enterQuantity}</Text>
            <TextInput
              style={styles.quantityInput}
              keyboardType="numeric"
              value={addQuantity}
              onChangeText={setAddQuantity}
              selectTextOnFocus
            />
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => setSelectedProduct(null)}
                activeOpacity={0.7}
              >
                <Text style={styles.cancelButtonText}>{uk.cancel}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.confirmButton}
                onPress={confirmAdd}
                activeOpacity={0.7}
              >
                <Text style={styles.confirmButtonText}>{uk.addButton}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  searchBar: {
    padding: 12,
    gap: 8,
  },
  searchInput: {
    backgroundColor: colors.inputBg,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
  },
  deptButton: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  deptButtonText: {
    color: colors.textSecondary,
    fontSize: 14,
    flex: 1,
  },
  deptArrow: {
    color: colors.textMuted,
    fontSize: 10,
    marginLeft: 8,
  },
  list: {
    paddingHorizontal: 12,
    paddingBottom: 20,
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: 16,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingTop: 20,
    paddingBottom: 40,
    paddingHorizontal: 16,
    maxHeight: '60%',
  },
  modalTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 16,
  },
  deptOption: {
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderRadius: 10,
    marginBottom: 4,
  },
  deptOptionSelected: {
    backgroundColor: colors.primaryDark,
  },
  deptOptionText: {
    color: colors.text,
    fontSize: 16,
  },
  quantityModal: {
    backgroundColor: colors.surface,
    marginHorizontal: 32,
    marginTop: 'auto',
    marginBottom: 'auto',
    borderRadius: 20,
    padding: 24,
  },
  selectedProductName: {
    color: colors.textSecondary,
    fontSize: 15,
    textAlign: 'center',
    marginBottom: 16,
  },
  quantityLabel: {
    color: colors.textMuted,
    fontSize: 14,
    marginBottom: 8,
  },
  quantityInput: {
    backgroundColor: colors.inputBg,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 20,
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: colors.surfaceLight,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: colors.textSecondary,
    fontSize: 16,
    fontWeight: '600',
  },
  confirmButton: {
    flex: 1,
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  confirmButtonText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
  },
});

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Modal,
  TextInput,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { colors } from '../theme/colors';
import { uk } from '../i18n/uk';
import {
  getListItems,
  updateListQuantity,
  removeFromList,
  clearList,
  saveList,
  getListCount,
} from '../database/queries';
import type { TempListItem } from '../database/queries';
import { ListItem } from '../components/ListItem';

interface ListScreenProps {
  userId: number;
  onListCountChange?: (count: number) => void;
}

export function ListScreen({ userId, onListCountChange }: ListScreenProps) {
  const [items, setItems] = useState<TempListItem[]>([]);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [listName, setListName] = useState('');

  useFocusEffect(
    useCallback(() => {
      loadItems();
    }, [userId])
  );

  function loadItems() {
    try {
      const data = getListItems(userId);
      setItems(data);
      const count = getListCount(userId);
      onListCountChange?.(count);
    } catch {
      // Handle silently
    }
  }

  function handleIncrement(item: TempListItem) {
    try {
      updateListQuantity(userId, item.product_id, item.quantity + 1);
      loadItems();
    } catch {
      Alert.alert(uk.error, uk.errorGeneral);
    }
  }

  function handleDecrement(item: TempListItem) {
    if (item.quantity <= 1) {
      handleDelete(item);
      return;
    }
    try {
      updateListQuantity(userId, item.product_id, item.quantity - 1);
      loadItems();
    } catch {
      Alert.alert(uk.error, uk.errorGeneral);
    }
  }

  function handleDelete(item: TempListItem) {
    Alert.alert(uk.deleteItem, uk.deleteItemConfirm, [
      { text: uk.cancel, style: 'cancel' },
      {
        text: uk.delete,
        style: 'destructive',
        onPress: () => {
          try {
            removeFromList(userId, item.product_id);
            loadItems();
          } catch {
            Alert.alert(uk.error, uk.errorGeneral);
          }
        },
      },
    ]);
  }

  function handleClear() {
    Alert.alert(uk.clearList, uk.clearListConfirm, [
      { text: uk.cancel, style: 'cancel' },
      {
        text: uk.yes,
        style: 'destructive',
        onPress: () => {
          try {
            clearList(userId);
            loadItems();
            Alert.alert(uk.success, uk.listCleared);
          } catch {
            Alert.alert(uk.error, uk.errorGeneral);
          }
        },
      },
    ]);
  }

  function handleSave() {
    if (!listName.trim()) return;
    try {
      saveList(userId, listName.trim());
      setShowSaveModal(false);
      setListName('');
      loadItems();
      Alert.alert(uk.success, uk.listSaved);
    } catch {
      Alert.alert(uk.error, uk.errorGeneral);
    }
  }

  function renderItem({ item }: { item: TempListItem }) {
    return (
      <ListItem
        name={item.name}
        article={item.article}
        quantity={item.quantity}
        department={item.department}
        price={item.price}
        onIncrement={() => handleIncrement(item)}
        onDecrement={() => handleDecrement(item)}
        onDelete={() => handleDelete(item)}
      />
    );
  }

  if (items.length === 0) {
    return (
      <View style={styles.container}>
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>📋</Text>
          <Text style={styles.emptyText}>{uk.listEmpty}</Text>
          <Text style={styles.emptyHint}>{uk.listEmptyHint}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.totalText}>
          {uk.totalItems}: {items.length}
        </Text>
      </View>

      <FlatList
        data={items}
        renderItem={renderItem}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
      />

      <View style={styles.actions}>
        <TouchableOpacity
          style={styles.saveButton}
          onPress={() => {
            setListName('');
            setShowSaveModal(true);
          }}
          activeOpacity={0.7}
        >
          <Text style={styles.saveButtonText}>{uk.saveList}</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.clearButton}
          onPress={handleClear}
          activeOpacity={0.7}
        >
          <Text style={styles.clearButtonText}>{uk.clearList}</Text>
        </TouchableOpacity>
      </View>

      {/* Save list modal */}
      <Modal
        visible={showSaveModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowSaveModal(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setShowSaveModal(false)}
        >
          <View style={styles.saveModal}>
            <Text style={styles.modalTitle}>{uk.saveListTitle}</Text>
            <TextInput
              style={styles.nameInput}
              placeholder={uk.saveListNamePlaceholder}
              placeholderTextColor={colors.textMuted}
              value={listName}
              onChangeText={setListName}
              autoFocus
            />
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setShowSaveModal(false)}
                activeOpacity={0.7}
              >
                <Text style={styles.cancelBtnText}>{uk.cancel}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.saveBtnModal,
                  !listName.trim() && styles.disabledBtn,
                ]}
                onPress={handleSave}
                disabled={!listName.trim()}
                activeOpacity={0.7}
              >
                <Text style={styles.saveBtnText}>{uk.saveListButton}</Text>
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
  header: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  totalText: {
    color: colors.textSecondary,
    fontSize: 15,
    fontWeight: '600',
  },
  list: {
    padding: 12,
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
    fontSize: 18,
    fontWeight: '600',
  },
  emptyHint: {
    color: colors.textMuted,
    fontSize: 14,
    marginTop: 4,
  },
  actions: {
    padding: 12,
    gap: 10,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  saveButton: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  saveButtonText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '700',
  },
  clearButton: {
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  clearButtonText: {
    color: colors.danger,
    fontSize: 15,
    fontWeight: '600',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  saveModal: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    padding: 24,
    width: '85%',
  },
  modalTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 16,
  },
  nameInput: {
    backgroundColor: colors.inputBg,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    marginBottom: 20,
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
  },
  cancelBtn: {
    flex: 1,
    backgroundColor: colors.surfaceLight,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  cancelBtnText: {
    color: colors.textSecondary,
    fontSize: 16,
    fontWeight: '600',
  },
  saveBtnModal: {
    flex: 1,
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  saveBtnText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
  },
  disabledBtn: {
    opacity: 0.5,
  },
});

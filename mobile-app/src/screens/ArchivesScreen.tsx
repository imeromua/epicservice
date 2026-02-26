import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Alert,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { colors } from '../theme/colors';
import { uk } from '../i18n/uk';
import {
  getSavedLists,
  getSavedListItems,
  deleteSavedList,
} from '../database/queries';
import type { SavedList, SavedListItem } from '../database/queries';

interface ArchivesScreenProps {
  userId: number;
}

export function ArchivesScreen({ userId }: ArchivesScreenProps) {
  const [lists, setLists] = useState<SavedList[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedItems, setExpandedItems] = useState<SavedListItem[]>([]);

  useFocusEffect(
    useCallback(() => {
      loadLists();
    }, [userId])
  );

  function loadLists() {
    try {
      const data = getSavedLists(userId);
      setLists(data);
    } catch {
      // Handle silently
    }
  }

  function handleExpand(listId: number) {
    if (expandedId === listId) {
      setExpandedId(null);
      setExpandedItems([]);
      return;
    }
    try {
      const items = getSavedListItems(listId);
      setExpandedItems(items);
      setExpandedId(listId);
    } catch {
      Alert.alert(uk.error, uk.errorGeneral);
    }
  }

  function handleDelete(listId: number) {
    Alert.alert(uk.deleteArchive, uk.deleteArchiveConfirm, [
      { text: uk.cancel, style: 'cancel' },
      {
        text: uk.delete,
        style: 'destructive',
        onPress: () => {
          try {
            deleteSavedList(listId);
            if (expandedId === listId) {
              setExpandedId(null);
              setExpandedItems([]);
            }
            loadLists();
            Alert.alert(uk.success, uk.archiveDeleted);
          } catch {
            Alert.alert(uk.error, uk.errorGeneral);
          }
        },
      },
    ]);
  }

  function formatDate(dateStr: string): string {
    try {
      const date = new Date(dateStr + 'Z');
      return date.toLocaleDateString('uk-UA', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  }

  function renderList({ item }: { item: SavedList }) {
    const isExpanded = expandedId === item.id;

    return (
      <View style={styles.listCard}>
        <TouchableOpacity
          style={styles.listHeader}
          onPress={() => handleExpand(item.id)}
          activeOpacity={0.7}
        >
          <View style={styles.listInfo}>
            <Text style={styles.listName}>{item.name}</Text>
            <Text style={styles.listMeta}>
              {formatDate(item.created_at)} • {item.item_count ?? 0}{' '}
              {uk.items}
            </Text>
          </View>
          <View style={styles.listActions}>
            <Text style={styles.expandIcon}>{isExpanded ? '▲' : '▼'}</Text>
            <TouchableOpacity
              style={styles.deleteBtn}
              onPress={() => handleDelete(item.id)}
              activeOpacity={0.7}
            >
              <Text style={styles.deleteBtnText}>🗑</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>

        {isExpanded && (
          <View style={styles.itemsList}>
            {expandedItems.map((listItem) => (
              <View key={listItem.id} style={styles.archiveItem}>
                <View style={styles.archiveItemInfo}>
                  <Text style={styles.archiveItemName}>
                    {listItem.product_name}
                  </Text>
                  <Text style={styles.archiveItemArticle}>
                    {listItem.article}
                  </Text>
                </View>
                <Text style={styles.archiveItemQty}>
                  ×{listItem.quantity}
                </Text>
              </View>
            ))}
          </View>
        )}
      </View>
    );
  }

  if (lists.length === 0) {
    return (
      <View style={styles.container}>
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>📁</Text>
          <Text style={styles.emptyText}>{uk.archivesEmpty}</Text>
          <Text style={styles.emptyHint}>{uk.archivesEmptyHint}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={lists}
        renderItem={renderList}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
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
  listCard: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  listHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
  },
  listInfo: {
    flex: 1,
  },
  listName: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  listMeta: {
    color: colors.textMuted,
    fontSize: 13,
  },
  listActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  expandIcon: {
    color: colors.textMuted,
    fontSize: 12,
  },
  deleteBtn: {
    padding: 4,
  },
  deleteBtnText: {
    fontSize: 18,
  },
  itemsList: {
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  archiveItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  archiveItemInfo: {
    flex: 1,
  },
  archiveItemName: {
    color: colors.text,
    fontSize: 14,
  },
  archiveItemArticle: {
    color: colors.textMuted,
    fontSize: 12,
  },
  archiveItemQty: {
    color: colors.primary,
    fontSize: 16,
    fontWeight: '700',
    marginLeft: 8,
  },
});

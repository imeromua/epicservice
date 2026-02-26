import { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, Alert } from 'react-native';
import {
  Text,
  Surface,
  Searchbar,
  Chip,
  Button,
  ActivityIndicator,
  Menu,
  IconButton,
} from 'react-native-paper';
import { FlashList } from '@shopify/flash-list';
import { useAdmin } from '../../../src/hooks/useAdmin';
import type { AdminUser } from '../../../src/types';

export default function UsersScreen() {
  const { getUsers, approveUser, blockUser, unblockUser, changeRole } = useAdmin();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [menuVisible, setMenuVisible] = useState<number | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getUsers({
        q: query || undefined,
        status: statusFilter,
      });
      setUsers(data.users);
    } catch {
      Alert.alert('Помилка', 'Не вдалося завантажити користувачів');
    } finally {
      setLoading(false);
    }
  }, [getUsers, query, statusFilter]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleApprove = useCallback(
    async (targetId: number) => {
      try {
        await approveUser(targetId);
        await loadUsers();
      } catch {
        Alert.alert('Помилка', 'Не вдалося підтвердити');
      }
    },
    [approveUser, loadUsers],
  );

  const handleBlock = useCallback(
    async (targetId: number) => {
      Alert.prompt?.('Причина блокування', '', async (reason) => {
        try {
          await blockUser(targetId, reason || 'Заблоковано адміном');
          await loadUsers();
        } catch {
          Alert.alert('Помилка', 'Не вдалося заблокувати');
        }
      }) ??
        (async () => {
          try {
            await blockUser(targetId, 'Заблоковано адміном');
            await loadUsers();
          } catch {
            Alert.alert('Помилка', 'Не вдалося заблокувати');
          }
        })();
    },
    [blockUser, loadUsers],
  );

  const handleUnblock = useCallback(
    async (targetId: number) => {
      try {
        await unblockUser(targetId);
        await loadUsers();
      } catch {
        Alert.alert('Помилка', 'Не вдалося розблокувати');
      }
    },
    [unblockUser, loadUsers],
  );

  const handleChangeRole = useCallback(
    async (targetId: number, role: string) => {
      try {
        await changeRole(targetId, role);
        setMenuVisible(null);
        await loadUsers();
      } catch {
        Alert.alert('Помилка', 'Не вдалося змінити роль');
      }
    },
    [changeRole, loadUsers],
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return '#4CAF50';
      case 'pending':
        return '#FF9800';
      case 'blocked':
        return '#F44336';
      default:
        return '#888';
    }
  };

  const renderItem = useCallback(
    ({ item }: { item: AdminUser }) => (
      <Surface style={styles.row} elevation={1}>
        <View style={styles.rowInfo}>
          <Text variant="titleSmall">{item.display_name || item.first_name}</Text>
          <View style={styles.badges}>
            <Chip
              compact
              textStyle={styles.chipText}
              style={[styles.badge, { backgroundColor: getStatusColor(item.status) }]}
            >
              {item.status}
            </Chip>
            <Chip compact textStyle={styles.chipText} style={styles.roleBadge}>
              {item.role}
            </Chip>
          </View>
        </View>
        <View style={styles.rowActions}>
          {item.status === 'pending' && (
            <Button compact mode="text" onPress={() => handleApprove(item.id)}>
              ✓
            </Button>
          )}
          {item.status === 'approved' && (
            <Button compact mode="text" onPress={() => handleBlock(item.id)}>
              ✕
            </Button>
          )}
          {item.status === 'blocked' && (
            <Button compact mode="text" onPress={() => handleUnblock(item.id)}>
              ↺
            </Button>
          )}
          <Menu
            visible={menuVisible === item.id}
            onDismiss={() => setMenuVisible(null)}
            anchor={
              <IconButton
                icon="dots-vertical"
                size={20}
                onPress={() => setMenuVisible(item.id)}
              />
            }
          >
            <Menu.Item
              onPress={() => handleChangeRole(item.id, 'user')}
              title="Користувач"
            />
            <Menu.Item
              onPress={() => handleChangeRole(item.id, 'moderator')}
              title="Модератор"
            />
            <Menu.Item
              onPress={() => handleChangeRole(item.id, 'admin')}
              title="Адмін"
            />
          </Menu>
        </View>
      </Surface>
    ),
    [menuVisible, handleApprove, handleBlock, handleUnblock, handleChangeRole],
  );

  return (
    <View style={styles.container}>
      <Searchbar
        placeholder="Пошук користувачів..."
        value={query}
        onChangeText={setQuery}
        style={styles.searchbar}
      />

      <View style={styles.filters}>
        {['approved', 'pending', 'blocked'].map((s) => (
          <Chip
            key={s}
            selected={statusFilter === s}
            onPress={() => setStatusFilter(statusFilter === s ? undefined : s)}
            style={styles.filterChip}
          >
            {s}
          </Chip>
        ))}
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" />
        </View>
      ) : (
        <FlashList
          data={users}
          renderItem={renderItem}
          estimatedItemSize={72}
          keyExtractor={(item) => String(item.id)}
          refreshing={loading}
          onRefresh={loadUsers}
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
  searchbar: {
    margin: 12,
  },
  filters: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    gap: 8,
    marginBottom: 8,
  },
  filterChip: {
    marginRight: 4,
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
    padding: 12,
  },
  rowInfo: {
    flex: 1,
  },
  badges: {
    flexDirection: 'row',
    marginTop: 4,
    gap: 4,
  },
  badge: {
    height: 24,
  },
  chipText: {
    fontSize: 11,
    color: '#fff',
  },
  roleBadge: {
    height: 24,
    backgroundColor: '#1976D2',
  },
  rowActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});

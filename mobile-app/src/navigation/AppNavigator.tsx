import React, { useState, useCallback } from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useFocusEffect } from '@react-navigation/native';
import { colors } from '../theme/colors';
import { uk } from '../i18n/uk';
import { SearchScreen } from '../screens/SearchScreen';
import { ListScreen } from '../screens/ListScreen';
import { ArchivesScreen } from '../screens/ArchivesScreen';
import { AdminScreen } from '../screens/AdminScreen';
import { Header } from '../components/Header';
import { getListCount } from '../database/queries';
import type { Session } from '../services/auth';
import { View, Text, StyleSheet } from 'react-native';

const Tab = createBottomTabNavigator();

interface AppNavigatorProps {
  session: Session;
  onLogout: () => void;
}

function TabIcon({ icon, focused }: { icon: string; focused: boolean }) {
  return (
    <Text style={{ fontSize: 22, opacity: focused ? 1 : 0.6 }}>{icon}</Text>
  );
}

export function AppNavigator({ session, onLogout }: AppNavigatorProps) {
  const [listCount, setListCount] = useState(0);

  const refreshListCount = useCallback(() => {
    try {
      const count = getListCount(session.userId);
      setListCount(count);
    } catch {
      // Handle silently
    }
  }, [session.userId]);

  return (
    <View style={styles.container}>
      <Header
        onLogout={onLogout}
        firstName={session.firstName}
      />
      <Tab.Navigator
        screenOptions={{
          headerShown: false,
          tabBarStyle: {
            backgroundColor: colors.surface,
            borderTopColor: colors.border,
            borderTopWidth: 1,
            paddingBottom: 4,
            paddingTop: 4,
            height: 60,
          },
          tabBarActiveTintColor: colors.primary,
          tabBarInactiveTintColor: colors.textMuted,
          tabBarLabelStyle: {
            fontSize: 12,
            fontWeight: '600',
          },
        }}
      >
        <Tab.Screen
          name="Search"
          options={{
            tabBarLabel: uk.tabSearch,
            tabBarIcon: ({ focused }) => (
              <TabIcon icon="🔍" focused={focused} />
            ),
          }}
        >
          {() => <SearchScreen userId={session.userId} />}
        </Tab.Screen>

        <Tab.Screen
          name="List"
          options={{
            tabBarLabel: uk.tabList,
            tabBarIcon: ({ focused }) => (
              <TabIcon icon="📋" focused={focused} />
            ),
            tabBarBadge: listCount > 0 ? listCount : undefined,
            tabBarBadgeStyle: {
              backgroundColor: colors.primary,
              color: colors.text,
              fontSize: 11,
              fontWeight: '700',
            },
          }}
          listeners={{
            focus: () => refreshListCount(),
          }}
        >
          {() => (
            <ListScreen
              userId={session.userId}
              onListCountChange={setListCount}
            />
          )}
        </Tab.Screen>

        <Tab.Screen
          name="Archives"
          options={{
            tabBarLabel: uk.tabArchives,
            tabBarIcon: ({ focused }) => (
              <TabIcon icon="📁" focused={focused} />
            ),
          }}
        >
          {() => <ArchivesScreen userId={session.userId} />}
        </Tab.Screen>

        {session.role === 'admin' && (
          <Tab.Screen
            name="Admin"
            options={{
              tabBarLabel: uk.tabAdmin,
              tabBarIcon: ({ focused }) => (
                <TabIcon icon="⚙️" focused={focused} />
              ),
            }}
          >
            {() => <AdminScreen session={session} />}
          </Tab.Screen>
        )}
      </Tab.Navigator>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
});

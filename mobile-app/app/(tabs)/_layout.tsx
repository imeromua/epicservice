import { Tabs } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuthStore } from '../../src/store/authStore';

export default function TabsLayout() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === 'admin' || user?.role === 'moderator';

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: '#1976D2',
        headerShown: true,
      }}
    >
      <Tabs.Screen
        name="search"
        options={{
          title: 'Пошук',
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="magnify" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="list"
        options={{
          title: 'Мій список',
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons
              name="clipboard-list"
              size={size}
              color={color}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="archives"
        options={{
          title: 'Архіви',
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons
              name="archive"
              size={size}
              color={color}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="admin"
        options={{
          title: 'Адмін',
          href: isAdmin ? '/(tabs)/admin' : null,
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="shield-crown" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}

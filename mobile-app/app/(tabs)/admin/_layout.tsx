import { Stack } from 'expo-router';
import { useAuthStore } from '../../../src/store/authStore';
import { Redirect } from 'expo-router';

export default function AdminLayout() {
  const user = useAuthStore((s) => s.user);

  if (user?.role !== 'admin' && user?.role !== 'moderator') {
    return <Redirect href="/(tabs)/search" />;
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="users" />
      <Stack.Screen name="import" />
      <Stack.Screen name="moderation" />
      <Stack.Screen name="danger" />
    </Stack>
  );
}

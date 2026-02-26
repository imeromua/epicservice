import { useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import * as adminApi from '../api/admin';
import * as photosApi from '../api/photos';

export function useAdmin() {
  const user = useAuthStore((s) => s.user);

  const isAdmin =
    user?.role === 'admin' || user?.role === 'moderator';

  const getStatistics = useCallback(async () => {
    if (!user) throw new Error('Not authenticated');
    return adminApi.getAdminStatistics(user.id);
  }, [user]);

  const getUsers = useCallback(
    async (params?: { status?: string; role?: string; q?: string }) => {
      if (!user) throw new Error('Not authenticated');
      return adminApi.getAllUsers(user.id, params);
    },
    [user],
  );

  const approveUser = useCallback(
    async (targetUserId: number) => {
      if (!user) throw new Error('Not authenticated');
      return adminApi.approveUser(user.id, targetUserId);
    },
    [user],
  );

  const blockUser = useCallback(
    async (targetUserId: number, reason: string) => {
      if (!user) throw new Error('Not authenticated');
      return adminApi.blockUser(user.id, targetUserId, reason);
    },
    [user],
  );

  const unblockUser = useCallback(
    async (targetUserId: number) => {
      if (!user) throw new Error('Not authenticated');
      return adminApi.unblockUser(user.id, targetUserId);
    },
    [user],
  );

  const changeRole = useCallback(
    async (targetUserId: number, role: string) => {
      if (!user) throw new Error('Not authenticated');
      return adminApi.changeUserRole(user.id, targetUserId, role);
    },
    [user],
  );

  const importExcel = useCallback(
    async (fileUri: string) => {
      if (!user) throw new Error('Not authenticated');
      return adminApi.importExcel(user.id, fileUri);
    },
    [user],
  );

  const exportStock = useCallback(async () => {
    if (!user) throw new Error('Not authenticated');
    return adminApi.exportStock(user.id);
  }, [user]);

  const getPendingPhotos = useCallback(async () => {
    if (!user) throw new Error('Not authenticated');
    return photosApi.getPendingPhotos(user.id);
  }, [user]);

  const moderatePhoto = useCallback(
    async (
      photoId: number,
      status: 'approved' | 'rejected',
      reason?: string,
    ) => {
      if (!user) throw new Error('Not authenticated');
      return photosApi.moderatePhoto(photoId, status, user.id, reason);
    },
    [user],
  );

  const dangerClearDatabase = useCallback(async () => {
    if (!user) throw new Error('Not authenticated');
    return adminApi.dangerClearDatabase(user.id);
  }, [user]);

  const dangerDeleteAllPhotos = useCallback(async () => {
    if (!user) throw new Error('Not authenticated');
    return adminApi.dangerDeleteAllPhotos(user.id);
  }, [user]);

  const dangerResetModeration = useCallback(async () => {
    if (!user) throw new Error('Not authenticated');
    return adminApi.dangerResetModeration(user.id);
  }, [user]);

  const dangerFullWipe = useCallback(async () => {
    if (!user) throw new Error('Not authenticated');
    return adminApi.dangerFullWipe(user.id);
  }, [user]);

  return {
    isAdmin,
    getStatistics,
    getUsers,
    approveUser,
    blockUser,
    unblockUser,
    changeRole,
    importExcel,
    exportStock,
    getPendingPhotos,
    moderatePhoto,
    dangerClearDatabase,
    dangerDeleteAllPhotos,
    dangerResetModeration,
    dangerFullWipe,
  };
}

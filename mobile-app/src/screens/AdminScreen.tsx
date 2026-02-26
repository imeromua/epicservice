import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  ActivityIndicator,
  TextInput,
  Modal,
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system';
import { useFocusEffect } from '@react-navigation/native';
import { colors } from '../theme/colors';
import { uk } from '../i18n/uk';
import {
  importProducts,
  getProductCount,
  clearAllProducts,
  clearAllData,
  getUserCount,
} from '../database/queries';
import { parseCSV } from '../utils/csv';
import type { Session } from '../services/auth';
import {
  isBiometricAvailable,
  isBiometricEnabled,
  enableBiometric,
  disableBiometric,
} from '../services/biometric';

interface AdminScreenProps {
  session: Session;
}

export function AdminScreen({ session }: AdminScreenProps) {
  const [productCount, setProductCount] = useState(0);
  const [userCount, setUserCount] = useState(0);
  const [importing, setImporting] = useState(false);
  const [showClearAllModal, setShowClearAllModal] = useState(false);
  const [clearAllInput, setClearAllInput] = useState('');
  const [biometricAvail, setBiometricAvail] = useState(false);
  const [biometricOn, setBiometricOn] = useState(false);

  useFocusEffect(
    useCallback(() => {
      loadStats();
      checkBiometric();
    }, [])
  );

  function loadStats() {
    try {
      setProductCount(getProductCount());
      setUserCount(getUserCount());
    } catch {
      // Handle silently
    }
  }

  async function checkBiometric() {
    const avail = await isBiometricAvailable();
    setBiometricAvail(avail);
    if (avail) {
      const enabled = await isBiometricEnabled();
      setBiometricOn(enabled);
    }
  }

  async function handleToggleBiometric() {
    try {
      if (biometricOn) {
        await disableBiometric();
        setBiometricOn(false);
        Alert.alert(uk.success, uk.biometricDisabled);
      } else {
        await enableBiometric(session);
        setBiometricOn(true);
        Alert.alert(uk.success, uk.biometricEnabled);
      }
    } catch {
      Alert.alert(uk.error, uk.errorGeneral);
    }
  }

  async function handleImport() {
    try {
      setImporting(true);
      const result = await DocumentPicker.getDocumentAsync({
        type: ['text/csv', 'text/comma-separated-values', 'text/*'],
        copyToCacheDirectory: true,
      });

      if (result.canceled || !result.assets || result.assets.length === 0) {
        setImporting(false);
        return;
      }

      const file = result.assets[0];
      const content = await FileSystem.readAsStringAsync(file.uri);

      if (!content.trim()) {
        Alert.alert(uk.error, uk.errorEmptyFile);
        setImporting(false);
        return;
      }

      const products = parseCSV(content);
      if (products.length === 0) {
        Alert.alert(uk.error, uk.errorInvalidCSV);
        setImporting(false);
        return;
      }

      const count = importProducts(products);
      loadStats();
      Alert.alert(
        uk.importSuccess,
        `${uk.importedCount}: ${count}`
      );
    } catch {
      Alert.alert(uk.error, uk.errorImportFailed);
    } finally {
      setImporting(false);
    }
  }

  function handleClearProducts() {
    Alert.alert(uk.warning, uk.clearProductsConfirm, [
      { text: uk.cancel, style: 'cancel' },
      {
        text: uk.yes,
        style: 'destructive',
        onPress: () => {
          try {
            clearAllProducts();
            loadStats();
            Alert.alert(uk.success, uk.productsCleared);
          } catch {
            Alert.alert(uk.error, uk.errorGeneral);
          }
        },
      },
    ]);
  }

  function handleClearAll() {
    setShowClearAllModal(true);
    setClearAllInput('');
  }

  function confirmClearAll() {
    if (clearAllInput !== uk.clearAllDataKeyword) return;
    try {
      clearAllData();
      loadStats();
      setShowClearAllModal(false);
      Alert.alert(uk.success, uk.dataCleared);
    } catch {
      Alert.alert(uk.error, uk.errorGeneral);
    }
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
    >
      {/* Stats */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>{uk.stats}</Text>
        <View style={styles.statsRow}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{productCount}</Text>
            <Text style={styles.statLabel}>{uk.productsInDb}</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{userCount}</Text>
            <Text style={styles.statLabel}>{uk.usersCount}</Text>
          </View>
        </View>
      </View>

      {/* Import */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>{uk.importProducts}</Text>
        <Text style={styles.hint}>{uk.csvFormat}</Text>
        <TouchableOpacity
          style={[styles.importButton, importing && styles.disabledBtn]}
          onPress={handleImport}
          disabled={importing}
          activeOpacity={0.7}
        >
          {importing ? (
            <ActivityIndicator color={colors.text} />
          ) : (
            <Text style={styles.importButtonText}>{uk.importButton}</Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Biometric */}
      {biometricAvail && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{uk.settings}</Text>
          <TouchableOpacity
            style={[
              styles.biometricButton,
              biometricOn && styles.biometricButtonActive,
            ]}
            onPress={handleToggleBiometric}
            activeOpacity={0.7}
          >
            <Text style={styles.biometricIcon}>🔐</Text>
            <Text style={styles.biometricText}>
              {biometricOn ? uk.disableBiometric : uk.enableBiometric}
            </Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Danger zone */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, styles.dangerTitle]}>
          {uk.actions}
        </Text>
        <TouchableOpacity
          style={styles.dangerButton}
          onPress={handleClearProducts}
          activeOpacity={0.7}
        >
          <Text style={styles.dangerButtonText}>{uk.clearProducts}</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.dangerButton, styles.dangerButtonCritical]}
          onPress={handleClearAll}
          activeOpacity={0.7}
        >
          <Text style={styles.dangerButtonText}>{uk.clearAllData}</Text>
        </TouchableOpacity>
      </View>

      {/* Clear all confirmation modal */}
      <Modal
        visible={showClearAllModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowClearAllModal(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setShowClearAllModal(false)}
        >
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>{uk.warning}</Text>
            <Text style={styles.modalText}>{uk.clearAllDataConfirm}</Text>
            <TextInput
              style={styles.modalInput}
              value={clearAllInput}
              onChangeText={setClearAllInput}
              autoCapitalize="characters"
              placeholder={uk.clearAllDataKeyword}
              placeholderTextColor={colors.textMuted}
            />
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setShowClearAllModal(false)}
                activeOpacity={0.7}
              >
                <Text style={styles.cancelBtnText}>{uk.cancel}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.confirmDeleteBtn,
                  clearAllInput !== uk.clearAllDataKeyword &&
                    styles.disabledBtn,
                ]}
                onPress={confirmClearAll}
                disabled={clearAllInput !== uk.clearAllDataKeyword}
                activeOpacity={0.7}
              >
                <Text style={styles.confirmDeleteText}>{uk.delete}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </TouchableOpacity>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 12,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  statValue: {
    color: colors.primary,
    fontSize: 28,
    fontWeight: '800',
  },
  statLabel: {
    color: colors.textSecondary,
    fontSize: 13,
    marginTop: 4,
  },
  hint: {
    color: colors.textMuted,
    fontSize: 13,
    marginBottom: 12,
  },
  importButton: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  importButtonText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '700',
  },
  biometricButton: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  biometricButtonActive: {
    borderColor: colors.success,
  },
  biometricIcon: {
    fontSize: 20,
    marginRight: 10,
  },
  biometricText: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '500',
  },
  dangerTitle: {
    color: colors.danger,
  },
  dangerButton: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.danger,
  },
  dangerButtonCritical: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
  },
  dangerButtonText: {
    color: colors.danger,
    fontSize: 15,
    fontWeight: '600',
  },
  disabledBtn: {
    opacity: 0.5,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modal: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    padding: 24,
    width: '85%',
  },
  modalTitle: {
    color: colors.danger,
    fontSize: 20,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 12,
  },
  modalText: {
    color: colors.textSecondary,
    fontSize: 15,
    textAlign: 'center',
    marginBottom: 16,
    lineHeight: 22,
  },
  modalInput: {
    backgroundColor: colors.inputBg,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.danger,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    textAlign: 'center',
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
  confirmDeleteBtn: {
    flex: 1,
    backgroundColor: colors.danger,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  confirmDeleteText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
  },
});

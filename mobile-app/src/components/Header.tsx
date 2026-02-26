import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';
import { uk } from '../i18n/uk';

interface HeaderProps {
  title?: string;
  onLogout: () => void;
  firstName?: string;
}

export function Header({
  title = uk.appName,
  onLogout,
  firstName,
}: HeaderProps) {
  return (
    <View style={styles.container}>
      <View style={styles.left}>
        <Text style={styles.title}>{title}</Text>
        {firstName ? (
          <Text style={styles.greeting}>👋 {firstName}</Text>
        ) : null}
      </View>
      <TouchableOpacity
        style={styles.logoutButton}
        onPress={onLogout}
        activeOpacity={0.7}
      >
        <Text style={styles.logoutText}>{uk.logout}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  left: {
    flex: 1,
  },
  title: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '700',
  },
  greeting: {
    color: colors.textSecondary,
    fontSize: 13,
    marginTop: 2,
  },
  logoutButton: {
    backgroundColor: colors.surfaceLight,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  logoutText: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: '500',
  },
});

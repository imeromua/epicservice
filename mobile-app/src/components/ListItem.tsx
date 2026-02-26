import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';

interface ListItemProps {
  name: string;
  article: string;
  quantity: number;
  department?: string;
  price?: number;
  onIncrement: () => void;
  onDecrement: () => void;
  onDelete: () => void;
}

export function ListItem({
  name,
  article,
  quantity,
  department,
  price,
  onIncrement,
  onDecrement,
  onDelete,
}: ListItemProps) {
  return (
    <View style={styles.container}>
      <View style={styles.info}>
        <Text style={styles.name} numberOfLines={2}>
          {name}
        </Text>
        <Text style={styles.article}>{article}</Text>
        {department ? (
          <Text style={styles.department}>{department}</Text>
        ) : null}
        {price !== undefined && price > 0 && (
          <Text style={styles.price}>{(price * quantity).toFixed(2)} ₴</Text>
        )}
      </View>
      <View style={styles.controls}>
        <View style={styles.quantityRow}>
          <TouchableOpacity
            style={styles.quantityButton}
            onPress={onDecrement}
            activeOpacity={0.7}
          >
            <Text style={styles.quantityButtonText}>−</Text>
          </TouchableOpacity>
          <Text style={styles.quantity}>{quantity}</Text>
          <TouchableOpacity
            style={styles.quantityButton}
            onPress={onIncrement}
            activeOpacity={0.7}
          >
            <Text style={styles.quantityButtonText}>+</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity
          style={styles.deleteButton}
          onPress={onDelete}
          activeOpacity={0.7}
        >
          <Text style={styles.deleteText}>✕</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  info: {
    flex: 1,
    marginRight: 10,
  },
  name: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '600',
    marginBottom: 2,
  },
  article: {
    color: colors.textSecondary,
    fontSize: 13,
  },
  department: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  price: {
    color: colors.success,
    fontSize: 13,
    fontWeight: '500',
    marginTop: 2,
  },
  controls: {
    alignItems: 'center',
    gap: 8,
  },
  quantityRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  quantityButton: {
    backgroundColor: colors.surfaceLight,
    width: 34,
    height: 34,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  quantityButtonText: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '600',
  },
  quantity: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '700',
    minWidth: 30,
    textAlign: 'center',
  },
  deleteButton: {
    backgroundColor: colors.danger,
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  deleteText: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '700',
  },
});

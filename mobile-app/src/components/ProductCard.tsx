import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';
import { uk } from '../i18n/uk';
import type { Product } from '../database/queries';

interface ProductCardProps {
  product: Product;
  onAdd: (product: Product) => void;
}

export function ProductCard({ product, onAdd }: ProductCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.info}>
        <Text style={styles.name} numberOfLines={2}>
          {product.name}
        </Text>
        <View style={styles.details}>
          <Text style={styles.article}>
            {uk.article}: {product.article}
          </Text>
          {product.department ? (
            <Text style={styles.department}>{product.department}</Text>
          ) : null}
        </View>
        {product.price > 0 && (
          <Text style={styles.price}>
            {uk.price}: {product.price.toFixed(2)} ₴
          </Text>
        )}
      </View>
      <TouchableOpacity
        style={styles.addButton}
        onPress={() => onAdd(product)}
        activeOpacity={0.7}
      >
        <Text style={styles.addButtonText}>{uk.addButton}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
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
    marginRight: 12,
  },
  name: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '600',
    marginBottom: 4,
  },
  details: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 4,
  },
  article: {
    color: colors.textSecondary,
    fontSize: 13,
  },
  department: {
    color: colors.textMuted,
    fontSize: 13,
  },
  price: {
    color: colors.success,
    fontSize: 14,
    fontWeight: '500',
  },
  addButton: {
    backgroundColor: colors.primary,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
  },
  addButtonText: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
  },
});

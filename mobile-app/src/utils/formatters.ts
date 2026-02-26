/**
 * Format price in UAH: 1 234 567,89 грн
 */
export function formatPrice(value: number): string {
  const parts = value.toFixed(2).split('.');
  const intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0');
  return `${intPart},${parts[1]} грн`;
}

/**
 * Format number with spaces: 1 234 567
 */
export function formatNumber(value: number): string {
  return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0');
}

/**
 * Format date: 26.02.2026 22:05
 */
export function formatDate(date: Date | number | string): string {
  const d = typeof date === 'object' ? date : new Date(date);
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${day}.${month}.${year} ${hours}:${minutes}`;
}

/**
 * Format relative time in Ukrainian
 */
export function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'щойно';
  if (minutes < 60) return `${minutes} хв тому`;
  if (hours < 24) return `${hours} год тому`;
  return `${days} дн тому`;
}

/**
 * Parse quantity string to number
 */
export function parseQuantity(qty: string): number {
  const parsed = parseFloat(qty);
  return isNaN(parsed) ? 0 : parsed;
}

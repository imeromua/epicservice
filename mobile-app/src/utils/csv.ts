export interface CSVProduct {
  article: string;
  name: string;
  department: string;
  group_name: string;
  quantity: string;
  price: number;
}

function parseCSVLine(line: string): string[] {
  const fields: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (inQuotes) {
      if (char === '"') {
        if (i + 1 < line.length && line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        current += char;
      }
    } else {
      if (char === '"') {
        inQuotes = true;
      } else if (char === ',' || char === ';') {
        fields.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
  }
  fields.push(current.trim());
  return fields;
}

export function parseCSV(text: string): CSVProduct[] {
  const lines = text
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .split('\n')
    .filter((line) => line.trim().length > 0);

  if (lines.length === 0) {
    return [];
  }

  // Skip header if first line looks like a header
  const firstFields = parseCSVLine(lines[0]);
  const hasHeader =
    firstFields.some(
      (f) =>
        f.toLowerCase().includes('артикул') ||
        f.toLowerCase().includes('article') ||
        f.toLowerCase().includes('назва') ||
        f.toLowerCase().includes('name')
    );

  const startIndex = hasHeader ? 1 : 0;
  const products: CSVProduct[] = [];

  for (let i = startIndex; i < lines.length; i++) {
    const fields = parseCSVLine(lines[i]);
    if (fields.length < 2) continue;

    const article = fields[0] || '';
    const name = fields[1] || '';
    const department = fields[2] || '';
    const group_name = fields[3] || '';
    const quantity = fields[4] || '';
    const priceStr = (fields[5] || '0').replace(',', '.');
    const price = parseFloat(priceStr) || 0;

    if (article && name) {
      products.push({ article, name, department, group_name, quantity, price });
    }
  }

  return products;
}

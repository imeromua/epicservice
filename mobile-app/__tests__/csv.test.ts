import { parseCSV, parseCSVLine } from '../src/utils/csv';

// Експортуємо parseCSVLine для тестування
// Тестуємо через parseCSV яка використовує parseCSVLine внутрішньо

describe('parseCSV — парсинг CSV файлів', () => {
  test('парсить прості CSV дані без заголовка', () => {
    const csv = `АРТ001,Молоток,Інструменти,Ручні,10,150.50
АРТ002,Дриль,Електро,Дрилі,5,2500`;
    const result = parseCSV(csv);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      article: 'АРТ001',
      name: 'Молоток',
      department: 'Інструменти',
      group_name: 'Ручні',
      quantity: '10',
      price: 150.50,
    });
    expect(result[1]).toEqual({
      article: 'АРТ002',
      name: 'Дриль',
      department: 'Електро',
      group_name: 'Дрилі',
      quantity: '5',
      price: 2500,
    });
  });

  test('пропускає заголовок з "артикул"', () => {
    const csv = `артикул,назва,відділ,група,кількість,ціна
АРТ001,Молоток,Інструменти,Ручні,10,150.50`;
    const result = parseCSV(csv);
    expect(result).toHaveLength(1);
    expect(result[0].article).toBe('АРТ001');
  });

  test('пропускає заголовок з "article"', () => {
    const csv = `article,name,department,group,quantity,price
АРТ001,Молоток,Інструменти,Ручні,10,150.50`;
    const result = parseCSV(csv);
    expect(result).toHaveLength(1);
  });

  test('пропускає заголовок з "назва"', () => {
    const csv = `код,назва товару,відділ,група,кількість,ціна
АРТ001,Молоток,Інструменти,Ручні,10,150.50`;
    const result = parseCSV(csv);
    expect(result).toHaveLength(1);
  });

  test('обробляє поля в лапках', () => {
    const csv = `АРТ001,"Молоток ""ударний""",Інструменти,Ручні,10,150.50`;
    const result = parseCSV(csv);
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('Молоток "ударний"');
  });

  test('обробляє роздільник крапку з комою', () => {
    const csv = `АРТ001;Молоток;Інструменти;Ручні;10;150.50`;
    const result = parseCSV(csv);
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('Молоток');
  });

  test('обробляє ціну з комою замість крапки', () => {
    const csv = `АРТ001,Молоток,Інструменти,Ручні,10,"150,50"`;
    const result = parseCSV(csv);
    expect(result).toHaveLength(1);
    expect(result[0].price).toBe(150.50);
  });

  test('обробляє відсутні поля', () => {
    const csv = `АРТ001,Молоток,,,,`;
    const result = parseCSV(csv);
    expect(result).toHaveLength(1);
    expect(result[0].department).toBe('');
    expect(result[0].price).toBe(0);
  });

  test('пропускає рядки з менше ніж 2 полями', () => {
    const csv = `АРТ001
АРТ002,Молоток,Інструменти,Ручні,10,150`;
    const result = parseCSV(csv);
    expect(result).toHaveLength(1);
    expect(result[0].article).toBe('АРТ002');
  });

  test('пропускає рядки без артикулу або назви', () => {
    const csv = `,Молоток,Інструменти,Ручні,10,150
АРТ001,,Інструменти,Ручні,10,150
АРТ002,Дриль,Електро,Дрилі,5,2500`;
    const result = parseCSV(csv);
    expect(result).toHaveLength(1);
    expect(result[0].article).toBe('АРТ002');
  });

  test('повертає порожній масив для порожнього тексту', () => {
    expect(parseCSV('')).toHaveLength(0);
    expect(parseCSV('   ')).toHaveLength(0);
    expect(parseCSV('\n\n')).toHaveLength(0);
  });

  test('обробляє різні закінчення рядків', () => {
    const csvCRLF = `АРТ001,Молоток,Інструменти,Ручні,10,150\r\nАРТ002,Дриль,Електро,Дрилі,5,2500\r\n`;
    const resultCRLF = parseCSV(csvCRLF);
    expect(resultCRLF).toHaveLength(2);

    const csvCR = `АРТ001,Молоток,Інструменти,Ручні,10,150\rАРТ002,Дриль,Електро,Дрилі,5,2500\r`;
    const resultCR = parseCSV(csvCR);
    expect(resultCR).toHaveLength(2);
  });

  test('обробляє великий набір даних', () => {
    const lines = Array.from({ length: 1000 }, (_, i) =>
      `АРТ${i},Товар ${i},Відділ ${i % 5},Група,${i},${i * 10.5}`
    );
    const csv = lines.join('\n');
    const result = parseCSV(csv);
    expect(result).toHaveLength(1000);
    expect(result[999].article).toBe('АРТ999');
    expect(result[999].price).toBe(999 * 10.5);
  });
});

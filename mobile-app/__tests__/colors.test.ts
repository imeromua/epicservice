import { colors } from '../src/theme/colors';

describe('colors — палітра кольорів', () => {
  test('визначені всі основні кольори', () => {
    expect(colors.background).toBeDefined();
    expect(colors.surface).toBeDefined();
    expect(colors.surfaceLight).toBeDefined();
    expect(colors.primary).toBeDefined();
    expect(colors.primaryDark).toBeDefined();
    expect(colors.success).toBeDefined();
    expect(colors.danger).toBeDefined();
    expect(colors.warning).toBeDefined();
    expect(colors.text).toBeDefined();
    expect(colors.textSecondary).toBeDefined();
    expect(colors.textMuted).toBeDefined();
    expect(colors.border).toBeDefined();
    expect(colors.inputBg).toBeDefined();
  });

  test('всі кольори є валідними hex значеннями', () => {
    const hexRegex = /^#[0-9a-fA-F]{6}$/;
    for (const [key, value] of Object.entries(colors)) {
      expect(value).toMatch(hexRegex);
    }
  });

  test('фон відповідає оригінальному мініапп', () => {
    expect(colors.background).toBe('#0f172a');
  });

  test('основний колір відповідає оригіналу', () => {
    expect(colors.primary).toBe('#3b82f6');
  });
});

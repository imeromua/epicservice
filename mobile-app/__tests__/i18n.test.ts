import { uk } from '../src/i18n/uk';

describe('uk — українська локалізація', () => {
  test('містить всі ключі авторизації', () => {
    expect(uk.login).toBeDefined();
    expect(uk.register).toBeDefined();
    expect(uk.loginTitle).toBeDefined();
    expect(uk.registerTitle).toBeDefined();
    expect(uk.loginPlaceholder).toBeDefined();
    expect(uk.passwordPlaceholder).toBeDefined();
    expect(uk.firstNamePlaceholder).toBeDefined();
    expect(uk.loginButton).toBeDefined();
    expect(uk.registerButton).toBeDefined();
    expect(uk.switchToRegister).toBeDefined();
    expect(uk.switchToLogin).toBeDefined();
    expect(uk.biometricLogin).toBeDefined();
    expect(uk.biometricPrompt).toBeDefined();
    expect(uk.logout).toBeDefined();
    expect(uk.logoutConfirm).toBeDefined();
  });

  test('містить всі ключі помилок', () => {
    expect(uk.errorLoginRequired).toBeDefined();
    expect(uk.errorPasswordRequired).toBeDefined();
    expect(uk.errorFirstNameRequired).toBeDefined();
    expect(uk.errorInvalidCredentials).toBeDefined();
    expect(uk.errorUserExists).toBeDefined();
    expect(uk.errorGeneral).toBeDefined();
    expect(uk.errorBiometricFailed).toBeDefined();
    expect(uk.errorBiometricNotAvailable).toBeDefined();
    expect(uk.errorBiometricNotEnabled).toBeDefined();
    expect(uk.errorPasswordTooShort).toBeDefined();
    expect(uk.errorLoginTooShort).toBeDefined();
    expect(uk.errorImportFailed).toBeDefined();
    expect(uk.errorInvalidCSV).toBeDefined();
    expect(uk.errorEmptyFile).toBeDefined();
  });

  test('містить всі ключі пошуку', () => {
    expect(uk.searchTitle).toBeDefined();
    expect(uk.searchPlaceholder).toBeDefined();
    expect(uk.searchEmpty).toBeDefined();
    expect(uk.searchNoResults).toBeDefined();
    expect(uk.allDepartments).toBeDefined();
    expect(uk.addToList).toBeDefined();
    expect(uk.addButton).toBeDefined();
    expect(uk.article).toBeDefined();
    expect(uk.department).toBeDefined();
    expect(uk.price).toBeDefined();
    expect(uk.quantity).toBeDefined();
    expect(uk.enterQuantity).toBeDefined();
  });

  test('містить всі ключі списку', () => {
    expect(uk.listTitle).toBeDefined();
    expect(uk.listEmpty).toBeDefined();
    expect(uk.listEmptyHint).toBeDefined();
    expect(uk.saveList).toBeDefined();
    expect(uk.clearList).toBeDefined();
    expect(uk.clearListConfirm).toBeDefined();
    expect(uk.saveListTitle).toBeDefined();
    expect(uk.saveListName).toBeDefined();
    expect(uk.saveListNamePlaceholder).toBeDefined();
    expect(uk.listSaved).toBeDefined();
    expect(uk.listCleared).toBeDefined();
    expect(uk.totalItems).toBeDefined();
    expect(uk.deleteItem).toBeDefined();
  });

  test('містить всі ключі архівів', () => {
    expect(uk.archivesTitle).toBeDefined();
    expect(uk.archivesEmpty).toBeDefined();
    expect(uk.archivesEmptyHint).toBeDefined();
    expect(uk.deleteArchive).toBeDefined();
    expect(uk.deleteArchiveConfirm).toBeDefined();
    expect(uk.archiveDeleted).toBeDefined();
    expect(uk.items).toBeDefined();
  });

  test('містить всі ключі адмін панелі', () => {
    expect(uk.adminTitle).toBeDefined();
    expect(uk.importProducts).toBeDefined();
    expect(uk.importButton).toBeDefined();
    expect(uk.importSuccess).toBeDefined();
    expect(uk.importedCount).toBeDefined();
    expect(uk.productsInDb).toBeDefined();
    expect(uk.clearProducts).toBeDefined();
    expect(uk.clearProductsConfirm).toBeDefined();
    expect(uk.clearAllData).toBeDefined();
    expect(uk.clearAllDataConfirm).toBeDefined();
    expect(uk.clearAllDataKeyword).toBeDefined();
    expect(uk.csvFormat).toBeDefined();
    expect(uk.stats).toBeDefined();
    expect(uk.usersCount).toBeDefined();
    expect(uk.enableBiometric).toBeDefined();
    expect(uk.disableBiometric).toBeDefined();
  });

  test('містить всі ключі вкладок', () => {
    expect(uk.tabSearch).toBeDefined();
    expect(uk.tabList).toBeDefined();
    expect(uk.tabArchives).toBeDefined();
    expect(uk.tabAdmin).toBeDefined();
  });

  test('містить всі загальні ключі', () => {
    expect(uk.yes).toBeDefined();
    expect(uk.no).toBeDefined();
    expect(uk.ok).toBeDefined();
    expect(uk.delete).toBeDefined();
    expect(uk.save).toBeDefined();
    expect(uk.close).toBeDefined();
    expect(uk.cancel).toBeDefined();
    expect(uk.confirm).toBeDefined();
    expect(uk.back).toBeDefined();
    expect(uk.noData).toBeDefined();
    expect(uk.refresh).toBeDefined();
    expect(uk.warning).toBeDefined();
    expect(uk.success).toBeDefined();
    expect(uk.error).toBeDefined();
  });

  test('всі значення є непорожніми рядками', () => {
    const entries = Object.entries(uk);
    for (const [key, value] of entries) {
      expect(typeof value).toBe('string');
      expect(value.length).toBeGreaterThan(0);
    }
  });

  test('ключове слово видалення відповідає українській', () => {
    expect(uk.clearAllDataKeyword).toBe('ВИДАЛИТИ ВСЕ');
  });

  test('містить щонайменше 80 ключів локалізації', () => {
    const count = Object.keys(uk).length;
    expect(count).toBeGreaterThanOrEqual(80);
  });
});

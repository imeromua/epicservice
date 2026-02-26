import type { SQLiteDatabase } from 'expo-sqlite';
import { createTables } from './schema';

const CURRENT_VERSION = 1;

export async function runMigrations(db: SQLiteDatabase): Promise<void> {
  await createTables(db);

  const result = await db.getFirstAsync<{ value: string } | null>(
    "SELECT value FROM sync_meta WHERE key = 'db_version'",
  );

  const currentVersion = result ? parseInt(result.value, 10) : 0;

  if (currentVersion < CURRENT_VERSION) {
    // Future migrations go here
    // if (currentVersion < 2) { ... }

    await db.runAsync(
      "INSERT OR REPLACE INTO sync_meta (key, value) VALUES ('db_version', ?)",
      CURRENT_VERSION.toString(),
    );
  }
}

# debug_archives.py
import os
from config import ARCHIVES_PATH, BASE_DIR

print(f"BASE_DIR: {BASE_DIR}")
print(f"ARCHIVES_PATH: {ARCHIVES_PATH}")
print(f"Існує ARCHIVES_PATH: {os.path.exists(ARCHIVES_PATH)}")
print(f"Абсолютний шлях: {os.path.abspath(ARCHIVES_PATH)}")

active_dir = os.path.join(ARCHIVES_PATH, "active")
trash_dir = os.path.join(ARCHIVES_PATH, "trash")

print(f"\nACTIVE_DIR: {active_dir}")
print(f"Існує: {os.path.exists(active_dir)}")
print(f"Права доступу: {oct(os.stat(active_dir).st_mode) if os.path.exists(active_dir) else 'N/A'}")

print(f"\nTRASH_DIR: {trash_dir}")
print(f"Існує: {os.path.exists(trash_dir)}")

# Спроба створити тестовий файл
test_file = os.path.join(active_dir, "test.txt")
try:
    with open(test_file, "w") as f:
        f.write("test")
    print(f"\n✅ Успішно створено тестовий файл: {test_file}")
    os.remove(test_file)
except Exception as e:
    print(f"\n❌ Помилка створення файлу: {e}")

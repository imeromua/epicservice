#!/usr/bin/env python3
"""
Генератор іконок для Android-додатку EpicService з вихідного зображення.
Використання: python3 make_app_icons.py epicenter.png
"""
import sys
import os
from PIL import Image

def make_icon(source_path, output_path, size, round_icon=False):
    """Створює іконку заданого розміру з вихідного зображення"""
    img = Image.open(source_path).convert("RGBA")
    
    # Обрізаємо до квадрата (центральна частина)
    w, h = img.size
    if w != h:
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
    
    # Resize з anti-aliasing
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Якщо потрібен круглий варіант — обрізаємо по колу
    if round_icon:
        mask = Image.new('L', (size, size), 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        draw.ellipse([0, 0, size-1, size-1], fill=255)
        
        result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        result.paste(img, (0, 0))
        result.putalpha(mask)
        img = result
    
    # Зберігаємо
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'PNG', optimize=True)
    print(f"✓ {output_path} ({size}x{size}px)")

def main():
    if len(sys.argv) < 2:
        print("Використання: python3 make_app_icons.py <шлях_до_epicenter.png>")
        sys.exit(1)
    
    source = sys.argv[1]
    if not os.path.isfile(source):
        print(f"Помилка: файл {source} не знайдено")
        sys.exit(1)
    
    # Базовий шлях до ресурсів Android
    base_res = os.path.expanduser("~/epicservice/android-app/android/app/src/main/res")
    
    # Розміри для різних density
    sizes = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    
    print(f"\n📦 Генерація іконок з {source}\n")
    
    for folder, size in sizes.items():
        folder_path = os.path.join(base_res, folder)
        
        # Квадратна іконка
        make_icon(source, os.path.join(folder_path, "ic_launcher.png"), size, round_icon=False)
        
        # Кругла іконка
        make_icon(source, os.path.join(folder_path, "ic_launcher_round.png"), size, round_icon=True)
    
    print(f"\n✅ Готово! Згенеровано {len(sizes) * 2} іконок")
    print("\nТепер можна збирати APK:")
    print("  cd ~/epicservice/android-app/android")
    print("  ./gradlew assembleDebug")

if __name__ == "__main__":
    main()

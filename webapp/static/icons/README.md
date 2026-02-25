# Іконки застосунку

Ця директорія містить PNG-іконки, які можуть використовуватись у фронтенді (наприклад, favicon/preview). Якщо у репозиторії залишилися файли з назвами `icon-192x192.png`, `icon-512x512.png` тощо — це просто набір зображень, а не обов’язково активна PWA-конфігурація.

## Генерація іконок

### Варіант 1: Онлайн генератори

- PWA Asset Generator: https://progressier.com/pwa-icons-and-ios-splash-screen-generator
- RealFaviconGenerator: https://realfavicongenerator.net/
- Favicon.io: https://favicon.io/

### Варіант 2: Python (PIL/Pillow)

```python
from PIL import Image

original = Image.open('logo.png')

sizes = [72, 96, 128, 144, 152, 192, 384, 512]

for size in sizes:
    resized = original.resize((size, size), Image.LANCZOS)
    resized.save(f'icon-{size}x{size}.png', 'PNG')
```

### Варіант 3: ImageMagick

```bash
# Установка: sudo apt install imagemagick

for size in 72 96 128 144 152 192 384 512; do
  convert logo.png -resize ${size}x${size} icon-${size}x${size}.png
done
```

## Рекомендації

- Формат: PNG (за потреби з прозорістю)
- Padding: 15–20% навколо логотипу
- Оригінал: бажано вектор (SVG) або PNG високої якості

---

"Зроблено в Україні з ❤️"

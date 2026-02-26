#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import os

print("🔧 Етап 2: Винесення JavaScript (правильно, з Jinja inline)")

# Читаємо index.html
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Витягуємо ВСЕ з великого <script> блоку в кінці
script_start = content.rfind('<script>\nconst tg = window.Telegram.WebApp;')
script_end = content.rfind('</script>\n</body>')

if script_start == -1 or script_end == -1:
    print("❌ Не знайдено основний JS блок!")
    exit(1)

js_content = content[script_start + 9:script_end]  # +9 щоб пропустити '<script>\n'
print(f"📦 Знайдено {len(js_content)} символів JavaScript")

# Розділяємо на inline (з Jinja) та exportable (без Jinja)
# Шукаємо секцію з Jinja templates
jinja_section_end = js_content.find('\nlet currentQuantity')

if jinja_section_end == -1:
    print("❌ Не знайдено розділ з Jinja!")
    exit(1)

inline_js = js_content[:jinja_section_end].strip()
export_js = js_content[jinja_section_end:].strip()

print(f"✅ Inline JS (з Jinja): {len(inline_js)} символів")
print(f"✅ Export JS (чистий): {len(export_js)} символів")

# Створюємо app.js
js_dir = '../static/js'
os.makedirs(js_dir, exist_ok=True)

js_file = os.path.join(js_dir, 'app.js')
with open(js_file, 'w', encoding='utf-8') as f:
    # Додаємо коментар та чистий JS
    f.write('// EpicService Main Application\n')
    f.write('// Auto-generated from index.html refactoring\n\n')
    f.write(export_js)

print(f"✅ JavaScript збережено в {js_file}")

# Оновлюємо HTML: залишаємо inline script + додаємо <script src>
new_inline_script = f'''<script>
{inline_js}
</script>
    <script src="/static/js/app.js"></script>
'''

# Замінюємо старий блок
new_content = content[:script_start] + new_inline_script + content[script_end:]

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"✅ index.html оновлено")
print(f"📉 Розмір: {len(content)} → {len(new_content)} ({len(content) - len(new_content)} символів менше)")

# Git операції
os.chdir('../..')
os.system('git add webapp/static/js/app.js')
os.system('git add webapp/templates/index.html')
os.system('git commit -m "refactor(step2): extract JS to app.js (keep Jinja inline)"')
os.system('git push')

print("\n🎉 Етап 2 завершено!")
print("📱 ТЕСТУЙ В ЖИВУ:")
print("   - Відкрий мініапп")
print("   - Перевір ВСІ функції")
print("   - Перевір адмінку")
print("   - Перевір що Telegram init працює")


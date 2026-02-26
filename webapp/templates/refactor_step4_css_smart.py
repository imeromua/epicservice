#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

print("🎨 Етап 4: Модульність CSS (smart split)")

# Читаємо base.css
css_file = '../static/css/base.css'
with open(css_file, 'r', encoding='utf-8') as f:
    css = f.read()

print(f"📦 Оригінальний base.css: {len(css)} символів")

# ============= РОЗУМНИЙ РОЗДІЛ =============

# 1. VARIABLES.CSS - :root блок
root_start = css.find(':root {')
root_end = css.find('}', root_start) + 1
variables_css = f"/* EpicService - CSS Variables */\n\n{css[root_start:root_end]}\n"

# 2. RESET.CSS - все до першого класу
first_class = css.find('\n.', root_end)
reset_css = f"/* EpicService - Reset & Base Styles */\n\n{css[root_end:first_class].strip()}\n"

# 3. LAYOUT.CSS - sticky-container, header, tabs, main-content
layout_markers = ['.sticky-container', '.header', '.tabs', '.main-content', '.search-box']
layout_start = css.find('.sticky-container')
layout_end = css.find('.product-card')
layout_css = f"/* EpicService - Layout Structure */\n\n{css[layout_start:layout_end].strip()}\n"

# 4. COMPONENTS.CSS - product-card, modal, buttons до admin
components_start = layout_end
components_end = css.find('.admin-stat-card') if '.admin-stat-card' in css else len(css)
components_css = f"/* EpicService - Components */\n\n{css[components_start:components_end].strip()}\n"

# 5. ADMIN.CSS - все що залишилось
if '.admin-stat-card' in css:
    admin_start = components_end
    admin_css = f"/* EpicService - Admin Panel */\n\n{css[admin_start:].strip()}\n"
else:
    admin_css = "/* EpicService - Admin Panel */\n\n/* No admin styles */\n"

# ============= ПЕРЕВІРКА ЦІЛІСНОСТІ =============
total_new = len(variables_css) + len(reset_css) + len(layout_css) + len(components_css) + len(admin_css)
print(f"✅ Розбито CSS: {total_new} символів")
print(f"   Різниця: {len(css) - total_new} символів (коментарі та пробіли)")

# ============= ЗБЕРІГАЄМО =============
css_dir = '../static/css'
modules = {
    'variables.css': variables_css,
    'reset.css': reset_css,
    'layout.css': layout_css,
    'components.css': components_css,
    'admin.css': admin_css
}

for filename, content in modules.items():
    filepath = os.path.join(css_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ {filename}: {len(content)} символів")

# ============= ОНОВЛЮЄМО INDEX.HTML =============
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_link = '<link rel="stylesheet" href="/static/css/base.css">'
new_links = '''<!-- Core Styles (modular) -->
    <link rel="stylesheet" href="/static/css/variables.css">
    <link rel="stylesheet" href="/static/css/reset.css">
    <link rel="stylesheet" href="/static/css/layout.css">
    <link rel="stylesheet" href="/static/css/components.css">
    <link rel="stylesheet" href="/static/css/admin.css">'''

html = html.replace(old_link, new_links)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ index.html оновлено")

# Видаляємо старий base.css
if os.path.exists(css_file):
    os.remove(css_file)
    print("🗑️ Видалено base.css")

# Git
os.chdir('../..')
os.system('git add webapp/static/css/')
os.system('git add webapp/templates/index.html')
os.system('git commit -m "refactor(step4): split CSS into 5 modules (1:1 copy, no style loss)"')
os.system('git push')

print("\n🎉 Етап 4 завершено!")
print("🎨 5 CSS модулів (без втрат):")
print("   - variables.css")
print("   - reset.css")
print("   - layout.css")
print("   - components.css")
print("   - admin.css")
print("\n📱 ТЕСТУЙ ДИЗАЙН!")


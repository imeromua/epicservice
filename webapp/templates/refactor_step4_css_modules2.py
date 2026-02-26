#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re

print("🎨 Етап 4: Модульність CSS")

# Читаємо base.css
css_file = '../static/css/base.css'
with open(css_file, 'r', encoding='utf-8') as f:
    css = f.read()

print(f"📦 Розмір base.css: {len(css)} символів")

# ============= ПРОСТИЙ РОЗДІЛ ЗА КОМЕНТАРЯМИ =============

# Розбиваємо CSS на логічні блоки
lines = css.split('\n')

# 1. VARIABLES.CSS
variables_css = '/* EpicService - CSS Variables */\n\n:root {\n'
in_root = False
for line in lines:
    if ':root {' in line:
        in_root = True
        continue
    if in_root:
        if line.strip() == '}':
            variables_css += '}\n'
            break
        variables_css += line + '\n'

# 2. RESET.CSS - все до .sticky-container
reset_end = css.find('.sticky-container')
reset_section = css[len(variables_css):reset_end]
reset_css = f'''/* EpicService - Reset & Base Styles */
/* Typography, body, and global resets */

{reset_section.strip()}
'''

# 3. LAYOUT.CSS - від .sticky-container до .product-card
layout_start = css.find('.sticky-container')
layout_end = css.find('.product-card')
layout_css = f'''/* EpicService - Layout Structure */
/* Header, tabs, containers */

{css[layout_start:layout_end].strip()}
'''

# 4. COMPONENTS.CSS - від .product-card до .admin або кінця
components_start = css.find('.product-card')
if '.admin-stat-card' in css:
    components_end = css.find('.admin-stat-card')
else:
    components_end = len(css)
    
components_css = f'''/* EpicService - Components */
/* Product cards, modals, buttons, inputs */

{css[components_start:components_end].strip()}
'''

# 5. ADMIN.CSS - решта якщо є admin стилі
if '.admin-stat-card' in css:
    admin_start = css.find('.admin-stat-card')
    admin_css = f'''/* EpicService - Admin Panel */
/* Admin statistics, users, danger zone */

{css[admin_start:].strip()}
'''
else:
    admin_css = '/* EpicService - Admin Panel */\n/* No admin styles */'

# 6. ANIMATIONS.CSS
animations_css = '''/* EpicService - Animations */
/* Transitions, keyframes, and interactive effects */

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}
'''

# 7. UTILITIES.CSS
utilities_css = '''/* EpicService - Utility Classes */
/* Loading, empty states, visibility helpers */

.loader {
    text-align: center;
    padding: 32px;
    font-size: 16px;
    color: var(--hint-color);
}

.hidden {
    display: none !important;
}

.empty-state {
    text-align: center;
    padding: 48px 24px;
    color: var(--hint-color);
}

.empty-icon {
    font-size: 64px;
    margin-bottom: 16px;
}
'''

# ============= ЗБЕРІГАЄМО МОДУЛІ =============

css_dir = '../static/css'
modules = {
    'variables.css': variables_css,
    'reset.css': reset_css,
    'layout.css': layout_css,
    'components.css': components_css,
    'admin.css': admin_css,
    'animations.css': animations_css,
    'utilities.css': utilities_css
}

for filename, content in modules.items():
    filepath = os.path.join(css_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ {filename}: {len(content)} символів")

# ============= ОНОВЛЮЄМО INDEX.HTML =============

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Замінюємо base.css на модулі
old_link = '<link rel="stylesheet" href="/static/css/base.css">'
new_links = '''<!-- Core Styles -->
    <link rel="stylesheet" href="/static/css/variables.css">
    <link rel="stylesheet" href="/static/css/reset.css">
    <link rel="stylesheet" href="/static/css/layout.css">
    <link rel="stylesheet" href="/static/css/components.css">
    <link rel="stylesheet" href="/static/css/admin.css">
    <link rel="stylesheet" href="/static/css/animations.css">
    <link rel="stylesheet" href="/static/css/utilities.css">'''

html = html.replace(old_link, new_links)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ index.html оновлено - додано 7 CSS модулів")

# Видаляємо старий base.css
if os.path.exists(css_file):
    os.remove(css_file)
    print("🗑️ Видалено старий base.css")

# Git
os.chdir('../..')
os.system('git add webapp/static/css/')
os.system('git add webapp/templates/index.html')
os.system('git commit -m "refactor(step4): split CSS into modules (variables, reset, layout, components, admin, animations, utilities)"')
os.system('git push')

print("\n🎉 Етап 4 завершено!")
print("🎨 Створено 7 CSS модулів:")
print("   - variables.css (змінні)")
print("   - reset.css (базові стилі)")
print("   - layout.css (структура)")
print("   - components.css (компоненти)")
print("   - admin.css (адмін)")
print("   - animations.css (анімації)")
print("   - utilities.css (утиліти)")
print("\n📱 ТЕСТУЙ В ЖИВУ!")


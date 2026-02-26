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

# ============= АНАЛІЗ І РОЗДІЛЕННЯ =============

# 1. VARIABLES.CSS - CSS змінні (root)
variables_match = re.search(r':root \{[^}]+\}', css, re.DOTALL)
variables_css = f'''/* EpicService - CSS Variables */
/* Theme colors and spacing */

{variables_match.group(0) if variables_match else ''}
'''

# 2. RESET.CSS - базові стилі (body, *, html)
reset_section = css.split('.sticky-container')[0]
reset_css = f'''/* EpicService - Reset & Base Styles */
/* Typography, body, and global resets */

{reset_section.replace(variables_match.group(0), '').strip() if variables_match else reset_section}
'''

# 3. LAYOUT.CSS - структура (sticky-container, main-content, tabs)
layout_start = css.find('.sticky-container')
layout_end = css.find('.product-card')
layout_section = css[layout_start:layout_end]
layout_css = f'''/* EpicService - Layout Structure */
/* Header, tabs, containers */

{layout_section}
'''

# 4. COMPONENTS.CSS - картки товарів, модалі, кнопки
components_start = css.find('.product-card')
components_end = css.find('.admin-stat-card') if '.admin-stat-card' in css else len(css)
components_section = css[components_start:components_end]
components_css = f'''/* EpicService - Components */
/* Product cards, modals, buttons, inputs */

{components_section}
'''

# 5. ADMIN.CSS - адмін панель
if '.admin-stat-card' in css:
    admin_start = css.find('.admin-stat-card')
    admin_end = css.find('.danger-zone') + len(css[css.find('.danger-zone'):].split('}')[10])
    admin_section = css[admin_start:admin_end]
    admin_css = f'''/* EpicService - Admin Panel */
/* Admin statistics, users, danger zone */

{admin_section}
'''
else:
    admin_css = '/* No admin styles found */'

# 6. ANIMATIONS.CSS - анімації та transitions
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

# 7. UTILITIES.CSS - утиліти (loader, empty-state, hidden)
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


#!/usr/bin/env python3
"""
Скрипт для автоматичного додавання PWA коду в index.html

Використання:
    python webapp/update-html.py
"""

import re
from pathlib import Path

# Шляхи до файлів
HTML_FILE = Path('webapp/templates/index.html')
PATCH_FILE = Path('webapp/templates/pwa-patch.html')
BACKUP_FILE = Path('webapp/templates/index.html.pwa-backup')


def read_file(filepath):
    """Reads file content"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(filepath, content):
    """Writes content to file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def extract_sections(patch_content):
    """Extracts HEAD and BODY sections from patch file"""
    # Extract HEAD section
    head_match = re.search(
        r'<!-- ========== Додати в <head> секцію ==========.*?-->(.*?)<!-- ========== Додати перед',
        patch_content,
        re.DOTALL
    )
    
    # Extract BODY section
    body_match = re.search(
        r'<!-- ========== Додати перед закриваючим </body> ==========.*?-->(.*?)$',
        patch_content,
        re.DOTALL
    )
    
    head_code = head_match.group(1).strip() if head_match else ''
    body_code = body_match.group(1).strip() if body_match else ''
    
    return head_code, body_code


def update_html(html_content, head_code, body_code):
    """Updates HTML with PWA code"""
    
    # Check if PWA code already exists
    if 'PWA Meta Tags' in html_content:
        print('⚠️  PWA code already exists in index.html')
        return html_content, False
    
    # Add HEAD section (before </head>)
    head_insertion = f'\n\n{head_code}\n'
    html_content = html_content.replace('</head>', f'{head_insertion}</head>')
    
    # Add BODY section (before </body>)
    body_insertion = f'\n\n{body_code}\n'
    html_content = html_content.replace('</body>', f'{body_insertion}</body>')
    
    return html_content, True


def main():
    print('🚀 PWA HTML Updater')
    print('=' * 50)
    
    # Check files existence
    if not HTML_FILE.exists():
        print(f'❌ Error: {HTML_FILE} not found')
        return
    
    if not PATCH_FILE.exists():
        print(f'❌ Error: {PATCH_FILE} not found')
        return
    
    # Read files
    print(f'📄 Reading {HTML_FILE}...')
    html_content = read_file(HTML_FILE)
    
    print(f'📄 Reading {PATCH_FILE}...')
    patch_content = read_file(PATCH_FILE)
    
    # Extract sections
    print('🔍 Extracting PWA code sections...')
    head_code, body_code = extract_sections(patch_content)
    
    if not head_code or not body_code:
        print('❌ Error: Could not extract PWA sections from patch file')
        return
    
    # Create backup
    print(f'💾 Creating backup: {BACKUP_FILE}...')
    write_file(BACKUP_FILE, html_content)
    
    # Update HTML
    print('⚙️ Updating index.html...')
    updated_html, was_modified = update_html(html_content, head_code, body_code)
    
    if not was_modified:
        print('✅ No changes needed - PWA code already present')
        return
    
    # Write updated HTML
    print(f'✅ Writing updated {HTML_FILE}...')
    write_file(HTML_FILE, updated_html)
    
    print('\n✅ Success! PWA code has been added to index.html')
    print(f'\n💾 Backup saved to: {BACKUP_FILE}')
    print('\n👀 Next steps:')
    print('  1. Створіть іконки (webapp/static/icons/README.md)')
    print('  2. Перезапустіть сервер')
    print('  3. Відкрийте сайт на телефоні та встановіть PWA')
    print('=' * 50)


if __name__ == '__main__':
    main()

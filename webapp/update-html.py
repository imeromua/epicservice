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
    
    # Extract HEAD section - all content between head markers
    head_pattern = r'<!-- ========== Додати в <head>.*?========== -->\s*\n(.+?)\n\s*<!-- ========== Додати перед'
    head_match = re.search(head_pattern, patch_content, re.DOTALL)
    
    # Extract BODY section - all content between body markers and end of file
    body_pattern = r'<!-- ========== Додати перед закриваючим </body>.*?========== -->\s*\n(.+)$'
    body_match = re.search(body_pattern, patch_content, re.DOTALL)
    
    if head_match:
        head_code = head_match.group(1).strip()
        print(f'✅ HEAD section extracted ({len(head_code)} chars)')
    else:
        head_code = ''
        print('⚠️  HEAD section not found')
    
    if body_match:
        body_code = body_match.group(1).strip()
        print(f'✅ BODY section extracted ({len(body_code)} chars)')
    else:
        body_code = ''
        print('⚠️  BODY section not found')
    
    return head_code, body_code


def update_html(html_content, head_code, body_code):
    """Updates HTML with PWA code"""
    
    # Check if PWA code already exists
    if 'PWA Meta Tags' in html_content or 'pwa-redirect.js' in html_content:
        print('⚠️  PWA code already exists in index.html')
        return html_content, False
    
    # Find where to insert HEAD code (before closing </head>)
    # Insert before telegram-web-app.js or before </head>
    if '<script src="https://telegram.org/js/telegram-web-app.js"></script>' in html_content:
        # Insert before telegram script
        head_insertion = f'\n    {head_code}\n    '
        html_content = html_content.replace(
            '<script src="https://telegram.org/js/telegram-web-app.js"></script>',
            f'{head_insertion}<script src="https://telegram.org/js/telegram-web-app.js"></script>'
        )
        print('✅ HEAD code inserted before telegram-web-app.js')
    else:
        # Fallback: insert before </head>
        head_insertion = f'\n    {head_code}\n'
        html_content = html_content.replace('</head>', f'{head_insertion}</head>')
        print('✅ HEAD code inserted before </head>')
    
    # Add BODY section (before </body>)
    body_insertion = f'\n{body_code}\n'
    html_content = html_content.replace('</body>', f'{body_insertion}</body>')
    print('✅ BODY code inserted before </body>')
    
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
    print(f'   Size: {len(html_content)} bytes')
    
    print(f'📄 Reading {PATCH_FILE}...')
    patch_content = read_file(PATCH_FILE)
    print(f'   Size: {len(patch_content)} bytes')
    
    # Extract sections
    print('🔍 Extracting PWA code sections...')
    head_code, body_code = extract_sections(patch_content)
    
    if not head_code and not body_code:
        print('❌ Error: Could not extract PWA sections from patch file')
        print('\nDebug info:')
        print(f'Patch file first 500 chars:\n{patch_content[:500]}')
        return
    
    if not head_code:
        print('⚠️  Warning: HEAD section is empty')
    
    if not body_code:
        print('⚠️  Warning: BODY section is empty')
    
    # Create backup
    print(f'💾 Creating backup: {BACKUP_FILE}...')
    write_file(BACKUP_FILE, html_content)
    print(f'   Backup size: {len(html_content)} bytes')
    
    # Update HTML
    print('⚙️  Updating index.html...')
    updated_html, was_modified = update_html(html_content, head_code, body_code)
    
    if not was_modified:
        print('✅ No changes needed - PWA code already present')
        print('\nTo force update, remove existing PWA code from index.html')
        return
    
    # Write updated HTML
    print(f'💾 Writing updated {HTML_FILE}...')
    write_file(HTML_FILE, updated_html)
    print(f'   New size: {len(updated_html)} bytes')
    print(f'   Difference: +{len(updated_html) - len(html_content)} bytes')
    
    print('\n' + '=' * 50)
    print('✅ Success! PWA code has been added to index.html')
    print('=' * 50)
    print(f'\n💾 Backup saved to: {BACKUP_FILE}')
    print('\n👀 Next steps:')
    print('  1. Створіть іконки (webapp/static/icons/README.md)')
    print('  2. Оновіть посилання на бот у manifest.json')
    print('  3. Перезапустіть сервер')
    print('  4. Відкрийте сайт на телефоні та встановіть PWA')
    print('\n📖 Докладніше: webapp/PWA_USAGE.md')
    print('=' * 50)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'\n❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()

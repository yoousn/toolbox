import os
import re

qml_dir = r'd:\Desktop\合成\工具箱\qml\pages'

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # If ModernButton is loaded from ../components
    if 'import "../components"' not in content:
        content = content.replace('import QtQuick.Controls', 'import QtQuick.Controls\nimport "../components"')
    
    # We want to replace Button { with ModernButton {
    content = re.sub(r'(\n\s*)Button\s*\{', r'\1ModernButton {', content)
    
    # We also have custom visual blocks like:
    content = re.sub(r'(?s)background:\s*Rectangle\s*\{[^}]*\}', '', content)
    content = re.sub(r'(?s)contentItem:\s*Label\s*\{[^}]*\}', '', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for f in os.listdir(qml_dir):
    if f.endswith('.qml'):
        process_file(os.path.join(qml_dir, f))
print('Done!')

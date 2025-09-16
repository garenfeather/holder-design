#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from pathlib import Path

# emoji替换映射
emoji_replacements = {
    '🚀': '[START]',
    '📡': '[INFO]',
    '🏠': '[INFO]',
    '💊': '[INFO]',
    '🔧': '[CONFIG]',
    '🛑': '[STOP]',
    '❌': '[ERROR]',
    '✅': '[SUCCESS]',
    '⚠️': '[WARNING]',
    '🔍': '[SEARCH]',
    '🔄': '[PROCESS]',
    '💾': '[SAVE]',
    '📁': '[FILE]',
    '📊': '[DATA]',
    '🎯': '[TARGET]',
    '✨': '[FEATURE]',
    '🎨': '[DESIGN]',
    '🗃️': '[STORAGE]',
    '📄': '[DOCUMENT]',
    '🗂️': '[FOLDER]',
    '🎮': '[GAME]',
    '🎪': '[CIRCUS]',
    '🌟': '[STAR]',
    '⭐': '[STAR]',
    '🎉': '[CELEBRATE]',
    '🎊': '[PARTY]',
    '🎈': '[BALLOON]',
    '✂️': '[CUT]',
    '⏭️': '[SKIP]',
    '1️⃣': '[STEP1]',
    '2️⃣': '[STEP2]',
    '3️⃣': '[STEP3]',
    '4️⃣': '[STEP4]',
    '📺': '[SCREEN]',
    '🖥️': '[MONITOR]',
    '⚡': '[FAST]',
    '🔥': '[HOT]',
    '💡': '[IDEA]',
    '🎭': '[MASK]',
    '🎪': '[SHOW]',
    '🏆': '[TROPHY]',
    '🎖️': '[MEDAL]',
    '🎁': '[GIFT]',
    '🎀': '[BOW]',
    '🌈': '[RAINBOW]',
    '☀️': '[SUN]',
    '🌙': '[MOON]',
    '⭐': '[STAR]',
    '💫': '[SPARKLE]',
    '🌟': '[SHINE]',
    '✨': '[GLITTER]',
}

def fix_file_encoding(file_path):
    """修复单个文件的编码问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 添加编码设置到文件开头
        lines = content.split('\n')
        if not lines[0].startswith('#!'):
            # 没有shebang，添加编码声明
            if '# -*- coding: utf-8 -*-' not in lines[0]:
                lines.insert(0, '# -*- coding: utf-8 -*-')
        else:
            # 有shebang，检查第二行
            if len(lines) < 2 or '# -*- coding: utf-8 -*-' not in lines[1]:
                lines.insert(1, '# -*- coding: utf-8 -*-')
                # 添加环境变量设置
                lines.insert(2, '')
                lines.insert(3, 'import os')
                lines.insert(4, 'os.environ["PYTHONIOENCODING"] = "utf-8"')

        # 替换emoji字符
        content = '\n'.join(lines)
        for emoji, replacement in emoji_replacements.items():
            content = content.replace(emoji, replacement)

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[SUCCESS] 修复文件: {file_path}")
        return True

    except Exception as e:
        print(f"[ERROR] 修复文件失败 {file_path}: {e}")
        return False

def main():
    backend_dir = Path('backend')

    if not backend_dir.exists():
        print("[ERROR] backend目录不存在")
        return

    # 处理所有Python文件
    python_files = list(backend_dir.glob('*.py'))
    python_files.extend(list(backend_dir.glob('**/*.py')))

    success_count = 0
    for py_file in python_files:
        if fix_file_encoding(py_file):
            success_count += 1

    print(f"\n[SUMMARY] 处理完成: {success_count}/{len(python_files)} 个文件成功")

if __name__ == '__main__':
    main()
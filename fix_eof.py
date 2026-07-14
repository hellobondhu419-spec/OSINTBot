#!/usr/bin/env python3
import sys
sys.path.insert(0, '/usr/bin')

with open('osint_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Add sys import if not present
if 'import sys' not in ''.join(lines[:15]):
    for i, line in enumerate(lines):
        if line.startswith('import'):
            lines.insert(i, 'import sys\n')
            break

# Find and replace await self.tg.start() calls with try-except wrapper
new_lines = []
for i, line in enumerate(lines):
    if 'await self.tg.start()' in line:
        indent = len(line) - len(line.lstrip())
        new_lines.append(' ' * indent + 'try:\n')
        new_lines.append(' ' * (indent + 4) + 'await self.tg.start()\n')
        new_lines.append(' ' * indent + 'except EOFError:\n')
        new_lines.append(' ' * (indent + 4) + 'if not sys.stdin.isatty():\n')
        new_lines.append(' ' * (indent + 8) + 'logger.warning("EOF in container (expected)")\n')
        new_lines.append(' ' * (indent + 8) + 'pass\n')
        new_lines.append(' ' * indent + 'except Exception as e:\n')
        new_lines.append(' ' * (indent + 4) + 'logger.error(f"TG start error: {e}")\n')
    else:
        new_lines.append(line)

with open('osint_bot.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Fixed EOF handling")

"""
تحلیل حجم پکیج‌های نصب شده در .venv
"""

import os
from pathlib import Path
from collections import defaultdict

VENV_DIR = Path('.venv')
SITE_PACKAGES = VENV_DIR / 'Lib' / 'site-packages'

def get_dir_size(path):
    """محاسبه حجم یک پوشه"""
    total = 0
    try:
        for item in path.rglob('*'):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total

def format_size(size):
    """تبدیل بایت به فرمت خوانا"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def main():
    if not SITE_PACKAGES.exists():
        print("پوشه site-packages پیدا نشد!")
        return
    
    print("=" * 60)
    print("تحلیل حجم پکیج‌های نصب شده")
    print("=" * 60)
    
    package_sizes = {}
    
    for item in SITE_PACKAGES.iterdir():
        if item.is_dir():
            size = get_dir_size(item)
            if size > 0:
                package_sizes[item.name] = size
    
    # مرتب‌سازی بر اساس حجم
    sorted_packages = sorted(package_sizes.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\nتعداد پکیج‌ها: {len(sorted_packages)}")
    print(f"\n10 پکیج بزرگ:\n")
    
    total_size = sum(package_sizes.values())
    top_10_size = 0
    
    for i, (name, size) in enumerate(sorted_packages[:10], 1):
        percentage = (size / total_size) * 100
        top_10_size += size
        print(f"{i:2d}. {name:40s} {format_size(size):>12s} ({percentage:5.2f}%)")
    
    print(f"\nحجم کل 10 پکیج بزرگ: {format_size(top_10_size)}")
    print(f"حجم کل همه پکیج‌ها: {format_size(total_size)}")
    print(f"\nدرصد حجم 10 پکیج بزرگ: {(top_10_size / total_size * 100):.2f}%")

if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    main()


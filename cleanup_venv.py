"""
اسکریپت پاکسازی محیط مجازی Python
این اسکریپت فایل‌های غیرضروری را از .venv حذف می‌کند تا حجم کاهش یابد
"""

import os
import sys
import shutil
from pathlib import Path

# تنظیم encoding برای Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

VENV_DIR = Path('.venv')

def get_size(path):
    """محاسبه حجم فایل یا پوشه"""
    if path.is_file():
        return path.stat().st_size
    total = 0
    try:
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
    except (PermissionError, OSError):
        pass
    return total

def format_size(size):
    """تبدیل بایت به فرمت خوانا"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def delete_files(pattern, description):
    """حذف فایل‌های مطابق با الگو"""
    deleted_count = 0
    deleted_size = 0
    
    for file_path in VENV_DIR.rglob(pattern):
        try:
            if file_path.is_file():
                size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                deleted_size += size
        except (PermissionError, OSError) as e:
            print(f"  ⚠ خطا در حذف {file_path}: {e}")
    
    if deleted_count > 0:
        print(f"  ✓ {description}: {deleted_count} فایل ({format_size(deleted_size)}) حذف شد")
        return deleted_size
    return 0

def delete_dirs(dir_name, description):
    """حذف پوشه‌های مطابق با نام"""
    deleted_count = 0
    deleted_size = 0
    
    for dir_path in VENV_DIR.rglob(dir_name):
        try:
            if dir_path.is_dir():
                size = get_size(dir_path)
                shutil.rmtree(dir_path)
                deleted_count += 1
                deleted_size += size
        except (PermissionError, OSError) as e:
            print(f"  ⚠ خطا در حذف {dir_path}: {e}")
    
    if deleted_count > 0:
        print(f"  ✓ {description}: {deleted_count} پوشه ({format_size(deleted_size)}) حذف شد")
        return deleted_size
    return 0

def main():
    """تابع اصلی پاکسازی"""
    print("=" * 60)
    print("پاکسازی محیط مجازی Python (.venv)")
    print("=" * 60)
    
    if not VENV_DIR.exists():
        print(f"✗ پوشه {VENV_DIR} پیدا نشد!")
        return
    
    # محاسبه حجم اولیه
    print("\n=== محاسبه حجم اولیه ===")
    initial_size = get_size(VENV_DIR)
    print(f"حجم اولیه: {format_size(initial_size)}")
    
    print("\n=== شروع پاکسازی ===")
    total_deleted = 0
    
    # 1. حذف فایل‌های __pycache__
    total_deleted += delete_dirs('__pycache__', '__pycache__')
    
    # 2. حذف فایل‌های .pyc
    total_deleted += delete_files('*.pyc', 'فایل‌های .pyc')
    
    # 3. حذف فایل‌های .pyo
    total_deleted += delete_files('*.pyo', 'فایل‌های .pyo')
    
    # 4. حذف فایل‌های .pyd (فایل‌های compiled Python در Windows)
    # این را حذف نمی‌کنیم چون ممکن است ضروری باشند
    
    # 5. حذف پوشه‌های test
    total_deleted += delete_dirs('tests', 'پوشه‌های tests')
    total_deleted += delete_dirs('test', 'پوشه‌های test')
    
    # 6. حذف فایل‌های documentation
    total_deleted += delete_dirs('docs', 'پوشه‌های docs')
    total_deleted += delete_dirs('doc', 'پوشه‌های doc')
    
    # 7. حذف فایل‌های .html documentation
    total_deleted += delete_files('*.html', 'فایل‌های HTML documentation')
    
    # 8. حذف پوشه‌های __pycache__ در site-packages
    site_packages = VENV_DIR / 'Lib' / 'site-packages'
    if site_packages.exists():
        for item in site_packages.iterdir():
            if item.is_dir():
                cache_dir = item / '__pycache__'
                if cache_dir.exists():
                    try:
                        size = get_size(cache_dir)
                        shutil.rmtree(cache_dir)
                        total_deleted += size
                    except (PermissionError, OSError):
                        pass
    
    # 9. حذف فایل‌های .dist-info غیرضروری (فقط metadata، نه خود پکیج)
    # این را حذف نمی‌کنیم چون pip به آن نیاز دارد
    
    # 10. حذف فایل‌های .egg-info
    total_deleted += delete_dirs('*.egg-info', 'پوشه‌های .egg-info')
    
    # 11. حذف پوشه‌های build
    total_deleted += delete_dirs('build', 'پوشه‌های build')
    
    # 12. حذف پوشه‌های .git (اگر وجود دارد)
    total_deleted += delete_dirs('.git', 'پوشه‌های .git')
    
    # 13. حذف فایل‌های .pyc در پوشه‌های مختلف
    for pyc_file in VENV_DIR.rglob('*.pyc'):
        try:
            if pyc_file.is_file():
                size = pyc_file.stat().st_size
                pyc_file.unlink()
                total_deleted += size
        except (PermissionError, OSError):
            pass
    
    # 14. حذف فایل‌های .cache
    cache_dirs = [
        VENV_DIR / 'Lib' / 'site-packages' / 'pip' / '_internal' / 'cache',
        VENV_DIR / 'Lib' / 'site-packages' / 'pip' / 'cache',
    ]
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            try:
                size = get_size(cache_dir)
                shutil.rmtree(cache_dir)
                total_deleted += size
                print(f"  ✓ Cache pip: {format_size(size)} حذف شد")
            except (PermissionError, OSError):
                pass
    
    # محاسبه حجم نهایی
    print("\n=== محاسبه حجم نهایی ===")
    final_size = get_size(VENV_DIR)
    saved_size = initial_size - final_size
    
    print(f"حجم اولیه: {format_size(initial_size)}")
    print(f"حجم نهایی: {format_size(final_size)}")
    print(f"حجم آزاد شده: {format_size(saved_size)}")
    print(f"درصد کاهش: {(saved_size / initial_size * 100):.2f}%")
    
    print("\n" + "=" * 60)
    print("✓ پاکسازی با موفقیت انجام شد!")
    print("=" * 60)

if __name__ == '__main__':
    main()


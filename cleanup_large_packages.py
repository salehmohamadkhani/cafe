"""
حذف فایل‌های غیرضروری از پکیج‌های بزرگ
"""

import os
import shutil
from pathlib import Path

VENV_DIR = Path('.venv')
SITE_PACKAGES = VENV_DIR / 'Lib' / 'site-packages'

def get_size(path):
    """محاسبه حجم"""
    if path.is_file():
        return path.stat().st_size
    total = 0
    try:
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
    except:
        pass
    return total

def format_size(size):
    """تبدیل به فرمت خوانا"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def cleanup_package(package_name, description=""):
    """پاکسازی یک پکیج خاص"""
    package_dir = SITE_PACKAGES / package_name
    if not package_dir.exists():
        return 0
    
    total_deleted = 0
    
    # حذف پوشه‌های test
    for test_dir in ['test', 'tests', 'testing', '__tests__']:
        test_path = package_dir / test_dir
        if test_path.exists():
            try:
                size = get_size(test_path)
                shutil.rmtree(test_path)
                total_deleted += size
                print(f"    ✓ {test_dir} حذف شد ({format_size(size)})")
            except:
                pass
    
    # حذف پوشه‌های doc
    for doc_dir in ['doc', 'docs', 'documentation']:
        doc_path = package_dir / doc_dir
        if doc_path.exists():
            try:
                size = get_size(doc_path)
                shutil.rmtree(doc_path)
                total_deleted += size
                print(f"    ✓ {doc_dir} حذف شد ({format_size(size)})")
            except:
                pass
    
    # حذف فایل‌های .pyc و __pycache__
    for pyc_file in package_dir.rglob('*.pyc'):
        try:
            if pyc_file.is_file():
                total_deleted += pyc_file.stat().st_size
                pyc_file.unlink()
        except:
            pass
    
    for cache_dir in package_dir.rglob('__pycache__'):
        try:
            if cache_dir.is_dir():
                size = get_size(cache_dir)
                shutil.rmtree(cache_dir)
                total_deleted += size
        except:
            pass
    
    # حذف فایل‌های .html و .md documentation
    for html_file in package_dir.rglob('*.html'):
        try:
            if html_file.is_file():
                total_deleted += html_file.stat().st_size
                html_file.unlink()
        except:
            pass
    
    # حذف فایل‌های README و LICENSE (اگر خیلی بزرگ هستند)
    for readme in package_dir.glob('README*'):
        try:
            if readme.is_file() and readme.stat().st_size > 100 * 1024:  # بیشتر از 100KB
                total_deleted += readme.stat().st_size
                readme.unlink()
        except:
            pass
    
    return total_deleted

def main():
    """تابع اصلی"""
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("پاکسازی پکیج‌های بزرگ")
    print("=" * 60)
    
    if not SITE_PACKAGES.exists():
        print("پوشه site-packages پیدا نشد!")
        return
    
    # لیست پکیج‌های بزرگ برای پاکسازی
    large_packages = [
        'torch',
        'cv2',
        'scipy',
        'pyarrow',
        'spacy',
        'transformers',
        'numpy',
        'pandas',
        'plotly',
        'matplotlib',
        'seaborn',
        'sklearn',
        'tensorflow',
        'keras',
    ]
    
    print("\n=== شروع پاکسازی ===")
    total_deleted = 0
    
    for package in large_packages:
        deleted = cleanup_package(package)
        if deleted > 0:
            print(f"  ✓ {package}: {format_size(deleted)} حذف شد")
            total_deleted += deleted
    
    # پاکسازی عمومی برای همه پکیج‌ها
    print("\n=== پاکسازی عمومی ===")
    
    # حذف همه فایل‌های .pyc باقی‌مانده
    pyc_count = 0
    pyc_size = 0
    for pyc_file in SITE_PACKAGES.rglob('*.pyc'):
        try:
            if pyc_file.is_file():
                size = pyc_file.stat().st_size
                pyc_file.unlink()
                pyc_count += 1
                pyc_size += size
        except:
            pass
    
    if pyc_count > 0:
        print(f"  ✓ {pyc_count} فایل .pyc ({format_size(pyc_size)}) حذف شد")
        total_deleted += pyc_size
    
    # حذف همه __pycache__
    cache_count = 0
    cache_size = 0
    for cache_dir in SITE_PACKAGES.rglob('__pycache__'):
        try:
            if cache_dir.is_dir():
                size = get_size(cache_dir)
                shutil.rmtree(cache_dir)
                cache_count += 1
                cache_size += size
        except:
            pass
    
    if cache_count > 0:
        print(f"  ✓ {cache_count} پوشه __pycache__ ({format_size(cache_size)}) حذف شد")
        total_deleted += cache_size
    
    print(f"\n✓ مجموع {format_size(total_deleted)} حذف شد")
    print("\n" + "=" * 60)
    print("✓ پاکسازی با موفقیت انجام شد!")
    print("=" * 60)

if __name__ == '__main__':
    main()


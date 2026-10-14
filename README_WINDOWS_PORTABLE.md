# اجرای قابل حمل روی ویندوز

فایل `CafePlatform.exe` از `scripts/portable_launcher.py` ساخته می‌شود. با اجرای آن، سرور فقط روی `127.0.0.1:5000` فعال می‌شود و صفحهٔ ورود «کافه اصلی» مستقیم در مرورگر باز می‌شود. پنجرهٔ راه‌انداز را برای فعال ماندن برنامه باز نگه دارید. نشانی پیش‌فرض با متغیر `CAFE_DEFAULT_SLUG` قابل تنظیم است.

دکمهٔ «پرینت فاکتور» در داشبورد، فیش را مستقیم و بدون پیش‌نمایش مرورگر به فیش‌پرینتر ESC/POS ویندوز می‌فرستد. اگر `Xprinter XP-80` نصب باشد همان را انتخاب می‌کند؛ در غیر این صورت چاپگر واقعی پیش‌فرض ویندوز استفاده می‌شود. برای انتخاب چاپگر مشخص، متغیر `CAFE_RECEIPT_PRINTER` را به نام دقیق آن در ویندوز تنظیم کنید. پیام برنامه فقط ارسال داده به صف چاپ را تأیید می‌کند؛ خروج کاغذ را باید روی دستگاه بررسی کرد.

داده‌های قابل تغییر کنار فایل اجرایی، در پوشهٔ `runtime/instance` و `runtime/tenants` قرار می‌گیرند. پیش از هر جابه‌جایی یا جایگزینی دیتابیس، برنامه را از دکمهٔ «توقف برنامه» ببندید و از فایل‌های `.db` نسخهٔ پشتیبان بگیرید. فایل `runtime/instance/secret_key` را همراه دیتابیس‌ها نگه دارید تا نشست‌های کاربران پس از راه‌اندازی دوباره معتبر بمانند.

برای ساخت فایل اجرایی در ویندوز، در ریشهٔ پروژه و یک محیط پایتون تازه:

```powershell
python -m pip install -r requirements_minimal.txt pyinstaller
pyinstaller --noconfirm --onefile --windowed --name CafePlatform --paths . --add-data "templates;templates" --add-data "static;static" --collect-data arabic_reshaper --hidden-import PIL._imagingft --hidden-import win32print --hidden-import bidi.algorithm --hidden-import services.receipt_printer --hidden-import arabic_reshaper scripts\portable_launcher.py
```

خروجی در `dist/CafePlatform.exe` ساخته می‌شود. برای نصب تازه، `MASTER_PASSWORD` را پیش از اولین اجرا به رمزی قوی تنظیم کنید. در نصب فعلی AnyDesk، دیتابیس قدیمی به شعبهٔ `legacy` با نام «کافه اصلی» متصل شده است؛ صفحهٔ ورود آن `http://127.0.0.1:5000/cafe/legacy/login` است.

حساب کافه از حساب مدیریت مرکزی جدا است. ورود با رمز کافه، نشست مدیریت مرکزی همان مرورگر را پاک می‌کند. دسترسی به مسیرهای `/master/` تنها با ورود جداگانهٔ مدیر مرکزی ممکن است.

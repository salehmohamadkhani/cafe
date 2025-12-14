# راهنمای کامل Deployment پروژه کافه

## اطلاعات سرور
- **IP Address:** (set via `CAFE_SERVER_IP`)
- **Username:** (set via `CAFE_SERVER_USER`)
- **Password:** (set via `CAFE_SERVER_PASSWORD`)
- **Domain:** cafe.baztaj.com
- **مسیر پروژه:** /var/www/کافه

## مرحله 1: آماده‌سازی فایل‌ها در سیستم محلی

### فایل‌های لازم برای کپی:
- تمام فایل‌های `.py`
- پوشه `templates/`
- پوشه `static/`
- پوشه `models/`
- پوشه `routes/`
- پوشه `services/`
- پوشه `utils/`
- پوشه `migrations/`
- فایل‌های `config.py`, `wsgi.py`, `requirements_production.txt`
- فایل `gunicorn_config.py`
- فایل `nginx_config.conf`

### فایل‌هایی که نباید کپی شوند:
- `__pycache__/`
- `*.pyc`
- `instance/*.db` (دیتابیس محلی)
- `*.bat`, `*.zip`
- `New folder/`
- `*.txt` (غیر از requirements)

## مرحله 2: اتصال و کپی فایل‌ها به سرور

### روش 1: استفاده از WinSCP (توصیه می‌شود برای Windows)

1. دانلود و نصب WinSCP
2. اتصال:
   - Host name: (server ip)
   - Username: (server user)
   - Password: (server password)
   - Port: `22`
3. کپی تمام فایل‌های پروژه به `/var/www/کافه`

### روش 2: استفاده از PowerShell با SCP

```powershell
# نصب OpenSSH در Windows (اگر نصب نیست)
# Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0

# کپی فایل‌ها
scp -r C:\Users\saleh\cafe1\* root@103.75.198.160:/var/www/کافه/
```

## مرحله 3: تنظیمات در سرور

### 3.1 اتصال به سرور
```bash
ssh root@103.75.198.160
# Password: (your server password)
```

### 3.2 ایجاد پوشه و بررسی فایل‌ها
```bash
mkdir -p /var/www/کافه
cd /var/www/کافه
ls -la
```

### 3.3 نصب Python و ابزارهای لازم
```bash
apt update
apt install -y python3 python3-pip python3-venv nginx
```

### 3.4 ایجاد محیط مجازی و نصب وابستگی‌ها
```bash
cd /var/www/کافه
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements_production.txt
```

### 3.5 ایجاد پوشه instance و تنظیمات
```bash
mkdir -p instance
mkdir -p /var/log/cafe
chmod 755 /var/log/cafe
```

### 3.6 تنظیم SECRET_KEY
```bash
nano config.py
# SECRET_KEY را به یک مقدار تصادفی و امن تغییر دهید
```

### 3.7 تست اجرای برنامه
```bash
source venv/bin/activate
python app.py
# اگر بدون خطا اجرا شد، Ctrl+C بزنید
```

## مرحله 4: تنظیم Gunicorn

### 4.1 نصب Gunicorn
```bash
source venv/bin/activate
pip install gunicorn
```

### 4.2 تست Gunicorn
```bash
gunicorn --config gunicorn_config.py wsgi:app
# اگر بدون خطا اجرا شد، Ctrl+C بزنید
```

### 4.3 ایجاد Systemd Service
```bash
nano /etc/systemd/system/cafe.service
```

محتوای فایل را از `systemd_service.txt` کپی کنید.

```bash
# فعال‌سازی و راه‌اندازی سرویس
systemctl daemon-reload
systemctl enable cafe
systemctl start cafe
systemctl status cafe
```

## مرحله 5: تنظیم Nginx

### 5.1 کپی فایل تنظیمات
```bash
cp nginx_config.conf /etc/nginx/sites-available/cafe.baztaj.com
```

### 5.2 فعال‌سازی سایت
```bash
ln -s /etc/nginx/sites-available/cafe.baztaj.com /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 5.3 تنظیم DNS
در پنل مدیریت دامنه، رکورد A را تنظیم کنید:
- Type: A
- Name: cafe
- Value: 103.75.198.160
- TTL: 3600

## مرحله 6: تنظیم SSL (HTTPS)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d cafe.baztaj.com
# ایمیل خود را وارد کنید و دستورالعمل‌ها را دنبال کنید
```

## مرحله 7: تنظیمات Firewall

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status
```

## دستورات مفید

### مشاهده لاگ‌ها
```bash
# لاگ Gunicorn
journalctl -u cafe -f

# لاگ Nginx
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log

# لاگ برنامه
tail -f /var/log/cafe/error.log
```

### مدیریت سرویس
```bash
# راه‌اندازی مجدد
systemctl restart cafe
systemctl restart nginx

# توقف
systemctl stop cafe

# شروع
systemctl start cafe

# وضعیت
systemctl status cafe
systemctl status nginx
```

### به‌روزرسانی کد
```bash
cd /var/www/کافه
# کپی فایل‌های جدید
systemctl restart cafe
```

### Backup دیتابیس
```bash
cd /var/www/کافه
cp instance/cafe.db instance/cafe.db.backup.$(date +%Y%m%d_%H%M%S)
```

## عیب‌یابی

### اگر سایت باز نمی‌شود:
1. بررسی وضعیت سرویس‌ها:
   ```bash
   systemctl status cafe
   systemctl status nginx
   ```

2. بررسی پورت‌ها:
   ```bash
   netstat -tlnp | grep 5000
   ```

3. بررسی لاگ‌ها:
   ```bash
   journalctl -u cafe -n 50
   tail -f /var/log/nginx/error.log
   ```

### اگر خطای Permission دارید:
```bash
chown -R root:root /var/www/کافه
chmod -R 755 /var/www/کافه
chmod -R 777 /var/www/کافه/instance
```

## نکات امنیتی

1. **SECRET_KEY:** حتماً در `config.py` تغییر دهید
2. **Firewall:** فقط پورت‌های لازم را باز کنید
3. **SSL:** حتماً HTTPS را فعال کنید
4. **Backup:** به صورت منظم backup بگیرید
5. **Updates:** سیستم را به‌روز نگه دارید

## پشتیبانی

در صورت بروز مشکل، لاگ‌ها را بررسی کنید و خطاها را گزارش دهید.


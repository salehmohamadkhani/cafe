# دستورالعمل Deployment پروژه کافه

## اطلاعات سرور
- **IP:** (server ip)
- **Password:** (server password)
- **Domain:** cafe.baztaj.com
- **مسیر پروژه:** /var/www/کافه

## مراحل Deployment

### 1. اتصال به سرور
```bash
ssh root@103.75.198.160
# Password: (your server password)
```

### 2. ایجاد پوشه پروژه
```bash
mkdir -p /var/www/کافه
cd /var/www/کافه
```

### 3. کپی فایل‌ها از سیستم محلی
از سیستم محلی خود (Windows) این دستورات را اجرا کنید:

**گزینه 1: استفاده از WinSCP یا FileZilla**
- Host: 103.75.198.160
- Username: root
- Password: (your server password)
- Port: 22
- تمام فایل‌های پروژه را به `/var/www/کافه` کپی کنید

**گزینه 2: استفاده از PowerShell (اگر SSH نصب است)**
```powershell
scp -r C:\Users\saleh\cafe1\* root@103.75.198.160:/var/www/کافه/
```

### 4. نصب Python و وابستگی‌ها در سرور
```bash
cd /var/www/کافه

# نصب Python 3 و pip (اگر نصب نیست)
apt update
apt install -y python3 python3-pip python3-venv

# ایجاد محیط مجازی
python3 -m venv venv
source venv/bin/activate

# نصب وابستگی‌ها
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. تنظیمات دیتابیس
```bash
# ایجاد پوشه instance
mkdir -p instance

# اجرای migration (اگر نیاز باشد)
source venv/bin/activate
python app.py
# این دستور دیتابیس را ایجاد می‌کند
```

### 6. نصب و تنظیم Gunicorn
```bash
source venv/bin/activate
pip install gunicorn

# تست اجرا
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

### 7. ایجاد Systemd Service
```bash
sudo nano /etc/systemd/system/cafe.service
```

محتوای فایل:
```ini
[Unit]
Description=Cafe Management System
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/کافه
Environment="PATH=/var/www/کافه/venv/bin"
ExecStart=/var/www/کافه/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app

[Install]
WantedBy=multi-user.target
```

```bash
# فعال‌سازی سرویس
sudo systemctl daemon-reload
sudo systemctl enable cafe
sudo systemctl start cafe
sudo systemctl status cafe
```

### 8. تنظیم Nginx
```bash
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/cafe.baztaj.com
```

محتوای فایل:
```nginx
server {
    listen 80;
    server_name cafe.baztaj.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/کافه/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# فعال‌سازی سایت
sudo ln -s /etc/nginx/sites-available/cafe.baztaj.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 9. تنظیم SSL (اختیاری اما توصیه می‌شود)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d cafe.baztaj.com
```

### 10. تنظیمات Firewall
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## دستورات مفید

### مشاهده لاگ‌ها
```bash
# لاگ Gunicorn
sudo journalctl -u cafe -f

# لاگ Nginx
sudo tail -f /var/log/nginx/error.log
```

### راه‌اندازی مجدد
```bash
sudo systemctl restart cafe
sudo systemctl restart nginx
```

### بررسی وضعیت
```bash
sudo systemctl status cafe
sudo systemctl status nginx
```

## نکات مهم

1. **امنیت:** بعد از deployment، SECRET_KEY را در config.py تغییر دهید
2. **Backup:** به صورت منظم از دیتابیس backup بگیرید
3. **Monitoring:** لاگ‌ها را به صورت منظم بررسی کنید
4. **Updates:** به‌روزرسانی‌های امنیتی را نصب کنید


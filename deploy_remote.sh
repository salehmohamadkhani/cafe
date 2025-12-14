#!/bin/bash
# اسکریپت اجرا در سرور - بعد از کپی فایل‌ها

set -e

echo "🚀 شروع تنظیمات پروژه کافه در سرور..."

PROJECT_DIR="/var/www/کافه"
cd "$PROJECT_DIR"

# به‌روزرسانی سیستم
echo "📦 به‌روزرسانی سیستم..."
apt update
apt install -y python3 python3-pip python3-venv nginx

# ایجاد محیط مجازی
echo "🐍 ایجاد محیط مجازی Python..."
python3 -m venv venv
source venv/bin/activate

# نصب وابستگی‌ها
echo "📚 نصب وابستگی‌های Python..."
pip install --upgrade pip
pip install -r requirements_production.txt
pip install gunicorn

# ایجاد پوشه‌های لازم
echo "📁 ایجاد پوشه‌های لازم..."
mkdir -p instance
mkdir -p /var/log/cafe
chmod 755 /var/log/cafe

# تنظیم Systemd Service
echo "⚙️  تنظیم Systemd Service..."
cp systemd_service.txt /etc/systemd/system/cafe.service
systemctl daemon-reload
systemctl enable cafe

# تنظیم Nginx
echo "🌐 تنظیم Nginx..."
cp nginx_config.conf /etc/nginx/sites-available/cafe.baztaj.com
ln -sf /etc/nginx/sites-available/cafe.baztaj.com /etc/nginx/sites-enabled/
nginx -t

# راه‌اندازی سرویس‌ها
echo "🔄 راه‌اندازی سرویس‌ها..."
systemctl start cafe
systemctl restart nginx

# نمایش وضعیت
echo ""
echo "✅ تنظیمات کامل شد!"
echo ""
echo "📊 وضعیت سرویس‌ها:"
systemctl status cafe --no-pager -l
echo ""
echo "📝 دستورات مفید:"
echo "  - مشاهده لاگ: journalctl -u cafe -f"
echo "  - راه‌اندازی مجدد: systemctl restart cafe"
echo "  - وضعیت: systemctl status cafe"
echo ""
echo "⚠️  نکته: حتماً SECRET_KEY را در config.py تغییر دهید!"


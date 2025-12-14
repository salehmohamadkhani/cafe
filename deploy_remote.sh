#!/bin/bash
# اسکریپت اجرا در سرور - بعد از کپی فایل‌ها

set -e

echo "🚀 شروع تنظیمات پروژه کافه در سرور..."

PROJECT_DIR="${CAFE_PROJECT_DIR:-/var/www/کافه}"
DOMAIN="${CAFE_DOMAIN:-cafe.baztaj.com}"
SERVICE_NAME="${CAFE_SERVICE_NAME:-cafe}"
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

# ایجاد پوشه‌های لازم
echo "📁 ایجاد پوشه‌های لازم..."
mkdir -p instance
mkdir -p tenants
mkdir -p /var/log/cafe
chmod 755 /var/log/cafe

# دسترسی‌ها برای اجرای سرویس با www-data
chown -R www-data:www-data "$PROJECT_DIR/instance" "$PROJECT_DIR/tenants" /var/log/cafe
chmod 775 "$PROJECT_DIR/instance" "$PROJECT_DIR/tenants" /var/log/cafe

# تنظیم Systemd Service
echo "⚙️  تنظیم Systemd Service..."
if [ ! -f systemd_service.txt ]; then
  echo "❌ فایل systemd_service.txt پیدا نشد. مطمئن شوید فایل‌های پروژه کامل کپی شده‌اند."
  exit 1
fi
TMP_SERVICE="/tmp/${SERVICE_NAME}.service"
sed "s|/var/www/کافه|${PROJECT_DIR}|g" systemd_service.txt > "$TMP_SERVICE"
cp "$TMP_SERVICE" "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# تنظیم Nginx
echo "🌐 تنظیم Nginx..."
if [ ! -f nginx_config.conf ]; then
  echo "❌ فایل nginx_config.conf پیدا نشد."
  exit 1
fi

# اگر دامنه سفارشی دارید، server_name را جایگزین می‌کنیم
TMP_NGINX_CONF="/tmp/${DOMAIN}.nginx.conf"
sed -e "s/server_name\\s\\+[^;]*;/server_name ${DOMAIN};/g" \
    -e "s|/var/www/کافه|${PROJECT_DIR}|g" \
    nginx_config.conf > "$TMP_NGINX_CONF"
cp "$TMP_NGINX_CONF" "/etc/nginx/sites-available/${DOMAIN}"
ln -sf "/etc/nginx/sites-available/${DOMAIN}" /etc/nginx/sites-enabled/
nginx -t

# راه‌اندازی سرویس‌ها
echo "🔄 راه‌اندازی سرویس‌ها..."
systemctl restart "$SERVICE_NAME"
systemctl restart nginx

# نمایش وضعیت
echo ""
echo "✅ تنظیمات کامل شد!"
echo ""
echo "📊 وضعیت سرویس‌ها:"
systemctl status "$SERVICE_NAME" --no-pager -l
echo ""
echo "📝 دستورات مفید:"
echo "  - مشاهده لاگ: journalctl -u ${SERVICE_NAME} -f"
echo "  - راه‌اندازی مجدد: systemctl restart ${SERVICE_NAME}"
echo "  - وضعیت: systemctl status ${SERVICE_NAME}"
echo ""
echo "🔐 نکته امنیتی: می‌توانید SECRET_KEY را در /etc/cafe.env ست کنید (اختیاری)."


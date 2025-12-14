#!/bin/bash

# اسکریپت deployment برای سرور
# آدرس سرور: (از ENV بخوانید)
# دامنه: cafe.baztaj.com

echo "🚀 شروع deployment پروژه کافه..."

# تنظیمات
SERVER_IP="${CAFE_SERVER_IP:-CHANGE_ME}"
SERVER_USER="${CAFE_SERVER_USER:-root}"
SERVER_PASSWORD="${CAFE_SERVER_PASSWORD:-}"
PROJECT_NAME="کافه"
DOMAIN="cafe.baztaj.com"
REMOTE_PATH="/var/www/$PROJECT_NAME"

# اتصال به سرور و ایجاد پوشه
echo "📁 ایجاد پوشه پروژه در سرور..."
if [ "$SERVER_IP" = "CHANGE_ME" ] || [ -z "$SERVER_PASSWORD" ]; then
  echo "ERROR: Set CAFE_SERVER_IP and CAFE_SERVER_PASSWORD environment variables."
  exit 1
fi

sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP << 'ENDSSH'
mkdir -p /var/www/کافه
cd /var/www/کافه
pwd
ENDSSH

# کپی فایل‌ها به سرور
echo "📦 کپی فایل‌ها به سرور..."
sshpass -p "$SERVER_PASSWORD" scp -r -o StrictHostKeyChecking=no \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='instance/*.db' \
    --exclude='instance/*.backup' \
    --exclude='*.bat' \
    --exclude='*.zip' \
    --exclude='New folder' \
    --exclude='*.txt' \
    . $SERVER_USER@$SERVER_IP:/var/www/کافه/

echo "✅ فایل‌ها با موفقیت کپی شدند!"
echo "📝 لطفاً دستورات زیر را در سرور اجرا کنید:"
echo ""
echo "1. cd /var/www/کافه"
echo "2. python3 -m venv venv"
echo "3. source venv/bin/activate"
echo "4. pip install -r requirements.txt"
echo "5. python app.py"


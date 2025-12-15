#!/bin/bash

# اسکریپت deployment برای سرور
# آدرس سرور: (از ENV بخوانید)
# دامنه: cafe.baztaj.com

set -euo pipefail

echo "🚀 شروع deployment پروژه کافه..."

# تنظیمات
SERVER_IP="${CAFE_SERVER_IP:-}"
SERVER_USER="${CAFE_SERVER_USER:-root}"
SERVER_PASSWORD="${CAFE_SERVER_PASSWORD:-}"
REMOTE_PATH="${CAFE_REMOTE_PATH:-/var/www/کافه}"
DOMAIN="${CAFE_DOMAIN:-cafe.baztaj.com}"

if [ -z "$SERVER_IP" ]; then
  echo "ERROR: Set CAFE_SERVER_IP environment variable."
  exit 1
fi

SSH_OPTS="-o StrictHostKeyChecking=no"

if [ -n "$SERVER_PASSWORD" ]; then
  if ! command -v sshpass >/dev/null 2>&1; then
    echo "ERROR: sshpass is required when CAFE_SERVER_PASSWORD is set. Install it (e.g., apt install -y sshpass)."
    exit 1
  fi
  SSH_BASE=(sshpass -p "$SERVER_PASSWORD" ssh $SSH_OPTS)
  RSYNC_BASE=(sshpass -p "$SERVER_PASSWORD" rsync -az --partial --info=progress2 -e "ssh $SSH_OPTS")
else
  SSH_BASE=(ssh $SSH_OPTS)
  RSYNC_BASE=(rsync -az --partial --info=progress2 -e "ssh $SSH_OPTS")
fi

echo "📁 آماده‌سازی مسیر پروژه در سرور (پاکسازی نسخه قبلی)..."
"${SSH_BASE[@]}" "$SERVER_USER@$SERVER_IP" bash -lc "
  set -e
  mkdir -p \"$REMOTE_PATH\"

  # Backup دیتابیس اگر وجود دارد
  if [ -f \"$REMOTE_PATH/instance/cafe.db\" ]; then
    mkdir -p /var/backups/cafe
    cp \"$REMOTE_PATH/instance/cafe.db\" \"/var/backups/cafe/cafe.db.backup.\$(date +%Y%m%d_%H%M%S)\"
  fi

  # پاکسازی کامل پوشه پروژه (همه فایل‌ها، حتی dotfiles)
  rm -rf -- \"$REMOTE_PATH\"/* \"$REMOTE_PATH\"/.[!.]* \"$REMOTE_PATH\"/..?* 2>/dev/null || true
"

echo "📦 کپی فایل‌ها به سرور (sync)..."
"${RSYNC_BASE[@]}" \
  --delete \
  --exclude ".git/" \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  --exclude "instance/*.db" \
  --exclude "instance/*.backup*" \
  --exclude "*.zip" \
  --exclude "*.bat" \
  ./ "$SERVER_USER@$SERVER_IP:\"$REMOTE_PATH/\""

echo "✅ فایل‌ها با موفقیت کپی شدند!"

echo "⚙️ اجرای تنظیمات سرور (nginx + systemd + venv + deps)..."
"${SSH_BASE[@]}" "$SERVER_USER@$SERVER_IP" bash -lc "
  set -e
  cd \"$REMOTE_PATH\"
  export CAFE_PROJECT_DIR=\"$REMOTE_PATH\"
  export CAFE_DOMAIN=\"$DOMAIN\"
  bash deploy_remote.sh
"

echo "🎉 Deployment تمام شد."


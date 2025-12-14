# 🚀 راهنمای سریع Deployment

## اطلاعات سرور
- **IP:** (server ip)
- **Password:** (server password)
- **Domain:** cafe.baztaj.com
- **مسیر:** /var/www/کافه

## مراحل سریع

### 1️⃣ کپی فایل‌ها به سرور

**روش آسان (WinSCP):**
1. دانلود WinSCP: https://winscp.net
2. اتصال:
   - Host: (server ip)
   - User: (server user)
   - Password: (server password)
3. کپی تمام فایل‌ها به `/var/www/کافه`

### 2️⃣ اجرای اسکریپت در سرور

```bash
ssh root@103.75.198.160
cd /var/www/کافه
bash deploy_remote.sh
```

### 3️⃣ تنظیم DNS

در پنل دامنه، رکورد A اضافه کنید:
- Type: A
- Name: cafe
- Value: 103.75.198.160

### 4️⃣ فعال‌سازی SSL (اختیاری)

```bash
certbot --nginx -d cafe.baztaj.com
```

## ✅ تمام!

سایت شما در `http://cafe.baztaj.com` در دسترس است.

## 📚 مستندات کامل

برای جزئیات بیشتر، فایل `DEPLOYMENT.md` را مطالعه کنید.


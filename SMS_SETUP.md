# راهنمای تنظیم پنل SMS

برای فعال‌سازی ارسال SMS و استفاده از سیستم ورود با OTP، باید پنل SMS خود را تنظیم کنید.

## تنظیمات Environment Variables

قبل از اجرای برنامه، متغیرهای محیطی زیر را تنظیم کنید:

### 1. انتخاب پنل SMS

```bash
# Windows PowerShell
$env:SMS_PROVIDER="kavenegar"  # یا payamak, smsir, melipayamak, farazsms

# Linux/Mac
export SMS_PROVIDER="kavenegar"
```

### 2. تنظیمات API

بسته به پنل SMS که انتخاب کرده‌اید:

#### کاوه نگار (Kavenegar)
```bash
$env:SMS_API_KEY="YOUR_KAVENEGAR_API_KEY"
$env:SMS_SENDER="10001001001001"  # شماره فرستنده
```

#### پیامک (Payamak)
```bash
$env:SMS_USERNAME="YOUR_USERNAME"
$env:SMS_PASSWORD="YOUR_PASSWORD"
$env:SMS_SENDER="YOUR_SENDER_NUMBER"
```

#### SMS.ir
```bash
$env:SMS_API_KEY="YOUR_SMSIR_API_KEY"
$env:SMS_SENDER="YOUR_LINE_NUMBER"
```

#### ملی پیامک (Melipayamak)
```bash
$env:SMS_USERNAME="YOUR_USERNAME"
$env:SMS_PASSWORD="YOUR_PASSWORD"
$env:SMS_SENDER="YOUR_SENDER_NUMBER"
```

#### فراز SMS (FarazSMS)
```bash
$env:SMS_USERNAME="YOUR_USERNAME"
$env:SMS_PASSWORD="YOUR_PASSWORD"
$env:SMS_SENDER="YOUR_SENDER_NUMBER"
$env:SMS_PATTERN_CODE="YOUR_PATTERN_CODE"  # کد پترن تایید شده
```

**نکته:** برای راهنمای کامل تنظیم فراز SMS و ساخت پترن، فایل `FARAZSMS_SETUP.md` را مطالعه کنید.

## حالت تست (بدون پنل SMS)

اگر پنل SMS ندارید یا می‌خواهید تست کنید، می‌توانید از حالت تست استفاده کنید:

```bash
$env:SMS_PROVIDER="test"
```

در این حالت، کد OTP در console نمایش داده می‌شود.

## ایجاد کاربر Master

بعد از تنظیمات، کاربر master را ایجاد کنید:

```bash
python create_master_user_otp.py
```

یا با شماره موبایل خاص:

```bash
$env:MASTER_PHONE="09121148277"
python create_master_user_otp.py
```

## استفاده

1. به `/master/login` بروید
2. شماره موبایل خود را وارد کنید
3. روی "ارسال کد ورود" کلیک کنید
4. کد 6 رقمی که به شماره شما ارسال شد را وارد کنید
5. وارد پنل مدیریت می‌شوید

## نکات مهم

- کد OTP تا 5 دقیقه معتبر است
- هر شماره موبایل می‌تواند یک کاربر master باشد
- در اولین ورود، کاربر به صورت خودکار ایجاد می‌شود
- شماره موبایل باید به فرمت ایرانی باشد (مثلاً 09121148277)


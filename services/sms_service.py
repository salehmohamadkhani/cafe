"""
سرویس ارسال SMS برای OTP
پشتیبانی از پنل‌های مختلف SMS ایرانی
"""
import os
import requests
from typing import Optional
from datetime import datetime, timedelta
import random


class SMSService:
    """سرویس ارسال SMS - قابل تنظیم برای پنل‌های مختلف"""
    
    def __init__(self):
        # تنظیمات از environment variables یا config
        self.provider = os.environ.get('SMS_PROVIDER', 'kavenegar').lower()
        self.api_key = os.environ.get('SMS_API_KEY', '')
        self.api_url = os.environ.get('SMS_API_URL', '')
        self.username = os.environ.get('SMS_USERNAME', '')
        self.password = os.environ.get('SMS_PASSWORD', '')
        self.sender = os.environ.get('SMS_SENDER', '10001001001001')  # شماره فرستنده
        # برای فراز SMS
        self.pattern_code = os.environ.get('SMS_PATTERN_CODE', '')  # کد پترن تایید شده
        
    def generate_otp(self) -> str:
        """تولید کد 6 رقمی OTP"""
        return str(random.randint(100000, 999999))
    
    def send_otp(self, phone_number: str, otp_code: str) -> tuple[bool, str]:
        """
        ارسال کد OTP به شماره موبایل
        Returns: (success: bool, message: str)
        """
        # نرمال‌سازی شماره موبایل (حذف فاصله و کاراکترهای اضافی)
        phone_number = phone_number.replace(' ', '').replace('-', '').replace('+', '')
        if phone_number.startswith('0'):
            phone_number = '98' + phone_number[1:]  # تبدیل 0912... به 98912...
        elif not phone_number.startswith('98'):
            phone_number = '98' + phone_number
        
        # متن پیامک
        message = f"کد ورود شما: {otp_code}\nاین کد تا 5 دقیقه معتبر است."
        
        try:
            if self.provider == 'kavenegar':
                return self._send_kavenegar(phone_number, message)
            elif self.provider == 'payamak':
                return self._send_payamak(phone_number, message)
            elif self.provider == 'smsir':
                return self._send_smsir(phone_number, message)
            elif self.provider == 'melipayamak':
                return self._send_melipayamak(phone_number, message)
            elif self.provider == 'farazsms' or self.provider == 'faraz':
                return self._send_farazsms(phone_number, otp_code)
            else:
                # Fallback: فقط در console نمایش می‌دهد (برای تست)
                print(f"[SMS TEST] Sending OTP to {phone_number}: {otp_code}")
                print(f"[SMS TEST] Message: {message}")
                return True, "کد OTP در console نمایش داده شد (حالت تست)"
        except Exception as e:
            return False, f"خطا در ارسال SMS: {str(e)}"
    
    def _send_kavenegar(self, phone_number: str, message: str) -> tuple[bool, str]:
        """ارسال از طریق کاوه نگار"""
        url = "https://api.kavenegar.com/v1/{}/sms/send.json".format(self.api_key)
        data = {
            'sender': self.sender,
            'receptor': phone_number,
            'message': message
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('return', {}).get('status') == 200:
                return True, "پیامک با موفقیت ارسال شد"
            else:
                return False, result.get('return', {}).get('message', 'خطا در ارسال')
        return False, f"خطا در ارتباط با API: {response.status_code}"
    
    def _send_payamak(self, phone_number: str, message: str) -> tuple[bool, str]:
        """ارسال از طریق پیامک"""
        url = "http://api.payamak-panel.com/post/Send.asmx/SendSimpleSMS2"
        data = {
            'username': self.username,
            'password': self.password,
            'to': phone_number,
            'from': self.sender,
            'text': message,
            'isflash': False
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            # پاسخ معمولاً یک عدد است (مثلاً 1 برای موفقیت)
            result = response.text.strip()
            if result.isdigit() and int(result) > 0:
                return True, "پیامک با موفقیت ارسال شد"
        return False, "خطا در ارسال پیامک"
    
    def _send_smsir(self, phone_number: str, message: str) -> tuple[bool, str]:
        """ارسال از طریق SMS.ir"""
        url = "https://api.sms.ir/v1/send"
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        data = {
            'mobile': phone_number,
            'message': message,
            'lineNumber': self.sender
        }
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 1:
                return True, "پیامک با موفقیت ارسال شد"
            else:
                return False, result.get('message', 'خطا در ارسال')
        return False, f"خطا در ارتباط با API: {response.status_code}"
    
    def _send_melipayamak(self, phone_number: str, message: str) -> tuple[bool, str]:
        """ارسال از طریق ملی پیامک"""
        url = "https://rest.payamak-panel.com/api/SendSMS/SendSMS"
        data = {
            'username': self.username,
            'password': self.password,
            'to': phone_number,
            'from': self.sender,
            'text': message
        }
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('RetStatus') == 1:
                return True, "پیامک با موفقیت ارسال شد"
            else:
                return False, result.get('StrRetStatus', 'خطا در ارسال')
        return False, f"خطا در ارتباط با API: {response.status_code}"
    
    def _send_farazsms(self, phone_number: str, otp_code: str) -> tuple[bool, str]:
        """ارسال از طریق فراز SMS با استفاده از Pattern"""
        if not self.pattern_code:
            return False, "کد پترن (SMS_PATTERN_CODE) تنظیم نشده است"
        
        # فراز SMS از API با Pattern استفاده می‌کند
        # URL معمولاً: https://ippanel.com/api/select
        url = os.environ.get('FARAZSMS_API_URL', 'https://ippanel.com/api/select')
        
        # برای فراز SMS، معمولاً از username/password یا API key استفاده می‌شود
        # بسته به نوع API که فراز SMS ارائه می‌دهد
        
        # روش 1: با username/password
        if self.username and self.password:
            data = {
                'op': 'send',  # یا 'pattern' برای Pattern
                'uname': self.username,
                'pass': self.password,
                'message': f"کد ورود شما: {otp_code}\nاین کد تا 5 دقیقه معتبر است.",
                'to': phone_number,
                'from': self.sender
            }
            response = requests.post(url, data=data, timeout=10)
        # روش 2: با API Key و Pattern
        elif self.api_key and self.pattern_code:
            # استفاده از Pattern API
            pattern_url = os.environ.get('FARAZSMS_PATTERN_URL', 'https://ippanel.com/services.jspd')
            data = {
                'op': 'pattern',
                'user': self.username if self.username else '',
                'pass': self.password if self.password else '',
                'fromNum': self.sender,
                'toNum': phone_number,
                'patternCode': self.pattern_code,
                'inputData': f'{{"otp":"{otp_code}"}}'  # JSON string برای متغیرهای Pattern
            }
            response = requests.post(pattern_url, data=data, timeout=10)
        else:
            return False, "اطلاعات احراز هویت فراز SMS (username/password یا API key) تنظیم نشده است"
        
        if response.status_code == 200:
            try:
                result = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                # بررسی پاسخ (فرمت پاسخ فراز SMS ممکن است متفاوت باشد)
                if isinstance(result, dict):
                    if result.get('status') == 'ok' or result.get('result') == 'success':
                        return True, "پیامک با موفقیت ارسال شد"
                    else:
                        return False, result.get('message', 'خطا در ارسال')
                elif isinstance(result, str):
                    # اگر پاسخ یک عدد مثبت باشد (مثل کدهای خطا)
                    if result.strip().isdigit():
                        code = int(result.strip())
                        if code > 0:
                            return True, "پیامک با موفقیت ارسال شد"
                        else:
                            return False, f"خطا در ارسال: کد {code}"
                    elif 'success' in result.lower() or 'ok' in result.lower():
                        return True, "پیامک با موفقیت ارسال شد"
            except:
                pass
        
        return False, f"خطا در ارتباط با API: {response.status_code}"


# Singleton instance
sms_service = SMSService()


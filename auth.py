from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required # <-- ایمپورت‌های لازم
# ایمپورت‌های دیگر مثل مدل User و db و فرم‌ها
# from .models import User
# from . import db
# from .forms import LoginForm, RegisterForm

auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/login', methods=['GET', 'POST'])
# این ویو نباید login_required داشته باشد!
def login():
    # منطق لاگین
    # form = LoginForm()
    # if form.validate_on_submit():
    #     user = User.query.filter_by(email=form.email.data).first()
    #     if user and user.check_password(form.password.data):
    #         login_user(user, remember=form.remember.data)
    #         next_page = request.args.get('next')
    #         return redirect(next_page or url_for('dashboard.dashboard')) # یا هر صفحه پیش‌فرض بعد از لاگین
    #     else:
    #         flash('ورود ناموفق. لطفا ایمیل و رمز عبور را بررسی کنید.', 'danger')
    # return render_template('auth/login.html', form=form)
    pass # مثال

@auth.route('/register', methods=['GET', 'POST'])
# این ویو هم نباید login_required داشته باشد!
def register():
    # منطق ثبت نام
    pass # مثال

@auth.route('/logout')
@login_required # <-- محافظت از ویو خروج
def logout():
    logout_user()
    flash('شما با موفقیت خارج شدید.', 'success')
    return redirect(url_for('auth.login')) # یا صفحه اصلی سایت

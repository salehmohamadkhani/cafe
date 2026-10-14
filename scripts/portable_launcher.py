"""Windowed launcher for a portable, local Cafe Platform installation."""

import os
import secrets
import socket
import sys
import threading
import traceback
import webbrowser
from pathlib import Path
from tkinter import Button, Label, Tk, messagebox
from urllib.parse import quote


if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(APP_DIR))
RUNTIME_DIR = APP_DIR / "runtime"
INSTANCE_DIR = RUNTIME_DIR / "instance"
TENANTS_DIR = RUNTIME_DIR / "tenants"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
TENANTS_DIR.mkdir(parents=True, exist_ok=True)

secret_file = INSTANCE_DIR / "secret_key"
if not secret_file.exists():
    secret_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")

os.environ.setdefault("SECRET_KEY", secret_file.read_text(encoding="utf-8").strip())
os.environ.setdefault("CAFE_DB_URI", f"sqlite:///{(INSTANCE_DIR / 'cafe.db').as_posix()}")
os.environ.setdefault("CAFE_MASTER_DB_URI", f"sqlite:///{(INSTANCE_DIR / 'master.db').as_posix()}")
os.environ.setdefault("CAFE_TENANTS_DIR", str(TENANTS_DIR))


def report_error(exc: BaseException) -> None:
    log_path = RUNTIME_DIR / "launcher-error.log"
    log_path.write_text(traceback.format_exc(), encoding="utf-8")
    messagebox.showerror("خطای اجرای سامانه کافه", f"برنامه اجرا نشد. جزئیات در این فایل است:\n{log_path}\n\n{exc}")


def main() -> None:
    try:
        from app import create_app
        from waitress import serve

        app = create_app()
    except Exception as exc:
        report_error(exc)
        return

    window = Tk()
    window.title("سامانه مدیریت کافه")
    window.geometry("450x175")
    window.resizable(False, False)
    status = Label(window, text="در حال راه‌اندازی سرور محلی...", font=("Segoe UI", 12))
    status.pack(pady=20)
    cafe_slug = os.environ.get("CAFE_DEFAULT_SLUG", "legacy")
    url = f"http://127.0.0.1:5000/cafe/{quote(cafe_slug, safe='')}/login"
    Button(window, text="باز کردن پنل کافه در مرورگر", command=lambda: webbrowser.open(url)).pack(pady=5)
    Button(window, text="توقف برنامه", command=window.destroy).pack(pady=5)

    threading.Thread(target=lambda: serve(app, host="127.0.0.1", port=5000, threads=8), daemon=True).start()

    def check_ready(attempt: int = 0) -> None:
        try:
            with socket.create_connection(("127.0.0.1", 5000), timeout=0.5):
                pass
        except OSError:
            if attempt < 30:
                window.after(500, check_ready, attempt + 1)
            else:
                status.configure(text="سرور آماده نشد؛ پورت ۵۰۰۰ را بررسی کنید.")
            return
        status.configure(text="پنل کافه آماده است")
        webbrowser.open(url)

    window.after(500, check_ready)
    window.mainloop()


if __name__ == "__main__":
    main()

"""Print a compact, Persian receipt directly to a Windows ESC/POS printer."""

from __future__ import annotations

import os
from datetime import datetime


class ReceiptPrintError(RuntimeError):
    pass


def _printer_name(win32print):
    installed = {
        item[2]
        for item in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
    }
    configured = os.environ.get("CAFE_RECEIPT_PRINTER", "").strip()
    if configured:
        if configured not in installed:
            raise ReceiptPrintError(f"چاپگر تنظیم‌شده «{configured}» در ویندوز پیدا نشد.")
        return configured
    if "Xprinter XP-80" in installed:
        return "Xprinter XP-80"
    try:
        default = win32print.GetDefaultPrinter()
    except Exception as exc:
        raise ReceiptPrintError("چاپگر پیش‌فرض ویندوز پیدا نشد.") from exc
    if not default or default not in installed or any(
        virtual in default.casefold()
        for virtual in ("pdf", "xps", "fax", "anydesk", "onenote")
    ):
        raise ReceiptPrintError("یک فیش‌پرینتر واقعی را به‌عنوان چاپگر پیش‌فرض تنظیم کنید.")
    return default


def _receipt_image(order, settings):
    from PIL import Image, ImageDraw, ImageFont, features
    from utils.helpers import to_jalali

    has_raqm = features.check("raqm")
    if has_raqm:
        def display_text(value):
            return str(value)

        text_options = {"direction": "rtl"}
        font_options = {}
    else:
        # PyInstaller builds can load Pillow without its optional RAQM engine.
        # Shape Arabic letters and reorder bidirectional text before BASIC draws it.
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
        except ImportError as exc:
            raise ReceiptPrintError("بستهٔ جایگزین چاپ فارسی نصب نشده است.") from exc

        def display_text(value):
            return get_display(arabic_reshaper.reshape(str(value)), base_dir="R")

        text_options = {}
        font_options = {"layout_engine": ImageFont.Layout.BASIC}

    width = 576  # 72 mm printable area at 203 dpi, on 80 mm paper.
    image = Image.new("L", (width, 12000), 255)
    draw = ImageDraw.Draw(image)
    font_path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "tahoma.ttf")
    bold_path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "tahomabd.ttf")
    try:
        normal = ImageFont.truetype(font_path, 25, **font_options)
        small = ImageFont.truetype(font_path, 22, **font_options)
        bold = ImageFont.truetype(bold_path, 27, **font_options)
        heading = ImageFont.truetype(bold_path, 33, **font_options)
    except OSError as exc:
        raise ReceiptPrintError("فونت فارسی Tahoma در ویندوز پیدا نشد.") from exc

    persian_digits = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

    def number(value):
        return str(value).translate(persian_digits)

    def price(value):
        return number(f"{int(value):,}")

    y = 8

    def line(value, font=normal, align="right", height=37):
        nonlocal y
        value = display_text(value)
        x, anchor = (width - 12, "ra") if align == "right" else (width // 2, "ma")
        draw.text((x, y), value, font=font, fill=0, anchor=anchor, **text_options)
        y += height

    def wrap_lines(value, font, max_width):
        words = str(value).split()
        part = ""
        lines = []
        for word in words:
            candidate = f"{part} {word}".strip()
            if part and draw.textlength(display_text(candidate), font=font, **text_options) > max_width:
                lines.append(part)
                part = word
            else:
                part = candidate
        if part:
            lines.append(part)
        return lines or [""]

    def wrapped(value, font=normal, align="right"):
        for part in wrap_lines(value, font, width - 24):
            line(part, font, align)

    def rule():
        nonlocal y
        y += 5
        draw.line((10, y, width - 10, y), fill=0, width=2)
        y += 12

    def amount(label, value, font=normal):
        nonlocal y
        draw.text((width - 12, y), display_text(label), font=font, fill=0, anchor="ra", **text_options)
        draw.text((12, y), price(value), font=font, fill=0, anchor="la")
        y += 39

    def table_row(item):
        nonlocal y
        description = wrap_lines(item.menu_item.name, normal, 238)
        row_height = max(38, 32 * len(description)) + 8
        for index, part in enumerate(description):
            draw.text((width - 12, y + index * 32), display_text(part), font=normal, fill=0, anchor="ra", **text_options)
        draw.text((293, y), number(item.quantity), font=small, fill=0, anchor="ma")
        draw.text((194, y), price(item.unit_price), font=small, fill=0, anchor="ma")
        draw.text((12, y), price(item.total_price), font=small, fill=0, anchor="la")
        y += row_height
        if item.note:
            for part in wrap_lines(f"توضیح: {item.note}", small, width - 24):
                line(part, small, height=32)
        draw.line((10, y - 3, width - 10, y - 3), fill=200, width=1)

    cafe_name = (settings.cafe_name if settings and settings.cafe_name else None) or "کافه"
    line(cafe_name, heading, "center", 47)
    if settings and settings.address:
        wrapped(settings.address, small, "center")
    if settings and settings.phone:
        line(f"تلفن: \u200e{number(settings.phone)}\u200e", small, "center")
    line(f"شماره فاکتور روزانه: {number(order.daily_sequence or '---')}", small, "center")
    line(f"شناسه فاکتور: \u200e{number(order.invoice_uid or order.invoice_number)}\u200e", small, "center")
    if order.created_at:
        try:
            date = to_jalali(order.created_at)
        except (TypeError, ValueError, AttributeError):
            date = order.created_at.strftime("%Y-%m-%d %H:%M")
        line(f"تاریخ: {number(date)}", small, "center")
    if order.customer and order.customer.name != "عمومی":
        wrapped(f"مشتری: {order.customer.name}", small, "center")
    rule()
    draw.text((width - 12, y), display_text("شرح"), font=bold, fill=0, anchor="ra", **text_options)
    draw.text((293, y), display_text("تعداد"), font=small, fill=0, anchor="ma", **text_options)
    draw.text((194, y), display_text("قیمت واحد"), font=small, fill=0, anchor="ma", **text_options)
    draw.text((12, y), display_text("مبلغ کل"), font=small, fill=0, anchor="la", **text_options)
    y += 40
    draw.line((10, y, width - 10, y), fill=0, width=1)
    y += 9
    for item in order.order_items:
        if item.is_deleted:
            continue
        table_row(item)
    y += 8
    draw.line((10, y, width - 10, y), fill=0, width=1)
    y += 12
    amount("جمع کل موارد:", order.total_amount, small)
    if order.discount:
        amount("تخفیف:", order.discount, small)
    tax_percent = getattr(settings, "tax_percent", None) if settings else None
    tax_label = f"مالیات ({number(tax_percent)}٪):" if tax_percent is not None else "مالیات:"
    amount(tax_label, order.tax_amount, small)
    amount("مبلغ نهایی قابل پرداخت:", order.final_amount, bold)
    if settings and settings.card_number:
        line(f"شماره کارت: \u200e{number(settings.card_number)}\u200e", small, "center", 35)
    rule()
    line("از خرید شما متشکریم!", small, "center", 30)
    if y > image.height - 24:
        raise ReceiptPrintError("فاکتور برای یک فیش بیش از حد بلند است.")
    return image.crop((0, 0, width, y + 8)).point(lambda pixel: 0 if pixel < 175 else 255, mode="1")


def _escpos_raster(image):
    # GS v 0 raster data in short strips keeps printer memory use bounded.
    width, height = image.size
    bytes_per_row = (width + 7) // 8
    for top in range(0, height, 256):
        strip_height = min(256, height - top)
        strip = image.crop((0, top, width, top + strip_height))
        data = bytes(~byte & 0xFF for byte in strip.tobytes())
        yield (
            b"\x1d\x76\x30\x00"
            + bytes((bytes_per_row & 255, bytes_per_row >> 8, strip_height & 255, strip_height >> 8))
            + data
        )


def print_receipt(order, settings):
    if os.name != "nt":
        raise ReceiptPrintError("چاپ مستقیم فقط روی ویندوز فعال است.")
    try:
        import win32print
    except ImportError as exc:
        raise ReceiptPrintError("بخش چاپ مستقیم ویندوز نصب نشده است.") from exc

    name = _printer_name(win32print)
    image = _receipt_image(order, settings)
    handle = None
    document_started = False
    try:
        handle = win32print.OpenPrinter(name)
        win32print.StartDocPrinter(handle, 1, (f"Cafe receipt {order.invoice_number}", None, "RAW"))
        document_started = True
        win32print.WritePrinter(handle, b"\x1b\x40")  # Reset ESC/POS state.
        for strip in _escpos_raster(image):
            if win32print.WritePrinter(handle, strip) != len(strip):
                raise ReceiptPrintError("ارسال همهٔ داده‌های فیش به چاپگر کامل نشد.")
        win32print.WritePrinter(handle, b"\x1b\x64\x02\x1d\x56\x00")  # Short feed, then cut.
        win32print.EndDocPrinter(handle)
        document_started = False
    except Exception as exc:
        if document_started:
            try:
                win32print.EndDocPrinter(handle)
            except Exception:
                pass
        if isinstance(exc, ReceiptPrintError):
            raise
        raise ReceiptPrintError(f"ارسال فیش به «{name}» انجام نشد: {exc}") from exc
    finally:
        if handle is not None:
            win32print.ClosePrinter(handle)
    return name

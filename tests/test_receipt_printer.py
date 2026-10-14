import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from services.receipt_printer import _escpos_raster, _receipt_image


class ReceiptPrinterTest(unittest.TestCase):
    def _receipt(self):
        item = SimpleNamespace(
            is_deleted=False,
            menu_item=SimpleNamespace(name="چای مخصوص با نبات"),
            quantity=2,
            unit_price=120000,
            total_price=240000,
            note=None,
        )
        order = SimpleNamespace(
            invoice_number=4774,
            invoice_uid="0114-20261003",
            daily_sequence=114,
            created_at=datetime(2026, 10, 3, 20, 0),
            customer=SimpleNamespace(name="عمومی"),
            order_items=[item],
            total_amount=240000,
            discount=0,
            tax_amount=21600,
            final_amount=261600,
        )
        settings = SimpleNamespace(cafe_name="کافه اصلی", address=None, phone=None, card_number=None)

        return order, settings

    def test_persian_receipt_is_compact_and_encodes_for_escpos(self):
        image = _receipt_image(*self._receipt())
        self.assertEqual(image.width, 576)
        self.assertLess(image.height, 650)
        self.assertIsNotNone(image.getbbox())

        strips = list(_escpos_raster(image))
        self.assertGreaterEqual(len(strips), 1)
        for strip in strips:
            self.assertEqual(strip[:4], b"\x1d\x76\x30\x00")
            row_bytes = strip[4] + 256 * strip[5]
            rows = strip[6] + 256 * strip[7]
            self.assertEqual(len(strip), 8 + row_bytes * rows)

    def test_persian_receipt_works_without_raqm(self):
        with patch("PIL.features.check", return_value=False):
            image = _receipt_image(*self._receipt())
        self.assertEqual(image.width, 576)
        self.assertLess(image.height, 650)
        self.assertIsNotNone(image.getbbox())


if __name__ == "__main__":
    unittest.main()

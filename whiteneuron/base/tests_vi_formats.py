"""#52: Django's vi locale has no input formats, so "05/11/2026" was read month-first."""
import datetime

from django import forms
from django.conf import settings
from django.test import SimpleTestCase
from django.utils import formats, translation


class VietnameseDateFormatTests(SimpleTestCase):
    def test_vietnamese_input_is_day_first(self):
        with translation.override("vi"):
            for value in ("05/11/2026", "05-11-2026", "05.11.2026", "2026-11-05"):
                self.assertEqual(forms.DateField().clean(value), datetime.date(2026, 11, 5), value)
            self.assertEqual(forms.DateTimeField().clean("05/11/2026 14:30").date(), datetime.date(2026, 11, 5))

    def test_english_input_is_unchanged(self):
        with translation.override("en"):
            self.assertEqual(forms.DateField().clean("05/11/2026"), datetime.date(2026, 5, 11))

    def test_vietnamese_display_is_short_and_date_first(self):
        moment = datetime.datetime(2026, 11, 5, 14, 30)
        with translation.override("vi"):
            self.assertEqual(formats.date_format(moment.date()), "05/11/2026")
            # the same order as typed: date, then time
            self.assertEqual(formats.date_format(moment, "DATETIME_FORMAT"), "05/11/2026 14:30")
            self.assertEqual(formats.date_format(moment, "SHORT_DATETIME_FORMAT"), "05/11/2026 14:30")
            self.assertEqual(formats.number_format(1234567.5, decimal_pos=1, force_grouping=True), "1.234.567,5")

    def test_vietnamese_weeks_start_on_monday(self):
        with translation.override("vi"):
            self.assertEqual(formats.get_format("FIRST_DAY_OF_WEEK"), 1)  # 0 = Sunday, Django's default

    def test_language_choice_outlives_the_browser_session(self):
        self.assertGreaterEqual(settings.LANGUAGE_COOKIE_AGE, 30 * 24 * 60 * 60)

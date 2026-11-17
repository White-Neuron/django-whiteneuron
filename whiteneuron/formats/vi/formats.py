# Vietnamese formats, read before Django's own (FORMAT_MODULE_PATH = ["whiteneuron.formats"]);
# whatever is not defined here comes from django/conf/locale/vi/formats.py.
#
# Django's vi locale defines no input formats, so the settings' DATE_INPUT_FORMATS applied:
# "05/11/2026" was read month-first and stored as 11 May. Vietnamese dates are day-first.

# Short, one line in a table cell (Django's default is "Ngày 05 tháng 11 năm 2026")
DATE_FORMAT = "d/m/Y"
DATETIME_FORMAT = "d/m/Y H:i"  # date first, as typed in DATETIME_INPUT_FORMATS
SHORT_DATE_FORMAT = "d/m/Y"
SHORT_DATETIME_FORMAT = "d/m/Y H:i"
FIRST_DAY_OF_WEEK = 1  # Monday

# Day first; ISO (2026-11-05) is always accepted as well
DATE_INPUT_FORMATS = [
    "%d/%m/%Y",  # '05/11/2026'
    "%d/%m/%y",  # '05/11/26'
    "%d-%m-%Y",  # '05-11-2026'
    "%d.%m.%Y",  # '05.11.2026'
]
DATETIME_INPUT_FORMATS = [
    "%d/%m/%Y %H:%M:%S",  # '05/11/2026 14:30:59'
    "%d/%m/%Y %H:%M:%S.%f",  # '05/11/2026 14:30:59.000200'
    "%d/%m/%Y %H:%M",  # '05/11/2026 14:30'
    "%d-%m-%Y %H:%M:%S",  # '05-11-2026 14:30:59'
    "%d-%m-%Y %H:%M",  # '05-11-2026 14:30'
    "%d.%m.%Y %H:%M:%S",  # '05.11.2026 14:30:59'
    "%d.%m.%Y %H:%M",  # '05.11.2026 14:30'
]

DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."
NUMBER_GROUPING = 3

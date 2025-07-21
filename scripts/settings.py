from datetime import timedelta
from whiteneuron.base.settings import _, environ
from whiteneuron.base.settings import *
from dotenv import load_dotenv
load_dotenv()

DATA_UPLOAD_MAX_NUMBER_FILES = environ.get("DATA_UPLOAD_MAX_NUMBER_FILES", 1000)


PROJECT_NAME = environ.get("PROJECT_NAME")
if not PROJECT_NAME:
    print("PROJECT_NAME environment variable is not set")
    sys.exit(1)
NAME= environ.get("NAME", PROJECT_NAME)
if not NAME:
    print("NAME environment variable is not set")
    sys.exit(1)
URL= environ.get("URL", f"https://{PROJECT_NAME.lower()}whiteneuron.com")

######################################################################
# Email
######################################################################
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = environ.get("EMAIL_HOST_USER", "anhnt@whiteneurons.com")
EMAIL_HOST_PASSWORD = environ.get("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", 
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # language
    "django.middleware.locale.LocaleMiddleware",

    # Third-party middleware
    "simple_history.middleware.HistoryRequestMiddleware",

    # My middleware
    "whiteneuron.base.middleware.ReadonlyExceptionHandlerMiddleware",
    "whiteneuron.base.middleware.UserActivityMiddleware",
    'whiteneuron.base.middleware.ThreadLocalMiddleware',
]
######################################################################
# General
######################################################################
BASE_DIR = Path(__file__).resolve().parent.parent
# print(f"BASE_DIR: {BASE_DIR}")

SECRET_KEY = environ.get("SECRET_KEY", get_random_secret_key())
# SECRET_KEY = "django-insecure-secret-key"

DEBUG = environ.get("DEBUG", "False") == "True"
# DEBUG = False

ROOT_URLCONF = f"{PROJECT_NAME}.urls"

BROWSER_RELOAD = environ.get("BROWSER_RELOAD", "False") == "True"

USE_CACHE = environ.get("USE_CACHE", "False") == "True"
USE_CACHE = False

WSGI_APPLICATION = f"{PROJECT_NAME}.wsgi.application"

######################################################################
# Domains
######################################################################
ALLOWED_HOSTS = environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
# ALLOWED_HOSTS.append('192.168.50.106')
# ALLOWED_HOSTS.append('172.16.56.189')

CSRF_TRUSTED_ORIGINS = environ.get(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:8000"
).split(",")

######################################################################
# CORS Settings
######################################################################
# CORS_ALLOWED_ORIGINS = [
#     "http://127.0.0.1:5500",
#     "http://localhost:5500",
#     "http://127.0.0.1:3000",
#     "http://localhost:3000",
#     "http://127.0.0.1:8000",
#     "http://localhost:8000",
#     # mọi origin khác
#     "*"
# ]

# # Cho phép tất cả origins trong development
# if DEBUG:
CORS_ALLOW_ALL_ORIGINS = True
# else:
#     CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

INSTALLED_APPS += [
    "djmoney",
    "apps.scripts",
    "apps.team_board",
    "apps.menu_master",
    "apps.table_flow",
    "apps.order_station",
    "apps.kitchen_flow",
    'apps.cashier',
    "apps.features",
    "apps.dineindex",
    "apps.authen",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_yasg",
]

if DEBUG:
    if "debug_toolbar" not in INSTALLED_APPS:
        INSTALLED_APPS += ["debug_toolbar"]
else:
    try:
        INSTALLED_APPS.remove("debug_toolbar")
    except ValueError:
        pass

if BROWSER_RELOAD:
    if "django_browser_reload.middleware.BrowserReloadMiddleware" not in MIDDLEWARE:
        MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")
else:
    try:
        MIDDLEWARE.remove("django_browser_reload.middleware.BrowserReloadMiddleware")
    except ValueError:
        pass

if USE_CACHE:
    CACHENAME = environ.get("CACHENAME", "default")
    if CACHENAME == "default":
        CACHES= {'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }}
    elif CACHENAME == "redis":
        CACHES= {"default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": environ.get("CACHE_REDIS_LOCATION", None),
        }}
        if not CACHES["default"]["LOCATION"]:
            print("CACHE_REDIS_LOCATION not set")
            sys.exit(1)
    else:
        print("Unknown cache backend")
        sys.exit(1)
    MIDDLEWARE = ["django.middleware.cache.UpdateCacheMiddleware"] + MIDDLEWARE + ["django.middleware.cache.FetchFromCacheMiddleware"]

if DEBUG:
    if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:
        MIDDLEWARE= ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
        INTERNAL_IPS = ["127.0.0.1"]
else:
    try:
        MIDDLEWARE.remove("debug_toolbar.middleware.DebugToolbarMiddleware")
    except ValueError:
        pass

# Add CORS middleware
if "corsheaders.middleware.CorsMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")

######################################################################
# Templates
######################################################################
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [Path.joinpath(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

######################################################################
# Databases
######################################################################
DATABASE= environ.get("DATABASE", "sqlite")
DBROOT= BASE_DIR
# DBROOT=Path("/Users/tanh.left/Projects/HOYA-Problem4/DATA-1")
if DATABASE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DBROOT / "db.sqlite3",
        },
    }
elif DATABASE == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": environ.get("DATABASE_NAME"),
            "USER": environ.get("DATABASE_USER"),
            "PASSWORD": environ.get("DATABASE_PASSWORD"),
            "HOST": environ.get("DATABASE_HOST"),
            "PORT": environ.get("DATABASE_PORT"),
        }
    }

######################################################################
# Languages
######################################################################

LANGUAGE_CODE = 'vi'

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

######################################################################
# Static
######################################################################
STATIC_URL = "static/"

import whiteneuron
WHITENEURON_PATH = Path(whiteneuron.__file__).parent
STATICFILES_DIRS = [
    BASE_DIR / "static",
    WHITENEURON_PATH / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_ROOT = DBROOT / "media"

MEDIA_URL = "/media/"

if DEBUG:
    STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    STORAGES["staticfiles"]["BACKEND"] =  "whitenoise.storage.CompressedStaticFilesStorage"

######################################################################
# Unfold
######################################################################
UNFOLD['SITE_HEADER'] = _(NAME)
UNFOLD['SITE_TITLE'] = _(NAME)
UNFOLD['ENVIRONMENT'] = f"{PROJECT_NAME}.utils.environment_callback"
UNFOLD['STYLES']= [lambda request: static("css/styles.css")] + UNFOLD['STYLES']
UNFOLD["SCRIPTS"].append(lambda request: static("js/wndinehub.js"))
UNFOLD['SHOW_LANGUAGES'] = True
UNFOLD['DASHBOARD_CALLBACK'] = "apps.dineindex.views.dashboard_callback"
navigations=[
    {
        "title": _("Home"),
        'collapsible': False,
        "items": [
            {
                "title": _("Order Flow"),
                "icon": "restaurant_menu",
                "link": reverse_lazy("admin:features_orderflow_changelist"),
            },
            # {
            #     "title": _("Kitchen Flow"),
            #     "icon": "kitchen",
            #     "link": reverse_lazy("admin:features_kitchenflow_changelist"),
            # },
            # {
            #     "title": _("Served Flow"),
            #     "icon": "sprint",
            #     "link": reverse_lazy("admin:features_preparedorderitem_changelist"),
            # },
            {
                "title": _("Coordination Flow"),
                "icon": "restaurant_menu",
                "link": reverse_lazy("admin:features_coordinationmenuitem_changelist"),
            },
            {
                "title": _("Checkout Flow"),
                "icon": "payment",
                "link": reverse_lazy("admin:features_checkoutflow_changelist"),
            },
            {
                "title": _("Invoice Flow"),
                "icon": "receipt",
                "link": reverse_lazy("admin:features_invoiceflow_changelist"),
            },
            # TableBookingAdmin
            # {
            #     "title": _("Table Bookings"),
            #     "icon": "event_seat",
            #     "link": reverse_lazy("admin:features_bookingflow_changelist"),
            # },
            {
                "title": _("Order Table Merges"),
                "icon": "event_seat",
                "link": reverse_lazy("admin:order_station_ordertablemerge_changelist"),
            },
            {
                "title": _("Invoice Reverts"),
                "icon": "receipt",
                "link": reverse_lazy("admin:cashier_invoicerevert_changelist"),
            },
            {
                "title": _("Payment Slips"),
                "icon": "payment",
                "link": reverse_lazy("admin:cashier_paymentslip_changelist"),
            },
            {
                "title": _("Cancellation Requests"),
                "icon": "cancel",
                "link": reverse_lazy("admin:order_station_orderitemcancellationrequest_changelist"),
            }, 
        ]
    },
    {
        "title": _("Admin site"),
        "collapsible": True,
        "items": [
            {
                "title": _("Orders"),
                "icon": "receipt_long",
                "link": reverse_lazy("admin:order_station_order_changelist"),
                "badge": "apps.order_station.unfold.order_badge_callback",
            },
            {
                "title": _("Order Items"),
                "icon": "list_alt",
                "link": reverse_lazy("admin:order_station_orderitem_changelist"),
                "badge": "apps.order_station.unfold.order_item_badge_callback",
            },
            {
                "title": _("Kitchen Stations"),
                "icon": "kitchen",
                "link": reverse_lazy("admin:kitchen_flow_kitchenstation_changelist"),
                "badge": "apps.kitchen_flow.unfold.kitchen_station_badge_callback",
            },
            {
                "title": _("Payments"),
                "icon": "payment",
                "link": reverse_lazy("admin:cashier_payment_changelist"),
                "badge": "apps.cashier.unfold.payment_badge_callback",
            },
            {
                "title": _("Invoices"),
                "icon": "receipt",
                "link": reverse_lazy("admin:cashier_invoice_changelist"),
                "badge": "apps.cashier.unfold.invoice_badge_callback",
            },
            {
                "title": _("Payment Methods"),
                "icon": "keyboard_keys",
                "link": reverse_lazy("admin:cashier_paymentmethod_changelist"),
                "badge": "apps.cashier.unfold.payment_method_badge_callback",
            },
            {
                "title": _("Item Categories"),
                "icon": "category",
                "link": reverse_lazy("admin:menu_master_itemcategory_changelist"),
                "badge": "apps.menu_master.unfold.item_category_badge_callback",
            },
            {
                "title": _("Menu Items"),
                "icon": "restaurant_menu",
                "link": reverse_lazy("admin:menu_master_menuitem_changelist"),
                "badge": "apps.menu_master.unfold.menu_item_badge_callback",
            },
            {
                "title": _("Dining Tables"),
                "icon": "table_restaurant",
                "link": reverse_lazy("admin:table_flow_diningtable_changelist"),
                "badge": "apps.table_flow.unfold.dining_table_badge_callback",
            },
            {
                "title": _("Table Bookings"),
                "icon": "event_seat",
                "link": reverse_lazy("admin:table_flow_tablebooking_changelist"),
                "badge": "apps.table_flow.unfold.table_booking_badge_callback",
            },
            {
                "title": _("Order Bookings"),
                "icon": "event_seat",
                "link": reverse_lazy("admin:table_flow_orderbooking_changelist"),
                "badge": "apps.table_flow.unfold.order_booking_badge_callback",
            },
            {
                "title": _("Order Booking Items"),
                "icon": "event_seat",
                "link": reverse_lazy("admin:table_flow_orderbookingitem_changelist"),
                "badge": "apps.table_flow.unfold.order_booking_item_badge_callback",
            },
            {
                "title": _("Shifts"),
                "icon": "event_seat",
                "link": reverse_lazy("admin:table_flow_shift_changelist"),
                "badge": "apps.table_flow.unfold.shift_badge_callback",
            },
            {
                "title": _("Booking Table Merges"),
                "icon": "event_seat",
                "link": reverse_lazy("admin:table_flow_bookingtablemerge_changelist"),
                "badge": "apps.table_flow.unfold.booking_table_merge_badge_callback",
            },
            {
                "title": _("Employees"),
                "icon": "diversity_3",
                "link": reverse_lazy("admin:team_board_employee_changelist"),
                "badge": "apps.team_board.unfold.employee_badge_callback",
            },
            {
                "title": _("Payment Slip Categories"),
                "icon": "payment",
                "link": reverse_lazy("admin:cashier_paymentslipcategory_changelist"),
                "badge": "apps.cashier.unfold.payment_slip_category_badge_callback",
            },
            {
                "title": _("Payment Slips"),
                "icon": "payment",
                "link": reverse_lazy("admin:cashier_paymentslip_changelist"),
                "badge": "apps.cashier.unfold.payment_slip_badge_callback",
            },
            # order table merge
            {
                "title": _("Order Table Merges"),
                "icon": "event_seat",
                "link": reverse_lazy("admin:order_station_ordertablemerge_changelist"),
                "badge": "apps.order_station.unfold.order_table_merge_badge_callback",
            },

        ]
    },
]
USING_FILE_MANAGEMENT_APP= False
USING_CELERY_TASKS_APP= True
apps_root= UNFOLD['SIDEBAR']['navigation'][:]
if not USING_FILE_MANAGEMENT_APP:
    apps_root= apps_root[:1] + apps_root[2:] # remove File Management app if it exists
if not USING_CELERY_TASKS_APP:
    apps_root= apps_root[:-1] # remove Celery Tasks app if it exists

UNFOLD['SIDEBAR']['navigation']= navigations + apps_root
UNFOLD["TABS"]= [
    {
        "models": [
                "features.coordinationmenuitem",
                "features.coordinationtablelistall",
            ],
       "items": [
        {
            "title": _("Coordination Menu Items"),
            "icon": "restaurant_menu",
            "link": reverse_lazy("admin:features_coordinationmenuitem_changelist"),
        },
        {
            "title": _("Coordination Tables List All"),
            "icon": "restaurant_menu",
            "link": reverse_lazy("admin:features_coordinationtablelistall_changelist"),
        },
       ]
    }
]
######################################################################
# Sentry
######################################################################
SENTRY_DSN = environ.get("SENTRY_DSN")

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        enable_tracing=False,
    )

######################################################################
# Celery
######################################################################
CELERY_BROKER_URL = environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND= CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Celery Beat Settings
CELERY_BEAT_SCHEDULE = {
    'notify-shift-start-every-minute': {
        'task': 'apps.table_flow.tasks.notify_shift_start',
        'schedule': 60.0,  # Chạy mỗi phút
    },
    # 'test-task': {
    #     'task': 'apps.table_flow.tasks.test_task',
    #     'schedule': 10.0,  # Chạy mỗi phút gọi mỗi 10s
    # },

}

########################################################################
# Timezone
########################################################################
TIME_ZONE = environ.get("TIME_ZONE", "UTC")
USE_TZ = True

######################################################################
# REST Framework
######################################################################
REST_FRAMEWORK = {
    "COERCE_DECIMAL_TO_STRING": False,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

######################################################################
# Simple JWT
######################################################################

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': "apiKey",
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
        }
    },
    'USE_SESSION_AUTH': False,
}
TIME_ZONE = 'Asia/Ho_Chi_Minh'
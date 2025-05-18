from os import environ
import sys
from pathlib import Path
from dotenv import load_dotenv
from django.core.management.utils import get_random_secret_key
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
load_dotenv()

import sentry_sdk

DATA_UPLOAD_MAX_NUMBER_FILES = environ.get("DATA_UPLOAD_MAX_NUMBER_FILES", 1000)

PROJECT_NAME = environ.get("PROJECT_NAME", "WN")
NAME= environ.get("NAME", "White Neuron")
URL= environ.get("URL", f"https://{PROJECT_NAME.lower()}whiteneuron.com")

DATA_UPLOAD_MAX_NUMBER_FIELDS = 20000

######################################################################
# Email
######################################################################
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = environ.get("EMAIL_HOST_USER", "anhnt@whiteneurons.com")
EMAIL_HOST_PASSWORD = environ.get("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True

######################################################################
# General
######################################################################
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = environ.get("SECRET_KEY", get_random_secret_key())

DEBUG = environ.get("DEBUG", "False") == "True"
# DEBUG = False

ROOT_URLCONF = f"{PROJECT_NAME}.urls"

BROWSER_RELOAD = environ.get("BROWSER_RELOAD", "False") == "True"

USE_CACHE = environ.get("USE_CACHE", "False") == "True"
# USE_CACHE = False

WSGI_APPLICATION = f"{PROJECT_NAME}.wsgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

######################################################################
# Domains
######################################################################
ALLOWED_HOSTS = environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
ALLOWED_HOSTS.append("192.168.88.115")
ALLOWED_HOSTS.append("192.168.50.164")
ALLOWED_HOSTS.append("192.168.50.2")
ALLOWED_HOSTS.append("172.20.10.2")
ALLOWED_HOSTS.append("172.20.0.1")

CSRF_TRUSTED_ORIGINS = environ.get(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:8000"
).split(",")

######################################################################
# Apps
######################################################################
INSTALLED_APPS = [
    "whiteneuron",
    "whiteneuron.base", # Base app
    "whiteneuron.feedbacks", # Feedbacks app
    "whiteneuron.file_management", # File management app
    "whiteneuron.contrib", # Contrib app
    "whiteneuron.dashboard",

    "modeltranslation",
    "unfold",
    "unfold.contrib.filters",  # optional, if special filters are needed
    "unfold.contrib.forms",  # optional, if special form elements are needed
    "unfold.contrib.inlines",  # optional, if special inlines are needed
    "unfold.contrib.import_export",  # optional, if django-import-export package is used
    "unfold.contrib.guardian",  # optional, if django-guardian package is used
    "unfold.contrib.simple_history",  # optional, if django-simple-history package is used

    "crispy_forms", # Crispy forms
]
if BROWSER_RELOAD:
    INSTALLED_APPS.append("django_browser_reload")

INSTALLED_APPS += [
    "colorfield",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "import_export",
    "guardian",
    "simple_history",
    "django_celery_beat",

    # Apps from the project
]

if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]

######################################################################
# Middleware
######################################################################
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
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
]

if BROWSER_RELOAD:
    MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")

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

# settings.py
DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
]

if DEBUG:
    MIDDLEWARE= ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
    INTERNAL_IPS = ["127.0.0.1"]

######################################################################
# Sessions
######################################################################
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

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
# Authentication
######################################################################
AUTH_USER_MODEL = "base.User"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_URL = "admin:login"

LOGIN_REDIRECT_URL = reverse_lazy("admin:index")

# Internationalization
LANGUAGE_CODE = "en"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

LANGUAGES = [
    ("en", _("English")),
    ("vi", _("Vietnamese")),
]

MODELTRANSLATION_DEFAULT_LANGUAGE = 'vi'
MODELTRANSLATION_LANGUAGES = ('vi', 'en')

# https://docs.djangoproject.com/en/5.1/ref/settings/#date-input-formats
DATE_INPUT_FORMATS = [
    "%d.%m.%Y",  # Custom input
    "%Y-%m-%d",  # '2006-10-25'
    "%m/%d/%Y",  # '10/25/2006'
    "%m/%d/%y",  # '10/25/06'
    "%b %d %Y",  # 'Oct 25 2006'
    "%b %d, %Y",  # 'Oct 25, 2006'
    "%d %b %Y",  # '25 Oct 2006'
    "%d %b, %Y",  # '25 Oct, 2006'
    "%B %d %Y",  # 'October 25 2006'
    "%B %d, %Y",  # 'October 25, 2006'
    "%d %B %Y",  # '25 October 2006'
    "%d %B, %Y",  # '25 October, 2006'
]

# https://docs.djangoproject.com/en/5.1/ref/settings/#datetime-input-formats
DATETIME_INPUT_FORMATS = [
    "%d.%m.%Y %H:%M:%S",  # Custom input
    "%Y-%m-%d %H:%M:%S",  # '2006-10-25 14:30:59'
    "%Y-%m-%d %H:%M:%S.%f",  # '2006-10-25 14:30:59.000200'
    "%Y-%m-%d %H:%M",  # '2006-10-25 14:30'
    "%m/%d/%Y %H:%M:%S",  # '10/25/2006 14:30:59'
    "%m/%d/%Y %H:%M:%S.%f",  # '10/25/2006 14:30:59.000200'
    "%m/%d/%Y %H:%M",  # '10/25/2006 14:30'
    "%m/%d/%y %H:%M:%S",  # '10/25/06 14:30:59'
    "%m/%d/%y %H:%M:%S.%f",  # '10/25/06 14:30:59.000200'
    "%m/%d/%y %H:%M",  # '10/25/06 14:30'
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

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

if DEBUG:
    STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"

######################################################################
# Unfold
######################################################################
UNFOLD = {
    "SITE_HEADER": _(NAME), 
    "SITE_TITLE": _(NAME),
    "SITE_SUBHEADER": _("Admin panel"),
    "SITE_DROPDOWN": [
        {
            "icon": "diamond",
            "title": _("White Neuron Co. Ltd."),
            "link": "https://whiteneuron.com/",
        },
        {
            "icon": "rocket_launch",
            "title": _("Email: anhnt@whiteneuron.com"),
            "link": "mailto:anhnt@whiteneuron.com",
        },
    ],
    # Nếu không có SITE_LOGO thì sẽ sử dụng SITE_ICON, nếu dùng SITE_LOGO thì sẽ không sử dụng SITE_ICON và SITE_TITLE
    # Vì vậy nên dùng SITE_ICON để đảm bảo hiển thị đúng
    "SITE_ICON": {
        "light": lambda request: static("base/images/logo/WhiteNeuron.png"),  # light mode
        "dark": lambda request: static("base/images/logo/WhiteNeuron.png"),  # dark mode
    },
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("base/images/logo/WhiteNeuron.png"),
        },
    ],
    "SHOW_HISTORY": False,
    "SHOW_LANGUAGES": True,
    "SHOW_VIEW_ON_SITE": True, # show/hide "View on site" button, default: True
    "SHOW_BACK_BUTTON": True, # show/hide "Back" button on changeform in header, default: False
    "ENVIRONMENT": f"{PROJECT_NAME}.utils.environment_callback",
    "DASHBOARD_CALLBACK": "whiteneuron.dashboard.views.dashboard_callback",
    "LOGIN": {
        "image": lambda request: static("base/images/login-bg.jpg"),
    },
    "STYLES": [
        lambda request: static("base/css/styles.css"),
        lambda request: static("base/css/btn-styles.css"),
        lambda request: static("base/css/loading.css"),
    ],
    "SCRIPTS": [
        lambda request: static("base/js/loading.js"),
    ],
    "COLORS": {
        "font": {
            "subtle-light": "107 114 128",
            "subtle-dark": "156 163 175",
            "default-light": "75 85 99",
            "default-dark": "209 213 219",
            "important-light": "17 24 39",
            "important-dark": "243 244 246",
        },
        "primary": {
            "50": "240 249 255",
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56 189 248",
            "500": "14 165 233",
            "600": "2 132 199",
            "700": "3 105 161",
            "800": "7 89 133",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
    "EXTENSIONS": {
        "modeltranslation": {
            "flags": {
                "en": "🇬🇧",
                "vi": "🇻🇳",
            },
        },
    },
    "TABS": [
        # "apps.projects.tabs.tabs_callback"
    ],
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Navigation"),
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": _("Notifications"),
                        "icon": "notifications",
                        "link": reverse_lazy("admin:base_notification_changelist"),
                        "badge": "whiteneuron.base.utils.notification_badge_callback",
                    },
                    {
                        "title": _("Feedbacks"),
                        "icon": "feedback",
                        "link": reverse_lazy("admin:feedbacks_feedbackdata_changelist"),
                        "badge": "whiteneuron.feedbacks.utils.feedback_data_badge_callback",
                    },
                ],
            },
            {
                "title": _("File Management"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Excel Files"),
                        "icon": "table",
                        "link": reverse_lazy("admin:file_management_excelfile_changelist"),
                        "badge": "whiteneuron.file_management.utils.excelfile_badge_callback",
                        "permission": "whiteneuron.base.utils.permission_non_guest_callback",
                    },
                    {
                        "title": _("PDF Files"),
                        "icon": "picture_as_pdf",
                        "link": reverse_lazy("admin:file_management_pdffile_changelist"),
                        "badge": "whiteneuron.file_management.utils.pdffile_badge_callback",
                        "permission": "whiteneuron.base.utils.permission_non_guest_callback",
                    },
                ],
            },
            {
                "title": _("Users & Groups"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy("admin:base_user_changelist"),
                        "badge": "whiteneuron.base.utils.user_badge_callback",
                        "permission": "whiteneuron.base.utils.permission_admin_callback",
                    },
                    {
                        "title": _("User activity"),
                        "icon": "history",
                        "link": reverse_lazy("admin:base_useractivity_changelist"),
                        "badge": "whiteneuron.base.utils.useractivity_badge_callback",
                        "permission": "whiteneuron.base.utils.permission_admin_callback",
                    },
                    {
                        "title": _("Groups"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "badge": "whiteneuron.base.utils.group_badge_callback",
                        "permission": "whiteneuron.base.utils.permission_admin_callback",
                    },
                ],
            },
            {
                "title": _("System"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Images"),
                        "icon": "image",
                        "link": reverse_lazy("admin:base_image_changelist"),
                        "permission": "whiteneuron.base.utils.permission_superuser_callback",
                    },
                    {
                        "title": _("Emails"),
                        "icon": "email",
                        "link": reverse_lazy("admin:base_mail_changelist"),
                        "permission": "whiteneuron.base.utils.permission_superuser_callback",
                    },
                ],
            },
            {
                "title": _("Celery Tasks"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Clocked"),
                        "icon": "hourglass_bottom",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_clockedschedule_changelist"
                        ),
                        "permission": "whiteneuron.base.utils.permission_superuser_callback",
                    },
                    {
                        "title": _("Crontabs"),
                        "icon": "update",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_crontabschedule_changelist"
                        ),
                        "permission": "whiteneuron.base.utils.permission_superuser_callback",
                    },
                    {
                        "title": _("Intervals"),
                        "icon": "arrow_range",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_intervalschedule_changelist"
                        ),
                        "permission": "whiteneuron.base.utils.permission_superuser_callback",
                    },
                    {
                        "title": _("Periodic tasks"),
                        "icon": "task",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_periodictask_changelist"
                        ),
                        "permission": "whiteneuron.base.utils.permission_superuser_callback",
                    },
                    {
                        "title": _("Solar events"),
                        "icon": "event",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_solarschedule_changelist"
                        ),
                        "permission": "whiteneuron.base.utils.permission_superuser_callback",
                    },
                ],
            },
        ],
    },
}

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
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

######################################################################
# CRISPY FORMS
######################################################################
CRISPY_TEMPLATE_PACK = "unfold_crispy"
CRISPY_ALLOWED_TEMPLATE_PACKS = ["unfold_crispy"]
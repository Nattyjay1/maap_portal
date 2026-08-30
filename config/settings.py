import os
from pathlib import Path

import dj_database_url


# BASE DIRECTORY

BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY

# Railway will use the SECRET_KEY environment variable.
# The fallback is only for local development.
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-local-development-only-change-this"
)


# Local development defaults to True.
# On Railway, set:
# DEBUG=False
DEBUG = os.environ.get("DEBUG", "True").lower() in (
    "true",
    "1",
    "yes",
    "on",
)

# ALLOWED HOSTS

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "ALLOWED_HOSTS",
        "127.0.0.1,localhost,jaynats.pythonanywhere.com"
    ).split(",")
    if host.strip()
]


# Railway can provide its public domain through this variable.
RAILWAY_PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN")

if (
    RAILWAY_PUBLIC_DOMAIN
    and RAILWAY_PUBLIC_DOMAIN not in ALLOWED_HOSTS
):
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)


# CSRF TRUSTED ORIGINS

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        ""
    ).split(",")
    if origin.strip()
]

if RAILWAY_PUBLIC_DOMAIN:
    railway_origin = f"https://{RAILWAY_PUBLIC_DOMAIN}"

    if railway_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(railway_origin)

# APPLICATIONS

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Unified Access Portal apps
    "accounts",
    "core",
    "academics",
    "evaluations",
    "formsrepo",
    "analytics_app",
    "reports",
    "materials",
]

# MIDDLEWARE

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Serve static files in production
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# URL CONFIGURATION

ROOT_URLCONF = "config.urls"


# TEMPLATES

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# WSGI

WSGI_APPLICATION = "config.wsgi.application"


# DATABASE

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
        )
    }

else:

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# PASSWORD VALIDATION

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator",
    },
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator",
    },
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator",
    },
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator",
    },
]


# INTERNATIONALIZATION

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# STATIC FILES

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# MEDIA FILES


MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# DEFAULT PRIMARY KEY

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# CUSTOM USER MODEL


AUTH_USER_MODEL = "accounts.CustomUser"


# AUTHENTICATION / LOGIN

LOGIN_URL = "login"

LOGIN_REDIRECT_URL = "role-redirect"

LOGOUT_REDIRECT_URL = "login"


# PRODUCTION / RAILWAY SECURITY

# Railway terminates HTTPS before forwarding requests to Django.
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)


# Enable secure cookies when DEBUG=False.
SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SECURE = not DEBUG
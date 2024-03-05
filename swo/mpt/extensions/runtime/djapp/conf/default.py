"""
Django settings for pippo project.

Generated by 'django-admin startproject' using Django 4.2.8.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-6r_%9ku+bg0=@xw1ah$wh+liwbsyhwpn#6alt*ppjn8t_uyp-u"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "swo.mpt.extensions.runtime.djapp.apps.DjAppConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "swo.mpt.extensions.runtime.djapp.middleware.MPTClientMiddleware",
]

ROOT_URLCONF = "swo.mpt.extensions.runtime.djapp.conf.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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



# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# OpenTelemetry configuration
SERVICE_NAME = os.getenv("SERVICE_NAME", "Swo.Extensions.SwoDefaultExtensions")
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
LOGGING_ATTEMPT_GETTER = os.getenv("LOGGING_ATTEMPT_GETTER", "adobe_vipm.utils.get_attempt_count")
USE_APPLICATIONINSIGHTS = APPLICATIONINSIGHTS_CONNECTION_STRING != ""

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "(pid={process:d} thread={thread:d}) {message}",
            "style": "{",
        },
        "rich": {
            "format": "{message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "rich": {
            "class": "swo.mpt.extensions.runtime.logging.RichHandler",
            "formatter": "rich",
            "log_time_format": lambda x: x.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "rich_tracebacks": True,
        },
    },
    "root": {
        "handlers": ["rich"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["rich"],
            "level": "INFO",
            "propagate": False,
        },
        "swo.mpt.extensions.runtime": {
            "handlers": ["rich"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Proxy settings
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# MPT settings

MPT_API_BASE_URL = os.getenv("MPT_API_BASE_URL", "http://localhost:8000")
MPT_API_TOKEN = os.getenv("MPT_API_TOKEN", "change-me!")
MPT_PRODUCT_ID = os.getenv("MPT_PRODUCT_ID", "PRD-1111-1111-1111")

ORDERS_API_POLLING_INTERVAL_SECS = 30

EXTENSION_CONFIG = {}

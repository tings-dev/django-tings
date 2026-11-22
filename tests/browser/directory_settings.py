"""Settings for the standalone browser consumer."""

from pathlib import Path

SECRET_KEY = "directory-browser-tests"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1"]
ROOT_URLCONF = "directory"
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django_tables2",
    "django_tings.interactive_table",
]
STATIC_URL = "/static/"
MIDDLEWARE = [
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [Path(__file__).parent / "templates"],
        "OPTIONS": {
            "context_processors": ["django.template.context_processors.request"]
        },
    }
]
LANGUAGE_CODE = "en"

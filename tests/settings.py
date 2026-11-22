SECRET_KEY = "table-tests"
INSTALLED_APPS = ["django_tables2", "django_tings.interactive_table"]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": ["django.template.context_processors.request"]
        },
    }
]
LANGUAGE_CODE = "en"
ROOT_URLCONF = "tests.test_engine_views"
STATIC_URL = "/static/"

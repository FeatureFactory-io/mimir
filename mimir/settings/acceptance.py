"""Django-client acceptance runner; never point at an existing runtime database."""

from .test import *

INSTALLED_APPS = [*INSTALLED_APPS, "behave_django"]

# This new runner owns an in-memory test DB regardless of ambient DATABASE_URL.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

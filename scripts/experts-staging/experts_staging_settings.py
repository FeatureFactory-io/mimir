"""Companion-only production overlay; never used by the normal EB entrypoint."""

import os
from pathlib import Path

import dj_database_url
from mimir.settings.prod import *

MIMIR_ENV = "experts_staging"
DEBUG = False
ALLOWED_HOSTS = ["cedar-web", "localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["https://cedar-web:8443"]
FRONTEND_URL = "https://cedar-web:8443"
DATABASES = {
    "default": dj_database_url.parse(
        os.environ["DATABASE_URL"], conn_max_age=0, ssl_require=False
    )
}
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = "/experts-mail"
DEFAULT_FROM_EMAIL = "cedar-recording@example.com"
EXPERTS_STAGING_SCOPE_ROOT = Path("/experts-scope")
STATIC_ROOT = Path("/experts-static")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = None
AWS_EC2_METADATA_DISABLED = True
GALDR_USE_ANTHROPIC = False
BUG_REPORT_DRY_RUN = True

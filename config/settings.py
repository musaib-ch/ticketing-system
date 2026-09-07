"""Settings shared by local development and production deployments."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name, default=''):
    return [value.strip() for value in os.getenv(name, default).split(',') if value.strip()]


DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-local-development-only-change-before-production'
    else:
        raise RuntimeError('DJANGO_SECRET_KEY must be set when DJANGO_DEBUG=False.')

ALLOWED_HOSTS = env_list(
    'DJANGO_ALLOWED_HOSTS',
    '127.0.0.1,localhost,.trycloudflare.com' if DEBUG else ''
)

CSRF_TRUSTED_ORIGINS = env_list(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    'https://*.trycloudflare.com' if DEBUG else ''
)

SITE_URL = os.getenv('SITE_URL', 'http://127.0.0.1:8000').rstrip('/')

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'corsheaders', 'users', 'tickets',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'users.middleware.ProfileCompletionMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug', 'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages',
        'users.context_processors.branding',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Development uses SQLite. Set POSTGRES_DB and the other POSTGRES_* variables
# in production to select PostgreSQL.
if not DEBUG and not os.getenv('POSTGRES_DB'):
    raise RuntimeError('POSTGRES_DB must be set when DJANGO_DEBUG=False.')

if os.getenv('POSTGRES_DB'):
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql', 'NAME': os.environ['POSTGRES_DB'],
        'USER': os.environ['POSTGRES_USER'], 'PASSWORD': os.environ['POSTGRES_PASSWORD'],
        'HOST': os.getenv('POSTGRES_HOST', '127.0.0.1'), 'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': int(os.getenv('POSTGRES_CONN_MAX_AGE', '60')),
        'OPTIONS': {'sslmode': os.getenv('POSTGRES_SSLMODE', 'require')},
    }}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('DJANGO_TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise serves static assets directly from the Render web service.
# Uploaded media is local by default for development, but can be moved to an
# S3-compatible store (including Supabase Storage) in production by setting
# AWS_STORAGE_BUCKET_NAME and AWS_S3_ENDPOINT_URL.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

if os.getenv('AWS_STORAGE_BUCKET_NAME'):
    STORAGES['default'] = {'BACKEND': 'storages.backends.s3.S3Storage'}
    AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
    AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', '') or None
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'ap-southeast-1')
    AWS_S3_ADDRESSING_STYLE = os.getenv('AWS_S3_ADDRESSING_STYLE', 'path')
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = os.getenv('AWS_QUERYSTRING_AUTH', 'True').lower() == 'true'
    AWS_S3_FILE_OVERWRITE = False

# Local development authenticates against mock_ad.xlsx. Production allows only
# Microsoft Entra ID SSO, initiated by the application callback in users.views.
MS_SSO_ENABLED = not DEBUG and all(os.getenv(name) for name in ('MS_CLIENT_ID', 'MS_CLIENT_SECRET', 'MS_TENANT_ID'))
if not DEBUG and not MS_SSO_ENABLED:
    raise RuntimeError('MS_CLIENT_ID, MS_CLIENT_SECRET, and MS_TENANT_ID must be set when DJANGO_DEBUG=False.')
AUTHENTICATION_BACKENDS = (
    ['users.auth.DummyADBackend', 'django.contrib.auth.backends.ModelBackend'] if DEBUG
    else ['django.contrib.auth.backends.ModelBackend']
)

EMAIL_BACKEND = os.getenv('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@localhost')

# Inbound email configuration. Both the Celery task and management command use
# these same names so deployments cannot accidentally configure one path only.
IMAP_HOST = os.getenv('IMAP_HOST', os.getenv('IMAP_SERVER', ''))
IMAP_USER = os.getenv('IMAP_USER', '')
IMAP_PASSWORD = os.getenv('IMAP_PASSWORD', '')
IMAP_FOLDER = os.getenv('IMAP_FOLDER', 'INBOX')

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS')
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# The browsable API is only ever used by the logged-in web app itself (see the
# ticket "viewing" presence endpoint), so it authenticates via the same
# session cookie as the rest of the site. There is no separate API client, so
# no token-based auth is exposed here - one less unauthenticated endpoint to
# secure and rate-limit.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework.authentication.SessionAuthentication',),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
}

# Upload limits enforced in tickets.utils.validate_uploaded_file and on
# model FileField validators.
MAX_ATTACHMENT_SIZE_MB = int(os.getenv('MAX_ATTACHMENT_SIZE_MB', '10'))
MAX_IMAGE_SIZE_MB = int(os.getenv('MAX_IMAGE_SIZE_MB', '5'))

# The CSRF token is only ever read out of the rendered template ({{ csrf_token }}),
# never out of the cookie via JavaScript, so the cookie itself can be locked down.
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'

# Shared cache backend. In production this must be shared across all
# app-server processes/workers (e.g. Redis) - the "who else is viewing this
# ticket" presence indicator (tickets.api.TicketViewSet.viewing) stores its
# state here, and a process-local cache would make it work inconsistently
# behind more than one worker.
REDIS_CACHE_URL = os.getenv('REDIS_CACHE_URL', '')
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    } if DEBUG or not REDIS_CACHE_URL else {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_CACHE_URL,
    }
}

# Send errors to the console/process log so they reach whatever the deployment
# already collects (journald, Docker log driver, etc.) without needing extra
# infrastructure. DEBUG=True keeps Django's own debug page instead.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

if not DEBUG:
    # Cloudflare terminates TLS and forwards plain HTTP to the origin server.
    # Setting SECURE_SSL_REDIRECT=True here would cause an infinite redirect loop
    # because Django would always see the incoming request as HTTP.
    # Cloudflare itself enforces HTTPS for end-users, so we disable the redirect.
    SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', 'False').lower() == 'true'

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Trust the X-Forwarded-Proto header injected by Cloudflare / Nginx so that
    # Django knows the original request was HTTPS.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Use the Host header forwarded by Cloudflare instead of the raw server host.
    USE_X_FORWARDED_HOST = True

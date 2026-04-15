import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-secret')
DEBUG = os.environ.get('DEBUG', '0') == '1'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'gateway.middleware.JWTValidationMiddleware',
]

ROOT_URLCONF = 'gateway.urls'
TEMPLATES = []
WSGI_APPLICATION = 'gateway.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

RESERVATION_SERVICE_URL = os.environ.get('RESERVATION_SERVICE_URL', 'http://reservation_service:8001')
WEB_APP_URL = os.environ.get('WEB_APP_URL', 'http://web_app:3000')
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'change_this_to_a_long_random_string')

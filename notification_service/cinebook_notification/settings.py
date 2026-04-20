import os

SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = os.environ.get("EMAIL_FROM", "noreply@cinebook.local")

USE_TZ = True
TIME_ZONE = "UTC"

"""WSGI entry point - used by gunicorn/waitress for production serving."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ngo_platform.settings")

application = get_wsgi_application()
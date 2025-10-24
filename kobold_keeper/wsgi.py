"""
WSGI config for the kobold_keeper project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kobold_keeper.settings')

application = get_wsgi_application()

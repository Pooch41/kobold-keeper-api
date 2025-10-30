"""
Celery worker application configuration for the Kobold Keeper project.
"""

import os

import django
from celery import Celery
from celery.signals import setup_logging
from django.apps import apps

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kobold_keeper.settings')
django.setup()
app = Celery('kobold_keeper')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: [n.name for n in apps.get_app_configs()])


@app.task(bind=True)
def debug_task(self):
    """
    A simple task used for testing and debugging the Celery setup.
    It prints the current request information.
    """
    print(f'Request: {self.request!r}')


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig
    from django.conf import settings
    dictConfig(settings.LOGGING)


if __name__ == '__main__':
    app.start()

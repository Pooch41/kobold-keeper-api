import os
from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kobold_keeper.settings')
app = Celery('kobold_keeper')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """
    A simple task used for testing and debugging the Celery setup.
    It prints the current request information.
    """
    print(f'Request: {self.request!r}')

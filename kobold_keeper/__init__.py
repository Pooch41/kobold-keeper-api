"""
Root package for the Kobold Keeper Django project.

This module ensures the Celery application is imported and available
when Django starts, allowing shared tasks to be defined and executed.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)

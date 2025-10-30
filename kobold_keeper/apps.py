"""
Application configuration for the Kobold Keeper project.

This file is primarily used to configure and register the project's
internal components and metadata with the Django framework.
"""

from django.apps import AppConfig


class KoboldKeeperConfig(AppConfig):
    name = 'kobold_keeper'
    verbose_name = "Kobold Keeper Core"
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        pass

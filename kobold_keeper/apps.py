from django.apps import AppConfig


class KoboldKeeperConfig(AppConfig):
    name = 'kobold_keeper'
    verbose_name = "Kobold Keeper Core"
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        pass

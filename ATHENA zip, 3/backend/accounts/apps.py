from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.accounts'

    def ready(self):
        from .monitor import start_monitor

        start_monitor()

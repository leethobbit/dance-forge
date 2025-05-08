import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "dance_forge.users"
    verbose_name = _("Users")

    def ready(self):
        with contextlib.suppress(ImportError):
            import dance_forge.users.signals  # noqa: F401

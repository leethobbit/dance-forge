from django.apps import AppConfig


class VideosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "videos"

    def ready(self):
        # Import signal handlers when app is ready
        import videos.signals

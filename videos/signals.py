import os

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import Video


@receiver(pre_delete, sender=Video)
def delete_video_files(sender, instance, **kwargs):
    """
    Signal handler to ensure video files are deleted from disk
    when video instances are deleted, even in bulk operations.
    This works as a backup to the model's delete method.
    """
    # Delete the physical video file
    if (
        instance.file
        and hasattr(instance.file, "path")
        and os.path.isfile(instance.file.path)
    ):
        try:
            os.remove(instance.file.path)
        except (OSError, PermissionError) as e:
            # Log the error but continue with instance deletion
            print(f"Signal: Error deleting video file {instance.file.path}: {e}")

    # Delete the physical thumbnail file
    if (
        instance.thumbnail
        and hasattr(instance.thumbnail, "path")
        and os.path.isfile(instance.thumbnail.path)
    ):
        try:
            os.remove(instance.thumbnail.path)
        except (OSError, PermissionError) as e:
            # Log the error but continue with instance deletion
            print(
                f"Signal: Error deleting thumbnail file {instance.thumbnail.path}: {e}"
            )

import os

from django.conf import settings
from django.db import models
from django.urls import reverse


class Video(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="videos/")
    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="videos"
    )
    view_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("video_detail", kwargs={"pk": self.pk})

    def get_stream_url(self):
        return reverse("video_stream", kwargs={"pk": self.pk})

    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=["view_count"])

    def delete(self, *args, **kwargs):
        # Delete the physical video file
        if self.file and hasattr(self.file, "path") and os.path.isfile(self.file.path):
            try:
                os.remove(self.file.path)
            except (OSError, PermissionError) as e:
                # Log the error but continue with model deletion
                print(f"Error deleting video file {self.file.path}: {e}")

        # Delete the physical thumbnail file
        if (
            self.thumbnail
            and hasattr(self.thumbnail, "path")
            and os.path.isfile(self.thumbnail.path)
        ):
            try:
                os.remove(self.thumbnail.path)
            except (OSError, PermissionError) as e:
                # Log the error but continue with model deletion
                print(f"Error deleting thumbnail file {self.thumbnail.path}: {e}")

        # Call the parent class delete method to remove the model instance
        super().delete(*args, **kwargs)


class WatchHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watch_history"
    )
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="watch_history"
    )
    watched_at = models.DateTimeField(auto_now=True)
    position = models.PositiveIntegerField(default=0)  # Position in seconds

    class Meta:
        unique_together = ("user", "video")
        ordering = ["-watched_at"]

    def __str__(self):
        return f"{self.user.username} - {self.video.title}"


class Playlist(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playlists"
    )
    videos = models.ManyToManyField(
        Video, related_name="playlists", through="PlaylistItem"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("playlist_detail", kwargs={"pk": self.pk})

    @property
    def video_count(self):
        return self.videos.count()


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "added_at"]
        unique_together = ("playlist", "video")


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "video")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.video.title}"

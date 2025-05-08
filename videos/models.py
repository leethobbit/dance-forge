from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse


class Video(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="videos/")
    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="videos")
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


class WatchHistory(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="watch_history"
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

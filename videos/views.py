import mimetypes
import os
import re
from wsgiref.util import FileWrapper

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.http import HttpResponseNotModified
from django.http import JsonResponse
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView

from .models import Playlist
from .models import Video
from .models import WatchHistory


class VideoListView(ListView):
    model = Video
    template_name = "videos/video_list.html"
    context_object_name = "videos"
    paginate_by = 12


class VideoDetailView(DetailView):
    model = Video
    template_name = "videos/video_detail.html"
    context_object_name = "video"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            watch_history, created = WatchHistory.objects.get_or_create(
                user=self.request.user, video=self.object
            )
            context["position"] = watch_history.position
        return context

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.object.increment_view_count()
        return response


class VideoCreateView(LoginRequiredMixin, CreateView):
    model = Video
    template_name = "videos/video_form.html"
    fields = ["title", "description", "file", "thumbnail"]

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class VideoUpdateView(LoginRequiredMixin, UpdateView):
    model = Video
    template_name = "videos/video_form.html"
    fields = ["title", "description", "thumbnail"]

    def get_queryset(self):
        return Video.objects.filter(owner=self.request.user)


class VideoDeleteView(LoginRequiredMixin, DeleteView):
    model = Video
    template_name = "videos/video_confirm_delete.html"
    success_url = reverse_lazy("video_list")

    def get_queryset(self):
        return Video.objects.filter(owner=self.request.user)


class PlaylistCreateView(LoginRequiredMixin, CreateView):
    model = Playlist
    fields = ["name", "description", "is_public"]
    template_name = "videos/playlist_form.html"
    success_url = reverse_lazy("video_list")  # Redirect to videos list after creation

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


def range_re_pattern():
    return re.compile(r"bytes\s*=\s*(\d+)\s*-\s*(\d*)", re.I)


def stream_video(request, pk):
    """
    Streaming video view with support for HTTP range requests.
    """
    video = get_object_or_404(Video, pk=pk)
    path = video.file.path

    range_header = request.META.get("HTTP_RANGE", "").strip()
    range_re = range_re_pattern()
    range_match = range_re.match(range_header)

    size = os.path.getsize(path)
    content_type, encoding = mimetypes.guess_type(path)
    content_type = content_type or "application/octet-stream"

    if range_match:
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = int(last_byte) if last_byte else size - 1
        if last_byte >= size:
            last_byte = size - 1
        length = last_byte - first_byte + 1

        resp = StreamingHttpResponse(
            file_iterator(path, first_byte, length),
            status=206,
            content_type=content_type,
        )
        resp["Content-Length"] = str(length)
        resp["Content-Range"] = f"bytes {first_byte}-{last_byte}/{size}"
    else:
        resp = StreamingHttpResponse(
            FileWrapper(open(path, "rb")), content_type=content_type
        )
        resp["Content-Length"] = str(size)

    resp["Accept-Ranges"] = "bytes"
    return resp


def file_iterator(path, offset=0, length=None, chunk_size=8192):
    """
    File iterator for streaming video files in chunks.
    """
    with open(path, "rb") as f:
        f.seek(offset)
        remaining = length
        while True:
            bytes_length = (
                chunk_size if remaining is None else min(remaining, chunk_size)
            )
            data = f.read(bytes_length)
            if not data:
                break
            if remaining:
                remaining -= len(data)
            yield data


def update_watch_position(request, pk):
    """
    HTMX-compatible view to update watch position.
    """
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    if request.method != "POST":
        return HttpResponse(status=405)

    video = get_object_or_404(Video, pk=pk)
    position = request.POST.get("position", 0)

    try:
        position = int(position)
    except ValueError:
        position = 0

    watch_history, created = WatchHistory.objects.get_or_create(
        user=request.user, video=video, defaults={"position": position}
    )

    if not created:
        watch_history.position = position
        watch_history.save(update_fields=["position", "watched_at"])

    return HttpResponse(status=204)

import mimetypes
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from wsgiref.util import FileWrapper

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.http import HttpResponseNotModified
from django.http import JsonResponse
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
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


class PlaylistListView(ListView):
    model = Playlist
    template_name = "videos/playlist_list.html"
    context_object_name = "playlists"
    paginate_by = 12

    def get_queryset(self):
        """Return public playlists and user's own playlists."""
        queryset = Playlist.objects.filter(is_public=True)
        if self.request.user.is_authenticated:
            queryset = queryset | Playlist.objects.filter(owner=self.request.user)
        return queryset.distinct().order_by("-created_at")


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
        # Check if a thumbnail was provided
        if not form.cleaned_data.get("thumbnail") and form.cleaned_data.get("file"):
            # Generate thumbnail from the first frame
            video_file = form.cleaned_data["file"]
            thumbnail = self.generate_thumbnail(video_file)
            if thumbnail:
                form.instance.thumbnail = thumbnail
        return super().form_valid(form)

    def generate_thumbnail(self, video_file):
        """Generate a thumbnail from a frame 5 seconds into the video."""
        # Create a unique temporary file
        temp_dir = tempfile.gettempdir()
        temp_video_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
        temp_thumb_path = os.path.join(temp_dir, f"{uuid.uuid4()}.jpg")

        # Save the uploaded file temporarily
        with open(temp_video_path, "wb+") as destination:
            for chunk in video_file.chunks():
                destination.write(chunk)

        try:
            # Use FFmpeg to extract a frame from 5 seconds into the video
            cmd = [
                "ffmpeg",
                "-i",
                temp_video_path,
                "-vframes",
                "1",
                "-an",
                "-ss",
                "5",  # 5 seconds into the video
                "-y",
                temp_thumb_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            # If video is shorter than 5 seconds, try again with a frame from 1 second
            if (
                not os.path.exists(temp_thumb_path)
                or os.path.getsize(temp_thumb_path) == 0
            ):
                cmd[7] = "1"  # Change to 1 second
                subprocess.run(cmd, check=True, capture_output=True)

                # If still no thumbnail, use the first frame
                if (
                    not os.path.exists(temp_thumb_path)
                    or os.path.getsize(temp_thumb_path) == 0
                ):
                    cmd[7] = "0"  # Use the first frame
                    subprocess.run(cmd, check=True, capture_output=True)

            # Read the generated thumbnail
            if os.path.exists(temp_thumb_path) and os.path.getsize(temp_thumb_path) > 0:
                with open(temp_thumb_path, "rb") as f:
                    thumbnail_content = f.read()

                # Create a Django ContentFile from the image data
                filename = f"{Path(video_file.name).stem}_thumbnail.jpg"
                thumbnail = ContentFile(thumbnail_content, name=filename)
                return thumbnail

        except Exception as e:
            # Log the error in a production environment
            print(f"Error generating thumbnail: {e}")

        finally:
            # Clean up temporary files
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            if os.path.exists(temp_thumb_path):
                os.remove(temp_thumb_path)

        return None


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


@require_GET
def partials_video_list(request):
    """
    Renders just the video list content without the navigation for HTMX requests.
    For direct browser requests, redirects to the full-page version.
    """
    video_list_view = VideoListView.as_view()
    response = video_list_view(request)

    # Check if it's an HTMX request
    if request.headers.get("HX-Request"):
        # For pagination ("Load More" button), only return the new items
        if (
            request.headers.get("HX-Trigger") == "load-more-btn"
            and "page" in request.GET
        ):
            return render(
                request,
                "videos/partials/video_cards.html",
                response.context_data if hasattr(response, "context_data") else {},
            )
        # Otherwise return the full content for the main area
        return render(
            request,
            "videos/partials/video_list_content.html",
            response.context_data if hasattr(response, "context_data") else {},
        )
    else:
        # Redirect to the full-page version for direct browser requests
        return redirect("video_list")


@require_GET
def partials_playlist_list(request):
    """
    Renders just the playlist list content without the navigation for HTMX requests.
    For direct browser requests, redirects to the full-page version.
    """
    playlist_list_view = PlaylistListView.as_view()
    response = playlist_list_view(request)

    # Check if it's an HTMX request
    if request.headers.get("HX-Request"):
        # For pagination ("Load More" button), only return the new items
        if (
            request.headers.get("HX-Trigger") == "load-more-btn"
            and "page" in request.GET
        ):
            return render(
                request,
                "videos/partials/playlist_cards.html",
                response.context_data if hasattr(response, "context_data") else {},
            )
        # Otherwise return the full content for the main area
        return render(
            request,
            "videos/partials/playlist_list_content.html",
            response.context_data if hasattr(response, "context_data") else {},
        )
    else:
        # Redirect to the full-page version for direct browser requests
        return redirect("playlist_list")

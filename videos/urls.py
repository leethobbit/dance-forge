from django.urls import path

from . import views

urlpatterns = [
    path("", views.VideoListView.as_view(), name="video_list"),
    path("video/<int:pk>/", views.VideoDetailView.as_view(), name="video_detail"),
    path("video/<int:pk>/stream/", views.stream_video, name="video_stream"),
    path(
        "video/<int:pk>/update-position/",
        views.update_watch_position,
        name="update_watch_position",
    ),
    path("video/create/", views.VideoCreateView.as_view(), name="video_create"),
    path(
        "video/<int:pk>/update/", views.VideoUpdateView.as_view(), name="video_update"
    ),
    path(
        "video/<int:pk>/delete/", views.VideoDeleteView.as_view(), name="video_delete"
    ),
]

from django.shortcuts import redirect
from django.shortcuts import render
from django.views.decorators.http import require_GET

from videos.models import Video  # Import the Video model


@require_GET
def partials_home(request):
    """
    Renders just the home page content without the navigation for HTMX requests.
    For direct browser requests, redirects to the full-page version.
    """
    # Fetch the 10 most recent videos
    recent_videos = Video.objects.order_by("-created_at")[:10]

    # Check if it's an HTMX request
    if request.headers.get("HX-Request"):
        # Return just the partial content for HTMX
        return render(
            request, "partials/home_content.html", {"recent_videos": recent_videos}
        )
    else:
        # Redirect to the full-page version for direct browser requests
        return redirect("home")


@require_GET
def partials_about(request):
    """
    Renders just the about page content without the navigation for HTMX requests.
    For direct browser requests, redirects to the full-page version.
    """
    # Check if it's an HTMX request
    if request.headers.get("HX-Request"):
        # Return just the partial content for HTMX
        return render(request, "partials/about_content.html")
    else:
        # Redirect to the full-page version for direct browser requests
        return redirect("about")


def home(request):
    """
    Renders the full home page.
    """
    # Fetch the 10 most recent videos
    recent_videos = Video.objects.order_by("-created_at")[:10]
    return render(request, "pages/home.html", {"recent_videos": recent_videos})

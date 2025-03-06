import logging
from io import BytesIO

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods
from PIL import Image, ImageDraw

from website.models import Domain, Project, Repo
from website.utils import check_security_txt

logger = logging.getLogger(__name__)


def generate_badge_image(text, status, color):
    """Generate a PNG badge image"""
    try:
        # Create a new image with a white background
        width = 200
        height = 40
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)

        # Draw text
        text_to_draw = f"{text}: {status}"
        draw.text((10, 10), text_to_draw, fill=color)

        # Convert to PNG
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"Error generating badge: {str(e)}")
        return None


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def project_badge_view(request, slug):
    """Generate badge for project status"""
    try:
        project = get_object_or_404(Project, slug=slug)

        # Increment visit count
        project.project_visit_count += 1
        project.save()

        badge_image = generate_badge_image(
            text="Project",
            status=project.status,
            color="#e74c3c",  # Using our standard red color
        )
        if badge_image is None:
            return HttpResponse("Error generating badge", status=500)

        response = HttpResponse(badge_image, content_type="image/png")
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response
    except Exception as e:
        logger.error(f"Project badge error: {str(e)}")
        return HttpResponse("Error generating badge", status=500)


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def repo_badge_view(request, slug):
    """Generate badge for repository status"""
    try:
        repo = get_object_or_404(Repo, slug=slug)

        # Increment visit count
        repo.repo_visit_count += 1
        repo.save()

        badge_image = generate_badge_image(
            text="Repository",
            status="Active" if repo.is_active else "Inactive",
            color="#e74c3c",  # Using our standard red color
        )
        if badge_image is None:
            return HttpResponse("Error generating badge", status=500)

        response = HttpResponse(badge_image, content_type="image/png")
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response
    except Exception as e:
        logger.error(f"Repo badge error: {str(e)}")
        return HttpResponse("Error generating badge", status=500)


@require_http_methods(["GET"])
def check_domain_security(request, domain_id):
    """Check if domain has security.txt file"""
    try:
        domain = Domain.objects.get(id=domain_id)
        has_security, error = check_security_txt(domain.url)

        return JsonResponse({"has_security_txt": has_security, "error": error if error else None})

    except Domain.DoesNotExist:
        return JsonResponse({"error": "Domain not found"}, status=404)

    except Exception as e:
        logger.error(f"Error checking security.txt: {str(e)}")
        return JsonResponse({"error": f"Error checking security.txt: {str(e)}"}, status=500)

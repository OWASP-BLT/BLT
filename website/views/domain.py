import logging

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from website.models import Domain, Project, Repo

logger = logging.getLogger(__name__)


def generate_badge_image(text, status, color):
    """Helper function to generate badge image"""
    # TODO: Implement badge generation logic
    # For now returning a placeholder
    return b"badge_placeholder"


def project_badge_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    badge_image = generate_badge_image(
        text="Project",
        status=project.status,
        color="#e74c3c",  # Using our standard red color
    )
    return HttpResponse(badge_image, content_type="image/png")


def repo_badge_view(request, slug):
    repo = get_object_or_404(Repo, slug=slug)
    badge_image = generate_badge_image(
        text="Repository",
        status="Active" if repo.is_active else "Inactive",
        color="#e74c3c",  # Using our standard red color
    )
    return HttpResponse(badge_image, content_type="image/png")


@require_http_methods(["GET"])
def check_domain_security(request, domain_id):
    try:
        domain = Domain.objects.get(id=domain_id)
        has_security, error = domain.check_security_txt()

        result = {"domain": domain.name, "has_security_txt": has_security, "url": domain.url, "error": error}

        return JsonResponse(result, safe=False)

    except Domain.DoesNotExist:
        return JsonResponse({"error": "Domain not found"}, status=404)
    except Exception as e:
        logger.error(f"Error checking security.txt: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)

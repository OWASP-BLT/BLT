import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from website.models import Domain

logger = logging.getLogger(__name__)


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

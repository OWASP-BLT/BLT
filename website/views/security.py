import csv
import json
import logging
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Value, When
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import TemplateView

from website.models import Issue, SecurityIncident

CSV_RATE_LIMIT_MAX_CALLS = 5  # max CSV downloads
CSV_RATE_LIMIT_WINDOW = 60  # per 60 seconds

logger = logging.getLogger(__name__)

SECURITY_LABEL = 4

# Severity ranking for correct sorting
SEVERITY_ORDER = Case(
    When(severity="critical", then=Value(4)),
    When(severity="high", then=Value(3)),
    When(severity="medium", then=Value(2)),
    When(severity="low", then=Value(1)),
    output_field=IntegerField(),
)


def is_csv_rate_limited(user_id):
    """
    Rate limit CSV exports per user using atomic cache operations.
    Prevents race conditions between get()/set()/incr().
    """
    key = f"csv_export_limit_{user_id}"

    # Atomic operation: returns True only if key was newly created
    # and sets initial count=1 with TTL.
    added = cache.add(key, 1, CSV_RATE_LIMIT_WINDOW)
    if added:
        return False  # first request in window

    # Key exists → safe atomic increment
    try:
        count = cache.incr(key)
    except ValueError:
        # Extremely rare: key expired between add() and incr()
        cache.set(key, 1, CSV_RATE_LIMIT_WINDOW)
        return False

    return count > CSV_RATE_LIMIT_MAX_CALLS


def _escape_csv_formula(value):
    """Escape leading formula characters to mitigate CSV formula injection."""
    if not isinstance(value, str):
        return value

    original = value
    value = value.strip()

    if not value:
        return value

    # Include all OWASP-recommended dangerous chars
    if value[0] in ("=", "+", "-", "@", "\t", "\r", "\n"):
        return "'" + value

    return value


class SecurityDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "security/dashboard.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "csv":
            return self.export_csv()
        return super().get(request, *args, **kwargs)

    def export_csv(self):
        user = self.request.user

        # Authorization
        if not user.is_superuser:
            return HttpResponse("Forbidden", status=403)

        # Rate limit
        if is_csv_rate_limited(user.id):
            return HttpResponse(
                "CSV export rate limit exceeded. Please try again in a minute.", status=429, content_type="text/plain"
            )

        queryset = SecurityIncident.objects.all().order_by("-created_at")
        queryset = self.apply_filters(queryset)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=security_incidents.csv"

        writer = csv.writer(response)
        writer.writerow(["ID", "Title", "Severity", "Status", "Created At", "Affected Systems"])

        for incident in queryset:
            writer.writerow(
                [
                    incident.id,
                    _escape_csv_formula(incident.title),
                    incident.severity,
                    incident.status,
                    incident.created_at,
                    _escape_csv_formula(incident.affected_systems or ""),
                ]
            )

        return response

        queryset = SecurityIncident.objects.all().order_by("-created_at")
        queryset = self.apply_filters(queryset)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=security_incidents.csv"

        writer = csv.writer(response)
        writer.writerow(["ID", "Title", "Severity", "Status", "Created At", "Affected Systems"])

        for incident in queryset:
            writer.writerow(
                [
                    incident.id,
                    _escape_csv_formula(incident.title),
                    incident.severity,
                    incident.status,
                    incident.created_at,
                    _escape_csv_formula(incident.affected_systems or ""),
                ]
            )

        return response

    def apply_filters(self, queryset):
        """
        Apply severity, status, date range, custom date, and sorting.
        """

        # Severity
        severity = self.request.GET.get("severity")
        allowed_severities = [choice[0] for choice in SecurityIncident.Severity.choices]
        if severity in allowed_severities:
            queryset = queryset.filter(severity=severity)

        # Status
        status = self.request.GET.get("status")
        allowed_statuses = [choice[0] for choice in SecurityIncident.Status.choices]
        if status in allowed_statuses:
            queryset = queryset.filter(status=status)

        # Date Ranges
        date_range = self.request.GET.get("range")
        start_raw = self.request.GET.get("start_date")
        end_raw = self.request.GET.get("end_date")

        # Safe date parsing
        start_date = parse_date(start_raw) if start_raw else None
        end_date = parse_date(end_raw) if end_raw else None

        now = timezone.now()

        if date_range == "today":
            queryset = queryset.filter(created_at__date=now.date())
        elif date_range == "7d":
            queryset = queryset.filter(created_at__gte=now - timedelta(days=7))
        elif date_range == "30d":
            queryset = queryset.filter(created_at__gte=now - timedelta(days=30))
        elif start_date and end_date:
            queryset = queryset.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

        # Sorting
        sort = self.request.GET.get("sort", "newest")

        if sort == "newest":
            queryset = queryset.order_by("-created_at")
        elif sort == "oldest":
            queryset = queryset.order_by("created_at")
        elif sort == "severity_desc":
            queryset = queryset.annotate(severity_rank=SEVERITY_ORDER).order_by("-severity_rank", "-created_at")
        elif sort == "severity_asc":
            queryset = queryset.annotate(severity_rank=SEVERITY_ORDER).order_by("severity_rank", "-created_at")
        elif sort == "status":
            queryset = queryset.order_by("status", "-created_at")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = SecurityIncident.objects.all()
        filtered_queryset = self.apply_filters(queryset)

        # Save UI filter state
        context["current_severity"] = self.request.GET.get("severity")
        context["current_status"] = self.request.GET.get("status")
        context["current_range"] = self.request.GET.get("range")
        context["current_sort"] = self.request.GET.get("sort", "newest")
        context["start_date"] = self.request.GET.get("start_date")
        context["end_date"] = self.request.GET.get("end_date")

        # Pagination
        page_raw = self.request.GET.get("page", "1")

        try:
            page_number = int(page_raw)
            if page_number < 1:
                page_number = 1
        except (ValueError, TypeError):
            page_number = 1

        paginator = Paginator(filtered_queryset, 9)
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["incidents"] = page_obj.object_list

        # Related Issues (label=4)
        context["security_issues"] = Issue.objects.filter(label=SECURITY_LABEL).order_by("-created")[:10]

        # Summary
        context["incident_count"] = filtered_queryset.count()

        severity_agg = list(filtered_queryset.values("severity").annotate(total=Count("severity")))
        status_agg = list(filtered_queryset.values("status").annotate(total=Count("status")))

        context["severity_breakdown"] = severity_agg
        context["status_breakdown"] = status_agg

        context["severity_chart_data"] = json.dumps(severity_agg)

        return context

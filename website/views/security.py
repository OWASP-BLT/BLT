import csv
import json
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Value, When
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import TemplateView

from website.models import Issue, SecurityIncident

# Severity ranking for correct sorting
SEVERITY_ORDER = Case(
    When(severity="critical", then=Value(4)),
    When(severity="high", then=Value(3)),
    When(severity="medium", then=Value(2)),
    When(severity="low", then=Value(1)),
    output_field=IntegerField(),
)


class SecurityDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "security/dashboard.html"

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "csv":
            return self.export_csv()
        return super().get(request, *args, **kwargs)

    def export_csv(self):
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
                    incident.title,
                    incident.severity,
                    incident.status,
                    incident.created_at,
                    incident.affected_systems or "",
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
        page_number = self.request.GET.get("page", 1)
        paginator = Paginator(filtered_queryset, 9)
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["incidents"] = page_obj.object_list

        # Related Issues (label=4)
        context["security_issues"] = Issue.objects.filter(label=4).order_by("-created")[:10]

        # Summary
        context["incident_count"] = filtered_queryset.count()

        severity_agg = list(filtered_queryset.values("severity").annotate(total=Count("severity")))
        status_agg = list(filtered_queryset.values("status").annotate(total=Count("status")))

        context["severity_breakdown"] = severity_agg
        context["status_breakdown"] = status_agg

        context["severity_chart_data"] = json.dumps(severity_agg)

        return context

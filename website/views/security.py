import csv
import json
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView

from website.models import Issue, SecurityIncident


class SecurityDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "security/dashboard.html"

    def get(self, request, *args, **kwargs):
        # Handle CSV export before calling get_context_data
        if request.GET.get("export") == "csv":
            return self.export_csv()
        return super().get(request, *args, **kwargs)

    def export_csv(self):
        queryset = SecurityIncident.objects.all().order_by("-created_at")

        # Apply the same filters as the main view
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
        # Severity filter
        severity = self.request.GET.get("severity")
        allowed_severities = [choice[0] for choice in SecurityIncident.Severity.choices]
        if severity in allowed_severities:
            queryset = queryset.filter(severity=severity)

        # Status filter
        status = self.request.GET.get("status")
        allowed_statuses = [choice[0] for choice in SecurityIncident.Status.choices]
        if status in allowed_statuses:
            queryset = queryset.filter(status=status)

        # Date range filter
        date_range = self.request.GET.get("range")
        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")
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
            queryset = queryset.order_by("-severity")
        elif sort == "severity_asc":
            queryset = queryset.order_by("severity")
        elif sort == "status":
            queryset = queryset.order_by("status")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Base queryset
        queryset = SecurityIncident.objects.all()

        # Apply filters
        filtered_queryset = self.apply_filters(queryset)

        # Save current filters for UI
        context["current_severity"] = self.request.GET.get("severity")
        context["current_status"] = self.request.GET.get("status")
        context["current_range"] = self.request.GET.get("range")
        context["current_sort"] = self.request.GET.get("sort", "newest")
        context["start_date"] = self.request.GET.get("start_date")
        context["end_date"] = self.request.GET.get("end_date")

        # Pagination
        page_number = self.request.GET.get("page", 1)
        paginator = Paginator(filtered_queryset, 9)  # 9 items per page (3×3 grid)
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["incidents"] = page_obj.object_list

        # Security issues (not filtered)
        context["security_issues"] = Issue.objects.filter(label=4).order_by("-created")[:10]

        # Summary (filtered, NOT global)
        context["incident_count"] = filtered_queryset.count()

        severity_agg = list(filtered_queryset.values("severity").annotate(total=Count("severity")))
        status_agg = list(filtered_queryset.values("status").annotate(total=Count("status")))

        context["severity_breakdown"] = severity_agg
        context["status_breakdown"] = status_agg

        # NEW: JSON data for chart
        context["severity_chart_data"] = json.dumps(severity_agg)

        return context

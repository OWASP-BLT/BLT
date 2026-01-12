import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, UpdateView

from website.models import SecurityIncident, SecurityIncidentHistory
from website.security_incident_form import SecurityIncidentForm


class StaffRequiredMixin(UserPassesTestMixin):
    """Restrict creation/editing to staff or superusers."""

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


class SecurityIncidentCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = SecurityIncident
    form_class = SecurityIncidentForm
    template_name = "security/incidents/incident_form.html"
    success_url = reverse_lazy("security_dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["form_title"] = "Create Security Incident"
        return context

    @transaction.atomic
    def form_valid(self, form):
        form.instance.reporter = self.request.user
        return super().form_valid(form)


class SecurityIncidentUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = SecurityIncident
    form_class = SecurityIncidentForm
    template_name = "security/incidents/incident_form.html"
    success_url = reverse_lazy("security_dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Edit Security Incident"
        if self.object and hasattr(self.object, "history"):
            context["unique_editors_count"] = (
                self.object.history.filter(changed_by__isnull=False).values("changed_by").order_by().distinct().count()
            )
        return context

    @transaction.atomic
    def form_valid(self, form):
        # Capture old state before save
        old_instance = SecurityIncident.objects.select_for_update().get(pk=self.object.pk)

        # Save the updated incident
        response = super().form_valid(form)

        # Create history records for changed fields
        fields_to_track = ["title", "severity", "status", "affected_systems", "description"]

        for field in fields_to_track:
            old_val = getattr(old_instance, field)
            new_val = getattr(self.object, field)

            if old_val != new_val:
                SecurityIncidentHistory.objects.create(
                    incident=self.object,
                    field_name=field,
                    old_value=old_val if old_val is not None else "",
                    new_value=new_val if new_val is not None else "",
                    changed_by=self.request.user,  # Direct access, no middleware!
                )

        return response


class SecurityIncidentDetailView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = SecurityIncident
    template_name = "security/incidents/incident_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        history_qs = self.object.history.select_related("changed_by").order_by("-changed_at")

        context["incident"] = self.object
        context["history_entries"] = history_qs
        context["history_count"] = history_qs.count()
        context["last_history"] = history_qs.first()

        context["unique_editors_count"] = (
            history_qs.filter(changed_by__isnull=False).values("changed_by").distinct().order_by().count()
        )

        history_json_qs = history_qs.values(
            "id",
            "field_name",
            "old_value",
            "new_value",
            "changed_by_id",
            "changed_at",
        )
        context["history_json"] = json.dumps(list(history_json_qs), cls=DjangoJSONEncoder)

        return context

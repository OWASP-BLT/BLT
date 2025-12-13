from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, UpdateView

from website.models import SecurityIncident
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
            context["unique_editor_count"] = self.object.history.values("changed_by").distinct().count()
        return context

    @transaction.atomic
    def form_valid(self, form):
        # Capture old state before save
        old_instance = SecurityIncident.objects.get(pk=self.object.pk)

        # Save the updated incident
        response = super().form_valid(form)

        # Create history records for changed fields
        fields_to_track = ["title", "severity", "status", "affected_systems", "resolved_at"]

        for field in fields_to_track:
            old_val = getattr(old_instance, field)
            new_val = getattr(self.object, field)

            if str(old_val) != str(new_val):
                SecurityIncidentHistory.objects.create(
                    incident=self.object,
                    field_name=field,
                    old_value=old_val if old_val is not None else "",
                    new_value=new_val if new_val is not None else "",
                    changed_by=self.request.user,  # Direct access, no middleware!
                )

        return response


class SecurityIncidentDetailView(LoginRequiredMixin, DetailView):
    model = SecurityIncident
    template_name = "security/incidents/incident_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["incident"] = self.object
        return context

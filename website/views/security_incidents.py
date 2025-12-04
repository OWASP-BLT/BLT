from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
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
        context["unique_editor_count"] = self.object.history.values("changed_by").distinct().count()
        return context


class SecurityIncidentUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = SecurityIncident
    form_class = SecurityIncidentForm
    template_name = "security/incidents/incident_form.html"
    success_url = reverse_lazy("security_dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Edit Security Incident"
        return context


class SecurityIncidentDetailView(LoginRequiredMixin, DetailView):
    model = SecurityIncident
    template_name = "security/incidents/incident_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        incident = self.object

        # add more metadata later (history, related issues, etc.)
        context["incident"] = incident
        return context

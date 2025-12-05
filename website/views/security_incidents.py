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

        obj = getattr(self, "object", None)
        if obj and hasattr(obj, "history"):
            context["unique_editor_count"] = obj.history.values("changed_by").distinct().count()
        else:
            context["unique_editor_count"] = 0

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
        return context

    @transaction.atomic
    def form_valid(self, form):
        return super().form_valid(form)


class SecurityIncidentDetailView(LoginRequiredMixin, DetailView):
    model = SecurityIncident
    template_name = "security/incidents/incident_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["incident"] = self.object
        return context

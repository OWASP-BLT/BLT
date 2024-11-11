import ipaddress

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.timezone import now
from django.views.generic import FormView, ListView

from website.forms import CaptchaForm, IpReportForm
from website.models import IpReport
from website.utils import get_client_ip


class ReportIpView(FormView):
    template_name = "report_ip.html"
    form_class = IpReportForm
    captcha = CaptchaForm()

    def is_valid_ip(self, ip_address, ip_type):
        """
        Validates an IP address format based on the specified type (IPv4 or IPv6).
        """
        try:
            if ip_type == "ipv4":
                ipaddress.IPv4Address(ip_address)
                return True
            elif ip_type == "ipv6":
                ipaddress.IPv6Address(ip_address)
                return True
            else:
                return False
        except ValueError:
            return False

    def post(self, request, *args, **kwargs):
        # Check CAPTCHA
        captcha_form = CaptchaForm(request.POST)
        if not captcha_form.is_valid():
            messages.error(request, "Invalid CAPTCHA. Please try again.")
            return render(
                request,
                self.template_name,
                {
                    "form": self.get_form(),
                    "captcha_form": captcha_form,
                },
            )

        # Process form and duplicate IP check
        form = self.get_form()
        if form.is_valid():
            ip_address = form.cleaned_data.get("ip_address")
            ip_type = form.cleaned_data.get("ip_type")
            print(ip_address + " " + ip_type)

            if not self.is_valid_ip(ip_address, ip_type):
                messages.error(request, f"Invalid {ip_type} address format.")
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "captcha_form": captcha_form,
                    },
                )
            if IpReport.objects.filter(ip_address=ip_address, ip_type=ip_type).exists():
                messages.error(request, "This IP address has already been reported.")
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "captcha_form": captcha_form,
                    },
                )

            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        # Check daily report limit per IP
        reporter_ip = get_client_ip(self.request)
        limit = 50 if self.request.user.is_authenticated else 30
        today = now().date()
        recent_reports_count = IpReport.objects.filter(
            reporter_ip_address=reporter_ip, created=today
        ).count()

        if recent_reports_count >= limit:
            messages.error(self.request, "You have reached the daily limit for IP reports.")
            return render(
                self.request,
                self.template_name,
                {
                    "form": self.get_form(),
                    "captcha_form": CaptchaForm(),
                },
            )

        form.instance.reporter_ip_address = reporter_ip
        form.instance.user = self.request.user if self.request.user.is_authenticated else None
        form.save()
        messages.success(self.request, "IP report successfully submitted.")

        return redirect("reported_ips_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["captcha_form"] = CaptchaForm()
        return context


class ReportedIpListView(ListView):
    model = IpReport
    template_name = "reported_ips_list.html"
    context_object_name = "reported_ips"
    paginate_by = 10

    def get_queryset(self):
        return IpReport.objects.all().order_by("-created")

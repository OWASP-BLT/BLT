from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Case, When, Value, CharField
from django.db.models.functions import TruncDate

from website.models import Issue


@login_required
def security_dashboard(request):
    today = timezone.now().date()
    start_date = today - timedelta(days=29)

    qs = Issue.objects.filter(
        label=4,
        created__date__gte=start_date,
        is_hidden=False,
    )

    # ---- KPIs ----
    total = qs.count()
    open_count = qs.filter(status="open").count()
    closed_count = qs.filter(status="closed").count()
    with_cve = qs.filter(cve_id__isnull=False).count()

    # ---- DAILY TREND ----
    daily_qs = (
        qs.annotate(day=TruncDate("created"))
        .values("day")
        .annotate(count=Count("id"))
    )

    daily_map = {x["day"]: x["count"] for x in daily_qs}

    daily_labels, daily_counts = [], []
    for i in range(30):
        d = start_date + timedelta(days=i)
        daily_labels.append(d.strftime("%d %b"))
        daily_counts.append(daily_map.get(d, 0))

    # ---- SEVERITY (FROM CVSS) ----
    severity_qs = (
        qs.annotate(
            severity=Case(
                When(cve_score__gte=9, then=Value("Critical")),
                When(cve_score__gte=7, then=Value("High")),
                When(cve_score__gte=4, then=Value("Medium")),
                default=Value("Low"),
                output_field=CharField(),
            )
        )
        .values("severity")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # ---- STATUS ----
    status_qs = qs.values("status").annotate(count=Count("id"))

    # ---- ORG / DOMAIN ----
    org_qs = (
        qs.values("domain__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )

    context = {
        "total": total,
        "open": open_count,
        "closed": closed_count,
        "with_cve": with_cve,
        "daily_labels": daily_labels,
        "daily_counts": daily_counts,
        "severity_qs": severity_qs,
        "status_qs": status_qs,
        "org_qs": org_qs,
    }

    return render(request, "dashboard/security_dashboard.html", context)


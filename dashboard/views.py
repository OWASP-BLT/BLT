from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Case, CharField, Count, IntegerField, Value, When
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from website.models import Issue


@login_required
def security_dashboard(request):
    today = timezone.now().date()
    start_date = today - timedelta(days=29)

    qs = Issue.objects.filter(
        label=4,  # Security issues
        created__date__gte=start_date,
        is_hidden=False,
    )

    # ---- KPIs ----
    total = qs.count()
    open_count = qs.filter(status="open").count()
    closed_count = qs.filter(status="closed").count()
    with_cve = qs.filter(cve_id__isnull=False).count()

    # ---- DAILY TREND ----
    daily_qs = qs.annotate(day=TruncDate("created")).values("day").annotate(count=Count("id"))

    daily_map = {x["day"]: x["count"] for x in daily_qs}

    daily_labels = []
    daily_counts = []
    for i in range(30):
        day = start_date + timedelta(days=i)
        daily_labels.append(day.strftime("%d %b"))
        daily_counts.append(daily_map.get(day, 0))

    # ---- SEVERITY (CVSS, FIXED ORDER) ----
    severity_qs = (
        qs.annotate(
            severity=Case(
                When(cve_score__gte=9, then=Value("Critical")),
                When(cve_score__gte=7, then=Value("High")),
                When(cve_score__gte=4, then=Value("Medium")),
                When(cve_score__isnull=True, then=Value("Not Scored")),
                default=Value("Low"),
                output_field=CharField(),
            ),
        )
        .annotate(
            severity_order=Case(
                When(severity="Critical", then=Value(1)),
                When(severity="High", then=Value(2)),
                When(severity="Medium", then=Value(3)),
                When(severity="Low", then=Value(4)),
                When(severity="Not Scored", then=Value(5)),
                output_field=IntegerField(),
            ),
        )
        .values("severity", "severity_order")
        .annotate(count=Count("id"))
        .order_by("severity_order")
    )

    # ---- STATUS ----
    status_qs = qs.values("status").annotate(count=Count("id"))

    # ---- ORGANIZATIONS / DOMAINS ----
    org_qs = qs.values("domain__name").annotate(count=Count("id")).order_by("-count")[:8]

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

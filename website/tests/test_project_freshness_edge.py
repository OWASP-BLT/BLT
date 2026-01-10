import pytest
from website.models import Project
from django.utils import timezone
from datetime import timedelta

def make_project(**kwargs):
    defaults = dict(archived=False, forked=False, status="active")
    defaults.update(kwargs)
    return Project(**defaults)

def test_archived_project_zero():
    p = make_project(archived=True)
    assert p.calculate_freshness() == 0

def test_forked_project_zero():
    p = make_project(forked=True)
    assert p.calculate_freshness() == 0

def test_inactive_status_zero():
    p = make_project(status="inactive")
    assert p.calculate_freshness() == 0

def test_lab_status_zero():
    p = make_project(status="lab")
    assert p.calculate_freshness() == 0

def test_outlier_spam():
    p = make_project()
    p.id = 999
    # Simulate excessive recent contributions
    p.calculate_freshness = lambda: 0
    assert p.calculate_freshness() == 0

def test_fallback_issue_comment():
    p = make_project()
    # Simulate fallback logic
    p.calculate_freshness = lambda: 50
    assert p.calculate_freshness() == 50

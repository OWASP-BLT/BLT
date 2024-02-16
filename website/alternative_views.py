
import json
import os
from typing import Any
import urllib.error
import urllib.parse
from datetime import datetime,timezone, timedelta
from user_agents import parse

import six
import base64
from decimal import Decimal
import requests
import uuid


#from django_cron import CronJobBase, Schedule
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.contrib.auth.models import User, AnonymousUser
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import reverse
from django.db.models import Sum, Count, Q
from django.dispatch import receiver
from django.http import JsonResponse,HttpResponseRedirect
from django.shortcuts import render
from django.views.generic.edit import CreateView
from django.conf import settings
from rest_framework.authtoken.models import Token
from django.http import Http404,JsonResponse,HttpResponseRedirect,HttpResponse,HttpResponseNotFound
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404


from website.models import (
    Wallet,
    Issue,
    Points,
    Hunt,
    Domain,
    UserProfile,
    IssueScreenshot,
    CompanyAdmin,
    IP

)
from .forms import FormInviteFriend, UserProfileForm, HuntForm, CaptchaForm
from website.views import get_client_ip

from django.conf import settings
from website.views import (
    IssueBaseCreate,
    IssueCreate
)
from django.views.generic import DetailView, TemplateView, ListView, View



@login_required(login_url="/accounts/login")
def flag_issue2(request, issue_pk):
    context = {}
    issue_pk = int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)
    if userprof in UserProfile.objects.filter(issue_flaged=issue):
        userprof.issue_flaged.remove(issue)
    else:
        userprof.issue_flaged.add(issue)
        issue_pk = issue.pk

    userprof.save()
    total_flag_votes = UserProfile.objects.filter(issue_flaged=issue).count()
    context["object"] = issue
    context["flags"] = total_flag_votes
    return render(request, "includes/_flags2.html", context)


@login_required(login_url="/accounts/login")
def like_issue2(request, issue_pk):
    context = {}
    issue_pk = int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)
    if userprof in UserProfile.objects.filter(issue_upvoted=issue):
        userprof.issue_upvoted.remove(issue)
    else:
        userprof.issue_upvoted.add(issue)
        liked_user = issue.user
        liker_user = request.user
        issue_pk = issue.pk
        msg_plain = render_to_string(
            "email/issue_liked.txt",
            {
                "liker_user": liker_user.username,
                "liked_user": liked_user.username,
                "issue_pk": issue_pk,
            },
        )
        msg_html = render_to_string(
            "email/issue_liked.txt",
            {
                "liker_user": liker_user.username,
                "liked_user": liked_user.username,
                "issue_pk": issue_pk,
            },
        )

        send_mail(
            "Your issue got an upvote!!",
            msg_plain,
            settings.EMAIL_TO_STRING,
            [liked_user.email],
            html_message=msg_html,
        )

    userprof.save()
    total_votes = UserProfile.objects.filter(issue_upvoted=issue).count()
    context["object"] = issue
    context["likes"] = total_votes
    return render(request, "includes/_likes2.html", context)

@login_required(login_url="/accounts/login")
def subscribe_to_domains(request, pk):

    domain = Domain.objects.filter(pk=pk).first()
    if domain == None:
        return JsonResponse("ERROR", safe=False,status=400)
    
    already_subscribed = request.user.userprofile.subscribed_domains.filter(pk=domain.id).exists()

    if already_subscribed:
        request.user.userprofile.subscribed_domains.remove(domain)
        request.user.userprofile.save()
        return JsonResponse("UNSUBSCRIBED",safe=False)

    else:
        request.user.userprofile.subscribed_domains.add(domain)
        request.user.userprofile.save()
        return JsonResponse("SUBSCRIBED",safe=False)


class IssueView2(DetailView):
    model = Issue
    slug_field = "id"
    template_name = "issue2.html"

    def get(self, request, *args, **kwargs):
        ipdetails = IP()
        try:
            id = int(self.kwargs["slug"])
        except ValueError:
            return HttpResponseNotFound("Invalid ID: ID must be an integer")

        self.object = get_object_or_404(Issue, id=self.kwargs["slug"])
        ipdetails.user = self.request.user
        ipdetails.address = get_client_ip(request)
        ipdetails.issuenumber = self.object.id
        try:
            if self.request.user.is_authenticated:
                try:
                    objectget = IP.objects.get(
                        user=self.request.user, issuenumber=self.object.id
                    )
                    self.object.save()
                except:
                    ipdetails.save()
                    self.object.views = (self.object.views or 0) + 1
                    self.object.save()
            else:
                try:
                    objectget = IP.objects.get(
                        address=get_client_ip(request), issuenumber=self.object.id
                    )
                    self.object.save()
                except:
                    ipdetails.save()
                    self.object.views = (self.object.views or 0) + 1
                    self.object.save()
        except Exception as e:
            print(e)
            messages.error(self.request, "That issue was not found."+str(e))
            return redirect("/")
        return super(IssueView2, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(IssueView2, self).get_context_data(**kwargs)
        if self.object.user_agent:
            user_agent = parse(self.object.user_agent)
            context["browser_family"] = user_agent.browser.family
            context["browser_version"] = user_agent.browser.version_string
            context["os_family"] = user_agent.os.family
            context["os_version"] = user_agent.os.version_string
        context["users_score"] = list(
            Points.objects.filter(user=self.object.user)
            .aggregate(total_score=Sum("score"))
            .values()
        )[0]

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["issue_count"] = Issue.objects.filter(
            url__contains=self.object.domain_name
        ).count()
        context["all_comment"] = self.object.comments.all().order_by("-created_date")
        context["all_users"] = User.objects.all()
        context["likes"] = UserProfile.objects.filter(issue_upvoted=self.object).count()
        context["likers"] = UserProfile.objects.filter(issue_upvoted=self.object)
        context["flags"] = UserProfile.objects.filter(issue_flaged=self.object).count()
        context["flagers"] = UserProfile.objects.filter(issue_flaged=self.object)
        context["more_issues"] = Issue.objects.filter(user=self.object.user).exclude(id=self.object.id).values("id","description","markdown_description","screenshots__image").order_by("views")[:4]
        context["subscribed_to_domain"] = False

        if isinstance(self.request.user,User):  
            context["subscribed_to_domain"] = self.object.domain.user_subscribed_domains.filter(pk=self.request.user.userprofile.id).exists()


        if isinstance(self.request.user,User): 
            context["bookmarked"] = self.request.user.userprofile.issue_saved.filter(pk=self.object.id  ).exists()

        context["screenshots"] = IssueScreenshot.objects.filter(issue=self.object).all()


        return context
        

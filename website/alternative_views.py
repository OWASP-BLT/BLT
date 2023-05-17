
import json
import os
import random
import re
import time
from typing import Any
import urllib.request
import urllib.error
import urllib.parse
from collections import deque
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from urllib.parse import urlsplit
from giturlparse import parse

from django import http

import requests
import uuid

#from django_cron import CronJobBase, Schedule
from allauth.account.models import EmailAddress
from allauth.account.signals import user_logged_in
from bs4 import BeautifulSoup
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, AnonymousUser
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse, reverse_lazy
from django.db.models import Sum, Count, Q
from django.db.models.functions import ExtractMonth
from django.dispatch import receiver
from django.http import Http404,JsonResponse,HttpResponseRedirect,HttpResponse,HttpResponseNotFound
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.generic import DetailView, TemplateView, ListView, View
from django.views.generic.edit import CreateView
from django.core import serializers
from django.conf import settings
from rest_framework.authtoken.models import Token


from website.models import (

    Winner,
    Payment,
    Wallet,
    Issue,
    Points,
    Hunt,
    Domain,
    InviteFriend,
    UserProfile,
    IP,
    CompanyAdmin,
    Subscription,
    Company,
    IssueScreenshot
)
from .forms import FormInviteFriend, UserProfileForm, HuntForm, CaptchaForm
from website.views import IssueBaseCreate

from django.conf import settings



class IssueCreate2(View):
    
    template_name = "report2.html"

    def get(self,request,*args,**kwargs):

        context = {
            "captcha_form":CaptchaForm,
        }
        return render(request,self.template_name,context)


    def post(self, request, *args, **kwargs):

        stream = request.POST
        url = request.POST.get("url").replace("www.","").replace("https://","")
        data = {
            "user": None if type(request.user) == AnonymousUser else request.user,
            "url": url,
            "description": stream.get("description",None),
            "markdown_description": stream.get("markdown_description",None),
            "label": stream.get("label",None),
            "domain":None,
            "user_agent": self.request.META.get("HTTP_USER_AGENT"),
        }
        is_authenticated = self.request.user.is_authenticated

        

        if stream.get("private"):
            data["is_hidden"] = True

        # disable domain search on testing
        if not settings.IS_TEST:
            try:

                if settings.DOMAIN_NAME in url:
                    print('Web site exists')

                # skip domain validation check if bugreport server down 
                elif data["label"] == "7":
                    pass
                else:
                    response = requests.get( "https://" + url ,timeout=2)
                    if response.status_code == 200:
                        print('Web site exists')
                    else:
                        raise Exception
            except Exception as e:
                messages.error(request,"Domain does not exist")
                return HttpResponseRedirect("/report2/")
            
        
        captcha_form = CaptchaForm(self.request.POST)
        if not captcha_form.is_valid() and not settings.TESTING:
            messages.error(self.request, "Invalid Captcha!")
            return HttpResponseRedirect("/report2/")
        
        domain = Domain.objects.filter(
            Q(name=data["url"]) |
            Q(url__icontains=data["url"])
        ).first()
        
        created = False if domain==None else True 

        if not created:
            domain = Domain.objects.create(
                name=data["url"],
                url=data["url"]
            )
            domain.save()
        

        data["domain"] = domain

        issue = Issue.objects.create(**data)

        if created and (is_authenticated):
            p = Points.objects.create(user=data["user"], domain=domain, score=1)
            messages.success(self.request, "Domain added! + 1")


        if is_authenticated:
            total_issues = Issue.objects.filter(user=self.request.user).count()
            user_prof = UserProfile.objects.get(user=self.request.user)
            if total_issues <= 10:
                user_prof.title = 1
            elif total_issues <= 50:
                user_prof.title = 2
            elif total_issues <= 200:
                user_prof.title = 3
            else:
                user_prof.title = 4

            user_prof.save()

        redirect_url = "/report2"

        if len(self.request.FILES.getlist("file")) > 5:
            messages.error(self.request, "Max limit of 5 images!")
            return HttpResponseRedirect("/report2/")
        for screenshot in self.request.FILES.getlist("file"):
            filename = screenshot.name
            extension = filename.split(".")[-1] 
            screenshot.name = filename[:99] + str(uuid.uuid4()) + "." + extension            
            default_storage.save(f"screenshots/{screenshot.name}",screenshot)
            IssueScreenshot.objects.create(image=f"screenshots/{screenshot.name}",issue=issue)

        obj_screenshots = IssueScreenshot.objects.filter(issue_id=issue.id)
        screenshot_text = ''
        for screenshot in obj_screenshots:
            screenshot_text += "![0](" + screenshot.image.url + ") "

        if domain.github and os.environ.get("GITHUB_ACCESS_TOKEN"):

            github_url = (
                domain.github.replace("https", "git").replace("http", "git") + ".git"
            )
            p = parse(github_url)

            url = "https://api.github.com/repos/%s/%s/issues" % (p.owner, p.repo)

            if not data["user"]:
                the_user = "Anonymous"
            else:
                the_user = data["user"]
                
            gh_issue = {
                "title": issue.description,
                "body": screenshot_text +
                 "https://" + settings.FQDN + "/issue/"
                + str(issue.id) + " found by " + str(the_user) + " at url: " + issue.url,
                "labels": ["bug", settings.PROJECT_NAME_LOWER],
            }
            r = requests.post(
                url,
                json.dumps(gh_issue),
                headers={
                    "Authorization": "token " + os.environ.get("GITHUB_ACCESS_TOKEN")
                },
            )
            response = r.json()

            if response.get("message",None) == "Bad credentials":
                messages.error(self.request, "Invalid Github Token")
            else:
                issue.github_url = response["html_url"]
                issue.save()

        if not (is_authenticated):
            self.request.session["issue"] = issue.id
            self.request.session["created"] = created
            self.request.session["domain"] = domain.id
            login_url = reverse("account_login")
            messages.success(self.request, "Bug added!")
            return HttpResponseRedirect("{}?next={}".format(login_url, redirect_url))

        return render(request,self.template_name)


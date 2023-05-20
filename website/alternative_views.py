
import json
import os
from typing import Any
import urllib.error
import urllib.parse
from datetime import datetime
from giturlparse import parse
import six
import base64


import requests
import uuid

#from django_cron import CronJobBase, Schedule
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


from website.models import (
    Wallet,
    Issue,
    Points,
    Hunt,
    Domain,
    UserProfile,
    IssueScreenshot
)
from .forms import FormInviteFriend, UserProfileForm, HuntForm, CaptchaForm
from website.views import IssueBaseCreate

from django.conf import settings
from website.views import (
    IssueBaseCreate,
    IssueCreate
)

class IssueCreate2(IssueBaseCreate, CreateView):
    model = Issue
    fields = ["url", "description", "domain", "label","markdown_description"]
    template_name = "report2.html"

    def get_initial(self):
        try:
            json_data = json.loads(self.request.body)
            if not self.request.GET._mutable:
                self.request.POST._mutable = True
            self.request.POST["url"] = json_data["url"]
            self.request.POST["description"] = json_data["description"]
            self.request.POST["markdown_description"] = json_data["markdown_description"]
            self.request.POST["file"] = json_data["file"]
            self.request.POST["label"] = json_data["label"]
            self.request.POST["token"] = json_data["token"]
            self.request.POST["type"] = json_data["type"]

            if self.request.POST.get("file"):
                if isinstance(self.request.POST.get("file"), six.string_types):
                    import imghdr

                    # Check if the base64 string is in the "data:" format
                    data = (
                        "data:image/"
                        + self.request.POST.get("type")
                        + ";base64,"
                        + self.request.POST.get("file")
                    )
                    data = data.replace(" ", "")
                    data += "=" * ((4 - len(data) % 4) % 4)
                    if "data:" in data and ";base64," in data:
                        # Break out the header from the base64 content
                        header, data = data.split(";base64,")

                    # Try to decode the file. Return validation error if it fails.
                    try:
                        decoded_file = base64.b64decode(data)
                    except TypeError:
                        TypeError("invalid_image")

                    # Generate file name:
                    file_name = str(uuid.uuid4())[
                        :12
                    ]  # 12 characters are more than enough.
                    # Get the file name extension:
                    extension = imghdr.what(file_name, decoded_file)
                    extension = "jpg" if extension == "jpeg" else extension
                    file_extension = extension

                    complete_file_name = "%s.%s" % (
                        file_name,
                        file_extension,
                    )

                    self.request.FILES["screenshot"] = ContentFile(
                        decoded_file, name=complete_file_name
                    )
        except:
            tokenauth = False
        initial = super(IssueCreate2, self).get_initial()
        if self.request.POST.get("screenshot-hash"):
            initial["screenshot"] = (
                "uploads\/" + self.request.POST.get("screenshot-hash") + ".png"
            )
        return initial

    def post(self, request, *args, **kwargs):

        # resolve domain
        url = request.POST.get("url").replace("www.","").replace("https://","")
        
        request.POST._mutable = True
        request.POST.update(url=url) # only domain.com will be stored in db
        request.POST._mutable = False


        # disable domain search on testing
        if not settings.IS_TEST:
            try:

                if settings.DOMAIN_NAME in url:
                    print('Web site exists')

                # skip domain validation check if bugreport server down 
                elif request.POST["label"] == "7":
                    pass

                else:
                    response = requests.get( "https://" + url ,timeout=2)
                    if response.status_code == 200:
                        print('Web site exists')
                    else:
                        raise Exception
            except:
                messages.error(request,"Domain does not exist")
                return HttpResponseRedirect("/issue/")

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        tokenauth = False
        obj = form.save(commit=False)
        if self.request.user.is_authenticated:
            obj.user = self.request.user
        if not self.request.user.is_authenticated:
            for token in Token.objects.all():
                if self.request.POST.get("token") == token.key:
                    obj.user = User.objects.get(id=token.user_id)
                    tokenauth = True

        captcha_form = CaptchaForm(self.request.POST)
        if not captcha_form.is_valid() and not settings.TESTING:
            messages.error(self.request, "Invalid Captcha!")
            return HttpResponseRedirect("/issue/")
        
        clean_domain = obj.domain_name.replace("www.", "").replace("https://","").replace("http://","")
        domain = Domain.objects.filter(
            Q(name=clean_domain) |
            Q(url__icontains=clean_domain)
        ).first()
        
        created = False if domain==None else True 

        if not created:
            domain = Domain.objects.create(
                name=clean_domain,
                url=clean_domain
            )
            domain.save()
        

        obj.domain = domain

        if created and (self.request.user.is_authenticated or tokenauth):
            p = Points.objects.create(user=self.request.user, domain=domain, score=1)
            messages.success(self.request, "Domain added! + 1")

        if self.request.POST.get("screenshot-hash"):
            reopen = default_storage.open(
                "uploads\/" + self.request.POST.get("screenshot-hash") + ".png", "rb"
            )
            django_file = File(reopen)
            obj.screenshot.save(
                self.request.POST.get("screenshot-hash") + ".png",
                django_file,
                save=True,
            )
        obj.user_agent = self.request.META.get("HTTP_USER_AGENT")       
        obj.save()

        if self.request.user.is_authenticated:
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

        if tokenauth:
            total_issues = Issue.objects.filter(
                user=User.objects.get(id=token.user_id)
            ).count()
            user_prof = UserProfile.objects.get(user=User.objects.get(id=token.user_id))
            if total_issues <= 10:
                user_prof.title = 1
            elif total_issues <= 50:
                user_prof.title = 2
            elif total_issues <= 200:
                user_prof.title = 3
            else:
                user_prof.title = 4

            user_prof.save()

        redirect_url = "/report"

        if len(self.request.FILES.getlist("screenshots")) > 5:
            messages.error(self.request, "Max limit of 5 images!")
            return HttpResponseRedirect("/issue/")
        for screenshot in self.request.FILES.getlist("screenshots"):
            filename = screenshot.name
            extension = filename.split(".")[-1] 
            screenshot.name = filename[:99] + str(uuid.uuid4()) + "." + extension            
            default_storage.save(f"screenshots/{screenshot.name}",screenshot)
            IssueScreenshot.objects.create(image=f"screenshots/{screenshot.name}",issue=obj)

        obj_screenshots = IssueScreenshot.objects.filter(issue_id=obj.id)
        screenshot_text = ''
        for screenshot in obj_screenshots:
            screenshot_text += "![0](" + screenshot.image.url + ") "

        if domain.github and os.environ.get("GITHUB_ACCESS_TOKEN"):
            from giturlparse import parse
            import json
            import requests

            github_url = (
                domain.github.replace("https", "git").replace("http", "git") + ".git"
            )
            p = parse(github_url)

            url = "https://api.github.com/repos/%s/%s/issues" % (p.owner, p.repo)

            if not obj.user:
                the_user = "Anonymous"
            else:
                the_user = obj.user
            issue = {
                "title": obj.description,
                "body": obj.markdown_description + "\n\n" + screenshot_text +
                 "https://" + settings.FQDN + "/issue/"
                + str(obj.id) + " found by " + str(the_user) + " at url: " + obj.url,
                "labels": ["bug", settings.PROJECT_NAME_LOWER],
            }
            r = requests.post(
                url,
                json.dumps(issue),
                headers={
                    "Authorization": "token " + os.environ.get("GITHUB_ACCESS_TOKEN")
                },
            )
            response = r.json()
            obj.github_url = response["html_url"]
            obj.save()

        if not (self.request.user.is_authenticated or tokenauth):
            self.request.session["issue"] = obj.id
            self.request.session["created"] = created
            self.request.session["domain"] = domain.id
            login_url = reverse("account_login")
            messages.success(self.request, "Bug added!")
            return HttpResponseRedirect("{}?next={}".format(login_url, redirect_url))

        if tokenauth:
            self.process_issue(
                User.objects.get(id=token.user_id), obj, created, domain, True
            )
            return JsonResponse("Created", safe=False)
        else:
            self.process_issue(self.request.user, obj, created, domain)
            return HttpResponseRedirect(self.request.META.get("HTTP_REFERER"))
        
        

    def get_context_data(self, **kwargs):
        context = super(IssueCreate2, self).get_context_data(**kwargs)
        context["activities"] = Issue.objects.exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))[0:10]
        context["captcha_form"] = CaptchaForm()
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["hunts"] = Hunt.objects.exclude(plan="Free")[:4]
        context["leaderboard"] = (
            User.objects.filter(
                points__created__month=datetime.now().month,
                points__created__year=datetime.now().year,
            )
            .annotate(total_score=Sum("points__score"))
            .order_by("-total_score")[:10],
        )
        return context

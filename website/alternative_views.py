
import json
import os
from typing import Any
import urllib.error
import urllib.parse
from datetime import datetime,timezone, timedelta
from giturlparse import parse
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


from website.models import (
    Wallet,
    Issue,
    Points,
    Hunt,
    Domain,
    UserProfile,
    IssueScreenshot,
    CompanyAdmin,

)
from .forms import FormInviteFriend, UserProfileForm, HuntForm, CaptchaForm
from website.views import IssueBaseCreate

from django.conf import settings
from website.views import (
    IssueBaseCreate,
    IssueCreate
)
from django.views.generic import DetailView, TemplateView, ListView, View



class CreateHunt2(TemplateView):
    model = Hunt
    fields = ["url", "logo", "domain", "plan", "prize", "txn_id"]
    template_name = "hunt2.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        
        return render(request, self.template_name)
        # except Exception as e:
        #     print(e)
        #     return HttpResponseRedirect("/")

    # @method_decorator(login_required)
    # def post(self, request, *args, **kwargs):
    #     try:
    #         domain_admin = CompanyAdmin.objects.get(user=request.user)
    #         if (
    #             domain_admin.role == 1
    #             and (
    #                 str(domain_admin.domain.pk)
    #                 == ((request.POST["domain"]).split("-"))[0].replace(" ", "")
    #             )
    #         ) or domain_admin.role == 0:
    #             wallet, created = Wallet.objects.get_or_create(user=request.user)
    #             total_amount = (
    #                 Decimal(request.POST["prize_winner"])
    #                 + Decimal(request.POST["prize_runner"])
    #                 + Decimal(request.POST["prize_second_runner"])
    #             )
    #             if total_amount > wallet.current_balance:
    #                 return HttpResponse("failed")
    #             hunt = Hunt()
    #             hunt.domain = Domain.objects.get(
    #                 pk=(request.POST["domain"]).split("-")[0].replace(" ", "")
    #             )
    #             data = {}
    #             data["content"] = request.POST["content"]
    #             data["start_date"] = request.POST["start_date"]
    #             data["end_date"] = request.POST["end_date"]
    #             form = HuntForm(data)
    #             if not form.is_valid():
    #                 return HttpResponse("failed")
    #             if not domain_admin.is_active:
    #                 return HttpResponse("failed")
    #             if domain_admin.role == 1:
    #                 if hunt.domain != domain_admin.domain:
    #                     return HttpResponse("failed")
    #             hunt.domain = Domain.objects.get(
    #                 pk=(request.POST["domain"]).split("-")[0].replace(" ", "")
    #             )
    #             tzsign = 1
    #             offset = request.POST["tzoffset"]
    #             if int(offset) < 0:
    #                 offset = int(offset) * (-1)
    #                 tzsign = -1
    #             start_date = form.cleaned_data["start_date"]
    #             end_date = form.cleaned_data["end_date"]
    #             if tzsign > 0:
    #                 start_date = start_date + timedelta(
    #                     hours=int(int(offset) / 60), minutes=int(int(offset) % 60)
    #                 )
    #                 end_date = end_date + timedelta(
    #                     hours=int(int(offset) / 60), minutes=int(int(offset) % 60)
    #                 )
    #             else:
    #                 start_date = start_date - (
    #                     timedelta(
    #                         hours=int(int(offset) / 60), minutes=int(int(offset) % 60)
    #                     )
    #                 )
    #                 end_date = end_date - (
    #                     timedelta(
    #                         hours=int(int(offset) / 60), minutes=int(int(offset) % 60)
    #                     )
    #                 )
    #             hunt.starts_on = start_date
    #             hunt.prize_winner = Decimal(request.POST["prize_winner"])
    #             hunt.prize_runner = Decimal(request.POST["prize_runner"])
    #             hunt.prize_second_runner = Decimal(request.POST["prize_second_runner"])
    #             hunt.end_on = end_date
    #             hunt.name = request.POST["name"]
    #             hunt.description = request.POST["content"]
    #             wallet.withdraw(total_amount)
    #             wallet.save()
    #             try:
    #                 is_published = request.POST["publish"]
    #                 hunt.is_published = True
    #             except:
    #                 hunt.is_published = False
    #             hunt.save()
    #             return HttpResponse("success")
    #         else:
    #             return HttpResponse("failed")
    #     except:
    #         return HttpResponse("failed")


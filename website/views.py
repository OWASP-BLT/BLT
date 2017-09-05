from allauth.account.signals import user_logged_in
from django.dispatch import receiver
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import DetailView, TemplateView, ListView, UpdateView, CreateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic.edit import CreateView, FormView
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.http import Http404
from django.contrib.auth.models import User
from django.http import JsonResponse
from website.models import Issue, Points, Hunt, Domain, InviteFriend, UserProfile
from django.core.files import File
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Sum, Count, Q
from django.core.urlresolvers import reverse
from django.core.files.storage import default_storage
from django.views.generic import View
from django.core.files.base import ContentFile
from django.db.models.functions import ExtractMonth
from urlparse import urlparse
import urllib2
from selenium.webdriver import PhantomJS
import time
from bs4 import BeautifulSoup
import requests
import requests.exceptions
from django.core.mail import send_mail
from django.template.loader import render_to_string
from urlparse import urlsplit
from datetime import datetime
from collections import deque
import re
import os
import json
from user_agents import parse
from .forms import FormInviteFriend, UserProfileForm
import random
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from allauth.account.models import EmailAddress

def index(request, template="index.html"):
    try:
        domains = random.sample(Domain.objects.all(), 3)
    except:
        domains = None
    try:
        show_message = ''
        if not EmailAddress.objects.get(email=request.user.email).verified:
            show_message = 'Please verify your email address'
    except:
        show_message = ''
    open_issue_owasp = Domain.objects.get(name='owasp.org').open_issues.count()
    closed_issue_owasp = Domain.objects.get(name='owasp.org').closed_issues.count()
    context = {
        'activities': Issue.objects.all()[0:10],
        'domains': domains,
        'hunts': Hunt.objects.exclude(txn_id__isnull=True)[:4],
        'leaderboard': User.objects.filter(points__created__month=datetime.now().month).annotate(
            total_score=Sum('points__score')).order_by('-total_score')[:10],
        'not_verified': show_message,
        'open_issue_owasp': open_issue_owasp,
        'closed_issue_owasp': closed_issue_owasp,
    }
    return render(request, template, context)


def find_key(request, token):
    if token == os.environ.get("ACME_TOKEN"):
        return HttpResponse(os.environ.get("ACME_KEY"))
    for k, v in os.environ.items():  # os.environ.iteritems() in Python 2
        if v == token and k.startswith("ACME_TOKEN_"):
            n = k.replace("ACME_TOKEN_", "")
            return HttpResponse(os.environ.get("ACME_KEY_%s" % n))
    raise Http404("Token or key does not exist")

@csrf_exempt
def domain_check(request):
    if request.method =="POST":
        domain_url = request.POST.get('dom_url')
        if "http://" not in domain_url:
            if "https://" not in domain_url:
                domain_url = 'http://' + domain_url

        if Issue.objects.filter(url=domain_url).exists():
            isu = Issue.objects.filter(url=domain_url)
            if isu.count()>1:
                str1 = "www."
                if "www." in domain_url:
                    k = domain_url.index(str1)
                    k=k+4
                    t=k
                    while k<len(domain_url):
                        if (domain_url[k]!="/"):
                            k=k+1
                        elif (domain_url[k]=="/"):
                            break

                elif "http://" in domain_url:
                    k=7
                    t=k
                    while k<len(domain_url):
                        if (domain_url[k]!="/"):
                            k=k+1
                        elif (domain_url[k]=="/"):
                            break

                elif "https://" in domain_url:
                    k=8
                    t=k
                    while k<len(domain_url):
                        if (domain_url[k]!="/"):
                            k=k+1
                        elif (domain_url[k]=="/"):
                            break
                else:
                    return HttpResponse('Nothing passed')
                
                url_parsed = domain_url[t:k]
                data = {'number': 2, 'domain': url_parsed}
                return HttpResponse(json.dumps(data))

            else:
                try:
                    a =  Issue.objects.get(url=domain_url)
                except:
                    a = None
                data = {'number': 1, 'id' : a.id ,'description' : a.description, 'date' :a.created.day, 'month' :a.created.month,'year':a.created.year,}
                return HttpResponse(json.dumps(data))

        else:
            data = {'number': 3,}
            return HttpResponse(json.dumps(data))

class IssueBaseCreate(object):
    def form_valid(self, form):
        score = 3
        obj = form.save(commit=False)
        obj.user = self.request.user
        domain, created = Domain.objects.get_or_create(name=obj.domain_name.replace("www.", ""), defaults={
            'url': "http://" + obj.domain_name.replace("www.", "")})
        obj.domain = domain
        if self.request.POST.get('screenshot-hash'):
            reopen = default_storage.open('uploads\/' + self.request.POST.get('screenshot-hash') + '.png', 'rb')
            django_file = File(reopen)
            obj.screenshot.save(self.request.POST.get('screenshot-hash') + '.png', django_file, save=True)
        obj.user_agent = self.request.META.get('HTTP_USER_AGENT')
        obj.save()
        p = Points.objects.create(user=self.request.user, issue=obj, score=score)

    def process_issue(self, user, obj, created, domain, score=3):
        p = Points.objects.create(user=user, issue=obj, score=score)
        messages.success(self.request, 'Bug added! +' + str(score))

        if created:
            try:
                email_to = get_email_from_domain(domain)
            except:
                email_to = "support@" + domain.name

            domain.email = email_to
            domain.save()

            name = email_to.split("@")[0]

            msg_plain = render_to_string('email/domain_added.txt', {'domain': domain.name, 'name': name})
            msg_html = render_to_string('email/domain_added.txt', {'domain': domain.name, 'name': name})

            send_mail(
                domain.name + ' added to Bugheist',
                msg_plain,
                'Bugheist <support@bugheist.com>',
                [email_to],
                html_message=msg_html,
            )
        else:
            email_to = domain.email
            try:
                name = email_to.split("@")[0]
            except:
                email_to = "support@" + domain.name
                name = "support"
                domain.email = email_to
                domain.save()

            msg_plain = render_to_string('email/bug_added.txt', {
                'domain': domain.name,
                'name': name,
                'username': self.request.user,
                'id': obj.id,
                'description': obj.description,
                'label': obj.get_label_display,
            })
            msg_html = render_to_string('email/bug_added.txt', {
                'domain': domain.name,
                'name': name,
                'username': self.request.user,
                'id': obj.id,
                'description': obj.description,
                'label': obj.get_label_display,
            })
            send_mail(
                'Bug found on ' + domain.name,
                msg_plain,
                'Bugheist <support@bugheist.com>',
                [email_to],
                html_message=msg_html,
            )

        return HttpResponseRedirect("/")


class IssueCreate(IssueBaseCreate, CreateView):
    model = Issue
    fields = ['url', 'description', 'screenshot', 'domain', 'label']
    template_name = "report.html"

    def get_initial(self):
        initial = super(IssueCreate, self).get_initial()
        if self.request.POST.get('screenshot-hash'):
            initial['screenshot'] = 'uploads\/' + self.request.POST.get('screenshot-hash') + '.png'
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)
        if self.request.user.is_authenticated():
            obj.user = self.request.user
        domain, created = Domain.objects.get_or_create(name=obj.domain_name.replace("www.", ""), defaults={
            'url': "http://" + obj.domain_name.replace("www.", "")})
        obj.domain = domain
        if created and self.request.user.is_authenticated():
            p = Points.objects.create(user=self.request.user, domain=domain, score=1)
            messages.success(self.request, 'Domain added! + 1')

        if self.request.POST.get('screenshot-hash'):
            reopen = default_storage.open('uploads\/' + self.request.POST.get('screenshot-hash') + '.png', 'rb')
            django_file = File(reopen)
            obj.screenshot.save(self.request.POST.get('screenshot-hash') + '.png', django_file, save=True)
        obj.user_agent = self.request.META.get('HTTP_USER_AGENT')
        obj.save()

        if self.request.user.is_authenticated():
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

        if domain.github and os.environ.get("GITHUB_PASSWORD"):
            from giturlparse import parse
            from requests.auth import HTTPBasicAuth
            import json
            import requests
            github_url = domain.github.replace("https", "git").replace("http", "git") + ".git"
            p = parse(github_url)

            url = 'https://api.github.com/repos/%s/%s/issues' % (p.owner, p.repo)

            auth = HTTPBasicAuth(os.environ.get("GITHUB_USERNAME"), os.environ.get("GITHUB_PASSWORD"))
            issue = {'title': obj.description,
                     'body': "![0](" + obj.screenshot.url + ") http://bugheist.com/issue/" + str(obj.id),
                     'labels': ['bug', 'bugheist']}
            r = requests.post(url, json.dumps(issue), auth=auth)
            response = r.json()
            obj.github_url = response['html_url']
            obj.save()

        redirect_url = '/report'
        # redirect users to login
        if not self.request.user.is_authenticated():
            # we store the issue id on the user session to assign it as soon as he login/register
            self.request.session['issue'] = obj.id
            self.request.session['created'] = created
            self.request.session['domain'] = domain.id
            login_url = reverse('account_login')
            return HttpResponseRedirect(u'{}?next={}'.format(login_url, redirect_url))

        # assign issue
        self.process_issue(self.request.user, obj, created, domain)
        return HttpResponseRedirect(self.request.META.get('HTTP_REFERER'))

    def get_context_data(self, **kwargs):
        context = super(IssueCreate, self).get_context_data(**kwargs)
        context['activities'] = Issue.objects.all()[0:10]
        context['hunts'] = Hunt.objects.exclude(plan="Free")[:4]
        context['leaderboard'] = User.objects.filter(points__created__month=datetime.now().month).annotate(
            total_score=Sum('points__score')).order_by('-total_score')[:10],
        return context


class UploadCreate(View):
    template_name = "index.html"

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UploadCreate, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = request.FILES.get('image')
        result = default_storage.save("uploads\/" + self.kwargs['hash'] + '.png', ContentFile(data.read()))
        return JsonResponse({'status': result})


class InviteCreate(TemplateView):
    template_name = "invite.html"

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        exists = False
        domain = None
        if email:
            domain = email.split("@")[-1]
            try:
                ret = urllib2.urlopen('http://' + domain + '/favicon.ico')
                if ret.code == 200:
                    exists = "exists"
            except:
                pass
        context = {
            'exists': exists,
            'domain': domain,
            'email': email,
        }
        return render(request, "invite.html", context)


def profile(request):
    try:
        return redirect('/profile/' + request.user.username)
    except Exception:
        return redirect('/')


class UserProfileDetailView(DetailView):
    model = get_user_model()
    slug_field = "username"
    template_name = "profile.html"

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            messages.error(self.request, 'That user was not found.')
            return redirect("/")
        return super(UserProfileDetailView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        user = self.object
        context = super(UserProfileDetailView, self).get_context_data(**kwargs)
        context['my_score'] = Points.objects.filter(user=self.object).aggregate(total_score=Sum('score')).values()[0]
        context['websites'] = Domain.objects.filter(issue__user=self.object).annotate(total=Count('issue')).order_by('-total')
        context['activities'] = Issue.objects.filter(user=self.object)[0:10]
        context['profile_form'] = UserProfileForm()
        context['total_open'] = Issue.objects.filter(user=self.object,status="open").count()
        context['total_closed'] = Issue.objects.filter(user=self.object,status="closed").count()
        context['current_month'] = datetime.now().month
        context['graph'] = Issue.objects.filter(user=self.object).filter(created__month__gte=(datetime.now().month-6), created__month__lte=datetime.now().month) \
                        .annotate(month=ExtractMonth('created')).values('month').annotate(c=Count('id')).order_by()
        context['total_bugs'] = Issue.objects.filter(user=self.object).count()
        for i in range(0,7):
            context['bug_type_'+str(i)] = Issue.objects.filter(user=self.object,label=str(i))
        
        arr = []
        allFollowers = user.userprofile.follower.all()
        for userprofile in allFollowers:
            arr.append(User.objects.get(username=str(userprofile.user)))
        context['followers'] = arr

        arr = []
        allFollowing = user.userprofile.follows.all()
        for userprofile in allFollowing:
            arr.append(User.objects.get(username=str(userprofile.user)))
        context['following'] = arr

        context['followers_list'] = [str(prof.user.email) for prof in user.userprofile.follower.all()]
        context['bookmarks'] = user.userprofile.issue_saved.all()
        return context

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
        return redirect(reverse('profile', kwargs={'slug': kwargs.get('slug')}))


def delete_issue(request, id):
    issue = Issue.objects.get(id=id)
    if request.user.is_superuser or request.user == issue.user:
        issue.delete()
        messages.success(request, 'Issue deleted')
    return redirect('/')


class DomainDetailView(ListView):
    template_name = "domain.html"
    model = Issue

    def get_context_data(self, *args, **kwargs):
        context = super(DomainDetailView, self).get_context_data(*args, **kwargs)
        parsed_url = urlparse("http://" + self.kwargs['slug'])

        open_issue = Issue.objects.filter(domain__name__contains=self.kwargs['slug']).filter(
            status="open")
        close_issue = Issue.objects.filter(domain__name__contains=self.kwargs['slug']).filter(
            status="closed")

        context['name'] = parsed_url.netloc.split(".")[-2:][0].title()
        
        try:
            context['domain'] = Domain.objects.get(name=self.kwargs['slug'])
        except Domain.DoesNoTExist:
            raise Http404("domain not found")

        paginator = Paginator(open_issue, 10)
        page = self.request.GET.get('open')
        try:
            openissue_paginated = paginator.page(page)
        except PageNotAnInteger:
            openissue_paginated = paginator.page(1)
        except EmptyPage:
            openissue_paginated = paginator.page(paginator.num_pages)

        paginator = Paginator(close_issue, 10)
        page = self.request.GET.get('close')
        try:
            closeissue_paginated = paginator.page(page)
        except PageNotAnInteger:
            closeissue_paginated = paginator.page(1)
        except EmptyPage:
            closeissue_paginated = paginator.page(paginator.num_pages)

        context['opened_net'] = open_issue
        context['opened'] = openissue_paginated
        context['closed_net'] = close_issue
        context['closed'] = closeissue_paginated
        context['leaderboard'] = User.objects.filter(issue__url__contains=self.kwargs['slug']).annotate(
            total=Count('issue')).order_by('-total')
        context['current_month'] = datetime.now().month
        context['domain_graph'] = Issue.objects.filter(domain=context['domain']).filter(created__month__gte=(datetime.now().month-6), created__month__lte=datetime.now().month) \
                        .annotate(month=ExtractMonth('created')).values('month').annotate(c=Count('id')).order_by()
        context['pie_chart'] = Issue.objects.filter(domain=context['domain']).values('label').annotate(c=Count('label')).order_by()
        return context


class StatsDetailView(TemplateView):
    template_name = "stats.html"

    def get_context_data(self, *args, **kwargs):
        context = super(StatsDetailView, self).get_context_data(*args, **kwargs)
        response = requests.get(
            "https://chrome.google.com/webstore/detail/bugheist/bififchikfckcnblimmncopjinfgccme?hl=en")
        soup = BeautifulSoup(response.text)

        for item in soup.findAll("span", {"class": "e-f-ih"}):
            stats = item.attrs['title']
        context['extension_users'] = stats.replace(" users", "")
        context['bug_count'] = Issue.objects.all().count()
        context['user_count'] = User.objects.all().count()
        context['hunt_count'] = Hunt.objects.all().count()
        context['domain_count'] = Domain.objects.all().count()
        context['user_graph'] = User.objects.annotate(month=ExtractMonth('date_joined')).values('month').annotate(c=Count('id')).order_by()
        context['graph'] = Issue.objects.annotate(month=ExtractMonth('created')).values('month').annotate(c=Count('id')).order_by()
        context['pie_chart'] = Issue.objects.values('label').annotate(c=Count('label')).order_by()
        return context


class AllIssuesView(ListView):
    paginate_by = 20
    template_name = "list_view.html"

    def get_queryset(self):
        username = self.request.GET.get('user')
        if username is None:
            self.activities = Issue.objects.all()
        else:
            self.activities = Issue.objects.filter(user__username=username)
        return self.activities

    def get_context_data(self, *args, **kwargs):
        context = super(AllIssuesView, self).get_context_data(*args, **kwargs)
        paginator = Paginator(self.activities, self.paginate_by)
        page = self.request.GET.get('page')

        try:
            activities_paginated = paginator.page(page)
        except PageNotAnInteger:
            activities_paginated = paginator.page(1)
        except EmptyPage:
            activities_paginated = paginator.page(paginator.num_pages)

        context['activities'] = activities_paginated
        context['user'] = self.request.GET.get('user')
        return context

class SpecificIssuesView(ListView):
    paginate_by = 20
    template_name = "list_view.html"

    def get_queryset(self):
        username = self.request.GET.get('user')
        label = self.request.GET.get('label')
        query = 0;
        statu = 'none';

        if label == "General":
            query=0;
        elif label == "Number":
            query=1;
        elif label == "Functional":
            query=2;
        elif label == "Performance":
            query=3;
        elif label == "Security":
            query=4;
        elif label == "Typo":
            query=5;
        elif label == "Design":
            query=6;
        elif label == "open":
            statu='open';
        elif label == "closed":
            statu='closed';

        if username is None:
            self.activities = Issue.objects.all()
        elif statu!='none':
            self.activities = Issue.objects.filter(user__username=username,status=statu)
        else:
            self.activities = Issue.objects.filter(user__username=username,label=query)
        return self.activities

    def get_context_data(self, *args, **kwargs):
        context = super(SpecificIssuesView, self).get_context_data(*args, **kwargs)
        paginator = Paginator(self.activities, self.paginate_by)
        page = self.request.GET.get('page')

        try:
            activities_paginated = paginator.page(page)
        except PageNotAnInteger:
            activities_paginated = paginator.page(1)
        except EmptyPage:
            activities_paginated = paginator.page(paginator.num_pages)

        context['activities'] = activities_paginated
        context['user'] = self.request.GET.get('user')
        context['label'] = self.request.GET.get('label')
        return context


class LeaderboardView(ListView):
    model = User
    template_name = "leaderboard.html"

    def get_context_data(self, *args, **kwargs):
        context = super(LeaderboardView, self).get_context_data(*args, **kwargs)
        context['leaderboard'] = User.objects.annotate(total_score=Sum('points__score')).order_by(
            '-total_score').filter(total_score__gt=0)
        return context


class ScoreboardView(ListView):
    model = Domain
    template_name = "scoreboard.html"
    paginate_by = 5

    def get_context_data(self, *args, **kwargs):
        context = super(ScoreboardView, self).get_context_data(*args, **kwargs)
        companies = Domain.objects.all().order_by('-modified')
        paginator = Paginator(companies, self.paginate_by)
        page = self.request.GET.get('page')

        try:
            scoreboard_paginated = paginator.page(page)
        except PageNotAnInteger:
            scoreboard_paginated = paginator.page(1)
        except EmptyPage:
            scoreboard_paginated = paginator.page(paginator.num_pages)

        context['scoreboard'] = scoreboard_paginated
        context['user'] = self.request.GET.get('user')
        return context


def search(request, template="search.html"):
    query = request.GET.get('query')
    stype = request.GET.get('type')
    context = None
    if query is None:
        return render(request, template)
    if query[:6]=="issue:":
        stype="issue"
        query=query[6:]
    elif query[:7]=="domain:":
        stype="domain"
        query=query[7:]
    elif query[:5]=="user:":
        stype="user"
        query=query[5:]
    elif query[:6]=="label:":
        stype="label"
        query=query[6:]
    if stype == "issue" or stype is None:
        context = {
            'query': query,
            'type': stype,
            'issues': Issue.objects.filter(Q(description__icontains=query))[0:20]
        }
    elif stype == "domain":
        context = {
            'query': query,
            'type': stype,
            'domains': Domain.objects.filter(Q(url__icontains=query))[0:20]
        }
    elif stype == "user":
        context = {
            'query': query,
            'type': stype,
            'users': User.objects.filter(Q(username__icontains=query))[0:20]
        }
    elif stype == "label":
        context = {
            'query': query,
            'type': stype,
            'issues': Issue.objects.filter(Q(label__icontains=query))[0:20]
        }
    return render(request, template, context)


class HuntCreate(CreateView):
    model = Hunt
    fields = ['url', 'logo', 'prize', 'plan']
    template_name = "hunt.html"

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.save()
        return super(HuntCreate, self).form_valid(form)

    def get_success_url(self):
        if self.request.POST.get('plan') == "Ant":
            return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=TSZ84RQZ8RKKC"
        if self.request.POST.get('plan') == "Wasp":
            return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=E3EELQQ6JLXKY"
        if self.request.POST.get('plan') == "Scorpion":
            return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=9R3LPM3ZN8KCC"
        return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=HH7MNY6KJGZFW"


class IssueView(DetailView):
    model = Issue
    slug_field = "id"
    template_name = "issue.html"

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            self.object.views = (self.object.views or 0) + 1
            self.object.save()
        except:
            messages.error(self.request, 'That issue was not found.')
            return redirect("/")
        return super(IssueView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(IssueView, self).get_context_data(**kwargs)
        if self.object.user_agent:
            user_agent = parse(self.object.user_agent)
            context['browser_family'] = user_agent.browser.family
            context['browser_version'] = user_agent.browser.version_string
            context['os_family'] = user_agent.os.family
            context['os_version'] = user_agent.os.version_string
        context['users_score'] = \
            Points.objects.filter(user=self.object.user).aggregate(total_score=Sum('score')).values()[0]
        context['issue_count'] = Issue.objects.filter(url__contains=self.object.domain_name).count()
        context['all_comment'] = self.object.comments.all
        context['all_users'] = User.objects.all()
        context['likes'] = UserProfile.objects.filter(issue_upvoted=self.object).count()
        return context


def IssueEdit(request):
    if request.method == "POST":
        issue = Issue.objects.get(pk=request.POST.get('issue_pk'))
        uri = request.POST.get('domain')
        link = uri.replace("www.", "")
        if request.user == issue.user or request.user.is_superuser:
            domain, created = Domain.objects.get_or_create(name=link, defaults={'url': "http://" + link})
            issue.domain = domain
            issue.url = uri
            issue.description = request.POST.get('description')
            issue.label = request.POST.get('label')
            issue.save()
            if created:
                return HttpResponse("Domain Created")
            else:
                return HttpResponse("Updated")
        else:
            return HttpResponse("Unauthorised")


class EmailDetailView(TemplateView):
    template_name = "email.html"

    def get_context_data(self, *args, **kwargs):
        context = super(EmailDetailView, self).get_context_data(*args, **kwargs)
        context['emails'] = get_email_from_domain(self.kwargs['slug'])
        return context


def get_email_from_domain(domain_name):
    new_urls = deque(['http://' + domain_name])
    processed_urls = set()
    emails = set()
    emails_out = set()
    t_end = time.time() + 20

    while len(new_urls) and time.time() < t_end:
        url = new_urls.popleft()
        processed_urls.add(url)
        parts = urlsplit(url)
        base_url = "{0.scheme}://{0.netloc}".format(parts)
        path = url[:url.rfind('/') + 1] if '/' in parts.path else url
        try:
            response = requests.get(url)
        except:
            continue
        new_emails = set(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", response.text, re.I))
        if new_emails:
            emails.update(new_emails)
            break
        soup = BeautifulSoup(response.text)
        for anchor in soup.find_all("a"):
            link = anchor.attrs["href"] if "href" in anchor.attrs else ''
            if link.startswith('/'):
                link = base_url + link
            elif not link.startswith('http'):
                link = path + link
            if not link in new_urls and not link in processed_urls and link.find(domain_name) > 0:
                new_urls.append(link)

    for email in emails:
        if email.find(domain_name) > 0:
            emails_out.add(email)
    try:
        return list(emails_out)[0]
    except:
        return False


class InboundParseWebhookView(View):
    def post(self, request, *args, **kwargs):
        data = request.body
        for event in json.loads(data):
            try:
                domain = Domain.objects.get(email__iexact=event.get('email'))
                domain.email_event = event.get('event')
                if event.get('event') == "click":
                    domain.clicks = int(domain.clicks or 0) + 1
                domain.save()
            except Exception, e:
                pass

        return JsonResponse({'detail': 'Inbound Sendgrid Webhook recieved'})


def UpdateIssue(request):
    try:
        issue = Issue.objects.get(id=request.POST.get('issue_pk'))
    except Issue.DoesNoTExist:
        raise Http404("issue not found")
    
    if request.method == "POST" and request.user.is_superuser or (issue is not None and request.user == issue.user):
        if request.POST.get('action') == "close":
            issue.status = "closed"
            issue.closed_by = request.user
            issue.closed_date = datetime.now()

            msg_plain = msg_html = render_to_string('email/bug_updated.txt', {
                'domain': issue.domain.name,
                'name': issue.user.username,
                'id': issue.id,
                'username': request.user.username,
                'action': "closed",
            })
            subject = issue.domain.name + ' bug # ' + str(issue.id) + ' closed by ' + request.user.username

        elif request.POST.get('action') == "open":
            issue.status = "open"
            msg_plain = msg_html = render_to_string('email/bug_updated.txt', {
                'domain': issue.domain.name,
                'name': issue.domain.email.split("@")[0],
                'id': issue.id,
                'username': request.user.username,
                'action': "opened",
            })
            subject = issue.domain.name + ' bug # ' + str(issue.id) + ' opened by ' + request.user.username

        mailer = 'Bugheist <support@bugheist.com>'
        email_to = issue.user.email
        send_mail(subject, msg_plain, mailer, [email_to], html_message=msg_html)
        send_mail(subject, msg_plain, mailer, [issue.domain.email], html_message=msg_html)
        issue.save()
        return HttpResponse("Updated")

    elif request.method == "POST":
        return HttpResponse("invalid")


@receiver(user_logged_in)
def assign_issue_to_user(request, user, **kwargs):
    # get params from session
    issue_id = request.session.get('issue')
    created = request.session.get('created')
    domain_id = request.session.get('domain')
    if issue_id and domain_id:
        # clean session
        try:
            del request.session['issue']
            del request.session['domain']
            del request.session['created']
        except Exception:
            pass  # ignore errors while cleaning session
        request.session.modified = True
        # get objects using session parameters
        issue = Issue.objects.get(id=issue_id)
        domain = Domain.objects.get(id=domain_id)
        # assing user to issue
        issue.user = user
        issue.save()
        # process issue
        assigner = IssueBaseCreate()
        assigner.request = request
        assigner.process_issue(user, issue, created, domain)


class CreateInviteFriend(CreateView):
    template_name = 'invite_friend.html'
    model = InviteFriend
    form_class = FormInviteFriend
    success_url = reverse_lazy('invite_friend')

    def form_valid(self, form):
        from django.conf import settings
        from django.contrib.sites.shortcuts import get_current_site

        instance = form.save(commit=False)
        instance.sender = self.request.user
        instance.save()

        site = get_current_site(self.request)

        mail_status = send_mail(
            'Inivtation to {site} from {user}'.format(
                site=site.name,
                user=self.request.user.username
            ),
            'You have been invited by {user} to join {site} community.'.format(
                user=self.request.user.username,
                site=site.name
            ),
            settings.DEFAULT_FROM_EMAIL,
            [instance.recipient],
        )

        if mail_status and InviteFriend.objects.filter(sender=self.request.user).count() == 2:
            Points.objects.create(user=self.request.user, score=1)
            InviteFriend.objects.filter(sender=self.request.user).delete()

        messages.success(self.request,
                         'An email has been sent to your friend. Keep inviting your friends and get points!')
        return HttpResponseRedirect(self.success_url)

def follow_user(request,user):
    if request.method == "GET":
        userx = User.objects.get(username=user)        
        flag = 0
        list_userfrof = request.user.userprofile.follows.all()
        for prof in list_userfrof:
            if str(prof) == (userx.email):
                request.user.userprofile.follows.remove(userx.userprofile)
                flag = 1
        if flag != 1:
            request.user.userprofile.follows.add(userx.userprofile)
            msg_plain = render_to_string(
                'email/follow_user.txt',
                {'follower': request.user,'followed':userx})
            msg_html = render_to_string(
                'email/follow_user.txt',
                {'follower': request.user,'followed':userx})

            send_mail('You got a new follower!!',
                      msg_plain,
                      'Bugheist <support@bugheist.com>',
                      [userx.email],
                      html_message=msg_html)
        return HttpResponse("Success")

@login_required(login_url='/accounts/login')
def like_issue(request,issue_pk):
    context={}
    issue_pk=int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)
    if userprof in UserProfile.objects.filter(issue_upvoted=issue):
        userprof.issue_upvoted = None
    else:
        userprof.issue_upvoted = issue
        liked_user = issue.user
        liker_user = request.user
        issue_pk = issue.pk
        msg_plain = render_to_string(
            'email/issue_liked.txt',
            {'liker_user': liker_user.username,'liked_user':liked_user.username,'issue_pk':issue_pk})
        msg_html = render_to_string(
            'email/issue_liked.txt',
            {'liker_user': liker_user.username,'liked_user':liked_user.username,'issue_pk':issue_pk})

        send_mail('Your issue got an upvote!!',
                  msg_plain,
                  'Bugheist <support@bugheist.com>',
                  [liked_user.email],
                  html_message=msg_html)

    userprof.save()
    total_votes = UserProfile.objects.filter(issue_upvoted=issue).count()
    context['object'] = issue
    context['likes'] = total_votes
    return render(request, '_likes.html', context)

@login_required(login_url='/accounts/login')
def save_issue(request, issue_pk):
    issue_pk=int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)
    userprof.issue_saved.add(issue)
    return HttpResponse('OK')

@login_required(login_url='/accounts/login')
def unsave_issue(request, issue_pk):
    issue_pk=int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)
    userprof.issue_saved.remove(issue)
    return HttpResponse('OK')

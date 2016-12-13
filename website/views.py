from allauth.account.signals import user_logged_in
from django.dispatch import receiver
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import DetailView, TemplateView, ListView, UpdateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic.edit import CreateView, FormView
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, render_to_response, RequestContext, get_object_or_404
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.http import Http404
from actstream.models import Action, user_stream, actor_stream
from actstream import action
from django.contrib.auth.models import User
from actstream import registry
from django.http import JsonResponse
from website.models import Issue, Points, Hunt, Domain
from django.core.files import File
from django.core.urlresolvers import reverse
from django.db.models import Sum, Count
from django.core.urlresolvers import reverse
from django.core.files.storage import default_storage
from django.views.generic import View
from django.core.files.base import ContentFile
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
from .forms import IssueEditForm


registry.register(User)
registry.register(Issue)
registry.register(Domain)

def index(request, template="index.html"):
    context = {
        'activities': Action.objects.all()[0:10],
        'domains': Domain.objects.all().order_by('?')[0:16],
        'hunts': Hunt.objects.exclude(txn_id__isnull=True)[:4],
        'leaderboard':  User.objects.filter(points__created__month=datetime.now().month).annotate(total_score=Sum('points__score')).order_by('-total_score'),
    }
    return render_to_response(template, context, context_instance=RequestContext(request))


def find_key(request, token):
    if token == os.environ.get("ACME_TOKEN"):
        return HttpResponse(os.environ.get("ACME_KEY"))
    for k, v in os.environ.items():  #  os.environ.iteritems() in Python 2
        if v == token and k.startswith("ACME_TOKEN_"):
            n = k.replace("ACME_TOKEN_", "")
            return HttpResponse(os.environ.get("ACME_KEY_%s" % n))
    raise Http404("Token or key does not exist")


class IssueBaseCreate(object):

    def process_issue(self, user, obj, created, domain, score=3):
        p = Points.objects.create(user=user, issue=obj, score=score)
        action.send(user, verb='found a bug on website', target=obj)
        messages.success(self.request, 'Bug added! +'+ str(score))


        if created:
            from selenium import webdriver
            from pyvirtualdisplay import Display

            driver = webdriver.PhantomJS()
            driver.set_window_size(1120, 550)
            parsed_url = urlparse(obj.domain_name)
            driver.get("http://"+parsed_url.path)
            png_data = driver.get_screenshot_as_png()
            default_storage.save('webshots\/'+parsed_url.path +'.png', ContentFile(png_data))
            driver.quit()
            reopen = default_storage.open('webshots\/'+ parsed_url.path +'.png', 'rb')
            django_file = File(reopen)
            domain.webshot.save(parsed_url.path +'.png', django_file, save=True)

            # if self.request.user.is_authenticated():
            #     p = Points.objects.create(user=self.request.user,domain=domain,score=1)
            #     action.send(self.request.user, verb='added domain', target=domain)
            #     messages.success(self.request, 'Domain added! + 1')

            email_to = get_email_from_domain(parsed_url.path)
            if not email_to:
                email_to = "support@"+parsed_url.path
            domain.email = email_to
            domain.save()

            name = email_to.split("@")[0]

            msg_plain = render_to_string('email/domain_added.txt', {'domain': domain.name,'name':name})
            msg_html = render_to_string('email/domain_added.txt', {'domain': domain.name,'name':name})

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
                email_to = "support@"+domain.name
                name = "support"
                domain.email = email_to
                domain.save()

            msg_plain = render_to_string('email/bug_added.txt', {
                'domain': domain.name,
                'name':name,
                'username':self.request.user,
                'id':obj.id,
                })
            msg_html = render_to_string('email/bug_added.txt', {
                'domain': domain.name,
                'name':name,
                'username':self.request.user,
                'id':obj.id,
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
    fields = ['url','description','screenshot','domain']
    template_name = "index.html"

    def get_initial(self):
        initial = super(IssueCreate, self).get_initial()
        if self.request.POST.get('screenshot-hash'):
            initial['screenshot'] = 'uploads\/'+ self.request.POST.get('screenshot-hash') +'.png'
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)
        if self.request.user.is_authenticated():
            obj.user = self.request.user
        domain, created = Domain.objects.get_or_create(name=obj.domain_name.replace("www.", ""), url="http://"+obj.domain_name.replace("www.", ""))
        obj.domain=domain
        if self.request.POST.get('screenshot-hash'):
            reopen = default_storage.open('uploads\/'+ self.request.POST.get('screenshot-hash') +'.png', 'rb')
            django_file = File(reopen)
            obj.screenshot.save(self.request.POST.get('screenshot-hash') +'.png', django_file, save=True)
        obj.user_agent = self.request.META.get('HTTP_USER_AGENT')
        obj.save()

        redirect_url = '/'
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
        return HttpResponseRedirect(redirect_url)


    def get_context_data(self, **kwargs):
        context = super(IssueCreate, self).get_context_data(**kwargs)
        context['activities'] = Action.objects.all()[0:10]
        context['hunts'] = Hunt.objects.exclude(plan="Free")[:4]
        context['leaderboard'] = User.objects.filter(points__created__month=datetime.now().month).annotate(total_score=Sum('points__score')).order_by('-total_score'),
        return context


class UploadCreate(View):
    template_name = "index.html"

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UploadCreate, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = request.FILES.get('image')
        result = default_storage.save("uploads\/" + self.kwargs['hash'] +'.png', ContentFile(data.read()))
        return JsonResponse({'status':result})


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
        return render_to_response("invite.html", context, context_instance=RequestContext(request))


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
        context = super(UserProfileDetailView, self).get_context_data(**kwargs)
        context['my_score'] = Points.objects.filter(user=self.object).aggregate(total_score=Sum('score')).values()[0]
        context['websites'] = Domain.objects.filter(issue__user=self.object).annotate(total=Count('issue')).order_by('-total')
        context['activities'] = user_stream(self.object, with_user_activity=True)
        return context


def delete_issue(request, id):
    issue = Issue.objects.get(id=id)
    if request.user.is_superuser or request.user == issue.user:
        issue.delete()
        messages.success(request, 'Issue deleted')
    return redirect('/')


class DomainDetailView(TemplateView):
    template_name = "domain.html"

    def get_context_data(self, *args, **kwargs):
        context = super(DomainDetailView, self).get_context_data(*args, **kwargs)
        parsed_url = urlparse("http://"+self.kwargs['slug'])
        context['name'] = parsed_url.netloc.split(".")[-2:][0].title()

        try:
            context['domain'] = Domain.objects.get(name=self.kwargs['slug'])
        except:
            context['domain'] = self.kwargs['slug']
        context['issues'] = Issue.objects.complete().filter(domain__name__contains=self.kwargs['slug'])
        context['leaderboard'] = User.objects.filter(issue__url__contains=self.kwargs['slug']).annotate(total=Count('issue')).order_by('-total')
        return context


class StatsDetailView(TemplateView):
    template_name = "stats.html"

    def get_context_data(self, *args, **kwargs):
        context = super(StatsDetailView, self).get_context_data(*args, **kwargs)
        response = requests.get("https://chrome.google.com/webstore/detail/bugheist/bififchikfckcnblimmncopjinfgccme?hl=en")
        soup = BeautifulSoup(response.text)

        for item in  soup.findAll("span", { "class" : "e-f-ih" }):
            stats = item.attrs['title']
        context['extension_users'] = stats.replace(" users", "")
        context['bug_count'] = Issue.objects.complete().count()
        context['user_count'] = User.objects.all().count()
        context['hunt_count'] = Hunt.objects.all().count()
        context['domain_count'] = Domain.objects.all().count()
        return context


class AllIssuesView(ListView):
    model = Issue
    template_name = "list_view.html"

    def get_context_data(self, *args, **kwargs):
        context = super(AllIssuesView, self).get_context_data(*args, **kwargs)
        context['activities'] = Action.objects.all()
        return context


class LeaderboardView(ListView):
    model = User
    template_name = "leaderboard.html"

    def get_context_data(self, *args, **kwargs):
        context = super(LeaderboardView, self).get_context_data(*args, **kwargs)
        context['leaderboard'] = User.objects.annotate(total_score=Sum('points__score')).order_by('-total_score').filter(total_score__gt=0)
        return context


class HuntCreate(CreateView):
    model = Hunt
    fields = ['url','logo','prize','plan']
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
        context['users_score'] = Points.objects.filter(user=self.object.user).aggregate(total_score=Sum('score')).values()[0]
        context['issue_count'] = Issue.objects.complete().filter(url__contains=self.object.domain_name).count()
        return context


class IssueEditView(UpdateView):
    model = Issue
    slug_field = "id"
    template_name = "issue_edit.html"
    form_class = IssueEditForm

    def get_object(self):
        if self.request.user.is_superuser:
            issues = Issue.objects.complete()
        else:
            issues = Issue.objects.complete().filter(user=self.request.user)
        return get_object_or_404(issues, pk=self.kwargs['slug'])

    def get_success_url(self):
        return reverse('issue_view', args=(self.object.id,))

    def get_context_data(self, **kwargs):
        context = super(IssueEditView, self).get_context_data(**kwargs)
        if self.object.user_agent:
            user_agent = parse(self.object.user_agent)
            context['browser_family'] = user_agent.browser.family
            context['browser_version'] = user_agent.browser.version_string
            context['os_family'] = user_agent.os.family
            context['os_version'] = user_agent.os.version_string
        context['users_score'] = Points.objects.filter(user=self.object.user).aggregate(total_score=Sum('score')).values()[0]
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Issue Updated')
        return super(IssueEditView, self).form_valid(form)


class EmailDetailView(TemplateView):
    template_name = "email.html"

    def get_context_data(self, *args, **kwargs):
        context = super(EmailDetailView, self).get_context_data(*args, **kwargs)
        context['emails'] = get_email_from_domain(self.kwargs['slug'])
        return context


def get_email_from_domain(domain_name):
        new_urls = deque(['http://'+domain_name])
        processed_urls = set()
        emails = set()
        emails_out = set()
        t_end = time.time() + 20

        while len(new_urls) and time.time() < t_end:

            url = new_urls.popleft()
            processed_urls.add(url)
            parts = urlsplit(url)
            base_url = "{0.scheme}://{0.netloc}".format(parts)
            path = url[:url.rfind('/')+1] if '/' in parts.path else url
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
                if not link in new_urls and not link in processed_urls and link.find(domain_name)>0:
                    new_urls.append(link)

        for email in emails:
            if email.find(domain_name)>0:
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

class UpdateIssue(View):
    def post(self, request, *args, **kwargs):
        issue = Issue.objects.complete().get(id=request.POST.get('id'))
        if request.POST.get('action') == "close":
            messages.success(self.request, 'Issue Closed')
            issue.status = "closed"
            msg_plain = msg_html = render_to_string('email/bug_updated.txt', {
                'domain': issue.domain.name,
                'name':issue.user.username,
                'id':issue.id,
                'username':request.user.username,
                'action':"closed",
                })
            subject = issue.domain.name + ' bug # ' + str(issue.id) + ' closed by ' + request.user.username
            email_to = issue.user.email

        elif request.POST.get('action') == "open":
            messages.success(self.request, 'Issue Opened')
            issue.status = "open"
            msg_plain = msg_html = render_to_string('email/bug_updated.txt', {
                'domain': issue.domain.name,
                'name':issue.domain.email.split("@")[0],
                'id':issue.id,
                'username':request.user.username,
                'action':"opened",
                })
            subject = issue.domain.name + ' bug # ' + str(issue.id) + ' opened by ' + request.user.username
            email_to = issue.user.email
        send_mail(
            subject,
            msg_plain,
            'Bugheist <support@bugheist.com>',
            [email_to],
            html_message=msg_html,
        )
        issue.save()
        return HttpResponseRedirect(issue.get_absolute_url)

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
            pass    # ignore errors while cleaning session
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


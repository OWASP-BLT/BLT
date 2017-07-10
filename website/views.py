from allauth.account.signals import user_logged_in
from django.dispatch import receiver
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import DetailView, TemplateView, ListView, UpdateView, CreateView
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
from website.models import Issue, Points, Hunt, Domain, InviteFriend, UserProfile
from django.core.files import File
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Sum, Count, Q
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
from .forms import IssueEditForm, FormInviteFriend, UserProfileForm
import random
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from allauth.account.models import EmailAddress

registry.register(User)
registry.register(Issue)
registry.register(Domain)

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
        'activities': Action.objects.all()[0:10],
        'domains': domains,
        'hunts': Hunt.objects.exclude(txn_id__isnull=True)[:4],
        'leaderboard':  User.objects.filter(points__created__month=datetime.now().month).annotate(total_score=Sum('points__score')).order_by('-total_score')[:10],
        'not_verified': show_message,
        'open_issue_owasp': open_issue_owasp,
        'closed_issue_owasp': closed_issue_owasp,
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

    def form_valid(self, form):
        score = 3
        obj = form.save(commit=False)
        obj.user = self.request.user
        domain, created = Domain.objects.get_or_create(name=obj.domain_name.replace("www.", ""), defaults={'url':"http://"+obj.domain_name.replace("www.", "")})
        obj.domain=domain
        if self.request.POST.get('screenshot-hash'):
            reopen = default_storage.open('uploads\/'+ self.request.POST.get('screenshot-hash') +'.png', 'rb')
            django_file = File(reopen)
            obj.screenshot.save(self.request.POST.get('screenshot-hash') +'.png', django_file, save=True)
        obj.user_agent = self.request.META.get('HTTP_USER_AGENT')
        obj.save()
        p = Points.objects.create(user=self.request.user,issue=obj,score=score)
        action.send(self.request.user, verb='found a bug on website', target=obj)

    def process_issue(self, user, obj, created, domain, score=3):
        p = Points.objects.create(user=user, issue=obj, score=score)
        action.send(user, verb='found a bug on website', target=obj)
        messages.success(self.request, 'Bug added! +'+ str(score))

        if created:
            try:
                email_to = get_email_from_domain(domain)
            except:
                email_to = "support@"+domain.name
                
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
    fields = ['url','description','screenshot','domain', 'label']
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
        domain, created = Domain.objects.get_or_create(name=obj.domain_name.replace("www.", ""), defaults={'url':"http://"+obj.domain_name.replace("www.", "")})
        obj.domain=domain
        if created and self.request.user.is_authenticated():
            p = Points.objects.create(user=self.request.user,domain=domain,score=1)
            messages.success(self.request, 'Domain added! + 1')

        if self.request.POST.get('screenshot-hash'):
            reopen = default_storage.open('uploads\/'+ self.request.POST.get('screenshot-hash') +'.png', 'rb')
            django_file = File(reopen)
            obj.screenshot.save(self.request.POST.get('screenshot-hash') +'.png', django_file, save=True)
        obj.user_agent = self.request.META.get('HTTP_USER_AGENT')
        obj.save()

        if self.request.user.is_authenticated():       
            total_issues = Issue.objects.filter(user=self.request.user).count()
            user_prof = UserProfile.objects.get(user=self.request.user)
            if total_issues <=10:
                user_prof.title = 1
            elif total_issues <=50:
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
            github_url= domain.github.replace("https","git").replace("http","git")+".git"
            p = parse(github_url)

            url = 'https://api.github.com/repos/%s/%s/issues' % (p.owner, p.repo)

            auth = HTTPBasicAuth(os.environ.get("GITHUB_USERNAME"), os.environ.get("GITHUB_PASSWORD"))
            issue = {'title': obj.description,
                     'body': "![0](" + obj.screenshot.url + ") http://bugheist.com/issue/"+str(obj.id),
                     'labels': ['bug','bugheist']}
            r = requests.post(url, json.dumps(issue),auth=auth)
            response = r.json()
            obj.github_url = response['html_url']
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
        return HttpResponseRedirect(self.request.META.get('HTTP_REFERER'))


    def get_context_data(self, **kwargs):
        context = super(IssueCreate, self).get_context_data(**kwargs)
        context['activities'] = Action.objects.all()[0:10]
        context['hunts'] = Hunt.objects.exclude(plan="Free")[:4]
        context['leaderboard'] = User.objects.filter(points__created__month=datetime.now().month).annotate(total_score=Sum('points__score')).order_by('-total_score')[:10],
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
        context['profile_form'] = UserProfileForm()
        for i in range(1,7):
            context['bug_type_'+str(i)] = Issue.objects.filter(user=self.object,label=str(i))
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


class DomainDetailView(TemplateView):
    template_name = "domain.html"

    def get_context_data(self, *args, **kwargs):
        context = super(DomainDetailView, self).get_context_data(*args, **kwargs)
        parsed_url = urlparse("http://"+self.kwargs['slug'])
        context['name'] = parsed_url.netloc.split(".")[-2:][0].title()

        try:
            context['domain'] = Domain.objects.get(name=self.kwargs['slug'])
            context['issue_choice'] = self.kwargs['choice']
        except:
            context['domain'] = self.kwargs['slug']
            context['issue_choice'] = "all"
        context['issues'] = Issue.objects.filter(domain__name__contains=self.kwargs['slug'])
        context['leaderboard'] = User.objects.filter(issue__url__contains=self.kwargs['slug']).annotate(total=Count('issue')).order_by('-total')
        context['total_issues'] = Issue.objects.filter(domain__name__contains=self.kwargs['slug']).count()
        context['total_open'] = Issue.objects.filter(domain__name__contains=self.kwargs['slug']).filter(status="open").count()
        context['total_closed'] = Issue.objects.filter(domain__name__contains=self.kwargs['slug']).filter(status="closed").count()          

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
        context['bug_count'] = Issue.objects.all().count()
        context['user_count'] = User.objects.all().count()
        context['hunt_count'] = Hunt.objects.all().count()
        context['domain_count'] = Domain.objects.all().count()
        return context


class AllIssuesView(ListView):
    model = Issue
    paginate_by = 25
    template_name = "list_view.html"

    def get_context_data(self, *args, **kwargs):
        context = super(AllIssuesView, self).get_context_data(*args, **kwargs)
        
        activities = Action.objects.all()
        paginator = Paginator(activities, self.paginate_by)
        
        page = self.request.GET.get('page')

        try:
            activities_paginated = paginator.page(page)
        except PageNotAnInteger:
            activities_paginated = paginator.page(1)
        except EmptyPage:
            activities_paginated = paginator.page(paginator.num_pages)

        context['activities'] = activities_paginated

        return context


class LeaderboardView(ListView):
    model = User
    template_name = "leaderboard.html"

    def get_context_data(self, *args, **kwargs):
        context = super(LeaderboardView, self).get_context_data(*args, **kwargs)
        context['leaderboard'] = User.objects.annotate(total_score=Sum('points__score')).order_by('-total_score').filter(total_score__gt=0)
        return context


class ScoreboardView(ListView):
    model = Domain
    template_name = "scoreboard.html"

    def get_context_data(self, *args, **kwargs):
        context = super(ScoreboardView, self).get_context_data(*args, **kwargs)
        context['scoreboard'] = Domain.objects.all().order_by('-modified')
        return context

def search(request, template="search.html"):
    query = request.GET.get('query')
    stype = request.GET.get('type')
    if query is None:
        return render_to_response(template, context_instance=RequestContext(request))

    if stype == "issue" or stype is None:
        context = {
            'query' : query,
            'type' : stype,
            'issues' :  Issue.objects.filter(Q(description__icontains=query))
        }
    elif stype == "domain":
        context = {
            'query' : query,
            'type' : stype,
            'domains' :  Domain.objects.filter(Q(url__icontains=query))
        }
    elif stype == "user":
        context = {
            'query' : query,
            'type' : stype,
            'users' :  User.objects.filter(Q(username__icontains=query))
        }
    return render_to_response(template, context, context_instance=RequestContext(request))

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
        context['issue_count'] = Issue.objects.filter(url__contains=self.object.domain_name).count()
        context['all_comment'] = self.object.comments.all
        return context


class IssueEditView(UpdateView):
    model = Issue
    slug_field = "id"
    template_name = "issue_edit.html"
    form_class = IssueEditForm

    def get_object(self):
        if self.request.user.is_superuser:
            issues = Issue.objects.all()
        else:
            issues = Issue.objects.filter(user=self.request.user)
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
        context['issue_count'] = Issue.objects.filter(url__contains=self.object.domain_name).count()
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
        issue = Issue.objects.get(id=request.POST.get('id'))
        if request.POST.get('action') == "close":
            messages.success(self.request, 'Issue Closed')
            issue.status = "closed"
            issue.closed_by = request.user
            issue.closed_date = datetime.now()

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
        send_mail(
            subject,
            msg_plain,
            'Bugheist <support@bugheist.com>',
            [issue.domain.email],
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

        messages.success(self.request, 'An email has been sent to your friend. Keep inviting your friends and get points!')

        return HttpResponseRedirect(self.success_url)

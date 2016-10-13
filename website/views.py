from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import DetailView, TemplateView, ListView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic.edit import CreateView, FormView
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render_to_response, RequestContext
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.http import Http404
from actstream.models import Action, user_stream, actor_stream
from actstream import action
from django.contrib.auth.models import User
from actstream import registry
from django.http import JsonResponse
from website.models import Issue, Points, Hunt, Domain
from .forms import UploadFileForm
from django.core.files import File
from django.db.models import Sum, Count
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

from collections import deque
import re

registry.register(User)
registry.register(Issue)
registry.register(Domain)

def index(request, template="index.html"):
    context = {
        'activities': Action.objects.all()[0:10],
        'hunts': Hunt.objects.exclude(plan="Free")[:4],
        'leaderboard':  User.objects.annotate(total_score=Sum('points__score')).order_by('-total_score').filter(total_score__gt=0),
    }
    return render_to_response(template, context, context_instance=RequestContext(request))



class IssueCreate(CreateView):
    model = Issue
    fields = ['url','description','screenshot','domain']
    template_name = "index.html"

    def form_valid(self, form):
        score = 1
        obj = form.save(commit=False)
        obj.user = self.request.user
        domain, created = Domain.objects.get_or_create(name=obj.domain_name, url="http://"+obj.domain_name)
        obj.domain=domain
        if self.request.POST.get('screenshot-hash'):
            reopen = default_storage.open('uploads\/'+ self.request.POST.get('screenshot-hash') +'.png', 'rb')
            django_file = File(reopen)
            obj.screenshot.save(self.request.POST.get('screenshot-hash') +'.png', django_file, save=True)
            
        obj.save()
        if obj.screenshot:
            score = score + 2
        p = Points.objects.create(user=self.request.user,issue=obj,score=score)
        action.send(self.request.user, verb='found a bug on website', target=obj)
        messages.success(self.request, 'Bug added! +'+ str(score))
        return HttpResponseRedirect("/") 

    def get_context_data(self, **kwargs):
        context = super(IssueCreate, self).get_context_data(**kwargs)
        context['activities'] = Action.objects.all()[0:10]
        context['hunts'] = Hunt.objects.exclude(plan="Free")[:4]
        context['leaderboard'] = User.objects.annotate(total_score=Sum('points__score')).order_by('-total_score').filter(total_score__gt=0)
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

class DomainCreate(TemplateView):
    template_name = "domain.html"
    model = Domain

    def get(self, request, *args, **kwargs):


        parsed_url = urlparse(request.GET.get('domain'))
        domain, created = Domain.objects.get_or_create(name=parsed_url.path.replace("www.", ""), url="http://"+parsed_url.path.replace("www.", ""))

        if created:
            from selenium import webdriver
            from pyvirtualdisplay import Display

            #display = Display(visible=0, size=(1024, 768))
            #display.start()

            #driver = webdriver.Firefox()
            driver = webdriver.PhantomJS()
            driver.set_window_size(1120, 550)
            driver.get("http://"+parsed_url.path)
            png_data = driver.get_screenshot_as_png()
            default_storage.save('webshots\/'+parsed_url.path +'.png', ContentFile(png_data))
            driver.quit()
            reopen = default_storage.open('webshots\/'+ parsed_url.path +'.png', 'rb')
            django_file = File(reopen)
            domain.webshot.save(parsed_url.path +'.png', django_file, save=True)
            #messages.success(self.request, 'New domain detected, what email address will receive new bug found emails?')

            if self.request.user.is_authenticated():
                p = Points.objects.create(user=self.request.user,domain=domain,score=1)
                action.send(self.request.user, verb='added domain', target=domain)
                messages.success(self.request, 'Domain added! + 1')


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

        return super(DomainCreate, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(DomainCreate, self).get_context_data(*args, **kwargs)
        parsed_url = urlparse(self.request.GET.get('domain'))
        domain = Domain.objects.get(name=parsed_url.path.replace("www.", ""))

        context['name'] = domain.get_name
        context['domain'] = domain
        context['issues'] = Issue.objects.filter(url__contains=domain)
        return context

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
        context['websites'] = Issue.objects.filter(user=self.object).defer("domain").annotate(total=Count('domain')).order_by('-total')
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
        context['issues'] = Issue.objects.filter(url__contains=self.kwargs['slug'])
        return context
        


class StatsDetailView(TemplateView):
    template_name = "stats.html"


    def get_context_data(self, *args, **kwargs):
        domain_values = [res.domain_title for res in Issue.objects.all()]
        unique_domains = set(domain_values)
        unique_domain_count = len(unique_domains)
        context = super(StatsDetailView, self).get_context_data(*args, **kwargs)
        context['bug_count'] = Issue.objects.all().count()
        context['user_count'] = User.objects.all().count()
        context['hunt_count'] = Hunt.objects.all().count()
        context['domain_count'] = unique_domain_count
        return context

class AllIssuesView(ListView):
    model = Issue
    template_name = "list_view.html"

    def get_context_data(self, *args, **kwargs):
        context = super(AllIssuesView, self).get_context_data(*args, **kwargs)
        context['activities'] = Action.objects.all()
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
        except:
            messages.error(self.request, 'That issue was not found.')
            return redirect("/")
        return super(IssueView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(IssueView, self).get_context_data(**kwargs)
        context['users_score'] = Points.objects.filter(user=self.object.user).aggregate(total_score=Sum('score')).values()[0]
        context['issue_count'] = Issue.objects.filter(url__contains=self.object.domain_name).count()
        return context



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
            print url
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
                    print link
                    new_urls.append(link)
        
        for email in emails:
            if email.find(domain_name)>0:
                emails_out.add(email)
        try:
            return list(emails_out)[0]
        except:
            return False


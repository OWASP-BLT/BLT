from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import DetailView, TemplateView, ListView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic.edit import CreateView, FormView
from website.models import Issue, Hunt
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render_to_response, RequestContext
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.http import Http404
from actstream.models import Action, user_stream
from actstream import action
from django.contrib.auth.models import User
from actstream import registry
from django.http import JsonResponse
from website.models import Issue, Points
from .forms import UploadFileForm
from django.core.files import File
from django.db.models import Sum
from django.core.files.storage import default_storage
from django.views.generic import View
from django.core.files.base import ContentFile
from urlparse import urlparse


registry.register(User)
registry.register(Issue)

def index(request, template="index.html"):
    activities = Action.objects.all()[0:10] 
    my_score = 0 
    try:
        my_score = Points.objects.filter(user=request.user).aggregate(total_score=Sum('score')).values()
    except:
        pass # not logged in - fix this to check if logged in
    context = {
        'activities': activities,
        'hunts': Hunt.objects.all()[:4],
        'leaderboard':  Points.objects.values('user__username','user__email').annotate(total_score=Sum('score')).order_by('-total_score'),
        'my_score': my_score,
    }
    return render_to_response(template, context, context_instance=RequestContext(request))



class IssueCreate(CreateView):
    model = Issue
    fields = ['url','description','screenshot']
    template_name = "index.html"

    def form_valid(self, form):
        score = 1
        obj = form.save(commit=False)
        obj.user = self.request.user
        if self.request.POST.get('screenshot-hash'):
            reopen = default_storage.open('uploads\/'+ self.request.POST.get('screenshot-hash') +'.png', 'rb')
            django_file = File(reopen)
            obj.screenshot.save(self.request.POST.get('screenshot-hash') +'.png', django_file, save=True)
            
        obj.save()
        if obj.screenshot:
            score = score + 2
        p = Points.objects.create(user=self.request.user,issue=obj,score=score)
        action.send(self.request.user, verb='found a bug on website', target=obj)
        messages.success(self.request, 'Issue added! +'+ str(score))
        return HttpResponseRedirect("/") 
        
class UploadCreate(View):
    template_name = "index.html"

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UploadCreate, self).dispatch(request, *args, **kwargs)


    def post(self, request, *args, **kwargs):
        data = request.FILES.get('image')
        result = default_storage.save("uploads\/" + self.kwargs['hash'] +'.png', ContentFile(data.read()))
        print result
        return JsonResponse({'status':result})

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
        context['domain'] = self.kwargs['slug']
        context['issues'] = Issue.objects.filter(url__contains=self.kwargs['slug'])
        return context
        

class AllIssuesView(ListView):
    model = Issue
    template_name = "list_view.html"


class HuntCreate(CreateView):
    model = Hunt
    fields = ['url','logo','prize']
    template_name = "hunt.html"

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.save()
        return super(HuntCreate, self).form_valid(form)

    def get_success_url(self):
        if self.request.POST.get('plan') == "Ant":
           return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=HHPNDVH3999AJ"
        if self.request.POST.get('plan') == "Wasp":
           return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=VSEVRU69QSY9G"
        if self.request.POST.get('plan') == "Scorpion":
           return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=ARD6HFRM92DJU"
        return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=3H596KRUY7N7Q"


class IssueView(DetailView):
    model = Issue
    slug_field = "id"
    template_name = "issue.html"

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            messages.error(self.request, 'That issue was not found.')
            return redirect("/")
        return super(IssueView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(IssueView, self).get_context_data(**kwargs)
        context['users_score'] = Points.objects.filter(user=self.object.user).aggregate(total_score=Sum('score')).values()[0]
        context['issue_count'] = Issue.objects.filter(url__contains=self.object.hostname_domain).count()
        return context
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import DetailView, TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic.edit import CreateView, FormView
from website.models import Issue
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

registry.register(User)
registry.register(Issue)

def index(request, template="index.html"):
    activities = Action.objects.all()[0:10] 
    try:
        my_score = Points.objects.filter(user=request.user).annotate(total_score=Sum('score'))
    except:
        pass # not logged in - fix this to check if logged in
    context = {
        'activities': activities,
        'leaderboard': Points.objects.annotate(total_score=Sum('score')),
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
            reopen = open('media\uploads\/'+ self.request.POST.get('screenshot-hash') +'.png', 'rb')
            django_file = File(reopen)
            obj.screenshot.save(self.request.POST.get('screenshot-hash') +'.png', django_file, save=True)
            
        obj.save()
        if obj.screenshot:
            score = score + 2
        p = Points.objects.create(user=self.request.user,issue=obj,score=score)
        action.send(self.request.user, verb='entered issue', target=obj)
        messages.success(self.request, 'Issue added! +'+score)
        return HttpResponseRedirect("/") 
        
class UploadCreate(CreateView):
    form_class = UploadFileForm
    template_name = "index.html"

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UploadCreate, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        destination = open('media\uploads\/'+self.kwargs['hash'] +'.png', 'wb+')
        for chunk in request.FILES['image'].chunks():
            destination.write(chunk)
        destination.close()
        return JsonResponse({'status':'success'})

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
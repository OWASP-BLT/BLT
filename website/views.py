from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import DetailView
from django.views.generic.edit import CreateView
from website.models import Issue
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render_to_response, RequestContext
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.http import Http404
from actstream.models import Action, user_stream

def index(request, template="index.html"):
    activities = Action.objects.all()[0:10] 
    context = {
        'activities': activities,
    }
    return render_to_response(template, context, context_instance=RequestContext(request))



class IssueCreate(CreateView):
    model = Issue
    fields = ['url','description','screenshot']
    template_name = "index.html"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.save()
        messages.success(self.request, 'Issue added! +1 point!')
        return HttpResponseRedirect("/") 
        

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
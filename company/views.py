from django.shortcuts import render
from django.views.generic import DetailView, TemplateView, ListView, View

# Create your views here.



class CompanyDashboard(View):

    def get(self,request,*args,**kwargs):

        return render(request,"company/company_index.html")
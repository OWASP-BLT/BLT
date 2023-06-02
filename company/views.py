from django.shortcuts import render
from django.views.generic import DetailView, TemplateView, ListView, View

# Create your views here.



class CompanyDashboardAnalyticsView(View):

    def get(self,request,*args,**kwargs):

        return render(request,"company/company_analytics.html")

class CompanyDashboardManageBugsView(View):
    
    def get(self,request,*args,**kwargs):

        return render(request,"company/company_manage_bugs.html")
    

class CompanyDashboardManageDomainsView(View):
    
    def get(self,request,*args,**kwargs):

        return render(request,"company/company_manage_domains.html")
    

class AddDomainView(View):
    
    def get(self,request,*args,**kwargs):

        return render(request,"company/add_domain.html")
    


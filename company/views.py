import uuid
from django.shortcuts import render, redirect
from django.views.generic import DetailView, TemplateView, ListView, View
from website.models import Company, Domain, Issue, Hunt
from django.contrib.auth.models import AnonymousUser
from django.contrib import messages
from django.db.models import Q, Sum
# Create your views here.

def get_email_domain(email):
    domain = email.split("@")[-1]
    return domain

def validate_company_user(func):
    
    def wrapper(self,request,company,*args,**kwargs):

        company = Company.objects.filter(
            Q(admin=request.user) |
            Q(managers__in=[request.user])
        ).filter(company_id=company).first()

        if company == None:
            print(request)
            return redirect("company_view")

        return func(self,request,company.company_id,*args,**kwargs)

    return wrapper

def company_view(request,*args,**kwargs):

    
    restricted_domain = ["gmail.com","hotmail.com","outlook.com","yahoo.com","proton.com"]
    user = request.user
    
    if (not user.is_active):
        messages.info(request,"Email not verified.")
        return redirect("/")

    if (user==None or isinstance(user,AnonymousUser)):
        messages.error(request,"Login with company or domain provided email.")
        return redirect("/accounts/login/")
    

    domain = get_email_domain(user.email)

    if domain in  restricted_domain:
        messages.error(request,"Login with company or domain provided email.")
        return redirect("/")


    user_companies = Company.objects.filter(
        Q(admin=user) | 
        Q(managers__in=[user])
    )
    if (user_companies.first()==None):

        company = Company.objects.create(
            admin=user,
            name=domain,
            company_id=uuid.uuid4()
        )

        company.managers.add([user.id])
        company.save()        

    company = Company.objects.filter(
        Q(admin=user) | 
        Q(managers__in=[user])
    ).first()

    return redirect('company_analytics',company=company.company_id) 



class CompanyDashboardAnalyticsView(View):
    
    @validate_company_user
    def get(self,request,company,*args,**kwargs):


        total_company_bugs = Issue.objects.filter(domain__company__company_id=company).count()
        total_bug_hunts = Hunt.objects.filter(domain__company__company_id=company).count()
        total_domains = Domain.objects.filter(company__company_id=company).count()
        total_money_distributed = Hunt.objects.filter(domain__company__company_id=company,result_published=True).aggregate(total_money=Sum('prize'))["total_money"]
        total_money_distributed = 0 if total_money_distributed==None else total_money_distributed
        
        context = {
            'company': company,
            'total_info':{
                'total_company_bugs':total_company_bugs,
                'total_bug_hunts':total_bug_hunts,
                'total_domains':total_domains,
                'total_money_distributed':total_money_distributed
            }
        }
        return render(request,"company/company_analytics.html",context=context)

class CompanyDashboardManageBugsView(View):
    
    @validate_company_user
    def get(self,request,company,*args,**kwargs):

        context = {
            'company': company
        }
        return render(request,"company/company_manage_bugs.html",context=context)
    

class CompanyDashboardManageDomainsView(View):
    
    @validate_company_user
    def get(self,request,company,*args,**kwargs):

        context = {
            'company': company
        }

        return render(request,"company/company_manage_domains.html",context=context)
    

class AddDomainView(View):
    
    @validate_company_user
    def get(self,request,company,*args,**kwargs):

        context = {
            'company': company
        }

        return render(request,"company/add_domain.html",context=context)
    


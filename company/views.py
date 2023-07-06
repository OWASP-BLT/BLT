from typing import Any
import uuid
import json
from django import http 
import requests
from urllib.parse import urlparse
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import DetailView, TemplateView, ListView, View
from django.contrib.auth.models import AnonymousUser
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.db.models.functions import ExtractMonth
from django.core.files.storage import default_storage
from django.contrib.auth.models import User
from django.http import Http404

from website.models import Company, Domain, Issue, Hunt, UserProfile

restricted_domain = ["gmail.com","hotmail.com","outlook.com","yahoo.com","proton.com"]


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
            return redirect("company_view")
        
        return func(self,request,company.company_id,*args,**kwargs)

    return wrapper

def company_view(request,*args,**kwargs):

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

        messages.error(request,"You do not have a company, create one.")
        return redirect("register_company")        

    company = Company.objects.filter(
        Q(admin=user) | 
        Q(managers__in=[user])
    ).first()

    return redirect('company_analytics',company=company.company_id) 


class RegisterCompanyView(View):

    def get(self,request,*args,**kwargs):
        
        return render(request,'company/register_company.html')
    
    def post(self,request,*args,**kwargs):

        user = request.user
        data = request.POST

        if (not user.is_active):
            messages.info(request,"Email not verified.")
            return redirect("/")

        if (user==None or isinstance(user,AnonymousUser)):
            messages.error(request,"Login to create company")
            return redirect("/accounts/login/")
        

        user_domain = get_email_domain(user.email)
        company_name = data.get("company_name","").strip().lower()
        
        if user_domain in  restricted_domain:
            messages.error(request,"Login with company email in order to create the company.")
            return redirect("/")
        
        if user_domain != company_name:
            messages.error(request,"Company name doesn't match your email domain.")
            return redirect("register_company")
        

        managers = User.objects.values("id").filter(email__in=data["email"])

        company = Company.objects.filter(name=data["company_name"]).first()

        if (company!=None):
            messages.error(request,"Company already exist.")
            return redirect("register_company")

        company_logo = request.FILES.get("logo")
        company_logo_file = company_logo.name.split(".")[0]
        extension = company_logo.name.split(".")[-1] 
        company_logo.name = company_logo_file[:99] + str(uuid.uuid4()) + "." + extension            
        default_storage.save(f"company_logos/{company_logo.name}",company_logo)
        company = Company.objects.create(
            admin=user,
            name=data["company_name"],
            url=data["company_url"],
            email=data["support_email"],
            twitter=data["twitter_url"],
            facebook=data["facebook_url"],
            logo=f"logos/{company_logo.name}",
            is_active=True,
            company_id=uuid.uuid4()
        )

        company.managers.set([manager["id"] for manager in managers])
        company.save()        

        company = Company.objects.filter(
            Q(admin=user) | 
            Q(managers__in=[user])
        ).first()

        return redirect('company_analytics',company=company.company_id) 



class CompanyDashboardAnalyticsView(View):

    labels = {
            0: "General",
            1: "Number Error",
            2: "Functional",
            3: "Performance",
            4: "Security",
            5: "Typo",
            6: "Design",
            7: "Server Down",
        }
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    def get_general_info(self,company):

        total_company_bugs = Issue.objects.filter(domain__company__company_id=company).count()
        total_bug_hunts = Hunt.objects.filter(domain__company__company_id=company).count()
        total_domains = Domain.objects.filter(company__company_id=company).count()
        total_money_distributed = Issue.objects.filter(domain__company__company_id=company).aggregate(total_money=Sum('rewarded'))["total_money"]
        total_money_distributed = 0 if total_money_distributed==None else total_money_distributed

        return {
                'total_company_bugs':total_company_bugs,
                'total_bug_hunts':total_bug_hunts,
                'total_domains':total_domains,
                'total_money_distributed':total_money_distributed,
            }
    
    def get_bug_report_type_piechart_data(self,company):

        bug_report_type = Issue.objects.values('label').filter(domain__company__company_id=company).annotate(count=Count('label'))
        bug_report_type_labels = []
        bug_report_type_data = []
       
        for issue_count in bug_report_type:
            bug_report_type_labels.append(self.labels[issue_count['label']])
            bug_report_type_data.append(issue_count['count'])

        return {
                "bug_report_type_labels":json.dumps(bug_report_type_labels), # lst to be converted to json to avoid parsing errors
                "bug_report_type_data": json.dumps(bug_report_type_data)
            }
    
    def get_reports_on_domain_piechart_data(self,company):

        report_piechart = Issue.objects.values("domain__name").filter(domain__company__company_id=company).annotate(count=Count('domain__name'))
        report_labels = []
        report_data = []

        for domain_data in report_piechart:
            report_labels.append(domain_data["domain__name"])
            report_data.append(domain_data["count"])


        return {
            "bug_report_on_domains_labels": json.dumps(report_labels),
            "bug_report_on_domains_data": json.dumps(report_data)
        }
    
    def get_current_year_monthly_reported_bar_data(self,company):
        # returns chart data on no of bugs reported monthly on this company for current year
        
        current_year = timezone.now().year
        data_monthly = Issue.objects.filter(
                domain__company__company_id=company,
                created__year=current_year
            ).annotate(
                month=ExtractMonth('created')
            ).values(
                'month'
            ).annotate(
                count=Count('id')
            ).order_by('month')  
        
    
        data = [0,0,0,0,0,0,0,0,0,0,0,0] #count

        for data_month in data_monthly:
            data[data_month["month"]] = data_month["count"]

        return {
            "bug_monthly_report_labels": json.dumps(self.months),
            "bug_monthly_report_data": json.dumps(data),
            "max_count": max(data)
        }       


    def bug_rate_increase_descrease_weekly(self,company, is_accepted_bugs=False):
        # returns stats by comparing the count of past 8-15 days (1 week) activity to this (0 - 7) week.

        current_date = timezone.now().date()
        prev_week_start_date = current_date - timedelta(days=15)
        prev_week_end_date = current_date - timedelta(days=8) 

        this_week_start_date = current_date - timedelta(days=7)
        this_week_end_date = current_date

        if is_accepted_bugs:

            prev_week_issue_count = Issue.objects.filter(
                domain__company__company_id=company,
                created__date__range=[prev_week_start_date, prev_week_end_date],
                verified=True
            ).count()

            this_week_issue_count = Issue.objects.filter(
                domain__company__company_id=company,
                created__date__range=[this_week_start_date, this_week_end_date],
                verified=True
            ).count()
        
        else:

            prev_week_issue_count = Issue.objects.filter(
                domain__company__company_id=company,
                created__date__range=[prev_week_start_date, prev_week_end_date]
            ).count()

            this_week_issue_count = Issue.objects.filter(
                domain__company__company_id=company,
                created__date__range=[this_week_start_date, this_week_end_date]
            ).count()

        if prev_week_issue_count == 0:
            percent_increase = this_week_issue_count * 100
        else:
            percent_increase = ((this_week_issue_count - prev_week_issue_count) / prev_week_issue_count) * 100


        return {
            
            "percent_increase": percent_increase,
            "is_increasing": True if (this_week_issue_count - prev_week_issue_count) >=0 else False,
            "this_week_issue_count":this_week_issue_count
        }
    
    def get_spent_on_bugtypes(self,company):

        spent_on_bugtypes = Issue.objects.values('label').filter(domain__company__company_id=company).annotate(spent=Sum('rewarded'))
        labels = list(self.labels.values())
        data = [0 for label in labels] # make all labels spent 0 / init with 0

        for bugtype in spent_on_bugtypes:
            data[bugtype["label"]] = bugtype["spent"]

        return {
            "labels": json.dumps(labels),
            "data": json.dumps(data),
            "zipped_data": zip(labels,data)
        }

    @validate_company_user
    def get(self,request,company,*args,**kwargs):

        companies = Company.objects.values("name","company_id").filter(
            Q(managers__in=[request.user]) | 
            Q(admin=request.user)
        ).distinct()

        context = {
            "company": company,
            "companies":companies,
            "company_obj": Company.objects.filter(company_id=company).first(),
            "total_info":self.get_general_info(company),
            "bug_report_type_piechart_data":self.get_bug_report_type_piechart_data(company),
            "reports_on_domain_piechart_data": self.get_reports_on_domain_piechart_data(company),
            "get_current_year_monthly_reported_bar_data":self.get_current_year_monthly_reported_bar_data(company),
            "bug_rate_increase_descrease_weekly": self.bug_rate_increase_descrease_weekly(company),
            "accepted_bug_rate_increase_descrease_weekly": self.bug_rate_increase_descrease_weekly(company,True),
            "spent_on_bugtypes": self.get_spent_on_bugtypes(company)
        }
        self.get_spent_on_bugtypes(company)
        return render(request,"company/company_analytics.html",context=context)

class CompanyDashboardManageBugsView(View):
    
    @validate_company_user
    def get(self,request,company,*args,**kwargs):

        companies = Company.objects.values("name","company_id").filter(
            Q(managers__in=[request.user]) | 
            Q(admin=request.user)
        ).distinct()

        context = {
            'company': company,
            "companies":companies,
            "company_obj": Company.objects.filter(company_id=company).first(),

        }
        return render(request,"company/company_manage_bugs.html",context=context)
    

class CompanyDashboardManageDomainsView(View):
    
    @validate_company_user
    def get(self,request,company,*args,**kwargs):

        domains = Domain.objects.values("id","name","url","logo").filter(company__company_id=company).order_by("modified")

        companies = Company.objects.values("name","company_id").filter(
            Q(managers__in=[request.user]) | 
            Q(admin=request.user)
        ).distinct()

        context = {
            'company': company,
            "companies": companies,
            "company_obj": Company.objects.filter(company_id=company).first(),
            'domains':domains
        }

        return render(request,"company/company_manage_domains.html",context=context)


class AddDomainView(View):

    def dispatch(self, request, *args, **kwargs):
        
        method = self.request.POST.get('_method', '').lower()
        
        if method == 'delete':
            return self.delete(request,*args,**kwargs)
        
        return super().dispatch(request, *args, **kwargs)

    @validate_company_user
    def get(self,request,company,*args,**kwargs):

        companies = Company.objects.values("name","company_id").filter(
            Q(managers__in=[request.user]) | 
            Q(admin=request.user)
        ).distinct()
        
        context = {
            'company': company,
            "company_obj": Company.objects.filter(company_id=company).first(),
            'companies': companies
        }

        return render(request,"company/add_domain.html",context=context)
    

    @validate_company_user
    def post(self,request,company,*args,**kwargs):
        
        
        domain_data = {
            "name": request.POST.get("domain_name",None),
            "url": request.POST.get("domain_url",None),
            "github": request.POST.get("github_url",None),
            "twitter": request.POST.get("twitter_url",None),
            "facebook": request.POST.get("facebook_url",None),
        }

        if domain_data["name"] == None:
            messages.error(request,"Enter domain name")
            return redirect("add_domain",company) 
        
        if domain_data["url"] == None:
            messages.error(request,"Enter domain url")
            return redirect("add_domain",company)
        
        parsed_url = urlparse(domain_data["url"])
        domain = parsed_url.hostname

        domain_data["url"] = f"{parsed_url.scheme}://{domain}" # clean the domain eg https://mail.google.com/mail1# -> https://mail.google.com  
        domain_data["name"] = domain_data["name"].lower()


        managers_list = request.POST.getlist("email")
        company_obj = Company.objects.get(company_id=company)


        domain_exist = Domain.objects.filter(
            Q(name=domain_data["name"]) |
            Q(url=domain)
        ).exists()

        if domain_exist:
            messages.error(request,"Domain name or url already exist.")
            return redirect("add_domain",company)

        # validate domain url
        try:
            response = requests.get(domain_data["url"] ,timeout=2)
            if response.status_code != 200:
                raise Exception
        except:
            messages.error(request,"Domain does not exist.")
            return redirect("add_domain",company)
        
        # validate domain email 
        user_email_domain = request.user.email.split("@")[-1]

        if domain != user_email_domain:
            messages.error(request,"your email does not match domain email. Action Denied!")
            return redirect("add_domain",company)
        
        for domain_manager_email in managers_list:

            user_email_domain = domain_manager_email.split("@")[-1]
            if domain != user_email_domain:
                messages.error(request,f"Manager: {domain_manager_email} does not match domain email.")
                return redirect("add_domain",company)



        domain_logo = request.FILES.get("logo")
        domain_logo_file = domain_logo.name.split(".")[0]
        extension = domain_logo.name.split(".")[-1] 
        domain_logo.name = domain_logo_file[:99] + str(uuid.uuid4()) + "." + extension            
        default_storage.save(f"logos/{domain_logo.name}",domain_logo)

        webshot_logo = request.FILES.get("webshot") 
        webshot_logo_file = webshot_logo.name.split(".")[0]
        extension = webshot_logo.name.split(".")[-1] 
        webshot_logo.name = webshot_logo_file[:99] + str(uuid.uuid4()) + "." + extension            
        default_storage.save(f"webshots/{webshot_logo.name}",webshot_logo)
        
        domain_managers = User.objects.filter(email__in=managers_list,is_active=True)
        
        domain = Domain.objects.create(
            **domain_data,
            company=company_obj,
            logo=f"logos/{domain_logo.name}",
            webshot=f"webshots/{webshot_logo.name}",
        )

        domain.managers.set(domain_managers)
        domain.save()

        return redirect("company_manage_domains",company)
    
    @validate_company_user
    def delete(self,request,company,*args,**kwargs):
        
        domain_id = request.GET.get("domain")
        domain = get_object_or_404(Domain,id=domain_id)
        domain.delete()
        messages.success(request,"Domain deleted successfully")
        return redirect("company_manage_domains",company)

    # @validate_company_user
    # def put(self,request,company,*args,**kwargs):

    #     domain_id = kwargs.get("domain",None)
    #     companies = Company.objects.values("name","company_id").filter(
    #         Q(managers__in=[request.user]) | 
    #         Q(admin=request.user)
    #     )
    #     domain_info = (
    #         Domain.objects
    #         .values("id","name","url","company__name","github","twitter","facebook","logo","webshot")
    #         .filter(id=domain_id).first()
    #     )
    #     managers_email = User.objects.values("email").filter(user_domains__id=domain_id)

    #     if domain_info == {}:
    #         return Http404("Domain not found")
        
    #     context = {
    #         'company': company,
    #         'companies': companies,
    #         'domain_info': managers_email
    #     }
    #     return render(request,"company/edit_domain.html", context)


class DomainView(View):

    def get_current_year_monthly_reported_bar_data(self,domain_id):
        # returns chart data on no of bugs reported monthly on this company for current year
        
        current_year = timezone.now().year
        data_monthly = Issue.objects.filter(
                domain__id=domain_id,
                created__year=current_year
            ).annotate(
                month=ExtractMonth('created')
            ).values(
                'month'
            ).annotate(
                count=Count('id')
            ).order_by('month')  
        
    
        data = [0,0,0,0,0,0,0,0,0,0,0,0] #count

        for data_month in data_monthly:
            data[data_month["month"]] = data_month["count"]

        return json.dumps(data)     

    def get(self,request,pk,*args,**kwargs):

        domain = Domain.objects.values("id","name","url","company__name","company__company_id","created__day","created__month","created__year","twitter","facebook","github","logo","webshot").filter(id=pk).first()

        if domain == {}:
            raise Http404("Domain not found")

        total_money_distributed = Issue.objects.filter(pk=domain["id"]).aggregate(total_money=Sum('rewarded'))["total_money"]
        total_money_distributed = 0 if total_money_distributed==None else total_money_distributed

        total_bug_reported = Issue.objects.filter(pk=domain["id"]).count()
        total_bug_accepted = Issue.objects.filter(pk=domain["id"], verified=True).count()

        # get latest reported public issues
        latest_issues = (
            Issue.objects
            .values("id","domain__name","url","description","user__id","user__username","user__userprofile__user_avatar","label","status","verified","rewarded","created__day","created__month","created__year")
            .filter(domain__id=domain["id"],is_hidden=False).order_by("-created")
            [:11]
        )
        issue_labels = [label[-1] for label in Issue.labels]
        cleaned_issues = []
        for issue in latest_issues:
            cleaned_issues.append({
                **issue,
                "label": issue_labels[issue["label"]]
            })

        

        # get top testers
        top_testers = Issue.objects.values("user__id","user__username","user__userprofile__user_avatar").filter(user__isnull=False).annotate(count=Count('user__username')).order_by("-count")[:16]

        context = {
            **domain,
            "total_money_distributed":total_money_distributed,
            "total_bug_reported": total_bug_reported,
            "total_bug_accepted": total_bug_accepted,
            "latest_issues": cleaned_issues,
            "monthly_activity_chart":self.get_current_year_monthly_reported_bar_data(domain["id"]),
            "top_testers":top_testers,
        }

        return render(request, "company/view_domain.html", context)


class CompanyDashboardManageRolesView(View):

    @validate_company_user
    def get(self,request,company,*args,**kwargs):
        
        companies = Company.objects.values("name","company_id").filter(
            Q(managers__in=[request.user]) | 
            Q(admin=request.user)
        ).distinct()
        
        domains = Domain.objects.filter(
            Q(company__company_id=company) &
            ( Q(company__managers__in=[request.user]) | Q(company__admin=request.user) )
            
        )
        domains_data = []
        for domain in domains:
            _id = domain.id
            name = domain.name
            managers = domain.managers.values("username","userprofile__user_avatar").all()
            domains_data.append({
                "id":_id,
                "name":name,
                "managers":managers
            })

        context = {
            'company': company,
            "company_obj": Company.objects.filter(company_id=company).first(),
            'companies': companies,
            'domains': domains_data,
        }

        return render(request,"company/company_manage_roles.html",context)
    

    def post(self,request,company,*args,**kwargs):

        domain = Domain.objects.filter(
            Q(company__company_id=company) &
            Q(id=request.POST.get('domain',None)) &
            ( Q(company__admin=request.user) | Q(managers__in=[request.user]) )   
        ).first()
        
        if domain == None:
            messages.error("you are not manager of this domain.")
            return redirect('company_manage_roles',company)
        
        domain_name = domain.name
        managers_list = request.POST.getlist("email",[])

        # validate emails for domain
        for domain_manager_email in managers_list:

            user_email_domain = domain_manager_email.split("@")[-1]
            if domain_name != user_email_domain:
                messages.error(request,f"Manager: {domain_manager_email} does not match domain email.")
                return redirect("company_manage_roles",company)
        
        domain_managers = User.objects.filter(email__in=managers_list,is_active=True)
        
        for manager in domain_managers:
            domain.managers.add(manager.id)

        domain.save()

        messages.success(request,"successfully added the managers")
        return redirect('company_manage_roles',company)


class CompanyDashboardManageBughuntView(View):

    @validate_company_user
    def get(self,request,company,*args,**kwargs):

        companies = Company.objects.values("name","company_id").filter(
            Q(managers__in=[request.user]) | 
            Q(admin=request.user)
        ).distinct()
        
        context = {
            'company': company,
            "company_obj": Company.objects.filter(company_id=company).first(),
            'companies': companies
        }

        return render(request,"company/company_manage_bughunts.html",context) 

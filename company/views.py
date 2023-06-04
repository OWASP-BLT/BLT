import uuid
import json 
from django.shortcuts import render, redirect
from django.views.generic import DetailView, TemplateView, ListView, View
from website.models import Company, Domain, Issue, Hunt
from django.contrib.auth.models import AnonymousUser
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.db.models.functions import ExtractMonth
from datetime import timedelta

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

    def get_general_info(self,company):

        total_company_bugs = Issue.objects.filter(domain__company__company_id=company).count()
        total_bug_hunts = Hunt.objects.filter(domain__company__company_id=company).count()
        total_domains = Domain.objects.filter(company__company_id=company).count()
        total_money_distributed = Hunt.objects.filter(domain__company__company_id=company,result_published=True).aggregate(total_money=Sum('prize'))["total_money"]
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
       
        for issue_count in bug_report_type:
            bug_report_type_labels.append(labels[issue_count['label']])
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
        
        months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        data = [0,0,0,0,0,0,0,0,0,0,0,0] #count

        for data_month in data_monthly:
            data[data_month["month"]] = data_month["count"]

        return {
            "bug_monthly_report_labels": json.dumps(months),
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
    

    @validate_company_user
    def get(self,request,company,*args,**kwargs):


        context = {
            "company": company,
            "total_info":self.get_general_info(company),
            "bug_report_type_piechart_data":self.get_bug_report_type_piechart_data(company),
            "reports_on_domain_piechart_data": self.get_reports_on_domain_piechart_data(company),
            "get_current_year_monthly_reported_bar_data":self.get_current_year_monthly_reported_bar_data(company),
            "bug_rate_increase_descrease_weekly": self.bug_rate_increase_descrease_weekly(company),
            "accepted_bug_rate_increase_descrease_weekly": self.bug_rate_increase_descrease_weekly(company,True)
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
    


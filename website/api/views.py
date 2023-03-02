from datetime import datetime

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db.models import Sum
from django.contrib.auth.models import AnonymousUser

from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.conf import settings

from website.models import (
    Issue,
    Domain,
)
from website.serializers import (
    IssueSerializer,
    UserProfileSerializer,
    DomainSerializer,
)

from website.models import (
    UserProfile,
    User,
    Points,
    Hunt
)

from website.views import (
    LeaderboardBase

)

# API's


class UserIssueViewSet(viewsets.ModelViewSet):
    """
    User Issue Model View Set
    """

    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ("user__username", "user__id")
    http_method_names = ["get", "post", "head"]


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    User Profile View Set
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    filter_backends = (filters.SearchFilter,)
    search_fields = ("id", "user__id", "user__username")
    http_method_names = ["get", "post", "head","put"]

    def retrieve(self, request,pk,*args, **kwargs):
        
        user_profile = UserProfile.objects.filter(user__id=pk).first()

        if user_profile == None:
            return Response({"detail": "Not found."},status=404)
        
        serializer = self.get_serializer(user_profile)
        return Response(serializer.data)

    def update(self, request, pk,*args, **kwargs):
        
        user_profile = request.user.userprofile
        
        if user_profile==None:
            return Response({"detail": "Not found."},status=404)
        
        instance = user_profile
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


class DomainViewSet(viewsets.ModelViewSet):
    """
    Domain View Set
    """

    serializer_class = DomainSerializer
    queryset = Domain.objects.all()
    filter_backends = (filters.SearchFilter,)
    search_fields = ("url", "name")
    http_method_names = ["get", "post", "head"]


class IssueViewSet(viewsets.ModelViewSet):
    """
    Issue View Set
    """

    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ("url", "description", "user__id")
    http_method_names = ["get", "post", "head"]

    def get_issue_info(self,request,issue):
        
        if issue == None:
            return {}

        screenshots = [
            # replacing space with url space notation
            request.build_absolute_uri(screenshot.image.url)
            for screenshot in 
            issue.screenshots.all()
        ] + ( [request.build_absolute_uri(issue.screenshot.url)] if issue.screenshot else [] )

        upvotes = issue.upvoted.all().__len__()
        flags = issue.flaged.all().__len__()
        upvotted = False
        flagged = False

        if type(request.user) != AnonymousUser:

            upvotted = bool(request.user.userprofile.issue_upvoted.filter(id=issue.id).first())
            flagged = bool(request.user.userprofile.issue_flaged.filter(id=issue.id).first())          

        issue = Issue.objects.filter(id=issue.id)
        issue_obj = issue.first()

        issue_data = IssueSerializer(issue_obj)

        return {
            **issue_data.data,
            "closed_by": issue_obj.closed_by.username if issue_obj.closed_by else None,
            "upvotes": upvotes,
            "flags": flags,
            "upvotted": upvotted,
            "flagged": flagged,
            "screenshots":screenshots
        }


    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())

        issues = []
        page = self.paginate_queryset(queryset)
        if page is None:
            return Response(issues)
            
        for issue in page:
            issues.append(self.get_issue_info(request,issue))

        return self.get_paginated_response(issues)


    def retrieve(self, request, pk,*args, **kwargs):

        issue = Issue.objects.filter(id=pk).first()
        return Response(self.get_issue_info(request,issue))

class LikeIssueApiView(APIView):

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request,id,format=None,*args, **kwargs):
        return Response({
            "likes":UserProfile.objects.filter(issue_upvoted__id=id).count(),
        })
    
    def post(self,request,id,format=None,*args,**kwargs):

        issue = Issue.objects.get(id=id)
        userprof = UserProfile.objects.get(user=request.user)
        if userprof in UserProfile.objects.filter(issue_upvoted=issue):
            userprof.issue_upvoted.remove(issue)
            userprof.save()
            return Response({"issue":"unliked"})
        else:
            userprof.issue_upvoted.add(issue)
            userprof.save()
            
            liked_user = issue.user
            liker_user = request.user
            issue_pk = issue.pk

            if liked_user:

                msg_plain = render_to_string(
                    "email/issue_liked.txt",
                    {
                        "liker_user": liker_user.username,
                        "liked_user": liked_user.username,
                        "issue_pk": issue_pk,
                    },
                )
                msg_html = render_to_string(
                    "email/issue_liked.txt",
                    {
                        "liker_user": liker_user.username,
                        "liked_user": liked_user.username,
                        "issue_pk": issue_pk,
                    },
                )

                send_mail(
                    "Your issue got an upvote!!",
                    msg_plain,
                    settings.EMAIL_TO_STRING,
                    [liked_user.email],
                    html_message=msg_html,
                )

            return Response({"issue":"liked"})

class FlagIssueApiView(APIView):
    '''
        api for Issue like,flag and bookmark
    '''

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request,id,format=None,*args, **kwargs):
        return Response({
            "flags":UserProfile.objects.filter(issue_flaged__id=id).count(),
        })
    
    def post(self,request,id,format=None,*args,**kwargs):

        
        issue = Issue.objects.get(id=id)
        userprof = UserProfile.objects.get(user=request.user)
        if userprof in UserProfile.objects.filter(issue_flaged=issue):
            userprof.issue_flaged.remove(issue)
            userprof.save()
            return Response({"issue":"unflagged"})
        else:
            userprof.issue_flaged.add(issue)
            userprof.save()
            return Response({"issue":"flagged"})



class UserScoreApiView(APIView):

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request,id,format=None,*args, **kwargs):
        total_score = Points.objects.filter(user__id=id).annotate(total_score=Sum('score'))

        return Response({"total_score":total_score})


class LeaderboardApiViewSet(APIView):


    def get_queryset(self):
        return User.objects.all()
    
    def filter(self,request,*args,**kwargs):

        paginator = PageNumberPagination()
        global_leaderboard = LeaderboardBase()

        month = self.request.query_params.get("month")
        year = self.request.query_params.get("year")

        if not year:
            return Response("Year not passed",status=400)
        
        elif isinstance(year,str) and not year.isdigit():
            return Response("Invalid year passed",status=400)

        if month:

            if not month.isdigit():
                return Response("Invalid month passed",status=400)

            try:
                date = datetime(int(year),int(month),1)
            except:
                return Response(f"Invalid month or year passed",status=400) 
        
        queryset = global_leaderboard.get_leaderboard(month,year,api=True)
        
        page = paginator.paginate_queryset(queryset,request)
        return paginator.get_paginated_response(page)


    
    def group_by_month(self,request,*args,**kwargs):
        

        global_leaderboard = LeaderboardBase()

        year = self.request.query_params.get("year")

        if not year: year = datetime.now().year

        if isinstance(year,str) and not year.isdigit():
            return Response(f"Invalid query passed | Year:{year}",status=400)
        
        year = int(year)

        leaderboard = global_leaderboard.monthly_year_leaderboard(year,api=True)
        month_winners = []

        months = ["January","February","March","April","May","June","July","August","September","October","Novermber","December"]

        for month_indx,usr in enumerate(leaderboard):
            
            
            month_winner = {"user":usr,"month":months[month_indx]}
            month_winners.append(month_winner)
            
        return Response(month_winners)



    def global_leaderboard(self,request,*args,**kwargs):
        
        paginator = PageNumberPagination()
        global_leaderboard = LeaderboardBase()

        queryset = global_leaderboard.get_leaderboard(api=True)
        page = paginator.paginate_queryset(queryset,request)

        return paginator.get_paginated_response(page)

    def get(self,request,format=None,*args,**kwargs):
        
        filter = request.query_params.get("filter")
        group_by_month = request.query_params.get("group_by_month")

        if filter:
            return self.filter(request,*args,**kwargs)
        
        elif group_by_month:
            return self.group_by_month(request,*args,**kwargs)
        
        else:
            return self.global_leaderboard(request,*args,**kwargs)


class StatsApiViewset(APIView):

    def get(self,request,*args,**kwargs):

        bug_count =  Issue.objects.all().count()
        user_count = User.objects.all().count()
        hunt_count = Hunt.objects.all().count()
        domain_count = Domain.objects.all().count()


        return Response({
            "bugs":bug_count,
            "users":user_count,
            "hunts":hunt_count,
            "domains":domain_count
        }) 

class UrlCheckApiViewset(APIView):
    def post(self, request, *args, **kwargs):
        domain_url = request.data["dom_url"]
        if "http://" not in domain_url:
            if "https://" not in domain_url:
                domain_url = "http://" + domain_url

        if Issue.objects.filter(url=domain_url).exists():
            isu = Issue.objects.filter(url=domain_url)
            try:
                a = isu[0]
            except:
                a = None
            data = {
                "number": 1,
                "id": a.id,
                "description": a.description,
                "date": a.created.day,
                "month": a.created.month,
                "year": a.created.year,
            }
            data = IssueSerializer(a).data
            
            return Response({"found": True, "issue": data})

        else:
            return Response({"found": False})
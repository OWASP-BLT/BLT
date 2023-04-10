from datetime import datetime
import uuid

from django.core.mail import send_mail
from django.core.files.storage import default_storage
from django.forms import ValidationError
from django.template.loader import render_to_string
from django.db.models import Sum
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.conf import settings

from website.models import (
    Issue,
    Domain,
    IssueScreenshot,
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
    
    def create(self, request, *args, **kwargs):
        if len(self.request.FILES.getlist("screenshots")) > 5:
            return Response({"error": "Max limit of 5 images!"}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(self.request.FILES.getlist("screenshots")) == 0:
            return Response({"error": "Upload atleast one image!"}, status=status.HTTP_400_BAD_REQUEST)
        
        response = super().create(request, *args, **kwargs)
        data = response.data
        issue = Issue.objects.filter(id=data["id"]).first()


        for screenshot in self.request.FILES.getlist("screenshots"):
            filename = screenshot.name
            extension = filename.split(".")[-1] 
            screenshot.name = filename[:99] + str(uuid.uuid4()) + "." + extension            
            default_storage.save(f"screenshots/{screenshot.name}",screenshot)
            IssueScreenshot.objects.create(image=f"screenshots/{screenshot.name}",issue=issue)

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
        users= list()
        rank_user =1 
        for each in queryset :
            temp = dict()
            temp["rank"]=rank_user
            temp["id"]=each["id"]
            temp["User"]=each["username"]
            temp["score"] = Points.objects.filter(user=each["id"]).aggregate(
                total_score=Sum("score")
            )
            temp["image"] = list(
                UserProfile.objects.filter(user=each["id"]).values("user_avatar")
            )[0]
            temp["title_type"] = list(
                UserProfile.objects.filter(user=each["id"]).values("title")
            )[0]
            temp["follows"] = list(
                UserProfile.objects.filter(user=each["id"]).values("follows")
            )[0]
            temp["savedissue"] = list(
                UserProfile.objects.filter(user=each["id"]).values("issue_saved")
            )[0]
            rank_user = rank_user+1
            users.append(temp)

        page = paginator.paginate_queryset(users,request)
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

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        
        domain_url = request.data.get("domain_url",None)

        if domain_url == None or domain_url.strip() == "": 
            return Response([])

        domain = domain_url.replace("https://","").replace("http://","").replace("www.","")

        issues = Issue.objects.filter(
            Q(
                Q(domain__name=domain) |
                Q(domain__url__icontains=domain)
            ) &
            Q(is_hidden=False)
        ).values("id","description","created__day","created__month","created__year","domain__url","user__userprofile__user_avatar").all()

        return Response(issues[:10])

class BugHuntApiViewset(APIView):

    def get_active_hunts(self,request,*args,**kwargs):

        hunts = Hunt.objects.values('id','name','url','prize','logo',"starts_on","end_on").filter(is_published=True,starts_on__lte=datetime.now(),end_on__gte=datetime.now()).order_by("-prize")
        return Response(hunts)

    def get_previous_hunts(self,request,*args,**kwargs):
        hunts = Hunt.objects.values('id','name','url','prize','logo',"starts_on","end_on").filter(is_published=True,end_on__lte=datetime.now()).order_by("-end_on")
        return Response(hunts)
    
    def get_upcoming_hunts(self,request,*args,**kwargs):
        hunts = Hunt.objects.values('id','name','url','prize','logo',"starts_on","end_on").filter(is_published=True,starts_on__gte=datetime.now()).order_by("starts_on")
        return Response(hunts)

    def get(self,request,*args,**kwargs):
        activeHunt = request.query_params.get("activeHunt")
        previousHunt = request.query_params.get("previousHunt")
        upcomingHunt = request.query_params.get("upcomingHunt")
        if activeHunt:
            return self.get_active_hunts(request,*args,**kwargs)
        elif previousHunt:
            return self.get_previous_hunts(request,*args,**kwargs)
        elif upcomingHunt:
            return self.get_upcoming_hunts(request,*args,**kwargs)
        hunts = Hunt.objects.values('id','name','url','prize','logo',"starts_on","end_on").filter(is_published=True).order_by("-end_on")
        return Response(hunts)
    

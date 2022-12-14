from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db.models import Sum
from django.contrib.auth.models import AnonymousUser

from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

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
    IssueScreenshot
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

    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    filter_backends = (filters.SearchFilter,)
    search_fields = ("id", "user__id", "user__username")
    http_method_names = ["get", "post", "head"]

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

    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        issues = []
        if page is None:
            return Response(issues)
            
        for issue in page:
        
            screenshot = None
            if issue.screenshot: 
                screenshot = issue.screenshot.url
            elif issue.screenshots.first(): 
                screenshot = issue.screenshots.first().image.url

            issues.append({
                **Issue.objects.values().filter(id=issue.id).first(),
                "screenshot":screenshot
            })

        return self.get_paginated_response(issues)


    def retrieve(self, request, pk,*args, **kwargs):
        issue = self.queryset.filter(id=pk).values().first()
        issue_obj = Issue.objects.filter(id=pk).first()
        
        screenshots = [
            # replacing space with url space notation
            screenshot["image"].replace(" ","%20")
            for screenshot in 
            issue_obj.screenshots.values("image").all()
        ] + ( [issue_obj.screenshot.url] if issue_obj.screenshot else [] )

        if issue == None:
            return Response({})

        upvotes = issue_obj.upvoted.all().__len__()
        flags = issue_obj.flaged.all().__len__()
        upvotted = False
        flagged = False

        if type(request.user) != AnonymousUser:

            upvotted = bool(request.user.userprofile.issue_upvoted.filter(id=pk).first())
            flagged = bool(request.user.userprofile.issue_flaged.filter(id=pk).first())
        
            
        return Response({
            **issue,
            "upvotes": upvotes,
            "flags": flags,
            "upvotted": upvotted,
            "flagged": flagged,
            "screenshots": screenshots
        })


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
                "Bugheist <support@bugheist.com>",
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
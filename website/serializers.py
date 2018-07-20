from website.models import Issue, User , UserProfile,Points, Domain
from rest_framework import routers, serializers, viewsets, filters
import django_filters

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id','username')

class IssueSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Issue
        fields = '__all__' 

class IssueViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('url', 'description', 'user__id')

class UserIssueViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('user__username', 'user__id')

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = UserProfile
        fields = '__all__'

class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    filter_backends = (filters.SearchFilter,)
    search_fields = ('id', 'user__id','user__username')

class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = '__all__'

class DomainViewSet(viewsets.ModelViewSet):
    serializer_class = DomainSerializer
    queryset = Domain.objects.all() 
    filter_backends = (filters.SearchFilter,)
    search_fields = ('url', 'name')


router = routers.DefaultRouter()
router.register(r'issues', IssueViewSet, base_name="issues")
router.register(r'userissues', UserIssueViewSet, base_name="userissues")
router.register(r'profile', UserProfileViewSet, base_name="profile")
router.register(r'domain', DomainViewSet, base_name="domain")

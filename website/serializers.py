from website.models import Issue 
from rest_framework import routers, serializers, viewsets, filters

class IssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = "__all__"

class IssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    model = Issue
    queryset = Issue.objects.all()


router = routers.DefaultRouter()
router.register(r'issues', IssueViewSet, base_name="issues")
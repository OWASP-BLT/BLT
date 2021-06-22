from website.models import Issue, User, UserProfile, Domain
from rest_framework import  serializers


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user model
    """

    class Meta:
        model = User
        fields = ('id', 'username')


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user model
    """
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = '__all__'


class IssueSerializer(serializers.ModelSerializer):
    """
    Serializer for Issue Model
    """
    user = UserSerializer(read_only=True)

    class Meta:
        model = Issue
        fields = '__all__'


class DomainSerializer(serializers.ModelSerializer):
    """
    Serializer for Domain Model
    """

    class Meta:
        model = Domain
        fields = '__all__'


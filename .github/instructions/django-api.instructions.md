---
applyTo: "website/api/**/*.py"
---

# Django REST Framework API Requirements for OWASP BLT

When creating or editing API views and serializers for OWASP BLT, follow these guidelines:

## API View Structure

1. **Use ViewSets** - Prefer ViewSets for CRUD operations
   ```python
   from rest_framework import viewsets
   
   class IssueViewSet(viewsets.ModelViewSet):
       queryset = Issue.objects.all()
       serializer_class = IssueSerializer
       permission_classes = [IsAuthenticated]
   ```

2. **Use APIView for Custom Logic** - When ViewSets are too restrictive
   ```python
   from rest_framework.views import APIView
   
   class CustomAPIView(APIView):
       permission_classes = [IsAuthenticated]
       
       def get(self, request):
           # Custom logic
           return Response(data)
   ```

## Serializer Guidelines

1. **Use ModelSerializer** - For model-based APIs
   ```python
   from rest_framework import serializers
   
   class IssueSerializer(serializers.ModelSerializer):
       class Meta:
           model = Issue
           fields = ['id', 'title', 'description', 'created_at']
           read_only_fields = ['id', 'created_at']
   ```

2. **Validation** - Add custom validation methods
   ```python
   def validate_title(self, value):
       if len(value) < 3:
           raise serializers.ValidationError("Title must be at least 3 characters")
       return value
   
   def validate(self, data):
       # Cross-field validation
       return data
   ```

3. **Nested Serializers** - For related objects
   ```python
   class IssueSerializer(serializers.ModelSerializer):
       user = UserSerializer(read_only=True)
       domain = DomainSerializer(read_only=True)
   ```

## Authentication and Permissions

1. **Use DRF Authentication Classes**
   ```python
   from rest_framework.permissions import IsAuthenticated
   from rest_framework.authentication import TokenAuthentication
   
   class IssueViewSet(viewsets.ModelViewSet):
       authentication_classes = [TokenAuthentication]
       permission_classes = [IsAuthenticated]
   ```

2. **Custom Permissions** - Create when needed
   ```python
   from rest_framework import permissions
   
   class IsOwnerOrReadOnly(permissions.BasePermission):
       def has_object_permission(self, request, view, obj):
           if request.method in permissions.SAFE_METHODS:
               return True
           return obj.user == request.user
   ```

## Response Format

1. **Standard Response Structure**
   ```python
   from rest_framework.response import Response
   from rest_framework import status
   
   # Success
   return Response({
       'status': 'success',
       'data': data
   }, status=status.HTTP_200_OK)
   
   # Error
   return Response({
       'status': 'error',
       'message': 'Error description'
   }, status=status.HTTP_400_BAD_REQUEST)
   ```

2. **Pagination** - Use DRF pagination
   ```python
   from rest_framework.pagination import PageNumberPagination
   
   class CustomPagination(PageNumberPagination):
       page_size = 20
       page_size_query_param = 'page_size'
       max_page_size = 100
   
   class IssueViewSet(viewsets.ModelViewSet):
       pagination_class = CustomPagination
   ```

## Filtering and Searching

1. **Use django-filter** - For query filtering
   ```python
   from django_filters import rest_framework as filters
   
   class IssueFilter(filters.FilterSet):
       class Meta:
           model = Issue
           fields = ['status', 'domain', 'user']
   
   class IssueViewSet(viewsets.ModelViewSet):
       filter_backends = [filters.DjangoFilterBackend]
       filterset_class = IssueFilter
   ```

2. **Search** - Use SearchFilter
   ```python
   from rest_framework.filters import SearchFilter
   
   class IssueViewSet(viewsets.ModelViewSet):
       filter_backends = [SearchFilter]
       search_fields = ['title', 'description']
   ```

## Error Handling

1. **Use DRF Exception Handlers**
   ```python
   from rest_framework.exceptions import ValidationError, NotFound
   
   if not issue:
       raise NotFound(detail="Issue not found")
   
   if not valid:
       raise ValidationError(detail="Invalid data")
   ```

2. **Custom Error Messages** - Use user-friendly messages
   - ❌ BAD: `raise Exception(str(e))`
   - ✅ GOOD: `raise ValidationError("Invalid issue format. Please check your input.")`

## API Documentation

1. **Use drf-yasg** - Document APIs with Swagger
   ```python
   from drf_yasg.utils import swagger_auto_schema
   from drf_yasg import openapi
   
   @swagger_auto_schema(
       operation_description="List all issues",
       responses={
           200: IssueSerializer(many=True),
           401: "Unauthorized"
       }
   )
   def list(self, request):
       # Implementation
   ```

2. **Add Docstrings** - Document view classes and methods
   ```python
   class IssueViewSet(viewsets.ModelViewSet):
       """
       API endpoint for managing issues.
       
       list: Return a list of all issues
       create: Create a new issue
       retrieve: Return a specific issue
       update: Update an issue
       destroy: Delete an issue
       """
   ```

## Testing API Endpoints

1. **Use APIClient** - For API tests
   ```python
   from rest_framework.test import APIClient, APITestCase
   
   class IssueAPITest(APITestCase):
       def setUp(self):
           self.client = APIClient()
           self.user = User.objects.create_user(username='test', password='test')
           self.client.force_authenticate(user=self.user)
       
       def test_list_issues(self):
           response = self.client.get('/api/issues/')
           self.assertEqual(response.status_code, 200)
   ```

## Throttling

1. **Rate Limiting** - Protect APIs from abuse
   ```python
   from rest_framework.throttling import UserRateThrottle
   
   class BurstRateThrottle(UserRateThrottle):
       rate = '60/min'
   
   class IssueViewSet(viewsets.ModelViewSet):
       throttle_classes = [BurstRateThrottle]
   ```

## Query Optimization

1. **Use select_related and prefetch_related**
   ```python
   class IssueViewSet(viewsets.ModelViewSet):
       def get_queryset(self):
           return Issue.objects.select_related('user', 'domain').prefetch_related('comments')
   ```

2. **Avoid N+1 Queries** - Use proper query optimization

## Security Best Practices

1. **Validate Input** - Never trust user input
2. **Use Permissions** - Protect endpoints appropriately
3. **Rate Limiting** - Implement throttling
4. **HTTPS Only** - Ensure secure communication (production)
5. **Token Authentication** - Use secure token storage

## Common Patterns

### Create with User
```python
def perform_create(self, serializer):
    serializer.save(user=self.request.user)
```

### Custom Action
```python
from rest_framework.decorators import action

@action(detail=True, methods=['post'])
def approve(self, request, pk=None):
    issue = self.get_object()
    issue.status = 'approved'
    issue.save()
    return Response({'status': 'approved'})
```

### Bulk Operations
```python
@action(detail=False, methods=['post'])
def bulk_create(self, request):
    serializer = self.get_serializer(data=request.data, many=True)
    serializer.is_valid(raise_exception=True)
    self.perform_create(serializer)
    return Response(serializer.data, status=status.HTTP_201_CREATED)
```

## Best Practices Summary

✅ **DO**:
- Use ModelSerializer for model-based APIs
- Add proper authentication and permissions
- Use pagination for list endpoints
- Implement filtering and search
- Document APIs with drf-yasg
- Optimize queries with select_related/prefetch_related
- Use proper HTTP status codes
- Validate all user input
- Write API tests
- Use throttling for rate limiting

❌ **DON'T**:
- Expose sensitive data in responses
- Return exception details to users
- Skip authentication/permission checks
- Create N+1 query problems
- Hardcode values
- Forget to test API endpoints
- Skip input validation
- Use generic error messages
- Commit untested code

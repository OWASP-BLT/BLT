import json
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView
from django.utils import timezone
from datetime import timedelta

from website.models import Tag, Issue, Organization, Domain, UserProfile, Repo, Course, Lecture


@method_decorator(staff_member_required, name='dispatch')
class TagManagementDashboard(ListView):
    """Admin dashboard for tag management"""
    model = Tag
    template_name = 'tag_management/dashboard.html'
    context_object_name = 'tags'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Tag.objects.annotate(
            total_usage=models.Count('organization', distinct=True) +
                       models.Count('issue', distinct=True) +
                       models.Count('courses', distinct=True) +
                       models.Count('lectures', distinct=True) +
                       models.Count('communities', distinct=True) +
                       models.Count('channels', distinct=True) +
                       models.Count('articles', distinct=True)
        )
        
        # Filter by category if provided
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
            
        # Filter by active status
        is_active = self.request.GET.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == 'true')
            
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
            
        # Ordering
        order_by = self.request.GET.get('order_by', 'name')
        if order_by in ['name', '-name', 'category', '-category', 'total_usage', '-total_usage', 'created', '-created']:
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by('name')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add category choices for filtering
        context['category_choices'] = Tag.CATEGORY_CHOICES
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_is_active'] = self.request.GET.get('is_active', '')
        context['search_query'] = self.request.GET.get('search', '')
        context['order_by'] = self.request.GET.get('order_by', 'name')
        
        # Tag statistics
        context['total_tags'] = Tag.objects.count()
        context['active_tags'] = Tag.objects.filter(is_active=True).count()
        context['inactive_tags'] = Tag.objects.filter(is_active=False).count()
        
        # Most used tags
        context['most_used_tags'] = Tag.objects.annotate(
            usage_count=models.Count('organization', distinct=True) +
                       models.Count('issue', distinct=True) +
                       models.Count('courses', distinct=True)
        ).filter(usage_count__gt=0).order_by('-usage_count')[:10]
        
        # Recently created tags
        context['recent_tags'] = Tag.objects.filter(
            created__gte=timezone.now() - timedelta(days=30)
        ).order_by('-created')[:10]
        
        # Category distribution
        context['category_stats'] = Tag.objects.values('category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return context


@staff_member_required
@require_http_methods(["POST"])
def bulk_tag_actions(request):
    """Handle bulk actions on tags"""
    action = request.POST.get('action')
    tag_ids = request.POST.getlist('tag_ids')
    
    if not action or not tag_ids:
        messages.error(request, "Please select tags and an action.")
        return redirect('tag_management_dashboard')
    
    tags = Tag.objects.filter(id__in=tag_ids)
    
    if action == 'activate':
        tags.update(is_active=True)
        messages.success(request, f"Activated {tags.count()} tags.")
    elif action == 'deactivate':
        tags.update(is_active=False)
        messages.success(request, f"Deactivated {tags.count()} tags.")
    elif action == 'delete':
        # Check if tags are being used
        tags_in_use = []
        for tag in tags:
            if tag.usage_count > 0:
                tags_in_use.append(tag.name)
        
        if tags_in_use:
            messages.error(request, f"Cannot delete tags that are in use: {', '.join(tags_in_use)}")
        else:
            count = tags.count()
            tags.delete()
            messages.success(request, f"Deleted {count} tags.")
    
    return redirect('tag_management_dashboard')


@staff_member_required
def tag_analytics(request):
    """Display tag usage analytics"""
    
    # Get tag usage across different models
    tag_usage_data = []
    for tag in Tag.objects.all():
        usage_data = {
            'tag': tag,
            'organizations': tag.organization_set.count(),
            'issues': tag.issue_set.count(),
            'domains': tag.domain_set.count(),
            'users': tag.userprofile_set.count(),
            'repos': tag.repo_set.count(),
            'courses': tag.courses.count(),
            'lectures': tag.lectures.count(),
            'communities': tag.communities.count(),
            'channels': tag.channels.count(),
            'articles': tag.articles.count(),
        }
        usage_data['total'] = sum([v for k, v in usage_data.items() if k != 'tag'])
        tag_usage_data.append(usage_data)
    
    # Sort by total usage
    tag_usage_data.sort(key=lambda x: x['total'], reverse=True)
    
    # Get trending tags (tags used in recent issues/organizations)
    recent_date = timezone.now() - timedelta(days=30)
    trending_tags = Tag.objects.filter(
        Q(issue__created__gte=recent_date) | 
        Q(organization__created__gte=recent_date)
    ).annotate(
        recent_usage=Count('issue', filter=Q(issue__created__gte=recent_date)) +
                    Count('organization', filter=Q(organization__created__gte=recent_date))
    ).filter(recent_usage__gt=0).order_by('-recent_usage')[:20]
    
    context = {
        'tag_usage_data': tag_usage_data[:50],  # Top 50 tags by usage
        'trending_tags': trending_tags,
        'total_tags': Tag.objects.count(),
        'unused_tags': Tag.objects.filter(
            organization__isnull=True,
            issue__isnull=True,
            courses__isnull=True,
            lectures__isnull=True,
            communities__isnull=True,
            channels__isnull=True,
            articles__isnull=True
        ).count(),
    }
    
    return render(request, 'tag_management/analytics.html', context)


@login_required
def tag_autocomplete(request):
    """API endpoint for tag autocomplete"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    tags = Tag.objects.filter(
        name__icontains=query,
        is_active=True
    ).order_by('name')[:20]
    
    results = [
        {
            'id': tag.id,
            'name': tag.name,
            'slug': tag.slug,
            'category': tag.category,
            'color': tag.color,
            'icon': tag.icon,
        }
        for tag in tags
    ]
    
    return JsonResponse({'results': results})


@login_required
def recommend_tags_api(request):
    """API endpoint for tag recommendations based on issue content"""
    from website.utils import recommend_tags_for_issue
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=405)
    
    try:
        data = json.loads(request.body)
        description = data.get('description', '')
        url = data.get('url', '')
        max_tags = min(int(data.get('max_tags', 5)), 10)  # Limit to 10
        
        if not description:
            return JsonResponse({'error': 'Description is required'}, status=400)
        
        # Get recommendations
        recommended_tag_names = recommend_tags_for_issue(description, url, max_tags)
        
        # Get tag objects for the recommendations
        recommendations = []
        for tag_name in recommended_tag_names:
            # Try to find existing tag
            tag = Tag.objects.filter(name__iexact=tag_name, is_active=True).first()
            if tag:
                recommendations.append({
                    'id': tag.id,
                    'name': tag.name,
                    'slug': tag.slug,
                    'category': tag.category,
                    'color': tag.color,
                    'icon': tag.icon,
                    'exists': True,
                })
            else:
                # Suggest new tag
                normalized_name = Tag.normalize_name(tag_name)
                recommendations.append({
                    'id': None,
                    'name': normalized_name,
                    'slug': None,
                    'category': 'general',
                    'color': '#e74c3c',
                    'icon': '',
                    'exists': False,
                })
        
        return JsonResponse({
            'recommendations': recommendations,
            'count': len(recommendations)
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required  
def tag_search(request):
    """Search functionality for tags across different models"""
    template_name = 'tag_management/search.html'
    
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    model_type = request.GET.get('type', 'all')  # all, issues, organizations, etc.
    
    context = {
        'query': query,
        'category': category,
        'model_type': model_type,
    }
    
    if query:
        # Search tags
        tags = Tag.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True
        )
        
        if category:
            tags = tags.filter(category=category)
        
        tags = tags.order_by('name')[:50]
        
        # Get entities tagged with these tags
        search_results = {}
        
        for tag in tags:
            tag_results = {
                'tag': tag,
                'issues': [],
                'organizations': [],
                'repos': [],
                'courses': [],
                'total_count': 0,
            }
            
            if model_type in ['all', 'issues']:
                issues = tag.issue_set.filter(
                    ~Q(is_hidden=True) | Q(user=request.user)
                ).order_by('-created')[:10]
                tag_results['issues'] = issues
                
            if model_type in ['all', 'organizations']:
                organizations = tag.organization_set.all()[:10]
                tag_results['organizations'] = organizations
                
            if model_type in ['all', 'repos']:
                repos = tag.repo_set.all()[:10]
                tag_results['repos'] = repos
                
            if model_type in ['all', 'courses']:
                courses = tag.courses.all()[:10]
                tag_results['courses'] = courses
            
            # Calculate total count
            tag_results['total_count'] = (
                len(tag_results['issues']) +
                len(tag_results['organizations']) +
                len(tag_results['repos']) +
                len(tag_results['courses'])
            )
            
            if tag_results['total_count'] > 0:
                search_results[tag.id] = tag_results
        
        context['search_results'] = search_results
        context['tags_found'] = len(search_results)
    
    context['category_choices'] = Tag.CATEGORY_CHOICES
    context['model_type_choices'] = [
        ('all', 'All Types'),
        ('issues', 'Issues'),
        ('organizations', 'Organizations'), 
        ('repos', 'Repositories'),
        ('courses', 'Courses'),
    ]
    
    return render(request, template_name, context)


def get_popular_tags_context(request, limit=20, category=None):
    """
    Get popular tags for use in templates
    
    Args:
        request: Django request object
        limit: Maximum number of tags to return
        category: Optional category filter
        
    Returns:
        dict: Context with popular tags
    """
    from website.models import Tag
    
    # Get popular tags with usage counts 
    tags = Tag.objects.filter(is_active=True).annotate(
        total_usage=models.Count('organization', distinct=True) +
                   models.Count('issue', distinct=True) +
                   models.Count('courses', distinct=True) +
                   models.Count('lectures', distinct=True) +
                   models.Count('communities', distinct=True)
    ).filter(total_usage__gt=0)
    
    if category:
        tags = tags.filter(category=category)
    
    tags = tags.order_by('-total_usage')[:limit]
    
    # Add usage_count attribute for template use
    for tag in tags:
        tag.usage_count = tag.total_usage
    
    return {
        'popular_tags': tags,
        'popular_tags_count': tags.count(),
    }


@staff_member_required
def merge_tags(request):
    """Merge multiple tags into one"""
    if request.method == 'POST':
        primary_tag_id = request.POST.get('primary_tag')
        merge_tag_ids = request.POST.getlist('merge_tags')
        
        if not primary_tag_id or not merge_tag_ids:
            messages.error(request, "Please select a primary tag and tags to merge.")
            return redirect('tag_management_dashboard')
        
        primary_tag = get_object_or_404(Tag, id=primary_tag_id)
        merge_tags = Tag.objects.filter(id__in=merge_tag_ids).exclude(id=primary_tag_id)
        
        # Move all relationships to the primary tag
        for tag in merge_tags:
            # Move organizations
            for org in tag.organization_set.all():
                org.tags.remove(tag)
                org.tags.add(primary_tag)
            
            # Move issues
            for issue in tag.issue_set.all():
                issue.tags.remove(tag)
                issue.tags.add(primary_tag)
            
            # Move other relationships similarly...
            # (This would need to be expanded for all related models)
        
        # Delete the merged tags
        merged_count = merge_tags.count()
        merge_tags.delete()
        
        messages.success(request, f"Merged {merged_count} tags into '{primary_tag.name}'.")
        return redirect('tag_management_dashboard')
    
    # GET request - show merge form
    tags = Tag.objects.all().order_by('name')
    return render(request, 'tag_management/merge.html', {'tags': tags})
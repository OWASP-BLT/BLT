from website.models import Project, Repo
from django.db.models import Sum

print(f'Projects: {Project.objects.count()}')
print(f'Repos: {Repo.objects.count()}')
print('\nSample projects:')
for p in Project.objects.all()[:5]:
    stars = p.repos.aggregate(Sum('stars'))['stars__sum'] or 0
    print(f'  {p.name}: {p.repos.count()} repos, {stars} stars')

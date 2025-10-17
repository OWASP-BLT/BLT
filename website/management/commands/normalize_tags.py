from django.core.management.base import BaseCommand
from django.db import transaction
from website.models import Tag


class Command(BaseCommand):
    help = 'Normalize existing tags to prevent duplicates and merge similar tags'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--auto-merge',
            action='store_true',
            help='Automatically merge duplicate tags',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.auto_merge = options['auto_merge']
        
        self.stdout.write(
            self.style.SUCCESS('Starting tag normalization process...')
        )
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        self.normalize_tags()
        self.find_duplicates()
        
        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS('Tag normalization completed successfully!')
            )

    def normalize_tags(self):
        """Normalize all existing tags"""
        self.stdout.write('Normalizing tag names...')
        
        tags = Tag.objects.all()
        updated_count = 0
        
        for tag in tags:
            original_name = tag.name
            normalized_name = Tag.normalize_name(original_name)
            
            if original_name != normalized_name:
                self.stdout.write(
                    f'  Would normalize: "{original_name}" -> "{normalized_name}"'
                )
                
                if not self.dry_run:
                    tag.name = normalized_name
                    tag.save()
                
                updated_count += 1
        
        if updated_count:
            self.stdout.write(
                self.style.SUCCESS(f'Normalized {updated_count} tag names')
            )
        else:
            self.stdout.write('No tags needed normalization')

    def find_duplicates(self):
        """Find and optionally merge duplicate tags"""
        self.stdout.write('Finding duplicate tags...')
        
        # Group tags by normalized name
        tag_groups = {}
        for tag in Tag.objects.all():
            normalized = tag.name.lower()
            if normalized not in tag_groups:
                tag_groups[normalized] = []
            tag_groups[normalized].append(tag)
        
        duplicates_found = 0
        merged_count = 0
        
        for normalized_name, tags in tag_groups.items():
            if len(tags) > 1:
                duplicates_found += 1
                self.stdout.write(
                    f'  Found duplicates for "{normalized_name}": '
                    f'{[tag.name for tag in tags]}'
                )
                
                if self.auto_merge and not self.dry_run:
                    merged_count += self.merge_duplicate_tags(tags)
        
        if duplicates_found:
            self.stdout.write(
                self.style.WARNING(
                    f'Found {duplicates_found} groups of duplicate tags'
                )
            )
            
            if merged_count:
                self.stdout.write(
                    self.style.SUCCESS(f'Merged {merged_count} duplicate tags')
                )
            elif not self.auto_merge:
                self.stdout.write(
                    'Use --auto-merge to automatically merge duplicates'
                )
        else:
            self.stdout.write('No duplicate tags found')

    @transaction.atomic
    def merge_duplicate_tags(self, tags):
        """Merge duplicate tags into the most used one"""
        if len(tags) <= 1:
            return 0
        
        # Find the tag with the most usage
        primary_tag = max(tags, key=lambda t: t.usage_count)
        duplicate_tags = [t for t in tags if t.id != primary_tag.id]
        
        self.stdout.write(
            f'    Merging into "{primary_tag.name}" (ID: {primary_tag.id})'
        )
        
        # Move all relationships to the primary tag
        for dup_tag in duplicate_tags:
            self.stdout.write(f'      Moving relationships from "{dup_tag.name}"')
            
            # Move organization relationships
            for org in dup_tag.organization_set.all():
                org.tags.remove(dup_tag)
                org.tags.add(primary_tag)
            
            # Move issue relationships
            for issue in dup_tag.issue_set.all():
                issue.tags.remove(dup_tag)
                issue.tags.add(primary_tag)
            
            # Move domain relationships
            for domain in dup_tag.domain_set.all():
                domain.tags.remove(dup_tag)
                domain.tags.add(primary_tag)
            
            # Move user profile relationships
            for profile in dup_tag.userprofile_set.all():
                profile.tags.remove(dup_tag)
                profile.tags.add(primary_tag)
            
            # Move repo relationships
            for repo in dup_tag.repo_set.all():
                repo.tags.remove(dup_tag)
                repo.tags.add(primary_tag)
            
            # Move course relationships
            for course in dup_tag.courses.all():
                course.tags.remove(dup_tag)
                course.tags.add(primary_tag)
            
            # Move lecture relationships
            for lecture in dup_tag.lectures.all():
                lecture.tags.remove(dup_tag)
                lecture.tags.add(primary_tag)
            
            # Move community relationships
            for community in dup_tag.communities.all():
                community.tags.remove(dup_tag)
                community.tags.add(primary_tag)
            
            # Move channel relationships
            for channel in dup_tag.channels.all():
                channel.tags.remove(dup_tag)
                channel.tags.add(primary_tag)
            
            # Move article relationships
            for article in dup_tag.articles.all():
                article.tags.remove(dup_tag)
                article.tags.add(primary_tag)
            
            # Delete the duplicate tag
            dup_tag.delete()
            self.stdout.write(f'      Deleted duplicate tag "{dup_tag.name}"')
        
        return len(duplicate_tags)
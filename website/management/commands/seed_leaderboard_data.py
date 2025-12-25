"""
Seed OWASP project data using raw SQL to bypass model field validation issues
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Seeds OWASP project data using raw SQL'

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            self.stdout.write('Creating sample projects...')
            
            # Sample OWASP projects
            projects = [
                ('OWASP BLT', 'blt', 'Bug Logging Tool - Crowdsourced security platform', 'flagship', 0),
                ('OWASP ZAP', 'zap', 'The world\'s most widely used web app scanner', 'flagship', 0),
                ('OWASP Juice Shop', 'juice-shop', 'Probably the most modern and sophisticated insecure web application', 'flagship', 0),
                ('OWASP ModSecurity', 'modsecurity', 'Open source web application firewall', 'flagship', 0),
                ('OWASP Dependency-Check', 'dependency-check', 'Software Composition Analysis tool', 'production', 0),
                ('OWASP Top 10', 'top-10', 'Standard awareness document for developers and web application security', 'flagship', 0),
                ('OWASP ASVS', 'asvs', 'Application Security Verification Standard', 'flagship', 0),
                ('OWASP Security Shepherd', 'security-shepherd', 'Web and mobile application security training platform', 'production', 0),
                ('OWASP Amass', 'amass', 'In-depth attack surface mapping and asset discovery', 'production', 0),
                ('OWASP Cheat Sheet Series', 'cheat-sheet-series', 'Concise collection of high value information', 'production', 0),
                ('OWASP WebGoat', 'webgoat', 'Deliberately insecure application for teaching web security', 'production', 0),
            ]
            
            # Insert projects
            for name, slug, desc, status, slack_count in projects:
                cursor.execute(
                    """
                    INSERT INTO website_project 
                    (name, slug, description, status, project_visit_count, slack_user_count, created, modified)
                    VALUES (%s, %s, %s, %s, 0, %s, NOW(), NOW())
                    ON CONFLICT (slug) DO NOTHING
                    RETURNING id
                    """,
                    [name, slug, desc, status, slack_count]
                )
                result = cursor.fetchone()
                if result:
                    project_id = result[0]
                    self.stdout.write(f'  Created project: {name} (ID: {project_id})')
            
            # Sample repos with GitHub stats - Actual data from GitHub (Dec 2024)
            repos_data = [
                ('blt', 'BLT', 'https://github.com/OWASP-BLT/BLT', 251, 316, 59, 6255, 117, 5, 107, 5200),
                ('zap', 'zaproxy', 'https://github.com/zaproxy/zaproxy', 14600, 2500, 825, 10154, 227, 396, 32, 9000),
                ('juice-shop', 'juice-shop', 'https://github.com/juice-shop/juice-shop', 12200, 15900, 9, 21432, 138, 173, 2, 10000),
                ('modsecurity', 'ModSecurity', 'https://github.com/owasp-modsecurity/ModSecurity', 9400, 1700, 242, 3712, 98, 380, 30, 3200),
                ('dependency-check', 'DependencyCheck', 'https://github.com/jeremylong/DependencyCheck', 40, 21, 1, 10416, 291, 1, 0, 7200),
                ('top-10', 'Top10', 'https://github.com/OWASP/Top10', 5000, 975, 3, 3019, 175, 288, 10, 2800),
                ('asvs', 'ASVS', 'https://github.com/OWASP/ASVS', 3300, 784, 79, 3259, 116, 145, 6, 2900),
                ('security-shepherd', 'SecurityShepherd', 'https://github.com/OWASP/SecurityShepherd', 1400, 494, 118, 932, 47, 84, 15, 700),
                ('amass', 'Amass', 'https://github.com/owasp-amass/amass', 13900, 2100, 183, 2559, 73, 225, 24, 2200),
                ('cheat-sheet-series', 'CheatSheetSeries', 'https://github.com/OWASP/CheatSheetSeries', 31000, 4300, 47, 2051, 583, 566, 10, 1900),
                ('webgoat', 'WebGoat', 'https://github.com/WebGoat/WebGoat', 8800, 7100, 34, 3158, 112, 211, 17, 3000),
            ]
            
            self.stdout.write('Creating repos with GitHub stats...')
            for project_slug, repo_name, repo_url, stars, forks, issues, commits, contributors, watchers, open_prs, closed_prs in repos_data:
                # Generate a slug for the repo based on project slug
                repo_slug = f"{project_slug}-repo"
                cursor.execute(
                    """
                    INSERT INTO website_repo 
                    (name, slug, repo_url, is_main, is_wiki, is_archived, is_owasp_repo,
                     stars, forks, open_issues, total_issues, repo_visit_count, watchers, 
                     network_count, subscribers_count, closed_issues, size,
                     commit_count, contributor_count, open_pull_requests, closed_pull_requests,
                     last_pr_page_processed, created, created_at, modified, updated_at, project_id)
                    SELECT %s, %s, %s, TRUE, FALSE, FALSE, TRUE,
                           %s, %s, %s, %s, 0, %s,
                           0, 0, 0, 0,
                           %s, %s, %s, %s,
                           0, NOW(), NOW(), NOW(), NOW(), p.id
                    FROM website_project p
                    WHERE p.slug = %s
                    ON CONFLICT (slug) DO UPDATE SET
                        name = EXCLUDED.name,
                        repo_url = EXCLUDED.repo_url,
                        stars = EXCLUDED.stars,
                        forks = EXCLUDED.forks,
                        open_issues = EXCLUDED.open_issues,
                        total_issues = EXCLUDED.total_issues,
                        commit_count = EXCLUDED.commit_count,
                        contributor_count = EXCLUDED.contributor_count,
                        watchers = EXCLUDED.watchers,
                        open_pull_requests = EXCLUDED.open_pull_requests,
                        closed_pull_requests = EXCLUDED.closed_pull_requests,
                        modified = NOW(),
                        updated_at = NOW()
                    RETURNING id
                    """,
                    [repo_name, repo_slug, repo_url, stars, forks, issues, issues, commits, contributors, 
                     watchers, open_prs, closed_prs, project_slug]
                )
                result = cursor.fetchone()
                if result:
                    self.stdout.write(f'  Created/Updated repo: {repo_name}')
            
            # Get counts
            cursor.execute("SELECT COUNT(*) FROM website_project")
            project_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM website_repo")
            repo_count = cursor.fetchone()[0]
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully seeded data!'))
            self.stdout.write(f'📊 Total projects: {project_count}')
            self.stdout.write(f'📦 Total repos: {repo_count}')

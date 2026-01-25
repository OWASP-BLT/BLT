from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from website.models import Issue, IssueReport, Domain

User = get_user_model()


class IssueReportingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.reporter = User.objects.create_user(username='reporter', password='12345')
        self.admin = User.objects.create_user(username='admin', password='12345', is_staff=True)
        
        # Create a domain for the issue
        self.domain = Domain.objects.create(name='example.com', url='https://example.com')
        
        # Create an issue
        self.issue = Issue.objects.create(
            user=self.user, 
            description='Test issue',
            url='https://example.com/test',
            domain=self.domain
        )

    def test_report_issue_success(self):
        """Test successful issue reporting"""
        self.client.login(username='reporter', password='12345')
        response = self.client.post(f'/report_issue/{self.issue.id}/', {
            'reason': 'spam',
            'description': 'This is spam'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IssueReport.objects.count(), 1)
        
        report = IssueReport.objects.first()
        self.assertEqual(report.reporter, self.reporter)
        self.assertEqual(report.reported_issue, self.issue)
        self.assertEqual(report.reason, 'spam')
        self.assertEqual(report.description, 'This is spam')

    def test_cannot_report_own_issue(self):
        """Test that users cannot report their own issues"""
        self.client.login(username='testuser', password='12345')
        response = self.client.post(f'/report_issue/{self.issue.id}/', {
            'reason': 'spam',
            'description': 'Test'
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IssueReport.objects.count(), 0)

    def test_cannot_report_twice(self):
        """Test that users cannot report the same issue twice"""
        IssueReport.objects.create(
            reporter=self.reporter,
            reported_issue=self.issue,
            reason='spam',
            description='First'
        )
        self.client.login(username='reporter', password='12345')
        response = self.client.post(f'/report_issue/{self.issue.id}/', {
            'reason': 'spam',
            'description': 'Second'
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IssueReport.objects.count(), 1)

    def test_update_report_status_admin_only(self):
        """Test that only admins can update report status"""
        report = IssueReport.objects.create(
            reporter=self.reporter,
            reported_issue=self.issue,
            reason='spam',
            description='Test'
        )
        self.client.login(username='reporter', password='12345')
        response = self.client.post(f'/issue-reports/{report.id}/update/', {
            'status': 'reviewed',
            'admin_notes': 'Checked'
        })
        self.assertEqual(response.status_code, 403)

    def test_update_report_status_admin_success(self):
        """Test successful report status update by admin"""
        report = IssueReport.objects.create(
            reporter=self.reporter,
            reported_issue=self.issue,
            reason='spam',
            description='Test'
        )
        self.client.login(username='admin', password='12345')
        response = self.client.post(f'/issue-reports/{report.id}/update/', {
            'status': 'reviewed',
            'admin_notes': 'Checked'
        })
        self.assertEqual(response.status_code, 200)
        
        report.refresh_from_db()
        self.assertEqual(report.status, 'reviewed')
        self.assertEqual(report.admin_notes, 'Checked')
        self.assertEqual(report.reviewed_by, self.admin)

    def test_xss_sanitization(self):
        """Test that XSS attempts are sanitized"""
        self.client.login(username='reporter', password='12345')
        response = self.client.post(f'/report_issue/{self.issue.id}/', {
            'reason': 'spam',
            'description': '<script>alert("xss")</script>Test description'
        })
        self.assertEqual(response.status_code, 200)
        
        report = IssueReport.objects.first()
        # The script tag should be escaped
        self.assertNotIn('<script>', report.description)
        self.assertIn('&lt;script&gt;', report.description)

    def test_empty_description_validation(self):
        """Test that empty descriptions are rejected"""
        self.client.login(username='reporter', password='12345')
        response = self.client.post(f'/report_issue/{self.issue.id}/', {
            'reason': 'spam',
            'description': '   '  # Only whitespace
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IssueReport.objects.count(), 0)

    def test_invalid_reason_validation(self):
        """Test that invalid reasons are rejected"""
        self.client.login(username='reporter', password='12345')
        response = self.client.post(f'/report_issue/{self.issue.id}/', {
            'reason': 'invalid_reason',
            'description': 'Test description'
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IssueReport.objects.count(), 0)

    def test_admin_notes_xss_sanitization(self):
        """Test that admin notes are also sanitized"""
        report = IssueReport.objects.create(
            reporter=self.reporter,
            reported_issue=self.issue,
            reason='spam',
            description='Test'
        )
        self.client.login(username='admin', password='12345')
        response = self.client.post(f'/issue-reports/{report.id}/update/', {
            'status': 'reviewed',
            'admin_notes': '<script>alert("admin xss")</script>Admin notes'
        })
        self.assertEqual(response.status_code, 200)
        
        report.refresh_from_db()
        # The script tag should be escaped
        self.assertNotIn('<script>', report.admin_notes)
        self.assertIn('&lt;script&gt;', report.admin_notes)

    def test_pagination_in_admin_views(self):
        """Test that pagination works in admin views"""
        # Create multiple reports to test pagination
        for i in range(25):  # More than the 20 per page limit
            user = User.objects.create_user(username=f'reporter{i}', password='12345')
            IssueReport.objects.create(
                reporter=user,
                reported_issue=self.issue,
                reason='spam',
                description=f'Test report {i}'
            )
        
        self.client.login(username='admin', password='12345')
        response = self.client.get('/admin/issue-reports/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Page 1 of')
        
        # Test second page
        response = self.client.get('/admin/issue-reports/?page=2')
        self.assertEqual(response.status_code, 200)

    def test_search_functionality(self):
        """Test search functionality in admin view"""
        IssueReport.objects.create(
            reporter=self.reporter,
            reported_issue=self.issue,
            reason='spam',
            description='Unique search term'
        )
        
        self.client.login(username='admin', password='12345')
        response = self.client.get('/admin/issue-reports/?search=Unique')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Unique search term')

    def test_status_filtering(self):
        """Test status filtering in admin view"""
        IssueReport.objects.create(
            reporter=self.reporter,
            reported_issue=self.issue,
            reason='spam',
            description='Test report',
            status='reviewed'
        )
        
        self.client.login(username='admin', password='12345')
        response = self.client.get('/admin/issue-reports/?status=reviewed')
        self.assertEqual(response.status_code, 200)
        # Should contain the reviewed report
        self.assertContains(response, 'Test report')

    def test_rate_limiting_report_issue(self):
        """Test that rate limiting works for issue reporting"""
        from django.core.cache import cache
        
        # Clear any existing rate limit data
        cache.clear()
        
        self.client.login(username='reporter', password='12345')
        
        # Make 5 successful reports (should be allowed)
        for i in range(5):
            issue = Issue.objects.create(
                user=self.user, 
                description=f'Test issue {i}',
                url=f'https://example.com/test{i}',
                domain=self.domain
            )
            response = self.client.post(f'/report_issue/{issue.id}/', {
                'reason': 'spam',
                'description': f'Report {i}'
            })
            self.assertEqual(response.status_code, 200)
        
        # 6th report should be rate limited
        issue6 = Issue.objects.create(
            user=self.user, 
            description='Test issue 6',
            url='https://example.com/test6',
            domain=self.domain
        )
        response = self.client.post(f'/report_issue/{issue6.id}/', {
            'reason': 'spam',
            'description': 'Report 6'
        })
        self.assertEqual(response.status_code, 429)
        
    def test_rate_limiting_update_status(self):
        """Test that rate limiting works for status updates"""
        from django.core.cache import cache
        
        # Clear any existing rate limit data
        cache.clear()
        
        self.client.login(username='admin', password='12345')
        
        # Create 30 reports for testing
        reports = []
        for i in range(31):
            issue = Issue.objects.create(
                user=self.user, 
                description=f'Test issue {i}',
                url=f'https://example.com/test{i}',
                domain=self.domain
            )
            report = IssueReport.objects.create(
                reporter=self.reporter,
                reported_issue=issue,
                reason='spam',
                description=f'Test report {i}'
            )
            reports.append(report)
        
        # Make 30 successful updates (should be allowed)
        for i in range(30):
            response = self.client.post(f'/issue-reports/{reports[i].id}/update/', {
                'status': 'reviewed',
                'admin_notes': f'Checked {i}'
            })
            self.assertEqual(response.status_code, 200)
        
        # 31st update should be rate limited
        response = self.client.post(f'/issue-reports/{reports[30].id}/update/', {
            'status': 'reviewed',
            'admin_notes': 'Checked 30'
        })
        self.assertEqual(response.status_code, 429)

    def test_integrity_error_handling(self):
        """Test that IntegrityError is properly handled"""
        # Create a report first
        IssueReport.objects.create(
            reporter=self.reporter,
            reported_issue=self.issue,
            reason='spam',
            description='First report'
        )
        
        # Try to create another report from the same user for the same issue
        self.client.login(username='reporter', password='12345')
        response = self.client.post(f'/report_issue/{self.issue.id}/', {
            'reason': 'spam',
            'description': 'Second report'
        })
        self.assertEqual(response.status_code, 400)
        # Should still only have one report
        self.assertEqual(IssueReport.objects.filter(reporter=self.reporter, reported_issue=self.issue).count(), 1)
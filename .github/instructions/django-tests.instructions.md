---
applyTo: "website/tests/**/*.py"
---

# Django Test Requirements for OWASP BLT

When writing Django tests for OWASP BLT, follow these guidelines to ensure consistency, speed, and maintainability:

## Test Structure and Organization

1. **Use TestCase Classes** - Inherit from `django.test.TestCase` for database-related tests
2. **Organize by Functionality** - Group related tests in the same test class
3. **Use setUpTestData()** - Use `setUpTestData()` instead of `setUp()` for test data that doesn't need modification
4. **Clear Test Names** - Use descriptive test method names that explain what is being tested
   - Format: `test_<feature>_<scenario>_<expected_outcome>`
   - Example: `test_issue_creation_with_valid_data_succeeds`

## Performance Optimization

1. **Tag Slow Tests** - Use `@tag("slow")` decorator for tests that take more than 1 second
   ```python
   from django.test import tag
   
   @tag("slow")
   def test_selenium_browser_interaction(self):
       # Slow test code
   ```

2. **Use setUpTestData()** - For test data that doesn't need to be modified
   ```python
   @classmethod
   def setUpTestData(cls):
       cls.user = User.objects.create_user(username='testuser', password='testpass')
       cls.domain = Domain.objects.create(name='example.com')
   ```

3. **Prefer In-Memory Operations** - Avoid unnecessary file I/O or external API calls

## Test Data Management

1. **Use Factories or Fixtures** - Create reusable test data creation methods
2. **Clean Up Test Data** - Ensure tests clean up after themselves (Django's TestCase handles this automatically)
3. **Use Realistic Data** - Create test data that resembles production data

## Assertions and Validation

1. **Use Specific Assertions** - Use the most specific assertion method available
   - ✅ `self.assertEqual(response.status_code, 200)`
   - ❌ `self.assertTrue(response.status_code == 200)`

2. **Test Edge Cases** - Include tests for boundary conditions and error cases
3. **Assert Response Content** - Verify both status codes and response content
   ```python
   self.assertEqual(response.status_code, 200)
   self.assertContains(response, 'Expected text')
   self.assertIn('key', response.json())
   ```

## API Testing Best Practices

1. **Use APIClient** - For testing REST API endpoints
   ```python
   from rest_framework.test import APIClient
   
   def setUp(self):
       self.client = APIClient()
       self.client.force_authenticate(user=self.user)
   ```

2. **Test Authentication** - Verify authentication requirements are enforced
3. **Test Permissions** - Ensure permission checks work correctly
4. **Validate Response Format** - Check JSON structure matches expected schema

## Authentication and Authorization Testing

1. **Test Anonymous Users** - Verify unauthenticated access is handled correctly
2. **Test Different User Roles** - Test with different user permissions
3. **Use force_login()** - For tests requiring authenticated users
   ```python
   self.client.force_login(self.user)
   ```

## Common Test Patterns

### Testing Views
```python
def test_issue_list_view_returns_correct_issues(self):
    # Arrange: Create test data
    issue = Issue.objects.create(...)
    
    # Act: Make request
    response = self.client.get(reverse('issue_list'))
    
    # Assert: Verify response
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, issue.title)
```

### Testing Forms
```python
def test_issue_form_validation_with_invalid_data(self):
    form_data = {'title': ''}  # Missing required field
    form = IssueForm(data=form_data)
    self.assertFalse(form.is_valid())
    self.assertIn('title', form.errors)
```

### Testing Models
```python
def test_issue_model_str_representation(self):
    issue = Issue.objects.create(title='Test Issue')
    self.assertEqual(str(issue), 'Test Issue')
```

### Testing Signals
```python
def test_issue_creation_sends_notification(self):
    with self.assertSignalSent(post_save, sender=Issue):
        Issue.objects.create(title='Test')
```

## Test Coverage

1. **Aim for High Coverage** - Strive for >80% code coverage
2. **Test Critical Paths** - Prioritize testing critical business logic
3. **Include Negative Tests** - Test failure scenarios and error handling

## Running Tests

```bash
# Run all tests
poetry run python manage.py test --parallel --failfast

# Run tests excluding slow ones (Selenium)
poetry run python manage.py test --exclude-tag=slow --parallel --failfast

# Run specific test class
poetry run python manage.py test website.tests.test_api.APITests

# Run specific test method
poetry run python manage.py test website.tests.test_api.APITests.test_specific_method

# Run with coverage
poetry run coverage run --source='.' manage.py test
poetry run coverage report
```

## Common Pitfalls to Avoid

1. ❌ **Don't use `setUp()` for data that doesn't change** - Use `setUpTestData()` instead
2. ❌ **Don't test Django's built-in functionality** - Trust Django's code works
3. ❌ **Don't create unnecessary test data** - Only create what's needed for the test
4. ❌ **Don't use real external services** - Mock external API calls
5. ❌ **Don't forget to test error cases** - Include negative test cases
6. ❌ **Don't hardcode URLs** - Use `reverse()` to resolve URLs by name

## Best Practices Summary

✅ **DO**:
- Use `setUpTestData()` for immutable test data
- Tag slow tests with `@tag("slow")`
- Use descriptive test names
- Test both success and failure scenarios
- Use specific assertion methods
- Mock external services
- Use `reverse()` for URL resolution
- Keep tests focused and simple
- Run tests before committing

❌ **DON'T**:
- Use `setUp()` for data that doesn't change
- Forget to test edge cases
- Test Django's built-in functionality
- Hardcode URLs or values
- Create excessive test data
- Make tests dependent on each other
- Skip testing error handling

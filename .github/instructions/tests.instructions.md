---
applyTo: 
  - "website/tests/**/*.py"
  - "**/test_*.py"
---

# Test-Specific Copilot Instructions

## Django Testing

### Test Structure
- Place all tests in `website/tests/` directory
- Use descriptive test file names: `test_feature_name.py`
- Organize tests by feature or module
- Use descriptive test method names: `test_user_can_submit_issue_with_valid_data`

### Test Classes
```python
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User

class MyFeatureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Set up data for the entire test class (runs once)."""
        # Use this for data that doesn't need to be modified
        cls.user = User.objects.create_user('testuser', 'test@example.com', 'password')
    
    def setUp(self):
        """Set up data before each test method (runs before each test)."""
        # Use this for data that needs to be fresh for each test
        self.client.login(username='testuser', password='password')
    
    def test_something(self):
        """Test description."""
        # Test implementation
        self.assertEqual(expected, actual)
```

### Performance Optimization
- **Prefer `setUpTestData()` over `setUp()`** when test data doesn't need to be modified
- Tests are optimized with:
  - In-memory database for faster I/O
  - Fast password hasher for user creation
  - Parallel test execution support

### Test Tags
```python
from django.test import tag

@tag("slow")
class SeleniumTests(TestCase):
    """Slow tests like browser automation."""
    pass

@tag("integration")
class IntegrationTests(TestCase):
    """Integration tests."""
    pass
```

### Running Tests

**Quick tests (excludes slow tests):**
```bash
poetry run python manage.py test --exclude-tag=slow --parallel --failfast
```

**Full test suite:**
```bash
poetry run python manage.py test --parallel --failfast
```

**Single test:**
```bash
poetry run python manage.py test website.tests.test_api.APITests.test_specific_method
```

## Test Best Practices

### Coverage
- Test both success and failure cases
- Test edge cases and boundary conditions
- Test permission/authentication requirements
- Test data validation and error handling

### Assertions
- Use specific assertions: `assertEqual`, `assertTrue`, `assertIn`, etc.
- Include meaningful assertion messages: `self.assertEqual(result, expected, "User should be redirected after login")`
- Test one concept per test method

### Test Data
- Use factories or fixtures for complex test data
- Keep test data minimal and relevant
- Clean up after tests (Django's TestCase does this automatically)
- Use realistic but simple test data

### API Tests
```python
from rest_framework.test import APITestCase
from rest_framework import status

class MyAPITests(APITestCase):
    def test_api_endpoint(self):
        response = self.client.get('/api/endpoint/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('key', response.json())
```

### Mocking
```python
from unittest.mock import patch, MagicMock

class MyTests(TestCase):
    @patch('website.services.external_api.call')
    def test_with_mock(self, mock_call):
        mock_call.return_value = {'data': 'test'}
        # Test code that uses external_api.call()
```

## Common Patterns

### Testing Views
```python
def test_view_requires_login(self):
    """Test that view redirects unauthenticated users."""
    response = self.client.get('/protected-url/')
    self.assertEqual(response.status_code, 302)
    self.assertIn('/login/', response.url)

def test_view_with_valid_data(self):
    """Test view with valid POST data."""
    data = {'field': 'value'}
    response = self.client.post('/url/', data)
    self.assertEqual(response.status_code, 200)
```

### Testing Models
```python
def test_model_str_method(self):
    """Test model string representation."""
    obj = MyModel.objects.create(name='Test')
    self.assertEqual(str(obj), 'Test')

def test_model_validation(self):
    """Test model validation raises errors for invalid data."""
    with self.assertRaises(ValidationError):
        obj = MyModel(invalid_field='bad')
        obj.full_clean()
```

### Testing Forms
```python
def test_form_valid_data(self):
    """Test form accepts valid data."""
    form = MyForm(data={'field': 'value'})
    self.assertTrue(form.is_valid())

def test_form_invalid_data(self):
    """Test form rejects invalid data."""
    form = MyForm(data={'field': ''})
    self.assertFalse(form.is_valid())
    self.assertIn('field', form.errors)
```

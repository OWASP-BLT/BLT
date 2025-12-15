# Testing Guide

This guide explains how to run tests efficiently in the BLT project.

## Quick Start

### Fast Tests (Recommended for Development)

Excludes slow tests like Selenium for quick feedback:

```bash
poetry run python manage.py test --exclude-tag=slow --parallel --failfast
```

### Full Test Suite (CI/PR Validation)

Runs all tests including Selenium:

```bash
poetry run python manage.py test --parallel --failfast
```

### Run Specific Tests

```bash
# Run a specific test file
poetry run python manage.py test website.tests.test_api

# Run a specific test class
poetry run python manage.py test website.tests.test_api.APITests

# Run a specific test method
poetry run python manage.py test website.tests.test_api.APITests.test_specific_method
```

## Test Performance Optimizations

The BLT test suite has been optimized for speed with the following improvements:

### 1. In-Memory Database

Tests use an in-memory SQLite database (`:memory:`) instead of writing to disk. This provides 30-50% faster database operations.

**Location:** `blt/settings.py` - Applied when `TESTING=True`

### 2. Fast Password Hasher

Tests use MD5PasswordHasher instead of the secure but slow PBKDF2 hasher. This speeds up user creation by 50-70%.

**Location:** `blt/settings.py` - Applied when `TESTING=True`

**Note:** This is only for tests. Production code still uses secure password hashing.

### 3. Parallel Test Execution

The `--parallel` flag automatically detects CPU cores and runs tests in parallel, providing 2-4x speedup.

### 4. Test Tags

Slow tests (like Selenium) are tagged with `@tag("slow")` so they can be excluded during development:

```python
from django.test import TestCase, tag

@tag("slow", "selenium")
class MySlowTests(TestCase):
    def test_something_slow(self):
        pass
```

## Writing Performant Tests

### Use `setUpTestData()` for Read-Only Fixtures

When test data doesn't need to be modified, use `setUpTestData()` instead of `setUp()`:

```python
class MyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # This runs once for the entire test class
        cls.user = User.objects.create_user('testuser', 'test@example.com', 'password')
    
    def test_something(self):
        # Use cls.user (read-only)
        self.assertEqual(self.user.username, 'testuser')
```

### Tag Slow Tests

If a test takes more than a few seconds, tag it as slow:

```python
from django.test import TestCase, tag

@tag("slow")
class MySlowTests(TestCase):
    def test_complex_operation(self):
        # Complex test that takes time
        pass
```

### Mock External Services

Always mock external API calls and network requests to avoid slowdowns and flakiness:

```python
from unittest.mock import patch

class MyAPITests(TestCase):
    @patch('requests.get')
    def test_external_api(self, mock_get):
        mock_get.return_value.json.return_value = {'data': 'test'}
        # Test code that calls requests.get()
```

## Test Database Management

### Keeping the Test Database

For debugging, you can keep the test database between runs:

```bash
poetry run python manage.py test --keepdb
```

This speeds up subsequent test runs by reusing the database.

## CI/CD Integration

The CI pipeline automatically runs tests with optimizations:

```bash
poetry run xvfb-run --auto-servernum python manage.py test -v 3 --parallel --failfast
```

- `xvfb-run`: Provides virtual display for Selenium tests
- `--auto-servernum`: Automatically finds available X server
- `-v 3`: Verbose output for debugging
- `--parallel`: Parallel execution
- `--failfast`: Stop on first failure

## Expected Performance

With all optimizations enabled:

| Optimization | Expected Speedup |
|--------------|------------------|
| Fast Password Hasher | 50-70% faster user creation |
| In-Memory Database | 30-50% faster DB operations |
| Parallel Execution | 2-4x speedup (depends on cores) |
| **Combined** | **3-5x overall speedup** |

## Troubleshooting

### Tests Fail in Parallel but Pass Individually

This usually indicates tests that aren't properly isolated:
- Check for shared state between tests
- Ensure tests don't depend on execution order
- Use transactions properly (Django does this automatically)

### Selenium Tests Timing Out

Increase timeouts or ensure Chrome/ChromeDriver are properly installed:

```bash
# Install Chrome and ChromeDriver
sudo apt-get install chromium-browser chromium-chromedriver
```

### Database Locked Errors

SQLite has limited concurrent access. If you see "database is locked" errors:
- Ensure tests properly close database connections
- Consider using PostgreSQL for local development
- Check for long-running transactions

## Additional Resources

- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Django Test Runner Options](https://docs.djangoproject.com/en/stable/ref/django-admin/#test)
- [Writing and Running Tests](https://docs.djangoproject.com/en/stable/topics/testing/overview/)

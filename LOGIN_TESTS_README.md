# Login Functionality Test Suite

This document describes the comprehensive test suite for the BLT login functionality. The tests are designed to ensure the login system works correctly and securely.

## Test Files

### 1. `test_login_standalone.py`
A standalone test file that can run without Django dependencies. This tests the core login logic and security features.

**Run with:** `python test_login_standalone.py`

### 2. `website/tests/test_login_functionality.py`
Django-based unit tests for login functionality using the Django test framework.

**Run with:** `python manage.py test website.tests.test_login_functionality`

### 3. `website/tests/test_login_integration.py`
Comprehensive Django integration tests that test the full login flow.

**Run with:** `python manage.py test website.tests.test_login_integration`

## Test Coverage

### ✅ Valid Login Scenarios
- **Username login**: Users can log in with their username
- **Email login**: Users can log in with their email address
- **Case insensitive email**: Email login works regardless of case
- **Session management**: Proper session creation and management
- **Remember me**: Extended session duration when "remember me" is checked

### ❌ Invalid Login Scenarios
- **Wrong password**: Login fails with incorrect password
- **Non-existent user**: Login fails for users that don't exist
- **Empty credentials**: Login fails when username/password are empty
- **Whitespace-only input**: Login fails with whitespace-only credentials
- **Inactive user**: Login fails for deactivated user accounts
- **Unverified email**: Redirects to email verification for unverified accounts

### 🔒 Security Protection Tests
- **SQL Injection**: Protection against SQL injection attacks
- **XSS Protection**: Protection against cross-site scripting attacks
- **CSRF Protection**: CSRF token validation on login forms
- **Rate Limiting**: Protection against brute force attacks
- **Input Validation**: Proper validation of all input fields

### 🎯 User Experience Tests
- **Login page loads**: Login page displays correctly with all required fields
- **Error messages**: Clear error messages for different failure scenarios
- **Redirect functionality**: Proper redirect after successful login
- **Next parameter**: Redirect to intended page after login
- **Already logged in**: Redirect away from login page if already authenticated

### 🔧 Technical Tests
- **Authentication backend**: Direct testing of Django authentication
- **Form validation**: Testing of form field validation
- **Session creation**: Proper session creation and storage
- **Logout functionality**: Complete session cleanup on logout
- **Custom form behavior**: Testing of custom login form features

## Security Features Tested

### 1. Input Validation
```python
# Tests empty, whitespace, and malformed inputs
test_empty_credentials()
test_missing_password()
test_missing_username()
```

### 2. SQL Injection Protection
```python
# Tests various SQL injection patterns
malicious_inputs = [
    "admin'; DROP TABLE auth_user; --",
    "' OR '1'='1' --",
    "'; DELETE FROM auth_user WHERE '1'='1"
]
```

### 3. XSS Protection
```python
# Tests XSS payload filtering
xss_payloads = [
    '<script>alert("xss")</script>',
    'javascript:alert("xss")',
    '<img src="x" onerror="alert(1)">'
]
```

### 4. Rate Limiting
```python
# Tests protection against brute force attacks
for i in range(10):
    # Multiple failed login attempts
    response = client.post(login_url, invalid_credentials)
```

### 5. CSRF Protection
```python
# Tests CSRF token validation
csrf_client = Client(enforce_csrf_checks=True)
response = csrf_client.post(login_url, data)  # Should return 403
```

## Expected Behaviors

### Successful Login
1. User provides valid username/email and password
2. System authenticates the user
3. Session is created
4. User is redirected to dashboard or intended page
5. User remains logged in for session duration

### Failed Login
1. User provides invalid credentials
2. System shows error message: "Invalid username/email or password"
3. No session is created
4. User remains on login page
5. Failed attempt may be logged for rate limiting

### Security Violations
1. Malicious input is detected and sanitized
2. Error message doesn't reveal system information
3. Attack attempts may be logged
4. Rate limiting may be triggered

## Error Messages

The tests verify these specific error messages:

- **Invalid credentials**: "Invalid username/email or password"
- **Empty fields**: "This field is required"
- **Rate limited**: "Too many failed attempts. Please try again later."
- **Inactive account**: "Invalid username/email or password" (same as invalid to prevent enumeration)
- **Unverified email**: Redirect to email verification page

## Running the Tests

### Prerequisites
```bash
# Install required dependencies
pip install django django-allauth dj-database-url django-environ sentry-sdk

# Or use Poetry (if available)
poetry install
```

### Run Individual Test Suites
```bash
# Standalone tests (no Django setup required)
python test_login_standalone.py

# Django unit tests
python manage.py test website.tests.test_login_functionality

# Django integration tests
python manage.py test website.tests.test_login_integration

# Run all login tests
python manage.py test website.tests.test_login_functionality website.tests.test_login_integration
```

### Test Output
Successful test runs will show:
- ✅ All test cases passed
- 🔒 Security protections working
- 📊 Coverage of all login scenarios
- 🎯 Proper error handling

## Maintenance

### Adding New Tests
When adding new login features, ensure you:
1. Add corresponding test cases
2. Test both positive and negative scenarios
3. Include security testing for new inputs
4. Update this documentation

### Test Data
Tests use these predefined users:
- `testuser` / `test@example.com` - Active, verified user
- `inactiveuser` / `inactive@example.com` - Inactive user
- `unverifieduser` / `unverified@example.com` - Unverified email

### Common Issues
- **Database errors**: Ensure test database is properly configured
- **Missing dependencies**: Install all required packages
- **Permission errors**: Ensure proper file permissions
- **Environment variables**: Set required environment variables for testing

## Conclusion

This comprehensive test suite ensures the BLT login functionality is:
- ✅ **Functional**: Works correctly for valid users
- 🔒 **Secure**: Protected against common attacks
- 🎯 **User-friendly**: Provides clear feedback
- 🔧 **Maintainable**: Easy to extend and modify

The tests cover all critical login scenarios and security requirements, providing confidence in the system's reliability and security.
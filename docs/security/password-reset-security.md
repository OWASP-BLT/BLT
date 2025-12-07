# Password Reset Security

## Overview

The BLT application implements secure password reset functionality that prevents account enumeration attacks.

## Implementation

The password reset feature uses `dj-rest-auth` with `allauth`, which implements the following security measures:

### 1. Consistent Response Behavior

**All password reset requests return the same response**, regardless of whether the email exists:

```json
HTTP 200 OK
{
  "detail": "Password reset e-mail has been sent."
}
```

This prevents attackers from determining which email addresses are registered in the system.

### 2. Selective Email Sending

While the API returns a success message for all requests:
- **Known accounts**: A password reset email is sent
- **Unknown accounts**: NO email is sent (prevents spam and information leakage)

This approach:
- ✅ Prevents account enumeration
- ✅ Reduces spam and abuse potential
- ✅ Follows OWASP security best practices
- ✅ Maintains good user experience

## Code Location

- **Implementation**: `dj-rest-auth` library with `allauth` backend
- **URL**: `/auth/password/reset/` (POST)
- **Settings**: `blt/settings.py` - `REST_AUTH` configuration
- **Form**: Uses `AllAuthPasswordResetForm` from `dj-rest-auth.forms`
- **Tests**: `website/tests/test_api.py` - `TestPasswordResetUnknownEmail`

## Testing

Tests verify the security behavior:

```bash
poetry run python manage.py test website.tests.test_api.TestPasswordResetUnknownEmail
```

Expected results:
- Unknown email: HTTP 200, no email sent
- Known email: HTTP 200, email sent

## Security Considerations

### Why This Matters

Without proper implementation, password reset could leak information:

❌ **Bad Practice**:
```
Unknown email → "This email is not registered"
Known email → "Password reset email sent"
```

✅ **Good Practice** (current implementation):
```
Any email → "Password reset email sent" (but only actually send to known addresses)
```

### Attack Prevention

This implementation prevents:
1. **Account Enumeration**: Attackers cannot determine valid email addresses
2. **Timing Attacks**: Response time is consistent (no database lookup difference exposed)
3. **Spam Abuse**: Unknown addresses don't receive emails

## Maintaining Security

When modifying authentication code:

1. **Never** reveal whether an email/username exists
2. **Always** return consistent responses for security-sensitive operations
3. **Test** with both valid and invalid inputs
4. **Monitor** for timing differences that could leak information

## Related Documentation

- [OWASP Authentication Cheat Sheet](https://cheatsheetsecurity.org/cheatsheet/authentication-cheat-sheet)
- [dj-rest-auth Documentation](https://dj-rest-auth.readthedocs.io/)
- [django-allauth Security](https://django-allauth.readthedocs.io/en/latest/overview.html#security)

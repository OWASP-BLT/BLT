# URL Migration Plan for OWASP BLT

This document outlines the plan for migrating legacy URL patterns to modern Django path-based routing.

**Status:** Planning Phase  
**Last Updated:** 2026-03-01  
**Related Documentation:** [URL_ENDPOINTS.md](URL_ENDPOINTS.md)

---

## Executive Summary

The OWASP BLT application currently uses a mix of:
- **117 legacy regex-based URLs** using `re_path()` (Django's old `url()` pattern)
- **389 modern path-based URLs** using `path()` (introduced in Django 2.0+)

This migration plan identifies which URLs need to be converted from regex patterns to modern path converters, improving code maintainability and readability.

---

## Table of Contents

1. [Migration Goals](#migration-goals)
2. [Current State Analysis](#current-state-analysis)
3. [Migration Strategy](#migration-strategy)
4. [URL Categories for Migration](#url-categories-for-migration)
5. [Priority & Phasing](#priority--phasing)
6. [Testing Plan](#testing-plan)
7. [Risk Assessment](#risk-assessment)
8. [Rollback Plan](#rollback-plan)

---

## Migration Goals

### Why Migrate?

1. **Improved Readability**: Path converters are more intuitive than regex patterns
2. **Better Maintainability**: Less error-prone and easier for new developers
3. **Modern Best Practices**: Align with current Django standards (Django 2.0+)
4. **Type Safety**: Path converters provide built-in type conversion and validation
5. **Performance**: Slightly better performance due to simpler pattern matching

### Success Criteria

- [ ] All regex-based URLs converted to path-based URLs where applicable
- [ ] Zero breaking changes to existing functionality
- [ ] All tests passing after migration
- [ ] Documentation updated to reflect new URL patterns
- [ ] No degradation in application performance

---

## Current State Analysis

### Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| Total URL patterns | 506 | 100% |
| Modern `path()` patterns | 389 | 76.9% |
| Legacy `re_path()` patterns | 117 | 23.1% |
| Third-party URL includes | ~15 | - |

### Legacy Pattern Distribution by Component

Based on analysis of `blt/urls.py`:

| Component | Legacy Patterns | Priority | Notes |
|-----------|----------------|----------|-------|
| **Issues & Bugs** | ~25 | HIGH | Core functionality |
| **User Management** | ~15 | HIGH | Authentication critical |
| **Organizations** | ~10 | MEDIUM | Dashboard URLs |
| **Bug Hunts** | ~8 | MEDIUM | Bounty system |
| **Projects** | ~8 | MEDIUM | Project views |
| **Education** | ~6 | LOW | Course system |
| **Leaderboards** | ~5 | LOW | Gamification |
| **Social/Messaging** | ~10 | MEDIUM | Community features |
| **API Endpoints** | ~15 | HIGH | External integrations |
| **Other Features** | ~15 | LOW | Misc functionality |

---

## Migration Strategy

### Phase 1: Preparation (Week 1)

**Goals**: 
- Audit all URL patterns
- Document existing behavior
- Set up comprehensive testing

**Tasks**:
1. ✅ Create complete URL endpoint inventory (see [URL_ENDPOINTS.md](URL_ENDPOINTS.md))
2. [ ] Document all URL parameters and their types
3. [ ] Review existing test coverage for URL routing
4. [ ] Create migration testing checklist
5. [ ] Set up URL monitoring/logging for production

### Phase 2: Low-Risk Migrations (Week 2-3)

**Goals**: 
- Convert simple patterns first
- Establish migration workflow
- Validate testing approach

**Targets**:
- Simple numeric IDs: `(?P<id>\d+)` → `<int:id>`
- String slugs: `(?P<slug>\w+)` → `<slug:slug>`
- UUIDs: `(?P<uuid>[0-9a-f-]+)` → `<uuid:uuid>`

**Examples**:

```python
# BEFORE (regex)
re_path(r"^like_issue/(?P<issue_pk>\d+)/$", like_issue, name="like_issue")
re_path(r"^project/(?P<slug>\w+)/$", project_detail, name="project_detail")

# AFTER (path)
path("like_issue/<int:issue_pk>/", like_issue, name="like_issue")
path("project/<slug:slug>/", project_detail, name="project_detail")
```

### Phase 3: Medium-Risk Migrations (Week 4-5)

**Goals**:
- Convert more complex patterns
- Handle special cases
- Maintain backward compatibility where needed

**Targets**:
- Patterns with optional parameters
- Multiple parameter patterns
- Patterns with complex validation

### Phase 4: High-Risk & API Migrations (Week 6-7)

**Goals**:
- Convert critical API endpoints
- Ensure no breaking changes for API consumers
- Update API documentation

**Targets**:
- REST API endpoints
- Webhook endpoints
- OAuth callbacks

### Phase 5: Validation & Cleanup (Week 8)

**Goals**:
- Comprehensive testing
- Performance validation
- Documentation updates

**Tasks**:
1. [ ] Full regression testing
2. [ ] Load testing
3. [ ] Update all documentation
4. [ ] Remove deprecated patterns
5. [ ] Final code review

---

## URL Categories for Migration

### Category 1: Simple Integer IDs ✅ SAFE

**Pattern**: `(?P<name>\d+)` → `<int:name>`

**Count**: ~40 patterns

**Examples**:

```python
# Issues & Bugs
re_path(r"^like_issue/(?P<issue_pk>\d+)/$", like_issue, name="like_issue")
→ path("like_issue/<int:issue_pk>/", like_issue, name="like_issue")

re_path(r"^flag_issue/(?P<issue_pk>\d+)/$", flag_issue, name="flag_issue")
→ path("flag_issue/<int:issue_pk>/", flag_issue, name="flag_issue")

re_path(r"^save_issue/(?P<issue_pk>\d+)/$", save_issue, name="save_issue")
→ path("save_issue/<int:issue_pk>/", save_issue, name="save_issue")

# Organizations
re_path(r"^organization/(?P<pk>\d+)/dashboard/", ...)
→ path("organization/<int:pk>/dashboard/", ...)

# Education
re_path(r"^education/view-course/(?P<id>\d+)/$", view_course, name="view_course")
→ path("education/view-course/<int:id>/", view_course, name="view_course")
```

**Risk Level**: LOW - Direct 1:1 conversion

---

### Category 2: String Slugs ✅ SAFE

**Pattern**: `(?P<slug>\w+)` or `(?P<slug>[\w-]+)` → `<slug:slug>`

**Count**: ~30 patterns

**Examples**:

```python
# Issues
re_path(r"^issue/(?P<slug>\w+)/$", IssueView.as_view(), name="issue_view")
→ path("issue/<slug:slug>/", IssueView.as_view(), name="issue_view")

# Projects
re_path(r"^project/(?P<slug>[\w-]+)/$", project_detail, name="project_detail")
→ path("project/<slug:slug>/", project_detail, name="project_detail")

# Blog
re_path(r"^blog/(?P<slug>[\w-]+)/$", PostDetailView.as_view(), name="post_detail")
→ path("blog/<slug:slug>/", PostDetailView.as_view(), name="post_detail")

# Organizations
re_path(r"^organization/(?P<slug>[\w-]+)/$", OrganizationDetailView.as_view())
→ path("organization/<slug:slug>/", OrganizationDetailView.as_view())
```

**Risk Level**: LOW - Django's slug converter is well-tested

---

### Category 3: Simple Path Patterns ✅ SAFE

**Pattern**: `^pattern/$` → `pattern/`

**Count**: ~25 patterns

**Examples**:

```python
# Core
re_path(r"^issues/$", newhome, name="issues")
→ path("issues/", newhome, name="issues")

re_path(r"^leaderboard/$", GlobalLeaderboardView.as_view(), name="leaderboard_global")
→ path("leaderboard/", GlobalLeaderboardView.as_view(), name="leaderboard_global")

# User
re_path(r"^contributors/$", contributors_view, name="contributors")
→ path("contributors/", contributors_view, name="contributors")

# Education
re_path(r"^education/$", education_home, name="education")
→ path("education/", education_home, name="education")
```

**Risk Level**: LOW - No parameters, just path conversion

---

### Category 4: Username/String Parameters ⚠️ REVIEW NEEDED

**Pattern**: `(?P<user>\w+)` or `(?P<username>[\w.@+-]+)` → Custom or `<str:user>`

**Count**: ~10 patterns

**Examples**:

```python
# User profiles
re_path(r"^profile/(?P<slug>[\w.@+-]+)/$", UserProfileDetailView.as_view(), name="profile")
→ path("profile/<str:slug>/", UserProfileDetailView.as_view(), name="profile")
# OR use custom converter for username validation

re_path(r"^follow/(?P<user>[\w.@+-]+)/$", follow_user, name="follow_user")
→ path("follow/<str:user>/", follow_user, name="follow_user")
```

**Risk Level**: MEDIUM - Need to ensure username characters are properly handled

**Note**: May need custom path converter for username validation:

```python
class UsernameConverter:
    regex = r'[\w.@+-]+'
    
    def to_python(self, value):
        return value
    
    def to_url(self, value):
        return value

register_converter(UsernameConverter, 'username')
```

---

### Category 5: Complex Patterns ⚠️ REQUIRES CUSTOM CONVERTER

**Pattern**: Complex regex patterns that don't map to built-in converters

**Count**: ~7 patterns

**Examples**:

```python
# Commit SHAs (GitHub integration)
re_path(r"^commit/(?P<sha>[0-9a-f]{40})/$", commit_detail, name="commit_detail")
→ # Requires custom converter or keep as re_path

# Date patterns
re_path(r"^stats/(?P<year>\d{4})/(?P<month>\d{1,2})/$", monthly_stats)
→ path("stats/<int:year>/<int:month>/", monthly_stats)  # Limited validation

# Token patterns
re_path(r"^verify/(?P<token>[0-9a-zA-Z-_]+)/$", verify_email)
→ # May need custom converter
```

**Risk Level**: HIGH - Need careful validation and testing

**Options**:
1. Create custom path converters
2. Keep as `re_path()` if too complex
3. Split into multiple simpler patterns

---

### Category 6: API Endpoints with Versions 🔴 CRITICAL

**Pattern**: API versioning patterns

**Count**: ~15 patterns

**Examples**:

```python
# API v1
re_path(r"^api/v1/issues/$", IssueViewSet.as_view(...))
→ path("api/v1/issues/", IssueViewSet.as_view(...))

# Keep version in path for backward compatibility
```

**Risk Level**: HIGH - External consumers depend on these

**Strategy**:
- Maintain exact URL structure
- Add deprecation warnings if changing
- Version API documentation

---

## Priority & Phasing

### High Priority (Do First)

1. **Category 1**: Simple Integer IDs (~40 patterns)
   - Core issues functionality
   - Most common pattern
   - Lowest risk

2. **Category 3**: Simple Path Patterns (~25 patterns)
   - No parameters
   - Zero risk

3. **Category 2**: String Slugs (~30 patterns)
   - Well-supported by Django
   - Low risk

### Medium Priority (Do Second)

4. **Category 4**: Username Parameters (~10 patterns)
   - Need validation review
   - Medium risk

5. **Category 5**: Complex Patterns (~7 patterns)
   - Requires custom work
   - Medium to high risk

### Low Priority (Do Last)

6. **Category 6**: API Endpoints (~15 patterns)
   - Critical for external consumers
   - Highest risk
   - May require deprecation period

---

## Testing Plan

### Pre-Migration Testing

1. **URL Resolution Tests**
   ```python
   def test_url_resolution_before_migration():
       # Test all existing URLs resolve correctly
       url = reverse('issue_view', kwargs={'slug': 'test-issue'})
       assert url == '/issue/test-issue/'
   ```

2. **Integration Tests**
   - Ensure all views are accessible
   - Test with various parameter values
   - Test edge cases (special characters, etc.)

3. **Performance Baseline**
   - Measure URL resolution time
   - Document current performance metrics

### Post-Migration Testing

1. **URL Resolution Tests (Updated)**
   ```python
   def test_url_resolution_after_migration():
       # Test migrated URLs still resolve correctly
       url = reverse('issue_view', kwargs={'slug': 'test-issue'})
       assert url == '/issue/test-issue/'
   ```

2. **Regression Testing**
   - Run full test suite
   - Check all endpoints manually
   - Verify no broken links

3. **Performance Validation**
   - Compare URL resolution time
   - Ensure no performance degradation

### Continuous Testing

- Run URL tests on every commit
- Monitor production URLs for 404s
- Track error rates in logging

---

## Risk Assessment

### Low Risk Items

- ✅ Simple integer ID conversions
- ✅ Basic path patterns without parameters
- ✅ Well-tested slug patterns

**Mitigation**: Standard testing, code review

### Medium Risk Items

- ⚠️ Username parameters with special characters
- ⚠️ Complex regex patterns
- ⚠️ Patterns with multiple parameters

**Mitigation**: 
- Extra validation tests
- Staged rollout
- Feature flags if needed

### High Risk Items

- 🔴 API endpoints with external consumers
- 🔴 OAuth callback URLs
- 🔴 Webhook endpoints
- 🔴 Patterns used in external documentation

**Mitigation**:
- Maintain backward compatibility
- Use redirects if changing URLs
- Version API endpoints
- Communicate changes in advance
- Extended testing period

---

## Rollback Plan

### If Issues Detected

1. **Immediate Rollback**
   ```bash
   # Revert to previous commit
   git revert <migration-commit>
   
   # Or checkout previous version
   git checkout <previous-commit> -- blt/urls.py
   ```

2. **Partial Rollback**
   - Revert specific URL categories
   - Keep low-risk changes
   - Roll back high-risk changes

3. **Feature Flag Approach**
   ```python
   # Use settings to toggle new/old URLs
   if settings.USE_NEW_URL_PATTERNS:
       path("issue/<slug:slug>/", IssueView.as_view())
   else:
       re_path(r"^issue/(?P<slug>\w+)/$", IssueView.as_view())
   ```

### Monitoring After Migration

1. **Error Tracking**
   - Monitor 404 errors
   - Track URL resolution failures
   - Alert on increased error rates

2. **Performance Monitoring**
   - Track response times
   - Monitor URL resolution time
   - Compare to baseline metrics

3. **User Feedback**
   - Monitor support tickets
   - Check for broken link reports
   - Review user complaints

---

## Implementation Checklist

### Before Starting

- [x] Create URL endpoint inventory
- [ ] Review all URL patterns in codebase
- [ ] Document current test coverage
- [ ] Set up monitoring/alerting
- [ ] Create migration branch
- [ ] Notify team of migration plan

### During Migration

- [ ] Migrate Category 1 (Simple IDs)
- [ ] Run tests and validate
- [ ] Migrate Category 3 (Simple paths)
- [ ] Run tests and validate
- [ ] Migrate Category 2 (Slugs)
- [ ] Run tests and validate
- [ ] Review and plan Category 4 (Usernames)
- [ ] Create custom converters if needed
- [ ] Migrate Category 4
- [ ] Run tests and validate
- [ ] Review and plan Category 5 (Complex)
- [ ] Migrate or keep complex patterns
- [ ] Run tests and validate
- [ ] Plan deprecation for Category 6 (APIs)
- [ ] Communicate API changes
- [ ] Migrate Category 6 with backward compatibility
- [ ] Run full test suite

### After Migration

- [ ] Update URL_ENDPOINTS.md documentation
- [ ] Update API documentation
- [ ] Update developer guides
- [ ] Deploy to staging
- [ ] Validate in staging environment
- [ ] Monitor for issues
- [ ] Deploy to production
- [ ] Monitor production metrics
- [ ] Mark migration as complete

---

## Reference: Django Path Converters

Django provides these built-in path converters:

| Converter | Pattern | Example |
|-----------|---------|---------|
| `str` | Non-empty string excluding `/` | `<str:name>` |
| `int` | Zero or positive integer | `<int:id>` |
| `slug` | Slug string (letters, numbers, hyphens, underscores) | `<slug:slug>` |
| `uuid` | UUID format | `<uuid:id>` |
| `path` | Non-empty string including `/` | `<path:file_path>` |

### Custom Converter Template

```python
# blt/converters.py
class CustomConverter:
    regex = r'[0-9a-f-]+'  # Your regex pattern
    
    def to_python(self, value):
        """Convert URL string to Python object"""
        return value
    
    def to_url(self, value):
        """Convert Python object to URL string"""
        return str(value)

# Register in urls.py
from django.urls import register_converter
from blt.converters import CustomConverter

register_converter(CustomConverter, 'custom')

# Use in patterns
path('item/<custom:id>/', view, name='item_detail')
```

---

## Related Documentation

- [URL Endpoints Documentation](URL_ENDPOINTS.md) - Complete list of all current URLs
- [Django URL Dispatcher Docs](https://docs.djangoproject.com/en/5.1/topics/http/urls/)
- [Django Path Converters](https://docs.djangoproject.com/en/5.1/topics/http/urls/#path-converters)

---

## Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2026-03-01 | 1.0 | Initial migration plan created | GitHub Copilot |

---

**Questions or Concerns?**

Contact the development team or create an issue on GitHub with the `url-migration` label.

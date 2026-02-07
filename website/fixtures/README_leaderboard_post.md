# Leaderboard Blog Post Fixture

This fixture contains a blog post announcing the Enhanced Monthly Leaderboard GitHub Action.

## Loading the Blog Post

To load this blog post into your database:

```bash
poetry run python manage.py loaddata website/fixtures/leaderboard_blog_post.json
```

**Note:** This fixture requires a user with username "admin" to exist. If you don't have this user, you can either:

1. Create the admin user first:
   ```bash
   poetry run python manage.py createsuperuser --username admin
   ```

2. Or modify the fixture to use a different existing username.

## Blog Post Details

- **Title:** Introducing the Enhanced Monthly Leaderboard GitHub Action
- **Slug:** introducing-the-enhanced-monthly-leaderboard-github-action
- **URL:** `/blog/introducing-the-enhanced-monthly-leaderboard-github-action/`
- **Author:** admin (must exist before loading)
- **Content:** Comprehensive announcement of the new leaderboard features including:
  - Point system breakdown
  - Monthly ranking system
  - Anti-abuse features
  - Automatic leaderboard comments
  - Security measures
  - Configuration options
  - Technical details

## Viewing the Blog Post

After loading the fixture, you can view the blog post at:
- List view: http://localhost:8000/blog/
- Detail view: http://localhost:8000/blog/introducing-the-enhanced-monthly-leaderboard-github-action/

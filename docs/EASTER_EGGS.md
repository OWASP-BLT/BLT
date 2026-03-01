# Easter Eggs Documentation

## Overview

BLT features several hidden Easter eggs throughout the site for users to discover. These Easter eggs are designed to be fun, engaging, and mobile-friendly. One special Easter egg even rewards users with BACON tokens!

## Easter Egg List

### 1. Konami Code
- **Trigger**: Type the classic Konami code sequence: ↑ ↑ ↓ ↓ ← → ← → B A
- **Reward**: Fun notification
- **Device**: Desktop/Mobile (keyboard required)

### 2. Secret Logo
- **Trigger**: Click the site logo 7 times rapidly (within 500ms between clicks)
- **Reward**: Fun notification
- **Device**: Desktop/Mobile

### 3. Footer Tap Master
- **Trigger**: Tap the footer 5 times within 2 seconds
- **Reward**: Fun notification
- **Device**: Desktop/Mobile

### 4. Secret BACON (Token Reward) 🥓
- **Trigger**: 
  1. Type 'bacon' on your keyboard
  2. Look for glowing bacon-related elements
  3. Click the glowing element within 30 seconds
- **Reward**: 10 BACON tokens
- **Limit**: Once per user, once per day across all bacon Easter eggs
- **Security**: CSRF protected, rate limited, requires verification token
- **Device**: Desktop/Mobile

### 5. Lucky Tap
- **Trigger**: Random chance (5%) on double-tap anywhere
- **Reward**: Fun notification
- **Device**: Mobile only (touch devices)

### 6. Four Corners Explorer
- **Trigger**: Click all four corners of the screen
- **Reward**: Fun notification
- **Device**: Desktop/Mobile

### 7. Speed Scroller
- **Trigger**: Scroll to the bottom of the page 3 times within 5 seconds
- **Reward**: Fun notification
- **Device**: Desktop/Mobile

## Technical Details

### Security Features

The Easter egg system includes several security measures to prevent abuse:

1. **Authentication Required**: Users must be logged in to discover Easter eggs
2. **CSRF Protection**: All discovery requests use Django's CSRF protection
3. **Rate Limiting**: Maximum 10 discovery attempts per user per hour
4. **Verification Tokens**: Bacon token Easter eggs require a secure verification token
   - Tokens are generated using PBKDF2-HMAC-SHA256
   - Tokens are tied to user ID, egg code, and current date
   - Tokens cannot be reused across days
5. **Daily Limits**: Users can only earn bacon tokens once per day
6. **IP and User Agent Tracking**: All discoveries are logged with metadata
7. **Unique Constraint**: Database constraint prevents duplicate discoveries

### Implementation

**Models**: `website/models.py`
- `EasterEgg`: Defines available Easter eggs
- `EasterEggDiscovery`: Tracks user discoveries

**Views**: `website/views/easter_eggs.py`
- `discover_easter_egg`: Handles discovery attempts
- `get_verification_token`: Generates verification tokens for bacon eggs

**Frontend**: `website/static/js/easter-eggs.js`
- Detects user interactions (keyboard, clicks, touches)
- Manages Easter egg state
- Sends discovery requests to backend
- Displays celebrations and notifications

**Admin**: `website/admin.py`
- Easter egg management interface
- Discovery tracking and statistics

### Setup

1. Run migrations:
```bash
python manage.py migrate
```

2. Create initial Easter eggs:
```bash
python manage.py create_easter_eggs
```

3. Easter eggs will be automatically loaded for authenticated users via the base template.

### Adding New Easter Eggs

#### Backend (Django)

1. Create the Easter egg in the database (admin panel or management command):
```python
EasterEgg.objects.create(
    name="My Easter Egg",
    code="my-egg-code",
    description="Description of the Easter egg",
    reward_type="fun",  # or "bacon", "badge", "points"
    reward_amount=0,  # amount if applicable
    is_active=True,
    max_claims_per_user=1
)
```

#### Frontend (JavaScript)

Add a new handler in `website/static/js/easter-eggs.js`:
```javascript
function initMyEasterEgg() {
    // Your detection logic
    document.addEventListener('event', (e) => {
        // Trigger condition
        if (condition) {
            discoverEasterEgg('my-egg-code');
        }
    });
}

// Add to init() function
initMyEasterEgg();
```

### Testing

Run the Easter egg tests:
```bash
python manage.py test website.tests.test_easter_eggs
```

### Best Practices

1. **Mobile Friendly**: Always test Easter eggs on both desktop and mobile devices
2. **Accessibility**: Don't make Easter eggs so hidden that they're frustrating
3. **Performance**: Keep detection logic lightweight
4. **Security**: Never trust client-side validation alone for rewards
5. **User Experience**: Provide satisfying feedback when Easter eggs are found

## Admin Management

Administrators can:
- View all Easter eggs in the Django admin
- Enable/disable Easter eggs
- View discovery statistics
- See who discovered which Easter eggs
- Modify reward amounts and limits

## Monitoring

Track Easter egg engagement through:
- Django admin discovery logs
- User bacon earning history
- Discovery count per Easter egg
- Discovery patterns (time, device, etc.)

## Future Ideas

Potential Easter eggs to add:
- Seasonal Easter eggs (holidays)
- Time-based Easter eggs (specific times of day)
- Achievement-based Easter eggs (after completing certain actions)
- Social Easter eggs (requires multiple users)
- Location-based Easter eggs
- Sound-based Easter eggs (use microphone with permission)

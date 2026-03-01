# Easter Eggs Quick Start Guide 🥚

## For Users: How to Find Easter Eggs

### Desktop Easter Eggs

1. **Konami Code** - Type: ↑ ↑ ↓ ↓ ← → ← → B A
2. **Secret Logo** - Click the BLT logo 7 times rapidly
3. **Four Corners** - Click all four corners of your screen
4. **Speed Scroller** - Scroll to bottom 3 times in 5 seconds
5. **Secret BACON** 🥓 - Type "bacon", then click glowing elements (EARNS TOKENS!)

### Mobile Easter Eggs

1. **Secret Logo** - Tap the BLT logo 7 times rapidly
2. **Footer Tap** - Tap the footer 5 times quickly
3. **Lucky Tap** - Double-tap anywhere (5% random chance)
4. **Four Corners** - Tap all four corners of your screen
5. **Secret BACON** 🥓 - Type "bacon", then tap glowing elements (EARNS TOKENS!)

### The BACON Token Easter Egg 🥓💰

This is the special one that rewards actual BACON tokens!

**How to trigger:**
1. Type the word "bacon" on your keyboard
2. Look for elements that start glowing (pulsing animation)
3. Click or tap the glowing element within 30 seconds
4. Earn 10 BACON tokens!

**Limits:**
- Once per user
- Once per day across all bacon Easter eggs
- Must be logged in

**Security:** Impossible to hack due to:
- Server-side verification tokens using PBKDF2-HMAC-SHA256
- CSRF protection
- Rate limiting (10 attempts per hour)
- Daily limits enforced server-side
- Unique constraint in database

## For Administrators

### Setup

1. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

2. **Create Easter eggs:**
   ```bash
   python manage.py create_easter_eggs
   ```

3. **Verify in admin:**
   - Go to Django admin
   - Navigate to "Easter Eggs" section
   - Ensure all eggs are active

### Management

Access the Django admin panel to:
- Enable/disable Easter eggs
- View discovery statistics
- See who found which Easter eggs
- Adjust reward amounts
- Set claim limits

### Monitoring

Check Easter egg engagement:
```python
# In Django shell
from website.models import EasterEgg, EasterEggDiscovery

# See total discoveries
EasterEggDiscovery.objects.count()

# Most popular Easter egg
EasterEgg.objects.annotate(
    discovery_count=Count('discoveries')
).order_by('-discovery_count')

# Recent discoveries
EasterEggDiscovery.objects.order_by('-discovered_at')[:10]
```

## For Developers

### File Structure

```
website/
├── models.py                       # EasterEgg, EasterEggDiscovery models
├── views/
│   └── easter_eggs.py             # Discovery views, verification
├── static/
│   └── js/
│       └── easter-eggs.js         # Client-side detection
├── management/
│   └── commands/
│       └── create_easter_eggs.py  # Setup command
├── migrations/
│   └── 0256_add_easter_egg_models.py
└── tests/
    └── test_easter_eggs.py        # Comprehensive tests

blt/
└── urls.py                        # Easter egg endpoints

website/templates/
└── base.html                      # JavaScript inclusion

docs/
└── EASTER_EGGS.md                 # Full documentation
```

### Adding a New Easter Egg

**Backend:**
```python
EasterEgg.objects.create(
    name="My Easter Egg",
    code="my-code",
    description="Description here",
    reward_type="fun",  # or "bacon", "badge", "points"
    reward_amount=0,
    is_active=True,
    max_claims_per_user=1
)
```

**Frontend (in easter-eggs.js):**
```javascript
function initMyEasterEgg() {
    // Your detection logic
    document.addEventListener('myevent', (e) => {
        if (condition) {
            discoverEasterEgg('my-code');
        }
    });
}

// Add to init() function
initMyEasterEgg();
```

### Testing

Run Easter egg tests:
```bash
python manage.py test website.tests.test_easter_eggs
```

## Security Features

✅ **Authentication Required** - Must be logged in
✅ **CSRF Protected** - All POST requests protected
✅ **Rate Limited** - Max 10 attempts/hour
✅ **Verification Tokens** - PBKDF2-HMAC-SHA256 for bacon eggs
✅ **Daily Limits** - Server-side enforcement
✅ **IP Tracking** - Abuse prevention
✅ **Unique Constraints** - Database-level protection

## Troubleshooting

### Easter Eggs Not Working

1. **Check authentication:**
   - Easter eggs only work for logged-in users
   - Sign in and try again

2. **Check JavaScript console:**
   - Open browser developer tools
   - Look for errors in console
   - Should see "🥚 Easter eggs initialized!"

3. **Verify Easter eggs are active:**
   - Check Django admin
   - Ensure Easter eggs are marked as active

4. **Clear cache:**
   ```bash
   python manage.py clear_cache
   ```

### Bacon Tokens Not Awarded

1. **Check daily limit:**
   - Only one bacon Easter egg per day
   - Try again tomorrow

2. **Check verification token:**
   - Ensure verification endpoint is working
   - Check server logs for errors

3. **Check BaconEarning model:**
   ```python
   from website.models import BaconEarning
   BaconEarning.objects.get(user=user)
   ```

## Fun Facts

- 🎮 The Konami Code is a classic gaming Easter egg from the 1980s
- 🥓 The bacon Easter egg uses the same security as cryptocurrency wallets
- 📱 All Easter eggs work on mobile devices (touch-friendly)
- 🎨 CSS animations make discoveries more exciting
- 🔐 The bacon token system is mathematically impossible to hack

## See Full Documentation

For complete technical details, see [docs/EASTER_EGGS.md](docs/EASTER_EGGS.md)

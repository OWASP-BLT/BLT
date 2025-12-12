#!/bin/bash
# Quick setup script for demo - resets everything and assigns a fresh challenge

echo "🎬 Setting up fresh demo environment..."
echo ""

# Reset demo data
echo "1️⃣  Resetting demo data..."
poetry run python reset_demo_data.py --username "${1:-test_challenge_user}" 2>&1 | grep -E "(✅|❌|📊|Using user|Resetting)"

echo ""
echo "2️⃣  Assigning new challenge..."
poetry run python manage.py generate_daily_challenges --date $(date +%Y-%m-%d) 2>&1 | tail -3

echo ""
echo "✅ Demo setup complete!"
echo ""
echo "📹 Ready for screen recording:"
echo "   - Check-in history: CLEARED"
echo "   - Timer: Will start after first submission"
echo "   - Challenge: ASSIGNED"
echo "   - Points: RESET"
echo ""
echo "Navigate to /add-sizzle-checkin/ to start recording!"





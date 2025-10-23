#!/bin/bash

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8787}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"

echo "🧪 Testing Bug Reporter Authentication"
echo "====================================="

# Check for required environment variables
if [ -z "$ADMIN_EMAIL" ] || [ -z "$ADMIN_PASSWORD" ]; then
    echo "❌ ADMIN_EMAIL and ADMIN_PASSWORD environment variables must be set"
    exit 1
fi

# Test API login
echo "🔄 Testing API login..."
RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASSWORD\"}")

if [ $? -ne 0 ]; then
    echo "❌ curl request failed for login"
    exit 1
fi

if echo "$RESPONSE" | grep -q "token"; then
    echo "✅ API login successful"
    TOKEN=$(echo "$RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    echo "   Token: ${TOKEN:0:20}..."
else
    echo "❌ API login failed"
    echo "   Response: $RESPONSE"
    exit 1
fi

# Test protected endpoint
echo "🔄 Testing protected endpoint..."
PROTECTED_RESPONSE=$(curl -s -X GET "$API_BASE_URL/api/protected/me" \
  -H "Authorization: Bearer $TOKEN")

if [ $? -ne 0 ]; then
    echo "❌ curl request failed for protected endpoint"
    exit 1
fi

if echo "$PROTECTED_RESPONSE" | grep -q "$ADMIN_EMAIL"; then
    echo "✅ Protected endpoint access successful"
else
    echo "❌ Protected endpoint access failed"
    echo "   Response: $PROTECTED_RESPONSE"
    exit 1
fi

# Test frontend
echo "🔄 Testing frontend..."
FRONTEND_RESPONSE=$(curl -s "$FRONTEND_URL")

if [ $? -ne 0 ]; then
    echo "❌ curl request failed for frontend"
    exit 1
fi

if echo "$FRONTEND_RESPONSE" | grep -q "Bug Reporter"; then
    echo "✅ Frontend is accessible"
else
    echo "❌ Frontend is not accessible"
    exit 1
fi

echo ""
echo "🎉 All authentication tests passed!"
echo ""
echo "Your Bug Reporter is ready to use:"
echo "• Frontend: $FRONTEND_URL"
echo "• API: $API_BASE_URL"
echo "• Admin login: Use ADMIN_EMAIL and ADMIN_PASSWORD environment variables"
echo ""
echo "The sign-in and signup should now work properly in the browser!"

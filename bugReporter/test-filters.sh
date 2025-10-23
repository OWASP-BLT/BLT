#!/bin/bash

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8787}"

echo "🧪 Testing Bug Reporter Filters"
echo "=============================="

# Check for required commands
if ! command -v curl &> /dev/null; then
    echo "❌ curl is required but not installed"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "❌ jq is required but not installed. Please install jq for JSON parsing"
    exit 1
fi

# Check for required environment variables
if [ -z "$ADMIN_EMAIL" ] || [ -z "$ADMIN_PASSWORD" ]; then
    echo "❌ ADMIN_EMAIL and ADMIN_PASSWORD environment variables must be set"
    exit 1
fi

# Helper function to parse HTTP response
parse_http_response() {
    local response="$1"
    HTTP_CODE="${response: -3}"
    RESPONSE_BODY="${response%???}"
}

# Helper function to test API endpoint
test_api_endpoint() {
    local endpoint="$1"
    local expected_field="$2"
    local test_name="$3"
    
    echo "Testing $test_name..."
    RESPONSE=$(curl -s -w "%{http_code}" -X GET "$API_BASE_URL$endpoint" \
      -H "Authorization: Bearer $TOKEN")
    
    if [ $? -ne 0 ]; then
        echo "❌ curl request failed for $test_name"
        return 1
    fi
    
    parse_http_response "$RESPONSE"
    
    if [ "$HTTP_CODE" = "200" ] && echo "$RESPONSE_BODY" | jq -e ".$expected_field" > /dev/null; then
        echo "✅ $test_name working"
        return 0
    else
        echo "❌ $test_name failed (HTTP $HTTP_CODE)"
        echo "   Response: $RESPONSE_BODY"
        return 1
    fi
}

# Get authentication token once
echo "🔄 Authenticating..."
LOGIN_RESPONSE=$(curl -s -w "%{http_code}" -X POST "$API_BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASSWORD\"}")

if [ $? -ne 0 ]; then
    echo "❌ curl request failed for authentication"
    exit 1
fi

parse_http_response "$LOGIN_RESPONSE"

if [ "$HTTP_CODE" != "200" ]; then
    echo "❌ Authentication failed with HTTP status $HTTP_CODE"
    echo "   Response: $RESPONSE_BODY"
    exit 1
fi

TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.token // empty')

if [ -z "$TOKEN" ]; then
    echo "❌ No token received in response"
    exit 1
fi

echo "✅ Authentication successful"

# Test API endpoints with filters
echo "🔄 Testing Bugs API with filters..."

# Test bugs with status filter
test_api_endpoint "/api/protected/bugs?status=open" "bugs" "Bugs API with status filter"

# Test projects with search
test_api_endpoint "/api/protected/projects?search=OWASP" "projects" "Projects API with search"

# Test repositories with filters
test_api_endpoint "/api/protected/repositories?status=active" "repositories" "Repositories API with filters"

echo ""
echo "🎉 Filter testing complete!"
echo ""
echo "If all tests passed, the filters should work in the frontend."
echo "If any tests failed, there might be an issue with the API endpoints."

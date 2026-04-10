#!/bin/bash
set -e
BASE_URL="${BASE_URL:-http://localhost:8000}"
echo "Running smoke tests against $BASE_URL..."

# 1. Health check
echo "1. Health check..."
curl -f -s "$BASE_URL/health" > /dev/null && echo "   PASS" || (echo "   FAIL: /health" && exit 1)

# 2. Login
echo "2. Login..."
TOKEN=$(curl -sf -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${SMOKE_TEST_USER:-dev_admin}&password=${SMOKE_TEST_PASS:-changeme_local_only}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
[ -n "$TOKEN" ] && echo "   PASS" || (echo "   FAIL: login returned no token" && exit 1)

# 3. Student list non-empty
echo "3. Student list..."
COUNT=$(curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/students?limit=1" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('total', 0))")
[ "$COUNT" -gt 0 ] && echo "   PASS ($COUNT students)" || echo "   WARN: student list is empty"

echo "All smoke tests passed."

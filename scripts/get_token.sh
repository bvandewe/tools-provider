TOKEN=$(curl -s -X POST "http://localhost:8041/realms/tools-provider/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=tools-provider-public" \
  -d "username=admin" \
  -d "password=test" | jq -r '.access_token')
  echo $TOKEN

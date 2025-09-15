import requests
API="http://localhost:5000"
H={"X-User-Id":"U123"}
requests.post(f"{API}/auth/login", json={"userId":"U123","name":"Demo User"})
print("Seeded demo user U123")

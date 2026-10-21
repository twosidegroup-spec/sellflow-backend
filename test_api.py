import requests

url = "https://sellflow-backend-0nyn.onrender.com/api/v1/auth/register"
data = {
    "email": "test@example.com",
    "full_name": "Test User",
    "phone": "1234567890",
    "business_name": "Test Business",
    "password": "1234"
}

try:
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

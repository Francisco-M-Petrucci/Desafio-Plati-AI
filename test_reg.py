import requests

payload = {
    "first_name": "samename",
    "username": "samename",
    "password": "password",
    "appliances": ["oven"],
    "restrictions": [],
    "ingredients": ["tomato"]
}

response = requests.post("http://127.0.0.1:8000/api/auth/register", json=payload)
print(response.status_code)
print(response.text)

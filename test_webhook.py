import requests

# Assuming your Flask server expects webhooks at this endpoint
webhook_url = "http://localhost:5000/api/log-webhook" 

payload = {
    "event": "hackathon.test",
    "status": "success",
    "project": "Endpoint Hero"
}
headers = {
    "Content-Type": "application/json",
    "X-Webhook-Source": "TestScript"
}

print(f"Sending webhook payload to {webhook_url}...")

try:
    response = requests.post(webhook_url, json=payload, headers=headers)
    print(f"Done! Server responded with status code: {response.status_code}")
except Exception as e:
    print(f"❌ Connection failed: {e}")
import os
import requests

BASE_URL = "https://api.paystack.co"

class PaystackError(RuntimeError):
    pass

def _headers():
    key = os.getenv("PAYSTACK_SECRET_KEY")
    if not key:
        raise PaystackError("PAYSTACK_SECRET_KEY is not configured")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

def initialize_payment(email, amount_naira, reference, callback_url=None):
    payload = {
        "email": email,
        "amount": int(round(amount_naira * 100)),
        "reference": reference,
        "currency": "NGN",
    }
    if callback_url:
        payload["callback_url"] = callback_url
    response = requests.post(f"{BASE_URL}/transaction/initialize", json=payload, headers=_headers(), timeout=15)
    data = response.json()
    if response.status_code >= 400 or not data.get("status"):
        raise PaystackError(data.get("message", "Unable to initialize payment"))
    return data["data"]

def verify_payment(reference):
    response = requests.get(f"{BASE_URL}/transaction/verify/{reference}", headers=_headers(), timeout=15)
    data = response.json()
    if response.status_code >= 400 or not data.get("status"):
        raise PaystackError(data.get("message", "Unable to verify payment"))
    return data["data"]

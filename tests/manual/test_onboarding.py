
import requests
import json

BASE_URL = "http://localhost:8001/api/ferwafa"

def get_token():
    login_url = "http://localhost:8001/api/auth/login"
    data = {"username": "admin@ferwafa.rw", "password": "admin123"}
    try:
        resp = requests.post(login_url, data=data)
        if resp.status_code == 200:
            return resp.json()["access_token"]
        return None
    except:
        return None

def test_onboard():
    token = get_token()
    if not token: return

    headers = {"Authorization": f"Bearer {token}"}
    
    # We want to TEST ROLLBACK
    # Institution code is NEW, but Admin Email ALREADY EXISTS (hq@ferwafa.rw)
    params = {
        "name": "Test Academy Rollback",
        "type": "academy",
        "code": "ROLLBACK-03",
        "admin_email": "hq@ferwafa.rw",
        "admin_name": "Rollback Test",
        "admin_pass": "pass123",
        "stadium_name": "Rollback Stadium",
        "province": "Test Prov",
        "district": "Test Dist",
        "sector": "Test Sect",
        "cell": "Test Cell",
        "contact": "0000000000",
        "capacity": 1000
    }

    print("Testing onboarding (Expecting failure/rollback)...")
    resp = requests.post(f"{BASE_URL}/onboard/full-node", json=params, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")

if __name__ == "__main__":
    test_onboard()

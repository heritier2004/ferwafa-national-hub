import requests
import json

BASE_URL = "http://localhost:8000"

def test_onboard():
    # 1. Login as FERWAFA
    login_resp = requests.post(f"{BASE_URL}/token", data={
        "username": "ferwafa@gov.rw", # Assuming this exists from seed
        "password": "FERWAFA_ADMIN_PASS"
    })
    if login_resp.status_code != 200:
        print("Login failed")
        return
    
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Onboard new institution
    inst_name = f"Test Club {requests.utils.quote('123')}"
    code = f"TEST-{requests.utils.quote('123')}"
    admin_email = f"testadmin_{requests.utils.quote('123')}@test.com"
    
    url = f"{BASE_URL}/api/ferwafa/onboard/full-node"
    params = {
        "name": "Test Club",
        "type": "club",
        "code": "TESTCODE1",
        "admin_email": "testadmin@club.com",
        "admin_name": "OFFICIAL",
        "admin_pass": "pass123",
        "stadium_name": "Test Stadium",
        "province": "Kigali City",
        "district": "Gasabo",
        "sector": "Remera",
        "cell": "Cell1",
        "contact": "0780000000"
    }
    
    print(f"Attempting to onboard with params: {params}")
    resp = requests.post(url, params=params, headers=headers)
    print(f"Onboard Status: {resp.status_code}")
    print(f"Onboard Response: {resp.text}")
    
    # 3. Check if it appears in list
    list_resp = requests.get(f"{BASE_URL}/api/ferwafa/entities/all", headers=headers)
    entities = list_resp.json()
    found = any(e["code"] == "TESTCODE1" for e in entities)
    print(f"Found in list: {found}")
    
    if not found:
        print("BUG REPRODUCED: Institution not found in list after onboarding.")
    else:
        print("Institution successfully found in list.")

if __name__ == "__main__":
    test_onboard()

"""
FERWAFA NATIONAL INTELLIGENCE SYSTEM - FULL END-TO-END TEST
Tests every endpoint, every database table, fixes issues.
"""
import requests
import json
import sys
import time

BASE = "http://127.0.0.1:8001"
PASS = 0
FAIL = 0
FIXES = []

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} -- {detail}")
    return condition

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ============================================================
# 1. HEALTH CHECK
# ============================================================
section("1. SERVER HEALTH")
try:
    r = requests.get(f"{BASE}/", timeout=5)
    test("Backend is reachable", r.status_code == 200)
except:
    print("  [FATAL] Cannot reach backend at localhost:8001. Is it running?")
    sys.exit(1)

# ============================================================
# 2. AUTH - LOGIN AS CLUB
# ============================================================
section("2. AUTH - CLUB LOGIN")
r = requests.post(f"{BASE}/api/auth/login", data={"username": "club@ferwafa.rw", "password": "club123"})
test("Club login returns 200", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")
if r.status_code == 200:
    login_data = r.json()
    TOKEN = login_data.get("access_token")
    test("Access token received", TOKEN is not None)
    test("Role is CLUB", login_data.get("role") == "CLUB")
    test("Full name present", login_data.get("full_name") == "Amavubi Club Manager")
    HEADERS = {"Authorization": f"Bearer {TOKEN}"}
else:
    print("  [FATAL] Cannot login. Stopping.")
    sys.exit(1)

# ============================================================
# 3. AUTH - LOGIN AS FERWAFA
# ============================================================
section("3. AUTH - FERWAFA LOGIN")
r = requests.post(f"{BASE}/api/auth/login", data={"username": "hq@ferwafa.rw", "password": "ferwafa123"})
test("FERWAFA login returns 200", r.status_code == 200, f"Got {r.status_code}")
if r.status_code == 200:
    fw = r.json()
    test("Role is FERWAFA", fw.get("role") == "FERWAFA")

# ============================================================
# 4. AUTH - LOGIN AS SUPER ADMIN
# ============================================================
section("4. AUTH - SUPER ADMIN LOGIN")
r = requests.post(f"{BASE}/api/auth/login", data={"username": "admin@ferwafa.rw", "password": "admin123"})
test("Admin login returns 200", r.status_code == 200, f"Got {r.status_code}")
if r.status_code == 200:
    ad = r.json()
    test("Role is SUPER_ADMIN", ad.get("role") == "SUPER_ADMIN")
    ADMIN_HEADERS = {"Authorization": f"Bearer {ad.get('access_token')}"}

# ============================================================
# 5. FERWAFA ENDPOINTS
# ============================================================
section("5. FERWAFA - ENTITIES")
r = requests.get(f"{BASE}/api/ferwafa/entities/all", headers=HEADERS)
test("GET /api/ferwafa/entities/all returns 200", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")
if r.status_code == 200:
    entities = r.json()
    test("Entities list is not empty", len(entities) > 0, f"Got {len(entities)} entities")
    apr_found = any(e.get("code") == "APR" for e in entities)
    test("APR FC found in entities", apr_found)
    print(f"    -> Found {len(entities)} institutions")

# ============================================================
# 6. MATCH CREATION (THE CORE TEST)
# ============================================================
section("6. MATCH - CREATE NEW SESSION")
import base64
payload_part = TOKEN.split('.')[1]
payload_part += "=" * ((4 - len(payload_part) % 4) % 4)
payload = json.loads(base64.b64decode(payload_part).decode('utf-8'))
INSTITUTION_ID = payload.get("institution_id")

match_payload = {
    "institution_id": INSTITUTION_ID,
    "match_date": "2026-05-01T16:00:00",
    "venue": "Amahoro National Stadium",
    "competition_type": "Friendly",
    "opponent_name": "Police FC"
}
r = requests.post(f"{BASE}/api/match/create", json=match_payload, headers=HEADERS)
test("POST /api/match/create returns 200", r.status_code == 200, f"Got {r.status_code}: {r.text[:300]}")
if r.status_code == 200:
    match_data = r.json()
    MATCH_ID = match_data.get("match_id")
    API_KEY = match_data.get("api_key")
    MATCH_TOKEN = match_data.get("match_token")
    
    test("Match ID returned", MATCH_ID is not None)
    test("API Key generated", API_KEY is not None)
    test("Match Token generated", MATCH_TOKEN is not None)
    test("API Key format: FWFA-XXX-YYYY-ZZZZ", API_KEY.startswith("FWFA-") if API_KEY else False)
    test("Match Token format: MATCH-YYYY-XXXX", MATCH_TOKEN.startswith("MATCH-") if MATCH_TOKEN else False)
    
    print(f"    -> Match ID: {MATCH_ID}")
    print(f"    -> API Key:  {API_KEY}")
    print(f"    -> Token:    {MATCH_TOKEN}")
else:
    print("  [FATAL] Cannot create match. Stopping.")
    MATCH_ID = None

# ============================================================
# 7. LOAD MATCH SESSION
# ============================================================
if MATCH_ID:
    section("7. MATCH - LOAD SESSION")
    r = requests.get(f"{BASE}/api/match/{MATCH_ID}", headers=HEADERS)
    test("GET /api/match/{id} returns 200", r.status_code == 200, f"Got {r.status_code}: {r.text[:300]}")
    if r.status_code == 200:
        m = r.json()
        test("Home team populated", m.get("home_team") is not None, f"Got: {m.get('home_team')}")
        test("Opponent is Police FC", m.get("opponent") == "Police FC", f"Got: {m.get('opponent')}")
        test("API key matches", m.get("api_key") == API_KEY)
        test("Match token matches", m.get("match_token") == MATCH_TOKEN)
        test("Score starts at 0-0", m.get("score_home") == 0 and m.get("score_away") == 0)

# ============================================================
# 8. MATCH LIST (ALL)
# ============================================================
    section("8. MATCH - LIST ALL")
    r = requests.get(f"{BASE}/api/match/all", headers=HEADERS)
    test("GET /api/match/all returns 200", r.status_code == 200, f"Got {r.status_code}")
    if r.status_code == 200:
        matches = r.json()
        test("Matches list is not empty", len(matches) > 0)
        print(f"    -> Total matches: {len(matches)}")

# ============================================================
# 9. PLAYERS / SQUAD
# ============================================================
    section("9. SQUAD - LOAD PLAYERS")
    r = requests.get(f"{BASE}/api/match/institution/{INSTITUTION_ID}/players", headers=HEADERS)
    test("GET /api/match/institution/{id}/players returns 200", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        players = r.json()
        test("Players list is not empty", len(players) > 0, f"Got {len(players)}")
        print(f"    -> Found {len(players)} players for APR FC")
        
        # Save squad
        if len(players) >= 11:
            squad_payload = {
                "players": [
                    {"player_id": p["id"], "role": "starting", "position": "CM", "jersey_number": i+1}
                    for i, p in enumerate(players[:11])
                ]
            }
            r2 = requests.post(f"{BASE}/api/match/{MATCH_ID}/squad", json=squad_payload, headers=HEADERS)
            test("POST /api/match/{id}/squad returns 200", r2.status_code == 200, f"Got {r2.status_code}: {r2.text[:200]}")

# ============================================================
# 10. MANUAL EVENTS
# ============================================================
    section("10. EVENTS - MANUAL LOGGING")
    event_payload = {
        "event_type": "goal",
        "player_id": players[0]["id"] if players else None,
        "minute": 23,
        "team": "home",
        "description": "Manual test goal",
        "x": 95, "y": 50
    }
    r = requests.post(f"{BASE}/api/match/{MATCH_ID}/event/manual", json=event_payload, headers=HEADERS)
    test("POST manual goal event", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")

    # Yellow card
    card_payload = {
        "event_type": "yellow_card",
        "player_id": players[1]["id"] if len(players) > 1 else None,
        "minute": 35,
        "team": "home",
        "description": "Test yellow card",
        "x": 50, "y": 50
    }
    r = requests.post(f"{BASE}/api/match/{MATCH_ID}/event/manual", json=card_payload, headers=HEADERS)
    test("POST manual yellow card", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")

    # Load events
    r = requests.get(f"{BASE}/api/match/{MATCH_ID}/events", headers=HEADERS)
    test("GET /api/match/{id}/events returns 200", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        evts = r.json()
        test("Events recorded in DB", len(evts) >= 2, f"Got {len(evts)} events")
        print(f"    -> {len(evts)} events in session log")

# ============================================================
# 11. SCORE VERIFICATION
# ============================================================
    section("11. SCORE - VERIFY AFTER GOAL")
    r = requests.get(f"{BASE}/api/match/{MATCH_ID}", headers=HEADERS)
    if r.status_code == 200:
        m = r.json()
        test("Home score updated to 1", m.get("score_home") == 1, f"Got score_home={m.get('score_home')}")
        test("Away score still 0", m.get("score_away") == 0, f"Got score_away={m.get('score_away')}")
# ============================================================
# 12. SCHOOL ENDPOINTS
# ============================================================
section("12. SCHOOL ENDPOINTS")
r = requests.get(f"{BASE}/api/school/stats/1", headers=HEADERS)
test("GET /api/school/stats/1", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")

r = requests.get(f"{BASE}/api/school/players/1", headers=HEADERS)
test("GET /api/school/players/1", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")

# ============================================================
# 13. SCOUTING ENDPOINTS
# ============================================================
section("13. SCOUTING ENDPOINTS")
r = requests.get(f"{BASE}/api/scouting/top-talents", headers=HEADERS)
test("GET /api/scouting/top-talents", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")

# ============================================================
# 14. ADMIN ENDPOINTS
# ============================================================
section("14. ADMIN ENDPOINTS")
r = requests.get(f"{BASE}/api/admin/system/settings", headers=ADMIN_HEADERS)
test("GET /api/admin/system/settings", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")

r = requests.get(f"{BASE}/api/admin/users", headers=ADMIN_HEADERS)
test("GET /api/admin/users", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")
if r.status_code == 200:
    users = r.json()
    print(f"    -> Total users: {len(users)}")

r = requests.get(f"{BASE}/api/admin/errors", headers=ADMIN_HEADERS)
test("GET /api/admin/errors", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")

# ============================================================
# 15. CSV EXPORT
# ============================================================
if MATCH_ID:
    section("15. CSV EXPORT")
    r = requests.get(f"{BASE}/api/match/{MATCH_ID}/export/csv", headers=HEADERS)
    test("GET /api/match/{id}/export/csv", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")

# ============================================================
# 16. AI MACHINE CREDENTIAL VALIDATION
# ============================================================
if MATCH_ID:
    section("16. AI MACHINE - CREDENTIAL VALIDATION")
    r = requests.post(f"{BASE}/api/match/validate-ai", json={"api_key": API_KEY, "match_token": MATCH_TOKEN}, headers=HEADERS)
    test("POST /api/match/validate-ai", r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}")

# ============================================================
# FINAL REPORT
# ============================================================
print(f"\n{'='*60}")
print(f"  FINAL REPORT")
print(f"{'='*60}")
print(f"  PASSED: {PASS}")
print(f"  FAILED: {FAIL}")
print(f"  TOTAL:  {PASS + FAIL}")
print(f"  RATE:   {PASS/(PASS+FAIL)*100:.0f}%")
print(f"{'='*60}")

if FAIL == 0:
    print("  ALL SYSTEMS OPERATIONAL")
else:
    print(f"  {FAIL} ISSUE(S) NEED ATTENTION")
print(f"{'='*60}")

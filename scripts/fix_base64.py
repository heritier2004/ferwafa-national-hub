import sqlite3
import base64
from pathlib import Path

# SVGs
SVGS = {
    'PLAYER': '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
    'CLUB': '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>',
    'ACADEMY': '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>',
    'SCHOOL': '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>'
}

B64_URIS = {k: "data:image/svg+xml;base64," + base64.b64encode(v.encode('utf-8')).decode('utf-8') for k, v in SVGS.items()}

# 1. Update Database
BASE_DIR = Path(r"c:\Users\User\Documents\NEW_VERSION")
DB_PATH = BASE_DIR / "football_intelligence.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get existing rows that have the old format
players = cursor.execute("SELECT id, photo_url FROM players WHERE photo_url LIKE 'data:image/svg+xml;utf8%'").fetchall()
for pid, url in players:
    cursor.execute("UPDATE players SET photo_url = ? WHERE id = ?", (B64_URIS['PLAYER'], pid))

institutions = cursor.execute("SELECT id, logo_url, type FROM institutions WHERE logo_url LIKE 'data:image/svg+xml;utf8%'").fetchall()
for iid, url, itype in institutions:
    itype_upper = str(itype).upper()
    if itype_upper == 'CLUB': fallback = B64_URIS['CLUB']
    elif itype_upper == 'ACADEMY': fallback = B64_URIS['ACADEMY']
    elif itype_upper == 'SCHOOL': fallback = B64_URIS['SCHOOL']
    else: fallback = B64_URIS['CLUB']
    cursor.execute("UPDATE institutions SET logo_url = ? WHERE id = ?", (fallback, iid))

conn.commit()
conn.close()
print("Updated database with base64 URIs.")

# 2. Update JS files
import re

for js_file in [BASE_DIR / 'frontend/assets/js/api.js', BASE_DIR / 'frontend/assets/js/app.js']:
    if not js_file.exists(): continue
    content = js_file.read_text('utf-8')
    content = re.sub(r"'data:image/svg\+xml;utf8,[^']*PLAYER.*?'", f"'{B64_URIS['PLAYER']}'", content, flags=re.IGNORECASE)
    content = re.sub(r"'data:image/svg\+xml;utf8,[^']*ACADEMY.*?'", f"'{B64_URIS['ACADEMY']}'", content, flags=re.IGNORECASE)
    content = re.sub(r"'data:image/svg\+xml;utf8,[^']*SCHOOL.*?'", f"'{B64_URIS['SCHOOL']}'", content, flags=re.IGNORECASE)
    content = re.sub(r"'data:image/svg\+xml;utf8,[^']*CLUB.*?'", f"'{B64_URIS['CLUB']}'", content, flags=re.IGNORECASE)
    # catch the generic one at the end
    content = re.sub(r"target\.src = 'data:image/svg\+xml;utf8,[^']*'", f"target.src = '{B64_URIS['CLUB']}'", content)
    
    js_file.write_text(content, 'utf-8')
    print(f"Updated {js_file.name} with base64 URIs.")

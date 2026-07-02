import sqlite3
import os
import json
from pathlib import Path

# Base paths
BASE_DIR = Path(r"c:\Users\User\Documents\NEW_VERSION")
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOADS_DIR = FRONTEND_DIR / "assets" / "uploads"

# Database
DB_PATH = BASE_DIR / "football_intelligence.db"

# Fallback SVGs (Data URIs for safety)
FALLBACKS = {
    'PLAYER': 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
    'CLUB': 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>',
    'ACADEMY': 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>',
    'SCHOOL': 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>',
    'TEAM': 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>'
}

def normalize_path(path):
    if not path:
        return path
    # Remove duplicate slashes
    while '//' in path:
        path = path.replace('//', '/')
    # Enforce base path
    if not path.startswith('/assets/') and not path.startswith('http') and not path.startswith('data:'):
        if path.startswith('assets/'):
            path = '/' + path
        else:
            path = '/assets/uploads/' + path.lstrip('/')
    # standardizing image format handling... maybe just ensure extension?
    return path

def check_image_exists(url):
    if not url:
        return False
    if url.startswith('http') or url.startswith('data:'):
        return True # Assume reachable or data uri
    
    # It's a local path
    local_path = FRONTEND_DIR / url.lstrip('/')
    return local_path.exists()

def generate_report():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {
        'total_missing_players': 0,
        'total_broken_clubs': 0,
        'total_broken_academies': 0,
        'total_broken_schools': 0,
        'total_fixed_entries': 0,
        'total_fallback_replacements': 0
    }
    
    # Process Players
    players = cursor.execute("SELECT id, photo_url FROM players").fetchall()
    for pid, url in players:
        original = url
        norm_url = normalize_path(url)
        is_broken = not check_image_exists(norm_url)
        
        if is_broken:
            stats['total_missing_players'] += 1
            norm_url = FALLBACKS['PLAYER']
            stats['total_fallback_replacements'] += 1
            stats['total_fixed_entries'] += 1
        elif original != norm_url:
            stats['total_fixed_entries'] += 1
            
        cursor.execute("UPDATE players SET photo_url = ? WHERE id = ?", (norm_url, pid))
    
    # Process Institutions
    institutions = cursor.execute("SELECT id, logo_url, type FROM institutions").fetchall()
    for iid, url, itype in institutions:
        original = url
        norm_url = normalize_path(url)
        is_broken = not check_image_exists(norm_url)
        
        if is_broken:
            itype_upper = str(itype).upper()
            if itype_upper == 'CLUB':
                stats['total_broken_clubs'] += 1
                fallback = FALLBACKS['CLUB']
            elif itype_upper == 'ACADEMY':
                stats['total_broken_academies'] += 1
                fallback = FALLBACKS['ACADEMY']
            elif itype_upper == 'SCHOOL':
                stats['total_broken_schools'] += 1
                fallback = FALLBACKS['SCHOOL']
            else:
                stats['total_broken_clubs'] += 1
                fallback = FALLBACKS['CLUB']
            
            norm_url = fallback
            stats['total_fallback_replacements'] += 1
            stats['total_fixed_entries'] += 1
        elif original != norm_url:
            stats['total_fixed_entries'] += 1
            
        cursor.execute("UPDATE institutions SET logo_url = ? WHERE id = ?", (norm_url, iid))

    conn.commit()
    conn.close()
    
    print("=" * 40)
    print("  IMAGE INTEGRITY REPORT")
    print("=" * 40)
    print(f"Total Missing Player Images: {stats['total_missing_players']}")
    print(f"Total Broken Club Logos: {stats['total_broken_clubs']}")
    print(f"Total Broken Academy Logos: {stats['total_broken_academies']}")
    print(f"Total Broken School Logos: {stats['total_broken_schools']}")
    print("-" * 40)
    print(f"Total Fixed Entries: {stats['total_fixed_entries']}")
    print(f"Total Fallback Replacements: {stats['total_fallback_replacements']}")
    print("=" * 40)

if __name__ == '__main__':
    generate_report()

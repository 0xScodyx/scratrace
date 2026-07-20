import re
import json
import sqlite3
from pathlib import Path

from scratrace.osint.sites import _DB_PATH

def migrate_redirects_to_json():
    con = sqlite3.connect(_DB_PATH)
    cur = con.cursor()
    
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    
    pattern = re.compile(r"Redirect\('(.+?)',\s*(\[.*?\]|\d+)\)")
    
    updated = 0
    for (table,) in tables:
        rows = cur.execute(f"SELECT rowid, link, type_url FROM {table} WHERE type_url LIKE 'Redirect%'").fetchall()
        
        for rowid, link, type_url in rows:
            match = pattern.match(type_url)
            if match:
                probe = match.group(1)
                type_url_probe = match.group(2)
                
                # Превращаем в JSON
                if type_url_probe.startswith("["):
                    type_url_probe = json.loads(type_url_probe.replace("'", '"'))
                else:
                    type_url_probe = int(type_url_probe)
                
                new_type_url = json.dumps({
                    "__redirect__": True,
                    "probe": probe,
                    "type_url_probe": type_url_probe
                })
                
                cur.execute(
                    f"UPDATE {table} SET type_url = ? WHERE rowid = ?",
                    (new_type_url, rowid)
                )
                print(f"[+] Migrated {link}: {type_url} -> {new_type_url}")
                updated += 1
    
    con.commit()
    con.close()

if __name__ == "__main__":
    migrate_redirects_to_json()

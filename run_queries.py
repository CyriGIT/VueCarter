from database.database import SessionLocal
from sqlalchemy import text
from datetime import date
db = SessionLocal()

# Find MX3 presences (id_plateforme = 5)
presences = db.execute(text("""
    SELECT id_presence, id_projet, identifiant_api 
    FROM "PresenceWeb" 
    WHERE id_plateforme = 5
""")).fetchall()

print(f"DEBUG: Found {len(presences)} MX3 presences.")

# For each presence
for p in presences:
    pid = p.id_presence
    proj_id = p.id_projet
    ext_id = p.identifiant_api
    
    print("\n========================================")
    print(f"Presence ID: {pid}")
    print(f"Project ID: {proj_id}")
    print(f"External Band ID: {ext_id}")
    
    # Today's ReleveMetrique rows
    today = date.today()
    releves_today = db.execute(text("""
        SELECT type_indicateur, valeur_compteur 
        FROM "ReleveMetrique" 
        WHERE id_presence = :pid AND date_releve = :today
    """), {"pid": pid, "today": today}).fetchall()
    
    print(f"Today's ({today}) ReleveMetrique rows:")
    indicators_found = set()
    for r in releves_today:
        print(f"  - {r.type_indicateur}: {r.valeur_compteur}")
        indicators_found.add(r.type_indicateur)
        
    expected = {"Ecoutes_Cumulees", "Vues_Profil", "Playlists", "Singles_Publies"}
    all_present = expected.issubset(indicators_found)
    print(f"Are all expected 4 indicators present today? {all_present}")
    
    # Count of duplicate groups across all dates
    # A duplicate group is same (id_presence, date_releve, type_indicateur) appearing > 1 time.
    duplicates = db.execute(text("""
        SELECT date_releve, type_indicateur, COUNT(*) 
        FROM "ReleveMetrique" 
        WHERE id_presence = :pid 
        GROUP BY date_releve, type_indicateur 
        HAVING COUNT(*) > 1
    """), {"pid": pid}).fetchall()
    
    print(f"Count of duplicate groups across all dates: {len(duplicates)}")
    if duplicates:
        print("Duplicate groups details:")
        for dup in duplicates:
            print(f"  - Date: {dup[0]}, Indicator: {dup[1]} (Count: {dup[2]})")


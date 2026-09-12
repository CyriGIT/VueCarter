import os
from sqlalchemy import create_engine

# Chaîne de connexion SQLAlchemy
DB_URL = "postgresql://postgres:mysecretpassword@localhost:5433/parcours_artiste"
engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        print("Connexion à PostgreSQL réussie !")
except Exception as e:
    print(f"Erreur de connexion : {e}")
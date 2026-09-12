from datetime import date

from pydantic import BaseModel, EmailStr
from typing import Optional

# Schéma pour la validation de la création de compte
class RegisterSchema(BaseModel):
    email: EmailStr
    password: str
    nom: str
    prenom: str
    commune: str
    genre: str
    date_naissance: Optional[date] = None

# Schéma pour la connexion
class LoginSchema(BaseModel):
    email: EmailStr
    password: str

# Schéma de réponse après authentification réussie
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


# Schéma pour finaliser une invitation (le compte est créé, la Personne existe déjà)
class AcceptInvitationSchema(BaseModel):
    token: str
    password: str
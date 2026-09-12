from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr


class AccountIdentityResponse(BaseModel):
    id: int
    email: EmailStr
    displayName: str
    role: str
    personId: Optional[int] = None
    canManageEvaluations: bool = False


class PersonUpdateRequest(BaseModel):
    nom_civil: str
    prenom: str
    date_naissance: date
    genre: str
    adresse: Optional[str] = None
    npa: str
    ville: str
    canton: Optional[str] = "Neuchâtel"
    telephone: Optional[str] = None
    email: EmailStr

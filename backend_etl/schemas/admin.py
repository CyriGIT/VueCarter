from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class ActiveState(BaseModel):
    estActif: bool = True


class LegalStatusWrite(BaseModel):
    libelle: str = Field(min_length=1, max_length=100)


class LegalStatusUpdate(LegalStatusWrite, ActiveState):
    pass


class LegalStatusOut(LegalStatusUpdate):
    id: int


class PhaseTypeWrite(BaseModel):
    nom: str = Field(min_length=1, max_length=50)


class PhaseTypeUpdate(PhaseTypeWrite, ActiveState):
    pass


class PhaseTypeOut(PhaseTypeUpdate):
    id: int


class StyleWrite(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    parentId: Optional[int] = Field(default=None, gt=0)


class StyleUpdate(StyleWrite, ActiveState):
    pass


class StyleAdminOut(StyleUpdate):
    id: int


class ProgramWrite(BaseModel):
    nom: str = Field(min_length=1, max_length=150)
    organisme: Optional[str] = Field(default=None, max_length=150)


class ProgramUpdate(ProgramWrite, ActiveState):
    pass


class ProgramOut(ProgramUpdate):
    id: int


class FormationWrite(BaseModel):
    nom: str = Field(min_length=1, max_length=150)
    organisme: Optional[str] = Field(default=None, max_length=150)


class FormationUpdate(FormationWrite, ActiveState):
    pass


class FormationOut(FormationUpdate):
    id: int


class ProfessionalStructureWrite(BaseModel):
    nom: str = Field(min_length=1, max_length=150)
    type: Literal["Label", "Agence Booking", "Management", "Édition", "Studio"]
    email: Optional[EmailStr] = None
    pays: str = Field(default="Suisse", min_length=1, max_length=100)


class ProfessionalStructureUpdate(ProfessionalStructureWrite, ActiveState):
    pass


class ProfessionalStructureOut(ProfessionalStructureUpdate):
    id: int


class VenueAdminWrite(BaseModel):
    nom: str = Field(min_length=1, max_length=150)
    adresse: Optional[str] = Field(default=None, max_length=255)
    ville: str = Field(min_length=1, max_length=100)
    npa: Optional[str] = Field(default=None, max_length=20)
    pays: str = Field(min_length=1, max_length=100)
    jauge: int = Field(ge=0)
    estFestival: bool = False


class VenueAdminUpdate(VenueAdminWrite, ActiveState):
    pass


class VenueAdminOut(VenueAdminUpdate):
    id: int


class PlatformWrite(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=50)


class PlatformUpdate(PlatformWrite, ActiveState):
    pass


class PlatformOut(PlatformUpdate):
    id: int


class ExpertInvitationWrite(BaseModel):
    prenom: str = Field(min_length=1, max_length=100)
    nom: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: Literal["expert_jury", "gestionnaire_case", "accompagnant"]
    dateNaissance: date
    genre: Literal["Homme", "Femme", "Autre"]
    npa: str = Field(min_length=1, max_length=20)
    ville: str = Field(min_length=1, max_length=100)
    telephone: Optional[str] = Field(default=None, max_length=20)


class InvitationOut(BaseModel):
    personId: int
    invitationUrl: str


class ExpertRoleWrite(BaseModel):
    role: Literal["expert_jury", "gestionnaire_case", "accompagnant"]


class ExpertUpdate(ExpertInvitationWrite):
    estActif: bool = True


class ExpertOut(BaseModel):
    id: int
    prenom: str
    nom: str
    email: EmailStr
    role: Literal["expert_jury", "gestionnaire_case", "accompagnant"]
    dateNaissance: date
    genre: str
    npa: str
    ville: str
    telephone: Optional[str] = None
    statut: Literal["pending", "active", "inactive"]
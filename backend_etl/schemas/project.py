from datetime import date as Date, datetime as DateTime
from decimal import Decimal
from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, JsonValue, field_validator, model_validator


class ProjectCreateRequest(BaseModel):
    nom: str
    dateCreation: Optional[Date] = None
    langueChant: Optional[str] = "Français"
    statutJuridiqueId: Optional[int] = Field(default=None, gt=0)
    statutJuridique: Optional[str] = "Aucun"
    bioCourte: Optional[str] = None


class ProjectCreateResponse(BaseModel):
    id: int


class ProjectUpdateRequest(BaseModel):
    nom: str
    dateCreation: Date
    statutJuridiqueId: Optional[int] = Field(default=None, gt=0)
    statutJuridique: str
    suisaInscrit: bool
    hasLocal: bool
    hasFicheTechnique: bool
    hasMerch: bool
    personalPageUrl: Optional[str] = Field(default=None, max_length=2048)
    personalPageSiteName: Optional[str] = Field(default=None, max_length=100)
    objectifsCourtTerme: Optional[str] = Field(default=None, max_length=5000)
    objectifsMoyenTerme: Optional[str] = Field(default=None, max_length=5000)

    @field_validator(
        "personalPageUrl",
        "personalPageSiteName",
        "objectifsCourtTerme",
        "objectifsMoyenTerme",
    )
    @classmethod
    def strip_optional_project_text(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def validate_personal_page(self):
        if (self.personalPageUrl is None) != (self.personalPageSiteName is None):
            raise ValueError("Le nom du site et son URL doivent être renseignés ensemble.")
        if self.personalPageUrl is None:
            return self

        parsed_url = urlparse(self.personalPageUrl)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
            raise ValueError("L'URL de la page doit utiliser HTTP ou HTTPS.")
        known_hosts = {
            "Instagram": "instagram.com",
            "linktr.ee": "linktr.ee",
            "lift.bio": "lift.bio",
            "hyperfollow.com": "hyperfollow.com",
            "beacons.ai": "beacons.ai",
        }
        expected_host = known_hosts.get(self.personalPageSiteName)
        hostname = parsed_url.hostname.lower()
        if expected_host and hostname != expected_host and not hostname.endswith(f".{expected_host}"):
            raise ValueError(f"L'URL ne correspond pas au site {self.personalPageSiteName}.")
        return self


class ProjectUpdateResponse(BaseModel):
    id: int
    nom: str
    dateCreation: Date
    statutJuridiqueId: int
    statutJuridique: str
    suisaInscrit: bool
    hasLocal: bool
    hasFicheTechnique: bool
    hasMerch: bool
    personalPageUrl: Optional[str] = None
    personalPageSiteName: Optional[str] = None
    objectifsCourtTerme: Optional[str] = None
    objectifsMoyenTerme: Optional[str] = None


class AccompanimentReferenceResponse(BaseModel):
    id: int
    nom: str
    organisme: Optional[str] = None
    estActif: bool


class ProjectFormationWrite(BaseModel):
    formationId: int = Field(gt=0)
    dateSuivi: Date


class ProjectProgrammeWrite(BaseModel):
    programmeId: int = Field(gt=0)
    anneeParticipation: int = Field(ge=1900, le=2100)
    estLaureat: bool


class ProjectFormationResponse(ProjectFormationWrite):
    nom: str
    organisme: Optional[str] = None


class ProjectProgrammeResponse(ProjectProgrammeWrite):
    nom: str
    organisme: Optional[str] = None


class ProjectAccompanimentUpdateRequest(BaseModel):
    formationsSuivies: list[ProjectFormationWrite]
    programmesPrecedents: list[ProjectProgrammeWrite]

    @model_validator(mode="after")
    def reject_duplicate_accompaniment_entries(self):
        formation_keys = {(item.formationId, item.dateSuivi) for item in self.formationsSuivies}
        if len(formation_keys) != len(self.formationsSuivies):
            raise ValueError("Une même formation ne peut apparaître deux fois à la même date.")
        programme_keys = {
            (item.programmeId, item.anneeParticipation)
            for item in self.programmesPrecedents
        }
        if len(programme_keys) != len(self.programmesPrecedents):
            raise ValueError("Un même programme ne peut apparaître deux fois la même année.")
        return self


class ProjectAccompanimentUpdateResponse(BaseModel):
    formationsSuivies: list[ProjectFormationResponse]
    programmesPrecedents: list[ProjectProgrammeResponse]


class AccompanyingExpertResponse(BaseModel):
    id: int
    nom: str
    prenom: str
    email: str
    dateAffectation: Optional[DateTime] = None


class ProjectExpertAssignmentRequest(BaseModel):
    expertId: Optional[int] = Field(default=None, gt=0)


class ProjectImageUpdateRequest(BaseModel):
    url: str


class ProjectImageUpdateResponse(BaseModel):
    avatarUrl: str


class AssetTypeResponse(BaseModel):
    id: int
    libelle: str
    description: Optional[str] = None


class AssetWriteRequest(BaseModel):
    titre: str = Field(min_length=1, max_length=255)
    date: Optional[Date] = None
    typeId: Optional[int] = Field(default=None, gt=0)
    typeLibelle: Optional[str] = Field(default=None, min_length=1, max_length=100)
    url: str = Field(default="", max_length=500)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    featuredRoster: bool = False
    isJourneyEvent: bool = False
    eventSource: Optional[str] = Field(default=None, max_length=150)

    @field_validator("titre", "typeLibelle")
    @classmethod
    def strip_required_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Ce champ ne peut pas être vide.")
        return value

    @field_validator("eventSource")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() or None if value is not None else None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        parsed_url = urlparse(value)
        if value and (parsed_url.scheme not in ("http", "https") or not parsed_url.netloc):
            raise ValueError("L'URL doit utiliser HTTP ou HTTPS.")
        return value

    @model_validator(mode="after")
    def validate_asset(self):
        if (self.typeId is None) == (self.typeLibelle is None):
            raise ValueError("Indiquez soit typeId, soit typeLibelle.")
        if self.isJourneyEvent and self.date is None:
            raise ValueError("La date est obligatoire pour un événement de parcours.")
        if not self.isJourneyEvent:
            self.eventSource = None
        return self


class HighlightResponse(BaseModel):
    id: int
    type: str
    titre: str
    date: Date
    source: Optional[str] = None
    url: Optional[str] = None


class AssetResponse(BaseModel):
    id: int
    titre: str
    date: Optional[Date] = None
    typeId: int
    type: str
    metadata: dict[str, JsonValue]
    url: str
    featuredRoster: bool
    isJourneyEvent: bool
    eventId: Optional[int] = None
    eventSource: Optional[str] = None


class AssetMutationResponse(BaseModel):
    asset: AssetResponse
    highlight: Optional[HighlightResponse] = None


class AssetDeleteResponse(BaseModel):
    assetId: int
    eventId: Optional[int] = None


class TrackOriginalityUpdateRequest(BaseModel):
    estOriginal: bool


class TrackOriginalityUpdateResponse(BaseModel):
    id: int
    estOriginal: bool


class TrackDeleteResponse(BaseModel):
    trackId: int


class EvaluationUpdateRequest(BaseModel):
    campaignId: int = Field(gt=0)
    scores: dict[str, int]
    remarques: str = Field(max_length=10000)
    statut: Literal["en_attente", "selectionne", "refuse"]


class EvaluationUpdateResponse(BaseModel):
    id: int
    campaignId: int
    projectId: int
    scores: dict[str, float]
    remarques: str
    statut: Literal["en_attente", "selectionne", "refuse"]
    decisionEmailSentAt: Optional[DateTime] = None
    gridScore: Optional[float] = None
    gridCoverageCount: int
    gridCriteriaCount: int
    juryAverage: Optional[float] = None
    globalScore: Optional[float] = None
    juryCoverageCount: int
    juryCount: int
    juryNotes: list[dict]


class DecisionEmailSentResponse(BaseModel):
    decisionEmailSentAt: DateTime


class MemberAddRequest(BaseModel):
    nom: str
    prenom: str
    dateNaissance: Date
    genre: str
    npa: str
    ville: str
    email: str
    telephone: Optional[str] = None
    role: str


class MemberResponse(BaseModel):
    id: int
    nom: str
    prenom: str
    genre: str
    dateNaissance: Date
    email: str
    telephone: Optional[str] = None
    role: str
    hasAccount: bool


class VenueCreateRequest(BaseModel):
    nom: str = Field(min_length=1, max_length=150)
    adresse: Optional[str] = Field(default=None, max_length=255)
    ville: str = Field(min_length=1, max_length=100)
    npa: Optional[str] = Field(default=None, max_length=20)
    pays: str = Field(min_length=1, max_length=100)
    jauge: int = Field(ge=0)
    estFestival: bool = False


class VenueResponse(BaseModel):
    id: int
    nom: str
    adresse: Optional[str] = None
    ville: str
    npa: Optional[str] = None
    pays: str
    jauge: int
    estFestival: bool


class ConcertAddRequest(BaseModel):
    date: str
    type: Literal["Local (NE)", "Hors-Canton", "Export"]
    typeEvenement: Literal["Concert", "Résidence", "Showcase"]
    cachetBrut: Optional[Decimal] = Field(default=None, ge=0)
    venueId: Optional[int] = Field(default=None, gt=0)
    newVenue: Optional[VenueCreateRequest] = None


class ConcertResponse(BaseModel):
    id: int
    annee: int
    date: Date
    venueId: int
    lieu: str
    ville: str
    pays: str
    jauge: int
    type: str
    typeEvenement: str
    cachetBrut: Optional[Decimal] = None


class MemberInviteResponse(BaseModel):
    invitationUrl: str
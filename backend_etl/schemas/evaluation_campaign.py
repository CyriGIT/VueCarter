from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


CampaignStatus = Literal["brouillon", "ouverte", "cloturee"]


class CampaignWrite(BaseModel):
    nom: str = Field(min_length=1, max_length=150)
    statut: CampaignStatus = "brouillon"
    dateDebut: date | None = None
    dateFin: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.dateDebut and self.dateFin and self.dateFin < self.dateDebut:
            raise ValueError("La date de fin doit suivre la date de début.")
        return self


class CampaignOut(CampaignWrite):
    id: int
    dateCreation: datetime
    projectIds: list[int]
    jurorIds: list[int]


class JurorOut(BaseModel):
    id: int
    prenom: str
    nom: str
    email: str


class JuryNoteWrite(BaseModel):
    note: int = Field(ge=0, le=20)


class JuryNoteOut(BaseModel):
    expertId: int
    expertNom: str
    note: int | None
    estNotePersonnelle: bool


class CampaignEvaluationOut(BaseModel):
    campaignId: int
    projectId: int
    bilanId: int | None
    scores: dict[str, float]
    remarques: str
    statut: Literal["en_attente", "selectionne", "refuse"]
    decisionEmailSentAt: datetime | None = None
    gridScore: float | None
    gridCoverageCount: int
    gridCriteriaCount: int
    juryAverage: float | None
    globalScore: float | None
    juryCoverageCount: int
    juryCount: int
    juryNotes: list[JuryNoteOut]

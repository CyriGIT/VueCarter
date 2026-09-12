from datetime import date
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


class GrantDeadlineBase(BaseModel):
    bailleur: str = Field(min_length=1, max_length=150)
    dateProchaineSoumission: date
    urlFormulaire: str = Field(min_length=1, max_length=2048)

    @field_validator("bailleur", "urlFormulaire")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Ce champ ne peut pas être vide.")
        return stripped

    @field_validator("urlFormulaire")
    @classmethod
    def validate_form_url(cls, value: str) -> str:
        parsed_url = urlparse(value)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
            raise ValueError("Le lien du formulaire doit utiliser HTTP ou HTTPS.")
        return value


class GrantDeadlineWrite(GrantDeadlineBase):
    @model_validator(mode="after")
    def require_upcoming_date(self):
        if self.dateProchaineSoumission < date.today():
            raise ValueError("La prochaine date de dépôt ne peut pas être passée.")
        return self


class GrantDeadlineUpdate(GrantDeadlineBase):
    estActif: bool = True

    @model_validator(mode="after")
    def allow_past_date_only_for_archive(self):
        if self.estActif and self.dateProchaineSoumission < date.today():
            raise ValueError("Une échéance passée doit être archivée.")
        return self


class GrantDeadlineOut(BaseModel):
    id: int
    bailleur: str
    dateProchaineSoumission: date
    urlFormulaire: str
    estActif: bool


class GrantApplicationWrite(BaseModel):
    deadlineId: int = Field(gt=0)
    dateDepot: date

    @field_validator("dateDepot")
    @classmethod
    def reject_future_deposit(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("La date de dépôt ne peut pas être future.")
        return value


class GrantApplicationOut(BaseModel):
    deadlineId: int
    bailleur: str
    dateEcheance: date
    dateDepot: date

from typing import Literal

from pydantic import BaseModel, Field, model_validator


CriterionType = Literal["objectif", "subjectif"]
EvaluationMode = Literal["automatique", "manuel"]
ObjectiveRule = Literal[
    "projet_neuchatelois",
    "membres_18_25",
    "au_moins_un_morceau_original",
    "concert_effectue",
    "au_moins_un_morceau",
]


class EvaluationCriterionBase(BaseModel):
    nom: str = Field(min_length=1, max_length=150)
    type: CriterionType
    noteMaximale: int = Field(ge=1, le=100)
    poids: int = Field(ge=1, le=100)
    ordre: int = Field(ge=0)
    modeEvaluation: EvaluationMode
    regleObjective: ObjectiveRule | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        if self.type == "objectif" and self.modeEvaluation == "automatique":
            if self.regleObjective is None:
                raise ValueError("Un critère objectif automatique doit utiliser une règle intégrée.")
        elif self.modeEvaluation != "manuel" or self.regleObjective is not None:
            raise ValueError("Cette configuration de critère n’est pas valide.")
        return self


class EvaluationCriterionWrite(EvaluationCriterionBase):
    pass


class EvaluationCriterionUpdate(EvaluationCriterionBase):
    estActif: bool


class EvaluationCriterionOut(EvaluationCriterionBase):
    id: int
    code: str
    estActif: bool
    estUtilise: bool


class ObjectiveRuleOut(BaseModel):
    code: ObjectiveRule
    libelle: str

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend_etl.core.dependencies import get_current_user
from backend_etl.database.session import get_db
from backend_etl.models.user import Utilisateur
from backend_etl.schemas.evaluation_criterion import (
    EvaluationCriterionOut,
    EvaluationCriterionUpdate,
    EvaluationCriterionWrite,
    ObjectiveRuleOut,
)
from backend_etl.services.evaluation_criteria_service import OBJECTIVE_RULE_LABELS

router = APIRouter(prefix="/evaluation/criteria", tags=["Critères d’évaluation"])

CRITERION_COLUMNS = '''
    critere.id_critere AS id,
    critere.code_critere AS code,
    critere.nom_critere AS nom,
    critere.type_critere AS type,
    critere.note_maximale AS "noteMaximale",
    critere.poids,
    critere.ordre,
    critere.est_actif AS "estActif",
    critere.mode_evaluation AS "modeEvaluation",
    critere.regle_objective AS "regleObjective",
    EXISTS (
        SELECT 1 FROM "AppreciationExpert" appreciation
        WHERE appreciation.id_critere = critere.id_critere
    ) OR EXISTS (
        SELECT 1 FROM "CampagneCritere" campagne_critere
        WHERE campagne_critere.id_critere = critere.id_critere
    ) AS "estUtilise"
'''


def _can_manage(user: Utilisateur) -> bool:
    return user.role in ("admin", "gestionnaire_case")


def _require_manager(user: Utilisateur) -> None:
    if not _can_manage(user):
        raise HTTPException(status_code=403, detail="Accès réservé à l’administration de la grille.")


def _get_criterion(db: Session, criterion_id: int):
    return db.execute(text(f'''
        SELECT {CRITERION_COLUMNS}
        FROM "CriteresEvaluation" critere
        WHERE critere.id_critere = :id
    '''), {"id": criterion_id}).mappings().first()


@router.get("", response_model=list[EvaluationCriterionOut])
def list_evaluation_criteria(
    include_inactive: bool = Query(default=False, alias="includeInactive"),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    if current_user.role not in ("admin", "gestionnaire_case", "expert_jury", "accompagnant"):
        raise HTTPException(status_code=403, detail="Accès réservé aux équipes d’évaluation.")
    if include_inactive and not _can_manage(current_user):
        raise HTTPException(status_code=403, detail="Les critères inactifs sont réservés aux gestionnaires.")
    where = "WHERE critere.type_critere IN ('objectif', 'subjectif')"
    if not include_inactive:
        where += " AND critere.est_actif"
    return db.execute(text(f'''
        SELECT {CRITERION_COLUMNS}
        FROM "CriteresEvaluation" critere
        {where}
        ORDER BY critere.ordre, critere.id_critere
    ''')).mappings().all()


@router.get("/objective-rules", response_model=list[ObjectiveRuleOut])
def list_objective_rules(current_user: Utilisateur = Depends(get_current_user)):
    _require_manager(current_user)
    return [{"code": code, "libelle": label} for code, label in OBJECTIVE_RULE_LABELS.items()]


@router.post("", response_model=EvaluationCriterionOut, status_code=status.HTTP_201_CREATED)
def create_evaluation_criterion(
    payload: EvaluationCriterionWrite,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _require_manager(current_user)
    if payload.regleObjective:
        duplicate_rule = db.execute(text('''
            SELECT 1 FROM "CriteresEvaluation"
            WHERE regle_objective = :rule
        '''), {"rule": payload.regleObjective}).first()
        if duplicate_rule:
            raise HTTPException(status_code=409, detail="Cette règle automatique est déjà utilisée.")
    try:
        criterion_id = db.execute(text('''
            INSERT INTO "CriteresEvaluation" (
                nom_critere, code_critere, est_objectif, poids, note_maximale,
                type_critere, est_actif, ordre, mode_evaluation,
                regle_objective
            ) VALUES (
                :nom, :code, :est_objectif, :poids, :note_maximale,
                :type, TRUE, :ordre, :mode_evaluation,
                :regle_objective
            )
            RETURNING id_critere
        '''), {
            "nom": payload.nom.strip(),
            "code": f"custom_{secrets.token_hex(8)}",
            "est_objectif": payload.type == "objectif",
            "poids": payload.poids,
            "note_maximale": payload.noteMaximale,
            "type": payload.type,
            "ordre": payload.ordre,
            "mode_evaluation": payload.modeEvaluation,
            "regle_objective": payload.regleObjective,
        }).scalar_one()
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ce critère ne peut pas être créé.") from error
    return _get_criterion(db, criterion_id)


@router.patch("/{criterion_id}", response_model=EvaluationCriterionOut)
def update_evaluation_criterion(
    criterion_id: int,
    payload: EvaluationCriterionUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _require_manager(current_user)
    current = _get_criterion(db, criterion_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Critère introuvable.")
    if current["estUtilise"] and any((
        current["type"] != payload.type,
        current["noteMaximale"] != payload.noteMaximale,
        current["poids"] != payload.poids,
        current["modeEvaluation"] != payload.modeEvaluation,
        current["regleObjective"] != payload.regleObjective,
    )):
        raise HTTPException(status_code=409, detail="Un critère déjà noté ne peut changer que de nom, d’ordre ou d’état.")
    if payload.regleObjective:
        duplicate_rule = db.execute(text('''
            SELECT 1 FROM "CriteresEvaluation"
            WHERE regle_objective = :rule AND id_critere <> :id
        '''), {"rule": payload.regleObjective, "id": criterion_id}).first()
        if duplicate_rule:
            raise HTTPException(status_code=409, detail="Cette règle automatique est déjà utilisée.")
    try:
        db.execute(text('''
            UPDATE "CriteresEvaluation"
            SET nom_critere = :nom, est_objectif = :est_objectif,
                poids = :poids, note_maximale = :note_maximale,
                type_critere = :type, est_actif = :est_actif, ordre = :ordre,
                mode_evaluation = :mode_evaluation,
                regle_objective = :regle_objective
            WHERE id_critere = :id
        '''), {
            "id": criterion_id,
            "nom": payload.nom.strip(),
            "est_objectif": payload.type == "objectif",
            "poids": payload.poids,
            "note_maximale": payload.noteMaximale,
            "type": payload.type,
            "est_actif": payload.estActif,
            "ordre": payload.ordre,
            "mode_evaluation": payload.modeEvaluation,
            "regle_objective": payload.regleObjective,
        })
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ce critère ne peut pas être modifié.") from error
    return _get_criterion(db, criterion_id)

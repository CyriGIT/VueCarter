from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend_etl.core.dependencies import get_current_user, require_grant_manager
from backend_etl.database.session import get_db
from backend_etl.models.user import Utilisateur
from backend_etl.schemas.grant_deadline import (
    GrantApplicationOut,
    GrantApplicationWrite,
    GrantDeadlineOut,
    GrantDeadlineUpdate,
    GrantDeadlineWrite,
)

router = APIRouter(prefix="/grant-deadlines", tags=["Échéances de subvention"])

GRANT_DEADLINE_COLUMNS = '''
    id_echeance AS id,
    bailleur,
    date_prochaine_soumission AS "dateProchaineSoumission",
    url_formulaire AS "urlFormulaire",
    est_actif AS "estActif"
'''


def _write_deadline(db: Session, statement: str, params: dict, not_found: str | None = None):
    try:
        row = db.execute(text(statement), params).mappings().first()
        if row is None and not_found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found)
        db.commit()
        return dict(row)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une échéance existe déjà pour ce bailleur à cette date.",
        ) from error


def _require_artist_project(db: Session, current_user: Utilisateur, project_id: int) -> None:
    if current_user.role != "artiste" or current_user.id_personne is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un artiste membre du projet peut déclarer une demande.",
        )
    membership = db.execute(text('''
        SELECT 1
        FROM "MembreProjet"
        WHERE id_projet = :project_id
          AND id_personne = :person_id
          AND date_depart IS NULL
    '''), {"project_id": project_id, "person_id": current_user.id_personne}).first()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce projet ne vous appartient pas.",
        )


@router.get("", response_model=list[GrantDeadlineOut])
def list_upcoming_grant_deadlines(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    return db.execute(text(f'''
        SELECT {GRANT_DEADLINE_COLUMNS}
        FROM "EcheanceSubvention"
        WHERE est_actif AND date_prochaine_soumission >= CURRENT_DATE
        ORDER BY date_prochaine_soumission, lower(bailleur)
    ''')).mappings().all()


@router.get("/manage", response_model=list[GrantDeadlineOut])
def list_managed_grant_deadlines(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_grant_manager),
):
    return db.execute(text(f'''
        SELECT {GRANT_DEADLINE_COLUMNS}
        FROM "EcheanceSubvention"
        ORDER BY est_actif DESC, date_prochaine_soumission DESC, lower(bailleur)
    ''')).mappings().all()


@router.post("", response_model=GrantDeadlineOut, status_code=status.HTTP_201_CREATED)
def create_grant_deadline(
    payload: GrantDeadlineWrite,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_grant_manager),
):
    return _write_deadline(db, f'''
        INSERT INTO "EcheanceSubvention" (
            bailleur, date_prochaine_soumission, url_formulaire
        ) VALUES (
            :bailleur, :dateProchaineSoumission, :urlFormulaire
        )
        RETURNING {GRANT_DEADLINE_COLUMNS}
    ''', payload.model_dump())


@router.patch("/{item_id}", response_model=GrantDeadlineOut)
def update_grant_deadline(
    item_id: int,
    payload: GrantDeadlineUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_grant_manager),
):
    return _write_deadline(db, f'''
        UPDATE "EcheanceSubvention"
        SET bailleur = :bailleur,
            date_prochaine_soumission = :dateProchaineSoumission,
            url_formulaire = :urlFormulaire,
            est_actif = :estActif
        WHERE id_echeance = :id
        RETURNING {GRANT_DEADLINE_COLUMNS}
    ''', {**payload.model_dump(), "id": item_id}, "Échéance de subvention introuvable.")


@router.post(
    "/projects/{project_id}/applications",
    response_model=GrantApplicationOut,
    status_code=status.HTTP_201_CREATED,
)
def declare_grant_application(
    project_id: int,
    payload: GrantApplicationWrite,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _require_artist_project(db, current_user, project_id)
    deadline = db.execute(text('''
        SELECT id_echeance, bailleur, date_prochaine_soumission
        FROM "EcheanceSubvention"
        WHERE id_echeance = :deadline_id
    '''), {"deadline_id": payload.deadlineId}).mappings().first()
    if deadline is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Échéance introuvable.")
    if payload.dateDepot > deadline["date_prochaine_soumission"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La date de dépôt ne peut pas être postérieure à l’échéance.",
        )
    row = db.execute(text('''
        INSERT INTO "DeclarationDemandeSubvention" (
            id_projet, id_echeance, date_depot, date_retrait
        ) VALUES (
            :project_id, :deadline_id, :deposit_date, NULL
        )
        ON CONFLICT (id_projet, id_echeance) DO UPDATE
        SET date_depot = EXCLUDED.date_depot,
            date_retrait = NULL
        RETURNING id_echeance AS "deadlineId", date_depot AS "dateDepot"
    '''), {
        "project_id": project_id,
        "deadline_id": payload.deadlineId,
        "deposit_date": payload.dateDepot,
    }).mappings().one()
    db.commit()
    return {
        **dict(row),
        "bailleur": deadline["bailleur"],
        "dateEcheance": deadline["date_prochaine_soumission"],
    }


@router.delete("/projects/{project_id}/applications/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
def withdraw_grant_application(
    project_id: int,
    deadline_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _require_artist_project(db, current_user, project_id)
    withdrawn = db.execute(text('''
        UPDATE "DeclarationDemandeSubvention"
        SET date_retrait = CURRENT_DATE
        WHERE id_projet = :project_id
          AND id_echeance = :deadline_id
          AND date_retrait IS NULL
        RETURNING id_echeance
    '''), {"project_id": project_id, "deadline_id": deadline_id}).first()
    if withdrawn is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande déclarée introuvable.")
    db.commit()

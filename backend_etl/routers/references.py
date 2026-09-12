from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend_etl.core.dependencies import get_current_user
from backend_etl.database.session import get_db
from backend_etl.models.user import Utilisateur
from backend_etl.schemas.admin import LegalStatusOut, PhaseTypeOut
from backend_etl.schemas.project import AccompanimentReferenceResponse

router = APIRouter(prefix="/references", tags=["Référentiels"])


@router.get("/legal-statuses", response_model=list[LegalStatusOut])
def get_active_legal_statuses(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    return db.execute(text('''
        SELECT id_statut_juridique AS id, libelle_statut AS libelle, est_actif AS "estActif"
        FROM "StatutJuridique"
        WHERE est_actif
        ORDER BY lower(libelle_statut)
    ''')).mappings().all()


@router.get("/phase-types", response_model=list[PhaseTypeOut])
def get_active_phase_types(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    return db.execute(text('''
        SELECT id_type_phase AS id, nom_phase AS nom, est_actif AS "estActif"
        FROM "TypePhaseProjet"
        WHERE est_actif
        ORDER BY lower(nom_phase)
    ''')).mappings().all()


@router.get("/formations", response_model=list[AccompanimentReferenceResponse])
def get_active_formations(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    return db.execute(text('''
        SELECT id_formation AS id, nom_formation AS nom,
               organisme_formateur AS organisme, est_actif AS "estActif"
        FROM "Formation"
        WHERE est_actif
        ORDER BY lower(nom_formation), lower(COALESCE(organisme_formateur, ''))
    ''')).mappings().all()


@router.get("/programs", response_model=list[AccompanimentReferenceResponse])
def get_active_programs(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    return db.execute(text('''
        SELECT id_programme AS id, nom_programme AS nom,
               organisme_organisateur AS organisme, est_actif AS "estActif"
        FROM "ProgrammeAccompagnement"
        WHERE est_actif
        ORDER BY lower(nom_programme), lower(COALESCE(organisme_organisateur, ''))
    ''')).mappings().all()
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend_etl.core.dependencies import get_current_user
from backend_etl.database.session import get_db
from backend_etl.models.user import Utilisateur
from backend_etl.schemas.evaluation_campaign import (
    CampaignEvaluationOut,
    CampaignOut,
    CampaignWrite,
    JurorOut,
    JuryNoteWrite,
)
from backend_etl.services.evaluation_service import (
    get_campaign,
    get_evaluation_summary,
    require_campaign_juror,
    require_campaign_project,
    require_mutable_campaign,
    require_open_campaign,
)

router = APIRouter(prefix="/evaluation/campaigns", tags=["Campagnes d’évaluation"])


def _require_manager(user: Utilisateur) -> None:
    if user.role not in ("admin", "gestionnaire_case"):
        raise HTTPException(status_code=403, detail="Accès réservé aux gestionnaires de campagne.")


def _campaign_rows(db: Session, where: str = "", params: dict | None = None):
    return db.execute(text(f'''
        SELECT campagne.id_campagne AS id, campagne.nom_campagne AS nom,
               campagne.statut, campagne.date_debut AS "dateDebut",
               campagne.date_fin AS "dateFin", campagne.date_creation AS "dateCreation",
               COALESCE(array_agg(DISTINCT projet.id_projet) FILTER (WHERE projet.id_projet IS NOT NULL), '{{}}') AS "projectIds",
               COALESCE(array_agg(DISTINCT jure.id_expert) FILTER (WHERE jure.id_expert IS NOT NULL), '{{}}') AS "jurorIds"
        FROM "CampagneEvaluation" campagne
        LEFT JOIN "CampagneProjet" projet ON projet.id_campagne = campagne.id_campagne
        LEFT JOIN "CampagneJure" jure ON jure.id_campagne = campagne.id_campagne
        {where}
        GROUP BY campagne.id_campagne
        ORDER BY campagne.date_creation DESC, campagne.id_campagne DESC
    '''), params or {}).mappings().all()


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    if current_user.role not in ("admin", "gestionnaire_case", "expert_jury"):
        raise HTTPException(status_code=403, detail="Accès réservé aux équipes d’évaluation.")
    if current_user.role == "expert_jury":
        if current_user.id_personne is None:
            return []
        return _campaign_rows(
            db,
            'WHERE EXISTS (SELECT 1 FROM "CampagneJure" acces WHERE acces.id_campagne = campagne.id_campagne AND acces.id_expert = :expert_id)',
            {"expert_id": current_user.id_personne},
        )
    return _campaign_rows(db)


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignWrite,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _require_manager(current_user)
    try:
        campaign_id = db.execute(text('''
            INSERT INTO "CampagneEvaluation" (nom_campagne, statut, date_debut, date_fin)
            VALUES (trim(:nom), :statut, :date_debut, :date_fin)
            RETURNING id_campagne
        '''), {
            "nom": payload.nom,
            "statut": payload.statut,
            "date_debut": payload.dateDebut,
            "date_fin": payload.dateFin,
        }).scalar_one()
        db.execute(text('''
            INSERT INTO "CampagneCritere" (id_campagne, id_critere, poids, ordre)
            SELECT :campaign_id, id_critere, poids, ordre
            FROM "CriteresEvaluation" WHERE est_actif
        '''), {"campaign_id": campaign_id})
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Une campagne de ce nom existe déjà.") from error
    return _campaign_rows(db, "WHERE campagne.id_campagne = :campaign_id", {"campaign_id": campaign_id})[0]


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: int,
    payload: CampaignWrite,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _require_manager(current_user)
    campaign = get_campaign(db, campaign_id)
    require_mutable_campaign(campaign)
    try:
        db.execute(text('''
            UPDATE "CampagneEvaluation"
            SET nom_campagne = trim(:nom), statut = :statut,
                date_debut = :date_debut, date_fin = :date_fin
            WHERE id_campagne = :campaign_id
        '''), {
            "campaign_id": campaign_id,
            "nom": payload.nom,
            "statut": payload.statut,
            "date_debut": payload.dateDebut,
            "date_fin": payload.dateFin,
        })
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cette campagne ne peut pas être modifiée.") from error
    return _campaign_rows(db, "WHERE campagne.id_campagne = :campaign_id", {"campaign_id": campaign_id})[0]


@router.put("/{campaign_id}/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def assign_project(
    campaign_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _require_manager(current_user)
    campaign = get_campaign(db, campaign_id)
    require_mutable_campaign(campaign)
    try:
        db.execute(text('''
            INSERT INTO "CampagneProjet" (id_campagne, id_projet)
            VALUES (:campaign_id, :project_id) ON CONFLICT DO NOTHING
        '''), {"campaign_id": campaign_id, "project_id": project_id})
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=404, detail="Projet introuvable.") from error


@router.delete("/{campaign_id}/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_project(
    campaign_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _require_manager(current_user)
    campaign = get_campaign(db, campaign_id)
    require_mutable_campaign(campaign)
    result = db.execute(text('''
        DELETE FROM "CampagneProjet"
        WHERE id_campagne = :campaign_id AND id_projet = :project_id
          AND NOT EXISTS (
              SELECT 1 FROM "BilanEvaluation"
              WHERE id_campagne = :campaign_id AND id_projet = :project_id
          )
    '''), {"campaign_id": campaign_id, "project_id": project_id})
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="Une évaluation existe ou le projet n’est pas affecté.")
    db.commit()


@router.get("/jurors", response_model=list[JurorOut])
def list_eligible_jurors(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _require_manager(current_user)
    return db.execute(text('''
        SELECT personne.id_personne AS id, personne.prenom,
               personne.nom_civil AS nom, compte.email
        FROM "Personne" personne
        JOIN "CompteUtilisateur" compte ON compte.id_personne = personne.id_personne
        WHERE compte.id_role = 3 AND compte.est_actif
        ORDER BY lower(personne.nom_civil), lower(personne.prenom)
    ''')).mappings().all()


@router.put("/{campaign_id}/jurors/{expert_id}", status_code=status.HTTP_204_NO_CONTENT)
def assign_juror(
    campaign_id: int,
    expert_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _require_manager(current_user)
    campaign = get_campaign(db, campaign_id)
    require_mutable_campaign(campaign)
    eligible = db.execute(text('''
        SELECT 1 FROM "CompteUtilisateur"
        WHERE id_personne = :expert_id AND id_role = 3 AND est_actif
    '''), {"expert_id": expert_id}).first()
    if eligible is None:
        raise HTTPException(status_code=422, detail="Le compte doit être un juré actif.")
    db.execute(text('''
        INSERT INTO "CampagneJure" (id_campagne, id_expert)
        VALUES (:campaign_id, :expert_id) ON CONFLICT DO NOTHING
    '''), {"campaign_id": campaign_id, "expert_id": expert_id})
    db.commit()


@router.delete("/{campaign_id}/jurors/{expert_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_juror(
    campaign_id: int,
    expert_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _require_manager(current_user)
    campaign = get_campaign(db, campaign_id)
    require_mutable_campaign(campaign)
    result = db.execute(text('''
        DELETE FROM "CampagneJure"
        WHERE id_campagne = :campaign_id AND id_expert = :expert_id
          AND NOT EXISTS (
              SELECT 1 FROM "NoteEvaluateur" note
              JOIN "BilanEvaluation" bilan ON bilan.id_bilan = note.id_bilan
              WHERE bilan.id_campagne = :campaign_id AND note.id_expert = :expert_id
          )
    '''), {"campaign_id": campaign_id, "expert_id": expert_id})
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="Une note existe ou le juré n’est pas affecté.")
    db.commit()


@router.get("/{campaign_id}/evaluations", response_model=list[CampaignEvaluationOut])
def list_campaign_evaluations(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    get_campaign(db, campaign_id)
    if current_user.role == "expert_jury":
        if current_user.id_personne is None:
            raise HTTPException(status_code=403, detail="Le compte jury doit être lié à une personne.")
        require_campaign_juror(db, campaign_id, current_user.id_personne)
    elif current_user.role not in ("admin", "gestionnaire_case"):
        raise HTTPException(status_code=403, detail="Accès réservé aux équipes d’évaluation.")
    project_ids = db.execute(text('''
        SELECT id_projet FROM "CampagneProjet"
        WHERE id_campagne = :campaign_id ORDER BY id_projet
    '''), {"campaign_id": campaign_id}).scalars().all()
    return [
        get_evaluation_summary(db, campaign_id, project_id, current_user.id_personne)
        for project_id in project_ids
    ]


@router.put(
    "/{campaign_id}/projects/{project_id}/jury-note",
    response_model=CampaignEvaluationOut,
)
def save_jury_note(
    campaign_id: int,
    project_id: int,
    payload: JuryNoteWrite,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    if current_user.role != "expert_jury" or current_user.id_personne is None:
        raise HTTPException(status_code=403, detail="Seul un juré affecté peut saisir cette note.")
    campaign = get_campaign(db, campaign_id)
    require_open_campaign(campaign)
    require_campaign_project(db, campaign_id, project_id)
    require_campaign_juror(db, campaign_id, current_user.id_personne)
    evaluation_id = db.execute(text('''
        SELECT id_bilan FROM "BilanEvaluation"
        WHERE id_campagne = :campaign_id AND id_projet = :project_id
    '''), {"campaign_id": campaign_id, "project_id": project_id}).scalar()
    if evaluation_id is None:
        category_id = db.execute(text('''
            SELECT id_categorie_actuelle FROM "ProjetMusical" WHERE id_projet = :project_id
        '''), {"project_id": project_id}).scalar()
        evaluation_id = db.execute(text('''
            INSERT INTO "BilanEvaluation" (
                id_campagne, id_projet, date_evaluation, id_categorie_obtenue
            ) VALUES (:campaign_id, :project_id, CURRENT_DATE, :category_id)
            RETURNING id_bilan
        '''), {
            "campaign_id": campaign_id,
            "project_id": project_id,
            "category_id": category_id,
        }).scalar_one()
    db.execute(text('''
        INSERT INTO "NoteEvaluateur" (id_bilan, id_expert, note)
        VALUES (:evaluation_id, :expert_id, :note)
        ON CONFLICT (id_bilan, id_expert) DO UPDATE SET
            note = EXCLUDED.note, date_saisie = CURRENT_TIMESTAMP
    '''), {
        "evaluation_id": evaluation_id,
        "expert_id": current_user.id_personne,
        "note": payload.note,
    })
    db.commit()
    return get_evaluation_summary(db, campaign_id, project_id, current_user.id_personne)
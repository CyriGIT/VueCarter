from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
import jwt
import json
from datetime import date, datetime
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from database.database import get_db
from backend_etl.routers.admin import router as admin_router
from backend_etl.routers.auth import router as auth_router
from backend_etl.routers.analytics import router as analytics_router
from backend_etl.routers.etl import router as etl_router
from backend_etl.routers.evaluation_criteria import router as evaluation_criteria_router
from backend_etl.routers.evaluation_campaigns import router as evaluation_campaigns_router
from backend_etl.routers.grant_deadlines import router as grant_deadlines_router
from backend_etl.routers.references import router as references_router
from backend_etl.routers.users import router as users_router
from backend_etl.routers.styles import router as styles_router
from backend_etl.schemas.project import (
    AssetDeleteResponse,
    AssetMutationResponse,
    AssetResponse,
    AssetTypeResponse,
    AssetWriteRequest,
    ConcertAddRequest,
    ConcertResponse,
    AccompanyingExpertResponse,
    DecisionEmailSentResponse,
    EvaluationUpdateRequest,
    EvaluationUpdateResponse,
    MemberAddRequest,
    MemberInviteResponse,
    MemberResponse,
    ProjectAccompanimentUpdateRequest,
    ProjectAccompanimentUpdateResponse,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectImageUpdateRequest,
    ProjectImageUpdateResponse,
    ProjectExpertAssignmentRequest,
    ProjectUpdateRequest,
    ProjectUpdateResponse,
    TrackDeleteResponse,
    TrackOriginalityUpdateRequest,
    TrackOriginalityUpdateResponse,
    VenueResponse,
)
from backend_etl.schemas.style import ProjectStylesUpdateRequest, StyleOut
from backend_etl.core.config import settings
from backend_etl.core.security import create_account_token
from backend_etl.services.evaluation_criteria_service import calculate_objective_rules
from backend_etl.services.evaluation_service import (
    get_campaign,
    get_evaluation_summary,
    require_campaign_project,
    require_open_campaign,
)
from backend_etl.services.asset_storage import (
    delete_managed_file,
    finalize_staged_file,
    restore_staged_file,
    stage_managed_file,
    store_upload,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

app = FastAPI()

settings.ASSET_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.ASSET_STORAGE_DIR), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(etl_router, prefix="/api")
app.include_router(evaluation_criteria_router, prefix="/api")
app.include_router(evaluation_campaigns_router, prefix="/api")
app.include_router(grant_deadlines_router, prefix="/api")
app.include_router(references_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(styles_router, prefix="/api")

def get_auth_payload(token: str = Depends(oauth2_scheme)):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalide ou expirée.",
        ) from error


def _get_project_grant_applications(db: Session, project_id: int) -> list[dict]:
        rows = db.execute(text('''
                SELECT declaration.id_echeance AS "deadlineId",
                             echeance.bailleur,
                             echeance.date_prochaine_soumission::text AS "dateEcheance",
                             declaration.date_depot::text AS "dateDepot"
                FROM "DeclarationDemandeSubvention" declaration
                JOIN "EcheanceSubvention" echeance
                    ON echeance.id_echeance = declaration.id_echeance
                WHERE declaration.id_projet = :project_id
                    AND declaration.date_retrait IS NULL
                ORDER BY declaration.date_depot DESC, lower(echeance.bailleur)
        '''), {"project_id": project_id}).mappings().all()
        return [dict(row) for row in rows]


@app.get("/api/projects")
def get_projects(
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    project_filter = ""
    params = {}
    role = auth_payload.get("role")
    if role == "artiste":
        project_filter = '''
            WHERE EXISTS (
                SELECT 1
                FROM "MembreProjet" current_member
                WHERE current_member.id_projet = p.id_projet
                  AND current_member.id_personne = :id_personne
                  AND current_member.date_depart IS NULL
            )
        '''
        params["id_personne"] = auth_payload.get("id_personne")
    elif role == "accompagnant":
        if auth_payload.get("id_personne") is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le compte accompagnant doit être lié à une personne.",
            )
        project_filter = '''
            WHERE EXISTS (
                SELECT 1
                FROM "AffectationAccompagnement" assignment
                WHERE assignment.id_projet = p.id_projet
                  AND assignment.id_expert = :id_personne
            )
        '''
        params["id_personne"] = auth_payload.get("id_personne")
    elif role == "expert_jury":
        if auth_payload.get("id_personne") is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le compte jury doit être lié à une personne.",
            )
        project_filter = '''
            WHERE EXISTS (
                SELECT 1
                FROM "CampagneProjet" campagne_projet
                JOIN "CampagneJure" campagne_jure
                  ON campagne_jure.id_campagne = campagne_projet.id_campagne
                WHERE campagne_projet.id_projet = p.id_projet
                  AND campagne_jure.id_expert = :id_personne
            )
        '''
        params["id_personne"] = auth_payload.get("id_personne")

    project_rows = db.execute(text("""
        SELECT
            p.id_projet AS id,
            p.nom_projet AS nom,
            p.bio_courte AS "bioCourte",
            p.page_personnelle_url AS "personalPageUrl",
            p.page_personnelle_nom_site AS "personalPageSiteName",
            p.objectifs_court_terme AS "objectifsCourtTerme",
            p.objectifs_moyen_terme AS "objectifsMoyenTerme",
            p.for_juridique AS commune,
            COALESCE((
                SELECT string_agg(sm.nom_style, ', ' ORDER BY ps.est_style_principal DESC, sm.nom_style)
                FROM "ProjetStyle" ps
                JOIN "StyleMusical" sm ON sm.id_style = ps.id_style
                WHERE ps.id_projet = p.id_projet
            ), 'Non renseigné') AS "genreMusical",
            p.langue_chant AS "langueChant",
            p.id_statut_juridique AS "statutJuridiqueId",
            COALESCE(statut.libelle_statut, p.statut_juridique) AS "statutJuridique",
            p.date_creation AS "dateCreation",
            p.est_inscrit_suisa AS "suisaInscrit",
            p.possede_local_repetition AS "hasLocal",
            p.possede_fiche_technique AS "hasFicheTechnique",
            p.possede_merchandising AS "hasMerch",
            p.a_contact_pro_studio AS "hasStudioContact",
            (
                EXISTS (
                    SELECT 1 FROM "SoutienFinancier" sf
                    WHERE sf.id_projet = p.id_projet
                ) OR EXISTS (
                    SELECT 1 FROM "DeclarationDemandeSubvention" declaration
                    WHERE declaration.id_projet = p.id_projet
                      AND declaration.date_retrait IS NULL
                )
            ) AS "hasDemandeSubvention",
            COALESCE((
                SELECT sp.nom_structure
                FROM "ProjetStructure" ps
                JOIN "StructureProfessionnelle" sp ON sp.id_structure = ps.id_structure
                WHERE ps.id_projet = p.id_projet AND sp.type_structure = 'Studio'
                ORDER BY ps.date_debut DESC
                LIMIT 1
            ), '') AS "mixMasterContact",
            (
                p.est_inscrit_suisa::int + p.possede_local_repetition::int +
                p.possede_fiche_technique::int + p.possede_merchandising::int +
                p.a_contact_pro_studio::int
            ) * 20 AS "readinessScore"
                FROM "ProjetMusical" p
                LEFT JOIN "StatutJuridique" statut
                    ON statut.id_statut_juridique = p.id_statut_juridique
    """ + project_filter + """
        ORDER BY p.id_projet
    """), params).mappings().all()

    project_ids = [project["id"] for project in project_rows]
    audience_metrics_by_project: dict[int, list[dict]] = {project_id: [] for project_id in project_ids}
    projects = []
    if project_ids:
        audience_metric_rows = db.execute(
            text('''
                WITH audience_metrics AS (
                    SELECT pw.id_projet,
                           pl.nom_plateforme AS platform,
                           rm.type_indicateur AS type,
                           rm.valeur_compteur AS value,
                           rm.date_releve
                    FROM "ReleveMetrique" rm
                    JOIN "PresenceWeb" pw ON pw.id_presence = rm.id_presence
                    JOIN "Plateforme" pl ON pl.id_plateforme = pw.id_plateforme
                    WHERE pw.id_projet IN :project_ids
                      AND rm.type_indicateur IN (
                          'Followers', 'Abonnes', 'Ecoutes_Mensuelles',
                          'Ecoutes_Cumulees', 'Vues_Profil'
                      )
                ), latest_dates AS (
                    SELECT id_projet, MAX(date_releve) AS latest_date
                    FROM audience_metrics
                    GROUP BY id_projet
                )
                SELECT metrics.id_projet,
                       metrics.platform,
                       metrics.type,
                       metrics.value,
                       metrics.date_releve::text AS date
                FROM audience_metrics metrics
                JOIN latest_dates latest
                  ON latest.id_projet = metrics.id_projet
                 AND latest.latest_date = metrics.date_releve
                ORDER BY metrics.id_projet, metrics.platform, metrics.type
            ''').bindparams(bindparam("project_ids", expanding=True)),
            {"project_ids": project_ids},
        ).mappings().all()
        for metric in audience_metric_rows:
            audience_metrics_by_project[metric["id_projet"]].append({
                "platform": metric["platform"],
                "type": metric["type"],
                "value": metric["value"],
                "date": metric["date"],
            })

        automatic_criteria = db.execute(text('''
                SELECT code_critere, regle_objective
                FROM "CriteresEvaluation"
                WHERE est_actif AND type_critere = 'objectif'
                    AND mode_evaluation = 'automatique'
        ''')).mappings().all()

    for project_row in project_rows:
        project_id = project_row["id"]
        members = db.execute(text('''
            SELECT pe.id_personne AS id, pe.nom_civil AS nom, pe.prenom,
                   pe.genre, pe.date_naissance AS "dateNaissance", pe.email,
                   pe.telephone, mp.role_dans_groupe AS role,
                   EXISTS(
                       SELECT 1 FROM "CompteUtilisateur" cu WHERE cu.id_personne = pe.id_personne
                   ) AS "hasAccount"
            FROM "MembreProjet" mp
            JOIN "Personne" pe ON pe.id_personne = mp.id_personne
            WHERE mp.id_projet = :project_id AND mp.date_depart IS NULL
            ORDER BY pe.nom_civil, pe.prenom
        '''), {"project_id": project_id}).mappings().all()

        styles = db.execute(text('''
            SELECT sm.id_style AS id, sm.nom_style AS nom, ps.est_style_principal AS principal
            FROM "ProjetStyle" ps
            JOIN "StyleMusical" sm ON sm.id_style = ps.id_style
            WHERE ps.id_projet = :project_id
            ORDER BY ps.est_style_principal DESC, sm.nom_style
        '''), {"project_id": project_id}).mappings().all()

        tracks = db.execute(text('''
            SELECT m.id_morceau AS id, m.titre_morceau AS titre,
                   duree::text AS duree, annee_composition AS "dateCreation",
                   code_isrc AS isrc, TRUE AS "hasAudio",
                   NOT m.est_reprise AS "estOriginal"
            FROM "Morceau" m
            WHERE m.id_projet = :project_id
            ORDER BY id_morceau
        '''), {"project_id": project_id}).mappings().all()

        assets = db.execute(text('''
            SELECT a.id_asset AS id, a.titre, a.date_creation AS date,
                   ta.id_type AS "typeId", ta.libelle AS type,
                   COALESCE(a.metadonnees, '{}'::jsonb) AS metadata,
                   COALESCE(a.chemin_stockage, '') AS url,
                   COALESCE(a.est_featured_roster, FALSE) AS "featuredRoster",
                   (ep.id_evenement IS NOT NULL) AS "isJourneyEvent",
                   ep.id_evenement AS "eventId", ep.media_source AS "eventSource"
            FROM "Asset" a
            JOIN "TypeAsset" ta ON ta.id_type = a.id_type
            LEFT JOIN "EvenementParcours" ep ON ep.id_asset = a.id_asset
            WHERE a.id_projet = :project_id
            ORDER BY a.date_creation NULLS LAST, a.id_asset
        '''), {"project_id": project_id}).mappings().all()

        concerts = db.execute(text('''
            SELECT c.id_concert AS id, EXTRACT(YEAR FROM c.date_heure)::int AS annee,
                                     c.date_heure::date AS date, v.id_venue AS "venueId",
                                     v.nom_venue AS lieu, v.ville,
                   v.pays, v.valeur_pairs AS jauge,
                                     c.type_evenement AS "typeEvenement",
                                     c.cachet_brut AS "cachetBrut",
                   CASE c.zone_geographique
                     WHEN 'Local/Neuchâtel' THEN 'Local (NE)'
                     WHEN 'Hors Canton' THEN 'Hors-Canton'
                     ELSE 'Export'
                   END AS type
            FROM "Concert" c
            JOIN "Venue" v ON v.id_venue = c.id_venue
            WHERE c.id_projet = :project_id
            ORDER BY c.date_heure
        '''), {"project_id": project_id}).mappings().all()

        highlights = db.execute(text('''
             SELECT id_evenement AS id, type_evenement AS type, titre_evenement AS titre,
                 date_evenement::text AS date, media_source AS source, url_preuve AS url
            FROM "EvenementParcours"
            WHERE id_projet = :project_id
            ORDER BY date_evenement DESC
        '''), {"project_id": project_id}).mappings().all()

        programs = db.execute(text('''
            SELECT pa.id_programme AS "programmeId", pa.nom_programme AS nom,
                   pa.organisme_organisateur AS organisme,
                   sa.annee_participation AS "anneeParticipation",
                   COALESCE(sa.est_laureat, TRUE) AS "estLaureat"
            FROM "SuiviAccompagnement" sa
            JOIN "ProgrammeAccompagnement" pa ON pa.id_programme = sa.id_programme
            WHERE sa.id_projet = :project_id
            ORDER BY sa.annee_participation DESC, lower(pa.nom_programme)
        '''), {"project_id": project_id}).mappings().all()

        formations = db.execute(text('''
            SELECT f.id_formation AS "formationId", f.nom_formation AS nom,
                   f.organisme_formateur AS organisme,
                   pf.date_suivi::text AS "dateSuivi"
            FROM "ProjetFormation" pf
            JOIN "Formation" f ON f.id_formation = pf.id_formation
            WHERE pf.id_projet = :project_id
            ORDER BY pf.date_suivi DESC, lower(f.nom_formation)
        '''), {"project_id": project_id}).mappings().all()

        evaluation = db.execute(text('''
            SELECT be.id_bilan, be.remarques, be.statut_selection, be.decision_email_sent_at
            FROM "BilanEvaluation" be
            WHERE be.id_projet = :project_id
            ORDER BY be.date_evaluation DESC, be.id_bilan DESC
            LIMIT 1
        '''), {"project_id": project_id}).mappings().first()

        evaluation_scores = None
        if evaluation:
            score_rows = db.execute(text('''
                SELECT ce.code_critere, AVG(ae.note)::float AS note
                FROM "AppreciationExpert" ae
                JOIN "CriteresEvaluation" ce ON ce.id_critere = ae.id_critere
                WHERE ae.id_bilan = :evaluation_id
                GROUP BY ce.id_critere, ce.code_critere
            '''), {"evaluation_id": evaluation["id_bilan"]}).mappings().all()
            evaluation_scores = {
                row["code_critere"]: row["note"]
                for row in score_rows
                if row["code_critere"]
            }

        if automatic_criteria:
            objective_values = calculate_objective_rules(db, project_id)
            evaluation_scores = evaluation_scores or {}
            for criterion in automatic_criteria:
                evaluation_scores.setdefault(
                    criterion["code_critere"],
                    objective_values[criterion["regle_objective"]],
                )

        avatar_url = db.execute(text('''
            SELECT a.chemin_stockage
            FROM "Asset" a
            JOIN "TypeAsset" ta ON ta.id_type = a.id_type
            WHERE a.id_projet = :project_id AND ta.libelle = 'Image'
            ORDER BY a.id_asset DESC
            LIMIT 1
        '''), {"project_id": project_id}).scalar()

        project = dict(project_row)
        accompanying_expert = db.execute(text('''
            SELECT personne.id_personne AS id,
                   personne.nom_civil AS nom,
                   personne.prenom,
                   compte.email,
                   affectation.date_affectation AS "dateAffectation"
            FROM "AffectationAccompagnement" affectation
            JOIN "Personne" personne ON personne.id_personne = affectation.id_expert
            JOIN "CompteUtilisateur" compte ON compte.id_personne = personne.id_personne
            WHERE affectation.id_projet = :project_id
        '''), {"project_id": project_id}).mappings().first()
        project.update({
            "avatarUrl": avatar_url or "",
            "pitchAccroche": None,
            "bioComplete": project["bioCourte"] or "",
            "formationsSuivies": [dict(formation) for formation in formations],
            "programmesPrecedents": [dict(program) for program in programs],
            "grantApplications": _get_project_grant_applications(db, project_id),
            "residencesCount": sum(1 for concert in concerts if concert["typeEvenement"] == "Résidence"),
            "instaFollowers": "N/A",
            "audienceMetrics": audience_metrics_by_project[project_id],
            "members": [dict(member) for member in members],
            "styles": [dict(style) for style in styles],
            "tracks": [dict(track) for track in tracks],
            "assets": [dict(asset) for asset in assets],
            "concerts": [dict(concert) for concert in concerts],
            "highlights": [dict(highlight) for highlight in highlights],
            "scores": evaluation_scores,
            "remarquesEvaluation": evaluation["remarques"] if evaluation else None,
            "statutSelection": evaluation["statut_selection"] if evaluation else "en_attente",
            "decisionEmailSentAt": evaluation["decision_email_sent_at"] if evaluation else None,
            "accompanyingExpert": dict(accompanying_expert) if accompanying_expert else None,
        })
        projects.append(project)

    return projects


@app.get("/api/accompanying-experts", response_model=list[AccompanyingExpertResponse])
def list_accompanying_experts(
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    if auth_payload.get("role") != "gestionnaire_case":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le gestionnaire Case peut consulter les accompagnants disponibles.",
        )
    rows = db.execute(text('''
        SELECT personne.id_personne AS id,
               personne.nom_civil AS nom,
               personne.prenom,
               compte.email
        FROM "Personne" personne
        JOIN "CompteUtilisateur" compte ON compte.id_personne = personne.id_personne
        JOIN "RoleUtilisateur" role ON role.id_role = compte.id_role
        WHERE personne.est_expert
          AND compte.est_actif
          AND lower(role.libelle_role) IN ('gestionnaire_case', 'expert_jury', 'accompagnant')
        ORDER BY personne.nom_civil, personne.prenom
    ''')).mappings().all()
    return [dict(row) for row in rows]


@app.put(
    "/api/projects/{project_id}/accompanying-expert",
    response_model=AccompanyingExpertResponse | None,
)
def assign_accompanying_expert(
    project_id: int,
    payload: ProjectExpertAssignmentRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    if auth_payload.get("role") != "gestionnaire_case":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le gestionnaire Case peut affecter un accompagnant.",
        )
    selection_status = db.execute(text('''
        SELECT statut_selection
        FROM "BilanEvaluation"
        WHERE id_projet = :project_id
        ORDER BY date_evaluation DESC, id_bilan DESC
        LIMIT 1
    '''), {"project_id": project_id}).scalar()
    if selection_status is None:
        project_exists = db.execute(
            text('SELECT 1 FROM "ProjetMusical" WHERE id_projet = :project_id'),
            {"project_id": project_id},
        ).scalar()
        if project_exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")
    if selection_status != "selectionne":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un accompagnant ne peut être affecté qu’à un projet sélectionné.",
        )
    if payload.expertId is None:
        db.execute(
            text('DELETE FROM "AffectationAccompagnement" WHERE id_projet = :project_id'),
            {"project_id": project_id},
        )
        db.commit()
        return None

    expert = db.execute(text('''
        SELECT personne.id_personne AS id,
               personne.nom_civil AS nom,
               personne.prenom,
               compte.email
        FROM "Personne" personne
        JOIN "CompteUtilisateur" compte ON compte.id_personne = personne.id_personne
        JOIN "RoleUtilisateur" role ON role.id_role = compte.id_role
        WHERE personne.id_personne = :expert_id
          AND personne.est_expert
          AND compte.est_actif
          AND lower(role.libelle_role) IN ('gestionnaire_case', 'expert_jury', 'accompagnant')
    '''), {"expert_id": payload.expertId}).mappings().first()
    if expert is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="L’accompagnant doit être un expert disposant d’un compte actif.",
        )
    assigned_at = db.execute(text('''
        INSERT INTO "AffectationAccompagnement" (id_projet, id_expert)
        VALUES (:project_id, :expert_id)
        ON CONFLICT (id_projet) DO UPDATE
        SET id_expert = EXCLUDED.id_expert,
            date_affectation = CURRENT_TIMESTAMP
        RETURNING date_affectation
    '''), {"project_id": project_id, "expert_id": payload.expertId}).scalar_one()
    db.commit()
    return {**dict(expert), "dateAffectation": assigned_at}


@app.put("/api/projects/{project_id}/evaluation", response_model=EvaluationUpdateResponse)
def update_project_evaluation(
    project_id: int,
    payload: EvaluationUpdateRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    role = auth_payload.get("role")
    if role != "gestionnaire_case":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le gestionnaire Case peut enregistrer la grille générale.",
        )

    expert_id = auth_payload.get("id_personne")
    if expert_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le compte doit être lié à une personne experte pour enregistrer une évaluation.",
        )

    campaign = get_campaign(db, payload.campaignId)
    require_open_campaign(campaign)
    require_campaign_project(db, payload.campaignId, project_id)

    category_id = db.execute(
        text('SELECT id_categorie_actuelle FROM "ProjetMusical" WHERE id_projet = :project_id'),
        {"project_id": project_id},
    ).scalar()
    if category_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")

    submitted_scores = dict(payload.scores)
    criteria = db.execute(text('''
        SELECT critere.id_critere, critere.code_critere, critere.type_critere,
               critere.note_maximale, critere.mode_evaluation,
               critere.regle_objective
        FROM "CampagneCritere" campagne_critere
        JOIN "CriteresEvaluation" critere
          ON critere.id_critere = campagne_critere.id_critere
        WHERE campagne_critere.id_campagne = :campaign_id
    '''), {"campaign_id": payload.campaignId}).mappings().all()
    criteria_by_code = {row["code_critere"]: row for row in criteria}
    unknown_scores = sorted(set(submitted_scores) - set(criteria_by_code))
    if unknown_scores:
        raise HTTPException(status_code=422, detail="Un ou plusieurs critères sont inconnus ou inactifs.")

    scores: dict[str, int] = {}
    score_owners: dict[str, int] = {}
    for score_key, score in submitted_scores.items():
        criterion = criteria_by_code[score_key]
        if score < 0 or score > criterion["note_maximale"]:
            raise HTTPException(
                status_code=422,
                detail=f"La note de {score_key} doit être comprise entre 0 et {criterion['note_maximale']}.",
            )
        if criterion["mode_evaluation"] == "automatique":
            raise HTTPException(status_code=403, detail="Ce critère n’est pas saisissable manuellement.")
        scores[score_key] = score
        score_owners[score_key] = expert_id

    objective_values = calculate_objective_rules(db, project_id)
    for criterion in criteria:
        if criterion["mode_evaluation"] != "automatique":
            continue
        score_key = criterion["code_critere"]
        scores[score_key] = objective_values[criterion["regle_objective"]]
        score_owners[score_key] = expert_id

    evaluation = db.execute(text('''
        SELECT id_bilan, remarques, statut_selection, decision_email_sent_at
        FROM "BilanEvaluation"
        WHERE id_campagne = :campaign_id AND id_projet = :project_id
    '''), {"campaign_id": payload.campaignId, "project_id": project_id}).mappings().first()

    if evaluation:
        evaluation_id = evaluation["id_bilan"]
        remarks = evaluation["remarques"] or ""
        selection_status = evaluation["statut_selection"]
        decision_email_sent_at = evaluation.get("decision_email_sent_at")
        db.execute(text('''
            UPDATE "BilanEvaluation"
            SET id_categorie_obtenue = :category_id,
                remarques = :remarques,
                statut_selection = :statut,
                decision_email_sent_at = CASE
                    WHEN statut_selection IS DISTINCT FROM :statut THEN NULL
                    ELSE decision_email_sent_at
                END
            WHERE id_bilan = :evaluation_id
        '''), {
            "evaluation_id": evaluation_id,
            "category_id": category_id,
            "remarques": payload.remarques,
            "statut": payload.statut,
        })
        remarks = payload.remarques
        if selection_status != payload.statut:
            decision_email_sent_at = None
        selection_status = payload.statut
    else:
        remarks = payload.remarques
        selection_status = payload.statut
        decision_email_sent_at = None
        evaluation_id = db.execute(
            text('''
                INSERT INTO "BilanEvaluation" (
                    id_campagne, id_projet, date_evaluation, id_categorie_obtenue, remarques, statut_selection
                ) VALUES (
                    :campaign_id, :project_id, CURRENT_DATE, :category_id, :remarques, :statut
                )
                RETURNING id_bilan
            '''),
            {
                "project_id": project_id,
                "campaign_id": payload.campaignId,
                "category_id": category_id,
                "remarques": remarks,
                "statut": selection_status,
            },
        ).scalar_one()

    for score_key, owner_id in score_owners.items():
        db.execute(text('''
            INSERT INTO "AppreciationExpert" (
                id_bilan, id_expert, id_critere, note
            ) VALUES (
                :evaluation_id, :expert_id, :criterion_id, :note
            )
            ON CONFLICT (id_bilan, id_critere) DO UPDATE SET
                id_expert = EXCLUDED.id_expert,
                note = EXCLUDED.note,
                commentaire = NULL
        '''), {
            "evaluation_id": evaluation_id,
            "expert_id": owner_id,
            "criterion_id": criteria_by_code[score_key]["id_critere"],
            "note": scores[score_key],
        })

    db.commit()
    summary = get_evaluation_summary(db, payload.campaignId, project_id, expert_id)
    return {"id": evaluation_id, **summary}


@app.post(
    "/api/projects/{project_id}/evaluation/decision-email",
    response_model=DecisionEmailSentResponse,
)
def mark_decision_email_sent(
    project_id: int,
    campaign_id: int,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    if auth_payload.get("role") != "gestionnaire_case":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le gestionnaire Case peut transmettre la décision.",
        )

    evaluation = db.execute(text('''
         SELECT be.id_bilan, be.statut_selection,
             EXISTS (
                 SELECT 1
                 FROM "MembreProjet" mp
                 JOIN "Personne" personne ON personne.id_personne = mp.id_personne
                 WHERE mp.id_projet = be.id_projet
                AND mp.date_depart IS NULL
                AND length(trim(personne.email)) > 0
             ) AS has_recipients
         FROM "BilanEvaluation" be
                 WHERE be.id_projet = :project_id
                     AND be.id_campagne = :campaign_id
        '''), {"project_id": project_id, "campaign_id": campaign_id}).mappings().first()
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Enregistrez la décision avant de préparer le mail.",
        )
    if evaluation["statut_selection"] == "en_attente":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une décision doit être prise avant de préparer le mail.",
        )
    if not evaluation["has_recipients"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aucune adresse e-mail active n’est renseignée pour les membres du projet.",
        )

    sent_at = db.execute(text('''
        UPDATE "BilanEvaluation"
        SET decision_email_sent_at = CURRENT_TIMESTAMP
        WHERE id_bilan = :evaluation_id
        RETURNING decision_email_sent_at
    '''), {"evaluation_id": evaluation["id_bilan"]}).scalar_one()
    db.commit()
    return {"decisionEmailSentAt": sent_at}


def _resolve_legal_status(
    db: Session,
    status_id: int | None,
    label: str | None,
    current_status_id: int | None = None,
) -> dict:
    if status_id is not None:
        row = db.execute(text('''
            SELECT id_statut_juridique AS id, libelle_statut AS libelle
            FROM "StatutJuridique"
            WHERE id_statut_juridique = :status_id
              AND (est_actif OR id_statut_juridique = :current_status_id)
        '''), {"status_id": status_id, "current_status_id": current_status_id}).mappings().first()
    else:
        normalized_label = "Aucun" if (label or "").strip().lower() in {"aucun", "aucune", ""} else label.strip()
        row = db.execute(text('''
            SELECT id_statut_juridique AS id, libelle_statut AS libelle
            FROM "StatutJuridique"
            WHERE lower(libelle_statut) = lower(:label) AND est_actif
        '''), {"label": normalized_label}).mappings().first()
    if not row:
        raise HTTPException(status_code=422, detail="Statut juridique introuvable ou inactif.")
    return dict(row)


@app.post("/api/projects", response_model=ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    """Crée un nouveau projet musical et y rattache son créateur comme membre."""
    if auth_payload.get("role") not in ("artiste", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les artistes peuvent créer un projet musical.",
        )
    id_personne = auth_payload.get("id_personne")
    if auth_payload.get("role") == "artiste" and id_personne is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le compte artiste doit être lié à un profil personnel avant de créer un projet.",
        )

    id_categorie = db.execute(
        text('SELECT id_categorie FROM "CategorieArtiste" WHERE libelle_categorie = \'Amateur\' LIMIT 1')
    ).scalar_one()
    legal_status = _resolve_legal_status(db, payload.statutJuridiqueId, payload.statutJuridique)

    new_project = db.execute(
        text('''
            INSERT INTO "ProjetMusical" (
                nom_projet, bio_courte, langue_chant, statut_juridique,
                id_statut_juridique, date_creation, id_categorie_actuelle
            ) VALUES (
                :nom, :bio_courte, :langue_chant, :statut_juridique,
                :status_id, :date_creation, :id_categorie
            )
            RETURNING id_projet
        '''),
        {
            "nom": payload.nom,
            "bio_courte": payload.bioCourte,
            "langue_chant": payload.langueChant,
            "statut_juridique": legal_status["libelle"],
            "status_id": legal_status["id"],
            "date_creation": payload.dateCreation or date.today(),
            "id_categorie": id_categorie,
        },
    ).mappings().first()
    project_id = new_project["id_projet"]

    db.execute(
        text('''
            INSERT INTO "HistoriqueStatutJuridique" (
                id_projet, statut_juridique, id_statut_juridique, date_debut
            ) VALUES (:project_id, :statut_juridique, :status_id, CURRENT_DATE)
        '''),
        {
            "project_id": project_id,
            "statut_juridique": legal_status["libelle"],
            "status_id": legal_status["id"],
        },
    )

    if id_personne:
        db.execute(
            text('''
                INSERT INTO "MembreProjet" (id_projet, id_personne, date_arrivee, role_dans_groupe)
                VALUES (:project_id, :id_personne, CURRENT_DATE, 'Artiste principal')
            '''),
            {"project_id": project_id, "id_personne": id_personne},
        )

    db.commit()
    return ProjectCreateResponse(id=project_id)


@app.delete("/api/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    """Supprime un projet musical (les données liées suivent via ON DELETE CASCADE)."""
    if auth_payload.get("role") == "accompagnant":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès en lecture seule.")
    if auth_payload.get("role") == "artiste":
        membership = db.execute(
            text('''
                SELECT 1 FROM "MembreProjet"
                WHERE id_projet = :project_id AND id_personne = :id_personne AND date_depart IS NULL
            '''),
            {"project_id": project_id, "id_personne": auth_payload.get("id_personne")},
        ).first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce projet ne vous appartient pas.",
            )

    asset_urls = db.execute(
        text('SELECT chemin_stockage FROM "Asset" WHERE id_projet = :project_id'),
        {"project_id": project_id},
    ).scalars().all()
    staged_files = [stage_managed_file(url) for url in asset_urls]
    try:
        deleted = db.execute(
            text('DELETE FROM "ProjetMusical" WHERE id_projet = :project_id RETURNING id_projet'),
            {"project_id": project_id},
        ).first()
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")
        db.commit()
        for staged_file in staged_files:
            finalize_staged_file(staged_file)
    except Exception:
        db.rollback()
        for staged_file in staged_files:
            restore_staged_file(staged_file)
        raise


@app.put("/api/projects/{project_id}", response_model=ProjectUpdateResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    if auth_payload.get("role") == "accompagnant":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès en lecture seule.")
    if auth_payload.get("role") == "artiste":
        membership = db.execute(
            text('''
                SELECT 1 FROM "MembreProjet"
                WHERE id_projet = :project_id AND id_personne = :id_personne AND date_depart IS NULL
            '''),
            {"project_id": project_id, "id_personne": auth_payload.get("id_personne")},
        ).first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce projet ne vous appartient pas.",
            )

    current_legal_status = db.execute(
        text('''
            SELECT id_statut_juridique AS id, statut_juridique AS libelle
            FROM "ProjetMusical" WHERE id_projet = :project_id
        '''),
        {"project_id": project_id},
    ).mappings().first()
    if current_legal_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")
    legal_status = _resolve_legal_status(
        db,
        payload.statutJuridiqueId,
        payload.statutJuridique,
        current_legal_status["id"],
    )

    updated_project = db.execute(
        text('''
            UPDATE "ProjetMusical"
            SET nom_projet = :nom,
                date_creation = :date_creation,
                statut_juridique = :statut_juridique,
                id_statut_juridique = :status_id,
                est_inscrit_suisa = :suisa_inscrit,
                possede_local_repetition = :has_local,
                possede_fiche_technique = :has_fiche_technique,
                possede_merchandising = :has_merch,
                page_personnelle_url = :personal_page_url,
                page_personnelle_nom_site = :personal_page_site_name,
                objectifs_court_terme = :objectifs_court_terme,
                objectifs_moyen_terme = :objectifs_moyen_terme
            WHERE id_projet = :project_id
            RETURNING id_projet AS id, nom_projet AS nom, date_creation AS "dateCreation",
                      id_statut_juridique AS "statutJuridiqueId",
                      statut_juridique AS "statutJuridique", est_inscrit_suisa AS "suisaInscrit",
                      possede_local_repetition AS "hasLocal", possede_fiche_technique AS "hasFicheTechnique",
                      possede_merchandising AS "hasMerch",
                      page_personnelle_url AS "personalPageUrl",
                      page_personnelle_nom_site AS "personalPageSiteName",
                      objectifs_court_terme AS "objectifsCourtTerme",
                      objectifs_moyen_terme AS "objectifsMoyenTerme"
        '''),
        {
            "nom": payload.nom,
            "date_creation": payload.dateCreation,
            "statut_juridique": legal_status["libelle"],
            "status_id": legal_status["id"],
            "suisa_inscrit": payload.suisaInscrit,
            "has_local": payload.hasLocal,
            "has_fiche_technique": payload.hasFicheTechnique,
            "has_merch": payload.hasMerch,
            "personal_page_url": payload.personalPageUrl,
            "personal_page_site_name": payload.personalPageSiteName,
            "objectifs_court_terme": payload.objectifsCourtTerme,
            "objectifs_moyen_terme": payload.objectifsMoyenTerme,
            "project_id": project_id,
        },
    ).mappings().first()

    if not updated_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")

    if current_legal_status["id"] != legal_status["id"]:
        current_history_start = db.execute(
            text('''
                SELECT date_debut
                FROM "HistoriqueStatutJuridique"
                WHERE id_projet = :project_id AND date_fin IS NULL
            '''),
            {"project_id": project_id},
        ).scalar()
        if current_history_start == date.today():
            db.execute(
                text('''
                    UPDATE "HistoriqueStatutJuridique"
                    SET statut_juridique = :statut_juridique,
                        id_statut_juridique = :status_id
                    WHERE id_projet = :project_id AND date_fin IS NULL
                '''),
                {
                    "project_id": project_id,
                    "statut_juridique": legal_status["libelle"],
                    "status_id": legal_status["id"],
                },
            )
        else:
            db.execute(
                text('''
                    UPDATE "HistoriqueStatutJuridique"
                    SET date_fin = CURRENT_DATE - 1
                    WHERE id_projet = :project_id AND date_fin IS NULL
                '''),
                {"project_id": project_id},
            )
            db.execute(
                text('''
                    INSERT INTO "HistoriqueStatutJuridique" (
                        id_projet, statut_juridique, id_statut_juridique, date_debut
                    ) VALUES (:project_id, :statut_juridique, :status_id, CURRENT_DATE)
                '''),
                {
                    "project_id": project_id,
                    "statut_juridique": legal_status["libelle"],
                    "status_id": legal_status["id"],
                },
            )

    db.commit()
    return dict(updated_project)


@app.put("/api/projects/{project_id}/styles", response_model=list[StyleOut])
def update_project_styles(
    project_id: int,
    payload: ProjectStylesUpdateRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    if auth_payload.get("role") == "accompagnant":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès en lecture seule.")
    if auth_payload.get("role") == "artiste":
        membership = db.execute(
            text('''
                SELECT 1 FROM "MembreProjet"
                WHERE id_projet = :project_id AND id_personne = :id_personne AND date_depart IS NULL
            '''),
            {"project_id": project_id, "id_personne": auth_payload.get("id_personne")},
        ).first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce projet ne vous appartient pas.",
            )

    if not payload.styles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Au moins un style est requis.")

    requested_style_ids = [entry.styleId for entry in payload.styles]
    active_style_count = db.execute(
        text('''
            SELECT count(*) FROM "StyleMusical"
            WHERE id_style IN :style_ids AND est_actif
        ''').bindparams(bindparam("style_ids", expanding=True)),
        {"style_ids": requested_style_ids},
    ).scalar_one()
    if active_style_count != len(set(requested_style_ids)):
        raise HTTPException(status_code=422, detail="Un ou plusieurs styles sont introuvables ou inactifs.")

    db.execute(
        text('DELETE FROM "ProjetStyle" WHERE id_projet = :project_id'),
        {"project_id": project_id},
    )
    for entry in payload.styles:
        db.execute(
            text('''
                INSERT INTO "ProjetStyle" (id_projet, id_style, est_style_principal)
                VALUES (:project_id, :style_id, :principal)
            '''),
            {"project_id": project_id, "style_id": entry.styleId, "principal": entry.principal},
        )
    db.commit()

    styles = db.execute(
        text('''
            SELECT sm.id_style AS id, sm.nom_style AS nom, sm.id_style_parent AS "idParent",
                   ps.est_style_principal AS principal
            FROM "ProjetStyle" ps
            JOIN "StyleMusical" sm ON sm.id_style = ps.id_style
            WHERE ps.id_projet = :project_id
            ORDER BY ps.est_style_principal DESC, sm.nom_style
        '''),
        {"project_id": project_id},
    ).mappings().all()
    return [dict(style) for style in styles]


@app.put("/api/projects/{project_id}/image", response_model=ProjectImageUpdateResponse)
def update_project_image(
    project_id: int,
    payload: ProjectImageUpdateRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    """Remplace le visuel officiel du projet (stocké comme Asset de type 'Image')."""
    if auth_payload.get("role") == "accompagnant":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès en lecture seule.")
    if auth_payload.get("role") == "artiste":
        membership = db.execute(
            text('''
                SELECT 1 FROM "MembreProjet"
                WHERE id_projet = :project_id AND id_personne = :id_personne AND date_depart IS NULL
            '''),
            {"project_id": project_id, "id_personne": auth_payload.get("id_personne")},
        ).first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce projet ne vous appartient pas.",
            )

    db.execute(text('''
        INSERT INTO "TypeAsset" (libelle, description)
        VALUES ('Image', 'Visuel officiel du projet')
        ON CONFLICT DO NOTHING
    '''))
    id_type_image = db.execute(
        text('SELECT id_type FROM "TypeAsset" WHERE lower(trim(libelle)) = lower(\'Image\')')
    ).scalar_one()

    previous_urls = db.execute(
        text('SELECT chemin_stockage FROM "Asset" WHERE id_projet = :project_id AND id_type = :id_type'),
        {"project_id": project_id, "id_type": id_type_image},
    ).scalars().all()
    db.execute(
        text('DELETE FROM "Asset" WHERE id_projet = :project_id AND id_type = :id_type'),
        {"project_id": project_id, "id_type": id_type_image},
    )
    db.execute(
        text('''
            INSERT INTO "Asset" (id_projet, id_type, titre, chemin_stockage)
            VALUES (:project_id, :id_type, 'Visuel officiel', :url)
        '''),
        {"project_id": project_id, "id_type": id_type_image, "url": payload.url},
    )
    db.commit()
    for previous_url in previous_urls:
        delete_managed_file(previous_url)

    return ProjectImageUpdateResponse(avatarUrl=payload.url)


def _assert_project_owner(db: Session, auth_payload: dict, project_id: int) -> None:
    role = auth_payload.get("role")
    if role == "admin":
        return
    if role != "artiste":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès en lecture seule.")
    membership = db.execute(
        text('''
            SELECT 1 FROM "MembreProjet"
            WHERE id_projet = :project_id AND id_personne = :id_personne AND date_depart IS NULL
        '''),
        {"project_id": project_id, "id_personne": auth_payload.get("id_personne")},
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce projet ne vous appartient pas.",
        )


def _assert_asset_write_access(db: Session, auth_payload: dict, project_id: int) -> None:
    if auth_payload.get("role") not in ("artiste", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les artistes et les administrateurs peuvent gérer les assets.",
        )
    _assert_project_owner(db, auth_payload, project_id)


@app.put(
    "/api/projects/{project_id}/accompaniment",
    response_model=ProjectAccompanimentUpdateResponse,
)
def update_project_accompaniment(
    project_id: int,
    payload: ProjectAccompanimentUpdateRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    if auth_payload.get("role") not in ("artiste", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les artistes et les administrateurs peuvent gérer les accompagnements.",
        )
    _assert_project_owner(db, auth_payload, project_id)
    if db.execute(
        text('SELECT 1 FROM "ProjetMusical" WHERE id_projet = :project_id'),
        {"project_id": project_id},
    ).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")

    for formation in payload.formationsSuivies:
        allowed = db.execute(text('''
            SELECT 1 FROM "Formation" f
            WHERE f.id_formation = :reference_id
              AND (f.est_actif OR EXISTS (
                  SELECT 1 FROM "ProjetFormation" pf
                  WHERE pf.id_projet = :project_id
                    AND pf.id_formation = f.id_formation
                    AND pf.date_suivi = :date_suivi
              ))
        '''), {
            "reference_id": formation.formationId,
            "project_id": project_id,
            "date_suivi": formation.dateSuivi,
        }).first()
        if allowed is None:
            raise HTTPException(status_code=422, detail="Formation inconnue ou inactive.")
    for programme in payload.programmesPrecedents:
        allowed = db.execute(text('''
            SELECT 1 FROM "ProgrammeAccompagnement" pa
            WHERE pa.id_programme = :reference_id
              AND (pa.est_actif OR EXISTS (
                  SELECT 1 FROM "SuiviAccompagnement" sa
                  WHERE sa.id_projet = :project_id
                    AND sa.id_programme = pa.id_programme
                    AND sa.annee_participation = :annee_participation
              ))
        '''), {
            "reference_id": programme.programmeId,
            "project_id": project_id,
            "annee_participation": programme.anneeParticipation,
        }).first()
        if allowed is None:
            raise HTTPException(status_code=422, detail="Programme inconnu ou inactif.")

    db.execute(text('DELETE FROM "ProjetFormation" WHERE id_projet = :project_id'), {"project_id": project_id})
    db.execute(text('DELETE FROM "SuiviAccompagnement" WHERE id_projet = :project_id'), {"project_id": project_id})
    for formation in payload.formationsSuivies:
        db.execute(text('''
            INSERT INTO "ProjetFormation" (id_projet, id_formation, date_suivi)
            VALUES (:project_id, :formation_id, :date_suivi)
        '''), {
            "project_id": project_id,
            "formation_id": formation.formationId,
            "date_suivi": formation.dateSuivi,
        })
    for programme in payload.programmesPrecedents:
        db.execute(text('''
            INSERT INTO "SuiviAccompagnement" (
                id_projet, id_programme, annee_participation, est_laureat
            ) VALUES (
                :project_id, :programme_id, :annee_participation, :est_laureat
            )
        '''), {
            "project_id": project_id,
            "programme_id": programme.programmeId,
            "annee_participation": programme.anneeParticipation,
            "est_laureat": programme.estLaureat,
        })

    formations = db.execute(text('''
        SELECT f.id_formation AS "formationId", f.nom_formation AS nom,
               f.organisme_formateur AS organisme, pf.date_suivi AS "dateSuivi"
        FROM "ProjetFormation" pf
        JOIN "Formation" f ON f.id_formation = pf.id_formation
        WHERE pf.id_projet = :project_id
        ORDER BY pf.date_suivi DESC, lower(f.nom_formation)
    '''), {"project_id": project_id}).mappings().all()
    programs = db.execute(text('''
        SELECT pa.id_programme AS "programmeId", pa.nom_programme AS nom,
               pa.organisme_organisateur AS organisme,
               sa.annee_participation AS "anneeParticipation",
               COALESCE(sa.est_laureat, TRUE) AS "estLaureat"
        FROM "SuiviAccompagnement" sa
        JOIN "ProgrammeAccompagnement" pa ON pa.id_programme = sa.id_programme
        WHERE sa.id_projet = :project_id
        ORDER BY sa.annee_participation DESC, lower(pa.nom_programme)
    '''), {"project_id": project_id}).mappings().all()
    db.commit()
    return {
        "formationsSuivies": [dict(formation) for formation in formations],
        "programmesPrecedents": [dict(program) for program in programs],
    }


def _resolve_asset_type(db: Session, payload: AssetWriteRequest) -> tuple[int, str]:
    if payload.typeId is not None:
        asset_type = db.execute(
            text('SELECT id_type, libelle FROM "TypeAsset" WHERE id_type = :type_id'),
            {"type_id": payload.typeId},
        ).mappings().first()
    else:
        db.execute(
            text('''
                INSERT INTO "TypeAsset" (libelle)
                VALUES (:libelle)
                ON CONFLICT DO NOTHING
            '''),
            {"libelle": payload.typeLibelle},
        )
        asset_type = db.execute(
            text('''
                SELECT id_type, libelle FROM "TypeAsset"
                WHERE lower(trim(libelle)) = lower(trim(:libelle))
            '''),
            {"libelle": payload.typeLibelle},
        ).mappings().first()
    if not asset_type:
        raise HTTPException(status_code=422, detail="Type d'asset introuvable.")
    return asset_type["id_type"], asset_type["libelle"]


def _get_asset_response(db: Session, project_id: int, asset_id: int) -> dict:
    asset = db.execute(
        text('''
            SELECT a.id_asset AS id, a.titre, a.date_creation AS date,
                   ta.id_type AS "typeId", ta.libelle AS type,
                   COALESCE(a.metadonnees, '{}'::jsonb) AS metadata,
                   COALESCE(a.chemin_stockage, '') AS url,
                   COALESCE(a.est_featured_roster, FALSE) AS "featuredRoster",
                   (ep.id_evenement IS NOT NULL) AS "isJourneyEvent",
                   ep.id_evenement AS "eventId", ep.media_source AS "eventSource"
            FROM "Asset" a
            JOIN "TypeAsset" ta ON ta.id_type = a.id_type
            LEFT JOIN "EvenementParcours" ep ON ep.id_asset = a.id_asset
            WHERE a.id_projet = :project_id AND a.id_asset = :asset_id
        '''),
        {"project_id": project_id, "asset_id": asset_id},
    ).mappings().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset introuvable pour ce projet.")
    return dict(asset)


def _get_asset_highlight(db: Session, asset_id: int) -> dict | None:
    highlight = db.execute(
        text('''
            SELECT id_evenement AS id, type_evenement AS type, titre_evenement AS titre,
                   date_evenement AS date, media_source AS source, url_preuve AS url
            FROM "EvenementParcours"
            WHERE id_asset = :asset_id
        '''),
        {"asset_id": asset_id},
    ).mappings().first()
    return dict(highlight) if highlight else None


@app.get("/api/asset-types", response_model=list[AssetTypeResponse])
def get_asset_types(
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    del auth_payload
    rows = db.execute(
        text('''
            SELECT id_type AS id, libelle, description
            FROM "TypeAsset"
            ORDER BY lower(libelle), id_type
        ''')
    ).mappings().all()
    return [dict(row) for row in rows]


@app.post(
    "/api/projects/{project_id}/assets",
    response_model=AssetMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_asset(
    project_id: int,
    payload: AssetWriteRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    _assert_asset_write_access(db, auth_payload, project_id)
    if not db.execute(
        text('SELECT 1 FROM "ProjetMusical" WHERE id_projet = :project_id'),
        {"project_id": project_id},
    ).first():
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    try:
        type_id, type_label = _resolve_asset_type(db, payload)
        asset_id = db.execute(
            text('''
                INSERT INTO "Asset" (
                    id_projet, id_type, titre, date_creation, metadonnees,
                    chemin_stockage, est_featured_roster
                ) VALUES (
                    :project_id, :type_id, :titre, :date, CAST(:metadata AS JSONB),
                    :url, :featured_roster
                )
                RETURNING id_asset
            '''),
            {
                "project_id": project_id,
                "type_id": type_id,
                "titre": payload.titre,
                "date": payload.date,
                "metadata": json.dumps(payload.metadata),
                "url": payload.url or None,
                "featured_roster": payload.featuredRoster,
            },
        ).scalar_one()
        if payload.isJourneyEvent:
            db.execute(
                text('''
                    INSERT INTO "EvenementParcours" (
                        id_projet, id_asset, type_evenement, titre_evenement,
                        date_evenement, media_source, url_preuve
                    ) VALUES (
                        :project_id, :asset_id, :type_label, :titre,
                        :date, :source, :url
                    )
                '''),
                {
                    "project_id": project_id,
                    "asset_id": asset_id,
                    "type_label": type_label,
                    "titre": payload.titre,
                    "date": payload.date,
                    "source": payload.eventSource,
                    "url": payload.url or None,
                },
            )
        asset = _get_asset_response(db, project_id, asset_id)
        highlight = _get_asset_highlight(db, asset_id)
        db.commit()
        return {"asset": asset, "highlight": highlight}
    except Exception:
        db.rollback()
        raise


@app.post(
    "/api/projects/{project_id}/assets/upload",
    response_model=AssetMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_asset_upload(
    project_id: int,
    payload: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    _assert_asset_write_access(db, auth_payload, project_id)
    asset_payload = AssetWriteRequest.model_validate_json(payload)
    stored_url = await store_upload(project_id, file)
    asset_payload.url = stored_url
    try:
        return create_project_asset(project_id, asset_payload, db, auth_payload)
    except Exception:
        delete_managed_file(stored_url)
        raise


@app.patch(
    "/api/projects/{project_id}/assets/{asset_id}",
    response_model=AssetMutationResponse,
)
def update_project_asset(
    project_id: int,
    asset_id: int,
    payload: AssetWriteRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    _assert_asset_write_access(db, auth_payload, project_id)
    previous_asset = _get_asset_response(db, project_id, asset_id)

    try:
        type_id, type_label = _resolve_asset_type(db, payload)
        db.execute(
            text('''
                UPDATE "Asset"
                SET id_type = :type_id, titre = :titre, date_creation = :date,
                    metadonnees = CAST(:metadata AS JSONB), chemin_stockage = :url,
                    est_featured_roster = :featured_roster
                WHERE id_projet = :project_id AND id_asset = :asset_id
            '''),
            {
                "project_id": project_id,
                "asset_id": asset_id,
                "type_id": type_id,
                "titre": payload.titre,
                "date": payload.date,
                "metadata": json.dumps(payload.metadata),
                "url": payload.url or None,
                "featured_roster": payload.featuredRoster,
            },
        )
        existing_event_id = db.execute(
            text('SELECT id_evenement FROM "EvenementParcours" WHERE id_asset = :asset_id'),
            {"asset_id": asset_id},
        ).scalar()
        event_params = {
            "project_id": project_id,
            "asset_id": asset_id,
            "type_label": type_label,
            "titre": payload.titre,
            "date": payload.date,
            "source": payload.eventSource,
            "url": payload.url or None,
        }
        if payload.isJourneyEvent and existing_event_id:
            db.execute(
                text('''
                    UPDATE "EvenementParcours"
                    SET type_evenement = :type_label, titre_evenement = :titre,
                        date_evenement = :date, media_source = :source, url_preuve = :url
                    WHERE id_asset = :asset_id AND id_projet = :project_id
                '''),
                event_params,
            )
        elif payload.isJourneyEvent:
            db.execute(
                text('''
                    INSERT INTO "EvenementParcours" (
                        id_projet, id_asset, type_evenement, titre_evenement,
                        date_evenement, media_source, url_preuve
                    ) VALUES (
                        :project_id, :asset_id, :type_label, :titre,
                        :date, :source, :url
                    )
                '''),
                event_params,
            )
        elif existing_event_id:
            db.execute(
                text('DELETE FROM "EvenementParcours" WHERE id_asset = :asset_id'),
                {"asset_id": asset_id},
            )

        asset = _get_asset_response(db, project_id, asset_id)
        highlight = _get_asset_highlight(db, asset_id)
        db.commit()
        if previous_asset["url"] != asset["url"]:
            delete_managed_file(previous_asset["url"])
        return {"asset": asset, "highlight": highlight}
    except Exception:
        db.rollback()
        raise


@app.patch(
    "/api/projects/{project_id}/assets/{asset_id}/upload",
    response_model=AssetMutationResponse,
)
async def update_project_asset_upload(
    project_id: int,
    asset_id: int,
    payload: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    _assert_asset_write_access(db, auth_payload, project_id)
    _get_asset_response(db, project_id, asset_id)
    asset_payload = AssetWriteRequest.model_validate_json(payload)
    stored_url = await store_upload(project_id, file)
    asset_payload.url = stored_url
    try:
        response = update_project_asset(project_id, asset_id, asset_payload, db, auth_payload)
    except Exception:
        delete_managed_file(stored_url)
        raise
    return response


@app.delete(
    "/api/projects/{project_id}/assets/{asset_id}",
    response_model=AssetDeleteResponse,
)
def delete_project_asset(
    project_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    _assert_asset_write_access(db, auth_payload, project_id)
    asset = _get_asset_response(db, project_id, asset_id)
    staged_file = stage_managed_file(asset["url"])
    try:
        event_id = db.execute(
            text('''
                SELECT ep.id_evenement
                FROM "Asset" a
                LEFT JOIN "EvenementParcours" ep ON ep.id_asset = a.id_asset
                WHERE a.id_projet = :project_id AND a.id_asset = :asset_id
            '''),
            {"project_id": project_id, "asset_id": asset_id},
        ).scalar()
        deleted_id = db.execute(
            text('''
                DELETE FROM "Asset"
                WHERE id_projet = :project_id AND id_asset = :asset_id
                RETURNING id_asset
            '''),
            {"project_id": project_id, "asset_id": asset_id},
        ).scalar()
        if deleted_id is None:
            raise HTTPException(status_code=404, detail="Asset introuvable pour ce projet.")
        db.commit()
        finalize_staged_file(staged_file)
        return {"assetId": deleted_id, "eventId": event_id}
    except Exception:
        db.rollback()
        restore_staged_file(staged_file)
        raise


@app.patch(
    "/api/projects/{project_id}/tracks/{track_id}/originality",
    response_model=TrackOriginalityUpdateResponse,
)
def update_track_originality(
    project_id: int,
    track_id: int,
    payload: TrackOriginalityUpdateRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    if auth_payload.get("role") not in ("artiste", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les artistes et les administrateurs peuvent modifier un morceau.",
        )
    _assert_project_owner(db, auth_payload, project_id)

    updated_track = db.execute(
        text('''
            UPDATE "Morceau"
            SET est_reprise = :est_reprise
            WHERE id_morceau = :track_id AND id_projet = :project_id
            RETURNING id_morceau AS id, NOT est_reprise AS "estOriginal"
        '''),
        {
            "project_id": project_id,
            "track_id": track_id,
            "est_reprise": not payload.estOriginal,
        },
    ).mappings().first()
    if not updated_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Morceau introuvable pour ce projet.",
        )

    db.commit()
    return dict(updated_track)


@app.delete(
    "/api/projects/{project_id}/tracks/{track_id}",
    response_model=TrackDeleteResponse,
)
def delete_project_track(
    project_id: int,
    track_id: int,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    _assert_project_owner(db, auth_payload, project_id)
    deleted_id = db.execute(
        text('''
            DELETE FROM "Morceau"
            WHERE id_projet = :project_id AND id_morceau = :track_id
            RETURNING id_morceau
        '''),
        {"project_id": project_id, "track_id": track_id},
    ).scalar()
    if deleted_id is None:
        raise HTTPException(status_code=404, detail="Morceau introuvable pour ce projet.")

    db.commit()
    return {"trackId": deleted_id}


@app.post("/api/projects/{project_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: int,
    payload: MemberAddRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    """Ajoute un membre au projet : réutilise une Personne existante (par email) ou en crée une."""
    _assert_project_owner(db, auth_payload, project_id)

    existing_personne = db.execute(
        text('SELECT id_personne FROM "Personne" WHERE lower(email) = lower(:email)'),
        {"email": payload.email},
    ).first()

    if existing_personne:
        id_personne = existing_personne.id_personne
    else:
        new_personne = db.execute(
            text('''
                INSERT INTO "Personne" (nom_civil, prenom, date_naissance, genre, npa, ville, telephone, email)
                VALUES (:nom, :prenom, :date_naissance, :genre, :npa, :ville, :telephone, :email)
                RETURNING id_personne
            '''),
            {
                "nom": payload.nom,
                "prenom": payload.prenom,
                "date_naissance": payload.dateNaissance,
                "genre": payload.genre,
                "npa": payload.npa,
                "ville": payload.ville,
                "telephone": payload.telephone,
                "email": payload.email,
            },
        ).mappings().first()
        id_personne = new_personne["id_personne"]

    already_member = db.execute(
        text('''
            SELECT 1 FROM "MembreProjet"
            WHERE id_projet = :project_id AND id_personne = :id_personne AND date_depart IS NULL
        '''),
        {"project_id": project_id, "id_personne": id_personne},
    ).first()
    if already_member:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette personne est déjà membre du projet.")

    db.execute(
        text('''
            INSERT INTO "MembreProjet" (id_projet, id_personne, date_arrivee, role_dans_groupe)
            VALUES (:project_id, :id_personne, CURRENT_DATE, :role)
        '''),
        {"project_id": project_id, "id_personne": id_personne, "role": payload.role},
    )
    db.commit()

    member = db.execute(
        text('''
            SELECT pe.id_personne AS id, pe.nom_civil AS nom, pe.prenom,
                   pe.genre, pe.date_naissance AS "dateNaissance", pe.email,
                   pe.telephone, mp.role_dans_groupe AS role,
                   EXISTS(
                       SELECT 1 FROM "CompteUtilisateur" cu WHERE cu.id_personne = pe.id_personne
                   ) AS "hasAccount"
            FROM "MembreProjet" mp
            JOIN "Personne" pe ON pe.id_personne = mp.id_personne
            WHERE mp.id_projet = :project_id AND pe.id_personne = :id_personne AND mp.date_depart IS NULL
        '''),
        {"project_id": project_id, "id_personne": id_personne},
    ).mappings().first()

    return dict(member)


@app.delete("/api/projects/{project_id}/members/{personne_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: int,
    personne_id: int,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    """Retire un membre du projet (d\u00e9part logique : conserve l'historique)."""
    _assert_project_owner(db, auth_payload, project_id)

    updated = db.execute(
        text('''
            UPDATE "MembreProjet"
            SET date_depart = CURRENT_DATE
            WHERE id_projet = :project_id AND id_personne = :personne_id AND date_depart IS NULL
            RETURNING id_personne
        '''),
        {"project_id": project_id, "personne_id": personne_id},
    ).first()
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable pour ce projet.")

    db.commit()


@app.post("/api/projects/{project_id}/members/{personne_id}/invite", response_model=MemberInviteResponse)
def invite_project_member(
    project_id: int,
    personne_id: int,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    """Génère un lien d'invitation permettant à un membre de créer son compte de connexion."""
    _assert_project_owner(db, auth_payload, project_id)

    member = db.execute(
        text('''
            SELECT pe.email FROM "MembreProjet" mp
            JOIN "Personne" pe ON pe.id_personne = mp.id_personne
            WHERE mp.id_projet = :project_id AND mp.id_personne = :personne_id AND mp.date_depart IS NULL
        '''),
        {"project_id": project_id, "personne_id": personne_id},
    ).mappings().first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable pour ce projet.")

    existing_account = db.execute(
        text('SELECT 1 FROM "CompteUtilisateur" WHERE lower(email) = lower(:email)'),
        {"email": member["email"]},
    ).first()
    if existing_account:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette personne a déjà un compte de connexion.",
        )

    token = create_account_token(email=member["email"], role="artiste")
    return MemberInviteResponse(invitationUrl=f"http://localhost:5173/invite?token={token}")


_ZONE_TO_TYPE = {
    "Local/Neuchâtel": "Local (NE)",
    "Hors Canton": "Hors-Canton",
    "International/Hors Suisse": "Export",
}
_TYPE_TO_ZONE = {v: k for k, v in _ZONE_TO_TYPE.items()}


def _parse_concert_date(raw_date: str) -> date:
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw_date, fmt).date()
        except ValueError:
            continue
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Format de date invalide pour le concert (attendu JJ.MM.AAAA).",
    )


@app.get("/api/venues", response_model=list[VenueResponse])
def get_venues(
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    """Retourne les salles disponibles pour la création d'une date."""
    return db.execute(
        text('''
            SELECT id_venue AS id, nom_venue AS nom, adresse, ville, npa, pays,
                   valeur_pairs AS jauge, est_festival AS "estFestival"
            FROM "Venue"
            WHERE est_actif
            ORDER BY lower(nom_venue), lower(ville), id_venue
        ''')
    ).mappings().all()


@app.post("/api/projects/{project_id}/concerts", response_model=ConcertResponse, status_code=status.HTTP_201_CREATED)
def add_project_concert(
    project_id: int,
    payload: ConcertAddRequest,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    """Ajoute une date au projet avec une salle existante ou créée dans la même transaction."""
    _assert_project_owner(db, auth_payload, project_id)

    concert_date = _parse_concert_date(payload.date)
    zone = _TYPE_TO_ZONE[payload.type]

    has_existing_venue = payload.venueId is not None
    has_new_venue = payload.newVenue is not None
    if has_existing_venue == has_new_venue:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sélectionnez une salle existante ou renseignez une nouvelle salle.",
        )

    if payload.venueId is not None:
        existing_venue = db.execute(
            text('SELECT id_venue FROM "Venue" WHERE id_venue = :venue_id'),
            {"venue_id": payload.venueId},
        ).first()
        if not existing_venue:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salle introuvable.")
        id_venue = existing_venue.id_venue
    else:
        venue = payload.newVenue
        if venue is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Salle invalide.")
        new_venue = db.execute(
            text('''
                INSERT INTO "Venue" (
                    nom_venue, adresse, ville, npa, pays, valeur_pairs, est_festival
                ) VALUES (
                    :nom, :adresse, :ville, :npa, :pays, :jauge, :est_festival
                )
                RETURNING id_venue
            '''),
            {
                "nom": venue.nom.strip(),
                "adresse": venue.adresse.strip() if venue.adresse else None,
                "ville": venue.ville.strip(),
                "npa": venue.npa.strip() if venue.npa else None,
                "pays": venue.pays.strip(),
                "jauge": venue.jauge,
                "est_festival": venue.estFestival,
            },
        ).mappings().first()
        id_venue = new_venue["id_venue"]

    new_concert = db.execute(
        text('''
            INSERT INTO "Concert" (
                id_projet, id_venue, date_heure, type_evenement, zone_geographique, cachet_brut
            ) VALUES (
                :project_id, :id_venue, :date_heure, :type_evenement, :zone, :cachet_brut
            )
            RETURNING id_concert
        '''),
        {
            "project_id": project_id,
            "id_venue": id_venue,
            "date_heure": concert_date,
            "type_evenement": payload.typeEvenement,
            "zone": zone,
            "cachet_brut": payload.cachetBrut,
        },
    ).mappings().first()
    db.commit()

    concert = db.execute(
        text('''
            SELECT c.id_concert AS id, EXTRACT(YEAR FROM c.date_heure)::int AS annee,
                                     c.date_heure::date AS date, v.id_venue AS "venueId",
                                     v.nom_venue AS lieu, v.ville,
                   v.pays, v.valeur_pairs AS jauge,
                                     c.type_evenement AS "typeEvenement",
                                     c.cachet_brut AS "cachetBrut",
                   CASE c.zone_geographique
                     WHEN 'Local/Neuchâtel' THEN 'Local (NE)'
                     WHEN 'Hors Canton' THEN 'Hors-Canton'
                     ELSE 'Export'
                   END AS type
            FROM "Concert" c
            JOIN "Venue" v ON v.id_venue = c.id_venue
            WHERE c.id_concert = :id_concert
        '''),
        {"id_concert": new_concert["id_concert"]},
    ).mappings().first()

    return dict(concert)


@app.delete("/api/projects/{project_id}/concerts/{concert_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_concert(
    project_id: int,
    concert_id: int,
    db: Session = Depends(get_db),
    auth_payload: dict = Depends(get_auth_payload),
):
    """Supprime une date de concert du projet."""
    _assert_project_owner(db, auth_payload, project_id)

    deleted = db.execute(
        text('''
            DELETE FROM "Concert"
            WHERE id_concert = :concert_id AND id_projet = :project_id
            RETURNING id_concert
        '''),
        {"concert_id": concert_id, "project_id": project_id},
    ).first()
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concert introuvable pour ce projet.")

    db.commit()
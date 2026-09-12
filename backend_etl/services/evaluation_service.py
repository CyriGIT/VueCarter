from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend_etl.services.evaluation_criteria_service import calculate_objective_rules


def get_campaign(db: Session, campaign_id: int):
    campaign = db.execute(text('''
        SELECT id_campagne, nom_campagne, statut
        FROM "CampagneEvaluation"
        WHERE id_campagne = :campaign_id
    '''), {"campaign_id": campaign_id}).mappings().first()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campagne introuvable.")
    return campaign


def require_open_campaign(campaign) -> None:
    if campaign["statut"] != "ouverte":
        raise HTTPException(status_code=409, detail="La campagne n’est pas ouverte aux évaluations.")


def require_mutable_campaign(campaign) -> None:
    if campaign["statut"] == "cloturee":
        raise HTTPException(status_code=409, detail="Une campagne clôturée ne peut plus être modifiée.")


def require_campaign_project(db: Session, campaign_id: int, project_id: int) -> None:
    assigned = db.execute(text('''
        SELECT 1 FROM "CampagneProjet"
        WHERE id_campagne = :campaign_id AND id_projet = :project_id
    '''), {"campaign_id": campaign_id, "project_id": project_id}).first()
    if assigned is None:
        raise HTTPException(status_code=403, detail="Ce projet n’est pas affecté à la campagne.")


def require_campaign_juror(db: Session, campaign_id: int, expert_id: int) -> None:
    assigned = db.execute(text('''
        SELECT 1 FROM "CampagneJure"
        WHERE id_campagne = :campaign_id AND id_expert = :expert_id
    '''), {"campaign_id": campaign_id, "expert_id": expert_id}).first()
    if assigned is None:
        raise HTTPException(status_code=403, detail="Ce juré n’est pas affecté à la campagne.")


def calculate_score_summary(
    criterion_rows: list[dict],
    jury_rows: list[dict],
) -> dict:
    scored_criteria = [row for row in criterion_rows if row["note"] is not None]
    scored_weight = sum(row["poids"] for row in scored_criteria)
    grid_score = None
    if scored_weight:
        grid_score = 20 * sum(
            row["poids"] * row["note"] / row["note_maximale"]
            for row in scored_criteria
        ) / scored_weight

    present_jury_notes = [row["note"] for row in jury_rows if row["note"] is not None]
    jury_average = (
        sum(present_jury_notes) / len(present_jury_notes)
        if present_jury_notes else None
    )
    global_score = (
        (grid_score + sum(present_jury_notes)) / (len(present_jury_notes) + 1)
        if grid_score is not None else None
    )
    return {
        "gridScore": round(grid_score, 2) if grid_score is not None else None,
        "gridCoverageCount": len(scored_criteria),
        "gridCriteriaCount": len(criterion_rows),
        "juryAverage": round(jury_average, 2) if jury_average is not None else None,
        "globalScore": round(global_score, 2) if global_score is not None else None,
        "juryCoverageCount": len(present_jury_notes),
        "juryCount": len(jury_rows),
    }


def get_evaluation_summary(
    db: Session,
    campaign_id: int,
    project_id: int,
    current_person_id: int | None = None,
) -> dict:
    evaluation = db.execute(text('''
        SELECT id_bilan, remarques, statut_selection, decision_email_sent_at
        FROM "BilanEvaluation"
        WHERE id_campagne = :campaign_id AND id_projet = :project_id
    '''), {"campaign_id": campaign_id, "project_id": project_id}).mappings().first()
    evaluation_id = evaluation["id_bilan"] if evaluation else None
    criterion_rows = db.execute(text('''
        SELECT critere.code_critere, critere.note_maximale,
             critere.mode_evaluation, critere.regle_objective,
             campagne_critere.poids, appreciation.note::float AS note
        FROM "CampagneCritere" campagne_critere
        JOIN "CriteresEvaluation" critere
          ON critere.id_critere = campagne_critere.id_critere
        LEFT JOIN "AppreciationExpert" appreciation
          ON appreciation.id_critere = critere.id_critere
         AND appreciation.id_bilan = :evaluation_id
        WHERE campagne_critere.id_campagne = :campaign_id
        ORDER BY campagne_critere.ordre, critere.id_critere
    '''), {"campaign_id": campaign_id, "evaluation_id": evaluation_id}).mappings().all()
    criterion_rows = [dict(row) for row in criterion_rows]
    automatic_criteria = [
        row for row in criterion_rows
        if row["mode_evaluation"] == "automatique" and row["regle_objective"]
    ]
    if automatic_criteria:
        objective_values = calculate_objective_rules(db, project_id)
        for criterion in automatic_criteria:
            criterion["note"] = objective_values[criterion["regle_objective"]]
    jury_rows = db.execute(text('''
        SELECT personne.id_personne AS expert_id,
               concat_ws(' ', personne.prenom, personne.nom_civil) AS expert_nom,
               note.note
        FROM "CampagneJure" campagne_jure
        JOIN "Personne" personne ON personne.id_personne = campagne_jure.id_expert
        LEFT JOIN "NoteEvaluateur" note
          ON note.id_expert = campagne_jure.id_expert
         AND note.id_bilan = :evaluation_id
        WHERE campagne_jure.id_campagne = :campaign_id
        ORDER BY lower(personne.nom_civil), lower(personne.prenom)
    '''), {"campaign_id": campaign_id, "evaluation_id": evaluation_id}).mappings().all()
    scores = {
        row["code_critere"]: row["note"]
        for row in criterion_rows
        if row["note"] is not None
    }
    summary = calculate_score_summary(
        criterion_rows,
        [dict(row) for row in jury_rows],
    )
    return {
        "campaignId": campaign_id,
        "projectId": project_id,
        "bilanId": evaluation_id,
        "scores": scores,
        "remarques": (evaluation["remarques"] or "") if evaluation else "",
        "statut": evaluation["statut_selection"] if evaluation else "en_attente",
        "decisionEmailSentAt": evaluation["decision_email_sent_at"] if evaluation else None,
        **summary,
        "juryNotes": [
            {
                "expertId": row["expert_id"],
                "expertNom": row["expert_nom"],
                "note": row["note"],
                "estNotePersonnelle": row["expert_id"] == current_person_id,
            }
            for row in jury_rows
        ],
    }

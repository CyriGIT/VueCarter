import sys
import json
sys.path.append('.')
from database.database import SessionLocal
from sqlalchemy import text
from backend_etl.main import update_project_evaluation
from backend_etl.schemas.project import EvaluationUpdateRequest, EvaluationScores

db = SessionLocal()
try:
    # 1. Select the lowest existing project id
    row = db.execute(text('SELECT MIN(id_projet) FROM "ProjetMusical"')).fetchone()
    project_id = row[0]
    print(f"Project ID: {project_id}")
    
    # 2. Construct valid EvaluationUpdateRequest
    scores = EvaluationScores(
        respectCriteres=1,
        potentielArtistique=2,
        motivation=3,
        qualiteDossier=2,
        gestionnaire=10,
        juryAlpha=11,
        juryBeta=12,
        juryGamma=13,
        juryDelta=14
    )
    payload = EvaluationUpdateRequest(
        scores=scores,
        remarques="validation temporaire evaluation",
        statut="en_attente"
    )

    # 3. Call update_project_evaluation directly with auth_payload role='admin'
    auth_payload = {"role": "admin"}
    res = update_project_evaluation(
        project_id=project_id,
        payload=payload,
        db=db,
        auth_payload=auth_payload
    )
    created_id = res["id"]
    print(f"Created Evaluation ID: {created_id}")

    # 4. Verify returned id row has matching JSONB scores/status/remarks
    verify_row = db.execute(
        text('SELECT scores, remarques, statut_selection FROM "BilanEvaluation" WHERE id_bilan = :id'),
        {"id": created_id}
    ).fetchone()
    
    retrieved_scores = verify_row[0]
    retrieved_remarques = verify_row[1]
    retrieved_statut = verify_row[2]

    scores_match = (
        retrieved_scores.get("respectCriteres") == 1 and
        retrieved_scores.get("potentielArtistique") == 2 and
        retrieved_scores.get("motivation") == 3 and
        retrieved_scores.get("qualiteDossier") == 2 and
        retrieved_scores.get("gestionnaire") == 10 and
        retrieved_scores.get("juryAlpha") == 11 and
        retrieved_scores.get("juryBeta") == 12 and
        retrieved_scores.get("juryGamma") == 13 and
        retrieved_scores.get("juryDelta") == 14
    )
    remarques_match = (retrieved_remarques == "validation temporaire evaluation")
    statut_match = (retrieved_statut == "en_attente")

    print(f"Scores Match: {scores_match}")
    print(f"Remarks Match: {remarques_match}")
    print(f"Status Match: {statut_match}")

finally:
    # 5. Delete only that returned BilanEvaluation row and commit cleanup
    if 'created_id' in locals():
        db.execute(
            text('DELETE FROM "BilanEvaluation" WHERE id_bilan = :id'),
            {"id": created_id}
        )
        db.commit()
        print("Cleanup completed successfully.")
    db.close()

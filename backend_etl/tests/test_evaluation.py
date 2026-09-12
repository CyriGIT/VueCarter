import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from backend_etl.main import mark_decision_email_sent, update_project_evaluation
from backend_etl.routers.evaluation_campaigns import save_jury_note
from backend_etl.schemas.evaluation_campaign import JuryNoteWrite
from backend_etl.schemas.project import EvaluationUpdateRequest
from backend_etl.services.evaluation_service import (
    calculate_score_summary,
    get_evaluation_summary,
    require_mutable_campaign,
)


MANAGER_SCORES = {
    "potentielArtistique": 8,
    "motivation": 5,
    "qualiteDossier": 2,
}

OBJECTIVE_SCORES = {
    "objectifProjetNeuchatelois": 1,
    "objectifMembres18A25": 1,
    "objectifMorceauOriginal": 1,
    "objectifConcertEffectue": 0,
    "objectifRepertoire": 1,
}

CRITERIA = [
    {"id_critere": 10, "code_critere": "objectifProjetNeuchatelois", "type_critere": "objectif", "note_maximale": 1, "mode_evaluation": "automatique", "regle_objective": "projet_neuchatelois"},
    {"id_critere": 11, "code_critere": "objectifMembres18A25", "type_critere": "objectif", "note_maximale": 1, "mode_evaluation": "automatique", "regle_objective": "membres_18_25"},
    {"id_critere": 12, "code_critere": "objectifMorceauOriginal", "type_critere": "objectif", "note_maximale": 1, "mode_evaluation": "automatique", "regle_objective": "au_moins_un_morceau_original"},
    {"id_critere": 13, "code_critere": "objectifConcertEffectue", "type_critere": "objectif", "note_maximale": 1, "mode_evaluation": "automatique", "regle_objective": "concert_effectue"},
    {"id_critere": 14, "code_critere": "objectifRepertoire", "type_critere": "objectif", "note_maximale": 1, "mode_evaluation": "automatique", "regle_objective": "au_moins_un_morceau"},
    {"id_critere": 2, "code_critere": "potentielArtistique", "type_critere": "subjectif", "note_maximale": 8, "mode_evaluation": "manuel", "regle_objective": None},
    {"id_critere": 3, "code_critere": "motivation", "type_critere": "subjectif", "note_maximale": 5, "mode_evaluation": "manuel", "regle_objective": None},
    {"id_critere": 4, "code_critere": "qualiteDossier", "type_critere": "subjectif", "note_maximale": 2, "mode_evaluation": "manuel", "regle_objective": None},
]


class ScoreSummaryTests(unittest.TestCase):
    def test_missing_jury_notes_are_not_zero(self):
        result = calculate_score_summary(
            [{"poids": 1, "note": 4, "note_maximale": 5}],
            [{"note": 12}, {"note": None}, {"note": 18}],
        )

        self.assertEqual(result["gridScore"], 16)
        self.assertEqual(result["juryAverage"], 15)
        self.assertEqual(result["globalScore"], 15.33)
        self.assertEqual(result["juryCoverageCount"], 2)
        self.assertEqual(result["juryCount"], 3)

    def test_grid_counts_as_one_vote_without_jury_notes(self):
        result = calculate_score_summary(
            [{"poids": 1, "note": 4, "note_maximale": 5}],
            [{"note": None}, {"note": None}],
        )

        self.assertEqual(result["gridScore"], 16)
        self.assertIsNone(result["juryAverage"])
        self.assertEqual(result["globalScore"], 16)
        self.assertEqual(result["juryCoverageCount"], 0)

    def test_closed_campaign_is_immutable(self):
        with self.assertRaises(HTTPException) as context:
            require_mutable_campaign({"statut": "cloturee"})

        self.assertEqual(context.exception.status_code, 409)

    def test_historical_evaluation_recalculates_missing_automatic_scores(self):
        db = MagicMock()
        evaluation_result = MagicMock()
        evaluation_result.mappings.return_value.first.return_value = {
            "id_bilan": 42,
            "remarques": "Bilan historique",
            "statut_selection": "selectionne",
            "decision_email_sent_at": None,
        }
        criteria_result = MagicMock()
        criteria_result.mappings.return_value.all.return_value = [
            {
                "code_critere": criterion["code_critere"],
                "note_maximale": criterion["note_maximale"],
                "mode_evaluation": criterion["mode_evaluation"],
                "regle_objective": criterion["regle_objective"],
                "poids": 1,
                "note": None,
            }
            for criterion in CRITERIA[:5]
        ]
        objective_result = MagicMock()
        objective_result.mappings.return_value.one.return_value = {
            "projet_neuchatelois": True,
            "membres_18_25": True,
            "au_moins_un_morceau_original": True,
            "concert_effectue": True,
            "au_moins_un_morceau": True,
        }
        jury_result = MagicMock()
        jury_result.mappings.return_value.all.return_value = []
        db.execute.side_effect = [evaluation_result, criteria_result, objective_result, jury_result]

        result = get_evaluation_summary(db, campaign_id=1, project_id=1)

        self.assertEqual(result["scores"], {criterion["code_critere"]: 1 for criterion in CRITERIA[:5]})
        self.assertEqual(result["gridCoverageCount"], 5)
        self.assertEqual(result["gridCriteriaCount"], 5)


class EvaluationPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.payload = EvaluationUpdateRequest(
            campaignId=1,
            scores=MANAGER_SCORES,
            remarques="Évaluation complète",
            statut="selectionne",
        )

    def test_case_manager_snapshots_objectives_and_updates_manual_scores(self):
        db = MagicMock()

        def execute(query, params=None):
            sql = str(query)
            result = MagicMock()
            if 'FROM "CampagneEvaluation"' in sql:
                result.mappings.return_value.first.return_value = {
                    "id_campagne": 1, "nom_campagne": "Embrayage", "statut": "ouverte"
                }
            elif 'SELECT 1 FROM "CampagneProjet"' in sql:
                result.first.return_value = (1,)
            elif 'SELECT id_categorie_actuelle' in sql:
                result.scalar.return_value = 2
            elif 'critere.id_critere' in sql and 'appreciation.note' not in sql:
                result.mappings.return_value.all.return_value = CRITERIA
            elif 'AS projet_neuchatelois' in sql:
                result.mappings.return_value.one.return_value = {
                    "projet_neuchatelois": True,
                    "membres_18_25": True,
                    "au_moins_un_morceau_original": True,
                    "concert_effectue": False,
                    "au_moins_un_morceau": True,
                }
            elif 'SELECT id_bilan, remarques, statut_selection, decision_email_sent_at' in sql:
                result.mappings.return_value.first.return_value = {
                    "id_bilan": 42,
                    "remarques": "Évaluation complète",
                    "statut_selection": "selectionne",
                    "decision_email_sent_at": None,
                }
            elif 'appreciation.note::float' in sql:
                result.mappings.return_value.all.return_value = [
                    {
                        "code_critere": criterion["code_critere"],
                        "note_maximale": criterion["note_maximale"],
                        "mode_evaluation": criterion["mode_evaluation"],
                        "regle_objective": criterion["regle_objective"],
                        "poids": 1,
                        "note": {**MANAGER_SCORES, **OBJECTIVE_SCORES}[criterion["code_critere"]],
                    }
                    for criterion in CRITERIA
                ]
            elif 'FROM "CampagneJure" campagne_jure' in sql:
                result.mappings.return_value.all.return_value = [
                    {"expert_id": 11, "expert_nom": "Jury Un", "note": 12},
                    {"expert_id": 12, "expert_nom": "Jury Deux", "note": None},
                ]
            return result

        db.execute.side_effect = execute

        result = update_project_evaluation(
            project_id=4,
            payload=self.payload,
            db=db,
            auth_payload={"role": "gestionnaire_case", "id_personne": 7},
        )

        self.assertEqual(result["scores"], {**MANAGER_SCORES, **OBJECTIVE_SCORES})
        self.assertEqual(result["juryCoverageCount"], 1)
        self.assertEqual(result["juryCount"], 2)
        appreciation_writes = [
            call.args[1]
            for call in db.execute.call_args_list
            if 'INSERT INTO "AppreciationExpert"' in str(call.args[0])
        ]
        self.assertEqual(len(appreciation_writes), len(CRITERIA))
        self.assertEqual({row["expert_id"] for row in appreciation_writes}, {7})
        self.assertIn(
            "ON CONFLICT (id_bilan, id_critere)",
            next(str(call.args[0]) for call in db.execute.call_args_list if 'INSERT INTO "AppreciationExpert"' in str(call.args[0])),
        )
        db.commit.assert_called_once_with()

    def test_jury_cannot_use_manager_grid_endpoint(self):
        with self.assertRaises(HTTPException) as context:
            update_project_evaluation(
                project_id=4,
                payload=self.payload,
                db=MagicMock(),
                auth_payload={"role": "expert_jury", "id_personne": 11},
            )
        self.assertEqual(context.exception.status_code, 403)

    def test_unlinked_manager_cannot_save_evaluation(self):
        with self.assertRaises(HTTPException) as context:
            update_project_evaluation(
                project_id=4,
                payload=self.payload,
                db=MagicMock(),
                auth_payload={"role": "gestionnaire_case", "id_personne": None},
            )
        self.assertEqual(context.exception.status_code, 403)


class JuryNoteTests(unittest.TestCase):
    @patch("backend_etl.routers.evaluation_campaigns.get_evaluation_summary")
    def test_assigned_juror_upserts_one_global_note(self, summary_mock):
        summary_mock.return_value = {"campaignId": 1, "projectId": 4}
        db = MagicMock()
        campaign_result = MagicMock()
        campaign_result.mappings.return_value.first.return_value = {
            "id_campagne": 1, "nom_campagne": "Embrayage", "statut": "ouverte"
        }
        assigned_project = MagicMock()
        assigned_project.first.return_value = (1,)
        assigned_juror = MagicMock()
        assigned_juror.first.return_value = (1,)
        evaluation = MagicMock()
        evaluation.scalar.return_value = 42
        db.execute.side_effect = [campaign_result, assigned_project, assigned_juror, evaluation, MagicMock()]

        result = save_jury_note(
            campaign_id=1,
            project_id=4,
            payload=JuryNoteWrite(note=17),
            db=db,
            current_user=SimpleNamespace(role="expert_jury", id_personne=11),
        )

        self.assertEqual(result, {"campaignId": 1, "projectId": 4})
        note_write = db.execute.call_args_list[4]
        self.assertIn("ON CONFLICT (id_bilan, id_expert)", str(note_write.args[0]))
        self.assertEqual(note_write.args[1]["note"], 17)
        db.commit.assert_called_once_with()

    def test_non_juror_cannot_save_note(self):
        db = MagicMock()
        with self.assertRaises(HTTPException) as context:
            save_jury_note(
                campaign_id=1,
                project_id=4,
                payload=JuryNoteWrite(note=17),
                db=db,
                current_user=SimpleNamespace(role="gestionnaire_case", id_personne=7),
            )
        self.assertEqual(context.exception.status_code, 403)
        db.execute.assert_not_called()


class DecisionEmailTrackingTests(unittest.TestCase):
    def test_case_manager_marks_decision_email_sent(self):
        sent_at = datetime(2026, 9, 2, 10, 30, tzinfo=timezone.utc)
        db = MagicMock()
        evaluation_result = MagicMock()
        evaluation_result.mappings.return_value.first.return_value = {
            "id_bilan": 42,
            "statut_selection": "selectionne",
            "has_recipients": True,
        }
        update_result = MagicMock()
        update_result.scalar_one.return_value = sent_at
        db.execute.side_effect = [evaluation_result, update_result]

        result = mark_decision_email_sent(
            project_id=4,
            campaign_id=1,
            db=db,
            auth_payload={"role": "gestionnaire_case"},
        )

        self.assertEqual(result["decisionEmailSentAt"], sent_at)
        db.commit.assert_called_once_with()

    def test_pending_decision_cannot_be_marked_as_sent(self):
        db = MagicMock()
        evaluation_result = MagicMock()
        evaluation_result.mappings.return_value.first.return_value = {
            "id_bilan": 42,
            "statut_selection": "en_attente",
            "has_recipients": True,
        }
        db.execute.return_value = evaluation_result

        with self.assertRaises(HTTPException) as context:
            mark_decision_email_sent(
                project_id=4,
                campaign_id=1,
                db=db,
                auth_payload={"role": "gestionnaire_case"},
            )

        self.assertEqual(context.exception.status_code, 409)
        db.commit.assert_not_called()

    def test_jury_member_cannot_mark_decision_email_sent(self):
        db = MagicMock()
        with self.assertRaises(HTTPException) as context:
            mark_decision_email_sent(
                project_id=4,
                campaign_id=1,
                db=db,
                auth_payload={"role": "expert_jury"},
            )
        self.assertEqual(context.exception.status_code, 403)
        db.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()

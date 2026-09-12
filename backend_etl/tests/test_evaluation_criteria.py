import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError

from backend_etl.routers.evaluation_criteria import (
    create_evaluation_criterion,
    list_evaluation_criteria,
    update_evaluation_criterion,
)
from backend_etl.schemas.evaluation_criterion import (
    EvaluationCriterionUpdate,
    EvaluationCriterionWrite,
)
from backend_etl.services.evaluation_criteria_service import calculate_objective_rules


class EvaluationCriteriaTests(unittest.TestCase):
    def test_manager_can_create_manual_objective(self):
        db = MagicMock()
        inserted = MagicMock()
        inserted.scalar_one.return_value = 15
        returned = MagicMock()
        returned.mappings.return_value.first.return_value = {
            "id": 15,
            "code": "custom_code",
            "nom": "Présence aux rendez-vous",
            "type": "objectif",
            "noteMaximale": 1,
            "poids": 1,
            "ordre": 55,
            "estActif": True,
            "modeEvaluation": "manuel",
            "regleObjective": None,
            "evaluateurId": None,
            "evaluateurNom": None,
            "estUtilise": False,
        }
        db.execute.side_effect = [inserted, returned]
        payload = EvaluationCriterionWrite(
            nom="Présence aux rendez-vous",
            type="objectif",
            noteMaximale=1,
            poids=1,
            ordre=55,
            modeEvaluation="manuel",
        )

        result = create_evaluation_criterion(
            payload, db, SimpleNamespace(role="gestionnaire_case")
        )

        self.assertEqual(result["id"], 15)
        db.commit.assert_called_once_with()

    def test_jury_lists_active_criteria_only(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.all.return_value = []

        list_evaluation_criteria(False, db, SimpleNamespace(role="expert_jury"))

        query = str(db.execute.call_args.args[0])
        self.assertIn("critere.type_critere IN ('objectif', 'subjectif')", query)
        self.assertIn("AND critere.est_actif", query)

    def test_jury_type_is_not_a_general_criterion(self):
        with self.assertRaises(ValidationError):
            EvaluationCriterionWrite(
                nom="Note jury",
                type="jury",
                noteMaximale=20,
                poids=1,
                ordre=90,
                modeEvaluation="manuel",
            )

    def test_jury_cannot_include_inactive_criteria(self):
        with self.assertRaises(HTTPException) as context:
            list_evaluation_criteria(True, MagicMock(), SimpleNamespace(role="expert_jury"))
        self.assertEqual(context.exception.status_code, 403)

    def test_used_criterion_rejects_structural_change(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.first.return_value = {
            "id": 2,
            "type": "subjectif",
            "noteMaximale": 5,
            "poids": 1,
            "modeEvaluation": "manuel",
            "regleObjective": None,
            "estUtilise": True,
        }
        payload = EvaluationCriterionUpdate(
            nom="Motivation",
            type="subjectif",
            noteMaximale=10,
            poids=1,
            ordre=20,
            modeEvaluation="manuel",
            regleObjective=None,
            estActif=True,
        )

        with self.assertRaises(HTTPException) as context:
            update_evaluation_criterion(2, payload, db, SimpleNamespace(role="gestionnaire_case"))

        self.assertEqual(context.exception.status_code, 409)
        db.commit.assert_not_called()

    def test_artist_cannot_manage_criteria(self):
        with self.assertRaises(HTTPException) as context:
            list_evaluation_criteria(False, MagicMock(), SimpleNamespace(role="artiste"))
        self.assertEqual(context.exception.status_code, 403)

    def test_original_rule_accepts_one_original_among_covers(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.one.return_value = {
            "projet_neuchatelois": True,
            "membres_18_25": True,
            "au_moins_un_morceau_original": True,
            "concert_effectue": False,
            "au_moins_un_morceau": True,
        }

        result = calculate_objective_rules(db, 4)

        self.assertEqual(result["au_moins_un_morceau_original"], 1)
        sql = str(db.execute.call_args.args[0])
        self.assertIn("AND NOT est_reprise", sql)
        self.assertIn("'NEUCHÂTEL'", sql)
        self.assertIn("'NEUCHATEL'", sql)
        self.assertNotIn("NOT EXISTS", sql.split("AS au_moins_un_morceau_original")[0].split("AS membres_18_25")[-1])


if __name__ == "__main__":
    unittest.main()
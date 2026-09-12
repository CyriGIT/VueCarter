import unittest
from datetime import date
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError

from backend_etl.main import app, update_project_accompaniment
from backend_etl.schemas.project import ProjectAccompanimentUpdateRequest


def accompaniment_payload(**overrides):
    values = {
        "formationsSuivies": [
            {"formationId": 2, "dateSuivi": date(2026, 4, 15)},
        ],
        "programmesPrecedents": [
            {"programmeId": 3, "anneeParticipation": 2025, "estLaureat": True},
        ],
    }
    values.update(overrides)
    return ProjectAccompanimentUpdateRequest(**values)


class ProjectAccompanimentContractTests(unittest.TestCase):
    def test_accepts_empty_histories(self):
        payload = accompaniment_payload(formationsSuivies=[], programmesPrecedents=[])

        self.assertEqual(payload.formationsSuivies, [])
        self.assertEqual(payload.programmesPrecedents, [])

    def test_rejects_duplicate_formation_date_and_program_year(self):
        with self.assertRaises(ValidationError):
            accompaniment_payload(formationsSuivies=[
                {"formationId": 2, "dateSuivi": "2026-04-15"},
                {"formationId": 2, "dateSuivi": "2026-04-15"},
            ])
        with self.assertRaises(ValidationError):
            accompaniment_payload(programmesPrecedents=[
                {"programmeId": 3, "anneeParticipation": 2025, "estLaureat": True},
                {"programmeId": 3, "anneeParticipation": 2025, "estLaureat": False},
            ])

    def test_routes_are_exposed(self):
        paths = app.openapi()["paths"]

        self.assertIn("get", paths["/api/references/formations"])
        self.assertIn("get", paths["/api/references/programs"])
        self.assertIn("put", paths["/api/projects/{project_id}/accompaniment"])


class ProjectAccompanimentPersistenceTests(unittest.TestCase):
    def test_admin_replaces_both_histories_atomically(self):
        db = MagicMock()

        def execute(query, params=None):
            sql = str(query)
            result = MagicMock()
            if 'SELECT 1 FROM "ProjetMusical"' in sql:
                result.first.return_value = (1,)
            elif 'SELECT 1 FROM "Formation"' in sql:
                result.first.return_value = (1,)
            elif 'SELECT 1 FROM "ProgrammeAccompagnement"' in sql:
                result.first.return_value = (1,)
            elif 'SELECT f.id_formation AS "formationId"' in sql:
                result.mappings.return_value.all.return_value = [{
                    "formationId": 2,
                    "nom": "Présence scénique",
                    "organisme": "Organisme Démo",
                    "dateSuivi": date(2026, 4, 15),
                }]
            elif 'SELECT pa.id_programme AS "programmeId"' in sql:
                result.mappings.return_value.all.return_value = [{
                    "programmeId": 3,
                    "nom": "Embrayage",
                    "organisme": "Organisme Démo",
                    "anneeParticipation": 2025,
                    "estLaureat": True,
                }]
            return result

        db.execute.side_effect = execute

        response = update_project_accompaniment(
            4,
            accompaniment_payload(),
            db,
            {"role": "admin"},
        )

        sql_calls = [str(call.args[0]) for call in db.execute.call_args_list]
        self.assertTrue(any('DELETE FROM "ProjetFormation"' in sql for sql in sql_calls))
        self.assertTrue(any('DELETE FROM "SuiviAccompagnement"' in sql for sql in sql_calls))
        self.assertTrue(any('INSERT INTO "ProjetFormation"' in sql for sql in sql_calls))
        self.assertTrue(any('INSERT INTO "SuiviAccompagnement"' in sql for sql in sql_calls))
        self.assertEqual(response["formationsSuivies"][0]["dateSuivi"], date(2026, 4, 15))
        self.assertEqual(response["programmesPrecedents"][0]["anneeParticipation"], 2025)
        db.commit.assert_called_once_with()

    def test_expert_is_forbidden_before_query(self):
        db = MagicMock()

        with self.assertRaises(HTTPException) as context:
            update_project_accompaniment(
                4,
                accompaniment_payload(),
                db,
                {"role": "expert_jury"},
            )

        self.assertEqual(context.exception.status_code, 403)
        db.execute.assert_not_called()
        db.commit.assert_not_called()

    def test_unrelated_artist_is_forbidden_before_mutation(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as context:
            update_project_accompaniment(
                4,
                accompaniment_payload(),
                db,
                {"role": "artiste", "id_personne": 999},
            )

        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(db.execute.call_count, 1)
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()

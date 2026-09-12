import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException

from backend_etl.main import assign_accompanying_expert
from backend_etl.schemas.project import ProjectExpertAssignmentRequest


class ProjectExpertAssignmentTests(unittest.TestCase):
    def test_manager_assigns_active_expert_to_selected_project(self):
        db = MagicMock()
        selected = MagicMock()
        selected.scalar.return_value = "selectionne"
        expert = MagicMock()
        expert.mappings.return_value.first.return_value = {
            "id": 11,
            "nom": "Démo",
            "prenom": "Jury Alpha",
            "email": "jury.alpha@example.com",
        }
        assignment = MagicMock()
        assigned_at = datetime(2026, 9, 2, tzinfo=timezone.utc)
        assignment.scalar_one.return_value = assigned_at
        db.execute.side_effect = [selected, expert, assignment]

        result = assign_accompanying_expert(
            project_id=1,
            payload=ProjectExpertAssignmentRequest(expertId=11),
            db=db,
            auth_payload={"role": "gestionnaire_case"},
        )

        self.assertEqual(result["id"], 11)
        self.assertEqual(result["dateAffectation"], assigned_at)
        self.assertIn('ON CONFLICT (id_projet)', str(db.execute.call_args_list[2].args[0]))
        db.commit.assert_called_once_with()

    def test_non_selected_project_cannot_receive_expert(self):
        db = MagicMock()
        pending = MagicMock()
        pending.scalar.return_value = "en_attente"
        db.execute.return_value = pending

        with self.assertRaises(HTTPException) as context:
            assign_accompanying_expert(
                project_id=1,
                payload=ProjectExpertAssignmentRequest(expertId=11),
                db=db,
                auth_payload={"role": "gestionnaire_case"},
            )

        self.assertEqual(context.exception.status_code, 409)
        db.commit.assert_not_called()

    def test_jury_cannot_assign_expert(self):
        db = MagicMock()

        with self.assertRaises(HTTPException) as context:
            assign_accompanying_expert(
                project_id=1,
                payload=ProjectExpertAssignmentRequest(expertId=11),
                db=db,
                auth_payload={"role": "expert_jury"},
            )

        self.assertEqual(context.exception.status_code, 403)
        db.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()